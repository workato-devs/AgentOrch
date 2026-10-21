"""Run a recipe with deterministic simulated connector tools."""

from __future__ import annotations

from pathlib import Path

from ._run_recipe import main as _shared_main
from ._run_recipe import run_recipe as _shared_run_recipe
from .config import load_env
from .context import RecipeContext
from .simulated_tools import build_simulated_tools, simulated_env


def build_context(seed: dict) -> RecipeContext:
    env = simulated_env(load_env())
    return RecipeContext(
        env=env,
        tools=build_simulated_tools(env, seed),
        seed=seed,
    )


def run_recipe(recipe_id: str, seed_file: Path) -> dict:
    return _shared_run_recipe(recipe_id, seed_file, build_context)


def main() -> int:
    return _shared_main(build_context)


if __name__ == "__main__":
    raise SystemExit(main())
