import pytest

from mully_rating.bot.nickname import extract_nickname


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
