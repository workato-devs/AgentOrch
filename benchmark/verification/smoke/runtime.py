"""Two-recipe protocol smoke runtime.

Full connector implementations live in ``verification/backends``. This small
runtime stays dependency-light for public protocol tests; private seed files
remain evaluator-only and never enter a model prompt.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SEEDS = Path(__file__).resolve().parent.parent / "seeds"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _tool_specs(recipe_id: str) -> list[dict[str, Any]]:
    if recipe_id == "64112882":
        return [
            {"name": "workato_db_table.get_records", "input_schema": {
                "type": "object", "required": ["table_id"], "properties": {
                    "table_id": {"type": "string"}, "filters": {
                        "type": "array", "items": {
                            "type": "object", "required": ["field_id", "op"],
                            "properties": {
                                "field_id": {"type": "string"},
                                "op": {"type": "string", "enum": [
                                    "eq", "equals", "ne", "gte", "gt", "lte", "lt",
                                    "starts_with", "isnull", "isnotnull",
                                ]},
                                "value": {"type": ["string", "number", "boolean", "null"]},
                            },
                        },
                    },
                    "limit": {"type": "integer"}, "order_by_field_id": {"type": "string"},
                    "order_direction": {"enum": ["asc", "desc"]},
                },
            }},
            {"name": "workato_api_platform.return_response", "input_schema": {
                "type": "object", "required": ["http_status_code"], "properties": {
                    "http_status_code": {"type": "string"}, "response": {},
                },
            }},
        ]
    if recipe_id == "69270259":
        schema = {"type": "object", "required": ["recipe_id"], "properties": {"recipe_id": {"type": "string"}}}
        return [
            {"name": "workato_app.stop_recipe", "input_schema": schema},
            {"name": "workato_app.start_recipe", "input_schema": schema},
        ]
    raise KeyError(f"no simulated tool surface for recipe {recipe_id}")


class SimulatedCase:
    """Fresh deterministic state and callable tool surface for one variant."""

    def __init__(self, recipe_id: str, variant_id: str) -> None:
        self.recipe_id = recipe_id
        self.variant_id = variant_id
        seed_path = SEEDS / recipe_id / f"variant_{int(variant_id):02d}.json"
        seed_record = _read_json(seed_path)
        # Full-corpus exports keep public runtime input and private simulator
        # state in an explicit wrapper.  Retain compatibility with the
        # original two-recipe seed files during source-control bisects.
        seed = seed_record.get("seed")
        if not isinstance(seed, dict):
            seed = seed_record
        public_runtime_input = seed_record.get("public_runtime_input") or {}
        self.trigger = deepcopy(
            public_runtime_input.get("trigger_input")
            or seed_record.get("trigger")
            or {}
        )
        section = seed.get("workato_db_table") or {}
        self.tables = deepcopy(section.get("tables") or {}) if isinstance(section, dict) else {}
        for rows in self.tables.values():
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict):
                        row.setdefault("_created_by", "seed")
        forced_error = seed_record.get("force_action_error")
        if not isinstance(forced_error, dict):
            forced_error = seed.get("forced_error")
        if isinstance(forced_error, dict) and "tool" not in forced_error:
            forced_error = {
                "tool": "workato_db_table.get_records",
                "error": forced_error.get("error"),
            }
        self.forced_error = forced_error if isinstance(forced_error, dict) else None
        self.lifecycle: dict[str, str] = {}
        self.terminal_result: Any = None
        self.terminal = False

    @property
    def tool_specs(self) -> list[dict[str, Any]]:
        return _tool_specs(self.recipe_id)

    @property
    def allowed_tools(self) -> set[str]:
        return {item["name"] for item in self.tool_specs}

    def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.terminal:
            raise RuntimeError("a terminal response already ended this run")
        if self.forced_error and self.forced_error.get("tool") == tool:
            message = self.forced_error.get("error")
            self.forced_error = None
            raise RuntimeError(str(message or "simulated connector failure"))
        if tool == "workato_db_table.get_records":
            return self._get_records(args)
        if tool == "workato_api_platform.return_response":
            if "http_status_code" not in args:
                raise RuntimeError("workato_api_platform.return_response requires http_status_code")
            self.terminal = True
            self.terminal_result = args.get("response")
            return {"ok": True, "http_status_code": str(args["http_status_code"]), "response": self.terminal_result}
        if tool in {"workato_app.stop_recipe", "workato_app.start_recipe"}:
            recipe = args.get("recipe_id")
            if not isinstance(recipe, str) or not recipe:
                raise RuntimeError(f"{tool} requires a non-empty recipe_id")
            self.lifecycle[recipe] = "running" if tool.endswith("start_recipe") else "stopped"
            return {"ok": True, "recipe_id": recipe}
        raise RuntimeError(f"tool not registered for this recipe: {tool}")

    def _get_records(self, args: dict[str, Any]) -> dict[str, Any]:
        table_id = args.get("table_id")
        if not isinstance(table_id, str) or not table_id:
            raise RuntimeError("workato_db_table.get_records requires table_id")
        rows = deepcopy(self.tables.get(table_id, []))
        filters = args.get("filters") or []
        if not isinstance(filters, list):
            raise RuntimeError("workato_db_table.get_records filters must be a list")
        for item in filters:
            if not isinstance(item, dict) or not isinstance(item.get("field_id"), str):
                raise RuntimeError("workato_db_table filter requires field_id")
            op = item.get("op", "eq")
            if op not in {"eq", "equals"}:
                raise RuntimeError(f"unsupported workato_db_table filter op: {op}")
            rows = [row for row in rows if row.get(item["field_id"]) == item.get("value")]
        order = args.get("order_by_field_id")
        if isinstance(order, str) and order:
            rows.sort(key=lambda row: str(row.get(order) or ""), reverse=args.get("order_direction") == "desc")
        if "limit" in args:
            try:
                rows = rows[:int(args["limit"])]
            except (TypeError, ValueError) as exc:
                raise RuntimeError("workato_db_table.get_records limit must be an integer") from exc
        return {"ok": True, "records": rows}

    def final_state(self) -> dict[str, Any]:
        if self.recipe_id == "64112882":
            return {
                "ok": True,
                "workato_db_table": {
                    "state_file": f"output/_state/workato_db_tables/{self.recipe_id}/variant_{int(self.variant_id):02d}/tables.json",
                    "tables": deepcopy(self.tables),
                },
            }
        return {}

    def execute_plan(self, plan: Any) -> dict[str, Any]:
        """Execute the released WorkflowPlan subset against this fresh state.

        This is adapted from the existing benchmark's frozen-plan execution
        semantics, narrowed to the node and expression forms needed by this
        pilot. It is evaluator-owned: neither seed nor execution bindings are
        sent to the model.
        """
        nodes = plan.get("plan") if isinstance(plan, dict) else plan
        if isinstance(plan, dict) and not isinstance(nodes, list):
            nodes = plan.get("steps")
        if not isinstance(nodes, list):
            return {"status": "invalid_plan", "trajectory": [], "error": "plan must contain a list"}
        bindings: dict[str, Any] = {}
        trajectory: list[dict[str, Any]] = []
        final_answer: Any = None

        class Terminal(Exception):
            pass

        def path_get(value: Any, path: Any) -> Any:
            current = value
            for item in path or []:
                if isinstance(current, dict):
                    current = current.get(str(item))
                elif isinstance(current, list) and isinstance(item, int) and 0 <= item < len(current):
                    current = current[item]
                else:
                    return None
            return current

        def resolve(value: Any, scope: dict[str, Any]) -> Any:
            if isinstance(value, list):
                return [resolve(item, scope) for item in value]
            if not isinstance(value, dict):
                return value
            kind = value.get("kind")
            if kind == "literal":
                return resolve(value.get("value"), scope)
            if kind == "input_ref":
                return path_get(self.trigger, value.get("path"))
            if kind in {"output_ref", "loop_ref", "error_ref"}:
                name = value.get("binding")
                return path_get(scope.get(str(name)), value.get("path"))
            if kind == "resource_ref":
                return value.get("resource")
            if kind == "expression":
                op = value.get("op")
                if op in {"map", "project", "filter"}:
                    source = resolve(value.get("items"), scope)
                    if source is None:
                        source = resolve((value.get("args") or [None])[0], scope)
                    if not isinstance(source, list):
                        raise RuntimeError(f"{op} requires array items")
                    item_bind = value.get("item_bind")
                    if not isinstance(item_bind, str):
                        raise RuntimeError(f"{op} requires item_bind")
                    prior = scope.get(item_bind)
                    output = []
                    for item in source:
                        scope[item_bind] = item
                        if op == "filter":
                            condition = value.get("condition")
                            if condition is None and len(value.get("args") or []) > 1:
                                condition = value["args"][1]
                            if resolve(condition, scope): output.append(item)
                        else:
                            mapped = value.get("value")
                            if mapped is None and len(value.get("args") or []) > 1:
                                mapped = value["args"][1]
                            output.append(resolve(mapped, scope))
                    if prior is None: scope.pop(item_bind, None)
                    else: scope[item_bind] = prior
                    return output
                args = [resolve(item, scope) for item in value.get("args") or []]
                if op == "count" or op == "length": return len(args[0] or [])
                if op == "eq": return args[0] == args[1]
                if op == "ne": return args[0] != args[1]
                if op == "gt": return args[0] > args[1]
                if op == "gte": return args[0] >= args[1]
                if op == "lt": return args[0] < args[1]
                if op == "lte": return args[0] <= args[1]
                if op == "and": return all(args)
                if op == "or": return any(args)
                if op == "not": return not args[0]
                if op == "array": return args
                if op == "object": return {key: resolve(item, scope) for key, item in (value.get("fields") or {}).items()}
                if op == "coalesce": return next((item for item in args if item not in (None, "")), None)
                if op == "get": return path_get(args[0], args[1] if len(args) > 1 else [])
                if op == "pluck":
                    source = args[0] if args else []
                    path = value.get("path") or (args[1] if len(args) > 1 else [])
                    return [path_get(item, path) for item in source if isinstance(source, list)]
                if op == "sort_by":
                    source = list(args[0] or [])
                    path = value.get("path") or []
                    return sorted(source, key=lambda item: str(path_get(item, path) or ""),
                                  reverse=value.get("direction") == "desc")
                raise RuntimeError(f"unsupported expression op: {op}")
            return {key: resolve(item, scope) for key, item in value.items()}

        def run(items: list[Any], scope: dict[str, Any]) -> None:
            nonlocal final_answer
            for node in items:
                if self.terminal:
                    raise Terminal()
                if not isinstance(node, dict):
                    raise RuntimeError("plan node must be an object")
                kind = node.get("kind")
                if kind == "call":
                    tool = node.get("tool")
                    args = resolve(node.get("arguments", node.get("args", {})), scope)
                    if not isinstance(tool, str) or not isinstance(args, dict):
                        raise RuntimeError("call requires tool and object arguments")
                    try:
                        result = self.call(tool, args)
                    except RuntimeError as exc:
                        trajectory.append({"tool": tool, "args": args, "error": str(exc)})
                        raise
                    trajectory.append({"tool": tool, "args": args, "result": result})
                    if isinstance(node.get("bind"), str):
                        scope[node["bind"]] = result
                    if self.terminal:
                        final_answer = self.terminal_result
                        raise Terminal()
                elif kind == "transform":
                    bind = node.get("bind")
                    if not isinstance(bind, str):
                        raise RuntimeError("transform requires bind")
                    scope[bind] = resolve(node.get("expression"), scope)
                elif kind == "if":
                    branch = node.get("then") if resolve(node.get("condition"), scope) else node.get("else")
                    run(branch if isinstance(branch, list) else [], scope)
                elif kind == "try":
                    try:
                        run(node.get("body") if isinstance(node.get("body"), list) else [], scope)
                    except Terminal:
                        raise
                    except RuntimeError as exc:
                        error_bind = node.get("error_bind")
                        if isinstance(error_bind, str):
                            scope[error_bind] = {"message": str(exc)}
                        run(node.get("catch") if isinstance(node.get("catch"), list) else [], scope)
                elif kind == "foreach":
                    item_bind = node.get("item_bind")
                    values = resolve(node.get("items"), scope)
                    if not isinstance(item_bind, str) or not isinstance(values, list):
                        raise RuntimeError("foreach requires an item_bind and array items")
                    prior = scope.get(item_bind)
                    for item in values:
                        scope[item_bind] = item
                        run(node.get("body") if isinstance(node.get("body"), list) else [], scope)
                    if prior is None: scope.pop(item_bind, None)
                    else: scope[item_bind] = prior
                elif kind == "return":
                    final_answer = resolve(node.get("value"), scope)
                    self.terminal = True
                    raise Terminal()
                elif kind == "stop":
                    final_answer = resolve(node.get("arguments", {}), scope)
                    self.terminal = True
                    raise Terminal()
                else:
                    raise RuntimeError(f"unsupported plan node kind: {kind}")

        try:
            run(nodes, bindings)
        except Terminal:
            return {"status": "ok", "trajectory": trajectory, "final_answer": final_answer,
                    "final_state": self.final_state()}
        except RuntimeError as exc:
            return {"status": "plan_execution_error", "trajectory": trajectory, "error": str(exc),
                    "final_state": self.final_state()}
        return {"status": "stopped_without_terminal", "trajectory": trajectory,
                "final_answer": final_answer, "final_state": self.final_state()}


def build_case(recipe_id: str, variant_id: str) -> SimulatedCase:
    return SimulatedCase(str(recipe_id), str(variant_id))
