#!/bin/bash
# zai-org/GLM-4.5-Air-FP8 (106B-A12B MoE, vendor FP8) — large model tier
# (frontier lane 0, 2×H200 TP=2). Protocol lives in run_scale_frontier.sbatch.
# Usage: ./GLM-4.5-Air-FP8.sh [run_name [recipe_limit [modes [ids_file]]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=0 --gres=gpu:h200:2 --cpus-per-task=16 --mem=200G --export=NIL \
  benchmark/reproduction/cluster/run_scale_frontier.sbatch "$@"
