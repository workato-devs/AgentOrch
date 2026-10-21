# Answers to the seven co-author questions (2026-09-06)

> This is a frozen audit note. Paths name the pre-release layout; current
> adapter examples live in `examples/smoke_adapter/`, audit tools in
> `reproduction/offline/`, and paper-only table builders are not shipped.

Every claim below was checked against the code and artifacts in this repo on
2026-09-06. Paths are relative to the repository root unless they start
with `benchmark/`. "Not documented" means no file in the repo states it.

---

## Q1. Does the model-visible specification justify the exact reference order?

**Short answer: no, not in general.** The public specification fixes the tool
set, call count, arguments, and branch/loop/terminal behaviour, and it fixes
*some* ordering (data flow, same-resource hazards, and ordering words the
description writer happened to include). It does not fix the relative order of
two writes to different systems that share no data flow and no stated timing
rule. The scorer nevertheless requires the reference serialization. So the
trace score is **compliance with the specified requirements plus fidelity to
the reference serialization wherever the specification underdetermines order**.
The paper should say that.

What the generator does (`task_description/redesign_pilot.py`):

- Requirements are deliberately permuted before rendering: two requirements are
  always reversed, three or more get a forced non-identity shuffle
  (`:5369-5380`, `SHUFFLE_VERSION = "requirement-shuffle-v1"`).
- The rendered description carries a disclaimer that presentation order is not
  execution order (`:83-87`), and the Global system prompt says "infer causal
  order".
- The Stage-4 prompt tells the writer to preserve "true temporal business
  rules" but to leave "action order" for the evaluated model to infer
  (`:6504-6511`). There is **no mechanical gate** that checks, for every pair
  of gold calls whose order is not fixed by data flow, that an ordering clause
  exists in the public text. The explicit requirement kind
  `temporal_business_constraint` is used on exactly one requirement in the 650
  accepted specs (recipe 88704851, and it is about sorting an array, not call
  order).
- `PUBLIC_PACKAGE.json` has no ordering section, no dependency edges, and no
  temporal-requirements block.

What the scorer does (`benchmark/verification/backends/shared/src/task/run_eval.py`):

- Primary: `tool_order_pass = (actual_tools == expected_tools)` (`:1795`),
  exact tool-name sequence; `tool_order_mode` is the constant
  `"canonical_exact"` (`:1862`).
- A dependency partial order **is** computed (`_task_description_runtime_order_spec`,
  `:240-507`: data/structural dependencies, same-resource read/write hazards,
  and "public temporal requirements" detected by a regex `after|before|then|only once`
  over the private TaskSpec text) and emitted as `tool_order_dependency_pass`,
  but it is a diagnostic only. It never enters `execution_trace_accuracy`.
- This is by documented design: `task_description/docs/exact_trace_policy.md:1-24`
  "supersedes earlier proposals to accept execution-equivalent tool choices,
  dependency-DAG reorderings, or benign extra reads as primary correctness".

Confirmed instance (recipe 116556165): two independent upserts (Workato data
table and Snowflake) with no dependency and no ordering words in the two
requirement bullets. The scorer's own spec for all 5 variants records
`dependency_edge_count = 0`, `public_temporal_requirement_count = 0`,
`multiple_topological_orders = True`. Qwen3.8-27B executed them in the swapped
order on all 5 variants: `tool_selection_exact_pass = True`,
`tool_order_dependency_pass = True`, `tool_order_pass = False`. The published
bullet order is the inverse of the reference call order for this recipe.

Corpus-wide (all 22 Global result sets): 71 of 650 recipes have at least one
variant with `multiple_topological_orders = True`; 61 of those also have zero
detected public temporal requirements. 61 is an upper bound on truly ambiguous
recipes because the regex under-detects real constraints (recipe 88782312 says
"Only when the record is created successfully, post to Slack", which the regex
misses). On the 27B Global rows, 114 of 1,807 scored rows fail exact order but
pass the dependency order; 5 of those are pure permutations of the correct
multiset (all recipe 116556165), the rest also involve extra or missing calls.

Suggested handling: keep the metric, state the framing above, and report an
order-relaxed variant as an ablation. It is computable from existing rows with
no re-run (`tool_order_dependency_pass` is in every results row); on the 27B
it changes 6.3% of scored rows.

---

## Q2. Operational definitions of the trace components

All five predicates are computed in one function,
`_runtime_orchestration_components` (`run_eval.py:1328-1937`), with one call
site (`:3476`). **There is no mode branch: ReAct and Global (and Replan) are
scored by the identical code on the executed runtime trajectory.** Global plans
are never scored on plan node ids; plan structure is a separate per-recipe
diagnostic (`plan_condition_control_flow_f1`, `metrics/plan_fidelity.py`) that
does not enter the score. Weighting is in `metrics/aggregate.py:60-97`:
trace = 0.2 x sum of five booleans; orchestration = 0.5 trace + 0.5 side effect.

Preprocessing (`:1356-1372`): the trace is the registry call log, which only
contains calls that returned without raising (`benchmark/tools.py:127-129`).
Failed attempts are in `steps` with an `error` key. Two structural tools are
dropped: `workato_genie.workflow_return_result`,
`workato_recipe_function.return_result` (`:159-162`). `return_response` is a
scored business call. `finish`/`stop` are protocol pseudo-tools and never reach
the registry. `workato_now` etc. are plan expression operators, not tools.

```
expected = [c.tool for c in gold_calls  if tool not structural]   # ordered
actual   = [c.tool for c in agent_calls if tool not structural]   # ordered, successful only

tool_selection   = Counter(actual) == Counter(expected)                       # :1371,1747
tool_order       = actual == expected                                          # :1795
condition_path   = actual == expected                                          # :1834  (same test as order)
tool_execution   = tool_selection and tool_order
                   and no failed attempt whose tool != seed.force_tool_error.tool   # :1373-1408, :1805-1809
tool_argument_required:
    per tool name, maximum bipartite matching gold<->agent where the gold
    args are a recursive subset of the agent args with strict type identity
    ("__ANY__" = present and non-empty)                                        # :1638-1703
    for salesforce.search_records / snowflake.search_rows_sql / run_custom_sql:
    canonical-exact OR same result row multiset / same table state             # :1271-1325
    checked  = every gold call got a match                                     # :1811
    pass     = checked and all matches pass                                    # :1812-1816
    unchecked -> counted as a vacuous pass (1.0) in aggregate.py:81-85
```

Consequences you should know before writing the metric section:

- `condition_path` is inferred from the observed tool trajectory only, and it
  is literally the same expression as `tool_order`. `doc/exp.md:380-383`
  states this ("at runtime this is reflected by the active business-call
  sequence"); `doc/metric.md:25` implies independent branch/error/terminal
  signals that the code does not compute.
- `tool_execution` is a conjunction of selection, order, and "no unexpected
  failed attempt". An extra *successful* read therefore fails four components
  (selection, order, execution, control path) and the row's trace score is
  0.2. The reason is not that execution failed; it is that three of the four
  are the same comparison re-tested. The doc/exp.md wording for execution
  ("selected calls execute successfully in the expected sequence") is the only
  hint of this coupling.
- A missing gold call scores 0 on four components but 1.0 on arguments
  (unchecked = vacuous pass).
- The public scorer `benchmark/evaluation/cal_acc.py:194-289` is a
  different implementation (its docstring says so, `:17-21`): its execution
  predicate checks per-call success and its control-path predicate is a
  terminal-reachability check. Under `cal_acc.py` the extra-read row scores
  0.6, under the leaderboard scorer 0.2. `aggregate.py:70-79` claims parity
  with `cal_acc.py`; that claim holds only for the vacuous-pass rule. This
  needs to be reconciled or disclosed.
- `orchestration_trace_pass` / `strict_pass` (`run_eval.py:3514-3523`) use
  `tool_argument_full_pass`, whereas the published metric uses
  `tool_argument_required_pass`.

---

## Q3. Source of the recipes and train/test separation

**Provenance is not documented.** The root is a single git-ignored CSV
(`dataset/standalone_recipes.csv`, 587 MB, 5,071 rows) whose columns are
internal Workato platform fields (`id, flow_id, version_no, author_id,
code_sanitized, category=standalone`). There is no title, template, or
community field, ~219 distinct authors, creation dates 2021-01 to 2025-10, and
tenant-specific custom connectors in the bodies (e.g.
`corporate_api_connector_748504_...`). The honest description is "a sanitized
export of real Workato workspace recipes", not community templates.
`DATA_CARD.md:118-127` and `README.md:196-204` leave the licence unresolved.
This needs a rights statement before submission.

**Separation is by recipe id only.** The 803 benchmark ids (650 active + 153
archived low-action) were removed from the 5,071, the remaining 4,268 were
ranked by structural complexity, and training = ranks 1..3000
(`backup/training_data/complexity.md:5-24`; verified). No hashing, structural
fingerprint, template, name-similarity, or author-level check exists anywhere;
`TOTAL.md:238-248` specifies near-duplicate clustering but it was never
implemented. The README line "Zero overlap ... (verified)"
(`benchmark/training_section/README.md:11`) has no backing script.

Measured on 2026-09-06:

| check | result |
|---|---|
| recipe-id overlap, `flow_id` overlap, `workflow_A_hash` collisions | 0 |
| structure-only fingerprint (kind+tool tree, args ignored) shared across splits | 8 structures: 23 train recipes, 51 test recipes, all 2 to 6-node plans |
| test recipes whose `author_id` also authored training recipes | 629 / 650 (96.8%) |
| within-split duplicates by the same fingerprint | train 1,122/3,000 (37%), test 377/650 (58%) |

Also note: training is the top-3,000 most complex of the remaining pool, so it
is not an i.i.d. sample; and it contains 199 single-call recipes although the
test split enforces a two-action minimum.

**Tool coverage.** The 64-card catalog (`benchmark/open_models/tool_catalog.json`)
is identical across all 650 recipes. Counting per recipe:

- 60 of 64 tools appear in at least one of the 3,000 training targets. The 4
  never targeted anywhere: `slack.delete_message`,
  `workato_db_table.search_records`, `workato_genie.workflow_return_result`,
  `workato_recipe_function.return_result`.
- 54 of 64 appear in at least one benchmark gold plan; 42 are executed in a
  `variant_00` trace. **Every tool used in benchmark gold is also a training
  target.** 6 are training-only (e.g. `slack_bot.block_kit_modals`, 249
  training recipes).
- All 64 cards also appear as distractor cards in training prompts by design.
- Caveat: training targets also use 973 recipe-specific raw connector tool
  names outside the catalog; 654 of 3,000 targets use no catalog tool at all.
  So held-out generalization is at the workflow level over a shared canonical
  vocabulary, not to unseen tools.

---

## Q4. Variant construction and shared execution conditions

**Generation.** 3,211 of the 3,220 variants were model-authored
(`claude-opus-5` via the Batch API, five requested per recipe with one repair
round) and entered the repo in the initial import; the generator script for
the *test* split is not in the tree (only the training-corpus generator that
imitates the same layout, `backup/training_data/generate_input_variants.py`).
The remaining 9 were synthesized by deterministic coverage-guided search
(`test_benchmark/record/full_corpus_task_descriptions/materialize_{control,exception}_coverage_variants.py`
plus a fallback pass): 5 condition/loop variants, 1 exception variant, 3
fallback. Per-recipe counts are not uniform: mode 5, mean 4.95, range 1 to 28;
15 recipes have a single variant. A variant varies the trigger payload, seeded
backend state, an optional injected fault, and branch/loop-flipping inputs.

**Coverage actually checked.** The blocking publication gate is
`executed_trace_coverage` (`redesign_pilot.py:73-81, 8741-9007`), measured on
executed gold traces, not static claims: per `if` node both `condition_true`
and `condition_false`; per `try` node both `try_success` and `exception`; per
`foreach` node `zero`, `one`, and `multiple` items. Over 650 recipes: 2,896
obligations, 2,758 observed, 138 (4.8%) waived through a hash-guarded waiver
registry (139 waivers over 53 recipes), 0 unwaived, 650/650 pass. A mutation
check (`semantic_variant_coverage`: flip each predicate operator, require a
variant to change outcome) is non-blocking: 609/650 pass, 159 surviving
mutants. Stage-7 `branch_coverage` is explicitly "secondary diagnostic only"
and has no loop check. Note 96.9% of loop boundaries in the published traces
iterate zero items.

**Fault injection and cross-protocol matching.** 258 of 3,220 variants (8.0%,
218 recipes) carry `force_action_error: {step_as, error}`. Gold replay matches
it by raw recipe node id (`raw_executor.py:523-533`). For evaluated models the
private step id is translated once per variant to a public tool
(`run_eval.py:1955-2033`) and matched inside the single shared
`ToolRegistry.call` (`benchmark/tools.py:79-109`) that both ReAct
(`runner.py:490`) and frozen-plan execution (`runner.py:935`) go through:

1. preferred: tool name + a literal argument selector (`table_id`, `channel`,
   `sobject`, `lookup_table_id`, ... from a fixed whitelist), used only when
   it is unique among same-tool nodes in the workflow;
2. fallback: tool name + per-tool-name occurrence ordinal.

So matching is never by node id and never by global call position. The one
divergence: under the ordinal fallback, an agent that makes an extra call to
the same tool before the intended one absorbs the fault early. The fault target
and error string are never in the prompt. `transient_event_*` fields are not
fault injection; they are the ordered trace of `workato_app.stop_recipe /
start_recipe / rerun_jobs` events, which are invisible in a final snapshot.

**Backend.** Every reported number uses `--backend simulated`
(`doc/exp.md:40`; all 13 launchers; default in `evaluation/full_eval.py:75`).
There are zero real-backend evaluation rows. The `real` backend exists and
covers 6 connector families only, so a full-corpus real run is not currently
possible. The correct wording is "frozen canonical reference executions"
(`doc/exp.md:346-353`), not "re-run on real connectors".

---

## Q5. Which protocols belong in the paper; how REPLAN operates

**LOCAL** is a planning-time mode: the model builds one variant-blind plan
through an append-only editor (one `append_node` or `finish_plan` per turn,
accepted prefix immutable, whole draft re-shown each turn, up to 64 editor
turns per recipe, each node validated on append), then the frozen plan is
executed exactly like GLOBAL with zero runtime LLM calls. It is a public
setting in the README and the HF configs, but it is absent from `doc/exp.md`
(the paper-facing doc) and every launcher calls it an ablation. 15 of 17
rostered models have complete results (command-r and Qwen2.5-72B were
cancelled). LOCAL beats GLOBAL on 11/15 models, mostly by turning invalid
one-shot plans into valid ones (e.g. Llama-3.3-70B 0.105 to 0.349, scored rows
919 to 2,830), and loses on 4. Recommendation: treat LOCAL as a reported
ablation of plan construction, not a headline setting. This is your call.

**REPLAN (v1, canonical).**

- Trigger: a review after **every executed tool call**, success or error
  (`runner.py:959-970`), one LLM call each. Transform, branch, and loop
  markers do not trigger a review. Resolver errors end the row without review
  in v1.
- Action: `{"type":"continue"}` or `{"type":"replan", "remaining_workflow":[...]}`
  which replaces the **entire unexecuted suffix**; the executed prefix and its
  bindings are immutable. No partial edits in v1.
- Validation: same `normalize_plan` validator as the initial plan plus live
  binding grounding (`runner.py:712-726`); malformed or invalid replans are
  rejected fail-closed and execution continues on the unchanged plan.
- Limits: `max_replans = 2` accepted replans per variant (the gemma-4-12B lane
  ran with 6; scores identical to 4 decimals). Reviews continue to cost an LLM
  call after the cap. No dedicated review token cap beyond the 8,192 generation
  limit. Review count is bounded by the action budget.
- Initial artifact: **the exact GLOBAL plan**, verified 650/650 identical
  `initial_plan_hashes` for Qwen3.8-27B and gemma-4-12B; the replan process
  made zero planner calls (`initial_plan_generation_calls_this_process: 0`).
- What the reviewer sees: trigger input, environment card (table ids and
  columns, no rows), the frozen plan, all prior observations and its own
  replies, and the current raw observation or `ERROR:` text. Never gold, state,
  or verdicts.
- Cost (from `benchmark/COST.csv`): Qwen3.8-27B 2,885 review calls over
  1,807 scored rows, 336 accepted; +0.8 orchestration points over GLOBAL.

**Replan v2** (repair turn, single-node patch, resolver-error review) was
smoke-tested on 5 models and not promoted (no lane met +3 pts, one regressed).

**Replan-iter (self-evolution)**: round 0 is the GLOBAL plan bit-for-bit, then
K=3 rounds of "execute all variants, feed back the model's own trace
(observations, errors, validator messages; never gold), emit a complete
revised plan". 8 models, all monotone, +3.0 to +11.2 points (27B 0.286 to
0.397). Documented caveat: after round 0 the plan is no longer variant-blind.
Cost: 3 revision calls per recipe plus 4 deterministic full executions.

---

## Q6. Inclusion criteria for the 3,000-target corpus

**Raw-recipe replay does not gate entry.** The active exporter
(`task_description/export_training_sft.py::export_dataset`, `:773-897`) takes
all 3,000 rows of `dataset/task_descriptions/train_recipes_terra.jsonl` and
applies, fail-hard (abort, not skip): deterministic Stage-1 compilation,
schema/call-shape/literal-type reconciliation, planner-protocol validation
(`normalize_plan`), tool-surface closure, and a private-key leakage guard. The
manifest's `row_count: 3000` therefore means 3,000/3,000 passed all of them.
Recorded reconciliation counts: 9,637 call-shape and 8,581 literal-type
repairs, 25 input-schema repairs.

**Relation to 2,751.** That number was variant-level replay gating of the
legacy 5-variant training track: 15,000 variants, 12,466 pass strict replay
over 2,752 recipes, 2,751 after dropping one recipe with a missing generation
manifest (`DATA_CARD.md:63-66`, `backup/training_data/input_variant_generation.md:244-263`).
Variant *construction* never failed ("all 3,000 recipes have exactly five
locally valid variants"). The current recipe-level corpus includes all 249
previously excluded recipes (verified: recipe 128639225 is present). **This
change of inclusion basis is not written down anywhere.** It should be stated
as: targets are deterministic compilations validated for compile success,
schema conformance, planner-protocol legality, and tool-surface closure;
execution replay is construction evidence for the legacy variant track, not a
gate.

**Compiler semantic checks that exist:**

- Unit tests in `task_description/tests/`: `test_workflow_fidelity.py`
  (nested control flow, dropped nodes, dropped bindings, wrong tool, changed
  branch topology), `test_canonical_tool_arguments.py` (19 tests on datapill
  and reference resolution, including parametrized checks against persisted
  simulator calls), `test_workato_formula.py` (10 tests, several differential
  against the raw executor), plus exact-trace normalization and control
  coverage tests.
- `static_workflow_fidelity_report` (raw recipe to Stage-1 to plan structural
  equivalence) is enforced fail-hard on the 650 **test** targets
  (`redesign_pilot.py:11662-11676`) but is **not called** on the 3,000
  training targets.
- No normalizer round-trip assertion exists.
- One execution-level parity probe of compiled training targets was run
  (`training_section/src/rl/tier2/probe_v3.py`, 4,339 replay-passed variants):
  all-five-components parity 28.0%, attributed in `EXPERIMENTS.md:309-315` to
  fixture poverty (gold observations defaulting to `{"ok": true}`), and the
  tier was closed. So there is no end-to-end verification that compiled
  targets reproduce raw-recipe effects; describe only the static checks.

---

## Q7. What has been trained and evaluated

**Models and method.** Five bases, all LoRA (no full fine-tune; rejected for
memory): Qwen3.8-27B (headline), Qwen3-4B-Instruct-2507, gemma-4-12B-it,
gemma-4-26B-A4B-it, gemma-4-31B-it. Default r=16, alpha=32, all-linear, lr
1e-4, cosine, 80k context, FSDP2 on 8xH200 (`training_section/src/train_sft_local.py`).

**Objective.** Plain SFT on the serialized WorkflowPlan completion only: loss
masked to the assistant turn (`train_sft_local.py:69-92`), chat template with
`enable_thinking=False`, assistant content is exactly `{"plan": [...]}`
(`export_training_sft.py:944`). No explanations, no thought text, no
intermediate representation. Targets over 6,144 tokens are dropped as
unscorable under the 4,096 decode cap; rows over the 80k context are skipped
(27B: 2,521 rows trained, 268 skipped).

**Validation set.** A recipe-disjoint 60-row split exists
(`prepare_dataset.py:66-71`, seed 0), but the trainer never loads it and
computes no validation loss; its recipe ids are not recorded (recoverable by
re-running with seed 0). **Checkpoints were selected by full benchmark score**:
the 2/3/4/5-epoch ladder (0.362/0.420/0.411/0.402), r16 vs r64, two learning
rates, and RL steps were each scored on all 3,220 variants and the best was
reported (`EXPERIMENTS.md:93`). The paper must disclose this or re-select on
the held-out split. Mitigation you can cite: the ladder is monotone on both
sides of the peak, and 3ep vs 4ep CIs overlap.

**Completed held-out evaluations** (simulated backend, greedy, all 3,220
variants; `reproduce_all.log`: 165 lanes reproduced exactly):

| model | mode | base | ours (SFT 3ep) |
|---|---|---|---|
| Qwen3.8-27B | global | 0.2857 | 0.4196 (r64: 0.4217) |
| Qwen3.8-27B | replan | 0.2939 | 0.4208 |
| Qwen3.8-27B | react | 0.5331 | 0.5112 |
| Qwen3.8-27B | local | 0.3276 | 0.2861 |
| Qwen3-4B | global | 0.1375 | SFT 0.2546, GRPO 0.2716 |
| gemma-4-12B | global | 0.1426 | SFT 0.1792, GRPO 0.2166 |
| gemma-4-26B-A4B | global | 0.0405 | SFT 0.1989, GRPO 0.2393 |
| gemma-4-31B | global | 0.1271 | SFT 0.1955, GRPO 0.1910 (n.s.) |

RL: verl GRPO for Qwen, TRL GRPO for gemma, Tier-1 symbolic-match reward. RL
helps weak bases and does not beat the 3ep SFT on the 27B. Transfer: training
on Global-shaped targets moves global and replan (+13.4, +12.7) and slightly
hurts react and local (-2.2, -4.2), which is an honest limitation to report.

So Section 4 can present **both**: a supervision-data construction method and
an empirically demonstrated training method, with the transfer limitation and
the test-set selection disclosure.

---

## Items for the maintainer, not for the co-author

1. `results.csv` dedup bug: `scripts/update_results_csv.py` keys on short model
   name and first-writer-wins, so the temp-sweep (T=0.3) lanes displaced the
   greedy base rows for Qwen3.8-27B global/react and gemma-4-31B global. The
   tier leaderboards are intact; `training_section/build_results_table.py`
   would now print empty base cells. Fix before regenerating `ALL_RESULTS.md`.
2. The inclusion-basis change (2,751 to 3,000) is undocumented; add a
   change.md entry and a DATA_CARD line.
3. `cal_acc.py` and the leaderboard scorer disagree on execution and
   control-path predicates; either align them or document the difference.
4. `orchestration_trace_pass` uses the full-argument predicate while the
   published metric uses the required-argument predicate.
5. `doc/pipeline.md` says seeding reads `verification/seeds/`; the canonical
   path reads `verification/dataset/input_recipes/`.
6. A rights/provenance statement for the source CSV is required.
