"""The game engine: AI writes a scene, chat votes, the winning choice shapes the next scene.
The overlay reads `engine.state` to show everything on stream."""
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
        self.state = {
            "status": "starting",  # starting -> voting -> reveal -> generating -> voting ...
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

    async def on_chat_message(self, username: str, text: str):
        """Called for every chat message (real or fake)."""
        if self.votes.handle_message(username, text):
            self.state["tally"] = self.votes.tally()
            self.state["total_votes"] = self.votes.total()
            print(f"   vote  {username:<16} {text:<8} tally={self.state['tally']}")

    async def run_forever(self):
        """Play chapter after chapter until the server stops."""
        scene = await self.story.start()
        while True:
            try:
                self._show_scene(scene)
                winner = await self._voting_round()
                chosen = scene["choices"][winner - 1]

                self.state["status"] = "reveal"
                self.state["winner"] = winner
                print(f"   WINNER: !{winner}  {chosen}")
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

    async def _voting_round(self) -> int:
        self.votes.start_round(len(self.state["choices"]))
        self.state["status"] = "voting"
        for remaining in range(self.voting_seconds, 0, -1):
            self.state["seconds_left"] = remaining
            await asyncio.sleep(1)
        self.state["seconds_left"] = 0
        await asyncio.sleep(GRACE_SECONDS)  # late votes still count
        self.votes.close()
        return self.votes.winner()