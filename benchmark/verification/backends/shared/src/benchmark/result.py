from __future__ import annotations

from typing import Any

from .context import RecipeContext


def recipe_result(
    *,
    recipe_id: str,
    ok: bool,
    track: str,
    ctx: RecipeContext,
    details: dict[str, Any],
    allowed_tools: list[str],
) -> dict[str, Any]:
    allowed = set(allowed_tools)
    return {
        "recipe_id": recipe_id,
        "ok": ok,
        "track": track,
        "allowed_tools": allowed_tools,
        "tool_specs": ctx.tools.exposed_specs(allowed),
        "tool_calls": ctx.tools.call_log(allowed),
        "harness_tool_calls": ctx.tools.call_log_excluding(allowed),
        "details": details,
    }
