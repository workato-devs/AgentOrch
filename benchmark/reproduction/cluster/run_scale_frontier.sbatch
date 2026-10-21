#!/bin/bash
#SBATCH --job-name=agentorch-scale-frontier
#SBATCH --partition=long
#SBATCH --array=0-7
#SBATCH --gres=gpu:h200:4
#SBATCH --cpus-per-task=24
#SBATCH --mem=400G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-frontier-%A_%a.out

# Frontier open-weight MoE members (evaluation/global_react_models.json):
# vendor-released FP8 checkpoints sharded across H200s with vLLM tensor
# parallelism (per-lane below; override GPUs at submit with sbatch --gres).
# Protocol is otherwise identical to run_scale_extension.sbatch: greedy
# decoding, 131,072-token context, offline pinned weights, the executed
# per-mode decoding caps.
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
  zai-org/GLM-4.5-Air-FP8
  zai-org/GLM-4.5-FP8
  zai-org/GLM-5.2-FP8
  deepseek-ai/DeepSeek-V4-Flash-0731
  Qwen/Qwen3.8-27B-FP8
  google/gemma-4-31B-it
  google/gemma-4-12B-it
  google/gemma-4-26B-A4B-it
)
revisions=(
  f9a9c5acf5e543cd24d659a056c5dbcda78ffcfc
  8cc290ee4c7cbfa38d3a2db9bd0b7371773ece81
  ba978f7d347eaf65d22f1a86833408afdb953541
  7872f01b1d1fe23eabc4c98b48bffcef5a386062
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
  842da3794eaa0b77d5f08bae87a17459d91ff475
  707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7
  4d7ae4984b7db7de8f8457170b3f1a419ee76d52
)
tensor_parallel=(
  2
  4
  8
  2
  1
  2
  1
  2
)
kv_cache_dtypes=(
  auto
  auto
  auto
  fp8
  auto
  auto
  auto
  auto
)
# deep_gemm per lane: DeepSeek-V4's block-FP8 layout dispatches only
# through deep_gemm (cutlass scaled_mm rejects it); with the 13.0.88
# toolchain aligned its JIT now compiles. Everyone else keeps prebuilt
# kernels.
use_deep_gemm=(
  0
  0
  0
  1
  0
  0
  0
  0
)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-${AGENTORCH_RUN_NAME:-frontier-ext-20260816}}
recipe_limit=${2:-${AGENTORCH_RECIPE_LIMIT:-}}
modes=${3:-plan_execute,react}
# Optional shard support: a file of recipe ids restricts this worker to
# that subset (one id per line); the state namespace gains the file stem
# so concurrent shards of one model never share simulator state.
ids_file=${4:-}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

# FP8 kernels JIT-compile through flashinfer, which needs a CUDA toolkit;
# the compute image has none, so point it at the toolkit shipped inside the
# torch cu13 wheels (nvcc 13.2 + headers + nvvm).
[[ -n "${AGENTORCH_CUDA_HOME:-}" ]] && export CUDA_HOME="$AGENTORCH_CUDA_HOME"
export PATH="${CUDA_HOME:+$CUDA_HOME/bin:}$PATH"
# deep_gemm JIT-compiles kernels at engine init and its nvcc invocation
# fails on this image; the prebuilt cutlass/triton FP8 paths are complete.
export VLLM_USE_DEEP_GEMM=${use_deep_gemm[$index]}
# The compute image ships the CUDA driver as libcuda.so.1 with no linker
# symlink; JIT link steps need -lcuda, resolved via this stub directory.
export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}${CUDA_HOME:+$CUDA_HOME/lib}${LIBRARY_PATH:+:$LIBRARY_PATH}"

export HF_MAX_NEW_TOKENS=4096
export HF_REACT_MAX_NEW_TOKENS=8192
export HF_REACT_SOFT_MAX_NEW_TOKENS=1024
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
export VLLM_TENSOR_PARALLEL=${tensor_parallel[$index]}
export VLLM_KV_CACHE_DTYPE=${kv_cache_dtypes[$index]}
# Lane 3 (DeepSeek-V4): its deepseek_v4 tokenizer mode races under the
# engine's async scheduling and front-end string tokenization; feed
# pre-rendered token ids and disable async scheduling for this lane.
if (( index == 3 )); then export HF_PROMPT_IDS=1; export VLLM_ASYNC_SCHEDULING=0; fi
# GLM-5.2 thinks by default with untagged inline reasoning that consumes
# the whole plan budget; the main roster runs thinking-disabled, matching
# every other lane's no-hidden-reasoning protocol.
if (( index == 2 )); then export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'; fi
# Qwen3.8's template also thinks by default (xhigh); the main lane runs
# thinking-disabled like every other roster lane.
if (( index == 4 )); then export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'; fi
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
  --state-namespace "frontier-model-${index}-${modes//,/-}${ids_file:+-$(basename "$ids_file" .txt)}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  ${ids_file:+--ids $(tr "\n" " " < "$ids_file")} \
  "${limit_args[@]}"
