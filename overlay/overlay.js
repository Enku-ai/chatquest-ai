// Asks the game for its state twice a second and updates the screen.
const POLL_MS = 500;
const TYPE_MS = 22; // typewriter speed (ms per letter)

const el = (id) => document.getElementById(id);
let shownScene = "";
let typingTimer = null;
const trailNodes = new Map();
let voterItems = [];

if (new URLSearchParams(location.search).has("preview")) {
  document.body.classList.add("preview");
}

function typeScene(text) {
  clearInterval(typingTimer);
  let i = 0;
  el("scene").textContent = "";
  typingTimer = setInterval(() => {
    i += 1;
    el("scene").textContent = text.slice(0, i);
    if (i >= text.length) clearInterval(typingTimer);
  }, TYPE_MS);
}

function replayAnimation(node, className) {
  node.classList.remove(className);
  void node.offsetWidth;
  node.classList.add(className);
}

function buildChoices(choices) {
  const list = el("choices");
  list.replaceChildren();
  choices.forEach((choice, i) => {
    const li = document.createElement("li");
    li.className = "choice";
    const bar = document.createElement("div");
    bar.className = "choice-bar";
    const key = document.createElement("span");
    key.className = "choice-key";
    key.textContent = `!${i + 1}`;
    const text = document.createElement("span");
    text.className = "choice-text";
    text.textContent = choice;
    const count = document.createElement("span");
    count.className = "choice-count";
    count.textContent = "0";
    li.append(bar, key, text, count);
    list.appendChild(li);
  });
}

function updateChoices(state) {
  const total = state.total_votes || 0;
  const revealing = state.status === "reveal";
  el("choices").querySelectorAll(".choice").forEach((li, i) => {
    const count = state.tally[i] || 0;
    li.querySelector(".choice-bar").style.width = (total ? (count / total) * 100 : 0) + "%";
    li.querySelector(".choice-count").textContent = count;
    li.classList.toggle("winner", revealing && state.winner === i + 1);
    li.classList.toggle("loser", revealing && state.winner !== i + 1);
  });
}

function updateTrail(trail) {
  const panel = el("trail-panel");
  const list = el("trail-list");
  const entries = Array.isArray(trail) ? trail.slice(-6).reverse() : [];
  panel.classList.toggle("hidden", entries.length === 0);
  panel.setAttribute("aria-hidden", entries.length === 0 ? "true" : "false");

  const activeKeys = new Set(entries.map((entry) => JSON.stringify([
    entry.chapter, entry.choice, entry.votes, entry.total,
  ])));
  for (const [key, node] of trailNodes) {
    if (!activeKeys.has(key)) {
      node.remove();
      trailNodes.delete(key);
    }
  }

  entries.forEach((entry) => {
    const key = JSON.stringify([entry.chapter, entry.choice, entry.votes, entry.total]);
    let item = trailNodes.get(key);
    if (!item) {
      item = document.createElement("li");
      item.className = "trail-entry new";
      const dot = document.createElement("span");
      dot.className = "trail-dot";
      dot.setAttribute("aria-hidden", "true");
      const copy = document.createElement("span");
      copy.className = "trail-copy";
      copy.textContent = `Ch. ${entry.chapter} — ${entry.choice} (${entry.votes}/${entry.total})`;
      item.append(dot, copy);
      trailNodes.set(key, item);
    }
    list.appendChild(item);
  });
}

function updateRecentVotes(recentVotes) {
  const list = el("voter-list");
  const seenUsers = new Set();
  const entries = (Array.isArray(recentVotes) ? recentVotes : []).filter((entry) => {
    const userKey = String(entry.user).toLowerCase();
    if (seenUsers.has(userKey)) return false;
    seenUsers.add(userKey);
    return true;
  }).slice(0, 5);
  const existingByUser = new Map(voterItems.map((item) => [item.userKey, item]));
  const nextItems = entries.map((entry) => {
    const userKey = String(entry.user).toLowerCase();
    const signature = JSON.stringify([entry.user, entry.choice]);
    let item = existingByUser.get(userKey);
    if (item) {
      existingByUser.delete(userKey);
      if (item.signature !== signature) {
        item.node.textContent = `${entry.user} → !${entry.choice}`;
        item.node.classList.remove("new");
        void item.node.offsetWidth;
        item.node.classList.add("new");
        item.signature = signature;
      }
      return item;
    }

    const node = document.createElement("li");
    node.className = "voter-pill new";
    node.textContent = `${entry.user} → !${entry.choice}`;
    return { userKey, signature, node };
  });

  existingByUser.forEach((item) => {
    item.node.classList.remove("new");
    item.node.classList.add("exiting");
    setTimeout(() => item.node.remove(), 340);
  });

  voterItems = nextItems;
  voterItems.forEach((item) => list.appendChild(item.node));
}

function render(state) {
  const writing = state.status === "starting" || state.status === "generating";

  // New chapter arrived: type it out and build fresh choice rows
  if (!writing && state.scene !== shownScene && state.scene) {
    shownScene = state.scene;
    el("chapter").textContent = `Chapter ${state.chapter}`;
    typeScene(state.scene);
    buildChoices(state.choices);
    replayAnimation(el("scene"), "chapter-enter");
    el("choices").querySelectorAll(".choice").forEach((choice, index) => {
      choice.style.animationDelay = `${index * 70}ms`;
      replayAnimation(choice, "chapter-enter");
    });
  }

  el("choices").classList.toggle("hidden", writing);
  updateChoices(state);

  const status = el("status");
  if (writing) {
    status.textContent = "✦ The Dungeon Master is writing… ✦";
  } else if (state.paused) {
    status.textContent = "⏸ Paused";
  } else if (state.status === "reveal") {
    status.textContent = `Chat has chosen: ${state.choices[state.winner - 1]}`;
  } else {
    status.textContent = "";
  }
  status.classList.toggle("active", status.textContent !== "");

  const voting = state.status === "voting";
  const timePct = state.voting_seconds ? (state.seconds_left / state.voting_seconds) * 100 : 0;
  el("timer-fill").style.width = (voting ? timePct : 0) + "%";
  el("timer-fill").classList.toggle("urgent", voting && state.seconds_left <= 5);

  el("hint").style.visibility = voting ? "visible" : "hidden";
  const votesText = `${state.total_votes} vote${state.total_votes === 1 ? "" : "s"}`;
  el("meta").textContent = voting ? `${state.seconds_left}s · ${votesText}` : votesText;
  const voterPanel = document.querySelector(".voter-panel");
  const voterPanelTopBefore = voterPanel.getBoundingClientRect().top;
  updateTrail(state.trail);
  updateRecentVotes(state.recent_votes);
  const voterPanelTopAfter = voterPanel.getBoundingClientRect().top;
  const verticalShift = voterPanelTopBefore - voterPanelTopAfter;
  if (verticalShift) {
    voterPanel.animate(
      [
        { transform: `translateY(${verticalShift}px)` },
        { transform: "translateY(0)" },
      ],
      { duration: 350, easing: "ease-out" },
    );
  }
}

async function poll() {
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    render(await response.json());
  } catch (error) {
    el("status").textContent = "Reconnecting to the game...";
  }
  setTimeout(poll, POLL_MS);
}

poll();
