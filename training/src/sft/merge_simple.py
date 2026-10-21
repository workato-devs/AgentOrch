"""Merge LoRA into a standard (non-wrapper) base model, with no-op guards."""
import argparse, time, torch
from pathlib import Path
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

p = argparse.ArgumentParser()
p.add_argument("--base", required=True)
p.add_argument("--adapter", type=Path, required=True)
p.add_argument("--out", type=Path, required=True)
a = p.parse_args()
t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(a.base, dtype=torch.bfloat16)
peft = PeftModel.from_pretrained(model, a.adapter)
lora_b = [(n, q) for n, q in peft.named_parameters() if "lora_B" in n]
nz_names = [n for n, q in lora_b if q.abs().sum() > 0]
print(f"lora_B nonzero: {len(nz_names)}/{len(lora_b)} "
      f"(zeros are expected for never-routed MoE experts)", flush=True)
assert nz_names, "adapter did not attach (all lora_B zero)"
# sample reference tensors from modules that actually carry nonzero deltas;
# pre-merge the wrapped weight lives at <module>.base_layer.weight, after
# merge_and_unload it is <module>.weight
prefixes = [n.split(".lora_B")[0].replace("base_model.model.", "")
            for n in nz_names[:8]]
base_sd = peft.get_base_model().state_dict()
ref = {}
for m in prefixes:
    for pre_key in (m + ".base_layer.weight", m + ".weight"):
        if pre_key in base_sd:
            ref[m + ".weight"] = base_sd[pre_key].clone()
            break
assert ref, f"could not locate any targeted base weights (sample prefix: {prefixes[:1]})"
merged = peft.merge_and_unload()
sd = merged.state_dict()
checked = sum(1 for k in ref if k in sd)
changed = sum(1 for k in ref if k in sd and not torch.equal(ref[k], sd[k]))
print(f"targeted tensors changed by merge: {changed}/{checked}", flush=True)
assert checked > 0 and changed > 0, "merge was a no-op on adapter-targeted tensors"
merged.save_pretrained(a.out, safe_serialization=True)
AutoTokenizer.from_pretrained(a.base).save_pretrained(a.out)
print(f"done in {time.time()-t0:.0f}s -> {a.out}", flush=True)
