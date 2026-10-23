"""FACEIT Mully Rating: a CS2 player rating and the Telegram bot that shows it.

Packages:
    faceit  - talking to the FACEIT Data API
    rating  - the Mully Rating formula, tiers and per-map rating
    bot     - the Telegram bot

analyzer.py ties them together: it downloads a player's matches and
turns them into a PlayerReport.
"""
