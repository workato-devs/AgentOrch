#!/usr/bin/env python3
"""Upload the fine-tuned checkpoints to the Hugging Face Hub with a model card.

Reads training/results/training.csv, and for every distinct checkpoint (or the
subset given with --only / --headline) uploads the merged model directory from
--checkpoints-dir as <org>/agentorch-<model_id>, then writes the resulting repo
id back into a `hf_repo` column of training.csv so the tables stay the record.

Requirements: `pip install huggingface_hub`, `HF_TOKEN` with write access.

  python training/scripts/upload_checkpoints_hf.py --org <org> --headline --dry-run
  python training/scripts/upload_checkpoints_hf.py --org <org> --headline
  python training/scripts/upload_checkpoints_hf.py --org <org> --only sft-27b-80k-3ep rl-gemma26b-step680
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "results" / "training.csv"

CARD = """---
license: {license}
base_model: {base_model}
tags: [agentorch, workflow-orchestration, {kind}]
---

# {repo_name}

{kind_upper} checkpoint from the AgentOrch training project ({family}), evaluated
on the AgentOrch benchmark (Global View, 3,220 variants, frozen harness):

| orchestration accuracy | final accuracy | error rate |
|---:|---:|---:|
| {orch} | {final} | {error} |

Training recipe (from `training/results/training.csv`, row `{model_id}`):
{recipe}

Base model: `{base_model}` at revision `{revision}`. Merged weights (LoRA
folded into the base); load with `transformers` or `vLLM` as a normal
checkpoint. Use `enable_thinking=False` in the chat template, as at training
and evaluation time.

Evaluation run: `{eval_run}`. See the AgentOrch repository for the harness,
the training data and the full experiment record.
"""


def rows() -> list[dict]:
    with open(TABLE, encoding="utf-8") as f:
        header = [line for line in f if line.startswith("#")]
    with open(TABLE, encoding="utf-8") as f:
        data = list(csv.DictReader(line for line in f if not line.startswith("#")))
    return header, data


def recipe(r: dict) -> str:
    parts = []
    if r.get("sft_epochs"):
        parts.append(f"- SFT: {r['sft_data']} data, {r['sft_epochs']} epochs, {r['sft_max_len']}-token budget, "
                     f"LoRA {r['sft_adapter']}, lr {r['sft_lr']}, schedule {r['sft_schedule'] or 'cosine'}")
    if r.get("rl_algo"):
        parts.append(f"- RL: {r['rl_algo']}, reward {r['rl_reward']}, lr {r['rl_lr']}, KL {r['rl_kl']}, "
                     f"group {r['rl_group_n']}, {r['rl_prompts_per_step']} prompts/step, steps {r['rl_steps']}, "
                     f"data {r['rl_data']}, initialised from `{r['init_from']}`")
    return "\n".join(parts) or "- see training.csv"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org", required=True, help="Hugging Face organisation or user")
    ap.add_argument("--checkpoints-dir", type=Path, default=ROOT / "output" / "checkpoints",
                    help="directory holding the merged model folders named as in training.csv")
    ap.add_argument("--headline", action="store_true", help="only rows flagged headline=yes")
    ap.add_argument("--only", nargs="*", default=None, help="explicit model_id list")
    ap.add_argument("--license", default="apache-2.0")
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    header, data = rows()
    pins = {}
    pins_file = ROOT / "src" / "sft" / "base_models.json"
    if pins_file.exists():
        import json
        pins = {k: v.get("revision", "") for k, v in json.loads(pins_file.read_text()).items() if isinstance(v, dict)}

    seen = set()
    targets = []
    for r in data:
        if r["kind"] not in ("sft", "rl") or r["model_id"] in seen:
            continue
        if a.headline and r.get("headline") != "yes":
            continue
        if a.only is not None and r["model_id"] not in a.only:
            continue
        seen.add(r["model_id"])
        targets.append(r)

    if not a.dry_run:
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ.get("HF_TOKEN"))

    repo_of = {}
    for r in targets:
        local = a.checkpoints_dir / r["checkpoint"]
        repo = f"{a.org}/agentorch-{r['model_id']}"
        base = r["base_model"].replace("-FP8", "")
        if base == "Qwen3.8-27B":
            base = "Qwen/Qwen3.8-27B"
        elif base.startswith("Qwen3-4B"):
            base = "Qwen/" + base
        elif base.startswith("gemma-4"):
            base = "google/" + base
        card = CARD.format(license=a.license, base_model=base, kind=r["kind"], kind_upper=r["kind"].upper(),
                           repo_name=repo.split("/")[1], family=r["family"], orch=r["orchestration_accuracy"],
                           final=r["final_accuracy"], error=r["error_rate"], model_id=r["model_id"],
                           recipe=recipe(r), revision=pins.get(base, "see training.csv"), eval_run=r["eval_run"])
        print(f"{'DRY ' if a.dry_run else ''}{r['model_id']:28s} {local} -> {repo}  exists={local.is_dir()}")
        if a.dry_run:
            continue
        if not local.is_dir():
            print(f"  skip: {local} missing")
            continue
        api.create_repo(repo, private=a.private, exist_ok=True)
        (local / "README.md").write_text(card, encoding="utf-8")
        api.upload_folder(folder_path=str(local), repo_id=repo, commit_message=f"AgentOrch {r['model_id']}")
        repo_of[r["model_id"]] = repo

    if repo_of:
        fields = list(data[0].keys())
        if "hf_repo" not in fields:
            fields.append("hf_repo")
        for r in data:
            r.setdefault("hf_repo", "")
            if r["model_id"] in repo_of:
                r["hf_repo"] = repo_of[r["model_id"]]
        with open(TABLE, "w", newline="", encoding="utf-8") as f:
            f.writelines(header)
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)
        print(f"wrote hf_repo for {len(repo_of)} checkpoints into {TABLE}")


if __name__ == "__main__":
    main()
