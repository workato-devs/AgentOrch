#!/bin/bash
#SBATCH --job-name=agentorch-grpo
#SBATCH --gres=gpu:h200:8
#SBATCH --cpus-per-task=32
#SBATCH --mem=800G
#SBATCH --time=3-00:00:00
#SBATCH --output=output/logs/grpo-%j.out

# GRPO (verl 0.9) on AgentOrch plan generation with the Tier-1 symbolic-match
# reward (src/rl/reward.py). Starts from a merged SFT checkpoint.
# Usage (from training/):
#   sbatch [--gres=gpu:h200:N] src/rl/verl/run_grpo.sbatch <model_path> [run_name] [hydra overrides...]
# Qwen GRPO settings (Appendix A.7, Table 9):
#   27B LoRA:  actor_rollout_ref.model.lora_rank=16 actor_rollout_ref.model.lora_alpha=32 \
#              actor_rollout_ref.actor.optim.lr=3e-6 actor_rollout_ref.actor.use_kl_loss=True \
#              actor_rollout_ref.actor.kl_loss_coef=0.001
#   4B full:   actor_rollout_ref.actor.optim.lr=1e-5 actor_rollout_ref.actor.use_kl_loss=True \
#              actor_rollout_ref.actor.kl_loss_coef=0.001
LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LAUNCHER_DIR/../../../scripts/_preamble.sh"
cd "$TRAIN_ROOT"
model=${1:?model path required}
run_name=${2:-grpo-$(date +%m%d-%H%M)}
shift $(( $# >= 2 ? 2 : 1 ))

# Slurm exports ROCR_VISIBLE_DEVICES even on NVIDIA nodes; verl refuses both.
unset ROCR_VISIBLE_DEVICES HIP_VISIBLE_DEVICES
# Per-job Ray session dir: stale daemons from cancelled jobs otherwise hang ray.init.
export RAY_TMPDIR="/tmp/ray-${SLURM_JOB_ID:-$$}"
mkdir -p "$RAY_TMPDIR"
# expandable_segments breaks verl FSDP offload (flat_param ptr assert); do not set for RL.
NGPU=${SLURM_GPUS_ON_NODE:-8}
CKPT_DIR="$TRAIN_ROOT/output/rl_checkpoints/verl"

exec "$AGENTORCH_RL_PYTHON" -m verl.trainer.main_ppo \
  ray_kwargs.ray_init.num_cpus="${SLURM_CPUS_PER_TASK:-32}" \
  algorithm.adv_estimator=grpo \
  algorithm.use_kl_in_reward=False \
  data.train_files="$TRAIN_ROOT/data/rl_verl_v1/train.parquet" \
  data.val_files="$TRAIN_ROOT/data/rl_verl_v1/eval.parquet" \
  data.prompt_key=prompt \
  data.max_prompt_length=65536 \
  data.max_response_length=6144 \
  data.train_batch_size=16 \
  data.filter_overlong_prompts=True \
  data.truncation=error \
  actor_rollout_ref.model.path="$model" \
  actor_rollout_ref.model.use_remove_padding=True \
  actor_rollout_ref.model.enable_gradient_checkpointing=True \
  actor_rollout_ref.actor.optim.lr=3e-6 \
  actor_rollout_ref.actor.ppo_mini_batch_size=16 \
  actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.actor.use_kl_loss=True \
  actor_rollout_ref.actor.kl_loss_coef=0.001 \
  actor_rollout_ref.actor.fsdp_config.param_offload=True \
  actor_rollout_ref.actor.fsdp_config.optimizer_offload=True \
  actor_rollout_ref.rollout.name=vllm \
  actor_rollout_ref.rollout.n=8 \
  actor_rollout_ref.rollout.gpu_memory_utilization=0.55 \
  actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
  actor_rollout_ref.rollout.max_num_batched_tokens=98304 \
  actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=1 \
  actor_rollout_ref.actor.ulysses_sequence_parallel_size=1 \
  reward.custom_reward_function.path="$TRAIN_ROOT/src/rl/reward.py" \
  reward.custom_reward_function.name=compute_score \
  trainer.project_name=agentorch-grpo \
  trainer.experiment_name="$run_name" \
  trainer.default_local_dir="$CKPT_DIR/$run_name" \
  trainer.logger='["console","wandb"]' \
  trainer.n_gpus_per_node="$NGPU" \
  trainer.nnodes=1 \
  trainer.save_freq=20 \
  trainer.test_freq=10 \
  trainer.total_epochs=2 \
  "$@"
