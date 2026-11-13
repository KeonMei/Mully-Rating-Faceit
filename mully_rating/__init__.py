"""FACEIT Mully Rating: a CS2 player rating and the website that shows it.

Packages:
    faceit  - talking to the FACEIT Data API
    rating  - the Mully Rating formula, tiers and per-map rating
    web     - the JSON API behind the website

analyzer.py ties them together: it downloads a player's matches and
turns them into a PlayerReport. nickname.py reads a nickname or a
FACEIT profile link typed by the user.
"""
