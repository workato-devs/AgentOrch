#!/bin/bash
#SBATCH --job-name=agentorch-replan-heldout
#SBATCH --partition=long
#SBATCH --array=0-7
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=24
#SBATCH --mem=100G
#SBATCH --time=2-00:00:00
# Nodes reserved by others: pass --exclude=<node> on the sbatch command line.
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-replan-heldout-%A_%a.out
#
# Held-out-variant self-evolution (experiments/replan_iter_heldout.py): the
# same eight models, all 650 recipes, K=3 revision rounds, but the model only
# receives execution feedback from each recipe's first two variants (v00,
# v01); the revised plan is scored on the remaining, never-shown variants.
# Round 0 is the frozen Global plan (pre-seeded from the tier global-plans,
# cache-key hit), so round 0 == Global on every subset. Everything else
# (prompt, validator, executor, scorer, decoding caps, engine flags) is
# identical to reproduction/cluster/run_replan_iter_smoke.sbatch / the full replan_iter run
# replan-iter-full-20260829.
#
# Submit (lanes 3 and 5 are TP2):
#   sbatch --qos=<qos> --exclude=<reserved-node> --array=0-2,4,6,7 benchmark/reproduction/cluster/run_replan_iter_heldout.sbatch
#   sbatch --qos=<qos> --exclude=<reserved-node> --array=3,5 --gres=gpu:h200:2 benchmark/reproduction/cluster/run_replan_iter_heldout.sbatch
# Args: $1 run name (default replan-iter-heldout-20260908), $2 rounds (3),
#       $3 ids file (all 650), $4 feedback variants (2).
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

lanes=(qwen3.8-27b qwen3-4b gemma-3-27b gemma-4-26b mistral-24b deepseek-v4-flash gemma-4-12b qwen3-30b-a3b)
models=(
  Qwen/Qwen3.8-27B-FP8
  Qwen/Qwen3-4B-Instruct-2507
  google/gemma-3-27b-it
  google/gemma-4-26B-A4B-it
  mistralai/Mistral-Small-3.1-24B-Instruct-2503
  deepseek-ai/DeepSeek-V4-Flash-0731
  google/gemma-4-12B-it
  Qwen/Qwen3-30B-A3B-Instruct-2507
)
revisions=(
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
  cdbee75f17c01a7cc42f958dc650907174af0554
  005ad3404e59d6023443cb575daa05336842228a
  4d7ae4984b7db7de8f8457170b3f1a419ee76d52
  68faf511d618ef198fef186659617cfd2eb8e33a
  7872f01b1d1fe23eabc4c98b48bffcef5a386062
  707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7
  0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe
)
tier_dirs=(
  large_model/Qwen3.8-27B-FP8
  small_model/Qwen3-4B-Instruct-2507
  large_model/gemma-3-27b-it
  medium_model/gemma-4-26B-A4B-it
  large_model/Mistral-Small-3.1-24B-Instruct-2503
  large_model/DeepSeek-V4-Flash-0731
  medium_model/gemma-4-12B-it
  large_model/Qwen3-30B-A3B-Instruct-2507
)
tensor_parallel=(1 1 1 2 1 2 1 1)
kv_cache_dtypes=(auto auto auto auto auto fp8 auto auto)
use_deep_gemm=(0 0 0 0 0 1 0 0)

index=${SLURM_ARRAY_TASK_ID}
lane=${lanes[$index]}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-replan-iter-heldout-20260908}
rounds=${2:-3}
ids_file=${3:-benchmark/experiments/replan_iter_smoke/ids_full.txt}
feedback_variants=${4:-2}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

# Pre-seed the frozen-plan cache from the canonical tier global-plans so
# round 0 == Global (invalid plans included, with their raw responses).
safe_model="hf_${model//\//__}"
plan_dst="benchmark/outputs/full_eval/${run_name}/plans/${safe_model}"
plan_src="benchmark/outputs/full_eval/${tier_dirs[$index]}/global-plans"
if [[ ! -d "$plan_dst" ]]; then
  mkdir -p "$(dirname "$plan_dst")"
  cp -r "$plan_src" "$plan_dst"
fi

[[ -n "${AGENTORCH_CUDA_HOME:-}" ]] && export CUDA_HOME="$AGENTORCH_CUDA_HOME"
export PATH="${CUDA_HOME:+$CUDA_HOME/bin:}$PATH"
export VLLM_USE_DEEP_GEMM=${use_deep_gemm[$index]}
export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}${CUDA_HOME:+$CUDA_HOME/lib}${LIBRARY_PATH:+:$LIBRARY_PATH}"

# Planner-lane decoding caps (cache-key parity; revisions use the planner cap).
export HF_MAX_NEW_TOKENS=4096
export HF_REACT_MAX_NEW_TOKENS=8192
export HF_REACT_SOFT_MAX_NEW_TOKENS=1024
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
export VLLM_TENSOR_PARALLEL=${tensor_parallel[$index]}
export VLLM_KV_CACHE_DTYPE=${kv_cache_dtypes[$index]}
# DeepSeek lane: same engine flags as its plan-generation lane (frontier idx 3)
if (( index == 5 )); then export HF_PROMPT_IDS=1; export VLLM_ASYNC_SCHEDULING=0; fi
# Revision requests go to the engine in chunks of 100 (the smoke's proven
# batch size): a single 650-prompt batch wedged the Qwen3.8-27B engine for
# 13 h on 2026-08-29, and async_scheduling=False (tried first) was 4.5x
# slower per prompt (32 prompts in 42 min vs 100 in 29 min).
export REPLAN_ITER_LLM_CHUNK=100
export HF_MODEL_CONTEXT_TOKENS=131072
export HF_MAX_INPUT_TOKENS=122880
export HF_MODEL_REVISION="$revision"
: "${HF_HOME:?set HF_HOME in benchmark/reproduction/cluster/env.sh}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH=benchmark
export REPLAN_ITER_EXEC_WORKERS=4
if (( index == 0 )); then export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'; fi

"$AGENTORCH_PYTHON" -m experiments.replan_iter_heldout \
  --run-name "$run_name" \
  --state-namespace "replan-heldout-${lane}" \
  --backend simulated \
  --model "hf:${model}" \
  --rounds "$rounds" \
  --feedback full \
  --feedback-variants "$feedback_variants" \
  --resume \
  --ids $(tr "\n" " " < "$ids_file")
