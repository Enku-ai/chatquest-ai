"""Streamer control panel (only you see this).
Run with:  streamlit run dashboard/control_panel.py"""
import httpx
import streamlit as st

API = "http://127.0.0.1:8765"

st.set_page_config(page_title="ChatQuest Control", page_icon="⚔️")
st.title("⚔️ ChatQuest Control Panel")


def send(path: str, **params):
    """Send a command to the game server."""
    try:
        response = httpx.post(f"{API}{path}", params=params, timeout=3)
        response.raise_for_status()
        st.toast("Done ✅")
    except httpx.HTTPError as error:
        st.error(f"Game server not reachable: {error}")


def get_state():
    try:
        return httpx.get(f"{API}/api/state", timeout=3).json()
    except httpx.HTTPError:
        return None


@st.fragment(run_every=1)
def live_status():
    """Redraws itself every second with the current game state."""
    state = get_state()
    if state is None:
        st.error("Game server is not running. Start it with: python -m app.main")
        return

    status = "PAUSED" if state["paused"] else state["status"].upper()
    col1, col2, col3 = st.columns(3)
    col1.metric("Status", status)
    col2.metric("Chapter", state["chapter"])
    col3.metric("Time left", f"{state['seconds_left']}s")

    st.write(state["scene"] or "_Waiting for the first chapter..._")

    total = state["total_votes"]
    for i, choice in enumerate(state["choices"]):
        count = state["tally"][i] if i < len(state["tally"]) else 0
        share = count / total if total else 0
        st.progress(share, text=f"!{i + 1}  {choice}  —  {count} votes")

    st.caption(f"Story source: {state['source'] or '-'}  ·  Total votes: {total}")


live_status()

st.divider()
st.subheader("Controls")
col1, col2, col3, col4 = st.columns(4)
if col1.button("⏸ Pause"):
    send("/api/control/pause")
if col2.button("▶ Resume"):
    send("/api/control/resume")
if col3.button("⏭ Skip vote"):
    send("/api/control/skip")
if col4.button("🔄 New adventure"):
    send("/api/control/restart")

st.subheader("Settings")
seconds = st.slider("Voting time (seconds)", min_value=15, max_value=120, value=45, step=5)
if st.button("Apply voting time"):
    send("/api/control/seconds", value=seconds)