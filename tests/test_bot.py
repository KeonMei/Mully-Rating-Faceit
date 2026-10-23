import pytest

from bot import extract_nickname, make_callback, maps_text, parse_callback, report_text
from src.analyzer import MatchResult, PlayerReport


@pytest.mark.parametrize("text, nickname", [
    ("s1mple", "s1mple"),
    ("  donk_666 ", "donk_666"),
    ("@ZywOo", "ZywOo"),
    ("https://www.faceit.com/en/players/s1mple", "s1mple"),
    ("faceit.com/ru/players/m0NESY/stats/cs2", "m0NESY"),
    ("https://www.faceit.com/players/Ax1Le?tab=stats", "Ax1Le"),
    ("hello world", None),
    ("a", None),
    ("<b>x</b>", None),
    ("", None),
])
def test_extract_nickname(text, nickname):
    assert extract_nickname(text) == nickname


def test_callback_round_trip():
    data = make_callback("an", 100, "some-long_Nick.12")
    assert len(data.encode()) <= 64  # Telegram limit for callback_data
    assert parse_callback(data) == ("an", 100, "some-long_Nick.12")


@pytest.mark.parametrize("data", ["m30", "trend", "maps", "an:7:nick", "an:x:nick", "an:30:", None])
def test_old_or_broken_callbacks_are_rejected(data):
    assert parse_callback(data) is None


def make_report(**changes):
    report = PlayerReport(
        nickname="Alice <3", avatar=None, elo=2100, level=10, flag="🇰🇿",
        score=72.5, tier="B", rank="🟢 B (Good)", bar="▰" * 14 + "▱" * 6,
        matches_requested=30,
        matches=[MatchResult("de_mirage", 80), MatchResult("de_nuke", 40)],
    )
    for key, value in changes.items():
        setattr(report, key, value)
    return report


def test_report_text():
    text = report_text(make_report())
    assert "🇰🇿 | Level 10 | 2100 ELO" in text
    assert "Matches analyzed: 2 of 30" in text
    assert "Mully Rating: 72.5" in text

    # No country: no dangling separator at the start of the line.
    assert report_text(make_report(flag="")).splitlines()[1] == "Level 10 | 2100 ELO"

    assert "Matches analyzed: 30\n" in report_text(make_report(
        matches=[MatchResult("de_mirage", 50)] * 30
    ))


def test_maps_text_escapes_html():
    text = maps_text(make_report())
    assert "Alice &lt;3" in text
    assert "Mirage" in text and "Nuke" in text
    assert text.count("<pre>") == 1 and text.count("</pre>") == 1
