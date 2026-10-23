import pytest

from mully_rating.faceit.matches import Duels
from mully_rating.rating.formula import (
    ANCHORS,
    COMBAT_WEIGHTS,
    DEFAULT_ROUNDS,
    WEIGHTS,
    MatchTotals,
    rate,
    scale,
)
from mully_rating.rating.tiers import score_tier


def player(adr=80, kd=1.0, kr=0.70, mvp=2.1, entry=0.50, clutch=1.0, multi=0.21):
    """MatchTotals whose stats() returns exactly these values."""
    return MatchTotals(
        matches=1,
        rounds=100,
        damage=adr * 100,
        kills_by_kr=kr * 100,
        kills=kd * 100,
        deaths=100,
        mvps=mvp,
        entry_rate_sum=entry,
        clutch_expected_wins=10,
        clutch_wins=clutch * 11 - 1,
        multikill_points=multi * 100,
    )


def no_clutches():
    return {kind: Duels(0, 0) for kind in ("1v1", "1v2", "1v3", "1v4", "1v5")}


def match_totals(adr=80, kd=1.0, kr=0.7, mvps=2, kills=None, deaths=None, rounds=24,
                 entry=None, entry_success=0.5, clutches=None, double=0, triple=0, quadra=0, ace=0):
    match = {"ADR": adr, "KD": kd, "KR": kr, "MVPs": mvps}
    if kills is not None:
        match["kills"] = kills
        match["deaths"] = deaths
    advanced = {
        "rounds": rounds, "entry": entry, "entry_success": entry_success,
        "clutches": {**no_clutches(), **(clutches or {})},
        "double": double, "triple": triple, "quadra": quadra, "ace": ace,
    }
    return MatchTotals.from_match(match, advanced)


def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1)
    assert sum(COMBAT_WEIGHTS.values()) == pytest.approx(1)


def test_scale_uses_three_anchors():
    assert scale(55, 55, 80, 110) == 0
    assert scale(80, 55, 80, 110) == 0.5
    assert scale(110, 55, 80, 110) == 1
    assert scale(67.5, 55, 80, 110) == pytest.approx(0.25)
    assert scale(95, 55, 80, 110) == pytest.approx(0.75)
    # Capped outside the anchors.
    assert scale(10, 55, 80, 110) == 0
    assert scale(200, 55, 80, 110) == 1


def test_anchors_are_ordered():
    for weak, average, elite in ANCHORS.values():
        assert weak < average < elite


def test_average_player_gets_50():
    rating = rate(player())
    assert rating.score == 50
    assert rating.components == {"combat": 50, "multi": 50, "entry": 50, "clutch": 50}


def test_empty_totals_are_average():
    assert rate(MatchTotals()).score == 50


# Typical stat lines; docs/rating.md shows the same table.
PROFILES = [
    ("D", dict(adr=62, kd=0.75, kr=0.55, mvp=1.4, entry=0.40, clutch=0.70, multi=0.13)),
    ("D", dict(adr=72, kd=0.90, kr=0.63, mvp=1.8, entry=0.46, clutch=0.90, multi=0.17)),
    ("C", dict(adr=80, kd=1.00, kr=0.70, mvp=2.1, entry=0.50, clutch=1.00, multi=0.21)),
    ("B", dict(adr=88, kd=1.15, kr=0.77, mvp=2.5, entry=0.54, clutch=1.15, multi=0.26)),
    ("A", dict(adr=97, kd=1.35, kr=0.84, mvp=3.0, entry=0.60, clutch=1.40, multi=0.32)),
    ("S", dict(adr=107, kd=1.55, kr=0.93, mvp=3.4, entry=0.67, clutch=1.80, multi=0.38)),
]


@pytest.mark.parametrize("tier, stats", PROFILES)
def test_reference_profiles_land_in_their_tier(tier, stats):
    assert score_tier(rate(player(**stats)).score) == tier


def test_better_profiles_score_higher():
    scores = [rate(player(**stats)).score for _, stats in PROFILES]
    assert scores == sorted(scores)
    assert 0 <= scores[0] and scores[-1] <= 100


def test_every_stat_moves_the_score():
    base = rate(player()).score
    better = dict(adr=95, kd=1.3, kr=0.85, mvp=3.0, entry=0.6, clutch=1.5, multi=0.3)
    for name, value in better.items():
        assert rate(player(**{name: value})).score > base, name


def test_score_is_capped():
    assert rate(player(adr=300, kd=9, kr=3, mvp=20, entry=1, clutch=10, multi=5)).score == 100
    assert rate(player(adr=0, kd=0, kr=0, mvp=0, entry=0, clutch=0, multi=0)).score == 0


def test_kd_is_total_kills_over_total_deaths():
    # A mean of per-match ratios would give (3.0 + 0.5) / 2 = 1.75.
    totals = match_totals(kills=30, deaths=10, kd=3.0) + match_totals(kills=10, deaths=20, kd=0.5)
    assert totals.stats()["kd"] == pytest.approx(40 / 30)


def test_kd_falls_back_to_ratio_without_kills_and_deaths():
    totals = match_totals(kd=1.2) + match_totals(kd=0.8)
    assert totals.stats()["kd"] == pytest.approx(1.0)


def test_adr_and_kr_are_weighted_by_rounds():
    totals = match_totals(adr=100, kr=1.0, rounds=30) + match_totals(adr=50, kr=0.5, rounds=10)
    assert totals.stats()["adr"] == pytest.approx(87.5)
    assert totals.stats()["kr"] == pytest.approx(0.875)


def test_missing_rounds_use_default():
    assert match_totals(rounds=0).rounds == DEFAULT_ROUNDS


def test_multikills_no_longer_hit_the_cap_at_two_doubles():
    # The old formula gave the maximum for 2 double kills per match,
    # so almost every player got the full bonus.
    def multi(**kills):
        return rate(match_totals(rounds=24, **kills)).components["multi"]

    assert multi(double=2) < 25
    assert 45 <= multi(double=3, triple=1) <= 55  # about average
    assert 75 < multi(double=5, triple=2) < 100
    assert multi(double=6, triple=2, quadra=1, ace=1) == 100


def test_clutches_compare_to_an_average_player():
    no_clutch = rate(match_totals()).stats["clutch"]
    lost_three_1v1_of_four = rate(match_totals(clutches={"1v1": Duels(4, 1)})).stats["clutch"]
    won_a_1v3 = rate(match_totals(clutches={"1v3": Duels(1, 1)})).stats["clutch"]

    assert no_clutch == 1  # no data -> average
    assert lost_three_1v1_of_four < 1  # 1 of 4 is below the 50% average
    assert won_a_1v3 > 1.8  # far above the 8% average


def test_entry_uses_duel_counts_when_present():
    # 3 of 4 duels plus 4 imaginary average duels: (3 + 2) / (4 + 4).
    assert match_totals(entry=Duels(4, 3)).stats()["entry"] == pytest.approx(5 / 8)
    # No duels at all -> average.
    assert match_totals(entry=Duels(0, 0)).stats()["entry"] == pytest.approx(0.5)


def test_entry_falls_back_to_success_rate():
    assert match_totals(entry=None, entry_success=0.8).stats()["entry"] == pytest.approx(0.8)
