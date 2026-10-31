"""Connects to Twitch chat (IRC over secure WebSocket) and passes on each message."""
import asyncio

import websockets

from app import config

TWITCH_IRC_URL = "wss://irc-ws.chat.twitch.tv:443"


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


async def listen(on_message):
    """Stay connected to chat forever, reconnecting if the connection drops."""
    while True:
        try:
            async with websockets.connect(TWITCH_IRC_URL) as ws:
                await ws.send(f"PASS oauth:{config.TWITCH_ACCESS_TOKEN}")
                await ws.send(f"NICK {config.TWITCH_BOT_USERNAME}")
                await ws.send(f"JOIN #{config.TWITCH_CHANNEL}")
                print(f"Connected to #{config.TWITCH_CHANNEL}. Waiting for chat...")

                async for raw in ws:
                    for line in raw.split("\r\n"):
                        if not line:
                            continue
                        if line.startswith("PING"):
                            await ws.send("PONG :tmi.twitch.tv")
                        elif "Login authentication failed" in line:
                            raise RuntimeError(
                                "Twitch rejected the token. Generate a new one with Twitch CLI."
                            )
                        else:
                            parsed = parse_chat_line(line)
                            if parsed:
                                await on_message(*parsed)
        except websockets.ConnectionClosed:
            print("Connection lost. Reconnecting in 3 seconds...")
            await asyncio.sleep(3)


async def print_message(username: str, text: str):
    print(f"{username}: {text}")


if __name__ == "__main__":
    asyncio.run(listen(print_message))