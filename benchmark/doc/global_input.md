# Input-Conditioned Global

Input-Conditioned Global is the runtime-input ablation in Section 4, Table 4.
It receives the Global task specification plus the concrete public runtime
input for the current variant, then generates a complete workflow before
execution. It observes no intermediate tool results or execution feedback.
Each variant has its own independently generated workflow.

The workflow serialization, validator, tool interfaces, executor, scorer,
and model generation settings are shared with Global. The supplied runtime
input has the same representation as Step-by-Step's initial input.
Reference workflows, hidden connector state, fault settings, and evaluation
scores remain outside the model prompt.

```bash
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name input-conditioned --backend simulated \
  --model compat:my-served-model --modes global_input --variants all
```

Configure the model endpoint as described in the
[evaluation guide](../README.md#run-an-evaluation). Add `--ids 64112882`
for a sample run. Results are written under
`benchmark/outputs/full_eval/input-conditioned/<model>/global_input/`.

Across the six models in Table 4, adding runtime inputs changes Global
Orchestration Accuracy by −0.18 percentage points on average. This comparison
still varies sequential decision making and intermediate execution information.
The aggregate results are in [global_input.csv](../results/global_input.csv).
