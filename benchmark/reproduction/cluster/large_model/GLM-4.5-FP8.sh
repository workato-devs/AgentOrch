#!/bin/bash
# zai-org/GLM-4.5-FP8 (355B-A32B MoE, vendor FP8) — large model tier
# (frontier lane 1, 4×H200 TP=4). Protocol lives in run_scale_frontier.sbatch.
# Usage: ./GLM-4.5-FP8.sh [run_name [recipe_limit [modes [ids_file]]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=1 --gres=gpu:h200:4 --cpus-per-task=24 --mem=400G --export=NIL \
  benchmark/reproduction/cluster/run_scale_frontier.sbatch "$@"
