"""Starts everything: the web server, the chat listener and the game engine."""
import argparse
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.game import GameEngine

OVERLAY_DIR = Path(__file__).parent.parent / "overlay"
settings = {"simulate": False, "seconds": 45, "port": 8765}
engine: GameEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts: launch chat + game in the background."""
    global engine
    engine = GameEngine(voting_seconds=settings["seconds"])

    if settings["simulate"]:
        from app.simulator import run_fake_viewers
        chat_task = asyncio.create_task(run_fake_viewers(engine.on_chat_message))
        print("Using FAKE viewers (simulate mode)")
    else:
        from app import twitch_chat
        engine.announce = twitch_chat.say
        chat_task = asyncio.create_task(twitch_chat.listen(engine.on_chat_message))

    game_task = asyncio.create_task(engine.run_forever())
    print(f"Overlay: http://127.0.0.1:{settings['port']}/overlay/")
    yield
    chat_task.cancel()
    game_task.cancel()


app = FastAPI(lifespan=lifespan)
app.mount("/overlay", StaticFiles(directory=OVERLAY_DIR, html=True), name="overlay")


@app.get("/api/state")
def get_state():
    """The overlay and control panel ask this every second."""
    return engine.state


@app.post("/api/control/pause")
def control_pause():
    engine.pause()
    return {"ok": True}


@app.post("/api/control/resume")
def control_resume():
    engine.resume()
    return {"ok": True}


@app.post("/api/control/skip")
def control_skip():
    engine.skip_vote()
    return {"ok": True}


@app.post("/api/control/restart")
def control_restart():
    engine.restart()
    return {"ok": True}


@app.post("/api/control/seconds")
def control_seconds(value: int):
    value = max(10, min(value, 300))  # keep it between 10 s and 5 min
    engine.set_voting_seconds(value)
    return {"ok": True, "seconds": value}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true", help="use fake viewers")
    parser.add_argument("--seconds", type=int, default=45, help="voting time per round")
    parser.add_argument("--port", type=int, default=8765, help="web server port")
    args = parser.parse_args()
    settings["simulate"] = args.simulate
    settings["seconds"] = args.seconds
    settings["port"] = args.port
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)