# Training for Global orchestration

AgentOrch trains models to generate a complete executable workflow from an
SOP specification. The training corpus contains 3,000 source recipes disjoint
from the benchmark by recipe ID. SFT uses LoRA with loss on the workflow
response. GRPO further optimizes symbolic workflow similarity without
executing generated workflows.

## Reported results

Global Orchestration Accuracy (%) on all 3,220 benchmark variants (Table 8):

| Model | Base | SFT | SFT + RL |
| --- | ---: | ---: | ---: |
| Qwen3.8-27B | 28.57 | 41.96 | 41.14 |
| Qwen3-4B | 13.75 | 25.46 | 27.16 |
| Gemma-4-26B-A4B | 4.05 | 19.89 | 23.93 |
| Gemma-4-12B | 14.26 | 17.92 | 21.66 |
| Gemma-4-31B | 12.71 | 19.55 | 19.10 |

The better of SFT and SFT + RL improves over the base by 12.18 percentage
points on average. [training.csv](results/training.csv) records metrics,
confidence intervals, and model links. The ten merged models
are linked in the [project README](../README.md#models).

## Data and code

From the repository root:

```bash
python -m pip install huggingface_hub
python scripts/download_data.py --only training --prepared
```

The download provides recipe specifications under `input/`, complete-workflow
targets under `groundtruth/`, and prepared SFT/GRPO data under `data/`.
Prepared downloads include the SFT data and Qwen GRPO prompt set.
Build the 1,000-prompt Gemma GRPO set with the command below.
Each recipe has 64 tool cards; the targets span 1,033 tool operations across
305 namespaces. Target validation checks workflow structure and tool interfaces
without execution. See Appendix A.6 and [DATA_CARD.md](../DATA_CARD.md).

| Directory | Purpose |
| --- | --- |
| `src/data/` | Convert recipe specifications and reference workflows into training examples. |
| `src/sft/` | Prepare SFT data, train LoRA adapters, merge/export checkpoints, and evaluate. |
| `src/rl/verl/` | Qwen GRPO data preparation, training, and checkpoint conversion. |
| `src/rl/trl_gemma/` | Gemma GRPO training and adapter export. |
| `src/rl/patches/` | Library compatibility patches required by the training stack. |
| `results/` | The five reported base/SFT/RL comparisons and aggregate records. |
| `output/` | Checkpoints and logs created during training. |

Base versions are recorded in [base_models.json](src/sft/base_models.json).
SFT defaults to those versions unless `--model-revision` is supplied.

## Set up

```bash
# SFT environment
conda create -n agentorch-train python=3.12 -y && conda activate agentorch-train
pip install -r training/requirements-sft.txt

# RL environment (verl pins an older transformers; keep it separate)
conda create -n agentorch-rl python=3.12 -y && conda activate agentorch-rl
pip install -r training/requirements-rl.txt
# flash-attn 2.8.3.post1 was built from source against torch 2.13 (pip install --no-build-isolation flash-attn==2.8.3.post1)

# Slurm site settings
cp training/scripts/env.sh.example training/scripts/env.sh && $EDITOR training/scripts/env.sh
```

`env.sh` names the three interpreters (SFT, RL, benchmark), the Hugging Face
cache, the credential file (`WANDB_API_KEY` is optional; without it runs log
offline) and an optional CUDA toolkit. Every launcher sources it relative to
its own location, so jobs can be submitted from any directory; the examples
below run from `training/` so the relative Slurm `--output` paths resolve.
Scoring checkpoints needs the benchmark environment from
[`../benchmark/README.md`](../benchmark/README.md).

## 1. Prepare the data

The prepared SFT files are downloaded into `data/`. GRPO uses 1,000
training prompts selected by prompt length, as described in Appendix A.7.
To rebuild the prepared data from `input/` and `groundtruth/`, or prepare
a different context budget, run the data builders below. The builders preserve
source row order and use a seeded train/evaluation split.

```bash
cd training
# Recipe files -> chat-messages JSONL
python src/data/build_sft_messages.py                 # -> data/sft_messages_v1.jsonl
# length filter with the exact Qwen tokenizer (rows over the budget are DROPPED, never truncated)
python src/sft/prepare_dataset.py                     # 80k budget -> data/sft_v1_80k/
# RL prompt sets (short prompts with complete-workflow targets)
python src/rl/verl/make_rl_dataset.py --n 1000        # -> data/rl_verl_v1/
python src/rl/trl_gemma/make_trl_dataset.py --n 1000   # -> data/rl_trl_1000/
```

Use the downloaded `data/sft_v1_80k/{train,eval}.jsonl` to reproduce the
reported data configuration. The data builders can also prepare alternative
context budgets and RL prompt subsets.

## 2. Supervised fine-tuning

`train_sft_local.py` runs pure data-parallel LoRA SFT: a full bf16 copy of the
model per GPU, gradient checkpointing, loss masked to the assistant turn,
`enable_thinking=False` in the chat template (inference uses the same
setting). Rows whose target exceeds 6,144 tokens are dropped at load time
because the benchmark caps plans at 4,096 decoded tokens.

```bash
cd training
sbatch src/sft/sbatch_sft.sh --max-rows 24                       # smoke test

# headline 27B: step 474 (three passes) from a five-epoch cosine schedule
# --model-revision defaults to the pin in src/sft/base_models.json
sbatch src/sft/sbatch_sft.sh --model Qwen/Qwen3.8-27B \
       --epochs 5 --max-len 81920 --save-every-steps 158 \
       --lora-r 16 --lora-alpha 32 --lr 1e-4 --seed 0 \
       --run-name sft-27b-80k-5ep --output output/checkpoints/sft-27b-80k-5ep-lora

# gemma-4 (sliding-window attention: sdpa is the only working implementation)
sbatch src/sft/sbatch_sft.sh --model google/gemma-4-26B-A4B-it --attn-impl sdpa --epochs 2 \
       --max-len 81920 --run-name sft-gemma26b-v1 --output output/checkpoints/sft-gemma26b-v1-lora
```

The SFT configuration is described in Appendix A.7, Table 9. The trainer seeds torch, CUDA and the sampler
(`--seed`, default 0), pins the base revision (`--model-revision`, defaulting to
`$HF_MODEL_REVISION` and then to `src/sft/base_models.json`), optionally
requests deterministic kernels (`--deterministic`) and writes
`train_config.json` with every argument and library version next to the
checkpoints. Multi-GPU bf16 LoRA is still not bit-exact across GPU counts or
drivers. Configuration requirements:
gemma-4's head dimension exceeds FlashAttention-2's limit; flex-attention
recompiles per sequence length.

### Merge the adapter

Qwen3.8 checkpoints are multimodal wrappers whose text tree differs from the
class the adapter was trained on. A naive `merge_and_unload` silently merges
nothing. `merge_adapter.py` merges on the training class, transplants the
changed tensors into the wrapper shards and **fails hard** if the adapter did
not attach:

```bash
python src/sft/merge_adapter.py --base Qwen/Qwen3.8-27B \
       --adapter output/checkpoints/sft-27b-80k-5ep-lora/step-474 \
       --out output/checkpoints/merged-27b-80k-3ep
# standard causal LMs (gemma-4, Qwen3-4B)
python src/sft/merge_simple.py --base google/gemma-4-26B-A4B-it \
       --adapter output/checkpoints/sft-gemma26b-v1-lora/final \
       --out output/checkpoints/merged-gemma26b-v1
```

### Score a checkpoint on the benchmark

```bash
sbatch src/sft/run_benchmark_eval.sbatch output/checkpoints/merged-27b-80k-3ep sft-27b-80k-3ep-global
```

Results land in `../benchmark/outputs/full_eval/<run_name>/`; `leaderboard.json`
there contains the aggregate evaluation scores.

## 3. Reinforcement learning (GRPO)

Both routes optimise the same **symbolic-match reward**
(`src/rl/reward.py`, deterministic, CPU, milliseconds): 0.15 valid JSON plan
+ 0.25 tool-sequence LCS + 0.35 canonical-argument match + 0.15 control-node
structure + 0.10 exact-match bonus, against the recipe's golden plan. Group
size 8, KL anchor to the SFT policy.

**Library patches.** Both routes needed one-line guards in torch 2.13,
accelerate 1.14 and trl 1.10 (unused vision-tower parameters under FSDP2, tied
`lm_head` grouping for gemma-4, buffer sync into colocated vLLM). The diffs
and how to apply them are in [`src/rl/patches/`](src/rl/patches/README.md).

**verl 0.9 (Qwen)**. Start from the merged SFT checkpoint; for the 27B
wrapper model first export the text-only view:

```bash
cd training
python src/sft/export_textonly.py --src output/checkpoints/merged-27b-80k-3ep \
       --out output/checkpoints/merged-27b-80k-3ep-textonly
sbatch src/rl/verl/run_grpo.sbatch output/checkpoints/merged-27b-80k-3ep-textonly grpo-27b-3ep \
       actor_rollout_ref.model.lora_rank=16 actor_rollout_ref.model.lora_alpha=32 \
       actor_rollout_ref.actor.optim.lr=3e-6 \
       actor_rollout_ref.actor.use_kl_loss=True actor_rollout_ref.actor.kl_loss_coef=0.001
# verl checkpoint -> merged, benchmark-ready model
sbatch src/rl/verl/convert_rl_ckpt.sbatch grpo-27b-3ep 124 output/checkpoints/merged-27b-80k-3ep merged-27b-3ep-rl-step124
```

**TRL GRPOTrainer (gemma-4)**. verl 0.9 cannot load gemma-4, so the gemma leg
uses TRL with colocated vLLM (tensor parallel 8) and LoRA r16/a32:

```bash
sbatch src/rl/trl_gemma/run_trl_grpo.sbatch \
       --model output/checkpoints/merged-gemma26b-v1 --run-name trl-grpo-gemma26b-v1
sbatch src/rl/trl_gemma/run_trl_grpo.sbatch --accel-config accelerate_fsdp2_12b.yaml \
       --model output/checkpoints/merged-gemma12b-v1 --run-name trl-grpo-gemma12b-v1
# FSDP2 checkpoint -> PEFT adapter -> merged model
python src/rl/trl_gemma/export_adapter.py --ckpt output/rl_checkpoints/trl/trl-grpo-gemma26b-v1/checkpoint-680 \
       --base output/checkpoints/merged-gemma26b-v1 --out output/checkpoints/gemma26b-rl-step680-adapter
python src/sft/merge_simple.py --base output/checkpoints/merged-gemma26b-v1 \
       --adapter output/checkpoints/gemma26b-rl-step680-adapter --out output/checkpoints/merged-gemma26b-rl-step680
```

Then score with `run_benchmark_eval.sbatch` as above. Appendix A.7, Table 9 gives the RL configuration. Finding: the
symbolic-match reward lifts weak SFT bases (4B +1.7, gemma-26B +4.0, gemma-12B +3.7)
and is flat or slightly negative on the strong 27B 3-epoch SFT.

## Evaluate the trained model

Use the [canonical evaluator](../benchmark/README.md#run-an-evaluation) with
`--model hf:<checkpoint>` and `--modes plan_execute`. Results are written under
`benchmark/outputs/full_eval/<run>/<model>/plan_execute/`.

Reported evaluation scores are in [training.csv](results/training.csv).
Aggregate records are in `results/leaderboards/`.
