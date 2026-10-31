"""Runs the game: AI writes a scene, chat votes, the winning choice shapes the next scene."""
import argparse
import asyncio

from app.story_ai import Story
from app.votes import VoteCounter

GRACE_SECONDS = 3  # extra time for viewers watching with stream delay

votes = VoteCounter()


async def on_chat_message(username: str, text: str):
    """Called for every chat message (real or fake)."""
    if votes.handle_message(username, text):
        print(f"   vote  {username:<16} {text:<8} tally={votes.tally()}")


async def run_voting_round(choices: list[str], seconds: int) -> int:
    votes.start_round(len(choices))
    print("\n----------- VOTE NOW -----------")
    for number, choice in enumerate(choices, start=1):
        print(f"  !{number}  {choice}")

    for remaining in range(seconds, 0, -1):
        if remaining % 10 == 0 or remaining <= 5:
            print(f"   ... {remaining}s left  tally={votes.tally()}")
        await asyncio.sleep(1)

    print("   Time's up! Accepting late votes...")
    await asyncio.sleep(GRACE_SECONDS)
    votes.close()

    winner = votes.winner()
    print(f"   RESULT {votes.tally()} from {votes.total()} viewers")
    print(f"   WINNER: !{winner}  {choices[winner - 1]}")
    return winner


def show_scene(chapter: int, scene: dict):
    print(f"\n########## CHAPTER {chapter}  [{scene['source']}] ##########")
    print(scene["scene"])


async def main(simulate: bool, seconds: int, rounds: int):
    if simulate:
        from app.simulator import run_fake_viewers
        chat_task = asyncio.create_task(run_fake_viewers(on_chat_message))
    else:
        from app.twitch_chat import listen
        chat_task = asyncio.create_task(listen(on_chat_message))

    story = Story()
    print("Writing chapter 1...")
    scene = await story.start()

    for _ in range(rounds):
        show_scene(story.chapter, scene)
        winner = await run_voting_round(scene["choices"], seconds)
        chosen = scene["choices"][winner - 1]
        print(f"   Writing chapter {story.chapter + 1}...")
        scene = await story.continue_with(chosen)

    show_scene(story.chapter, scene)
    chat_task.cancel()
    print("\nTest finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true", help="use fake viewers")
    parser.add_argument("--seconds", type=int, default=45, help="voting time per round")
    parser.add_argument("--rounds", type=int, default=3, help="how many votes before stopping")
    args = parser.parse_args()
    asyncio.run(main(args.simulate, args.seconds, args.rounds))