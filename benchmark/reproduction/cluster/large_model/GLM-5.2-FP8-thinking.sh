#!/bin/bash
# zai-org/GLM-5.2-FP8 with template-default reasoning enabled (untagged
# inline thinking; final-JSON scoring) — large model tier, test-time-
# reasoning ablation lane. Protocol in run_thinking_local.sbatch (lane 2,
# 8xH200 TP=8; plan 32K / react 16K caps).
# Usage: ./GLM-5.2-FP8-thinking.sh [run_name [recipe_limit [modes]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=2 --gres=gpu:h200:8 --mem=800G --cpus-per-task=32 --export=NIL \
  benchmark/reproduction/cluster/run_thinking_local.sbatch "$@"
