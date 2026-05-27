"""Seed data + DDL for the demo SQLite DB.

Two tables — `benchmarks` (audited scores) and `costs` (audited compute spend) —
covering the same three labs that publish the markdown corpus. The DB is the
audited record; the docs are public claims. By design there is at least one
inconsistency between a qualitative doc claim and a DB row, which the demo
agent is supposed to find.
"""
from __future__ import annotations

DDL = """
CREATE TABLE benchmarks (
    lab        TEXT NOT NULL,
    eval_name  TEXT NOT NULL,
    period     TEXT NOT NULL,
    score      REAL NOT NULL,      -- 0..1 (e.g. 0.87 == 87%)
    source     TEXT                -- 'self_reported' | 'consortium_audited'
);

CREATE TABLE costs (
    lab                 TEXT NOT NULL,
    eval_name           TEXT NOT NULL,
    period              TEXT NOT NULL,
    agent_gpu_hours     REAL,
    grader_gpu_hours    REAL,
    human_review_hours  REAL
);
"""

# Each row: (lab, eval_name, period, score, source)
# Note the planted inconsistency: Lab Alpha's docs claim 92% on AgentEval-Pro
# Q1-2026; the consortium-audited row below says 0.87 (87%).
BENCHMARKS = [
    ("Lab Alpha",  "AgentEval-Pro",  "2026-Q1", 0.87, "consortium_audited"),
    ("Lab Alpha",  "AgentEval-Lite", "2026-Q1", 0.94, "consortium_audited"),
    ("Lab Alpha",  "ToolBench-Hard", "2026-Q1", 0.71, "consortium_audited"),
    ("Lab Alpha",  "AgentEval-Pro",  "2025-Q4", 0.83, "consortium_audited"),

    ("Lab Beta",   "AgentEval-Pro",  "2026-Q1", 0.89, "consortium_audited"),
    ("Lab Beta",   "DriftBench-v1",  "2026-Q1", 0.74, "consortium_audited"),
    ("Lab Beta",   "ToolBench-Hard", "2026-Q1", 0.69, "consortium_audited"),
    ("Lab Beta",   "AgentEval-Pro",  "2025-Q4", 0.81, "consortium_audited"),

    ("Lab Gamma",  "AgentEval-Pro",  "2026-Q1", 0.88, "consortium_audited"),
    ("Lab Gamma",  "ToolBench-Hard", "2026-Q1", 0.66, "consortium_audited"),
    ("Lab Gamma",  "Internal-Eval-v3", "2026-Q1", 0.79, "self_reported"),
    ("Lab Gamma",  "AgentEval-Pro",  "2025-Q4", 0.80, "consortium_audited"),
]

# (lab, eval_name, period, agent_gpu_hours, grader_gpu_hours, human_review_hours)
COSTS = [
    ("Lab Alpha",  "AgentEval-Pro",  "2026-Q1", 180.0, 0.0,   40.0),
    ("Lab Alpha",  "AgentEval-Lite", "2026-Q1",  28.0, 0.0,   12.0),
    ("Lab Alpha",  "ToolBench-Hard", "2026-Q1",  95.0, 0.0,   25.0),

    ("Lab Beta",   "AgentEval-Pro",  "2026-Q1", 175.0, 0.0,   30.0),
    ("Lab Beta",   "DriftBench-v1",  "2026-Q1", 210.0, 45.0,   0.0),
    ("Lab Beta",   "ToolBench-Hard", "2026-Q1",  88.0, 0.0,   20.0),

    ("Lab Gamma",  "AgentEval-Pro",  "2026-Q1", 165.0, 110.0,  35.0),
    ("Lab Gamma",  "ToolBench-Hard", "2026-Q1",  90.0,  60.0,  18.0),
    ("Lab Gamma",  "Internal-Eval-v3", "2026-Q1", 220.0, 140.0, 50.0),
]
