#!/bin/bash
# google/gemma-4-12B-it — large model tier (frontier lane 6, 1xH200 TP=1).
# Protocol lives in run_scale_frontier.sbatch.
# Usage: ./gemma-4-12B-it.sh [run_name [recipe_limit [modes [ids_file]]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=6 --gres=gpu:h200:1 --mem=100G --cpus-per-task=8 --export=NIL \
  benchmark/reproduction/cluster/run_scale_frontier.sbatch "$@"
