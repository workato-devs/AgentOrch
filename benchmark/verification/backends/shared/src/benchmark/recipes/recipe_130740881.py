from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130740881


RECIPE_ID = "130740881"
SEED_TYPE = "genie_tracked_opportunities_variant"
TRACK = "workato_genie_tracked_opportunities"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TRIGGER_AS = "30d84672"
TABLE_ID = "46815"
# Genie tool 'tracked opportunities' (trigger as 30d84672; parameters
# primaryScEmail / accountManagerEmail / opportunityId, all optional strings)
# over mock db table 46815 'Tracked opportunities':
#   IF 2  (primaryScEmail present)   > get_records 8b541c4d filter
#         'Primary SC' (45e52601) eq primaryScEmail > workflow_return_result
#         ed8f3d88 (terminal)
#   ELSIF 5 (accountManagerEmail present) > get_records 3559ec8c -- RAW RECIPE
#         BUG replayed verbatim: the filter dereferences the primaryScEmail
#         pill, never accountManagerEmail > workflow_return_result fc357629
#         (terminal). Because workato_db_filters raises on a MISSING filter
#         value, this branch is only reachable with primaryScEmail pinned to
#         "" (blank fails IF 2's 'present' but resolves the filter to eq "").
#   ELSIF 8 (opportunityId present)  > get_records f9fbc34b filter
#         'Opportunity ID' (ca9edae0) eq opportunityId >
#         workflow_return_result 42171a13 (terminal)
#   ELSE 11 > get_records 4c1a8753 (NO filters; the raw limit 30 is metadata
#         the mock does not enforce, so the size==30 branch must be seeded
#         with EXACTLY 30 rows)
#         IF 13 (records size == 30) > workflow_return_result cf2ff671
#               (static refine-your-query message, terminal)
#         > workflow_return_result cf8e9db6 (full-list mapping, terminal;
#           never runs when cf2ff671 fired)
# Every return maps the same 10 columns; relation_set columns (f2b7d805 /
# bdf4a3af) are declared in the schema but never dereferenced. All backends
# are Workato-internal (db table mock + genie return): no cleanup, the table
# is per-variant isolated seeded state and the recipe never writes it.
MAPPED_FIELD_IDS = (
    "ca9edae0_2cda_4c9f_ba6d_0f6c46d3833a",  # Opportunity ID
    "bc552cec_ca25_4e6e_8c0c_bc18925f9295",  # Opportunity Name
    "50ef1322_1da8_4b58_8d37_11152e9ecf66",  # Account ID
    "be67b011_7fdf_4eec_b945_45d22d91136c",  # Account Name
    "092638f6_880d_47cf_8c9c_a9a31f117052",  # Stage
    "45e52601_bb12_491b_a3d5_2f5f448dc968",  # Primary SC
    "8727f282_5f62_49d4_8859_412a0a4f3e0d",  # Customer roadmap Doc-ID
    "95229104_7b3a_4720_bcc5_9199e8dbe748",  # Customer roadmap score
    "93c1dab2_2512_4e23_bea8_4d2114e6e7ce",  # Customer roadmap cache
    "a79eaf9b_27ee_496a_9fce_c1d1d37ac7b1",  # Customer Drive ID
)
TRIGGER_PARAMETER_KEYS = ("primaryScEmail", "accountManagerEmail", "opportunityId")
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("8b541c4d", "workato_db_table", "get_records"),
    ("ed8f3d88", "workato_genie", "workflow_return_result"),
    ("3559ec8c", "workato_db_table", "get_records"),
    ("fc357629", "workato_genie", "workflow_return_result"),
    ("f9fbc34b", "workato_db_table", "get_records"),
    ("42171a13", "workato_genie", "workflow_return_result"),
    ("4c1a8753", "workato_db_table", "get_records"),
    ("cf2ff671", "workato_genie", "workflow_return_result"),
    ("cf8e9db6", "workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_genie.workflow_return_result",
]
EXPECT_KEYS = ("executed_action_count", "tools", "tool_expectations", "return_value")

# Verbatim raw-recipe pin: the full normalized node tree (number, keyword,
# provider, name, as, skip, input for every node). Any drift in the elsif
# ladder, the buggy primaryScEmail filter pill on the accountManagerEmail
# branch, the 10-field return mappings or the refine-message text fails
# validation instead of silently changing groundtruth.
_RAW_PIN_JSON = r"""{"as": "30d84672", "block": [{"as": "", "block": [{"as": "8b541c4d", "block": [], "input": {"05f2ad1e-3741-4784-9a0a-d78749bcdb49": "string", "092638f6-880d-47cf-8c9c-a9a31f117052": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "2cfd5a87-3dd0-49d5-a012-b651def9b87a": "string", "39f0b478-001e-48e6-bc84-5485aae16b03": "date_time", "45e52601-bb12-491b-a3d5-2f5f448dc968": "string", "50ef1322-1da8-4b58-8d37-11152e9ecf66": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "8727f282-5f62-49d4-8859-412a0a4f3e0d": "string", "93c1dab2-2512-4e23-bea8-4d2114e6e7ce": "string", "95229104-7b3a-4720-bcc5-9199e8dbe748": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "a79eaf9b-27ee-496a-9fce-c1d1d37ac7b1": "string", "b2edc416-2cc9-4961-93e4-f58f8065227d": "string", "b5249fe4-0905-4cb4-8cb1-fbf0e3be4a6c": "string", "bc552cec-ca25-4e6e-8c0c-bc18925f9295": "string", "bdf4a3af-7a66-4219-bd28-5bdd659e0b0b": "relation_set", "be67b011-7fdf-4eec-b945-45d22d91136c": "string", "ca9edae0-2cda-4c9f-ba6d-0f6c46d3833a": "string", "f2b7d805-7e87-43b0-9f05-0b8953e548c2": "relation_set", "filters": [{"field_id": "45e52601-bb12-491b-a3d5-2f5f448dc968", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_genie\",\"line\":\"30d84672\",\"path\":[\"parameters\", \"primaryScEmail\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "46815"}, "keyword": "action", "name": "get_records", "number": 3, "provider": "workato_db_table", "skip": false}, {"as": "ed8f3d88", "block": [], "input": {"result": {"opportunities": {"PrimarySC": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"45e52601_bb12_491b_a3d5_2f5f448dc968\"]}')}", "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\"]}')}", "accountId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"50ef1322_1da8_4b58_8d37_11152e9ecf66\"]}')}", "accountName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"be67b011_7fdf_4eec_b945_45d22d91136c\"]}')}", "customerRoadmapCache": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"93c1dab2_2512_4e23_bea8_4d2114e6e7ce\"]}')}", "customerRoadmapDocumentId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"8727f282_5f62_49d4_8859_412a0a4f3e0d\"]}')}", "customerRoadmapScore": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"95229104_7b3a_4720_bcc5_9199e8dbe748\"]}')}", "customerSharedDriveId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"a79eaf9b_27ee_496a_9fce_c1d1d37ac7b1\"]}')}", "opportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"ca9edae0_2cda_4c9f_ba6d_0f6c46d3833a\"]}')}", "opportunityName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"bc552cec_ca25_4e6e_8c0c_bc18925f9295\"]}')}", "stage": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"8b541c4d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"092638f6_880d_47cf_8c9c_a9a31f117052\"]}')}"}}}, "keyword": "action", "name": "workflow_return_result", "number": 4, "provider": "workato_genie", "skip": false}, {"as": "", "block": [{"as": "3559ec8c", "block": [], "input": {"05f2ad1e-3741-4784-9a0a-d78749bcdb49": "string", "092638f6-880d-47cf-8c9c-a9a31f117052": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "2cfd5a87-3dd0-49d5-a012-b651def9b87a": "string", "39f0b478-001e-48e6-bc84-5485aae16b03": "date_time", "45e52601-bb12-491b-a3d5-2f5f448dc968": "string", "50ef1322-1da8-4b58-8d37-11152e9ecf66": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "8727f282-5f62-49d4-8859-412a0a4f3e0d": "string", "93c1dab2-2512-4e23-bea8-4d2114e6e7ce": "string", "95229104-7b3a-4720-bcc5-9199e8dbe748": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "a79eaf9b-27ee-496a-9fce-c1d1d37ac7b1": "string", "b2edc416-2cc9-4961-93e4-f58f8065227d": "string", "b5249fe4-0905-4cb4-8cb1-fbf0e3be4a6c": "string", "bc552cec-ca25-4e6e-8c0c-bc18925f9295": "string", "bdf4a3af-7a66-4219-bd28-5bdd659e0b0b": "relation_set", "be67b011-7fdf-4eec-b945-45d22d91136c": "string", "ca9edae0-2cda-4c9f-ba6d-0f6c46d3833a": "string", "f2b7d805-7e87-43b0-9f05-0b8953e548c2": "relation_set", "filters": [{"field_id": "45e52601-bb12-491b-a3d5-2f5f448dc968", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_genie\",\"line\":\"30d84672\",\"path\":[\"parameters\", \"primaryScEmail\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "46815"}, "keyword": "action", "name": "get_records", "number": 6, "provider": "workato_db_table", "skip": false}, {"as": "fc357629", "block": [], "input": {"result": {"opportunities": {"PrimarySC": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"45e52601_bb12_491b_a3d5_2f5f448dc968\"]}')}", "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\"]}')}", "accountId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"50ef1322_1da8_4b58_8d37_11152e9ecf66\"]}')}", "accountName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"be67b011_7fdf_4eec_b945_45d22d91136c\"]}')}", "customerRoadmapCache": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"93c1dab2_2512_4e23_bea8_4d2114e6e7ce\"]}')}", "customerRoadmapDocumentId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"8727f282_5f62_49d4_8859_412a0a4f3e0d\"]}')}", "customerRoadmapScore": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"95229104_7b3a_4720_bcc5_9199e8dbe748\"]}')}", "customerSharedDriveId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"a79eaf9b_27ee_496a_9fce_c1d1d37ac7b1\"]}')}", "opportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"ca9edae0_2cda_4c9f_ba6d_0f6c46d3833a\"]}')}", "opportunityName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"bc552cec_ca25_4e6e_8c0c_bc18925f9295\"]}')}", "stage": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3559ec8c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"092638f6_880d_47cf_8c9c_a9a31f117052\"]}')}"}}}, "keyword": "action", "name": "workflow_return_result", "number": 7, "provider": "workato_genie", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_genie\",\"line\":\"30d84672\",\"path\":[\"parameters\", \"accountManagerEmail\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "elsif", "name": "", "number": 5, "provider": "", "skip": false}, {"as": "", "block": [{"as": "f9fbc34b", "block": [], "input": {"05f2ad1e-3741-4784-9a0a-d78749bcdb49": "string", "092638f6-880d-47cf-8c9c-a9a31f117052": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "2cfd5a87-3dd0-49d5-a012-b651def9b87a": "string", "45e52601-bb12-491b-a3d5-2f5f448dc968": "string", "50ef1322-1da8-4b58-8d37-11152e9ecf66": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "8727f282-5f62-49d4-8859-412a0a4f3e0d": "string", "93c1dab2-2512-4e23-bea8-4d2114e6e7ce": "string", "95229104-7b3a-4720-bcc5-9199e8dbe748": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "a79eaf9b-27ee-496a-9fce-c1d1d37ac7b1": "string", "b2edc416-2cc9-4961-93e4-f58f8065227d": "string", "b5249fe4-0905-4cb4-8cb1-fbf0e3be4a6c": "string", "bc552cec-ca25-4e6e-8c0c-bc18925f9295": "string", "bdf4a3af-7a66-4219-bd28-5bdd659e0b0b": "relation_set", "be67b011-7fdf-4eec-b945-45d22d91136c": "string", "ca9edae0-2cda-4c9f-ba6d-0f6c46d3833a": "string", "f2b7d805-7e87-43b0-9f05-0b8953e548c2": "relation_set", "filters": [{"field_id": "ca9edae0-2cda-4c9f-ba6d-0f6c46d3833a", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_genie\",\"line\":\"30d84672\",\"path\":[\"parameters\", \"opportunityId\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "46815"}, "keyword": "action", "name": "get_records", "number": 9, "provider": "workato_db_table", "skip": false}, {"as": "42171a13", "block": [], "input": {"result": {"opportunities": {"PrimarySC": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"45e52601_bb12_491b_a3d5_2f5f448dc968\"]}')}", "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\"]}')}", "accountId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"50ef1322_1da8_4b58_8d37_11152e9ecf66\"]}')}", "accountName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"be67b011_7fdf_4eec_b945_45d22d91136c\"]}')}", "customerRoadmapCache": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"93c1dab2_2512_4e23_bea8_4d2114e6e7ce\"]}')}", "customerRoadmapDocumentId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"8727f282_5f62_49d4_8859_412a0a4f3e0d\"]}')}", "customerRoadmapScore": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"95229104_7b3a_4720_bcc5_9199e8dbe748\"]}')}", "customerSharedDriveId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"a79eaf9b_27ee_496a_9fce_c1d1d37ac7b1\"]}')}", "opportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"ca9edae0_2cda_4c9f_ba6d_0f6c46d3833a\"]}')}", "opportunityName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"bc552cec_ca25_4e6e_8c0c_bc18925f9295\"]}')}", "stage": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f9fbc34b\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"092638f6_880d_47cf_8c9c_a9a31f117052\"]}')}"}}}, "keyword": "action", "name": "workflow_return_result", "number": 10, "provider": "workato_genie", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_genie\",\"line\":\"30d84672\",\"path\":[\"parameters\", \"opportunityId\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "elsif", "name": "", "number": 8, "provider": "", "skip": false}, {"as": "", "block": [{"as": "4c1a8753", "block": [], "input": {"05f2ad1e-3741-4784-9a0a-d78749bcdb49": "string", "092638f6-880d-47cf-8c9c-a9a31f117052": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "2cfd5a87-3dd0-49d5-a012-b651def9b87a": "string", "45e52601-bb12-491b-a3d5-2f5f448dc968": "string", "50ef1322-1da8-4b58-8d37-11152e9ecf66": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "8727f282-5f62-49d4-8859-412a0a4f3e0d": "string", "93c1dab2-2512-4e23-bea8-4d2114e6e7ce": "string", "95229104-7b3a-4720-bcc5-9199e8dbe748": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "a79eaf9b-27ee-496a-9fce-c1d1d37ac7b1": "string", "b2edc416-2cc9-4961-93e4-f58f8065227d": "string", "b5249fe4-0905-4cb4-8cb1-fbf0e3be4a6c": "string", "bc552cec-ca25-4e6e-8c0c-bc18925f9295": "string", "bdf4a3af-7a66-4219-bd28-5bdd659e0b0b": "relation_set", "be67b011-7fdf-4eec-b945-45d22d91136c": "string", "ca9edae0-2cda-4c9f-ba6d-0f6c46d3833a": "string", "f2b7d805-7e87-43b0-9f05-0b8953e548c2": "relation_set", "limit": "30", "order_direction": "asc", "table_id": "46815"}, "keyword": "action", "name": "get_records", "number": 12, "provider": "workato_db_table", "skip": false}, {"as": "", "block": [{"as": "cf2ff671", "block": [], "input": {"result": {"message": "If the number of opportunities found is too large, do not return the full list and don't try to find the opportunity in Salesforce.\nInstead, ask the user to refine their query by providing more specific details \u2014 for example:\n- the account name (e.g., \u201cShow me opportunities for Acme Corp\u201d),\n- the timeframe (e.g., \u201copportunities closing this quarter\u201d),\n- the stage (e.g., \u201conly open opportunities\u201d),\n- or the owner (e.g., \u201cmy opportunities only\u201d)."}}, "keyword": "action", "name": "workflow_return_result", "number": 14, "provider": "workato_genie", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "30"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 13, "provider": "", "skip": false}, {"as": "cf8e9db6", "block": [], "input": {"result": {"opportunities": {"PrimarySC": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"45e52601_bb12_491b_a3d5_2f5f448dc968\"]}')}", "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\"]}')}", "accountId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"50ef1322_1da8_4b58_8d37_11152e9ecf66\"]}')}", "accountName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"be67b011_7fdf_4eec_b945_45d22d91136c\"]}')}", "customerRoadmapCache": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"93c1dab2_2512_4e23_bea8_4d2114e6e7ce\"]}')}", "customerRoadmapDocumentId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"8727f282_5f62_49d4_8859_412a0a4f3e0d\"]}')}", "customerRoadmapScore": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"95229104_7b3a_4720_bcc5_9199e8dbe748\"]}')}", "customerSharedDriveId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"a79eaf9b_27ee_496a_9fce_c1d1d37ac7b1\"]}')}", "opportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"ca9edae0_2cda_4c9f_ba6d_0f6c46d3833a\"]}')}", "opportunityName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"bc552cec_ca25_4e6e_8c0c_bc18925f9295\"]}')}", "stage": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"4c1a8753\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"092638f6_880d_47cf_8c9c_a9a31f117052\"]}')}"}}}, "keyword": "action", "name": "workflow_return_result", "number": 15, "provider": "workato_genie", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 11, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_genie\",\"line\":\"30d84672\",\"path\":[\"parameters\", \"primaryScEmail\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"description": "This tool is the single source of truth for tracked opportunities you have knowledge about it. There are many other opportunities not being tracked in Salesforce, but you don't have full knowledge about it.\nBefore proceeding with any other skills, always use this skill to get more details about one or more opportunities.\n\n- Only populate primaryScEmail or accountManagerEmail when explicitly requested by the user. For example, if the user says \u2018Show my opportunities\u2019, set primaryScEmail with the user\u2019s email.\n- Populate the opportunityId to filter a single specific opportunity\n- If the user wants to perform a broader search with different criteria, search opportunities directly in Salesforce and then cross-check whether the opportunity is already tracked.\n\nUsage Rules:\n- Resolve by name: Use it whenever you need to find an opportunity by name or confirm its existence.\n- No guessing: Never infer attributes (e.g., close date) from the opportunity name.\n- Presentation: Always display results in a table format, even if only one record is found.\n- IDs: Do not expose internal IDs (opportunityId, accountId) to the user.\n\nLink Formatting:\n- Instead of raw IDs, generate clickable Salesforce links:\n- Opportunity:\nhttps://workato--dev.sandbox.lightning.force.com/lightning/r/Opportunity/<opportunityId>/view\n- Account:\nhttps://workato--dev.sandbox.lightning.force.com/lightning/r/Account/<accountId>/view\n- Both links should be placed on the respective OpportunityName and AccountName in the results table.", "parameters_schema_json": "[{\"name\":\"primaryScEmail\",\"type\":\"string\",\"optional\":true,\"hint\":\"Populate only if the user explicitly asks to filter by their own opportunities (e.g., when they say \u2018Show my opportunities\u2019).\",\"control_type\":\"text\"},{\"name\":\"accountManagerEmail\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"hint\":\"Fill this attribute if opportunities should be filtered for a account manager.\"},{\"name\":\"opportunityId\",\"type\":\"string\",\"optional\":true,\"hint\":\"The ID of the opportunity from Salesforce. Use it get details about a specific tracked opportunity.\",\"control_type\":\"text\"}]", "requires_user_confirmation": "false", "result_schema_json": "[{\"name\":\"opportunities\",\"type\":\"array\",\"optional\":true,\"properties\":[{\"control_type\":\"text\",\"label\":\"Primary SC\",\"name\":\"PrimarySC\",\"type\":\"string\",\"optional\":false,\"hint\":\"The primary solution consultant handling this opportunity.\"},{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"accountId\",\"type\":\"string\",\"optional\":false,\"hint\":\"The ID of the account in Salesforce\"},{\"control_type\":\"text\",\"label\":\"Opportunity ID\",\"name\":\"opportunityId\",\"type\":\"string\",\"optional\":false,\"hint\":\"The ID of the opportunity in Salesforce\"},{\"control_type\":\"text\",\"label\":\"Opportunity name\",\"name\":\"opportunityName\",\"type\":\"string\",\"optional\":false,\"hint\":\"The name of the opportunity.\"},{\"control_type\":\"text\",\"label\":\"Account name\",\"name\":\"accountName\",\"type\":\"string\",\"optional\":false,\"hint\":\"The name of the account.\"},{\"control_type\":\"text\",\"label\":\"Stage\",\"name\":\"stage\",\"type\":\"string\",\"optional\":false,\"hint\":\"The stage this opportunity is right now. For instance S1: Discovery\"},{\"name\":\"customerRoadmapCache\",\"type\":\"string\",\"optional\":false,\"hint\":\"The file name of the customer roadmap cache\",\"control_type\":\"text\",\"label\":\"Customer roadmap cache\"},{\"name\":\"customerSharedDriveId\",\"type\":\"string\",\"optional\":false,\"hint\":\"The ID of the customer shared drive on Google\",\"control_type\":\"text\",\"label\":\"Customer shared drive ID\"},{\"name\":\"customerRoadmapScore\",\"type\":\"string\",\"optional\":false,\"hint\":\"The score calculated for the customer roadmap\",\"control_type\":\"text\",\"label\":\"Customer roadmap score\"},{\"name\":\"customerRoadmapDocumentId\",\"type\":\"string\",\"optional\":false,\"hint\":\"The ID of the customer roadmap document\",\"control_type\":\"text\",\"label\":\"Customer roadmap document ID\"}],\"of\":\"object\",\"label\":\"Opportunities\"},{\"name\":\"message\",\"type\":\"string\",\"optional\":true,\"hint\":\"An optional message, used to instruct the Genie\",\"control_type\":\"text\",\"label\":\"Message\"}]"}, "keyword": "trigger", "name": "start_workflow", "number": 1, "provider": "workato_genie", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_130740881(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_130740881(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130740881(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}"
        )
    unknown = sorted(set(parameters) - set(TRIGGER_PARAMETER_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has unknown keys: {unknown}")
    for key, value in parameters.items():
        if not isinstance(value, str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameter {key!r} must be an explicit string; got {value!r}"
            )
    if str(parameters.get("accountManagerEmail") or "").strip() and not str(
        parameters.get("primaryScEmail") or ""
    ).strip():
        # The raw-bug branch's filter dereferences the primaryScEmail pill.
        # With the key ABSENT the engine fails fast (MISSING filter value), so
        # the branch is only reachable with an explicit blank pin.
        if "primaryScEmail" not in parameters:
            raise RuntimeError(
                f"recipe {RECIPE_ID} accountManagerEmail variants must pin primaryScEmail: '' "
                "(the raw recipe's bug filter dereferences the primaryScEmail pill)"
            )
    seed_in = data.get("seed")
    table_seed = seed_in.get("workato_db_table") if isinstance(seed_in, dict) else None
    tables = table_seed.get("tables") if isinstance(table_seed, dict) else None
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly workato_db_table.tables[{TABLE_ID!r}]"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} seed must be a non-empty row list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be objects")
        missing = [field for field in MAPPED_FIELD_IDS if field not in row]
        if missing:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {TABLE_ID} row {idx} is missing mapped columns: {missing}"
            )
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {TABLE_ID} row {idx} column {key!r} must be a string"
                )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing_keys = [key for key in EXPECT_KEYS if key not in expect]
    if missing_keys:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing_keys}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(table_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130740881(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130740881(raw)
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_130740881(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
