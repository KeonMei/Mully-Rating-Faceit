"""Settings read from environment variables (or the .env file)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    faceit_api_key: str
    bot_token: str


def load_settings():
    """Read settings; stop with a clear message if something is missing."""

    load_dotenv()

    faceit_api_key = os.getenv("FACEIT_API_KEY")
    bot_token = os.getenv("TG_BOT_TOKEN")

    missing = [
        name for name, value in (("FACEIT_API_KEY", faceit_api_key), ("TG_BOT_TOKEN", bot_token))
        if not value
    ]

    if missing:
        raise SystemExit(
            f"Missing {', '.join(missing)}. Copy .env.example to .env and fill it in."
        )

    return Settings(faceit_api_key=faceit_api_key, bot_token=bot_token)
