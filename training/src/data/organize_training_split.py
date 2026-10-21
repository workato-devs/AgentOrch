"""Materialise a Plan-SFT export as a recipe-level training split.

Reads an export directory containing ``manifest.json``, ``plan_sft.jsonl`` and
``plan_sft_messages.jsonl`` and writes the same layout the public benchmark
uses for its test split:

  <out>/input/recipes/<recipe_id>/
      PLAN_system.txt        frozen GLOBAL_VIEW system prompt
      PLAN_user.txt          frozen-template user prompt, 64-card tool surface
      TRAINING_PACKAGE.json  structured model-visible input
  <out>/groundtruth/recipes/<recipe_id>/
      golden_trace.json      target golden trace + full row metadata
      PLAN_assistant.txt     serialized target plan (the SFT assistant turn)

The inverse operation (recipe files -> chat-messages JSONL) is
``build_sft_messages.py`` in this directory.

Run:
  python organize_training_split.py --source <export dir> --out training/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

MODEL_SAFE_META_KEYS = (
    "recipe_id",
    "split",
    "planner_prompt_version",
    "task_description_hash",
    "D_hash",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def dump_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def bundle_hash(recipe_dir: Path) -> str:
    lines = [f"{sha256_file(f)}  {f.name}" for f in sorted(recipe_dir.iterdir())]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, required=True,
                        help="export directory with manifest.json, plan_sft.jsonl, "
                             "plan_sft_messages.jsonl")
    parser.add_argument("--out", type=Path, required=True,
                        help="directory that will receive input/ and groundtruth/")
    parser.add_argument("--input-dir-name", default="input",
                        help="name of the input folder under --out (default: input)")
    parser.add_argument("--skip-groundtruth", action="store_true",
                        help="write only the input side (targets are shared across "
                             "data versions)")
    parser.add_argument("--package-schema",
                        default="agentorch-training-planning-package-v1-global-aligned")
    args = parser.parse_args()

    source_manifest_hash = sha256_file(args.source / "manifest.json")
    in_root = args.out / args.input_dir_name
    gt_root = args.out / "groundtruth"

    for root in ([in_root] if args.skip_groundtruth else [in_root, gt_root]):
        d = root / "recipes"
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    recipe_ids = []
    with open(args.source / "plan_sft.jsonl", encoding="utf-8") as sft_f, \
            open(args.source / "plan_sft_messages.jsonl", encoding="utf-8") as msg_f:
        for i, (sft_line, msg_line) in enumerate(zip(sft_f, msg_f)):
            sft = json.loads(sft_line)
            msg = json.loads(msg_line)
            meta = sft["metadata"]
            rid = meta["recipe_id"]
            assert msg["metadata"]["recipe_id"] == rid, f"row {i}: order mismatch"
            recipe_ids.append(rid)

            messages = {m["role"]: m["content"] for m in msg["messages"]}

            in_dir = in_root / "recipes" / rid
            in_dir.mkdir()
            (in_dir / "PLAN_system.txt").write_text(messages["system"], encoding="utf-8")
            (in_dir / "PLAN_user.txt").write_text(messages["user"], encoding="utf-8")
            package = {
                "schema_version": args.package_schema,
                "recipe_id": rid,
                **sft["input"],
                "metadata": {k: meta[k] for k in MODEL_SAFE_META_KEYS if k in meta},
            }
            dump_json(in_dir / "TRAINING_PACKAGE.json", package)

            if not args.skip_groundtruth:
                gt_dir = gt_root / "recipes" / rid
                gt_dir.mkdir()
                (gt_dir / "PLAN_assistant.txt").write_text(messages["assistant"],
                                                           encoding="utf-8")
                gt = {
                    "schema": "agentorch-training-ground-truth",
                    "recipe_id": rid,
                    "golden_trace": sft["target"]["golden_trace"],
                    "metadata": meta,
                }
                dump_json(gt_dir / "golden_trace.json", gt)

            if (i + 1) % 500 == 0:
                print(f"{i + 1} recipes written", flush=True)

    assert len(set(recipe_ids)) == len(recipe_ids)

    common = {
        "task_count": len(recipe_ids),
        "instance_count": len(recipe_ids),
        "training_unit": "one complete recipe-level symbolic workflow per recipe",
        "alignment": "global-mode benchmark-aligned inputs "
                     "(frozen GLOBAL_VIEW template, 64-card tool surface)",
        "source_manifest_hash": source_manifest_hash,
    }
    input_manifest = {
        "schema": "agentorch-training-input",
        **common,
        "recipes": [{"recipe_id": rid} for rid in sorted(recipe_ids)],
    }
    dump_json(in_root / "manifest.json", input_manifest)
    (in_root / "MANIFEST.sha256").write_text(
        f"{sha256_file(in_root / 'manifest.json')}  manifest.json\n")

    if not args.skip_groundtruth:
        print("hashing groundtruth bundles...", flush=True)
        gt_manifest = {
            "schema": "agentorch-training-ground-truth-manifest",
            **common,
            "recipes": [
                {"recipe_id": rid,
                 "groundtruth_bundle_hash": bundle_hash(gt_root / "recipes" / rid)}
                for rid in sorted(recipe_ids)
            ],
        }
        dump_json(gt_root / "manifest.json", gt_manifest)
        (gt_root / "MANIFEST.sha256").write_text(
            f"{sha256_file(gt_root / 'manifest.json')}  manifest.json\n")

    print("done:", len(recipe_ids), "recipes ->", args.out, flush=True)


if __name__ == "__main__":
    main()
