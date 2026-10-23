"""Rating tiers (S–D), their emoji and the text progress bar."""

# Lowest score of each tier, best tier first.
TIER_THRESHOLDS = (
    ("S", 90),
    ("A", 75),
    ("B", 60),
    ("C", 45),
    ("D", 0),
)

TIER_COLORS = {
    "S": "🟣",
    "A": "🔵",
    "B": "🟢",
    "C": "🟡",
    "D": "🔴"
}

TIER_NAMES = {
    "S": "Strong",
    "A": "Great",
    "B": "Good",
    "C": "Average",
    "D": "Weak"
}


def score_tier(score):

    for tier, lowest_score in TIER_THRESHOLDS:
        if score >= lowest_score:
            return tier

    return "D"


def tier_color(tier):
    return TIER_COLORS.get(tier, "⚪")


def pretty_rank(tier):

    if tier not in TIER_NAMES:
        return tier

    return f"{tier_color(tier)} {tier} ({TIER_NAMES[tier]})"


def progress_bar(score, length=20, filled_char="▰", empty_char="▱"):

    filled = int(length * max(0, min(score, 100)) / 100)

    return filled_char * filled + empty_char * (length - filled)
