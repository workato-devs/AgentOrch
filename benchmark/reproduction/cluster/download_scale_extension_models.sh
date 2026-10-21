#!/bin/bash
# Pre-download the scale-extension checkpoints at their pinned revisions into
# the shared Hugging Face cache. The evaluation jobs run with
# HF_HUB_OFFLINE=1, so every checkpoint must be complete before submission.
# Gated repositories (gemma-3, Llama-3.3-70B, Command R) require the
# HF_TOKEN account to have accepted the model licenses first.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
source "${AGENTORCH_ENV_FILE:-../.env}"  # HF_TOKEN; never in git
set +a
export HF_HOME=${HF_HOME:-$HOME/.cache/huggingface}

python3 - <<'EOF'
import json
from huggingface_hub import snapshot_download

manifest = json.load(open("evaluation/global_react_models.json"))
missing = []
for row in manifest["local_models"]:
    if row.get("status") != "planned":
        continue
    model, revision = row["model"], row["revision"]
    print(f"==> {model} @ {revision[:12]}", flush=True)
    try:
        snapshot_download(
            model,
            revision=revision,
            # Skip non-safetensors duplicates of the weights.
            ignore_patterns=["*.pth", "*.bin", "original/*", "*.gguf"],
        )
    except Exception as exc:
        # Typically a gated repository whose license has not been accepted
        # yet. Keep downloading the rest and report the gaps at the end.
        print(f"    FAILED: {exc}", flush=True)
        missing.append(model)
if missing:
    print("\nNOT DOWNLOADED (accept the license on huggingface.co, then re-run):")
    for model in missing:
        print(f"  - {model}")
    raise SystemExit(1)
print("all planned checkpoints present")
EOF
