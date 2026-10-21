"""Build the length-filtered SFT files from the chat-messages export.

Reads data/sft_messages_v1.jsonl (built by src/data/build_sft_messages.py,
OpenAI chat-messages format) and writes:

  <out>/train.jsonl   rows whose total tokens fit --max-context
  <out>/eval.jsonl    held-out slice for Fireworks' evaluation loss curve
  <out>/prep_report.json  counts, token totals, and cost estimate

Rows longer than --max-context are DROPPED, not truncated: the assistant
target sits at the end of the sequence, so a truncated row would train on
input with no (or partial) target.

Usage:
  python prepare_dataset.py                           # 80k prep (headline runs)
  python prepare_dataset.py --max-context 65536 --out ../../data/sft_v1_64k
  python prepare_dataset.py --limit 8 --eval-rows 0   # smoke-test slice
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from common import DATA_ROOT, SFT_MESSAGES_V1, SFT_PRICE_PER_M, make_token_counter, row_tokens


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SFT_MESSAGES_V1)
    parser.add_argument("--out", type=Path, default=DATA_ROOT / "sft_v1_80k")
    parser.add_argument("--max-context", type=int, default=81_920,
                        help="token budget per row; longer rows are dropped")
    parser.add_argument("--token-margin", type=float, default=0.98,
                        help="keep rows only up to margin*max_context (exact "
                             "Qwen counting; headroom covers chat-template "
                             "wrapper tokens only)")
    parser.add_argument("--eval-rows", type=int, default=60,
                        help="rows held out into eval.jsonl (0 disables)")
    parser.add_argument("--limit", type=int, default=0,
                        help="cap total rows for a smoke test (0 = all)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--epochs", type=float, default=1.0,
                        help="epochs used for the cost estimate only")
    args = parser.parse_args()

    count, counter_name = make_token_counter()
    budget = int(args.max_context * args.token_margin)

    kept, dropped = [], []
    with open(args.source, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            tokens = row_tokens(row["messages"], count)
            entry = (row["metadata"]["recipe_id"], tokens)
            if tokens <= budget:
                kept.append((row, tokens))
            else:
                dropped.append(entry)

    rng = random.Random(args.seed)
    rng.shuffle(kept)
    if args.limit:
        kept = kept[:args.limit]
    eval_n = min(args.eval_rows, max(len(kept) - 1, 0))
    eval_rows, train_rows = kept[:eval_n], kept[eval_n:]

    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train.jsonl", train_rows), ("eval.jsonl", eval_rows)):
        path = args.out / name
        if not rows:
            path.unlink(missing_ok=True)
            continue
        with open(path, "w", encoding="utf-8") as f:
            for row, _tokens in rows:
                f.write(json.dumps({"messages": row["messages"]},
                                   ensure_ascii=False) + "\n")

    train_tokens = sum(t for _, t in train_rows)
    report = {
        "source": str(args.source),
        "token_counter": counter_name,
        "max_context": args.max_context,
        "row_budget_tokens": budget,
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "dropped_over_budget": len(dropped),
        "dropped_recipe_ids": sorted(rid for rid, _ in dropped),
        "train_tokens": train_tokens,
        "eval_tokens": sum(t for _, t in eval_rows),
        "epochs_for_estimate": args.epochs,
        "estimated_cost_usd": {
            tier: round(train_tokens * args.epochs * price / 1e6, 2)
            for tier, price in SFT_PRICE_PER_M.items()
        },
    }
    (args.out / "prep_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"train: {len(train_rows)} rows, {train_tokens:,} tokens "
          f"({counter_name})")
    print(f"eval:  {len(eval_rows)} rows | dropped over {budget:,} tokens: "
          f"{len(dropped)}")
    est = report["estimated_cost_usd"]["16.1B-80B"]
    print(f"estimated SFT cost @ $3/M (16.1B-80B tier, e.g. qwen3p5-27b), "
          f"{args.epochs} epoch(s): ${est:,.2f}")
    print(f"report: {args.out / 'prep_report.json'}")


if __name__ == "__main__":
    main()
