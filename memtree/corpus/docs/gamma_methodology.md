# Lab Gamma — Process-Supervised Agent Evaluation (2026-02)

*[Synthetic content. Fictional lab. For the MemTree demo only.]*

## Thesis

Outcome-only evaluation is too coarse. Two agents that both complete a task can
differ enormously in **how** they got there — number of tool calls, recovered
errors, hallucinated facts that happened not to affect the final answer. We
propose **process supervision**: scoring the trajectory, not just the endpoint.

## The protocol

1. Agent runs end-to-end on a task. The final answer is recorded.
2. The full trace is replayed to a separate **grader** model from a different
   model family.
3. The grader assigns scores across five axes: planning coherence, tool
   accuracy, error recovery, factual grounding, efficiency.
4. The headline score is the **minimum** across the five axes, not the mean.
   A weak link drags the score down.

## Headline result on AgentEval-Pro

Our flagship Q1-2026 system, scored under our own protocol, achieved **88%** on
AgentEval-Pro — slightly below Lab Alpha's 92% end-to-end number, but our
process score is **76%**, exposing a weakness in error recovery that the
endpoint metric hides.

## Response to "circular grading"

Lab Alpha argued process supervision is circular when the grader is from the
same model family. We agree, which is why our protocol requires a different
family. Lab Alpha's objection assumes a worst-case implementation we do not
endorse.
