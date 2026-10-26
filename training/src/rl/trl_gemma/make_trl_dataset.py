"""Build TRL GRPO jsonl datasets from the aligned v1 training rows.

Each output row: {"prompt": [system, user] chat messages, "golden": golden
plan JSON string}. TRL applies the model's chat template at rollout; "golden"
rides along as an extra dataset column and reaches the reward function as a
kwarg. Selection mirrors rl/make_rl_dataset.py: drop rows whose target can't
fit the 4096 decode cap, take the --n shortest prompts, shuffle
deterministically.

Usage:
  python make_trl_dataset.py --n 1000 --out ../../../data/rl_trl_1000
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

TRAIN_ROOT = Path(__file__).resolve().parents[3]
DATA = TRAIN_ROOT / "data"


def load_rows(path: Path, cap_chars: int) -> list[tuple[int, list, str]]:
    out = []
    for line in path.read_text().splitlines():
        msgs = json.loads(line)["messages"]
        prompt = [m for m in msgs if m["role"] != "assistant"]
        golden = next(m["content"] for m in msgs if m["role"] == "assistant")
        # ~4 chars/token: keep targets scorable under the 4096 decode cap
        if len(golden) > 4096 * 4:
            continue
        chars = sum(len(m["content"]) for m in prompt)
        if chars > cap_chars:
            continue
        out.append((chars, prompt, golden))
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=DATA / "sft_v1_80k" / "train.jsonl")
    p.add_argument("--eval-data", type=Path, default=DATA / "sft_v1_80k" / "eval.jsonl")
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--n-eval", type=int, default=24)
    p.add_argument("--max-prompt-chars", type=int, default=260_000,
                   help="~65k gemma tokens; caps rollout prefill cost")
    p.add_argument("--out", type=Path, default=DATA / "rl_trl_1000")
    a = p.parse_args()

    selected = []
    for src, n, name in [(a.data, a.n, "train"), (a.eval_data, a.n_eval, "eval")]:
        rows = sorted(load_rows(src, a.max_prompt_chars), key=lambda r: r[0])
        if len(rows) < n:
            raise ValueError(
                f"{name}: requested {n} prompts, but only {len(rows)} fit the configured limits"
            )
        rows = rows[:n]
        random.Random(7).shuffle(rows)
        selected.append((name, rows))
    a.out.mkdir(parents=True, exist_ok=True)
    for name, rows in selected:
        with (a.out / f"{name}.jsonl").open("w") as f:
            for chars, prompt, golden in rows:
                f.write(json.dumps({"prompt": prompt, "golden": golden}) + "\n")
        lens = [r[0] for r in rows]
        print(f"{name}: {len(rows)} rows | prompt chars min {min(lens)} "
              f"median {sorted(lens)[len(lens)//2]} max {max(lens)}", flush=True)


if __name__ == "__main__":
    main()
