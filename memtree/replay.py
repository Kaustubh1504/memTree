"""Replay agent code from a workspace commit to rebuild kernel state.

`replay(repo, sha, scope, tools, cache)` reads `notebook.py` and
`tool_outputs.json` at the given commit, spins up a fresh `LocalPythonExecutor`,
pre-loads the original scope + replay-mode wrapped tools, executes the notebook,
and returns the resulting state dict.

Per CLAUDE.md design decision: "Kernel state is rebuilt, not snapshotted."
No dill, no deepcopy of live state — we re-execute from Turn 0 in a clean kernel.
"""
from __future__ import annotations

from typing import Any, Sequence

from smolagents.local_python_executor import LocalPythonExecutor
from smolagents.tools import Tool

from memtree.repo import WorkspaceRepo
from memtree.tools.cached import ToolCache, attach_cache, current_cache


def _read_blob(repo: WorkspaceRepo, sha: str, path: str) -> str:
    """Read a file's contents at the given commit via `git show`."""
    return repo.repo.git.show(f"{sha}:{path}")


def replay(
    repo: WorkspaceRepo,
    sha: str,
    scope: dict[str, Any],
    tools: Sequence[Tool],
    cache: ToolCache | None = None,
    additional_authorized_imports: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Re-execute notebook.py up to `sha` in a fresh kernel and return its state.

    Args:
        repo: the workspace.
        sha: the commit to replay up to (inclusive).
        scope: variables the agent had at Turn 0 (docs, conn, etc.).
        tools: the same tool objects the agent was using. Wrapped in-place with
            replay-mode caching for the duration of this call.
        cache: optional cache; if omitted we build one from the commit's
            `tool_outputs.json`.
        additional_authorized_imports: same list passed to the original agent.

    Returns:
        The replayed kernel's state dict (mutable view; copy if you need to detach).
    """
    notebook = _read_blob(repo, sha, "notebook.py")

    # Build a replay-only cache from the commit's tool_outputs.json. We give
    # it no path so its save() is a no-op — we don't want to clobber the live
    # tool_outputs.json on disk during replay.
    replay_cache = ToolCache(path=None)
    replay_cache.load_text(_read_blob(repo, sha, "tool_outputs.json"))
    replay_cache.mode = "replay"

    # Remember the cache each tool was wrapped with before this call so we can
    # restore it afterwards. (None if the tool has never been wrapped.)
    saved_caches = [(t, current_cache(t)) for t in tools]
    attach_cache(tools, replay_cache)

    executor = LocalPythonExecutor(
        additional_authorized_imports=list(additional_authorized_imports or []),
    )
    executor.send_variables(dict(scope))
    executor.send_tools({t.name: t for t in tools})
    # Neutralise final_answer during replay — its real behaviour is to raise
    # out of the agent loop, which we're not in here.
    executor.state["final_answer"] = lambda *a, **kw: None

    try:
        executor(notebook)
    finally:
        # Restore each tool's previous cache (the live record-mode cache, in
        # the normal case). Tools that had no prior cache are left wrapped
        # with the replay cache, but that's harmless since the caller didn't
        # have a cache for them anyway.
        for t, prev in saved_caches:
            if prev is not None:
                attach_cache([t], prev)

    return executor.state
