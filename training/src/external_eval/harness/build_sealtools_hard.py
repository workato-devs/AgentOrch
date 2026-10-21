"""Build a harder Seal-Tools variant: 64 retriever-style hard negatives.

Why this exists. The upstream `dataset_for_finetune` prompts carry only ~5
candidate APIs, not the advertised 4,076 -- they are already retrieved.
Untrained base models score F1_api ~0.98 against a 0.998 gold ceiling, on the
`difficult` subset too, so the split cannot show whether training transferred
any tool-*selection* ability.

FAILED FIRST ATTEMPT, recorded so nobody repeats it. v1 of this script padded
each prompt to 64 tools with distractors sampled uniformly at random from the
catalogue. That made the task *easier*, not harder: base-qwen4b out-domain
went 0.9845 -> 0.9912. Measured cause -- 15.5% of upstream's 5 candidates
share the gold API's `field` (they are hard negatives), while only 0.1% of
uniformly-sampled distractors do. Burying one correct API among 59 tools from
unrelated domains makes it the only plausible answer. Difficulty here is set
by distractor *similarity*, not distractor count.

v2 (this script) therefore selects distractors the way a retriever would: rank
the whole catalogue by TF-IDF cosine similarity against the task instruction
alone -- never against the gold, so no label leaks -- and take the top-scoring
non-gold tools. That is the realistic deployment setting (an agent sees what
its retriever returned) and it is the setting upstream's own DPR training
targets.

Reported as "Seal-Tools (64 retrieved candidates, derived)". It is NOT the
upstream protocol; keep the 5-candidate numbers for comparability.

Run: python3 harness/build_sealtools_hard.py
"""

from __future__ import annotations

import ast
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEAL = ROOT / "seal_tools" / "Seal-Tools_Dataset"
OUT = ROOT / "tasks"
SURFACE = 64

HEADER = (
    'Please chooose the needed apis and return api_calling list according to '
    'the task_instruction.\nOutput format: [{"api": "", "parameters": {"": ""}, '
    '"responses": ["API_call_0","API_call_1"]},{"api": "", "parameters": {"": ""}, '
    '"responses": ["API_call_2"]}]\nResponses can be used as parameter value. '
    "The number of responses depends on information in api_list.\n\nInput:\n"
)

TOKEN_RE = re.compile(r"[A-Za-z][a-z]+|[A-Z]{2,}|\d+")


def tokenize(text: str) -> list[str]:
    """Split on non-alpha and camelCase, lowercase."""
    return [t.lower() for t in TOKEN_RE.findall(text)]


def load_catalog() -> list[dict]:
    tools = []
    for line in (SEAL / "tool.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            tools.append(json.loads(line))
    return tools


def build_index(tools: list[dict]) -> tuple[list[dict], list[str]]:
    """TF-IDF vectors over 'api_name + description + field' per tool."""
    docs = [tokenize(f"{t['api_name']} {t.get('api_description','')} {t.get('field','')}")
            for t in tools]
    df: Counter = Counter()
    for doc in docs:
        df.update(set(doc))
    n = len(docs)
    idf = {w: math.log((n + 1) / (c + 1)) + 1.0 for w, c in df.items()}
    vecs = []
    for doc in docs:
        tf = Counter(doc)
        v = {w: (1 + math.log(c)) * idf.get(w, 0.0) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs, idf


def rank(query: str, vecs: list[dict], idf: dict, tools: list[dict]) -> list[int]:
    q_tf = Counter(tokenize(query))
    qv = {w: (1 + math.log(c)) * idf.get(w, 0.0) for w, c in q_tf.items()}
    norm = math.sqrt(sum(x * x for x in qv.values())) or 1.0
    qv = {w: x / norm for w, x in qv.items()}
    scores = []
    for i, v in enumerate(vecs):
        s = 0.0
        if len(qv) < len(v):
            for w, x in qv.items():
                y = v.get(w)
                if y:
                    s += x * y
        else:
            for w, y in v.items():
                x = qv.get(w)
                if x:
                    s += x * y
        scores.append((s, i))
    scores.sort(key=lambda p: (-p[0], tools[p[1]]["api_name"]))
    return [i for _, i in scores]


def build(split: str, tools: list[dict], vecs, idf) -> list[dict]:
    by_name = {t["api_name"]: t for t in tools}
    src = json.loads((SEAL / "dataset_for_finetune" / f"{split}.json").read_text(encoding="utf-8"))
    rows = []
    for rec in src:
        conv = rec["conversations"]
        human = next(t["value"] for t in conv if t["from"] == "human")
        gold = next(t["value"] for t in conv if t["from"] == "gpt")
        idx = human.find("task_instruction =")
        if idx == -1:
            continue
        tail = human[idx:]
        instruction = tail.split("=", 1)[1].strip()

        try:
            gold_names = []
            for call in ast.literal_eval(gold):
                name = call.get("api")
                if name and name not in gold_names:
                    gold_names.append(name)
        except Exception:
            continue
        known = [n for n in gold_names if n in by_name]
        gold_set = set(gold_names)

        # Retriever's view: rank by the instruction only. Gold never enters
        # the query, so nothing about the answer leaks into the candidates.
        ordered = rank(instruction, vecs, idf, tools)
        distractors = []
        for i in ordered:
            name = tools[i]["api_name"]
            if name in gold_set:
                continue
            distractors.append(name)
            if len(distractors) >= SURFACE - len(known):
                break

        surface = sorted(set(known) | set(distractors))
        api_list = [by_name[n] for n in surface]
        user = HEADER + "api_list = " + repr(api_list) + "\n" + tail
        rows.append({
            "task_id": rec["id"],
            "bench": "sealtools",
            "split": f"{split}_64",
            "system": "",
            "user": user,
            "gold": gold,
            "meta": {
                "difficulty": "easy" if "easy" in rec["id"] else "difficult",
                "n_candidates": len(api_list),
                "n_gold_apis": len(gold_names),
                "n_gold_in_catalog": len(known),
            },
        })
    return rows


def field_overlap(rows: list[dict], by_name: dict) -> float:
    """Fraction of distractors sharing a gold API's exact field."""
    same = tot = 0
    for r in rows:
        try:
            gold = {c["api"] for c in ast.literal_eval(r["gold"])}
        except Exception:
            continue
        gf = {by_name[n].get("field") for n in gold if n in by_name}
        for name in re.findall(r"'api_name': '([^']+)'", r["user"]):
            if name in gold:
                continue
            tot += 1
            if by_name.get(name, {}).get("field") in gf:
                same += 1
    return 100 * same / max(tot, 1)


def main() -> None:
    tools = load_catalog()
    by_name = {t["api_name"]: t for t in tools}
    print(f"catalogue: {len(tools)} tools; building TF-IDF index...")
    vecs, idf = build_index(tools)
    for split in ("test_in_domain", "test_out_domain"):
        rows = build(split, tools, vecs, idf)
        path = OUT / f"sealtools_{split}_64.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        lens = sorted(len(r["user"]) for r in rows)
        print(f"  {path.name}: {len(rows)} rows, prompt chars "
              f"p50={lens[len(lens)//2]} max={lens[-1]}, "
              f"distractors sharing gold field: {field_overlap(rows, by_name):.1f}% "
              f"(upstream 5-candidate: 15.5%, random-64: 0.1%)")


if __name__ == "__main__":
    main()
