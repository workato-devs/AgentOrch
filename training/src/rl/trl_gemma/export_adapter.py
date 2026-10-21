"""Convert a TRL/accelerate FSDP2 sharded checkpoint (checkpoint-N/pytorch_model_fsdp_0,
torch DCP format, LoRA params only) into a standard PEFT adapter directory that
merge_simple.py can consume.

Usage: python export_adapter.py --ckpt checkpoints/<run>/checkpoint-180 --base <merged base> --out <adapter dir>
"""
import argparse, json, re
from pathlib import Path
import torch
from safetensors.torch import save_file
from torch.distributed.checkpoint.format_utils import dcp_to_torch_save

p = argparse.ArgumentParser()
p.add_argument("--ckpt", type=Path, required=True)
p.add_argument("--base", required=True)
p.add_argument("--out", type=Path, required=True)
p.add_argument("--r", type=int, default=16)
p.add_argument("--alpha", type=int, default=32)
a = p.parse_args()

a.out.mkdir(parents=True, exist_ok=True)
tmp = a.out / "full_state.pt"
dcp_to_torch_save(str(a.ckpt / "pytorch_model_fsdp_0"), str(tmp))
sd = torch.load(tmp, map_location="cpu", weights_only=False)
if "model" in sd and isinstance(sd["model"], dict):
    sd = sd["model"]
lora = {k: v for k, v in sd.items() if "lora_" in k and "language_model" in k}
dropped = sum(1 for k in sd if "lora_" in k and "language_model" not in k)
print(f"non-text lora tensors dropped (audio/vision towers, inert for text RL): {dropped}", flush=True)
assert lora, f"no lora_ keys; sample keys: {list(sd)[:5]}"
# PEFT adapter keys: base_model.model.<module>.lora_A.weight (no adapter name)
out_sd, modules = {}, set()
for k, v in lora.items():
    k2 = re.sub(r"\.lora_(A|B)\.default\.", r".lora_\1.", k)
    if not k2.startswith("base_model.model."):
        k2 = "base_model.model." + k2
    out_sd[k2] = v.detach().to(torch.bfloat16).contiguous()
    m = re.sub(r"\.lora_(A|B)\.weight$", "", k2).replace("base_model.model.", "")
    modules.add(m)  # full module path: PEFT matches exact/suffix, so suffix-only
    # names (e.g. "proj") would also grab same-named Gemma4ClippableLinear modules
nz = sum(1 for k, v in out_sd.items() if "lora_B" in k and v.abs().sum() > 0)
nb = sum(1 for k in out_sd if "lora_B" in k)
print(f"lora tensors: {len(out_sd)} | lora_B nonzero: {nz}/{nb} | target module names: {sorted(modules)}", flush=True)
assert nz > 0, "all lora_B are zero — adapter never trained"
save_file(out_sd, str(a.out / "adapter_model.safetensors"), metadata={"format": "pt"})
cfg = {
    "peft_type": "LORA", "task_type": "CAUSAL_LM", "base_model_name_or_path": a.base,
    "r": a.r, "lora_alpha": a.alpha, "lora_dropout": 0.0, "bias": "none",
    "target_modules": sorted(modules), "inference_mode": True,
}
(a.out / "adapter_config.json").write_text(json.dumps(cfg, indent=2))
tmp.unlink()
print(f"adapter written -> {a.out}", flush=True)
