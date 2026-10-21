#!/bin/bash
#SBATCH --job-name=agentorch-local-view
#SBATCH --partition=long
#SBATCH --array=0-16
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=24
#SBATCH --mem=100G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-local-view-%A_%a.out

# Local View ablation (mode incremental_workflow): the model builds one
# WorkflowPlan through the append-only plan editor — one editor-operation
# JSON per turn, immutable accepted prefix, planning only — and the frozen
# plan is then executed on every hidden variant exactly like Global View.
# Roster = every model configuration that ran replan, so the four settings
# (global / local / react / replan) share one model set. No plan-cache
# seeding: incremental planning artifacts are their own planning_mode and
# cannot reuse the one-shot Global caches.
# Lanes 7/12/13/14 are TP2 — submit those with --gres=gpu:h200:2.
# Lane 16 is the Qwen3.8-27B thinking config (run suffix -think).
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
  Qwen/Qwen2.5-3B-Instruct
  Qwen/Qwen3-4B-Instruct-2507
  mistralai/Mistral-Nemo-Instruct-2407
  google/gemma-3-12b-it
  zai-org/glm-4-9b-chat
  Qwen/Qwen2.5-14B-Instruct
  google/gemma-4-12B-it
  google/gemma-4-26B-A4B-it
  google/gemma-3-27b-it
  Qwen/Qwen3-30B-A3B-Instruct-2507
  mistralai/Mistral-Small-3.1-24B-Instruct-2503
  CohereForAI/c4ai-command-r-08-2024
  meta-llama/Llama-3.3-70B-Instruct
  Qwen/Qwen2.5-72B-Instruct
  zai-org/GLM-4.5-Air-FP8
  Qwen/Qwen3.8-27B-FP8
  Qwen/Qwen3.8-27B-FP8
)
revisions=(
  aa8e72537993ba99e69dfaafa59ed015b17504d1
  cdbee75f17c01a7cc42f958dc650907174af0554
  04d8a90549d23fc6bd7f642064003592df51e9b3
  96b6f1eccf38110c56df3a15bffe176da04bfd80
  bd8234fe5e0c09c48637a92abb0c797cb5fa0e73
  cf98f3b3bbb457ad9e2bb7baf9a0125b6b88caa8
  707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7
  4d7ae4984b7db7de8f8457170b3f1a419ee76d52
  005ad3404e59d6023443cb575daa05336842228a
  0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe
  68faf511d618ef198fef186659617cfd2eb8e33a
  dc835b893cd3fb8f14b24970dbc2a0a6d3c22ee3
  6f6073b423013f6a7d4d9f39144961bfbfbc386b
  495f39366efef23836d0cfae4fbe635880d2be31
  f9a9c5acf5e543cd24d659a056c5dbcda78ffcfc
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
)
tensor_parallel=(1 1 1 1 1 1 1 2 1 1 1 1 2 2 2 1 1)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-local-view-20260824}
if (( index == 16 )); then run_name="${run_name}-think"; fi
recipe_limit=${2:-}
modes=${3:-incremental_workflow}
ids_file=${4:-}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

# FP8 JIT toolchain (27B/Air FP8 lanes; harmless elsewhere).
[[ -n "${AGENTORCH_CUDA_HOME:-}" ]] && export CUDA_HOME="$AGENTORCH_CUDA_HOME"
export PATH="${CUDA_HOME:+$CUDA_HOME/bin:}$PATH"
export VLLM_USE_DEEP_GEMM=0
export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}${CUDA_HOME:+$CUDA_HOME/lib}${LIBRARY_PATH:+:$LIBRARY_PATH}"

if (( index == 16 )); then
  export HF_MAX_NEW_TOKENS=32768
  export HF_REACT_MAX_NEW_TOKENS=16384
  export HF_MAX_INPUT_TOKENS=98304
  export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": true, "reasoning_effort": "xhigh"}'
  export HF_THINKING_PREFIX=1
else
  export HF_MAX_NEW_TOKENS=4096
  export HF_REACT_MAX_NEW_TOKENS=8192
  export HF_REACT_SOFT_MAX_NEW_TOKENS=1024
  export HF_MAX_INPUT_TOKENS=122880
fi
if (( index == 15 )); then
  export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'
fi
if (( index == 14 )); then
  # GLM-4.5-Air on the muse env (0.27.1): the newer chat template defaults
  # enable_thinking=true and the model emits unclosed <think> reasoning
  # that strips to empty text; pin thinking off to match the non-thinking
  # ablation protocol (the 0.24 template never injected the switch).
  export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'
fi
if (( index == 4 )); then
  # glm-4-9b ships custom modeling code
  export HF_TRUST_REMOTE_CODE=1
fi
export HF_LOCAL_ENGINE=vllm
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
# Editor sessions run concurrently through the engine (cache-warmer pass);
# doomed 64-turn sessions are 1-3 h each and serial planning would take
# weeks on low-compliance models.
export VLLM_PLANNER_CONCURRENCY=12
# Periodic all-thread stack dumps for live-stall diagnosis (srun --overlap
# is disabled on this cluster).
export HF_STACK_DUMP_SECONDS=600
export HF_STACK_DUMP_DIR="$AGENTORCH_ROOT/benchmark/outputs/stackdumps"
# Engine-wedge countermeasure + flight recorder: the second shard cohort
# reliably hung inside engine.generate (leader at the same frame across
# 9 consecutive stack dumps, artifacts frozen 2 h). Our own frontier
# launcher already disables async scheduling for the DeepSeek lane
# because of logits-processor races under async scheduling — same class.
export VLLM_ASYNC_SCHEDULING=0
export HF_GEN_DEBUG_DIR="$AGENTORCH_ROOT/benchmark/outputs/stackdumps"
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

# GLM-4.5-Air (lane 14): mid-conversation prompts (editor turns, like the
# replan review turns) trigger its empty-completion behavior on the
# benchmark-standard vLLM 0.24.0; run this lane on the muse env
# (vLLM 0.27.1) as the same declared newer-stack deviation as its
# thinking lanes. All other lanes stay on the standard engine.
PY="$AGENTORCH_PYTHON"
if (( index == 14 )); then PY="$AGENTORCH_MUSE_PYTHON"; fi

"$PY" -m evaluation.full_eval \
  --run-name "$run_name" \
  --state-namespace "local-view-${index}${ids_file:+-$(basename "$ids_file" .txt)}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  ${ids_file:+--ids $(tr "\n" " " < "$ids_file")} \
  "${limit_args[@]}"
