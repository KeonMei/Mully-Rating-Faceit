"""The Mully Rating formula: match stats -> score from 0 to 100."""


def clamp(value, min_value=0, max_value=1):
    return max(min_value, min(value, max_value))


def normalize(value, max_value, power=3.4):

    if max_value == 0:
        return 0

    ratio = value / max_value
    ratio = clamp(ratio)

    return ratio ** power


def clutch_rate(wins, attempts):
    if attempts == 0:
        return 0
    return clamp(wins / attempts)


def multikill_score(double, triple, quadra, ace, rounds):

    score = (
        1 * double +
        2 * triple +
        4 * quadra +
        6 * ace
    )

    score = score / max(rounds, 1)

    return clamp(score * 20)


def match_stat(match, advanced):
    """Stats of a single match in the shape compute_score() expects.

    `match` comes from player.get_matches(), `advanced` from
    match.analyze_match().
    """

    stat = {
        "ADR_avg": match["ADR"],
        "KD_avg": match["KD"],
        "KR_avg": match["KR"],
        "MVP_avg": match["MVPs"],
        "entry": advanced["entry_success"],
        "multi": multikill_score(
            advanced["double"],
            advanced["triple"],
            advanced["quadra"],
            advanced["ace"],
            advanced["rounds"]
        )
    }

    for kind, clutch in advanced["clutches"].items():
        stat[kind] = clutch_rate(clutch.wins, clutch.attempts)

    return stat


def compute_score(stats):

    adr = normalize(stats["ADR_avg"], 110, 3.1)
    kd = normalize(stats["KD_avg"], 1.7, 3.6)
    kr = normalize(stats["KR_avg"], 1.0, 2.8)

    entry = normalize(stats["entry"], 0.7, 2.6)

    mvp = normalize(stats["MVP_avg"], 2.5, 1.4)

    combat = (
        0.45 * adr +
        0.40 * kd +
        0.12 * kr +
        0.03 * mvp
    )

    clutch = clamp(
        stats["1v1"] * 0.40 +
        stats["1v2"] * 0.30 +
        stats["1v3"] * 0.15 +
        stats["1v4"] * 0.10 +
        stats["1v5"] * 0.05
    )

    multi = clamp(stats["multi"])

    score = 100 * clamp(
        0.80 * combat +
        0.05 * entry +
        0.05 * clutch +
        0.10 * multi
    )

    penalty = 0

    if stats["KD_avg"] < 1:
        penalty += (1 - stats["KD_avg"]) * 20

    if stats["ADR_avg"] < 80:
        penalty += (80 - stats["ADR_avg"]) * 0.4

    score = score - penalty

    score = clamp(score, 0, 100)

    return round(score, 2)
