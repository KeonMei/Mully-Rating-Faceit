"""FACEIT Mully Rating: a CS2 player rating, the Telegram bot and the
website that show it.

Packages:
    faceit  - talking to the FACEIT Data API
    rating  - the Mully Rating formula, tiers and per-map rating
    bot     - the Telegram bot
    web     - the JSON API behind the website

analyzer.py ties them together: it downloads a player's matches and
turns them into a PlayerReport. nickname.py reads a nickname or a
FACEIT profile link; the bot and the website both use it.
"""
