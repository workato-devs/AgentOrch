#!/bin/bash
# Qwen/Qwen3.8-27B-FP8 with enable_thinking + reasoning_effort=high —
# large model tier, test-time-reasoning ablation lane (reported separately
# from the main comparison). Protocol lives in run_thinking_local.sbatch
# (lane 0, 1xH200; 16,384-token caps, <think> spans stripped from scoring).
# Usage: ./Qwen3.8-27B-FP8-thinking.sh [run_name [recipe_limit [modes]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=0 --export=NIL \
  benchmark/reproduction/cluster/run_thinking_local.sbatch "$@"
