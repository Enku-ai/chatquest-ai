"""The game engine: AI writes a scene, chat votes, the winning choice shapes the next scene.
The overlay reads `engine.state`; the control panel calls pause/skip/restart."""
import asyncio
import traceback

from app.story_ai import Story
from app.votes import VoteCounter

GRACE_SECONDS = 3   # extra time for viewers watching with stream delay
REVEAL_SECONDS = 6  # how long the winning choice is shown before the next chapter


class GameEngine:
    def __init__(self, voting_seconds: int = 45):
        self.voting_seconds = voting_seconds
        self.votes = VoteCounter()
        self.story = Story()
        self.paused = False
        self._skip_vote = False
        self._restart = False
        self.announce = lambda text: None  # replaced with twitch_chat.say in live mode
        self.state = {
            "status": "starting",  # starting -> voting -> reveal -> generating -> voting ...
            "paused": False,
            "chapter": 0,
            "scene": "",
            "choices": [],
            "source": "",
            "tally": [],
            "total_votes": 0,
            "seconds_left": 0,
            "voting_seconds": voting_seconds,
            "winner": None,
        }

    # ---------- controls (called from the control panel) ----------

    def pause(self):
        self.paused = True
        self.state["paused"] = True

    def resume(self):
        self.paused = False
        self.state["paused"] = False

    def skip_vote(self):
        """End the current vote right now."""
        self._skip_vote = True

    def restart(self):
        """Start a brand-new adventure after the current step."""
        self._restart = True
        self._skip_vote = True
        self.resume()

    def set_voting_seconds(self, seconds: int):
        self.voting_seconds = seconds
        self.state["voting_seconds"] = seconds

    # ---------- chat ----------

    async def on_chat_message(self, username: str, text: str):
        """Called for every chat message (real or fake)."""
        if self.votes.handle_message(username, text):
            self.state["tally"] = self.votes.tally()
            self.state["total_votes"] = self.votes.total()
            print(f"   vote  {username:<16} {text:<8} tally={self.state['tally']}")

    # ---------- main loop ----------

    async def run_forever(self):
        """Play chapter after chapter until the server stops."""
        scene = await self.story.start()
        while True:
            try:
                if self._restart:
                    self._restart = False
                    self.state["status"] = "generating"
                    print("\n*** NEW ADVENTURE ***")
                    self.announce("🔄 A brand-new adventure begins!")
                    scene = await self.story.start()

                self._show_scene(scene)
                winner = await self._voting_round()
                if self._restart:
                    continue  # skip the reveal, go straight to the new adventure

                chosen = scene["choices"][winner - 1]
                self.state["status"] = "reveal"
                self.state["winner"] = winner
                print(f"   WINNER: !{winner}  {chosen}")
                votes_for_winner = self.votes.tally()[winner - 1]
                self.announce(
                    f"⚔️ Chat chose !{winner}: {chosen} "
                    f"({votes_for_winner}/{self.votes.total()} votes)"
                )
                await asyncio.sleep(REVEAL_SECONDS)

                self.state["status"] = "generating"
                scene = await self.story.continue_with(chosen)
            except Exception:
                traceback.print_exc()  # never let one error kill the live game
                await asyncio.sleep(3)

    def _show_scene(self, scene: dict):
        self.state.update(
            chapter=self.story.chapter,
            scene=scene["scene"],
            choices=scene["choices"],
            source=scene["source"],
            winner=None,
            tally=[0] * len(scene["choices"]),
            total_votes=0,
        )
        print(f"\n### CHAPTER {self.story.chapter} [{scene['source']}]\n{scene['scene']}")
        options = " | ".join(f"!{i} {c}" for i, c in enumerate(scene["choices"], start=1))
        self.announce(f"📜 Chapter {self.story.chapter} — vote now! {options}")

    async def _voting_round(self) -> int:
        self.votes.start_round(len(self.state["choices"]))
        self.state["status"] = "voting"
        self._skip_vote = False

        remaining = self.voting_seconds
        while remaining > 0 and not self._skip_vote:
            self.state["seconds_left"] = remaining
            await asyncio.sleep(1)
            if not self.paused:
                remaining -= 1  # time only runs while not paused
        self.state["seconds_left"] = 0

        if not self._skip_vote:
            await asyncio.sleep(GRACE_SECONDS)  # late votes still count
        self.votes.close()
        return self.votes.winner()