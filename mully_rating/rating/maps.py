"""Mully Rating on each map."""

from collections import defaultdict

from mully_rating.rating.formula import MatchTotals, rate
from mully_rating.rating.tiers import score_tier


def pretty_map_name(name):
    """'de_mirage' -> 'Mirage'."""

    if not name:
        return "Unknown"

    for prefix in ("de_", "cs_"):
        if name.startswith(prefix):
            name = name[len(prefix):]

    return name.replace("_", " ").title()


def map_score(matches):
    """Rating of a group of matches on one map.

    All rounds on the map are rated together, exactly like the overall
    rating, so a single lucky clutch or a short 13-2 game does not
    weigh as much as a whole match.
    """

    if all(match.totals is not None for match in matches):

        totals = MatchTotals()

        for match in matches:
            totals = totals + match.totals

        return rate(totals).score

    # Matches without raw stats: average of their scores.
    return round(sum(match.score for match in matches) / len(matches), 1)


def get_map_stats(matches):
    """Mully Rating per map, best map first.

    `matches` is PlayerReport.matches. Returns a list of
    (map name, score, tier, games played).
    """

    maps = defaultdict(list)

    for match in matches:
        maps[pretty_map_name(match.map)].append(match)

    result = []

    for name, games in maps.items():
        score = map_score(games)
        result.append((name, score, score_tier(score), len(games)))

    result.sort(key=lambda x: x[1], reverse=True)

    return result
