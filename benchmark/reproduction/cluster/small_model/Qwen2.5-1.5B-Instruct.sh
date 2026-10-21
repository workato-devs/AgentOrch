#!/bin/bash
# Qwen/Qwen2.5-1.5B-Instruct — small model tier (canonical lane).
# Submits this model's dedicated lane of the shared launcher; the lane's
# full protocol (pinned revision, decoding caps, ports, memory) lives in
# run_instruct_scale_comparison.sbatch and is identical for every model in its group.
# Usage: ./Qwen2.5-1.5B-Instruct.sh [run_name [recipe_limit [modes]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=2 --export=NIL \
  benchmark/reproduction/cluster/run_instruct_scale_comparison.sbatch "$@"
