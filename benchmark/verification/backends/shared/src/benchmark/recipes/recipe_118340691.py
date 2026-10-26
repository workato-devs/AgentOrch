from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118340691


RECIPE_ID = "118340691"
SEED_TYPE = "workspace_schema_compare_recipe_function_variant"
TRACK = "workato_internal_workspace_schema_compare"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "97295061"
CREATE_INPUT_AS = "b6591ebf"
CREATE_OUTPUT_AS = "eeaeaf5a"
INSERT_INPUT_AS = "19fafc56"
INSERT_OUTPUT_AS = "902227bd"
COMPARE_AS = "5651eeb1"
DECLARE_LIST_AS = "ba37f78a"
LOGGER_AS = "1c3f1dfa"
STOP_AS = "8657dddc"
RETURN_AS = "cb8d5642"
STOP_STEP_NUMBER = 10


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "97295061", "skip": false, "input": {"parameters_schema_json": "[{\"properties\":[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Email\",\"type\":\"string\",\"name\":\"email\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"name\"},{\"control_type\":\"text\",\"label\":\"Membership ID\",\"type\":\"string\",\"name\":\"membership_id\"},{\"control_type\":\"text\",\"label\":\"Billing start date\",\"type\":\"string\",\"name\":\"billing_start_date\"},{\"name\":\"ad_hoc_features\",\"type\":\"array\",\"of\":\"string\",\"control_type\":\"text\",\"label\":\"Ad hoc features\"},{\"name\":\"adhoc_adapters\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Adhoc Adapters\",\"optional\":false},{\"properties\":[{\"name\":\"credit_limit\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Credit limit\",\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Custom action limit\",\"type\":\"integer\",\"name\":\"custom_action_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Billable flow limit\",\"type\":\"integer\",\"name\":\"billable_flow_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max account property\",\"type\":\"integer\",\"name\":\"max_account_property\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max flows\",\"type\":\"integer\",\"name\":\"max_flows\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max hvr tier 1\",\"type\":\"integer\",\"name\":\"max_hvr_tier1\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max hvr tier 2\",\"type\":\"integer\",\"name\":\"max_hvr_tier2\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max hvr tier 3\",\"type\":\"integer\",\"name\":\"max_hvr_tier3\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max lookup table\",\"type\":\"integer\",\"name\":\"max_lookup_table\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max personalized connection\",\"type\":\"integer\",\"name\":\"max_personalized_connection\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max project property\",\"type\":\"integer\",\"name\":\"max_project_property\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max shared account\",\"type\":\"integer\",\"name\":\"max_shared_account\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max topic\",\"type\":\"integer\",\"name\":\"max_topic\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max managed user grant\",\"type\":\"integer\",\"name\":\"max_managed_user_grant\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max workato schema\",\"type\":\"integer\",\"name\":\"max_workato_schema\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max workato template\",\"type\":\"integer\",\"name\":\"max_workato_template\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max worker concurrency\",\"type\":\"integer\",\"name\":\"max_worker_concurrency\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max workflow app user\",\"type\":\"integer\",\"name\":\"max_workflow_app_user\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max secure gateway tunnel\",\"type\":\"integer\",\"name\":\"max_secure_gateway_tunnel\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Opa limit\",\"type\":\"integer\",\"name\":\"opa_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Shared account limit\",\"type\":\"integer\",\"name\":\"shared_account_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Transaction credit\",\"type\":\"integer\",\"name\":\"transaction_credit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Workbots limit\",\"type\":\"integer\",\"name\":\"workbots_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"text\",\"label\":\"Data retention policy\",\"type\":\"string\",\"name\":\"data_retention_policy\"}],\"label\":\"Limits\",\"type\":\"object\",\"name\":\"limits\"},{\"properties\":[{\"control_type\":\"integer\",\"label\":\"Workspaces limit\",\"type\":\"integer\",\"name\":\"workspaces_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Custom action limit\",\"type\":\"integer\",\"name\":\"custom_action_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Billable flow limit\",\"type\":\"integer\",\"name\":\"billable_flow_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Opa limit\",\"type\":\"integer\",\"name\":\"opa_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max additional worker concurrency\",\"type\":\"integer\",\"name\":\"max_additional_worker_concurrency\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"label\":\"Saml linking enabled\",\"type\":\"boolean\",\"name\":\"saml_linking_enabled\",\"optional\":false,\"control_type\":\"checkbox\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Saml linking enabled\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"saml_linking_enabled\",\"optional\":false}}],\"label\":\"Federated account\",\"type\":\"object\",\"name\":\"federated_account\"},{\"control_type\":\"text\",\"label\":\"Workspace type\",\"type\":\"string\",\"name\":\"workspace_type\"},{\"control_type\":\"text\",\"label\":\"Trial\",\"type\":\"string\",\"name\":\"trial\"},{\"control_type\":\"text\",\"label\":\"Membership label\",\"type\":\"string\",\"name\":\"membership_label\"},{\"control_type\":\"text\",\"label\":\"Trial duration\",\"type\":\"string\",\"name\":\"trial_duration\"}],\"label\":\"Workspace\",\"type\":\"object\",\"name\":\"workspace\"}],\"label\":\"Input\",\"name\":\"input\",\"type\":\"object\",\"optional\":true},{\"properties\":[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Email\",\"type\":\"string\",\"name\":\"email\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"name\"},{\"control_type\":\"text\",\"label\":\"Membership ID\",\"type\":\"string\",\"name\":\"membership_id\"},{\"control_type\":\"text\",\"label\":\"Billing start date\",\"type\":\"string\",\"name\":\"billing_start_date\"},{\"name\":\"ad_hoc_features\",\"type\":\"array\",\"of\":\"string\",\"control_type\":\"text\",\"label\":\"Ad hoc features\"},{\"name\":\"adhoc_adapters\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Adhoc Adapters\",\"optional\":false},{\"properties\":[{\"name\":\"credit_limit\",\"type\":\"number\",\"optional\":false,\"control_type\":\"number\",\"label\":\"Credit limit\",\"parse_output\":\"float_conversion\"},{\"control_type\":\"integer\",\"label\":\"Custom action limit\",\"type\":\"integer\",\"name\":\"custom_action_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Billable flow limit\",\"type\":\"integer\",\"name\":\"billable_flow_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max account property\",\"type\":\"integer\",\"name\":\"max_account_property\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max flows\",\"type\":\"integer\",\"name\":\"max_flows\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max hvr tier 1\",\"type\":\"integer\",\"name\":\"max_hvr_tier1\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max hvr tier 2\",\"type\":\"integer\",\"name\":\"max_hvr_tier2\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max hvr tier 3\",\"type\":\"integer\",\"name\":\"max_hvr_tier3\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max lookup table\",\"type\":\"integer\",\"name\":\"max_lookup_table\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max personalized connection\",\"type\":\"integer\",\"name\":\"max_personalized_connection\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max project property\",\"type\":\"integer\",\"name\":\"max_project_property\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max shared account\",\"type\":\"integer\",\"name\":\"max_shared_account\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max topic\",\"type\":\"integer\",\"name\":\"max_topic\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max managed user grant\",\"type\":\"integer\",\"name\":\"max_managed_user_grant\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max workato schema\",\"type\":\"integer\",\"name\":\"max_workato_schema\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max workato template\",\"type\":\"integer\",\"name\":\"max_workato_template\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max worker concurrency\",\"type\":\"integer\",\"name\":\"max_worker_concurrency\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max workflow app user\",\"type\":\"integer\",\"name\":\"max_workflow_app_user\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max secure gateway tunnel\",\"type\":\"integer\",\"name\":\"max_secure_gateway_tunnel\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Opa limit\",\"type\":\"integer\",\"name\":\"opa_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Shared account limit\",\"type\":\"integer\",\"name\":\"shared_account_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Transaction credit\",\"type\":\"integer\",\"name\":\"transaction_credit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Workbots limit\",\"type\":\"integer\",\"name\":\"workbots_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"text\",\"label\":\"Data retention policy\",\"type\":\"string\",\"name\":\"data_retention_policy\"}],\"label\":\"Limits\",\"type\":\"object\",\"name\":\"limits\"},{\"properties\":[{\"control_type\":\"integer\",\"label\":\"Workspaces limit\",\"type\":\"integer\",\"name\":\"workspaces_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Custom action limit\",\"type\":\"integer\",\"name\":\"custom_action_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Billable flow limit\",\"type\":\"integer\",\"name\":\"billable_flow_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Opa limit\",\"type\":\"integer\",\"name\":\"opa_limit\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"integer\",\"label\":\"Max additional worker concurrency\",\"type\":\"integer\",\"name\":\"max_additional_worker_concurrency\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"text\",\"label\":\"Saml linking enabled\",\"type\":\"string\",\"name\":\"saml_linking_enabled\"}],\"label\":\"Federated account\",\"type\":\"object\",\"name\":\"federated_account\"},{\"control_type\":\"text\",\"label\":\"Workspace type\",\"type\":\"string\",\"name\":\"workspace_type\"},{\"control_type\":\"text\",\"label\":\"Trial\",\"type\":\"string\",\"name\":\"trial\"},{\"control_type\":\"text\",\"label\":\"Membership label\",\"type\":\"string\",\"name\":\"membership_label\"},{\"control_type\":\"text\",\"label\":\"Trial duration\",\"type\":\"string\",\"name\":\"trial_duration\"}],\"label\":\"Workspace\",\"type\":\"object\",\"name\":\"workspace\"}],\"label\":\"Output\",\"name\":\"output\",\"type\":\"object\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Workato user opportunity ID\",\"name\":\"workato_user_opportunity_id\",\"type\":\"string\",\"optional\":false}]", "result_schema_json": "[{\"name\":\"success\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Success\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Success\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"success\",\"type\":\"boolean\",\"optional\":false}}]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_smart_list", "name": "query_list", "as": "b6591ebf", "skip": false, "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"features\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Features\"}]", "sql": "CREATE TABLE input_list (\n    all_products TEXT\n)"}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_smart_list", "name": "query_list", "as": "eeaeaf5a", "skip": false, "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"features\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Features\"}]", "sql": "CREATE TABLE output_list (\n    all_products TEXT\n)"}, "block": []}, {"number": 4, "keyword": "action", "provider": "workato_smart_list", "name": "query_list", "as": "19fafc56", "skip": false, "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"all_products\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"All products\"}]", "sql": "=\"INSERT INTO input_list (all_products) VALUES\n#{(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"ad_hoc_features\"]}')&.concat(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"adhoc_adapters\"]}')))&.format_map('(\\'%s\\')')&.join(\",\\n\")}\"\n"}, "block": []}, {"number": 5, "keyword": "action", "provider": "workato_smart_list", "name": "query_list", "as": "902227bd", "skip": false, "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"all_products\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"All products\"}]", "sql": "=\"INSERT INTO output_list (all_products) VALUES\n#{(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"ad_hoc_features\"]}')&.concat(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"adhoc_adapters\"]}'))).format_map('(\\'%s\\')').join(\",\\n\")}\"\n"}, "block": []}, {"number": 6, "keyword": "action", "provider": "workato_smart_list", "name": "query_list", "as": "5651eeb1", "skip": false, "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"features\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Features\"}]", "sql": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"902227bd\",\"path\":[\"rows\",{\"path_element_type\":\"size\"}]}') > _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19fafc56\",\"path\":[\"rows\",{\"path_element_type\":\"size\"}]}')\n  \"Select all_products FROM output_list WHERE all_products NOT IN (SELECT all_products FROM input_list)\"\nelse\n  \"Select all_products FROM input_list WHERE all_products NOT IN (SELECT all_products FROM output_list)\"\nend"}, "block": []}, {"number": 7, "keyword": "action", "provider": "workato_variable", "name": "declare_list", "as": "ba37f78a", "skip": false, "input": {"list_item_schema_json": "[{\"name\":\"key\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Key\"},{\"name\":\"match_result\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Match result\"}]", "list_items": [{"key": "custom_action_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"custom_action_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"custom_action_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"custom_action_limit\"]}').present?) ?\n(\"Custom Action Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"custom_action_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"custom_action_limit\"]}')].join(\" vs \")) : skip"}, {"key": "billable_flow_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"billable_flow_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"billable_flow_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"billable_flow_limit\"]}').present?) ? \n(\"Billable flow Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"billable_flow_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"billable_flow_limit\"]}')].join(\" vs \")) : skip"}, {"key": "max_account_property", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_account_property\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_account_property\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_account_property\"]}').present?) ? \n(\"Max Account Property Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_account_property\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_account_property\"]}')].join(\" vs \")) : skip"}, {"key": "max_flows", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_flows\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_flows\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_flows\"]}').present?) ?\n(\"Max Flows Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_flows\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_flows\"]}')].join(\" vs \")) : skip"}, {"key": "max_hvr_tier1", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier1\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_hvr_tier1\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier1\"]}').present?) ? \n(\"Max HVR tier 1 Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier1\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_hvr_tier1\"]}')].join(\" vs \")) : skip"}, {"key": "max_hvr_tier2", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier2\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_hvr_tier2\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier2\"]}').present?) ? \n(\"Max HVR tier 2 Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier2\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_hvr_tier2\"]}')].join(\" vs \")) : skip"}, {"key": "max_hvr_tier3", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier3\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_hvr_tier3\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier3\"]}').present?) ? \n(\"Max HVR Tier 3 Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_hvr_tier3\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_hvr_tier3\"]}')].join(\" vs \")) : skip"}, {"key": "max_lookup_table", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_lookup_table\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_lookup_table\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_lookup_table\"]}').present?) ?\n(\"Max Lookup Table Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_lookup_table\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_lookup_table\"]}')].join(\" vs \")) : skip"}, {"key": "max_personalized_connection", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_personalized_connection\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_personalized_connection\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_personalized_connection\"]}').present?) ? \n(\"Max personalized connection Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_personalized_connection\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_personalized_connection\"]}')].join(\" vs \")) : skip"}, {"key": "max_project_property", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_project_property\"]}').present? && (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_project_property\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_project_property\"]}'))) ?\n(\"Max Project property Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_project_property\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_project_property\"]}')].join(\" vs \")) : skip"}, {"key": "max_shared_account", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_shared_account\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_shared_account\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_shared_account\"]}').present?) ?\n(\"Max Shared Account Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_shared_account\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_shared_account\"]}')].join(\" vs \")) : skip"}, {"key": "max_topic", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_topic\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_topic\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_topic\"]}').present?) ?\n(\"Max Topic Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_topic\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_topic\"]}')].join(\" vs \")) : skip"}, {"key": "max_managed_user_grant", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_managed_user_grant\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_managed_user_grant\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_managed_user_grant\"]}').present?) ?\n(\"Max Managed User Grant Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_managed_user_grant\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_managed_user_grant\"]}')].join(\" vs \")) : skip"}, {"key": "max_workato_schema", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workato_schema\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_workato_schema\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workato_schema\"]}').present?) ?\n(\"Max Workato Schema Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workato_schema\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_workato_schema\"]}')].join(\" vs \")) : skip"}, {"key": "max_workato_template", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workato_template\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_workato_template\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workato_template\"]}').present?) ?\n(\"Max Workato Template Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workato_template\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_workato_template\"]}')].join(\" vs \")) : skip"}, {"key": "max_worker_concurrency", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_worker_concurrency\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_worker_concurrency\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_worker_concurrency\"]}').present?) ?\n(\"Max Worker Concurrency Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_worker_concurrency\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_worker_concurrency\"]}')].join(\" vs \")) : skip"}, {"key": "max_workflow_app_user", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workflow_app_user\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_workflow_app_user\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workflow_app_user\"]}').present?) ?\n(\"Max Workflow App Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_workflow_app_user\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_workflow_app_user\"]}')].join(\" vs \")) : skip"}, {"key": "max_secure_gateway_tunnel", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_secure_gateway_tunnel\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_secure_gateway_tunnel\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_secure_gateway_tunnel\"]}').present?) ? \n(\"Max Secure gateway tunnel Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"max_secure_gateway_tunnel\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"max_secure_gateway_tunnel\"]}')].join(\" vs \")) : skip"}, {"key": "opa_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"opa_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"opa_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"opa_limit\"]}').present?) ? \n(\"OPA Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"opa_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"opa_limit\"]}')].join(\" vs \")) : skip"}, {"key": "shared_account_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"shared_account_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"shared_account_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"shared_account_limit\"]}').present?) ? \n(\"Shared Account Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"shared_account_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"shared_account_limit\"]}')].join(\" vs \")) : skip"}, {"key": "workbots_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"workbots_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"workbots_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"workbots_limit\"]}').present?) ?\n(\"Workbot Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"limits\",\"workbots_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"limits\",\"workbots_limit\"]}')].join(\" vs \")) : skip"}, {"key": "federated_account.workspaces_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"workspaces_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"workspaces_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"workspaces_limit\"]}').present?) ?\n(\"Federated Account Workspace Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"workspaces_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"workspaces_limit\"]}')].join(\" vs \")) : skip"}, {"key": "federated_account.custom_action_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"custom_action_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"custom_action_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"custom_action_limit\"]}').present?) ?\n(\"Federated Account Custom Action Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"custom_action_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"custom_action_limit\"]}')].join(\" vs \")) : skip"}, {"key": "federated_account.billable_flow_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"billable_flow_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"billable_flow_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"billable_flow_limit\"]}').present?) ?\n(\"Federated Account Billable Flow Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"billable_flow_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"billable_flow_limit\"]}')].join(\" vs \")) : skip"}, {"key": "federated_account.opa_limit", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"opa_limit\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"opa_limit\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"opa_limit\"]}').present?) ?\n(\"Federated Account OPA Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"opa_limit\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"opa_limit\"]}')].join(\" vs \")) : skip"}, {"key": "federated_account.max_additional_worker_concurrency", "match_result": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"max_additional_worker_concurrency\"]}') != _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"max_additional_worker_concurrency\"]}') && _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"max_additional_worker_concurrency\"]}').present?) ?\n(\"Federated Account Max Additional worker concurrency Limit didn't match. Input vs Output: \" + [_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"input\",\"workspace\",\"federated_account\",\"max_additional_worker_concurrency\"]}'), _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"97295061\",\"path\":[\"parameters\",\"output\",\"workspace\",\"federated_account\",\"max_additional_worker_concurrency\"]}')].join(\" vs \")) : skip"}], "name": "Limits Matching"}, "block": []}, {"number": 8, "keyword": "action", "provider": "logger", "name": "log_message", "as": "1c3f1dfa", "skip": false, "input": {"message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"ba37f78a\",\"path\":[\"list_items\"]}').pluck('match_result').compact.join('; ').presence or \"Schema matched\"", "user_logs_enabled": "false"}, "block": []}, {"number": 9, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"1c3f1dfa\",\"path\":[\"message\"]}')}", "operand": "not_equals_to", "rhs": "=\"Schema matched\""}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5651eeb1\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "operand": "not_equals_to", "rhs": "0"}], "operand": "or", "type": "compound"}, "block": [{"number": 10, "keyword": "stop", "provider": "", "name": "", "as": "8657dddc", "skip": false, "input": {"stop_reason": "Limits: #{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"1c3f1dfa\",\"path\":[\"message\"]}')}, Features missing:  #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5651eeb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"features\"]}')}", "stop_with_error": "true"}, "block": []}]}, {"number": 11, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "cb8d5642", "skip": false, "input": {"result": {"success": "true"}}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (CREATE_INPUT_AS, "workato_smart_list", "query_list"),
    (CREATE_OUTPUT_AS, "workato_smart_list", "query_list"),
    (INSERT_INPUT_AS, "workato_smart_list", "query_list"),
    (INSERT_OUTPUT_AS, "workato_smart_list", "query_list"),
    (COMPARE_AS, "workato_smart_list", "query_list"),
    (DECLARE_LIST_AS, "workato_variable", "declare_list"),
    (LOGGER_AS, "logger", "log_message"),
    (RETURN_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_smart_list.query_list",
    "workato_runtime.declare_list",
    "workato_runtime.log_message",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_recipe_function.return_result",
]
EXPECTED_LIMIT_KEYS = [
    "custom_action_limit",
    "billable_flow_limit",
    "max_account_property",
    "max_flows",
    "max_hvr_tier1",
    "max_hvr_tier2",
    "max_hvr_tier3",
    "max_lookup_table",
    "max_personalized_connection",
    "max_project_property",
    "max_shared_account",
    "max_topic",
    "max_managed_user_grant",
    "max_workato_schema",
    "max_workato_template",
    "max_worker_concurrency",
    "max_workflow_app_user",
    "max_secure_gateway_tunnel",
    "opa_limit",
    "shared_account_limit",
    "workbots_limit",
    "federated_account.workspaces_limit",
    "federated_account.custom_action_limit",
    "federated_account.billable_flow_limit",
    "federated_account.opa_limit",
    "federated_account.max_additional_worker_concurrency",
]
WORKSPACE_ARRAY_KEYS = ("ad_hoc_features", "adhoc_adapters")
WORKSPACE_LIMIT_KEYS = frozenset(
    key for key in EXPECTED_LIMIT_KEYS if not key.startswith("federated_account.")
) | {"credit_limit", "transaction_credit", "data_retention_policy"}
FEDERATED_KEYS = frozenset(
    key.split(".", 1)[1] for key in EXPECTED_LIMIT_KEYS if key.startswith("federated_account.")
) | {"saml_linking_enabled"}
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "stopped",
    "return_value",
    "query_sql",
    "query_rows",
    "limit_items",
    "logger_message",
)
KNOWN_BRANCHES = (
    "all_match_success",
    "limit_mismatch_stop",
    "features_missing_output_bigger",
    "features_missing_input_bigger",
    "input_limit_absent_skip",
    "equal_size_swap_stop",
)


def validate_118340691(raw: dict[str, Any]) -> dict[str, Any]:
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
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    # Semantic pins (the tree pin holds the bytes; these name the traps):
    # 1. the 26 comparison items keep their keys and order,
    items = ((nodes[DECLARE_LIST_AS].get("input") or {}).get("list_items")) or []
    actual_keys = [str(item.get("key")) for item in items if isinstance(item, dict)]
    if actual_keys != EXPECTED_LIMIT_KEYS:
        raise RuntimeError(f"recipe {RECIPE_ID} limit item keys changed: {actual_keys}")
    for item in items:
        formula = str(item.get("match_result") or "")
        if ".present?" not in formula or ": skip" not in formula or '.join(" vs ")' not in formula:
            raise RuntimeError(
                f"recipe {RECIPE_ID} match_result ternary changed for {item.get('key')!r}: "
                f"{formula!r}"
            )
    # 2. the direction-picking compare keeps both NOT IN arms,
    compare_sql = str((nodes[COMPARE_AS].get("input") or {}).get("sql") or "")
    if (
        "output_list WHERE all_products NOT IN (SELECT all_products FROM input_list)" not in compare_sql
        or "input_list WHERE all_products NOT IN (SELECT all_products FROM output_list)" not in compare_sql
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} compare SQL changed: {compare_sql!r}")
    # 3. the compound-OR stop gate with its formula RHS.
    if_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "if"]
    if len(if_nodes) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} IF layout changed")
    if_input = if_nodes[0].get("input") or {}
    conditions = if_input.get("conditions") or []
    if (
        str(if_input.get("operand")) != "or"
        or len(conditions) != 2
        or str(conditions[0].get("rhs")) != '="Schema matched"'
        or str(conditions[0].get("operand")) != "not_equals_to"
        or str(conditions[1].get("rhs")) != "0"
        or str(conditions[1].get("operand")) != "not_equals_to"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} stop gate changed: {if_input!r}")
    stop_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "stop"]
    if (
        len(stop_nodes) != 1
        or stop_nodes[0].get("number") != STOP_STEP_NUMBER
        or str(stop_nodes[0].get("as") or "") != STOP_AS
        or str((stop_nodes[0].get("input") or {}).get("stop_with_error")) != "true"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} stop layout changed: {stop_nodes!r}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
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


def seed_118340691(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118340691(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: a forced action error would fail the whole "
            "run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if seed_in not in (None, {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} is a full-mock recipe (all backends Workato-internal); "
            f"seed sections are not allowed: {seed_in!r}"
        )
    expect = data.get("expect")
    _require_expect_shape(expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_118340691(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118340691(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    _require_trigger_shape(seed.get("trigger") or {})
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
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118340691(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': ...}}; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger["parameters"]
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters must be an object")
    unknown = sorted(set(parameters.keys()) - {"input", "output", "workato_user_opportunity_id"})
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has unknown keys: {unknown}")
    for side in ("input", "output"):
        payload = parameters.get(side)
        if not isinstance(payload, dict) or sorted(payload.keys()) != ["workspace"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} parameters.{side} must be exactly {{'workspace': ...}}"
            )
        workspace = payload["workspace"]
        if not isinstance(workspace, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} parameters.{side}.workspace must be an object")
        for key in WORKSPACE_ARRAY_KEYS:
            value = workspace.get(key)
            if (
                not isinstance(value, list)
                or not value
                or not all(isinstance(item, str) and item.strip() for item in value)
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} parameters.{side}.workspace.{key} must be a NON-EMPTY "
                    "array of non-empty strings: a nil/absent array renders the INSERT body "
                    "empty and faithfully errors the job (not a recipe branch); the strings "
                    "become quoted VALUES tuples so they must not contain quotes"
                )
            if any("'" in item or "," in item for item in value):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} parameters.{side}.workspace.{key} items must avoid "
                    f"quotes/commas (they are spliced into VALUES tuples verbatim): {value!r}"
                )
        limits = workspace.get("limits")
        if not isinstance(limits, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} parameters.{side}.workspace.limits missing")
        unknown_limits = sorted(set(limits.keys()) - WORKSPACE_LIMIT_KEYS)
        if unknown_limits:
            raise RuntimeError(
                f"recipe {RECIPE_ID} parameters.{side}.workspace.limits unknown keys: "
                f"{unknown_limits}"
            )
        for key, value in limits.items():
            if key == "data_retention_policy":
                if not isinstance(value, str):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {side} limits.data_retention_policy must be a string"
                    )
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {side} limits.{key} must be a JSON integer "
                    f"(integer_conversion schema; the ternaries compare and join raw values): "
                    f"{value!r}"
                )
        federated = workspace.get("federated_account")
        if not isinstance(federated, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} parameters.{side}.workspace.federated_account missing"
            )
        unknown_fed = sorted(set(federated.keys()) - FEDERATED_KEYS)
        if unknown_fed:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {side} federated_account unknown keys: {unknown_fed}"
            )
        for key, value in federated.items():
            if key == "saml_linking_enabled":
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {side} federated_account.{key} must be a JSON integer: "
                    f"{value!r}"
                )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("branch") not in KNOWN_BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch unknown: {expect.get('branch')!r}")
    stopped = expect.get("stopped")
    if not isinstance(stopped, bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be a boolean")
    if stopped:
        if expect.get("executed_action_count") != 7 or expect.get("tools") != []:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stop variants run exactly the 7 mock actions and call "
                f"no registry tool: {expect!r}"
            )
        if expect.get("return_value") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stop variants must pin a null return_value"
            )
    else:
        if expect.get("executed_action_count") != 8 or expect.get("tools") != ALLOWED_TOOLS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} success variants run 8 actions ending in return_result: "
                f"{expect!r}"
            )
        if expect.get("return_value") != {"success": "true"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} success variants must pin return_value "
                f"{{'success': 'true'}}: {expect.get('return_value')!r}"
            )
    query_sql = expect.get("query_sql")
    if not isinstance(query_sql, dict) or sorted(query_sql.keys()) != sorted(
        [CREATE_INPUT_AS, CREATE_OUTPUT_AS, INSERT_INPUT_AS, INSERT_OUTPUT_AS, COMPARE_AS]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.query_sql must pin all five query_list steps by id"
        )
    query_rows = expect.get("query_rows")
    if not isinstance(query_rows, dict) or sorted(query_rows.keys()) != sorted(query_sql.keys()):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.query_rows must pin all five query_list results by id"
        )
    limit_items = expect.get("limit_items")
    if (
        not isinstance(limit_items, list)
        or [item.get("key") for item in limit_items if isinstance(item, dict)] != EXPECTED_LIMIT_KEYS
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.limit_items must pin all 26 items in raw order "
            "(skipped items carry only their key)"
        )
    if not isinstance(expect.get("logger_message"), str) or not expect["logger_message"]:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.logger_message must be a non-empty string")


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
