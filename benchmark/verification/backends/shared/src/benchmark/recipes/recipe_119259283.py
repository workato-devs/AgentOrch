from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_119259283


RECIPE_ID = "119259283"
SEED_TYPE = "recipe_function_workato_product_key_variant"
TRACK = "workato_recipe_function_product_key_mapper"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "9410e4ed"
LOOKUP_TABLE_ID = "322627"
REQ_TABLE = "PUBLIC.WORKSPACE_REQ_LOG"
ADJ_TABLE = "PUBLIC.WORKSPACE_FEATURES_ADJ_LOG"
SNOWFLAKE_STEP_AS = "62d83e8f"
SNOWFLAKE_STEP_NUMBER = "9"
# Callable recipe function (trigger as 9410e4ed; parameters.workato_key +
# parameters.workspace_details{~80 feature/limit fields}). Whole body wrapped
# in TRY (step 2):
#   declare_variable Mapper (step 3, as 15d20217) = giant hash literal (with
#     inline '# Page N' comments) indexed by the interpolated workato_key pill
#   IF4 workato_key == 'ad_hoc_adapters' AND ad_hoc_adapters&.compact present:
#     parse_json (step 5, as dfca28a6) document = ad_hoc_adapters.compact
#     IF6 document.array.length > 0:
#       update Mapper = document.array.smart_join(", ") (step 7, as d7316f53)
#   IF8 workato_key == 'trial_end':
#     snowflake.search_rows_sql (step 9, as 62d83e8f) -- LIVE Snowflake over
#       PUBLIC.WORKSPACE_REQ_LOG LEFT JOIN PUBLIC.WORKSPACE_FEATURES_ADJ_LOG,
#       binds :workato_user_id/:datacenter_alpha2code, limit 1
#     IF10 rows.size > 1 -> STOP 11 with error  [PROVABLY DEAD: the action
#       pins limit='1', so the executor/live client always appends LIMIT 1 and
#       rows.size can never exceed 1; no variant exercises step 11]
#     IF12 rows.size == 1 -> update Mapper = rows[current_item]
#       .workspace_end_date.strftime("%Y-%m-%d") (step 13, as fc06c248)
#   lookup_table.search_entries 322627 '[WORK] Workato Products' by
#     col1=workato_key (step 14, as ce9db633) -- Workato-internal mock
#   return_result {workato_key: {current_value: "#{Mapper}", label: col3
#     .presence or nil, section: col2.presence or nil, type: "#{col4}"}}
#     (step 15, as 30c78cc9)
# CATCH (step 16, as 1f0c9ee0, max_retry_count=3, retry_interval=5) -> STOP 17
#   stop_with_error reason = catch message. The harness executes try/catch as
#   a single attempt (no retries) -- observably identical for the
#   deterministic forced-error variant.
# UNREACHABLE FALSE-CASE of IF6: IF4 already requires ad_hoc_adapters&.compact
#   present (a non-empty array) and the parse_json document is that same
#   .compact array, so document.array.length > 0 is always true inside IF4.
# The executor drops the search_rows_sql 'orderby' input ("WORKSPACE_END_DATE
#   DESC"); benign only while every variant seeds at most ONE matching
#   bind-param row -- variants must never seed 2 candidate rows.
# Snowflake runs LIVE (provisioned via harness.snowflake_live.seed_tables from
#   seed.snowflake_live and dropped by cleanup); the lookup table and the
#   recipe-function return are deterministic Workato-internal mocks.
PINNED_TRIGGER_INPUT = {   'parameters_schema_json': '[{"properties":[{"control_type":"text","label":"Datacenter '
                              'Alpha2Code","name":"datacenter_alpha2code","type":"string","optional":false},{"control_type":"text","label":"User '
                              'ID","type":"string","name":"user_id"},{"control_type":"text","label":"User '
                              'Name","type":"string","name":"user_name"},{"control_type":"email","label":"User '
                              'Email","type":"string","name":"user_email"},{"control_type":"text","label":"Workspace '
                              'ID","type":"string","name":"workspace_id"},{"control_type":"integer","label":"Account '
                              'ID","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"account_id"},{"control_type":"text","label":"Account '
                              'Name","type":"string","name":"account_name"},{"control_type":"date_time","label":"Created '
                              'At","render_input":"date_time_conversion","parse_output":"date_time_conversion","type":"date_time","name":"created_at"},{"control_type":"date_time","label":"Deleted '
                              'At","render_input":"date_time_conversion","parse_output":"date_time_conversion","type":"date_time","name":"deleted_at"},{"control_type":"text","label":"Activity '
                              'Logs","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Activity '
                              'Logs","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"activity_logs","type":"boolean","optional":false},"name":"activity_logs","type":"boolean","optional":false},{"control_type":"text","label":"Advanced '
                              'Recipe '
                              'Management","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Advanced Recipe '
                              'Management","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"advanced_recipe_management","type":"boolean","optional":false},"name":"advanced_recipe_management","type":"boolean","optional":false},{"control_type":"text","label":"Advanced '
                              'Security","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Advanced '
                              'Security","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"advanced_security","type":"boolean","optional":false},"name":"advanced_security","type":"boolean","optional":false},{"name":"ad_hoc_features","type":"array","of":"string","label":"Adhoc '
                              'Features"},{"name":"ad_hoc_adapters","type":"array","of":"string","label":"Adhoc '
                              'Adapters"},{"control_type":"text","label":"API '
                              'Key","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"API '
                              'Key","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"api_key","type":"boolean","optional":false},"name":"api_key","type":"boolean","optional":false},{"control_type":"text","label":"API '
                              'Platform","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"API '
                              'Platform","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"api_platform","type":"boolean","optional":false},"name":"api_platform","type":"boolean","optional":false},{"control_type":"text","label":"Audit '
                              'Log '
                              'Replication","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Audit Log '
                              'Replication","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"audit_log_replication","type":"boolean","optional":false},"name":"audit_log_replication","type":"boolean","optional":false},{"control_type":"text","label":"Configurable '
                              'Data '
                              'Retention","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Configurable '
                              'Data '
                              'Retention","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"configurable_data_retention","type":"boolean","optional":false},"name":"configurable_data_retention","type":"boolean","optional":false},{"control_type":"integer","label":"Data '
                              'Retention '
                              'Policy","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"data_retention_policy"},{"control_type":"text","label":"Data '
                              'Retention '
                              'Unit","type":"string","name":"data_retention_unit"},{"control_type":"text","label":"In '
                              'Trial","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"In '
                              'Trial","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","type":"boolean","name":"in_trial"},"type":"boolean","name":"in_trial"},{"control_type":"integer","label":"Action '
                              'Limit","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"action_limit"},{"control_type":"integer","label":"Billable '
                              'Flow '
                              'Limit","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"billable_flow_limit"},{"control_type":"text","label":"Connection '
                              'Folders","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Connection '
                              'Folders","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"connection_folders","type":"boolean","optional":false},"name":"connection_folders","type":"boolean","optional":false},{"control_type":"integer","label":"Custom '
                              'Action '
                              'Limit","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"custom_action_limit"},{"control_type":"text","label":"Custom '
                              'OAuth '
                              'Key","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Custom OAuth '
                              'Key","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"custom_oauth_key","type":"boolean","optional":false},"name":"custom_oauth_key","type":"boolean","optional":false},{"control_type":"text","label":"Custom '
                              'Roles","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Custom '
                              'Roles","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"custom_roles","type":"boolean","optional":false},"name":"custom_roles","type":"boolean","optional":false},{"control_type":"text","label":"Data '
                              'Warehousing","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"Data '
                              'Warehousing","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"data_warehousing","type":"boolean","optional":false},"name":"data_warehousing","type":"boolean","optional":false},{"control_type":"text","label":"Debug '
                              'Trace","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Debug '
                              'Trace","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"debug_trace","type":"boolean","optional":false},"name":"debug_trace","type":"boolean","optional":false},{"control_type":"text","label":"Enterprise '
                              'Key '
                              'Management","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Enterprise Key '
                              'Management","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"cmk_management","type":"boolean","optional":false},"name":"cmk_management","type":"boolean","optional":false},{"control_type":"text","label":"Enterprise '
                              'Workbot","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Enterprise '
                              'Workbot","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"enterprise_workbot","type":"boolean","optional":false},"name":"enterprise_workbot","type":"boolean","optional":false},{"control_type":"text","label":"Environment","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Environment","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"environment","type":"boolean","optional":false},"name":"environment","type":"boolean","optional":false},{"control_type":"text","label":"Extended '
                              'Data '
                              'Retention","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Extended Data '
                              'Retention","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"extended_data_retention","type":"boolean","optional":false},"name":"extended_data_retention","type":"boolean","optional":false},{"control_type":"text","label":"External '
                              'Secret '
                              'Sources","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"External Secret '
                              'Sources","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"external_secret_sources","type":"boolean","optional":false},"name":"external_secret_sources","type":"boolean","optional":false},{"control_type":"text","label":"Group '
                              'Recommendations","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Group '
                              'Recommendations","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"group_recommendations","type":"boolean","optional":false},"name":"group_recommendations","type":"boolean","optional":false},{"control_type":"integer","label":"OPA '
                              'Limit","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"opa_limit"},{"control_type":"integer","label":"Max '
                              'Shared '
                              'Account","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_shared_account"},{"control_type":"integer","label":"Max '
                              'Personalized '
                              'Connection","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_personalized_connection"},{"control_type":"integer","label":"Max '
                              'Workato '
                              'Template","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_workato_template"},{"control_type":"integer","label":"Max '
                              'Topic","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_topic"},{"control_type":"integer","label":"Max '
                              'Workato '
                              'Schema","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_workato_schema"},{"control_type":"integer","label":"Max '
                              'Team '
                              'Size","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_team_size"},{"control_type":"integer","label":"Max '
                              'Lookup '
                              'Table","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_lookup_table"},{"control_type":"integer","label":"Max '
                              'Custom '
                              'Connector","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_custom_connector"},{"control_type":"integer","label":"Max '
                              'On-Prem '
                              'Groups","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_onprem_groups"},{"control_type":"integer","label":"Max '
                              'Custom OAuth '
                              'Key","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_custom_oauth_key"},{"control_type":"integer","label":"Max '
                              'Flow","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_flow"},{"control_type":"integer","label":"Max '
                              'Account '
                              'Property","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"max_account_property"},{"control_type":"text","label":"Membership '
                              'ID","type":"string","name":"membership_id"},{"control_type":"date_time","label":"Membership '
                              'Started '
                              'At","render_input":"date_time_conversion","parse_output":"date_time_conversion","type":"date_time","name":"membership_started_at"},{"control_type":"text","label":"OEM '
                              'Share Custom '
                              'Adapters","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"OEM '
                              'Share Custom '
                              'Adapters","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"oem_share_custom_adapters","type":"boolean","optional":false},"name":"oem_share_custom_adapters","type":"boolean","optional":false},{"control_type":"text","label":"OEM '
                              'Vendor","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"OEM '
                              'Vendor","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"oem_vendor","type":"boolean","optional":false},"name":"oem_vendor","type":"boolean","optional":false},{"control_type":"text","label":"On-Prem '
                              'Agent","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"On-Prem '
                              'Agent","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"on_prem_agent","type":"boolean","optional":false},"name":"on_prem_agent","type":"boolean","optional":false},{"control_type":"text","label":"On-Prem '
                              'Groups & '
                              'Agents","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"On-Prem Groups & '
                              'Agents","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"opa","type":"boolean","optional":false},"name":"opa","type":"boolean","optional":false},{"control_type":"text","label":"Package","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Package","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"package","type":"boolean","optional":false},"name":"package","type":"boolean","optional":false},{"control_type":"text","label":"Personalization","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Personalization","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"personalization","type":"boolean","optional":false},"name":"personalization","type":"boolean","optional":false},{"name":"plan_addons","type":"array","of":"string","label":"Plan '
                              'Addons"},{"control_type":"integer","label":"Profile '
                              'ID","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"profile_id"},{"control_type":"text","label":"SAML","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"SAML","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"saml","type":"boolean","optional":false},"name":"saml","type":"boolean","optional":false},{"control_type":"date_time","label":"Scheduled '
                              'Deletion","render_input":"date_time_conversion","parse_output":"date_time_conversion","type":"date_time","name":"scheduled_deletion"},{"control_type":"text","label":"Service '
                              'Console","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Service '
                              'Console","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"service_console","type":"boolean","optional":false},"name":"service_console","type":"boolean","optional":false},{"control_type":"checkbox","label":"Task '
                              'Usage Alert: RecipeOps '
                              'Trigger","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"Task '
                              'Usage Alert: RecipeOps '
                              'Trigger","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"task_usage_recipe_ops_trigger_feature","type":"boolean","optional":false},"name":"task_usage_recipe_ops_trigger_feature","type":"boolean","optional":false},{"control_type":"checkbox","label":"Task '
                              'Usage Alert: '
                              'Banners","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"Task '
                              'Usage Alert: '
                              'Banners","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"task_usage_banners_feature","type":"boolean","optional":false},"name":"task_usage_banners_feature","type":"boolean","optional":false},{"control_type":"text","label":"Team","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Team","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"team","type":"boolean","optional":false},"name":"team","type":"boolean","optional":false},{"control_type":"text","label":"Topic","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Topic","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"topic","type":"boolean","optional":false},"name":"topic","type":"boolean","optional":false},{"control_type":"integer","label":"Trial '
                              'Duration","parse_output":"integer_conversion","render_input":"integer_conversion","type":"integer","name":"trial_duration"},{"control_type":"text","label":"Workato '
                              'Schema","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Workato '
                              'Schema","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"workato_schema","type":"boolean","optional":false},"name":"workato_schema","type":"boolean","optional":false},{"control_type":"text","label":"User '
                              'Resource","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"User '
                              'Resource","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"user_resource","type":"boolean","optional":false},"name":"user_resource","type":"boolean","optional":false},{"control_type":"text","label":"SCIM","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"SCIM","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"scim","type":"boolean","optional":false},"name":"scim","type":"boolean","optional":false},{"control_type":"text","label":"Workato '
                              'Logs","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Workato '
                              'Logs","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"logging_service","type":"boolean","optional":false},"name":"logging_service","type":"boolean","optional":false},{"control_type":"text","label":"Data '
                              'Tables","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"Data '
                              'Tables","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"workato_db_table","type":"boolean","optional":false},"name":"workato_db_table","type":"boolean","optional":false},{"control_type":"text","label":"Workato '
                              'Apps","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Workato '
                              'Apps","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"lcap","type":"boolean","optional":false},"name":"lcap","type":"boolean","optional":false},{"control_type":"checkbox","label":"Test '
                              'Automation","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"Test '
                              'Automation","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"test_automation","type":"boolean","optional":false},"name":"test_automation","type":"boolean","optional":false},{"control_type":"checkbox","label":"APIM '
                              'Log '
                              'Replication","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"APIM '
                              'Log '
                              'Replication","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"apim_log_replication","type":"boolean","optional":false},"name":"apim_log_replication","type":"boolean","optional":false},{"control_type":"checkbox","label":"Audit '
                              'Log Replication '
                              '(v2)","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Audit Log '
                              'Replication '
                              '(v2)","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"audit_log_replication_v2","type":"boolean","optional":false},"name":"audit_log_replication_v2","type":"boolean","optional":false},{"control_type":"checkbox","label":"RLCM '
                              'Repeatable Recipes '
                              'Start","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"RLCM '
                              'Repeatable Recipes '
                              'Start","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"repeatable_flow_start","type":"boolean","optional":false},"name":"repeatable_flow_start","type":"boolean","optional":false},{"control_type":"checkbox","label":"Realtime '
                              'Tasks Usage '
                              'Data","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Realtime Tasks '
                              'Usage '
                              'Data","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"realtime_usage","type":"boolean","optional":false},"name":"realtime_usage","type":"boolean","optional":false},{"control_type":"checkbox","label":"Require '
                              'Base URL for HTTP '
                              'Connections","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Require Base URL '
                              'for HTTP '
                              'Connections","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"require_base_url","type":"boolean","optional":false},"name":"require_base_url","type":"boolean","optional":false},{"control_type":"checkbox","label":"HTTP '
                              '- Send Request and Wait for '
                              'Response","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"HTTP '
                              '- Send Request and Wait for '
                              'Response","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"http_offload_proxy","type":"boolean","optional":false},"name":"http_offload_proxy","type":"boolean","optional":false},{"control_type":"checkbox","label":"Deployment","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Deployment","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"project_deployments","type":"boolean","optional":false},"name":"project_deployments","type":"boolean","optional":false},{"control_type":"checkbox","label":"Connection '
                              '- Command Line '
                              'Scripts","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Connection - '
                              'Command Line '
                              'Scripts","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"connection_opa_cmd_scripts","type":"boolean","optional":false},"name":"connection_opa_cmd_scripts","type":"boolean","optional":false},{"control_type":"checkbox","label":"Connection '
                              '- On-Prem '
                              'Files","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Connection - '
                              'On-Prem '
                              'Files","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"connection_opa_files","type":"boolean","optional":false},"name":"connection_opa_files","type":"boolean","optional":false},{"control_type":"checkbox","label":"Disable '
                              'Password '
                              'Authentication","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Disable Password '
                              'Authentication","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"disable_password_authentication","type":"boolean","optional":false},"name":"disable_password_authentication","type":"boolean","optional":false},{"control_type":"checkbox","label":"File '
                              'Storage","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"File '
                              'Storage","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"file_storage","type":"boolean","optional":false},"name":"file_storage","type":"boolean","optional":false},{"control_type":"checkbox","label":"Job '
                              'Resume","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"Job '
                              'Resume","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"job_resume","type":"boolean","optional":false},"name":"job_resume","type":"boolean","optional":false},{"control_type":"checkbox","label":"Remove '
                              'Access to this '
                              'Account","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Remove Access to '
                              'this '
                              'Account","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"disable_me","type":"boolean","optional":false},"name":"disable_me","type":"boolean","optional":false},{"control_type":"checkbox","label":"Apps '
                              'Insights","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"Apps '
                              'Insights","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"lcap_insights","type":"boolean","optional":false},"name":"lcap_insights","type":"boolean","optional":false},{"control_type":"checkbox","label":"Workspace '
                              'Usage '
                              'Insights","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Workspace Usage '
                              'Insights","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"usage_insights","type":"boolean","optional":false},"name":"usage_insights","type":"boolean","optional":false},{"control_type":"checkbox","label":"Remove '
                              'Access to Collaborator Personal '
                              'Accounts","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Remove Access to '
                              'Collaborator Personal '
                              'Accounts","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"team_security_disable_me","type":"boolean","optional":false},"name":"team_security_disable_me","type":"boolean","optional":false},{"control_type":"checkbox","label":"Use '
                              'New Grouping for Flows '
                              'Dashboard","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option list","toggle_field":{"label":"Use '
                              'New Grouping for Flows '
                              'Dashboard","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"use_new_flows_dashboard_stats_grouping","type":"boolean","optional":false},"name":"use_new_flows_dashboard_stats_grouping","type":"boolean","optional":false},{"control_type":"checkbox","label":"Enable '
                              'AI Utility '
                              'Connector","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Enable AI '
                              'Utility '
                              'Connector","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"ai_helper_connector","type":"boolean","optional":false},"name":"ai_helper_connector","type":"boolean","optional":false},{"control_type":"checkbox","label":"Connector '
                              'CoPilot","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Connector '
                              'CoPilot","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"ai_helper_sdk","type":"boolean","optional":false},"name":"ai_helper_sdk","type":"boolean","optional":false},{"control_type":"checkbox","label":"Recipe '
                              'CoPilot","render_input":{},"parse_output":{},"toggle_hint":"Select '
                              'from option '
                              'list","toggle_field":{"label":"Recipe '
                              'CoPilot","control_type":"text","toggle_hint":"Use '
                              'custom '
                              'value","name":"ai_helper_recipe","type":"boolean","optional":false},"name":"ai_helper_recipe","type":"boolean","optional":false}],"label":"Workspace '
                              'Details","name":"workspace_details","type":"object","optional":false},{"control_type":"text","label":"Workato '
                              'Key","name":"workato_key","type":"string","optional":false}]',
    'result_schema_json': '[{"label":"Workato '
                          'Key","name":"workato_key","type":"object","optional":false,"properties":[{"control_type":"text","label":"Section","name":"section","type":"string","optional":true},{"control_type":"text","label":"Label","name":"label","type":"string","optional":false},{"control_type":"text","label":"Current '
                          'Value","name":"current_value","type":"string","optional":false},{"control_type":"text","label":"Type","name":"type","type":"string","optional":false}]}]'}
EXPECTED_ACTIONS: list = [   ('workato_variable', 'declare_variable'),
    ('json_parser', 'parse_json'),
    ('workato_variable', 'update_variables'),
    ('snowflake', 'search_rows_sql'),
    ('workato_variable', 'update_variables'),
    ('lookup_table', 'search_entries'),
    ('workato_recipe_function', 'return_result')]
EXPECTED_ACTION_AS: list = [   '15d20217',
    'dfca28a6',
    'd7316f53',
    '62d83e8f',
    'fc06c248',
    'ce9db633',
    '30c78cc9']
PINNED_ACTION_INPUTS: list = [   {   'variables': {   'data': {   'mapper': '={\n'
                                               '  "membership_id" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","membership_id"]}\'), '
                                               '# Page 1\n'
                                               '  "oem_vendor" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","oem_vendor"]}\'), '
                                               '# Page 1\n'
                                               '  "in_trial" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","in_trial"]}\'), '
                                               '# Page 1\n'
                                               '  "trial_end" => nil, # Page '
                                               '1\n'
                                               '  "max_flow" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_flow"]}\'), '
                                               '# Page 2\n'
                                               '  "max_team_size" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_team_size"]}\'), '
                                               '# Page 2\n'
                                               '  "max_workato_template" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_workato_template"]}\'), '
                                               '# Page 2\n'
                                               '  "max_workato_schema" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_workato_schema"]}\'), '
                                               '# Page 2\n'
                                               '  "max_custom_connector" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_custom_connector"]}\'), '
                                               '# Page 2\n'
                                               '  "max_custom_oauth_key" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_custom_oauth_key"]}\'), '
                                               '# Page 2\n'
                                               '  "max_shared_account" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_shared_account"]}\'), '
                                               '# Page 2\n'
                                               '  "max_account_property" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_account_property"]}\'), '
                                               '# Page 2\n'
                                               '  "max_topic" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_topic"]}\'), '
                                               '# Page 2\n'
                                               '  "max_lookup_table" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_lookup_table"]}\'), '
                                               '# Page 2\n'
                                               '  "max_onprem_groups" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_onprem_groups"]}\'), '
                                               '# Page 2\n'
                                               '  "billable_flow_limit" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","billable_flow_limit"]}\'), '
                                               '# Page 3\n'
                                               '  "shared_account_limit" => '
                                               'nil, # Page 3\n'
                                               '  "opa_limit" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","opa_limit"]}\'), '
                                               '# Page 3\n'
                                               '  "action_limit" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","action_limit"]}\'), '
                                               '# Page 3\n'
                                               '  "custom_action_limit" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","custom_action_limit"]}\'), '
                                               '# Page 3\n'
                                               '  "api_key" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","api_key"]}\'), '
                                               '# Page 4\n'
                                               '  "service_console" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","service_console"]}\'), '
                                               '# Page 4\n'
                                               '  "activity_logs" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","activity_logs"]}\'), '
                                               '# Page 4\n'
                                               '  "audit_log_replication" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","audit_log_replication"]}\'), '
                                               '# Page 4\n'
                                               '  "workato_schema" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","workato_schema"]}\'), '
                                               '# Page 4\n'
                                               '  '
                                               '"configurable_data_retention" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","configurable_data_retention"]}\'), '
                                               '# Page 4\n'
                                               '  "custom_oauth_key" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","custom_oauth_key"]}\'), '
                                               '# Page 4\n'
                                               '  "custom_roles" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","custom_roles"]}\'), '
                                               '# Page 4\n'
                                               '  "extended_data_retention" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","extended_data_retention"]}\'), '
                                               '# Page 4\n'
                                               '  "group_recommendations" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","group_recommendations"]}\'), '
                                               '# Page 4\n'
                                               '  "debug_trace" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","debug_trace"]}\'), '
                                               '# Page 5\n'
                                               '  "opa" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","opa"]}\'), '
                                               '# Page 5\n'
                                               '  "topic" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","topic"]}\'), '
                                               '# Page 5\n'
                                               '  "package" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","package"]}\'), '
                                               '# Page 5\n'
                                               '  "user_resource" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","user_resource"]}\'), '
                                               '# Page 5\n'
                                               '  "personalization" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","personalization"]}\'), '
                                               '# Page 5\n'
                                               '  "saml" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","saml"]}\'), '
                                               '# Page 5\n'
                                               '  "oem_share_custom_adapters" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","oem_share_custom_adapters"]}\'), '
                                               '# Page 5\n'
                                               '  "team" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","team"]}\'), '
                                               '# Page 5\n'
                                               '  "connection_folders" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","connection_folders"]}\'), '
                                               '# Page 5\n'
                                               '  "advanced_recipe_management" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","advanced_recipe_management"]}\'), '
                                               '# Page 6\n'
                                               '  "advanced_security" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","advanced_security"]}\'), '
                                               '# Page 6\n'
                                               '  "api_platform" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","api_platform"]}\'), '
                                               '# Page 6\n'
                                               '  "data_warehousing" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","data_warehousing"]}\'), '
                                               '# Page 6\n'
                                               '  "enterprise_workbot" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","enterprise_workbot"]}\'), '
                                               '# Page 6\n'
                                               '  "on_prem_agent" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","on_prem_agent"]}\'), '
                                               '# Page 6\n'
                                               '  "environment" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","environment"]}\'),\n'
                                               '  "federation" => nil,\n'
                                               '  "premium_adapter" => nil,\n'
                                               '  "professional_adapter" => '
                                               'nil,\n'
                                               '  "business_adapter" => nil,\n'
                                               '  "enterprise_adapter" => '
                                               'nil,\n'
                                               '  "enterprise_plus_adapter" => '
                                               'nil,\n'
                                               '  "preview_adapter" => nil,\n'
                                               '  "transaction_credit" => '
                                               'nil,\n'
                                               '  "cmk_management" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","cmk_management"]}\'),\n'
                                               '  "external_secret_sources" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","external_secret_sources"]}\'),\n'
                                               '  "ad_hoc_adapters" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","ad_hoc_adapters"]}\')&.smart_join(", '
                                               '"),\n'
                                               '  "skip_restart_membership" => '
                                               'nil,\n'
                                               '  "data_retention_policy" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","data_retention_policy"]}\'),\n'
                                               '  "data_retention_unit" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","data_retention_unit"]}\'),\n'
                                               '  "consultant" => nil,\n'
                                               '  "max_worker_concurrency" => '
                                               'nil,\n'
                                               '  "extend_trial_duration" => '
                                               'nil,\n'
                                               '  '
                                               '"max_personalized_connection" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","max_personalized_connection"]}\'),\n'
                                               '  '
                                               '"task_usage_recipe_ops_trigger_feature" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","task_usage_recipe_ops_trigger_feature"]}\'),\n'
                                               '  "task_usage_banners_feature" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","task_usage_banners_feature"]}\'),\n'
                                               '  "scim" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","scim"]}\'), '
                                               '# Page 6\n'
                                               '  "logging_service" '
                                               '=>_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","logging_service"]}\'), '
                                               '# Page 6\n'
                                               '  "workato_db_table" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","workato_db_table"]}\'), '
                                               '# Page 6\n'
                                               '  "lcap" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","lcap"]}\'), '
                                               '# Page 6\n'
                                               '  "test_automation" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","test_automation"]}\'), '
                                               '# Page 6\n'
                                               '  "apim_log_replication" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","apim_log_replication"]}\'), '
                                               '# Page 6\n'
                                               '  "audit_log_replication_v2" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","audit_log_replication_v2"]}\'), '
                                               '# Page 6\n'
                                               '  "repeatable_flow_start" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","repeatable_flow_start"]}\'), '
                                               '# Page 6\n'
                                               '  "realtime_usage" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","realtime_usage"]}\'), '
                                               '# Page 7\n'
                                               '  "require_base_url" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","require_base_url"]}\'), '
                                               '# Page 7\n'
                                               '  "http_offload_proxy" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","http_offload_proxy"]}\'), '
                                               '# Page 7\n'
                                               '  "project_deployments" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","project_deployments"]}\'), '
                                               '# Page 7\n'
                                               '  "connection_opa_cmd_scripts" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","connection_opa_cmd_scripts"]}\'), '
                                               '# Page 7\n'
                                               '  "connection_opa_files" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","connection_opa_files"]}\'), '
                                               '# Page 7\n'
                                               '  '
                                               '"disable_password_authentication" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","disable_password_authentication"]}\'), '
                                               '# Page 7\n'
                                               '  "file_storage" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","file_storage"]}\'), '
                                               '# Page 7\n'
                                               '  "job_resume" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","job_resume"]}\'), '
                                               '# Page 7\n'
                                               '  "disable_me" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","disable_me"]}\'), '
                                               '# Page 7\n'
                                               '  "lcap_insights" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","lcap_insights"]}\'), '
                                               '# Page 8\n'
                                               '  "usage_insights" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","usage_insights"]}\'), '
                                               '# Page 8\n'
                                               '  "team_security_disable_me" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","team_security_disable_me"]}\'), '
                                               '# Page 8\n'
                                               '  '
                                               '"use_new_flows_dashboard_stats_grouping" '
                                               '=> '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","use_new_flows_dashboard_stats_grouping"]}\'), '
                                               '# Page 8\n'
                                               '  "ai_helper_connector" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","ai_helper_connector"]}\'), '
                                               '# Page 9\n'
                                               '  "ai_helper_sdk" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","ai_helper_sdk"]}\'), '
                                               '# Page 9\n'
                                               '  "ai_helper_recipe" => '
                                               '_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","ai_helper_recipe"]}\') '
                                               '# Page 9\n'
                                               '}["#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workato_key"]}\')}"]'},
                         'schema': '[{"control_type":"text","label":"Mapper","name":"mapper","type":"string","optional":true}]'}},
    {   'document': '=_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","ad_hoc_adapters"]}\').compact',
        'sample_document': '[\n  "js_eval",\n  "workato_api_platform"\n]'},
    {   'mapper': '=_dp(\'{"pill_type":"output","provider":"json_parser","line":"dfca28a6","path":["document","array"]}\').smart_join(", '
                  '")',
        'name': '59a08ab3-8c91-4345-ab50-5291fafacdca:15d20217:mapper'},
    {   'limit': '1',
        'orderby': 'WORKSPACE_END_DATE DESC',
        'output_schema': '[{"control_type":"text","label":"WORKATO USER '
                         'ID","name":"WORKATO_USER_ID","type":"string","optional":false},{"control_type":"text","label":"INITIAL '
                         'USERNAME","name":"INITIAL_USERNAME","type":"string","optional":false},{"control_type":"text","label":"SOURCE","name":"SOURCE","type":"string","optional":false},{"control_type":"date","label":"WORKSPACE '
                         'END '
                         'DATE","render_input":"date_conversion","parse_output":"date_conversion","name":"WORKSPACE_END_DATE","type":"date","optional":false}]',
        'parameters': {   'data': {   'datacenter_alpha2code': '#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters", '
                                                               '"workspace_details", '
                                                               '"datacenter_alpha2code"]}\')}',
                                      'workato_user_id': '#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters", '
                                                         '"workspace_details", '
                                                         '"user_id"]}\')}'},
                          'schema': '[{"control_type":"text","label":"Workato '
                                    'User '
                                    'ID","name":"workato_user_id","type":"string","optional":true},{"control_type":"text","label":"Datacenter '
                                    'Alpha2Code","name":"datacenter_alpha2code","type":"string","optional":true}]'},
        'sql': 'SELECT DISTINCT\n'
               'W.WORKATO_USER_ID,\n'
               'W.INITIAL_USERNAME,\n'
               'W.SOURCE,\n'
               'CASE\n'
               'WHEN W.SCHEDULED_NEXT_ACTION_DATE IS NULL\n'
               'THEN F.END_DATE::DATE\n'
               'ELSE W.SCHEDULED_NEXT_ACTION_DATE::DATE\n'
               'END AS WORKSPACE_END_DATE\n'
               '\n'
               'FROM PUBLIC.WORKSPACE_REQ_LOG W\n'
               'LEFT JOIN PUBLIC.WORKSPACE_FEATURES_ADJ_LOG F\n'
               'ON W.ID = F.REQUEST_ID\n'
               '\n'
               'WHERE W.WORKATO_USER_ID = :workato_user_id\n'
               'AND W.DATA_CENTER_ALPHA2CODE = :datacenter_alpha2code\n'
               "AND W.STATUS NOT IN ('Completed', 'Rejected')\n"
               'AND \n'
               '(\n'
               "    (W.REQUEST_TYPE = 'Trial' AND W.NEXT_ACTION IN "
               "('Downgrade', 'Deactivate') AND W.STATUS = 'Pending Next "
               "Action')\n"
               "    OR (F.STATUS IN ('Adjusted','Applied'))\n"
               ')'},
    {   'mapper': '=_dp(\'{"pill_type":"output","provider":"snowflake","line":"62d83e8f","path":["rows",{"path_element_type":"current_item"},"workspace_end_date"]}\').strftime("%Y-%m-%d")',
        'name': '59a08ab3-8c91-4345-ab50-5291fafacdca:15d20217:mapper'},
    {   'lookup_table_id': '322627',
        'parameters': {   'col1': '#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters", '
                                  '"workato_key"]}\')}'}},
    {   'result': {   'workato_key': {   'current_value': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"15d20217","path":["mapper"]}\')}',
                                         'label': '=_dp(\'{"pill_type":"output","provider":"lookup_table","line":"ce9db633","path":["entries",{"path_element_type":"current_item"},"entry","col3"]}\').presence '
                                                  'or nil',
                                         'section': '=_dp(\'{"pill_type":"output","provider":"lookup_table","line":"ce9db633","path":["entries",{"path_element_type":"current_item"},"entry","col2"]}\').presence '
                                                    'or nil',
                                         'type': '#{_dp(\'{"pill_type":"output","provider":"lookup_table","line":"ce9db633","path":["entries", '
                                                 '{"path_element_type": '
                                                 '"current_item"}, "entry", '
                                                 '"col4"]}\')}'}}}]
EXPECTED_CONTROL_FLOW: list = [   {'input': {}, 'keyword': 'try', 'number': 2},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters", '
                                                  '"workato_key"]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': 'ad_hoc_adapters'},
                                       {   'lhs': '=_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters","workspace_details","ad_hoc_adapters"]}\')&.compact',
                                           'operand': 'present',
                                           'rhs': ''}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 4},
    {   'input': {   'conditions': [   {   'lhs': '=_dp(\'{"pill_type":"output","provider":"json_parser","line":"dfca28a6","path":["document","array"]}\').length',
                                           'operand': 'greater_than',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 6},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"9410e4ed","path":["parameters", '
                                                  '"workato_key"]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': 'trial_end'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 8},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"snowflake","line":"62d83e8f","path":["rows", '
                                                  '{"path_element_type": '
                                                  '"size"}]}\')}',
                                           'operand': 'greater_than',
                                           'rhs': '1'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 10},
    {   'input': {   'stop_reason': 'Unable to identify unique Wworkato User '
                                    'request entry',
                     'stop_with_error': 'true'},
        'keyword': 'stop',
        'number': 11},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"snowflake","line":"62d83e8f","path":["rows", '
                                                  '{"path_element_type": '
                                                  '"size"}]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': '1'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 12},
    {   'input': {'max_retry_count': '3', 'retry_interval': '5'},
        'keyword': 'catch',
        'number': 16},
    {   'input': {   'stop_reason': '#{_dp(\'{"pill_type":"output","provider":"catch","line":"1f0c9ee0","path":["message"]}\')}',
                     'stop_with_error': 'true'},
        'keyword': 'stop',
        'number': 17}]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.parse_json",
    "workato_runtime.update_variables",
    "snowflake.search_rows_sql",
    "lookup_table.search_entries",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "lookup_table.search_entries",
    "workato_recipe_function.return_result",
]
CONTROL_KEYWORDS = {"if", "elsif", "else", "try", "repeat", "while_condition", "catch", "foreach", "stop"}


def validate_119259283(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    if raw.get("input") != PINNED_TRIGGER_INPUT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter/result schema drifted")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    actual_as = [action.get("as") for action in actions]
    if actual_as != EXPECTED_ACTION_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} action step ids changed: {actual_as}")
    for idx, action in enumerate(actions):
        if action.get("input") != PINNED_ACTION_INPUTS[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} raw formula drift at action index {idx} "
                f"(step {action.get('number')}, as {action.get('as')!r})"
            )
    control = _collect_control(raw)
    actual_control = [
        {"keyword": node.get("keyword"), "number": node.get("number"), "input": node.get("input")}
        for node in control
    ]
    if actual_control != EXPECTED_CONTROL_FLOW:
        raise RuntimeError(f"recipe {RECIPE_ID} control flow drifted: {actual_control}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": action.get("number"),
                "provider": action.get("provider"),
                "name": action.get("name"),
                "as": action.get("as"),
            }
            for action in actions
        ],
    }


def seed_119259283(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_119259283(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    workato_key = parameters.get("workato_key")
    if not isinstance(workato_key, str) or not workato_key.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a non-empty parameters.workato_key")
    if not isinstance(parameters.get("workspace_details"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters.workspace_details object")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    lookup_section = seed_in.get("lookup_table")
    if not isinstance(lookup_section, dict) or not isinstance(lookup_section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.lookup_table.tables")
    if not isinstance(lookup_section["tables"].get(LOOKUP_TABLE_ID), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must explicitly declare lookup table {LOOKUP_TABLE_ID} "
            "(an empty row list is a valid declaration)"
        )
    if not isinstance(data.get("expect"), dict) or not data["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect block")
    force = data.get("force_action_error") if isinstance(data.get("force_action_error"), dict) else {}
    snowflake_required = workato_key == "trial_end" and not _force_targets_snowflake(force)
    provision: dict[str, Any] | None = None
    if snowflake_required or isinstance(seed_in.get("snowflake_live"), dict):
        _require_snowflake_tables(RECIPE_ID, seed_in.get("snowflake_live"), [REQ_TABLE, ADJ_TABLE])
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
        "harness_tool_calls": ctx.tools.call_log(),
        "expect": deepcopy(data["expect"]),
    }
    if provision is not None:
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    for key, value in seed_in.items():
        if key == "snowflake_live":
            continue
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_119259283(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_119259283(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
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
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_119259283(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _force_targets_snowflake(force: dict[str, Any]) -> bool:
    if not force:
        return False
    if str(force.get("step_as") or "") == SNOWFLAKE_STEP_AS:
        return True
    return str(force.get("step_number") or "") == SNOWFLAKE_STEP_NUMBER


def _require_snowflake_tables(recipe_id: str, snowflake_seed: Any, tables: list[str]) -> None:
    if not isinstance(snowflake_seed, dict) or not isinstance(snowflake_seed.get("tables"), dict):
        raise RuntimeError(f"recipe {recipe_id} requires seed.snowflake_live.tables")
    for table in tables:
        spec = snowflake_seed["tables"].get(table)
        if not isinstance(spec, dict):
            raise RuntimeError(
                f"recipe {recipe_id} seed must define snowflake_live.tables[{table!r}] explicitly"
            )
        columns = spec.get("columns")
        if not isinstance(columns, dict) or not columns or not all(
            isinstance(kind, str) and kind.strip() for kind in columns.values()
        ):
            raise RuntimeError(
                f"recipe {recipe_id} snowflake_live table {table} must declare explicit column types"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(
                f"recipe {recipe_id} snowflake_live table {table} must declare rows (may be empty)"
            )
        lower_columns = {str(name).strip().lower() for name in columns}
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {recipe_id} snowflake_live table {table} rows must be objects")
            extra = {str(key).strip().lower() for key in row} - lower_columns
            if extra:
                raise RuntimeError(
                    f"recipe {recipe_id} snowflake_live table {table} row uses undeclared columns: {sorted(extra)}"
                )


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _collect_control(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") in CONTROL_KEYWORDS:
            found.append(child)
        found.extend(_collect_control(child))
    return found


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
