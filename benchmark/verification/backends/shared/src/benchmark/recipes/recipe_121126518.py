from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_121126518


RECIPE_ID = "121126518"
SEED_TYPE = "recipe_function_term_date_math_variant"
TRACK = "answer"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "05712dbe"
CAST_DECLARE_AS = "8429b1a9"
DERIVE_DECLARE_AS = "7d95b75b"
RETURN_AS = "eec9b5dc"


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "05712dbe", "skip": false, "input": {"parameters_schema_json": "[{\"control_type\":\"date\",\"label\":\"Start date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"startdate\",\"type\":\"date_time\",\"optional\":true},{\"control_type\":\"date\",\"label\":\"End date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"enddate\",\"type\":\"date_time\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Term in months\",\"parse_output\":\"integer_conversion\",\"name\":\"terminmonths\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Quantity\",\"parse_output\":\"integer_conversion\",\"name\":\"quantity\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Allocated hours per unit\",\"parse_output\":\"integer_conversion\",\"name\":\"allocatedhoursperunit\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Term in days\",\"parse_output\":\"integer_conversion\",\"name\":\"termindays\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Planned duration\",\"parse_output\":\"integer_conversion\",\"name\":\"plannedduration\",\"type\":\"integer\",\"optional\":false}]", "result_schema_json": "[{\"name\":\"enddate\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date\",\"label\":\"Enddate\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"},{\"name\":\"requestedhours\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Requestedhours\",\"parse_output\":\"integer_conversion\"},{\"name\":\"startdate\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date\",\"label\":\"Startdate\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"},{\"name\":\"expirationdate\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date\",\"label\":\"Expirationdate\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "8429b1a9", "skip": false, "input": {"variables": {"data": {"allocatedhoursperunit": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"allocatedhoursperunit\"]}').to_i", "enddate": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"enddate\"]}')\n_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"enddate\"]}').to_date()\nelse \nblank\nend", "plannedduration": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"plannedduration\"]}').to_i", "quantity": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"quantity\"]}').to_i", "startdate": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"startdate\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"startdate\"]}').to_date() : blank", "termindays": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"termindays\"]}').to_i", "terminmonths": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"05712dbe\",\"path\":[\"parameters\",\"terminmonths\"]}').to_i"}, "schema": "[{\"control_type\":\"date\",\"label\":\"Start Date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"startdate\",\"type\":\"date_time\",\"optional\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"date\",\"label\":\"End Date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"enddate\",\"type\":\"date_time\",\"optional\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"integer\",\"label\":\"Term in months\",\"parse_output\":\"integer_conversion\",\"name\":\"terminmonths\",\"type\":\"integer\",\"optional\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"integer\",\"label\":\"Quantity\",\"parse_output\":\"integer_conversion\",\"name\":\"quantity\",\"type\":\"integer\",\"optional\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"integer\",\"label\":\"Allocated hours per unit\",\"parse_output\":\"integer_conversion\",\"name\":\"allocatedhoursperunit\",\"type\":\"integer\",\"optional\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"integer\",\"label\":\"Term in days\",\"parse_output\":\"integer_conversion\",\"name\":\"termindays\",\"type\":\"integer\",\"optional\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"integer\",\"label\":\"planned duration\",\"parse_output\":\"integer_conversion\",\"name\":\"plannedduration\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"plannedduration\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "7d95b75b", "skip": false, "input": {"variables": {"data": {"enddate": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"plannedduration\"]}').present? and _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"plannedduration\"]}') != 0\n(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"startdate\"]}') + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"plannedduration\"]}').days) - 1.days\nelse\nnil\nend", "expirationdate": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"enddate\"]}').present?\n_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"enddate\"]}')\nelsif _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"terminmonths\"]}').present? and _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"terminmonths\"]}') != 0\n(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"startdate\"]}') + (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"terminmonths\"]}') * _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"quantity\"]}')).months) - 1.days\nelsif _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"termindays\"]}').present? and _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"termindays\"]}') != 0\n(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"startdate\"]}')+ (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"termindays\"]}') * _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"quantity\"]}')).days) - 1.days\nelse\nnil\nend", "requestedhours": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"quantity\"]}') * _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"allocatedhoursperunit\"]}')"}, "schema": "[{\"control_type\":\"date\",\"label\":\"enddate\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"enddate\",\"type\":\"date\",\"optional\":true,\"details\":{\"real_name\":\"enddate\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"integer\",\"label\":\"requestedhours\",\"parse_output\":\"integer_conversion\",\"name\":\"requestedhours\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"requestedhours\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"name\":\"expirationdate\",\"type\":\"date\",\"optional\":true,\"label\":\"expirationdate\",\"details\":{\"real_name\":\"expirationdate\"},\"control_type\":\"date\",\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 4, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "eec9b5dc", "skip": false, "input": {"result": {"enddate": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"7d95b75b\",\"path\":[\"enddate\"]}')}", "expirationdate": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"7d95b75b\",\"path\":[\"expirationdate\"]}')}", "requestedhours": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"7d95b75b\",\"path\":[\"requestedhours\"]}')}", "startdate": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8429b1a9\",\"path\":[\"startdate\"]}')}"}}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (CAST_DECLARE_AS, "workato_variable", "declare_variable"),
    (DERIVE_DECLARE_AS, "workato_variable", "declare_variable"),
    (RETURN_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_recipe_function.return_result",
]
_CAST_DATA = _EXPECTED_TREE["block"][0]["input"]["variables"]["data"]
_DERIVE_DATA = _EXPECTED_TREE["block"][1]["input"]["variables"]["data"]
_RETURN_MAPPING = _EXPECTED_TREE["block"][2]["input"]["result"]
CAST_KEYS = (
    "allocatedhoursperunit",
    "enddate",
    "plannedduration",
    "quantity",
    "startdate",
    "termindays",
    "terminmonths",
)
INT_PARAMS = (
    "terminmonths",
    "quantity",
    "allocatedhoursperunit",
    "termindays",
    "plannedduration",
)
RESULT_KEYS = ("enddate", "expirationdate", "requestedhours", "startdate")
EXPIRATION_ARMS = ("enddate", "months", "days", "nil")
REQUIRED_EXPECT_KEYS = (
    "case",
    "branch",
    "cast_variables",
    "derived_variables",
    "result",
    "executed_action_count",
    "tools",
    "tool_expectations",
)
_EXPECTATION_TARGET_KEYS = {"tool"}
_EXPECTATION_VALUE_KEYS = {"args_contains", "result_contains"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_121126518(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Named traps on top of the byte pin: the three formula bodies this build
    # depends on (bare-pill if / blank else, plannedduration date math with
    # .days, elsif chain) must still be the pinned bytes.
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    cast_data = ((nodes.get(CAST_DECLARE_AS) or {}).get("input") or {}).get("variables", {}).get("data")
    if cast_data != _CAST_DATA:
        raise RuntimeError(f"recipe {RECIPE_ID} cast declare formulas changed")
    derive_data = ((nodes.get(DERIVE_DECLARE_AS) or {}).get("input") or {}).get("variables", {}).get("data")
    if derive_data != _DERIVE_DATA:
        raise RuntimeError(f"recipe {RECIPE_ID} derive declare formulas changed")
    if ((nodes.get(RETURN_AS) or {}).get("input") or {}).get("result") != _RETURN_MAPPING:
        raise RuntimeError(f"recipe {RECIPE_ID} return_result mapping changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for keyword in ("if", "elsif", "else", "foreach", "stop", "repeat", "try", "catch"):
        if any(node.get("keyword") == keyword for node in _walk_nodes(raw)):
            raise RuntimeError(f"recipe {RECIPE_ID} unexpectedly contains a {keyword} block")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
    }


def seed_121126518(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121126518(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("seed") not in (None, {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} is pure Workato-internal: seed must be absent or exactly {{}}"
        )
    for key in ("force_action_error", "job_context", "now"):
        if data.get(key) is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} has no catch/clock/time formula: variant key {key!r} "
                "must not be declared"
            )
    trigger = trigger_input(ctx)
    parameters = _require_parameters(trigger)
    derived = _derive_ground_truth(parameters)
    _require_expect_shape(data.get("expect"), derived)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_121126518(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121126518(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("trigger"), dict) or not isinstance(
        seed["trigger"].get("parameters"), dict
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger.parameters")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": {},
            "final_snapshot": {},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_121126518(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_parameters(trigger: dict[str, Any]) -> dict[str, Any]:
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    allowed = {"startdate", "enddate", *INT_PARAMS}
    unknown = sorted(set(parameters) - allowed)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters carry unknown keys: {unknown}")
    startdate = parameters.get("startdate")
    if not isinstance(startdate, str) or not _DATE_RE.fullmatch(startdate):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters.startdate must be an explicit YYYY-MM-DD "
            "string. An ABSENT startdate is a DEFERRED sub-branch: the cast ternary's "
            "`blank` alternative is unsupported by eval_dp_formula's ternary-arm "
            f"evaluation (engine gap -- see module header): {startdate!r}"
        )
    if "enddate" in parameters:
        enddate = parameters["enddate"]
        if not isinstance(enddate, str) or not _DATE_RE.fullmatch(enddate):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.enddate, when present, must be a "
                f"YYYY-MM-DD string (omit the key entirely for the no-enddate branch): {enddate!r}"
            )
    for name in INT_PARAMS:
        value = parameters.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{name} must be an explicit "
                f"non-negative JSON integer (0 selects the arm's else/guard path): {value!r}"
            )
    return parameters


def _derive_ground_truth(parameters: dict[str, Any]) -> dict[str, Any]:
    """Mirror of the two declare steps + return mapping over the validated
    trigger parameters. Month arithmetic clamps to month end exactly like the
    engine's shift_months (Ruby ActiveSupport parity)."""
    startdate = str(parameters["startdate"])
    enddate = parameters.get("enddate")
    cast: dict[str, Any] = {
        "allocatedhoursperunit": int(parameters["allocatedhoursperunit"]),
        "enddate": str(enddate) if enddate is not None else None,
        "plannedduration": int(parameters["plannedduration"]),
        "quantity": int(parameters["quantity"]),
        "startdate": startdate,
        "termindays": int(parameters["termindays"]),
        "terminmonths": int(parameters["terminmonths"]),
    }
    start = datetime.date.fromisoformat(startdate)
    if cast["plannedduration"] != 0:
        v2_enddate = (start + datetime.timedelta(days=cast["plannedduration"] - 1)).isoformat()
        pd_arm = "then"
    else:
        v2_enddate = None
        pd_arm = "else"
    if cast["enddate"] is not None:
        expiration: Any = cast["enddate"]
        expiration_arm = "enddate"
    elif cast["terminmonths"] != 0:
        shifted = _shift_months(start, cast["terminmonths"] * cast["quantity"])
        expiration = (shifted - datetime.timedelta(days=1)).isoformat()
        expiration_arm = "months"
    elif cast["termindays"] != 0:
        expiration = (
            start + datetime.timedelta(days=cast["termindays"] * cast["quantity"] - 1)
        ).isoformat()
        expiration_arm = "days"
    else:
        expiration = None
        expiration_arm = "nil"
    requestedhours = cast["quantity"] * cast["allocatedhoursperunit"]
    derived_variables = {
        "enddate": v2_enddate,
        "expirationdate": expiration,
        "requestedhours": requestedhours,
    }
    return {
        "cast_variables": cast,
        "derived_variables": derived_variables,
        "result": {
            "enddate": v2_enddate,
            "expirationdate": expiration,
            "requestedhours": requestedhours,
            "startdate": startdate,
        },
        "branch": {"pd_arm": pd_arm, "expiration_arm": expiration_arm},
    }


def _shift_months(day: datetime.date, months: int) -> datetime.date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    last_day = (next_month - datetime.timedelta(days=1)).day
    return day.replace(year=year, month=month, day=min(day.day, last_day))


def _require_expect_shape(expect: Any, derived: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if not isinstance(expect.get("case"), str) or not expect["case"].strip():
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must describe the variant branch")
    branch = expect.get("branch")
    if branch != derived["branch"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} contradicts the derived arms "
            f"{derived['branch']!r}"
        )
    if branch["expiration_arm"] not in EXPIRATION_ARMS:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch.expiration_arm invalid: {branch!r}")
    checks = (
        expect.get("cast_variables") == derived["cast_variables"],
        expect.get("derived_variables") == derived["derived_variables"],
        expect.get("result") == derived["result"],
        expect.get("executed_action_count") == 3,
        expect.get("tools") == ALLOWED_TOOLS,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground truth "
            f"{derived!r}: {expect!r}"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin exactly the return_result call"
        )
    item = items[0]
    unknown = sorted(set(item) - _EXPECTATION_TARGET_KEYS - _EXPECTATION_VALUE_KEYS)
    if unknown:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] has non-corpus keys: {unknown}"
        )
    if (
        item.get("tool") != "workato_recipe_function.return_result"
        or item.get("args_contains") != {"result": derived["result"]}
        or item.get("result_contains") != derived["result"]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the full return payload "
            f"{derived['result']!r}: {item!r}"
        )


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if not out["skip"]:
        out["input"] = node.get("input")
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        out["filter"] = node["filter"]
    out["block"] = [
        _normalize_tree(child) for child in node.get("block") or [] if isinstance(child, dict)
    ]
    return out


def _first_tree_mismatch(actual: Any, expected: Any, path: str = "root") -> str:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                return f"{path}.{key}: missing in raw recipe"
            if key not in expected:
                return f"{path}.{key}: unexpected in raw recipe"
            found = _first_tree_mismatch(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return ""
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return f"{path}: length {len(actual)} != {len(expected)}"
        for idx, (act, exp) in enumerate(zip(actual, expected)):
            found = _first_tree_mismatch(act, exp, f"{path}[{idx}]")
            if found:
                return found
        return ""
    if actual != expected:
        return f"{path}: {json.dumps(actual, default=str)[:200]} != {json.dumps(expected, default=str)[:200]}"
    return ""


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
