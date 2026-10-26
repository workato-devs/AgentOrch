# Training for Global orchestration

AgentOrch trains models to generate a complete workflow from an SOP
specification. The training set contains 3,000 source recipes, disjoint from
the benchmark by recipe ID. SFT applies loss to the workflow response.
GRPO compares generated workflows with reference workflows without executing
connectors.

## Reported results

Global Orchestration Accuracy (%) on all 3,220 benchmark variants (Table 8):

| Model | Base | SFT | SFT + RL |
| --- | ---: | ---: | ---: |
| Qwen3.8-27B | 28.57 | 41.96 | 41.14 |
| Qwen3-4B | 13.75 | 25.46 | 27.16 |
| Gemma-4-26B-A4B | 4.05 | 19.89 | 23.93 |
| Gemma-4-12B | 14.26 | 17.92 | 21.66 |
| Gemma-4-31B | 12.71 | 19.55 | 19.10 |

The ten merged models are linked in the [project README](../README.md#models).
[training.csv](results/training.csv) contains scores and model links.

## Training settings

The defaults follow Appendix A.7, Table 9:

| Setting | SFT | Qwen GRPO | Gemma GRPO |
| --- | --- | --- | --- |
| Learning rate | `1e-4` | `3e-6` for 27B | `1e-5` |
| LoRA | Rank 16, alpha 32 | Configurable in the launcher | Rank 16, alpha 32 |
| Batch | 16 sequences | 16 prompts, 8 responses per prompt | 8 prompts, 8 responses per prompt |
| Sequence limits | 81,920 tokens | 65,536 prompt / 6,144 completion | 4,096 completion |
| KL coefficient | — | `0.001` | `0.001` |
| GRPO training prompts | — | 1,000 | 1,000 |

SFT adjusts gradient accumulation to preserve a 16-sequence batch across
1, 2, 4, 8, or 16 GPUs. `--grad-accum` overrides this behavior. Training
records its arguments and library versions in the checkpoint directory.

The symbolic reward weights are validity 0.15, tool sequence 0.25,
arguments 0.35, workflow structure 0.15, and exact match 0.10. Invalid
workflow responses receive zero reward.

## Setup and data

Run commands from the repository root. Training uses Python 3.12, Linux,
and CUDA GPUs. Evaluation through an HTTP endpoint can run on CPU.

Create the SFT environment:

```bash
python3.12 -m venv .venv-sft
source .venv-sft/bin/activate
python -m pip install -r training/requirements-sft.txt
python scripts/download_data.py --only training --prepared
```

Set `HF_TOKEN` in your shell for base models that require Hub authentication.

The download provides recipe specifications, complete-workflow targets,
prepared SFT files, and the Qwen GRPO prompt set. To rebuild SFT data:

```bash
python training/src/data/build_sft_messages.py
python training/src/sft/prepare_dataset.py
```

Data preparation uses the base model's tokenizer. Set `AGENTORCH_TOKENIZER`
to select another model's tokenizer. Examples exceeding the context budget
are excluded; target workflows are preserved in full.

## Supervised fine-tuning

This Qwen3.8-27B example uses eight GPUs:

```bash
WANDB_MODE=offline torchrun --nproc-per-node 8 training/src/sft/train_sft_local.py \
  --model Qwen/Qwen3.8-27B \
  --data training/data/sft_v1_80k/train.jsonl \
  --epochs 5 --max-len 81920 --save-every-steps 158 \
  --lora-r 16 --lora-alpha 32 --lr 1e-4 --seed 0 \
  --run-name sft-27b-80k-5ep \
  --output training/output/checkpoints/sft-27b-80k-5ep-lora
```

The released Qwen3.8-27B SFT model corresponds to `step-474` of this
five-epoch cosine schedule. To train another model, replace `--model`,
choose the number of GPUs in `--nproc-per-node`, and set its output path.
Use `--max-len` to select a context budget supported by that model.

The trainer uses FSDP2, bf16, gradient checkpointing, LoRA, and assistant-only
loss. Base model versions are recorded in
[base_models.json](src/sft/base_models.json); `--model-revision` selects a
specific version for another model. The default attention implementation is
`sdpa`.

Merge the selected adapter before evaluation. For Qwen3.8 wrapper models:

```bash
python training/src/sft/merge_adapter.py \
  --base Qwen/Qwen3.8-27B \
  --adapter training/output/checkpoints/sft-27b-80k-5ep-lora/step-474 \
  --out training/output/checkpoints/merged-27b
```

For standard causal language models:

```bash
python training/src/sft/merge_simple.py \
  --base google/gemma-4-26B-A4B-it \
  --adapter training/output/checkpoints/my-gemma-lora/final \
  --out training/output/checkpoints/merged-gemma
```

Set the adapter path to the output of your training run. Both merge utilities
use the recorded base model versions by default and accept `--revision`.

## Reinforcement learning

Create a separate environment:

```bash
python3.12 -m venv .venv-rl
source .venv-rl/bin/activate
python -m pip install -r training/requirements-rl.txt
```

Apply the included [library patches](src/rl/patches/README.md) in this
environment. GRPO starts from a merged SFT checkpoint.

### Qwen with verl

Install the attention kernel against the PyTorch version in the RL environment:

```bash
python -m pip install --no-build-isolation flash-attn==2.8.3.post1
```

The downloaded `training/data/rl_verl_v1/` set contains 1,000 training
prompts. To rebuild it:

```bash
python training/src/rl/verl/make_rl_dataset.py --n 1000
```

Export the text-only model using the SFT environment:

```bash
.venv-sft/bin/python training/src/sft/export_textonly.py \
  --src training/output/checkpoints/merged-27b \
  --out training/output/checkpoints/merged-27b-textonly
```

Run Qwen3.8-27B GRPO with eight GPUs from the RL environment:

```bash
AGENTORCH_RL_PYTHON="$(command -v python)" \
  bash training/src/rl/verl/run_grpo.sbatch \
  "$PWD/training/output/checkpoints/merged-27b-textonly" grpo-27b \
  actor_rollout_ref.model.lora_rank=16 \
  actor_rollout_ref.model.lora_alpha=32
```

The launcher defaults to the Table 9 learning rate, KL coefficient, batch,
and generation limits. For Qwen3-4B, pass
`actor_rollout_ref.actor.optim.lr=1e-5`. Further verl arguments are forwarded
to its trainer. Checkpoints are written under
`training/output/rl_checkpoints/verl/<run>/`.

Convert a selected verl checkpoint into merged weights:

```bash
AGENTORCH_RL_PYTHON="$PWD/.venv-rl/bin/python" \
AGENTORCH_TRAIN_PYTHON="$PWD/.venv-sft/bin/python" \
  bash training/src/rl/verl/convert_rl_ckpt.sbatch grpo-27b 124 \
  "$PWD/training/output/checkpoints/merged-27b" merged-27b-rl
```

Use the step number saved by your run. The merged model is written to
`training/output/checkpoints/merged-27b-rl/`.

### Gemma with TRL

Build the 1,000-prompt dataset:

```bash
python training/src/rl/trl_gemma/make_trl_dataset.py --n 1000
```

Run eight-GPU GRPO:

```bash
WANDB_MODE=offline accelerate launch \
  --config_file training/src/rl/trl_gemma/accelerate_fsdp2.yaml \
  --num_processes 8 training/src/rl/trl_gemma/train_grpo_gemma.py \
  --model training/output/checkpoints/merged-gemma \
  --data training/data/rl_trl_1000 --run-name grpo-gemma \
  --num-generations 8 --batch-prompts 8 --lr 1e-5 --max-completion 4096
```

Use `accelerate_fsdp2_12b.yaml` for Gemma-4-12B. Export and merge a selected
TRL adapter using the SFT environment:

```bash
.venv-sft/bin/python training/src/rl/trl_gemma/export_adapter.py \
  --ckpt training/output/rl_checkpoints/trl/grpo-gemma/checkpoint-680 \
  --base training/output/checkpoints/merged-gemma \
  --out training/output/checkpoints/gemma-rl-adapter

.venv-sft/bin/python training/src/sft/merge_simple.py \
  --base training/output/checkpoints/merged-gemma \
  --adapter training/output/checkpoints/gemma-rl-adapter \
  --out training/output/checkpoints/merged-gemma-rl
```

Replace `checkpoint-680` with the checkpoint selected from your run.

## Evaluate a released or custom model

Activate the [evaluation environment](../benchmark/README.md#setup),
download the benchmark fixtures, and run all SOPs:

```bash
python scripts/download_data.py --only benchmark
PYTHONPATH=benchmark python -m evaluation.full_eval \
  --run-name trained-model --backend simulated \
  --model hf:JesseLiu/agentorch-sft-4b-v1-2ep \
  --modes plan_execute --variants all --resume
```

For your own merged weights, use `--model hf:/absolute/checkpoint/path`.
Each complete Global evaluation scores 3,220 variants. Results are written
under `benchmark/outputs/full_eval/<run>/<model>/plan_execute/`.

## Slurm

The same launchers can be submitted with `sbatch`. Configure the interpreter
paths in `training/scripts/env.sh`:

```bash
cp training/scripts/env.sh.example training/scripts/env.sh
mkdir -p training/output/logs
(cd training && sbatch src/sft/sbatch_sft.sh --model Qwen/Qwen3.8-27B \
  --epochs 5 --max-len 81920 --save-every-steps 158)
```

Paths passed to training launchers are resolved from `training/`.
`run_benchmark_eval.sbatch` resolves the checkpoint directory before changing
to the repository root for evaluation.
