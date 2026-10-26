# Canonical evaluation support

This directory is evaluator data, not result-formatting code. It is required
by `evaluation.full_eval` and must remain next to the other verification
fixtures.

| Path | Role in canonical scoring |
| --- | --- |
| `canonical_ir/` | normalized per-recipe representation used for trace and control-flow adjudication |
| `workflow_groundtruth/` | frozen reference workflow plans used for plan fidelity and scripted integrity checks |
| `critic/` | per-recipe semantic constraints used by the evaluator |
| `scoring_contract_registry.json` | registry that selects the scoring contract for each recipe |

There is one support bundle per benchmark recipe. The local evaluator uses
these files for reference execution and scoring; they are not included in
the model prompt.
