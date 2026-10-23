"""Inline buttons and the data stored inside them.

Everything a button needs is kept in the button itself
("action:matches:nickname"), so buttons keep working after a restart
and old messages always show the player they were sent for.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from mully_rating.bot.nickname import is_nickname

MATCH_OPTIONS = (10, 30, 50, 100)

ANALYZE = "an"
TREND = "tr"
MAPS = "mp"


def make_callback(action, match_limit, nickname):
    return f"{action}:{match_limit}:{nickname}"


def parse_callback(data):
    """(action, match_limit, nickname) or None for unknown/old buttons."""

    try:
        action, match_limit, nickname = (data or "").split(":", 2)
        match_limit = int(match_limit)
    except ValueError:
        return None

    if match_limit not in MATCH_OPTIONS or not is_nickname(nickname):
        return None

    return action, match_limit, nickname


def matches_keyboard(nickname):

    return InlineKeyboardMarkup([[
        InlineKeyboardButton(str(n), callback_data=make_callback(ANALYZE, n, nickname))
        for n in MATCH_OPTIONS
    ]])


def report_keyboard(nickname, match_limit):

    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Trend 📈", callback_data=make_callback(TREND, match_limit, nickname)),
        InlineKeyboardButton("Maps 🗺", callback_data=make_callback(MAPS, match_limit, nickname))
    ]])
