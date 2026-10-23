from src.analyzer import MatchResult
from src.maps import get_map_stats, pretty_map_name
from src.trend import build_trend_chart

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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


def test_trend_chart_is_png():
    for scores in ([], [50], [10, 55.5, 80, 30]):
        chart = build_trend_chart(scores, "Alice")
        assert chart.read(8) == PNG_SIGNATURE
