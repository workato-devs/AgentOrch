#!/bin/bash
#SBATCH --job-name=agentorch-replan-expanded
#SBATCH --partition=long
#SBATCH --array=0-6
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=24
#SBATCH --mem=100G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-replan-exp-%A_%a.out

# Replan-budget expansion: the same replan protocol as
# replan-smallmed-20260823 but with --max-replans 6 (was the default 2).
# Roster: three mediums never replan-tested with the strongest
# ReAct-over-Global gaps (Qwen2.5-14B, gemma-4-12B, gemma-4-26B-A4B), two
# repeat lanes for a budget dose comparison against the cap-2 wave
# (Qwen3-4B, glm-4-9b), and the one model where mid-course repair emerged
# at cap 2 (Qwen3.8-27B), non-thinking (lane 5) and thinking (lane 6).
# Lane 6 runs under <run>-think so the two 27B fingerprints never share a
# plan cache directory. Decoding caps per lane match the lane that
# generated each model's frozen plans, so cache keys hit.
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
  Qwen/Qwen3-4B-Instruct-2507
  zai-org/glm-4-9b-chat
  Qwen/Qwen2.5-14B-Instruct
  google/gemma-4-12B-it
  google/gemma-4-26B-A4B-it
  Qwen/Qwen3.8-27B-FP8
  Qwen/Qwen3.8-27B-FP8
)
revisions=(
  cdbee75f17c01a7cc42f958dc650907174af0554
  bd8234fe5e0c09c48637a92abb0c797cb5fa0e73
  cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8
  707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7
  4d7ae4984b7db7de8f8457170b3f1a419ee76d52
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
)
tensor_parallel=(1 1 1 1 2 1 1)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-replan-expanded-20260824}
if (( index == 6 )); then run_name="${run_name}-think"; fi
recipe_limit=${2:-}
modes=${3:-replan}
ids_file=${4:-}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

# FP8 JIT toolchain (27B FP8 lanes; harmless elsewhere).
[[ -n "${AGENTORCH_CUDA_HOME:-}" ]] && export CUDA_HOME="$AGENTORCH_CUDA_HOME"
export PATH="${CUDA_HOME:+$CUDA_HOME/bin:}$PATH"
export VLLM_USE_DEEP_GEMM=0
export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}${CUDA_HOME:+$CUDA_HOME/lib}${LIBRARY_PATH:+:$LIBRARY_PATH}"

# Caps match each model's plan-generation lane (cache-key fingerprint):
# scale-ext/frontier lanes 0-5 = 4096/8192; thinking lane 6 = 32768/16384.
if (( index == 6 )); then
  export HF_MAX_NEW_TOKENS=32768
  export HF_REACT_MAX_NEW_TOKENS=16384
  export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": true, "reasoning_effort": "xhigh"}'
  # thinking-wave input clamp: input + plan budget must fit the context
  export HF_MAX_INPUT_TOKENS=98304
else
  export HF_MAX_NEW_TOKENS=4096
  export HF_REACT_MAX_NEW_TOKENS=8192
  export HF_REACT_SOFT_MAX_NEW_TOKENS=1024
  export HF_MAX_INPUT_TOKENS=122880
fi
if (( index == 5 )); then
  export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'
fi
if (( index == 1 )); then
  # glm-4-9b ships custom modeling code (same as its scale-ext lane)
  export HF_TRUST_REMOTE_CODE=1
fi
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
export VLLM_TENSOR_PARALLEL=${tensor_parallel[$index]}
export HF_MODEL_CONTEXT_TOKENS=131072
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
  --state-namespace "replan-exp-${index}${ids_file:+-$(basename "$ids_file" .txt)}" \
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
