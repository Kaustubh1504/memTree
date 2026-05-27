# MemTree — Phase 1: MemEx replication

A from-scratch replication of the MemEx code-as-action architecture (Databricks AI Research, May 2026) using HuggingFace's `smolagents`. Phase 1 goal: a working MemEx-style agent with all four primitives, demonstrated on a multi-document research synthesis task. Phase 2 (later) adds git history and dashboard.

Not built on MemEx (internal Databricks framework on `aroll`). Clean-room replication of the public paper.

## Behavioral guidelines

Bias toward caution over speed.

### 1. Think before coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so.
- If something is unclear, stop and ask.

### 2. Simplicity first
**Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" that wasn't requested.
- No error handling for impossible scenarios.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical changes
**Touch only what you must.**
- Don't refactor things that aren't broken.
- Match existing style.
- Remove imports/variables YOUR changes made unused. Don't remove pre-existing dead code unless asked.

### 4. Goal-driven execution
**Define success criteria. Loop until verified.**
For multi-step tasks, state a brief plan with verify steps per step.

## The four MemEx primitives

From the paper, MemEx extends code-as-action with four additions:

1. **Drop-in tools** — existing tool-calling tools become typed Python functions with schemas preserved
2. **Live scope at rollout start** — pre-loaded variables and objects in the agent's namespace before turn 1
3. **Typed `submit()`** — final answer validated against a Pydantic schema
4. **`spawn_agent()`** — spawn sub-agents in parallel, sharing scope, gathering typed results

The same ReAct loop runs MemEx and Tool Calling. Only the action space changes.

## Mapping to smolagents

| Primitive | smolagents has | We build |
|---|---|---|
| Persistent Python kernel | `CodeAgent` + `LocalPythonExecutor` | nothing |
| Drop-in tools | `@tool` decorator | nothing |
| Live scope | `executor.state` dict | helper to inject before `run()` |
| Typed `submit()` | untyped `FinalAnswerTool` | `TypedFinalAnswerTool` with Pydantic validation |
| `spawn_agent()` | nothing native | sync `spawn_agent(task, scope, return_type)`; parallelism via `ThreadPoolExecutor` |

**Async note:** the MemEx paper shows `await asyncio.gather(spawn_agent(...))` directly in code blocks. smolagents' executor doesn't support top-level await cleanly. Phase 1 compromise: `spawn_agent` is sync; parallelism is internal via thread pool. The agent calls it as `reports = [spawn_agent(...) for entity in entities]` and threads run them concurrently. Documented divergence from MemEx.

## Architecture

- `memtree/kernel.py` — wrapper around `CodeAgent` with primitives wired in
- `memtree/primitives/typed_submit.py` — `TypedFinalAnswerTool`, validates against a Pydantic model
- `memtree/primitives/spawn.py` — `spawn_agent(task, scope, return_type)` with thread-pool parallelism
- `memtree/primitives/scope.py` — `inject_scope(agent, **variables)` helper
- `memtree/tools/` — `search_documents.py`, `read_section.py`, `query_db.py`, `save_finding.py`
- `memtree/corpus/` — pre-loaded document corpus + small SQLite DB (the data)
- `examples/research_synthesis.py` — CLI demo exercising all four primitives

No dashboard. No git. Just the agent.

## The demo task

**Multi-document research synthesis** — mirrors the shape of OfficeQA Pro at small scale.

Pre-loaded scope:
- 6-10 markdown documents in a real topic area
- A small SQLite DB with related quantitative data (a few tables, maybe 50-200 rows total)
- The four tools registered as Python functions

Example task (substitute any topic where comparison matters):
> "Compare how three [companies/labs/governments] approached [some topic] over [time period]. Identify common themes, disagreements, and one factual inconsistency between qualitative claims in the documents and quantitative numbers in the database. Return a structured `ComparisonReport`."

What this exercises:
- **Persistent scope:** findings accumulate across turns as the agent reads each document
- **Drop-in tools:** four typed functions callable as Python
- **Pre-loaded scope:** documents and DB available from turn 1
- **Typed submit:** `ComparisonReport(themes: list[Theme], disagreements: list[Disagreement], inconsistency: Inconsistency)`
- **spawn_agent:** one sub-agent per entity being compared, parent aggregates

### Choosing the corpus

Pick a topic where the comparison is genuinely interesting and the data is public. Suggestions:
- Recent agent-eval papers from different research groups (most on-topic for the audience)
- AI lab public statements over a year on a specific issue (safety policy, open-weights, scaling)
- Climate policy positions from different governments
- Public earnings-call segments from companies in the same sector

The corpus should be small enough to bundle in the repo (under a few MB total) but realistic enough that the task isn't trivially solvable from one document.

## Phase 1 success criteria

The demo script must show:

1. **Persistent scope** — turn 1 loads a document; turn 3 references it without reloading
2. **Drop-in tools** — `@tool` functions callable inside code blocks
3. **Pre-loaded scope** — document corpus and DB connection already exist in turn 1
4. **Typed submit** — final answer is a Pydantic-validated `ComparisonReport`; schema violations raise
5. **Parallel sub-agents** — agent spawns N sub-agents (one per entity), gets N typed results, aggregates into the final report

Single command: `python -m examples.research_synthesis` exercises all five.

## Implementation order

1. Vanilla `CodeAgent` with Gemini Flash on a trivial task
2. Verify persistent scope holds across turns (small test)
3. Build the corpus: pick a topic, gather 6-10 markdown files, generate a small related SQLite DB
4. Implement the four tools, each with full type hints and docstrings
5. Inject pre-loaded scope via `agent.python_executor.state[...] = ...` before `run()`
6. `TypedFinalAnswerTool` — subclass smolagents' final answer tool, validate args against a passed Pydantic class
7. `spawn_agent` — function that instantiates sub-`CodeAgent`, injects scope, runs sync, returns typed result. Wrap parallel calls in `ThreadPoolExecutor`.
8. Write `research_synthesis.py` exercising all five criteria

Verify each step works before moving on.

## Dependencies

```toml
[project]
name = "memtree"
requires-python = ">=3.11"
dependencies = [
    "smolagents>=1.0",
    "pandas>=2.0",
    "pydantic>=2.0",
    "rich>=13.0",
]
```

No Streamlit, no GitPython, no pandasql in Phase 1.

## Run

```bash
uv pip install -e .
export GEMINI_API_KEY=...   # https://aistudio.google.com/apikey
python -m examples.research_synthesis
```

Default model: `gemini/gemini-2.5-flash` via smolagents' `LiteLLMModel`.

## Key design decisions

1. **Use smolagents, don't replace it.** No homegrown ReAct loop, executor, or LLM client.
2. **Each primitive is its own module.** Composable, replaceable.
3. **`spawn_agent` is sync with internal thread-pool parallelism.** Documented divergence from MemEx's async API.
4. **No persistence.** Phase 1 is in-memory only.
5. **Demo task mirrors OfficeQA Pro shape.** Multi-document + structured data, not just a CSV.

## Avoid

- Custom Python executor (smolagents has `LocalPythonExecutor`)
- Custom ReAct loop (smolagents has `CodeAgent.run()`)
- Dashboard or git work — Phase 2
- Top-level async support — `ThreadPoolExecutor` is enough for Phase 1
- A single-CSV demo task — too narrow for the architecture
- Premature optimization

## Framing

External pitch: "clean-room replication of the MemEx architecture using open-source smolagents, demoed on a multi-document research synthesis task that mirrors OfficeQA Pro at small scale."

Never "built on MemEx" or "extends MemEx".