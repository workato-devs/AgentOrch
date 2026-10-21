#!/bin/bash
#SBATCH --job-name=agentorch-convert
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=400G
#SBATCH --time=4:00:00
#SBATCH --output=output/logs/convert-%j.out
# verl LoRA checkpoint (Qwen3.8 wrapper models) -> benchmark-ready merged model:
#   1. verl.model_merger: FSDP shards -> HF dump + lora_adapter        (>125 GB RAM)
#   2. rewrite adapter keys from the language_model view to the CausalLM view
#   3. src/sft/merge_adapter.py: transplant merge with no-op guards
# Usage (from training/):
#   sbatch src/rl/verl/convert_rl_ckpt.sbatch <run_name> <step> <base_merged_dir> <out_name>
# Result: output/checkpoints/<out_name>
LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LAUNCHER_DIR/../../../scripts/_preamble.sh"
RUN=${1:?run}; STEP=${2:?step}; BASE=${3:?base merged dir}; OUT=${4:?out name}
CKPT_DIR="$TRAIN_ROOT/output/rl_checkpoints/verl"
RAW="$CKPT_DIR/merged_raw/${OUT}-raw"
mkdir -p "$CKPT_DIR/merged_raw"
"$AGENTORCH_RL_PYTHON" -m verl.model_merger merge --backend fsdp \
  --local_dir "$CKPT_DIR/${RUN}/global_step_${STEP}/actor" --target_dir "$RAW"
"$AGENTORCH_TRAIN_PYTHON" - "$RAW" <<'PY'
import json, sys
from pathlib import Path
from safetensors.torch import load_file, save_file
raw = Path(sys.argv[1]); src, dst = raw/"lora_adapter", raw/"lora_adapter_textview"
dst.mkdir(exist_ok=True)
sd = load_file(str(src/"adapter_model.safetensors"))
out = {k.replace("base_model.model.model.language_model.", "base_model.model.model."): v for k, v in sd.items()}
save_file(out, str(dst/"adapter_model.safetensors"), metadata={"format": "pt"})
cfg = json.load(open(src/"adapter_config.json")); cfg["base_model_name_or_path"] = None
json.dump(cfg, open(dst/"adapter_config.json", "w"), indent=2)
print(f"textview adapter: {len(out)} tensors")
PY
"$AGENTORCH_TRAIN_PYTHON" "$TRAIN_ROOT/src/sft/merge_adapter.py" \
  --base "$BASE" \
  --adapter "$RAW/lora_adapter_textview" \
  --out "$TRAIN_ROOT/output/checkpoints/${OUT}"
rm -rf "$RAW"/model-*.safetensors   # the full HF dump is not needed once merged
echo "CONVERT DONE ${OUT}"
