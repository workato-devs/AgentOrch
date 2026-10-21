"""Seed a recipe with live connector tools."""

from __future__ import annotations

from ._seed_recipe import load_variant_input
from ._seed_recipe import main as _shared_main
from ._seed_recipe import seed_recipe as _shared_seed_recipe
from .config import load_env
from .context import RecipeContext
from .live_tools import build_live_tools


def build_context(variant_input: dict) -> RecipeContext:
    if not isinstance(variant_input, dict) or not variant_input:
        raise RuntimeError("seeding requires an explicit variant input object")
    env = load_env()
    seed = {"variant_input": variant_input}
    return RecipeContext(env=env, tools=build_live_tools(env), seed=seed)


def seed_recipe(recipe_id: str, variant_input: dict) -> dict:
    return _shared_seed_recipe(recipe_id, variant_input, build_context)


def main() -> int:
    return _shared_main(build_context)


if __name__ == "__main__":
    raise SystemExit(main())
