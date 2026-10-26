# Evaluation pipeline

AgentOrch starts from executable enterprise recipes. Each reference recipe
defines one SOP; task specifications describe its requirements, and runtime
variants instantiate inputs and connector conditions. The benchmark contains
650 SOPs, 3,220 variants, and 64 tool interfaces.

## Model inputs

A public specification contains the task description, input/output schemas,
execution context, workspace resources, communication templates when applicable,
and tool interfaces. It excludes reference workflows and executions, hidden
connector state, fault settings, and concrete runtime inputs.

Global and Local use that specification before execution. Step-by-Step also
receives the concrete runtime input and subsequent tool observations.
Input-Conditioned Global receives the concrete input before generating a
complete workflow. Replan receives feedback from executions of its own
workflow between revision rounds.

## Execution

`evaluation.full_eval` loads selected fixtures, activates the simulated
backend, configures output/state directories, and invokes the shared
`task.run_eval` evaluator. Global workflows are parsed and validated before
deterministic execution across variants. Local builds a workflow through an
append-only editor. Step-by-Step selects one tool action per turn.

`experiments.replan_iter` runs the paper's complete-workflow revision loop;
`experiments.replan_iter_heldout` restricts feedback to designated variants.
Each workflow execution uses fresh simulator state. The model does not receive
reference plans, reference traces, or scorer verdicts.

## Scoring

The evaluator compares executed behavior with reference executions collected
through real connectors. Five binary trace checks measure tool selection,
order, execution, required arguments, and control path. Orchestration Accuracy
averages their mean with Side-Effect Accuracy. Final Accuracy requires both
correct side effects and terminal output.

Per-variant records are written to `results.jsonl`, execution observations to
`trajectories.jsonl`, and aggregates to `leaderboard.json`. Failed generations
and non-scoreable executions remain in the denominator at zero accuracy.

See the [evaluation guide](../README.md) for runnable commands and
[metric definitions](metric.md) for the scoring contract.
