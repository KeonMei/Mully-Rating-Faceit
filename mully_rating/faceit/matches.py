"""Detailed stats of one match (entry, clutches, multikills), with a cache."""

import threading
from collections import OrderedDict
from typing import NamedTuple

from mully_rating.faceit.client import FaceitError, to_float, to_int

CLUTCH_TYPES = ("1v1", "1v2", "1v3", "1v4", "1v5")

# How many matches to keep in memory. Each entry holds the stats of
# all 10 players, so 2000 matches is only a few MB.
CACHE_SIZE = 2000

_cache = OrderedDict()
_cache_lock = threading.Lock()


class Clutch(NamedTuple):
    attempts: int
    wins: int


def _parse_player(player_stats, rounds):

    return {
        "rounds": rounds,
        "entry_success": to_float(player_stats.get("Match Entry Success Rate")),
        "clutches": {
            kind: Clutch(
                attempts=to_int(player_stats.get(f"{kind}Count")),
                wins=to_int(player_stats.get(f"{kind}Wins")),
            )
            for kind in CLUTCH_TYPES
        },
        "double": to_int(player_stats.get("Double Kills")),
        "triple": to_int(player_stats.get("Triple Kills")),
        "quadra": to_int(player_stats.get("Quadro Kills")),
        "ace": to_int(player_stats.get("Penta Kills")),
    }


def _parse_match(data):
    """One entry per map of the match (BO1 has one, BO3 up to three)."""

    maps = []

    for round_data in data.get("rounds") or []:

        rounds = to_int(round_data.get("round_stats", {}).get("Rounds"))

        players = {}

        for team in round_data.get("teams", []):
            for player in team.get("players", []):
                player_id = player.get("player_id")
                if player_id:
                    players[player_id] = _parse_player(player.get("player_stats", {}), rounds)

        maps.append({
            "match_round": str(round_data.get("match_round", "")),
            "players": players,
        })

    return maps


def _get_match(client, match_id):
    """Parsed match stats, cached by match_id.

    The cache stores every player of the match, so analysing two
    players from the same game gives each of them their own stats.
    Failed requests are not cached and will be retried next time.
    """

    with _cache_lock:
        if match_id in _cache:
            _cache.move_to_end(match_id)
            return _cache[match_id]

    try:
        data = client.get(f"/matches/{match_id}/stats")
    except FaceitError:
        return None

    if not data:
        return None

    maps = _parse_match(data)

    if not maps:
        return None

    with _cache_lock:
        _cache[match_id] = maps
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)

    return maps


def analyze_match(client, match_id, player_id, match_round=None):
    """Advanced stats (entry, clutches, multikills) of one player in one match."""

    maps = _get_match(client, match_id)

    if not maps:
        return None

    chosen = maps[0]

    if match_round:
        for game_map in maps:
            if game_map["match_round"] == str(match_round):
                chosen = game_map
                break

    return chosen["players"].get(player_id)


def clear_cache():
    with _cache_lock:
        _cache.clear()
