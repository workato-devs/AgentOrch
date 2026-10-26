# Evaluation metrics

AgentOrch scores realized executions against the prescribed SOP behavior,
including operation order, resulting connector state, and terminal output
(Section 3.3 and Appendix A.5).

## Execution Trace Accuracy

Execution Trace Accuracy is the mean of five binary components:

| Component | Criterion |
| --- | --- |
| Tool selection | Tool identities and call counts match the reference. |
| Tool order | The executed tool-name sequence equals the prescribed reference sequence. |
| Tool execution | Selection and order pass, without unexpected execution failures. |
| Required arguments | Executed calls provide the required reference argument values. |
| Control path | Branch, error-handling, and termination behavior matches the prescribed execution. |

Runtime values are resolved before argument comparison. Supported generated
identifiers are normalized. Salesforce and Snowflake query arguments include
operation-specific semantic checks. Components are coupled: an extra tool
call can affect selection, order, execution, and control-path agreement.

## Side-Effect Accuracy

Side-Effect Accuracy is binary. The verifier checks required state changes
and externally recorded effects, including missing, duplicated, or unintended
changes covered by that verifier. It evaluates resulting state rather than
the complete sequence of intermediate states.

## Orchestration Accuracy

For each runtime variant:

```text
Orchestration Accuracy = 0.5 × Execution Trace Accuracy
                       + 0.5 × Side-Effect Accuracy
```

This is the primary benchmark metric.

## Final Accuracy

Terminal Output Accuracy checks the terminal response against the SOP's
output contract. Final Accuracy passes only when both Side-Effect Accuracy
and Terminal Output Accuracy pass. It complements the primary metric by
checking effects and output independently of the execution trajectory.

## Errors and aggregation

Error Rate is the fraction of variants without a scoreable execution because
of planning, model, infrastructure, or evaluation failure. Those variants
remain in the denominator and receive zero accuracy.

Partial executions terminated by a tool failure or execution limit are scored
using their accumulated trajectory and simulator state. Benchmark metrics
are arithmetic means over the 3,220 variants. The workflow-characteristic
analysis uses confidence intervals from bootstrapping clustered by SOP.

See the [evaluation guide](../README.md) for commands and output files.
