#!/bin/bash
#SBATCH --job-name=agentorch-thinking-pairs
#SBATCH --partition=long
#SBATCH --array=0-1
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=24
#SBATCH --mem=100G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-thinking-pairs-%A_%a.out

# Thinking/non-thinking matched pairs across scale: Qwen3's dedicated
# Thinking-2507 checkpoints, paired against the already-evaluated
# Instruct-2507 releases of the same generation and size
# (Qwen3-4B-Instruct-2507, small; Qwen3-30B-A3B-Instruct-2507, large).
# Same protocol as the local-thinking-20260817 ablation wave: 32768-token
# plan / 16384-token react budgets, only text outside <think> spans is
# parsed and scored (these templates open <think> on the prompt side, so
# completions carry only the closing tag; _strip_thinking handles both).
set -euo pipefail
# Repository root = the Slurm submission directory (the per-model launchers in
# reproduction/cluster/{small,medium,large}_model cd there first). Site paths come from
# benchmark/reproduction/cluster/env.sh (gitignored; copy env.sh.example).
cd "${AGENTORCH_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
export AGENTORCH_ROOT="$PWD"
if [[ ! -f benchmark/reproduction/cluster/env.sh ]]; then
  echo "missing $PWD/benchmark/reproduction/cluster/env.sh: copy env.sh.example and set your site paths" >&2
  exit 1
fi
source benchmark/reproduction/cluster/env.sh
export PATH="$AGENTORCH_ROOT/benchmark/reproduction/cluster/toolchain:$AGENTORCH_CONDA_BIN:/usr/local/bin:/usr/bin:/bin"

models=(
  Qwen/Qwen3-4B-Thinking-2507
  Qwen/Qwen3-30B-A3B-Thinking-2507
)
revisions=(
  768f209d9ea81521153ed38c47d515654e938aea
  144afc2f379b542fdd4e85a1fcd5e1f79112d95d
)
index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-thinking-pairs-20260824}
recipe_limit=${2:-}
modes=${3:-plan_execute,react}
ids_file=${4:-}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

export HF_MAX_NEW_TOKENS=32768
export HF_REACT_MAX_NEW_TOKENS=16384
# These templates open <think> on the prompt side: nothing before the
# closing tag may trip the balanced-JSON stop, and scanning starts after
# it (same setting as every run_thinking_local lane).
export HF_THINKING_PREFIX=1
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
export VLLM_TENSOR_PARALLEL=1
export HF_MODEL_CONTEXT_TOKENS=131072
export HF_MAX_INPUT_TOKENS=98304
export HF_MODEL_REVISION="$revision"
: "${HF_HOME:?set HF_HOME in benchmark/reproduction/cluster/env.sh}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH=benchmark

limit_args=()
if [[ -n "$recipe_limit" ]]; then
  limit_args=(--limit "$recipe_limit")
fi

"$AGENTORCH_PYTHON" -m evaluation.full_eval \
  --run-name "$run_name" \
  --state-namespace "thinking-pair-${index}-${modes//,/-}${ids_file:+-$(basename "$ids_file" .txt)}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  ${ids_file:+--ids $(tr "\n" " " < "$ids_file")} \
  "${limit_args[@]}"
