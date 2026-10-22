#!/usr/bin/env python3
"""Download the AgentOrch data that is not stored in this Git repository.

The GitHub tree ships code, docs, results and one sample recipe (64112882) so
the smoke test runs right after cloning. The full benchmark fixtures, the
training recipes and the prepared training files live on the Hugging Face Hub:

  JesseLiu/agentorch-benchmark   source/*.tar.gz  -> benchmark/input, groundtruth, verification
  JesseLiu/agentorch-training    source/*.tar.gz  -> training/input, training/groundtruth
                                 sft_*/ rl_*/      -> training/data/ (prepared SFT / RL files)

Usage (from anywhere):
  python scripts/download_data.py                  # benchmark + training recipes
  python scripts/download_data.py --only benchmark # benchmark fixtures only
  python scripts/download_data.py --prepared       # also fetch training/data/*
  python scripts/download_data.py --verify-only    # re-check already-downloaded archives

Archives are verified against scripts/data_release.json before extraction and
unpack to their original paths, so no code path changes. Requires
`pip install huggingface_hub`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = json.loads((ROOT / "scripts" / "data_release.json").read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract(archive: Path, dest: Path, allowed: list[str]) -> int:
    n = 0
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar.getmembers():
            name = Path(m.name)
            if name.is_absolute() or ".." in name.parts or not (m.isfile() or m.isdir()):
                raise SystemExit(f"refusing unsafe member {m.name!r} in {archive.name}")
            if not any(m.name == a or m.name.startswith(a.rstrip("/") + "/") for a in allowed):
                raise SystemExit(f"unexpected path {m.name!r} in {archive.name}")
        tar.extractall(dest)
        n = sum(1 for m in tar.getmembers() if m.isfile())
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=["benchmark", "training"], help="fetch one group only")
    ap.add_argument("--prepared", action="store_true", help="also fetch prepared SFT/RL files into training/data/")
    ap.add_argument("--cache-dir", type=Path, default=None, help="Hugging Face cache directory")
    ap.add_argument("--verify-only", action="store_true", help="verify cached archives without extracting")
    a = ap.parse_args()

    try:
        from huggingface_hub import hf_hub_download, snapshot_download
    except ImportError:
        print("install huggingface_hub first: pip install huggingface_hub", file=sys.stderr)
        return 1

    for group, spec in RELEASE["archives"].items():
        if a.only and group != a.only:
            continue
        for item in spec["files"]:
            print(f"[{group}] {item['path']} ({item['bytes'] / 1e6:.0f} MB)")
            local = Path(hf_hub_download(spec["repo_id"], item["path"], repo_type="dataset",
                                         revision=spec.get("revision"), cache_dir=a.cache_dir))
            got = sha256(local)
            if got != item["sha256"]:
                print(f"  sha256 MISMATCH: {got} != {item['sha256']}", file=sys.stderr)
                return 1
            print("  sha256 ok")
            if not a.verify_only:
                n = safe_extract(local, ROOT, item["contains"])
                print(f"  extracted {n} files -> {', '.join(item['contains'])}")

    if a.prepared and not a.verify_only and a.only in (None, "training"):
        prep = RELEASE["prepared"]
        print(f"[prepared] {prep['repo_id']} -> training/data/")
        snapshot_download(prep["repo_id"], repo_type="dataset", revision=prep.get("revision"),
                          allow_patterns=prep["allow_patterns"], local_dir=ROOT / "training" / "data",
                          cache_dir=a.cache_dir)

    print("done. Check the tree with: python scripts/check_repository.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
