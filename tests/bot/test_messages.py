from mully_rating.analyzer import MatchResult, PlayerReport
from mully_rating.bot.messages import maps_text, report_text


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
