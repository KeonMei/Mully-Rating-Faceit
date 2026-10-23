"""Texts the bot sends."""

import html

from mully_rating.rating.maps import get_map_stats
from mully_rating.rating.tiers import progress_bar, tier_color

HELP_TEXT = (
    "Send a FACEIT nickname or a link to a FACEIT profile.\n\n"
    "I will calculate the Mully Rating (0–100) from recent CS2 matches "
    "and can show the rating trend and the rating on each map."
)

NOT_A_NICKNAME_TEXT = (
    "That doesn't look like a FACEIT nickname.\n"
    "Send a nickname (e.g. s1mple) or a faceit.com profile link."
)

FACEIT_DOWN_TEXT = "FACEIT is not responding right now. Please try again in a minute."

OUTDATED_BUTTON_TEXT = "This button is outdated. Send the nickname again."

SOMETHING_WENT_WRONG_TEXT = "Something went wrong. Please try again."


def choose_matches_text(nickname):
    return f"Player: {nickname}\nChoose number of matches:"


def analyzing_text(nickname, match_limit):
    return f"⏳ Analyzing {nickname}: last {match_limit} matches…"


def report_text(report):

    profile = " | ".join(
        part for part in (report.flag, f"Level {report.level}", f"{report.elo} ELO") if part
    )

    analyzed = str(report.matches_count)

    if report.matches_count < report.matches_requested:
        analyzed += f" of {report.matches_requested}"

    text = (
        f"👤 {report.nickname}\n"
        f"{profile}\n\n"
        f"Matches analyzed: {analyzed}\n\n"
        f"Mully Rating: {report.score}\n"
        f"{report.bar}\n\n"
        f"Rank: {report.rank}"
    )

    if report.components:
        parts = report.components
        text += (
            "\n\nBreakdown (50 = average player):\n"
            f"Combat {parts['combat']} · Multikills {parts['multi']}\n"
            f"Entry {parts['entry']} · Clutch {parts['clutch']}"
        )

    if report.stats:
        stats = report.stats
        text += f"\n\nADR {stats['adr']:.1f} · K/D {stats['kd']:.2f} · K/R {stats['kr']:.2f}"

    return text


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
