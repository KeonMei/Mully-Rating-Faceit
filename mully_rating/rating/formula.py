"""The Mully Rating formula: match stats -> score from 0 to 100.

How it works (the full explanation is in docs/rating.md):

1. Raw stats are summed over all analysed matches (MatchTotals), so
   K/D is total kills / total deaths and ADR is weighted by rounds.
2. Every stat is scaled to 0..1 with three anchor values from ANCHORS:
   weak -> 0, average FACEIT player -> 0.5, elite -> 1. Between the
   anchors the scale is linear; outside them it is capped.
3. The scaled stats are combined with WEIGHTS and multiplied by 100.

A player who is average in everything gets exactly 50.
"""

from dataclasses import dataclass, fields

# For every stat: (weak, average, elite) -> scaled to 0, 0.5 and 1.
ANCHORS = {
    "adr": (55.0, 80.0, 110.0),      # damage per round
    "kd": (0.60, 1.00, 1.60),        # kills / deaths
    "kr": (0.45, 0.70, 0.95),        # kills per round
    "mvp": (1.0, 2.1, 3.5),          # MVP stars per match
    "entry": (0.30, 0.50, 0.70),     # share of opening duels won
    "clutch": (0.0, 1.0, 2.0),       # clutches won / clutches an average player wins
    "multi": (0.09, 0.21, 0.40),     # multikill points per round (see MULTIKILL_POINTS)
}

# How much each part of combat matters (sums to 1).
COMBAT_WEIGHTS = {
    "adr": 0.45,
    "kd": 0.40,
    "kr": 0.12,
    "mvp": 0.03,
}

# How much each part matters in the final score (sums to 1).
WEIGHTS = {
    "combat": 0.80,
    "multi": 0.10,
    "entry": 0.05,
    "clutch": 0.05,
}

# Share of clutches an average player wins. 1v1 is below 50% because
# a player who turns a 1v2 into a 1v1 is counted as being in a 1v2;
# the 1v1 is recorded for the opponent who was left alone.
EXPECTED_CLUTCH_WIN_RATE = {
    "1v1": 0.40,
    "1v2": 0.20,
    "1v3": 0.08,
    "1v4": 0.03,
    "1v5": 0.01,
}

# Rounds with 2/3/4/5 kills; harder multikills give more points.
MULTIKILL_POINTS = {
    "double": 1,
    "triple": 2,
    "quadra": 4,
    "ace": 6,
}

# Small samples are pulled towards average, so one lucky clutch or a
# single opening duel can not swing the rating much. The numbers are
# "imaginary" average results added to the real ones.
CLUTCH_PRIOR_WINS = 1.0
ENTRY_PRIOR_DUELS = 4

# Used when FACEIT does not report how many rounds a match had.
DEFAULT_ROUNDS = 21


def clamp(value, min_value=0.0, max_value=1.0):
    return max(min_value, min(value, max_value))


def scale(value, weak, average, elite):
    """0 at `weak`, 0.5 at `average`, 1 at `elite`, linear in between."""

    if value <= average:
        if average == weak:
            return 0.5
        return clamp(0.5 * (value - weak) / (average - weak))

    if elite == average:
        return 0.5

    return clamp(0.5 + 0.5 * (value - average) / (elite - average))


@dataclass
class MatchTotals:
    """Raw stats summed over one or more matches.

    Build one per match with from_match() and add them up with `+`.
    """

    matches: int = 0
    rounds: float = 0
    damage: float = 0              # ADR * rounds
    kills_by_kr: float = 0         # K/R * rounds
    kills: float = 0
    deaths: float = 0
    kd_sum: float = 0              # fallback when kills/deaths are missing
    mvps: float = 0
    entry_duels: int = 0
    entry_wins: int = 0
    entry_count_matches: int = 0   # matches where FACEIT gave duel counts
    entry_rate_sum: float = 0      # fallback when duel counts are missing
    clutch_wins: int = 0
    clutch_expected_wins: float = 0
    multikill_points: float = 0

    @classmethod
    def from_match(cls, match, advanced):
        """`match` from players.get_matches(), `advanced` from matches.analyze_match()."""

        rounds = advanced["rounds"] or DEFAULT_ROUNDS

        totals = cls(
            matches=1,
            rounds=rounds,
            damage=match["ADR"] * rounds,
            kills_by_kr=match["KR"] * rounds,
            kills=match.get("kills", 0),
            deaths=match.get("deaths", 0),
            kd_sum=match["KD"],
            mvps=match["MVPs"],
            clutch_wins=sum(c.wins for c in advanced["clutches"].values()),
            clutch_expected_wins=sum(
                c.attempts * EXPECTED_CLUTCH_WIN_RATE[kind]
                for kind, c in advanced["clutches"].items()
            ),
            multikill_points=sum(
                advanced[kind] * points for kind, points in MULTIKILL_POINTS.items()
            ),
        )

        entry = advanced.get("entry")

        if entry is not None:
            totals.entry_duels = entry.attempts
            totals.entry_wins = entry.wins
            totals.entry_count_matches = 1
        else:
            totals.entry_rate_sum = advanced["entry_success"]

        return totals

    def __add__(self, other):
        return MatchTotals(**{
            f.name: getattr(self, f.name) + getattr(other, f.name)
            for f in fields(self)
        })

    def stats(self):
        """Per-player stats the formula uses (see ANCHORS)."""

        if not self.matches:
            return {name: anchors[1] for name, anchors in ANCHORS.items()}

        rounds = self.rounds or DEFAULT_ROUNDS * self.matches

        if self.kills or self.deaths:
            kd = self.kills / max(self.deaths, 1)
        else:
            kd = self.kd_sum / self.matches

        average_entry = ANCHORS["entry"][1]

        if self.entry_count_matches:
            entry = (
                (self.entry_wins + ENTRY_PRIOR_DUELS * average_entry)
                / (self.entry_duels + ENTRY_PRIOR_DUELS)
            )
        else:
            entry = self.entry_rate_sum / self.matches

        clutch = (
            (self.clutch_wins + CLUTCH_PRIOR_WINS)
            / (self.clutch_expected_wins + CLUTCH_PRIOR_WINS)
        )

        return {
            "adr": self.damage / rounds,
            "kd": kd,
            "kr": self.kills_by_kr / rounds,
            "mvp": self.mvps / self.matches,
            "entry": entry,
            "clutch": clutch,
            "multi": self.multikill_points / rounds,
        }


@dataclass
class Rating:
    score: float          # Mully Rating, 0..100
    components: dict      # combat / multi / entry / clutch, each 0..100
    stats: dict           # raw stats the score was computed from


def rate(totals):
    """Mully Rating of a MatchTotals (one match or many added together)."""

    stats = totals.stats()

    scaled = {name: scale(stats[name], *anchors) for name, anchors in ANCHORS.items()}

    parts = {
        "combat": sum(weight * scaled[name] for name, weight in COMBAT_WEIGHTS.items()),
        "multi": scaled["multi"],
        "entry": scaled["entry"],
        "clutch": scaled["clutch"],
    }

    score = 100 * sum(WEIGHTS[name] * value for name, value in parts.items())

    return Rating(
        score=round(score, 1),
        components={name: round(100 * value) for name, value in parts.items()},
        stats=stats,
    )
