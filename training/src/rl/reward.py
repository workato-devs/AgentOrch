"""GRPO reward for AgentOrch plan generation (Tier 1: symbolic matching).

Dense deterministic reward in [0, 1] comparing a sampled plan against the
recipe's golden plan (deterministic canonical compilation). Components:

  valid    (0.15)  reply parses to {"plan":[...]}
  tools    (0.25)  LCS similarity of the flattened call-tool sequences
  args     (0.35)  exact canonical-argument match over LCS-aligned calls
  struct   (0.15)  control-node kind-sequence similarity
  exact    (0.10)  canonical JSON equality bonus

Signature follows VERL's custom reward interface (compute_score). Pure CPU,
~ms per call. Tier 2 (fixture-replay execution against the recipe's 5
recorded variants) will replace `args`/`exact` with execution equivalence.
"""

from __future__ import annotations

import json
import re

WEIGHTS = {"valid": 0.15, "tools": 0.25, "args": 0.35, "struct": 0.15,
           "exact": 0.10}


def _extract_json(text: str):
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object")
    return json.loads(text[start:end + 1])


def _walk(nodes, calls, kinds):
    for node in nodes:
        if not isinstance(node, dict):
            continue
        kind = node.get("kind")
        kinds.append(kind)
        if kind == "call":
            calls.append((node.get("tool"),
                          json.dumps(node.get("arguments"), sort_keys=True,
                                     separators=(",", ":"))))
        for key in ("then", "else", "body", "catch"):
            child = node.get(key)
            if isinstance(child, list):
                _walk(child, calls, kinds)
    return calls, kinds


def _lcs_pairs(a, b):
    """Length + aligned index pairs of the LCS of two sequences."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = (dp[i + 1][j + 1] + 1 if a[i] == b[j]
                        else max(dp[i + 1][j], dp[i][j + 1]))
    pairs = []
    i = j = 0
    while i < n and j < m:
        if a[i] == b[j]:
            pairs.append((i, j))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return dp[0][0], pairs


def _seq_sim(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    length, _ = _lcs_pairs(a, b)
    return 2.0 * length / (len(a) + len(b))


def score_plan(solution_str: str, golden: dict) -> dict:
    parts = {k: 0.0 for k in WEIGHTS}
    try:
        candidate = _extract_json(solution_str)
        plan = candidate.get("plan")
        if not isinstance(plan, list):
            raise ValueError("no plan list")
    except (ValueError, json.JSONDecodeError):
        return {"score": 0.0, **parts}
    parts["valid"] = 1.0

    g_calls, g_kinds = _walk(golden.get("plan") or [], [], [])
    c_calls, c_kinds = _walk(plan, [], [])
    g_tools = [t for t, _ in g_calls]
    c_tools = [t for t, _ in c_calls]
    parts["tools"] = _seq_sim(c_tools, g_tools)
    parts["struct"] = _seq_sim(c_kinds, g_kinds)

    if g_calls:
        _, pairs = _lcs_pairs(c_tools, g_tools)
        matched_args = sum(1 for ci, gi in pairs
                           if c_calls[ci][1] == g_calls[gi][1])
        parts["args"] = matched_args / len(g_calls)
    else:
        parts["args"] = 1.0 if not c_calls else 0.0

    if json.dumps(candidate, sort_keys=True) == json.dumps(golden, sort_keys=True):
        parts["exact"] = 1.0

    return {"score": sum(WEIGHTS[k] * v for k, v in parts.items()), **parts}


def compute_score(data_source: str, solution_str: str, ground_truth,
                  extra_info=None) -> float:
    """VERL custom reward entry point."""
    if isinstance(ground_truth, str):
        ground_truth = json.loads(ground_truth)
    return score_plan(solution_str, ground_truth)["score"]


if __name__ == "__main__":
    from pathlib import Path
    eval_file = Path(__file__).resolve().parents[2] / "data" / "sft_v1_80k" / "eval.jsonl"
    rows = [json.loads(l) for l in open(eval_file)][:20]
    perfect = corrupt = trunc = 0.0
    for row in rows:
        golden = json.loads(row["messages"][-1]["content"])
        gs = json.dumps(golden)
        perfect += score_plan(gs, golden)["score"]
        bad = gs.replace('"kind"', '"knd"', 3)
        corrupt += score_plan(bad, golden)["score"]
        trunc += score_plan(gs[:len(gs) // 2], golden)["score"]
    n = len(rows)
    print(f"golden-vs-golden mean: {perfect/n:.3f} (expect 1.0)")
    print(f"corrupted-keys mean:   {corrupt/n:.3f} (expect low-mid)")
    print(f"truncated mean:        {trunc/n:.3f} (expect ~0)")
