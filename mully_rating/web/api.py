"""JSON API for the website.

    GET /api/rating?player=<nickname or FACEIT profile link>&matches=30

Answers with the player's Mully Rating, breakdown, per-match scores and
per-map ratings. Errors come back as {"error": "..."} with an HTTP code:
400 bad input, 404 player or matches not found, 503 FACEIT is down,
500 the server has no FACEIT_API_KEY.
"""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from mully_rating.analyzer import AnalysisError, analyze_player
from mully_rating.faceit.client import FaceitClient, FaceitError
from mully_rating.nickname import extract_nickname
from mully_rating.rating.formula import ANCHORS
from mully_rating.rating.maps import get_map_stats, pretty_map_name
from mully_rating.rating.tiers import TIER_NAMES

log = logging.getLogger(__name__)

MATCH_OPTIONS = (10, 30, 50, 100)
DEFAULT_MATCHES = 30

# Vercel's CDN keeps successful answers for 10 minutes and may serve
# them for one more hour while it refreshes them in the background.
# The same player is then not downloaded from FACEIT again on every
# visit, which keeps us far from the FACEIT API rate limit.
CACHE_OK = "public, max-age=0, s-maxage=600, stale-while-revalidate=3600"
CACHE_NOT_FOUND = "public, max-age=0, s-maxage=60"
NO_CACHE = "no-store"

BAD_NICKNAME = "That doesn't look like a FACEIT nickname. Enter a nickname or a faceit.com profile link."
BAD_MATCHES = "Number of matches must be one of: " + ", ".join(map(str, MATCH_OPTIONS)) + "."
FACEIT_DOWN = "FACEIT is not responding right now. Please try again in a minute."
NOT_CONFIGURED = "The server is not configured: FACEIT_API_KEY is missing."


def report_to_json(report):
    """PlayerReport -> plain dict for JSON."""

    stats = report.stats

    return {
        "player": {
            "nickname": report.nickname,
            "avatar": report.avatar,
            "country": report.country,
            "flag": report.flag,
            "level": report.level,
            "elo": report.elo,
        },
        "matches_requested": report.matches_requested,
        "matches_analyzed": report.matches_count,
        "score": report.score,
        "tier": report.tier,
        "tier_name": TIER_NAMES.get(report.tier, ""),
        "components": report.components,
        "stats": {
            "adr": round(stats["adr"], 1),
            "kd": round(stats["kd"], 2),
            "kr": round(stats["kr"], 2),
            "mvp": round(stats["mvp"], 2),
            "entry": round(stats["entry"], 3),
            "clutch": round(stats["clutch"], 2),
            "multi": round(stats["multi"], 3),
        } if stats else {},
        # What an average FACEIT player has, for comparison on the page.
        "averages": {name: average for name, (_, average, _) in ANCHORS.items()},
        # Oldest match first, as the per-match chart on the page shows them.
        "matches": [
            {"map": pretty_map_name(match.map), "score": match.score}
            for match in report.matches
        ],
        "maps": [
            {"map": name, "score": score, "tier": tier, "games": games}
            for name, score, tier, games in get_map_stats(report.matches)
        ],
    }


def rating_response(client, query):
    """(HTTP status, JSON body, Cache-Control) for a parsed query string.

    `query` is the output of urllib.parse.parse_qs: {"player": ["..."]}.
    """

    player = (query.get("player") or [""])[0]
    matches = (query.get("matches") or [str(DEFAULT_MATCHES)])[0]

    nickname = extract_nickname(player)

    if not nickname:
        return 400, {"error": BAD_NICKNAME}, NO_CACHE

    try:
        match_limit = int(matches)
    except ValueError:
        match_limit = None

    if match_limit not in MATCH_OPTIONS:
        return 400, {"error": BAD_MATCHES}, NO_CACHE

    try:
        report = analyze_player(client, nickname, match_limit)

    except AnalysisError as error:
        return 404, {"error": str(error)}, CACHE_NOT_FOUND

    except FaceitError:
        log.exception("FACEIT request failed for %s", nickname)
        return 503, {"error": FACEIT_DOWN}, NO_CACHE

    return 200, report_to_json(report), CACHE_OK


_client = None


def get_client():
    """One FaceitClient per running function (it is reused while warm)."""

    global _client

    if _client is None:
        api_key = os.getenv("FACEIT_API_KEY")
        if api_key:
            _client = FaceitClient(api_key)

    return _client


class RatingHandler(BaseHTTPRequestHandler):
    """HTTP handler for /api/rating. Vercel calls it as `handler`."""

    def do_GET(self):

        client = get_client()

        if client is None:
            status, body, cache_control = 500, {"error": NOT_CONFIGURED}, NO_CACHE
        else:
            query = parse_qs(urlparse(self.path).query)
            status, body, cache_control = rating_response(client, query)

        self.send_json(status, body, cache_control)

    def send_json(self, status, body, cache_control):

        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache_control)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        log.info("%s - %s", self.address_string(), format % args)
