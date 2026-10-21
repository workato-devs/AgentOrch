#!/bin/bash
#SBATCH --job-name=agentorch-scale-ext
#SBATCH --partition=long
#SBATCH --array=0-14
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=100G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-ext-%A_%a.out

# Scale-extension campaign: the 15 single-GPU additions from
# evaluation/global_react_models.json (tiers small/medium/large). Same
# protocol as run_instruct_scale_comparison.sbatch: one model per array
# task, frozen Global View plans then ReAct on all 3,220 variants with the
# simulated backend, resumable checkpoints. The 70B-class additions run in
# run_scale_extension_70b.sbatch. Checkpoints must be pre-downloaded
# (reproduction/cluster/download_scale_extension_models.sh) because HF_HUB_OFFLINE=1.
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
  ibm-granite/granite-3.1-2b-instruct
  Qwen/Qwen2.5-3B-Instruct
  microsoft/Phi-3.5-mini-instruct
  Qwen/Qwen3-4B-Instruct-2507
  google/gemma-3-4b-it
  microsoft/Phi-3-small-128k-instruct
  ibm-granite/granite-3.1-8b-instruct
  zai-org/glm-4-9b-chat
  google/gemma-3-12b-it
  mistralai/Mistral-Nemo-Instruct-2407
  microsoft/Phi-3-medium-128k-instruct
  mistralai/Mistral-Small-3.1-24B-Instruct-2503
  google/gemma-3-27b-it
  Qwen/Qwen3-30B-A3B-Instruct-2507
  CohereForAI/c4ai-command-r-08-2024
)
revisions=(
  bbc2aed595bd38bd770263dc3ab831db9794441d
  aa8e72537993ba99e69dfaafa59ed015b17504d1
  2fe192450127e6a83f7441aef6e3ca586c338b77
  cdbee75f17c01a7cc42f958dc650907174af0554
  093f9f388b31de276ce2de164bdc2081324b9767
  e95b185a59a58450c9b1dd7347a9dee78f18113e
  4009206d5fc95d2e65a7b7633e159d6e97e25d35
  bd8234fe5e0c09c48637a92abb0c797cb5fa0e73
  96b6f1eccf38110c56df3a15bffe176da04bfd80
  04d8a90549d23fc6bd7f642064003592df51e9b3
  a088b37c71d441ab6d862bb3fcfe6165b3014702
  68faf511d618ef198fef186659617cfd2eb8e33a
  005ad3404e59d6023443cb575daa05336842228a
  0d7cf23991f47feeb3a57ecb4c9cee8ea4a17bfe
  dc835b893cd3fb8f14b24970dbc2a0a6d3c22ee3
)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
run_name=${1:-${AGENTORCH_RUN_NAME:-scale-ext-15models-20260815}}
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
if (( index <= 4 )); then
  export VLLM_REACT_CONCURRENCY=32
else
  export VLLM_REACT_CONCURRENCY=16
fi
# GLM-4 chat and Phi-3-small ship tokenizer/config as repository code.
if [[ "$index" == 5 || "$index" == 7 ]]; then
  export HF_TRUST_REMOTE_CODE=1
fi
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
  --state-namespace "ext-model-${index}-${modes//,/-}${ids_file:+-$(basename "$ids_file" .txt)}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  ${ids_file:+--ids $(tr "\n" " " < "$ids_file")} \
  "${limit_args[@]}"
