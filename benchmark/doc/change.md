# Evaluation contract

The canonical evaluator uses the same plan normalization, execution, and
scoring rules for every model. This document summarizes the behavior needed
to interpret generated plans and cached runs.

## Plan normalization

A Global response contains a `plan` array. The validator accepts deterministic
JSON shorthand where the meaning is unambiguous:

- Bare scalar values are treated as literals.
- An omitted or null `else` or `catch` region is treated as an empty region.
- A single node in a region can be wrapped into a one-element array.

Normalization does not choose tools or infer missing business logic. Unknown
tools, invalid argument shapes, duplicate bindings, and unresolved references
remain validation errors. See
[`workflow_plan.py`](../verification/backends/shared/src/task/workflow_plan.py)
for the executable grammar.

## Frozen plans and caches

Global generates one variant-blind plan per SOP and reuses it across runtime
variants. Local constructs a plan incrementally before execution. Replan
starts with a frozen plan and can revise its unexecuted suffix after feedback.
Global+Input creates a separate plan for each concrete runtime input.

Cache entries bind a plan to its model, prompt, and generation settings. A
cached invalid response can be parsed and validated again when loading it;
that operation does not call the model. Use a new run name when changing a
model, endpoint, or evaluation configuration.

## Scoring

Orchestration Accuracy is the equally weighted mean of execution-trace and
side-effect accuracy. Final Accuracy requires both the expected side effects
and a correct terminal output. Failed rows stay in the denominator.

Exact trace checks, normalized semantic diagnostics, and structural plan
fidelity are separate outputs. Metric definitions are in
[`metric.md`](metric.md), and interpretation limits are in
[`evaluation_notes.md`](evaluation_notes.md).

## Model interfaces

The evaluator supports local Hugging Face inference, provider APIs, and
self-hosted Chat Completions endpoints. The explicit `compat:` prefix routes
served model names to the configured endpoint. Local generation budgets
reserve output space within the context window.

The [model roster](../evaluation/global_react_models.json) records the model
configurations used in the reported comparisons. The
[reproduction tools](../reproduction/README.md) can rescore or aggregate
result files from an existing run.
