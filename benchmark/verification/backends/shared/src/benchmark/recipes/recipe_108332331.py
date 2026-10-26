from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_108332331


RECIPE_ID = "108332331"
SEED_TYPE = "api_platform_workato_usage_account_profile_variant"
TRACK = "workato_api_platform_snowflake_workato_usage"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "458af9a1"
SEARCH_STEP_AS = "5a86b1ad"
SUCCESS_RETURN_AS = "426432f0"
CATCH_AS = "c96801ed"
CATCH_RETURN_AS = "1c0a9f98"
ACCOUNTS_TABLE = "product.workato_usage.accounts_dim"
ACCOUNT_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\","
    "\"line\":\"" + TRIGGER_AS + "\",\"path\":[\"request\", \"account_id\"]}')}"
)
RAW_SQL_TEMPLATE = (
    "select *\nfrom product.workato_usage.accounts_dim ad\n"
    "where ad.account_id = '" + ACCOUNT_ID_PILL + "'\nand ad.is_latest"
)
RAW_LIMIT = "1"
RAW_OFFSET = "0"
STRING_KEYS = (
    "account_id",
    "account_name",
    "industry",
    "owner_id",
    "owner",
    "success_owner_id",
    "success_owner",
    "subscription_start_date",
    "subscription_end_date",
    "cat_company_size",
    "current_plan",
    "limit_types",
    "cpq_contracts",
    "startdate",
    "enddate",
    "ai_opt_in",
    "plan_type",
    "plan_description",
    "pricing_model",
    "hard_deleted_date",
)
BOOLEAN_KEYS = (
    "active_subscription",
    "is_core",
    "is_direct",
    "is_embedded",
    "is_bpo",
    "is_partner",
    "is_paying",
    "is_churned",
    "is_latest",
    "is_deleted",
)
FLOAT_KEYS = (
    "current_arr",
    "current_arr_usd",
    "num_active_cpq_contracts",
    "task_limit",
    "hvr_tier_1_limit",
    "hvr_tier_2_limit",
    "hvr_tier_3_limit",
    "num_professional_services_opp",
    "num_standard_contract",
    "num_non_standard_contract",
    "num_non_professional_services_opp",
    "recipe_limit",
)
ACCOUNTS_COLUMNS: dict[str, str] = (
    {key: "string" for key in STRING_KEYS}
    | {key: "boolean" for key in BOOLEAN_KEYS}
    | {key: "float" for key in FLOAT_KEYS}
)
RESPONSE_KEYS = tuple(sorted(ACCOUNTS_COLUMNS))
EMPTY_OK_STRING_KEYS = {"hard_deleted_date"}
SQL_SAFE_TEXT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]*")


_STRUCTURE_PINS_JSON = r"""[
 {
  "as": "458af9a1",
  "input": {
   "request": {
    "content_type": "json",
    "schema": "[{\"name\":\"account_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"type\":\"string\",\"name\":\"account_id\"},{\"control_type\":\"text\",\"label\":\"Account name\",\"type\":\"string\",\"name\":\"account_name\"},{\"control_type\":\"text\",\"label\":\"Industry\",\"type\":\"string\",\"name\":\"industry\"},{\"control_type\":\"text\",\"label\":\"Owner ID\",\"type\":\"string\",\"name\":\"owner_id\"},{\"control_type\":\"text\",\"label\":\"Owner\",\"type\":\"string\",\"name\":\"owner\"},{\"control_type\":\"text\",\"label\":\"Success owner ID\",\"type\":\"string\",\"name\":\"success_owner_id\"},{\"control_type\":\"text\",\"label\":\"Success owner\",\"type\":\"string\",\"name\":\"success_owner\"},{\"control_type\":\"text\",\"label\":\"Active subscription\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Active subscription\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"active_subscription\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"active_subscription\"},{\"control_type\":\"number\",\"label\":\"Current arr\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"current_arr\"},{\"control_type\":\"number\",\"label\":\"Current arr usd\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"current_arr_usd\"},{\"control_type\":\"text\",\"label\":\"Subscription start date\",\"type\":\"string\",\"name\":\"subscription_start_date\"},{\"control_type\":\"text\",\"label\":\"Subscription end date\",\"type\":\"string\",\"name\":\"subscription_end_date\"},{\"control_type\":\"text\",\"label\":\"Cat company size\",\"type\":\"string\",\"name\":\"cat_company_size\"},{\"control_type\":\"text\",\"label\":\"Current plan\",\"type\":\"string\",\"name\":\"current_plan\"},{\"control_type\":\"text\",\"label\":\"Limit types\",\"type\":\"string\",\"name\":\"limit_types\"},{\"control_type\":\"text\",\"label\":\"Is core\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is core\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_core\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_core\"},{\"control_type\":\"text\",\"label\":\"Is direct\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is direct\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_direct\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_direct\"},{\"control_type\":\"text\",\"label\":\"Is embedded\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is embedded\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_embedded\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_embedded\"},{\"control_type\":\"text\",\"label\":\"Is bpo\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is bpo\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_bpo\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_bpo\"},{\"control_type\":\"text\",\"label\":\"Is partner\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is partner\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_partner\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_partner\"},{\"control_type\":\"text\",\"label\":\"Is paying\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is paying\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_paying\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_paying\"},{\"control_type\":\"text\",\"label\":\"Is churned\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is churned\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_churned\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_churned\"},{\"control_type\":\"text\",\"label\":\"Cpq contracts\",\"type\":\"string\",\"name\":\"cpq_contracts\"},{\"control_type\":\"number\",\"label\":\"Num active cpq contracts\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_active_cpq_contracts\"},{\"control_type\":\"text\",\"label\":\"Startdate\",\"type\":\"string\",\"name\":\"startdate\"},{\"control_type\":\"text\",\"label\":\"Enddate\",\"type\":\"string\",\"name\":\"enddate\"},{\"control_type\":\"text\",\"label\":\"Is latest\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is latest\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_latest\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_latest\"},{\"control_type\":\"number\",\"label\":\"Task limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"task_limit\"},{\"control_type\":\"number\",\"label\":\"HVR tier 1 limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"hvr_tier_1_limit\"},{\"control_type\":\"number\",\"label\":\"HVR tier 2 limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"hvr_tier_2_limit\"},{\"control_type\":\"number\",\"label\":\"HVR tier 3 limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"hvr_tier_3_limit\"},{\"control_type\":\"text\",\"label\":\"Ai opt in\",\"type\":\"string\",\"name\":\"ai_opt_in\"},{\"control_type\":\"text\",\"label\":\"Plan type\",\"type\":\"string\",\"name\":\"plan_type\"},{\"control_type\":\"text\",\"label\":\"Plan description\",\"type\":\"string\",\"name\":\"plan_description\"},{\"control_type\":\"text\",\"label\":\"Pricing model\",\"type\":\"string\",\"name\":\"pricing_model\"},{\"control_type\":\"number\",\"label\":\"Num professional services opp\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_professional_services_opp\"},{\"control_type\":\"number\",\"label\":\"Num standard contract\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_standard_contract\"},{\"control_type\":\"number\",\"label\":\"Num non standard contract\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_non_standard_contract\"},{\"control_type\":\"number\",\"label\":\"Num non professional services opp\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_non_professional_services_opp\"},{\"control_type\":\"number\",\"label\":\"Recipe limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"recipe_limit\"},{\"control_type\":\"text\",\"label\":\"Hard deleted date\",\"type\":\"string\",\"name\":\"hard_deleted_date\"},{\"control_type\":\"text\",\"label\":\"Is deleted\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is deleted\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_deleted\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_deleted\"}]",
      "http_status_code": "200",
      "name": "Success"
     },
     {
      "http_status_code": "500",
      "name": "failure"
     }
    ]
   }
  },
  "keyword": "trigger",
  "name": "receive_request",
  "number": 1,
  "provider": "workato_api_platform",
  "skip": false
 },
 {
  "as": null,
  "input": {},
  "keyword": "try",
  "name": null,
  "number": 2,
  "provider": null,
  "skip": false
 },
 {
  "as": "5a86b1ad",
  "input": {
   "limit": "1",
   "offset": "0",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"type\":\"string\",\"name\":\"account_id\"},{\"control_type\":\"text\",\"label\":\"Account name\",\"type\":\"string\",\"name\":\"account_name\"},{\"control_type\":\"text\",\"label\":\"Industry\",\"type\":\"string\",\"name\":\"industry\"},{\"control_type\":\"text\",\"label\":\"Owner ID\",\"type\":\"string\",\"name\":\"owner_id\"},{\"control_type\":\"text\",\"label\":\"Owner\",\"type\":\"string\",\"name\":\"owner\"},{\"control_type\":\"text\",\"label\":\"Success owner ID\",\"type\":\"string\",\"name\":\"success_owner_id\"},{\"control_type\":\"text\",\"label\":\"Success owner\",\"type\":\"string\",\"name\":\"success_owner\"},{\"control_type\":\"text\",\"label\":\"Active subscription\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Active subscription\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"active_subscription\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"active_subscription\"},{\"control_type\":\"number\",\"label\":\"Current arr\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"current_arr\"},{\"control_type\":\"number\",\"label\":\"Current arr usd\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"current_arr_usd\"},{\"control_type\":\"text\",\"label\":\"Subscription start date\",\"type\":\"string\",\"name\":\"subscription_start_date\"},{\"control_type\":\"text\",\"label\":\"Subscription end date\",\"type\":\"string\",\"name\":\"subscription_end_date\"},{\"control_type\":\"text\",\"label\":\"Cat company size\",\"type\":\"string\",\"name\":\"cat_company_size\"},{\"control_type\":\"text\",\"label\":\"Current plan\",\"type\":\"string\",\"name\":\"current_plan\"},{\"control_type\":\"text\",\"label\":\"Limit types\",\"type\":\"string\",\"name\":\"limit_types\"},{\"control_type\":\"text\",\"label\":\"Is core\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is core\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_core\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_core\"},{\"control_type\":\"text\",\"label\":\"Is direct\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is direct\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_direct\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_direct\"},{\"control_type\":\"text\",\"label\":\"Is embedded\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is embedded\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_embedded\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_embedded\"},{\"control_type\":\"text\",\"label\":\"Is bpo\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is bpo\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_bpo\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_bpo\"},{\"control_type\":\"text\",\"label\":\"Is partner\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is partner\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_partner\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_partner\"},{\"control_type\":\"text\",\"label\":\"Is paying\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is paying\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_paying\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_paying\"},{\"control_type\":\"text\",\"label\":\"Is churned\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is churned\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_churned\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_churned\"},{\"control_type\":\"text\",\"label\":\"Cpq contracts\",\"type\":\"string\",\"name\":\"cpq_contracts\"},{\"control_type\":\"number\",\"label\":\"Num active cpq contracts\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_active_cpq_contracts\"},{\"control_type\":\"text\",\"label\":\"Startdate\",\"type\":\"string\",\"name\":\"startdate\"},{\"control_type\":\"text\",\"label\":\"Enddate\",\"type\":\"string\",\"name\":\"enddate\"},{\"control_type\":\"text\",\"label\":\"Is latest\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is latest\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_latest\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_latest\"},{\"control_type\":\"number\",\"label\":\"Task limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"task_limit\"},{\"control_type\":\"number\",\"label\":\"HVR tier 1 limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"hvr_tier_1_limit\"},{\"control_type\":\"number\",\"label\":\"HVR tier 2 limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"hvr_tier_2_limit\"},{\"control_type\":\"number\",\"label\":\"HVR tier 3 limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"hvr_tier_3_limit\"},{\"control_type\":\"text\",\"label\":\"Ai opt in\",\"type\":\"string\",\"name\":\"ai_opt_in\"},{\"control_type\":\"text\",\"label\":\"Plan type\",\"type\":\"string\",\"name\":\"plan_type\"},{\"control_type\":\"text\",\"label\":\"Plan description\",\"type\":\"string\",\"name\":\"plan_description\"},{\"control_type\":\"text\",\"label\":\"Pricing model\",\"type\":\"string\",\"name\":\"pricing_model\"},{\"control_type\":\"number\",\"label\":\"Num professional services opp\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_professional_services_opp\"},{\"control_type\":\"number\",\"label\":\"Num standard contract\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_standard_contract\"},{\"control_type\":\"number\",\"label\":\"Num non standard contract\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_non_standard_contract\"},{\"control_type\":\"number\",\"label\":\"Num non professional services opp\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"num_non_professional_services_opp\"},{\"control_type\":\"number\",\"label\":\"Recipe limit\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"recipe_limit\"},{\"control_type\":\"text\",\"label\":\"Hard deleted date\",\"type\":\"string\",\"name\":\"hard_deleted_date\"},{\"control_type\":\"text\",\"label\":\"Is deleted\",\"render_input\":null,\"parse_output\":null,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is deleted\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\",\"name\":\"is_deleted\",\"render_input\":null,\"parse_output\":null},\"type\":\"boolean\",\"name\":\"is_deleted\"}]",
   "parameters": {
    "schema": "[]"
   },
   "sql": "select *\nfrom product.workato_usage.accounts_dim ad\nwhere ad.account_id = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"458af9a1\",\"path\":[\"request\", \"account_id\"]}')}'\nand ad.is_latest"
  },
  "keyword": "action",
  "name": "search_rows_sql",
  "number": 3,
  "provider": "snowflake",
  "skip": false
 },
 {
  "as": "426432f0",
  "input": {
   "http_status_code": "200",
   "response": {
    "account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id_54508f65\"]}')}",
    "account_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_name_3c1f99b1\"]}')}",
    "active_subscription": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"active_subscription_6d868af2\"]}')}",
    "ai_opt_in": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"ai_opt_in_cb0aa35c\"]}')}",
    "cat_company_size": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"cat_company_size_733d40af\"]}')}",
    "cpq_contracts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"cpq_contracts_9c7f783e\"]}')}",
    "current_arr": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_arr_db5a18cb\"]}')}",
    "current_arr_usd": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_arr_usd_2cf78073\"]}')}",
    "current_plan": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_plan_21067bdb\"]}')}",
    "enddate": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"enddate_d845b407\"]}')}",
    "hard_deleted_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"hard_deleted_date_715d6bdb\"]}')}",
    "hvr_tier_1_limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"hvr_tier_1_limit_6675d7f8\"]}')}",
    "hvr_tier_2_limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"hvr_tier_2_limit_37651d2b\"]}')}",
    "hvr_tier_3_limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"hvr_tier_3_limit_6fc355d3\"]}')}",
    "industry": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"industry_a03f151f\"]}')}",
    "is_bpo": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_bpo_d8c801fe\"]}')}",
    "is_churned": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_churned_784f6c8c\"]}')}",
    "is_core": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_core_e8b3932c\"]}')}",
    "is_deleted": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_deleted_60962d1e\"]}')}",
    "is_direct": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_direct_1d187968\"]}')}",
    "is_embedded": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_embedded_e24ad27b\"]}')}",
    "is_latest": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_latest_cdd7c6c2\"]}')}",
    "is_partner": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_partner_a3250d7f\"]}')}",
    "is_paying": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_paying_a5ce168b\"]}')}",
    "limit_types": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"limit_types_746c4197\"]}')}",
    "num_active_cpq_contracts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"num_active_cpq_contracts_261240ea\"]}')}",
    "num_non_professional_services_opp": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"num_non_professional_services_opp_e3e786ba\"]}')}",
    "num_non_standard_contract": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"num_non_standard_contract_861c491e\"]}')}",
    "num_professional_services_opp": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"num_professional_services_opp_015415a9\"]}')}",
    "num_standard_contract": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"num_standard_contract_26881f7c\"]}')}",
    "owner": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner_0f2d6414\"]}')}",
    "owner_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner_id_dd3604dc\"]}')}",
    "plan_description": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"plan_description_4d8f65b9\"]}')}",
    "plan_type": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"plan_type_c6fc5a15\"]}')}",
    "pricing_model": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"pricing_model_e5c8b282\"]}')}",
    "recipe_limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"recipe_limit_7741c5ba\"]}')}",
    "startdate": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"startdate_f6537ddf\"]}')}",
    "subscription_end_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"subscription_end_date_0e479ba9\"]}')}",
    "subscription_start_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"subscription_start_date_f2958fdf\"]}')}",
    "success_owner": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"success_owner_13bd34df\"]}')}",
    "success_owner_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"success_owner_id_a185d7d7\"]}')}",
    "task_limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"task_limit_6a8058a2\"]}')}"
   }
  },
  "keyword": "action",
  "name": "return_response",
  "number": 4,
  "provider": "workato_api_platform",
  "skip": false
 },
 {
  "as": "c96801ed",
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  },
  "keyword": "catch",
  "name": null,
  "number": 5,
  "provider": null,
  "skip": false
 },
 {
  "as": "1c0a9f98",
  "input": {
   "http_status_code": "500"
  },
  "keyword": "action",
  "name": "return_response",
  "number": 6,
  "provider": "workato_api_platform",
  "skip": false
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
SUCCESS_TOOLS = ["snowflake.search_rows_sql", "workato_api_platform.return_response"]
CATCH_TOOLS = ["workato_api_platform.return_response"]
EXPECT_KEYS = (
    "case",
    "outcome",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "http_status_code",
    "response",
    "sql_row_count",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("account_found_200", "account_not_found_200", "catch_500")
VALUE_KEYS = (
    "args_contains",
    "result_count",
    "response_contains",
    "result_contains",
    "created",
    "http_status_code",
    "text_fragments",
    "options_contains",
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
    if node.get("keyword") == "foreach":
        pin["repeat_mode"] = node.get("repeat_mode")
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_108332331(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} (step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    sql_pin = next(pin for pin in actual if pin["as"] == SEARCH_STEP_AS)
    if sql_pin["input"].get("sql") != RAW_SQL_TEMPLATE:
        raise RuntimeError(f"recipe {RECIPE_ID} search SQL changed: {sql_pin['input'].get('sql')!r}")
    if sql_pin["input"].get("limit") != RAW_LIMIT or sql_pin["input"].get("offset") != RAW_OFFSET:
        raise RuntimeError(f"recipe {RECIPE_ID} search limit/offset changed")
    success_pin = next(pin for pin in actual if pin["as"] == SUCCESS_RETURN_AS)
    mapping = (success_pin["input"].get("response") or {})
    if tuple(sorted(mapping)) != RESPONSE_KEYS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} 42-field response mapping changed: {sorted(mapping)}"
        )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "snowflake_tables": [ACCOUNTS_TABLE],
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


def resolved_sql(trigger: dict[str, Any]) -> str:
    request = trigger.get("request") or {}
    return RAW_SQL_TEMPLATE.replace(ACCOUNT_ID_PILL, str(request.get("account_id")))


def _require_trigger(trigger: Any) -> str:
    request = (trigger or {}).get("request") if isinstance(trigger, dict) else None
    if (
        not isinstance(trigger, dict)
        or sorted(trigger.keys()) != ["request"]
        or not isinstance(request, dict)
        or sorted(request.keys()) != ["account_id"]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger must be exactly {{'request': "
            f"{{'account_id'}}}} (the only request schema field): {trigger!r}"
        )
    account_id = request["account_id"]
    if not isinstance(account_id, str) or not SQL_SAFE_TEXT_RE.fullmatch(account_id):
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.account_id must be a SQL-quote-safe string "
            f"(it interpolates inside single quotes in the SQL text): {account_id!r}"
        )
    return account_id


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [ACCOUNTS_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{ACCOUNTS_TABLE!r} (the literal 3-part SQL name)"
        )
    spec = tables[ACCOUNTS_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != ACCOUNTS_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table must declare exactly the full 42-column set "
            f"(select * returns whatever the physical table has; FLOAT numerics keep "
            f"fractional pins exact)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table rows must be NON-EMPTY — the not-found branch "
            "proves the WHERE arms via stale/other-account decoys, never an empty table"
        )
    latest_by_account: dict[str, int] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(ACCOUNTS_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must fill ALL 42 columns (a NULL "
                f"would silently null its response field — the not-found variant owns "
                f"the null path); got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for key in STRING_KEYS:
            value = row[key]
            if not isinstance(value, str) or (not value.strip() and key not in EMPTY_OK_STRING_KEYS):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {idx} column {key} must be a non-empty "
                    f"string (only {sorted(EMPTY_OK_STRING_KEYS)} may be ''): {value!r}"
                )
        for key in BOOLEAN_KEYS:
            if not isinstance(row[key], bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {idx} column {key} must be a strict "
                    f"boolean: {row[key]!r}"
                )
        for key in FLOAT_KEYS:
            if isinstance(row[key], bool) or not isinstance(row[key], (int, float)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {idx} column {key} must be numeric "
                    f"(seeded onto a FLOAT column): {row[key]!r}"
                )
        if row["is_latest"]:
            latest_by_account[row["account_id"]] = latest_by_account.get(row["account_id"], 0) + 1
    for account, count in latest_by_account.items():
        if count > 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} at most ONE is_latest row per account — `limit 1` "
                f"over {count} matches would be order-non-deterministic: {account!r}"
            )
    return rows


def _coerced_field(key: str, value: Any) -> Any:
    # FLOAT columns come back as Python floats (an int seed reads back x.0);
    # BOOLEAN and VARCHAR round-trip natively.
    if key in FLOAT_KEYS:
        return float(value)
    return value


def _derived_response(rows: list[dict[str, Any]], account_id: str) -> tuple[dict[str, Any], int]:
    matched = [row for row in rows if row["account_id"] == account_id and row["is_latest"]]
    if not matched:
        return {key: None for key in RESPONSE_KEYS}, 0
    row = matched[0]
    return {key: _coerced_field(key, row[key]) for key in RESPONSE_KEYS}, len(matched)


def _require_expect(
    expect: Any,
    force: Any,
    derived: dict[str, Any] | None,
    row_count: int | None,
    trigger: dict[str, Any],
) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if (outcome == "catch_500") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch outcome and force_action_error must be "
            "declared together (the pill-in-SQL text has no other deterministic failure)"
        )
    tools = expect.get("tools")
    items = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(items, list) or len(items) != len(tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expected call"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("tool") != tools[idx]:
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] does not match tools")
        if not any(key in item for key in VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] carries no value-asserting key"
            )
    if outcome == "catch_500":
        checks = (
            derived is None,
            expect.get("http_status_code") == "500",
            expect.get("response") == {},
            expect.get("catch_message") == (force or {}).get("error"),
            expect.get("sql_row_count") is None,
            expect.get("executed_action_count") == 1,
            tools == CATCH_TOOLS,
            items[0].get("http_status_code") == "500",
        )
        reason = (
            "catch variants pin the BODYLESS 500 (response {}), catch_message, "
            "1 action and no snowflake seed"
        )
    else:
        if derived is None or row_count is None:
            raise RuntimeError(f"recipe {RECIPE_ID} data variants require a snowflake_live seed")
        if outcome == "account_found_200" and row_count != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} account_found_200 requires exactly ONE matching "
                f"is_latest row; derived {row_count}"
            )
        if outcome == "account_not_found_200" and row_count != 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} account_not_found_200 requires ZERO matching rows "
                f"(all 42 response fields null); derived {row_count}"
            )
        checks = (
            expect.get("http_status_code") == "200",
            expect.get("response") == derived,
            expect.get("sql_row_count") == row_count,
            expect.get("executed_action_count") == 2,
            tools == SUCCESS_TOOLS,
            "catch_message" not in expect,
            items[0].get("args_contains")
            == {
                "sql": resolved_sql(trigger),
                "limit": RAW_LIMIT,
                "offset": RAW_OFFSET,
                "parameters": {},
            },
            items[0].get("result_count") == row_count,
            items[1].get("http_status_code") == "200",
            items[1].get("response_contains") == derived,
        )
        reason = (
            "data variants must pin the EXACT pill-resolved SQL text with limit '1'/"
            "offset '0'/no bind parameters, sql_row_count (1 found / 0 not-found) and "
            f"the EXACT derived 42-field object {derived!r}"
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome "
            f"{outcome!r} ({reason}): {expect!r}"
        )


def seed_108332331(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108332331(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    account_id = _require_trigger(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    force = data.get("force_action_error")
    if force is not None:
        if not isinstance(force, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
        if str(force.get("step_as") or "") != SEARCH_STEP_AS or not str(force.get("error") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target step_as "
                f"{SEARCH_STEP_AS!r} with an explicit error message"
            )
        if seed_in != {}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must seed NOTHING (the forced error "
                f"fires before the snowflake adapter): {sorted(seed_in)}"
            )
        derived = None
        row_count = None
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} data variants must seed exactly the snowflake_live "
                f"section; got {sorted(seed_in.keys())}"
            )
        rows = _require_snowflake_section(seed_in["snowflake_live"])
        derived, row_count = _derived_response(rows, account_id)
    _require_expect(data.get("expect"), force, derived, row_count, trigger)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
    }
    if force is None:
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_108332331(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108332331(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a "
            "forced catch error — nothing to run"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": trigger,
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx, live)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, live)
    finally:
        if live:
            # Required cleanup: ACCOUNTS_DIM is benchmark-owned create-or-replace
            # state in the shared WORKATO_USAGE schema — drop it whether or not
            # the run completed. Catch variants own NO live state.
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if live and not (snowflake_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {snowflake_cleanup}")
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_108332331(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if not live:
        return {}
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
