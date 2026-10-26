"""Export the text-only causal-LM view of a Qwen3_5 wrapper checkpoint.

Drops the vision tower (model.visual.*) and MTP head (mtp.*), which text-only
RL never executes; under FSDP2 those never-forwarded params also trip a torch
2.13 post-backward bug (see training/results/training.csv). AutoModelForCausalLM builds the
model.layers.* text tree directly from the wrapper checkpoint (same load path
the SFT used), so weights are byte-identical to the wrapper's language model.
"""
import argparse, time, torch
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer

p = argparse.ArgumentParser()
p.add_argument("--src", type=Path, required=True)
p.add_argument("--out", type=Path, required=True)
a = p.parse_args()
t0 = time.time()

model = AutoModelForCausalLM.from_pretrained(a.src, dtype=torch.bfloat16)
print(f"loaded {model.__class__.__name__}: "
      f"{sum(x.numel() for x in model.parameters())/1e9:.1f}B params", flush=True)
bad = [n for n, _ in model.named_parameters() if n.startswith(("visual", "mtp", "model.visual", "model.mtp"))]
assert not bad, f"text-only view still holds non-text params: {bad[:3]}"
model.save_pretrained(a.out, safe_serialization=True)
AutoTokenizer.from_pretrained(a.src).save_pretrained(a.out)
for extra in ("generation_config.json", "chat_template.jinja"):
    src = a.src / extra
    if src.exists() and not (a.out / extra).exists():
        (a.out / extra).write_bytes(src.read_bytes())
print(f"done in {time.time()-t0:.0f}s -> {a.out}", flush=True)
