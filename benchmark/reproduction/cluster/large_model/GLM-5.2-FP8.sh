#!/bin/bash
# zai-org/GLM-5.2-FP8 — large model tier (frontier lane 2, 8xH200 TP=8).
# Protocol lives in run_scale_frontier.sbatch.
# Usage: ./GLM-5.2-FP8.sh [run_name [recipe_limit [modes [ids_file]]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=2 --gres=gpu:h200:8 --mem=800G --cpus-per-task=32 --export=NIL \
  benchmark/reproduction/cluster/run_scale_frontier.sbatch "$@"
