# AgentOrch metrics

Every recipe-variant receives three primary metrics in `[0, 1]`:

- `orchestration_accuracy`
- `side_effect_accuracy`
- `final_accuracy`

The scorer also returns two diagnostic metrics:
`execution_trace_accuracy` and `terminal_output_accuracy`. Failed model runs
remain in the denominator and receive zero for every metric.

## 1. Execution-trace accuracy (diagnostic)

Execution-trace accuracy is the former standalone orchestration score. It
measures whether the generated workflow or interactive trajectory follows the
required workflow logic. Five binary components have equal weight:

| Component | Pass criterion | Weight |
| --- | --- | ---: |
| Tool selection | The active business-tool multiset is correct. | 0.2 |
| Tool order | Active business-tool calls occur in the required order. | 0.2 |
| Tool execution | Required calls succeed, except a declared expected failure. | 0.2 |
| Required semantic arguments | Each aligned required argument has the required business meaning. | 0.2 |
| Control path | The executed branch, error, and terminal behavior matches the required active path. | 0.2 |

For variant `i`:

```text
execution_trace_accuracy_i =
    0.2 × (selection + order + execution + arguments + control_path)
```

Each component is `1` when it passes and `0` otherwise. Four correct
components score `0.8`; all five score `1.0`.

Example: the agent calls the correct two tools in the correct order with the
right arguments, but follows the wrong terminal path. Its execution-trace
accuracy is `0.2 × (1 + 1 + 1 + 1 + 0) = 0.8`.

## 2. Side-effect accuracy (primary)

Side-effect accuracy evaluates the resulting environment independently of the
terminal response. It is binary for each variant and equals `1` only when:

- the final backend state contains the required state;
- every required non-terminal write or lifecycle transition occurs;
- no required effect is missing or duplicated; and
- the effect calls have the required tools, order, and semantic arguments.

Otherwise it is `0`. Read-only operations and terminal-response calls are not
classified as side effects. If a task requires no external mutation, this
metric is `1` when the expected state is preserved and no unexpected effect is
performed.

Example: an agent updates the correct record but also performs an extra
lifecycle mutation. The final trace may look mostly correct, but
side-effect accuracy is `0`.

## 3. Orchestration accuracy (primary)

Orchestration accuracy gives equal weight to workflow-logic quality and the
realized environment effect:

```text
orchestration_accuracy_i =
    0.5 × execution_trace_accuracy_i
    + 0.5 × side_effect_accuracy_i
```

Execution trace contributes 50% and side effect contributes 50%. This keeps
partial credit for correct workflow logic while applying a substantial penalty
when the workflow fails to produce the required state change.

| Execution trace | Side effect | Orchestration |
| ---: | ---: | ---: |
| 1.0 | 1.0 | 1.0 |
| 0.8 | 1.0 | 0.9 |
| 1.0 | 0.0 | 0.5 |
| 0.8 | 0.0 | 0.4 |

The weighted combination is defined per variant before benchmark aggregation.

## 4. Terminal-output and final accuracy

`terminal_output_accuracy` is a binary diagnostic. It is `1` only when the
normalized terminal result, such as an API response body and status, matches
the expected output. If a variant expects no terminal output, it is `1` only
when no terminal result and no terminal-response call are present.

Final accuracy is the strict conjunction defined previously:

```text
final_accuracy_i =
    side_effect_accuracy_i AND terminal_output_accuracy_i
```

Example: an invoice lookup reads the right rows and leaves the environment in
the correct state, but returns `{}` instead of the required invoice response.
Its side-effect accuracy is `1`, terminal-output accuracy is `0`, and final
accuracy is `0`.

## Aggregation

For `N` attempted recipe-variants, calculate every metric on each variant and
then take its arithmetic mean:

```text
benchmark_metric = (1 / N) × sum(metric_i for i in variants)
```

Report the three primary means—Orchestration, Side Effect, and Final—together.
Execution Trace and Terminal Output should be retained as diagnostics so a
failure can be attributed to workflow logic, environment mutation, or output
delivery. Recipe-level means and all-variant recipe pass rates may be reported
as secondary robustness summaries.

The scorer emits the following structure:

```json
{
  "execution_trace_accuracy": 0.8,
  "execution_trace_components": {
    "tool_selection": true,
    "tool_order": true,
    "tool_execution": true,
    "required_semantic_arguments": true,
    "control_path": false
  },
  "side_effect_accuracy": 1.0,
  "orchestration_accuracy": 0.9,
  "terminal_output_accuracy": 0.0,
  "final_accuracy": 0.0
}
```
