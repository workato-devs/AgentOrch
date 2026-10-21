"""Re-execute Global View (plan_execute) scoring from cached frozen plans.

Every frozen-plan artifact stores the model's raw response and the decoding
fingerprint that keyed it. This driver replays those artifacts through the
canonical evaluator without any model access: the evaluator re-adjudicates
each cached response under the current plan validator, executes the surviving
plans on every hidden variant with the simulated connector backend, and
writes results plus a leaderboard exactly as an online run would.

Any recipe whose artifact is missing would require a real model call; the
offline client refuses, and that recipe is recorded as an error row.

Usage:
    PYTHONPATH=benchmark python -m reproduction.offline.rescore_frozen_plans \
        --run-name <run> --model claude-opus-5

The run directory outputs/full_eval/<run>/plans/<model>/ must already hold
the frozen-plan artifacts (copied from the run that generated them).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PUBLIC_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PUBLIC_ROOT))


class OfflineClient:
    """A model client that can only serve cache hits.

    The frozen-plan cache key covers the decoding fingerprint of the client
    that generated it, so this stub carries the fingerprint recorded in the
    cached artifacts and raises on any attempt to sample the model.
    """

    calls = 0
    total_tokens = 0

    def __init__(self, model: str, decoding: dict) -> None:
        self.model = model
        for key, value in decoding.items():
            setattr(self, key, value)

    def complete(self, *args, **kwargs):
        raise RuntimeError(
            "offline rescoring cannot sample the model; a frozen-plan "
            "artifact is missing for this recipe"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--model", required=True, help="model id, e.g. claude-opus-5 or hf:Qwen/Qwen2.5-32B-Instruct")
    parser.add_argument("--limit", type=int, default=0, help="restrict to the first N recipes (smoke test)")
    parser.add_argument("--state-namespace", default=None)
    args = parser.parse_args(argv)

    import evaluation.full_eval as full_eval

    safe_model = args.model.replace("/", "__").replace(":", "_")
    namespace = args.state_namespace or f"rescore-{safe_model[:48]}"
    full_eval._configure(args.run_name, "simulated", namespace)

    plans_root = (
        PUBLIC_ROOT / "outputs/full_eval" / args.run_name / "plans" / safe_model
    )
    artifacts = sorted(plans_root.glob("*/initial_plan.json"))
    if not artifacts:
        raise SystemExit(f"no frozen-plan artifacts under {plans_root}")
    sample = json.loads(artifacts[0].read_text(encoding="utf-8"))
    if sample.get("model") != args.model:
        raise SystemExit(
            f"artifact model {sample.get('model')!r} does not match --model {args.model!r}"
        )
    decoding = (sample.get("cache_key_payload") or {}).get("decoding") or {}

    import task.llm_client as llm_client

    llm_client.build_client = lambda model: OfflineClient(model, decoding)

    from task.run_eval import main as canonical_main

    recipe_ids = full_eval._recipe_ids()
    if args.limit:
        recipe_ids = recipe_ids[: args.limit]
    return canonical_main([
        "--model", args.model,
        "--modes", "plan_execute",
        "--variants", "all",
        "--task-source", "task_description",
        "--tool-surface", "broad",
        "--resume",
        "--ids", *recipe_ids,
    ])


if __name__ == "__main__":
    raise SystemExit(main())
