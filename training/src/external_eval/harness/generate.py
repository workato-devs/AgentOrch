"""Batch-generate one model's answers for one external-benchmark task file.

Deliberately standalone: it does not import the AgentOrch evaluation package,
so nothing about our own harness (WorkflowPlan validators, JSON-stop logits
processors, simulator state) can leak into an external measurement.

Greedy decoding, seed 0, each model's own chat template. Resumable: an
existing generations.jsonl is read back and only missing task_ids are run.

Usage:
  python3 harness/generate.py --model-dir <path> --model-id <name> \
      --task tasks/workflowbench_id_test.jsonl [--limit N] [--tp 1]
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Generation caps. WorkflowBench targets are code (p90 ~3.1k tokens); 4096
# matches the visible-output cap the AgentOrch benchmark uses, so a model is
# not given more room here than it gets at home. Seal-Tools targets are short
# JSON call lists (p90 ~180 tokens).
MAX_NEW = {"workflowbench": 4096, "sealtools": 1024}


def load_tasks(path: Path, limit: int | None) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows[:limit] if limit else rows


def render(tokenizer, row: dict) -> str:
    messages = []
    if row["system"]:
        messages.append({"role": "system", "content": row["system"]})
    messages.append({"role": "user", "content": row["user"]})
    kwargs = {"tokenize": False, "add_generation_prompt": True}
    # Qwen3 templates emit a thinking channel unless told otherwise; the
    # AgentOrch runs disable it, so match that here.
    try:
        return tokenizer.apply_chat_template(messages, enable_thinking=False, **kwargs)
    except TypeError:
        return tokenizer.apply_chat_template(messages, **kwargs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--task", required=True, nargs="+",
                    help="one or more task files; all share a single engine load")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tp", type=int, default=int(os.environ.get("VLLM_TENSOR_PARALLEL", "1")))
    ap.add_argument("--max-model-len", type=int, default=16384)
    ap.add_argument("--gpu-util", type=float, default=0.90)
    ap.add_argument("--out-root", default=str(ROOT / "runs"))
    args = ap.parse_args()

    # Plan every split first, so a fully-cached model skips the engine load.
    plans = []
    for task_arg in args.task:
        tasks = load_tasks(Path(task_arg), args.limit)
        bench, split = tasks[0]["bench"], tasks[0]["split"]
        out_dir = Path(args.out_root) / f"{bench}_{split}" / args.model_id
        out_dir.mkdir(parents=True, exist_ok=True)
        gen_path = out_dir / "generations.jsonl"
        done: set[str] = set()
        if gen_path.exists():
            for line in gen_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    done.add(json.loads(line)["task_id"])
        todo = [t for t in tasks if t["task_id"] not in done]
        print(f"[{args.model_id}] {bench}/{split}: {len(tasks)} tasks, "
              f"{len(done)} done, {len(todo)} to run", flush=True)
        plans.append({"bench": bench, "split": split, "out_dir": out_dir,
                      "gen_path": gen_path, "tasks": tasks, "todo": todo})

    if not any(p["todo"] for p in plans):
        print(f"[{args.model_id}] nothing to do", flush=True)
        return 0

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    tokenizer = AutoTokenizer.from_pretrained(args.model_dir, trust_remote_code=True)
    llm = LLM(
        model=args.model_dir,
        tokenizer=args.model_dir,
        dtype="bfloat16",
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_util,
        tensor_parallel_size=args.tp,
        trust_remote_code=True,
        enable_prefix_caching=True,
        seed=0,
    )

    for plan in plans:
        if not plan["todo"]:
            continue
        bench, split, todo = plan["bench"], plan["split"], plan["todo"]
        max_new = MAX_NEW[bench]
        params = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=max_new, seed=0)
        prompts = [render(tokenizer, t) for t in todo]
        started = time.time()
        outputs = llm.generate(prompts, params)
        elapsed = time.time() - started

        n_trunc = 0
        with plan["gen_path"].open("a", encoding="utf-8") as fh:
            for task, out in zip(todo, outputs):
                comp = out.outputs[0]
                n_trunc += int(comp.finish_reason == "length")
                fh.write(json.dumps({
                    "task_id": task["task_id"],
                    "bench": bench,
                    "split": split,
                    "model_id": args.model_id,
                    "response": comp.text,
                    "finish_reason": comp.finish_reason,
                    "n_prompt_tokens": len(out.prompt_token_ids or []),
                    "n_completion_tokens": len(comp.token_ids or []),
                }, ensure_ascii=False) + "\n")

        (plan["out_dir"] / "meta.json").write_text(json.dumps({
            "model_id": args.model_id,
            "model_dir": args.model_dir,
            "bench": bench,
            "split": split,
            "n_tasks": len(plan["tasks"]),
            "n_generated_this_run": len(todo),
            "n_truncated_this_run": n_trunc,
            "max_new_tokens": max_new,
            "max_model_len": args.max_model_len,
            "tensor_parallel": args.tp,
            "decoding": "greedy(temperature=0, top_p=1, seed=0)",
            "chat_template": "model's own, enable_thinking=False where supported",
            "elapsed_seconds": round(elapsed, 1),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }, indent=2), encoding="utf-8")

        print(f"[{args.model_id}] {bench}/{split} done in {elapsed/60:.1f} min, "
              f"{n_trunc}/{len(todo)} hit the length cap", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
