#!/bin/bash
# gpt-35-turbo (Azure) — medium model tier (canonical lane).
# Submits this model's dedicated lane of the shared launcher; the lane's
# full protocol (pinned revision, decoding caps, ports, memory) lives in
# run_api_model_comparison.sbatch and is identical for every model in its group.
# Usage: ./gpt-35-turbo.sh [run_name [recipe_limit [modes]]]
# Submit from the repository root so the .sbatch file resolves its paths.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
mkdir -p benchmark/outputs/slurm_logs
exec sbatch --array=1 --export=NIL \
  benchmark/reproduction/cluster/run_api_model_comparison.sbatch "$@"
