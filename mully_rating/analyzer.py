"""Analyses a player: downloads matches and builds a PlayerReport."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from mully_rating.faceit.client import FaceitError
from mully_rating.faceit.matches import analyze_match
from mully_rating.faceit.players import get_matches, get_player_info
from mully_rating.rating.formula import MatchTotals, rate
from mully_rating.rating.tiers import pretty_rank, progress_bar, score_tier

# One pool for the whole bot: limits parallel FACEIT requests even when
# several users ask at the same time, so we hit rate limits less often.
_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="faceit")


class AnalysisError(Exception):
    """Problem with a message that can be shown to the user as is."""


@dataclass
class MatchResult:
    map: str
    score: float
    # Raw stats of the match; maps.py adds them up per map.
    totals: MatchTotals | None = None


@dataclass
class PlayerReport:
    nickname: str
    avatar: str | None
    elo: int | str
    level: int | str
    flag: str
    score: float
    tier: str
    rank: str
    bar: str
    matches_requested: int
    # Analysed matches, oldest first.
    matches: list[MatchResult] = field(default_factory=list)
    # Combat / multi / entry / clutch, each 0..100 (see rating/formula.py).
    components: dict = field(default_factory=dict)
    # Raw stats behind the score: adr, kd, kr, mvp, entry, clutch, multi.
    stats: dict = field(default_factory=dict)

    @property
    def matches_count(self):
        return len(self.matches)


def country_flag(code):
    if not code or len(code) != 2 or not code.isalpha():
        return ""
    return chr(127397 + ord(code[0].upper())) + chr(127397 + ord(code[1].upper()))


def analyze_player(client, nickname, match_limit=30):

    player = get_player_info(client, nickname)

    if not player:
        raise AnalysisError(f"Player {nickname} not found on FACEIT.")

    matches = get_matches(client, player.player_id, limit=match_limit)

    if not matches:
        raise AnalysisError(f"{player.nickname} has no CS2 matches on FACEIT.")

    def fetch_advanced(match):
        return analyze_match(
            client,
            match["match_id"],
            player.player_id,
            match.get("match_round")
        )

    advanced_results = list(_pool.map(fetch_advanced, matches))

    totals = MatchTotals()
    results = []

    for match, advanced in zip(matches, advanced_results):

        if not advanced:
            continue

        match_totals = MatchTotals.from_match(match, advanced)

        totals = totals + match_totals

        results.append(MatchResult(
            map=match["map"],
            score=rate(match_totals).score,
            totals=match_totals
        ))

    if not results:
        # Every match request failed: FACEIT is down or rate-limits us.
        raise FaceitError("Could not load details of any match")

    rating = rate(totals)
    tier = score_tier(rating.score)

    # FACEIT returns newest matches first; charts read better oldest first.
    results.reverse()

    return PlayerReport(
        nickname=player.nickname,
        avatar=player.avatar,
        elo=player.elo,
        level=player.level,
        flag=country_flag(player.country),
        score=rating.score,
        tier=tier,
        rank=pretty_rank(tier),
        bar=progress_bar(rating.score),
        matches_requested=match_limit,
        matches=results,
        components=rating.components,
        stats=rating.stats,
    )
