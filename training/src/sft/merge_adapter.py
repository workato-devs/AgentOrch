"""Merge a LoRA adapter into the base and produce a full-wrapper model dir.

Two stages, both required because of a module-tree mismatch:
1. Merge on AutoModelForCausalLM — the SAME class used in training, so the
   adapter keys (base_model.model.model.layers.*) actually attach. (Merging
   on the ConditionalGeneration wrapper silently loads NOTHING: its tree is
   model.language_model.layers.* and PEFT's non-strict load zero-fills.)
2. Transplant: serialized text-model keys are remapped by transformers to
   model.language_model.* — identical to the wrapper checkpoint's keys — so
   copy the base wrapper's shards and overwrite every tensor the merge
   changed. Result: full multimodal checkpoint vLLM accepts, with the SFT
   deltas actually present.

The script verifies the merge is not a no-op before writing anything.

Usage:
  python merge_adapter.py --adapter checkpoints/sft-lora/final \
      --out checkpoints/merged-final-fixed
"""

import argparse
import glob
import json
import os
from pathlib import Path
import shutil
import time

import torch
from peft import PeftModel
from safetensors import safe_open
from safetensors.torch import save_file
from transformers import AutoModelForCausalLM

BASE = "Qwen/Qwen3.8-27B"


def base_snapshot(base: str) -> Path:
    """Shard dir of the base: a local model dir, or the HF cache snapshot."""
    if Path(base).is_dir():
        return Path(base)
    hf_home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    pattern = str(hf_home / "hub" / f"models--{base.replace('/', '--')}" / "snapshots" / "*")
    return Path(sorted(glob.glob(pattern))[0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base", default=BASE,
                        help="HF id or local dir; for RL adapters use the merged SFT dir")
    args = parser.parse_args()

    t0 = time.time()
    print(f"[1/3] merging adapter on the training class (text-only)", flush=True)
    model = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.bfloat16)
    peft = PeftModel.from_pretrained(model, args.adapter)
    nonzero = sum(1 for n, p in peft.named_parameters()
                  if "lora_B" in n and p.abs().sum().item() > 0)
    total_b = sum(1 for n, _p in peft.named_parameters() if "lora_B" in n)
    print(f"  lora_B loaded nonzero: {nonzero}/{total_b}", flush=True)
    if nonzero == 0:
        raise RuntimeError("adapter did not attach — refusing to write a no-op merge")
    merged = peft.merge_and_unload()
    merged_sd = merged.state_dict()

    # Serialization remaps text keys to the wrapper namespace; replicate it.
    def to_wrapper_key(key: str) -> str:
        if key.startswith("model."):
            return "model.language_model." + key[len("model."):]
        return key  # lm_head.weight

    remapped = {to_wrapper_key(k): v for k, v in merged_sd.items()}
    print(f"  merged {len(remapped)} tensors at {time.time()-t0:.0f}s", flush=True)

    print("[2/3] transplanting into the full wrapper checkpoint", flush=True)
    snap = base_snapshot(args.base)
    index = json.loads((snap / "model.safetensors.index.json").read_text())
    weight_map = index["weight_map"]
    args.out.mkdir(parents=True, exist_ok=True)
    changed_tensors = 0
    identical_overwrites = 0
    for shard_name in sorted(set(weight_map.values())):
        tensors = {}
        with safe_open(snap / shard_name, "pt") as f:
            for key in f.keys():
                base_t = f.get_tensor(key)
                if key in remapped:
                    new_t = remapped[key].to(base_t.dtype)
                    if not torch.equal(new_t, base_t):
                        changed_tensors += 1
                    else:
                        identical_overwrites += 1
                    tensors[key] = new_t
                else:
                    tensors[key] = base_t
        save_file(tensors, str(args.out / shard_name),
                  metadata={"format": "pt"})
        print(f"  wrote {shard_name}", flush=True)
    (args.out / "model.safetensors.index.json").write_text(json.dumps(index))
    print(f"  tensors changed by merge: {changed_tensors} "
          f"(unchanged overwrites: {identical_overwrites})", flush=True)
    if changed_tensors == 0:
        raise RuntimeError("transplant produced zero changed tensors")

    print("[3/3] copying config/tokenizer/processor files", flush=True)
    for f in snap.iterdir():
        if f.suffix in {".json", ".jinja", ".txt"} and \
                f.name != "model.safetensors.index.json":
            shutil.copy(f, args.out / f.name)
    print(f"done in {time.time()-t0:.0f}s -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
