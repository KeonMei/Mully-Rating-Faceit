"""Suggest rating anchors from real FACEIT players.

The anchors in mully_rating/rating/formula.py say which value of each
stat is "weak", "average" and "elite". This script analyses a list of
players and prints the 10th percentile, the median and the 95th
percentile of every stat, ready to paste into ANCHORS.

Usage (needs FACEIT_API_KEY in .env):

    python scripts/calibrate.py s1mple donk m0NESY ...
    python scripts/calibrate.py --file players.txt --matches 50

Use as many players as you can (50+), from the levels your users play
at. The median of that group becomes the "average" of the rating.
"""

import argparse
import os
import sys
from pathlib import Path

# Make "mully_rating" importable when the script is run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

from mully_rating.analyzer import AnalysisError, analyze_player  # noqa: E402
from mully_rating.faceit.client import FaceitClient, FaceitError  # noqa: E402
from mully_rating.rating.formula import ANCHORS  # noqa: E402

WEAK_PERCENTILE = 10
ELITE_PERCENTILE = 95


def percentile(values, percent):
    """Linear-interpolated percentile of a non-empty list."""

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)

    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def suggest_anchors(player_stats):
    """{stat: (weak, average, elite)} from a list of PlayerReport.stats."""

    suggestions = {}

    for name in ANCHORS:
        values = [stats[name] for stats in player_stats]
        suggestions[name] = (
            round(percentile(values, WEAK_PERCENTILE), 2),
            round(percentile(values, 50), 2),
            round(percentile(values, ELITE_PERCENTILE), 2),
        )

    return suggestions


def read_nicknames(args):

    nicknames = list(args.nicknames)

    if args.file:
        lines = Path(args.file).read_text(encoding="utf-8").splitlines()
        nicknames += [line.strip() for line in lines if line.strip() and not line.startswith("#")]

    return nicknames


def main():

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("nicknames", nargs="*", help="FACEIT nicknames")
    parser.add_argument("--file", help="text file with one nickname per line")
    parser.add_argument("--matches", type=int, default=30, help="matches per player (max 100)")
    args = parser.parse_args()

    nicknames = read_nicknames(args)

    if len(nicknames) < 2:
        parser.error("give at least 2 players (50+ is much better)")

    load_dotenv()
    api_key = os.getenv("FACEIT_API_KEY")

    if not api_key:
        sys.exit("FACEIT_API_KEY is missing. Copy .env.example to .env and fill it in.")

    client = FaceitClient(api_key)

    header = f"{'player':<16} {'lvl':>3} {'score':>5}  " + " ".join(f"{name:>6}" for name in ANCHORS)
    print(header)
    print("-" * len(header))

    all_stats = []

    for nickname in nicknames:

        try:
            report = analyze_player(client, nickname, args.matches)
        except (AnalysisError, FaceitError) as error:
            print(f"{nickname:<16} skipped: {error}")
            continue

        all_stats.append(report.stats)

        values = " ".join(f"{report.stats[name]:6.2f}" for name in ANCHORS)
        print(f"{report.nickname:<16} {report.level!s:>3} {report.score:5.1f}  {values}")

    if len(all_stats) < 2:
        sys.exit("Not enough players were analysed.")

    print(f"\nSuggested ANCHORS from {len(all_stats)} players "
          f"(p{WEAK_PERCENTILE} / median / p{ELITE_PERCENTILE}):\n")
    print("ANCHORS = {")

    for name, (weak, average, elite) in suggest_anchors(all_stats).items():
        current = ANCHORS[name]
        print(f'    "{name}": ({weak}, {average}, {elite}),  # now {current}')

    print("}")


if __name__ == "__main__":
    main()
