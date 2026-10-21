# Sourced by every training launcher. Resolves the release root, loads the
# site settings and exports the common runtime environment.
#   TRAIN_ROOT      = <release>/training
#   AGENTORCH_ROOT  = <release>
# The launcher must set LAUNCHER_DIR before sourcing this file.
set -euo pipefail
TRAIN_ROOT="$(cd "${LAUNCHER_DIR}" && while [[ ! -d src || ! -d data ]]; do cd ..; done; pwd)"
export TRAIN_ROOT
export AGENTORCH_ROOT="${AGENTORCH_ROOT:-$(dirname "$TRAIN_ROOT")}"
if [[ ! -f "$TRAIN_ROOT/scripts/env.sh" ]]; then
  echo "missing $TRAIN_ROOT/scripts/env.sh: copy scripts/env.sh.example and set your site paths" >&2
  exit 1
fi
source "$TRAIN_ROOT/scripts/env.sh"
mkdir -p "$TRAIN_ROOT/output/logs" "$TRAIN_ROOT/output/checkpoints" "$TRAIN_ROOT/output/rl_checkpoints"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TOKENIZERS_PARALLELISM=false
if [[ -f "$AGENTORCH_ENV_FILE" ]]; then
  # Only WANDB_API_KEY is read from the credential file here; the benchmark
  # evaluator loads its own provider keys when it needs them.
  key="$(grep '^WANDB_API_KEY=' "$AGENTORCH_ENV_FILE" | cut -d= -f2- || true)"
  [[ -n "$key" ]] && export WANDB_API_KEY="$key"
fi
if [[ -z "${WANDB_API_KEY:-}" ]]; then export WANDB_MODE="${WANDB_MODE:-offline}"; fi
