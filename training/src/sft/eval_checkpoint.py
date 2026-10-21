"""Evaluate a LoRA SFT checkpoint on the held-out eval split.

Loads base + adapter on one GPU, greedily generates plans for eval.jsonl
rows (enable_thinking=False, matching training), and reports:
  - json_parse_rate:    reply parses as JSON
  - plan_shape_rate:    top-level {"plan": [...]} object
  - known_tools_rate:   every called tool exists in the prompt's 64-card surface
  - tool_seq_match:     called tool sequence equals the golden plan's
  - exact_match:        canonical JSON equality with the golden plan

Usage (single GPU):
  python eval_checkpoint.py --adapter checkpoints/sft-lora/step-100 --n 30
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

SRC = Path(__file__).resolve().parent
BASE = "Qwen/Qwen3.8-27B"


def plan_tools(nodes, acc):
    for node in nodes:
        if node.get("kind") == "call":
            acc.append(node.get("tool"))
        for key in ("then", "else", "body", "catch"):
            if isinstance(node.get(key), list):
                plan_tools(node[key], acc)
    return acc


def surface_tools(user_prompt: str) -> set:
    section = user_prompt.split("## Available tool contracts\n")[1]
    section = section.split("\n\n## Symbolic value shapes")[0]
    return {card["name"] for card in json.loads(section)}


def extract_json(text: str):
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.index("{")
    return json.loads(text[start:text.rindex("}") + 1])


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE,
                        help="base model id (e.g. Qwen/Qwen3-4B-Instruct-2507)")
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=SRC / "data" / "eval.jsonl")
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--max-new-tokens", type=int, default=6144)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForCausalLM.from_pretrained(
        args.base, dtype=torch.bfloat16, attn_implementation="sdpa",
        device_map="cuda:0")
    model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()

    rows = []
    with open(args.data, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line)["messages"])
            if len(rows) >= args.n:
                break

    counts = {"json_parse": 0, "plan_shape": 0, "known_tools": 0,
              "tool_seq_match": 0, "exact_match": 0}
    records = []
    for i, messages in enumerate(rows):
        prompt = tokenizer.apply_chat_template(
            messages[:-1], add_generation_prompt=True, tokenize=False,
            enable_thinking=False)
        golden = json.loads(messages[-1]["content"])
        inputs = tokenizer(prompt, return_tensors="pt",
                           add_special_tokens=False).to("cuda:0")
        t0 = time.time()
        with torch.no_grad():
            output = model.generate(
                **inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                pad_token_id=tokenizer.eos_token_id)
        reply = tokenizer.decode(output[0][inputs.input_ids.shape[1]:],
                                 skip_special_tokens=True)
        record = {"index": i, "prompt_tokens": int(inputs.input_ids.shape[1]),
                  "gen_tokens": int(output.shape[1] - inputs.input_ids.shape[1]),
                  "seconds": round(time.time() - t0, 1)}
        try:
            plan = extract_json(reply)
            counts["json_parse"] += 1
            if isinstance(plan.get("plan"), list):
                counts["plan_shape"] += 1
                called = plan_tools(plan["plan"], [])
                surface = surface_tools(messages[1]["content"])
                if all(t in surface for t in called):
                    counts["known_tools"] += 1
                golden_called = plan_tools(golden["plan"], [])
                record["called"] = called
                record["golden_called"] = golden_called
                if called == golden_called:
                    counts["tool_seq_match"] += 1
                if canonical(plan) == canonical(golden):
                    counts["exact_match"] += 1
        except (ValueError, json.JSONDecodeError, KeyError) as err:
            record["error"] = f"{type(err).__name__}: {err}"
            record["reply_head"] = reply[:200]
        records.append(record)
        done = i + 1
        print(f"[{done}/{len(rows)}] " +
              " ".join(f"{k}={v}/{done}" for k, v in counts.items()), flush=True)

    out = args.out or (args.adapter / "eval_report.json")
    out.write_text(json.dumps({"counts": counts, "n": len(rows),
                               "records": records}, indent=2) + "\n")
    print("report:", out)


if __name__ == "__main__":
    main()
