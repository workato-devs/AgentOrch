"""Seed and execute one recipe using a vendored connector backend."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .backend import DATASET_ROOT, OUTPUT_ROOT, activate


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def execute(
    backend: str,
    recipe_id: str,
    variant: int,
    *,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    runtime_root = (output_dir or OUTPUT_ROOT / backend).resolve()
    activate(backend, output_dir=runtime_root)

    from benchmark.run_recipe import run_recipe
    from benchmark.seed_recipe import load_variant_input, seed_recipe

    variant_file = (
        DATASET_ROOT
        / "input_recipes"
        / str(recipe_id)
        / f"variant_{variant:02d}"
        / "input.json"
    )
    if not variant_file.is_file():
        raise FileNotFoundError(f"unknown recipe variant: {variant_file}")
    variant_input = load_variant_input(str(recipe_id), variant, variant_file)
    seed = seed_recipe(str(recipe_id), variant_input)
    variant_label = str(seed.get("variant_label") or f"variant_{variant:02d}")
    seed_path = runtime_root / str(recipe_id) / variant_label / "seed.json"
    _write_json(seed_path, seed)
    result = run_recipe(str(recipe_id), seed_path)
    result_path = runtime_root / str(recipe_id) / variant_label / "output.json"
    _write_json(result_path, result)
    return {
        "backend": backend,
        "recipe_id": str(recipe_id),
        "variant_id": f"{variant:02d}",
        "ok": result.get("ok") is True,
        "seed_file": str(seed_path),
        "output_file": str(result_path),
        "verifier_ok": (result.get("verifier") or {}).get("ok") is True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, choices=("simulated", "real"))
    parser.add_argument("--recipe-id", required=True)
    parser.add_argument("--variant", required=True, type=int)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = execute(
        args.backend,
        args.recipe_id,
        args.variant,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] and result["verifier_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
