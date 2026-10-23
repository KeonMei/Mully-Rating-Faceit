"""Mully Rating on each map."""

from collections import defaultdict

from mully_rating.rating.tiers import score_tier


def pretty_map_name(name):
    """'de_mirage' -> 'Mirage'."""

    if not name:
        return "Unknown"

    for prefix in ("de_", "cs_"):
        if name.startswith(prefix):
            name = name[len(prefix):]

    return name.replace("_", " ").title()


def get_map_stats(matches):
    """Average Mully Rating per map, best map first.

    `matches` is PlayerReport.matches. Returns a list of
    (map name, average score, tier, games played).
    """

    maps = defaultdict(list)

    for match in matches:
        maps[pretty_map_name(match.map)].append(match.score)

    result = []

    for name, scores in maps.items():
        avg_score = sum(scores) / len(scores)
        result.append((name, round(avg_score, 1), score_tier(avg_score), len(scores)))

    result.sort(key=lambda x: x[1], reverse=True)

    return result
