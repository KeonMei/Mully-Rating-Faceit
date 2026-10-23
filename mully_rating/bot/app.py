"""Creates the Telegram bot, registers handlers and starts polling."""

import logging

from telegram import BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from mully_rating.bot import handlers
from mully_rating.bot.keyboards import ANALYZE, MAPS, TREND
from mully_rating.config import load_settings
from mully_rating.faceit.client import FaceitClient

log = logging.getLogger(__name__)


async def set_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "How to use the bot"),
        BotCommand("help", "How to use the bot"),
    ])


def add_handlers(app: Application):

    app.add_handler(CommandHandler(["start", "help"], handlers.start))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_nickname))

    app.add_handler(CallbackQueryHandler(handlers.matches_callback, pattern=f"^{ANALYZE}:"))
    app.add_handler(CallbackQueryHandler(handlers.trend_callback, pattern=f"^{TREND}:"))
    app.add_handler(CallbackQueryHandler(handlers.maps_callback, pattern=f"^{MAPS}:"))
    app.add_handler(CallbackQueryHandler(handlers.outdated_callback))

    app.add_error_handler(handlers.on_error)


def build_app(settings):

    app = (
        ApplicationBuilder()
        .token(settings.bot_token)
        # Handle several users at once instead of one update at a time.
        .concurrent_updates(True)
        .post_init(set_commands)
        .build()
    )

    app.bot_data["faceit"] = FaceitClient(settings.faceit_api_key)

    add_handlers(app)

    return app


def main():

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO
    )

    # httpx logs every Telegram request URL, and the URL contains the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    app = build_app(load_settings())

    log.info("Bot started")

    app.run_polling()
