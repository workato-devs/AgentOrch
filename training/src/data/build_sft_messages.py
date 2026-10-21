"""Turn the recipe-level training split into a chat-messages JSONL file.

For every recipe in <input>/recipes/<rid>/ and <groundtruth>/recipes/<rid>/ one
row is written:

  {"messages": [{"role": "system",    "content": PLAN_system.txt},
                {"role": "user",      "content": PLAN_user.txt},
                {"role": "assistant", "content": PLAN_assistant.txt}],
   "metadata": {"recipe_id": ..., ...golden_trace.json metadata...},
   "schema_version": "agentorch-plan-sft-v1"}

Rows are written in the original export order (the `row_position` recorded in
each golden_trace.json) and serialized exactly like the export (sorted keys,
compact separators, ASCII-escaped), so the output is byte-identical to the
file the published models were prepared from. It feeds
src/sft/prepare_dataset.py, whose seeded shuffle depends on this order.

Usage (from training/):
  python src/data/build_sft_messages.py                       # v1 -> data/sft_messages_v1.jsonl
(input/ and groundtruth/ come from scripts/download_data.py --only training.
The v2 ablation prompts are not distributed.)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

TRAIN_ROOT = Path(__file__).resolve().parents[2]

# metadata keys carried by the messages export (a subset of golden_trace.json metadata)
MESSAGE_META_KEYS = ("D_hash", "compiler_version", "exporter_version", "golden_trace_hash",
                     "planner_prompt_version", "raw_recipe_sha256", "recipe_id", "row_position",
                     "split", "task_description_hash", "workflow_A_hash")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=TRAIN_ROOT / "input")
    parser.add_argument("--groundtruth", type=Path, default=TRAIN_ROOT / "groundtruth")
    parser.add_argument("--out", type=Path, default=TRAIN_ROOT / "data" / "sft_messages_v1.jsonl")
    args = parser.parse_args()

    manifest = json.loads((args.input / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("schema") == "agentorch-training-input", manifest.get("schema")
    recipe_ids = [r["recipe_id"] for r in manifest["recipes"]]

    # restore the export order: golden_trace.json carries each row's position
    metas = {}
    for rid in recipe_ids:
        gt = json.loads((args.groundtruth / "recipes" / rid / "golden_trace.json").read_text(encoding="utf-8"))
        metas[rid] = gt.get("metadata", {})
    recipe_ids.sort(key=lambda rid: (metas[rid].get("row_position", 1 << 30), rid))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for i, rid in enumerate(recipe_ids):
            in_dir = args.input / "recipes" / rid
            gt_dir = args.groundtruth / "recipes" / rid
            meta = metas[rid]
            row = {
                "messages": [
                    {"role": "system", "content": (in_dir / "PLAN_system.txt").read_text(encoding="utf-8")},
                    {"role": "user", "content": (in_dir / "PLAN_user.txt").read_text(encoding="utf-8")},
                    {"role": "assistant", "content": (gt_dir / "PLAN_assistant.txt").read_text(encoding="utf-8")},
                ],
                "metadata": {k: meta[k] for k in MESSAGE_META_KEYS if k in meta},
                "schema_version": "agentorch-plan-sft-v1",
            }
            f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            if (i + 1) % 500 == 0:
                print(f"{i + 1} rows", flush=True)
    print(f"wrote {len(recipe_ids)} rows -> {args.out}")


if __name__ == "__main__":
    main()
