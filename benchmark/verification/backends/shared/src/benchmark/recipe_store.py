from __future__ import annotations

import json
import re
from typing import Any

from .config import CODE_FLOW_DIR


_COMPLETE_RAW_RE = re.compile(
    r"Complete raw recipe:\s*```json\s*(?P<json>\{.*\})\s*```",
    flags=re.S,
)


def load_raw_recipe(recipe_id: str) -> dict[str, Any]:
    path = CODE_FLOW_DIR / str(recipe_id) / "raw_recipe.md"
    if not path.exists():
        raise RuntimeError(f"recipe {recipe_id} has no benchmark-local raw recipe file: {path}")
    text = path.read_text()
    match = _COMPLETE_RAW_RE.search(text)
    if not match:
        raise RuntimeError(f"recipe {recipe_id} raw_recipe.md does not contain a complete raw recipe JSON block")
    raw = json.loads(match.group("json"))
    if not isinstance(raw, dict):
        raise RuntimeError(f"recipe {recipe_id} raw recipe JSON must be an object")
    return raw
