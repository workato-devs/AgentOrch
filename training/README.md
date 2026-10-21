# AgentOrch Training

Fine-tune open models to raise their **Global View** (`plan_execute`) score on
the AgentOrch benchmark. The recipe is a LoRA SFT warm-up on the 3,000-recipe
training split, optionally followed by GRPO with a symbolic-match reward. Every
checkpoint is scored with the frozen benchmark harness
(`../benchmark/evaluation/full_eval.py`) under exactly the protocol used for
the off-the-shelf models.

## Results at a glance

Orchestration accuracy, Global View, all 3,220 test variants
([`results/training.csv`](results/training.csv) has every row with CIs,
hyper-parameters, job ids and checkpoint names; the combined base / SFT / RL
view is [`../results/combined_leaderboard.md`](../results/combined_leaderboard.md)):

| Base model | base | best SFT | best SFT + RL | Notes |
|---|---:|---:|---:|---|
| Qwen3.8-27B-FP8 | 0.286 | **0.420** (3 ep, 80k, LoRA r16) | 0.416 | 90% of claude-opus-5 (0.464); error rate 0.171 beats opus (0.192). RL flat on the strong SFT base. |
| Qwen3-4B-Instruct-2507 | 0.138 | 0.255 (2 ep) | **0.272** (GRPO step 60) | RL +1.7 (significant) |
| gemma-4-26B-A4B-it | 0.041 | 0.199 (2 ep) | **0.239** (TRL GRPO step 680) | largest RL gain, +4.0 |
| gemma-4-12B-it | 0.143 | 0.179 (2 ep) | **0.217** (TRL GRPO step 460) | RL +3.7 (significant) |
| gemma-4-31B-it | 0.127 | **0.196** (1 ep, 64k) | 0.191 | only 51% of rows fit 64k under the gemma tokenizer |

Mode transfer of the headline 27B SFT model: global +13.4, replan +12.7,
react −2.2, local −4.2 points over the base. Global-only training helps the
plan-shaped protocols and slightly hurts the interactive ones.

The full experiment record, including aborted runs, incidents and negative
results, is [`results/EXPERIMENTS.md`](results/EXPERIMENTS.md).
Transfer to three external benchmarks (WorkflowBench, Seal-Tools, tau2-bench)
is in [`results/external/`](results/external/).

## Layout

`input/recipes/`, `groundtruth/recipes/` and the prepared files under `data/`
are not stored in Git; fetch them with `python scripts/download_data.py
--only training --prepared` from the repository root (see the top-level
README, "Getting the data").

```text
training/
  input/                        v1 prompts: the data behind every headline run
    manifest.json  MANIFEST.sha256
    recipes/<recipe_id>/
      PLAN_system.txt           frozen GLOBAL_VIEW system prompt (== benchmark)
      PLAN_user.txt             frozen-template user prompt, 64-card tool surface
      TRAINING_PACKAGE.json     structured model-visible input
  groundtruth/                  targets
    recipes/<recipe_id>/
      golden_trace.json         target golden trace (symbolic WorkflowPlan) + row metadata
      PLAN_assistant.txt        serialized target plan = the SFT assistant turn
  data/                         prepared training files, exactly as trained on
    sft_v1_80k/                 train.jsonl (2,789 rows) + eval.jsonl (60), 80k-token budget
    rl_verl_v1/                 GRPO prompts for verl (1,000 shortest v1 prompts), parquet
    rl_trl_v1/  rl_trl_v1_31b/  GRPO prompts for TRL (gemma-4), jsonl
    source_manifest_v{1,2}.json provenance of the two exports
  src/
    data/
      organize_training_split.py   export -> input/ + groundtruth/ (how this split was written)
      build_sft_messages.py        input/ + groundtruth/ -> chat-messages JSONL
    sft/
      prepare_dataset.py           messages JSONL -> length-filtered train/eval files
      train_sft_local.py           LoRA SFT (torchrun DDP, loss masked to the assistant turn)
      sbatch_sft.sh                Slurm launcher for train_sft_local.py
      merge_adapter.py             LoRA -> merged model for Qwen3.8 wrapper checkpoints (with no-op guards)
      merge_simple.py              LoRA -> merged model for standard causal LMs (gemma-4, Qwen3-4B)
      export_textonly.py           drop the vision tower / MTP head of a Qwen3.8 checkpoint (RL input)
      eval_checkpoint.py           quick held-out check of an adapter (parse / tool-sequence / exact match)
      run_benchmark_eval.sbatch    full benchmark evaluation of a merged checkpoint
      base_models.json             pinned Hugging Face revisions of the five base models
    rl/
      reward.py                    Tier-1 symbolic-match reward (verl signature, shared by both RL routes)
      reward_validity.py           validity-weighted variant of the reward
      patches/                     torch / accelerate / trl diffs the RL runs needed
      verl/                        GRPO with verl 0.9 (Qwen): dataset builder, launcher, checkpoint conversion
      trl_gemma/                   GRPO with TRL GRPOTrainer (gemma-4): dataset builder, trainer, launcher
    external_eval/                 harness for the three external transfer benchmarks
  results/
    training.csv                 one row per checkpoint x mode, with hyper-parameters and provenance
    ALL_RESULTS.md               AgentOrch + external-benchmark table
    EXPERIMENTS.md               full dated experiment record
    leaderboards/<run>__<mode>.json   archived leaderboard.json aggregate behind every row
    external/                    WorkflowBench / Seal-Tools summary and findings
  output/                        checkpoints and logs (created on first run, not committed)
  scripts/env.sh.example         site settings for the launchers (copy to env.sh)
  scripts/upload_checkpoints_hf.py   publish merged checkpoints to the Hugging Face Hub
  requirements-sft.txt  requirements-rl.txt
```

## Data

The training split is aligned to the benchmark's Global View distribution:

1. **Prompt template**: system and user prompts use the exact frozen
   `GLOBAL_VIEW` render served by the benchmark at test time.
2. **Tool surface**: every recipe is padded to exactly **64 tool cards**,
   sorted by name, like the benchmark's shared catalog. Distractors are drawn
   (seeded per recipe) from the benchmark's 64 canonical cards plus all 1,036
   unique training tool cards.
3. **Prompt length** is targeted at the benchmark's empirical user-prompt
   length distribution; **workspace resources** are padded to the benchmark's
   per-recipe counts.
4. **Zero overlap** with the 650 test recipes (verified).

Two prompt versions were built. **v1** (`input/`) keeps needed tool cards in
their raw-recipe style; v2 rewrote every card into the canonical catalog form.
A single-variable ablation on Qwen3-4B showed v2 *hurts* by 4.5 points, so
every headline run uses v1 and only v1 is distributed. Targets are identical;
`data/source_manifest_v2.json` records the v2 export settings.

Only Global View is covered; Local View, ReAct and Replan have no training
data here. Needed cards and canonical distractor cards can also have slightly
different contract shapes, and roughly 1% of the source recipes have unusually
large schemas; these are known residual distribution limitations.

### Reproducibility boundary

The recipe inputs, targets, prepared SFT/GRPO datasets, training code,
aggregate evaluation results, and hyperparameters are included. The trained
weights and training logs are not. Exact reruns also require the immutable
base snapshots listed below and, for the Qwen verl route, the local PyTorch
FSDP2 guard described in `results/EXPERIMENTS.md` (the patch itself is not in
this release). Until those artifacts are published, this project supports
independent retraining but not byte-identical reconstruction of every reported
checkpoint. The SFT code fixes the sampler seed but does not expose a complete
model-initialization/RNG seed or force deterministic CUDA kernels, so a fresh
training run should be treated as a statistical reproduction.

| Base | Revision used |
|---|---|
| `Qwen/Qwen3.8-27B` | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` |
| `Qwen/Qwen3-4B-Instruct-2507` | `cdbee75f17c01a7cc42f958dc650907174af0554` |
| `google/gemma-4-12B-it` | `707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7` |
| `google/gemma-4-26B-A4B-it` | `4d7ae4984b7db7de8f8457170b3f1a419ee76d52` |
| `google/gemma-4-31B-it` | `842da3794eaa0b77d5f08bae87a17459d91ff475` |

Download a revision to a local snapshot and pass that directory to `--model`;
the current training script does not expose a separate `--revision` option.

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

The prepared files in `data/` are what the published models trained on.
Rebuilding from `input/` + `groundtruth/` is byte-exact: `build_sft_messages.py`
writes rows in the export's `row_position` order with the export's
serialization, so the result matches the SHA-256 recorded in
`data/source_manifest_v1.json`, and `prepare_dataset.py` on it reproduces the
shipped `sft_v1_80k/` files (the seeded shuffle depends on that order). To
rebuild them, or to build a variant:

```bash
cd training
# recipe files -> semantically identical chat-messages JSONL
# (JSON whitespace/key order differs from the historical source export)
python src/data/build_sft_messages.py                 # -> data/sft_messages_v1.jsonl
# length filter with the exact Qwen tokenizer (rows over the budget are DROPPED, never truncated)
python src/sft/prepare_dataset.py                     # 80k budget -> data/sft_v1_80k/
python src/sft/prepare_dataset.py --max-context 65536 --out data/sft_v1_64k
# RL prompt sets (shortest prompts, targets scorable under the 4096 decode cap)
python src/rl/verl/make_rl_dataset.py --n 1000        # -> data/rl_verl_v1/
python src/rl/trl_gemma/make_trl_dataset.py --n 500   # -> data/rl_trl_v1/
```

Use the committed `data/sft_v1_80k/{train,eval}.jsonl` for a reproduction of
the reported runs. The current builders preserve the historical row order and
serialization: `build_sft_messages.py` reproduces the SHA-256 in
`data/source_manifest_v1.json`, and `prepare_dataset.py` reproduces the shipped
train/eval split. Run `python ../scripts/release_check.py` from this directory
to verify both claims.

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
# --model-revision defaults to the pin in src/sft/base_models.json (1d4bf0f2... for this base)
sbatch src/sft/sbatch_sft.sh --model Qwen/Qwen3.8-27B \
       --epochs 5 --max-len 81920 --save-every-steps 158 \
       --lora-r 16 --lora-alpha 32 --lr 1e-4 --seed 0 \
       --run-name sft-27b-80k-5ep --output output/checkpoints/sft-27b-80k-5ep-lora

# gemma-4 (sliding-window attention: sdpa is the only working implementation)
sbatch src/sft/sbatch_sft.sh --model google/gemma-4-26B-A4B-it --attn-impl sdpa --epochs 2 \
       --max-len 81920 --run-name sft-gemma26b-v1 --output output/checkpoints/sft-gemma26b-v1-lora
```

Per-model settings behind every published row are in the `sft_*` columns of
`results/training.csv`. The trainer seeds torch, CUDA and the sampler
(`--seed`, default 0), pins the base revision (`--model-revision`, defaulting to
`$HF_MODEL_REVISION` and then to `src/sft/base_models.json`), optionally
requests deterministic kernels (`--deterministic`) and writes
`train_config.json` with every argument and library version next to the
checkpoints. Multi-GPU bf16 LoRA is still not bit-exact across GPU counts or
drivers; expect scores within the reported confidence intervals. Notable pitfalls recorded in `results/EXPERIMENTS.md`:
gemma-4's head dimension exceeds FlashAttention-2's limit; flex-attention
recompiles per sequence length; the 31B model only fits a 64k budget.

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
sbatch src/sft/run_benchmark_eval.sbatch output/checkpoints/merged-27b-80k-3ep sft-27b-80k-3ep-react react
```

Results land in `../benchmark/outputs/full_eval/<run_name>/`; `leaderboard.json`
there is the aggregate reported in `results/training.csv`.

## 3. Reinforcement learning (GRPO)

Both routes optimise the same **Tier-1 symbolic-match reward**
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
sbatch src/rl/verl/convert_rl_ckpt.sbatch grpo-27b-3ep 60 output/checkpoints/merged-27b-80k-3ep merged-27b-3ep-rl-step60
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

Then score with `run_benchmark_eval.sbatch` as above. The `rl_*` columns of
`results/training.csv` hold every published RL configuration. Finding: the
Tier-1 reward lifts weak SFT bases (4B +1.7, gemma-26B +4.0, gemma-12B +3.7)
and is flat or slightly negative on the strong 27B 3-epoch SFT.

## 4. External transfer benchmarks

`src/external_eval/` is a standalone harness (it imports nothing from the
benchmark) that runs a checkpoint on WorkflowBench, Seal-Tools and tau2-bench
with the upstream scorers. Fetch the third-party data as described in
[`src/external_eval/README.md`](src/external_eval/README.md); the published
numbers are in [`results/external/`](results/external/).

## Reproducing the reported scores

Every AgentOrch number in `results/` was produced by the frozen harness and
was previously verified byte-identically from the archived per-variant records
(165/165 lanes with `PYTHONPATH=benchmark python -m reproduction.offline.reproduce_scores --all`, fixed
bootstrap seed). The aggregates ship in `results/leaderboards/`, but a fresh
clone cannot repeat that audit until the separately distributed per-variant
archive has a public URL and checksum (see the benchmark README). The 80 GB
archive is kept by the maintainers and not published. Model weights are
published on the Hugging Face Hub with `scripts/upload_checkpoints_hf.py`
(`--headline` uploads the five headline checkpoints; the repo id of each is
written to the `hf_repo` column of `results/training.csv`);
`results/training.csv` and `results/EXPERIMENTS.md` map every score to its
training job, evaluation run and checkpoint name.
