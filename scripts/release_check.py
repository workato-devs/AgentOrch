#!/usr/bin/env python3
"""Automated release check for the AgentOrch community tree.

Run from anywhere:  python scripts/release_check.py [--smoke] [--write-checksums]

During development, --allow-incomplete-metadata reports a missing LICENSE or
CITATION.cff without failing. Never use that option for the publication gate.

Checks (all offline, no model, CPU only):
  1. dataset cardinality and manifests: 650 test recipes / 3,220 variants,
     3,000 training recipes in input/ and groundtruth/, MANIFEST.sha256 files
     match their manifest.json (skipped with a note on a fresh clone that has
     only the sample recipe; fetch the rest with scripts/download_data.py)
  2. training-data lineage: data/sft_v1_80k/prep_report.json is consistent with
     the source manifest (rows, budget); optional byte check of
     data/sft_messages_v1.jsonl against source_manifest_v1.json when present
  3. result tables parse and the combined leaderboard regenerates identically
  4. no personal paths, site-specific node names or credentials in tracked
     code/docs and non-ignored local additions
  5. every relative link in Markdown documentation resolves
  6. community-health files and publication blockers
  7. --smoke: the scripted self-test (example adapter, global + react), one
     connector-runner cycle and the vendored evaluator tests
  8. --write-checksums: SHA256SUMS over tracked files and non-ignored local
     additions (downloaded data is covered by scripts/data_release.json)
Exit status is non-zero when any check fails.
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
    if not data_downloaded():
        note("full data not downloaded (sample recipe only); run: python scripts/download_data.py")
        return
    d = check_manifest_pair(BENCH / "input", 650, "benchmark/input")
    if d:
        n_var = sum(len(r.get("variant_ids") or r.get("variants") or []) for r in d["recipes"])
        if n_var and n_var != 3220:
            fail(f"benchmark/input: {n_var} variant ids, expected 3220")
        elif n_var:
            ok("benchmark/input: 3,220 variant ids")
    gt = BENCH / "groundtruth" / "recipes"
    n_gt = sum(1 for _ in gt.glob("*/variant_*.json")) if gt.is_dir() else 0
    (ok if n_gt == 3220 else fail)(f"benchmark/groundtruth: {n_gt} variant files (expect 3220)")
    for sub in ("input", "groundtruth"):
        check_manifest_pair(TRAIN / sub, 3000, f"training/{sub}")
    test_ids = {p.name for p in (BENCH / "input" / "recipes").iterdir()}
    train_ids = {p.name for p in (TRAIN / "input" / "recipes").iterdir()}
    (ok if not (test_ids & train_ids) else fail)(f"train/test recipe overlap: {len(test_ids & train_ids)}")


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


PERSONAL = re.compile(
    r"/home/[a-z]+/|" + "jess" + r"eliu|zijie|3ugenz|3ugr9d|"
    r"sk-[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{30,}|"
    r"(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
KNOWN_PERSONAL_MARKERS = ("jess" + "eliu", "cs." + "unc.edu")
# intentional public identifiers, not leaked identities: the Hugging Face namespace,
# the GitHub repository, and the paper's corresponding-author address
ALLOWED_PUBLIC_IDS = re.compile(
    r"jess" + r"eliu/agentorch-[a-z0-9.-]+|github\.com/jess" + r"eliu0913/AgentOrch|jess" + r"eliu@cs\.unc\.edu",
    re.IGNORECASE)
CODE_EXT = {".py", ".sh", ".sbatch", ".md", ".json", ".yaml", ".yml", ".txt", ".csv", ".ipynb", ".example", ".patch"}
# frozen fixtures (recipe data carries synthetic organisation e-mails) and this script's own pattern
SKIP_PERSONAL = ("benchmark/groundtruth/", "benchmark/verification/", "benchmark/input/",
                 "benchmark/results/validation_checks/simulator_replay_mismatches.csv",
                 "scripts/release_check.py")


def check_personal() -> None:
    print("[4] personal paths / credentials")
    hits = []
    frozen_hits = []
    for p in repository_files():
        if not p.is_file() or p.suffix not in CODE_EXT:
            continue
        rel = str(p.relative_to(ROOT))
        if any(part in IGNORED_DIRS for part in p.parts):
            continue
        if p.stat().st_size > 20_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if not rel.startswith(SKIP_PERSONAL):
            for m in PERSONAL.finditer(ALLOWED_PUBLIC_IDS.sub("", text)):
                hits.append(f"{rel}: {m.group(0)}")
                if len(hits) > 20:
                    break
        lowered = ALLOWED_PUBLIC_IDS.sub("", text).lower()
        for marker in KNOWN_PERSONAL_MARKERS:
            if marker in lowered:
                frozen_hits.append(f"{rel}: {marker}")
    (ok if not hits else fail)(f"{len(hits)} personal/credential references in code and docs")
    for h in hits[:20]:
        print(f"        {h}")
    (ok if not frozen_hits else fail)(f"{len(frozen_hits)} known personal-identity references in frozen fixtures")
    for h in frozen_hits[:20]:
        print(f"        {h}")


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


def check_community_health(require_publication_metadata: bool) -> None:
    print("[6] community health / publication metadata")
    required = ("README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
                "SUPPORT.md", "DATA_CARD.md", "THIRD_PARTY_NOTICES.md")
    missing = [name for name in required if not (ROOT / name).is_file()]
    (ok if not missing else fail)(f"community-health files: {'complete' if not missing else 'missing ' + ', '.join(missing)}")
    license_path = ROOT / "LICENSE"
    citation_path = ROOT / "CITATION.cff"
    metadata = {
        "LICENSE": license_path.is_file() and license_path.stat().st_size >= 100,
        "CITATION.cff": citation_path.is_file()
        and all(field in citation_path.read_text(encoding="utf-8")
                for field in ("cff-version:", "title:", "authors:")),
    }
    for name, valid in metadata.items():
        message = f"publication metadata: {name} {'present' if valid else 'missing or incomplete'}"
        if valid:
            ok(message)
        elif require_publication_metadata:
            fail(message)
        else:
            note(message)
    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    large_tracked = [rel for rel in tracked.decode().split("\0")
                     if rel and (ROOT / rel).is_file() and (ROOT / rel).stat().st_size >= 50_000_000]
    (ok if not large_tracked else fail)(
        f"large files: {'no tracked file >= 50 MB (data is on the Hugging Face Hub)' if not large_tracked else ', '.join(large_tracked)}")


def check_smoke() -> None:
    output_root = BENCH / "outputs"
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-check-", dir=output_root) as temporary:
        _check_smoke(Path(temporary))


def _check_smoke(output_dir: Path) -> None:
    print("[7] smoke: scripted self-test, connector runner, vendored tests")
    env = {**os.environ, "PYTHONPATH": str(BENCH), "PYTHONDONTWRITEBYTECODE": "1"}
    run = output_dir.name
    for mode in ("global", "react"):
        r = subprocess.run([sys.executable, "-m", "examples.smoke_adapter.eval", "--mode", mode, "--adapter",
                            "examples.smoke_adapter.example_adapter:build", "--model-id", "smoke-test", "--run-name", run,
                            "--recipe-id", "64112882", "--limit", "1"], cwd=ROOT, env=env, capture_output=True, text=True)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        good = r.returncode == 0 and '"n": 1' in last
        (ok if good else fail)(f"smoke adapter --mode {mode}: {'n=1 scored' if good else r.stderr[-300:]}")
    r = subprocess.run([sys.executable, "-m", "verification.connector_runner", "--backend", "simulated",
                        "--recipe-id", "64112882", "--variant", "0", "--output-dir", str(output_dir / "connector")], cwd=ROOT, env=env, capture_output=True, text=True)
    good = r.returncode == 0 and '"verifier_ok": true' in r.stdout
    (ok if good else fail)(f"connector_runner simulated 64112882/00: {'verifier_ok' if good else r.stderr[-300:]}")
    env2 = {**env, "PYTHONPATH": f"{BENCH}/verification/backends/simulated/src:{BENCH}/verification/backends/shared/src"}
    r = subprocess.run([sys.executable, "-m", "pytest", "verification/backends/shared/src/tests", "-q", "-x", "-p", "no:cacheprovider"],
                       cwd=BENCH, env=env2, capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
    (ok if r.returncode == 0 else fail)(f"vendored evaluator tests: {tail}")


def write_checksums() -> None:
    print("[8] SHA256SUMS")
    out = ROOT / "SHA256SUMS"
    skip_names = {"SHA256SUMS", ".env", "sft_messages_v1.jsonl", "sft_messages_v2.jsonl"}
    files = []
    for p in repository_files():
        if p.name in skip_names or p.name.startswith(".env."):
            continue
        files.append(p)
    files.sort()
    with open(out, "w", encoding="utf-8") as f:
        for p in files:
            f.write(f"{sha256(p)}  {p.relative_to(ROOT).as_posix()}\n")
    ok(f"{len(files)} files hashed -> SHA256SUMS (verify with: sha256sum -c SHA256SUMS)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--write-checksums", action="store_true")
    ap.add_argument("--allow-incomplete-metadata", action="store_true",
                    help="do not fail for missing LICENSE/CITATION.cff (development only)")
    a = ap.parse_args()
    check_data(); check_lineage(); check_tables(); check_personal(); check_links()
    check_community_health(not a.allow_incomplete_metadata)
    if a.smoke:
        check_smoke()
    if a.write_checksums:
        write_checksums()
    print(f"\n{'PASS' if not FAILS else 'FAIL'}: {len(FAILS)} failing check(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
