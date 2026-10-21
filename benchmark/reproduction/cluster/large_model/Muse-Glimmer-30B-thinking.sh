#!/bin/bash
# meta-models/Muse-Glimmer-30B at "Reasoning strength: high" (the model's
# documented system-prompt effort control) — large model tier, test-time-
# reasoning ablation lane. Protocol lives in run_thinking_local.sbatch
# (lane 1, 1xH200). NOTE: this architecture postdates the campaign's
# pinned vLLM, so the lane runs from the isolated `muse` conda env — a
# declared runtime difference, never mixed into pinned-stack comparisons.
# Usage: ./Muse-Glimmer-30B-thinking.sh [run_name [recipe_limit [modes]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=1 --export=NIL \
  benchmark/reproduction/cluster/run_thinking_local.sbatch "$@"
