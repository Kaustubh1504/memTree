# Lab Alpha — Agent Evaluation Methodology (2026-01)

*[Synthetic content. Fictional lab. For the MemTree demo only.]*

## Position

Lab Alpha argues that **end-to-end task completion** is the only metric that matters
for agent evaluation. Component-level scores (planning quality, tool-call accuracy)
are noisy proxies that diverge from real user outcomes.

## Headline result

On the public **AgentEval-Pro** benchmark, our Q1-2026 system completed **92%** of
tasks without human intervention — the highest published score by a public lab at
release time. Internal A/B testing across 412 production users confirmed the gain.

## Stance on disclosure

We publish full traces for every benchmark run. We do **not** publish per-step
reasoning unless it would not enable model-extraction attacks. We believe the
field is over-indexed on leaderboards and under-indexed on reproducibility.

## Cost transparency

Each AgentEval-Pro run costs roughly **180 GPU-hours** end to end. We do not
amortise infrastructure cost across benchmark runs in our published numbers.
