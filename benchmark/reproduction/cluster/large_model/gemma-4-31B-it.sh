#!/bin/bash
# google/gemma-4-31B-it — large model tier (frontier lane 5, 2xH200 TP=2).
# Protocol lives in run_scale_frontier.sbatch.
# Usage: ./gemma-4-31B-it.sh [run_name [recipe_limit [modes [ids_file]]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=5 --gres=gpu:h200:2 --mem=200G --cpus-per-task=16 --export=NIL \
  benchmark/reproduction/cluster/run_scale_frontier.sbatch "$@"
