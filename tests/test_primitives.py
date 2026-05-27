"""Offline tests for MemEx primitives — no LLM call required.

Validates Pydantic-typed submission, scope injection, and that smolagents'
LocalPythonExecutor persists variables across `__call__` invocations (which is
the substrate underneath Phase-1 persistent scope).
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError
from smolagents.local_python_executor import LocalPythonExecutor

from memtree.primitives.typed_submit import TypedFinalAnswerError, TypedFinalAnswerTool


class Report(BaseModel):
    region: str
    total: float


def test_typed_submit_accepts_dict():
    tool = TypedFinalAnswerTool(Report)
    out = tool.forward({"region": "north", "total": 1.2})
    assert isinstance(out, Report)
    assert out.region == "north"


def test_typed_submit_accepts_instance():
    tool = TypedFinalAnswerTool(Report)
    out = tool.forward(Report(region="south", total=0.9))
    assert isinstance(out, Report)


def test_typed_submit_rejects_bad_shape():
    tool = TypedFinalAnswerTool(Report)
    with pytest.raises(TypedFinalAnswerError):
        tool.forward({"region": "north"})  # missing `total`


def test_executor_state_persists_across_calls():
    """The Phase-1 'persistent scope' guarantee bottoms out here."""
    ex = LocalPythonExecutor(additional_authorized_imports=[])
    ex.send_tools({})
    ex("x = 41 + 1")
    result = ex("x")
    # smolagents' executor returns a CodeOutput with `.output`; tolerate either shape.
    value = getattr(result, "output", result)
    assert value == 42


def test_corpus_conn_usable_from_worker_thread():
    """Sub-agents run on `ThreadPoolExecutor` workers; the conn must work there."""
    from concurrent.futures import ThreadPoolExecutor

    from memtree.corpus import load_corpus

    _, conn = load_corpus()

    def _query():
        return conn.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]

    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(_query).result() > 0


def test_corpus_loads_and_planted_inconsistency_is_present():
    """Alpha's docs claim 92% on AgentEval-Pro Q1-2026; the DB audit must say something else."""
    from memtree.corpus import load_corpus

    docs, conn = load_corpus()
    assert len(docs) >= 6, "corpus must have at least 6 documents per spec"
    assert "alpha_methodology" in docs

    # The qualitative claim
    assert "92%" in docs["alpha_methodology"]

    # The audited number
    (score,) = conn.execute(
        "SELECT score FROM benchmarks WHERE lab='Lab Alpha' AND eval_name='AgentEval-Pro' AND period='2026-Q1'"
    ).fetchone()
    assert score != 0.92, "planted inconsistency removed — Criterion 5 will be unsatisfiable"
