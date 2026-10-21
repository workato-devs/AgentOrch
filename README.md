<div align="center">

# AgentOrch

### How Close Can Global Orchestration Come to Step-by-Step Interaction?

Zijie Liu¹, Qi Yang Huang², Jinhao Duan¹, Yueh Che Lee², Thomas A. Joseph²,<br>
Zayne Turner², Adam Seligman², Tianlong Chen¹, Zhaozhuo Xu²

¹ University of North Carolina at Chapel Hill · ² Workato

[Benchmark data](https://huggingface.co/datasets/JesseLiu/agentorch-benchmark) ·
[Training data](https://huggingface.co/datasets/JesseLiu/agentorch-training) ·
[Models](#models) · [Results](#results) · [Quick start](#quick-start) · [Citation](#citation)

</div>

**AgentOrch evaluates whether an LLM can write an entire executable workflow
up front, and how that compares with choosing tools one step at a time.**
Both approaches solve the same enterprise tasks with the same tools,
deterministic connector simulator, and execution-based scorer.

The benchmark contains **650 standard operating procedures (SOPs), 3,220
runtime variants, and a 64-tool interface**. A separate **3,000-recipe
training set**, disjoint by recipe ID, supports supervised fine-tuning (SFT)
and reinforcement learning (GRPO). This repository provides the evaluator,
simulator, training code, and published results; the full datasets and
**10 merged SFT / RL checkpoints** are available on Hugging Face.

![AgentOrch: benchmark construction and evaluation pipeline](benchmark/figures/agentorch_pipeline.png)

## What AgentOrch measures

An SOP specifies the business task. Runtime variants change the concrete
inputs and connector state under which that task must succeed. Evaluation
checks the executed calls, their effects on the environment, and the final
response.

| Protocol | How the model solves the task | Evaluator mode |
| --- | --- | --- |
| **Global** | Generates one complete workflow before seeing concrete runtime inputs; the workflow is reused across the SOP's variants. | `plan_execute` |
| **Step-by-Step** | Chooses one tool call at a time, observing the input and intermediate execution results. | `react` |
| **Local** | Builds a workflow incrementally with editor and validation feedback, without executing it during construction. | `incremental_workflow` |
| **Replan** | Revises a Global workflow using execution feedback, then runs the revised workflow without further LLM calls. | `replan` |

The primary comparison is **Global versus Step-by-Step**. Local, Replan, SFT,
and GRPO examine ways to improve global workflow orchestration. See the
[pipeline](benchmark/doc/pipeline.md) and [worked case](benchmark/doc/case.md)
for the execution and scoring details.

## Results

- **Step-by-Step leads across all 31 models in the main comparison.** The
  Orchestration Accuracy gap is 40.67 percentage points for GPT-3.5 Turbo
  and 8.53 points for Claude Opus 5 Thinking.
- **Global amortizes planning across runtime variants.** One generated
  workflow serves multiple executions. The [cost table](benchmark/results/COST.csv)
  records model calls, completion tokens, and the coverage of token counters.
- **Complete-workflow training improves Global accuracy.** Across five model
  families, the better of the reported SFT and SFT + RL checkpoints improves
  over the base model by 12.18 percentage points on average.

### Global versus Step-by-Step

Orchestration Accuracy (%) on all 3,220 variants. For each variant, this is
`0.5 × execution-trace accuracy + 0.5 × side-effect accuracy`. Failed
generations and executions remain in the denominator at zero. Gap is
Step-by-Step minus Global, in percentage points.

| Model | Global | Step-by-Step | Gap |
| --- | ---: | ---: | ---: |
| Claude Opus 5 Thinking | 59.88 | 68.41 | 8.53 |
| GPT-5.6 Sol Thinking | 51.76 | 66.88 | 15.12 |
| Claude Opus 5 | 46.44 | 63.52 | 17.08 |
| Qwen 3.8 27B FP8 | 28.57 | 53.31 | 24.74 |
| GPT-4o | 28.09 | 50.12 | 22.03 |
| DeepSeek V4 Flash | 27.01 | 58.99 | 31.98 |

<details>
<summary>All 31 models in the main comparison</summary>

| # | Model | Global | Step-by-Step | Gap |
|--:|---|--:|--:|--:|
| 1 | Claude Opus 5 Thinking | **59.88** | **68.41** | 8.53 |
| 2 | GPT-5.6 Sol Thinking | 51.76 | 66.88 | 15.12 |
| 3 | Claude Opus 5 | 46.44 | 63.52 | 17.08 |
| 4 | Qwen 3.8 27B FP8 | 28.57 | 53.31 | 24.74 |
| 5 | GPT-4o | 28.09 | 50.12 | 22.03 |
| 6 | DeepSeek V4 Flash | 27.01 | 58.99 | 31.98 |
| 7 | Qwen 2.5 32B | 16.18 | 45.64 | 29.46 |
| 8 | Mistral Small 3.1 24B | 14.15 | 44.71 | 30.56 |
| 9 | Qwen 3 4B | 13.75 | 41.84 | 28.09 |
| 10 | GLM-4.5 FP8 | 12.93 | 54.47 | 41.54 |
| 11 | GLM-4.5 Air FP8 | 12.28 | 48.59 | 36.31 |
| 12 | Llama 3.1 70B | 10.81 | 38.92 | 28.11 |
| 13 | Llama 3.3 70B | 10.45 | 42.98 | 32.53 |
| 14 | GPT-3.5 Turbo | 10.11 | 50.78 | 40.67 |
| 15 | Qwen 2.5 72B | 9.91 | 46.57 | 36.66 |
| 16 | Gemma 3 12B | 8.46 | 37.85 | 29.39 |
| 17 | Qwen 3 30B | 8.35 | 47.81 | 39.46 |
| 18 | Gemma 3 27B | 7.41 | 39.93 | 32.52 |
| 19 | Command R | 6.64 | 35.97 | 29.33 |
| 20 | Granite 3.1 8B | 6.52 | 34.19 | 27.67 |
| 21 | Granite 3.1 2B | 6.30 | 31.83 | 25.53 |
| 22 | Gemma 3 4B | 6.15 | 32.75 | 26.60 |
| 23 | Qwen 2.5 14B | 5.33 | 41.54 | 36.21 |
| 24 | Llama 3.1 8B | 4.45 | 34.82 | 30.37 |
| 25 | Qwen 2.5 7B | 2.63 | 30.50 | 27.87 |
| 26 | Mistral Nemo | 2.26 | 34.27 | 32.01 |
| 27 | Qwen 2.5 3B | 2.19 | 34.16 | 31.97 |
| 28 | Llama 3.2 3B | 2.07 | 35.50 | 33.43 |
| 29 | Qwen 2.5 1.5B | 1.66 | 31.41 | 29.75 |
| 30 | Qwen 2.5 0.5B | 0.13 | 36.46 | 36.33 |
| 31 | Llama 3.2 1B | 0.00 | 36.93 | 36.93 |

</details>

Full results, additional models and protocols, confidence intervals, and
error rates are in [benchmark/results/](benchmark/results/). The
[combined leaderboard](results/combined_leaderboard.md) brings base, SFT,
and RL runs together. [Metric definitions](benchmark/doc/metric.md) describe
the individual checks and aggregation.

### Training for Global orchestration

Global Orchestration Accuracy (%) for the checkpoints linked below.
Δ is the better of SFT and SFT + RL minus the base score; it is measured in
percentage points. Additional checkpoint sweeps are recorded in the
[training results](training/results/training.csv).

| Model | Base | SFT | SFT + RL | Δ |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.8-27B | 28.57 | **41.96** | 41.14 | +13.39 |
| Qwen3-4B | 13.75 | 25.46 | **27.16** | +13.41 |
| Gemma-4-26B-A4B | 4.05 | 19.89 | **23.93** | +19.88 |
| Gemma-4-12B | 14.26 | 17.92 | **21.66** | +7.40 |
| Gemma-4-31B | 12.71 | **19.55** | 19.10 | +6.84 |

## Quick start

Use **Python 3.12**. The CPU smoke suite runs on the recipe included in Git;
it needs no model, GPU, provider credentials, or dataset download.

```bash
git clone https://github.com/jesseliu0913/AgentOrch.git
cd AgentOrch
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/release_check.py --smoke --allow-incomplete-metadata
```

A successful run ends with `PASS: 0 failing check(s)`. It exercises the
Global and ReAct example adapters, a simulated connector execution, and the
evaluator tests. The metadata option allows the pending repository license
and citation files during development; the strict publication check is in
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

## Datasets

| Dataset | Contents | Hugging Face |
| --- | --- | --- |
| **Benchmark** | 650 SOPs / 3,220 variants; prompts, reference workflows, and simulator fixtures | [agentorch-benchmark](https://huggingface.co/datasets/JesseLiu/agentorch-benchmark) |
| **Training** | 3,000 disjoint recipes; reference workflows and prepared SFT / GRPO sets | [agentorch-training](https://huggingface.co/datasets/JesseLiu/agentorch-training) |

**For evaluation or training in this repository**, download the pinned
archives into the paths expected by the code:

```bash
python -m pip install huggingface_hub
python scripts/download_data.py --only benchmark          # evaluation fixtures
python scripts/download_data.py --only training --prepared # training + prepared SFT / RL sets
```

Source archives total approximately 250 MB compressed. The downloader pins
Hub revisions and verifies each source archive's SHA-256 before extraction;
revision IDs and checksums are in [scripts/data_release.json](scripts/data_release.json).

**For direct access to the model-visible prompts**, use Hugging Face Datasets:

```bash
python -m pip install datasets
```

```python
from datasets import load_dataset

prompts = load_dataset(
    "JesseLiu/agentorch-benchmark",
    "global",
    split="train",
    revision="a0328e666e7039f118b7799dffb85d6f4700a9f1",
)
print(prompts[0]["task"])
```

The benchmark configs are `global` (650 rows), `local` (650), `react` (3,220),
and `replan` (3,220). The Hub's `train` split name is a storage convention;
these are **benchmark evaluation prompts**. The training dataset provides
`sft_messages_v1`, `sft_v1_80k`, `rl_verl_v1`, `rl_trl_v1`, and
`rl_trl_v1_31b`. Configs, fields, and subset sizes are described in the dataset
cards. The Hub viewer currently has only partial ReAct / Replan conversions
and does not render the verl config; use the pinned source archives and
prepared files for complete evaluation and training.

## Models

All ten checkpoints below are public, merged weights with model configuration
and tokenizer files. Bold links identify the better of SFT and SFT + RL for
each family in the training table above.

| Base model | SFT | SFT + RL |
|---|---|---|
| Qwen3.8-27B | [**agentorch-sft-27b-80k-3ep**](https://huggingface.co/JesseLiu/agentorch-sft-27b-80k-3ep) | [agentorch-rl-27b-3ep-step124](https://huggingface.co/JesseLiu/agentorch-rl-27b-3ep-step124) |
| Qwen3-4B | [agentorch-sft-4b-v1-2ep](https://huggingface.co/JesseLiu/agentorch-sft-4b-v1-2ep) | [**agentorch-rl-4b-v1-step60**](https://huggingface.co/JesseLiu/agentorch-rl-4b-v1-step60) |
| Gemma-4-26B-A4B | [agentorch-sft-gemma26b-v1-2ep](https://huggingface.co/JesseLiu/agentorch-sft-gemma26b-v1-2ep) | [**agentorch-rl-gemma26b-step680**](https://huggingface.co/JesseLiu/agentorch-rl-gemma26b-step680) |
| Gemma-4-12B | [agentorch-sft-gemma12b-v1-2ep](https://huggingface.co/JesseLiu/agentorch-sft-gemma12b-v1-2ep) | [**agentorch-rl-gemma12b-final**](https://huggingface.co/JesseLiu/agentorch-rl-gemma12b-final) |
| Gemma-4-31B | [**agentorch-sft-gemma31b-v1-1ep**](https://huggingface.co/JesseLiu/agentorch-sft-gemma31b-v1-1ep) | [agentorch-rl-gemma31b-final](https://huggingface.co/JesseLiu/agentorch-rl-gemma31b-final) |

The Qwen3.8-27B SFT checkpoint is **step 474 of a five-epoch cosine schedule**,
corresponding to three passes through the data. Training a separate three-epoch
schedule does not reproduce that checkpoint. Model cards record base revisions,
training settings, evaluation runs, and scores.

## Evaluate your model

Install the evaluation stack in a separate environment and fetch the benchmark:

```bash
python -m pip install -r benchmark/requirements.txt
python scripts/download_data.py --only benchmark

# Local checkpoints require a compatible GPU and enough GPU memory.
export HF_LOCAL_ENGINE=vllm
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name my-model --backend simulated \
  --model hf:JesseLiu/agentorch-sft-4b-v1-2ep \
  --modes plan_execute,react --variants all --limit 1
```

This command checks one SOP. Remove `--limit 1` and add `--resume` for a full
run. To reproduce the published protocol, also apply the decoding settings in
[benchmark/README.md](benchmark/README.md#the-canonical-evaluator). Results
are written under `benchmark/outputs/full_eval/<run-name>/`.

The same evaluator accepts `hf:<org>/<model>` or local checkpoint paths,
provider model IDs, and model IDs served by an OpenAI-compatible endpoint.
For provider credentials, copy [.env.example](.env.example) to `.env` and
fill the relevant fields. Setup, model integration, and optional Slurm
launchers are documented in the [evaluation guide](benchmark/README.md).

## Train and reproduce

The [training guide](training/README.md) covers data preparation, LoRA SFT,
GRPO with verl or TRL, checkpoint merging, and evaluation. Use separate
training environments and configure `training/scripts/env.sh` before using
the Slurm launchers. The [experiment record](training/results/EXPERIMENTS.md)
includes checkpoint sweeps and negative results.

| Entry point | Purpose |
| --- | --- |
| [benchmark/](benchmark/README.md) | Evaluator, connector simulator, metrics, and model integration |
| [training/](training/README.md) | Dataset builders, SFT / GRPO, and external transfer evaluation |
| [results/](results/combined_leaderboard.md) | Combined base / SFT / RL leaderboard |
| [benchmark/reproduction/](benchmark/reproduction/README.md) | Offline scoring of your own runs and optional cluster launchers |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and automated checks |

Evaluation uses the deterministic **simulated** backend. Ground truth and
simulator state are public for local evaluation and must stay out of model
prompts. The maintainers' approximately 80 GB of per-variant run traces are
not distributed; published aggregate leaderboards are included in Git.
Fine-tuning is not bit-exact across hardware. See the [data card](DATA_CARD.md)
for provenance and limitations.

## License and citation

Hugging Face artifact cards currently declare `apache-2.0`. This Git snapshot
still has no top-level `LICENSE`; project licensing and formal citation
metadata remain tracked in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
Third-party components are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

### Citation

```bibtex
@misc{liu2026agentorch,
  title  = {AgentOrch: How Close Can Global Orchestration Come to Step-by-Step Interaction?},
  author = {Liu, Zijie and Huang, Qi Yang and Duan, Jinhao and Lee, Yueh Che and Joseph, Thomas A.
            and Turner, Zayne and Seligman, Adam and Chen, Tianlong and Xu, Zhaozhuo},
  year   = {2026}
}
```

Contact: Zijie Liu ([jesseliu@cs.unc.edu](mailto:jesseliu@cs.unc.edu)).
