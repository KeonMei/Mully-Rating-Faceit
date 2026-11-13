import pytest

from mully_rating.rating.tiers import TIER_NAMES, TIER_THRESHOLDS, score_tier


@pytest.mark.parametrize("score, tier", [
    (100, "S"), (90, "S"), (89.9, "A"), (75, "A"), (60, "B"), (45, "C"), (44.9, "D"), (0, "D"),
])
def test_score_tier(score, tier):
    assert score_tier(score) == tier


def test_every_tier_has_a_name():
    assert [tier for tier, _ in TIER_THRESHOLDS] == list(TIER_NAMES)
    assert TIER_NAMES["S"] == "Strong"
    assert TIER_NAMES["D"] == "Weak"
