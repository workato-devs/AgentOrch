#!/bin/bash
# GLOBAL+INPUT information-control ablation (doc/global_input.md).
#
# Submits the `global_input` mode for the priority roster through each
# model's existing per-model launcher, so every lane inherits exactly the
# pinned revision, decoding caps, GPU shape, and (for the thinking pairs)
# the thinking configuration of its headline Global/ReAct comparison.
# The only protocol difference to those lanes is the mode string.
#
# Usage (repository root):
#   benchmark/reproduction/cluster/submit_global_input.sh [run_name [recipe_limit]] [--dry-run]
#
# Nothing is submitted with --dry-run; the sbatch commands are printed.
# Teammates' reserved nodes are excluded after submission via scontrol
# (AGENTORCH_SLURM_EXCLUDE from reproduction/cluster/env.sh, optional).
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

run_name=${1:-global-input-$(date +%Y%m%d)}
recipe_limit=${2:-}
dry_run=0
for arg in "$@"; do [[ "$arg" == "--dry-run" ]] && dry_run=1; done
[[ "$run_name" == "--dry-run" ]] && run_name="global-input-$(date +%Y%m%d)"
[[ "$recipe_limit" == "--dry-run" ]] && recipe_limit=""

# Priority roster from the spec, matched to the headline configurations.
# Thinking pairs are separate lanes (their headline rows are thinking rows).
launchers=(
  benchmark/reproduction/cluster/small_model/Qwen3-4B-Instruct-2507.sh
  benchmark/reproduction/cluster/large_model/gemma-4-12B-it.sh
  benchmark/reproduction/cluster/large_model/gemma-4-26B-A4B-it.sh
  benchmark/reproduction/cluster/large_model/Qwen3.8-27B-FP8.sh
  benchmark/reproduction/cluster/large_model/Qwen3.8-27B-FP8-thinking.sh
  benchmark/reproduction/cluster/large_model/DeepSeek-V4-Flash-0731.sh
  benchmark/reproduction/cluster/large_model/claude-opus-5.sh
  benchmark/reproduction/cluster/large_model/claude-opus-5-thinking.sh
)

# The thinking configurations reuse their base model id (`--model
# claude-opus-5`, `hf:Qwen/Qwen3.8-27B-FP8`), so the evaluator would write
# them into the SAME <run>/<model>/global_input directory as the
# non-thinking lane and mix rows and plan caches. Give them their own run
# names, exactly as the canonical thinking ablations did
# (opus-thinking-20260815, local-thinking-20260817).
declare -A run_suffix=(
  [benchmark/reproduction/cluster/large_model/Qwen3.8-27B-FP8-thinking.sh]="-27b-thinking"
  [benchmark/reproduction/cluster/large_model/claude-opus-5-thinking.sh]="-opus-thinking"
)

for launcher in "${launchers[@]}"; do
  if [[ ! -x "$launcher" ]]; then
    echo "skip (not executable or missing): $launcher" >&2
    continue
  fi
  lane_run="${run_name}${run_suffix[$launcher]:-}"
  cmd=("$launcher" "$lane_run" "$recipe_limit" global_input)
  if (( dry_run )); then
    echo "DRY RUN: ${cmd[*]}"
  else
    echo "submit: ${cmd[*]}"
    out=$("${cmd[@]}")
    echo "$out"
    # Nodes reserved by teammates are excluded on the submission, never in
    # the scripts (README). The per-model launchers accept no extra sbatch
    # flags and SBATCH_EXCLUDE is not reliably honored, so apply it here.
    jobid=$(sed -n 's/^Submitted batch job \([0-9]*\).*/\1/p' <<<"$out")
    if [[ -n "$jobid" && -n "${AGENTORCH_SLURM_EXCLUDE:-}" ]]; then
      scontrol update jobid="$jobid" ExcNodeList="${AGENTORCH_SLURM_EXCLUDE:-}" \
        || echo "note: job $jobid already started; exclusion not applied" >&2
    fi
  fi
done

cat <<EOF

Outputs land in benchmark/outputs/full_eval/${run_name}/<model>/global_input/
(thinking lanes: ${run_name}-27b-thinking/ and ${run_name}-opus-thinking/).
When every lane has 3,220 rows:
  use each lane's leaderboard.json directly. Cross-model paper-table builders
  are intentionally not part of the community benchmark runtime.
EOF
