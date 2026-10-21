#!/bin/bash
# Submit the 15 temperature-sweep lanes (run_temp_sweep.sbatch) with the
# per-model GPU shape. Set AGENTORCH_SLURM_EXCLUDE to skip a node on every
# submission. Usage: ./submit_temp_sweep.sh [args...]
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"  # repository root
mkdir -p benchmark/outputs/slurm_logs
SBATCH=benchmark/reproduction/cluster/run_temp_sweep.sbatch
EXCLUDE=${AGENTORCH_SLURM_EXCLUDE:-}  # optional node exclusion, e.g. a reserved node

# per-model resource shape (model_index 0-4)
gpus=(1 2 2 4 1)
mems=(100G 200G 200G 400G 100G)
cpus=(8 16 16 24 8)

for temp_index in 0 1 2; do
  for model_index in 0 1 2 3 4; do
    lane=$(( temp_index * 5 + model_index ))
    sbatch --array="$lane" \
      --gres=gpu:h200:${gpus[$model_index]} \
      --mem=${mems[$model_index]} \
      --cpus-per-task=${cpus[$model_index]} \
      ${EXCLUDE:+--exclude="$EXCLUDE"} \
      --export=NIL \
      "$SBATCH" "$@"
  done
done
