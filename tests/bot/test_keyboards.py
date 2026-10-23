import pytest

from mully_rating.bot.keyboards import make_callback, matches_keyboard, parse_callback, report_keyboard


def test_callback_round_trip():
    data = make_callback("an", 100, "some-long_Nick.12")
    assert len(data.encode()) <= 64  # Telegram limit for callback_data
    assert parse_callback(data) == ("an", 100, "some-long_Nick.12")


@pytest.mark.parametrize("data", ["m30", "trend", "maps", "an:7:nick", "an:x:nick", "an:30:", None])
def test_old_or_broken_callbacks_are_rejected(data):
    assert parse_callback(data) is None


def test_keyboards_carry_nickname_and_match_count():
    matches = matches_keyboard("Alice").inline_keyboard[0]
    assert [b.text for b in matches] == ["10", "30", "50", "100"]
    assert [b.callback_data for b in matches] == ["an:10:Alice", "an:30:Alice", "an:50:Alice", "an:100:Alice"]

    report = report_keyboard("Alice", 50).inline_keyboard[0]
    assert [b.callback_data for b in report] == ["tr:50:Alice", "mp:50:Alice"]
