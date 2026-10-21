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

There is one support bundle per benchmark recipe. These files are hidden from
the model prompt but intentionally available to the local evaluator. Removing
them does not make the benchmark “cleaner”; it makes canonical evaluation
incomplete or changes the metric contract.

