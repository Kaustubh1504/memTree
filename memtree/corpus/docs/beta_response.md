# Lab Beta — On Lab Alpha's "Reproducibility" Defence (2026-04)

*[Synthetic content. Fictional lab. For the MemTree demo only.]*

Lab Alpha has argued that DriftBench sacrifices reproducibility for
non-gameability. We disagree on both the framing and the facts.

## Reproducibility ≠ task transparency

Reproducibility means a third party can re-run the evaluation and get the same
score. DriftBench provides exactly this: any submitted agent binary can be
re-run on the same week's task batch by the consortium, and the score will
match within a documented variance band.

What DriftBench does *not* provide is the ability for the agent's authors to
**read** the tasks. That is the property Lab Alpha actually wants. We do not
think it is a property an honest benchmark should provide.

## On end-to-end vs. process

We agree with Lab Gamma that process-supervised evaluation has merit, but we
disagree with their proposed implementation. The grader model should be from
a different model family than the agent under test. This is straightforward to
enforce and Lab Alpha's "circular grading" objection only applies to lazy
implementations.

## Joint statement opportunity

We are open to a joint statement with Lab Alpha and Lab Gamma on minimum
methodology standards for public agent benchmarks. We have circulated a
working draft.
