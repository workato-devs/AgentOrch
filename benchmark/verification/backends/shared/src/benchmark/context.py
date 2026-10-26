from __future__ import annotations

from dataclasses import dataclass

from .config import Env
from .tools import ToolRegistry


@dataclass
class RecipeContext:
    env: Env
    tools: ToolRegistry
    seed: dict
