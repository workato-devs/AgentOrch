# Evaluation notes

These notes describe how to interpret AgentOrch scores and reproduce
comparisons using the public evaluator.

## Canonical evaluation

[`evaluation.full_eval`](../evaluation/full_eval.py) supplies the simulator,
model client, protocol, and frozen scorer used for reported results. Global,
ReAct, Local, and Replan are scored from their executed trajectories using the
same metric implementation. The small adapter example is for protocol
integration; its trace checks are simplified and its scores are not a
substitute for the canonical evaluator.

## Exact reference order

The primary trace metric compares the successful business-call sequence with
the canonical reference sequence. A dependency-order diagnostic is recorded
separately and does not replace the primary exact-order check.

Public task requirements can permit multiple execution orders for independent
operations. A semantically valid reordering can therefore fail the primary
order check even when the dependency diagnostic passes. The primary metric
measures fidelity to the reference serialization as well as task compliance.

## Trace components

Execution-trace accuracy combines five binary checks: tool selection, tool
order, execution success, required arguments, and control path. These checks
are coupled: order and control path are derived from the executed call
sequence, and an extra successful call can affect multiple components.
Structural plan fidelity and order-relaxed diagnostics are reported
separately. The metric definitions and aggregation are in
[`metric.md`](metric.md).

## Data separation and coverage

The training and benchmark sets are disjoint by recipe ID. They share a tool
ecosystem and can contain structurally similar workflows. Results measure
workflow generalization within this environment, rather than generalization
to an entirely unseen tool vocabulary.

Variants change runtime inputs, seeded connector state, and selected error
conditions. Variant counts differ by SOP. Reported results use the simulated
backend; the optional live backend does not cover the complete benchmark.

## Training comparisons

Training targets are complete Global workflows. Improvements need not
transfer to free-form ReAct or incremental Local construction. See the
[training experiment summary](../../training/results/EXPERIMENTS.md) for
checkpoint sweeps and cross-protocol results.

Checkpoint sweeps were evaluated on the benchmark, and reported checkpoint
selection used those benchmark scores. The prepared training data also
contains an evaluation split, but the reported sweeps should not be
interpreted as selection on an independent hidden test server.

## Reference controls

`--scripted-selftest` exercises the included sample without model inference.
Its Global control translates a reference workflow into the model-facing
plan format. That translation is not universally equivalent across all
workflow constructs, so an arbitrary reference-control run is not an
expectation of perfect scores. Real model evaluation uses generated plans
and the canonical execution/scoring path.

## Reproducing aggregates

The repository includes aggregate leaderboards and the data needed to run a
new evaluation. Offline re-aggregation tools operate on the result files from
your own runs. The maintainers' per-variant generation archive is not public.
