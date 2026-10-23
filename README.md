<p align="center">
  <img src="mully_score.png" alt="FACEIT Mully Score" width="420">
</p>

# FACEIT Mully Rating Bot

Telegram bot for analyzing FACEIT CS2 players using a custom **Mully Rating** system.

The project evaluates player performance beyond basic stats (K/D, ADR) by combining combat impact, clutch ability, entry success, and multikill contribution into a single score.

---

## 🚀 Features

### 📊 Player Analysis

* Calculates **Mully Rating (0–100)** over the last 10 / 30 / 50 / 100 matches
* Displays rank tier (S–D)
* Shows ELO, level, and country
* Accepts a nickname or a FACEIT profile link

---

### 📈 Match Trend

* Performance graph across recent matches with the average line
* Shows consistency and performance changes

---

### 🗺 Map Statistics

* Rating per map and number of games on it
* Tier-based visualization (S–D)
* Performance bars for quick comparison

---

### ⚡ Performance

* Handles several users at once (FACEIT requests run in worker threads)
* Parallel match requests over one shared, keep-alive HTTP session
* Automatic retry with backoff when FACEIT rate-limits (HTTP 429) or fails
* Match details are cached in memory; Trend and Maps reuse the last analysis
  instead of downloading everything again

---

## 🧠 Mully Rating System

The rating is based on multiple weighted components:

* **Combat** (ADR, K/D, K/R, MVP)
* **Entry impact**
* **Clutch success (1v1–1v5)**
* **Multikills (double → ace)**

Final score is normalized to **0–100** and adjusted with penalties for low performance.
The formula lives in [`src/score.py`](src/score.py).

| Tier | Score  |
| ---- | ------ |
| S    | 90–100 |
| A    | 75–89  |
| B    | 60–74  |
| C    | 45–59  |
| D    | 0–44   |

---

## 📦 Project Structure

```text
Mully-Rating-Faceit/
│
├── src/
│   ├── faceit.py        # FACEIT API client (session, timeouts, retries)
│   ├── player.py        # Player info & match history
│   ├── match.py         # Match details + cache
│   ├── analyzer.py      # Builds the player report
│   ├── score.py         # Rating formula, tiers, progress bar
│   ├── maps.py          # Per-map rating
│   └── trend.py         # Trend chart
│
├── tests/               # pytest tests (no network needed)
├── bot.py               # Telegram bot entry point
├── requirements.txt
├── requirements-dev.txt # + pytest
├── .env.example
└── README.md
```

---

## ⚙️ Setup

Requires **Python 3.11+**.

### 1. Clone repository

```bash
git clone https://github.com/KeonMei/Mully-Rating-Faceit.git
cd Mully-Rating-Faceit
```

---

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

### 3. Create `.env` file

Copy `.env.example` to `.env` and fill it in:

```env
FACEIT_API_KEY=your_faceit_api_key
TG_BOT_TOKEN=your_telegram_bot_token
```

* FACEIT API key (server-side key): <https://developers.faceit.com>
* Telegram bot token: [@BotFather](https://t.me/BotFather)

---

### 4. Run bot

```bash
python bot.py
```

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests use a fake FACEIT API, so they need no API key or internet.

---

## 🔐 Environment Variables

| Variable       | Description           |
| -------------- | --------------------- |
| FACEIT_API_KEY | FACEIT Data API key   |
| TG_BOT_TOKEN   | Telegram bot token    |

---

## ⚠️ Notes

* Do NOT commit your `.env` file (it is in `.gitignore`)
* API requests are optimized but still limited by FACEIT rate limits
* The cache lives in memory and is cleared when the bot restarts
* Designed for analytical purposes, not official ranking

---

## 🛠 Tech Stack

* Python
* python-telegram-bot
* requests
* matplotlib
* pytest

---

## 📈 Future Improvements

* Player comparison system
* Advanced playstyle detection
* Recommendations based on weaknesses
* Persistent cache (SQLite / Redis)
* Web interface

---

## 📄 License

MIT
