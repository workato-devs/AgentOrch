from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_126727654


RECIPE_ID = "126727654"
SEED_TYPE = "feedback_features_pubsub_snowflake_sync_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_pub_sub"
TRIGGER_NAME = "batch_subscribe_to_topic"
TRIGGER_AS = "4b945496"
TOPIC_ID = "29770"
BATCH_SIZE = 5
DECLARE_STEP_AS = "52ceb148"
CREATE_LIST_STEP_AS = "2f8bcd17"
DEDUP_QUERY_STEP_AS = "a2248f44"
FEATURES_UPSERT_STEP_AS = "9ee39bf1"
STATUS_QUERY_STEP_AS = "bf6a7af9"
UPDATES_UPSERT_STEP_AS = "d80f131c"
FINAL_QUERY_STEP_AS = "8721b984"
FEATURES_TABLE = "FEEDBACK.FEATURES_F"
UPDATES_TABLE = "FEEDBACK.FEATURE_UPDATES_F"
PRODUCTION_USER_NAME = "Environment Production"

# workato_pub_sub.batch_subscribe_to_topic (as 4b945496, topic_id 29770,
# batch_size 5, since_offset -604800) — byte-identical twin of 126727318 except this topic_id (diff-verified). Body:
#   2  workato_variable.declare_list 52ceb148 'feedback.features_f': one row
#      per trigger message; formulas: creator/requested_by/groups/uploads
#      .to_json (the engine renders SORTED compact JSON, so every seeded
#      object must be authored with alphabetized keys to stay byte-equal to
#      Ruby's insertion-order render), the seven non-created *_at pills
#      .in_time_zone("UTC") (PLAIN chain: a nil *_at raises — that raise is
#      NOT a recipe branch, so every seeded *_at is non-nil), created_at and
#      the scalar fields plain interpolation (created_at keeps its raw seeded
#      form until step 6), tags/products/owners bare array pills
#   3  workato_smart_list.create_list 2f8bcd17 'feedback_raw' (primary id) —
#      arrays round-trip through SQLite as json.dumps text: tags/products/
#      owners become '["a", "b"]' (WITH the ", " space), unlike the .to_json
#      fields' compact '["a","b"]'
#   4  workato_smart_list.query_list a2248f44: SELECT DISTINCT f.* + JOIN
#      (SELECT id, MAX(updated_at) ... GROUP BY id) — latest revision per id
#   IF 5 (job_context.user_name equals_to 'Environment Production' — gates
#      ALL live writes and queries 2/3):
#     6  snowflake.upsert_rows_batch 9ee39bf1 (LIVE): FEEDBACK.FEATURES_F key
#        ID; *_at re-rendered via '&.in_time_zone("UTC")' (created_at only
#        now converts to '+00:00'); 31 mapped columns — tags / is_private /
#        products_list / groups_list / resolved_by_user_name are NOT written
#     7  workato_smart_list.query_list bf6a7af9: id, status,
#        IFNULL(MIN(updated_by_user_id), MIN(resolved_by_user_id)) as
#        updated_by, MAX(status_changed_at) GROUP BY id,status
#     8  snowflake.upsert_rows_batch d80f131c (LIVE):
#        FEEDBACK.FEATURE_UPDATES_F, multi-key FEATURE_ID\nUPDATED_AT
#     9  workato_smart_list.query_list 8721b984: dedup join by (id, status,
#        updated_by, status_updated_at) — terminal read, output unused (a
#        NULL updated_by row drops out of this join: SQL NULL semantics)
#
# Backends: the pub_sub trigger and the variable/smart-list steps are
# Workato-internal (mock/engine); ONLY the two upserts run LIVE against
# Snowflake. Both tables are benchmark-owned create-or-replace seeds with
# registered drops in the runner's finally. All *_at / JSON-text columns are
# seeded VARCHAR so every rendered byte is pinned verbatim; the id/count
# columns are NUMBER. TWIN: 126727654 (topic 29770) and 126727318 (topic
# 29184) share these live FEEDBACK.* tables — their live runs MUST be
# serialized (never run the twins concurrently).

_RAW_PIN_JSON = r"""{"as": "4b945496", "block": [{"as": "52ceb148", "block": [], "input": {"list_item_schema_json": "[{\"control_type\":\"integer\",\"label\":\"ID\",\"parse_output\":\"integer_conversion\",\"name\":\"id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"text\",\"label\":\"Title\",\"name\":\"title\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Description\",\"name\":\"description\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Resolution\",\"name\":\"resolution\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Status\",\"name\":\"status\",\"type\":\"string\"},{\"control_type\":\"integer\",\"label\":\"Vendor ID\",\"parse_output\":\"integer_conversion\",\"name\":\"vendor_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Created by user ID\",\"parse_output\":\"integer_conversion\",\"name\":\"created_by_user_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Updated by user ID\",\"parse_output\":\"integer_conversion\",\"name\":\"updated_by_user_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Resolved by user ID\",\"parse_output\":\"integer_conversion\",\"name\":\"resolved_by_user_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Merged to case ID\",\"parse_output\":\"integer_conversion\",\"name\":\"merged_to_case_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"text\",\"label\":\"Form entry\",\"name\":\"form_entry\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"App URL\",\"name\":\"app_url\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Created at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"created_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Updated at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"updated_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Declined at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"declined_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Developing at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"developing_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Planned at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"planned_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Released at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"released_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Waiting at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"waiting_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Status changed at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"status_changed_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Requested by\",\"name\":\"requested_by\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Status name\",\"name\":\"status_name\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Merged to feature ID\",\"name\":\"merged_to_feature_id\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Vendor name\",\"name\":\"vendor_name\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Is private\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"control_type\":\"text\",\"label\":\"Is private\",\"name\":\"is_private\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\"},\"name\":\"is_private\",\"type\":\"boolean\"},{\"control_type\":\"integer\",\"label\":\"View count\",\"parse_output\":\"integer_conversion\",\"name\":\"view_count\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Effort\",\"parse_output\":\"integer_conversion\",\"name\":\"effort\",\"optional\":false,\"type\":\"integer\"},{\"name\":\"tags\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Tags\"},{\"name\":\"products\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Products\"},{\"name\":\"groups\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Groups\"},{\"control_type\":\"text\",\"label\":\"Resolved by user name\",\"name\":\"resolved_by_user_name\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Creator\",\"name\":\"creator\",\"type\":\"string\"},{\"name\":\"uploads\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Uploads\"},{\"name\":\"owners\",\"type\":\"array\",\"of\":\"string\",\"label\":\"owners\"},{\"control_type\":\"text\",\"label\":\"Products list\",\"name\":\"products_list\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Groups list\",\"name\":\"groups_list\",\"type\":\"string\"}]", "list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\"]}')}", "app_url": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"app_url\"]}')}", "created_at": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"created_at\"]}')}", "created_by_user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"created_by_user_id\"]}')}", "creator": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"creator\"]}').to_json", "declined_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"declined_at\"]}').in_time_zone(\"UTC\")", "description": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"description\"]}')}", "developing_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"developing_at\"]}').in_time_zone(\"UTC\")", "effort": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"effort\"]}')}", "form_entry": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"form_entry\"]}')}", "groups": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"groups\"]}').to_json", "groups_list": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"groups_list\"]}')}", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"id\"]}')}", "is_private": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"is_private\"]}')}", "merged_to_case_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"merged_to_case_id\"]}')}", "merged_to_feature_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"merged_to_feature_id\"]}')}", "owners": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"owners\"]}')", "planned_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"planned_at\"]}').in_time_zone(\"UTC\")", "products": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"products\"]}')", "products_list": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"products_list\"]}')}", "released_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"released_at\"]}').in_time_zone(\"UTC\")", "requested_by": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"requested_by\"]}').to_json", "resolution": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"resolution\"]}')}", "resolved_by_user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"resolved_by_user_id\"]}')}", "resolved_by_user_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"resolved_by_user_name\"]}')}", "status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"status\"]}')}", "status_changed_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"status_changed_at\"]}').in_time_zone(\"UTC\")", "status_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"status_name\"]}')}", "tags": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"tags\"]}')", "title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"title\"]}')}", "updated_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"updated_at\"]}').in_time_zone(\"UTC\")", "updated_by_user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"updated_by_user_id\"]}')}", "uploads": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"uploads\"]}').to_json", "vendor_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"vendor_id\"]}')}", "vendor_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"vendor_name\"]}')}", "view_count": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\", {\"path_element_type\": \"current_item\"}, \"case\", \"view_count\"]}')}", "waiting_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"4b945496\",\"path\":[\"messages\",{\"path_element_type\":\"current_item\"},\"case\",\"waiting_at\"]}').in_time_zone(\"UTC\")"}, "name": "feedback.features_f"}, "keyword": "action", "name": "declare_list", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "2f8bcd17", "block": [], "input": {"list_name": "feedback_raw", "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"52ceb148\",\"path\":[\"list_items\"]}')", "primary_index": "id"}, "keyword": "action", "name": "create_list", "number": 3, "provider": "workato_smart_list", "skip": false}, {"as": "a2248f44", "block": [], "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"control_type\":\"integer\",\"label\":\"ID\",\"parse_output\":\"integer_conversion\",\"name\":\"id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"text\",\"label\":\"Title\",\"name\":\"title\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Description\",\"name\":\"description\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Resolution\",\"name\":\"resolution\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Status\",\"name\":\"status\",\"type\":\"string\"},{\"control_type\":\"integer\",\"label\":\"Vendor ID\",\"parse_output\":\"integer_conversion\",\"name\":\"vendor_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Created by user ID\",\"parse_output\":\"integer_conversion\",\"name\":\"created_by_user_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Updated by user ID\",\"parse_output\":\"integer_conversion\",\"name\":\"updated_by_user_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Resolved by user ID\",\"parse_output\":\"integer_conversion\",\"name\":\"resolved_by_user_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Merged to case ID\",\"parse_output\":\"integer_conversion\",\"name\":\"merged_to_case_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"text\",\"label\":\"Form entry\",\"name\":\"form_entry\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"App URL\",\"name\":\"app_url\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Created at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"created_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Updated at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"updated_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Declined at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"declined_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Developing at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"developing_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Planned at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"planned_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Released at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"released_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Waiting at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"waiting_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Status changed at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"status_changed_at\",\"type\":\"date_time\"},{\"control_type\":\"text\",\"label\":\"Requested by\",\"name\":\"requested_by\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Status name\",\"name\":\"status_name\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Merged to feature ID\",\"name\":\"merged_to_feature_id\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Vendor name\",\"name\":\"vendor_name\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Is private\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"control_type\":\"text\",\"label\":\"Is private\",\"name\":\"is_private\",\"toggle_hint\":\"Use custom value\",\"type\":\"boolean\"},\"name\":\"is_private\",\"type\":\"boolean\"},{\"control_type\":\"integer\",\"label\":\"View count\",\"parse_output\":\"integer_conversion\",\"name\":\"view_count\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"integer\",\"label\":\"Effort\",\"parse_output\":\"integer_conversion\",\"name\":\"effort\",\"optional\":false,\"type\":\"integer\"},{\"name\":\"tags\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Tags\"},{\"name\":\"products\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Products\"},{\"name\":\"groups\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Groups\"},{\"control_type\":\"text\",\"label\":\"Resolved by user name\",\"name\":\"resolved_by_user_name\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Creator\",\"name\":\"creator\",\"type\":\"string\"},{\"name\":\"uploads\",\"type\":\"array\",\"of\":\"string\",\"label\":\"Uploads\"},{\"name\":\"owners\",\"type\":\"array\",\"of\":\"string\",\"label\":\"owners\"},{\"control_type\":\"text\",\"label\":\"Products list\",\"name\":\"products_list\",\"type\":\"string\"},{\"control_type\":\"text\",\"label\":\"Groups list\",\"name\":\"groups_list\",\"type\":\"string\"}]", "sql": "SELECT DISTINCT f.*\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"list_name\"]}')} f\nJOIN (\n\tSELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')} as id, MAX(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"updated_at\"]}')}) as updated_at\n\tFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"list_name\"]}')} \n\tGROUP BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')}\n) d on d.id = f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')} and d.updated_at = f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"updated_at\"]}')}"}, "keyword": "action", "name": "query_list", "number": 4, "provider": "workato_smart_list", "skip": false}, {"as": "", "block": [{"as": "9ee39bf1", "block": [], "input": {"key_columns": "ID", "rows": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\"]}')}", "app_url": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"app_url\"]}')}", "created_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"created_at\"]}')&.in_time_zone(\"UTC\")", "created_by_user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"created_by_user_id\"]}')}", "creator": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"creator\"]}')}", "declined_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"declined_at\"]}')&.in_time_zone(\"UTC\")", "description": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"description\"]}')}", "developing_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"developing_at\"]}')&.in_time_zone(\"UTC\")", "effort": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"effort\"]}')}", "form_entry": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"form_entry\"]}')}", "groups": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"groups\"]}')}", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "merged_to_case_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"merged_to_case_id\"]}')}", "merged_to_feature_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"merged_to_feature_id\"]}')}", "owners": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owners\"]}')}", "planned_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"planned_at\"]}')&.in_time_zone(\"UTC\")", "products": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"products\"]}')}", "released_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"released_at\"]}')&.in_time_zone(\"UTC\")", "requested_by": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"requested_by\"]}')}", "resolution": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"resolution\"]}')}", "resolved_by_user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"resolved_by_user_id\"]}')}", "status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"status\"]}')}", "status_changed_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"status_changed_at\"]}')&.in_time_zone(\"UTC\")", "status_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"status_name\"]}')}", "title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"title\"]}')}", "updated_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"updated_at\"]}')&.in_time_zone(\"UTC\")", "updated_by_user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"updated_by_user_id\"]}')}", "uploads": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"uploads\"]}')}", "vendor_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"vendor_id\"]}')}", "vendor_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"vendor_name\"]}')}", "view_count": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"view_count\"]}')}", "waiting_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a2248f44\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"waiting_at\"]}')&.in_time_zone(\"UTC\")"}, "table": "FEEDBACK.FEATURES_F"}, "keyword": "action", "name": "upsert_rows_batch", "number": 6, "provider": "snowflake", "skip": false}, {"as": "bf6a7af9", "block": [], "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"control_type\":\"integer\",\"label\":\"ID\",\"parse_output\":\"integer_conversion\",\"name\":\"id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"text\",\"label\":\"Status\",\"name\":\"status\",\"type\":\"string\"},{\"name\":\"updated_by\",\"type\":\"string\",\"optional\":false,\"label\":\"updated_by\",\"control_type\":\"text\"},{\"label\":\"status_updated_at\",\"name\":\"status_updated_at\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date_time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\"}]", "sql": "\tSELECT \n  \t\t#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')} as id, \n  \t\t#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status\"]}')} as status, \n  \t\tIFNULL(MIN(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"updated_by_user_id\"]}')}),MIN(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"resolved_by_user_id\"]}')})) as updated_by,\n  \t\tMAX(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status_changed_at\"]}')}) as status_updated_at\n\tFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"list_name\"]}')} \n\tGROUP BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status\"]}')}"}, "keyword": "action", "name": "query_list", "number": 7, "provider": "workato_smart_list", "skip": false}, {"as": "d80f131c", "block": [], "input": {"key_columns": "FEATURE_ID\nUPDATED_AT", "rows": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bf6a7af9\",\"path\":[\"rows\"]}')}", "feature_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bf6a7af9\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bf6a7af9\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"status\"]}')}", "updated_at": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bf6a7af9\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"status_updated_at\"]}').in_time_zone(\"UTC\")", "updated_by_user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bf6a7af9\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"updated_by\"]}')}"}, "table": "FEEDBACK.FEATURE_UPDATES_F"}, "keyword": "action", "name": "upsert_rows_batch", "number": 8, "provider": "snowflake", "skip": false}, {"as": "8721b984", "block": [], "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"control_type\":\"integer\",\"label\":\"ID\",\"parse_output\":\"integer_conversion\",\"name\":\"id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"text\",\"label\":\"Status\",\"name\":\"status\",\"type\":\"string\"},{\"control_type\":\"integer\",\"label\":\"Updated by user ID\",\"parse_output\":\"integer_conversion\",\"name\":\"updated_by_user_id\",\"optional\":false,\"type\":\"integer\"},{\"control_type\":\"text\",\"label\":\"Updated at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"updated_at\",\"type\":\"date_time\"}]", "sql": "SELECT DISTINCT f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')}, f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status\"]}')}, f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"updated_by_user_id\"]}')}, f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status_changed_at\"]}')}\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"list_name\"]}')} f\nJOIN (\n\tSELECT \n  \t\t#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')} as id, \n  \t\t#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status\"]}')} as status, \n  \t\tMIN(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"updated_by_user_id\"]}')}) as updated_by,\n  \t\tMAX(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status_changed_at\"]}')}) as status_updated_at\n\tFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"list_name\"]}')} \n\tGROUP BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status\"]}')}\n) d on d.id = f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"id\"]}')} and d.status = f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status\"]}')} and d.updated_by = f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"updated_by_user_id\"]}')} and d.status_updated_at = f.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2f8bcd17\",\"path\":[\"columns\", \"status_changed_at\"]}')}"}, "keyword": "action", "name": "query_list", "number": 9, "provider": "workato_smart_list", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"user_name\"]}')}", "operand": "equals_to", "rhs": "Environment Production"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 5, "provider": "", "skip": false}], "input": {"batch_size": "5", "since_offset": "-604800", "topic_id": "29770"}, "keyword": "trigger", "name": "batch_subscribe_to_topic", "number": 1, "provider": "workato_pub_sub", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_list"),
    (CREATE_LIST_STEP_AS, "workato_smart_list", "create_list"),
    (DEDUP_QUERY_STEP_AS, "workato_smart_list", "query_list"),
    (FEATURES_UPSERT_STEP_AS, "snowflake", "upsert_rows_batch"),
    (STATUS_QUERY_STEP_AS, "workato_smart_list", "query_list"),
    (UPDATES_UPSERT_STEP_AS, "snowflake", "upsert_rows_batch"),
    (FINAL_QUERY_STEP_AS, "workato_smart_list", "query_list"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "snowflake.upsert_rows_batch",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.upsert_rows_batch",
]
CASE_INT_KEYS = (
    "id", "vendor_id", "created_by_user_id", "resolved_by_user_id",
    "merged_to_case_id", "view_count", "effort",
)
CASE_AT_KEYS = (
    "created_at", "updated_at", "declined_at", "developing_at",
    "planned_at", "released_at", "waiting_at", "status_changed_at",
)
CASE_STRING_KEYS = (
    "title", "description", "resolution", "status", "form_entry", "app_url",
    "status_name", "merged_to_feature_id", "vendor_name",
    "resolved_by_user_name", "products_list", "groups_list",
)
CASE_ARRAY_KEYS = ("tags", "products", "owners")
CASE_OBJECT_KEYS = ("creator", "requested_by")
CASE_OBJECT_LIST_KEYS = ("groups", "uploads")
CASE_KEYS = tuple(sorted(
    CASE_INT_KEYS + ("updated_by_user_id", "is_private") + CASE_AT_KEYS
    + CASE_STRING_KEYS + CASE_ARRAY_KEYS + CASE_OBJECT_KEYS + CASE_OBJECT_LIST_KEYS
))
FEATURES_COLUMNS = {
    "app_url": "string",
    "created_at": "string",
    "created_by_user_id": "number",
    "creator": "string",
    "declined_at": "string",
    "description": "string",
    "developing_at": "string",
    "effort": "number",
    "form_entry": "string",
    "groups": "string",
    "id": "number",
    "merged_to_case_id": "number",
    "merged_to_feature_id": "string",
    "owners": "string",
    "planned_at": "string",
    "products": "string",
    "released_at": "string",
    "requested_by": "string",
    "resolution": "string",
    "resolved_by_user_id": "number",
    "status": "string",
    "status_changed_at": "string",
    "status_name": "string",
    "title": "string",
    "updated_at": "string",
    "updated_by_user_id": "number",
    "uploads": "string",
    "vendor_id": "number",
    "vendor_name": "string",
    "view_count": "number",
    "waiting_at": "string",
}
UPDATES_COLUMNS = {
    "feature_id": "number",
    "status": "string",
    "updated_at": "string",
    "updated_by_user_id": "number",
}
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "production_branch",
    "dedup_query_rows",
    "status_query_rows",
    "final_query_rows",
    "upsert_counts",
    "final_snowflake_tables",
)
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}


def validate_126727654(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    trigger_in = raw.get("input") or {}
    if (
        str(trigger_in.get("topic_id") or "") != TOPIC_ID
        or str(trigger_in.get("batch_size") or "") != str(BATCH_SIZE)
        or str(trigger_in.get("since_offset") or "") != "-604800"
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input changed (topic {TOPIC_ID} is THE twin "
            f"discriminator): {trigger_in!r}"
        )
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone inputs (the tree pin holds exact bytes).
    for node in _walk_nodes(raw):
        step = str(node.get("as") or "")
        node_input = node.get("input") or {}
        if node.get("keyword") == "if":
            conditions = node_input.get("conditions") or []
            if (
                len(conditions) != 1
                or conditions[0].get("operand") != "equals_to"
                or conditions[0].get("rhs") != PRODUCTION_USER_NAME
            ):
                raise RuntimeError(f"recipe {RECIPE_ID} production gate changed: {node_input}")
        if step == FEATURES_UPSERT_STEP_AS:
            if node_input.get("table") != FEATURES_TABLE or node_input.get("key_columns") != "ID":
                raise RuntimeError(f"recipe {RECIPE_ID} features upsert target changed")
        if step == UPDATES_UPSERT_STEP_AS:
            if (
                node_input.get("table") != UPDATES_TABLE
                or node_input.get("key_columns") != "FEATURE_ID\nUPDATED_AT"
            ):
                raise RuntimeError(f"recipe {RECIPE_ID} feature-updates upsert target changed")
        if step == STATUS_QUERY_STEP_AS and "IFNULL(MIN(" not in str(node_input.get("sql") or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} status query lost its IFNULL fallback")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "topic_id": TOPIC_ID,
        "features_table": FEATURES_TABLE,
        "updates_table": UPDATES_TABLE,
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


def seed_126727654(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_126727654(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    job_context = data.get("job_context")
    if (
        not isinstance(job_context, dict)
        or sorted(job_context.keys()) != ["user_name"]
        or not isinstance(job_context.get("user_name"), str)
        or not job_context["user_name"].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must declare job_context "
            "{{'user_name': <str>}} (the step-5 production gate reads it)"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section")
    _require_snowflake_section(seed_in["snowflake_live"])
    production = job_context["user_name"] == PRODUCTION_USER_NAME
    _require_expect_shape(data.get("expect"), production)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "job_context": deepcopy(job_context),
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_126727654(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_126727654(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Required cleanup: both FEEDBACK.* tables are benchmark-owned live
        # objects shared with the twin recipe — create-or-replace seed +
        # registered drop on every path (and twin runs stay serialized).
        cleanup_response = ctx.tools.call("harness.snowflake_live.cleanup", {})
        details["cleanup_response"] = {"snowflake_live": cleanup_response}
    if not (cleanup_response or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_126727654(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["messages"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the messages list; "
            f"got {sorted(trigger.keys())}"
        )
    messages = trigger["messages"]
    if not isinstance(messages, list) or not 1 <= len(messages) <= BATCH_SIZE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger messages must be a list of 1..{BATCH_SIZE} "
            "(trigger batch_size 5)"
        )
    seen_revisions: set[tuple[Any, Any]] = set()
    for idx, message in enumerate(messages):
        if not isinstance(message, dict) or sorted(message.keys()) != ["case"]:
            raise RuntimeError(f"recipe {RECIPE_ID} message {idx} must be exactly {{'case': ...}}")
        case = message["case"]
        if not isinstance(case, dict) or tuple(sorted(case.keys())) != CASE_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} message {idx}.case must carry exactly the "
                f"{len(CASE_KEYS)} dereferenced fields"
            )
        for key in CASE_INT_KEYS:
            if isinstance(case[key], bool) or not isinstance(case[key], int):
                raise RuntimeError(f"recipe {RECIPE_ID} message {idx}.case.{key} must be an int")
        updated_by = case["updated_by_user_id"]
        if updated_by is not None and (isinstance(updated_by, bool) or not isinstance(updated_by, int)):
            raise RuntimeError(
                f"recipe {RECIPE_ID} message {idx}.case.updated_by_user_id must be an int "
                "or null (null exercises the IFNULL fallback)"
            )
        if not isinstance(case["is_private"], bool):
            raise RuntimeError(f"recipe {RECIPE_ID} message {idx}.case.is_private must be a boolean")
        for key in CASE_AT_KEYS:
            value = case[key]
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} message {idx}.case.{key} must be a non-empty ISO "
                    "datetime (the plain .in_time_zone chain raises on nil — that raise is "
                    "NOT a recipe branch)"
                )
            parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} message {idx}.case.{key} must carry an explicit "
                    f"offset: {value!r}"
                )
        for key in CASE_STRING_KEYS:
            if not isinstance(case[key], str):
                raise RuntimeError(f"recipe {RECIPE_ID} message {idx}.case.{key} must be a string")
        for key in CASE_ARRAY_KEYS:
            value = case[key]
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} message {idx}.case.{key} must be a list of strings"
                )
        for key in CASE_OBJECT_KEYS:
            if not isinstance(case[key], dict) or not case[key]:
                raise RuntimeError(f"recipe {RECIPE_ID} message {idx}.case.{key} must be an object")
            _require_sorted_keys(case[key], f"message {idx}.case.{key}")
        for key in CASE_OBJECT_LIST_KEYS:
            value = case[key]
            if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} message {idx}.case.{key} must be a list of objects"
                )
            _require_sorted_keys(value, f"message {idx}.case.{key}")
        revision = (case["id"], case["updated_at"])
        if revision in seen_revisions:
            raise RuntimeError(
                f"recipe {RECIPE_ID} message {idx} duplicates (id, updated_at) "
                f"{revision!r} — the MAX(updated_at) dedup would be nondeterministic"
            )
        seen_revisions.add(revision)


def _require_sorted_keys(value: Any, label: str) -> None:
    # The engine's .to_json renders objects with SORTED keys while Ruby keeps
    # insertion order — seeded objects must be authored alphabetized at every
    # level so both renders are byte-identical.
    if isinstance(value, dict):
        keys = list(value.keys())
        if keys != sorted(keys):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {label} keys must be authored in alphabetical order "
                f"(engine .to_json sorts; Ruby preserves insertion order): {keys}"
            )
        for key, item in value.items():
            _require_sorted_keys(item, f"{label}.{key}")
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            _require_sorted_keys(item, f"{label}[{idx}]")


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["current_time", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly "
            "{'current_time': ..., 'tables': ...}"
        )
    if not str(section["current_time"] or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live.current_time must be pinned")
    tables = section["tables"]
    expected = {FEATURES_TABLE: FEATURES_COLUMNS, UPDATES_TABLE: UPDATES_COLUMNS}
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(expected):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly {sorted(expected)} "
            "(the twin-shared FEEDBACK.* tables)"
        )
    for table, columns in expected.items():
        spec = tables[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(f"recipe {RECIPE_ID} table {table} spec must be {{'columns', 'rows'}}")
        if spec["columns"] != columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} must declare exactly the {len(columns)} "
                "written columns (VARCHAR datetimes/JSON text pin the rendered bytes; "
                "NUMBER ids)"
            )
        if not isinstance(spec["rows"], list):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table} rows must be a list (may be empty)")
        for idx, row in enumerate(spec["rows"]):
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} table {table} row {idx} must be an object")
            extra = sorted(set(row.keys()) - set(columns))
            if extra:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} uses undeclared columns: {extra}"
                )


def _require_expect_shape(expect: Any, production: bool) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("production_branch") is not production:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.production_branch must match the seeded "
            f"job_context user_name (production={production})"
        )
    if not isinstance(expect.get("dedup_query_rows"), list) or not expect["dedup_query_rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.dedup_query_rows must pin the step-4 rows "
            "(the dedup query runs on BOTH branches)"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a list")
    if production:
        counts = expect.get("upsert_counts")
        if (
            expect.get("executed_action_count") != 7
            or expect.get("tools") != ["snowflake.upsert_rows_batch", "snowflake.upsert_rows_batch"]
            or not isinstance(expect.get("status_query_rows"), list)
            or not isinstance(expect.get("final_query_rows"), list)
            or not isinstance(counts, dict)
            or sorted(counts.keys()) != ["feature_updates", "features"]
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} production expect must pin 7 actions, both upserts, "
                "both gated query row sets and upsert_counts"
            )
        for key in ("features", "feature_updates"):
            spec = counts[key]
            if (
                not isinstance(spec, dict)
                or sorted(spec.keys()) != ["created", "updated"]
                or not all(isinstance(spec[k], int) and spec[k] >= 0 for k in ("created", "updated"))
            ):
                raise RuntimeError(f"recipe {RECIPE_ID} upsert_counts.{key} must be {{'created','updated'}}")
        if len(items) != 2:
            raise RuntimeError(
                f"recipe {RECIPE_ID} production tool_expectations must pin exactly the two upserts"
            )
        features_args = (items[0].get("args_contains") or {}) if isinstance(items[0], dict) else {}
        updates_args = (items[1].get("args_contains") or {}) if isinstance(items[1], dict) else {}
        if (
            features_args.get("table") != FEATURES_TABLE
            or features_args.get("key_columns") != "ID"
            or not isinstance(features_args.get("rows"), list)
            or len(features_args["rows"]) != len(expect["dedup_query_rows"])
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[0] must pin the FEATURES_F upsert "
                "args (one row per dedup query row)"
            )
        if (
            updates_args.get("table") != UPDATES_TABLE
            or updates_args.get("key_columns") != "FEATURE_ID\nUPDATED_AT"
            or not isinstance(updates_args.get("rows"), list)
            or len(updates_args["rows"]) != len(expect["status_query_rows"])
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[1] must pin the FEATURE_UPDATES_F "
                "upsert args (one row per status query row)"
            )
    else:
        if (
            expect.get("executed_action_count") != 3
            or expect.get("tools") != []
            or items != []
            or expect.get("status_query_rows") is not None
            or expect.get("final_query_rows") is not None
            or expect.get("upsert_counts") is not None
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} non-production expect must pin 3 actions and NO live "
                "writes (steps 6-9 are gated off)"
            )
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object")
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unrecognized keys: {unknown}"
            )
        if item.get("tool") not in ALLOWED_TOOLS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be one of "
                f"{ALLOWED_TOOLS}; got {item.get('tool')!r}"
            )
        if not any(key in item for key in _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must carry at least one value "
                "key (corpus lint)"
            )
        if not isinstance(item.get("match_fields"), list) or not item["match_fields"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must declare match_fields "
                "(the generic verifier keys the final-state row checks on them)"
            )
    tables = expect.get("final_snowflake_tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([FEATURES_TABLE, UPDATES_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_snowflake_tables must pin BOTH live tables"
        )
    for table, spec in tables.items():
        if (
            not isinstance(spec, dict)
            or sorted(spec.keys()) != ["count", "match_fields", "rows"]
            or not isinstance(spec.get("rows"), list)
            or not isinstance(spec.get("match_fields"), list)
            or spec.get("count") != len(spec["rows"])
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} final_snowflake_tables[{table}] must be "
                "{'count','match_fields','rows'} covering the WHOLE table"
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
