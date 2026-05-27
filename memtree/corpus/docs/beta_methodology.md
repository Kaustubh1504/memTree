# Lab Beta — Why Current Agent Benchmarks Are Broken (2026-02)

*[Synthetic content. Fictional lab. For the MemTree demo only.]*

## Claim

Every major public agent benchmark in 2026 — including AgentEval-Pro, ToolBench,
and WebArena — measures something other than agent quality. We argue they are
**fundamentally broken** in their current form.

## The three failures

1. **Leakage.** Benchmark tasks appear in pre-training corpora. We have found
   verbatim copies of 31 of the 200 AgentEval-Pro tasks in three open web crawls.
2. **Over-specification.** Tasks bundle so much context that the agent's job is
   reduced to instruction-following, not autonomous problem solving.
3. **Score saturation.** Top labs are within 2 percentage points of each other.
   The metric no longer separates capability from luck.

## What we propose

We are launching **DriftBench** — a continuously regenerated benchmark whose
tasks are sampled weekly from a held-out distribution and never published.
Labs submit a sealed agent binary; we score it; we publish the score.

## Headline result on our own system

On DriftBench v1, our Q1-2026 system scored **74%** — far below AgentEval-Pro
results from any lab including our own, which we read as evidence that
saturation on public benchmarks is a measurement artefact.
