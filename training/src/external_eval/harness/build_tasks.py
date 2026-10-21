"""Materialise the external benchmarks into one normalised task format.

Each output row is:
    {"task_id", "bench", "split", "system", "user", "gold", "meta"}

`system`/`user` hold *content only*. Rendering through a model's own chat
template happens in generate.py, so every checkpoint sees the prompt in the
format it was trained to read. The upstream WorkflowLLM prompt hard-codes
Llama-3 special tokens; reproducing those verbatim for a Qwen or gemma model
would measure tokenizer mismatch rather than orchestration ability, so only
the prompt *text* is carried over (byte-identical wording).

Run:  python3 harness/build_tasks.py
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WFB = ROOT / "workflowllm" / "data"
SEAL = ROOT / "seal_tools" / "Seal-Tools_Dataset" / "dataset_for_finetune"
OUT = ROOT / "tasks"

# Verbatim from workflowllm/code/code/utils_for_llm.py::format_instruction_with_code
WFB_SYSTEM = (
    "You are a very helpful AI assistant who can write corresponding Python "
    "main code based on user's query and usable Python function interface."
)
WFB_USER = """Please generate python main code based on the following query :
 {query}
You can start by using natural language to plan your tool call strategy, and then generate the complete code. For example, `Thought:\\n<tool call strategy>\\n\\nCode:\\n```python\\n<main code>\\n````.
Note that your output should always include `Code:\\n```python\\n<main code>\\n````, formatted accordingly.
Here are some useful function interface you may use:
 {apis_desc}"""


def _write(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  wrote {len(rows):5d} rows -> {path.relative_to(ROOT)}")


def build_workflowbench() -> None:
    seed = json.loads((WFB / "seed_data.json").read_text(encoding="utf-8"))
    stat = pickle.loads((WFB / "statistics.pkl").read_bytes())
    id2py = pickle.loads((WFB / "identifier2python.pkl").read_bytes())
    id_split = json.loads((WFB / "dataset_split_keys.json").read_text())
    ood_split = json.loads((WFB / "dataset_split_keys_ood.json").read_text())

    by_key = {rec["key"]: rec for rec in seed}

    def make(split_name: str, keys: list[str]) -> list[dict]:
        rows = []
        for key in keys:
            rec = by_key.get(key)
            if rec is None:
                continue
            # Upstream: sample['apis'] when present, else stat[key]['action_names'].
            # action_names is a *set* upstream and is joined straight into the
            # prompt, so upstream API ordering differs run to run. Sorted here
            # so a prompt is byte-reproducible; content is unchanged.
            names = rec.get("apis") or (stat.get(key) or {}).get("action_names") or []
            names = sorted(names)
            descs = [id2py.get(n.replace(".", "_")) for n in names]
            descs = [d for d in descs if d is not None]
            if not descs:
                continue  # no resolvable API docs -> prompt would be degenerate
            rows.append({
                "task_id": key,
                "bench": "workflowbench",
                "split": split_name,
                "system": WFB_SYSTEM,
                "user": WFB_USER.format(query=rec["query"], apis_desc="\n".join(descs)),
                "gold": rec.get("workflow_code", ""),
                "meta": {
                    "gold_thought": rec.get("task_plan", ""),
                    "apis": names,
                    "n_apis": len(names),
                    "type": (stat.get(key) or {}).get("type", "NA"),
                    "depth": (stat.get(key) or {}).get("depth"),
                    "num_nodes": (stat.get(key) or {}).get("num_nodes"),
                },
            })
        return rows

    print("workflowbench:")
    # ID: unseen instructions. `test` is the clean held-out split — upstream's
    # own training script validates on `dev`, so `dev` is model-selection data.
    _write(make("id_test", id_split["test"]), OUT / "workflowbench_id_test.jsonl")
    # OOD: unseen APIs. Only train/dev exist upstream; dev is the eval split.
    _write(make("ood_dev", ood_split["dev"]), OUT / "workflowbench_ood_dev.jsonl")


def build_sealtools() -> None:
    print("seal_tools:")
    for split in ("test_in_domain", "test_out_domain"):
        data = json.loads((SEAL / f"{split}.json").read_text(encoding="utf-8"))
        rows = []
        for rec in data:
            conv = rec["conversations"]
            human = next(t["value"] for t in conv if t["from"] == "human")
            gpt = next(t["value"] for t in conv if t["from"] == "gpt")
            rows.append({
                "task_id": rec["id"],
                "bench": "sealtools",
                "split": split,
                # Upstream prompt is a single user turn with the instruction
                # and api_list inlined; there is no system message.
                "system": "",
                "user": human,
                "gold": gpt,
                "meta": {"difficulty": "easy" if "easy" in rec["id"] else "difficult"},
            })
        _write(rows, OUT / f"sealtools_{split}.jsonl")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    build_workflowbench()
    build_sealtools()
