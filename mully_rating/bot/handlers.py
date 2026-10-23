"""What the bot does on messages and button taps."""

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from mully_rating.analyzer import AnalysisError
from mully_rating.bot import messages
from mully_rating.bot.charts import build_trend_chart
from mully_rating.bot.keyboards import matches_keyboard, parse_callback, report_keyboard
from mully_rating.bot.nickname import extract_nickname
from mully_rating.bot.reports import get_report
from mully_rating.faceit.client import FaceitError

log = logging.getLogger(__name__)


# ---------------------------HELPERS-----------------------------------------
async def safe_edit(query, text, reply_markup=None):
    """Edit the button message; ignore 'message is not modified' and similar."""

    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as error:
        log.debug("Could not edit message: %s", error)


async def button_data(query):
    """(match_limit, nickname) of a pressed button, or None if it is outdated."""

    parsed = parse_callback(query.data)

    if not parsed:
        await query.answer(messages.OUTDATED_BUTTON_TEXT, show_alert=True)
        return None

    await query.answer()

    _, match_limit, nickname = parsed

    return match_limit, nickname


async def load_report_for_button(query, context, nickname, match_limit):
    """Report for Trend / Maps buttons; tells the user if it failed."""

    await query.message.chat.send_action(ChatAction.TYPING)

    try:
        return await get_report(context, nickname, match_limit)

    except AnalysisError as error:
        await query.message.reply_text(str(error))

    except FaceitError:
        log.exception("FACEIT request failed for %s", nickname)
        await query.message.reply_text(messages.FACEIT_DOWN_TEXT)

    return None


# -------------START / HELP -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(messages.HELP_TEXT)


# ------------HANDLE NICKNAME-----------
async def handle_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):

    nickname = extract_nickname(update.message.text)

    if not nickname:
        await update.message.reply_text(messages.NOT_A_NICKNAME_TEXT)
        return

    await update.message.reply_text(
        messages.choose_matches_text(nickname),
        reply_markup=matches_keyboard(nickname)
    )


# ---------------MATCHES CALLBACK------------------------------------------
async def matches_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    data = await button_data(query)

    if not data:
        return

    match_limit, nickname = data

    # Hide the buttons while working, so the same analysis is not started twice.
    await safe_edit(query, messages.analyzing_text(nickname, match_limit))

    try:
        report = await get_report(context, nickname, match_limit)

    except AnalysisError as error:
        await safe_edit(query, str(error))
        return

    except FaceitError:
        log.exception("FACEIT request failed for %s", nickname)
        await safe_edit(
            query,
            f"{messages.FACEIT_DOWN_TEXT}\n\n{messages.choose_matches_text(nickname)}",
            reply_markup=matches_keyboard(nickname)
        )
        return

    text = messages.report_text(report)
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
    await safe_edit(
        query,
        messages.choose_matches_text(nickname),
        reply_markup=matches_keyboard(nickname)
    )


# ---------------------TREND CALLBACK----------------------------------------------
async def trend_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    data = await button_data(query)

    if not data:
        return

    match_limit, nickname = data

    report = await load_report_for_button(query, context, nickname, match_limit)

    if not report:
        return

    scores = [match.score for match in report.matches]

    chart = await asyncio.to_thread(build_trend_chart, scores, report.nickname)

    await query.message.reply_photo(chart)


# -------------------------MAPS CALLBACK-----------------------------
async def maps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    data = await button_data(query)

    if not data:
        return

    match_limit, nickname = data

    report = await load_report_for_button(query, context, nickname, match_limit)

    if not report:
        return

    await query.message.reply_text(messages.maps_text(report), parse_mode=ParseMode.HTML)


# Buttons from older versions of the bot ("m30", "trend", "maps").
async def outdated_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer(messages.OUTDATED_BUTTON_TEXT, show_alert=True)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):

    log.error("Unhandled error while processing an update", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(messages.SOMETHING_WENT_WRONG_TEXT)
        except Exception:
            log.exception("Could not send the error message")
