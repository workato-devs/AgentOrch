"""Build VERL GRPO parquet datasets from the aligned training rows.

Each row: prompt = [system, user] chat messages (VERL applies the model's
chat template at rollout), ground_truth = golden plan JSON (consumed by
rl/reward.py:compute_score), extra_info = recipe id + token stats.

Selection: rows are filtered by prompt length (rollout cost) and target
length (must be scorable under the 4096 decode cap), then the shortest
--n prompts are taken for throughput, shuffled deterministically.

Usage:
  python make_rl_dataset.py --n 1000 --out ../../../data/rl_verl_v1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

import pandas as pd

TRAIN_ROOT = Path(__file__).resolve().parents[3]
DATA = TRAIN_ROOT / "data"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA / "sft_v1_80k" / "train.jsonl")
    parser.add_argument("--eval-data", type=Path,
                        default=DATA / "sft_v1_80k" / "eval.jsonl")
    parser.add_argument("--out", type=Path, default=DATA / "rl_verl_v1")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--max-prompt-chars", type=int, default=260_000,
                        help="~65k tokens; caps rollout prefill cost")
    parser.add_argument("--max-target-chars", type=int, default=16_000,
                        help="~4k tokens; scorable under the decode cap")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    def rows_from(path: Path):
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                messages = json.loads(line)["messages"]
                prompt_chars = sum(len(m["content"]) for m in messages[:-1])
                target = messages[-1]["content"]
                if prompt_chars > args.max_prompt_chars:
                    continue
                if len(target) > args.max_target_chars:
                    continue
                out.append((prompt_chars, messages))
        return out

    train_rows = sorted(rows_from(args.data), key=lambda r: r[0])[:args.n]
    random.Random(args.seed).shuffle(train_rows)
    eval_rows = sorted(rows_from(args.eval_data), key=lambda r: r[0])[:64]

    def records(rows, split):
        recs = []
        for i, (prompt_chars, messages) in enumerate(rows):
            golden = messages[-1]["content"]
            recs.append({
                "data_source": "agentorch_plan",
                "prompt": messages[:-1],
                "ability": "workflow_planning",
                "reward_model": {"style": "rule", "ground_truth": golden},
                "extra_info": {"split": split, "index": i,
                               "prompt_chars": prompt_chars},
            })
        return recs

    args.out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records(train_rows, "train")).to_parquet(args.out / "train.parquet")
    pd.DataFrame(records(eval_rows, "eval")).to_parquet(args.out / "eval.parquet")
    print(f"train: {len(train_rows)} rows | eval: {len(eval_rows)} rows -> {args.out}")
    lens = [c for c, _ in train_rows]
    print(f"prompt chars: min {min(lens)} median {sorted(lens)[len(lens)//2]} "
          f"max {max(lens)}")


if __name__ == "__main__":
    main()
