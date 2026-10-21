#!/bin/bash
#SBATCH --job-name=agentorch-scale-ext-70b
#SBATCH --partition=long
#SBATCH --array=0-2
#SBATCH --gres=gpu:h200:2
#SBATCH --cpus-per-task=16
#SBATCH --mem=200G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-ext70b-%A_%a.out

# 70B-class scale-extension members (evaluation/global_react_models.json):
# each model shards across two H200s with vLLM tensor parallelism. Protocol
# is otherwise identical to run_scale_extension.sbatch.
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
  meta-llama/Llama-3.1-70B-Instruct
  meta-llama/Llama-3.3-70B-Instruct
  Qwen/Qwen2.5-72B-Instruct
)
revisions=(
  1605565b47bb9346c5515c34102e054115b4f98b
  6f6073b423013f6a7d4d9f39144961bfbfbc386b
  495f39366efef23836d0cfae4fbe635880d2be31
)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-${AGENTORCH_RUN_NAME:-scale-ext-70b-20260815}}
recipe_limit=${2:-${AGENTORCH_RECIPE_LIMIT:-}}
modes=${3:-plan_execute,react}
# Optional shard support: a file of recipe ids restricts this worker to
# that subset (one id per line); the state namespace gains the file stem
# so concurrent shards of one model never share simulator state.
ids_file=${4:-}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

export HF_MAX_NEW_TOKENS=4096
export HF_REACT_MAX_NEW_TOKENS=8192
export HF_REACT_SOFT_MAX_NEW_TOKENS=1024
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
export VLLM_TENSOR_PARALLEL=2
export HF_MODEL_CONTEXT_TOKENS=131072
export HF_MAX_INPUT_TOKENS=122880
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
  --state-namespace "ext70b-model-${index}-${modes//,/-}${ids_file:+-$(basename "$ids_file" .txt)}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  ${ids_file:+--ids $(tr "\n" " " < "$ids_file")} \
  "${limit_args[@]}"
