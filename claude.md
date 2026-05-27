# MemTree

A code-as-action agent whose code history is a real git repository. Inspired by Databricks' MemEx paper (May 2026), using HuggingFace's `smolagents`. The four MemEx primitives are working (Phase 1, done). Phase 2 adds git-backed turn history and a Streamlit dashboard.

Not built on MemEx (internal Databricks framework on `aroll`). Clean-room replication of the public paper plus original git-history and dashboard layers.

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

## Status

- **Phase 1: COMPLETE.** MemEx primitives working: persistent kernel via smolagents, drop-in tools, live scope at rollout start, typed `submit()`, `spawn_agent()` with thread-pool parallelism. Demo task: multi-document research synthesis.
- **Phase 2: IN PROGRESS.** Git-backed turn history + Streamlit dashboard.

## The four MemEx primitives (Phase 1, done)

1. **Drop-in tools** — handled by smolagents' `@tool` decorator
2. **Live scope at rollout start** — `agent.python_executor.state[...] = ...` before `run()`
3. **Typed `submit()`** — `TypedFinalAnswerTool` validates against a Pydantic model
4. **`spawn_agent()`** — instantiates a sub-`CodeAgent`, injects scope, runs sync, returns typed result. Parallelism via `ThreadPoolExecutor`. Documented divergence from MemEx's async API.

## Phase 2: git history + dashboard

Every code block the agent writes becomes a real git commit in a real workspace repo. The dashboard is a repo browser with commit log, code view, and kernel state.

### Architecture additions

- `memtree/agent.py` — `MemTreeAgent(CodeAgent)` subclass. Overrides `step()` to capture each turn and commit it.
- `memtree/repo.py` — `WorkspaceRepo` wrapper around `GitPython`. Initializes the workspace, appends each turn's code to `notebook.py`, commits with a turn-numbered message, persists tool outputs to `tool_outputs.json`.
- `memtree/replay.py` — `replay(repo, up_to_commit)` rebuilds kernel state in a fresh dict by re-executing `notebook.py` up to the given commit, using cached tool outputs.
- `memtree/primitives/revert.py` — `revert(to_turn, reason)` tool exposed to the agent. Calls `replay`, truncates turn list, creates a new branch from the reverted commit.
- `memtree/tools/cached.py` — `cached_tool(fn, cache)` decorator. Hashes `(name, args)`, returns cached output on replay.
- `app.py` — Streamlit dashboard. Three panels: commit log, code view (with `streamlit-ace`), kernel state summary.

### Workspace layout (created at session start)

```
workspace/
├── .git/                # real git repo
├── notebook.py          # agent's growing code with `# Turn N` markers
├── tool_outputs.json    # cached outputs keyed by hash(tool_name + args)
└── state_summary.json   # variable names, types, shapes — written by agent after each turn
```

### Phase 2 build order

1. **Turn capture.** Override `MemTreeAgent.step()`. Log every captured `Turn` to console. Verify code, stdout, tool outputs all populate. **Print one `memory_step` first to confirm the exact field names smolagents uses on your installed version.**
2. **Git commits.** After each captured turn, append to `notebook.py` and create a git commit. Run a full demo, open the workspace folder, `git log` shows one commit per turn.
3. **Replay + revert.** Implement `replay(repo, sha)` using cached tool outputs. Expose `revert` tool to the agent. Test by triggering a manual revert mid-rollout and confirming the kernel state matches.
4. **Streamlit dashboard.** Read-only first: commit log + notebook contents from the selected commit. Add the "Checkout selected commit" button last.

Verify each step works before moving to the next.

## Key design decisions (do not relitigate)

1. **Real git, not a homegrown log.** `GitPython`. Free diffs, log, checkout, branches.
2. **One file accumulates the agent's code.** `notebook.py` grows turn-by-turn with `# Turn N: <summary>` markers.
3. **Tool outputs cached alongside code.** `tool_outputs.json` is committed with each turn. Replay is deterministic and cheap.
4. **Kernel state is rebuilt, not snapshotted.** No `dill`, no deepcopy. Replay from turn 0 forward in a fresh kernel.
5. **Turn 0 is the starter scratchpad, locked.** Initial commit contains the corpus + tools. Cannot revert past.
6. **Use smolagents.** No homegrown ReAct loop, LLM client, or executor.
7. **`spawn_agent` is sync with internal thread-pool parallelism.** Documented divergence from MemEx's `asyncio.gather`.
8. **Dashboard and agent are decoupled via the filesystem.** Agent writes to git + state_summary.json. Dashboard polls the workspace every 2 seconds. No IPC needed.

## Dependencies

```toml
[project]
name = "memtree"
requires-python = ">=3.11"
dependencies = [
    "smolagents>=1.0",
    "litellm>=1.40",
    "GitPython>=3.1",
    "streamlit>=1.30",
    "streamlit-ace>=0.1.1",
    "streamlit-autorefresh>=1.0",
    "pandas>=2.0",
    "pydantic>=2.0",
    "rich>=13.0",
]
```

Do not add: `dill`, `cloudpickle`, `IPython`, `langchain`, `crewai`, `langgraph`.

Requires `git` installed on the system.

## Run

```bash
uv pip install -e .

# Model: qwen3.7-max via DashScope International (1M free tokens on signup)
export DASHSCOPE_API_KEY=sk-...
export QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
export QWEN_MODEL=qwen3.7-max

# Phase 1 CLI demo (no dashboard)
python -m examples.research_synthesis

# Phase 2 dashboard
streamlit run app.py
```

Model config:

```python
model = LiteLLMModel(
    model_id=f"openai/{os.getenv('QWEN_MODEL')}",
    api_base=os.getenv("QWEN_BASE_URL"),
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)
```

Pass `extra_body={"enable_thinking": False}` if smolagents exposes it — qwen3.7-max is a reasoning model and enabling thinking burns tokens fast.

## Demo story (Phase 2)

1. Dashboard open. Empty commit log on the left. Notebook viewer in the center. Kernel state panel on the right.
2. User submits the research-synthesis prompt.
3. Agent works: turn 1, 2, 3 commits populate live as the agent writes code. Right panel shows variables appearing in scope.
4. Turn N: agent makes a recoverable mistake (drops the wrong column, mutates a DataFrame in place). Kernel state panel shows the corrupted variable.
5. Recovery path (either):
   - Agent calls `revert(to_turn=N-1, reason="dropped wrong column")` and retries — visible as a new branch in the commit log
   - User clicks the turn N-1 commit, hits "Checkout selected commit," nudges the agent forward
6. Agent retries, succeeds.
7. User clicks any past commit, sees the exact code at that point. Optionally clicks "Diff vs HEAD" to compare turns.

Whole thing in under 60 seconds. The repo-browser visual is the hook.

## Avoid

- State snapshotting via `dill`, `copy.deepcopy` of kernel globals, or anything similar
- Sandboxing (`RestrictedPython`, subprocess isolation)
- Async, locking, concurrency primitives (except the `ThreadPoolExecutor` inside `spawn_agent`)
- Multi-file workspace — one `notebook.py` is enough
- Agent-driven git branching — branching happens via dashboard `edit_turn` only
- Premature abstraction — one file per layer until something forces a split
- Tests for dashboard code; cover replay logic and turn diff logic only

## Framing

External pitch: "code-as-action agent inspired by MemEx, with the agent's code blocks committed to a real git repo. Dashboard is a repo browser. Checkout any commit to rebuild kernel state via replay. Phase 1 replicates the MemEx primitives on smolagents; Phase 2 adds the history layer."

Never "built on MemEx" or "extends MemEx".