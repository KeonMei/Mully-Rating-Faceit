"""Rating tiers (S–D) and their names."""

# Lowest score of each tier, best tier first.
TIER_THRESHOLDS = (
    ("S", 90),
    ("A", 75),
    ("B", 60),
    ("C", 45),
    ("D", 0),
)

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
