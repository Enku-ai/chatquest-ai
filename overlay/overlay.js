// Asks the game for its state twice a second and updates the screen.
const POLL_MS = 500;
const TYPE_MS = 22; // typewriter speed (ms per letter)

const el = (id) => document.getElementById(id);
let shownScene = "";
let typingTimer = null;
const trailNodes = new Map();

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

function buildChoices(choices) {
  const list = el("choices");
  list.innerHTML = "";
  choices.forEach((choice, i) => {
    const li = document.createElement("li");
    li.className = "choice";
    li.innerHTML = `
      <div class="choice-bar"></div>
      <span class="choice-key">!${i + 1}</span>
      <span class="choice-text"></span>
      <span class="choice-count">0</span>`;
    li.querySelector(".choice-text").textContent = choice; // safe: no HTML from AI
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

function render(state) {
  const writing = state.status === "starting" || state.status === "generating";

  // New chapter arrived: type it out and build fresh choice rows
  if (!writing && state.scene !== shownScene && state.scene) {
    shownScene = state.scene;
    el("chapter").textContent = `Chapter ${state.chapter}`;
    typeScene(state.scene);
    buildChoices(state.choices);
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
  updateTrail(state.trail);
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
