# AgentOrch data card

## Summary

AgentOrch contains a 650-recipe test split with 3,220 runtime variants and a
disjoint 3,000-recipe training split. The release includes model-visible
prompts, evaluator-only symbolic plans and state, a deterministic connector
simulator, prepared training data, and aggregate model results.

The corpus was derived from workflow recipe JSON. Task descriptions and input
variants were produced through automated generation and validation pipelines;
critic acceptance is not equivalent to human review.

## Intended use

The data supports research on tool-using agents, workflow planning,
orchestration protocols, deterministic replay, and fine-tuning for symbolic
plans. The simulated backend is the intended reproducible evaluation surface.

This dataset is not evidence that a model can safely execute arbitrary
workflows in production. It must not be used to authorize unsupervised access
to real business systems or consequential decisions.

## Splits and leakage

The release checker verifies 650 test recipes, 3,000 training recipes, and zero
recipe-ID overlap. Ground truth is shipped locally so results are auditable;
this makes the repository unsuitable as a secret or hosted blind test set.
Evaluated models must not receive files under `groundtruth/` or
`benchmark/verification/` in their context.

## Sensitive operations and privacy

Recipes can represent reads, writes, notifications, and deletions. The
simulator performs those operations only against deterministic local state.
The real backend is optional and requires an independently reviewed,
least-privilege sandbox.

A known personal identity found during release review was replaced with a
synthetic `corp.example` persona across public prompts, seeds, reference
outputs, verifier fixtures, and runtime constants. This mechanical
anonymization preserves equality relationships used by the tasks. Automated
checks reduce risk but do not replace the maintainers' final privacy and
source-rights review.

## Reproducibility and limitations

Manifests and `SHA256SUMS` bind the released files. Aggregate result JSON is
included, while the roughly 80 GB row-level output archive and model
checkpoints are distributed separately or remain pending upload. API models,
gated checkpoints, GPU kernels, and provider changes can prevent exact reruns.
Multi-GPU bf16 training is not expected to be bit-for-bit identical across
hardware.

The benchmark emphasizes workflows expressible by the included connector and
recipe distributions. Results should not be generalized to arbitrary tools,
organizations, languages, or production safety.

## Licensing

No project or dataset license has been selected for this snapshot. Confirm
rights to the underlying recipe material and add a top-level `LICENSE` before
public distribution. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
for material with a separately identified license.
