"""MemTree dashboard — a repo browser for the running agent.

Three panels:
- LEFT:   commit log (one row per turn). Click to select.
- CENTER: notebook.py contents at the selected commit, syntax-highlighted.
- RIGHT:  kernel-state summary (variables, types, length, repr) at the selected commit.

The dashboard is decoupled from the agent: both processes coordinate only
through the `workspace/` directory. The agent commits each turn (writing
notebook.py / tool_outputs.json / state_summary.json); the dashboard polls
the repo every 2 seconds via `streamlit-autorefresh`.

"Checkout selected commit" writes `workspace/.revert_request` with the target
turn number. The agent's `_finalize_step` honours it at the end of its next
step. (CLAUDE.md design decision #8: decoupled via the filesystem.)
"""
from __future__ import annotations

import atexit
import json
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh

import git


WORKSPACE = Path("workspace").resolve()
TURN_RE = re.compile(r"^Turn (\d+):")
KLAUS_PORT = 5099  # auto-started subprocess, see start_klaus()


# -----------------------------------------------------------------------------
# Workspace adapters (no agent imports — dashboard reads files only)
# -----------------------------------------------------------------------------
def workspace_ready() -> bool:
    return (WORKSPACE / ".git").exists() and (WORKSPACE / "notebook.py").exists()


def open_repo() -> git.Repo:
    return git.Repo(WORKSPACE)


def list_commits(repo: git.Repo) -> list[dict]:
    """Return [{sha, short, turn, message, branch?}, ...] oldest-first."""
    commits = list(repo.iter_commits(repo.active_branch.name))
    commits.reverse()
    rows = []
    for c in commits:
        msg = c.message.strip().splitlines()[0]
        m = TURN_RE.match(msg)
        turn = int(m.group(1)) if m else None
        rows.append(
            {"sha": c.hexsha, "short": c.hexsha[:7], "turn": turn, "message": msg}
        )
    return rows


def read_at(repo: git.Repo, sha: str, path: str) -> str:
    try:
        return repo.git.show(f"{sha}:{path}")
    except git.GitCommandError:
        return ""


def write_revert_request(to_turn: int, reason: str) -> None:
    (WORKSPACE / ".revert_request").write_text(
        json.dumps({"to_turn": to_turn, "reason": reason}, indent=2), encoding="utf-8"
    )


# -----------------------------------------------------------------------------
# Klaus auto-start (full git web UI, embedded via iframe)
# -----------------------------------------------------------------------------
def _port_in_use(port: int) -> bool:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


@st.cache_resource
def start_klaus(workspace_path: str, port: int = KLAUS_PORT) -> dict:
    """Start klaus on `port` (or detect one already running). Cached across reruns."""
    if shutil.which("klaus") is None:
        return {"status": "missing", "url": None}
    if _port_in_use(port):
        # Assume klaus (or something else) is already serving the port.
        return {"status": "external", "url": f"http://127.0.0.1:{port}"}

    proc = subprocess.Popen(
        ["klaus", "--host", "127.0.0.1", "--port", str(port), workspace_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    atexit.register(lambda: proc.terminate())

    # Wait briefly for it to bind.
    for _ in range(20):
        if _port_in_use(port):
            return {"status": "started", "url": f"http://127.0.0.1:{port}", "pid": proc.pid}
        time.sleep(0.1)
    return {"status": "started-slow", "url": f"http://127.0.0.1:{port}", "pid": proc.pid}


# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="MemTree", layout="wide")
st_autorefresh(interval=2000, key="memtree-autorefresh")

st.title("MemTree — agent repo browser")
st.caption(f"Watching `{WORKSPACE}` · refresh every 2s · CLAUDE.md design #8")

if not workspace_ready():
    st.info(
        "Workspace not initialised yet. Start the agent in another terminal:\n\n"
        "```\npython -m examples.research_synthesis\n```\n"
        f"This dashboard polls `{WORKSPACE}` and will populate once the agent "
        "writes its first commit."
    )
    st.stop()

repo = open_repo()
branch = repo.active_branch.name
commits = list_commits(repo)
if not commits:
    st.warning("Repo exists but has no commits yet.")
    st.stop()

# Default selection = HEAD (last commit)
default_sha = commits[-1]["sha"]
selected_sha = st.session_state.get("selected_sha") or default_sha
if selected_sha not in {c["sha"] for c in commits}:
    selected_sha = default_sha
    st.session_state["selected_sha"] = selected_sha


# -----------------------------------------------------------------------------
# Layout: two tabs — live agent view + embedded klaus git browser
# -----------------------------------------------------------------------------
live_tab, git_tab = st.tabs(["📊 Live", "📜 Git Browser (klaus)"])

with live_tab:
    left, center, right = st.columns([1.0, 2.2, 1.4])

    with left:
        st.subheader("Commits")
        st.caption(f"branch: `{branch}` · {len(commits)} commits")
        # Newest first so the latest turn is visible without scrolling
        for c in reversed(commits):
            label = (
                f"**Turn {c['turn']}** · `{c['short']}`" if c["turn"] is not None
                else f"`{c['short']}` · {c['message'][:40]}"
            )
            is_selected = c["sha"] == selected_sha
            prefix = "▸ " if is_selected else "  "
            if st.button(
                f"{prefix}{label}",
                key=f"commit-{c['sha']}",
                use_container_width=True,
                type=("primary" if is_selected else "secondary"),
            ):
                st.session_state["selected_sha"] = c["sha"]
                st.rerun()
            st.caption(c["message"][:80])

    with center:
        selected = next(c for c in commits if c["sha"] == selected_sha)
        st.subheader(f"notebook.py @ {selected['short']}")
        st.caption(selected["message"])
        nb = read_at(repo, selected_sha, "notebook.py")
        st.code(nb or "# (empty)", language="python", line_numbers=True)

        if selected["turn"] is not None and selected["turn"] >= 1:
            col_a, col_b = st.columns([1, 3])
            with col_a:
                if st.button("⏮ Checkout selected commit", type="primary"):
                    write_revert_request(
                        to_turn=selected["turn"],
                        reason=f"dashboard checkout to Turn {selected['turn']}",
                    )
                    st.success(
                        f"Wrote revert request for Turn {selected['turn']}. "
                        "The agent will honour it after its next step."
                    )
            with col_b:
                req = WORKSPACE / ".revert_request"
                if req.exists():
                    st.warning(f"Pending revert request: `{req.read_text().strip()}`")
        elif selected["turn"] == 0:
            st.caption("Turn 0 is the locked initial scaffolding — cannot be reverted to.")

    with right:
        st.subheader("Kernel state")
        summary_raw = read_at(repo, selected_sha, "state_summary.json")
        try:
            summary = json.loads(summary_raw) if summary_raw else {}
        except json.JSONDecodeError:
            summary = {}
        variables = summary.get("variables", [])
        st.caption(f"turn snapshot: {summary.get('turn', '—')} · {len(variables)} vars")
        if not variables:
            st.caption("_no variables captured at this commit_")
        for v in variables:
            with st.expander(
                f"`{v['name']}` · {v['type']}"
                + (f" · len={v['length']}" if v.get("length") is not None else "")
            ):
                st.code(v["repr"], language="python")

with git_tab:
    klaus_info = start_klaus(str(WORKSPACE))
    if klaus_info["status"] == "missing":
        st.error(
            "`klaus` is not installed. Install it in this venv:\n\n"
            "```bash\npip install klaus\n```\n\n"
            "Then refresh this page."
        )
    else:
        url = klaus_info["url"]
        status_blurb = {
            "started": f"auto-started (pid {klaus_info.get('pid')})",
            "started-slow": f"auto-started, may take a moment to come up (pid {klaus_info.get('pid')})",
            "external": "detected on port already (not started by dashboard)",
        }.get(klaus_info["status"], klaus_info["status"])
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"klaus serving at {url} · {status_blurb}")
        with col2:
            st.link_button("Open in new tab ↗", url, use_container_width=True)
        st.components.v1.iframe(url, height=900, scrolling=True)
