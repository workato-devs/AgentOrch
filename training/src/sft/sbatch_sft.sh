#!/bin/bash
#SBATCH --job-name=agentorch-sft
#SBATCH --gres=gpu:h200:8
#SBATCH --cpus-per-task=32
#SBATCH --mem=600G
#SBATCH --time=3-00:00:00
#SBATCH --output=output/logs/sft-%j.out

# LoRA SFT on the benchmark-aligned training split (torchrun, 8 GPUs, DDP).
# Submit from training/ so the relative --output path resolves:
#   cd training
#   sbatch src/sft/sbatch_sft.sh --max-rows 24                 # smoke test
#   sbatch src/sft/sbatch_sft.sh --epochs 3 --max-len 81920 \
#          --run-name sft-27b-80k-3ep --output output/checkpoints/sft-27b-80k-3ep-lora
# Any argument is forwarded to train_sft_local.py (see its --help).
LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LAUNCHER_DIR/../../scripts/_preamble.sh"
cd "$TRAIN_ROOT/src/sft"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export OMP_NUM_THREADS=4

exec "$AGENTORCH_TRAIN_PYTHON" -m torch.distributed.run \
  --nproc-per-node "${SLURM_GPUS_ON_NODE:-8}" \
  train_sft_local.py "$@"
