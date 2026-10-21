"""Shared recipe-run command; variants provide only context construction."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Callable

from .config import OUTPUT_DIR, output_file, seed_file, variant_label, verify_file
from .context import RecipeContext
from .recipe_store import load_raw_recipe
from .recipes import RUNNERS

ContextBuilder = Callable[[dict], RecipeContext]


STRUCTURAL_TERMINAL_TOOLS = {
    "workato_genie.workflow_return_result",
    "workato_recipe_function.return_result",
}


def canonical_persisted_result(result: dict) -> dict:
    """Exclude structural recipe returns from the orchestration call trace.

    The raw executor and verifier still observe these calls.  WorkflowPlanV1
    compiles the corresponding Stage-1 ``terminal_result`` node as ``return``,
    however, so the canonical artifact must not present it as a model-selected
    tool action.
    """

    persisted = deepcopy(result)
    tool_calls = persisted.get("tool_calls") or []
    structural_calls = [
        call
        for call in tool_calls
        if str(call.get("tool") or "") in STRUCTURAL_TERMINAL_TOOLS
    ]
    if not structural_calls:
        return persisted
    persisted["tool_calls"] = [
        call
        for call in tool_calls
        if str(call.get("tool") or "") not in STRUCTURAL_TERMINAL_TOOLS
    ]
    persisted["harness_tool_calls"] = [
        *(persisted.get("harness_tool_calls") or []),
        *structural_calls,
    ]
    persisted["allowed_tools"] = [
        tool
        for tool in persisted.get("allowed_tools") or []
        if str(tool) not in STRUCTURAL_TERMINAL_TOOLS
    ]
    persisted["tool_specs"] = [
        spec
        for spec in persisted.get("tool_specs") or []
        if str(spec.get("name") or "") not in STRUCTURAL_TERMINAL_TOOLS
    ]
    details = persisted.setdefault("details", {})
    details["structural_terminal_calls"] = structural_calls
    details["orchestration_trace_policy"] = (
        "terminal_result_is_structural_return_not_model_tool_action"
    )
    return persisted


def run_recipe(
    recipe_id: str,
    selected_seed_file: Path,
    build_context: ContextBuilder,
) -> dict:
    if recipe_id not in RUNNERS:
        raise KeyError(f"recipe {recipe_id} is not registered")
    raw = load_raw_recipe(recipe_id)
    seed = json.loads(selected_seed_file.read_text())
    if seed.get("recipe_id") != recipe_id:
        raise ValueError(f"seed file recipe_id mismatch: {selected_seed_file}")
    ctx = build_context(seed)
    return RUNNERS[recipe_id](raw, seed, ctx)


def main(build_context: ContextBuilder) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("recipe_id")
    parser.add_argument("--variant", type=int)
    parser.add_argument("--seed-file", type=Path)
    args = parser.parse_args()
    if args.seed_file is not None:
        # Benchmark-local rule: replay only from this repo's output tree, not
        # from arbitrary filesystem paths.
        seed_root = (OUTPUT_DIR / str(args.recipe_id)).resolve()
        if not args.seed_file.resolve().is_relative_to(seed_root):
            parser.error(f"--seed-file must live under {seed_root}")
    selected_seed_file = args.seed_file or seed_file(
        args.recipe_id, variant_label(args.variant)
    )
    if not selected_seed_file.exists():
        parser.error(
            "seed file does not exist: %s\n"
            "Run seed first:\n"
            "  PYTHONPATH=src python3 -m benchmark.seed_recipe %s"
            % (selected_seed_file, args.recipe_id)
        )
    result = run_recipe(args.recipe_id, selected_seed_file, build_context)
    seed = json.loads(selected_seed_file.read_text())
    variant = seed.get("variant_label")
    out_path = output_file(args.recipe_id, variant)
    verify_path = verify_file(args.recipe_id, variant)
    # Validate the complete result before touching artifacts: a failed run
    # must never overwrite the last known-good output with partial content.
    verifier = result.get("verifier")
    print(json.dumps(result, indent=2, sort_keys=True))
    if (
        not isinstance(verifier, dict)
        or result.get("ok") is not True
        or verifier.get("ok") is not True
    ):
        return 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    persisted_result = canonical_persisted_result(result)
    for path, payload in ((out_path, persisted_result), (verify_path, verifier)):
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        tmp.replace(path)
    return 0
