# How I used Codex

ChatQuest AI's core (Twitch chat connection, voting engine, AI story generation, overlay server)
was built step by step. I then used **OpenAI Codex (desktop app)** to extend and polish the
stream overlay, reviewing every change before approving it ("Ask for approval" mode) and testing
it live in OBS.

---

## 1. Adventure Trail panel

**Goal:** Fill the empty right side of the overlay with the path chat has chosen so far.

**Prompt given to Codex:**
> Add an "Adventure Trail" that shows the path chat has chosen so far.
> Backend: keep the last 6 winning choices in engine.state["trail"] ({chapter, choice, votes, total}),
> clear it on restart. Frontend: a second panel on the right side of the 1920x1080 canvas titled
> "The Path So Far", a vertical timeline with gold dots, newest first, new entries slide/fade in,
> hidden while empty. Match the existing dark fantasy style. Constraints: transparent background,
> textContent only for AI/chat text, don't break existing fields/routes/controls, no new libraries.

**What Codex did:**
- `app/game.py` — records each revealed winning choice with its chapter and vote counts,
  keeps the latest six, clears the trail when a new adventure starts.
- `overlay/index.html`, `overlay/overlay.js`, `overlay/style.css` — new "The Path So Far"
  panel with a gold dotted timeline, newest entries first, hidden while empty.
- Kept the security and OBS constraints: text added with `textContent`, background stays transparent.
- Change size: 4 files, +106 / -6 lines.

**My review / testing:**
- Reviewed the diff in Codex ("View changes") and with `git diff --stat`; only the expected 4 files changed, `.env` untouched.
- Tested in simulate mode in OBS: the "The Path So Far" panel stays hidden until the first vote ends, then adds one entry per chapter, newest first, and clears on "New adventure".
- Rating: **4.5/5** — met every requirement and constraint; half a point off because Codex did not run the app itself, so manual testing was needed.


---

## 2. Live voter feed

**Goal:** Show viewers' names on stream as they vote, so chat feels seen.

**Prompt given to Codex:**
> Keep the last 5 counted votes in engine.state["recent_votes"] ({user, choice}, newest first),
> cleared each voting round. Show them as pill-shaped tags under the trail panel
> ("goblin_queen → !2") that fade/slide in, without layout jumps. Same style and constraints.

**What Codex did:**
- `app/game.py` — stores the latest five accepted votes, newest first, reset each round.
- `overlay/index.html`, `overlay/overlay.js`, `overlay/style.css` — "Recent Voters" feed of pill tags
  beneath the Adventure Trail; new tags slide in, leaving tags fade out; fixed position so it
  doesn't jump when the trail is empty.
- On its own initiative, replaced the overlay's remaining `innerHTML` usage with DOM construction
  and `textContent`, applying the security constraint to older code too.
- Change size: 4 files, +110 / -13 lines.

**My review / testing:**
- (Тест хийсний дараа бичнэ)