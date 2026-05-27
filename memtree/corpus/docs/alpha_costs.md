# Lab Alpha — Cost Disclosure Addendum (2026-04)

*[Synthetic content. Fictional lab. For the MemTree demo only.]*

After requests from journalists and several academic groups, we are publishing
finer-grained cost data for our benchmark submissions in Q1 and Q2 of 2026.

## Per-benchmark GPU hours (Q1-2026)

| Benchmark        | GPU hours | Notes                                |
|------------------|-----------|--------------------------------------|
| AgentEval-Pro    | ~180      | End-to-end, single seed              |
| AgentEval-Lite   | ~28       | Subset of 50 tasks                   |
| ToolBench-Hard   | ~95       | 3-seed average                       |

## What this excludes

These numbers exclude:
- Training-data curation
- Pre-training of the base model
- Human review of failed traces (≈ 40 hours of analyst time per benchmark)

## Going forward

From Q3 onward we will report **all-in cost** including human review time, in
dollars rather than GPU hours, to make cross-lab comparison easier.
