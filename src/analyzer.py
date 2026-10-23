from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from src.faceit import FaceitError
from src.match import CLUTCH_TYPES, analyze_match
from src.player import get_matches, get_player_info
from src.score import clutch_rate, compute_score, match_stat, multikill_score
from src.score import pretty_rank, progress_bar, score_tier

# One pool for the whole bot: limits parallel FACEIT requests even when
# several users ask at the same time, so we hit rate limits less often.
_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="faceit")


class AnalysisError(Exception):
    """Problem with a message that can be shown to the user as is."""


@dataclass
class MatchResult:
    map: str
    score: float


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

    totals = {
        "ADR": 0, "KD": 0, "KR": 0, "MVP": 0, "entry": 0,
        "double": 0, "triple": 0, "quadra": 0, "ace": 0, "rounds": 0,
    }
    clutch_totals = {kind: [0, 0] for kind in CLUTCH_TYPES}  # [wins, attempts]

    results = []

    for match, advanced in zip(matches, advanced_results):

        if not advanced:
            continue

        totals["ADR"] += match["ADR"]
        totals["KD"] += match["KD"]
        totals["KR"] += match["KR"]
        totals["MVP"] += match["MVPs"]
        totals["entry"] += advanced["entry_success"]

        for key in ("double", "triple", "quadra", "ace", "rounds"):
            totals[key] += advanced[key]

        for kind, clutch in advanced["clutches"].items():
            clutch_totals[kind][0] += clutch.wins
            clutch_totals[kind][1] += clutch.attempts

        results.append(MatchResult(
            map=match["map"],
            score=compute_score(match_stat(match, advanced))
        ))

    if not results:
        # Every match request failed: FACEIT is down or rate-limits us.
        raise FaceitError("Could not load details of any match")

    count = len(results)

    stats = {
        "ADR_avg": totals["ADR"] / count,
        "KD_avg": totals["KD"] / count,
        "KR_avg": totals["KR"] / count,
        "MVP_avg": totals["MVP"] / count,
        "entry": totals["entry"] / count,
        "multi": multikill_score(
            totals["double"],
            totals["triple"],
            totals["quadra"],
            totals["ace"],
            totals["rounds"]
        )
    }

    for kind, (wins, attempts) in clutch_totals.items():
        stats[kind] = clutch_rate(wins, attempts)

    score = compute_score(stats)
    tier = score_tier(score)

    # FACEIT returns newest matches first; charts read better oldest first.
    results.reverse()

    return PlayerReport(
        nickname=player.nickname,
        avatar=player.avatar,
        elo=player.elo,
        level=player.level,
        flag=country_flag(player.country),
        score=score,
        tier=tier,
        rank=pretty_rank(tier),
        bar=progress_bar(score),
        matches_requested=match_limit,
        matches=results,
    )
