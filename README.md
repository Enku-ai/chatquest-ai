# ChatQuest AI

ChatQuest AI is a fantasy dungeon adventure that a Twitch chat plays together. Every chapter ends
with three choices, viewers vote by typing `!1`, `!2` or `!3`, and when the timer runs out the winning
choice goes to an AI Dungeon Master that writes what happens next. No two streams end up telling the
same story.

I built it solo over a weekend for the Codex x TwitchCon Hackathon 2026.

Demo video: (link coming soon)

---

## What it does

- Reads votes live from Twitch chat, and a bot account posts each new chapter and the result back
  into chat.
- Counts one vote per viewer per round. If someone changes their mind, their new vote replaces the
  old one. Ties are broken at random, and votes are still accepted for a few seconds after the timer
  ends to make up for stream delay.
- Writes each chapter with the OpenAI API. The story reacts to what chat picked and keeps track of
  earlier chapters, so it stays connected instead of jumping around.
- Keeps going if the AI has a problem. It retries once, then falls back to a set of pre-written
  scenes, so the stream never stalls on a blank screen.
- Shows everything in an OBS overlay: the story types itself out, vote bars fill up as people vote,
  a countdown runs, the winner is highlighted, and side panels show the path chat has taken so far and
  who voted most recently.
- Gives the streamer a small control panel to pause, skip a vote, start a new adventure, or change
  the voting time.
- Refreshes the Twitch token automatically and reconnects if the connection drops, so it can run for
  a long stream without babysitting.
- Has a simulator mode with fake viewers, which made it possible to test everything without an
  audience.

---

## How it fits together

```
Twitch chat ──► Chat listener ──► Vote counter ──► Game engine ◄──► AI story (OpenAI API)
                                                        │              └─ fallback scenes
                                                        ▼
                                                  FastAPI server
                                          /api/state      /api/control/*
                                              │                  ▲
                                   OBS overlay (HTML/CSS/JS)   Streamlit control panel
```

The game engine runs inside a FastAPI server. The overlay polls `/api/state` twice a second and
redraws itself, and the Streamlit panel sends commands to `/api/control/*`. Keeping the game in one
place meant the overlay and the control panel could stay simple.

| Part | Built with |
|---|---|
| Game engine and API | Python, FastAPI, uvicorn, asyncio |
| Twitch chat | Twitch IRC over a secure WebSocket, OAuth token refresh |
| Story generation | OpenAI API with JSON output |
| Stream overlay | HTML, CSS and plain JavaScript, used as an OBS Browser Source |
| Control panel | Streamlit |

---

## Running it yourself

You will need Python 3.12 or newer, OBS Studio, a Twitch account and an OpenAI API key.

**Install**

```bash
git clone https://github.com/Enku-ai/chatquest-ai.git
cd chatquest-ai
python -m venv .venv
.venv\Scripts\activate        # on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

**Set up credentials**

1. Register an app at [dev.twitch.tv/console](https://dev.twitch.tv/console) with the category
   "Chat Bot" and the redirect URL `http://localhost:3000`. This gives you a Client ID and a Client
   Secret.
2. Generate a user token with the [Twitch CLI](https://github.com/twitchdev/twitch-cli):
   ```bash
   twitch configure
   twitch token -u -s "chat:read chat:edit"
   ```
3. Copy `.env.example` to `.env` and fill in every value: your Twitch app details and tokens, your
   channel name, your OpenAI key and the model name.

**Start the game**

```bash
# the game, connected to real Twitch chat
python -m app.main --seconds 30

# or try it with fake viewers first
python -m app.main --simulate --seconds 15

# in a second terminal, the control panel
streamlit run dashboard/control_panel.py
```

**Add the overlay to OBS**

Add a Browser source with the URL `http://127.0.0.1:8765/overlay/?bg` and a size of 1920 x 1080.
If you want to put the overlay on top of something else, leave off `?bg` and the background will be
transparent.

---

## How I used Codex

I wrote the core of the game myself, step by step: the chat connection, the voting rules, the AI
story and the server. Once that worked, I used the OpenAI Codex desktop app to build out and polish
the overlay. I reviewed every change before approving it, tested it in OBS, and went back to Codex
with follow-up prompts whenever something was off.

With Codex I added the "The Path So Far" timeline and the "Recent Voters" feed, the animations, and
the full-screen layout. Testing turned up two bugs, a voter showing up twice and the timeline cutting
off its last entry, and Codex fixed both. It also replaced some leftover `innerHTML` in the overlay on
its own, which made it safer against text coming from chat or the AI.

The full log, with each prompt, what Codex changed and my notes, is in
[`docs/codex-log.md`](docs/codex-log.md).

---

## Testing

I tested the voting rules in simulator mode, where fake viewers also send spam and invalid votes.
I checked the fallback by giving the game a wrong model name and confirming it kept running on the
pre-written scenes. Finally I went live on Twitch and had a real viewer vote from another computer.

---

## Safety

Viewers can only send numbers, so chat has no way to push the AI toward harmful content, and the AI
is told to keep the story family-friendly. Any text from chat or the AI is shown with `textContent`
rather than as HTML. Secrets are kept in `.env`, which is excluded from git.

---

## License

MIT