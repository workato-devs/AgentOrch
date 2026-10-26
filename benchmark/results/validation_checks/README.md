# Simulator fidelity and workflow characteristics

These records support Appendices D and E.

| Files | Contents |
| --- | --- |
| `simulator_replay_fidelity.csv` / `.md` | Agreement from replaying recorded real-backend reference actions in simulation. |
| `global_vs_step_stratified.csv` / `.md` | Global versus Step-by-Step by workflow size, application count, control flow, nesting depth, and fault injection. |
| `sop_structural_features.csv` | Reference-workflow features for each SOP. |
| `variant_features.csv` | Runtime-variant features used in the subgroup analysis. |

Reference-action replay uses the same tool interfaces, variant state, and
scorer as model-generated runs. It is available with:

```bash
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name reference-actions --backend simulated --model scripted-gold \
  --modes react --variants all --scripted-selftest
```

The fidelity comparison concerns trace components and side effects. SOP
features count tool-call nodes, application families, conditional branches,
loops, try/catch regions, and maximum nesting depth. Runtime fault injection
is a variant-level feature. Failed model executions remain in the subgroup
denominators at zero accuracy.
