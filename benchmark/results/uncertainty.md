# Temperature Sweep: Decoding Uncertainty of Open-Weight Models

Status: complete (2026-09-08). Thirty sweep lanes (5 models x 3 temperatures
x 2 settings, 3,220 rows each) plus two greedy reruns that replace the
problematic T=0 baselines (section 7). This document is a frozen paper
artifact retained with the release. The maintainer-only table-generation
scripts are intentionally excluded because they are not required to run or
score the benchmark. Source run locations are recorded below for provenance.

## 1. Question

The main leaderboard uses greedy decoding (temperature 0), so every model
contributes one deterministic trajectory per instance. This sweep asks how
much of a model's reported score survives when the decoder samples, and how
much per-instance disagreement sampling reveals. The spread across
temperatures is read as the model's uncertainty about each instance: an
instance solved at every temperature is one the model "knows"; an instance
solved only sometimes is one it is guessing on.

## 2. Protocol

- **Models** (five open-weight checkpoints from the canonical large tier,
  pinned revisions identical to the greedy lanes): DeepSeek-V4-Flash-0731,
  Qwen3.8-27B-FP8, gemma-4-31B-it, GLM-4.5-FP8, Qwen3-30B-A3B-Instruct-2507.
- **Temperatures**: 0, 0.3, 0.6, 1.0. top_p = 1.0, vLLM engine seed 0, no
  other sampling change. Temperature is read from `HF_TEMPERATURE` by the
  vendored vLLM client (`verification/backends/shared/src/task/llm_client.py`).
- **T=0 lanes**: DeepSeek, gemma, Qwen3-30B use the canonical greedy tier
  lanes (`outputs/full_eval/large_model/<model>/{global,react}`). Qwen3.8
  and GLM-4.5 use the 2026-09-07 greedy reruns
  (`outputs/full_eval/greedy-rerun-20260907/`), see section 7 for why.
- **Settings**: Global View (`plan_execute`) and ReAct (`react`), all 3,220
  runtime variants, simulated backend, same prompts, tool surface, token
  limits, and scorer as the main comparison (`doc/exp.md`).
- **Thinking**: Qwen3.8 and GLM-4.5 are hybrid reasoners; every lane in
  this file pins `enable_thinking=false` for both.
- **Scoring rule**: identical to the leaderboard. Failed generations (plan
  parse errors, LLM errors) stay in the denominator at zero on every metric.
- **Launchers**: `reproduction/cluster/run_temp_sweep.sbatch` via
  `reproduction/cluster/submit_temp_sweep.sh` (sweep, 15 lanes);
  `reproduction/cluster/run_greedy_recheck.sbatch` (greedy reruns, array index 0 and 3).
  Sweep results: `outputs/full_eval/temp-sweep-t{03,06,10}-20260906/hf:<model>/{plan_execute,react}/`.

### Metric definitions

- **final accuracy**: 1 if the side effect (writes to simulated connector
  state) matches the gold snapshot AND the normalized terminal output
  matches; else 0.
- **orchestration accuracy**: 0.5 x execution-trace accuracy + 0.5 x
  side-effect accuracy. Execution-trace accuracy is the mean of five binary
  checks (tool selection, tool order, tool execution success, required
  arguments, control path). Partial credit for process correctness.
- **error rate**: fraction of rows with no scorable output (Global View:
  plan did not parse or generation failed; ReAct: LLM error).

## 3. Accuracy by temperature

Final accuracy, with orchestration accuracy in parentheses. Bootstrap 95%
confidence intervals (cluster bootstrap over recipes, 2,000 resamples) are
in section 6.

| model | mode | T=0 | T=0.3 | T=0.6 | T=1.0 |
|---|---|---|---|---|---|
| DeepSeek-V4-Flash | global | 0.114 (0.270) | 0.113 (0.268) | 0.100 (0.237) | 0.080 (0.197) |
| DeepSeek-V4-Flash | react | 0.446 (0.590) | 0.456 (0.591) | 0.448 (0.585) | 0.434 (0.575) |
| Qwen3.8-27B | global | 0.126 (0.283) | 0.112 (0.255) | 0.104 (0.226) | 0.069 (0.161) |
| Qwen3.8-27B | react | 0.486 (0.617) | 0.489 (0.617) | 0.474 (0.611) | 0.462 (0.596) |
| gemma-4-31B | global | 0.048 (0.127) | 0.047 (0.125) | 0.049 (0.131) | 0.046 (0.118) |
| gemma-4-31B | react | 0.461 (0.614) | 0.461 (0.614) | 0.470 (0.614) | 0.465 (0.615) |
| GLM-4.5 | global | 0.066 (0.166) | 0.072 (0.159) | 0.064 (0.172) | 0.070 (0.165) |
| GLM-4.5 | react | 0.386 (0.554) | 0.389 (0.557) | 0.385 (0.553) | 0.373 (0.543) |
| Qwen3-30B-A3B | global | 0.029 (0.084) | 0.036 (0.085) | 0.032 (0.081) | 0.034 (0.080) |
| Qwen3-30B-A3B | react | 0.267 (0.478) | 0.266 (0.477) | 0.268 (0.475) | 0.273 (0.477) |

Error rate (Global View = plan failure rate; ReAct error is 0.0-0.2%
everywhere and is omitted):

| model | T=0 | T=0.3 | T=0.6 | T=1.0 |
|---|---|---|---|---|
| DeepSeek-V4-Flash | 0.435 | 0.461 | 0.498 | 0.556 |
| Qwen3.8-27B | 0.448 | 0.487 | 0.522 | 0.660 |
| gemma-4-31B | 0.749 | 0.748 | 0.735 | 0.752 |
| GLM-4.5 | 0.615 | 0.639 | 0.616 | 0.636 |
| Qwen3-30B-A3B | 0.764 | 0.771 | 0.785 | 0.803 |

## 4. Agreement with the greedy run

For each sampled temperature, each variant's final verdict is compared with
the greedy verdict for the same variant.

- **agree**: fraction of variants with the same final verdict as greedy.
- **greedy-pass lost**: among variants greedy solved, the fraction the
  sampled run failed. How fragile the reported greedy successes are.
- **greedy-fail gained**: among variants greedy failed, the fraction the
  sampled run solved.

The run-to-run noise floor for these columns is in section 7.3: two greedy
runs of the same lane agree on 95.4% of verdicts and lose 18% of each
other's passes.

| model | mode | T | agree | greedy-pass lost | greedy-fail gained |
|---|---|---|---|---|---|
| DeepSeek-V4-Flash | global | 0.3 | 0.919 | 0.361 | 0.045 |
| DeepSeek-V4-Flash | global | 0.6 | 0.897 | 0.514 | 0.050 |
| DeepSeek-V4-Flash | global | 1.0 | 0.898 | 0.598 | 0.038 |
| DeepSeek-V4-Flash | react | 0.3 | 0.912 | 0.088 | 0.088 |
| DeepSeek-V4-Flash | react | 0.6 | 0.906 | 0.102 | 0.087 |
| DeepSeek-V4-Flash | react | 1.0 | 0.875 | 0.153 | 0.103 |
| Qwen3.8-27B | global | 0.3 | 0.920 | 0.373 | 0.038 |
| Qwen3.8-27B | global | 0.6 | 0.877 | 0.575 | 0.058 |
| Qwen3.8-27B | global | 1.0 | 0.892 | 0.651 | 0.029 |
| Qwen3.8-27B | react | 0.3 | 0.941 | 0.058 | 0.060 |
| Qwen3.8-27B | react | 0.6 | 0.922 | 0.092 | 0.064 |
| Qwen3.8-27B | react | 1.0 | 0.889 | 0.139 | 0.085 |
| gemma-4-31B | global | 0.3 | 0.984 | 0.175 | 0.008 |
| gemma-4-31B | global | 0.6 | 0.973 | 0.266 | 0.015 |
| gemma-4-31B | global | 1.0 | 0.971 | 0.331 | 0.014 |
| gemma-4-31B | react | 0.3 | 0.942 | 0.063 | 0.054 |
| gemma-4-31B | react | 0.6 | 0.938 | 0.058 | 0.066 |
| gemma-4-31B | react | 1.0 | 0.931 | 0.070 | 0.067 |
| GLM-4.5 | global | 0.3 | 0.955 | 0.300 | 0.027 |
| GLM-4.5 | global | 0.6 | 0.945 | 0.432 | 0.028 |
| GLM-4.5 | global | 1.0 | 0.936 | 0.460 | 0.036 |
| GLM-4.5 | react | 0.3 | 0.919 | 0.101 | 0.069 |
| GLM-4.5 | react | 0.6 | 0.909 | 0.120 | 0.073 |
| GLM-4.5 | react | 1.0 | 0.885 | 0.166 | 0.083 |
| Qwen3-30B-A3B | global | 0.3 | 0.978 | 0.263 | 0.015 |
| Qwen3-30B-A3B | global | 0.6 | 0.973 | 0.421 | 0.015 |
| Qwen3-30B-A3B | global | 1.0 | 0.972 | 0.390 | 0.017 |
| Qwen3-30B-A3B | react | 0.3 | 0.909 | 0.172 | 0.061 |
| Qwen3-30B-A3B | react | 0.6 | 0.893 | 0.198 | 0.074 |
| Qwen3-30B-A3B | react | 1.0 | 0.890 | 0.194 | 0.079 |

High "agree" values for weak planners (gemma, Qwen3-30B in Global View) are
mostly agreement on failure: their plan error rate is 75-80% at every
temperature, so most variants fail identically.

## 5. Per-instance stability across the four runs

Each variant has four final verdicts (T = 0, 0.3, 0.6, 1.0).

- **always pass / never pass**: identical verdict in all four runs.
- **unstable**: passes in some runs and fails in others; the per-instance
  uncertainty mass.
- **pass@any**: passes in at least one of the four runs; an upper bound on
  what the model can do with resampling.
- **sampled mean**: mean final accuracy over the three sampled runs.

| model | mode | always pass | never pass | unstable | pass@any | greedy | sampled mean |
|---|---|---|---|---|---|---|---|
| DeepSeek-V4-Flash | global | 0.024 | 0.794 | 0.182 | 0.206 | 0.114 | 0.098 |
| DeepSeek-V4-Flash | react | 0.339 | 0.458 | 0.203 | 0.542 | 0.446 | 0.446 |
| Qwen3.8-27B | global | 0.021 | 0.788 | 0.190 | 0.211 | 0.126 | 0.095 |
| Qwen3.8-27B | react | 0.385 | 0.444 | 0.171 | 0.556 | 0.486 | 0.475 |
| gemma-4-31B | global | 0.026 | 0.925 | 0.049 | 0.075 | 0.048 | 0.047 |
| gemma-4-31B | react | 0.404 | 0.478 | 0.119 | 0.522 | 0.461 | 0.465 |
| GLM-4.5 | global | 0.021 | 0.871 | 0.108 | 0.129 | 0.066 | 0.068 |
| GLM-4.5 | react | 0.286 | 0.526 | 0.188 | 0.474 | 0.386 | 0.383 |
| Qwen3-30B-A3B | global | 0.011 | 0.938 | 0.051 | 0.062 | 0.029 | 0.034 |
| Qwen3-30B-A3B | react | 0.171 | 0.635 | 0.194 | 0.365 | 0.267 | 0.269 |

## 6. Confidence intervals, plan divergence, sampling-only agreement

- **plan hash differs**: Global View only. Fraction of variants whose
  frozen plan at temperature T has a different content hash from the
  greedy plan, over variants where both runs produced a plan. Confirms
  sampling was live. Calibration: two greedy runs of Qwen3.8 already differ
  on 67.5% of plans (section 7.3), because vLLM batched greedy decoding is
  not bit-reproducible; only the outcome-level agreement is meaningful.
- **pairwise sampled agreement**: mean final-verdict agreement between the
  three sampled runs (0.3 vs 0.6, 0.3 vs 1.0, 0.6 vs 1.0). Does not involve
  the greedy lane.

| model | mode | T | final [CI95] | orch [CI95] | plan hash differs | pairwise sampled agreement |
|---|---|---|---|---|---|---|
| DeepSeek-V4-Flash | global | 0.0 | 0.114 [0.103, 0.126] | 0.270 [0.258, 0.282] |  | 0.895 |
| DeepSeek-V4-Flash | global | 0.3 | 0.113 [0.102, 0.124] | 0.268 [0.256, 0.280] | 0.963 (n=1307) |  |
| DeepSeek-V4-Flash | global | 0.6 | 0.100 [0.090, 0.110] | 0.237 [0.226, 0.249] | 0.989 (n=1141) |  |
| DeepSeek-V4-Flash | global | 1.0 | 0.080 [0.071, 0.089] | 0.197 [0.186, 0.208] | 1.000 (n=998) |  |
| DeepSeek-V4-Flash | react | 0.0 | 0.446 [0.429, 0.463] | 0.590 [0.578, 0.602] |  | 0.881 |
| DeepSeek-V4-Flash | react | 0.3 | 0.456 [0.439, 0.473] | 0.591 [0.579, 0.602] |  |  |
| DeepSeek-V4-Flash | react | 0.6 | 0.448 [0.431, 0.466] | 0.585 [0.573, 0.597] |  |  |
| DeepSeek-V4-Flash | react | 1.0 | 0.434 [0.417, 0.452] | 0.575 [0.564, 0.586] |  |  |
| Qwen3.8-27B | global | 0.0 | 0.126 [0.115, 0.139] | 0.283 [0.271, 0.295] |  | 0.892 |
| Qwen3.8-27B | global | 0.3 | 0.112 [0.101, 0.124] | 0.255 [0.243, 0.267] | 0.937 (n=1359) |  |
| Qwen3.8-27B | global | 0.6 | 0.104 [0.094, 0.115] | 0.226 [0.214, 0.237] | 0.986 (n=1211) |  |
| Qwen3.8-27B | global | 1.0 | 0.069 [0.061, 0.078] | 0.161 [0.151, 0.172] | 1.000 (n=768) |  |
| Qwen3.8-27B | react | 0.0 | 0.486 [0.469, 0.504] | 0.617 [0.606, 0.628] |  | 0.898 |
| Qwen3.8-27B | react | 0.3 | 0.489 [0.473, 0.507] | 0.617 [0.605, 0.628] |  |  |
| Qwen3.8-27B | react | 0.6 | 0.474 [0.457, 0.492] | 0.611 [0.599, 0.622] |  |  |
| Qwen3.8-27B | react | 1.0 | 0.462 [0.445, 0.479] | 0.596 [0.584, 0.607] |  |  |
| gemma-4-31B | global | 0.0 | 0.048 [0.040, 0.055] | 0.127 [0.118, 0.137] |  | 0.969 |
| gemma-4-31B | global | 0.3 | 0.047 [0.040, 0.054] | 0.125 [0.115, 0.134] | 0.849 (n=671) |  |
| gemma-4-31B | global | 0.6 | 0.049 [0.042, 0.057] | 0.131 [0.121, 0.140] | 0.989 (n=652) |  |
| gemma-4-31B | global | 1.0 | 0.046 [0.038, 0.053] | 0.118 [0.109, 0.127] | 0.983 (n=595) |  |
| gemma-4-31B | react | 0.0 | 0.461 [0.444, 0.479] | 0.614 [0.603, 0.626] |  | 0.933 |
| gemma-4-31B | react | 0.3 | 0.461 [0.444, 0.477] | 0.614 [0.602, 0.625] |  |  |
| gemma-4-31B | react | 0.6 | 0.470 [0.452, 0.487] | 0.614 [0.603, 0.626] |  |  |
| gemma-4-31B | react | 1.0 | 0.465 [0.448, 0.482] | 0.615 [0.603, 0.627] |  |  |
| GLM-4.5 | global | 0.0 | 0.066 [0.058, 0.074] | 0.166 [0.156, 0.177] |  | 0.938 |
| GLM-4.5 | global | 0.3 | 0.072 [0.063, 0.081] | 0.159 [0.149, 0.169] | 0.945 (n=868) |  |
| GLM-4.5 | global | 0.6 | 0.064 [0.056, 0.072] | 0.172 [0.162, 0.183] | 0.999 (n=887) |  |
| GLM-4.5 | global | 1.0 | 0.070 [0.061, 0.078] | 0.165 [0.155, 0.175] | 1.000 (n=783) |  |
| GLM-4.5 | react | 0.0 | 0.386 [0.370, 0.403] | 0.554 [0.542, 0.565] |  | 0.891 |
| GLM-4.5 | react | 0.3 | 0.389 [0.373, 0.406] | 0.557 [0.546, 0.568] |  |  |
| GLM-4.5 | react | 0.6 | 0.385 [0.368, 0.402] | 0.553 [0.541, 0.564] |  |  |
| GLM-4.5 | react | 1.0 | 0.373 [0.356, 0.390] | 0.543 [0.531, 0.554] |  |  |
| Qwen3-30B-A3B | global | 0.0 | 0.029 [0.024, 0.035] | 0.084 [0.076, 0.091] |  | 0.970 |
| Qwen3-30B-A3B | global | 0.3 | 0.036 [0.030, 0.043] | 0.085 [0.077, 0.092] | 0.865 (n=496) |  |
| Qwen3-30B-A3B | global | 0.6 | 0.032 [0.026, 0.038] | 0.081 [0.074, 0.089] | 0.937 (n=474) |  |
| Qwen3-30B-A3B | global | 1.0 | 0.034 [0.028, 0.040] | 0.080 [0.072, 0.088] | 0.956 (n=343) |  |
| Qwen3-30B-A3B | react | 0.0 | 0.267 [0.252, 0.281] | 0.478 [0.467, 0.489] |  | 0.887 |
| Qwen3-30B-A3B | react | 0.3 | 0.266 [0.251, 0.281] | 0.477 [0.466, 0.488] |  |  |
| Qwen3-30B-A3B | react | 0.6 | 0.268 [0.253, 0.283] | 0.475 [0.464, 0.485] |  |  |
| Qwen3-30B-A3B | react | 1.0 | 0.273 [0.258, 0.288] | 0.477 [0.465, 0.488] |  |  |

## 7. Findings

1. **Global View is temperature-sensitive for models that can plan.**
   DeepSeek and Qwen3.8 lose 30% and 45% of their final accuracy (relative)
   from T=0 to T=1.0, and their CI95 bands at T=0 and T=1.0 do not overlap.
   The loss is driven by plan failures: plan error rises from ~44% to 56%
   (DeepSeek) and 66% (Qwen3.8). A single frozen plan is executed on every
   variant, so one sampling mistake in the plan is amplified across all
   variants of the recipe.
2. **Greedy Global View successes are fragile.** Of the variants a model
   solves greedily, 33-65% fail at T=1.0 (section 4), against an 18%
   run-to-run floor (section 7.3), and only 1-3% of all variants pass at
   every temperature (section 5). The greedy score sits near the top of the
   model's distribution, not at its typical behaviour.
3. **ReAct is robust in the mean but not per instance.** Mean final accuracy
   moves by at most 2.4 points across temperatures for every model, and all
   four CI95 bands overlap. Yet 12-20% of variants flip verdict between
   runs, and pass@any exceeds any single run by 5-10 points. Online
   observation lets the model recover from a bad sampled action, so noise
   averages out instead of compounding as in a frozen plan.
4. **Weak planners show no temperature effect** (gemma, Qwen3-30B in Global
   View): plan failures dominate at every temperature (75-80%), so sampling
   has nothing to perturb. GLM-4.5 with thinking off behaves the same way
   at a 62-64% plan error rate.
5. **Text-level diversity is far larger than outcome-level diversity.** At
   T=0.3, 85-96% of Global View plans differ textually from the greedy plan
   while verdict agreement stays above 0.92; and two greedy runs already
   differ on 67% of plans while agreeing on 95% of verdicts.

### 7.1 Qwen3.8-27B ReAct: the canonical greedy lane was stale (rerun)

The canonical Qwen3.8-27B non-thinking ReAct lane (2026-08-17,
`outputs/full_eval/large_model/Qwen3.8-27B-FP8/react`, final 0.318) stopped
with `format_error_budget` (three consecutive unparseable actions) in 1,973
of 3,220 rows; 1,184 rows executed zero actions. The last-JSON action
extractor was rewritten on 2026-08-19 (commits 49e43c7d, 92df092c), two
days after that lane finished. A greedy rerun with current code
(job 27008, `outputs/full_eval/greedy-rerun-20260907/hf:Qwen__Qwen3.8-27B-FP8/`)
reproduces the parse failures on 3 rows instead of 1,973:

| Qwen3.8-27B greedy | error | orch | final [CI95] | format_error_budget rows | zero-action rows |
|---|---|---|---|---|---|
| react, old lane (Aug 17) | 0.002 | 0.533 | 0.318 [0.302, 0.335] | 1,973 | 1,184 |
| react, rerun (Sep 7) | 0.002 | 0.617 | 0.486 [0.469, 0.504] | 3 | 132 |
| global, old lane (Aug 17) | 0.439 | 0.286 | 0.127 [0.115, 0.138] | n/a | 503* |
| global, rerun (Sep 7) | 0.448 | 0.283 | 0.126 [0.115, 0.139] | n/a | 503* |

\* Global View zero-action rows are recipes whose plan failed to parse; the
count is unchanged.

The Global View lane is unaffected (0.127 vs 0.126), so only the ReAct
action path was hit by the old extractor bug. All Qwen3.8 rows in sections
3-6 use the rerun as T=0. The canonical `results.csv` row still carries the
old 0.318 value; replacing it is a separate decision (it changes a reported
number).

### 7.2 GLM-4.5 Global View: prompt confound removed (rerun)

GLM-4.5 is a hybrid reasoner. Under greedy decoding it never opens a
`<think>` span, so the canonical lane ran without `enable_thinking=false`.
Under sampling it does open one, drafts the plan inside it, and the
no-hidden-reasoning protocol scores the generation as failed (93% plan
error on the first attempt, quarantined under
`outputs/full_eval/quarantine-glm-think-20260906/`). The sweep therefore
pins thinking off, which also changes the prompt's template marker. To make
T=0 comparable, GLM-4.5 was rerun greedily with the same flag
(job 27009, `outputs/full_eval/greedy-rerun-20260907/hf:zai-org__GLM-4.5-FP8/`):

| GLM-4.5 greedy | error | orch | final [CI95] |
|---|---|---|---|
| global, old lane (no flag) | 0.757 | 0.129 | 0.052 [0.045, 0.060] |
| global, rerun (thinking off) | 0.615 | 0.166 | 0.066 [0.058, 0.075] |
| react, old lane (no flag) | 0.001 | 0.545 | 0.383 [0.365, 0.400] |
| react, rerun (thinking off) | 0.001 | 0.554 | 0.386 [0.370, 0.403] |

With a matched prompt the greedy Global View point (0.066) sits inside the
sampled band (0.064-0.072), so the apparent "sampling helps GLM" pattern
in the first draft of this table was entirely the prompt confound. ReAct is
unchanged within noise. All GLM rows in sections 3-6 use the rerun as T=0.

### 7.3 Run-to-run noise floor (greedy vs greedy)

Old greedy lane against the 2026-09-07 greedy rerun, same metrics as
section 4. The Qwen3.8 Global View pair is a clean floor (same prompt, same
code path, only the batch composition differs); the other three pairs carry
the confound named in the last column and are listed for completeness.


| model | mode | agree (final) | greedy-pass lost | greedy-fail gained | plan hash differs | confound |
|---|---|---|---|---|---|---|
| Qwen3.8-27B-FP8 | global | 0.954 | 0.181 | 0.026 | 0.675 (n=1559) | none (clean floor) |
| Qwen3.8-27B-FP8 | react | 0.731 | 0.157 | 0.320 |  | old lane had the action-parse bug |
| GLM-4.5-FP8 | global | 0.927 | 0.563 | 0.046 | 1.000 (n=482) | old lane lacked enable_thinking=false |
| GLM-4.5-FP8 | react | 0.915 | 0.106 | 0.071 |  | old lane lacked enable_thinking=false |

Reading: with no temperature change at all, 4.6% of verdicts and 18% of
greedy passes flip between two runs, and 67.5% of plans differ textually.
Temperature effects in section 4 should be read against this floor: the
T=0.3 Global View "greedy-pass lost" values (0.18-0.37) are at or just
above it, while the T=1.0 values (0.33-0.65) are well above it.

### 7.4 Bookkeeping

- The canonical `results.csv` excludes `temp-sweep-*`, `quarantine*`, and
  `*greedy-re*` run directories, so sweep and rerun lanes do not replace
  canonical rows (they had on 2026-09-07; the restored table was verified).
- The other three models' greedy lanes were checked against their sweep
  lanes and are consistent (DeepSeek: 111 format-error rows in both the
  greedy and the T=0.3 ReAct lane; gemma and Qwen3-30B within 1 point in
  every metric), so no further reruns were needed.
