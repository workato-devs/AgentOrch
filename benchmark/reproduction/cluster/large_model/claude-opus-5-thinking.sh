#!/bin/bash
# claude-opus-5 with adaptive thinking (ablation) — large model tier (ablation lane).
# Submits this model's dedicated lane of the shared launcher; the lane's
# full protocol (pinned revision, decoding caps, ports, memory) lives in
# run_opus_thinking_ablation.sbatch and is identical for every model in its group.
# Usage: ./claude-opus-5-thinking.sh [run_name [recipe_limit [modes]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --export=NIL \
  benchmark/reproduction/cluster/run_opus_thinking_ablation.sbatch "$@"
