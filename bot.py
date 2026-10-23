import asyncio
import html
import logging
import os
import re
import time

from dotenv import load_dotenv

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)

from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from src.analyzer import AnalysisError, analyze_player
from src.faceit import FaceitClient, FaceitError
from src.maps import get_map_stats
from src.score import progress_bar, tier_color
from src.trend import build_trend_chart

log = logging.getLogger("mully_bot")

MATCH_OPTIONS = (10, 30, 50, 100)

# Trend / Maps buttons reuse the last analysis for this many seconds
# instead of downloading everything from FACEIT again.
REPORT_TTL = 10 * 60
REPORT_CACHE_SIZE = 200

# FACEIT nicknames use latin letters, digits, "-" and "_".
NICKNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{2,32}$")

# https://www.faceit.com/en/players/s1mple -> s1mple
PROFILE_URL_RE = re.compile(
    r"faceit\.com/(?:[a-z]{2}(?:-[a-z]{2})?/)?players/([^/?#\s]+)",
    re.IGNORECASE
)

HELP_TEXT = (
    "Send a FACEIT nickname or a link to a FACEIT profile.\n\n"
    "I will calculate the Mully Rating (0–100) from recent CS2 matches "
    "and can show the rating trend and the rating on each map."
)

FACEIT_DOWN_TEXT = "FACEIT is not responding right now. Please try again in a minute."

OUTDATED_BUTTON_TEXT = "This button is outdated. Send the nickname again."


# ---------------------------HELPERS-----------------------------------------
def extract_nickname(text):
    """Nickname from a message: plain nickname or FACEIT profile link."""

    text = (text or "").strip()

    url_match = PROFILE_URL_RE.search(text)

    if url_match:
        text = url_match.group(1)

    text = text.lstrip("@")

    return text if NICKNAME_RE.match(text) else None


# Everything a button needs is stored in the button itself
# ("action:matches:nickname"), so buttons keep working after a restart
# and old messages always show the player they were sent for.
def make_callback(action, match_limit, nickname):
    return f"{action}:{match_limit}:{nickname}"


def parse_callback(data):

    try:
        action, match_limit, nickname = (data or "").split(":", 2)
        match_limit = int(match_limit)
    except ValueError:
        return None

    if match_limit not in MATCH_OPTIONS or not NICKNAME_RE.match(nickname):
        return None

    return action, match_limit, nickname


def matches_keyboard(nickname):

    return InlineKeyboardMarkup([[
        InlineKeyboardButton(str(n), callback_data=make_callback("an", n, nickname))
        for n in MATCH_OPTIONS
    ]])


def report_keyboard(nickname, match_limit):

    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Trend 📈", callback_data=make_callback("tr", match_limit, nickname)),
        InlineKeyboardButton("Maps 🗺", callback_data=make_callback("mp", match_limit, nickname))
    ]])


def choose_matches_text(nickname):
    return f"Player: {nickname}\nChoose number of matches:"


async def safe_edit(query, text, reply_markup=None):
    """Edit the button message; ignore 'message is not modified' and similar."""

    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as error:
        log.debug("Could not edit message: %s", error)


async def get_report(context, nickname, match_limit):
    """Analyse a player, reusing a fresh result if we have one."""

    cache = context.bot_data.setdefault("reports", {})
    key = (nickname.lower(), match_limit)

    cached = cache.get(key)

    if cached and time.monotonic() - cached[0] < REPORT_TTL:
        return cached[1]

    # FACEIT requests are blocking, so run them in a worker thread
    # to keep the bot responsive for other users meanwhile.
    report = await asyncio.to_thread(
        analyze_player,
        context.bot_data["faceit"],
        nickname,
        match_limit
    )

    now = time.monotonic()

    for old_key in [k for k, (saved_at, _) in cache.items() if now - saved_at >= REPORT_TTL]:
        del cache[old_key]

    while len(cache) >= REPORT_CACHE_SIZE:
        cache.pop(next(iter(cache)))

    cache[key] = (now, report)

    return report


def report_text(report):

    profile = " | ".join(
        part for part in (report.flag, f"Level {report.level}", f"{report.elo} ELO") if part
    )

    analyzed = str(report.matches_count)

    if report.matches_count < report.matches_requested:
        analyzed += f" of {report.matches_requested}"

    return (
        f"👤 {report.nickname}\n"
        f"{profile}\n\n"
        f"Matches analyzed: {analyzed}\n\n"
        f"Mully Rating: {report.score}\n"
        f"{report.bar}\n\n"
        f"Rank: {report.rank}"
    )


def maps_text(report):

    stats = get_map_stats(report.matches)[:8]

    width = max((len(name) for name, *_ in stats), default=0)

    lines = []

    for name, score, tier, games in stats:
        bar = progress_bar(score, length=10, filled_char="█", empty_char="░")
        lines.append(f"{tier_color(tier)} {name.ljust(width)} {score:5.1f} {bar} {games}")

    return (
        f"🗺 Map Mully Rating — {html.escape(report.nickname)}\n"
        f"Last {report.matches_count} matches\n\n"
        "<pre>" + html.escape("\n".join(lines)) + "</pre>\n"
        "Number on the right = games on that map."
    )


async def load_report_for_button(query, context, nickname, match_limit):
    """Report for Trend / Maps buttons; tells the user if it failed."""

    await query.message.chat.send_action(ChatAction.TYPING)

    try:
        return await get_report(context, nickname, match_limit)

    except AnalysisError as error:
        await query.message.reply_text(str(error))

    except FaceitError:
        log.exception("FACEIT request failed for %s", nickname)
        await query.message.reply_text(FACEIT_DOWN_TEXT)

    return None


# -------------START / HELP -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


# ------------HANDLE NICKNAME-----------
async def handle_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):

    nickname = extract_nickname(update.message.text)

    if not nickname:
        await update.message.reply_text(
            "That doesn't look like a FACEIT nickname.\n"
            "Send a nickname (e.g. s1mple) or a faceit.com profile link."
        )
        return

    await update.message.reply_text(
        choose_matches_text(nickname),
        reply_markup=matches_keyboard(nickname)
    )


# ---------------MATCHES CALLBACK------------------------------------------
async def matches_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    parsed = parse_callback(query.data)

    if not parsed:
        await query.answer(OUTDATED_BUTTON_TEXT, show_alert=True)
        return

    _, match_limit, nickname = parsed

    await query.answer()

    # Hide the buttons while working, so the same analysis is not started twice.
    await safe_edit(query, f"⏳ Analyzing {nickname}: last {match_limit} matches…")

    try:
        report = await get_report(context, nickname, match_limit)

    except AnalysisError as error:
        await safe_edit(query, str(error))
        return

    except FaceitError:
        log.exception("FACEIT request failed for %s", nickname)
        await safe_edit(
            query,
            f"{FACEIT_DOWN_TEXT}\n\n{choose_matches_text(nickname)}",
            reply_markup=matches_keyboard(nickname)
        )
        return

    text = report_text(report)
    keyboard = report_keyboard(nickname, match_limit)

    sent = False

    if report.avatar:
        try:
            await query.message.reply_photo(photo=report.avatar, caption=text, reply_markup=keyboard)
            sent = True
        except BadRequest as error:
            log.warning("Telegram could not send avatar %s: %s", report.avatar, error)

    if not sent:
        await query.message.reply_text(text, reply_markup=keyboard)

    # Bring the buttons back, so another number of matches can be picked.
    await safe_edit(query, choose_matches_text(nickname), reply_markup=matches_keyboard(nickname))


# ---------------------TREND CALLBACK----------------------------------------------
async def trend_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    parsed = parse_callback(query.data)

    if not parsed:
        await query.answer(OUTDATED_BUTTON_TEXT, show_alert=True)
        return

    _, match_limit, nickname = parsed

    await query.answer()

    report = await load_report_for_button(query, context, nickname, match_limit)

    if not report:
        return

    scores = [match.score for match in report.matches]

    chart = await asyncio.to_thread(build_trend_chart, scores, report.nickname)

    await query.message.reply_photo(chart)


# -------------------------MAPS CALLBACK-----------------------------
async def maps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    parsed = parse_callback(query.data)

    if not parsed:
        await query.answer(OUTDATED_BUTTON_TEXT, show_alert=True)
        return

    _, match_limit, nickname = parsed

    await query.answer()

    report = await load_report_for_button(query, context, nickname, match_limit)

    if not report:
        return

    await query.message.reply_text(maps_text(report), parse_mode=ParseMode.HTML)


# Buttons from older versions of the bot ("m30", "trend", "maps").
async def outdated_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer(OUTDATED_BUTTON_TEXT, show_alert=True)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):

    log.error("Unhandled error while processing an update", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("Something went wrong. Please try again.")
        except Exception:
            log.exception("Could not send the error message")


async def set_commands(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start", "How to use the bot"),
        BotCommand("help", "How to use the bot"),
    ])


# --------------------------BOT RUN------------------------------------------
def main():

    load_dotenv()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO
    )

    # httpx logs every Telegram request URL, and the URL contains the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    faceit_api_key = os.getenv("FACEIT_API_KEY")
    bot_token = os.getenv("TG_BOT_TOKEN")

    missing = [
        name for name, value in (("FACEIT_API_KEY", faceit_api_key), ("TG_BOT_TOKEN", bot_token))
        if not value
    ]

    if missing:
        raise SystemExit(
            f"Missing {', '.join(missing)}. Copy .env.example to .env and fill it in."
        )

    app = (
        ApplicationBuilder()
        .token(bot_token)
        # Handle several users at once instead of one update at a time.
        .concurrent_updates(True)
        .post_init(set_commands)
        .build()
    )

    app.bot_data["faceit"] = FaceitClient(faceit_api_key)

    app.add_handler(CommandHandler(["start", "help"], start))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nickname))

    app.add_handler(CallbackQueryHandler(matches_callback, pattern=r"^an:"))
    app.add_handler(CallbackQueryHandler(trend_callback, pattern=r"^tr:"))
    app.add_handler(CallbackQueryHandler(maps_callback, pattern=r"^mp:"))
    app.add_handler(CallbackQueryHandler(outdated_callback))

    app.add_error_handler(on_error)

    log.info("Bot started")

    app.run_polling()


if __name__ == "__main__":
    main()
