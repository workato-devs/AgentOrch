#!/bin/bash
#SBATCH --job-name=agentorch-opus-thinking
#SBATCH --partition=long
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=7-00:00:00
#SBATCH --output=benchmark/outputs/slurm_logs/slurm-opus-thinking-%j.out

# Ablation: claude-opus-5 with adaptive thinking enabled. The main comparison
# disables thinking so every model gets the same test-time compute; this run
# measures how much extra Global View capability hidden reasoning buys. It
# writes to its own run directory and state namespace and never touches the
# canonical global-react-final-20260814 results.
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

run_name=${1:-opus-thinking-20260815}
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

# Simulated-connector run: strip live-connector routing (see
# run_api_model_comparison.sbatch for the rationale).
unset SLACK_BOT_TOKEN SLACK_CHANNEL_OVERRIDE
unset SHEETS_SPREADSHEET_ID SHEETS_TAB
unset SNOWFLAKE_ACCOUNT SNOWFLAKE_USER SNOWFLAKE_ROLE SNOWFLAKE_PAT
unset SNOWFLAKE_PRIVATE_KEY SNOWFLAKE_PRIVATE_KEY_PATH
unset SNOWFLAKE_PRIVATE_KEY_PASSPHRASE SNOWFLAKE_WAREHOUSE
unset SNOWFLAKE_DATABASE SNOWFLAKE_SCHEMA

export API_CONCURRENT_BATCHING=1
export API_MAX_ATTEMPTS=20
export API_CONCURRENCY=4
export VLLM_REACT_CONCURRENCY=8
# Adaptive thinking at the same effort as the main run. Thinking tokens share
# the max_tokens budget on the Anthropic API, so raise the cap to 16384 to
# leave the usual 4096 visible-output headroom under high-effort reasoning;
# only text blocks are scored (thinking blocks are never parsed as output).
export ANTHROPIC_THINKING=adaptive
export ANTHROPIC_EFFORT=high
export ANTHROPIC_MAX_TOKENS=16384
export ANTHROPIC_TEMPERATURE=none
export PYTHONPATH=benchmark

limit_args=()
if [[ -n "$recipe_limit" ]]; then
  limit_args=(--limit "$recipe_limit")
fi

"$AGENTORCH_PYTHON" -m evaluation.full_eval \
  --run-name "$run_name" \
  --state-namespace "opus-thinking" \
  --backend simulated \
  --model claude-opus-5 \
  --modes "$modes" \
  --variants all \
  --task-source task_description \
  --tool-surface broad \
  --resume \
  "${limit_args[@]}"
