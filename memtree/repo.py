"""WorkspaceRepo — a real git repo that grows as the agent runs.

Each captured Turn becomes one commit. The agent's code blocks accumulate in
`notebook.py` with `# Turn N` markers. `tool_outputs.json` and
`state_summary.json` are placeholder scaffolding now; they're populated in
Phase 2 step 3 (replay) and by the agent (state summary).

Per design decisions (CLAUDE.md + 2026-05-26 conversation):
- Wipe and recreate `workspace/` at every session start.
- Only the main agent writes commits; sub-agents capture in-memory only.
- Turn 0 is the locked initial commit — empty scaffolding, no corpus dump.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import git

from memtree.agent import Turn

_AUTHOR = git.Actor("MemTree Agent", "agent@memtree.local")
_NOTEBOOK_HEADER = "# Turn 0 — initial scaffolding (locked)\n"


class WorkspaceRepo:
    """Per-session git workspace for the agent's accumulated code."""

    def __init__(self, path: str | Path = "workspace", reset: bool = True) -> None:
        self.path = Path(path).resolve()
        if reset and self.path.exists():
            shutil.rmtree(self.path)
        self.path.mkdir(parents=True, exist_ok=True)

        self.notebook_path = self.path / "notebook.py"
        self.tool_outputs_path = self.path / "tool_outputs.json"
        self.state_summary_path = self.path / "state_summary.json"

        self.notebook_path.write_text(_NOTEBOOK_HEADER, encoding="utf-8")
        self.tool_outputs_path.write_text("[]\n", encoding="utf-8")
        self.state_summary_path.write_text("{}\n", encoding="utf-8")

        self.repo = git.Repo.init(self.path, initial_branch="main")
        self.repo.index.add(
            [self.notebook_path.name, self.tool_outputs_path.name, self.state_summary_path.name]
        )
        self.repo.index.commit("Turn 0: initial scaffolding", author=_AUTHOR, committer=_AUTHOR)

    # ------------------------------------------------------------------
    # Per-turn commit
    # ------------------------------------------------------------------
    def append_turn(self, turn: Turn) -> str:
        """Append the turn's code to notebook.py and commit. Returns the new sha."""
        code = (turn.code or "").rstrip()
        summary = self._summary(turn)
        header = f"\n\n# Turn {turn.turn_number} — {summary}\n"
        body = code + "\n" if code else "# (no code in this step)\n"
        with self.notebook_path.open("a", encoding="utf-8") as f:
            f.write(header + body)

        # Stage notebook + tool outputs + state summary so per-turn cache state
        # AND kernel-state snapshot are captured at the same commit.
        # - tool_outputs.json is written by ToolCache.save() during the turn.
        # - state_summary.json is written by MemTreeAgent._finalize_step.
        self.repo.index.add(
            [
                self.notebook_path.name,
                self.tool_outputs_path.name,
                self.state_summary_path.name,
            ]
        )
        commit_msg = f"Turn {turn.turn_number}: {summary}"
        commit = self.repo.index.commit(commit_msg, author=_AUTHOR, committer=_AUTHOR)
        return commit.hexsha

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _summary(turn: Turn) -> str:
        """One-line label for the commit / notebook marker."""
        if turn.is_final_answer:
            return "final_answer"
        if turn.error:
            first = turn.error.splitlines()[0] if isinstance(turn.error, str) else str(turn.error)
            return f"error — {first[:60]}"
        first_code = next(
            (ln.strip() for ln in (turn.code or "").splitlines() if ln.strip() and not ln.strip().startswith("#")),
            "",
        )
        return (first_code[:60] + "…") if len(first_code) > 60 else (first_code or "no-op")

    def log(self) -> list[tuple[str, str]]:
        """Return [(short_sha, message), ...] in topological order, oldest first."""
        commits = list(self.repo.iter_commits("main"))
        commits.reverse()
        return [(c.hexsha[:7], c.message.strip()) for c in commits]
