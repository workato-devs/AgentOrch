#!/bin/bash
#SBATCH --job-name=agentorch-ckpt-eval
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=24
#SBATCH --mem=400G
#SBATCH --time=3-00:00:00
#SBATCH --output=output/logs/eval-%j.out

# Full-benchmark evaluation of a merged checkpoint with the frozen harness
# (benchmark/evaluation/full_eval.py): simulated backend, greedy decoding,
# 131k context, 4096-token plan cap, enable_thinking=false. This is exactly
# the protocol behind every row of results/training.csv.
#
# Usage (from training/):
#   sbatch src/sft/run_benchmark_eval.sbatch <merged_model_dir> <run_name> [modes]
#   modes: plan_execute (default) | react | replan | incremental_workflow | comma list
# Output: <release>/benchmark/outputs/full_eval/<run_name>/hf:<...>/<mode>/
LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LAUNCHER_DIR/../../scripts/_preamble.sh"
model_dir=${1:?merged model dir required}
run_name=${2:?run name required}
modes=${3:-plan_execute}

cd "$AGENTORCH_ROOT"
export PATH="$AGENTORCH_ROOT/benchmark/reproduction/cluster/toolchain:$AGENTORCH_CONDA_BIN:/usr/local/bin:/usr/bin:/bin"
if [[ -f "$AGENTORCH_ENV_FILE" ]]; then set -a; source "$AGENTORCH_ENV_FILE"; set +a; fi
if [[ -n "${AGENTORCH_CUDA_HOME:-}" ]]; then
  export CUDA_HOME="$AGENTORCH_CUDA_HOME"; export PATH="$CUDA_HOME/bin:$PATH"
  export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}$CUDA_HOME/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
fi

export HF_MAX_NEW_TOKENS=4096
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_TENSOR_PARALLEL="${VLLM_TENSOR_PARALLEL:-1}"
export VLLM_KV_CACHE_DTYPE=auto
export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'
export HF_MODEL_CONTEXT_TOKENS=131072
export HF_MAX_INPUT_TOKENS=122880
export TRANSFORMERS_OFFLINE=1
export PYTHONPATH=benchmark

exec "$AGENTORCH_PYTHON" -m evaluation.full_eval \
  --run-name "$run_name" \
  --state-namespace "ckpt-eval-$run_name" \
  --backend simulated \
  --model "hf:${model_dir}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume
