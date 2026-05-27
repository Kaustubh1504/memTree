# Lab Gamma — Evaluation Cost Comparison (2026-03)

*[Synthetic content. Fictional lab. For the MemTree demo only.]*

We track end-to-end evaluation cost for every benchmark we run, including the
process-grading pass.

## Q1-2026 published runs

| Benchmark        | Agent GPU hours | Grader GPU hours | Total |
|------------------|-----------------|------------------|-------|
| AgentEval-Pro    | 165             | 110              | 275   |
| ToolBench-Hard   | 90              | 60               | 150   |
| Internal-Eval-v3 | 220             | 140              | 360   |

## Comparison with peers

- Lab Alpha reports ~180 GPU-hours for AgentEval-Pro, which we believe excludes
  the human-review pass.
- Lab Beta reports ~210 GPU-hours for DriftBench plus ~45 hours of grader
  compute. We have not yet run our system on DriftBench.

## Recommendation

We recommend that all public benchmark submissions disclose **agent compute**,
**grader compute** (if any), and **human-review hours**, separately.
