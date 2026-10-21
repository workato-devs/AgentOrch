# Evaluation Pipeline

How the code in this bundle turns a model into the released numbers. Two
scoring paths exist; every published table comes from the first.

```
                       ┌──────────────────────────────────────────────┐
 reproduction/cluster/run_*.sbatch │ credentials, decoding caps, env │
                       └───────────────────┬──────────────────────────┘
                                           ▼
                    evaluation/full_eval.py  (canonical entry point)
                    routes dataset env vars, activates a vendored backend,
                    forwards to the canonical evaluator
                                           ▼
        verification/backends/shared/src/task/run_eval.py  (vendored)
        per recipe/variant: run the model, execute on the simulator,
        derive gold at scoring time, adjudicate every metric
                                           ▼
   outputs/full_eval/<run>/<model>/<mode>/{leaderboard.json, results.jsonl,
                                           trajectories.jsonl, artifacts/}
        Each model/mode lane writes its own leaderboard.json directly.
```

## 1. Data the pipeline reads

| Location | Contents | Visibility |
| --- | --- | --- |
| `input/recipes/<id>/` | model-visible prompts for every mode, `PUBLIC_PACKAGE.json` | model |
| `input/manifest.json` | 650 recipes × 3,220 variant ids | harness |
| `groundtruth/recipes/<id>/variant_XX.json` | published per-variant ground truth: reference trace, tool expectations, canonical `final_snapshot` / `outcome_gold_calls` / `structural_return`, terminal contract | evaluator only |
| `verification/seeds/` | private simulator seed state per variant | evaluator only |
| `verification/groundtruth/reference_outputs/` | recorded reference execution bundles (`output.json`) — the canonical gold source | evaluator only |
| `verification/evaluation_support/` | canonical IR, workflow ground truth, scoring contract registry | evaluator only |
| `verification/backends/{shared,simulated,real}/src/` | the vendored evaluator and connector runtime | evaluator only |

The canonical evaluator never reads `groundtruth/recipes/`; it derives gold
from `reference_outputs/` at scoring time (§3). The published ground-truth
files carry that same derived gold for the standalone scorer (§6).

## 2. Launch

Every run goes through one command (the `reproduction/cluster/run_*.sbatch` launchers
only add credentials, decoding caps, and Slurm placement around it):

```bash
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name <run> --state-namespace <ns> --backend simulated \
  --model <model> --modes plan_execute,react --variants all \
  --task-source task_description --tool-surface broad --resume
```

`--modes` also accepts `replan` (§3b). `--max-replans` (default 2) caps
accepted mid-course revisions per row in that mode.

`full_eval.py` validates the run name, points the canonical module's
dataset environment variables at this bundle
(`BENCHMARK_GROUND_TRUTH_DIR` → `verification/groundtruth/reference_outputs`,
package/workflow/critic/registry paths → `input/` and
`verification/evaluation_support/`), activates the requested backend with a
per-run mutable state root
(`outputs/full_eval/<run>/_state_root/<namespace>/` — parallel jobs never
share simulator state), injects all 650 recipe ids, and forwards to
`task.run_eval.main`. `verification/backend.py` is fail-closed: importing
`benchmark`/`metrics`/`task` modules without an activated backend raises.

Model access is uniform across providers (`task/llm_client.py`): vLLM for
local checkpoints (greedy, seed 0, bfloat16), Azure/OpenAI/Anthropic
clients for API models. The main comparison disables hidden reasoning
(`thinking=disabled` / `reasoning_effort=none`); decoding caps are the
executed per-mode settings recorded in the manifest's `output_budget`
block. Retries honor provider rate limits so transport throttling is never
recorded as a model failure.

## 3. What one evaluation row does

For each recipe (Global) or recipe-variant (ReAct), `run_eval`:

1. **Seeds the simulator** from `verification/seeds/` into the run's state
   namespace and builds the tool context (64-tool broad surface; the same
   surface in both modes).
2. **Runs the model.**
   - `plan_execute` (Global View): one variant-blind symbolic
     `WorkflowPlan` per recipe, requested once and frozen under
     `outputs/full_eval/<run>/plans/<model>/<recipe>/initial_plan.json`.
     The cache key covers the prompt and the decoding fingerprint
     (temperature/thinking/effort/max_tokens), so a protocol change never
     silently reuses a stale response; cached `invalid_plan` verdicts are
     re-adjudicated against the current validator from the stored raw
     response (no model is ever resampled). The frozen plan is then
     executed symbolically on every hidden variant.
   - `react`: a per-variant interactive loop — one JSON action per turn,
     the simulator returns the observation, schema violations return a
     structured protocol observation instead of crashing the run. The
     action budget is `B_i = max(G_i+3, ceil(1.5·G_i), S_i+2)` with a hard
     stop at `2·B_i`.
3. **Derives gold at scoring time** from the recorded reference execution:
   `reference_outputs/<recipe>/variant_XX/output.json` → runtime reference
   rebinding → the public gold projection → business-call projection. This
   yields the gold calls, the gold final snapshot, and the structural
   terminal return.
4. **Adjudicates** with `metrics/outcome.evaluate_outcome` plus the trace
   machinery: per-backend exact row-multiset state comparison, transient
   side-effect outputs, normalized terminal comparison (boolean argument
   paths derived from the recipe's public output schema), and the runtime
   trace checks (tool selection / dependency-DAG order / execution /
   semantic required arguments / condition path).

### 3b. Replan mode

`replan` (`task/agents.py:ReplanAgent`) sits between the two poles: the
model produces the same variant-blind frozen initial plan as Global View
(same cache, same validator), but execution is interactive at the plan
level. After every successful non-terminal tool call — and after a tool
`RuntimeError` — the executor shows the model the numbered observation and
asks for exactly one typed JSON object: `{"type": "continue"}` or
`{"type": "replan", "reason": ..., "based_on_observation_step": n,
"remaining_workflow": [...]}`. The executed prefix is immutable; an
accepted `remaining_workflow` replaces only the unexecuted suffix and is
validated by the same symbolic plan schema (`normalize_plan`) as the
initial plan. Reviews are fail-closed: malformed JSON, a wrong-typed
reply, a stale `based_on_observation_step`, a schema-invalid suffix, a
suffix identical to the current one, or a revision past `--max-replans`
all reject the replan (the row continues on the current plan; the raw
reply is stored on the row for audit). Observation messages fold into an
open user turn when one exists, so strict-alternation chat templates
(e.g. gemma) see a valid conversation. `leaderboard.json` adds
`replan_review_count` and `accepted_replan_count`.

### 3c. Engine environments (declared deviations)

All local lanes run the benchmark conda env (vLLM 0.24.0, the standard
engine for every released number) except two models that cannot produce
text on it, which run the isolated `muse` env (vLLM 0.27.1, transformers
5.15) as a declared newer-stack deviation, recorded per lane in
`evaluation/global_react_models.json`:

- **Muse-Glimmer-30B** — architecture absent from vLLM registries through
  0.27.1; native transformers engine (`HF_LOCAL_ENGINE=transformers`) with
  the harmony-channel response split (`HF_RESPONSE_SPLIT_MARKER`).
- **GLM-4.5-Air-FP8 (thinking)** — `enable_thinking` returns empty
  completions on vLLM 0.24.0; plans were regenerated fresh on 0.27.1
  (0.24-era caches quarantined, never mixed).

The lane-level environment knobs (`HF_*` variables read by
`task/llm_client.py`) are set only in the corresponding
`reproduction/cluster/run_thinking_local.sbatch` lanes; the main comparison uses none
of them.

## 4. Metrics

Defined in `doc/metric.md`, computed by
`metrics/aggregate.primary_metrics_for_row`:

- `execution_trace_accuracy` — equal-weight mean of the five binary trace
  checks (a check that is not applicable passes vacuously);
- `side_effect_accuracy` — every outcome check except the terminal
  comparison, plus the transient-event trace;
- `orchestration_accuracy` = `0.5 · trace + 0.5 · side_effect` (primary);
- `terminal_output_accuracy` — normalized terminal comparison;
- `final_accuracy` = `side_effect AND normalized terminal`.

`metrics/aggregate.leaderboard` divides every primary metric by the full
variant count (n = 3,220 per model/mode): a `plan_error` or infra-failed
row scores zero and stays in the denominator. `n_scored`, `error_rate`,
and the bootstrap CIs (clustered by recipe) are reported alongside.

Per model/mode the run directory holds `results.jsonl` (one adjudicated
row per variant — the ground record), `trajectories.jsonl`,
`leaderboard.json` (derived), and `artifacts/<task>.json` (full
input/output/gold/verdict bundles used by audits).

## 5. Per-lane outputs and offline reproduction

The evaluator writes `leaderboard.json` automatically for every model/mode
lane. That file, together with its `results.jsonl`, is the canonical output
for a community evaluation. The paper-level cross-model CSV/Markdown builders
were maintainer reporting utilities and are intentionally not part of the
community benchmark; users may combine lane leaderboards in any analysis
tool without changing benchmark scores.

- `reproduction/offline/rescore_frozen_plans.py` re-scores Global View offline from the
  cached raw plan responses — zero model access; the reproduction path for
  auditing the scoring without API keys.
- `reproduction/offline/recompute_leaderboard.py` rebuilds any `leaderboard.json` from
  its `results.jsonl` (rows are the ground record; leaderboards are
  derived).

## 6. Standalone public scorer (not the released numbers)

`examples/smoke_adapter/cal_acc.py:score(record, ground_truth)` scores one externally
produced run record against the published per-variant ground truth. Its
side-effect / terminal / final verdicts delegate to the same vendored
`metrics.outcome.evaluate_outcome` and consume the exported canonical gold
fields; `reproduction/offline/verify_calacc_parity.py` pins the equivalence to frozen
artifact manifests (2026-08-15 audit: 16,703 archived canonical rows, zero
disagreements). Its execution-trace components come from the published
`tool_expectations` and are a documented simplification of the canonical
trace adjudication, so `evaluation/full_eval.py` remains the only
result-producing implementation.

A dependency-light adapter harness demonstrates the interactive protocol
without the vendored runtime: `examples/smoke_adapter/eval.py` (mode runners and
schema-feedback protocol) + `examples/smoke_adapter/model_corpus.py` (adapter
interface, HF Inference API adapter, run-record schema) +
`examples/smoke_adapter/example_adapter.py` (no-op reference adapter), executing on
`verification/smoke/` — a two-recipe pilot runtime whose full state
fidelity covers the pilot recipe (`64112882`). Use it to integrate a new
model against the protocol; use `full_eval.py` for real evaluations.

## 7. Invariants worth knowing

- **Determinism**: greedy decoding, seed 0, deterministic simulator; a
  rerun with `--resume` never re-queries a model for work already
  checkpointed.
- **Isolation**: mutable simulator state lives under the run's
  `_state_root/<namespace>`; the published `verification/seeds/` are never
  written.
- **Fail-closed scoring**: unknown tools, schema-invalid plans, missing
  frozen-plan artifacts, and transport-exhausted rows are recorded as
  zero-scoring rows, never dropped.
- **One gold**: both scoring paths trace to the same
  `evaluate_outcome` implementation and the same reference-execution gold;
  the ground-truth export is regenerated from that pipeline, not
  hand-maintained.
