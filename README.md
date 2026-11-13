<p align="center">
  <img src="assets/logo.png" alt="FACEIT Mully Score" width="420">
</p>

<h1 align="center">FACEIT Mully Rating</h1>

<p align="center">
  A website that rates FACEIT CS2 players from 0 to 100,
  using more than K/D and ADR.
</p>

<p align="center">
  <a href="https://github.com/KeonMei/Mully-Rating-Faceit/actions/workflows/tests.yml"><img src="https://github.com/KeonMei/Mully-Rating-Faceit/actions/workflows/tests.yml/badge.svg" alt="tests"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license">
</p>

---

Type a FACEIT nickname and the site analyses the player's last 10–100
CS2 matches. It combines **combat** (ADR, K/D, K/R, MVPs),
**multikills**, **opening duels** and **clutches** into one
**Mully Rating**, where **50 is an average FACEIT player**.

## Contents

- [What the website shows](#-what-the-website-shows)
- [How the Mully Rating works](#-how-the-mully-rating-works)
- [Run it locally](#️-run-it-locally)
- [Deploy to Vercel](#-deploy-to-vercel)
- [Tests](#-tests)
- [Tuning the rating](#-tuning-the-rating)
- [Project structure](#-project-structure)
- [Under the hood](#️-under-the-hood)
- [Roadmap](#-roadmap)

---

## 🌐 What the website shows

Enter a nickname or a faceit.com profile link, pick 10, 30, 50 or 100
matches and get:

- **the player card**: avatar, country, level and ELO,
- **the Mully Rating** with its tier (S–D),
- **the breakdown**: combat, multikills, entry and clutch, each from 0
  to 100, with a mark at 50 for an average player,
- **stats** (ADR, K/D, kills per round, MVPs, opening duels, clutches,
  multikills) next to what an average player has,
- **the rating of every match** on an interactive chart,
- **the rating on each map** and how many games it is based on.

Every result has its own link (`/?player=nickname&matches=30`) to share
with friends. The page works on phones too.

<p align="center">
  <img src="assets/website-example.png" alt="The Mully Rating website" width="720">
</p>

*Screenshot made with sample data.*

---

## 🧠 How the Mully Rating works

```text
combat = 45% ADR + 40% K/D + 12% K/R + 3% MVP

Mully Rating = 100 × (80% combat + 10% multikills + 5% entry + 5% clutch)
```

1. **Stats are added up over all matches**: K/D is total kills / total
   deaths, ADR and K/R are weighted by rounds, so one extreme game does
   not dominate.
2. **Each stat is scaled from 0 to 1** between three anchors: weak → 0,
   average FACEIT player → 0.5, elite → 1. For example ADR 55 / 80 / 110,
   K/D 0.60 / 1.00 / 1.60.
3. **Clutches are compared with an average player** (who wins about
   40% of 1v1 and 8% of 1v3), so a won 1v3 counts much more than a 1v1.
4. **Small samples are pulled towards average**, so one lucky clutch
   does not swing the rating.

| Tier | Score | |
| ---- | ----- | --- |
| 🟣 **S** | 90–100 | Strong: elite in almost everything |
| 🔵 **A** | 75–89 | Great: clearly carries games |
| 🟢 **B** | 60–74 | Good: above average |
| 🟡 **C** | 45–59 | Average FACEIT player |
| 🔴 **D** | 0–44 | Weak: below average |

📖 Full explanation, a worked example and what changed from the first
version of the formula: **[docs/rating.md](docs/rating.md)**.

---

## ⚙️ Run it locally

You need **Python 3.11+** and a [FACEIT API key](https://developers.faceit.com)
(server-side key).

```bash
# 1. Clone
git clone https://github.com/KeonMei/Mully-Rating-Faceit.git
cd Mully-Rating-Faceit

# 2. Install
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env             # then put your FACEIT key into .env

# 4. Run
python scripts/serve_web.py      # → http://localhost:8000
```

The local server serves the pages from `public/` and the same
`/api/rating` code that runs on Vercel.

---

## 🚀 Deploy to Vercel

The website runs on [Vercel](https://vercel.com) for free (the Hobby
plan is for personal, non-commercial projects).

1. On vercel.com, sign in with GitHub and choose **Add New… → Project**.
2. Import the `Mully-Rating-Faceit` repository. Leave the settings as
   they are: `vercel.json` already selects the **Other** preset, the
   pages come from `public/` and there is no build command.
3. Open **Environment Variables** and add `FACEIT_API_KEY` with your
   FACEIT key.
4. Press **Deploy**. The site opens at `https://<project>.vercel.app`.

After that every push to `main` updates the site, and every pull request
gets its own preview link.

How it is set up:

- `api/rating.py` becomes the `/api/rating` function. Vercel installs
  only what `pyproject.toml` lists (just `requests`), so the function is
  small and starts fast.
- Answers are cached by Vercel's CDN for 10 minutes, so popular players
  are not downloaded from FACEIT again on every visit.
- `vercel.json` lets one analysis run for up to 60 seconds. That is
  plenty even for 100 matches: about 100 FACEIT requests, 10 at a time.

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The tests use a fake FACEIT API, so they need no keys and no internet.
They cover the rating formula, the FACEIT client, the website's API,
the local server and the files Vercel reads. They also run on GitHub
Actions for every push (Python 3.11 and 3.14).

---

## 🎯 Tuning the rating

The anchors that define "weak", "average" and "elite" are constants in
[`mully_rating/rating/formula.py`](mully_rating/rating/formula.py). To
fit them to real players, list nicknames in a file (one per line, 50+
players is best) and run:

```bash
python scripts/calibrate.py --file players.txt --matches 50
```

The script prints every player's stats and a ready-to-paste `ANCHORS`
table built from the 10th percentile, median and 95th percentile.

---

## 📦 Project structure

```text
Mully-Rating-Faceit/
├── public/                   # the website: index.html, style.css, app.js
├── api/
│   └── rating.py             # Vercel function → /api/rating
├── mully_rating/
│   ├── analyzer.py           # downloads matches → PlayerReport
│   ├── nickname.py           # nickname / profile link parsing
│   ├── faceit/               # everything that talks to FACEIT
│   │   ├── client.py         #   HTTP session, timeouts, retries
│   │   ├── players.py        #   profile and match history
│   │   └── matches.py        #   match details + cache
│   ├── rating/               # the math, no network
│   │   ├── formula.py        #   the Mully Rating formula
│   │   ├── tiers.py          #   S–D tiers and their names
│   │   └── maps.py           #   rating per map
│   └── web/
│       └── api.py            # JSON API for the website
├── scripts/
│   ├── serve_web.py          # runs the website locally
│   └── calibrate.py          # suggests rating anchors from real players
├── tests/                    # same layout as mully_rating/
├── docs/
│   └── rating.md             # how the rating works
├── assets/                   # logo and README images
├── requirements.txt          # for the local server and scripts
├── requirements-dev.txt      # + pytest
├── pyproject.toml            # website dependencies + pytest settings
├── vercel.json               # Vercel settings
└── .env.example
```

---

## 🛠️ Under the hood

- **Fast and polite to the API.** One keep-alive HTTP session, up to 10
  parallel requests, automatic retry with backoff on rate limits (429)
  and server errors, 10-second timeouts.
- **Caching.** Match details are cached in memory while the function is
  warm (up to 2000 matches, all 10 players each), and whole answers are
  cached by Vercel's CDN for 10 minutes.
- **Light website.** No frameworks and no build step; the chart is drawn
  in the browser, so the Vercel function only needs `requests`.
- **Shareable results.** The nickname and match count live in the page
  address, so a copied link opens the same result.
- **Clear errors.** Unknown player, no CS2 matches and FACEIT being down
  each get their own message.

Tech stack: Python, requests and pytest for the API; plain HTML, CSS
and JavaScript for the page; hosted on Vercel.

---

## 📈 Roadmap

- [ ] Player comparison (two players side by side)
- [ ] Playstyle detection (entry fragger, clutcher, support…)
- [ ] Tips based on the weakest part of the breakdown
- [ ] Persistent cache (SQLite / Redis) that survives restarts
- [x] Web interface (Vercel)

---

## ⚠️ Notes

- Do not commit your `.env` file (it is in `.gitignore`).
- The rating is an analytical tool, not an official FACEIT ranking.
- FACEIT matchmaking pairs players of similar ELO, so the rating shows
  how a player performs **against their own level**.

## 📄 License

MIT
