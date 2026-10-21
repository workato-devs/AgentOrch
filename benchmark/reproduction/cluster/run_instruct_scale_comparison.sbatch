#!/bin/bash
#SBATCH --job-name=agentorch-8model
#SBATCH --partition=long
#SBATCH --array=0-7
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=100G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-%A_%a.out

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
  Qwen/Qwen2.5-0.5B-Instruct
  meta-llama/Llama-3.2-1B-Instruct
  Qwen/Qwen2.5-1.5B-Instruct
  meta-llama/Llama-3.2-3B-Instruct
  Qwen/Qwen2.5-7B-Instruct
  meta-llama/Llama-3.1-8B-Instruct
  Qwen/Qwen2.5-14B-Instruct
  Qwen/Qwen2.5-32B-Instruct
)
revisions=(
  7ae557604adf67be50417f59c2c2f167def9a775
  9213176726f574b556790deb65791e0c5aa438b6
  989aa7980e4cf806f80c7fef2b1adb7bc71aa306
  0cb88a4f764b7a12671c53f0838cd831a0843b95
  a09a35458c702b33eeacc393d103063234e8bc28
  0e9e39f249a16976918f6564b8830bc894c89659
  cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8
  5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd
)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
# Positional arguments let submissions use ``--export=NIL``.  That avoids
# Slurm's cluster-side login-environment retrieval while keeping reproducible
# preflight/full-run names and limits.
run_name=${1:-${AGENTORCH_RUN_NAME:-instruct-scale-8models-20260813}}
recipe_limit=${2:-${AGENTORCH_RECIPE_LIMIT:-}}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

export HF_MAX_NEW_TOKENS=4096
export HF_REACT_MAX_NEW_TOKENS=8192
export HF_REACT_SOFT_MAX_NEW_TOKENS=1024
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
# Keep enough independent trajectories in flight to fill each model's KV
# cache.  The three smallest models can hold at least 30 full-context
# requests on one H200; larger models use the conservative default.
if (( index <= 2 )); then
  export VLLM_REACT_CONCURRENCY=32
else
  export VLLM_REACT_CONCURRENCY=16
fi
export HF_MODEL_CONTEXT_TOKENS=131072
export HF_MAX_INPUT_TOKENS=122880
export HF_MODEL_REVISION="$revision"
if [[ "$index" == 1 || "$index" == 2 ]]; then
  export HF_HOME=/shared/huggingface
else
  : "${HF_HOME:?set HF_HOME in benchmark/reproduction/cluster/env.sh}"
fi
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
  --state-namespace "model-${index}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes plan_execute,react \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  "${limit_args[@]}"
