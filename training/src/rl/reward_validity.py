"""Validity-weighted Tier-1 reward for the 27B RL round-2.

Same scoring machinery as reward.py; only the component weights change to
prioritize producing a valid, well-formed plan (the error-rate metric):
  valid 0.15 -> 0.40 | tools 0.25 -> 0.20 | args 0.35 -> 0.25
  struct 0.15 -> 0.10 | exact 0.10 -> 0.05
Goal (2026-08-31, user-approved): push benchmark error_rate below opus
(0.1916) from the RL step-120 model's 0.2224 without giving up orchestration.
"""
import reward as _base

_base.WEIGHTS.clear()
_base.WEIGHTS.update({"valid": 0.40, "tools": 0.20, "args": 0.25,
                      "struct": 0.10, "exact": 0.05})

score_plan = _base.score_plan
compute_score = _base.compute_score

if __name__ == "__main__":
    import json
    golden = {"plan": [{"kind": "call", "tool": "a.b", "arguments": {}, "bind": "x"}]}
    g = json.dumps(golden)
    full = compute_score("t", g, g, None)
    invalid = compute_score("t", "not json", g, None)
    valid_wrong = compute_score("t", json.dumps({"plan": [{"kind": "call", "tool": "c.d", "arguments": {}, "bind": "y"}]}), g, None)
    print("golden:", full, "| invalid:", invalid, "| valid-but-wrong:", valid_wrong)
    assert abs(sum(_base.WEIGHTS.values()) - 1.0) < 1e-9
    fs = full if isinstance(full, float) else full.get("score", full)
    print("weights sum ok")
