#!/bin/bash
#SBATCH --job-name=agentorch-api-models
#SBATCH --partition=long
#SBATCH --array=0-5
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-api-%A_%a.out

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
export PATH="$AGENTORCH_CONDA_BIN:/usr/local/bin:/usr/bin:/bin"

# Indexes 0-2 are the original three-model comparison; indexes 3-4 are the
# scale extension (claude-haiku-4-5 and the direct-OpenAI GPT-5.5 snapshot).
# Submit extensions alone with ``--array=3`` / ``--array=4`` and their own
# run name so completed runs are never appended to.
models=(
  gpt-4o
  gpt-35-turbo
  claude-opus-5
  claude-haiku-4-5
  gpt-5.5-2026-04-23
  gpt-5.6-sol
)

index=${SLURM_ARRAY_TASK_ID}
model=${models[$index]}
run_name=${1:-api-3models-clean-sim-global-react-20260814}
recipe_limit=${2:-}
modes=${3:-plan_execute,react}
# GLOBAL+INPUT plans once per variant (3,220 ~60k-token prompts per lane,
# identical within a recipe up to the runtime-input section): enable
# Anthropic prompt caching for that mode. Output-neutral, billing only;
# usage counters land in leaderboard.json meta.model_runtime.api_usage.
if [[ "$modes" == *global_input* ]]; then export ANTHROPIC_PROMPT_CACHE=1; fi

# Load credentials at runtime. Never copy API secrets into benchmark.
set -a
source "$AGENTORCH_API_ENV_FILE"  # model-provider keys (Azure/OpenAI/Anthropic); never in git
set +a

# This is a simulated-connector comparison. The credential file also contains
# routing for real Slack, Sheets, and Snowflake connectors; do not let those
# values alter the simulator's canonical logical environment. Keep only model
# provider settings from the sourced file.
unset SLACK_BOT_TOKEN SLACK_CHANNEL_OVERRIDE
unset SHEETS_SPREADSHEET_ID SHEETS_TAB
unset SNOWFLAKE_ACCOUNT SNOWFLAKE_USER SNOWFLAKE_ROLE SNOWFLAKE_PAT
unset SNOWFLAKE_PRIVATE_KEY SNOWFLAKE_PRIVATE_KEY_PATH
unset SNOWFLAKE_PRIVATE_KEY_PASSPHRASE SNOWFLAKE_WAREHOUSE
unset SNOWFLAKE_DATABASE SNOWFLAKE_SCHEMA

export API_CONCURRENT_BATCHING=1
export API_MAX_ATTEMPTS=20
if (( index == 0 )); then
  # The two Azure deployments have a low TPM quota; bound concurrency and
  # honor Retry-After rather than recording rate-limit failures as model errors.
  # Two in-flight calls keep latency hidden without the eight-request burst
  # that exceeded the gpt-4o deployment's quota in preflight.
  export API_CONCURRENCY=2
  export VLLM_REACT_CONCURRENCY=8
elif (( index == 1 )); then
  # The weaker deployment maps to a lower-quota gpt-4.1-mini backend. Frozen
  # plans are generated serially by the harness; two ReAct requests overlap
  # variable per-case latency while the retry layer honors deployment TPM.
  export API_CONCURRENCY=2
  export VLLM_REACT_CONCURRENCY=8
elif (( index == 2 )); then
  export API_CONCURRENCY=4
  export VLLM_REACT_CONCURRENCY=8
  # Claude Opus 5 thinks by default. The benchmark scores direct JSON
  # plans/actions, so keep the 4096-token cap shared by the API clients
  # instead of allowing hidden thinking to consume it.
  export ANTHROPIC_THINKING=disabled
  export ANTHROPIC_EFFORT=high
  export ANTHROPIC_MAX_TOKENS=4096
  export ANTHROPIC_TEMPERATURE=none
elif (( index == 3 )); then
  export API_CONCURRENCY=4
  export VLLM_REACT_CONCURRENCY=8
  # claude-haiku-4-5 does not accept the effort parameter (400), and
  # thinking is off by default on this model — the explicit disable keeps
  # the protocol declaration identical to the Opus task.
  export ANTHROPIC_THINKING=disabled
  export ANTHROPIC_MAX_TOKENS=4096
  export ANTHROPIC_TEMPERATURE=none
elif (( index == 5 )); then
  # gpt-5.6-sol test-time-reasoning ablation: direct OpenAI with
  # reasoning_effort=high and a 16,384 completion cap (reasoning tokens
  # bill inside max_completion_tokens). Reported separately, like the
  # claude-opus-5 thinking ablation.
  set -a
  source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
  set +a
  export OPENAI_API_MODE=direct
  export OPENAI_REASONING_EFFORT=high
  export OPENAI_MAX_TOKENS=16384
  export API_CONCURRENCY=4
  export VLLM_REACT_CONCURRENCY=8
  unset AZURE_OPENAI_ENDPOINT AZURE_OPENAI_DEPLOYMENT AZURE_OPENAI_API_VERSION AZURE_OPENAI_API_KEY
else
  # Direct OpenAI (api.openai.com) for the GPT-5 reasoning family. The key
  # lives in the repo-root .env (outside the published bundle) and overrides
  # the Azure key sourced above; reasoning_effort=none keeps hidden reasoning
  # at zero tokens, mirroring the Claude thinking=disabled protocol.
  set -a
  source "$AGENTORCH_ENV_FILE"  # HF_TOKEN and provider keys; never in git
  set +a
  export OPENAI_API_MODE=direct
  export OPENAI_REASONING_EFFORT=none
  export API_CONCURRENCY=4
  export VLLM_REACT_CONCURRENCY=8
  unset AZURE_OPENAI_ENDPOINT AZURE_OPENAI_DEPLOYMENT AZURE_OPENAI_API_VERSION AZURE_OPENAI_API_KEY
fi
export PYTHONPATH=benchmark

limit_args=()
if [[ -n "$recipe_limit" ]]; then
  limit_args=(--limit "$recipe_limit")
fi

"$AGENTORCH_PYTHON" -m evaluation.full_eval \
  --run-name "$run_name" \
  --state-namespace "api-model-${index}" \
  --backend simulated \
  --model "$model" \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  "${limit_args[@]}"
