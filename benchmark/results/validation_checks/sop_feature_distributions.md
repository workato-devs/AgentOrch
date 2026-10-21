# SOP structural feature distributions

recipes: 650   variants: 3220

| feature | min | p25 | median | p75 | max | mean |
|---|---:|---:|---:|---:|---:|---:|
| num_tool_calls | 0 | 2 | 3 | 6 | 43 | 4.56 |
| num_business_tool_calls | 0 | 2 | 3 | 4 | 36 | 3.51 |
| num_total_workflow_nodes | 2 | 3 | 5 | 9 | 90 | 7.44 |
| num_control_flow_nodes | 0 | 0 | 1 | 3 | 38 | 2.14 |
| num_conditionals | 0 | 0 | 1 | 2 | 27 | 1.39 |
| num_loops | 0 | 0 | 0 | 0 | 8 | 0.29 |
| num_try_catch_blocks | 0 | 0 | 0 | 1 | 10 | 0.46 |
| max_nesting_depth | 1 | 1 | 2 | 3 | 9 | 2.26 |
| num_dependency_edges | 0 | 2 | 3 | 6 | 67 | 5.17 |
| num_distinct_apps | 0 | 1 | 2 | 2 | 4 | 1.72 |
| num_distinct_services | 0 | 1 | 2 | 2 | 3 | 1.65 |
| num_distinct_tools | 0 | 2 | 2 | 4 | 8 | 2.92 |

## num_tool_calls (call nodes in the plan) histogram
0:1, 1:31, 2:202, 3:101, 4:76, 5:74, 6:39, 7:42, 8:18, 9:26, 10:8, 11:3, 12:6, 13:4, 14:3, 15:4, 16:2, 17:1, 18:1, 20:1, 24:2, 29:1, 30:1, 31:1, 36:1, 43:1

## number of apps (tool-family identity, runtime helpers excluded)
- 0 app(s): 5 SOPs
- 1 app(s): 230 SOPs
- 2 app(s): 360 SOPs
- 3 app(s): 50 SOPs
- 4 app(s): 5 SOPs

## number of services (coarse: all Workato families = one service)
- 0 service(s): 1 SOPs
- 1 service(s): 274 SOPs
- 2 service(s): 328 SOPs
- 3 service(s): 47 SOPs

## app frequency (SOPs using the app)
- workato_db_table: 197
- salesforce: 173
- snowflake: 154
- workato_api_platform: 139
- lookup_table: 114
- slack: 97
- slack_bot: 86
- google_sheets: 49
- workato_service: 49
- workato_smart_list: 45
- workato_pub_sub: 9
- workato_app: 6
- google_drive: 1
- jira: 1

## control flow
- has_conditional: 347 / 650 SOPs
- has_loop: 139 / 650 SOPs
- has_try_catch: 237 / 650 SOPs
- category branch_only: 132 SOPs
- category error_handling_only: 78 SOPs
- category linear: 186 SOPs
- category loop_only: 36 SOPs
- category multiple_control_flow_types: 218 SOPs

## fault injection: 264 / 3220 variants (8.2%), in 224 SOPs
