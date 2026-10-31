"""Writes the next story scene and three choices using the OpenAI API."""
import json
import random
from pathlib import Path

from openai import AsyncOpenAI

from app import config

HISTORY_LENGTH = 6  # how many past chapters the AI remembers
FALLBACK_FILE = Path(__file__).parent / "fallback_story.json"

SYSTEM_PROMPT = """You are the narrator of ChatQuest, a fantasy dungeon adventure played live on Twitch.
Twitch chat controls the adventuring party by voting on what to do next.

Rules:
- Family-friendly: no gore, no sexual content, no real people.
- Each scene is 2-3 short sentences, at most 60 words, vivid and fun to read aloud on stream.
- React directly to the action chat chose. Choices have real consequences: danger, treasure, allies, twists.
- Keep the story connected to earlier chapters.
- Then offer exactly 3 different choices, each at most 6 words, starting with a verb:
  one cautious, one bold, and one weird or funny.
- Reply ONLY with JSON in this exact shape:
  {"scene": "...", "choices": ["...", "...", "..."]}"""

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY, timeout=20)


class Story:
    def __init__(self):
        self.chapter = 0
        self.history = []  # list of {"scene": str, "chosen": str}
        self.fallbacks = []

    async def start(self) -> dict:
        """Begin a new adventure and return chapter 1."""
        self.chapter = 1
        self.history = []
        prompt = (
            "Begin a brand-new adventure: the party stands at the entrance "
            "of a mysterious dungeon. Write chapter 1."
        )
        return await self._generate(prompt)

    async def continue_with(self, chosen: str) -> dict:
        """Remember chat's choice and return the next chapter."""
        self.history[-1]["chosen"] = chosen
        self.chapter += 1
        story_so_far = "\n".join(
            f"- {past['scene']} (Chat chose: {past['chosen']})"
            for past in self.history[-HISTORY_LENGTH:]
        )
        prompt = (
            f"Story so far:\n{story_so_far}\n\n"
            f"Chat just chose: {chosen}\n"
            f"Write chapter {self.chapter}."
        )
        return await self._generate(prompt)

    async def _generate(self, prompt: str) -> dict:
        """Ask the AI (with one retry). If both attempts fail, use a fallback scene."""
        scene = None
        for attempt in range(1, 3):
            try:
                response = await client.chat.completions.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                data = json.loads(response.choices[0].message.content)
                scene = self._validate(data)
                scene["source"] = "ai"
                break
            except Exception as error:
                print(f"   [AI] attempt {attempt} failed: {error}")

        if scene is None:
            scene = self._fallback()

        self.history.append({"scene": scene["scene"], "chosen": ""})
        return scene

    @staticmethod
    def _validate(data: dict) -> dict:
        """Make sure the AI reply has a scene and exactly 3 short choices."""
        scene = str(data.get("scene", "")).strip()
        choices = data.get("choices", [])
        if not scene or not isinstance(choices, list) or len(choices) != 3:
            raise ValueError(f"Bad AI reply shape: {data}")
        choices = [str(choice).strip()[:60] for choice in choices]
        if not all(choices):
            raise ValueError(f"Empty choice in AI reply: {data}")
        return {"scene": scene, "choices": choices}

    def _fallback(self) -> dict:
        """Take the next pre-written scene, reshuffling when we run out."""
        if not self.fallbacks:
            self.fallbacks = json.loads(FALLBACK_FILE.read_text(encoding="utf-8"))
            random.shuffle(self.fallbacks)
        print("   [AI] using a fallback scene")
        scene = dict(self.fallbacks.pop())
        scene["source"] = "fallback"
        return scene