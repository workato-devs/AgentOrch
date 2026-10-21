#!/bin/bash
#SBATCH --job-name=agentorch-thinking-local
#SBATCH --partition=long
#SBATCH --array=0-5
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=200G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-thinking-%A_%a.out

# Local test-time-reasoning ablation lanes (reported separately from the
# main comparison, like the claude-opus-5 thinking ablation): the same
# checkpoints and scoring with the vendor's thinking mode enabled at HIGH
# effort. Thinking tokens share the generation budget, so caps rise to
# 16,384 with the soft early-exit disabled (a soft stop would truncate
# reasoning); only the text outside <think> spans is parsed and scored.
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
  meta-models/Muse-Glimmer-30B
  zai-org/GLM-5.2-FP8
  deepseek-ai/DeepSeek-V4-Flash-0731
  zai-org/GLM-4.5-FP8
  zai-org/GLM-4.5-Air-FP8
)
revisions=(
  017b9c7af6b5689d5dd426a76e0bc077eb5ca20a
  a4e59da52a7bc87ae7251dd5545c0dd437c44b68
  ba978f7d347eaf65d22f1a86833408afdb953541
  7872f01b1d1fe23eabc4c98b48bffcef5a386062
  8cc290ee4c7cbfa38d3a2db9bd0b7371773ece81
  f9a9c5acf5e543cd24d659a056c5dbcda78ffcfc
)
pythons=(
  "$AGENTORCH_PYTHON"
  "$AGENTORCH_MUSE_PYTHON"
  "$AGENTORCH_PYTHON"
  "$AGENTORCH_PYTHON"
  "$AGENTORCH_PYTHON"
  "$AGENTORCH_PYTHON"
)
tensor_parallel=(
  1
  1
  8
  2
  4
  2
)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
revision=${revisions[$index]}
python_bin=${pythons[$index]}
run_name=${1:-local-thinking-20260817}
recipe_limit=${2:-}
modes=${3:-plan_execute,react}
ids_file=${4:-}

set -a
source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
set +a

if (( index == 0 )); then
  # Qwen3.8: thinking via chat-template switches.
  export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": true, "reasoning_effort": "xhigh"}'
  export HF_THINKING_PREFIX=1
  export HF_TAKE_LAST_JSON=1
elif (( index == 2 )); then
  # GLM-5.2: template-default reasoning (untagged inline); score the final
  # JSON only.
  export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": true}'
  export HF_THINKING_PREFIX=1
  export HF_TAKE_LAST_JSON=1
elif (( index == 3 )); then
  # DeepSeek-V4-Flash: vLLM's deepseek_v4 tokenizer accepts thinking +
  # reasoning_effort chat-template kwargs; the encoder opens <think> on the
  # prompt side. Frontier-lane stability flags carry over (fp8 MLA KV cache,
  # deep_gemm dispatch, ids-prompts, synchronous scheduling).
  export HF_CHAT_TEMPLATE_KWARGS='{"thinking": true, "reasoning_effort": "high"}'
  export HF_THINKING_PREFIX=1
  export HF_TAKE_LAST_JSON=1
  export HF_PROMPT_IDS=1
  export VLLM_KV_CACHE_DTYPE=fp8
  export VLLM_ASYNC_SCHEDULING=0
  export LANE_DEEP_GEMM=1
elif (( index == 4 || index == 5 )); then
  # GLM-4.5 / GLM-4.5-Air: hybrid reasoning, enable_thinking template switch
  # (tagged <think> blocks).
  export HF_CHAT_TEMPLATE_KWARGS='{"enable_thinking": true}'
  export HF_THINKING_PREFIX=1
  export HF_TAKE_LAST_JSON=1
else
  # Muse Glimmer: reasoning strength via documented system-prompt directive.
  export HF_SYSTEM_PROMPT_SUFFIX='Reasoning strength: high'
  # Architecture postdates every vLLM registry and 0.27's transformers
  # wrapper produces garbage (probe-verified); native transformers via the
  # image-text auto class generates correctly, so this lane runs the pure
  # transformers engine. Harmony-style channel output: score the final
  # JSON only.
  export HF_LOCAL_ENGINE=transformers
  # Harmony special markers do not survive a string render/re-encode
  # round-trip; feed template token ids directly.
  export HF_PROMPT_IDS=1
  export HF_TAKE_LAST_JSON=1
  # The balanced-JSON early stop fires on brace snippets inside the analysis
  # channel (channel markers are special tokens, stripped from the decoded
  # text); generate to the model's own EOS instead.
  export HF_JSON_EARLYSTOP=0
  # Split the surfaced answer from reasoning on the exact channel header
  # (recipient + message special token); a plain-text marker can occur
  # inside the answer's own strings and cut it apart.
  export HF_RESPONSE_SPLIT_MARKER='to=user<|message|>'
fi

# xhigh reasoning on the one-shot plan can exceed 16K thinking tokens;
# the plan cap is doubled (react keeps 16K, which preflight validated).
export HF_MAX_NEW_TOKENS=32768
export HF_REACT_MAX_NEW_TOKENS=16384
export HF_REACT_SOFT_MAX_NEW_TOKENS=16384
# Default engine; a lane block above may pin transformers (Muse Glimmer).
export HF_LOCAL_ENGINE=${HF_LOCAL_ENGINE:-vllm}
export VLLM_USE_FLASHINFER_SAMPLER=0
export VLLM_CONCURRENT_BATCHING=1
export VLLM_REACT_CONCURRENCY=16
export VLLM_TENSOR_PARALLEL=${tensor_parallel[$index]}
export HF_MODEL_CONTEXT_TOKENS=131072
# 16,384-token generation must fit inside the 131,072 context window
export HF_MAX_INPUT_TOKENS=98304
export HF_MODEL_REVISION="$revision"
: "${HF_HOME:?set HF_HOME in benchmark/reproduction/cluster/env.sh}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
[[ -n "${AGENTORCH_CUDA_HOME:-}" ]] && export CUDA_HOME="$AGENTORCH_CUDA_HOME"
export PATH="${CUDA_HOME:+$CUDA_HOME/bin:}$PATH"
export VLLM_USE_DEEP_GEMM=${LANE_DEEP_GEMM:-0}
# The compute image ships the CUDA driver as libcuda.so.1 with no linker
# symlink; JIT link steps need -lcuda, resolved via this stub directory.
export LIBRARY_PATH="${AGENTORCH_CUDA_STUBS:+$AGENTORCH_CUDA_STUBS:}${CUDA_HOME:+$CUDA_HOME/lib}${LIBRARY_PATH:+:$LIBRARY_PATH}"
export PYTHONPATH=benchmark

limit_args=()
if [[ -n "$recipe_limit" ]]; then
  limit_args=(--limit "$recipe_limit")
fi

"$python_bin" -m evaluation.full_eval \
  --run-name "$run_name" \
  --state-namespace "thinking-model-${index}-${modes//,/-}${ids_file:+-$(basename "$ids_file" .txt)}" \
  --backend simulated \
  --model "hf:${model}" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  ${ids_file:+--ids $(tr "\n" " " < "$ids_file")} \
  "${limit_args[@]}"
