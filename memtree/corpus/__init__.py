"""Pre-loaded scope for the research-synthesis demo.

`load_corpus()` returns `(docs, conn)`:
- `docs`: dict[str, str] — `{doc_id: full_markdown_body}` for every .md in `docs/`.
- `conn`: an in-memory `sqlite3.Connection` populated from `seed.py`.

The agent's job is to compare claims across the markdown docs and reconcile them
with the audited numbers in the DB. The DB is the ground truth.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from memtree.corpus.seed import BENCHMARKS, COSTS, DDL

_DOCS_DIR = Path(__file__).parent / "docs"


def load_documents() -> dict[str, str]:
    """Read every .md file in `docs/` into a `{doc_id: body}` dict."""
    return {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted(_DOCS_DIR.glob("*.md"))
    }


def load_db() -> sqlite3.Connection:
    """Build an in-memory SQLite DB populated from `seed.py`.

    Opens with `check_same_thread=False` so the connection can be passed into
    sub-agents running under `spawn_agents`' thread pool. The demo only reads.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.executescript(DDL)
    conn.executemany(
        "INSERT INTO benchmarks (lab, eval_name, period, score, source) VALUES (?, ?, ?, ?, ?)",
        BENCHMARKS,
    )
    conn.executemany(
        "INSERT INTO costs (lab, eval_name, period, agent_gpu_hours, grader_gpu_hours, human_review_hours) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        COSTS,
    )
    conn.commit()
    return conn


def load_corpus() -> tuple[dict[str, str], sqlite3.Connection]:
    return load_documents(), load_db()
