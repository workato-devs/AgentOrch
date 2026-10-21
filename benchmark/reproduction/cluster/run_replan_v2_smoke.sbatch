#!/bin/bash
#SBATCH --job-name=agentorch-replan-v2-smoke
#SBATCH --partition=long
#SBATCH --array=0-4
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=24
#SBATCH --mem=100G
#SBATCH --time=2-00:00:00
# Nodes reserved by others: pass --exclude=<node> on the sbatch command line.
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-replan-v2-smoke-%A_%a.out
#
# Replan protocol v2 smoke: five models x ~100 recipes (all variants) whose
# frozen initial plan is valid, `--replan-protocol v2 --max-replans 6`.
# Frozen plans are pre-seeded from each model's canonical tier global-plans
# (cache-key hit, 0 planner calls) so v2-v1 deltas isolate the review-turn
# protocol. Subsets: experiments/replan_v2_smoke/<lane>.txt
# (experiments/select_replan_v2_smoke_ids.py). Paired comparison against the
# tier v1 replan artifacts: experiments/compare_replan_v2_smoke.py.
#
# Submit (lane 3 = gemma-4-26B-A4B is TP2):
#   sbatch --qos=borrow --exclude=<reserved-node> --array=0-2,4 benchmark/reproduction/cluster/run_replan_v2_smoke.sbatch
#   sbatch --qos=borrow --exclude=<reserved-node> --array=3 --gres=gpu:h200:2 benchmark/reproduction/cluster/run_replan_v2_smoke.sbatch
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

lanes=(qwen3.8-27b qwen3-4b gemma-3-27b gemma-4-26b mistral-24b)
models=(
  Qwen/Qwen3.8-27B-FP8
  Qwen/Qwen3-4B-Instruct-2507
  google/gemma-3-27b-it
  google/gemma-4-26B-A4B-it
  mistralai/Mistral-Small-3.1-24B-Instruct-2503
)
revisions=(
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
  cdbee75f17c01a7cc42f958dc650907174af0554
  005ad3404e59d6023443cb575daa05336842228a
  4d7ae4984b7db7de8f8457170b3f1a419ee76d52
  68faf511d618ef198fef186659617cfd2eb8e33a
)
tier_dirs=(
  large_model/Qwen3.8-27B-FP8
  small_model/Qwen3-4B-Instruct-2507
  large_model/gemma-3-27b-it
  medium_model/gemma-4-26B-A4B-it
  large_model/Mistral-Small-3.1-24B-Instruct-2503
)
tensor_parallel=(1 1 1 2 1)

index=${SLURM_ARRAY_TASK_ID}
lane=${lanes[$index]}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-replan-v2-smoke-20260828}
protocol=${2:-v2}
ids_file=${3:-benchmark/experiments/replan_v2_smoke/${lane}.txt}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

# Pre-seed the frozen-plan cache from the canonical tier global-plans so the
# smoke makes zero planner calls (same decoding fingerprint as those lanes).
safe_model="hf_${model//\//__}"
plan_dst="benchmark/outputs/full_eval/${run_name}/plans/${safe_model}"
plan_src="benchmark/outputs/full_eval/${tier_dirs[$index]}/global-plans"
if [[ ! -d "$plan_dst" ]]; then
  mkdir -p "$(dirname "$plan_dst")"
  cp -r "$plan_src" "$plan_dst"
fi

# FP8 JIT toolchain (harmless on non-FP8 lanes).
[[ -n "${AGENTORCH_CUDA_HOME:-}" ]] && export CUDA_HOME="$AGENTORCH_CUDA_HOME"
export PATH="${CUDA_HOME:+$CUDA_HOME/bin:}$PATH"
export VLLM_USE_DEEP_GEMM=0
export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}${CUDA_HOME:+$CUDA_HOME/lib}${LIBRARY_PATH:+:$LIBRARY_PATH}"

# Decoding caps identical to the plan-generation lanes (cache-key parity)
# and to the v1 replan waves (review-turn parity: 4096 new tokens).
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
# Qwen3.8 thinks by default; the roster lane runs thinking-disabled.
if (( index == 0 )); then export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'; fi

"$AGENTORCH_PYTHON" -m evaluation.full_eval \
  --run-name "$run_name" \
  --state-namespace "replan-v2-smoke-${lane}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes replan \
  --replan-protocol "$protocol" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  --max-replans 6 \
  --ids $(tr "\n" " " < "$ids_file")
