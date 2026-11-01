"""Connects to Twitch chat (IRC over secure WebSocket): reads messages, posts announcements,
and refreshes the access token automatically so it never expires mid-stream."""
import asyncio
from pathlib import Path

import httpx
import websockets
from dotenv import set_key

from app import config

TWITCH_IRC_URL = "wss://irc-ws.chat.twitch.tv:443"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
ENV_FILE = Path(__file__).parent.parent / ".env"

outgoing: asyncio.Queue = asyncio.Queue()  # messages waiting to be posted in chat


def say(text: str):
    """Queue a message for the bot to post in chat."""
    outgoing.put_nowait(text[:450])  # Twitch limit is 500 characters


async def refresh_access_token():
    """Get a fresh access token using the refresh token, and save it to .env."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(TOKEN_URL, data={
            "grant_type": "refresh_token",
            "refresh_token": config.TWITCH_REFRESH_TOKEN,
            "client_id": config.TWITCH_CLIENT_ID,
            "client_secret": config.TWITCH_CLIENT_SECRET,
        })
        response.raise_for_status()
        data = response.json()

    config.TWITCH_ACCESS_TOKEN = data["access_token"]
    config.TWITCH_REFRESH_TOKEN = data.get("refresh_token", config.TWITCH_REFRESH_TOKEN)
    set_key(ENV_FILE, "TWITCH_ACCESS_TOKEN", config.TWITCH_ACCESS_TOKEN, quote_mode="never")
    set_key(ENV_FILE, "TWITCH_REFRESH_TOKEN", config.TWITCH_REFRESH_TOKEN, quote_mode="never")
    print("Twitch token refreshed.")


def parse_chat_line(line: str):
    """Turn a raw Twitch line into (username, text), or None if it is not a chat message.

    Example raw line:
    :viewer123!viewer123@viewer123.tmi.twitch.tv PRIVMSG #mychannel :!2
    """
    if " PRIVMSG " not in line:
        return None
    if line.startswith("@"):  # skip optional tags section
        line = line.split(" ", 1)[1]
    prefix, rest = line.split(" PRIVMSG ", 1)
    username = prefix.lstrip(":").split("!", 1)[0]
    text = rest.split(" :", 1)[1] if " :" in rest else ""
    return username, text.strip()


async def _send_queued(ws):
    """Post queued messages one by one, slowly enough to respect Twitch rate limits."""
    while True:
        text = await outgoing.get()
        await ws.send(f"PRIVMSG #{config.TWITCH_CHANNEL} :{text}")
        await asyncio.sleep(1.5)


async def listen(on_message):
    """Stay connected to chat forever: refresh the token, connect, reconnect on any drop."""
    while True:
        try:
            await refresh_access_token()
        except Exception as error:
            print(f"Token refresh failed ({error}). Trying the saved token...")

        sender = None
        try:
            async with websockets.connect(TWITCH_IRC_URL) as ws:
                await ws.send(f"PASS oauth:{config.TWITCH_ACCESS_TOKEN}")
                await ws.send(f"NICK {config.TWITCH_BOT_USERNAME}")
                await ws.send(f"JOIN #{config.TWITCH_CHANNEL}")
                print(f"Connected to #{config.TWITCH_CHANNEL}. Waiting for chat...")
                sender = asyncio.create_task(_send_queued(ws))

                async for raw in ws:
                    for line in raw.split("\r\n"):
                        if not line:
                            continue
                        if line.startswith("PING"):
                            await ws.send("PONG :tmi.twitch.tv")
                        elif "Login authentication failed" in line:
                            raise ConnectionError("Twitch rejected the token")
                        else:
                            parsed = parse_chat_line(line)
                            if parsed:
                                await on_message(*parsed)
        except (websockets.ConnectionClosed, OSError) as error:
            print(f"Chat connection problem ({error}). Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        finally:
            if sender:
                sender.cancel()