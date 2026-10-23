# How the Mully Rating works

The Mully Rating turns a player's recent FACEIT CS2 matches into one
number from **0 to 100**. **50 is an average FACEIT player.**

The code is in [`mully_rating/rating/formula.py`](../mully_rating/rating/formula.py).
Every number mentioned here is a named constant at the top of that file.

---

## 1. Add up the matches

The rating is computed from totals over all analysed matches, not from
averages of per-match numbers:

| Stat | How it is computed |
| ---- | ------------------ |
| ADR | total damage / total rounds |
| K/D | total kills / total deaths |
| K/R | total kills / total rounds |
| MVP | MVP stars per match |
| Entry | opening duels won / opening duels taken |
| Clutch | clutches won / clutches an average player would win |
| Multikills | multikill points per round |

Why totals: with per-match averages one 30–10 game (K/D 3.0) and one
10–20 game (K/D 0.5) average to K/D 1.75, while the real K/D over the
two games is 40 / 30 = **1.33**. A 13–2 stomp would also count as much
as a 16–14 overtime game.

The same code rates a single match (the trend chart), all matches on
one map (the map table) and all analysed matches (the main rating).

Because of that, the main rating is usually not the plain average of
the trend chart: a short 13–2 game weighs less than a 16–14 one, and a
single match is capped at 0 and 100 while the totals are not.

### Clutches

FACEIT reports how many 1v1 … 1v5 situations a player was in and how
many they won. Winning a 1v4 is much rarer than winning a 1v1, so each
situation is compared with how often an average player wins it:

| Situation | Average win rate |
| --------- | ---------------- |
| 1v1 | 40% |
| 1v2 | 20% |
| 1v3 | 8% |
| 1v4 | 3% |
| 1v5 | 1% |

`clutch = clutches won / expected clutch wins`, so **1.0 is average**
and 2.0 means twice as many clutches as expected.

1v1 is below 50% on purpose. A player who turns a 1v2 into a 1v1 is
still counted as being in a 1v2. The 1v1 is recorded for the opponent
who was left alone, usually in the worse position. Public FACEIT
profiles show most players winning about 37–42% of 1v1 and 17–25% of
1v2 clutches.

### Multikills

Every round with 2, 3, 4 or 5 kills gives points:

| Round | Points |
| ----- | ------ |
| 2 kills | 1 |
| 3 kills | 2 |
| 4 kills | 4 |
| ace | 6 |

`multikills = points / rounds`.

### Small samples

One match has only a few clutches and opening duels, so they are
pulled towards average:

- **clutch:** one imaginary clutch win at the average rate is added
  (`CLUTCH_PRIOR_WINS`),
- **entry:** four imaginary opening duels at 50% are added
  (`ENTRY_PRIOR_DUELS`).

Over 30 matches this changes almost nothing. In a single match it stops
one won 1v1 from looking like a superhuman clutch rate.

---

## 2. Scale every stat to 0–1

Each stat has three anchors in `ANCHORS`:

- **weak** → 0
- **average** → 0.5
- **elite** → 1

Between the anchors the scale is a straight line. Outside them it is
capped at 0 or 1.

| Stat | Weak (0) | Average (0.5) | Elite (1) | Why "average" is there |
| ---- | -------- | ------------- | --------- | ---------------------- |
| ADR | 55 | 80 | 110 | ~0.7 kills per player per round × 100 damage, plus ~10 damage on survivors |
| K/D | 0.60 | 1.00 | 1.60 | every kill is someone's death |
| K/R | 0.45 | 0.70 | 0.95 | about 7 of 10 players die in a typical round |
| MVP | 1.0 | 2.1 | 3.5 | one MVP per round, ~21 rounds, 10 players |
| Entry | 0.30 | 0.50 | 0.70 | every opening duel has one winner and one loser |
| Clutch | 0.0 | 1.0 | 2.0 | compared with the average rates above |
| Multikills | 0.09 | 0.21 | 0.40 | kill distribution of a ~0.7 K/R player |

The "average" values follow from how CS2 works and hold for any
group of players. The "weak" and "elite" values set how spread out the
ratings are. They are estimates and are the first thing to tune with
real data (see [Recalibrating](#recalibrating)).

---

## 3. Combine with weights

```text
combat = 45% ADR + 40% K/D + 12% K/R + 3% MVP

score  = 100 × (80% combat + 10% multikills + 5% entry + 5% clutch)
```

These are the weights of the original formula. Combat decides most of
the rating, and the other parts move it a few points.

The bot shows the four parts on the player card ("Breakdown"), each
on the same 0–100 scale, so a player can see where their score comes
from.

### Worked example

A good player: ADR 88, K/D 1.15, K/R 0.77, MVP 2.5, entry 54%,
clutch 1.15, multikills 0.26.

| Stat | Value | Scaled |
| ---- | ----- | ------ |
| ADR | 88 | 0.633 |
| K/D | 1.15 | 0.625 |
| K/R | 0.77 | 0.640 |
| MVP | 2.5 | 0.643 |
| Entry | 0.54 | 0.600 |
| Clutch | 1.15 | 0.575 |
| Multikills | 0.26 | 0.632 |

```text
combat = 0.45 × 0.633 + 0.40 × 0.625 + 0.12 × 0.640 + 0.03 × 0.643 = 0.631
score  = 100 × (0.80 × 0.631 + 0.10 × 0.632 + 0.05 × 0.600 + 0.05 × 0.575)
       = 62.7  →  B (Good)
```

---

## 4. Tiers

| Tier | Score | Meaning |
| ---- | ----- | ------- |
| 🟣 S (Strong) | 90–100 | elite: close to the top anchors in everything |
| 🔵 A (Great) | 75–89 | clearly carries games |
| 🟢 B (Good) | 60–74 | above average |
| 🟡 C (Average) | 45–59 | around a typical FACEIT player |
| 🔴 D (Weak) | 0–44 | below average |

Reference stat lines (these are also tests in
`tests/rating/test_formula.py`):

| Player | ADR | K/D | K/R | Entry | Clutch | Multi | Score | Old formula* |
| ------ | --- | --- | --- | ----- | ------ | ----- | ----- | ----------- |
| Weak | 62 | 0.75 | 0.55 | 40% | 0.70 | 0.13 | **18 D** | 10 D |
| Below average | 72 | 0.90 | 0.63 | 46% | 0.90 | 0.17 | **36 D** | 25 D |
| Average | 80 | 1.00 | 0.70 | 50% | 1.00 | 0.21 | **50 C** | 37 D |
| Good | 88 | 1.15 | 0.77 | 54% | 1.15 | 0.26 | **63 B** | 47 C |
| Great | 97 | 1.35 | 0.84 | 60% | 1.40 | 0.32 | **78 A** | 62 B |
| Elite | 107 | 1.55 | 0.93 | 67% | 1.80 | 0.38 | **95 S** | 83 A |

\* The old formula needs a win rate for every clutch type; for this table
they were taken as the average rates above times the clutch value, so the
old scores are approximate.

---

## What changed from the original formula

| Original | Now | Why |
| -------- | --- | --- |
| Each stat divided by a maximum and raised to a power of 2.6–3.6 | Linear between weak / average / elite anchors | The powers pushed normal values to the bottom: an average player scored 37, "D (Weak)" |
| Multikill score × 20, capped at 1 | Points per round scaled between anchors | The cap was hit at ~2 double kills per match, so almost everyone got the full 10 points |
| Clutch win rate per situation vs. 100%, 0 if never in that situation | Clutch wins vs. wins an average player would get | Never being in a 1v5 is not a weakness, and 100% in 1v5 is not a realistic target |
| Mean of per-match K/D, ADR, K/R | Totals; ADR and K/R weighted by rounds | One extreme match no longer dominates; long games count more than short ones |
| Entry: mean of per-match success rates | Opening duels won / taken, smoothed | A match with no opening duels no longer counts as 0% |
| Extra penalties for K/D < 1 and ADR < 80 | Removed | They counted the same stats twice; below-average values already score below 0.5 |
| Score rounded to 0.01 | Rounded to 0.1 | Hundredths are noise |

---

## Recalibrating

The weak and elite anchors were set from how the game works and from
public tracker numbers, not from a large FACEIT dataset (the API could
not be reached while tuning). To fit them to real players:

```bash
python scripts/calibrate.py --file players.txt --matches 50
```

`players.txt` has one FACEIT nickname per line. Use 50 or more players
from the levels your users play at. The script analyses each player and
prints the 10th percentile, median and 95th percentile of every stat as
a ready-to-paste `ANCHORS` table:

```text
Suggested ANCHORS from N players (p10 / median / p95):

ANCHORS = {
    "adr": (<p10>, <median>, <p95>),  # now (55.0, 80.0, 110.0)
    "kd": (<p10>, <median>, <p95>),  # now (0.6, 1.0, 1.6)
    ...
}
```

After changing `ANCHORS`, run `python -m pytest`.
`tests/rating/test_formula.py` shows whether the reference players
still land in the expected tiers.

## Limitations

- FACEIT matchmaking puts players against opponents of similar ELO,
  so stats measure how a player performs **against their own level**.
  A level 4 and a level 10 player with the same stats get the same
  rating.
- Utility usage, trading, positioning and economy are not in the
  FACEIT stats the bot reads, so the rating can not see them.
- 10 matches are a small sample; 30+ give a much more stable rating.
