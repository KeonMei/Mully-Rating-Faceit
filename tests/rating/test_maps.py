from mully_rating.analyzer import MatchResult
from mully_rating.rating.maps import get_map_stats, pretty_map_name


def test_pretty_map_name():
    assert pretty_map_name("de_mirage") == "Mirage"
    assert pretty_map_name("de_dust2") == "Dust2"
    assert pretty_map_name("cs_office") == "Office"
    assert pretty_map_name("") == "Unknown"


def test_map_stats_are_averaged_and_sorted():
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
