from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118427850


RECIPE_ID = "118427850"
SEED_TYPE = "salesforce_bizible_touchpoint_landing_page_backfill_variant"
TRACK = "live_salesforce_sheets_bizible_touchpoint_backfill"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
# Salesforce new Campaign_Activity__c trigger (as 275f1578; field_list 12 cols;
# OR-filter on 4 hardcoded Campaign__c ids) -> IF#2 repeated_job is_not_true ->
# clock.wait 7200 -> CA re-search by trigger Id (65274018) ->
#  IF#5 Bizible_Touchpoint__c present:
#    touchpoint search by Id (c1aea3da) -> update#7 CA bizible URL fields
#    (presence-or-skip chains; Landing_Page__c = Form/Landing/AdDest 3-way) ->
#    CA re-read (b34eb31d) -> IF#9 Landing_Page__c present -> STOP#10;
#    TRY sheets search (be9b46dd) CATCH#13 (empty, max_retry 0) ->
#    IF#14 'col_Please link the Landing Page' present -> update#15 + STOP#16.
#  ELSE#17 -> IF#18 (Lead_Source__c contains 'Paid' OR trigger Campaign__c =
#  7013l000001ZKOcAAO) gates the PAID families:
#    IF#19 Contact__c present -> bizible person by contact (e9551436) ->
#      IF#21 size>0 -> touchpoints by person (3a187aee) -> FOREACH accumulate
#      'bizible touchpoint list' -> smart_list create(force)+query (SELECT 7
#      cols ORDER BY touchpoint_date desc) -> logger = CA CreatedDate.to_date()
#      -> FOREACH rows: IF#29 paid-row OR -> IF#30 3-arm date window (<= CA
#      created + 86400s) -> update#31 + re-read -> IF#33 LP present -> STOP#34;
#      TRY sheets (205363b2) -> IF#38 col present -> update#39 + STOP#40.
#    IF#41 Lead__c present -> exact lead mirror (42..62).
#    STOP#63 (UNCONDITIONAL) -> non-paid families 64..95 reachable ONLY when
#    IF#18 is false: contact mirror (64..79) and lead mirror (80..95) with the
#    paid-row IF inverted to AND(not_contains, not_equals) and NO sheets
#    fallback.
# All stops are stop_with_error=false.
#
# Backends: Salesforce LIVE (Campaign_Activity__c physical==logical;
# bizible2__Bizible_Person__c / bizible2__Bizible_Touchpoint__c mapped to the
# benchmark-owned Bizible_Person__c / Bizible_Touchpoint__c stand-ins via
# SALESFORCE_SOBJECT_MAP / SALESFORCE_FIELD_MAP, deployed 2026-07-07).
# Google Sheets LIVE (criteria-less page read; the raw spreadsheet/tab is
# redirected to the configured benchmark sheet; the seed writes the literal
# 'col_Please link the Landing Page' header per the 104417970 precedent).
# workato_list / workato_smart_list / logger / clock are deterministic
# Workato-internal mocks.
#
# DETERMINISM: the date-window IFs compare seeded touchpoint dates against the
# LIVE CA CreatedDate (org-assigned wall clock). In-window variants seed
# far-PAST touchpoint dates (arm 2 'less_than' always true); out-of-window
# variants far-FUTURE dates (all 3 arms false). Never seed near-now dates.
# Cleanup: every seeded Salesforce record is benchmark-owned and deleted after
# verification (fail-fast on leftovers); the sheets seed fully overwrites the
# benchmark tab per run, so no separate sheets cleanup is required.

CAMPAIGN_IDS: tuple[str, ...] = (
    "7011N000000xp4nQAA",
    "7011N000000TW0aQAG",
    "7013l000001ZKOcAAO",
    "7013l000001BceiAAC",
)
CA_SOBJECT = "Campaign_Activity__c"
PERSON_SOBJECT = "bizible2__Bizible_Person__c"
TP_SOBJECT = "bizible2__Bizible_Touchpoint__c"
SHEET_COL = "col_Please link the Landing Page"
CA_ID_TOKEN = "$CA_ID"
_REF_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*_ID")

TRIGGER_FIELD_LIST = (
    "Id\nOwnerId\nName\nCreatedDate\nActivity_Created_At__c\nLanding_Page__c\n"
    "Bizible_Touchpoint__c\nEmail__c\nCompany_Name__c\nCampaign__c\nContact__c\nLead__c"
)
TRIGGER_SINCE = "<anon>2024-01-01T00:00:00-07:00</anon>"
CA_FIELD_LIST = (
    "Id\nOwnerId\nName\nCreatedDate\nCampaign__c\nLead__c\nContact__c\nEmail__c\n"
    "Landing_Page__c\nBizible_Touchpoint__c\nActivity_Created_At__c\nLead_Source__c\nRegion__c"
)
# Step 6 (touchpoint by Id) omits Touchpoint_Date; the per-person searches carry it.
TP_FIELD_LIST_NO_DATE = (
    "Id\nName\nCreatedDate\nbizible2__Marketing_Channel_Path__c\nbizible2__Marketing_Channel__c\n"
    "bizible2__Landing_Page__c\nbizible2__Landing_Page_Raw__c\nbizible2__Form_URL_Raw__c\n"
    "bizible2__Form_URL__c\nbizible2__Ad_Destination_URL__c\nbizible2__Ad_Campaign_Name__c\n"
    "bizible2__Referrer_Page__c"
)
TP_FIELD_LIST = (
    "Id\nName\nCreatedDate\nbizible2__Marketing_Channel_Path__c\nbizible2__Marketing_Channel__c\n"
    "bizible2__Landing_Page__c\nbizible2__Landing_Page_Raw__c\nbizible2__Form_URL_Raw__c\n"
    "bizible2__Form_URL__c\nbizible2__Ad_Destination_URL__c\nbizible2__Touchpoint_Date__c\n"
    "bizible2__Ad_Campaign_Name__c\nbizible2__Referrer_Page__c"
)
PERSON_FIELD_LIST = (
    "Id\nCreatedDate\nName\nOwnerId\nbizible2__UniqueId__c\nbizible2__Lead__c\nbizible2__Contact__c"
)
SHEETS_ACTION_INPUT: dict[str, Any] = {
    "count": "200",
    "sheet": "Master Google Campaigns Add here",
    "spreadsheet": "<anon>2PqR8StU9VwX0YzA1BcD2EfG3HiJ4KlM5NoPqRsT6Uv</anon>",
    "team_drives": "my_drive",
}
STOP_INPUT: dict[str, Any] = {"stop_with_error": "false"}
CATCH_INPUT: dict[str, Any] = {"max_retry_count": "0", "retry_interval": "2"}
ACCUMULATE_SCHEMA_JSON = (
    '[{"name":"touchpoint_date","type":"string","optional":true,"label":"touchpoint date",'
    '"details":{"real_name":"touchpoint date"},"control_type":"text"},'
    '{"name":"marketing_channel","type":"string","optional":true,"label":"marketing channel",'
    '"details":{"real_name":"marketing channel"},"control_type":"text"},'
    '{"name":"landing_page","type":"string","optional":true,"label":"landing page",'
    '"details":{"real_name":"landing page"},"control_type":"text"},'
    '{"name":"form_url","type":"string","optional":true,"label":"form url",'
    '"details":{"real_name":"form url"},"control_type":"text"},'
    '{"name":"ad_campaign_name","type":"string","optional":true,"label":"ad campaign name",'
    '"details":{"real_name":"ad campaign name"},"control_type":"text"},'
    '{"name":"bizibletouchpoint","type":"string","optional":true,"label":"bizibletouchpoint",'
    '"details":{"real_name":"bizibletouchpoint"},"control_type":"text"},'
    '{"name":"referrer_page","type":"string","optional":true,"label":"referrer page",'
    '"details":{"real_name":"referrer page"},"control_type":"text"}]'
)
QUERY_RESULT_SCHEMA_JSON = (
    '[{"name":"touchpointdate","type":"string","optional":false,"control_type":"text","label":"Touchpointdate"},'
    '{"name":"marketingchannel","type":"string","optional":false,"control_type":"text","label":"Marketingchannel"},'
    '{"name":"landingpage","type":"string","optional":true,"control_type":"text","label":"Landingpage"},'
    '{"name":"formurl","type":"string","optional":true,"control_type":"text","label":"Formurl"},'
    '{"name":"adcampaignname","type":"string","optional":true,"control_type":"text","label":"Adcampaignname"},'
    '{"name":"bizibletouchpoint","type":"string","optional":true,"control_type":"text","label":"Bizibletouchpoint"},'
    '{"name":"referrerpage","type":"string","optional":true,"control_type":"text","label":"Referrerpage"}]'
)

# --- verbatim datapill templates (spacing/quoting exactly as in the raw JSON) ---


def _trigger_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\","
        "\"line\":\"275f1578\",\"path\":[\"%s\"]}')}" % field
    )


def _ca_ci_pill(line: str, field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"%s\","
        "\"path\":[\"Campaign_Activity__c\", {\"path_element_type\": \"current_item\"}, \"%s\"]}')}"
        % (line, field)
    )


def _tp_field_formula(line: str, field: str) -> str:
    return (
        "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"%s\","
        "\"path\":[\"bizible2__Bizible_Touchpoint__c\",{\"path_element_type\":\"current_item\"},\"%s\"]}').presence"
        % (line, field)
    )


def _person_ci_id_pill(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"%s\","
        "\"path\":[\"bizible2__Bizible_Person__c\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
        % line
    )


def _list_size_pill(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"%s\","
        "\"path\":[\"list_size\"]}')}" % line
    )


def _tp_list_pill(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"%s\","
        "\"path\":[\"bizible2__Bizible_Touchpoint__c\"]}')}" % line
    )


def _foreach_pill(line: str, field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"%s\","
        "\"path\":[\"%s\"]}')}" % (line, field)
    )


def _foreach_formula(line: str, field: str) -> str:
    return (
        "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"%s\","
        "\"path\":[\"%s\"]}')" % (line, field)
    )


def _smart_list_col_pill(line: str, column: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"%s\","
        "\"path\":[\"columns\", \"%s\"]}')}" % (line, column)
    )


def _smart_list_name_pill(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"%s\","
        "\"path\":[\"list_name\"]}')}" % line
    )


def _smart_list_rows_pill(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"%s\","
        "\"path\":[\"rows\"]}')}" % line
    )


def _sheets_col_pill(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"%s\","
        "\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"%s\"]}')}" % (line, SHEET_COL)
    )


def _sheets_col_formula(line: str) -> str:
    return (
        "=_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"%s\","
        "\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"%s\"]}').presence or skip"
        % (line, SHEET_COL)
    )


def _logger_message_formula() -> str:
    return (
        "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65274018\","
        "\"path\":[\"Campaign_Activity__c\",{\"path_element_type\":\"current_item\"},\"CreatedDate\"]}').to_date()"
    )


def _window_lhs(foreach_line: str) -> str:
    return _foreach_formula(foreach_line, "touchpointdate") + ".to_time"


def _window_rhs(logger_line: str) -> str:
    return (
        "=_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"%s\","
        "\"path\":[\"message\"]}').to_time" % logger_line
    )


def _compound(operand: str, conditions: list[dict[str, str]]) -> dict[str, Any]:
    return {"conditions": conditions, "operand": operand, "type": "compound"}


def _cond(lhs: str, operand: str, rhs: str = "") -> dict[str, str]:
    return {"lhs": lhs, "operand": operand, "rhs": rhs}


def _ca_search_input() -> dict[str, Any]:
    return {
        "Id": _trigger_pill("Id"),
        "field_list": CA_FIELD_LIST,
        "limit": "150",
        "sobject_name": CA_SOBJECT,
    }


def _query_sql(create_line: str) -> str:
    columns = [
        "touchpoint_date",
        "marketing_channel",
        "landing_page",
        "form_url",
        "ad_campaign_name",
        "bizibletouchpoint",
        "referrer_page",
    ]
    select = ", ".join(_smart_list_col_pill(create_line, column) for column in columns)
    return (
        "SELECT %s FROM %s ORDER BY %s desc"
        % (select, _smart_list_name_pill(create_line), _smart_list_col_pill(create_line, "touchpoint_date"))
    )


def _accumulate_input(foreach_line: str) -> dict[str, Any]:
    return {
        "list_item": {
            "data": {
                "ad_campaign_name": _foreach_pill(foreach_line, "bizible2__Ad_Campaign_Name__c"),
                "bizibletouchpoint": _foreach_pill(foreach_line, "Name"),
                "form_url": _foreach_pill(foreach_line, "bizible2__Form_URL__c"),
                "landing_page": _foreach_pill(foreach_line, "bizible2__Landing_Page__c"),
                "marketing_channel": _foreach_pill(foreach_line, "bizible2__Marketing_Channel__c"),
                "referrer_page": _foreach_pill(foreach_line, "bizible2__Referrer_Page__c"),
                "touchpoint_date": _foreach_formula(foreach_line, "bizible2__Touchpoint_Date__c") + ".to_date()",
            },
            "schema": ACCUMULATE_SCHEMA_JSON,
        },
        "name": "bizible touchpoint list",
    }


def _rows_update_input(foreach_line: str) -> dict[str, Any]:
    return {
        "Bizible_Form_URL__c": _foreach_formula(foreach_line, "formurl") + ".presence or skip",
        "Bizible_Landing_Page__c": _foreach_formula(foreach_line, "landingpage") + ".presence or skip",
        "Bizible_Referrer_Page__c": _foreach_formula(foreach_line, "referrerpage") + ".presence or skip",
        "Bizible_Touchpoint__c": _foreach_formula(foreach_line, "bizibletouchpoint") + ".presence or skip",
        "Landing_Page__c": (
            _foreach_formula(foreach_line, "formurl")
            + ".presence or "
            + _foreach_formula(foreach_line, "landingpage")[1:]
            + ".presence or skip"
        ),
        "id": _ca_ci_pill("65274018", "Id"),
        "sobject_name": CA_SOBJECT,
    }


def _sheet_update_input(sheets_line: str) -> dict[str, Any]:
    return {
        "Landing_Page__c": _sheets_col_formula(sheets_line),
        "id": _ca_ci_pill("65274018", "Id"),
        "sobject_name": CA_SOBJECT,
    }


TRIGGER_INPUT_EXPECTED: dict[str, Any] = {
    "field_list": TRIGGER_FIELD_LIST,
    "since": TRIGGER_SINCE,
    "sobject_name": CA_SOBJECT,
}
TRIGGER_FILTER_EXPECTED: dict[str, Any] = _compound(
    "or",
    [_cond(_trigger_pill("Campaign__c"), "equals_to", campaign_id) for campaign_id in CAMPAIGN_IDS],
)


# The four mirrored person->touchpoint families, parametrized by their step
# line ids and numbers so the mirrors are generated (triage: avoid
# transcription drift). paid=True families use the OR paid-row IF and carry the
# TRY/sheets fallback; paid=False families use the AND not-paid IF, no sheets.
FAMILIES: dict[str, dict[str, Any]] = {
    "contact_paid": {
        "gate_number": 19, "gate_field": "Contact__c", "person_filter": "bizible2__Contact__c",
        "person": "e9551436", "tps": "3a187aee", "tp_foreach": "08d8bf0b", "accumulate": "8e27070c",
        "create": "024c7f44", "query": "9103d732", "logger": "14226a38", "rows_foreach": "eb9564c6",
        "update": "b410fe47", "reread": "9dd1aea3",
        "numbers": {"person": 20, "size_if": 21, "tps": 22, "tp_foreach": 23, "accumulate": 24,
                     "create": 25, "query": 26, "logger": 27, "rows_foreach": 28, "row_if": 29,
                     "window_if": 30, "update": 31, "reread": 32, "lp_if": 33, "stop": 34,
                     "try": 35, "sheets": 36, "catch": 37, "sheet_if": 38, "sheet_update": 39,
                     "sheet_stop": 40},
        "paid": True, "sheets": "205363b2", "catch": "4a01c237", "sheet_update": "d825678f",
        "stop_as": "4fc12de2", "sheet_stop_as": "6017d701",
        # contact-paid: TRY/sheets fallback is a SIBLING of the window IF#30
        # (inside IF#29) — it runs for every paid row, window hit or not.
        "sheets_in_window": False,
    },
    "lead_paid": {
        "gate_number": 41, "gate_field": "Lead__c", "person_filter": "bizible2__Lead__c",
        "person": "570a25c1", "tps": "562da63a", "tp_foreach": "f21d984e", "accumulate": "492e1d84",
        "create": "d98a63bd", "query": "5f25d219", "logger": "6903e834", "rows_foreach": "08fea4a3",
        "update": "03a4a07b", "reread": "d159444c",
        "numbers": {"person": 42, "size_if": 43, "tps": 44, "tp_foreach": 45, "accumulate": 46,
                     "create": 47, "query": 48, "logger": 49, "rows_foreach": 50, "row_if": 51,
                     "window_if": 52, "update": 53, "reread": 54, "lp_if": 55, "stop": 56,
                     "try": 57, "sheets": 58, "catch": 59, "sheet_if": 60, "sheet_update": 61,
                     "sheet_stop": 62},
        "paid": True, "sheets": "d110ee63", "catch": "6db36320", "sheet_update": "0ebe49d8",
        "stop_as": "088fc60d", "sheet_stop_as": "6202b5b3",
        # lead-paid asymmetry (verified against the raw JSON): TRY#57/IF#60 are
        # nested INSIDE the window IF#52, so the lead sheets fallback only runs
        # for a paid row that is ALSO in-window and still has no Landing_Page__c.
        "sheets_in_window": True,
    },
    "contact_nonpaid": {
        "gate_number": 64, "gate_field": "Contact__c", "person_filter": "bizible2__Contact__c",
        "person": "3d75b9ee", "tps": "783d37c6", "tp_foreach": "4807203d", "accumulate": "4d749d2b",
        "create": "34e80465", "query": "be7a2911", "logger": "bc90299d", "rows_foreach": "5a480411",
        "update": "6bf747d5", "reread": "611508a2",
        "numbers": {"person": 65, "size_if": 66, "tps": 67, "tp_foreach": 68, "accumulate": 69,
                     "create": 70, "query": 71, "logger": 72, "rows_foreach": 73, "row_if": 74,
                     "window_if": 75, "update": 76, "reread": 77, "lp_if": 78, "stop": 79},
        "paid": False, "stop_as": "5ba16c28",
    },
    "lead_nonpaid": {
        "gate_number": 80, "gate_field": "Lead__c", "person_filter": "bizible2__Lead__c",
        "person": "5f109d4c", "tps": "03aa4ae2", "tp_foreach": "6c99c1c5", "accumulate": "ebffb9f6",
        "create": "fb8e4439", "query": "40af8ad2", "logger": "91287882", "rows_foreach": "24a56f27",
        "update": "9174c2db", "reread": "abc1fbbe",
        "numbers": {"person": 81, "size_if": 82, "tps": 83, "tp_foreach": 84, "accumulate": 85,
                     "create": 86, "query": 87, "logger": 88, "rows_foreach": 89, "row_if": 90,
                     "window_if": 91, "update": 92, "reread": 93, "lp_if": 94, "stop": 95},
        "paid": False, "stop_as": "6a183f28",
    },
}


def _node(depth: int, number: int, keyword: str, provider: str, name: str, as_: str,
          node_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "depth": depth, "number": number, "keyword": keyword, "provider": provider,
        "name": name, "as": as_, "input": node_input,
    }


def _family_nodes(family: dict[str, Any], depth: int) -> list[dict[str, Any]]:
    numbers = family["numbers"]
    foreach_line = family["rows_foreach"]
    logger_line = family["logger"]
    if family["paid"]:
        row_if = _compound("or", [
            _cond(_foreach_pill(foreach_line, "marketingchannel"), "contains", "Paid"),
            _cond(_foreach_pill(foreach_line, "adcampaignname"), "equals_to", "WF-Demo Intercom Paid"),
        ])
    else:
        row_if = _compound("and", [
            _cond(_foreach_pill(foreach_line, "marketingchannel"), "not_contains", "Paid"),
            _cond(_foreach_pill(foreach_line, "adcampaignname"), "not_equals_to", "WF-Demo Intercom Paid"),
        ])
    window_if = _compound("or", [
        _cond(_window_lhs(foreach_line), "equals_to", _window_rhs(logger_line)),
        _cond(_window_lhs(foreach_line), "less_than", _window_rhs(logger_line)),
        _cond(_window_lhs(foreach_line) + " - " + _window_rhs(logger_line)[1:], "less_than", "86401"),
    ])
    nodes = [
        _node(depth, family["gate_number"], "if", "", "", "",
              _compound("and", [_cond(_trigger_pill(family["gate_field"]), "present")])),
        _node(depth + 1, numbers["person"], "action", "salesforce", "search_sobjects", family["person"], {
            family["person_filter"]: _trigger_pill(family["gate_field"]),
            "field_list": PERSON_FIELD_LIST,
            "limit": "150",
            "sobject_name": PERSON_SOBJECT,
        }),
        _node(depth + 1, numbers["size_if"], "if", "", "", "",
              _compound("and", [_cond(_list_size_pill(family["person"]), "greater_than", "0")])),
        _node(depth + 2, numbers["tps"], "action", "salesforce", "search_sobjects", family["tps"], {
            "bizible2__Bizible_Person__c": _person_ci_id_pill(family["person"]),
            "field_list": TP_FIELD_LIST,
            "limit": "150",
            "sobject_name": TP_SOBJECT,
        }),
        _node(depth + 2, numbers["tp_foreach"], "foreach", "", "", family["tp_foreach"],
              {"source": _tp_list_pill(family["tps"])}),
        _node(depth + 3, numbers["accumulate"], "action", "workato_list", "accumulate_list_items",
              family["accumulate"], _accumulate_input(family["tp_foreach"])),
        _node(depth + 2, numbers["create"], "action", "workato_smart_list", "create_list", family["create"], {
            "force": "true",
            "list_name": "bizible touchpoint list",
            "list_source": (
                "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"%s\","
                "\"path\":[\"list_items\"]}')" % family["accumulate"]
            ),
        }),
        _node(depth + 2, numbers["query"], "action", "workato_smart_list", "query_list", family["query"], {
            "col_sep": "comma",
            "csv": "false",
            "headers": "false",
            "output_schema_by": "index",
            "result_schema_json": QUERY_RESULT_SCHEMA_JSON,
            "sql": _query_sql(family["create"]),
        }),
        _node(depth + 2, numbers["logger"], "action", "logger", "log_message", family["logger"], {
            "message": _logger_message_formula(),
            "user_logs_enabled": "false",
        }),
        _node(depth + 2, numbers["rows_foreach"], "foreach", "", "", family["rows_foreach"],
              {"source": _smart_list_rows_pill(family["query"])}),
        _node(depth + 3, numbers["row_if"], "if", "", "", "", row_if),
        _node(depth + 4, numbers["window_if"], "if", "", "", "", window_if),
        _node(depth + 5, numbers["update"], "action", "salesforce", "update_sobject", family["update"],
              _rows_update_input(foreach_line)),
        _node(depth + 5, numbers["reread"], "action", "salesforce", "search_sobjects", family["reread"],
              _ca_search_input()),
        _node(depth + 5, numbers["lp_if"], "if", "", "", "",
              _compound("and", [_cond(_ca_ci_pill(family["reread"], "Landing_Page__c"), "present")])),
        _node(depth + 6, numbers["stop"], "stop", "", "", family["stop_as"], dict(STOP_INPUT)),
    ]
    if family["paid"]:
        sheets_depth = depth + 4 + (1 if family["sheets_in_window"] else 0)
        nodes.extend([
            _node(sheets_depth, numbers["try"], "try", "", "", "", {}),
            _node(sheets_depth + 1, numbers["sheets"], "action", "google_sheets",
                  "search_spreadsheet_rows_v4_new", family["sheets"], dict(SHEETS_ACTION_INPUT)),
            _node(sheets_depth + 1, numbers["catch"], "catch", "", "", family["catch"], dict(CATCH_INPUT)),
            _node(sheets_depth, numbers["sheet_if"], "if", "", "", "",
                  _compound("and", [_cond(_sheets_col_pill(family["sheets"]), "present")])),
            _node(sheets_depth + 1, numbers["sheet_update"], "action", "salesforce", "update_sobject",
                  family["sheet_update"], _sheet_update_input(family["sheets"])),
            _node(sheets_depth + 1, numbers["sheet_stop"], "stop", "", "", family["sheet_stop_as"],
                  dict(STOP_INPUT)),
        ])
    return nodes


def _expected_nodes() -> list[dict[str, Any]]:
    nodes = [
        _node(1, 2, "if", "", "", "",
              _compound("and", [_cond(
                  "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"repeated_job\"]}')}",
                  "is_not_true")])),
        _node(2, 3, "action", "clock", "wait_for_interval", "2b5f87f1", {"interval": "7200"}),
        _node(1, 4, "action", "salesforce", "search_sobjects", "65274018", _ca_search_input()),
        _node(1, 5, "if", "", "", "",
              _compound("and", [_cond(_ca_ci_pill("65274018", "Bizible_Touchpoint__c"), "present")])),
        _node(2, 6, "action", "salesforce", "search_sobjects", "c1aea3da", {
            "Id": _ca_ci_pill("65274018", "Bizible_Touchpoint__c"),
            "field_list": TP_FIELD_LIST_NO_DATE,
            "limit": "150",
            "sobject_name": TP_SOBJECT,
        }),
        _node(2, 7, "action", "salesforce", "update_sobject", "fdae5bc3", {
            "Bizible_Form_URL__c": _tp_field_formula("c1aea3da", "bizible2__Form_URL__c") + " or skip",
            "Bizible_Landing_Page__c": _tp_field_formula("c1aea3da", "bizible2__Landing_Page__c") + " or skip",
            "Bizible_Referrer_Page__c": _tp_field_formula("c1aea3da", "bizible2__Referrer_Page__c") + " or skip",
            "Landing_Page__c": (
                _tp_field_formula("c1aea3da", "bizible2__Form_URL__c")
                + " or "
                + _tp_field_formula("c1aea3da", "bizible2__Landing_Page__c")[1:]
                + " or "
                + _tp_field_formula("c1aea3da", "bizible2__Ad_Destination_URL__c")[1:]
                + " or skip"
            ),
            "id": _ca_ci_pill("65274018", "Id"),
            "sobject_name": CA_SOBJECT,
        }),
        _node(2, 8, "action", "salesforce", "search_sobjects", "b34eb31d", _ca_search_input()),
        _node(2, 9, "if", "", "", "",
              _compound("and", [_cond(_ca_ci_pill("b34eb31d", "Landing_Page__c"), "present")])),
        _node(3, 10, "stop", "", "", "", dict(STOP_INPUT)),
        _node(2, 11, "try", "", "", "", {}),
        _node(3, 12, "action", "google_sheets", "search_spreadsheet_rows_v4_new", "be9b46dd",
              dict(SHEETS_ACTION_INPUT)),
        _node(3, 13, "catch", "", "", "c84bedec", dict(CATCH_INPUT)),
        _node(2, 14, "if", "", "", "",
              _compound("and", [_cond(_sheets_col_pill("be9b46dd"), "present")])),
        _node(3, 15, "action", "salesforce", "update_sobject", "06ad85d6", _sheet_update_input("be9b46dd")),
        _node(3, 16, "stop", "", "", "678d6278", dict(STOP_INPUT)),
        _node(2, 17, "else", "", "", "", {}),
        _node(3, 18, "if", "", "", "", _compound("or", [
            _cond(_ca_ci_pill("65274018", "Lead_Source__c"), "contains", "Paid"),
            _cond(_trigger_pill("Campaign__c"), "equals_to", "7013l000001ZKOcAAO"),
        ])),
    ]
    nodes.extend(_family_nodes(FAMILIES["contact_paid"], 4))
    nodes.extend(_family_nodes(FAMILIES["lead_paid"], 4))
    nodes.append(_node(4, 63, "stop", "", "", "f0d0e7b7", dict(STOP_INPUT)))
    nodes.extend(_family_nodes(FAMILIES["contact_nonpaid"], 3))
    nodes.extend(_family_nodes(FAMILIES["lead_nonpaid"], 3))
    return nodes


def _walk_nodes(node: dict[str, Any], depth: int = 0) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if depth > 0:
        out.append({
            "depth": depth,
            "number": node.get("number"),
            "keyword": str(node.get("keyword") or ""),
            "provider": str(node.get("provider") or ""),
            "name": str(node.get("name") or ""),
            "as": str(node.get("as") or ""),
            "input": node.get("input") if isinstance(node.get("input"), dict) else {},
        })
        if node.get("skip"):
            raise RuntimeError(f"recipe {RECIPE_ID} step {node.get('number')} is now skipped")
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} raw block contains a non-object node")
        out.extend(_walk_nodes(child, depth + 1))
    return out


def validate_118427850(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != "275f1578":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger line id changed: {raw.get('as')}")
    if raw.get("input") != TRIGGER_INPUT_EXPECTED:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input changed: {raw.get('input')}")
    if raw.get("filter") != TRIGGER_FILTER_EXPECTED:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter changed: {raw.get('filter')}")
    actual = _walk_nodes(raw)
    expected = _expected_nodes()
    if len(actual) != len(expected):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(expected)}"
        )
    for actual_node, expected_node in zip(actual, expected):
        for key in ("depth", "number", "keyword", "provider", "name", "as"):
            if actual_node[key] != expected_node[key]:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} step {actual_node['number']} {key} changed: "
                    f"{actual_node[key]!r} != {expected_node[key]!r}"
                )
        if actual_node["input"] != expected_node["input"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} step {actual_node['number']} input changed:\n"
                f"actual:   {actual_node['input']!r}\n"
                f"expected: {expected_node['input']!r}"
            )
    actions = [node for node in actual if node["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {"number": node["number"], "provider": node["provider"], "name": node["name"], "as": node["as"]}
            for node in actions
        ],
    }


# Every custom field the recipe (or its seeds) touches. ensure_custom_field
# grants FLS on the already-deployed fields; schema is a constant so a variant
# cannot silently drop a grant. Field names are PHYSICAL (the bizible2__
# sobject names map via SALESFORCE_SOBJECT_MAP).
REQUIRED_SCHEMA: list[dict[str, str]] = [
    {"sobject": CA_SOBJECT, "field": "Campaign__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Contact__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Lead__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Lead_Source__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Email__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Company_Name__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Region__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Activity_Created_At__c", "sf_type": "DateTime"},
    {"sobject": CA_SOBJECT, "field": "Landing_Page__c", "sf_type": "LongTextArea"},
    {"sobject": CA_SOBJECT, "field": "Bizible_Touchpoint__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Bizible_Form_URL__c", "sf_type": "LongTextArea"},
    {"sobject": CA_SOBJECT, "field": "Bizible_Landing_Page__c", "sf_type": "LongTextArea"},
    {"sobject": CA_SOBJECT, "field": "Bizible_Referrer_Page__c", "sf_type": "LongTextArea"},
    {"sobject": PERSON_SOBJECT, "field": "Contact__c", "sf_type": "Text"},
    {"sobject": PERSON_SOBJECT, "field": "Lead__c", "sf_type": "Text"},
    {"sobject": PERSON_SOBJECT, "field": "UniqueId__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Bizible_Person__c", "sf_type": "Lookup"},
    {"sobject": TP_SOBJECT, "field": "Marketing_Channel__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Marketing_Channel_Path__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Landing_Page__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Landing_Page_Raw__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Form_URL__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Form_URL_Raw__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Ad_Destination_URL__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Ad_Campaign_Name__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Referrer_Page__c", "sf_type": "Text"},
    {"sobject": TP_SOBJECT, "field": "Touchpoint_Date__c", "sf_type": "DateTime"},
]
EXPECT_REQUIRED_KEYS = (
    "tools", "tool_expectations", "trace_tools", "executed_action_count",
    "stopped", "sf_update_fields_exact", "final_ca", "final_ca_id",
)
EXPECTED_RAW_TOOLS: list[str] = [
    "clock.wait_for_interval",
    "salesforce.search_records",
    "salesforce.update_record",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "workato_runtime.accumulate_list_items",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "clock.wait_for_interval",
    "salesforce.search_records",
    "salesforce.update_record",
    "google_sheets.search_spreadsheet_rows_v4_new",
]


def _require_expect(expect: Any) -> dict[str, Any]:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_REQUIRED_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be an explicit boolean")
    if expect["stopped"] and "stop_step_number" not in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} stopped variants must pin expect.stop_step_number")
    if not isinstance(expect.get("sf_update_fields_exact"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.sf_update_fields_exact must be a list")
    return expect


def _validate_salesforce_seed(section: dict[str, Any], trigger: dict[str, Any]) -> list[dict[str, Any]]:
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the canonical "
            "REQUIRED_SCHEMA verbatim (FLS grants on every touched custom field)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    seen_refs: list[str] = []
    ca_records: list[dict[str, Any]] = []
    person_count = 0
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("fields"), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} salesforce seed records must carry fields objects")
        sobject = str(record.get("sobject") or "")
        ref = str(record.get("ref") or "")
        if sobject not in {CA_SOBJECT, PERSON_SOBJECT, TP_SOBJECT}:
            raise RuntimeError(f"recipe {RECIPE_ID} unexpected seed sobject {sobject!r}")
        if not ref or ref.upper() in seen_refs:
            raise RuntimeError(f"recipe {RECIPE_ID} every seed record needs a unique ref: {record}")
        fields = record["fields"]
        if not str(fields.get("Name") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} seed record {ref!r} must set an explicit Name")
        for key, value in fields.items():
            if isinstance(value, str):
                for token in _REF_TOKEN_RE.findall(value):
                    if token[1:-3].lower() not in [seen.lower() for seen in seen_refs]:
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} seed record {ref!r} field {key!r} references "
                            f"{token} before that record is created"
                        )
        if sobject == CA_SOBJECT:
            ca_records.append(record)
        if sobject == PERSON_SOBJECT:
            person_count += 1
        seen_refs.append(ref.upper())
    if len(ca_records) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must create exactly one {CA_SOBJECT} record")
    if person_count > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} person searches read current_item (first) — seed at most one person"
        )
    ca_fields = ca_records[0]["fields"]
    for field in ("Campaign__c", "Contact__c", "Lead__c"):
        if str(ca_fields.get(field) or "") != str(trigger.get(field) or ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} CA seed field {field} must match trigger_input "
                f"({ca_fields.get(field)!r} != {trigger.get(field)!r})"
            )
    return records


def _ref_ids(section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    seeded = [record for record in section.get("records") or []]
    snapshot_records = (((provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or [])
    if len(snapshot_records) != len(seeded):
        raise RuntimeError(
            f"recipe {RECIPE_ID} provision snapshot count mismatch: "
            f"{len(snapshot_records)} != {len(seeded)}"
        )
    refs: dict[str, str] = {}
    for record, snap in zip(seeded, snapshot_records):
        if str(snap.get("sobject") or "") != str(record.get("sobject") or ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} provision snapshot order mismatch: "
                f"{snap.get('sobject')} != {record.get('sobject')}"
            )
        record_id = str(snap.get("id") or "")
        if not record_id:
            raise RuntimeError(f"recipe {RECIPE_ID} provision snapshot record missing id: {snap}")
        refs["$%s_ID" % str(record.get("ref")).upper()] = record_id
    return refs


def _replace_tokens(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_tokens(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_no_tokens(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _require_no_tokens(item, f"{where}.{key}")
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            _require_no_tokens(item, f"{where}[{idx}]")
    elif isinstance(value, str) and _REF_TOKEN_RE.search(value):
        raise RuntimeError(f"recipe {RECIPE_ID} unresolved seed ref token in {where}: {value!r}")


def seed_118427850(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118427850(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if sorted(trigger.keys()) != sorted(["Id", "Campaign__c", "Contact__c", "Lead__c"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the dereferenced trigger "
            f"fields Id/Campaign__c/Contact__c/Lead__c; got {sorted(trigger.keys())}"
        )
    if trigger.get("Id") != CA_ID_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Id must be the {CA_ID_TOKEN} seed token "
            "(the live Campaign_Activity__c id is only known after provisioning)"
        )
    if not str(trigger.get("Campaign__c") or ""):
        # Both trigger-filter outcomes are benchmarked: one of the four
        # CAMPAIGN_IDS runs the touchpoint-sync path verbatim, any other
        # campaign id is the verified zero-action trigger-filter-false path.
        # Only a missing/blank Campaign__c is invalid input.
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Campaign__c must be an explicit campaign id; "
            f"got {trigger.get('Campaign__c')!r}"
        )
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or not isinstance(job_context.get("repeated_job"), bool):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin job_context.repeated_job as an "
            "explicit boolean (IF#2 reads it)"
        )
    expect = _require_expect(data.get("expect"))
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("salesforce"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    _validate_salesforce_seed(seed_in["salesforce"], trigger)
    expects_sheets_read = "google_sheets.search_spreadsheet_rows_v4_new" in (expect.get("tools") or [])
    forces_sheets_error = (
        str((data.get("force_action_error") or {}).get("step_as") or "") in {"be9b46dd", "205363b2", "d110ee63"}
    )
    sheets_seed = seed_in.get("sheets")
    if expects_sheets_read or forces_sheets_error:
        if not isinstance(sheets_seed, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} this variant reaches the sheets search — seed.sheets is required"
            )
        headers = sheets_seed.get("headers")
        rows = sheets_seed.get("rows")
        if not isinstance(headers, list) or SHEET_COL not in headers:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.sheets.headers must include the literal "
                f"{SHEET_COL!r} header (104417970 precedent)"
            )
        if not isinstance(rows, list) or not rows:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.sheets.rows must be a non-empty list "
                "(IF reads the first data row)"
            )
        if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
            raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets seed")
    elif sheets_seed is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} this variant never reads sheets — remove seed.sheets "
            "(variants must not carry dead seed state)"
        )
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _ref_ids(seed_in["salesforce"], provision)
    resolved_trigger = _replace_tokens(trigger, refs)
    _require_no_tokens(resolved_trigger, "trigger")
    resolved_expect = _replace_tokens(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": resolved_trigger,
        "track": data.get("track"),
        "expect": resolved_expect,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(sheets_seed, dict):
        sheets_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
        if not sheets_response.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} sheets seed failed: {sheets_response}")
        out["sheets"] = deepcopy(sheets_seed)
        out["sheets_seed_response"] = sheets_response
        out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_118427850(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118427850(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if isinstance(seed.get("sheets"), dict) and (
        not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab
    ):
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets read")
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context (IF#2 reads it)")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    try:
        details["initial_snapshot"] = _snapshot(ctx, seed)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, seed)
    finally:
        # Snapshot-then-cleanup: verification reads final_snapshot; the owned
        # Salesforce records (CA + person + touchpoints) are deleted here and
        # the verifier fails closed on leftovers.
        details["salesforce_cleanup"] = ctx.tools.call("harness.salesforce.cleanup", {})
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118427850(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    if isinstance(seed.get("sheets"), dict):
        out["google_sheets"] = ctx.tools.call("harness.google_sheets.snapshot", {})
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
