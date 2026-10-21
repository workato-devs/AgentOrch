# AgentOrch additional validation checks (2026-09-15)

Answers to `results/Extra_detail.md`. Nothing in the benchmark, simulator or
scorer was changed; every number below comes from the frozen evaluator and the
archived per-variant records.

Files in this directory:

| file | contents |
|---|---|
| `simulator_replay_fidelity.csv` / `.md` | reference-workflow replay in the simulator vs stored real-backend reference, per mode |
| `simulator_replay_mismatches.csv` | one row per mismatching (mode, SOP, variant) with tool sequences, failed metrics, cause category |
| `sop_structural_features.csv` | per-SOP features derived from the reference WorkflowPlan |
| `variant_features.csv` | per-variant features (fault injection, reference call count) |
| `sop_feature_distributions.md` | distributions used to choose the bins |
| `global_vs_step_stratified.csv` / `.md` | pooled GLOBAL vs STEP-BY-STEP (ReAct) subgroup tables |
| `global_vs_step_stratified_per_model.csv` | the same per model (45 models) |

These are frozen paper-analysis artifacts. Their maintainer-only aggregation
scripts are intentionally excluded from the community benchmark because they
do not participate in model execution or scoring.

---

## A. Simulator fidelity / reference replay

### A1. Is the replay already supported?  Yes.

The canonical evaluator has an offline control mode, `--scripted-selftest`
(`verification/backends/shared/src/task/run_eval.py`), that needs no model:

* **plan_execute (Global View) replay** — the recipe's reference
  `WorkflowPlan` (the compiler plan stored in `groundtruth/recipes/<id>/*.json`
  and `verification/evaluation_support/workflow_groundtruth/<id>.json`) is
  translated into the model protocol by `_scripted_initial_plan_artifact`,
  frozen, and executed symbolically on every hidden variant on the simulated
  backend, exactly like a model's frozen plan.
* **react replay** — the recorded reference tool calls
  (`verification/groundtruth/reference_outputs/<id>/variant_XX/output.json`)
  are replayed one action per turn through `ScriptedLLM`
  (`_scripted_from_gold`), with fault-injected variants inserting the forced
  failing attempt first and ending with `finish`.

Both are scored by the same `evaluate_outcome` / runtime-trace machinery as
model runs, so dynamic IDs, timestamps, boolean/enum coercion and query
semantics are normalized exactly as in the benchmark. Runtime variant, seed and
fault configuration are the variant's own.

Command used (repository root, CPU only, ~40 min for plan mode; ReAct mode ~1.5 h, dominated by recipe 89583975 at ~12 min per variant, which was finished in a separate lane `gold-replay-20260915-slow` and merged):

```bash
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name gold-replay-20260915 --state-namespace goldreplay --backend simulated \
  --model scripted-gold --modes plan_execute,react --variants all --scripted-selftest
```

The retained CSV/Markdown tables were generated from the archived raw run;
the canonical scripted replay itself remains directly runnable with the first
command.

Raw outputs: `outputs/full_eval/gold-replay-20260915/scripted-gold/{plan_execute,react}/`.
A two-recipe smoke (`gold-replay-smoke-20260915`) and a single-recipe isolation
rerun under both the system and the conda Python (`gold-replay-iso-*`)
reproduce the same per-variant verdicts, so nothing below is a concurrency or
environment artifact.

### A2. Aggregate table

See `simulator_replay_fidelity.md` for the exact tables (both modes) and the
counts. Summary:

```
Reference workflow replay: real-reference vs simulator

Metric                         plan_execute replay   react replay
                               (reference plan,      (reference tool calls,
                                frozen, all variants) one per turn)
-------------------------------------------------------------------------
Replay success rate            100.00%               100.00%
Tool selection                  61.68%                97.20%
Tool order                      61.68%                97.20%
Tool execution                  60.99%                97.20%
Required arguments              90.34%                99.97%
Control path                    61.68%                97.20%
Execution Trace Accuracy        67.27%                97.76%
Side-Effect Accuracy            81.55%                99.32%
Terminal Output Accuracy        71.43%                76.80% *
Final Accuracy                  56.83%                76.52% *
Orchestration Accuracy          74.41%                98.54%

# SOPs attempted:                650                   650
# runtime variants attempted:    3220                  3220
# variants excluded:             0                     0
# mismatched variants:           1652 (51.30%)         757 (23.51%)
```

`*` The scripted ReAct control never emits the structural return value (it
ends with `finish`), so every variant that expects a terminal return fails
terminal output: 653 of the 757 ReAct mismatches (86%) are exactly this
`missing-output` case and carry no information about the simulator.
Excluding them, ReAct trace/side-effect agreement is ~98–99% and the
remaining 104 mismatches are listed in A3.

The plan-mode replay is the pessimistic case: it replays the private compiler
plan, which is not the public gold projection (A3, Group 1).

### A3. What the mismatches are (plan_execute)

`simulator_replay_mismatches.csv` categorizes every mismatching variant.
Plan-mode mismatches (1,652 of 3,220 variants, 51.3%) split into three groups.

**Group 1 — the reference plan is not the public gold (~70% of mismatches).**
Not simulator behaviour; a property of the published `workflow_plan`.

* *Private runtime-helper steps* (766 + 17 rows, 47%). The compiler plan keeps
  the raw recipe's `workato_runtime.*` steps (declare_variable,
  update_variables, insert_to_list_batch, declare_list, log_message, ...).
  The recorded real-backend reference only logs connector actions, and the
  public gold projection drops runtime helpers ("private implementation
  details", `run_eval.py:_task_description_public_gold_projection`). When the
  plan executes them in the simulator they are classified as **extra write
  calls**, which fails tool selection; because execution requires selection
  and order, and control path is `actual_tools == expected_tools`, four of the
  five trace components fail together. Exact-match rate is 13.1% for the 1,356
  variants whose plan contains helper nodes vs 74.6% for the 1,864 without.
  **Benchmark-relevant:** the nine `workato_runtime.*` tools are in the
  64-tool surface models see. A model that mirrors the recipe and calls them
  is penalized identically. In archived runs this actually happens to
  79 / 2,603 scored claude-opus-5 Global rows and 39 / 3,220 ReAct rows
  (24 and 12 for Qwen3.8-27B), i.e. 1–3% of rows.
* *Return-value envelope* (303 rows, 18%). The compiler plan's `return` node
  carries the raw `{"result": {...}}` envelope while the gold structural return
  is the unwrapped value, so terminal output reports `missing-field`.
  257 of the 303 match exactly once unwrapped; the remaining 46 differ only in
  volatile fields (e.g. `CreatedDate`). Models are instructed to return the
  fields directly, so this is a translation artifact of the control, not a
  scorer or simulator issue.
* *Action budget exhausted* (78 rows). Helper-heavy loops (57% of executed
  calls are runtime helpers in these rows) hit the 2×budget hard stop of 40
  actions on tasks whose gold has 1–3 calls.
* *Trigger filter not encoded in the plan* (16 rows). The engine's trigger
  filter skipped the recipe (gold = no calls); the plan has no trigger gate and
  runs its first read.

**Group 2 — simulator fail-closed guards (~15%).**

* *Fixture guard refused a call* (250 rows): `workato_smart_list.create_list`
  (147), `workato_service.call_service` (47), `salesforce.search_records`
  without SOQL/equality filter (17), `workato_smart_list.query_list` (15),
  `snowflake.search_rows_sql` missing FROM (8), and a few others. The
  simulator serves fixture-backed responses for these tools and refuses
  arguments it cannot map deterministically; the symbolically resolved plan
  arguments do not hit the recorded fixture. The plan aborts
  (`plan_tool_error`). Same behaviour applies to models by design.
* *Plan-executor resolution error* (91 rows): e.g.
  `formula value is not numeric: '2026-01-01T00:00:00+00:00'`,
  `'>' not supported between NoneType`. The symbolic executor cannot evaluate
  some compiler formulas on runtime values.
* *Unexpected tool failure* (9 rows).

**Group 3 — genuine reference/simulator differences (~7%, benchmark-relevant).**

* *Argument value mismatch* (32 rows): a read returned a different result set
  in the simulator so a downstream write got different arguments
  (e.g. `salesforce.update_record` with `records: []`).
* *Required-argument check fails while the canonical exact check passes*
  (44 rows): gold recorded connector default fields (`thread_ts: ""`,
  `replace_original: false`, `channel: "C_SIMULATED"`) that the plan omits;
  the primary required-semantics verdict flags them although the canonical
  comparison accepts the call. Affects real models rarely
  (2 opus Global rows, 19 opus ReAct rows).
* *Call-count / loop-count* (18), *extra/missing tool identity* (17),
  *state mismatch* (10), *terminal missing-field* (1).

### A3b. What the mismatches are (react)

757 of 3,220 replayed variants (23.5%):

* *Structural return not emitted by the control* (653, 86%): control
  limitation (see `*` above), not a simulator difference. Of the 720 variants
  whose gold has a structural return, only 67 pass terminal output in this
  mode; those 67 return through a terminal tool call.
* *Simulator refused or failed a gold call* (83, 11%): the same fail-closed
  fixture guards as in plan mode (`workato_service.call_service requires a
  deterministic callable fixture`, `workato_smart_list.*` without an exact
  fixture). The refused call raises, is absent from the success log, and the
  trace shows a missing call. **Benchmark-relevant**: the recorded real
  execution succeeded on these calls, so on these variants no agent can
  reproduce the reference trace in the simulator.
* *State mismatch with identical call sequence* (13): the replay performed
  exactly the gold calls yet the expected final snapshot is not reached.
  For **9 of the 13** (`103988401` v00–v04, `124154692` v00–v03) no strong
  archived ReAct lane (claude-opus-5, gpt-5.6-sol-thinking, Qwen3.8-27B) ever
  passed side-effect either: the seeded simulator state and the gold snapshot
  disagree (e.g. expected `Survey_Response__c` rows missing), so those
  variants are unattainable for every model. **Benchmark-relevant.**
* *Call-count / loop-count* (4), *extra/missing tool identity* (3),
  *argument value* (1): e.g. `121898837` v00 where the recorded bundle
  contains one `delete_record` but the projected public gold expects two
  (projection expansion), and `105071555` where the public projection adds a
  logging call the recorded trace lacks.

Exact-match rate in ReAct mode is 70.4% for variants whose plan contains
runtime-helper nodes vs 81.0% without; the difference is the structural-return
artifact (helper-heavy recipes are the API-endpoint recipes that return
values), not helper execution (ReAct replays only public calls).

### A4. Engineering issues preventing a cleaner comparison

1. The scripted plan control replays the **private compiler plan**, not the
   public projection of it; helper steps and the `result` envelope make the
   plan-mode replay a pessimistic bound on simulator fidelity.
2. The scripted ReAct control ends with `finish` and never emits the
   structural return value, so ReAct terminal-output / final accuracy are not
   measurable with the existing control (the trace and side-effect metrics
   are).
3. The evaluator's fail-closed backend import prevents reusing
   `normalize_terminal_value` outside an activated backend, so the
   "257/303 match after unwrapping" figure is raw equality, not normalized.

---

## B. Stratified GLOBAL vs STEP-BY-STEP

### B1. Available metadata

No structural metadata is shipped; everything is derived from the reference
`WorkflowPlan` (`groundtruth/recipes/<id>/variant_00.json`; the plan hash is
identical across a recipe's variants, asserted). Node kinds: `call`, `if`,
`foreach`, `repeat`, `try`, `return`, `stop`. Apps use the evaluator's
tool-family identity (tool-name prefix, `run_eval._tool_families`) with the
runtime helpers `workato_runtime` and `clock` excluded; a coarse service
grouping (all Workato families = one service) is reported alongside.
Fault injection is variant-level: `hidden_variant_state.force_action_error`
(or `simulated_action_faults`).

### B2. Distributions (650 SOPs, 3,220 variants) — `sop_feature_distributions.md`

| feature | min | p25 | median | p75 | max | mean |
|---|---:|---:|---:|---:|---:|---:|
| num_tool_calls (call nodes) | 0 | 2 | 3 | 6 | 43 | 4.56 |
| num_business_tool_calls (excl. runtime helpers) | 0 | 2 | 3 | 4 | 36 | 3.51 |
| num_total_workflow_nodes | 2 | 3 | 5 | 9 | 90 | 7.44 |
| num_control_flow_nodes | 0 | 0 | 1 | 3 | 38 | 2.14 |
| max_nesting_depth | 1 | 1 | 2 | 3 | 9 | 2.26 |
| num_dependency_edges | 0 | 2 | 3 | 6 | 67 | 5.17 |
| num_distinct_apps | 0 | 1 | 2 | 2 | 4 | 1.72 |

Size buckets chosen from the quartiles: **short = 1–2 calls (234 SOPs),
medium = 3–5 (251), long = 6+ (165)**; the single 0-call SOP falls in short.

Apps (family identity): 0 apps 5 SOPs (plans with only runtime-helper calls:
121126518, 127782581, 50957083, 88674737, 88676643), 1 app 230, 2 apps 360,
3 apps 50, 4 apps 5 → buckets ≤1 / 2 / 3+ (all 650 SOPs covered).
Services (coarse): 0 = 1, 1 = 274, 2 = 328, 3 = 47 → ≤1 / 2 / 3+.

Control flow: has_conditional 347/650, has_loop 139/650, has_try_catch
237/650. Categories: linear 186, branch_only 132, loop_only 36,
error_handling_only 78, multiple_control_flow_types 218.
Fault injection: 264/3,220 variants (8.2%) in 224 SOPs.

### B3. Subgroup tables

Pooled over the 45 models with both Global and ReAct lanes complete
(fine-tuned checkpoints excluded); failed rows scored 0 and counted in the
error rate exactly as in the main benchmark; metrics recomputed with the
harness's `primary_metrics_for_row`. Gap = STEP − GLOBAL orchestration; CI =
clustered bootstrap over SOPs. `+` = number of models (of 45) whose own gap is
positive. Full tables with final / side-effect / execution-trace columns are in
`global_vs_step_stratified.md`.

```
Workflow size            #SOP  #Var   GLOBAL  STEP    Gap     CI95            +     G-err  S-err
all                      650   3220   0.138   0.464   +0.326  [+0.312,+0.342] 45/45 0.707  0.005
short (1-2 calls)        234   1035   0.188   0.452   +0.263  [+0.245,+0.284] 45/45 0.609  0.005
medium (3-5 calls)       251   1149   0.142   0.473   +0.331  [+0.309,+0.351] 45/45 0.693  0.005
long (6+ calls)          165   1036   0.083   0.466   +0.383  [+0.351,+0.413] 45/45 0.820  0.007

Apps (family identity; <=1 folds in the 5 SOPs whose plan calls no connector tool)
<=1                      235   1192   0.190   0.515   +0.325  [+0.302,+0.347] 45/45 0.652  0.004
2                        360   1676   0.117   0.442   +0.325  [+0.304,+0.346] 45/45 0.721  0.006
3+                        55    352   0.059   0.394   +0.334  [+0.285,+0.385] 45/45 0.824  0.007

Services (coarse)
<=1                      275   1462   0.190   0.570   +0.380  [+0.358,+0.400] 45/45 0.669  0.004
2                        328   1508   0.101   0.393   +0.292  [+0.271,+0.312] 45/45 0.727  0.007
3+                        47    250   0.056   0.271   +0.215  [+0.182,+0.245] 45/45 0.810  0.006

Control flow
no conditional           303   1239   0.142   0.407   +0.265  [+0.246,+0.283] 45/45 0.665  0.006
has conditional          347   1981   0.136   0.500   +0.364  [+0.343,+0.384] 45/45 0.733  0.005
no loop                  511   2413   0.156   0.471   +0.315  [+0.299,+0.331] 45/45 0.679  0.004
has loop                 139    807   0.085   0.443   +0.357  [+0.325,+0.392] 45/45 0.789  0.008
no try/catch             413   1929   0.137   0.432   +0.295  [+0.277,+0.314] 45/45 0.679  0.006
has try/catch            237   1291   0.140   0.512   +0.372  [+0.347,+0.396] 45/45 0.748  0.005

Structure category
linear                   186    781   0.144   0.397   +0.253  [+0.227,+0.280] 45/45 0.642  0.005
branch_only              132    688   0.149   0.486   +0.336  [+0.302,+0.369] 45/45 0.694  0.005
loop_only                 36    148   0.089   0.309   +0.220  [+0.186,+0.262] 45/45 0.704  0.007
error_handling_only       78    295   0.166   0.488   +0.322  [+0.286,+0.361] 45/45 0.696  0.005
multiple types           218   1308   0.128   0.504   +0.377  [+0.352,+0.404] 45/45 0.755  0.006

Nesting depth
1 (flat)                 186    781   0.144   0.397   +0.253  [+0.229,+0.280] 45/45 0.642  0.005
2                        235   1030   0.150   0.478   +0.328  [+0.304,+0.353] 45/45 0.693  0.004
3+                       229   1409   0.126   0.490   +0.365  [+0.342,+0.388] 45/45 0.753  0.006

Fault injection (variant-level)
normal variant           650   2956   0.136   0.458   +0.322  [+0.307,+0.338] 45/45 0.704  0.005
fault-injected variant   224    264   0.164   0.528   +0.365  [+0.338,+0.393] 45/45 0.742  0.006
```

### B4. Reading

* The GLOBAL–STEP gap is positive for **every one of the 45 models in every
  subgroup**. It is not concentrated in one workflow type.
* The gap **grows with complexity**: +0.26 (short) → +0.33 → +0.38 (long);
  +0.25 (linear) → +0.38 (multiple control-flow types); +0.25 (flat) →
  +0.37 (depth 3+). GLOBAL collapses on long workflows (0.083, error rate
  0.82) while STEP is flat across sizes (0.45–0.47). Conditionals, loops and
  try/catch each widen the gap by 7–10 points.
* The one feature that **narrows** the gap is number of services: +0.38 (≤1) →
  +0.29 (2) → +0.22 (3+), because STEP degrades with cross-service
  workflows (0.57 → 0.27) faster than GLOBAL does (0.19 → 0.06). Under the
  finer family identity the gap is flat (+0.32 to +0.33).
* Fault-injected variants score *higher* than normal ones in both modes
  (+0.03 GLOBAL, +0.07 STEP) and show a slightly larger gap; error-handling
  paths are short and STEP sees the failure observation.
* Sparse cells: loop_only (36 SOPs, 148 variants); the 5 zero-connector SOPs
  and the 5 four-app SOPs are merged into ≤1 and 3+ respectively.

### B5. Sanity checks performed

* Same task-id → bucket mapping for both modes (buckets are keyed by task id).
* Structural labels are SOP-level (plan hash identical across variants,
  asserted); `has_injected_fault` is variant-level only.
* Apps are counted from `call` nodes of the reference plan, not the 64-tool
  surface.
* Failed rows (status ≠ ok) are scored zero and kept in the denominator; the
  pooled "all" row reproduces the published per-model leaderboards (mean of
  45 models: GLOBAL 0.138, ReAct 0.464).
* Scoring reuses `metrics.aggregate.primary_metrics_for_row`; nothing is
  reimplemented.
