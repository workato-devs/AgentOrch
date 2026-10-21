#!/bin/bash
#SBATCH --job-name=agentorch-replan-scale
#SBATCH --partition=long
#SBATCH --array=0-6
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=24
#SBATCH --mem=100G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-replan-scale-%A_%a.out

# Replan scale ladder: does mid-course-repair capability grow with model
# scale above the 27B emergence point? Seven open-weight checkpoints from
# 24B dense to 110B MoE, replan mode, --max-replans 6 (cap shown to be
# non-binding by the cap-2 vs cap-6 dose comparison). Frozen plans are
# pre-seeded from each model's canonical tier global-plans; decoding caps
# match the plan-generation lanes (4096/8192) so every cache key hits.
# Lanes 4-6 are TP2 — submit with --gres=gpu:h200:2 for --array=4-6.
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
  mistralai/Mistral-Small-3.1-24B-Instruct-2503
  google/gemma-3-27b-it
  Qwen/Qwen3-30B-A3B-Instruct-2507
  CohereForAI/c4ai-command-r-08-2024
  meta-llama/Llama-3.3-70B-Instruct
  Qwen/Qwen2.5-72B-Instruct
  zai-org/GLM-4.5-Air-FP8
)
revisions=(
  68faf511d618ef198fef186659617cfd2eb8e33a
  005ad3404e59d6023443cb575daa05336842228a
  0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe
  dc835b893cd3fb8f14b24970dbc2a0a6d3c22ee3
  6f6073b423013f6a7d4d9f39144961bfbfbc386b
  495f39366efef23836d0cfae4fbe635880d2be31
  f9a9c5acf5e543cd24d659a056c5dbcda78ffcfc
)
tensor_parallel=(1 1 1 1 2 2 2)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-replan-scale-20260824}
recipe_limit=${2:-}
modes=${3:-replan}
ids_file=${4:-}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

# FP8 JIT toolchain (Air lane; harmless elsewhere).
[[ -n "${AGENTORCH_CUDA_HOME:-}" ]] && export CUDA_HOME="$AGENTORCH_CUDA_HOME"
export PATH="${CUDA_HOME:+$CUDA_HOME/bin:}$PATH"
export VLLM_USE_DEEP_GEMM=0
export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}${CUDA_HOME:+$CUDA_HOME/lib}${LIBRARY_PATH:+:$LIBRARY_PATH}"

export HF_MAX_NEW_TOKENS=4096
export HF_REACT_MAX_NEW_TOKENS=8192
export HF_REACT_SOFT_MAX_NEW_TOKENS=1024
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
export VLLM_TENSOR_PARALLEL=${tensor_parallel[$index]}
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
  --state-namespace "replan-scale-${index}${ids_file:+-$(basename "$ids_file" .txt)}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  --max-replans 6 \
  ${ids_file:+--ids $(tr "\n" " " < "$ids_file")} \
  "${limit_args[@]}"
