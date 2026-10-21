Yes. The cleanest **GLOBAL+INPUT** control is:

> Give the model the same concrete public runtime input that \textsc{Step-by-Step} receives, but still require it to generate the entire workflow before execution and forbid any execution feedback.

The purpose is to separate **the value of seeing the concrete runtime input** from **the value of step-by-step execution feedback**.

You can send the following specification directly to engineering.

---

### GLOBAL+INPUT experiment specification

**Goal.** Add an ablation called `GLOBAL+INPUT` to answer:

> How much of the GLOBAL--STEP-BY-STEP gap comes from GLOBAL not seeing the concrete runtime input, versus from STEP-BY-STEP being able to adapt to intermediate execution results?

The key comparisons will be:

$$
\textsc{Global}
\quad\rightarrow\quad
\textsc{Global+Input}
\quad\rightarrow\quad
\textsc{Step-by-Step}.
$$

`GLOBAL+INPUT - GLOBAL` measures the benefit of knowing the concrete runtime input before planning.

`STEP-BY-STEP - GLOBAL+INPUT` measures the remaining advantage associated with execution-time interaction, after initial runtime-input information is controlled for.

### Exact protocol

1. **Unit of generation changes from SOP-level to runtime-variant-level.**
   Current `GLOBAL` generates one complete workflow per SOP and reuses it across all runtime variants. `GLOBAL+INPUT` must instead generate **one complete workflow independently for each runtime variant**, because each variant has a different concrete input.

2. **Model input should equal GLOBAL information plus the public concrete runtime input.**
   Provide:

   * the same task specification used in `GLOBAL`;
   * the same task description;
   * the same public input/output schemas;
   * the same public execution-context information;
   * the same workspace resources/templates;
   * the same 64 tool interfaces;
   * **the concrete public runtime input for the current variant**.

   Do **not** expose hidden connector state, fault-injection configuration, reference workflow, reference execution, expected tool sequence, evaluator outputs, or any information unavailable to `STEP-BY-STEP` at episode start.

3. **Planning remains strictly one-shot.**
   The model must produce one complete executable workflow in a single planning call, exactly as in `GLOBAL`. Do not execute tools while the model is constructing the workflow.

4. **No execution feedback during generation.**
   The model must not observe tool outputs, tool errors, connector state changes, branch outcomes, or any intermediate execution information before finalizing its workflow.

5. **Freeze the workflow after generation.**
   Once the complete workflow is generated and validated, execute it only on the corresponding runtime variant. There is no replanning, repair, retry using execution feedback, or second LLM call.

6. **No information sharing across variants.**
   Every runtime variant is an independent `GLOBAL+INPUT` episode. A workflow or execution result from variant \(i\) must not be available when generating the workflow for variant \(j\).

7. **Keep the planner implementation matched to GLOBAL.**
   Use the same workflow serialization, system prompt, tool descriptions, parser, workflow validator, decoding parameters, temperature, maximum output tokens, and model-specific inference configuration used for `GLOBAL`. The only intentional difference should be the addition of the concrete public runtime input.

8. **Use exactly the existing execution and evaluator.**
   After generation, execute the workflow through the same simulated connector backend and score it with the existing evaluator. Report at least Orchestration Accuracy, Final Accuracy, Side-Effect Accuracy, Execution Trace Accuracy, Terminal Output Accuracy, and Error Rate.

9. **Count failures exactly as in GLOBAL.**
   Parsing failures, invalid workflows, generation truncation, planning failures, and other non-scoreable executions should retain the existing zero-score/Error Rate treatment. Do not add special recovery logic for `GLOBAL+INPUT`.

10. **Record efficiency separately.**
    Because `GLOBAL+INPUT` generates one workflow per runtime variant rather than one per SOP, also log LLM calls, input tokens, completion tokens, and planning failures. Do not directly claim it retains GLOBAL's original efficiency advantage without reporting these costs.

---

### Prompt-level implementation

Conceptually, the existing GLOBAL input is:

```text
Task Specification
- Task description
- Input/output schemas
- Public execution context
- Workspace resources
- Templates
- Tool interfaces

Generate one complete executable workflow that can handle the task.
```

For `GLOBAL+INPUT`, change it to:

```text
Task Specification
- Task description
- Input/output schemas
- Public execution context
- Workspace resources
- Templates
- Tool interfaces

Concrete Runtime Input
- <the exact public runtime input for this variant>

Generate one complete executable workflow for this runtime instance.
The workflow must be fully specified before execution.
You will not receive tool results or execution feedback while constructing it.
```

The runtime-input representation should preferably be **identical to the representation given to STEP-BY-STEP at the beginning of its episode**. Do not rewrite or enrich it specifically for `GLOBAL+INPUT`.

### Important fairness requirement

This is the most important engineering check:

> `GLOBAL+INPUT` should see exactly the information STEP-BY-STEP has **before its first tool call**, but none of the information STEP-BY-STEP obtains **after executing its first tool call**.

That makes the comparison interpretable.

The decomposition is then:

$$
\underbrace{
\textsc{Global+Input}-\textsc{Global}
}_{\text{benefit of concrete runtime input}}
$$

and

$$
\underbrace{
\textsc{Step-by-Step}-\textsc{Global+Input}
}_{\text{residual benefit of execution-time interaction}}.
$$

### What engineering should save

For every `(model, SOP, runtime_variant)` row, save something equivalent to:

```text
model
sop_id
variant_id
protocol = global_input

planning_status
workflow_valid
workflow_json

llm_calls
prompt_tokens
completion_tokens

orchestration_accuracy
final_accuracy
side_effect_accuracy
trace_accuracy
terminal_accuracy
error_rate

executed_trace
terminal_output
```

Also preserve the raw model completion so we can later diagnose whether runtime-input access changes workflow structure or only reduces invalid plans.

### Models

Best case: run it for every model used in the main GLOBAL vs STEP-BY-STEP comparison.

If cost is limited, I would prioritize a representative set spanning capability levels and families, for example:

```text
Qwen3-4B
Gemma-4-12B
Gemma-4-26B-A4B
Qwen3.8-27B
DeepSeek-V4-Flash
Claude Opus 5
```

For models where your headline result uses a thinking/reasoning configuration, match the exact configuration used in the corresponding GLOBAL/STEP-BY-STEP comparison.

### What result would be most informative

Suppose, illustratively:

```text
GLOBAL              30%
GLOBAL+INPUT        36%
STEP-BY-STEP        45%
```

Then the original 15-point gap decomposes into:

```text
6 pp recovered by concrete runtime input
9 pp remaining after runtime input is controlled
```

That would let the paper make a much stronger statement than simply saying STEP-BY-STEP is better.

If instead:

```text
GLOBAL              30%
GLOBAL+INPUT        43%
STEP-BY-STEP        45%
```

then the interpretation changes dramatically: most of the observed gap comes from **variant-specific information at planning time**, rather than repeated execution feedback.

And if:

```text
GLOBAL              30%
GLOBAL+INPUT        32%
STEP-BY-STEP        45%
```

then you have strong evidence that **runtime feedback/adaptive decision making**, rather than initial input visibility, explains most of the advantage.

### Main table I would eventually build

Once results are available, the cleanest paper table is:

```latex
\begin{tabular}{lrrrrr}
\toprule
Model &
GLOBAL &
GLOBAL+INPUT &
STEP-BY-STEP &
Input Gain &
Residual Gap \\
\midrule
...
\bottomrule
\end{tabular}
```

where

```latex
Input Gain = GLOBAL+INPUT - GLOBAL
```

and

```latex
Residual Gap = STEP-BY-STEP - GLOBAL+INPUT.
```

I would treat `GLOBAL+INPUT` explicitly as an **information-control ablation**, not as a new primary orchestration paradigm. That keeps your storyline focused on the original question while removing one of the strongest potential confounds in the GLOBAL vs STEP-BY-STEP comparison.

---

## Implementation (2026-09-15)

Evaluator mode **`global_input`** (`--modes global_input`), same harness,
scorer, and outputs as every other mode. Every protocol item above maps to
code as follows.

| Spec item | Where | How |
| --- | --- | --- |
| 1. one plan per runtime variant | `task/run_eval.py::run_one` | for `global_input` the plan is generated inside `run_one` for the current `(recipe, variant)`; nothing is prepared per recipe |
| 2. Global information + concrete runtime input | `task/workflow_plan.py::planner_prompts(runtime_input=...)` | the Global prompt body (task, schemas, execution-context schema, workspace cards, templates, 64 tool contracts) plus one `## Concrete runtime input` section; the input is the projected public payload (`trigger_input` + `execution_context`) the executor binds `input_ref` against, nothing seeded, expected, or hidden |
| identical representation to STEP-BY-STEP | `task/prompt.py::runtime_input_parts` | ReAct's first user turn and the planner section render the runtime input through the same function (`TRIGGER EVENT:` / `EXECUTION CONTEXT:` JSON blocks, byte-identical) |
| 3./4. strictly one-shot, no feedback | `task/run_eval.py::prepare_variant_plan` | exactly one `llm.complete` with a single user turn, before any tool call; the runtime input is projected from the seed but no tool is executed and no observation exists yet |
| 5. frozen, executed on its own variant | `task/agents.py::GlobalInputAgent`, `task/runner.py::_run_symbolic` | `request_initial_plan=True, allow_replan=False`: the same deterministic interpreter as Global View, zero model calls at runtime |
| 6. no sharing across variants | `plans_global_input/<model>/<recipe>/variant_XX.json` | per-variant cache; the cache key includes the variant id and a hash of its runtime input |
| 7. planner matched to GLOBAL | `initial_plan_context(runtime_input=..., variant=...)` | same tool specs, workspace context, validation schema, parser, validator, decoding attributes, and output cap (the planner system prompt does not start with the ReAct prefix, so vLLM applies `HF_MAX_NEW_TOKENS`) |
| 8. same execution + evaluator | `metrics/plan_fidelity.py::evaluate_for_mode` | `global_input` is routed like `plan_execute`; `metrics.aggregate.leaderboard` unchanged |
| 9. failures as in GLOBAL | `run_one` | parse/validation failures and a failed planning call become `status=plan_error` rows (zero score, in the denominator); the failed artifact is cached so a resumed lane does not resample |
| 10. efficiency logged separately | row fields `planner_calls`, `planner_tokens`, `planner_prompt_tokens`, `planner_prompt_chars`, `planning_status`; `leaderboard.json["meta"]["variant_planning"]` | per-row and per-lane planning calls, prompt tokens (local clients expose `prompt_token_count`), completion tokens, failures; `results/global_input.csv` reports them next to Input Gain / Residual Gap |
| raw completion preserved | artifact `raw_response`, `runtime_input`, `planner_input` | per variant, on disk |

**One deliberate wording change.** The Global system prompt says *"Never copy a
concrete runtime value, assume a tool result, or invent a private identifier."*
With the runtime input shown that sentence is self-contradictory, so for
`global_input` only it reads *"Never assume a tool result or invent a private
identifier; the only concrete values you may use are those in the supplied
runtime input."* Everything else in the system prompt is byte-identical
(`tests/test_global_input.py` pins this). The user prompt is the Global user
prompt plus the runtime-input section and the three sentences from the
"Prompt-level implementation" above, nothing else.

**What the planner does not see.** The seeded-table environment card and the
schema card that ReAct receives in its first turn are workspace descriptions,
not runtime input; Global View already receives their public counterpart
(workspace resource cards). They are therefore not added, so the ablation
isolates the runtime input alone.

**Efficiency caveat, as required.** A `global_input` lane makes one planning
call per variant (3,220) instead of one per recipe (650). Report
`planning_calls`, `planning_prompt_tokens`, `planning_completion_tokens`, and
`planning_failures` from `results/global_input.csv` alongside any accuracy
claim; do not describe the mode as inheriting Global View's cost profile.

**Running it.**

```bash
# CPU end-to-end check with an oracle planner (no GPU/API)
PYTHONPATH=benchmark python -m experiments.global_input_selfcheck --limit 3
# unit tests
PYTHONPATH=benchmark:benchmark/verification/backends/simulated/src:benchmark/verification/backends/shared/src \
  python -m pytest benchmark/verification/backends/shared/src/tests/test_global_input.py -q
# priority roster (Qwen3-4B, gemma-4-12B, gemma-4-26B-A4B, Qwen3.8-27B (+thinking),
# DeepSeek-V4-Flash, claude-opus-5 (+thinking)) through the existing launchers
benchmark/reproduction/cluster/submit_global_input.sh global-input-<date> [recipe_limit] [--dry-run]
# any single model: its launcher with modes=global_input
benchmark/reproduction/cluster/large_model/Qwen3.8-27B-FP8.sh global-input-<date> "" global_input
# tables once lanes are complete
# Each lane writes leaderboard.json and results.jsonl automatically.
# Combine lane leaderboards with your preferred analysis tool if needed.
```

Outputs: `outputs/full_eval/<run>/<model>/global_input/{results.jsonl,trajectories.jsonl,leaderboard.json}`
and the per-variant plan artifacts under `outputs/full_eval/<run>/plans_global_input/`.
