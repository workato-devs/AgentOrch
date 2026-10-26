#!/usr/bin/env python3
"""Check AgentOrch datasets, result tables, documentation, and sample execution.

Run from the repository root: python scripts/check_repository.py [--smoke]

Checks run offline on a CPU. Dataset counts and training lineage are checked
when those datasets are downloaded. The --smoke option exercises the shipped
sample workflow and evaluator tests without calling a model.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark"
TRAIN = ROOT / "training"
IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".venv", "outputs", "output", ".git", "wandb"}
FAILS: list[str] = []


def repository_files() -> list[Path]:
    """Include local additions, excluding ignored data, outputs and caches."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    return sorted({ROOT / os.fsdecode(rel) for rel in result.stdout.split(b"\0")
                   if rel and (ROOT / os.fsdecode(rel)).is_file()})


def fail(msg: str) -> None:
    FAILS.append(msg)
    print(f"  FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"  ok    {msg}")


def note(msg: str) -> None:
    print(f"  note  {msg}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest_pair(root: Path, expect: int, label: str) -> None:
    manifest = root / "manifest.json"
    if not manifest.is_file():
        fail(f"{label}: missing {manifest}"); return
    data = json.loads(manifest.read_text(encoding="utf-8"))
    recipes = data.get("recipes") or []
    n_dirs = sum(1 for p in (root / "recipes").iterdir() if p.is_dir()) if (root / "recipes").is_dir() else 0
    if len(recipes) != expect or n_dirs != expect:
        fail(f"{label}: manifest lists {len(recipes)} recipes, {n_dirs} folders, expected {expect}")
    else:
        ok(f"{label}: {expect} recipes")
    pin = root / "MANIFEST.sha256"
    if pin.is_file():
        want = pin.read_text().split()[0]
        got = sha256(manifest)
        (ok if want == got else fail)(f"{label}: MANIFEST.sha256 {'matches' if want == got else 'MISMATCH'}")
    return data


def data_downloaded() -> bool:
    recipes = BENCH / "input" / "recipes"
    return recipes.is_dir() and sum(1 for p in recipes.iterdir() if p.is_dir()) > 1


def check_data() -> None:
    print("[1] cardinality and manifests")
    benchmark_present = data_downloaded()
    if benchmark_present:
        data = check_manifest_pair(BENCH / "input", 650, "benchmark/input")
        if data:
            variants = sum(len(row.get("variant_ids") or []) for row in data["recipes"])
            (ok if variants == 3220 else fail)(f"benchmark/input: {variants} variant ids (expect 3220)")
        count = sum(1 for _ in (BENCH / "groundtruth/recipes").glob("*/variant_*.json"))
        (ok if count == 3220 else fail)(f"benchmark/groundtruth: {count} variant files (expect 3220)")
    else:
        note("full benchmark data not downloaded; checking the included sample in --smoke")
    train_recipes = TRAIN / "input/recipes"
    training_present = train_recipes.is_dir() and any(train_recipes.iterdir())
    if training_present:
        for group in ("input", "groundtruth"):
            check_manifest_pair(TRAIN / group, 3000, f"training/{group}")
    else:
        note("training recipes not downloaded; skipping training cardinality")
    if benchmark_present and training_present:
        test_ids = {p.name for p in (BENCH / "input/recipes").iterdir() if p.is_dir()}
        train_ids = {p.name for p in train_recipes.iterdir() if p.is_dir()}
        overlap = len(test_ids & train_ids)
        (ok if overlap == 0 else fail)(f"train/test recipe overlap: {overlap}")


def check_lineage() -> None:
    print("[2] training-data lineage")
    src = json.loads((TRAIN / "data" / "source_manifest_v1.json").read_text())
    report = TRAIN / "data" / "sft_v1_80k" / "prep_report.json"
    if not report.is_file():
        note("prepared training files not downloaded; run: python scripts/download_data.py --prepared")
        return
    rep = json.loads(report.read_text())
    total = rep["train_rows"] + rep["eval_rows"] + rep["dropped_over_budget"]
    (ok if total == src["row_count"] else fail)(
        f"sft_v1_80k rows {rep['train_rows']}+{rep['eval_rows']}+{rep['dropped_over_budget']} = {total} (source {src['row_count']})")
    for name in ("train.jsonl", "eval.jsonl"):
        n = sum(1 for _ in open(TRAIN / "data" / "sft_v1_80k" / name, encoding="utf-8"))
        want = rep["train_rows" if name == "train.jsonl" else "eval_rows"]
        (ok if n == want else fail)(f"sft_v1_80k/{name}: {n} rows (report {want})")
    msgs = TRAIN / "data" / "sft_messages_v1.jsonl"
    want = src["outputs"]["plan_sft_messages.jsonl"]["sha256"]
    if msgs.is_file():
        got = sha256(msgs)
        (ok if got == want else fail)(f"sft_messages_v1.jsonl sha256 {'matches' if got == want else 'MISMATCH vs'} source manifest")
    else:
        ok("sft_messages_v1.jsonl not present (regenerate with src/data/build_sft_messages.py to verify)")


def check_tables() -> None:
    print("[3] result tables")
    for t in (BENCH / "results" / "results.csv", TRAIN / "results" / "training.csv"):
        with open(t, encoding="utf-8") as f:
            rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
        (ok if rows else fail)(f"{t.relative_to(ROOT)}: {len(rows)} rows")
    for lb in (BENCH / "results" / "leaderboards", TRAIN / "results" / "leaderboards"):
        bad = 0
        for p in lb.glob("*.json"):
            try:
                json.loads(p.read_text())
            except Exception:
                bad += 1
        (ok if not bad else fail)(f"{lb.relative_to(ROOT)}: {len(list(lb.glob('*.json')))} files, {bad} unparsable")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_combined_leaderboard.py"), "--check"],
        capture_output=True, text=True,
    )
    (ok if result.returncode == 0 else fail)("results/combined_leaderboard.* regenerate identically")
    if result.returncode:
        print(result.stdout or result.stderr)


CREDENTIAL = re.compile(
    r"sk-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{30,}|"
    r"(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
CODE_EXT = {".py", ".sh", ".sbatch", ".md", ".json", ".yaml", ".yml", ".txt", ".csv", ".ipynb", ".example", ".patch"}


def check_credentials() -> None:
    print("[4] credentials")
    hits = []
    for path in repository_files():
        if path.suffix not in CODE_EXT or path == Path(__file__).resolve():
            continue
        if path.stat().st_size > 20_000_000:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        if CREDENTIAL.search(content):
            hits.append(str(path.relative_to(ROOT)))
    (ok if not hits else fail)(f"{len(hits)} files with possible credentials")
    for rel in hits:
        print(f"        {rel}")


LINK = re.compile(r"\]\(([^)#\s]+)(#[^)]*)?\)")
SKIP_LINKS = ("benchmark/verification/dataset/", "benchmark/input/", "training/input/")


def check_links() -> None:
    print("[5] Markdown links")
    bad = []
    for md in (p for p in repository_files() if p.suffix == ".md"):
        if any(part in IGNORED_DIRS for part in md.parts):
            continue
        rel = str(md.relative_to(ROOT))
        if rel.startswith(SKIP_LINKS):
            continue
        for m in LINK.finditer(md.read_text(encoding="utf-8")):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:")) or target.startswith("<"):
                continue
            if not (md.parent / target).exists():
                bad.append(f"{md.relative_to(ROOT)} -> {target}")
    (ok if not bad else fail)(f"{len(bad)} broken relative links")
    for b in bad:
        print(f"        {b}")


def check_documentation() -> None:
    print("[6] project documentation")
    required = ("README.md", "benchmark/README.md", "training/README.md", "DATA_CARD.md")
    missing = [name for name in required if not (ROOT / name).is_file()]
    (ok if not missing else fail)(
        "project guides present" if not missing else "missing guides: " + ", ".join(missing))


def check_smoke() -> None:
    output_root = BENCH / "outputs/full_eval"
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="benchmark-check-", dir=output_root) as temporary:
        _check_smoke(Path(temporary))


def _check_smoke(output_dir: Path) -> None:
    print("[7] smoke: canonical evaluator, connector runner, evaluator tests")
    env = {**os.environ, "PYTHONPATH": str(BENCH), "PYTHONDONTWRITEBYTECODE": "1"}
    run = output_dir.name
    r = subprocess.run(
        [sys.executable, "-m", "evaluation.full_eval", "--run-name", run,
         "--backend", "simulated", "--model", "scripted-gold",
         "--modes", "plan_execute,react", "--ids", "64112882",
         "--variants", "0", "--scripted-selftest"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    (ok if r.returncode == 0 else fail)(
        "canonical Global / Step-by-Step sample: " +
        ("completed" if r.returncode == 0 else r.stderr[-300:]))
    r = subprocess.run([sys.executable, "-m", "verification.connector_runner", "--backend", "simulated",
                        "--recipe-id", "64112882", "--variant", "0", "--output-dir", str(output_dir / "connector")], cwd=ROOT, env=env, capture_output=True, text=True)
    good = r.returncode == 0 and '"verifier_ok": true' in r.stdout
    (ok if good else fail)(f"connector_runner simulated 64112882/00: {'verifier_ok' if good else r.stderr[-300:]}")
    env2 = {**env, "PYTHONPATH": f"{BENCH}/verification/backends/simulated/src:{BENCH}/verification/backends/shared/src"}
    r = subprocess.run([sys.executable, "-m", "pytest", "verification/backends/shared/src/tests", "-q", "-x", "-p", "no:cacheprovider"],
                       cwd=BENCH, env=env2, capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
    (ok if r.returncode == 0 else fail)(f"vendored evaluator tests: {tail}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    check_data(); check_lineage(); check_tables(); check_credentials(); check_links()
    check_documentation()
    if a.smoke:
        check_smoke()
    print(f"\n{'PASS' if not FAILS else 'FAIL'}: {len(FAILS)} failing check(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
