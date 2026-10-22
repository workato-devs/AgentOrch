# AgentOrch data card

## Dataset

AgentOrch contains 650 benchmark SOPs with 3,220 runtime variants and a
separate 3,000-recipe training set. The datasets provide model-visible task
specifications, reference workflows and executions, simulator state, and
prepared SFT / GRPO examples.

The corpus is derived from sanitized enterprise workflow recipes. Task
descriptions and runtime variants were produced through generation and
validation pipelines. Automated critic acceptance does not itself establish
human review.

## Intended use

The data supports research on workflow planning, tool use, orchestration,
execution-based evaluation, and training on complete symbolic workflows.
Reported model results use the deterministic simulated backend.

## Splits and information boundaries

Training and benchmark recipe IDs do not overlap. The tool ecosystem is
shared across splits; recipe separation does not imply unseen tools or
absence of structurally similar workflows.

Ground truth is available to the local evaluator. Model prompts use public
task specifications and permitted runtime observations, while reference plans,
expected outcomes, and private simulator state remain evaluator inputs. This
is an open local benchmark rather than a hosted blind test.

## Runtime data

Examples use synthetic identifiers consistently across task inputs, simulator
seeds, and expected outputs. The simulator executes reads, writes,
notifications, and deletions against local state. The optional live connector
backend requires separate service configuration and credentials.

## Reproduction

[Benchmark data](https://huggingface.co/datasets/JesseLiu/agentorch-benchmark),
[training data](https://huggingface.co/datasets/JesseLiu/agentorch-training),
and the model checkpoints linked in [README.md](README.md#models) are available
on Hugging Face. Dataset manifests describe membership and prepared-data
lineage. The repository includes the evaluator and published aggregate scores;
the maintainers' per-variant model-run archive is not distributed.

Exact model reruns can vary with provider versions, GPU kernels, and
hardware. The benchmark characterizes the included workflows and connector
interfaces; it does not establish general production readiness.

## Interpretation

See [evaluation notes](benchmark/doc/evaluation_notes.md) for exact-order
scoring, protocol differences, checkpoint selection, and reference-control
limitations. Dataset and model cards provide artifact-specific license
metadata; included third-party notices are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
