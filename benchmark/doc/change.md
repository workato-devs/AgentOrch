# Change log — evaluation-contract fixes for the published comparison

> Historical-path note: entries preserve filenames as they existed when each
> change was recorded. In the community layout, canonical execution remains in
> `evaluation/`; optional experiments are in `experiments/`; audit tools are in
> `reproduction/offline/`; and Slurm launchers are in `reproduction/cluster/`.
> Paper-only table builders mentioned below are intentionally not shipped.

Date: 2026-08-14. All changes below were made together, after an audit of the
Global View (plan_execute) failure modes across the 11-model comparison, and
before producing the canonical result set `outputs/full_eval/global-react-final-20260814`.
Every change is deterministic and model-blind: nothing consults ground truth,
variant state, or any model-specific signal.

## Why

The audit found that 97–100% of Global View "errors" for every model were
plan **serialization** rejections, not orchestration failures. Three concrete
contract defects caused them, and one metric in the leaderboard did not match
its published definition:

1. The plan validator accepted JSON-shaped shorthand for containers (a bare
   array/object where a symbolic value is expected) but rejected bare scalar
   leaves, so a plan writing `"limit": 150` instead of
   `{"kind": "literal", "value": 150}` was discarded whole. 339/650 of
   claude-opus-5's plans (and 244/650 of gpt-4o's) failed for this reason
   alone while being otherwise well-formed.
2. The validator required every `if` to carry an explicit `else` array and
   every `try` an explicit `catch` (`plan[0].else must be an array` when the
   key was omitted or null), rejecting complete programs for a missing `[]`.
3. Frozen-plan caches rejected under the old validator were terminal: a rerun
   returned the cached `invalid_plan` verdict without re-checking the stored
   raw response against the current contract.
4. The leaderboard field `orchestration_rate` was **not** the orchestration
   accuracy defined in `doc/metric.md` — `run_eval.py` set
   `orchestration_pass = canonical_trace_pass` (a strict exact-trace verdict,
   duplicating `strict_rate`), so the reported "orchestration" number was a
   different, far harsher metric than the documented
   `0.5 × execution_trace + 0.5 × side_effect`.

## Code changes

### `verification/backends/shared/src/task/workflow_plan.py`

- `_normalize_value` now wraps a bare JSON scalar leaf as
  `{"kind": "literal", "value": ...}`. In this grammar every reference and
  expression form is an object, so a non-container leaf can only mean a
  literal; the wrap is deterministic and repairs no semantic choice. This
  extends the existing container shorthand (bare arrays/objects) to leaves.
- `normalize_plan`'s region parser treats an omitted or explicit-`null`
  region as the empty region (an `if` without an `else`, a `try` without a
  `catch`), and accepts a single node object where a region array is
  expected (wrapped to a one-element array). The top-level plan is still
  required to be a non-empty array, and all genuine grammar errors (unknown
  tools, missing required arguments, duplicate bindings, unknown input
  paths) are still rejected.

### `verification/backends/shared/src/task/run_eval.py`

- Frozen-plan cache loading re-adjudicates `invalid_plan` entries: if the
  stored `raw_response` parses and validates under the **current** validator,
  the entry is upgraded in place (`validation_reclassified` +
  `syntax_normalized_from_raw` are set) instead of replaying a stale verdict.
  This mirrors the pre-existing downgrade path for caches that an older
  validator accepted but the current contract rejects. No model is ever
  resampled.
- Removed the misleading row field `orchestration_pass` (it duplicated
  `canonical_trace_pass`, which remains). Result rows now carry the
  `doc/metric.md` metrics per row: `execution_trace_accuracy`,
  `side_effect_accuracy`, `orchestration_accuracy`,
  `terminal_output_accuracy`, `final_accuracy`, computed from the same
  component verdicts the leaderboard aggregates.

### `verification/backends/shared/src/metrics/aggregate.py`

- New `primary_metrics_for_row()` implements the `doc/metric.md` formulas
  from the row-level component verdicts: execution-trace accuracy is the
  equal-weight mean of the five binary checks (tool selection, order,
  execution, required semantic arguments, control path; a check that is not
  applicable passes vacuously, matching `evaluation/cal_acc.py`);
  orchestration accuracy is `0.5 × trace + 0.5 × side_effect`; final
  accuracy is `side_effect AND normalized terminal output`.
- `leaderboard()` now reports the three primary metrics
  (`orchestration_accuracy`, `side_effect_accuracy`, `final_accuracy`) with
  cluster-bootstrap 95% CIs for orchestration and final, plus the two
  diagnostics (`execution_trace_accuracy`, `terminal_output_accuracy`).
  Failed rows stay in the denominator at zero. The former
  `orchestration_pass` / `orchestration_rate` fields were removed — they
  duplicated `strict_pass` / `strict_rate`, which remain available as the
  strict exact-trace diagnostic.

### `evaluation/summarize_scale_comparison.py`

- The comparison now reports the three primary metrics plus `error_rate`
  (columns `*_orchestration_accuracy`, `*_final_accuracy`,
  `*_side_effect_accuracy`); the previous `outcome/strict/orchestration_rate`
  columns are gone with the fields they read.

### New scripts

- `scripts/rescore_frozen_plans.py` — offline Global View re-scoring: replays
  the cached frozen-plan artifacts (raw model responses) through the
  canonical evaluator with zero model access, re-adjudicating each response
  under the current validator and executing surviving plans on all hidden
  variants with the simulated backend. Used to produce the canonical run
  below; also the reproduction path for anyone auditing the scoring without
  API keys.
- `scripts/recompute_leaderboard.py` — rebuilds a `leaderboard.json` from an
  existing `results.jsonl` (rows are the ground record; the leaderboard is
  derived), preserving the run-protocol `meta` block. Used to refresh the
  ReAct leaderboards after the metric change without re-running anything.

### Tests

- `tests/test_plan_shorthand_and_metrics.py` pins the shorthand contract
  (bare scalars ≡ explicit literals, omitted/null regions ≡ `[]`,
  single-node regions, idempotent normalization, genuine errors still fail)
  and the primary-metric formulas (per-row and leaderboard aggregation,
  errored rows scored zero in the denominator).
- `tests/test_comparison_tools.py` updated to the new comparison columns.

## What deliberately did **not** change

- **Prompts are byte-identical.** The Global/Local/ReAct prompt text and the
  planner prompt hash are untouched, so every frozen-plan cache key stays
  valid and no model was re-queried. All 11 models are scored from the very
  same raw responses recorded in the original runs.
- **The executed decoding caps** are kept. The one-shot Global plan is
  capped at 4,096 visible tokens for every model; responses truncated under
  that cap (54/650 claude-opus-5 recipes, 6 gpt-4o, and a larger share for
  the weaker models) remain plan errors. ReAct turns stop at the first
  complete top-level JSON object; the per-turn truncation guard is 4,096
  tokens for API models and 8,192 hard / 1,024 soft for local checkpoints —
  so the two modes do **not** share one uniform output budget, and the
  paper must quote the executed per-mode settings (see `doc/exp.md`,
  "Reproducibility and current audit notes"). Each cap is applied
  identically to every model within its lane, so within-figure comparisons
  are unaffected.
- **Ground truth, seeds, simulator, and the ReAct protocol** are untouched.
  ReAct numbers change only through the leaderboard recomputation (the same
  rows aggregated under the corrected metric definitions).
- **Genuine model failures still fail**: unparseable JSON, unknown tools,
  missing required arguments, duplicate bindings, and wrong-typed literals
  are rejected exactly as before, and every executed plan is still scored by
  the unchanged simulator and scorer.

## Canonical result set

`outputs/full_eval/global-react-final-20260814` — one directory, all 11
models:

- `plans/<model>/` — the original frozen-plan artifacts (raw responses and
  cache keys copied verbatim from
  `api-3models-clean-sim-global-react-20260814` and
  `instruct-scale-8models-vllm-20260813`), upgraded in place by cache
  re-adjudication where the current validator accepts them.
- `<model>/plan_execute/` — produced by
  `python -m scripts.rescore_frozen_plans --run-name global-react-final-20260814 --model <id>`
  for each model.
- `<model>/react/` — result rows copied verbatim from the source runs, with
  leaderboards recomputed by `scripts/recompute_leaderboard.py`.
- `comparison*.{json,csv,md}` — `evaluation/summarize_scale_comparison.py`
  over this single run.

Reported metrics: **orchestration accuracy** (primary), **final accuracy**,
**side-effect accuracy**, per `doc/metric.md`.

Pending at the time of writing: the gpt-4o and gpt-35-turbo ReAct workers
and the gpt-35-turbo frozen-plan repair (one recipe lost to an Azure
transport failure) were still running on Slurm. Once they finish, copy their
react results into the canonical run, recompute those two leaderboards, and
re-run the summarize command with `--expected-n 3220 --expected-plans 650
--expected-models 11`.

## Repository cleanup

The publishable bundle keeps only continuously useful files. Superseded
material was moved (not deleted) to the repository-level `local_archive/` directory (not part of this bundle),
which is git-ignored and outside the bundle:

- Diagnostic/preflight/scripted-selftest run directories and the pre-isolation
  API attempts (`api-3models-global-react-20260814`,
  `api-opus5-direct-global-react-20260814`, `api-opus-*-diagnostic`,
  `api-*-preflight*`, `instruct-scale-*preflight*/check*`, `scripted-*`,
  `inspect*`, `structural-selftest`, and the failed
  `api-gpt35-plan-repair-20260814`).
- The 32B ReAct shard/rescue working directories (their contents were merged
  and validated into `instruct-scale-8models-vllm-20260813`).
- The early single-model `llama-local-*` runs and their Slurm entry points
  (`run_local_llama_react.sbatch`, `run_local_llama_plan_views.sbatch`),
  superseded by the instruct-scale comparison pipeline.
- Completed Slurm job logs (logs of still-active jobs stay in place).

Retained under `outputs/full_eval/`: the two generation runs
(`instruct-scale-8models-vllm-20260813`,
`api-3models-clean-sim-global-react-20260814` — the provenance for every raw
model response) and the canonical `global-react-final-20260814`.

`scripts/finalize_global_react_comparison.sbatch` was rewritten for the
canonical single-run flow (copy ReAct results in, recompute leaderboards,
re-score gpt-35 after its plan repair, summarize); the previously queued
finalize job carrying the old script copy was cancelled and resubmitted with
the same dependencies.

## Scale-extension campaign (30+ models, three size tiers)

Date: 2026-08-14/15. The comparison grows from 11 to 30 models (31 once the
pending newest-GPT deployment key is provided), clustered into size tiers —
small (≤4B), medium (4–15B), large (>15B, plus frontier API models assigned
by vendor capability tier). The full roster with pinned revisions, tiers,
per-model runtime flags, and run names is
`evaluation/global_react_models.json` (schema v2), which replaces
`global_react_11models.json`; `tests/test_comparison_tools.py` cross-checks
it against every launcher script.

Model selection was constrained by the benchmark's context requirement
(prompts are pinned at 122,880 input tokens inside a 131,072-token window;
the Global View user prompt alone has a median of ~49K and a maximum of
~107K tokens), so every added checkpoint natively supports a 128K-class
context or has an official YaRN recipe (Qwen2.5). Families whose instruct
checkpoints top out at 4K–32K context (Gemma 2, OLMo 2, SmolLM2, Phi-4,
Yi-1.5, Ministral-8B, Mistral-Small-2501) are excluded for that reason, and
long-context relatives were substituted where they exist (Gemma 3,
Mistral-NeMo/Small-3.1, Phi-3 128k variants).

New launchers, same protocol as the original arrays (frozen plan → all
variants → ReAct, simulated backend, resumable checkpoints, and the same
executed decoding caps: 4,096 visible tokens for the one-shot plan, the
usual per-turn ReAct truncation guards):

- `scripts/run_scale_extension.sbatch` — 15 single-GPU checkpoints
  (2.5B–32B; granite, Qwen2.5/Qwen3-2507, Phi-3/3.5, gemma-3, GLM-4,
  Mistral-NeMo/Small-3.1, Command R).
- `scripts/run_scale_extension_70b.sbatch` — Llama-3.1-70B, Llama-3.3-70B,
  Qwen2.5-72B on two H200s each.
- `scripts/download_scale_extension_models.sh` — pre-downloads every planned
  checkpoint at its pinned revision (evaluators run offline).
- `run_api_model_comparison.sbatch` index 3 — `claude-haiku-4-5` under the
  identical Anthropic protocol (thinking disabled, 4,096 visible tokens),
  submitted into `api-ext-20260815`.

Runtime support added to `task/llm_client.py` for the wider roster, all
model-blind:

- `_render_chat_prompt`: chat templates that reject a `system` role
  (e.g. Gemma) receive the system text folded into the first user turn —
  those models' own documented convention; identical information either way.
- `HF_TRUST_REMOTE_CODE` (per-model, set in the launcher) for checkpoints
  whose tokenizer/config ships as repository code (GLM-4 chat, Phi-3-small).
- `VLLM_TENSOR_PARALLEL` for sharding 70B-class checkpoints across GPUs.

`evaluation/summarize_scale_comparison.py` now attaches each model's tier
from the manifest, emits `tier_summary.json` plus a tier-means table in
`comparison.md` (equal model weight within a tier), and rounds deltas.

Gated repositories requiring a one-time license acceptance on
huggingface.co before their downloads succeed: `google/gemma-3-*-it`,
`meta-llama/Llama-3.3-70B-Instruct`, `CohereForAI/c4ai-command-r-08-2024`.

## Test-time reasoning ablation (claude-opus-5 with thinking)

The main comparison's protocol removes hidden test-time compute: every
model — local instruct checkpoints and API models alike — answers directly,
with no hidden reasoning channel (`thinking=disabled` for Claude,
`reasoning_effort=none` for the GPT-5 family) and a 4,096-visible-token cap
on the one-shot Global plan (ReAct turns use the per-mode truncation guards
recorded in the manifest's `output_budget`). That keeps model scale the
main independent variable, which is what the scale-tier claim requires; it
also means the headline Opus rows understate what the model can do with
reasoning enabled.

`scripts/run_opus_thinking_ablation.sbatch` runs the complementary
ablation: `claude-opus-5` under the byte-identical prompts and scoring,
with `thinking=adaptive`, `effort=high`, and `max_tokens=16384` (thinking
tokens share the Anthropic `max_tokens` budget, so the cap is raised to
preserve the usual visible-output headroom; only `text` content blocks
are parsed and scored, thinking blocks are never seen by the harness).
Results land in `outputs/full_eval/opus-thinking-20260815/` with their own
state namespace and frozen-plan cache keys (the decoding fingerprint
includes thinking/effort/max_tokens), so the canonical
`global-react-final-20260814` result set is never touched. The run is
reported separately as "does test-time reasoning substitute for scale in
Global View", never mixed into the main leaderboard. The manifest records
it under `ablation_runs`.

## Pre-release audit fixes (2026-08-15)

An external audit of the release candidate surfaced six issues. All are
resolved; none changes any published number (the canonical scorer's output
is byte-identical before and after — see the fixture check below).

**One side-effect scorer, not two.** `evaluation/cal_acc.py` previously
carried its own effects/state/terminal logic (READ_ONLY_TOOLS heuristics,
subset state containment) that could disagree with the canonical
`metrics.outcome.evaluate_outcome` used by `evaluation/full_eval.py`. The
public scorer now delegates: it activates the vendored simulated backend,
projects the trajectory into canonical outcome calls (control pseudo-tools
and structural authoring-layer returns stripped; a symbolic plan-level
`return` stop contributes `synthetic_return_call`), derives terminal
boolean paths from the published `terminal_contract` via the shared
`public_output_boolean_argument_paths`, and applies the same side-effect /
terminal / final verdict rules as `run_eval.py`. The helpers it needs
(`STRUCTURAL_RETURN_TOOLS`, `synthetic_return_call`,
`public_output_boolean_argument_paths`) moved into `metrics/outcome.py`;
`run_eval.py`'s private copies are now thin wrappers over them. Validation:
`test_every_reference_fixture_scores_perfectly` replays all 3,220 reference
fixtures through the unified path and requires a perfect score on each;
the full public suite (29 tests) and the internal suite (93 tests) pass.

  Scope caveat (measured, not assumed): replaying 6,228 canonical rows
  (claude-opus-5 react + plan_execute, gpt-4o plan_execute) through
  `cal_acc.score` against the stored `run_eval` verdicts agrees on
  side-effect for 99.4% of rows and on terminal-normalized for 88.3%. The
  residual disagreement is a **ground-truth export gap, not divergent
  scoring code**: the public `final_snapshot` strips rows the reference
  agent created at runtime (`_created_by: "agent"`), and variants whose
  gold output is a structural recipe-function return export
  `terminal_result: null`, so `cal_acc` cannot check expectations the
  public files do not carry. Until `scripts/build_pilot.py` exports the
  full internal expectations, `evaluation/full_eval.py` with the vendored
  evaluator remains the only result-producing implementation and
  `cal_acc.py` must not be cited as one (see `doc/exp.md` audit notes).

**Finalizer dependency repaired.** Array element 25820_2 (the opus lane,
already complete in the canonical run) exited on a corrupt frozen-plan
cache entry for recipe 88017708 (`plans/claude-opus-5/88017708/
initial_plan.json` differed from its own re-adjudicated validation). The
file was restored from the canonical run's copy — same `cache_key`, same
`raw_response`, previous bytes kept as `initial_plan.json.pre_repair_backup`
— and the finalize job's Slurm dependency was retargeted to the elements
that still run (`afterok:25820_0:25820_1,afterok:25827_1,afterok:25828`),
so the 11-model canonical summary is produced automatically when the two
GPT ReAct lanes finish.

**Manifest tells the truth.** `evaluation/global_react_models.json` no
longer marks gpt-4o / gpt-35-turbo `complete`; they are `react_running`
with a note that plan_execute is complete and ReAct resumes under job
25820, folded in by the finalize job. The opus thinking run is declared
under `ablation_runs`, never in the main roster.

**Public and internal evaluators re-synced.** The vendored
`verification/backends/shared/src` copies of `task/workflow_plan.py`,
`task/run_eval.py`, `task/llm_client.py`, `metrics/aggregate.py`, and
`metrics/outcome.py` are again byte-identical with `benchmark/shared/src`
(the internal tree had older chat-template and boolean-path code; the
public copies were authoritative and were synced inward).

**Credentials out of the bundle.** The real `.env` moved from
`benchmark/.env` to the repo root (mode 600, gitignored); every
launcher sources the root file. No credential file remains anywhere under
`benchmark/`.

**Auditable commit.** The published bundle is committed as a single
release commit. The 14 GB HuggingFace jsonl export is gitignored — it is
regenerated from `input/` by `scripts/export_hf_dataset.py` and
distributed through the HF Hub — as are `outputs/` and all secrets.

**Thinking-ablation result (job 25833, completed 2026-08-15, 9h37m).**
Full 3,220-variant sweep, byte-identical prompts and scoring:

| mode | orchestration | side-effect | final | plan_error excluded |
|---|---|---|---|---|
| Global, thinking disabled (canonical) | 0.4644 | 0.5016 | 0.2354 | 617 (19.2%) |
| Global, thinking adaptive/high | 0.5988 | 0.6398 | 0.3233 | 200 (6.2%) |
| ReAct, thinking disabled (canonical) | 0.6352 | 0.7009 | 0.4714 | 0 |
| ReAct, thinking adaptive/high | 0.6841 | 0.7457 | 0.5531 | 0 |

Reasoning helps Global far more than ReAct (+13.4 vs +4.9 orchestration
points) and cuts frozen-plan generation failures three-fold, narrowing the
Global-vs-ReAct gap from 17.1 to 8.5 points — test-time reasoning partially
substitutes for the interaction loop, but does not close the gap. The
means are directly comparable: `plan_error` rows score zero and stay in
the fixed 3,220-variant denominator (`aggregate.leaderboard` divides
primary metrics by `n`, not `n_scored`), so the error-rate reduction is
itself part of the orchestration gain, not a population shift.

## Documentation accuracy pass (2026-08-15, follow-up)

Two review findings against `doc/exp.md` were verified and folded into the
bundle's own claims:

- **No uniform output budget across modes.** Every place that described a
  single "4,096-token visible-output budget" (README, this changelog, the
  launcher comment, and the manifest's `visible_output_budget` scalar) now
  states the executed settings: 4,096 visible tokens for the one-shot
  Global plan on every model; ReAct turns stop at the first complete
  top-level JSON object under per-turn truncation guards of 8,192 hard /
  1,024 soft tokens (local checkpoints) or 4,096 tokens per request (API
  models). The manifest scalar was replaced by an `output_budget` block
  recording exactly these caps.
- **`cal_acc.py` is not the result-producing scorer.** A 6,228-row replay
  of canonical trajectories through `cal_acc.score` against the stored
  `run_eval` verdicts measured 99.4% side-effect and 88.3%
  terminal-normalized agreement; the residual gap is the ground-truth
  export (agent-created snapshot rows stripped; structural-return
  terminals exported as `terminal_result: null`), not divergent verdict
  code. The `cal_acc` docstring, the scorer-unification entry above, and
  the `doc/exp.md` audit notes now say this explicitly: released numbers
  come from `evaluation/full_eval.py` with the vendored evaluator only.

## Ground-truth export closes the scorer-parity gap (2026-08-15)

The residual `cal_acc` divergence documented above (99.4% side-effect /
88.3% terminal agreement, caused by the export rather than the verdict
code) is now closed at the data level.

**New second-pass exporter.** `scripts/rebuild_groundtruth_outcome_fields.py`
(run after every `build_pilot.py` export) derives three fields of every
`groundtruth/recipes/<recipe>/variant_<id>.json` through the canonical
evaluator's own gold pipeline — reference execution bundle → runtime
reference rebinding → public gold projection, imported from the vendored
`task.run_eval`, never reimplemented:

- `final_snapshot` — the projected gold final state (now including rows the
  reference agent creates at runtime, e.g. `_created_by: "agent"` entries);
- `outcome_gold_calls` — the business-projected gold calls exactly as
  `run_eval` hands them to `evaluate_outcome`;
- `structural_return` — `{present, value}` for structural recipe-function
  terminals (previously exported as `terminal_result: null`).

For the handful of recipes whose public gold projection adds business calls
the historical trace predates (105071555's lookup write, 88674737's
runtime log, 91033108/121898837 cleanup deletes, 131710998/131716751
propagated updates), the added calls are folded into
`reference_tool_calls` and `tool_expectations`, so the published trace
expectations no longer penalize the behavior the outcome metrics require.
All 3,220 files were rewritten; a second run is a no-op (idempotent).

**`cal_acc` consumes the canonical gold.** The gold side scores
`outcome_gold_calls` plus the synthetic structural-return terminal; the
agent side applies the same per-recipe outcome canonicalization
(`_task_description_outcome_calls`, imported from the vendored module) and
converts explicit structural-return calls into the uniform synthetic
return, exactly as `run_eval` does. `terminal_required` for the control
path now also counts structural-return recipes.

**Parity is verified, not asserted.** New
`scripts/verify_calacc_parity.py` replays archived canonical artifacts
through `cal_acc.score` against the stored `run_eval` verdicts. Because
the two GPT ReAct lanes were still appending artifacts, the audit is
pinned to a frozen manifest rather than a directory scan: the tool takes
`--manifest` (a newline list of artifact paths) and `--expected-rows`, and
fails on zero rows, a directory with no artifacts, a manifest entry that
disappeared, or a row-count mismatch. The 2026-08-15 audit
(`outputs/parity_audit/frozen_artifact_list_20260815.txt`, 16,703 rows:
claude-opus-5, gpt-4o, gpt-35-turbo, and the local Qwen2.5 checkpoints
with artifacts, both modes; result in
`outputs/parity_audit/result_20260815.txt`): **zero disagreements** on
side-effect, normalized-terminal, and final accuracy, zero scoring
exceptions. The full public suite (29 tests, including all-3,220-fixture
perfection) passes. The rows the in-flight GPT ReAct lanes add after the
freeze are re-verified with a fresh frozen manifest once those lanes
complete.

Scope: execution-trace components — and therefore the trace half of
`orchestration_accuracy` — remain the published `tool_expectations`
simplification (measured agreement with the canonical runtime trace
verdicts is 78–88% per component, and the two control-path notions differ
by design); `evaluation/full_eval.py` remains the source of every released
number. No canonical result changes: the rewritten ground truth reproduces
byte-for-byte the gold the canonical runs already scored against.

## Published bundle trimmed to the run surface (2026-08-15)

The bundle now ships only what running and scoring the benchmark requires.
Development infrastructure — dataset construction (`build_pilot.py`,
`rebuild_groundtruth_outcome_fields.py`, `export_hf_dataset.py`), vendored
evaluator sync (`sync_connector_backends.py`), the 32B ReAct shard/rescue/
merge launchers, the one-off gpt-35 plan repair and finalize sbatch files
(Slurm holds its own copies of the two still-queued ones), the shard-merge
helper `evaluation/merge_react_shards.py`, and the regression-test suite
(`tests/`) — moved to the project-local archive outside the published tree.
All of it remains in git history at the release commits.

Deliberately retained: every run launcher (`scripts/run_*.sbatch`,
`download_scale_extension_models.sh`, the vLLM linker shim
`scripts/toolchain/`), the offline reproduction path
(`rescore_frozen_plans.py`, `recompute_leaderboard.py`,
`summarize_scale_comparison.py`), the public harness
(`evaluation/full_eval.py`, `eval.py`, `cal_acc.py`, `datasets.py`,
`model_corpus.py`, `example_adapter.py`), and the parity audit tool
(`verify_calacc_parity.py`) — the artifacts the two in-flight GPT ReAct
lanes add after the frozen 2026-08-15 audit still require a fresh frozen
manifest and a parity rerun on completion. `evaluation/merge_recipe_repair.py`
is retained temporarily: the queued repair job (25828) imports it at run
time; it moves to the archive when the finalize chain completes.

## Per-model launchers organized by tier (2026-08-15)

`scripts/` now mirrors the results layout: `scripts/{small_model,
medium_model,large_model}/<model-name>.sh` — one launcher per model, 32 in
total (canonical roster, the thinking ablation, and the on-hold extension
models). Each is a thin wrapper that submits its model's dedicated lane
(`sbatch --array=<index>`) of the shared protocol scripts
(`run_instruct_scale_comparison`, `run_scale_extension[_70b]`,
`run_api_model_comparison`, `run_opus_thinking_ablation`), so every pinned
revision, decoding cap, and resource setting keeps a single source of
truth in the shared launcher rather than 32 divergent copies. `outputs/`
was reorganized to the matching
`full_eval/{small_model,medium_model,large_model}/<model-name>/{global,react}`
layout (mode names global/react; frozen plans under `<model>/global/plans`;
per-task artifacts merged in from the source runs before those runs were
deleted); the canonical and API run directories migrate the same way when
the in-flight finalize chain completes.

## Extension launchers accept a modes argument (2026-08-15)

`run_scale_extension.sbatch` and `run_scale_extension_70b.sbatch` gain the
same third positional `modes` argument the API launcher already had
(default `plan_execute,react` — existing invocations unchanged), and their
`--state-namespace` now carries a mode suffix
(`ext-model-<i>-<modes>`), so a model's Global and ReAct evaluations can
run as two concurrent jobs without sharing mutable simulator state. The
two modes are independent by construction (ReAct never reads the frozen
plans; each mode writes its own results directory), and the frozen-plan
cache under the run root is unaffected. Used to mode-split the
local-scale-ext-20260816 campaign across the stable and borrow QOS lanes.

## Fail-closed hardening for malformed agent actions (2026-08-16)

Weak extension models produced action shapes the canonical models never
emitted, and two of them crashed the evaluator instead of scoring as
failed calls (glm-4-9b / Qwen2.5-3B passed the literal string
"parameters.limit" as a record limit, killing the simulator in
`int()`; Qwen3-4B emitted `args` as a JSON array, crashing the runner's
`args.get`). Both violated the fail-closed rule that an agent's malformed
input must never kill the run:

- `benchmark/tools.py` `call()` now converts argument-shape crashes inside
  a tool implementation (ValueError/TypeError/KeyError/AttributeError/
  IndexError) into the standard catchable tool error, so the call is
  recorded as failed and the agent receives an ERROR observation —
  identical to every other failed-call path. Deliberate RuntimeErrors
  (forced connector failures) are unchanged.
- `task/agents.py` `parse_action()` rejects actions whose `args` is not a
  JSON object; they take the existing format-error feedback path.

No recorded result changes: every completed run finished without touching
these paths (a hit was a crash, not a score), and the fixes are
model-blind. Synced to the internal tree. The three failed extension
react jobs were resubmitted and resume from their checkpoints.

## mistral-common chat templates render to token ids (2026-08-16)

Mistral-Nemo's tokenizer (transformers `MistralCommonBackend`) declares
`apply_chat_template(tokenize=False)` unsafe, and it is: the returned
string re-encodes with mangled special tokens and vLLM generated empty
text for every single request — the model's entire ReAct lane completed
with 3,220 `llm_error: model returned no text` rows. `_render_chat_prompt`
now renders with `tokenize=True` for mistral-common backends (normalizing
the BatchEncoding/batched shapes) and the vLLM / Transformers clients feed
the token ids directly (`prompt_token_ids`). Every other tokenizer keeps
the exact string path — byte-identical prompts, no cache impact. Verified
on CPU: Nemo now renders the documented `<s>[INST] ... [/INST]` form.
The broken ReAct results were quarantined
(`react.broken-empty-text-20260816`) and the lane resubmitted; no other
model was affected (the API clients never render templates locally, and
Mistral-Small-3.1 uses a standard tokenizer).

## Live results roll-up (2026-08-16)

`scripts/update_results_csv.py` regenerates `results.csv` (gitignored, at
the bundle root): one row per model/mode across the canonical run, the
thinking ablation, and the extension campaign. Completed modes report
leaderboard numbers; in-flight modes report partial means over scored
rows, marked `running`, with per-row primary metrics recomputed through
the vendored `primary_metrics_for_row` for rows that predate the stored
fields. A `health` column flags lanes whose recent rows are all errors
(the failure mode above) so a "completed" garbage lane can never pass as
a result. A detached loop refreshes the file every 30 minutes.

## React sharding for pathological lanes (2026-08-16)

The extension launchers accept an optional fourth argument: a file of
recipe ids that restricts the worker to that subset (forwarded as
`--ids`), with the file stem appended to the state namespace so
concurrent shards of one model never share simulator state. Each shard
writes its own run directory; rows merge back into the main run after
completion (duplicates resolved in favor of the main checkpoint, exactly
the 32B rescue semantics).

First application: `c4ai-command-r-08-2024`'s ReAct lane ran at ~4
episodes/hour — not a harness fault but the model's behavior (it pushes
the per-turn truncation guard with long generations on most turns), which
sharding scales linearly. The solo lane was cancelled at 18 completed
rows and its remaining 649 recipes split into four variant-balanced
shards (~804 variants each).

**Guard broadened (same day):** the first hardening enumerated crash
classes (ValueError/TypeError/KeyError/AttributeError/IndexError); a
Mistral-Small-24B frozen plan then killed its lane with
`sqlite3.ProgrammingError` (missing SQL binding parameter) inside the
snowflake simulator — a class outside the list. The tool boundary now
converts every non-RuntimeError exception from a tool implementation into
the standard failed call. A genuine harness defect surfaces as an
elevated failed-call rate in the results.csv health column instead of a
dead job.

## Frontier open-weight wave (2026-08-16)

Eight post-release open-weight models join the large-model roster in run
`frontier-ext-20260816`, launched by the new `run_scale_frontier.sbatch`
(per-lane tensor parallelism; vendor FP8 checkpoints where released;
otherwise the identical extension protocol): GLM-4.5-Air-FP8 (2xH200),
GLM-4.5-FP8 (4x), GLM-5.2-FP8 (8x, full node), DeepSeek-V4-Flash-0731
(2x), Qwen3.8-27B-FP8 (1x), and gemma-4 at 31B / 12B / 26B-A4B. Weight
downloads run as a Slurm job the eval jobs depend on. Not feasible on a
single 8xH200 node and therefore excluded from the local roster:
DeepSeek-V4-Pro (1.8 TB), Qwen3.8-2.4T-A95B (2.5 TB), and Kimi-K3
(1.6 TB; architecture also unsupported by the pinned vLLM) — these would
require API access or multi-node serving.

**Frontier lanes and the missing CUDA toolkit (2026-08-16):** the FP8
frontier checkpoints select flashinfer kernels whose first use JIT-compiles
through nvcc; the compute image ships no CUDA toolkit, so every generation
failed with `Could not find nvcc` (Qwen3.8-27B produced 6,440 error rows in
16 minutes before the run self-terminated; both GLM-4.5 lanes hit the same
wall at their first plan). `run_scale_frontier.sbatch` now exports
`CUDA_HOME` pointing at the toolkit inside the torch cu13 wheels (nvcc
13.2, headers, nvvm). The garbage Qwen3.8 run was quarantined
(`.broken-no-nvcc`) and every frontier lane restarted from scratch.

**Batched plan generation is silent until the batch completes:** local
frozen-plan generation submits all 650 planner prompts as one vLLM
scheduler batch (`prepare_initial_plans_batched`); no cache file is
written until the whole batch returns, so a healthy 70B lane can show
zero output for many hours at 100% GPU. The first Llama-3.1-70B plan
attempt was killed at 12h under the assumption it had hung — a
misdiagnosis this note exists to prevent repeating. Judge liveness by GPU
utilization (`srun --overlap nvidia-smi`), not by cache-file counts.

**nvcc/toolkit version alignment (2026-08-16):** with CUDA_HOME set, the
flashinfer JIT for Qwen3.8's gated-delta-net attention kernels still
failed — the env carried `nvidia-cuda-nvcc` 13.2.78 against cuda-toolkit
13.0.2 headers ("CUDA compiler and CUDA toolkit headers are
incompatible"). nvcc downgraded to 13.0.x to match, the poisoned
flashinfer JIT cache cleared, and the lane restarted. Qwen3.8-27B's two
garbage all-error runs were removed before any result could be mistaken
for a score.

## Local test-time-reasoning lanes (2026-08-17)

The harness gains declared, env-gated thinking support for local models
(absent env → every existing lane byte-identical):

- `HF_CHAT_TEMPLATE_KWARGS` — JSON chat-template switches (Qwen3.8's
  `enable_thinking` / `reasoning_effort`);
- `HF_SYSTEM_PROMPT_SUFFIX` — for models controlling effort via prompt
  text (Muse Glimmer's documented `Reasoning strength: high`);
- inline `<think>...</think>` spans are stripped from scored text (an
  unterminated span scores as a failed generation), and the JSON
  early-stop detector ignores draft JSON inside think spans;
- thinking lanes raise generation caps to 16,384 with the soft early-exit
  disabled.

`scripts/run_thinking_local.sbatch` runs the ablation lanes (reported
separately, like claude-opus-5 thinking): Qwen3.8-27B-FP8 at
reasoning_effort=high, and meta-models/Muse-Glimmer-30B at Reasoning
strength high. Muse Glimmer's architecture postdates the campaign's
pinned vLLM/transformers, so its lane runs from an isolated `muse` conda
env with a newer vLLM — an explicitly declared runtime difference for
this one ablation lane, never mixed into the pinned-stack comparisons.

A tier-layout view (`outputs/full_eval/{small,medium,large}_model/`)
now tracks every lane — completed and in-flight — via symlinks refreshed
every 30 minutes alongside results.csv; physical directories are never
clobbered, and full physical consolidation still happens once the
canonical finalize chain completes.

**Toolkit fully pinned to 13.0.88 (2026-08-17):** the nvcc downgrade left
`nvidia-nvvm` (cicc) at 13.2 and `nvidia-cuda-crt` at 13.3; cicc emitted
PTX ISA 9.2 that the 13.0 ptxas rejects ("Unsupported .version 9.2"),
killing the Qwen3.8 and DeepSeek-V4-Flash lanes at flashinfer JIT time.
nvcc, nvvm, and crt are now all 13.0.88, the flashinfer JIT cache was
cleared, and both lanes restarted (the poisoned Qwen3.8 plan cache —
3,220 error-status artifacts that --resume would have replayed — was
deleted with the garbage results).

**Default-on thinking in frontier templates (2026-08-17):** GLM-5.2 and
Qwen3.8 chat templates enable reasoning by default (untagged inline for
GLM-5.2; xhigh-tier for Qwen3.8). Under the main roster's 4,096-token
plan budget the models spent the whole generation reasoning and never
reached a plan, and the JSON early-stop could truncate at a JSON example
quoted inside the reasoning. Both main lanes now pass
`enable_thinking: false` through the declared template-kwargs knob —
matching the no-hidden-reasoning protocol every other roster lane runs —
and their Global modes were redone from clean caches (Qwen3.8's valid
ReAct results were kept). The thinking ablation lanes remain the place
where reasoning is deliberately enabled.

**Muse-Glimmer-30B blocked (2026-08-18):** three probe-verified dead ends —
absent from every vLLM registry through 0.27.1; vLLM 0.27's transformers
modeling backend loads the checkpoint but emits a lone <|eot|> or <|eom|>
noise under greedy, vendor sampling, channel priming, and forced
continuation alike; and plain transformers refuses the multimodal
conditional-generation class through AutoModelForCausalLM. The lane stays
registered and re-activates when vLLM ships native support.

## 2026-08-18 — Muse Glimmer lane: engine override was being clobbered
- Root cause of preflight v2/v3 "still garbage": `scripts/run_thinking_local.sbatch`
  exported `HF_LOCAL_ENGINE=vllm` unconditionally *after* the per-lane block, so the
  Muse lane's `HF_LOCAL_ENGINE=transformers` never reached the process — both
  preflights re-ran the known-broken vLLM transformers-wrapper path (confirmed by the
  vLLM V1 engine banner in slurm-thinking-26019_1.out). The native-transformers path
  had never actually been exercised in the harness.
- Fix: the global default is now `HF_LOCAL_ENGINE=${HF_LOCAL_ENGINE:-vllm}` so lane
  blocks can pin an engine. A/B probe also cleared `attn_implementation=sdpa` as a
  suspect (native generation is coherent under both sdpa and default attention).
- muse-preflight2 run dir quarantined as `.broken-vllm-engine`; preflight v4
  (job 26021, run `muse-preflight3`) is the first true test of the
  transformers + HF_PROMPT_IDS lane.

## 2026-08-18 — Composite-config context window (Muse Glimmer, second blocker)
- With the engine fix in place, preflight v4 (job 26021) failed differently: every
  call rejected at the input gate ("prompt has 59645 tokens, exceeding pinned limit
  32768"). Muse Glimmer's config is a composite multimodal config whose
  `max_position_embeddings` (131072) lives on `text_config`; the top level has none,
  so both local clients fell back to the 32768 default and clamped
  `HF_MAX_INPUT_TOKENS=98304` down to 32768.
- Fix: new `_native_context_tokens(config)` helper in
  `verification/backends/shared/src/task/llm_client.py` (checks the top level, then
  `text_config`); used at all three derivation sites (TransformersClient pre-load,
  TransformersClient post-load, VLLMClient). No behavior change for text-only
  configs. Synced to benchmark/shared copy.
- muse-preflight3 quarantined as `.broken-context-clamp`; preflight v5 = job 26022,
  run `muse-preflight4`.

## 2026-08-19 — Balanced-JSON early stop vs harmony channels (Muse, third blocker)
- With engine + context fixed, preflight v5 (job 26022) produced *coherent* harmony
  reasoning for the first time — but every plan stopped mid-analysis with "model
  response does not contain a plan array". Cause: the transformers-path
  `CompleteJSON` stopping criteria scans the decoded text from the first `{`/`[`
  and stops at the first balanced span, without validating it as JSON. Muse's
  `to=self` analysis channel is full of brace snippets, and its channel markers are
  special tokens (stripped by `skip_special_tokens=True`), so no `</think>`-style
  gating is possible.
- Fix: new `HF_JSON_EARLYSTOP=0` knob in TransformersClient disables the stopping
  criteria for such lanes; generation then runs to the model's own EOS, taken from
  `generation_config.eos_token_id` (Muse: [200001, 200008]) with the tokenizer id
  as fallback — the previous single-tokenizer-id override could miss list-eos
  models. Default behavior (early stop on, same eos when configs agree) unchanged.
  `HF_TAKE_LAST_JSON=1` then extracts the final-channel JSON. Muse lane exports the
  knob. Synced to benchmark/shared.
- muse-preflight4 quarantined as `.broken-earlystop`; preflight v6 = job 26023,
  run `muse-preflight5`.

## 2026-08-19 — Last-JSON extractor rewrite (Muse, fourth blocker)
- Preflight v6 (job 26023) reached full coherent generation: the final channel
  emitted a complete, valid `{"plan":[...]}` (verified parseable standalone). But
  extraction still failed: `_take_last_json`'s single-pass bracket state machine
  desyncs on reasoning prose (unquoted keys, ellipsis fragments, unclosed braces),
  so the real answer was swallowed into a never-balancing span and an inner step
  object was returned instead. TransformersClient also never applied
  `HF_TAKE_LAST_JSON`/`_strip_thinking` at all (only the vLLM path did).
- Fixes: (1) `_take_last_json` rewritten around `json.JSONDecoder.raw_decode`,
  attempted from every opener right-to-left — returns the rightmost value that
  consumes the rest of the text, else the parseable value ending furthest right.
  Verified against the captured Muse raw (extracts the 2-step plan) plus
  regression cases incl. quoted-example-then-answer, unclosed-brace poisoning,
  and trailing prose; 20 extractions on the 39KB raw in 0.01s. (2)
  TransformersClient now applies `_strip_thinking` + `HF_TAKE_LAST_JSON` like the
  vLLM path. In-flight Qwen/GLM thinking jobs keep the old code in memory
  (their tag-delimited outputs never triggered the desync); rows are unaffected.
- muse-preflight5 quarantined as `.broken-extractor`; preflight v7 = job below,
  run `muse-preflight6`.

## 2026-08-19 — Extractor preserves unclosed wrappers (Muse, fifth blocker)
- Preflight v7 (job 26028) was the first partial success: 1/5 recipes produced a
  valid scored plan (orch 0.6 on its variants), 1/5 failed on a genuine model
  schema slip. The other 3 failed with post-extraction raws that were bare step
  arrays ending exactly at end-of-text — the signature of `{"plan": [ ... ]` with
  the final `}` dropped by the model: the inner array parses and consumes to the
  end, so the extractor discarded the unclosed wrapper that
  `parse_plan(..., repair_missing_closers=True)` could have repaired.
- Fix: `_take_last_json` now walks left from the winning value through an
  unambiguous chain of unclosed openers (direct `[`, or `{"key":` immediately
  preceding) and returns from the chain start, handing the unclosed wrapper to the
  downstream repair. Prose can never match (key must be quoted and directly follow
  `{`). Verified end-to-end: extractor output + parse_plan repair recovers the
  wrapper; bare arrays without a wrapper stay bare (genuine model error, still
  penalized); all prior regressions pass, incl. the full preflight-v6 raw.
- `parse_plan` itself is untouched (scoring parity across models preserved).
- muse-preflight6 quarantined as `.partial-lossy-extractor`; preflight v8 = job
  below, run `muse-preflight7`.

## 2026-08-19 — Extractor keeps unclosed plan wrappers (user edit)
- Follow-up to the raw_decode extractor: preflight v7 (run `muse-preflight6`) got the
  first valid Muse plan + scored rows (plan 1/5 ok; plan_execute 6/51 ok,
  orch 0.600), but 3 plans still failed with a bare step array. Cause: when the
  model drops the wrapper's closing brace (`{"plan": [ ... ]` with no final `}`),
  the extractor returned only the inner array that consumes to end-of-text,
  discarding the wrapper prefix that `parse_plan(repair_missing_closers=True)`
  could have repaired.
- Fix (commit 92df092c, made under the user's account by a parallel session — the user confirmed they did not edit by hand): `_extend_through_unclosed_openers`
  walks left from a consume-to-end value through an unambiguous chain of unclosed
  openers (`[`, or `{"key":`), so the unclosed wrapper survives extraction; prose
  cannot match the pattern. Verified: real preflight5 raw still extracts the 2-step
  plan; missing-closer wrapper case now preserved; bare-array-after-prose unaffected.
- Job 26028 (preflight v7) cancelled under the user's account after the edit (stale code in memory);
  preflight v8 = job 26033, run `muse-preflight7`.

## 2026-08-19 — Muse Glimmer thinking lane: preflight PASSED, full run launched
- Preflight v8 (job 26032, run `muse-preflight7`): plans 4/5 valid (the fifth is a
  genuine model format error — a bare if-node with no plan wrapper, penalized like
  any other model's invalid plan); plan_execute 11/51 rows ok before cancellation,
  mean orch 0.764 on ok rows; first react episode ok at orch 0.9. Harness now runs
  Muse Glimmer faithfully end to end on the native transformers engine.
- Full ablation run launched mode-split into `local-thinking-20260817`
  (namespaces `thinking-model-1-plan_execute` / `thinking-model-1-react`):
  jobs 26034 (Global) + 26035 (ReAct) on the reservation.

## 2026-08-19 — Muse: final-channel marker split + 8-way sharding
- First full-run hour surfaced two issues. (1) Correctness: a recipe that passed
  preflight produced an inner-fragment extraction (a syntax slip anywhere inside
  the wrapper makes every JSON-side heuristic fall back to inner values). Root
  fix: Muse's harmony final channel carries a plain-text recipient header
  ("to=user") that survives special-token stripping — new
  `HF_RESPONSE_SPLIT_MARKER` env in TransformersClient splits on its last
  occurrence so extraction only ever sees the final channel (verified on the
  captured preflight raw). Absent marker → unchanged behavior; only the Muse lane
  sets it. (2) Throughput: single-stream HF generate at 60–100K context yields
  ~1 plan/h and ~7 react episodes/h (GPU 100% busy — intrinsic, not offloading);
  serial completion would take weeks.
- `run_thinking_local.sbatch` gained the ids-file 4th arg (same pattern as
  run_scale_extension: `--ids` + namespace suffix). Serial jobs 26034/26035
  cancelled; the one stale invalid plan artifact deleted; relaunched as 8 shards
  on the reservation: plans 3× (~217 recipes each, jobs 26036-26038), react 5×
  (130 recipes each, jobs 26039-26043), run dirs
  `local-thinking-20260817-muse-{plan,react}-N`. The 7 valid react rows already
  in the main run dir are kept (merge rule: main rows win). Merge via
  merge_react_shards_any + leaderboard recompute when shards finish.

## 2026-08-19 — Muse full-run relaunch hygiene
- The first full-run pair (26034 plan / 26035 react, pre-split-marker code) was
  cancelled and superseded by the sharded relaunch (26036-26038 plan shards,
  26039-26043 react shards, each with its own run dir
  `local-thinking-20260817-muse-{plan,react}-N`). Before any future merge into the
  main run dir: the 9 react rows 26035 left in
  `local-thinking-20260817/hf:meta-models__Muse-Glimmer-30B` were all status=ok with
  ZERO actions (vacuous passes from the pre-fix client); merge rules prefer main
  rows, so the dir is quarantined as `.broken-vacuous-zerostep-26035`. The one plan
  artifact 26034 cached (invalid, pre-split-marker) is quarantined as
  `plans/….broken-pre-splitmarker-26034` so a later `--resume` cannot replay it.

## 2026-08-19 — Muse plan sharding rebalanced 3→5
- 90-min checkpoint: react shards healthy (82/82 rows ok, ~55 rows/h aggregate →
  ~2.4 days for 3220). Plan shards too slow at 3-way (~1.3 plans/h/shard incl.
  load → ~3.3 days, past the 8/23 reservation end). Two reservation GPUs were
  idle: plan shards cancelled and resplit 5-way (130 recipes each, jobs
  26044-26048, run dirs local-thinking-20260817-muse-plan5-{0..4}); the three
  3-way run dirs were deleted (only 6 cached plans lost, regenerated by the new
  split). Projected plan completion ~2 days.

## 2026-08-19 — gpt-5.6-sol thinking ablation complete + heal
- Job 26008_5 finished: 3220/3220 rows both modes. plan_execute orch 0.5176 /
  final 0.3189 (477 plan_error rows are genuine model plan-grammar failures,
  protocol-scored); react orch 0.6656 / final 0.5422 (error_rate 0.0071).
- 23 react llm_error rows (transient API failures) excised with .pre-heal backups
  and resubmitted with --resume, react mode only (standard heal procedure).
- Heal (job 26049) recovered 21/23 rows in 4 minutes. Final gpt-5.6-sol react:
  orch 0.6688 / final 0.5444 / side 0.7379, error_rate 0.0006. The 2 remaining
  llm_error rows (122142838__v01, 59798940__v00) are deterministic OpenAI
  content-policy 400s on the task prompts — not transient; excluded-by-status per
  protocol, like other models' upstream refusals.

## 2026-08-19 — Plain-text marker cut answers apart; switched to exact channel header
- 2h checkpoint: plan5 ok rate collapsed to 4/19; the 13 "no plan array" raws were
  plan *tail fragments* of recipes that had passed preflight — the plain-text
  "to=user" split marker also occurs inside some plans' own strings, and rsplit cut
  the plan mid-body. React was barely affected (163/164 ok; the 1 llm_error is
  consistent with the same cut in an action string).
- Fix: `HF_RESPONSE_SPLIT_MARKER` is now matched against the *unstripped* decode,
  and the Muse lane sets it to the exact channel header `to=user<|message|>`
  (recipient + message special token); remaining special tokens are regex-stripped
  from the tail. Content strings cannot plausibly contain the special-token
  sequence. No marker → unchanged stripped decode.
- plan5 shards restarted as jobs 26050-26054 after deleting the 13 poisoned plan
  caches (no result rows existed yet; the 3 genuine schema-slip caches kept, and
  the 4 ok plans — whose split was provably clean, wrapper precedes any cut — are
  reused). React shards (26039-26043) keep the old in-memory code; their tail will
  be healed at merge (excise error rows + resume under the fixed client).

## 2026-08-19 — Correction: the "vacuous zero-step" quarantine reason was wrong
- The 9 react rows from superseded job 26035 (quarantined earlier today as
  `.broken-vacuous-zerostep-26035`) were NOT zero-action: their trajectories hold
  real tool-call steps (2-40 per episode). The "zero actions" reading came from a
  monitoring script querying a nonexistent `actions` field on results rows (the
  steps live in trajectories.jsonl). The quarantine itself stands for a different,
  valid reason: those rows were produced by the pre-exact-header-split client,
  while the react shards regenerate every task (incl. these 9) with uniform fixed
  code — keeping main-dir rows would let older-code rows win merges. No data loss.
- Same metric bug affected an interim report of shard react rows as "all
  zero-action"; actual distribution across 332 shard trajectories: 27 zero-step
  (genuine format failures, 8%), 49 at the 40-step budget cap, remainder normal.

## 2026-08-19 — GLM-5.2-thinking resharded (user-approved speedup)
- Single monolithic job 25987 (plans 231/650 at ~7.5/h; whole-lane ETA 8/24-25,
  brushing the 7-day wall) cancelled and replaced by:
  - 26056: plan_execute-only, canonical run name `local-thinking-20260817`
    (reuses all 231 cached plans; still on the dev_37ziwb node).
  - 26057-26059: react shards over 650 recipes split 209/210/231
    (`glm_shards/glm-react-0{0,1,2}.txt`), run names
    `local-thinking-20260817-glm-react-{0,1,2}`, qos=borrow (preemptible, no GPU
    cap) — react needs no plans, so shards start the moment any full node frees
    (Muse shard wind-down / reservation expiry 8/23 / other users' nodes).
- Merge back via the established shard-merge + leaderboard recompute path.

## 2026-08-19 — gpt-35 recipe 59838285 repair: root cause found, repair infeasible
- The finalize chain stalled twice on `merge_recipe_repair.py`'s gate ("repair
  produced no frozen-plan artifact"). Instrumented the swallowed exception path
  (run_eval.py open_loop planning now prints `[plan-transport]` diagnostics to
  stderr): the rerun fails with a deterministic HTTP 429 — "requests to
  gpt-4.1-mini for gpt-35-turbo in eastus have exceeded rate limit".
- Root cause: this recipe's planner prompt is ~156K tokens (double the ~70K of a
  typical recipe), which exceeds the gpt-35-turbo deployment's tokens-per-minute
  quota by itself. Every request is rejected instantly; API_MAX_ATTEMPTS retries
  cannot ever succeed. This is an upstream capacity refusal, not a transient
  transport failure and not model behavior.
- Protocol decision: the recipe's single task (59838285__v00) stays excluded-by-
  status for gpt-35 (plan_execute plan_error / react llm_error), the same
  treatment as gpt-5.6-sol's two content-policy 400 rows. The finalize/summary
  job now runs without the repair dependency. If the Azure quota is ever raised,
  `repair_gpt35_plan.sbatch` + finalize can rerun unchanged (both idempotent).
- Fixed en route: the repair run had a stale resume checkpoint (quarantined as
  `.stale-resume-noop`) that made attempt 25828 a 15-second no-op.

## 2026-08-19 — Canonical 11-model comparison finalized
- Finalize job 26064 failed at the react re-copy step: the source run
  `instruct-scale-8models-vllm-20260813` was archived to local_archive after its
  data was folded into the canonical run on 08-14 (canonical copies verified
  complete at 3220 rows each). The copy step is obsolete; remaining steps run
  manually: 8 local react leaderboards recomputed in place, gpt-35 plan-diff gate
  confirmed unchanged (rescore skipped), summary regenerated.
- Per user direction, gpt-35 is not run again. `summarize_scale_comparison.py`
  gains `--allow-missing-plan MODEL:RECIPE_ID` for documented permanently-missing
  plan artifacts; the exemption (gpt-35-turbo:59838285, TPM-quota refusal) is
  recorded in comparison.json under `plan_artifact_exclusions`.
- comparison.{json,csv,md} + comparison_wide.* + tier_summary.json regenerated
  over `global-react-final-20260814`: 11 models complete, gpt-35 react now
  reflects the healed 3220-row checkpoint (react orch 0.5078 / final 0.3006).

## 2026-08-19 — results.csv: finished lanes only (user request)
- `scripts/update_results_csv.py` now lists only complete lanes (leaderboard
  n == 3220, or 3220 checkpoint rows) and omits in-flight lanes entirely —
  no more partial moving means in the file. Coverage generalized from three
  hardcoded runs to every run directory under outputs/full_eval, with
  shard/preflight/debug/quarantined dirs and tier symlink views excluded and
  (model, mode) de-duplicated (canonical run wins). Thinking ablation runs are
  labeled with a " (thinking)" suffix. Current output: 37 finished models,
  72 lane rows. The 30-minute refresh loop uses the same script unchanged.

## 2026-08-19/20 — phi/nemo react tail rebalanced onto freed GPUs
- As Muse plan5 shards 2-3 and two extension workers finished, 3 GPUs freed. The
  single nemo tail worker (26066, 36 rows) was cancelled and the remaining gap
  recomputed fresh: phi 401 tasks / 86 recipes, nemo 1,087 tasks / 217 recipes.
  Resubmitted as 4 parallel workers over disjoint recipe lists: 26067
  (phi-tail2-0) + 26068-26070 (nemo-tail2-0..2), run names
  `local-scale-ext-20260816-{phi,nemo}-tail2-*`. All four running immediately.
- Muse plan5 progress at rebalance time: 588/650 artifacts (validity ~31%,
  dominated by bare-array format noncompliance — documented earlier).

## 2026-08-20 — Qwen3.8-thinking resharded (same pattern as GLM)
- Muse plan5-0 completed and freed a GPU; with Qwen plans effectively done
  (648/650 cached) the monolithic 25978 was cancelled (2d6h in) and replaced by:
  26071 plan_execute-only on the canonical run name (reuses every cached plan;
  the 16 react rows it had already written remain and win merges), plus react
  shards 26072-26075 over recipe splits 157/157/163/173
  (`qwen_shards/qwen-react-0{0..3}.txt`, run names
  `local-thinking-20260817-qwen-react-{0..3}`). Shard 0 started immediately;
  1-3 queued on resv priority and start as Muse plan5-1/4 finish.
- Expected effect: Qwen thinking react drops from a ~3-5 day single-GPU tail to
  ~1-1.5 days across 4 GPUs.

## 2026-08-20 — Qwen3.8-thinking Global complete
- plan_execute finished with the monolith's incremental rows (3220/3220,
  confirmed by 26071's resume pass): orch 0.3302 / final 0.1705 / side 0.3571 —
  the strongest open-source Global result in the campaign (non-thinking Qwen3.8
  0.2857; gpt-4o 0.2809). plan_error 1271 rows (xhigh reasoning degrades plan
  format compliance relative to the non-thinking lane).
- Two recipes lack plan artifacts, both protocol-legitimate: 59838285 (prompt
  123,322 tokens > the thinking lanes' 98,304 input pin; fail-closed, identical
  to the non-thinking lane) and 100761994 (thinking never closed within the 32K
  cap → empty surfaced text on all 17 variants; the non-thinking lane got an
  invalid plan on the same recipe). Any thinking-tier summarize pass must use
  --allow-missing-plan for these.

## 2026-08-20 — Thinking ablations extended to every capable open model (user request)
- All feasible open-source thinking ablations are now covered. New launcher lanes
  in `run_thinking_local.sbatch`: index 3 DeepSeek-V4-Flash (vLLM deepseek_v4
  tokenizer accepts `thinking`+`reasoning_effort` template kwargs; frontier
  stability flags carried over: fp8 MLA KV cache, per-lane deep_gemm, ids
  prompts, synchronous scheduling; TP2), index 4 GLM-4.5-FP8 (TP4) and index 5
  GLM-4.5-Air-FP8 (TP2), both `enable_thinking: true` with tagged <think>
  handling. Revisions pinned to the same SHAs as the frontier run.
  `VLLM_USE_DEEP_GEMM` became per-lane (`LANE_DEEP_GEMM`).
- Preflights queued (5 recipes, both modes): V4-Flash, GLM-4.5, GLM-4.5-Air —
  they start as GPUs free; full runs follow only after preflight validation.
- Not feasible, documented: Kimi-K3 / DeepSeek-V4-Pro / Qwen3.8-2.4T (exceed
  cluster memory); gemma-4 family and the older roster have no thinking mode;
  Qwen3-*-Instruct-2507 are the non-reasoning variants by design; Muse Glimmer
  is thinking-only and already runs at Reasoning strength: high.

## 2026-08-20 — Muse plan failures confirmed genuine; no shard restart
- Ground-truth dumps (debug probe 26055, unstripped decode): the channel
  structure is `to=self<|message|>analysis<|eom|><|start|>assistant
  to=user<|message|>{plan}<|eot|>`; the exact-header split isolates the final
  channel correctly. A previously-failing recipe's channel content has a genuine
  mid-text JSON syntax error (missing delimiter at char 1333) — a model grammar
  slip, not an extraction artifact and not repairable by the (closers-only)
  repair pass.
- Verdict-equivalence analysis: the running v2 client (exact header +
  last-JSON-with-wrapper-extension) and the improved v3 client (whole channel
  handed to the parser when the split succeeds; committed for future runs)
  produce identical verdicts on every observed class — missing-closer plans are
  recovered by both (extension + repair), mid-text-error plans are invalid under
  both. Restarting the 10 Muse shards for v3 would only improve raw_response
  auditability while ceding reservation GPUs to the queued follow-on lanes, so
  the shards run on with v2. Remaining "no plan array" caches are deterministic
  genuine model errors and stand as final results.
- React shards (plain-marker code in memory): error rows (~1%) will be excised
  and re-run under the fixed client during the merge phase; ok rows are
  trustworthy (a silent wrong verdict would require the marker inside the
  action's own strings AND a parseable fragment — not observed).

## 2026-08-20 — Canonical finalize chain: status and recovery
- gpt-35 react completed (3220 rows). The dependency chain broke twice on the
  same step: the single-recipe (59838285) frozen-plan repair hit the Azure
  gpt-4.1-mini deployment's rate limit at 17:50 and 17:54 on 8/19 (LLMError
  raised before any artifact write — hence "repair produced no frozen-plan
  artifact"), failing jobs 25828 and 26062 and cascading 25830/26063/26064.
- Finalize job 26064 (resubmitted without the failed dependency) copied the API
  models' react rows into the canonical run (gpt-35 react: orch 0.5078,
  final 0.3006) before dying on a step that is now obsolete: it re-copies local
  models' react rows from instruct-scale-8models-vllm-20260813, which was
  already deleted in the reorg prep. The canonical run dir is structurally
  complete: 11 models × 3220 rows in both modes + comparison files.
- Remaining gap is exactly one artifact: the 59838285 gpt-35 frozen plan. A
  detached 15-min-spaced retry loop is running on the login node
  (gpt35_repair_retry.sh, 16 attempts); on success: merge_recipe_repair into the
  API run → rsync plans → rescore gpt-35 plan_execute in canonical →
  summarize_scale_comparison (expected 11 models / 3220 / 650). The
  reorganize_outputs.sh safety gate will be repointed from job 25830 to the
  actual completion evidence before the reorg runs.
- Muse plan validity spot-check (3 fragment-raw failing recipes) queued as job
  26079 with unstripped-decode dumps to confirm the mid-text-syntax-error
  diagnosis on a wider sample.

## 2026-08-20 — V4-Flash thinking preflight: 32K plan-budget overruns are model behavior
- Preflight (job 26080): react 13/13 ok; plans 2/5 ok with clean extraction.
  The 3 failing recipes each consumed exactly 32,768 planner tokens —
  reasoning_effort=high overruns the plan budget and truncates the final plan
  (successes used 7-9K). 32,768 is the physical ceiling under the shared
  thinking-lane protocol (98,304-token input pin + generation must fit the
  131,072 context), and all thinking lanes share it, so the cap stays; overruns
  score as failures, mirroring Qwen xhigh's overrun on recipe 100761994. This is
  a reportable ablation finding (high-effort reasoning can exhaust generous plan
  budgets), not a harness defect.

## 2026-08-20 — V4-Flash + GLM-4.5 thinking full runs launched
- V4-Flash preflight completed: react 51 rows / 48 ok / orch 0.685 (plan-side
  32K overruns documented above). Full runs: plan_execute into the canonical
  thinking run + react run `local-thinking-20260817-v4-react-0`, TP2, borrow.
- GLM-4.5 preflight passed earlier (react 51/51 ok orch 0.706; invalid plans
  are genuine schema errors). Full runs 26083 (plan) / 26084 (react), TP4,
  borrow. GLM-4.5-Air preflight (26082) in flight.

## 2026-08-20 — GLM-4.5-Air preflight verdict + full runs
- Preflight (26082): react 51/51 ok orch 0.606. Plans 1/5 (the valid one used
  15K tokens); the 4 failures are "model returned no text" — the tagged <think>
  block never closes within the 32K cap, so the strip yields empty output.
  Same budget-overrun family as V4-Flash (untagged truncation) and Qwen xhigh;
  protocol cap unchanged. Full runs launched: plan_execute into the canonical
  thinking run + react `local-thinking-20260817-air-react-0`, TP2, borrow.

## 2026-08-20 — Muse plan-invalidity confirmed genuine (spot-check closed)
- Job 26079 re-generated three fragment-raw failing recipes with unstripped
  dumps. Ground truth: one plan parses but violates the plan schema
  (filters.items[0].args not an array); two have real mid-text JSON syntax
  errors — both "Expecting ',' delimiter" at the step-1→step-2 boundary
  (over-closed braces after deeply nested filter expressions), a systematic
  model grammar weakness. No extraction artifact involved; the ~50% Muse plan
  invalidity stands as the model's genuine Global View behavior (its ReAct
  lane is strong: 99.5% ok rows so far), consistent with the paper's thesis
  that variant-blind planning, not ReAct competence, is the differentiator.
- Minor run-to-run nondeterminism observed across GPUs (one recipe parsed on
  the spot-check node but not in the shard run) — same failure class either
  way; canonical Muse numbers come from the sharded ablation run only.

## 2026-08-20 — gpt-5.6-sol thinking ablation COMPLETE; Qwen3.8 thinking Global complete
- gpt-5.6-sol (reasoning_effort=high, direct OpenAI): Global orch 0.5176 /
  final 0.3189 / side-effect 0.5488 (477 invalid plans, 14.8%); ReAct orch
  0.6688 / final 0.5444 / side-effect 0.7379 with 2 residual llm_error rows
  (0.06%) — both deterministic OpenAI content-policy HTTP 400 refusals of the
  prompt (retried in-run; persistent). Kept as terminal provider-side refusals,
  analogous to a model refusal; not healable by resubmission.
- Qwen3.8-27B-FP8 thinking (xhigh): Global complete — orch 0.3302 / final
  0.1705 (1271 invalid plans, 39%); react in progress via the user's shard jobs.
  Thinking lifts Qwen's Global orch from 0.2857 to 0.3302 (+4.5 points).
- Note: the user cancelled the serial Qwen (25978) / GLM-5.2 (25987) thinking
  jobs and took over those lanes with their own shard submissions (26056-26059,
  26072-26075) plus queued lanes 3-5 (DeepSeek-V4-Flash / GLM-4.5 / GLM-4.5-Air
  thinking) added to run_thinking_local.sbatch.

## 2026-08-21 — phi-mini react finalized
- All 3,220 unique react tasks assembled across the main checkpoint + 10 shard
  runs (536+820+856+311 folded in; main rows win). merge_react_shards_any's
  3,220-unique guard passed; leaderboard recomputed:
  phi-mini react orch 0.2917 / final 0.0907 / side 0.3748, error_rate 0.0612
  (the residual errors are the >131k-token over-context conversations,
  fail-closed by protocol). phi-mini now complete in both modes and will enter
  results.csv on the next refresh.

## 2026-08-21 — Muse react error cluster: transient cuDNN SDPA failures in shard h2
- 42 llm_error rows in the user-launched helper shard
  local-thinking-20260817-muse-react-h2, all "local generation failed: Expected
  mha_graph.execute(...)" — a cuDNN SDPA graph-execution failure on that
  process/GPU. The shard has since recovered and is producing ok rows, so the
  job is left running; the 42 poisoned rows go on the merge-phase healing list
  (excise + resume under the fixed client), alongside the ~1% plain-marker-era
  error rows in react-0..4. The remaining Muse react errors (~11) are
  legitimate over-context rows (prompt > 98304, truncation forbidden) and stand.

## 2026-08-21 — GLM-4.5-Air react: 16K-budget overruns are model behavior
- Air react (26089) errors ~21% of early rows with "model returned no text":
  the tagged <think> block fails to close within the shared 16,384-token react
  budget on harder recipes, so the strip yields empty output (same failure
  family as its plan-side overruns; its preflight's 51/51 covered easier
  recipes). Protocol cap unchanged for comparability; rows score as llm_error /
  excluded. Reportable finding: Air's high-effort reasoning frequently cannot
  fit even generous react budgets.

## 2026-08-21 — CANONICAL FINALIZE COMPLETE; outputs reorganized to tier layout
- gpt-35 frozen-plan repair for recipe 59838285 succeeded on retry 18 of the
  overnight loop (Azure quota freed); merge_recipe_repair replaced the
  plan_error row (backup under repair_backups/, archived with the repair run to
  <maintainer archive>/finalize_audit_20260821/).
  gpt-35 plan_execute rescored in the canonical run (orch 0.1011, final 0.0432,
  unchanged at reported precision). summarize_scale_comparison rebuilt all
  comparison tables: models_complete=11.
- reorganize_outputs.sh executed (safety gate repointed from the dead job-id
  check to the FINALIZE_DONE marker + comparison.json evidence): canonical and
  API run dirs migrated into outputs/full_eval/{small,medium,large}_model/
  <model>/{global,react}; comparison files now live at outputs/full_eval/ root;
  slurm logs moved to outputs/logs/; repair-run leftovers removed (archived).
- scripts/update_results_csv.py: canonical block now falls back to the tier
  layout (with the pre-reorg run-dir branch kept for older checkouts); model
  names and tiers unchanged in the csv.
- evaluation/merge_recipe_repair.py archived to evaluation/archive/ (single-use
  tool, retained for audit).
- Row-level cal_acc parity rerun launched over a fresh frozen manifest of the
  reorganized layout (49,730 artifacts; manifest + result stored in
  <maintainer archive>/parity_{manifest,result}_20260821.txt).

## 2026-08-21 — Mistral-Nemo react finalized
- 3,220/3,220 unique assembled (main 299 + react-0/1 shards 2,826 + tail2-2 95;
  overlapping tail rows deduped, main wins). Leaderboard: orch 0.3427 /
  final 0.1196 / side 0.4550, error_rate 0.0019. The extension wave is now
  complete in both modes for every model; nemo enters results.csv on the next
  refresh.

## 2026-08-21 — cal_acc parity PASSED on the reorganized layout
- verify_calacc_parity over the frozen manifest of all tier-layout artifacts:
  49,730 rows compared, 0 score() exceptions, 0 side-effect / terminal / final
  mismatches (exit 0). Manifest and result stored at
  <maintainer archive>/parity_{manifest,result}_20260821.txt.

## 2026-08-21 — Qwen3.8-thinking complete (both modes)
- React merged from 7 shard runs (3,220-unique guard passed; redundant helper
  rows deduped, main wins): orch 0.6303 / final 0.4938 / side 0.7233,
  error_rate 0.0078. Combined with the Global result (orch 0.3302), the xhigh
  ablation shows large gains over the non-thinking lane in BOTH modes
  (Global +4.5pts, react orch +9.7pts, react final +17.6pts — react final now
  exceeds claude-opus-5 non-thinking's 0.4714). Redundant shard 26075
  cancelled after coverage confirmed.

## 2026-08-21 — Thinking-lane wave status (user-driven lanes)
- GLM-4.5-FP8 thinking react complete: orch 0.5364 / final 0.3717 / side 0.6289,
  with 55 healable "model returned no text" transient rows (excise+resume once
  its job exits — on the healing list) and 6 legitimate over-context rows.
- DeepSeek-V4-Flash thinking react 2120/3220 (all 47 errors are legitimate
  over-context rows). GLM-5.2 thinking plans 617/650; GLM-4.5 plans 527/650;
  GLM-4.5-Air plans 72/650. Muse react 2716 unique/3220 (errors stable at the
  documented 272; no new failures since h2 died).

## 2026-08-21 — GLM-4.5-Air thinking lane cancelled (user decision)
- Per the user's instruction, the GLM-4.5-Air thinking lane was stopped: jobs
  26088_5 (plans, 100/650 cached) and 26089_5 (react, 2844/3220 rows) cancelled.
  Partial outputs remain in place (local-thinking-20260817 plans cache and
  local-thinking-20260817-air-react-0) but the lane is not reported — it was the
  slowest remaining lane and would not have finished inside the reservation.

## 2026-08-21 — GLM-4.5 thinking react healed
- The 55 transient "model returned no text" rows were excised
  (results.jsonl.pre-heal backup kept; the 6 over-context rows stand) and the
  lane resubmitted as job 26118 with the same run name/namespace — resume
  re-runs only the excised episodes.

## 2026-08-22 — Muse react merged (ok-preferred); 2 shape-specific cuDNN rows healed
- All Muse react shards completed with full coverage: 3220/3220 unique tasks,
  3200 with ok rows. Merged into local-thinking-20260817 via
  merge_muse_react.py (devtools): for each task an OK row is preferred over any
  error row regardless of source (h2's 251 transient cuDNN rows and the early
  plain-marker rows are thereby superseded by clean rows from the full-cover
  shards); trajectories follow the kept row's source; 3220-unique guard.
- Residual errors after merge: 18 legitimate over-context rows (prompt >
  98304, truncation forbidden) plus 2 rows (123613394__v01, 123622274__v01)
  that failed with the cuDNN mha_graph error in every shard that tried them —
  a sequence-shape-specific cuDNN SDPA bug, i.e. a stack fault, not model
  behavior. New `HF_ATTN_IMPL` knob in TransformersClient (default sdpa
  unchanged); the two rows were excised (.pre-heal backup) and are re-running
  under eager attention (job 26128, ids-file heal into the main run dir).

## 2026-08-23 — Muse Glimmer thinking lane FINAL
- cuDNN heal v2 (HF_DISABLE_CUDNN_SDP=1, SDPA on flash/mem-efficient backends):
  123622274__v01 completed ok; 123613394__v01 became a legitimate over-context
  error under working attention (the episode ran longer and crossed 98304 input
  tokens). Final Muse react: n=3220, orch 0.5480 / final 0.3907 / side-effect
  0.6630; residual errors = 19 over-context rows only, zero infra errors.
- Muse ablation summary: Global 206/650 valid plans (orch on scored rows per
  leaderboard; spot-check-verified genuine grammar weakness on the symbolic
  plan schema) vs strong ReAct — the sharpest Global/ReAct split in the
  thinking wave, consistent with the paper's thesis.

## 2026-08-23 — Thinking-wave Global leaderboards complete; targeted heals
- Global (thinking) results: GLM-5.2 orch 0.1775 (73% invalid plans; below its
  non-thinking 0.1923), GLM-4.5 orch 0.2009, DeepSeek-V4-Flash orch 0.1714
  (well below its non-thinking 0.2701), Qwen3.8 0.3302 (above non-thinking
  0.2857), gpt-5.6-sol 0.5176. Reading: enabled thinking helps Global View only
  where plan-schema competence already exists (opus, gpt-5.6-sol, Qwen3.8);
  for GLM/V4 it inflates plan-grammar failures and lowers Global scores.
  ReAct (thinking): V4 0.5885, Muse 0.5480, GLM-4.5 0.5364 — uniformly strong,
  consistent with the thesis.
- The one missing plan artifact in every local lane is recipe 59838285 — its
  planner prompt exceeds the pinned 98304-token input limit, so plan generation
  raises before the artifact write (rows correctly record plan_error;
  deterministic, not healable, same class as the react over-context rows).
- Redundant Muse h-shard jobs (26092/26093/26110) cancelled after the final
  merge; GLM-4.5 react heal v2 = job 26131 (55 rows previously excised — found
  already excised in place — refilled via 20-recipe ids run into the same dir).

## 2026-08-23 — Muse Glimmer Global (plan_execute) merged; lane closed
- (Heal v2 details in the "Muse Glimmer thinking lane FINAL" entry above.)
  plan_execute shards merged into the main run (3220 unique, 953 ok rows) and
  plan caches consolidated (649 cached artifacts; the 650th, recipe 59838285,
  has no artifact in any local lane because its planner prompt exceeds the
  98304-token input limit — rows correctly record plan_error).
  Muse Global FINAL: orch 0.1415 / final 0.0547 / side 0.1466 — weak
  variant-blind planning against strong ReAct, consistent with the paper's
  thesis. Tier views + results.csv refreshed.

## 2026-08-23 — Qwen3.8 thinking lane FINAL
- React shards merged (ok-preferred, generalized merge_react_ok_preferred.py):
  n=3220, orch 0.6308 / final 0.4941 / side 0.7239; residual = 23 legitimate
  over-context rows. Thinking lifts Qwen3.8 react orch from 0.5331 to 0.6308
  and final from 0.3177 to 0.4941 — the strongest open-source react result,
  above non-thinking claude-opus-5 (0.6352 orch is higher, but final 0.4714 is
  now below Qwen's 0.4941).

## 2026-08-23 — Codebase/results organization per user request
- All API-based models now live under large_model (outputs + scripts):
  gpt-35-turbo moved from medium_model; claude-haiku-4-5.sh script moved
  (its lane is on_hold, no outputs); manifest analytic tiers for API models
  set to "large" to match. gpt55_sol renamed gpt-5.5-sol (model's own name).
- Completed thinking lanes physicalized into large_model (symlink views
  replaced by real dirs, sources retired after verification):
  Muse-Glimmer-30B-thinking (global merged from the 5 plan shards — 3220 rows,
  649 plan dirs; byte-identical to the user's 00:33 main-run merge, which was
  removed as redundant), Qwen3.8-27B-FP8-thinking, DeepSeek-V4-Flash-0731-thinking,
  gpt-5.6-sol-thinking. GLM-5.2 / GLM-4.5 / GLM-4.5-Air stay as views until
  their lanes finish (GLM-4.5 react heal = job 26132 with corrected --gres;
  Air global/react resumed as borrow jobs 26133/26134).
- update_results_csv.py: normalized cross-convention dedup (run-dir "hf:org/…",
  tier-dir short names, "(thinking)"/"-thinking"), a tier-layout scan that runs
  after the run-dir scan, and tier hints from the folder for names absent from
  the manifest tier map.

## 2026-08-23 — Replan Mode enabled; small/medium open-source replan wave launched
- Replan mode (ReplanAgent: model-driven continue-vs-replan after every real
  tool observation; immutable executed prefix; suffix replacement validated by
  the same symbolic plan schema; max_replans=2) was already implemented in the
  vendored evaluator but never exercised. It is now wired through the public
  pipeline: run_scale_extension.sbatch modes arg, results.csv replan columns.
- Preflight sequence: (1) toolless-plan recipe correctly produces zero review
  turns; (2) frozen initial plans are reused from the Global runs' caches
  (cache-key hit, 0 planner calls) so Replan−Global deltas isolate mid-course
  repair; (3) with tool-calling plans the review loop fires — Qwen3-4B emitted
  structurally-correct replans whose JSON carries the same class of grammar
  slips seen elsewhere (bracket over-closing; fail-closed, now reported as
  "malformed JSON" distinct from wrong-type replies, raw reply kept on every
  rejection for audit), glm-4-9b's replans parse and fail on semantic
  validation (stale observation cite, illegal op) — all failures
  model-attributable, harness verified end-to-end.
- Full wave (run replan-smallmed-20260823, borrow QOS): Qwen2.5-3B (26139),
  Qwen3-4B (26140) [small]; glm-4-9b (26141), gemma-3-12b (26142),
  Mistral-Nemo (26143) [medium].

## 2026-08-23 — Replan wave results (4/5 complete); GLM-4.5 thinking final; engine-version note
- Replan headline (vs Global / ReAct orch): Qwen2.5-3B 0.0219 (= Global 0.0219,
  ReAct 0.3416); Qwen3-4B 0.1380 (Global 0.1375, ReAct 0.4184, 99 accepted
  replans / 1330 reviews); Mistral-Nemo 0.0226 (= Global, 0 accepted); glm-4-9b
  0.0904 (Global 0.0903, 91 accepted / 1160 reviews). Finding: at small/medium
  scale, observation-driven mid-course repair adds ~nothing over frozen plans —
  even accepted replans do not convert to outcomes; ReAct >> Replan ≈ Global.
  gemma-3-12b lane still running.
- GLM-4.5-FP8 thinking finalized after react heal: react orch 0.5468 / final
  0.3792 / side 0.6410 (6 residual llm_error rows out of 3220); physicalized to
  large_model/GLM-4.5-FP8-thinking (global orch 0.2009).
- Engine-version record correction: the campaign's standard local engine is
  vLLM 0.24.0 (benchmark env, installed Jul 4) for ALL local lanes; the muse
  env (vLLM 0.27.1 + transformers 5.15) is used only by the Muse lane, as its
  declared newer-stack deviation. GLM-4.5-Air's thinking-mode empty-text plan
  failures reproduce in the user's original job (164 occurrences) — an
  Air+enable_thinking behavior on 0.24.0, being probed on 0.27.1 (job 26144)
  before deciding the lane's path.

## 2026-08-23 — GLM-4.5-Air thinking lane migrated to vLLM 0.27.1
- Root cause of Air's empty-text failures (164 in the user's original global
  job, 66 in the resume, 399 react rows): GLM-4.5-Air with enable_thinking on
  vLLM 0.24.0 returns an empty completion for a large fraction of prompts
  (immediate close-and-EOS). Probe on vLLM 0.27.1 (muse env): the same
  always-failing recipe generates a real 4,630-token plan (its schema slip is
  an ordinary model error). No empty completions on 0.27.1.
- Lane migrated to the muse env's 0.27.1 (declared engine deviation, same
  precedent as the Muse lane): the 107 0.24-era plan caches were quarantined
  (.v024-era) so the Global side regenerates entirely on one engine (job
  26145); the react side keeps its 2,811 valid 0.24 rows and heals only the
  excised 399 no-text rows on 0.27.1 (job 26146) — the intra-lane engine mix
  for react is documented here.

## 2026-08-23 — Qwen3.8-27B-FP8 added to the replan wave (user request)
- Frozen plans copied from frontier-ext-20260816 (649 cached recipes; the
  650th is the known 59838285 over-context planner prompt); job 26147 runs
  modes=replan into replan-smallmed-20260823 via the frontier launcher's lane
  (enable_thinking:false, TP1) — the large-tier anchor for the replan
  comparison (its Global 0.2857 / ReAct 0.5331 are the strongest open-source
  non-thinking numbers).

## 2026-08-23 — Air react heal pass 2; gemma replan restart
- Air react heal pass 1 (0.27.1, job 26146): of the 399 excised 0.24-era
  no-text rows, 238 completed ok and 161 returned empty again on 0.27.1 —
  unlike the plan phase, which is fully clean on 0.27.1. Pass 2 (job 26149)
  re-runs those 161; tasks that fail both 0.27.1 passes will be recorded as
  genuine model behavior (Air emitting an immediate-EOS empty reply on those
  episodes) and kept as llm_error rows, same policy as over-context rows.
- gemma-3-12b replan job 26142 died at 2.5 min ("engine core exited
  unexpectedly", node-transient); resubmitted as 26148 (resumes past the 55
  existing rows).

## 2026-08-23 — Replan review-turn message protocol fix; uniform wave rerun
- gemma-3-12b's replan job died twice at the same recipe: a failing tool call
  triggers the review turn, whose message list opens with two consecutive
  user turns (initial-plan message, then the first observation) — gemma's
  strict-alternation chat template raises jinja TemplateError, which escaped
  as a process-fatal error (not an LLMError).
- Fixes: (1) runner folds an observation into the still-open user turn when
  the last message is a user turn (template-agnostic, protocol-equivalent);
  (2) VLLMClient wraps chat-template rendering failures as LLMError so any
  future template rejection fails the row, not the job.
- Prompt-construction parity: the previously completed replan lanes ran with
  the two-consecutive-user-turn construction that tolerant templates accepted.
  To keep one prompt construction across every replan model, all six lanes
  were rerun from scratch under the fixed runner (results dirs quarantined as
  .pre-usermerge, frozen plan caches reused): jobs 26150 (Qwen2.5-3B),
  26151 (Qwen3-4B), 26152 (glm-4-9b), 26153 (gemma-3-12b), 26154 (Nemo),
  26155 (Qwen3.8-27B).

## 2026-08-23 — Replan wave v2 complete: all six models verified, quarantine removed
- All six v2 lanes (26150-26155) COMPLETED exit 0 with 3220/3220 rows each.
  gemma-3-12b now runs through its previously process-fatal recipe 100956844,
  which lands as a row-level plan_error (the model's own failure), confirming
  the observation-folding + LLMError fixes.
- v2 vs quarantined v1 leaderboards: max per-metric drift 0.0028 (Qwen3.8-27B,
  from re-sampled review turns); Qwen2.5-3B and Nemo byte-identical metrics;
  Qwen3-4B/glm-4-9b within 0.001. v1 `.pre-usermerge` dirs deleted after
  verification; v2 is the sole canonical replan result set.
- Final replan numbers (orchestration/final, accepted replans over reviews):
  Qwen2.5-3B 0.0219/0.0059 (1/105); Qwen3-4B 0.1381/0.0394 (78/1309);
  gemma-3-12b 0.0846/0.0168 (22/308); glm-4-9b 0.0908/0.0283 (77/1166);
  Mistral-Nemo 0.0226/0.0099 (0/191); Qwen3.8-27B 0.2939/0.1339 (336/2885).
- Finding: Replan ≈ Global at small/medium scale (|Δ| ≤ 0.002 everywhere;
  accepted replans do not convert to outcomes). Mid-course repair marginally
  emerges only at 27B: Qwen3.8-27B replan +0.8 orch / +0.7 final points over
  its Global baseline (0.2857/0.1267). ReAct >> Replan ≈ Global at all scales.
- Bookkeeping: manifest replan_runs updated with v2 numbers + protocol note;
  refresh_tier_views.py (devtools) extended to link replan dirs into the tier
  layout (all six models now expose global/react/replan views); results.csv
  regenerated (89 rows, six replan rows, no quarantine leakage).

## 2026-08-23 — GLM-4.5-Air 0.27.1 plan lane sharded 4-wide
- Job 26145 generated 76/650 fresh plans in 10.4h (~7/h; xhigh thinking on
  the one-shot plan is the cost) — ~3 days remaining single-lane. With the
  replan wave's GPUs freed, the 574 remaining recipes were split: 26145 keeps
  the first 143 in manifest order; three borrow-QOS shards (26159/26160/26161,
  TP2, --exclude=<reserved-node>) take 144/144/143 ids each
  (shard_ids/air-plan-{0,1,2}.txt) into run dirs
  local-thinking-20260817-air-plan-{0,1,2}. On completion: copy plans into
  the canonical run's plans dir and ok-preferred-merge the plan_execute rows
  (same pattern as the Muse/Air react shard heals).
- Also: results_csv_updater_loop restarted (found dead); refresh_tier_views
  now links replan dirs (see previous entry).

## 2026-08-23 — Root cause of the Air plan crawl: batched-planning poisoning; per-request isolation fix
- Diagnosis of the GLM-4.5-Air "model returned no text" plague on 0.27.1:
  VLLMClient sets batch_initial_plans=True and defines no
  initial_plan_batch_size, so prepare_initial_plans_batched submits ALL
  pending recipes as one complete_many batch. complete_many raised on the
  FIRST empty completion, discarding every peer completion in the batch and
  dropping the run into the serial per-recipe fallback — the observed
  ~7 plans/hour crawl on 26145 (and the reason shards 26159/26161 showed
  zero output for 1h45: still grinding a doomed 144-prompt batch). The same
  poisoning hit react's concurrent-batch leader: one empty completion failed
  every trajectory in the scheduler batch (why react heals kept recovering
  "innocent" rows in bulk).
- Fix (commit d0b8b0c9): VLLMClient.complete_many_indexed returns a str or
  LLMError PER REQUEST (context-overflow at prompt prep is also per-item);
  the react batch leader assigns per-entry exceptions; the plan batcher
  consumes indexed results and writes per-recipe invalid_plan artifacts
  instead of retrying the whole chunk serially. complete_many keeps its
  raise-on-first-error contract for single-item callers. Empty-completion
  errors are now self-describing (completion_tokens, finish_reason,
  raw_len, raw tail; optional HF_DEBUG_DUMP_DIR dump — commit d307b307),
  so the WHY of Air's empties (thinking-budget overrun vs genuinely empty)
  will be readable from the new lanes' plan-transport lines.
- Ops: cancelled 26145/26159/26160/26161 (their batches could not survive
  the first empty completion under the old code) and probe 26162 (held by
  the cluster: "user env retrieval failed" — this slurm rejects
  --export=ALL,VAR submissions; in-lane diagnostics replace it). Absorbed
  the 18 shard-generated plans into the canonical cache (109/650 total);
  re-split the 541 remaining ids 4-wide (shard_ids/air-plan2-{0..3}.txt)
  and resubmitted on the fixed code: jobs 26163-26166 (borrow, TP2,
  --exclude=<reserved-node>), run dirs
  local-thinking-20260817-air-plan2-{0..3}. Consolidation on completion:
  copy shard plans into the canonical plans dir and merge plan_execute rows
  into the canonical run.

## 2026-08-24 — Reproducibility hardening pass, stage 1: integrity audits (session B)

User directive: after this round, organize code and results for third-party
reproduction and verify everything strictly. Audits run and archived:

- Aggregation-layer audit: every `leaderboard.json` under `outputs/full_eval`
  (161 boards, canonical tier layout + thinking lanes + replan + shard dirs)
  recomputed in-memory from its `results.jsonl` with the canonical
  `metrics.aggregate.leaderboard` and diffed key-by-key. Result: 161/161
  exact (tolerance 5e-4 for float rounding), zero duplicate
  (recipe, variant, run_index) rows anywhere. A first naive audit pass that
  summed per-row composite fields flagged 11 old-schema react dirs; those
  were false positives of the naive method (pre-metric-fix rows store only
  boolean components; boards were legitimately regenerated via
  `scripts/recompute_leaderboard.py`) and are exact under the canonical
  aggregator.
- Row-level audit of the NEW replan mode (not covered by the 2026-08-21
  parity audit): frozen-manifest `scripts/verify_calacc_parity.py` over all
  4,917 replan artifacts in `replan-smallmed-20260823` (6 models). Result:
  4,917 rows compared, 0 score() exceptions, 0 side-effect / terminal /
  final mismatches. Manifest + result archived as
  `<maintainer archive>/parity_{manifest,result}_replan_20260824.txt`.
- Replan v2 finalization independently re-verified: six models at n=3220,
  `.pre-usermerge` quarantine dirs confirmed removed.
- Credential sweep: no secret patterns in tracked code/docs/scripts; only
  placeholder `.env.example` files; `results.csv` gitignored. A scan of
  `outputs/` trajectories for token patterns is running (result to be
  recorded when complete).
- Documented gap (to fix in stage 2, after in-flight lanes close):
  `doc/pipeline.md` lacks the replan review-turn protocol
  (`--max-replans`, fail-closed rejection rules) and the thinking-wave
  engine deviation (Muse-Glimmer + GLM-4.5-Air on the vLLM 0.27.1 muse
  env, lane env knobs); currently recorded only in this changelog.
- Outputs secret scan complete: full recursive regex sweep of `outputs/`
  (26 GB — trajectories, artifacts, plan caches) for Anthropic/HF/AWS
  token shapes and Bearer headers: zero matches. Pattern validity
  confirmed against a planted positive sample before recording.

## 2026-08-24 — Reproducibility hardening pass, stage 2: single-version tier layout (user directive)

User directive: keep only the latest version of every result, organize
everything under `outputs/full_eval/{small_model,medium_model,large_model}`,
and clean the remaining run/temp directories.

- Closed the two open lanes first:
  - **GLM-5.2-FP8-thinking react**: merged the three user-submitted shards
    (26057-26059; 3220 rows, zero overlap verified) into
    `large_model/GLM-5.2-FP8-thinking/react`; leaderboard recomputed via
    `scripts/recompute_leaderboard.py` (meta preserved from shard 0).
    Final: orchestration 0.6266, final 0.4891 (global was 0.1775/0.0929).
  - **GLM-4.5-Air-FP8-thinking global**: the four fixed-code shard runs
    (26163-26166) covered 2669/3220 rows; the remaining 551 rows (the 109
    recipes whose plans sat in the canonical cache) were produced by
    offline frozen-plan replay (`scripts/rescore_frozen_plans.py`, zero
    model access) over the assembled 333-artifact union. Strictness check
    before merging: the offline replay of the shard-covered rows agrees
    with the online shard verdicts on ALL 2669 overlap rows (status +
    all pass flags + all five composite metrics) — determinism confirmed.
    Merged canonical: n=3220, orchestration 0.1072, final 0.0425,
    error_rate 0.7463 (errors are genuine model behavior: schema-invalid
    plans, missing plan array, thinking burning the full 32768-token
    budget). React (already healed): 0.4949/0.3006. Both under
    `large_model/GLM-4.5-Air-FP8-thinking/`.
- **Physicalized the tier layout**: converted all 78 tier symlinks (into
  local-scale-ext-20260816, frontier-ext-20260816, replan-smallmed-20260823)
  to real directories by moving the target mode dirs into place; embedded
  `global/plans` for the six thinking entries verified present (~650
  recipes × 3 files each). No broken links, no clobbered physical data
  (`refresh_tier_views.py` is never-clobber and no-ops once run dirs are
  gone).
- **Archived everything else** (88 run/preflight/shard/probe dirs incl. all
  `.broken-*` quarantines — verified to contain only superseded or empty
  data — plus `outputs/logs`, `outputs/parity_audit`,
  `outputs/connector-runtime`, and all slurm stdout files) to
  `local_archive/full_eval_runs_archive_20260824/` (outside the public
  bundle; nothing deleted). `outputs/` now contains only `full_eval/` with
  the three tier dirs and the released comparison files.
- **Post-move verification**: canonical-aggregator audit over the final
  layout — 92/92 leaderboards reproduce exactly from their results.jsonl,
  zero duplicate rows, every board n=3220. `results.csv` regenerated (92
  rows) — includes the two new thinking entries.
- Docs updated for third-party reproduction: `doc/pipeline.md` gains §3b
  (replan review-turn protocol, fail-closed rejection rules,
  `--max-replans`) and §3c (engine environments: vLLM 0.24.0 standard;
  declared 0.27.1 muse-env deviation for Muse-Glimmer and thinking
  GLM-4.5-Air); README directory layout and canonical-results paragraph
  rewritten for the tier layout. `evaluation/global_react_models.json`:
  all thinking lanes marked completed with final headline numbers, stale
  statuses fixed (opus-thinking, gpt-5.6 lane, GLM-5.2 "preflight
  queued", Air "cancelled"), new `results_layout` section records the
  reorganization and archive location.

## 2026-08-24 — Two new comparison waves: thinking pairs + expanded replan budget (user request)

- **thinking-pairs-20260824** (`scripts/run_thinking_pairs.sbatch`, job
  26174): Qwen3-4B-Thinking-2507 and Qwen3-30B-A3B-Thinking-2507
  (dedicated thinking checkpoints, revisions pinned 768f209d / 144afc2f),
  plan_execute+react, thinking-wave caps (plan 32768 / react 16384, input
  98304). Matched non-thinking baselines already evaluated:
  Qwen3-4B-Instruct-2507 (small) and Qwen3-30B-A3B-Instruct-2507 (large).
  Purpose: extend the "thinking helps Global only where plan-schema
  competence exists" finding across scale with same-generation pairs.
- **replan-expanded-20260824** (`scripts/run_replan_expanded.sbatch`,
  jobs 26167 / resubmits 26176-26177): replan mode with --max-replans 6
  (cap-2 wave: replan-smallmed-20260823). Roster: three never-tested
  mediums with the largest ReAct-over-Global gaps (Qwen2.5-14B,
  gemma-4-12B, gemma-4-26B-A4B), two cap-2 repeats for a budget
  dose-comparison (Qwen3-4B, glm-4-9b), and Qwen3.8-27B non-thinking
  (lane 5) + thinking (lane 6, run suffix -think so the two fingerprints
  never share a plan-cache dir). Frozen plans pre-seeded from the tier
  layout (649-650 recipes per model; thinking plans 648; Qwen2.5-14B has
  no preserved cache and plans fresh); per-lane decoding caps match each
  model's plan-generation lane so cache keys hit.
- First-submit failures fixed and lanes resubmitted: glm-4-9b needs
  HF_TRUST_REMOTE_CODE=1 (as in its scale-ext lane); lane 6 needed the
  thinking-wave input clamp (98304 + 32768 = context); gemma-4-26B-A4B is
  TP2 and needs --gres=gpu:h200:2 at submit (launcher default is 1 GPU).
  All submissions borrow QOS with --exclude=<reserved-node>.
- **thinking-pairs v1 invalidated and rerun (26178)**: the pairs launcher
  omitted HF_THINKING_PREFIX=1 (set by every run_thinking_local lane).
  Qwen3 *-Thinking-2507 templates open <think> on the prompt side, so the
  decoded completion carries no opening tag and the balanced-JSON stop
  fired on the first JSON value quoted inside reasoning: plans were
  truncated mid-reasoning (global err ~0.99, "no plan array"), and every
  sampled react trajectory was unparseable_action ×3 → format_error_budget
  with zero real actions (rows read "ok" only because the loop terminated
  normally). v1 run dir quarantined to
  local_archive/full_eval_runs_archive_20260824/thinking-pairs-20260824.broken-no-thinking-prefix
  (plans regenerate — cached artifacts moved with it); jobs 26174 killed.
  Fix committed to scripts/run_thinking_pairs.sbatch; full rerun submitted.
- **thinking-pairs v2 stall root-caused and fixed (jobs 26183 killed)**:
  with HF_THINKING_PREFIX=1 the vLLM stop processor's pre-</think> scan
  joined and re-searched the full transcript on every decode step —
  O(n^2) per stream; 650 concurrent 30K-token thinking streams turned the
  batched planning call into terabytes of string scanning (4.65 h, zero
  artifacts; the react long-action soft-limit search had the same shape).
  Both searches are now incremental with rolling cross-chunk tails
  (`</think>`: 7-char tail; long-action regex: 120-char tail), semantics
  unchanged (verified by offline closure tests: reasoning-quoted JSON
  still never stops generation; split tags detected; non-prefix mode
  identical). The dead full-transcript buffer was removed. Synced to
  benchmark/shared. v2 run dir (empty) reused; wave resubmitted.
- **thinking-pairs throughput**: probe (26188, 3 recipes) confirmed the
  incremental-scan fix — 3 valid-pipeline plans in 3m48s, raw responses
  properly stripped past </think>, plan JSON reaching schema validation.
  The single-batch full wave stays KV-bound (planning prompts are tens of
  K tokens; with the 32768 thinking budget only single-digit sequences
  fit an H200's cache), projecting ~8 h per model. 26186 killed; wave
  resharded 4-wide per model on idle nodes (seeded shuffle, shard_ids/
  pairs-0{0..3}.txt, 161-165 recipes each): jobs 26189-26192, run dirs
  thinking-pairs-20260824-s{0..3}, both models per shard, modes
  plan_execute,react; merge + recompute on completion (the Air-wave shard
  pattern). Probe run dir thinking-pairs-probe kept for the record.

## 2026-08-24 — Replan scale ladder (user request, user-submitted)

Does mid-course repair grow with scale above the 27B emergence point?
Seven checkpoints spanning 24B dense → 110B MoE, replan mode,
--max-replans 6 (`scripts/run_replan_scale.sbatch`, run
replan-scale-20260824): Mistral-Small-3.1-24B, gemma-3-27b,
Qwen3-30B-A3B, c4ai-command-r-32B (TP1 group, job 26202) and
Llama-3.3-70B, Qwen2.5-72B, GLM-4.5-Air-FP8 (TP2 group, job 26203,
queued behind the pairs wave). Frozen plans pre-seeded from tier
global-plans (649-650 each, caps 4096/8192 match — full cache hits).
Jobs submitted by the user after reviewing the prepared launcher.

## 2026-08-24 — Local View (incremental_workflow) wave prep: editor fail-closed fix

User directive: run the Local View ablation over the full replan roster.
Probes (26216 Qwen3-4B, 26217 Qwen3.8-27B; 3 recipes) exposed a doomed-
session trap before scale-up: a model that closes the node object one
brace early puts ``bind`` (and other node fields) at the action's top
level; ``parse_incremental_plan_action`` silently ignored stray top-level
keys, so the editor accepted a bind-less call node — and with an
immutable prefix nothing could ever reference that result, burning the
remaining 63 editor turns (both models, same two recipes; 27B built
recipe 100191269 cleanly in 9 turns, proving the protocol itself sound).
Fix: stray top-level keys on append_node are now rejected fail-closed
with explicit feedback naming the keys and pointing them into the node
object (new ``invalid_action`` parser result + editor-loop branch).
Parser unit-tested; synced to benchmark/shared. Probes rerun on fresh
run names before the 17-lane wave (invalid_plan artifacts are
cache-reused, so reruns must not share the probe run dirs).
- Probe3 (26220): after the two editor fixes Qwen3.8-27B builds ALL three
  probe plans cleanly (12/8/7 turns, 10/5/5 nodes) — protocol green.
  Qwen3-4B's remaining failures are honest (schema errors with per-turn
  diagnostics; recipe 100191269 is a genuine context overflow: its Local
  View prompt tokenizes to 126,036 > the 122,880 pinned input limit for
  that tokenizer, kept as a zero-scored error row per the Muse
  over-context precedent). Full 17-lane wave submitted: 26221 (TP1 ×12),
  26222 (TP2 ×4: gemma-4-26B-A4B, Llama-3.3-70B, Qwen2.5-72B, GLM-4.5-Air),
  26223 (Qwen3.8-27B thinking, run local-view-20260824-think).
- Scale-ladder caveat — GLM-4.5-Air replan headline (0.0839) is NOT
  comparable to its global (0.1228): plan errors are row-identical
  (2375=2375, shared frozen plans), and the entire gap is 274 review-turn
  rows lost to the known vLLM 0.24.0 Air empty-completion behavior
  (llm_error "model returned no text", absent from global; the canonical
  non-thinking react lane never triggered it, replan review prompts do).
  Apples-to-apples on the identical 2946-row subset excluding those rows:
  replan 0.0917 vs global 0.0899 (+0.0018, noise-level — consistent with
  the rest of the ladder). Recorded as-is; do not read the headline delta
  as "replanning hurts Air".
- **replan-scale Air anomaly root-caused**: GLM-4.5-Air replan (0.0839)
  reads 3.9 points BELOW its global baseline (0.1228). Autopsy: 270 rows
  that scored in global die in replan as review-turn llm_errors — Air's
  template-default untagged inline reasoning hits the balanced-JSON early
  stop on the first bracket pair quoted in its reasoning prose (e.g.
  "(columns: [])"; finish_reason=stop at tens-to-hundreds of tokens, no
  action extracted). HF_THINKING_PREFIX cannot help (no </think> marker
  to wait for). Only 19 genuinely-replanned rows differ from global;
  the regression is transport contamination of ~800 extra short review
  turns, not model repair behavior. Pending user decision: annotate-and-
  exclude Air from the replan ladder (recommended; keeps canonical
  fingerprints aligned) vs. a thinking-disabled paired rerun.

## 2026-08-25 — Thinking pairs merged + replan scale ladder complete

- **thinking-pairs-20260824 merged** (5 shard runs s0/s1/s2/s2a/s2b + s3;
  3220/3220 unique rows per model/mode verified; leaderboards recomputed;
  physicalized to small_model/Qwen3-4B-Thinking-2507 and
  large_model/Qwen3-30B-A3B-Thinking-2507). Findings (vs same-generation
  Instruct-2507 baselines):
  - Qwen3-4B: thinking HURTS Global View (0.1025 vs 0.1375) while helping
    ReAct (0.4734 vs 0.4184). At 4B the model cannot convert reasoning
    into a valid one-shot plan — reasoning even degrades plan grammar —
    but interactive stepwise use of the same reasoning helps.
  - Qwen3-30B-A3B: thinking helps BOTH Global (0.1475 vs 0.0835, +0.064)
    and ReAct (0.5209 vs 0.4781, +0.043).
  - Combined with the earlier wave (27B +0.045 global; GLM-4.5/V4-Flash
    hurt): test-time reasoning helps Global View only above a
    plan-competence threshold, and the threshold is model-specific, not
    purely scale.
- **replan-scale-20260824 complete** (7 models, 24B dense → 110B MoE,
  cap 6): no ladder point exceeds noise — Mistral-24B +0.0033,
  gemma-3-27b −0.0005, Qwen3-30B-A3B +0.0017, command-r-32B +0.0023,
  Llama-3.3-70B +0.0002, Qwen2.5-72B +0.0038, GLM-4.5-Air +0.0018
  (conditional subset; headline is the documented engine artifact).
  Qwen3.8-27B (+0.0083) remains the single positive outlier: mid-course
  repair does not emerge with scale per se. results.csv now 106 rows;
  manifest ablation_runs gains thinking-pairs-20260824 and
  replan-scale-20260824 sections. Spurious requeue of completed
  command-r lane (26202_3) cancelled.

## 2026-08-25 — Comparison waves finalized: thinking pairs + replan ladder consolidated into tier layout

- **thinking-pairs merged** (5 shards for 4B incl. the s2a/s2b re-split;
  4 for 30B): 3220 unique rows asserted per model/mode, plans 649 each,
  leaderboards recomputed. Final: Qwen3-4B-Thinking global 0.1025 / react
  0.4734 (vs Instruct global 0.1380 — thinking is a net LOSS at 4B);
  Qwen3-30B-A3B-Thinking global 0.1475 / react 0.5209 (vs 0.0835 /
  0.4781 — thinking nearly doubles Global at 30B). Together with
  Qwen3.8-27B (+0.045) this pins the thinking-gain-on-Global crossover
  between 4B and ~27B. Tier entries small_model/Qwen3-4B-Thinking-2507
  and large_model/Qwen3-30B-A3B-Thinking-2507.
- **replan ladder consolidated**: replan-scale seven models moved to
  large_model/<model>/replan; replan-expanded's three new mediums to
  medium_model/<model>/replan; Qwen3.8-27B-FP8-thinking/replan added.
  The cap-6 dose-repeat dirs for Qwen3-4B / glm-4-9b / Qwen3.8-27B stay
  archived (tier keeps the canonical cap-2 wave; numbers identical to 4
  decimals). GLM-4.5-Air's replan is annotated EXCLUDED in the manifest
  (review-turn transport contamination, root cause in the 2026-08-24
  entry). Ladder conclusion recorded in the manifest: no scale emergence
  of mid-course repair 24B→72B (deltas ±0.004); Qwen3.8-27B stays the
  only positive case.
- Run dirs archived to local_archive/full_eval_runs_archive_20260824/
  (replan-scale, replan-expanded[-think], thinking-pairs shards + probe);
  shard_ids restored under full_eval (pairs id splits, kept while user
  waves may reference them). The user's local-view-2026082x runs are
  untouched and in flight.
- Post-consolidation audit: 112/112 leaderboards (tier layout + in-flight
  local-view run dirs) reproduce exactly from raw rows under the
  canonical aggregator; results.csv regenerated (107 rows).

## 2026-08-25 — Model-I/O solidity audit (pre-publication) + Air local-view engine rerun

- **Air local-view invalidated & rerunning**: the 0.24 lane "completed" in
  ~3h with 3220 rows but only 20/650 plans — editor-turn calls hit the
  known GLM-4.5-Air empty-completion behavior (same class as its replan
  review turns). Output quarantined
  (local-view-Air*.broken-v024-empty-completions); lane 14 resubmitted on
  the muse env / vLLM 0.27.1 (job 26250), the same declared deviation as
  its thinking lanes (launcher now encodes the per-lane engine switch).
- **I/O audit, all green**:
  1. Gold-leakage scan over model-visible planner inputs (25 sampled
     recipes × marker + concrete hidden-variant value probes): zero hits.
  2. Thinking-strip check over 120 sampled thinking-lane react
     trajectories (27B/4B-Thinking/Air): zero <think> remnants in scored
     fields.
  3. React observation sanity (30 rows): no simulator internals
     (_state_root/seeds/gold paths) in observations.
  4. Qualitative per-setting samples (global raw→plan, react turn
     structure, replan review event, live local-view editor steps) all
     structurally correct.
  5. **Prompt provenance closure**: artifacts store
     system_hash/user_hash/public_package_hash; re-deriving prompts via
     the vendored `initial_plan_context` reproduces all three hashes
     bit-exact on 15/15 sampled artifacts across Qwen3.8-27B,
     Qwen3-4B-Instruct, and claude-opus-5-thinking. (A naive
     hash-the-.txt-file check does NOT match by design: the recorded hash
     is over the rendered prompt's canonical JSON.)
- Slurm requeued the killed 0.24 Air lane (26222_14 came back RESIZING→
  RUNNING after the node-pin) and raced the 0.27.1 rerun (26250) on the
  same run dir for ~75 min. Both killed; the 16 ambiguous-provenance plan
  artifacts (no way to distinguish engine of origin from the cache key —
  the decoding fingerprint does not include the engine) plus the Air
  state root were wiped, and lane 14 resubmitted clean on 0.27.1 as job
  26251. Provenance certainty over 1.2 h of redone compute.
- Air local-view root cause FOUND (three failed attempts deep): the
  "empty completions" on 0.27.1 were never empty — raw responses carried
  ~14K chars ending in valid plan JSON, but the 0.27.1-era chat template
  defaults enable_thinking=true for the GLM family and Air emits
  unclosed-<think> inline reasoning that _strip_thinking reduces to empty
  text (the 0.24 template never injected the switch, which is why the
  canonical global/react lanes were fine; the 0.24 replan review-turn
  empties were genuinely empty — same symptom, different disease). Fix:
  lane 14 pins HF_CHAT_TEMPLATE_KWARGS enable_thinking=false on the muse
  env, matching the GLM-5.2 canonical protocol. Probe 26255: 2/3 clean
  plans (14/11 editor turns), third a genuine schema failure, zero
  no-text rows. v2 output quarantined
  (local-view-Air*.broken2-default-thinking-strip); full lane resubmitted.

## 2026-08-26 — Local-view treadmill root-caused and fixed

Seven low-editor-compliance lanes froze for ~20 h across multiple
preemption restarts (zero new artifacts, logs silent after engine init).
Root cause: a doomed editor session's conversation grows ~4K tokens per
rejected turn until the prompt exceeds the pinned input limit (~turn 28);
the LLMError propagated out of prepare_incremental_plan, the call site
recorded only an IN-MEMORY invalid_plan, and nothing reached the disk
cache — so every preempted-and-resumed incarnation re-ran the same doomed
sessions (~1 h each, serial) from scratch, forever. High-compliance
models finish sessions in ~10 turns and never hit the limit, which is why
their lanes completed. Fix: the editor loop now catches per-turn client
exceptions, records "editor session aborted at turn N: ..." and falls
through to the normal artifact write, so the failure is CACHED and resume
skips it (unit-tested: abort artifact on disk, resume reuses with zero
model calls). Synced to benchmark/shared. All incomplete lanes restarted
on the fixed code; two spurious requeues of already-boarded lanes
(gemma-3-27b, Mistral-Small) cancelled.
- Follow-up: even with aborts cached, doomed sessions run 1-3 h each and
  the planning loop is serial — the remaining low-compliance lanes
  projected to weeks (log-based progress monitoring was also debunked:
  python planning prints only flush at process exit, so disk artifacts
  are the sole live progress signal). Added a concurrency-gated
  cache-warmer pass (VLLM_PLANNER_CONCURRENCY, default 1 = unchanged
  behavior): independent editor sessions run concurrently through the
  engine exactly like react turns, populating the per-recipe disk cache;
  the unchanged serial loop then consumes pure cache hits. Launcher sets
  concurrency 12. Sessions are per-recipe independent, artifact dirs
  disjoint, and concurrent llm.complete is the proven react path, so
  protocol and artifacts are bit-identical to serial execution.
- Concurrency fix VALIDATED by in-process stack dumps (new
  HF_STACK_DUMP_SECONDS/HF_STACK_DUMP_DIR knobs in evaluation/full_eval.py
  — faulthandler.dump_traceback_later, since srun --overlap is disabled
  here): the snapshot that looked like an engine hang was a normal 12-wide
  batched turn (leader inside LLM.generate, 11 waiters at the batching
  barrier); artifacts confirmed landing (Nemo 364→365+). Doomed-session
  cohorts complete in ~30-60 min at 12-way vs ~1-3 h EACH serial. Also
  corrected an earlier misdiagnosis for the record: the artifact set is
  NOT an in-order prefix — the "missing" recipes are exactly the sessions
  the pre-fix code aborted without caching (scattered, ids[0] included).

## 2026-08-26 — Local-view tail resharded for full utilization (user directive)

User directive: use the full <owner-qos> allowance plus every borrowable GPU.
The 8 serial tail lanes (preemption churn from concurrent SFT jobs kept
truncating ~1 h 12-way cohorts) were cancelled and replaced by 16 disjoint
shard jobs (26337-26352): per remaining model, the full 650-id list
seeded-shuffle split 2-4 ways (width ∝ remaining sessions: 27B-thinking 4,
command-r 3, Nemo/14B/72B 2, others 1), each shard run dir pre-seeded with
a copy of the model's existing incremental_plans so completed sessions are
pure cache hits and only missing sessions generate. Disjoint id sets rule
out any concurrent-writer races by construction. On completion: per-model
merge of shard rows (must total 3220 unique) + leaderboard recompute, the
same consolidation pattern as the thinking-pairs and Air waves. 8 shards
started immediately (7 borrow + 1 <owner-qos> headroom), 8 queued behind the
SFT jobs.
- Flight-recorder verdict: with async scheduling off the wave is fully
  healthy — glm9b and gemma-3-12b shards completed all 650 planning
  artifacts within ~2.5 h (5,347 editor-turn requests, batch histogram
  414×11-wide lockstep + 491 stragglers); the lone "begin without done"
  was a preempted-and-requeued job's killed batch, not a wedge (the
  discriminator now checks job liveness). Node-clock skew makes
  find -newermt unreliable across NFS — artifact totals are the only
  trustworthy progress signal. Whether the original 2 h freeze was the
  async-scheduling race alone remains unproven either way; async stays
  off for this wave (engine-internal, decoding-neutral).

## 2026-08-27 — Local-view consolidation begins: merge tool + 15/17 models physicalized

New `scripts/merge_local_view_shards.py`: reassembles one canonical
`<tier>/<model>/local` mode dir from shard mode dirs with hard verification
(rows disjoint on (recipe, variant, run_index); union == the full 650-recipe
manifest; trajectories unique on task_id; artifact/plan filename collisions
allowed only when byte-identical — these are the pre-seeded cache copies;
leaderboard recomputed from merged rows via the canonical aggregator, never
summed from shard boards; shard meta carried with per-process counters summed
and a `merged_from` provenance block). Invariant on plans: every recipe with
at least one executed (non plan_error) row must have its frozen plan on disk;
recipes whose editor session aborted before any plan existed (pre-treadmill-fix
sessions) legitimately have rows but no plan artifact and are counted in the
summary as `planless_aborted_recipes`, not papered over.

Physicalized with this tool (each verified 3220 rows / 650 recipes):
- merges: Nemo (s0+s1, orch 0.0039), Qwen2.5-14B (s0+s1, 0.0999),
  Qwen3.8-27B-thinking (s0-s3, 0.4154, final_acc 0.2273)
- single-source copies through the same verification path: Qwen2.5-3B 0.2275,
  Qwen3-4B 0.0690, Qwen3-30B-A3B 0.0848, Qwen3.8-27B 0.3276 (thinking gain
  +0.088), gemma-3-27b 0.1262, gemma-4-12B 0.1067, Llama-3.3-70B 0.3491,
  Mistral-Small-24B 0.2726, GLM-4.5-Air 0.1898, gemma-4-26B-A4B 0.0635,
  gemma-3-12b 0.1645, glm-4-9b 0.0445

Still running: command-r (s0 resubmitted as 26480 after job 26367 died to a
one-off vLLM segfault and sat unnoticed ~32 h; s1/s2 live) and Qwen2.5-72B
(s0/s1 live, TP2) — planning at 440/650 and 372/650 unique recipes. On their
completion: same merge + the layout-wide aggregator audit, results.csv local
column, and manifest ablation entry.

## 2026-08-28 — Replan protocol v2 (user request): smoke on 5 models x 100 recipes

Why: the row-level audit of canonical replan (27B: 1807 paired rows) showed
replan ≈ global for three structural reasons — (a) 197/1807 rows die at
`plan_resolution_error` with zero reviews (resolver exceptions bypass
`maybe_replan`); (b) ~640 rejected replans, 396 "malformed JSON", the rest
schema errors (`bind duplicates binding`, forward refs) — rejection was
silent and single-shot, and rejected rows' plans are 2x longer; (c) accepted
replans (336) fix the local symptom but the dominant failure is
`resource_xxx is not part of the seeded benchmark state` (table_id grounding)
so 280/290 accepted rows still fail. Only 3 fail→pass / 1 pass→fail flips.

Protocol v2 (`--replan-protocol v2`, default `v1`; mode string stays `replan`
so scoring/leaderboard plumbing is untouched and canonical v1 numbers are
reproducible bit-for-bit; `verification/backends/shared/src/task/{agents,runner,run_eval}.py`,
`metrics/aggregate.py`):
- F1 resolver errors are routed through the review as `ERROR:` observations
  (v1: row ends). Same fail-closed rules; an error inside a review turn is
  never re-reviewed.
- F2 a rejected revision gets ONE repair turn carrying the validator error
  verbatim (not offered when the cap is hit); second rejection continues on
  the current plan exactly like v1.
- F3 `{"type":"patch","node_id":..,"node":{..}}` replaces one unexecuted
  node; the runner derives the unexecuted suffix from its execution frames
  (top level / pending if-branches only; inside foreach/repeat/try or a
  partial call expansion the patch is rejected with an explanatory error)
  and validates the whole suffix with the same `normalize_plan`. Each
  observation lists the patchable ids; after acceptance the model is shown
  the normalized workflow so later patches can address real ids.
- F4 error observations restate the public workspace cards
  (public_id / name / resource_ref / fields; already in the first turn's
  PUBLIC WORKFLOW CONTEXT — no new information) next to the error.
- Not changed: continue-on-success (no gold signal), initial-plan failures
  (shared with Global by design), max_replans (2→6 shown non-binding),
  HF_MAX_NEW_TOKENS (4096, review-turn parity with v1).
- Attribution counters per row + leaderboard: `replan_rejected_count`,
  `replan_repair_offered_count`, `replan_repair_accepted_count`,
  `replan_patch_accepted_count`, `replan_resolver_review_count`,
  `replan_resolver_accepted_count`; meta `replan_protocol`.
- Tests: `verification/backends/shared/src/tests/test_replan_v2.py` (19; v1
  semantics pinned). Offline scripted selftest: v1 unchanged (0 errors, 0
  repair turns), v2 exercises the new counters.

Smoke (`scripts/run_replan_v2_smoke.sbatch`, run `replan-v2-smoke-20260828`,
jobs 26525 lanes 0-2,4 + 26526 lane 3 (TP2), borrow QOS, --exclude a colleague's reserved
node): Qwen3.8-27B-FP8, Qwen3-4B, gemma-3-27b, gemma-4-26B-A4B, Mistral-24B;
per model 100 recipes (gemma-26B: all 86 eligible) drawn from recipes with a
VALID frozen plan and a v1 replan artifact (replan cannot act on plan_error
rows), coverage-first then seeded shuffle (`scripts/select_replan_v2_smoke_ids.py`,
seed 20260828, 17 recipes common to all five). Plans pre-seeded from tier
global-plans (0 planner calls). Paired comparison vs tier v1 rows:
`scripts/compare_replan_v2_smoke.py`. Pre-registered decision rule: promote
to the full 3,220 only if Δorch ≥ +3 pts on ≥3/5 lanes and no lane ≤ −1 pt.
Note: 27B/4B v1 tier rows ran at max_replans 2 (cap shown non-binding: 22
limit rejections in 1807 rows), the other three at 6.

## 2026-08-28 — Replan v2 smoke complete: verdict DO NOT PROMOTE

All five lanes finished (0 planner calls — pre-seeded caches byte-identical;
4B 59 min, 27B 70 min per lane on 1xH200). Paired vs tier v1 rows,
orchestration accuracy (`outputs/full_eval/replan-v2-smoke-20260828/compare_v1_v2.{md,json}`):

| lane | rows | v1 | v2 | Δ pts [CI95] | fail→pass / pass→fail | accepted v1→v2 |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-FP8 | 457 | 0.5685 | 0.5816 | +1.31 [+0.42, +2.34] | 0 / 0 | 97→215 |
| Qwen3-4B | 452 | 0.3622 | 0.3639 | +0.18 [−0.11, +0.53] | 2 / 1 | 63→365 |
| gemma-3-27b | 459 | 0.3582 | 0.3495 | −0.87 [−1.94, +0.11] | 4 / 0 | 146→697 |
| gemma-4-26B-A4B | 347 | 0.4069 | 0.3821 | −2.48 [−4.58, −0.49] | 2 / 13 | 118→299 |
| Mistral-Small-24B | 457 | 0.4182 | 0.4193 | +0.11 [−0.98, +1.18] | 0 / 2 | 99→443 |

Pre-registered rule (≥3 lanes at +3, none ≤ −1): 0 lanes clear the bar,
one regresses → v2 is NOT promoted to the full benchmark. Canonical replan
(v1) rows stay the published numbers; `--replan-protocol` defaults to v1.

Findings (mechanism counters + row audit):
- The protocol changes fire as designed — 2–5x more accepted revisions,
  repair turns rescue 25–30% of rejections, patches are used heavily — but
  accepted revisions overwhelmingly leave the row's score unchanged
  (27B: 114 rows with an accepted revision → 18 up / 6 down / 90 same).
  27B's +1.31 is partial-credit (tool_selection/order/condition_path +14
  each), zero full fail→pass flips. Top remaining error is still
  `workato_db_table X is not part of the seeded benchmark state`: the model
  swaps one wrong table id for another even with the cards restated (F4).
  Conclusion stands: the binding constraint is initial-plan resource
  grounding, not the review protocol.
- F1 (resolver-error review) is net NEGATIVE: accepted resolver-triggered
  revisions 3 up / 19 down across lanes, 15 on gemma-26B — all its 13
  pass→fail rows. Those rows crashed at step 0 in v1 with zero calls and
  passed vacuously (gold = no business call on that branch); v2 let the model
  "repair" the expression and then execute writes gold never makes. v1 was
  passing by crashing; the models do not know the answer is "do nothing".
- Context growth is a real v2 cost: gemma-3-27b lost 13 rows (3.8 orch
  points) to `prompt exceeds pinned limit 122880` after up to 6 accepted
  revisions each appending the normalized workflow; net of those rows it is
  exactly flat (0.3601 vs 0.3596). Any v2.1 must cap/drop the
  "REPLAN ACCEPTED" workflow dump.
- Tool-error-triggered revisions are mildly positive (65 up / 30 down over
  all lanes), success-observation revisions 30 / 8 — i.e. F2/F3 help at the
  margin, F1 hurts, and none of it moves outcomes.
- Ops: gemma-26B lane preempted twice under borrow QOS (auto-requeued, the
  second requeue after completion was cancelled); no other incidents.

## 2026-08-29 — Replan redefined as self-evolution: iterative replan smoke launched

User clarification: the replan setting exists to ask whether a model can
improve WITHOUT parameter updates, purely by revising its own previous plan
from feedback (self-evolution). The canonical `replan` mode (mid-execution
suffix revision) is one narrow instance of that and, as shown on 2026-08-28,
cannot move the score: it never touches the 44% plan_error rows and the
binding failures are grounding errors made at planning time.

New evaluation `evaluation/replan_iter.py` (mode `replan_iter`): round 0 =
the frozen Global plan (pre-seeded cache, invalid plans included; verified
bit-identical to the Global rows on 4 recipes / 15 rows); round k = execute
the current plan on every variant with fresh simulator state (plan_execute
semantics, no runtime LLM call), show the model [planner prompt, its previous
plan as the assistant turn, EXECUTION FEEDBACK] and take one complete revised
plan, validated with the initial-plan validator; invalid revision → keep the
previous plan (fail-closed, the validator error is fed back next round).
Feedback = model-visible environment output only: validator error, each
call with args + observation/error, branch/loop markers, terminal return,
per variant with its trigger input — never gold calls/state/verdicts. Note
the plan is therefore no longer variant-blind after round 0 (it sees the
variants' trigger inputs and observations); that is the definition of
test-time environment interaction and is documented as such. Every round is
scored with the canonical scorer → accuracy-vs-round curve
(`<run>/<model>/replan_iter/curve.json`, per-round `round_k/results.jsonl` +
leaderboard, `plans/round_k/<recipe>.json` with the exact feedback text).
Tests: `verification/backends/shared/src/tests/test_replan_iter.py` (8).

Smoke (`scripts/run_replan_iter_smoke.sbatch`, run `replan-iter-smoke-20260829`,
jobs 26547 lanes 0-2,4 + 26548 lane 3 TP2 (26542/26543 died at startup on a missing build_client import, fixed), borrow QOS, --exclude a colleague's reserved
node): same five models; 100 recipes seeded from the FULL manifest
(`scripts/replan_iter_smoke/ids.txt`, seed 20260829, identical across
models, plan_error recipes included); K=3 rounds, full-trace feedback.
Cost per lane ≈ 300 planner-size revision calls + 4x ~500 deterministic
executions. Pre-registered read-out: Δorch(round 3 − round 0) per model;
"self-evolution works" if ≥ +3 pts on ≥3/5 models with no model ≤ −1; also
report valid-plan count per round (the plan_error pool is where the most
room is) and paired flips vs round 0.

## 2026-08-29 — Iterative replan smoke: rule met; full-benchmark run launched

Smoke `replan-iter-smoke-20260829` (100 recipes / 489 rows per model, K=3,
full-trace feedback), orchestration accuracy round 0 → round 3
(round 0 == Global, verified):
Qwen3.8-27B 0.3297 → 0.4217 (+9.2; final 0.143 → 0.221; 84 rows up / 9 down),
gemma-4-26B 0.0466 → 0.1065 (+6.0), gemma-3-27b 0.0552 → 0.1086 (+5.3),
Mistral-24B 0.1757 → 0.2123 at round 2 (+3.7; round 3 resumed after a
preemption), Qwen3-4B 0.1793 → 0.2080 (+2.9). Pre-registered rule
(≥ +3 on ≥3/5, none ≤ −1) is met → full run submitted immediately:
`replan-iter-full-20260829`, jobs 26562 (lanes 0-2,4) + 26563 (lane 3 TP2),
650 recipes (`scripts/replan_iter_smoke/ids_full.txt`), same launcher and
protocol, borrow QOS. Expected wall time from smoke scaling (x6.6): 27B ~10 h,
Mistral ~7 h, gemma-3-27b ~6 h, 4B ~4.5 h, gemma-26B ~2 h — queue wait on top
(cluster 100% allocated at submission).

Attribution (per-row Δ by plan-status transition, smoke): for four models
the gain is almost entirely invalid→valid repair driven by the validator
error (4B +3.0 of +2.9 net, gemma-3-27b +5.3 of +5.3, gemma-26B +5.3 of +6.0,
Mistral +3.2 of +3.7); only 27B also improves already-valid plans from the
execution trace (+3.1 pts over 317 rows, on top of +5.2 from repairs). ~70%
of revisions are still rejected; the "no plan array" ones are genuine model
errors (JS-style string concatenation inside JSON), not a parser bug. Curves
flatten after round 2 for the small models; K=3 is sufficient.

## 2026-08-29 — Iterative replan smoke COMPLETE (all five lanes, K=3)

Final smoke curve (`replan-iter-smoke-20260829`, 100 recipes / 489 rows per
model; `smoke_summary.json` in the run dir), orchestration accuracy
round 0 (= Global) → round 3:

| model | r0 | r3 | Δ | final r0→r3 | valid plans r0→r3 | rows up/down |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-FP8 | 0.3297 | 0.4217 | +9.2 | 0.143→0.221 | 66→77 | 84/9 |
| Mistral-Small-24B | 0.1757 | 0.2524 | +7.7 | 0.104→0.137 | 43→58 | 80/5 |
| gemma-4-26B-A4B | 0.0466 | 0.1065 | +6.0 | 0.012→0.068 | 17→28 | 68/0 |
| gemma-3-27b | 0.0552 | 0.1086 | +5.3 | 0.020→0.039 | 19→31 | 74/0 |
| Qwen3-4B | 0.1793 | 0.2080 | +2.9 | 0.070→0.076 | 48→58 | 48/5 |

4/5 lanes ≥ +3, none negative → rule met (recorded before the full run was
launched). Ops: the Mistral smoke lane was preempted twice; the second
requeue came after round 3 had completed and was cancelled. Full run
`replan-iter-full-20260829` in flight: jobs 26562_0 (27B), 26562_1 (4B),
26568_2 (gemma-3-27b, resubmitted after a stale-NFS read of the pre-fix
driver), 26563_3 (gemma-26B), 26562_4 (Mistral). Driver fix 2026-08-29:
an initial-planning failure (recipe 59838285's planner prompt exceeds the
122,880-token input cap for every model) is now a per-recipe plan_error, not
a crash. Full-run round-0 baselines reproduce the published Global numbers
(4B 0.1375, gemma-26B 0.0405, Mistral 0.1415 exact; gemma-3-27b 0.0738 vs
0.0741 = that one recipe). Local-view jobs 26370_13/26371_13/26480_11 were
cancelled on user request to free GPUs for the full run.

## 2026-08-29 — Full run: gemma-26B lane complete; other four lanes moved to <owner-qos>

- gemma-4-26B-A4B full curve (3,220 rows): 0.0405 → 0.0658 → 0.0872 →
  **0.0982** (+5.8 pts, 2.4x Global); valid plans 86 → 169; 434 rows up /
  13 down; final 0.018 → 0.039. Job 26563_3.
- User request: switch off borrow QOS. Running jobs cannot change QOS in
  place, so the four in-flight borrow lanes (26562_0/1/4, 26568_2; all in
  their round-1 revision batch, nothing on disk beyond round 0) were
  cancelled and resubmitted under `--qos=<owner-qos>` as job 26584
  (lanes 0-2,4), resuming from the cached round-0 rows/plans. <owner-qos> has a
  24-GPU per-user cap shared with the training jobs (16 in use), so the 4
  TP1 lanes fit.

## 2026-08-29 — Three more models added to the full self-evolution run (user request)

To use the remaining <owner-qos> headroom (24-GPU cap; training 16 + replan 4):
lanes 5-7 appended to `scripts/run_replan_iter_smoke.sbatch` and submitted
under <owner-qos> — DeepSeek-V4-Flash-0731 (TP2, fp8 KV, deep_gemm,
HF_PROMPT_IDS=1, VLLM_ASYNC_SCHEDULING=0, as in its frontier lane; job
26589_5, pending 2 co-located GPUs), gemma-4-12B-it (26588_6) and
Qwen3-30B-A3B-Instruct-2507 (26588_7), both TP1 and running. All three have
tier global-plans caches (650/649/650 plans) so round 0 == Global
(0.2701 / 0.1426 / 0.0835). Rationale: DeepSeek is the strongest open model
on Global (does self-evolution scale with capability?), gemma-4-12B completes
the gemma-4 family (12B/26B/31B), Qwen3-30B-A3B adds a MoE mid-tier point.
Roster is now 8 models: 27B, 4B, gemma-3-27b, gemma-4-26B (done), Mistral,
DeepSeek-V4-Flash, gemma-4-12B, Qwen3-30B-A3B.

## 2026-08-29 — Full self-evolution run: 7/8 lanes complete; 27B lane hung and rerun

Full 3,220-row curves (`replan-iter-full-20260829`, K=3, round 0 == published
Global; per-row attribution = Δ from invalid→valid plan repair vs Δ from
revising already-valid plans):

| model | Global | r1 | r2 | r3 | Δ | final | valid plans | up/down | repair | revise-valid |
|---|---|---|---|---|---|---|---|---|---|---|
| DeepSeek-V4-Flash | 0.2701 | 0.3314 | 0.3511 | **0.3576** | +8.7 | 0.114→0.154 | 382→466 | 591/69 | +7.2 | +1.5 |
| Mistral-Small-24B | 0.1415 | 0.1933 | 0.2105 | **0.2176** | +7.6 | 0.061→0.089 | 222→339 | 617/43 | +7.1 | +0.5 |
| gemma-4-26B-A4B | 0.0405 | 0.0658 | 0.0872 | **0.0982** | +5.8 | 0.018→0.039 | 86→169 | 434/13 | +5.4 | +0.4 |
| gemma-4-12B | 0.1426 | 0.1784 | 0.1869 | **0.1919** | +4.9 | 0.041→0.059 | 236→315 | 411/18 | +4.5 | +0.4 |
| Qwen3-4B | 0.1375 | 0.1692 | 0.1827 | **0.1863** | +4.9 | 0.039→0.048 | 265→350 | 436/11 | +4.9 | −0.0 |
| Qwen3-30B-A3B | 0.0835 | 0.1060 | 0.1126 | **0.1176** | +3.4 | 0.029→0.049 | 163→203 | 302/28 | +2.7 | +0.7 |
| gemma-3-27b | 0.0738 | 0.0989 | 0.1029 | **0.1034** | +3.0 | 0.026→0.035 | 147→203 | 299/13 | +2.9 | +0.1 |
| Qwen3.8-27B | 0.2857 | — | — | — | rerun | | | | | |

Every completed lane improves monotonically; 7/7 ≥ +3 pts; regressions
≤ 69 rows. Round 1 carries 55–70% of the total gain; curves flatten by
round 3. Gains remain dominated by validator-driven invalid→valid repair;
DeepSeek (+1.5) is the only lane besides 27B (smoke: +3.1) with a material
gain from revising valid plans using the execution trace.

27B lane (26584_0) hung: no output after 01:19 for 13.5 h at the start of the
650-prompt round-1 revision batch (Qwen3.5 hybrid GDN/mamba kernels; same
class of freeze as the 2026-08-2x frozen-plan batches). Cancelled; driver now
generates revisions in chunks (`--llm-chunk`, default 32, env
REPLAN_ITER_LLM_CHUNK) writing each chunk's plans immediately (progress +
resume granularity), and the 27B lane runs with VLLM_ASYNC_SCHEDULING=0
(engine-internal, decoding-neutral). Stub-tested offline; resubmitted as
26593_0 under <owner-qos>, resuming from the cached round 0.

## 2026-08-30 — Full self-evolution run COMPLETE (8/8 models)

27B lane rerun (26597_0, chunks of 100, async on) finished in 9h46m:
0.2857 → 0.3646 → 0.3893 → **0.3973** (+11.2 pts; final 0.127 → 0.203; valid
plans 380 → 477; 746 rows up / 40 down). Full table with attribution in
`outputs/full_eval/replan-iter-full-20260829/summary.{md,json}`:

| model | Global | r3 | Δ | Δ repair | Δ revise-valid |
|---|---|---|---|---|---|
| Qwen3.8-27B | 0.2857 | 0.3973 | +11.2 | +7.8 | +3.4 |
| DeepSeek-V4-Flash | 0.2701 | 0.3576 | +8.7 | +7.2 | +1.5 |
| Mistral-Small-24B | 0.1415 | 0.2176 | +7.6 | +7.1 | +0.5 |
| gemma-4-26B-A4B | 0.0405 | 0.0982 | +5.8 | +5.4 | +0.4 |
| gemma-4-12B | 0.1426 | 0.1919 | +4.9 | +4.5 | +0.4 |
| Qwen3-4B | 0.1375 | 0.1863 | +4.9 | +4.9 | −0.0 |
| Qwen3-30B-A3B | 0.0835 | 0.1176 | +3.4 | +2.7 | +0.7 |
| gemma-3-27b | 0.0738 | 0.1034 | +3.0 | +2.9 | +0.1 |

Findings: 8/8 improve monotonically, +3.0 to +11.2 pts, regressions ≤ 2% of
rows; round 1 carries 55–70% of the gain and curves flatten by round 3.
The gain is dominated by validator-driven repair of initially-invalid plans
in every model; the ability to improve an already-valid plan from the
execution trace scales with capability (27B +3.4, DeepSeek +1.5, everyone
else ≤ +0.7). 27B self-evolved (0.397) surpasses its own SFT (0.359) and
comes within 7 pts of claude-opus-5 Global (0.464) with no weight update.

## 2026-09-08 — Self-evolution with held-out variants launched (replan_iter_heldout)

User request: the canonical self-evolution run (`replan-iter-full-20260829`)
feeds back every variant and scores the same variants, so its gain includes
test-time adaptation to the scored inputs. New mode `replan_iter_heldout`
(`evaluation/replan_iter_heldout.py`) keeps the protocol (round 0 = frozen
Global plan pre-seeded from tier global-plans; K=3 complete-plan revisions
from environment feedback; same prompt, validator, executor, scorer; all
imported from `evaluation/replan_iter.py`, whose `execute_round` gained an
optional `mode` label kwarg) but renders EXECUTION FEEDBACK from each
recipe's first two variants only (by index; v00/v01 for 624 recipes, v00/v02
for the 26 recipes without a v01) and scores every round on four row subsets:
`seen` (1,285 rows), `heldout` (every other variant; 609 recipes, 1,935 rows),
`heldout2` (the next two held-out variants; 1,115 rows), `all` (3,220). The split is
recorded per lane (`split.json`); all rows keep their variant id so any other
split can be re-scored. Tests:
`verification/backends/shared/src/tests/test_replan_iter_heldout.py` (2) +
the existing 8 replan_iter tests, all green. Offline stub run (3 recipes,
`--stub-llm`): feedback names only v00/v01, held-out ids never appear, round 0
matches the published Global verdicts row for row, all four leaderboards written.

Run `replan-iter-heldout-20260908` (README.md in the run dir documents the
protocol, code, reproduce commands and layout): same eight models as the
canonical run, all 650 recipes, K=3, `scripts/run_replan_iter_heldout.sbatch`
(engine flags / caps / revisions identical to the replan_iter launcher; new
run name, ids_full default, `--feedback-variants 2`). Jobs 27041 (lanes
0-2,4,6,7 TP1) + 27042 (lanes 3,5 TP2), <owner-qos>, --exclude a colleague's reserved node.
Summary via `scripts/summarize_replan_iter_heldout.py` → summary.{md,json,csv}.
Pre-registered read-out: Δorch on `heldout` (round 3 − round 0) per model,
compared with the same model's Δ on `seen` and with the canonical run's Δ on
all variants; the gap between `seen` and `heldout` is the test-time-adaptation
component, the `heldout` gain is what generalizes.

## 2026-09-09 — Held-out-variant self-evolution COMPLETE (8/8 models)

`replan-iter-heldout-20260908` finished (jobs 27041/27042; 27B lane ~10 h,
gemma-4-12B last at ~11 h). Round 0 == published Global on all variants for
every lane. Summary in the run dir (`summary.{md,json,csv}`); rows added to
`replan_iter.csv` (`feedback_scope=first2_variants`, one row per model x round
x scored subset). Orchestration Δ (round 3 − round 0), points:

| model | Δ heldout (unseen v02..) | Δ heldout2 (v02/v03) | Δ seen (v00/v01) | Δ all | Δ all, canonical all-variant feedback |
|---|---|---|---|---|---|
| Qwen3.8-27B | +11.0 | +10.5 | +12.2 | +11.5 | +11.2 |
| DeepSeek-V4-Flash | +8.2 | +7.8 | +8.6 | +8.4 | +8.7 |
| Mistral-24B | +7.4 | +7.7 | +8.1 | +7.7 | +7.6 |
| gemma-4-26B | +5.8 | +5.8 | +6.0 | +5.9 | +5.8 |
| gemma-4-12B | +5.8 | +5.4 | +4.8 | +5.4 | +4.9 |
| Qwen3-4B | +4.9 | +4.7 | +4.0 | +4.5 | +4.9 |
| gemma-3-27b | +3.3 | +3.1 | +2.6 | +3.0 | +3.0 |
| Qwen3-30B-A3B | +2.6 | +2.3 | +2.1 | +2.4 | +3.4 |

Findings: the improvement generalizes. On variants the model never received
feedback about, every model gains +2.6..+11.0 pts, within ~1 pt of its gain on
the feedback variants (seen − heldout = −0.9..+1.3) and of the canonical
all-variant-feedback run. Held-out regressions are ≤ 2.6% of rows (27B 428
up / 31 down; gemma-4-12B 264 / 6). Held-out error rate drops with valid-plan
repair (27B 0.452 → 0.316). Interpretation: the self-evolution gain is
plan-level (validator-driven repair and trace-driven fixes to the workflow),
not adaptation to the scored inputs; the test-time-adaptation component is at
most ~1 pt. Two variants of feedback are sufficient to realize essentially the
full effect.

## 2026-09-15 — GLOBAL+INPUT information-control ablation implemented (`global_input`)

Spec: `doc/global_input.md` (now with an implementation appendix). New
evaluator mode `global_input` = Global View's one-shot planner + the concrete
public runtime input of ONE variant, planned once per variant inside
`run_one` after the public runtime-input projection, frozen, executed by the
unchanged deterministic interpreter, scored by the unchanged evaluator.
- `task/prompt.py`: `runtime_input_parts()` factored out of
  `build_first_user_turn` (ReAct first turn byte-identical); the planner
  renders the runtime input through the same function, so GLOBAL+INPUT sees
  exactly ReAct's pre-first-call runtime input text.
- `task/workflow_plan.py`: `planner_prompts(runtime_input=...)`, prompt
  version `recipe-level-symbolic-executable-plan+runtime-input`; the Global
  prompt without runtime input is unchanged (pinned by tests). Only wording
  change: the "never copy a concrete runtime value" clause is narrowed for
  this mode (it would contradict showing the input).
- `task/run_eval.py`: `initial_plan_context(runtime_input, variant)`,
  `prepare_variant_plan()` (per-variant cache
  `plans_global_input/<model>/<recipe>/variant_XX.json`, cache key includes
  variant + runtime-input hash, raw completion + prompt/completion token
  counts stored, failed planning call cached as `invalid_plan`), `run_one`
  branch (plan_error rows exactly as Global), `main()` wiring (parallel like
  react under vLLM batching; `meta.per_variant_frozen_plan`,
  `meta.variant_planning` cost block; scripted-selftest control supported).
- `task/agents.py`: `GlobalInputAgent` (frozen-plan, no replan);
  `metrics/plan_fidelity.py`: routed like `plan_execute`;
  `task/llm_client.py`: `prompt_token_count()` on vLLM/transformers clients
  for input-token accounting.
- Tooling: `scripts/build_global_input_csv.py` → `results/global_input.csv`
  (Global / Global+Input / ReAct, Input Gain, Residual Gap, planning cost);
  `scripts/update_results_csv.py` picks up `global_input` lanes;
  `scripts/submit_global_input.sh` submits the spec's priority roster through
  the existing per-model launchers with `modes=global_input`;
  `scripts/global_input_selfcheck.py` = CPU oracle-planner end-to-end check.
- Verification: 13 new unit tests (`tests/test_global_input.py`, 42/42 pass);
  scripted control through `evaluation.full_eval --modes global_input
  --scripted-selftest` (11/11 rows, orch 1.0, meta flags correct); oracle
  self-check on 3 recipes / 17 variants: 17/17 ok, orch 1.0, 17 planning
  calls (one per variant, each carrying only its own trigger input), per-variant
  artifacts flagged `contains_runtime_input`, second pass 0 model calls,
  GLOBAL+INPUT user prompt == Global user prompt + runtime section.
- Not run: no GPU lanes submitted (cluster policy: ask before placing jobs).
  `results/global_input.csv` is header-only until lanes complete.

## 2026-09-15 — GLOBAL+INPUT campaign submitted (8 lanes) + two early fixes

User directive: submit every lane in doc/global_input.md and monitor to valid
results. Submitted via `scripts/submit_global_input.sh` (per-model launchers,
`modes=global_input`, site QOS, a reserved node excluded with
`scontrol update ExcNodeList` because SBATCH_EXCLUDE was not honored — the
submit script now does this itself). Run dirs: `global-input-20260915/`
(Qwen3-4B, gemma-4-12B, gemma-4-26B-A4B, Qwen3.8-27B, DeepSeek-V4-Flash,
claude-opus-5), `global-input-20260915-27b-thinking/`,
`global-input-20260915-opus-thinking/`.
- Fix 1 (caught after ~2 min): the thinking configurations reuse the base
  model id, so opus-thinking and opus (and 27B-thinking / 27B) wrote into the
  same `<run>/<model>/global_input` dir and per-variant plan cache. Lanes
  cancelled, mixed rows deleted, thinking lanes resubmitted under their own
  run names (as the canonical thinking ablations were).
- Fix 2 (caught after ~30 rows): `prepare_variant_plan` derived per-row
  planner_calls/planner_tokens from the shared client totals; under the
  16-way vLLM batch (and 4-way API concurrency) every row reported the whole
  batch's tokens (all 33 rows showed 4096+). Added per-thread per-call
  counters to VLLMClient/AnthropicClient (`last_call_completion_tokens`,
  `last_call_prompt_tokens`, from the batch token counts / response usage);
  `planner_calls` is 1 by construction; `planner_tokens_source` records
  per_call vs client_delta. Affected lanes wiped and restarted (they had run
  <10 min). Tests: 48/48.
- Anthropic prompt caching (opt-in `ANTHROPIC_PROMPT_CACHE=1`, enabled by the
  API launchers for `modes=global_input`): the user prompt is split into the
  recipe-invariant prefix (cache breakpoint) and the runtime-input tail;
  output-neutral. Verified live: second call read 21,620 cached tokens.
  Observed prompt ~89k tokens/variant (not ~60k as estimated); the plain Opus
  lane is ~$600 with caching vs ~$1.5k without. Usage counters land in
  `leaderboard.json meta.model_runtime.api_usage`.
- Early health: Opus lanes 9/9 and 3/3 rows ok (orch 0.74 / 0.93 on the
  first rows); Qwen3-4B first 33 rows (pre-restart) 11 ok / 22 plan_error,
  in line with its canonical Global validity (265/650).
- Monitoring: `scripts/global_input_status.py` (per-lane rows, plan_error
  rate, running orch, prompt/completion tokens, health) polled every 10 min
  by a session monitor; `results/global_input.csv` builds once lanes finish.

## 2026-09-15 — GLOBAL+INPUT: Claude lanes stopped on user instruction (open-source only)

User: "only run opensource model, stop the claude". The claude-opus-5
GLOBAL+INPUT lane had already completed (3,220 rows, orch 0.4879, kept);
the claude-opus-5-thinking lane (job 27882) was cancelled at 1,467/3,220
rows (46%) and stays `partial` in results/global_input.csv (no deltas, not
citable). No further API lanes will be submitted for this ablation; the
remaining lane is Qwen3.8-27B-thinking (job 27874_0, open-source).
