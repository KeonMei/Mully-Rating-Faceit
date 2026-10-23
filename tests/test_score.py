import pytest

from src.match import Clutch
from src.score import (
    clamp,
    clutch_rate,
    compute_score,
    match_stat,
    multikill_score,
    normalize,
    pretty_rank,
    progress_bar,
    score_tier,
)


def stats(adr=80, kd=1.0, kr=0.7, mvp=2, entry=0.5, clutch=0.3, multi=0.5):
    return {
        "ADR_avg": adr, "KD_avg": kd, "KR_avg": kr, "MVP_avg": mvp, "entry": entry,
        "1v1": clutch, "1v2": clutch, "1v3": clutch, "1v4": clutch, "1v5": clutch,
        "multi": multi,
    }


def test_clamp_and_normalize():
    assert clamp(5) == 1
    assert clamp(-1) == 0
    assert normalize(0, 0) == 0
    assert normalize(200, 100) == 1
    assert normalize(50, 100, power=1) == 0.5


def test_clutch_rate():
    assert clutch_rate(0, 0) == 0
    assert clutch_rate(1, 4) == 0.25
    assert clutch_rate(5, 4) == 1


def test_multikill_score_is_per_round_and_capped():
    assert multikill_score(0, 0, 0, 0, 0) == 0
    assert multikill_score(1, 0, 0, 0, 40) == pytest.approx(0.5)
    assert multikill_score(10, 10, 10, 10, 20) == 1


def test_score_is_in_range_and_grows_with_better_stats():
    weak = compute_score(stats(adr=60, kd=0.7, kr=0.5))
    average = compute_score(stats())
    strong = compute_score(stats(adr=110, kd=1.7, kr=1.0, mvp=4, entry=0.7, clutch=1, multi=1))

    assert 0 <= weak < average < strong <= 100
    assert compute_score(stats(adr=0, kd=0, kr=0, mvp=0, entry=0, clutch=0, multi=0)) == 0


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


def test_match_stat_uses_wins_divided_by_attempts():
    # Regression: per-match clutch rate used to be attempts / wins.
    match = {"ADR": 90, "KD": 1.2, "KR": 0.8, "MVPs": 3}
    advanced = {
        "rounds": 24, "entry_success": 0.6,
        "double": 2, "triple": 0, "quadra": 0, "ace": 0,
        "clutches": {
            "1v1": Clutch(attempts=4, wins=1),
            "1v2": Clutch(attempts=0, wins=0),
            "1v3": Clutch(attempts=2, wins=2),
            "1v4": Clutch(attempts=0, wins=0),
            "1v5": Clutch(attempts=0, wins=0),
        },
    }

    stat = match_stat(match, advanced)

    assert stat["1v1"] == 0.25
    assert stat["1v2"] == 0
    assert stat["1v3"] == 1
    assert stat["ADR_avg"] == 90
    assert stat["multi"] == multikill_score(2, 0, 0, 0, 24)
