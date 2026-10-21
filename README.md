# AgentOrch

AgentOrch measures whether a language model can **orchestrate a business
workflow over real connector tools**. This release has two parts:

| Folder | What it is |
|---|---|
| [`benchmark/`](benchmark/README.md) | the benchmark: 650 test recipes with 3,220 hidden runtime variants, the deterministic connector simulator, the frozen scorer, launchers, and the published result tables for 45 off-the-shelf models |
| [`training/`](training/README.md) | the training project: a 3,000-recipe training split (zero overlap with the test set), the SFT and GRPO code, prepared datasets, and the results of every fine-tuned checkpoint |
| [`results/`](results/) | one combined leaderboard that lines up every model as `<base model>-base`, `-sft` and `-rl` |

Every number in this release was produced by the same frozen harness
(`benchmark/evaluation/full_eval.py`, simulated backend, greedy decoding, all
3,220 variants). Nothing in the evaluation path differs between the
off-the-shelf models and the fine-tuned checkpoints.

## Quick start

The fastest path is a CPU-only integrity check. It does not call a model,
require credentials, or execute against live services. From the repository
root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install jsonschema==4.26.0 pytest==9.1.1

PYTHONPATH=benchmark python -m verification.connector_runner \
  --backend simulated --recipe-id 64112882 --variant 0
```

The final JSON object should contain `"verifier_ok": true`. Contributors can
then run the broader smoke suite while the publisher metadata is pending:

```bash
python scripts/release_check.py --smoke --allow-incomplete-metadata
```

The benchmark smoke path above does not need a GPU or provider account.

## Getting the data

The Git repository holds code, docs, results and one sample recipe
(`64112882`), so it clones in seconds and the smoke test runs immediately. The
full data lives on the Hugging Face Hub and unpacks into the same paths:

| What | Hugging Face dataset | Unpacks to |
|---|---|---|
| Benchmark fixtures: 650 recipes, 3,220 variants, ground truth, evaluator state | [`JesseLiu/agentorch-benchmark`](https://huggingface.co/datasets/JesseLiu/agentorch-benchmark) (`source/`) | `benchmark/input/`, `benchmark/groundtruth/`, `benchmark/verification/{dataset,evaluation_support,groundtruth,seeds}/` |
| Training recipes: 3,000 v1 prompts and reference workflows | [`JesseLiu/agentorch-training`](https://huggingface.co/datasets/JesseLiu/agentorch-training) (`source/`) | `training/input/`, `training/groundtruth/` |
| Prepared SFT / RL files exactly as trained on | [`JesseLiu/agentorch-training`](https://huggingface.co/datasets/JesseLiu/agentorch-training) | `training/data/` |

```bash
pip install huggingface_hub
python scripts/download_data.py              # benchmark + training recipes (~250 MB download)
python scripts/download_data.py --prepared   # also the prepared SFT / RL files (~930 MB)
python scripts/download_data.py --only benchmark
```

Archives are pinned to a Hub revision and checked against the SHA-256 values in
[`scripts/data_release.json`](scripts/data_release.json) before extraction.
The model-visible prompts are also published as ready-to-load configs
(`global`, `local`, `react`, `replan`) in `JesseLiu/agentorch-benchmark` for
use without this repository.

## Benchmark source code at a glance

The benchmark is not only the files in `benchmark/input/` and
`benchmark/groundtruth/`. Its complete executable runtime is vendored inside
[`benchmark/verification/`](benchmark/verification/README.md):

| What you are looking for | Location |
| --- | --- |
| Full model-evaluation entry point | [`benchmark/evaluation/full_eval.py`](benchmark/evaluation/full_eval.py) |
| Deterministic simulation environment | [`benchmark/verification/backends/simulated/src/benchmark/`](benchmark/verification/backends/simulated/src/benchmark/) |
| Simulated Slack, Jira, Salesforce, Sheets, Drive, Snowflake connectors | [`simulated_connectors.py`](benchmark/verification/backends/simulated/src/benchmark/simulated_connectors.py) |
| Workato and connector tool handlers | [`simulated_tools.py`](benchmark/verification/backends/simulated/src/benchmark/simulated_tools.py) |
| Shared recipe engine and 650 executable recipes | [`benchmark/verification/backends/shared/src/benchmark/`](benchmark/verification/backends/shared/src/benchmark/) |
| Scorer, verifier, and metric aggregation | [`benchmark/verification/backends/shared/src/metrics/`](benchmark/verification/backends/shared/src/metrics/) |
| Optional live connector implementations | [`benchmark/verification/backends/real/src/benchmark/`](benchmark/verification/backends/real/src/benchmark/) |

Run a no-credential simulator check from this directory:

```bash
PYTHONPATH=benchmark python -m verification.connector_runner \
  --backend simulated --recipe-id 64112882 --variant 0
```

The exact code path and a component-by-component map are at the top of the
[`benchmark` README](benchmark/README.md#where-are-the-benchmark-code-simulator-and-connectors).

## What can be reproduced from this checkout?

| Goal | Status | What is required |
|---|---|---|
| Validate the scorer and simulator | **Yes** | CPU only; use the smoke tests below |
| Evaluate a new local, API, or OpenAI-compatible model | **Yes** | model weights or provider access; use the frozen full evaluator |
| Inspect the committed result tables | **Yes** | frozen CSV/Markdown tables and per-lane aggregate JSON files are included; paper-only table builders are intentionally omitted |
| Re-aggregate every published per-variant result | **Maintainers only** | the 80 GB per-variant archive is kept by the maintainers and is not published; this tree ships the `leaderboard.json` aggregates and the canonical scorer |
| Re-run every published off-the-shelf model | **Partly** | the pinned public weights are identified, but gated weights, retired/mutable APIs, and provider access may prevent an exact rerun |
| Rebuild the training data | **Yes** | `training/src/data/build_sft_messages.py` + `prepare_dataset.py` reproduce the original export and the prepared files byte-for-byte (SHA-256 in `data/source_manifest_v1.json`) |
| Reproduce the fine-tuning runs | **Yes, within CI noise** | pinned base revisions (`training/src/sft/base_models.json`), the exact data, the launch settings in `training.csv`, the library patches in `training/src/rl/patches/`, `--seed` / `--deterministic` in the trainer; multi-GPU bf16 LoRA is not bit-exact across hardware |
| Download the fine-tuned checkpoints | **Pending upload** | published on the Hugging Face Hub with `training/scripts/upload_checkpoints_hf.py`; repo ids land in the `hf_repo` column of `training/results/training.csv` |
| Submit a blind/official score | **No** | this is a local research harness, not a hosted evaluation service; evaluator ground truth ships here and is only hidden from the model at runtime |

The benchmark is ready for **local, comparable evaluation of a new model**,
but this directory is not yet a complete archival reproduction of every
published run. See [Release status](#release-status) before publishing it.

## Layout

```text
community_ready/
  README.md                      this file
  DATA_CARD.md                   provenance, intended use, and limitations
  CONTRIBUTING.md                development and review workflow
  SECURITY.md                    private reporting and execution boundary
  THIRD_PARTY_NOTICES.md         bundled third-party attribution
  RELEASE_CHECKLIST.md           publisher-owned release gates
  .github/                       issue forms and pull-request template
  .env.example                   credential template (copy to .env, never commit)
  .gitignore
  results/
    combined_leaderboard.csv     every model x mode, named <base>-<base|sft|rl>
    combined_leaderboard.md      headline table + full listing
  scripts/
    build_combined_leaderboard.py   release-level combined-table builder
    download_data.py             fetch benchmark / training data from the Hugging Face Hub
    data_release.json            pinned Hub revisions and SHA-256 of every data archive
    release_check.py             offline release gate
  benchmark/
    input/                       public, model-visible prompts (650 recipes; downloaded)
    groundtruth/                 evaluator-only reference per variant (scorer only; downloaded)
    evaluation/                  canonical harness: full_eval.py + model roster
    examples/smoke_adapter/      optional two-recipe integration example
    experiments/                optional protocol-ablation drivers
    reproduction/
      offline/                  score verification for runs you already have
      cluster/                  optional Slurm launchers and campaign settings
    verification/                runtime source + evaluator-only fixtures
      backends/{shared,simulated,real}/src    vendored connector runtime and scorer
      seeds/ dataset/ groundtruth/ evaluation_support/   evaluator-private state (downloaded)
    results/                     published tables + per-lane leaderboard.json aggregates
    doc/  figures/               metric definitions, pipeline, experiments, case study, figures
    outputs/                     run outputs (created on first run, not committed)
  training/
    input/                       3,000 training recipes, v1 prompts (used by every headline run; downloaded)
    groundtruth/                 golden symbolic plans (downloaded)
    data/                        source manifests; prepared SFT / RL files via download_data.py --prepared
    src/
      data/                      split <-> chat-messages converters
      sft/                       LoRA SFT, adapter merge, checkpoint evaluation
      rl/                        GRPO reward, verl launcher (Qwen), TRL launcher (gemma-4)
      external_eval/             WorkflowBench / Seal-Tools / tau2-bench transfer harness
    results/                     training.csv, EXPERIMENTS.md, external transfer results, leaderboards
    output/                      checkpoints and logs (created on first run, not committed)
```

## Full setup

```bash
# After cloning or downloading the release repository:
cd agentorch

# 1. benchmark environment (scorer, simulator, vLLM inference)
conda create -n benchmark python=3.12 -y && conda activate benchmark
pip install -r benchmark/requirements.txt          # jsonschema alone is enough for the scorer

# 2. credentials (only what you use; the simulator needs none)
cp .env.example .env && $EDITOR .env
# Direct Python commands do not auto-load the release-root .env:
set -a; source .env; set +a

# 3. optional: Slurm site settings for the launchers
cp benchmark/reproduction/cluster/env.sh.example benchmark/reproduction/cluster/env.sh
cp training/scripts/env.sh.example  training/scripts/env.sh
```

Verify the installation without a model or GPU (about a second):

```bash
PYTHONPATH=benchmark python -m examples.smoke_adapter.eval \
  --mode global --adapter examples.smoke_adapter.example_adapter:build \
  --model-id smoke-test --run-name smoke --recipe-id 64112882 --limit 1
```

That command tests the lightweight two-recipe adapter path. Also test the
actual canonical evaluator, simulator, and scorer on one complete recipe:

```bash
export HF_LOCAL_ENGINE=vllm
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name install-check --backend simulated --state-namespace install-check \
  --model scripted-selftest --modes plan_execute,react \
  --variants all --limit 1 --scripted-selftest
```

Both emitted leaderboards should have orchestration accuracy `1.0`. This is a
harness integrity check, not a model result.

## Use the benchmark

```bash
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name my-first-run --backend simulated \
  --model hf:Qwen/Qwen3-4B-Instruct-2507 \
  --modes plan_execute,react --variants all --resume
```

`--model` accepts `hf:<org>/<name>` (local checkpoint through vLLM),
`gpt-*` / `claude-*` (API), or any id served by an OpenAI-compatible server at
`LOCAL_LLM_BASE_URL`. The four decision protocols are `plan_execute` (Global
View), `incremental_workflow` (Local View), `react` and `replan`. Details,
scoring, launchers and reproduction commands: [`benchmark/README.md`](benchmark/README.md).

### Evaluate your own model

Run a small shard first, then remove `--limit` for the comparable 650-recipe,
3,220-variant run:

```bash
# Local Hugging Face checkpoint or directory (requires the full benchmark stack)
export HF_LOCAL_ENGINE=vllm
export HF_MODEL_REVISION=cdbee75f17c01a7cc42f958dc650907174af0554
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name my-model-smoke --backend simulated \
  --model hf:Qwen/Qwen3-4B-Instruct-2507 \
  --modes plan_execute,react --variants all --limit 1

# Full comparable run
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name my-model --backend simulated \
  --model hf:Qwen/Qwen3-4B-Instruct-2507 \
  --modes plan_execute,react --variants all --resume
```

For an OpenAI-compatible server, set `LOCAL_LLM_BASE_URL` to its `/v1`
endpoint and pass a served model id that does not begin with `hf:`, `gpt`,
`o1`, `o3`, `o4`, `openai`, `azure`, `claude`, or `anthropic` (those prefixes
select built-in clients):

```bash
export LOCAL_LLM_BASE_URL=http://127.0.0.1:8000/v1
export LOCAL_LLM_API_KEY=sk-local             # optional for local servers
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name my-server-model --backend simulated \
  --model my-served-model --modes plan_execute,react --variants all --resume
```

API models use credentials exported into the process; run
`set -a; source .env; set +a` first. Use `OPENAI_API_MODE=direct` for the
OpenAI API; otherwise `gpt*`/`o*` ids use the Azure settings. A custom adapter
to `examples.smoke_adapter.eval` is useful for protocol development, but its two-recipe
smoke score is **not** comparable to the published leaderboard. Comparable
scores must come from `evaluation.full_eval` with the simulated backend,
`--variants all`, the documented decoding caps, and no prompt access to
`groundtruth/` or `verification/`.

## Train a model

```bash
conda create -n agentorch-train python=3.12 -y && conda activate agentorch-train
pip install -r training/requirements-sft.txt
cd training
# base revision is pinned in training/src/sft/base_models.json (1d4bf0f2...)
sbatch src/sft/sbatch_sft.sh --model Qwen/Qwen3.8-27B \
       --epochs 5 --max-len 81920 --save-every-steps 158 \
       --run-name sft-27b-80k-5ep --output output/checkpoints/sft-27b-80k-5ep-lora
python src/sft/merge_adapter.py --base Qwen/Qwen3.8-27B \
       --adapter output/checkpoints/sft-27b-80k-5ep-lora/step-474 \
       --out output/checkpoints/merged-27b-80k-3ep
sbatch src/sft/run_benchmark_eval.sbatch output/checkpoints/merged-27b-80k-3ep sft-27b-80k-3ep-global
```

Data preparation, the RL stage (GRPO with verl for Qwen, TRL for gemma-4) and
the full experiment record: [`training/README.md`](training/README.md).

The reported `3ep` model is step 474 (three passes) from a five-epoch cosine
schedule. A standalone `--epochs 3` run uses a different learning-rate curve
and does not reproduce that checkpoint.

## Headline results

Orchestration accuracy, Global View (`plan_execute`), from
[`results/combined_leaderboard.md`](results/combined_leaderboard.md):

| Base model | base | sft | rl |
|---|---:|---:|---:|
| Qwen3.8-27B-FP8 | 0.286 | **0.420** | 0.416 |
| Qwen3-4B-Instruct-2507 | 0.138 | 0.255 | **0.272** |
| gemma-4-26B-A4B-it | 0.041 | 0.199 | **0.239** |
| gemma-4-12B-it | 0.143 | 0.179 | **0.217** |
| gemma-4-31B-it | 0.127 | **0.196** | 0.191 |
| claude-opus-5 (reference) | 0.464 | – | – |

Off-the-shelf models plan far worse than they act: every model scores higher
in ReAct than in Global View, and the gap narrows only for the strongest
frontier models (full table in `benchmark/README.md`).

## License, citation, and attribution

This snapshot does **not** yet have a project or dataset license. Public
visibility alone does not grant permission to copy, modify, or redistribute
it. Publication remains blocked until the maintainers confirm rights to the
underlying recipe material and add a top-level `LICENSE`.

Formal citation metadata is also pending the paper title, complete author
list, release version, and canonical repository URL. Add those fields in a
valid `CITATION.cff` before creating the public release. Third-party material
already identified in the bundle is recorded in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

See the [`DATA_CARD.md`](DATA_CARD.md) for intended use and limitations, and
the [`release checklist`](RELEASE_CHECKLIST.md) for the remaining publisher
decisions.

## Release status

Resolved in this tree:

- **Training data lineage.** `training/src/data/build_sft_messages.py` and
  `training/src/sft/prepare_dataset.py` rebuild the export and the prepared
  files byte-for-byte (SHA-256 in `training/data/source_manifest_v1.json`).
- **Library patches.** The torch 2.13, accelerate 1.14 and trl 1.10 guards the
  RL runs needed ship as diffs in `training/src/rl/patches/`.
- **Training determinism controls.** Pinned base revisions in
  `training/src/sft/base_models.json` (used automatically), `--seed`,
  `--deterministic`, and a `train_config.json` written next to every run.
- **Credentials.** `evaluation.full_eval` loads the release-root `.env` itself.
- **Headline command.** The 27B headline is step 474 of a five-epoch schedule;
  the README examples say so.
- **Large files.** No Git LFS. Benchmark fixtures, training recipes and the
  prepared training files are on the Hugging Face Hub and fetched with
  `scripts/download_data.py`; only the sample recipe `64112882` is committed.
  `training/data/sft_messages_v1.jsonl` is regenerated, not shipped.
- **Release check.** `python scripts/release_check.py --smoke --write-checksums`
  verifies cardinality, manifests, lineage, tables, links, personal paths, the
  scripted self-test and the vendored tests, and writes `SHA256SUMS`.

Decisions taken:

- The 80 GB per-variant archive stays with the maintainers. The published
  numbers are auditable at the aggregate level (`results/leaderboards/`), and
  any model can be re-evaluated from scratch with the frozen harness.
- Fine-tuned checkpoints will be published on the Hugging Face Hub; run
  `training/scripts/upload_checkpoints_hf.py` after choosing the organisation.
- This is an open evaluation with local ground truth, not a hosted blind
  leaderboard.

Still to do before publishing:

1. Add the canonical repository URL, approved `LICENSE`, and complete
   `CITATION.cff`.
2. Upload the checkpoints and commit the `hf_repo` column, or label those rows
   unavailable and remove the download claim.
3. Record maintainer approval of the legal/privacy review. A known personal
   identity in frozen fixtures has been replaced consistently with a synthetic
   `corp.example` persona; the broader source-rights review remains a human
   decision.
