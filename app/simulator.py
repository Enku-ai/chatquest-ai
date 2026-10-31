"""Fake viewers that send random chat messages, for testing without a real audience."""
import asyncio
import random

FAKE_NAMES = [
    "dragonslayer99", "pixel_wizard", "goblin_queen", "noob_knight",
    "torchbearer", "mimic_chest", "elfarcher_7", "darkmage_x",
    "potionseller", "lootgoblin", "bard_of_chat", "skeleton_king",
]

# Mostly votes, plus noise and invalid votes to test the filter
FAKE_MESSAGES = ["!1", "!2", "!3", "!2", "3", "!vote 1", "lol", "pog", "!4", "go left!!"]


async def run_fake_viewers(on_message, min_delay: float = 0.3, max_delay: float = 1.5):
    """Send a random message from a random fake viewer every so often, forever."""
    while True:
        await asyncio.sleep(random.uniform(min_delay, max_delay))
        await on_message(random.choice(FAKE_NAMES), random.choice(FAKE_MESSAGES))