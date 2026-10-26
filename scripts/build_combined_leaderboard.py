#!/usr/bin/env python3
"""Combine the benchmark table and the training table into one leaderboard.

Sources (both regenerated from archived leaderboard.json files upstream):
  benchmark/results/results.csv   off-the-shelf models, one row per model x mode
  training/results/training.csv   SFT / RL checkpoints from the training project

Every row is renamed  <base model>-<base|sft|rl>[-<variant>]  so a family's
untrained, fine-tuned and RL checkpoints line up by name. Per (base model,
kind, mode) one run is the headline: the one flagged in training.csv, else the
highest orchestration accuracy. Headline rows carry the bare
`<base model>-<kind>` name; the other runs keep their run id as a suffix.

Outputs:
  results/combined_leaderboard.csv   every row
  results/combined_leaderboard.md    headline table + full listing

Run from anywhere:  python scripts/build_combined_leaderboard.py
"""

from __future__ import annotations

import argparse
import csv
import io
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmark" / "results" / "results.csv"
TRAIN = ROOT / "training" / "results" / "training.csv"
OUT_CSV = ROOT / "results" / "combined_leaderboard.csv"
OUT_MD = ROOT / "results" / "combined_leaderboard.md"

METRICS = ("orchestration_accuracy", "final_accuracy", "side_effect_accuracy",
           "execution_trace_accuracy", "terminal_output_accuracy", "error_rate")
COLUMNS = ("name", "base_model", "kind", "variant", "headline", "tier", "mode", "n",
           *METRICS, "training_recipe", "source_table", "source_run")
MODE_ORDER = {"global": 0, "global_input": 1, "local": 2, "react": 3, "replan": 4}
KIND_ORDER = {"base": 0, "sft": 1, "rl": 2}


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        rows = [line for line in f if not line.startswith("#")]
    return list(csv.DictReader(rows))


def fmt(x: str) -> str:
    return f"{float(x):.3f}" if x not in ("", None) else "–"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check generated tables without writing files")
    args = parser.parse_args()
    rows: list[dict] = []

    for r in read_csv(BENCH):
        if r.get("status") not in ("complete", ""):
            continue
        rows.append({
            "name": f"{r['model']}-base", "base_model": r["model"], "kind": "base",
            "variant": "", "headline": "yes", "tier": r["tier"], "mode": r["mode"],
            "n": r["total"], **{m: r[m] for m in METRICS},
            "training_recipe": "", "source_table": "benchmark/results/results.csv",
            "source_run": r["run"],
        })
    base_names = {(r["base_model"], r["mode"]) for r in rows}

    train_rows = [r for r in read_csv(TRAIN) if r["kind"] in ("sft", "rl")]
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in train_rows:
        groups[(r["base_model"], r["kind"], r["mode"])].append(r)
    for (base, kind, mode), members in groups.items():
        flagged = [m for m in members if m.get("headline") == "yes"]
        head = flagged[0] if flagged else max(members, key=lambda m: float(m["orchestration_accuracy"]))
        for m in members:
            is_head = m is head
            recipe = []
            if m.get("sft_epochs"):
                recipe.append(f"SFT {m['sft_data']} data, {m['sft_epochs']} ep, {m['sft_max_len']} ctx, "
                              f"LoRA {m['sft_adapter']}, lr {m['sft_lr']}")
            if m.get("rl_algo"):
                recipe.append(f"{m['rl_algo']}, reward {m['rl_reward']}, lr {m['rl_lr']}, "
                              f"kl {m['rl_kl']}, steps {m['rl_steps']}, init {m['init_from']}")
            rows.append({
                "name": f"{base}-{kind}" if is_head else f"{base}-{kind}-{m['model_id']}",
                "base_model": base, "kind": kind, "variant": m["model_id"],
                "headline": "yes" if is_head else "", "tier": m["tier"], "mode": m["mode"],
                "n": m["n"], **{k: m[k] for k in METRICS},
                "training_recipe": "; ".join(recipe),
                "source_table": "training/results/training.csv", "source_run": m["eval_run"],
            })
        if (base, mode) not in base_names:
            # keep the untrained reference next to its checkpoints even when the
            # benchmark table has no row for that mode
            for m in read_csv(TRAIN):
                if m["kind"] == "base" and m["base_model"] == base and m["mode"] == mode:
                    rows.append({
                        "name": f"{base}-base", "base_model": base, "kind": "base", "variant": "",
                        "headline": "yes", "tier": m["tier"], "mode": mode, "n": m["n"],
                        **{k: m[k] for k in METRICS}, "training_recipe": "",
                        "source_table": "training/results/training.csv", "source_run": m["eval_run"],
                    })
                    base_names.add((base, mode))

    rows.sort(key=lambda r: (r["base_model"].lower(), MODE_ORDER.get(r["mode"], 9),
                             KIND_ORDER[r["kind"]], r["headline"] != "yes",
                             -float(r["orchestration_accuracy"])))

    with io.StringIO(newline="") as f:
        f.write("# generated by scripts/build_combined_leaderboard.py from "
                "benchmark/results/results.csv + training/results/training.csv; "
                "all rows: frozen harness, simulated backend, greedy decoding, "
                "3,220 variants, failed rows score 0\n")
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        csv_bytes = f.getvalue().encode("utf-8")

    # --- markdown ---------------------------------------------------------
    trained_bases = sorted({r["base_model"] for r in rows if r["kind"] != "base"}, key=str.lower)
    md = ["# Combined leaderboard: base / SFT / RL", "",
          "Orchestration accuracy on the AgentOrch benchmark (frozen harness, simulated "
          "backend, greedy decoding, all 3,220 variants; failed rows score 0). Every row is "
          "named `<base model>-<base|sft|rl>`; non-headline training runs carry their run id.",
          "Generated by `scripts/build_combined_leaderboard.py`; the full table is "
          "`combined_leaderboard.csv`.", "",
          "## Headline: models that were fine-tuned", "",
          "| Base model | Mode | base | sft | rl | best trained run |",
          "|---|---|---:|---:|---:|---|"]
    for base in trained_bases:
        modes = sorted({r["mode"] for r in rows if r["base_model"] == base and r["kind"] != "base"},
                       key=lambda m: MODE_ORDER.get(m, 9))
        for mode in modes:
            cell = {}
            best = None
            for kind in ("base", "sft", "rl"):
                hits = [r for r in rows if r["base_model"] == base and r["mode"] == mode
                        and r["kind"] == kind and r["headline"] == "yes"]
                cell[kind] = fmt(hits[0]["orchestration_accuracy"]) if hits else "–"
                if hits and kind != "base" and (best is None or float(hits[0]["orchestration_accuracy"]) > best[0]):
                    best = (float(hits[0]["orchestration_accuracy"]), hits[0]["variant"])
            md.append(f"| {base} | {mode} | {cell['base']} | {cell['sft']} | {cell['rl']} | "
                      f"{best[1] if best else '–'} |")
    md += ["", "## All rows", "",
           "| Name | Mode | Orchestration | Final | Side-effect | Exec-trace | Terminal | Error rate |",
           "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        md.append(f"| {r['name']} | {r['mode']} | {fmt(r['orchestration_accuracy'])} | "
                  f"{fmt(r['final_accuracy'])} | {fmt(r['side_effect_accuracy'])} | "
                  f"{fmt(r['execution_trace_accuracy'])} | {fmt(r['terminal_output_accuracy'])} | "
                  f"{fmt(r['error_rate'])} |")
    outputs = {OUT_CSV: csv_bytes, OUT_MD: ("\n".join(md) + "\n").encode("utf-8")}
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, content in outputs.items()
                 if not path.is_file() or path.read_bytes() != content]
        if stale:
            print("Stale or missing tables: " + ", ".join(stale))
            print("Run: python scripts/build_combined_leaderboard.py")
            return 1
        print(f"{len(rows)} rows: combined leaderboard is up to date")
        return 0
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_bytes(content)
    print(f"{len(rows)} rows -> {OUT_CSV}\n{OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
