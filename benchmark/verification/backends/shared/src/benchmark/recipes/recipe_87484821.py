from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data, variant_index
from ..verifier import verify_87484821


RECIPE_ID = "87484821"
SEED_TYPE = "training_exemption_reject_variant"
TRACK = "live_slack_training_exemption_reject"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "50f227a4"
# Slack bot command /hrbot training_exemption (scope reject, hide_from_help;
# trigger as 50f227a4, parameters {request_id, exempted_user, training,
# requestor}, context {user_email, user, channel}, ts):
#   workato_db_table.get_records 663b098b (mock table 400 '[INTT] Training
#     Exemption Requests', filter record-id field 11fbe9a6-... eq
#     parameters.request_id, limit 200 asc)
#   IF 3 (records size == 1):
#     update_record 8a53f61a: record_id = records.current_item.11fbe9a6_...
#       (current_item outside foreach -> FIRST record), sets rejected-by
#       8cd7177d_... = context.user_email, rejected-on b3bd6f53_... =
#       job_created_at.to_date (renders YYYY-MM-DD, probed), status
#       f4cff202_... = 'Rejected'
#     post_bot_message 998ab05c to context.channel with advanced.ts =
#       trigger ts -> live chat.update of the SEEDED message ('was `rejected`
#       by <@context.user>')
#     post_bot_message 1158581b to '@context.user' (no ts -> fresh live post;
#       the executor routes both channels to SLACK_CHANNEL_OVERRIDE)
#   ELSE 7 > IF 8 (records size == 0):
#     post_bot_message 5a95df0c ('was not found.', advanced.ts = trigger ts)
#   ELSE 10:
#     post_bot_message 5590253b ('More than one exemption request ... was
#       found. Please contact an admin for assistance.', advanced.ts)
#
# The blocks' attachment_fields (*Training Type* / *Rejected On*) are NOT part
# of the harness-rendered text (slack_text only renders per-block
# section_text); their value formulas still resolve, so job_context must be
# pinned in every variant. Slack runs LIVE: every reachable branch issues one
# advanced.ts post, so every variant's trigger ts must be the $SEED_MESSAGE_TS
# token, which the seeder replaces with a real chat.postMessage ts (two-phase
# seed, recipe_121365920 precedent). The db table is a per-run isolated
# Workato-internal mock (allowed per backend policy) — no cleanup; ordinary
# benchmark Slack posts are not re-read by later runs, so no Slack cleanup
# either (cleanup principle).
TABLE_ID = "400"
COL_RECORD_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
COL_REJECTED_BY = "8cd7177d_9b65_4fc0_8da3_9ca574899bf7"
COL_REJECTED_ON = "b3bd6f53_27d1_4a58_b900_92bd7e355d13"
COL_STATUS = "f4cff202_a89b_4a7c_a584_2ea61c26ee3b"
SEED_TS_TOKEN = "$SEED_MESSAGE_TS"
REQUIRED_TRIGGER_PARAMETERS = ("request_id", "exempted_user", "training", "requestor")
REQUIRED_TRIGGER_CONTEXT_FIELDS = ("user_email", "user", "channel")
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("663b098b", "workato_db_table", "get_records"),
    ("8a53f61a", "workato_db_table", "update_record"),
    ("998ab05c", "slack_bot", "post_bot_message"),
    ("1158581b", "slack_bot", "post_bot_message"),
    ("5a95df0c", "slack_bot", "post_bot_message"),
    ("5590253b", "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "slack.post_message",
]

# --- Verbatim raw-recipe pin: the full normalized node tree (number, keyword,
# provider, name, as, skip, input for every node). Any upstream drift in the
# db-table filter, the update field formulas (incl. job_created_at.to_date),
# the block-kit section texts or the IF conditions fails validation instead of
# silently changing groundtruth.
_RAW_PIN_JSON = r"""{"as": "50f227a4", "block": [{"as": "663b098b", "block": [], "input": {"0b6c338a-82ec-42a4-9608-137bc0e9d35c": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "13b2933d-fd41-4f83-83a6-c77c8b2f4493": "string", "48a91e69-397c-45ce-87a3-de612b22d197": "date", "4c529387-ee19-4b34-b40f-a9aaf2c36448": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "8cd7177d-9b65-4fc0-8da3-9ca574899bf7": "string", "a525ecc6-6e75-40e2-937f-27daf2d1ca32": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "b07eb5f6-6661-4382-8081-14f09c49c8f1": "string", "b3bd6f53-27d1-4a58-b900-92bd7e355d13": "date", "c484f77c-6f52-4e7d-a3e2-3dc9795adf5c": "string", "f4cff202-a89b-4a7c-a584-2ea61c26ee3b": "string", "filters": [{"field_id": "11fbe9a6-a16d-4d7e-86ea-afe42ec03005", "op_id": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"request_id\"]}')}"}], "limit": "200", "order_direction": "asc", "table_id": "400"}, "keyword": "action", "name": "get_records", "number": 2, "provider": "workato_db_table", "skip": false}, {"as": "", "block": [{"as": "8a53f61a", "block": [], "input": {"parameters": {"8cd7177d_9b65_4fc0_8da3_9ca574899bf7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"context\", \"user_email\"]}')}", "b3bd6f53_27d1_4a58_b900_92bd7e355d13": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').to_date", "f4cff202_a89b_4a7c_a584_2ea61c26ee3b": "Rejected"}, "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"663b098b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}", "table_id": "400"}, "keyword": "action", "name": "update_record", "number": 4, "provider": "workato_db_table", "skip": false}, {"as": "998ab05c", "block": [], "input": {"advanced": {"ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"ts\"]}')}"}, "blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":workatonew: *Internal Trainings* :workatonew:"}, {"block_type": "divider", "button_type": "continue_flow"}, {"attachment_fields": [{"title": "*Training Type*\n", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"training\"]}')}"}, {"title": "*Rejected On*\n", "value": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').to_date"}], "block_type": "section_with_fields", "button_type": "continue_flow", "section_text": "The exemption request for <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"exempted_user\"]}')}> requested by <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"requestor\"]}')}> was `rejected` by <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"context\", \"user\"]}')}>."}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"context\", \"channel\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 5, "provider": "slack_bot", "skip": false}, {"as": "1158581b", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "section_text": ":workatonew: *Internal Trainings* :workatonew:"}, {"block_type": "divider"}, {"attachment_fields": [{"title": "*Training Type*\n", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"training\"]}')}"}, {"title": "*Rejected On*\n", "value": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').to_date"}], "block_type": "section_with_fields", "section_text": "The exemption request for <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"exempted_user\"]}')}> requested by <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"requestor\"]}')}> was `rejected` by <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"context\", \"user\"]}')}>."}], "channel": "@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"context\", \"user\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 6, "provider": "slack_bot", "skip": false}, {"as": "", "block": [{"as": "", "block": [{"as": "5a95df0c", "block": [], "input": {"advanced": {"ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"ts\"]}')}"}, "blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":workatonew: *Internal Trainings* :workatonew:"}, {"block_type": "divider", "button_type": "continue_flow"}, {"attachment_fields": [{"title": "*Training Type*\n", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"training\"]}')}"}, {"title": "*Rejected On*\n", "value": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').to_date"}], "block_type": "section_with_fields", "button_type": "continue_flow", "section_text": "The exemption request for <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"exempted_user\"]}')}> requested by <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"requestor\"]}')}> was not found."}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"context\", \"channel\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 9, "provider": "slack_bot", "skip": false}, {"as": "", "block": [{"as": "5590253b", "block": [], "input": {"advanced": {"ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"ts\"]}')}"}, "blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":workatonew: *Internal Trainings* :workatonew:"}, {"block_type": "divider", "button_type": "continue_flow"}, {"attachment_fields": [{"title": "*Training Type*\n", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"training\"]}')}"}, {"title": "*Rejected On*\n", "value": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').to_date"}], "block_type": "section_with_fields", "button_type": "continue_flow", "section_text": "More than one exemption request for <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"exempted_user\"]}')}> requested by <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"parameters\", \"requestor\"]}')}> was found. Please contact an admin for assistance."}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"50f227a4\",\"path\":[\"context\", \"channel\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 11, "provider": "slack_bot", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 10, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"663b098b\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 8, "provider": "", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 7, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"663b098b\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "1"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 3, "provider": "", "skip": false}], "input": {"allow_dialog": "false", "domain": "hrbot", "hide_from_help": "true", "name": "training_exemption", "parameters": "[\n  {\n    \"name\": \"request_id\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"exempted_user\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"training\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"requestor\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\"\n  }\n]", "scope": "reject"}, "keyword": "trigger", "name": "bot_command_v2", "number": 1, "provider": "slack_bot", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_87484821(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if (
        str(trigger_cfg.get("domain") or "") != "hrbot"
        or str(trigger_cfg.get("name") or "") != "training_exemption"
        or str(trigger_cfg.get("scope") or "") != "reject"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} bot command identity changed: {trigger_cfg}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
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


def seed_87484821(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87484821(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != sorted(REQUIRED_TRIGGER_PARAMETERS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            f"{sorted(REQUIRED_TRIGGER_PARAMETERS)}; got "
            f"{sorted(parameters.keys()) if isinstance(parameters, dict) else parameters}"
        )
    for field in REQUIRED_TRIGGER_PARAMETERS:
        if not str(parameters.get(field) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter {field!r} must be a non-empty string")
    context = trigger.get("context")
    if not isinstance(context, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input missing context object")
    for field in REQUIRED_TRIGGER_CONTEXT_FIELDS:
        if not str(context.get(field) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger context field {field!r} must be a non-empty string")
    if trigger.get("ts") != SEED_TS_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.ts must be the {SEED_TS_TOKEN!r} token: every "
            "reachable branch chat.updates the trigger message via advanced.ts, so the seeder "
            "must post a real Slack message and thread its live ts (never fabricate a ts)"
        )
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or not str(job_context.get("job_created_at") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin job_context.job_created_at "
            "(the rejected-on .to_date formula reads it; never use wall-clock time)"
        )
    seed_in = data.get("seed")
    db_section = seed_in.get("workato_db_table") if isinstance(seed_in, dict) else None
    tables = db_section.get("tables") if isinstance(db_section, dict) else None
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly workato_db_table.tables[{TABLE_ID!r}]"
        )
    if not isinstance(tables[TABLE_ID], list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} seed rows must be a list")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    channel = ctx.env.slack_channel_override
    if not channel:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    idx = variant_index(ctx)
    seed_text = (
        f"benchmark seed for recipe {RECIPE_ID} variant {idx:02d}: "
        f"training exemption request {parameters.get('request_id')} pending review"
    )
    posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": seed_text})
    ts = str(posted.get("ts") or "")
    if not ts:
        raise RuntimeError(f"Slack chat.postMessage returned no ts: {posted}")
    trigger = _replace_token(trigger, SEED_TS_TOKEN, ts)
    message = {"channel": str(posted.get("channel") or channel), "ts": ts, "text": seed_text}
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(db_section),
        "job_context": deepcopy(job_context),
        "message": message,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_87484821(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87484821(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context section")
    message = seed.get("message")
    if not isinstance(message, dict) or not str(message.get("ts") or "") or not str(message.get("channel") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a live seeded Slack message (seed['message'] with "
            "channel + ts); never fabricate a ts"
        )
    trigger = seed.get("trigger") if isinstance(seed.get("trigger"), dict) else {}
    if str(trigger.get("ts") or "") != str(message.get("ts") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed trigger.ts does not match the seeded live message ts"
        )
    initial_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "seed_message": {
                "channel": message.get("channel"),
                "ts": message.get("ts"),
                "text": message.get("text"),
            },
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_87484821(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _replace_token(value: Any, token: str, replacement: str) -> Any:
    if isinstance(value, dict):
        return {key: _replace_token(item, token, replacement) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_token(item, token, replacement) for item in value]
    if isinstance(value, str) and token in value:
        return value.replace(token, replacement)
    return value


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
