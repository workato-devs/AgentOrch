"""Shared recipe-seed command; variants provide only context construction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

from .config import (
    BENCHMARK_ROOT,
    CODE_FLOW_DIR,
    OUTPUT_DIR,
    recipe_output_dir,
    variant_label,
)
from .context import RecipeContext
from .recipe_store import load_raw_recipe
from .recipes import SEEDERS

ContextBuilder = Callable[[dict], RecipeContext]


def seed_recipe(
    recipe_id: str,
    variant_input: dict,
    build_context: ContextBuilder,
) -> dict:
    if recipe_id not in SEEDERS:
        raise KeyError(f"recipe {recipe_id} has no registered seeder")
    raw = load_raw_recipe(recipe_id)
    ctx = build_context(variant_input)
    return SEEDERS[recipe_id](raw, ctx)


def load_variant_input(
    recipe_id: str,
    variant: int | None,
    variant_file: Path | None,
) -> dict:
    if variant_file is None and variant is None:
        raise ValueError(
            "provide --variant or --variant-file; implicit no-variant seeding "
            "is not allowed"
        )
    if variant_file is not None:
        path = variant_file
    else:
        label = variant_label(variant)
        path = CODE_FLOW_DIR / str(recipe_id) / str(label) / "input.json"
        if not path.exists():
            raise FileNotFoundError(f"variant input does not exist: {path}")
    data = json.loads(path.read_text())
    if str(data.get("recipe_id")) != str(recipe_id):
        raise ValueError(f"variant file recipe_id mismatch: {path}")
    return data


def main(build_context: ContextBuilder) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("recipe_id")
    parser.add_argument("--variant", type=int)
    parser.add_argument("--variant-file", type=Path)
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    if args.variant is None and args.variant_file is None:
        parser.error("one of --variant or --variant-file is required")
    if args.variant_file is not None:
        # Variants load only from this recipe's shared dataset tree, never
        # from arbitrary paths.
        variant_root = (CODE_FLOW_DIR / str(args.recipe_id)).resolve()
        if not args.variant_file.resolve().is_relative_to(variant_root):
            parser.error(f"--variant-file must live under {variant_root}")
    base_dir = Path(args.out_dir)
    if base_dir.resolve() != OUTPUT_DIR.resolve():
        # Output redirection is only sanctioned through BENCHMARK_OUTPUT_DIR.
        parser.error(
            f"--out-dir must be the benchmark output dir {OUTPUT_DIR} "
            "(set BENCHMARK_OUTPUT_DIR to relocate the whole tree)"
        )
    variant_input = load_variant_input(
        args.recipe_id, args.variant, args.variant_file
    )
    seed = seed_recipe(args.recipe_id, variant_input, build_context)
    variant = seed.get("variant_label")
    out_dir = recipe_output_dir(args.recipe_id, variant)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "seed.json"
    out_path.write_text(json.dumps(seed, indent=2, sort_keys=True) + "\n")
    try:
        display_path = out_path.relative_to(BENCHMARK_ROOT)
    except ValueError:
        display_path = out_path
    print(
        json.dumps(
            {"ok": True, "seed_file": str(display_path), "seed": seed},
            indent=2,
            sort_keys=True,
        )
    )
    return 0
