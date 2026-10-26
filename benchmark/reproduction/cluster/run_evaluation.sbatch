#!/bin/bash
#SBATCH --job-name=agentorch-eval
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/eval-%j.out
set -euo pipefail
cd "${AGENTORCH_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
export AGENTORCH_ROOT="$PWD"
source benchmark/reproduction/cluster/env.sh
export PYTHONPATH=benchmark
model=${1:?provide a model ID}
run_name=${2:?provide a run name}
modes=${3:-plan_execute,react}
shift $(( $# >= 3 ? 3 : 2 ))
exec "$AGENTORCH_PYTHON" -m evaluation.full_eval \
  --backend simulated --model "$model" --run-name "$run_name" \
  --modes "$modes" --variants all --resume "$@"
