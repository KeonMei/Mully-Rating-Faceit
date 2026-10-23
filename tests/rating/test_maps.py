from mully_rating.analyzer import MatchResult
from mully_rating.rating.formula import MatchTotals, rate
from mully_rating.rating.maps import get_map_stats, pretty_map_name


def test_pretty_map_name():
    assert pretty_map_name("de_mirage") == "Mirage"
    assert pretty_map_name("de_dust2") == "Dust2"
    assert pretty_map_name("cs_office") == "Office"
    assert pretty_map_name("") == "Unknown"


def test_matches_without_raw_stats_are_averaged():
    matches = [
        MatchResult("de_mirage", 80),
        MatchResult("de_mirage", 90),
        MatchResult("de_nuke", 40),
        MatchResult("de_inferno", 95),
    ]

    assert get_map_stats(matches) == [
        ("Inferno", 95.0, "S", 1),
        ("Mirage", 85.0, "A", 2),
        ("Nuke", 40.0, "D", 1),
    ]


def totals(adr, rounds):
    return MatchTotals(matches=1, rounds=rounds, damage=adr * rounds, kills_by_kr=0.7 * rounds,
                       kd_sum=1.0, mvps=2.1, entry_rate_sum=0.5, multikill_points=0.21 * rounds)


def test_rounds_on_a_map_are_rated_together():
    long_game, short_game = totals(adr=100, rounds=30), totals(adr=40, rounds=10)
    matches = [
        MatchResult("de_mirage", rate(long_game).score, long_game),
        MatchResult("de_mirage", rate(short_game).score, short_game),
    ]

    [(name, score, tier, games)] = get_map_stats(matches)

    # ADR on the map is (100 * 30 + 40 * 10) / 40 = 85, not (100 + 40) / 2 = 70.
    assert (name, games) == ("Mirage", 2)
    assert score == rate(long_game + short_game).score
    assert score > (matches[0].score + matches[1].score) / 2
