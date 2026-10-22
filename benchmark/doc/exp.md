# Experiments: Global Workflow Planning versus ReAct

This section documents the eight-model comparison in a form that can be
adapted directly for the paper. It specifies the evaluated models, the exact
information available to a model in each setting, the model output protocol,
the evaluator-only ground truth, and the computation of every reported score.
All paths are relative to `benchmark/` unless stated otherwise.

## Experimental question

We study whether an instruction-tuned language model is more effective when it
must compile an automation workflow before observing runtime data, or when it
can choose actions interactively after observing connector results. We compare
two settings over the same business tasks, runtime variants, tool catalog,
simulated connectors, and scoring procedure:

- **Global View (`plan_execute`)**: the model receives a recipe-level public
  specification and emits one complete symbolic `WorkflowPlan`. The plan is
  frozen and executed unchanged on every hidden runtime variant of that
  recipe.
- **ReAct (`react`)**: the model receives one concrete public runtime input and
  emits one JSON tool action per turn. After each action, the simulated
  connector returns an observation that becomes part of the next model input.

The comparison therefore changes the information and decision schedule, not
the task, connector implementation, or ground-truth target. Global View tests
variant-independent workflow compilation; ReAct tests variant-specific online
execution.

## Dataset and execution environment

The benchmark contains 650 automation recipes and 3,220 recipe--variant
instances. A recipe describes a business process; its variants instantiate
different triggers, seeded connector states, branches, loop cardinalities,
and error conditions. Each model is evaluated once on every instance in both
settings. Thus each model contributes 3,220 Global View rows and 3,220 ReAct
rows. Failed generations and executions remain in the denominator and receive
zero on every primary metric.

All model executions reported here use the deterministic `simulated` backend.
Before each episode, the evaluator creates an isolated connector state from a
private seed. The model sees only a coarse environment card (for example, a
table identifier and its public columns), never the seeded row values. The
evaluator executes the model's calls, records the resulting trajectory and
final state, and compares them with the frozen variant ground truth. Separate
state namespaces prevent contamination across parallel workers.

We expose the broad workspace tool catalog rather than only the gold tools.
Consequently, tool selection is part of the task: most exposed tools are
distractors, and unnecessary calls can reduce trace correctness.

## Models and inference configuration

We evaluate eight decoder-only instruction-tuned models spanning 0.5B to 32B
parameters and two model families.

| Model | Nominal size | Size tier |
| --- | ---: | --- |
| Qwen2.5-0.5B-Instruct | 0.5B | Small |
| Llama-3.2-1B-Instruct | 1B | Small |
| Qwen2.5-1.5B-Instruct | 1.5B | Small |
| Llama-3.2-3B-Instruct | 3B | Small |
| Qwen2.5-7B-Instruct | 7B | Medium |
| Llama-3.1-8B-Instruct | 8B | Medium |
| Qwen2.5-14B-Instruct | 14B | Medium |
| Qwen2.5-32B-Instruct | 32B | Large |

Every checkpoint is pinned to the revision recorded in
`evaluation/global_react_models.json`. We run the eight models concurrently as
an eight-task Slurm array, allocating one H200 GPU, eight CPU cores, and 100 GB
of host memory to each model. Inference uses vLLM with bfloat16 weights,
greedy decoding (`temperature=0`, `do_sample=false`), seed 0, prefix caching,
and no prompt truncation. The context window is 131,072 tokens and the maximum
accepted input is 122,880 tokens. Qwen2.5 checkpoints use their documented
4x YaRN extension when the native configuration is shorter than the requested
context.

The executed launcher sets a 4,096-token maximum for the one-shot Global View
plan. For ReAct it sets an 8,192-token hard maximum per turn, while generation
stops as soon as one complete top-level JSON object is produced. ReAct is also
bounded by an action budget. If the efficient reference trace has $G_i$
actions and uses $S_i$ connector families, the primary budget is

\[
B_i = \max(G_i + 3, \lceil 1.5G_i \rceil, S_i + 2),
\]

and execution is allowed at most $2B_i$ actions. The benchmark additionally
records whether success occurred within $1.0B_i$, $1.5B_i$, and $2.0B_i$,
but these budget-sensitivity fields are diagnostics rather than the headline
metrics.

## What the model sees and produces

The following table summarizes the model/evaluator boundary. “Ground truth”
is always evaluator-only.

| Setting | Initial model input | Subsequent model input | Model output | Ground-truth use |
| --- | --- | --- | --- | --- |
| Global View | Recipe objective and requirements; public input/output schemas; public workspace resources and templates; broad tool contracts; symbolic plan grammar | None during planning | One JSON object, `{"plan": [...]}`, containing a complete symbolic workflow | The plan is executed on every hidden variant and each grounded trajectory/state/output is scored |
| ReAct | Objective and requirements; output contract; broad tool contracts; one concrete trigger; public execution context; coarse environment card | Previous model actions and connector observations | One JSON action per turn, `{"thought": ..., "tool": ..., "args": ...}` | The resulting interactive trajectory/state/output is scored for that variant |

### Global View input

Global View is deliberately variant-blind. For a given recipe, every runtime
variant shares the same system and user prompts. The prompt describes the
input schema but does not reveal a concrete trigger payload or seeded rows.
The model must therefore express runtime values symbolically with constructs
such as `input_ref`, `output_ref`, `loop_ref`, `error_ref`, and deterministic
expressions.

An abridged input for recipe `102467097` is:

```text
SYSTEM:
You design complete, executable automation workflows.
Create one complete recipe-level WorkflowPlan covering every behavior ...
Never copy a concrete runtime value, assume a tool result, or invent a
private identifier ... Return exactly one JSON object and no prose.

USER:
Design the complete symbolic WorkflowPlan for this task.

Objective
Provide authorized callers with a bounded, chronologically ordered listing
of package versions deprecated after a supplied timestamp.

Requirements
- If no enabled workspace authorization record links the caller's access
  profile to request.workspace_user_id, return HTTP 401.
- Otherwise retrieve at most 200 deprecated package versions after
  request.deprecated_since, order them from earliest to latest, and return
  HTTP 200.
- On a protected-path error, return HTTP 400 with "Unexpected Error".

Public input schema: ...
Public output schema: ...
Public workspace context: ...
Available tool contracts: ...
Symbolic value and node shapes: ...

The top-level response is exactly {"plan":[]}.
```

The omitted sections are not hidden from the model; they are abbreviated here
only for readability. The actual prompt for this recipe is approximately
241 KB because it contains the full public resource and broad tool schemas.

### Global View output

The model returns a complete symbolic program once per recipe. For example,
the beginning of the actual Claude Opus 5 output for recipe `102467097` was:

```json
{
  "plan": [
    {
      "kind": "call",
      "tool": "workato_db_table.get_records",
      "arguments": {
        "table_id": "7201",
        "filters": [
          {
            "field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24",
            "op": "eq",
            "value": {"kind": "input_ref", "path": ["context", "access_profile", "id"]}
          },
          {
            "field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2",
            "op": "eq",
            "value": {"kind": "input_ref", "path": ["request", "workspace_user_id"]}
          },
          {
            "field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63",
            "op": "eq",
            "value": true
          }
        ]
      },
      "bind": "authorization_lookup"
    },
    {
      "kind": "if",
      "condition": {
        "kind": "expression",
        "op": "is_present",
        "args": [
          {"kind": "output_ref", "binding": "authorization_lookup", "path": ["records", 0]}
        ]
      },
      "then": ["... protected retrieval and HTTP 200 path ..."],
      "else": ["... HTTP 401 path ..."]
    },
    {"kind": "return", "value": {"kind": "literal", "value": null}}
  ]
}
```

The evaluator parses and validates the plan, assigns deterministic node IDs,
and freezes it. Bare JSON scalars are normalized to literals; omitted
`else`/`catch` regions are normalized to empty regions. Unknown tools, missing
required arguments, duplicate bindings, invalid references, and malformed
program structure remain plan errors. A valid frozen plan is grounded against
each variant's concrete trigger and connector observations without any further
model call.

### ReAct input

The ReAct system prompt contains the same business objective and public tool
contracts, but requests exactly one action per turn. The first user message
adds the concrete public trigger and a coarse description of the initialized
environment. For the same recipe and variant `00`, the relevant part is:

```text
TRIGGER EVENT:
{
  "context": {"access_profile": {"id": "10"}},
  "request": {
    "deprecated_since": "2025-01-01",
    "workspace_user_id": "U12345678"
  }
}

ENVIRONMENT:
- Data table 7199: columns [...]
- Data table 7201: columns [...]

PUBLIC WORKFLOW CONTEXT:
{ ... public schemas, resources, templates, and control actions ... }

Begin. Emit your next action as JSON.
```

The environment card reveals that the tables and columns exist, but not their
row values. Those values become visible only if the model performs an
appropriate read.

### ReAct output and observation loop

The actual Claude Opus 5 interaction for this variant can be abbreviated as:

```json
{"thought":"First check authorization.","tool":"workato_db_table.get_records","args":{"table_id":"7201","filters":[{"field_id":"e417aefa_9690_4edd_83c5_8e3f8749fc24","op":"eq","value":"10"},{"field_id":"9d00233f_dc89_4f40_b0f4_c2b6ee765ed2","op":"eq","value":"U12345678"},{"field_id":"73fd1e82_f4d2_48a9_8ff2_96713f5acd63","op":"eq","value":true}]}}
```

The simulator then returned an observation containing one authorized workspace
record. The model issued the protected query:

```json
{"thought":"Authorized; retrieve qualifying versions.","tool":"workato_db_table.get_records","args":{"table_id":"7199","filters":[{"field_id":"e3bdb7a7_3561_48c0_b600_c210f5d64bb7","op":"eq","value":true},{"field_id":"3c0b720b_bbe8_47de_a88d_96d759af819e","op":"gt","value":"2025-01-01"}],"limit":200,"order_by_field_id":"3c0b720b_bbe8_47de_a88d_96d759af819e","order_direction":"asc"}}
```

The returned record contained the nested package object
`{"record_id":"Bench record_id","display_name":"Bench display_name"}`.
Using this observation, the model emitted the terminal action:

```json
{"thought":"Return the observed package identifiers.","tool":"workato_api_platform.return_response","args":{"http_status_code":"200","response":{"deprecations":[{"deprecated_at":"2026-01-01","id":"rec_001","name":"Acme Approval","package_id":"Bench record_id","package_name":"Bench display_name"}]}}}
```

The terminal connector call ends the episode. The saved model output for ReAct
is the full sequence of model JSON messages, connector observations, grounded
tool calls, final state, and stop reason.

## Evaluator-only ground truth

Each `groundtruth/recipes/<recipe_id>/variant_<id>.json` bundle is frozen before
model evaluation. It is never concatenated into either prompt. A bundle
contains:

- `workflow_plan`: the canonical recipe-level control flow and symbolic
  dataflow;
- `active_trace`: the branch decisions, loop events, and tool calls active for
  this variant;
- `reference_tool_calls`: grounded expected calls and their expected results;
- `final_snapshot`: the expected observable connector state;
- `terminal_result` and `terminal_contract`: the expected caller-visible
  response;
- `tool_expectations`: compatibility projections used by auxiliary checks;
- `hidden_variant_state`: the private trigger support data and simulator seed.

For recipe `102467097`, variant `00`, the relevant ground truth is:

```json
{
  "reference_tool_calls": [
    {
      "tool": "workato_db_table.get_records",
      "args": {
        "table_id": "7201",
        "filters": [
          {"field_id": "e417aefa_9690_4edd_83c5_8e3f8749fc24", "op": "eq", "value": "10"},
          {"field_id": "9d00233f_dc89_4f40_b0f4_c2b6ee765ed2", "op": "eq", "value": "U12345678"},
          {"field_id": "73fd1e82_f4d2_48a9_8ff2_96713f5acd63", "op": "eq", "value": true}
        ]
      }
    },
    {
      "tool": "workato_db_table.get_records",
      "args": {
        "table_id": "7199",
        "filters": [
          {"field_id": "e3bdb7a7_3561_48c0_b600_c210f5d64bb7", "op": "eq", "value": true},
          {"field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e", "op": "gt", "value": "2025-01-01"}
        ],
        "limit": 200,
        "order_by_field_id": "3c0b720b_bbe8_47de_a88d_96d759af819e",
        "order_direction": "asc"
      }
    },
    {
      "tool": "workato_api_platform.return_response",
      "args": {
        "http_status_code": "200",
        "response": {
          "deprecations": [
            {
              "deprecated_at": "2026-01-01",
              "id": "rec_001",
              "name": "Acme Approval",
              "package_id": "Bench record_id",
              "package_name": "Bench display_name"
            }
          ]
        }
      }
    }
  ],
  "terminal_result": {
    "deprecations": [
      {
        "deprecated_at": "2026-01-01",
        "id": "rec_001",
        "name": "Acme Approval",
        "package_id": "Bench record_id",
        "package_name": "Bench display_name"
      }
    ]
  },
  "final_snapshot": {
    "workato_db_table": {"tables": {"7199": ["..."], "7201": ["..."]}}
  }
}
```

The reported eight-model experiment does **not** generate ground truth during
model evaluation. It reuses these frozen canonical reference bundles while
executing model actions with simulated connectors. The source evaluator can
rebind identifiers originating in live reference runs to newly provisioned
simulator identifiers, but the exported bundle does not include a per-variant
field that proves which backend originally produced each reference trace.
Accordingly, the defensible paper wording is “frozen canonical reference
executions,” not “we freshly reran every ground-truth trace on real connectors.”

## Metrics

Scoring occurs independently for each recipe--variant instance $i$. We report
three primary metrics—Orchestration Accuracy, Side-Effect Accuracy, and Final
Accuracy—and two diagnostic metrics—Execution-Trace Accuracy and
Terminal-Output Accuracy.

### Execution-Trace Accuracy

The evaluator computes five binary components:

1. **Tool selection** ($s_i$): the multiset of non-structural business tools
   exactly matches the active reference trace. Missing calls, duplicate calls,
   and extra reads or writes fail this component.
2. **Tool order** ($o_i$): the business-tool sequence exactly matches the
   active canonical sequence. Dependency-DAG-compatible alternative orders are
   retained only as a diagnostic.
3. **Tool execution** ($e_i$): selected calls execute successfully in the
   expected sequence, except for a failure explicitly required by the variant.
4. **Required arguments** ($a_i$): aligned calls contain the required canonical
   arguments. Ordinary connector slots use canonical exact/subset comparison;
   declared SQL/SOQL/query slots may pass through audited result-, execution-,
   or state-semantic equivalence.
5. **Control path** ($c_i$): the grounded active branch/loop/terminal path
   matches the reference active trace. At runtime this is reflected by the
   active business-call sequence; recipe-level static branch structure is also
   retained as a plan-fidelity diagnostic.

The diagnostic score is the equally weighted mean:

\[
\mathrm{TraceAcc}_i = 0.2(s_i + o_i + e_i + a_i + c_i).
\]

If a component is not applicable, the aggregation helper treats it as a
vacuous pass. A generation or infrastructure failure receives zero rather than
being omitted.

### Side-Effect Accuracy

Side-Effect Accuracy is binary:

\[
\mathrm{SideEffectAcc}_i \in \{0,1\}.
\]

It is one only when the model produces the required observable state while
matching required non-terminal external effects and transient lifecycle
events. Durable mutations are checked through the final connector snapshot.
External writes without a read-back state representation (for example, an
accepted Slack post) are checked through their successful outbound call
records. Transient operations such as stop--start sequences are checked as an
ordered event list. Terminal response calls are excluded from this component.

For a read-only task, Side-Effect Accuracy is one when the expected state is
preserved and no unexpected external effect is introduced. This separation is
intentional: a read-only agent may preserve state yet return the wrong answer.

### Orchestration Accuracy

The headline metric gives equal weight to trace quality and realized effects:

\[
\mathrm{OrchAcc}_i =
0.5\,\mathrm{TraceAcc}_i + 0.5\,\mathrm{SideEffectAcc}_i.
\]

It provides partial credit for a mostly correct orchestration trace while
still imposing a large penalty for failing to realize the required state.

### Terminal-Output Accuracy

Terminal-Output Accuracy is binary. It is one when the model's caller-visible
terminal value matches the expected value after the benchmark's documented
schema-aware normalization. For example, declared Workato scalar encodings and
structural return aliases are normalized before comparison. If no terminal
output is expected, the model must produce neither a terminal result nor a
terminal-response call.

\[
\mathrm{TerminalAcc}_i \in \{0,1\}.
\]

The evaluator also retains an exact terminal comparison and a similarity score
as diagnostics, but the reported `terminal_output_accuracy` uses the normalized
verdict.

### Final Accuracy

Final Accuracy is the strict conjunction of correct side effects and terminal
output:

\[
\mathrm{FinalAcc}_i =
\mathbb{1}[\mathrm{SideEffectAcc}_i=1 \land
           \mathrm{TerminalAcc}_i=1].
\]

Thus a workflow that mutates the environment correctly but returns the wrong
response receives zero Final Accuracy; so does one that returns the expected
text without performing the required mutation.

### Dataset aggregation

For any per-instance metric $m_i$, the reported model/setting score is the
micro-average over all $N=3{,}220$ attempted instances:

\[
\overline{m} = \frac{1}{N}\sum_{i=1}^{N}m_i.
\]

Rows with `plan_error`, `llm_error`, `infra_error`, or another non-`ok` status
contribute zero. This prevents a model from improving its score by failing on
difficult instances. The leaderboard also reports error rate and
cluster-bootstrap 95% confidence intervals for Orchestration and Final
Accuracy. Resampling is grouped by the stable recipe--variant task identity so
repeated runs of the same instance remain together.

## Worked scoring example: why ReAct can outperform a frozen plan

The Global View and ReAct trajectories shown above are actual outputs from
Claude Opus 5 on recipe `102467097`, variant `00`. The reference response
requires extracting `record_id` and `display_name` from a nested package
object.

The frozen Global View plan selected the correct three tools in the correct
order and successfully executed the authorized branch. However, before seeing
the runtime record it mapped the entire nested package object into
`package_id` and looked for `display_name` at the wrong level. Its terminal
response therefore contained:

```json
{
  "package_id": {
    "record_id": "Bench record_id",
    "display_name": "Bench display_name"
  },
  "package_name": null
}
```

instead of:

```json
{
  "package_id": "Bench record_id",
  "package_name": "Bench display_name"
}
```

The per-instance calculation is:

| Component | Global View | ReAct |
| --- | ---: | ---: |
| Tool selection ($s_i$) | 1 | 1 |
| Tool order ($o_i$) | 1 | 1 |
| Tool execution ($e_i$) | 1 | 1 |
| Required arguments ($a_i$) | 0 | 1 |
| Control path ($c_i$) | 1 | 1 |
| Execution-Trace Accuracy | $0.2(1+1+1+0+1)=0.8$ | $0.2(1+1+1+1+1)=1.0$ |
| Side-Effect Accuracy | 1.0 | 1.0 |
| Orchestration Accuracy | $0.5(0.8)+0.5(1)=0.9$ | $0.5(1)+0.5(1)=1.0$ |
| Terminal-Output Accuracy | 0.0 | 1.0 |
| Final Accuracy | 0.0 | 1.0 |

Side-Effect Accuracy is one for the faulty Global View execution because this
variant is read-only and the database remains in the required state. Final
Accuracy nevertheless fails because the terminal response is wrong. ReAct
observes the nested row representation before constructing its response and
therefore maps both fields correctly.

Two additional counterfactuals clarify the metric separation:

| Trace | Side effect | Terminal | Orchestration | Final | Interpretation |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0.8 | 1 | 0 | 0.9 | 0 | Mostly correct workflow and preserved/correct state, but wrong caller output |
| 1.0 | 0 | 1 | 0.5 | 0 | Correct-looking calls and response, but required mutation is absent or wrong |

## Eight-model results

The following table reports the current canonical frozen-run results for the
eight local instruction-tuned models. `Orch.`, `Side`, and `Final` are the
three primary metrics; `Err.` is the fraction of attempted instances whose
model generation or execution did not produce a scored `ok` row. All values
are micro-averages over 3,220 instances.

| Model | Setting | Orch. | Side | Final | Err. |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen2.5-0.5B | Global | 0.0013 | 0.0022 | 0.0000 | 0.9978 |
|  | ReAct | 0.3646 | 0.4885 | 0.1245 | 0.0022 |
| Llama-3.2-1B | Global | 0.0000 | 0.0000 | 0.0000 | 1.0000 |
|  | ReAct | 0.3693 | 0.4910 | 0.1326 | 0.0053 |
| Qwen2.5-1.5B | Global | 0.0166 | 0.0252 | 0.0022 | 0.9643 |
|  | ReAct | 0.3141 | 0.4062 | 0.0891 | 0.0025 |
| Llama-3.2-3B | Global | 0.0207 | 0.0270 | 0.0112 | 0.9528 |
|  | ReAct | 0.3550 | 0.4776 | 0.1311 | 0.0019 |
| Qwen2.5-7B | Global | 0.0263 | 0.0345 | 0.0047 | 0.9345 |
|  | ReAct | 0.3050 | 0.3950 | 0.0742 | 0.0109 |
| Llama-3.1-8B | Global | 0.0445 | 0.0528 | 0.0134 | 0.8804 |
|  | ReAct | 0.3482 | 0.4823 | 0.1280 | 0.0022 |
| Qwen2.5-14B | Global | 0.0533 | 0.0693 | 0.0161 | 0.8540 |
|  | ReAct | 0.4154 | 0.5388 | 0.2146 | 0.0003 |
| Qwen2.5-32B | Global | 0.1618 | 0.1860 | 0.0640 | 0.5814 |
|  | ReAct | 0.4564 | 0.5652 | 0.2441 | 0.0034 |

ReAct outperforms Global View on all three primary metrics for every evaluated
model. The largest Global View failure source is failure to emit a valid,
complete recipe-level symbolic plan within the output contract; this appears
in the high Global error rates. Among valid plans, the remaining failures
include incorrect symbolic references, branch/loop structure, and argument
projection. Larger models generally improve Global View, with Qwen2.5-32B
substantially ahead of the smaller checkpoints, but model family and protocol
also matter: parameter count alone does not determine ReAct performance.

These are descriptive comparisons from one deterministic run per instance.
Any claim of statistical significance should use the stored bootstrap
confidence intervals rather than infer significance from point estimates
alone.

## Reproduction and scoring details

The public task specifications are in `input/recipes/`, and evaluator-only
reference data are in `groundtruth/recipes/` and `verification/`. Model
configurations are recorded in `evaluation/global_react_models.json`.
Evaluate a model with `evaluation.full_eval` to create its plans,
trajectories, per-variant scores, and aggregate leaderboard.

The compact adapter scorer delegates side-effect, terminal-output, and final
verdicts to the same outcome module. Its execution-trace checks are simplified
and can differ from canonical runtime adjudication. Use the canonical
evaluator for comparable model scores. The offline parity utility can compare
outcome verdicts in an existing run.

Global plans have a 4,096-token output cap. Local-model ReAct turns have an
8,192-token hard cap and a 1,024-token soft cap, with complete-JSON stopping;
API ReAct requests use a 4,096-token cap. These are per-mode generation limits,
not an identical compute budget. The model roster records the executed
settings, and [evaluation notes](evaluation_notes.md) describe interpretation
limits.
