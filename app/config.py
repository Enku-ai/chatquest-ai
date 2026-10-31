"""Loads settings from the .env file."""
import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    """Return a setting from .env, or stop with a clear error if it is missing."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing {name} in .env file")
    return value


TWITCH_CLIENT_ID = _require("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = _require("TWITCH_CLIENT_SECRET")
TWITCH_ACCESS_TOKEN = _require("TWITCH_ACCESS_TOKEN").removeprefix("oauth:")
TWITCH_REFRESH_TOKEN = _require("TWITCH_REFRESH_TOKEN")
TWITCH_CHANNEL = _require("TWITCH_CHANNEL").lower().lstrip("#")
TWITCH_BOT_USERNAME = _require("TWITCH_BOT_USERNAME").lower()
OPENAI_API_KEY = _require("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip()