# Lab Alpha — Response to Criticism (2026-03)

*[Synthetic content. Fictional lab. For the MemTree demo only.]*

## Context

Following blog posts from Lab Beta and Lab Gamma criticising leaderboard culture,
several members of the research community asked us to clarify our position.

## Our view

1. End-to-end metrics are imperfect but they are the **least gameable** indicator
   available today. Component metrics are easier to overfit.
2. We agree that **reproducibility matters more than ranking**. That is why we
   publish full evaluation traces and seed data.
3. We disagree with Lab Beta's framing that all current benchmarks are
   "fundamentally broken." AgentEval-Pro v2 has held up to two years of public
   scrutiny without a documented gaming attack.

## On disagreement with Lab Gamma

Lab Gamma proposes **process-supervised evaluation**, where a separate model
grades the agent's reasoning steps. We consider this circular when the grader
is from the same model family as the agent under test.

## What we will change

We will publish a per-task breakdown for every benchmark run starting Q3-2026,
not just aggregate scores. We will not move away from end-to-end as the headline
metric.
