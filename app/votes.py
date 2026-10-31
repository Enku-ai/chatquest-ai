"""Counts chat votes. Each viewer gets one vote per round; a new vote replaces the old one."""
import random
import re

# Accepts: "!1", "1", "!vote 1", "!VOTE 2"
VOTE_PATTERN = re.compile(r"^!?(?:vote\s*)?([1-9])$", re.IGNORECASE)


class VoteCounter:
    def __init__(self):
        self.num_choices = 0
        self.votes = {}  # username -> chosen number
        self.is_open = False

    def start_round(self, num_choices: int = 3):
        """Clear old votes and open voting for a new round."""
        self.num_choices = num_choices
        self.votes = {}
        self.is_open = True

    def close(self):
        self.is_open = False

    def handle_message(self, username: str, text: str) -> bool:
        """Record a vote if the message is a valid one. Returns True if it counted."""
        if not self.is_open:
            return False
        match = VOTE_PATTERN.match(text.strip())
        if not match:
            return False
        choice = int(match.group(1))
        if choice > self.num_choices:
            return False
        self.votes[username.lower()] = choice  # same user again = replaces old vote
        return True

    def tally(self) -> list[int]:
        """Vote counts per choice, e.g. [5, 2, 8]."""
        counts = [0] * self.num_choices
        for choice in self.votes.values():
            counts[choice - 1] += 1
        return counts

    def total(self) -> int:
        return len(self.votes)

    def winner(self) -> int:
        """Choice with the most votes. Ties (or zero votes) are decided randomly."""
        counts = self.tally()
        best = max(counts)
        leaders = [i + 1 for i, count in enumerate(counts) if count == best]
        return random.choice(leaders)