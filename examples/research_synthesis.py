"""End-to-end research-synthesis demo exercising all five Phase-1 criteria.

Run with:
    cp .env.example .env   # then put your key in .env
    python -m examples.research_synthesis

Task: compare three fictional AI labs' positions on agent-evaluation methodology
across a 9-document markdown corpus plus an audited SQLite DB of benchmark scores
and costs. The agent must surface common themes, disagreements, and one factual
inconsistency between a doc claim and the audited numbers.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

# Load `.env` from the project root if present. Shell env still wins (override=False).
load_dotenv(override=False)

from memtree import WorkspaceRepo, build_agent, spawn_agents
from memtree.corpus import load_corpus
from memtree.kernel import build_model
from memtree.primitives.typed_submit import TypedFinalAnswerError, TypedFinalAnswerTool
from memtree.run_log import RunLogger
from memtree.tools.query_db import query_db
from memtree.tools.read_section import read_section
from memtree.tools.save_finding import save_finding
from memtree.tools.search_documents import search_documents

console = Console()


# ---------------------------------------------------------------------------
# Typed submit schema
# ---------------------------------------------------------------------------

class Theme(BaseModel):
    title: str = Field(description="Short label for the theme.")
    summary: str = Field(description="One- to two-sentence summary.")
    labs: list[str] = Field(description="Labs whose docs support this theme.")


class Disagreement(BaseModel):
    topic: str = Field(description="What the labs disagree about.")
    positions: dict[str, str] = Field(
        description="Mapping of lab name to that lab's position in one sentence."
    )


class Inconsistency(BaseModel):
    description: str = Field(description="What the inconsistency is, in plain English.")
    doc_claim: str = Field(description="The claim made in a markdown document.")
    db_evidence: str = Field(description="The contradicting value or row from the DB.")
    doc_id: str = Field(description="The document id where the claim appears.")


class ComparisonReport(BaseModel):
    themes: list[Theme]
    disagreements: list[Disagreement]
    inconsistency: Inconsistency


class LabBrief(BaseModel):
    """Per-lab brief returned by a spawned sub-agent."""
    lab: str = Field(description="Lab name (Lab Alpha / Lab Beta / Lab Gamma).")
    position_summary: str = Field(description="2-3 sentence summary of the lab's overall stance.")
    headline_score: float | None = Field(
        description="Audited Q1-2026 AgentEval-Pro score (0-1) for this lab from the DB, or null."
    )
    notable_claims: list[str] = Field(description="2-4 short notable claims from the lab's docs.")


# ---------------------------------------------------------------------------
# Pretty-printers
# ---------------------------------------------------------------------------

def banner(title: str) -> None:
    console.print(Rule(f"[bold cyan]{title}[/bold cyan]"))


def require_model_credentials() -> None:
    """Check the env var that matches the selected provider."""
    from memtree.kernel import DEFAULT_MODEL_ID

    if DEFAULT_MODEL_ID.startswith(("hosted_vllm/", "ollama_chat/", "ollama/")):
        return  # local providers need no key
    if DEFAULT_MODEL_ID.startswith("xai/"):
        required, hint = "XAI_API_KEY", "https://console.x.ai/"
    elif DEFAULT_MODEL_ID.startswith("groq/"):
        required, hint = "GROQ_API_KEY", "https://console.groq.com/keys"
    elif DEFAULT_MODEL_ID.startswith("openai/"):
        # Covers DashScope/Qwen-Cloud via OpenAI-compatible endpoint.
        required, hint = "OPENAI_API_KEY", "https://bailian.console.alibabacloud.com/ (DashScope)"
    else:
        required, hint = "GEMINI_API_KEY", "https://aistudio.google.com/apikey"

    if not os.environ.get(required):
        console.print(
            Panel.fit(
                f"{required} is not set.\n"
                f"Get a key at {hint} and add it to `.env`\n"
                "(`cp .env.example .env` for the template). Pick the provider\n"
                "section in `.env.example` that matches the model you want.",
                title="Missing credentials",
                border_style="red",
            )
        )
        sys.exit(2)


# ---------------------------------------------------------------------------
# Section 1: typed-submit guardrail (cheap; runs first)
# ---------------------------------------------------------------------------

def demo_typed_submit_guardrail() -> None:
    banner("Typed submit — schema violation raises")
    tool = TypedFinalAnswerTool(ComparisonReport)
    try:
        tool.forward({"themes": [], "disagreements": []})  # missing `inconsistency`
    except TypedFinalAnswerError as e:
        console.print(Panel.fit(str(e)[:400], title="Caught TypedFinalAnswerError", border_style="yellow"))
        return
    raise AssertionError("Typed submit accepted an invalid payload — guardrail broken.")


# ---------------------------------------------------------------------------
# Section 2: parallel sub-agents (Criterion 5) — one brief per lab
# ---------------------------------------------------------------------------

def demo_per_lab_briefs(docs: dict[str, str], conn: Any, run_logger: RunLogger | None = None) -> list[LabBrief]:
    banner("spawn_agents — one sub-agent per lab, in parallel")
    labs = ["Lab Alpha", "Lab Beta", "Lab Gamma"]
    jobs = [
        {
            "task": (
                f"You are briefing on {lab!r}. The variables `docs` (dict of markdown bodies "
                "keyed by doc_id) and `conn` (sqlite3 connection) are already in your scope.\n\n"
                "DB schema (use these column names exactly):\n"
                "  benchmarks(lab TEXT, eval_name TEXT, period TEXT, score REAL, source TEXT)\n"
                "  costs(lab TEXT, eval_name TEXT, period TEXT, agent_gpu_hours REAL, "
                "grader_gpu_hours REAL, human_review_hours REAL)\n"
                "`score` is a fraction in [0, 1] (e.g. 0.87 == 87%). `eval_name` examples: "
                "'AgentEval-Pro', 'AgentEval-Lite', 'ToolBench-Hard', 'DriftBench-v1'.\n\n"
                "Use `search_documents(docs, query)` and `read_section(docs, doc_id, section)` to "
                "read this lab's documents. Use `query_db(conn, sql)` to look up this lab's audited "
                f"AgentEval-Pro score for period '2026-Q1'. Finally call final_answer with a "
                f"LabBrief: lab={lab!r}, position_summary=..., headline_score=<float or None>, "
                "notable_claims=[2-4 short strings]."
            ),
            "scope": {"docs": docs, "conn": conn},
            "agent_label": f"sub-{lab.lower().replace(' ', '-')}",
        }
        for lab in labs
    ]
    briefs: list[LabBrief] = spawn_agents(
        jobs,
        return_type=LabBrief,
        tools=[search_documents, read_section, query_db],
        model=build_model(),
        max_steps=10,
        additional_authorized_imports=["json"],
        run_logger=run_logger,
    )
    for b in briefs:
        score_str = f"{b.headline_score:.0%}" if b.headline_score is not None else "n/a"
        console.print(f"  • {b.lab} (audited AEP {score_str}): {b.position_summary}")
    return briefs


# ---------------------------------------------------------------------------
# Section 3: main agent (Criteria 1–4) — synthesises across briefs + corpus
# ---------------------------------------------------------------------------

def demo_synthesis(
    docs: dict[str, str],
    conn: Any,
    briefs: list[LabBrief],
    run_logger: RunLogger | None = None,
    repo: WorkspaceRepo | None = None,
) -> ComparisonReport:
    banner("Main agent — persistent scope, drop-in tools, pre-loaded scope, typed submit")

    findings: list[dict] = []

    agent = build_agent(
        tools=[search_documents, read_section, query_db, save_finding],
        final_answer_type=ComparisonReport,
        scope={
            "docs": docs,
            "conn": conn,
            "findings": findings,
            "briefs": [b.model_dump() for b in briefs],
        },
        additional_authorized_imports=["json"],
        run_logger=run_logger,
        agent_label="main",
        repo=repo,
    )

    schema_hint = (
        "DB schema (use these column names exactly):\n"
        "  benchmarks(lab, eval_name, period, score, source)\n"
        "  costs(lab, eval_name, period, agent_gpu_hours, grader_gpu_hours, human_review_hours)\n"
        "`score` is a fraction in [0, 1]."
    )

    # Turn 1 — pull common themes across docs, accumulate via save_finding.
    agent.run(
        "Skim the corpus using `search_documents(docs, ...)` and `read_section(docs, ...)`. "
        "The variable `briefs` already contains a per-lab summary you can use as a starting point. "
        "Identify 2-3 themes that appear across at least two labs. For each, call "
        "`save_finding(findings, 'theme', <one-line description>)`. Do NOT call final_answer yet.\n\n"
        + schema_hint,
        reset=True,
    )

    # Turn 2 — re-use `findings` from turn 1; cross-check qualitative vs quantitative.
    agent.run(
        "The list `findings` already has the themes you saved last turn — do not redo that work. "
        "Now find at least one factual inconsistency between a qualitative claim in a markdown "
        "doc and an audited number in the `benchmarks` table. Hint: look at Lab Alpha's headline "
        "AgentEval-Pro number. Save the inconsistency via "
        "`save_finding(findings, 'inconsistency', <description>)`. Print `findings` at the end. "
        "Do NOT call final_answer yet.",
        reset=False,
    )

    # Turn 3 — assemble the typed ComparisonReport from accumulated findings.
    result = agent.run(
        "Using only the items already in `findings` plus `briefs` (both still in scope), "
        "assemble a ComparisonReport and call final_answer with it. Themes and disagreements "
        "come from the saved findings; the inconsistency entry maps directly to the "
        "Inconsistency object (set doc_id to the document where the claim appears).",
        reset=False,
    )

    console.print(Panel(result.model_dump_json(indent=2), title="ComparisonReport (typed)", border_style="green"))
    assert isinstance(result, ComparisonReport), f"expected ComparisonReport, got {type(result)!r}"
    if run_logger is not None:
        run_logger.event("final_report", result)
        run_logger.event("findings_final", findings)
    return result


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    require_model_credentials()
    demo_typed_submit_guardrail()

    run_logger = RunLogger()
    console.print(f"[dim]Logging full run to {run_logger.path}[/dim]")

    repo = WorkspaceRepo("workspace")
    console.print(f"[dim]Workspace git repo: {repo.path} (Turn 0 committed)[/dim]")

    docs, conn = load_corpus()
    console.print(f"[dim]Loaded corpus: {len(docs)} docs, "
                  f"{conn.execute('SELECT COUNT(*) FROM benchmarks').fetchone()[0]} benchmark rows, "
                  f"{conn.execute('SELECT COUNT(*) FROM costs').fetchone()[0]} cost rows.[/dim]")

    briefs = demo_per_lab_briefs(docs, conn, run_logger=run_logger)
    demo_synthesis(docs, conn, briefs, run_logger=run_logger, repo=repo)

    run_logger.event("run_end", {"ok": True})
    console.print(Rule("[bold green]All five Phase-1 criteria exercised.[/bold green]"))
    console.print(f"[dim]Full transcript: {run_logger.path}[/dim]")
    console.print(f"[dim]Inspect workspace: cd {repo.path} && git log --oneline[/dim]")


if __name__ == "__main__":
    main()
