#!/bin/bash
#SBATCH --job-name=agentorch-temp-sweep
#SBATCH --partition=long
#SBATCH --array=0-14
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=100G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-tempsweep-%A_%a.out

# Temperature-uncertainty sweep (2026-09-06): five strong open-weight
# checkpoints from the canonical roster re-evaluated at sampling
# temperatures 0.3 / 0.6 / 1.0 (top_p 1.0, engine seed 0). The existing
# greedy tier runs are the T=0 baseline. Protocol otherwise matches
# run_scale_frontier.sbatch / run_scale_extension.sbatch: frozen Global
# View plans then ReAct on all 3,220 variants, simulated backend,
# resumable checkpoints, offline pinned weights.
#
# Lane layout: index = temp_index*5 + model_index.
#   models 0-4: Qwen3.8-27B-FP8 (TP1), gemma-4-31B-it (TP2),
#               DeepSeek-V4-Flash-0731 (TP2), GLM-4.5-FP8 (TP4),
#               Qwen3-30B-A3B-Instruct-2507 (TP1)
#   temps 0-2:  0.3, 0.6, 1.0
# Submit one lane per sbatch call with matching --gres/--mem/--cpus
# (see reproduction/cluster/submit_temp_sweep.sh); results land in
# outputs/full_eval/temp-sweep-t{03,06,10}-20260906/.
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
  Qwen/Qwen3.8-27B-FP8
  google/gemma-4-31B-it
  deepseek-ai/DeepSeek-V4-Flash-0731
  zai-org/GLM-4.5-FP8
  Qwen/Qwen3-30B-A3B-Instruct-2507
)
revisions=(
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
  842da3794eaa0b77d5f08bae87a17459d91ff475
  7872f01b1d1fe23eabc4c98b48bffcef5a386062
  8cc290ee4c7cbfa38d3a2db9bd0b7371773ece81
  0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe
)
tensor_parallel=(1 2 2 4 1)
kv_cache_dtypes=(auto auto fp8 auto auto)
use_deep_gemm=(0 0 1 0 0)
temps=(0.3 0.6 1.0)
temp_tags=(t03 t06 t10)

index=${SLURM_ARRAY_TASK_ID}
model_index=$(( index % 5 ))
temp_index=$(( index / 5 ))
model=${models[$model_index]}
revision=${revisions[$model_index]}
temp=${temps[$temp_index]}
run_name=${1:-temp-sweep-${temp_tags[$temp_index]}-20260906}
recipe_limit=${2:-${AGENTORCH_RECIPE_LIMIT:-}}
modes=${3:-plan_execute,react}
ids_file=${4:-}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

# FP8 JIT toolchain wiring, identical to run_scale_frontier.sbatch.
[[ -n "${AGENTORCH_CUDA_HOME:-}" ]] && export CUDA_HOME="$AGENTORCH_CUDA_HOME"
export PATH="${CUDA_HOME:+$CUDA_HOME/bin:}$PATH"
export VLLM_USE_DEEP_GEMM=${use_deep_gemm[$model_index]}
export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}${CUDA_HOME:+$CUDA_HOME/lib}${LIBRARY_PATH:+:$LIBRARY_PATH}"

export HF_TEMPERATURE=$temp
export HF_MAX_NEW_TOKENS=4096
export HF_REACT_MAX_NEW_TOKENS=8192
export HF_REACT_SOFT_MAX_NEW_TOKENS=1024
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
export VLLM_TENSOR_PARALLEL=${tensor_parallel[$model_index]}
export VLLM_KV_CACHE_DTYPE=${kv_cache_dtypes[$model_index]}
# DeepSeek-V4: tokenizer thread-safety and fp8_ds_mla constraints
# (same as frontier lane 3).
if (( model_index == 2 )); then export HF_PROMPT_IDS=1; export VLLM_ASYNC_SCHEDULING=0; fi
# Qwen3.8 thinks by default; the sweep matches the main roster's
# thinking-disabled protocol so temperature is the only variable.
if (( model_index == 0 )); then export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'; fi
# GLM-4.5 is a hybrid reasoner: greedy decoding never opened a <think>
# span, but sampling does (drafting the plan inside an unterminated span
# that the no-hidden-reasoning protocol scores as a failed generation),
# so the sweep pins thinking off explicitly.
if (( model_index == 3 )); then export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'; fi
export HF_MODEL_CONTEXT_TOKENS=131072
export HF_MAX_INPUT_TOKENS=122880
export HF_MODEL_REVISION="$revision"
: "${HF_HOME:?set HF_HOME in benchmark/reproduction/cluster/env.sh}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH=benchmark

echo "temp-sweep lane ${index}: model=${model} temperature=${temp} run=${run_name} modes=${modes}"

limit_args=()
if [[ -n "$recipe_limit" ]]; then
  limit_args=(--limit "$recipe_limit")
fi

"$AGENTORCH_PYTHON" -m evaluation.full_eval \
  --run-name "$run_name" \
  --state-namespace "tempsweep-model-${model_index}-${temp_tags[$temp_index]}-${modes//,/-}${ids_file:+-$(basename "$ids_file" .txt)}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  ${ids_file:+--ids $(tr "\n" " " < "$ids_file")} \
  "${limit_args[@]}"
