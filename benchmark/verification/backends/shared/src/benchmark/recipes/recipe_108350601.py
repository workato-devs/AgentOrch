from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_108350601


RECIPE_ID = "108350601"
SEED_TYPE = "slack_dynamic_menu_salesforce_user_email_typeahead_variant"
TRACK = "live_salesforce_slack_dynamic_menu_fv_owners"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "4cc98c36"
SEARCH_AS = "8661bd72"
MENU_AS = "3c75f8f0"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")

# slack_bot.dynamic_menu 'Retrieve FV Owners' (as 4cc98c36) -> v1
# salesforce.search_sobjects_soql 8661bd72 (sobject_name User, limit 150,
# BARE-condition query "Email like '%<typeahead.value>%'" -- no SELECT/FROM;
# the harness evaluates the bare string as the WHERE clause) ->
# slack_bot.generate_menu_options 3c75f8f0 with ____source = the SOBJECT-NAMED
# pill result['User'] (the live tool aliases records under the sobject name,
# live_tools sf_search_records) and label == value == current_item.Email.
#
# EXACT TWIN of 107245433: the raw_recipe.md files differ ONLY in the title
# line, CSV metadata (flow_id 48716877 vs 47700612, created_at, version_no
# 3 vs 12) and the trigger `parameters` JSON WHITESPACE (this id pins the
# pretty-printed literal; 107245433 pins the compact one -- semantically the
# same single required fv_owner string param). Byte-diffed on the current
# tree. verify_107245433 DELEGATES to verify_108350601 (registered
# 88674737 -> 88676643 delegation precedent: merge this head fragment first).
# Distinct variant data per id.
#
# The declared trigger parameter fv_owner is REQUIRED by the menu schema but
# NEVER dereferenced by any step (probed: the traced search args carry only
# sobject/query/limit) -- every variant seeds it for trigger faith and the
# verifier pins the full search args by equality, which proves inertness.
#
# Backends: salesforce LIVE (read-only). The searchable User set is EXACTLY
# the read-only current-user registration (seed.salesforce.current_user --
# org Users cannot be created/deleted via the API; registered precedents
# 118168683/119184209/124203347). The recipe's ~4.4k-line User
# extended_output_schema is inert -- only Email is dereferenced and it is in
# add_current_user's read field list. slack_bot dynamic_menu trigger +
# generate_menu_options are Workato-internal and mockable under the backend
# policy -- menu-option generation returns the Workato menu payload for the
# Slack interaction and never makes a Slack API call: the trigger payload is
# seeded and the menu is a validation-only Workbot response.
#
# Harness LIKE semantics (probed): the bare-condition LIKE lowers BOTH sides
# (case-insensitive, matching live SOQL LIKE); '%' spans any run. Variants
# therefore cover: mid-substring match, uppercased-substring match
# (case-insensitivity pin), no-match -> pinned [] options (empty-list
# precedent: generate_menu_options always runs), and whole-email match.
#
# Ref tokens resolved at seed time into trigger AND expect (longest-first so
# $CURRENT_USER_EMAIL never clobbers the derived tokens):
#   $CURRENT_USER_ID / $CURRENT_USER_NAME / $CURRENT_USER_EMAIL from the
#   read-only current-user row;
#   $CURRENT_USER_EMAIL_CORE       = email[1:-1] (strict INNER substring --
#                                    proves both %-wildcards);
#   $CURRENT_USER_EMAIL_CORE_UPPER = email[1:-1].upper() (case-fold pin).
# The live email must be non-trivial (len >= 4, contains '@' and a letter)
# and stored lowercase, else the case-fold variant would be meaningless --
# the seeder fails fast instead of guessing.

# Frozen document-order structure pins (keyword/number/as/provider/name/skip
# + verbatim raw input per node, incl. the bare-condition SOQL query pill and
# the sobject-named ____source pill). Any upstream drift fails validation
# instead of silently changing ground truth.
_STRUCTURE_PINS_JSON = r'''
[
 {
  "as": "4cc98c36",
  "input": {
   "dynamic_menu_name": "Retrieve FV Owners",
   "parameters": "[\n  {\n    \"name\": \"fv_owner\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\",\n    \"label\": \"Fv owner\"\n  }\n]"
  },
  "keyword": "trigger",
  "name": "dynamic_menu",
  "number": 1,
  "provider": "slack_bot",
  "skip": false
 },
 {
  "as": "8661bd72",
  "input": {
   "limit": "150",
   "query": "Email like '%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4cc98c36\",\"path\":[\"typeahead\", \"value\"]}')}%'",
   "sobject_name": "User"
  },
  "keyword": "action",
  "name": "search_sobjects_soql",
  "number": 2,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "3c75f8f0",
  "input": {
   "options": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"8661bd72\",\"path\":[\"User\"]}')}",
    "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"8661bd72\",\"path\":[\"User\", {\"path_element_type\": \"current_item\"}, \"Email\"]}')}",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"8661bd72\",\"path\":[\"User\", {\"path_element_type\": \"current_item\"}, \"Email\"]}')}"
   }
  },
  "keyword": "action",
  "name": "generate_menu_options",
  "number": 3,
  "provider": "slack_bot",
  "skip": false
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
BRANCHES = (
    "match_email_substring",
    "match_case_insensitive",
    "no_match",
    "full_email_match",
)


def _structure(node: dict[str, Any]) -> list[dict[str, Any]]:
    pin: dict[str, Any] = {
        "keyword": node.get("keyword"),
        "number": node.get("number"),
        "as": node.get("as"),
        "provider": node.get("provider"),
        "name": node.get("name"),
        "skip": bool(node.get("skip")),
        "input": node.get("input") or {},
    }
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_108350601(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger line id changed: {raw.get('as')!r}")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: "
            f"{len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} "
                f"(step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": pin["number"],
                "provider": pin["provider"],
                "name": pin["name"],
                "as": pin["as"],
            }
            for pin in actions
        ],
    }


def seed_108350601(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108350601(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    branch = _require_expect_shape(data)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    _require_salesforce_section(seed_in.get("salesforce"))
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _current_user_ref_tokens(provision)
    trigger = _replace_value(trigger, refs)
    _require_no_tokens(trigger, "trigger")
    resolved_typeahead = str((trigger.get("typeahead") or {}).get("value") or "")
    if any(ch in resolved_typeahead for ch in ("%", "'", "\\")):
        # '_' stays allowed: emails may carry literal underscores and the
        # single-char wildcard self-matches its own literal, so substring
        # re-computation still agrees for email-derived patterns.
        raise RuntimeError(
            f"recipe {RECIPE_ID} resolved typeahead.value lands inside the "
            f"%-wrapped LIKE pattern: a %/quote/escape would change the predicate "
            f"the verifier re-computes with plain substring semantics; got "
            f"{resolved_typeahead!r}"
        )
    resolved_expect = _replace_value(deepcopy(data.get("expect")), refs)
    _require_no_tokens(resolved_expect, "expect")
    _require_branch_typeahead(branch, trigger, refs)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track"),
        "raw_validation": validation,
        "trigger": trigger,
        "expect": resolved_expect,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
    }
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch block: a forced action error would "
            "fail the whole job, which is not a recipe branch"
        )
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_108350601(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108350601(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    if not (cleanup_response or {}).get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_108350601(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"typeahead", "parameters"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly typeahead + "
            f"parameters (the dynamic_menu payload with the declared required "
            f"fv_owner param); got {sorted(trigger)}"
        )
    typeahead = trigger.get("typeahead")
    if not isinstance(typeahead, dict) or set(typeahead) != {"value"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger typeahead must be exactly {{'value'}}; got {typeahead!r}"
        )
    if not isinstance(typeahead.get("value"), str) or not typeahead["value"].strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger typeahead.value must be a non-empty string")
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or set(parameters) != {"fv_owner"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly the declared "
            f"required fv_owner (seeded for faith; the recipe never derefs it); got "
            f"{parameters!r}"
        )
    fv_owner = parameters.get("fv_owner")
    if not isinstance(fv_owner, str) or not fv_owner.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.fv_owner must be a non-empty string")
    if fv_owner == typeahead["value"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.fv_owner must differ from typeahead.value "
            "so the exact-args pin actually proves the parameter is inert"
        )


def _require_expect_shape(data: dict[str, Any]) -> str:
    expect = data.get("expect")
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    if not isinstance(expect.get("tools"), list) or not isinstance(expect.get("tool_expectations"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect must pin tools and tool_expectations lists")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch must be one of {sorted(BRANCHES)}; got {branch!r}"
        )
    if not isinstance(expect.get("menu_options"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.menu_options must pin the exact options list")
    if expect.get("executed_action_count") != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} is branchless: both steps run on every variant "
            f"(executed_action_count must be 2); got {expect.get('executed_action_count')!r}"
        )
    return str(branch)


def _require_salesforce_section(section: Any) -> None:
    expected = {"strict_soql_conditions": True, "current_user": {"sobject": "User"}}
    if section != expected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly {expected!r} -- the "
            f"User search is served ONLY by the read-only current-user registration "
            f"(org Users are uncreatable/undeletable); got {section!r}"
        )


def _current_user_ref_tokens(provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    records = [record for record in salesforce_snapshot.get("records") or [] if isinstance(record, dict)]
    owned = [record for record in records if not record.get("read_only")]
    read_only_users = [
        record for record in records
        if record.get("read_only") and str(record.get("sobject") or "").lower() == "user"
    ]
    if owned:
        raise RuntimeError(f"recipe {RECIPE_ID} seeds no owned records; got {owned}")
    if len(read_only_users) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected exactly one read-only current-user row; "
            f"got {len(read_only_users)}"
        )
    row = read_only_users[0]
    user_id = str(row.get("id") or "")
    fields = row.get("fields") if isinstance(row.get("fields"), dict) else {}
    user_name = str(fields.get("Name") or "")
    email = str(fields.get("Email") or fields.get("Username") or "")
    if not _SF_ID_RE.fullmatch(user_id):
        raise RuntimeError(f"recipe {RECIPE_ID} current-user id looks invalid: {user_id!r}")
    if not user_name.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} current-user row has no Name")
    if len(email) < 4 or "@" not in email or not any(ch.isalpha() for ch in email):
        raise RuntimeError(
            f"recipe {RECIPE_ID} current-user email is too trivial to build "
            f"substring/case-fold variants from: {email!r}"
        )
    if email != email.lower():
        raise RuntimeError(
            f"recipe {RECIPE_ID} current-user email must be stored lowercase so the "
            f"uppercased-typeahead variant genuinely proves LIKE case-insensitivity; "
            f"got {email!r}"
        )
    core = email[1:-1]
    return {
        "$CURRENT_USER_EMAIL_CORE_UPPER": core.upper(),
        "$CURRENT_USER_EMAIL_CORE": core,
        "$CURRENT_USER_EMAIL": email,
        "$CURRENT_USER_NAME": user_name,
        "$CURRENT_USER_ID": user_id,
    }


def _require_branch_typeahead(branch: str, trigger: dict[str, Any], refs: dict[str, str]) -> None:
    value = str((trigger.get("typeahead") or {}).get("value") or "")
    email = refs["$CURRENT_USER_EMAIL"]
    if branch == "match_email_substring":
        ok = value == email[1:-1]
    elif branch == "match_case_insensitive":
        ok = value == email[1:-1].upper() and value != value.lower()
    elif branch == "no_match":
        ok = value.lower() not in email.lower()
    else:  # full_email_match
        ok = value == email
    if not ok:
        raise RuntimeError(
            f"recipe {RECIPE_ID} branch {branch!r} typeahead does not satisfy the "
            f"branch's relation to the live current-user email: value={value!r} "
            f"email={email!r}"
        )


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        # Longest token first: $CURRENT_USER_EMAIL is a prefix of the derived
        # tokens and must never clobber them.
        for token in sorted(refs, key=len, reverse=True):
            out = out.replace(token, refs[token])
        return out
    return value


def _require_no_tokens(value: Any, label: str) -> None:
    leftover = sorted(set(_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("salesforce_live"), dict):
        return ctx.tools.call("harness.salesforce.snapshot", {})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
