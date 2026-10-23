"""Runs the real handlers inside python-telegram-bot with a fake Telegram
server and a fake FACEIT API, and checks what the bot sends back."""

import asyncio
import json
import time

import pytest
from telegram import Update
from telegram.ext import ApplicationBuilder
from telegram.request import BaseRequest

from mully_rating.bot.app import add_handlers

from fakes import FakeClient, history_item, match_round, player_stats

BOT_USER = {"id": 1, "is_bot": True, "first_name": "Mully", "username": "mully_bot"}
USER = {"id": 42, "is_bot": False, "first_name": "User"}
CHAT = {"id": 42, "type": "private", "first_name": "User"}


class FakeTelegram(BaseRequest):
    """Answers Bot API calls locally and records them."""

    def __init__(self):
        self.calls = []

    @property
    def read_timeout(self):
        return 5

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def do_request(self, url, method, request_data=None, **kwargs):
        name = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        self.calls.append((name, params))

        if name == "getMe":
            result = BOT_USER
        elif name in ("sendMessage", "sendPhoto", "editMessageText"):
            result = {"message_id": len(self.calls) + 100, "date": int(time.time()), "chat": CHAT}
        else:
            result = True

        return 200, json.dumps({"ok": True, "result": result}).encode()

    def sent(self, method):
        return [params for name, params in self.calls if name == method]


def faceit_client():
    player = {
        "player_id": "pid", "nickname": "Alice", "avatar": "", "country": "kz",
        "games": {"cs2": {"faceit_elo": 2100, "skill_level": 10}},
    }
    return FakeClient({
        "/players": lambda params: player if params["nickname"].lower() == "alice" else None,
        "/players/pid/games/cs2/stats": {"items": [
            history_item("m1", "de_mirage", adr=95, kd=1.3),
            history_item("m2", "de_nuke", adr=70, kd=0.9),
        ]},
        "/matches/m1/stats": {"rounds": [match_round({"pid": player_stats(0.6, (2, 1), 3)})]},
        "/matches/m2/stats": {"rounds": [match_round({"pid": player_stats(0.3, (1, 0), 1)})]},
    })


def message(text):
    msg = {"message_id": 1, "date": int(time.time()), "chat": CHAT, "from": USER, "text": text}
    if text.startswith("/"):
        msg["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text)}]
    return {"update_id": 1, "message": msg}


def button(data):
    return {"update_id": 2, "callback_query": {
        "id": "cb", "from": USER, "chat_instance": "ci", "data": data,
        "message": {"message_id": 7, "date": int(time.time()), "chat": CHAT,
                    "from": BOT_USER, "text": "Player: Alice\nChoose number of matches:"},
    }}


@pytest.fixture
def bot():
    telegram = FakeTelegram()
    app = (
        ApplicationBuilder()
        .token("123:abc")
        .request(telegram)
        .get_updates_request(FakeTelegram())
        .concurrent_updates(True)
        .build()
    )
    app.bot_data["faceit"] = faceit_client()
    add_handlers(app)

    asyncio.run(app.initialize())

    def send(update):
        telegram.calls.clear()
        asyncio.run(app.process_update(Update.de_json(update, app.bot)))
        return telegram

    yield send

    asyncio.run(app.shutdown())


def test_start(bot):
    telegram = bot(message("/start"))
    assert "Send a FACEIT nickname" in telegram.sent("sendMessage")[0]["text"]


def test_profile_link_gives_match_buttons(bot):
    telegram = bot(message("https://www.faceit.com/en/players/Alice"))
    reply = telegram.sent("sendMessage")[0]
    assert reply["text"].startswith("Player: Alice")
    buttons = reply["reply_markup"]["inline_keyboard"][0]
    assert [b["callback_data"] for b in buttons] == ["an:10:Alice", "an:30:Alice", "an:50:Alice", "an:100:Alice"]


def test_not_a_nickname(bot):
    telegram = bot(message("hello there"))
    assert "doesn't look like a FACEIT nickname" in telegram.sent("sendMessage")[0]["text"]


def test_analysis_then_trend_and_maps(bot):
    telegram = bot(button("an:30:Alice"))

    edits = [e["text"] for e in telegram.sent("editMessageText")]
    assert edits[0].startswith("⏳ Analyzing Alice")
    assert edits[-1].startswith("Player: Alice")  # buttons are back

    card = telegram.sent("sendMessage")[0]  # no avatar -> text card
    assert "👤 Alice" in card["text"]
    assert "Matches analyzed: 2 of 30" in card["text"]
    buttons = card["reply_markup"]["inline_keyboard"][0]
    assert [b["callback_data"] for b in buttons] == ["tr:30:Alice", "mp:30:Alice"]

    telegram = bot(button("tr:30:Alice"))
    assert len(telegram.sent("sendPhoto")) == 1

    telegram = bot(button("mp:30:Alice"))
    maps = telegram.sent("sendMessage")[0]
    assert maps["parse_mode"] == "HTML"
    assert "Mirage" in maps["text"] and "Nuke" in maps["text"]


def test_unknown_player(bot):
    telegram = bot(button("an:10:Nobody"))
    assert telegram.sent("editMessageText")[-1]["text"] == "Player Nobody not found on FACEIT."


def test_button_from_old_version(bot):
    telegram = bot(button("m30"))
    answer = telegram.sent("answerCallbackQuery")[0]
    assert answer["show_alert"] is True
    assert "outdated" in answer["text"]
