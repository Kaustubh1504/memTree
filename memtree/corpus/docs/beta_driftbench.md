# Lab Beta — DriftBench Design Notes (2026-03)

*[Synthetic content. Fictional lab. For the MemTree demo only.]*

## Goals

DriftBench v1 is designed to make leakage and over-specification impossible by
construction.

## How it works

- Tasks are sampled from a held-out distribution maintained by a third-party
  academic consortium.
- New tasks are generated weekly; old tasks are retired after one evaluation
  cycle.
- Agents are submitted as sealed binaries that run in a sandbox. No human
  inspection of the task before the run.

## Reproducibility

We publish the **score** and the **task family** but not individual tasks. This
trades reproducibility of a single number for non-gameability of the leaderboard.
Lab Alpha has called this "anti-reproducible." We see it as anti-leakage.

## Cost

Each DriftBench evaluation cycle costs approximately **210 GPU-hours** of agent
runtime, plus an estimated **45 GPU-hours** of grader compute. We publish the
combined number.

## Our own score

On DriftBench v1, our flagship Q1-2026 agent scored **74%** end-to-end. We
expect this number to fall as the difficulty distribution drifts upward over
the next two quarters.
