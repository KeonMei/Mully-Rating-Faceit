import pytest

from mully_rating.rating.tiers import pretty_rank, progress_bar, score_tier, tier_color


@pytest.mark.parametrize("score, tier", [
    (100, "S"), (90, "S"), (89.9, "A"), (75, "A"), (60, "B"), (45, "C"), (44.9, "D"), (0, "D"),
])
def test_score_tier(score, tier):
    assert score_tier(score) == tier


def test_pretty_rank():
    assert pretty_rank("S") == "🟣 S (Strong)"
    assert pretty_rank("D") == "🔴 D (Weak)"
    assert pretty_rank("?") == "?"


def test_progress_bar():
    assert progress_bar(0) == "▱" * 20
    assert progress_bar(100) == "▰" * 20
    assert progress_bar(50) == "▰" * 10 + "▱" * 10
    assert progress_bar(150, length=10, filled_char="#", empty_char=".") == "#" * 10
    assert len(progress_bar(37.9)) == 20


def test_tier_color():
    assert tier_color("A") == "🔵"
    assert tier_color("?") == "⚪"
