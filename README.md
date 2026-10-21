# AgentOrch

**How close can global orchestration come to step-by-step interaction?**

Zijie Liu<sup>1</sup>, Qi Yang Huang<sup>2</sup>, Jinhao Duan<sup>1</sup>, Yueh Che Lee<sup>2</sup>, Thomas A. Joseph<sup>2</sup>,
Zayne Turner<sup>2</sup>, Adam Seligman<sup>2</sup>, Tianlong Chen<sup>1</sup>, Zhaozhuo Xu<sup>2</sup>
<br><sup>1</sup>University of North Carolina at Chapel Hill &nbsp; <sup>2</sup>Workato

[Benchmark data](https://huggingface.co/datasets/JesseLiu/agentorch-benchmark) ·
[Training data](https://huggingface.co/datasets/JesseLiu/agentorch-training) ·
[Checkpoints](#released-artifacts) ·
[Leaderboard](#leaderboard) ·
[Citation](#citation)

Enterprise workflow agents usually work **step by step**: run one action,
observe the result, and call the LLM again. **Global orchestration** instead
has the LLM write one complete executable workflow up front, which then runs
with no further LLM calls. AgentOrch compares the two directly on 650
enterprise SOPs and 3,220 runtime variants, using the same tools, the same
simulated environment, and the same scorer for both.

![AgentOrch benchmark construction and evaluation pipeline](benchmark/figures/agentorch_pipeline.png)

## Key findings

- **Step-by-Step is more accurate for every one of the 31 models**, but the
  gap has shrunk by about 79%: from 40.67 pp for GPT-3.5 Turbo to 8.53 pp for
  Claude Opus 5 Thinking.
- **Global is much cheaper.** Step-by-Step makes 15.4×–35.4× more LLM calls
  and generates 1.42×–5.29× more completion tokens.
- **Scale, newer generations, and reasoning do not reliably close the gap.**
  Giving Global the concrete runtime input changes its accuracy by only
  −0.18 pp on average.
- **Three routes narrow it:**
  - incremental workflow construction (Local): +9.98 pp, with no execution
    feedback;
  - execution-feedback revision (Replan): +6.13 pp on held-out variants;
  - training on complete workflows: +12.18 pp across five models.
- **The bottleneck is specifying calls before execution.** 83.9% of the
  workflows Replan repairs parse correctly but get tool arguments or
  references between steps wrong.

## Leaderboard

Orchestration Accuracy (%) on all 650 SOPs / 3,220 variants. Each score is the
mean of Execution Trace Accuracy and Side-Effect Accuracy per variant, and
failed executions score zero. Gap = Step-by-Step − Global. Paper Table 20.

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

Every model, mode, and metric (Final, Side-Effect, Trace, Terminal, Error
Rate) is in [`benchmark/results/`](benchmark/results/) and
[`results/combined_leaderboard.md`](results/combined_leaderboard.md).

### Training for global orchestration

Global Orchestration Accuracy (%) after training on 3,000 source recipes that
do not overlap with the benchmark. Δ compares the better of SFT and RL with the
base model (paper Table 8).

| Model | Base | SFT | SFT + RL | Δ |
|---|--:|--:|--:|--:|
| Gemma-4-26B-A4B | 4.05 | 19.89 | **23.93** | +19.88 |
| Qwen3-4B | 13.75 | 25.46 | **27.16** | +13.41 |
| Qwen3.8-27B | 28.57 | **41.96** | 41.14 | +13.39 |
| Gemma-4-12B | 14.26 | 17.92 | **21.66** | +7.40 |
| Gemma-4-31B | 12.71 | **19.55** | 19.10 | +6.84 |

## Quick start

A CPU-only check needs no model, credentials, GPU, or downloaded data. It runs
the simulator and scorer on the sample recipe committed in this repository:

```bash
git clone https://github.com/jesseliu0913/AgentOrch.git && cd AgentOrch
python3 -m venv .venv && source .venv/bin/activate
pip install jsonschema==4.26.0 pytest==9.1.1

PYTHONPATH=benchmark python -m verification.connector_runner \
  --backend simulated --recipe-id 64112882 --variant 0     # expect "verifier_ok": true
python scripts/release_check.py --smoke --allow-incomplete-metadata
```

## Get the data

This repository holds code, docs, result tables, and one sample recipe
(`64112882`). Everything else is on the Hugging Face Hub and unpacks into the
paths the code expects:

```bash
pip install huggingface_hub
python scripts/download_data.py              # benchmark + training recipes (~250 MB)
python scripts/download_data.py --prepared   # also the prepared SFT / RL files (~930 MB)
python scripts/download_data.py --only benchmark
```

| Data | Hugging Face | Unpacks to |
|---|---|---|
| Benchmark: 650 SOPs, 3,220 variants, ground truth, evaluator state | [`JesseLiu/agentorch-benchmark`](https://huggingface.co/datasets/JesseLiu/agentorch-benchmark) `source/` | `benchmark/input/`, `benchmark/groundtruth/`, `benchmark/verification/{dataset,evaluation_support,groundtruth,seeds}/` |
| Training: 3,000 recipes, prompts and reference workflows | [`JesseLiu/agentorch-training`](https://huggingface.co/datasets/JesseLiu/agentorch-training) `source/` | `training/input/`, `training/groundtruth/` |
| Prepared SFT / RL files, exactly as trained on | [`JesseLiu/agentorch-training`](https://huggingface.co/datasets/JesseLiu/agentorch-training) | `training/data/` |

Archives are pinned to a Hub revision and verified against the SHA-256 values
in [`scripts/data_release.json`](scripts/data_release.json) before
extraction. To use the model-visible prompts without this repository, load the
`global`, `local`, `react`, or `replan` config of `JesseLiu/agentorch-benchmark`
with `datasets`.

## Evaluate a model

```bash
pip install -r benchmark/requirements.txt
python scripts/download_data.py --only benchmark

# smoke: one recipe; remove --limit and add --resume for the comparable full run
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name my-model --backend simulated \
  --model hf:Qwen/Qwen3-4B-Instruct-2507 \
  --modes plan_execute,react --variants all --limit 1
```

| Paper protocol | `--modes` value | What the model does |
|---|---|---|
| Global | `plan_execute` | writes one complete workflow before seeing runtime inputs; it is reused for every variant |
| Step-by-Step | `react` | sees the runtime input, makes one tool call per turn, and observes each result |
| Local | `incremental_workflow` | builds the workflow node by node through a validating editor, with no execution |
| Replan | `replan` | revises its Global workflow from execution feedback; still no LLM calls at run time |

`--model` accepts:
- `hf:<org>/<name>`: a local checkpoint served through vLLM (`HF_LOCAL_ENGINE=vllm`);
- `gpt-*` / `claude-*`: the provider APIs (credentials in `.env`, see `.env.example`);
- any model id served by an OpenAI-compatible endpoint at `LOCAL_LLM_BASE_URL`.

Comparable scores must come from `evaluation.full_eval` with the simulated
backend, `--variants all`, and no prompt access to `groundtruth/` or
`verification/`. Scoring details, launchers, and every reproduction command are
in [`benchmark/README.md`](benchmark/README.md).

## Train a model

```bash
pip install -r training/requirements-sft.txt
python scripts/download_data.py --only training --prepared
cd training
sbatch src/sft/sbatch_sft.sh --model Qwen/Qwen3.8-27B \
       --epochs 5 --max-len 81920 --save-every-steps 158 \
       --run-name sft-27b-80k-5ep --output output/checkpoints/sft-27b-80k-5ep-lora
```

The reported 27B SFT model is step 474 (three passes) of this five-epoch cosine
schedule. A standalone `--epochs 3` run uses a different learning-rate curve.
SFT uses LoRA (r=16, α=32). RL uses GRPO with verl for Qwen and TRL for Gemma
4. The reward compares the sampled workflow with the reference without
executing it. Data preparation, RL, and the full experiment record are in
[`training/README.md`](training/README.md).

## Released artifacts

| Artifact | Link |
|---|---|
| Benchmark prompts and source fixtures | [`JesseLiu/agentorch-benchmark`](https://huggingface.co/datasets/JesseLiu/agentorch-benchmark) |
| Training recipes and prepared SFT / RL sets | [`JesseLiu/agentorch-training`](https://huggingface.co/datasets/JesseLiu/agentorch-training) |

Fine-tuned checkpoints (merged weights). **Bold** marks the one reported in the
training table above.

| Base model | SFT | SFT + RL |
|---|---|---|
| Qwen3.8-27B | [**agentorch-sft-27b-80k-3ep**](https://huggingface.co/JesseLiu/agentorch-sft-27b-80k-3ep) | [agentorch-rl-27b-3ep-step124](https://huggingface.co/JesseLiu/agentorch-rl-27b-3ep-step124) |
| Qwen3-4B | [agentorch-sft-4b-v1-2ep](https://huggingface.co/JesseLiu/agentorch-sft-4b-v1-2ep) | [**agentorch-rl-4b-v1-step60**](https://huggingface.co/JesseLiu/agentorch-rl-4b-v1-step60) |
| Gemma-4-26B-A4B | [agentorch-sft-gemma26b-v1-2ep](https://huggingface.co/JesseLiu/agentorch-sft-gemma26b-v1-2ep) | [**agentorch-rl-gemma26b-step680**](https://huggingface.co/JesseLiu/agentorch-rl-gemma26b-step680) |
| Gemma-4-12B | [agentorch-sft-gemma12b-v1-2ep](https://huggingface.co/JesseLiu/agentorch-sft-gemma12b-v1-2ep) | [**agentorch-rl-gemma12b-final**](https://huggingface.co/JesseLiu/agentorch-rl-gemma12b-final) |
| Gemma-4-31B | [**agentorch-sft-gemma31b-v1-1ep**](https://huggingface.co/JesseLiu/agentorch-sft-gemma31b-v1-1ep) | [agentorch-rl-gemma31b-final](https://huggingface.co/JesseLiu/agentorch-rl-gemma31b-final) |

## Repository layout

```text
AgentOrch/
  benchmark/
    evaluation/        full_eval.py (canonical harness) and model roster
    verification/      connector simulator, recipe engine, frozen scorer (backends/);
                       evaluator-private fixtures are downloaded
    input/ groundtruth/  model-visible prompts / per-variant references (downloaded)
    examples/ experiments/ reproduction/   smoke adapter, ablation drivers, launchers
    results/ figures/ doc/                 published tables, figures, metric definitions
  training/
    src/               data converters, LoRA SFT, GRPO (verl / TRL), external transfer evals
    input/ groundtruth/  3,000 training recipes and reference workflows (downloaded)
    data/              source manifests; prepared SFT / RL files (downloaded with --prepared)
    results/           training.csv, experiment record, leaderboards
  results/             combined leaderboard: every model as base / sft / rl
  scripts/             download_data.py, data_release.json, release_check.py
```

## Scope and reproducibility

- **Evaluation runs locally against public ground truth.** The scorer and the
  ground truth ship with the release and are hidden from the model only at run
  time. Nothing is held out on a server for blind scoring.
- **The simulator matches the real connectors.** Replaying the recorded
  real-connector actions in the simulator gives 98.54% Orchestration Accuracy
  (paper Appendix D).
- **Per-variant traces are not published.** The 80 GB per-variant result
  archive stays with the maintainers. Aggregate `leaderboard.json` files for
  every run are in `benchmark/results/leaderboards/` and
  `training/results/leaderboards/`.
- **Training data rebuilds exactly.** `training/src/data/build_sft_messages.py`
  and `prepare_dataset.py` reproduce the prepared files byte for byte
  (SHA-256 in `training/data/source_manifest_v1.json`).
- **Fine-tuning reruns are close but not bit-exact.** Base revisions are
  pinned in `training/src/sft/base_models.json`, and RL library patches are in
  `training/src/rl/patches/`. Multi-GPU bf16 LoRA is not bit-exact across
  hardware.

See [`DATA_CARD.md`](DATA_CARD.md) for provenance, intended use, and
limitations. The benchmark covers structured enterprise workflows over 64 tool
interfaces. It is not evidence that a model can safely run arbitrary workflows
against live business systems.

## License

No license has been selected yet, so the code and data are not yet licensed
for reuse. Open items are tracked in
[`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md). Third-party material is listed
in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Citation

```bibtex
@misc{liu2026agentorch,
  title  = {AgentOrch: How Close Can Global Orchestration Come to Step-by-Step Interaction?},
  author = {Liu, Zijie and Huang, Qi Yang and Duan, Jinhao and Lee, Yueh Che and Joseph, Thomas A.
            and Turner, Zayne and Seligman, Adam and Chen, Tianlong and Xu, Zhaozhuo},
  year   = {2026}
}
```

Contact: Zijie Liu ([jesseliu@cs.unc.edu](mailto:jesseliu@cs.unc.edu))
