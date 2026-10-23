"""Recent player analyses, kept for a few minutes.

The Trend and Maps buttons reuse the analysis that was just shown
instead of downloading everything from FACEIT again.
"""

import asyncio
import time

from mully_rating.analyzer import analyze_player

# How long (seconds) an analysis stays reusable, and how many we keep.
REPORT_TTL = 10 * 60
REPORT_CACHE_SIZE = 200


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
