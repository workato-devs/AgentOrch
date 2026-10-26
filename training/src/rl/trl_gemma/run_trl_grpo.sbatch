#!/bin/bash
#SBATCH --job-name=agentorch-trl-gemma
#SBATCH --gres=gpu:h200:8
#SBATCH --cpus-per-task=24
#SBATCH --mem=400G
#SBATCH --time=2-00:00:00
#SBATCH --output=output/logs/trl-%j.out

# TRL GRPOTrainer for gemma-4 (verl 0.9 does not support gemma-4; see
# results/training.csv). Colocated vLLM, LoRA r16/a32, Tier-1 reward.
# Usage (from training/):
#   sbatch src/rl/trl_gemma/run_trl_grpo.sbatch [--accel-config <yaml>] [train_grpo_gemma.py args...]
# accelerate_fsdp2.yaml wraps Gemma4TextDecoderLayer (26B/31B);
# accelerate_fsdp2_12b.yaml wraps Gemma4UnifiedTextDecoderLayer (12B).
LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LAUNCHER_DIR/../../../scripts/_preamble.sh"
cd "$TRAIN_ROOT"
export WANDB_PROJECT=agentorch-grpo
NGPU=${SLURM_GPUS_ON_NODE:-1}
ACCEL_CFG=${ACCEL_CFG:-$LAUNCHER_DIR/accelerate_fsdp2.yaml}
if [ "${1:-}" = "--accel-config" ]; then ACCEL_CFG="$2"; shift 2; fi

if [[ ! -f "$ACCEL_CFG" && -f "$LAUNCHER_DIR/$ACCEL_CFG" ]]; then
  ACCEL_CFG="$LAUNCHER_DIR/$ACCEL_CFG"
fi
if [ "$NGPU" -gt 1 ]; then
  exec "$AGENTORCH_RL_PYTHON" -m accelerate.commands.launch \
    --config_file "$ACCEL_CFG" --num_processes "$NGPU" \
    "$LAUNCHER_DIR/train_grpo_gemma.py" "$@"
else
  exec "$AGENTORCH_RL_PYTHON" "$LAUNCHER_DIR/train_grpo_gemma.py" "$@"
fi
