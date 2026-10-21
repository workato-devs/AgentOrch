#!/bin/bash
#SBATCH --job-name=agentorch-merge
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=400G
#SBATCH --time=4:00:00
#SBATCH --output=output/logs/merge-%j.out
# verl FSDP checkpoint -> HF model (+ PEFT adapter when lora_train_meta.json is
# present). Needs a large-memory node: the fp32 shards exceed a login node's RAM.
# Usage (from training/): sbatch src/rl/verl/merge_verl_ckpt.sbatch <actor_ckpt_dir> <target_dir>
LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LAUNCHER_DIR/../../../scripts/_preamble.sh"
exec "$AGENTORCH_RL_PYTHON" -m verl.model_merger merge --backend fsdp --local_dir "${1:?actor ckpt dir}" --target_dir "${2:?target dir}"
