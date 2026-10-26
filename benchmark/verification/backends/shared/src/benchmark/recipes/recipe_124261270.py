from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_124261270


RECIPE_ID = "124261270"
SEED_TYPE = "usage_email_alert_top10recipes_v2_insert_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "f9c4c34b"
SQL_STEP_AS = "fcbdd078"
SUCCESS_POST_AS = "2ed0fd60"
CATCH_AS = "6acde0a3"
CATCH_POST_AS = "60a29776"
SLACK_LITERAL_CHANNEL = "C05LVU4NVN0"
SUCCESS_TEXT = "Top 10 recipes data V2 has been successfully ingested"
FAILURE_TEXT = "Top 10 recipes V2 ingestion has failed"
TARGET_TABLE = "PRODUCT.ITERABLE.USAGE_EMAIL_ALERT_TOP10RECIPES_V2"
SQL_PREFIX = "insert into PRODUCT.ITERABLE.USAGE_EMAIL_ALERT_TOP10RECIPES_V2\n"
SQL_FINAL_TAIL = "\nfrom top_10_recipes_monthly_v2\n;"
TARGET_COLUMNS = {
    "ingestion_date": "date",
    "reporting_month": "date",
    "rn": "number",
    "account_id": "string",
    "account_name": "string",
    "contract_id": "string",
    "contract_startdate": "date",
    "contract_enddate": "date",
    "consumption_startdate": "date",
    "consumption_enddate": "date",
    "dt_month": "date",
    "user_id": "string",
    "user_name": "string",
    "data_center": "string",
    "unique_env_workspace": "string",
    "environment_type": "string",
    "flow_id": "number",
    "flow_monthly_task_count": "number",
    "flow_cumulative_task_count": "number",
    "flow_name": "string",
    "flow_deleted": "boolean",
}
SOURCE_COLUMNS: dict[str, dict[str, str]] = {
    "workato_business_systems.salesforce.account": {
        "id": "string",
        "name": "string",
        "ownerid": "string",
        "expansion_csm__c": "string",
        "active_subscription__c": "boolean",
    },
    "workato_business_systems.salesforce.user": {
        "id": "string",
        "name": "string",
        "email": "string",
    },
    "workato_business_systems.salesforce.cpq_contract": {
        "id": "string",
        "accountid": "string",
        "term": "number",
        "startdate": "date",
        "enddate": "date",
        "sbcf_recipelimit__c": "number",
        "sbcf_tasklimit__c": "number",
        "renewal_date__c": "date",
        "sbqqsc__renewalquoted__c": "boolean",
        "sbqqsc__opportunity__c": "string",
        "isdeleted": "boolean",
        "non_standard_contract__c": "boolean",
        "sbcf_cpqcontractstatus__c": "string",
        "status": "string",
    },
    "workato_business_systems.salesforce.opportunity": {
        "id": "string",
        "type": "string",
    },
    "workato_business_systems.salesforce.workato_user": {
        "user_id__c": "string",
        "data_center__c": "string",
        "account__c": "string",
    },
    "workato_business_systems.salesforce_snapshot.cpq_contract": {
        "id": "string",
        "accountid": "string",
        "entry_date": "date",
        "sbqqsc__opportunity__c": "string",
        "isdeleted": "boolean",
        "sbcf_cpqcontractstatus__c": "string",
        "status": "string",
    },
    "workato_business_systems.salesforce_snapshot.opportunity": {
        "id": "string",
        "entry_date": "date",
        "type": "string",
    },
    "workato_usage.profiles": {
        "data_center": "string",
        "user_id": "string",
        "membership_id": "string",
        "in_trial": "boolean",
    },
    "workato_usage.users": {
        "id": "string",
        "data_center": "string",
        "name": "string",
        "environment_type": "string",
        "workspace_id": "number",
        "deleted_at": "timestamp",
        "federated_account_id": "string",
    },
    "workato_usage.notification_settings": {
        "data_center": "string",
        "user_id": "string",
        "admin_notification_emails": "string",
    },
    "workato_usage.user_daily_stats": {
        "user_id": "string",
        "data_center": "string",
        "time": "date",
        "billable_flow_count": "number",
        "last_billable_flow_count": "number",
    },
    "product.workato_usage.consumption_usage_fact": {
        "data_center": "string",
        "entry_date": "date",
        "user_id": "number",
        "flow_id": "number",
        "task_count": "number",
    },
    "public.cal_month_dim": {
        "my_date": "date",
    },
    "workato_usage_intermediate.flows_persistent": {
        "user_id": "string",
        "id": "number",
        "data_center": "string",
        "name": "string",
        "deleted_at": "timestamp",
    },
}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "f9c4c34b", "skip": false, "input": {"cron_expression": "10 12 2 * *", "time_unit": "custom_schedule"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "fcbdd078", "skip": false, "input": {"sql": "insert into PRODUCT.ITERABLE.USAGE_EMAIL_ALERT_TOP10RECIPES_V2\nwith direct_paying_customers as (\n    select \n        a.id as account_id\n        , a.name as account_name\n        , a.ownerid as account_owner_id\n        , c.name as account_owner_name\n        , c.email as account_owner_email\n        , a.expansion_csm__c as csm_id\n        , b.name as csm_name\n        , b.email as csm_email\n    from workato_business_systems.salesforce.account a\n    left join workato_business_systems.salesforce.user b\n        on a.expansion_csm__c = b.id\n    left join workato_business_systems.salesforce.user c\n        on a.ownerid = c.id\n    where 1=1\n        and a.name not ilike '%embedded%'      -- direct customers\n        and a.active_subscription__c = true    -- paying customers        \n)\n\n\n, cpq_contracts as (\n    select \n        a.id as contract_id\n       , a.accountid as account_id\n       , a.term\n       , a.startdate as contract_startdate\n       , a.enddate as contract_enddate\n       , a.sbcf_recipelimit__c as contract_recipe_limit\n       , a.sbcf_tasklimit__c as contract_task_limit\n       , case\n           when (date_part(month, a.renewal_date__c) = 2) AND (date_part(day, a.renewal_date__c) = 29) then a.renewal_date__c + 1\n           else a.renewal_date__c\n        end as renewal_date_adj\n       , greatest(a.startdate, dateadd(year, floor(least(-1, months_between(current_date, renewal_date_adj)) / 12), renewal_date_adj)) AS consumption_startdate -- jeff approved\n       , dateadd(year, ceil(least(0, months_between(current_date, enddate)) / 12), enddate) AS consumption_enddate -- jeff approved\n       , a.sbqqsc__renewalquoted__c as in_renewal\n       , iff(a.term%12 = 0, true, false) is_12months\n       , case \n            when contract_recipe_limit = 999999 then 'TBP'\n            when contract_recipe_limit in (0, 999999999999, 999999999) and contract_task_limit not in (0, 999999999999, 999999999) then 'TBP'     \n            when contract_recipe_limit not in (0, 999999999999, 999999999) and contract_task_limit not in (0, 999999999999, 999999999) then 'RBP_w_task_limit'\n            when contract_recipe_limit not in (0, 999999999999, 999999999) and contract_task_limit in (0, 999999999999, 999999999) then 'RBP_no_task_limit'\n            else 'unlimited'\n        end as plan_cat    \n    from workato_business_systems.salesforce.cpq_contract a\n    join workato_business_systems.salesforce.opportunity b\n        on a.sbqqsc__opportunity__c = b.id\n    where 1=1\n        and ifnull(b.type, '') != 'Professional Services'                 -- exclude PS contracts which counts towards multiple CPQ contracts\n        and ifnull(a.isdeleted, false) = false                            -- exclude deleted cpq contracts  \n        and ifnull(a.non_standard_contract__c, false) = false             -- standard - customers with different limits per workspace for direct\n        and coalesce(a.sbcf_cpqcontractstatus__c, a.status) = 'Active'    -- active cpq contract\n    qualify count(distinct a.id) over (partition by a.accountid) = 1      -- only accounts with one active cpq contract\n)\n\n, direct_customers_contracts as (\n    select \n        a.*\n        , b.contract_id\n        , b.term\n        , b.contract_startdate\n        , b.contract_enddate\n        , b.contract_recipe_limit\n        , b.contract_task_limit\n        , b.consumption_startdate\n        , b.consumption_enddate\n        , b.in_renewal\n        , b.is_12months\n        , b.plan_cat\n    from direct_paying_customers a\n    join cpq_contracts b\n        on a.account_id = b.account_id\n)\n\n, workato_profiles_all_dc as (\n    select *\n    from workato_usage.profiles\n)\n\n, workato_users_all_dc as (\n    select *\n    from workato_usage.users\n)\n\n, workato_notification_settings as (\n    select \n        data_center\n        , user_id\n        , iff(admin_notification_emails = '', null, admin_notification_emails) admin_notification_emails\n    from workato_usage.notification_settings\n)\n\n, profiles_users_all_dc_filtered as (\n    select \n        a.data_center\n        , a.user_id\n        , a.membership_id\n        , b.name as user_name\n        , b.environment_type\n        , b.workspace_id\n        , b.deleted_at\n        , iff(b.federated_account_id is not null, true, false) is_ahq_workspace\n    from workato_profiles_all_dc a\n    join workato_users_all_dc b\n        on a.user_id = b.id\n        and a.data_center = b.data_center\n    where 1=1\n        and ifnull(a.in_trial, false) = false                                         -- exclude users who are in trial\n        and a.membership_id in ('tbp_yearly_workspace', 'rbp_workspace_yearly')       -- only users who have either membership_ids\n)\n\n, environment_workspaces_all_dc as (\n    select data_center, workspace_id\n    from workato_users_all_dc\n    where environment_type != 'dev'\n    group by 1,2\n)\n\n, profiles_users_all_dc_filtered_env_1 as (\n    select \n        a.data_center\n        , a.user_id\n        , a.user_name\n        , a.membership_id\n        , a.is_ahq_workspace\n        , a.workspace_id::varchar as unique_workspace\n        , b.workspace_id::varchar as unique_env_workspace -- essentially a flag to indicate if user has environments\n        , a.environment_type\n        , a.deleted_at\n    from profiles_users_all_dc_filtered a\n    left join environment_workspaces_all_dc b\n        on a.data_center = b.data_center\n        and a.workspace_id = b.workspace_id\n)\n\n/* Rename environment workspaces  \n test/ prod should use dev's name\n*/\n, profiles_users_all_dc_filtered_env_2 as (\n    select \n        *\n        , iff(unique_env_workspace is not null, true, false) is_environment\n        , case \n            when is_environment = false then user_name\n            when is_environment = true and environment_type = 'dev' then user_name\n            when is_environment = true and environment_type != 'dev' then first_value(user_name) over (partition by unique_workspace, data_center order by environment_type)\n        end user_name_adj // environments name should follow the primary user nameworkspaces\n    from profiles_users_all_dc_filtered_env_1\n    where 1=1\n    order by unique_env_workspace, environment_type\n)\n\n, profiles_users_all_dc_filtered_env as (\n    select \n        a.data_center\n        , a.user_id\n        , a.user_name_adj\n        , a.membership_id\n        , a.is_ahq_workspace\n        , a.unique_workspace\n        , a.unique_env_workspace\n        , a.environment_type\n        , a.deleted_at\n        , b.admin_notification_emails\n    from profiles_users_all_dc_filtered_env_2 a\n    left join workato_notification_settings b\n        on a.user_id = b.user_id\n        and a.data_center = b.data_center\n)\n\n/* Definition of CTE\n    users of direct paying customers who have either tbp_yearly_workspace or rbp_workspace_yearly\n    contains contract limits/ startdate/ enddate/ consumption start and end date\n    other data fields like csm emails tagged to an account \n*/\n, direct_customers_contracts_users as (\n    select \n        c.*\n        , a.*\n        , case \n            when a.deleted_at is null then true\n            when a.deleted_at > c.consumption_startdate and a.deleted_at < c.consumption_enddate then true\n            else false\n        end exists_in_current_period\n    from profiles_users_all_dc_filtered_env a\n    join workato_business_systems.salesforce.workato_user b\n        on a.user_id = b.user_id__c\n        and a.data_center = nvl(b.data_center__c, 'US')\n    join direct_customers_contracts c\n        on b.account__c = c.account_id\n)\n\n, ahq_identifier as (\n    select account_id, ahq_customer as ahq_customer\n    from (\n        select *, iff(sum(is_ahq_workspace::integer) over (partition by account_id) > 0, true, false) ahq_customer\n        from direct_customers_contracts_users\n        where deleted_at is null -- we determine whether or not a customer is AHQ based on non-deleted workspaces \n    )\n    group by 1,2\n)\n\n, admin_notification_emails_identifier_0 as (\n    select \n        account_id\n        , account_name\n        , user_id\n        , admin_notification_emails\n        , iff(trim(temp.value) = '', null, trim(temp.value)) as admin_notification_email -- WebSumit had an email that was something like this a, , b  (leading whitespace and no value email) \n    from direct_customers_contracts_users, lateral split_to_table(admin_notification_emails, ',') as temp\n)\n\n// New - <anon>01 Jan 2024</anon>\n, admin_notification_emails_identifier as (\n    select \n        account_id\n        , array_agg(distinct admin_notification_email) list_admin_notification_emails\n    from admin_notification_emails_identifier_0\n    group by 1\n)\n\n, direct_customers_contracts_details as (\n    select a.*, b.ahq_customer, c.list_admin_notification_emails\n    from direct_customers_contracts a\n    left join ahq_identifier b\n        on a.account_id = b.account_id\n    left join admin_notification_emails_identifier c\n        on a.account_id = c.account_id\n)\n\n\n\n, user_daily_task_consumption as (\n    select \n        data_center\n        , entry_date as dt\n        , user_id\n        , sum(task_count) as user_daily_tasks\n    from product.workato_usage.consumption_usage_fact\n    group by all\n)\n\n, account_daily_tasks_current_consumption as (\n    select \n        b.account_id\n        , a.dt\n        , date_trunc('month', a.dt) as dt_month\n        , sum(a.user_daily_tasks) as account_daily_tasks\n    from user_daily_task_consumption a\n    join direct_customers_contracts_users b\n        on a.data_center = b.data_center\n        and a.user_id = b.user_id\n        and a.dt >= b.consumption_startdate\n        and a.dt <= b.consumption_enddate\n        and b.exists_in_current_period = true // filter to include tasks from deleted users as well\n    group by 1,2,3\n)\n\n, account_monthly_tasks_current_consumption as (\n    select \n        a.account_id\n        , a.dt_month\n        , sum(a.account_daily_tasks) as account_monthly_tasks\n        , sum(account_monthly_tasks) over (partition by a.account_id order by a.dt_month) as account_cumulative_tasks // cumlative tasks of current consumption period\n    from account_daily_tasks_current_consumption a\n    group by 1,2\n    order by a.account_id, a.dt_month  \n)\n\n// NEW\n, account_daily_tasks_all_consumption as (\n    select \n        a.account_id\n        , b.dt\n        , date_trunc('month', b.dt) as dt_month\n        , sum(b.user_daily_tasks) as account_daily_tasks\n    from direct_customers_contracts_users a\n    join user_daily_task_consumption b\n        on a.data_center = b.data_center\n        and a.user_id = b.user_id\n    \n    group by 1,2,3\n)\n\n// NEW\n, account_monthly_tasks_all_consumption as (\n    select\n        account_id\n        , dt_month\n        , sum(account_daily_tasks) as account_monthly_tasks\n        , lag(account_monthly_tasks, 1) over (partition by account_id order by dt_month) as prev_account_monthly_tasks\n        , lag(account_monthly_tasks, 2) over (partition by account_id order by dt_month) as prev_prev_account_monthly_tasks\n    from account_daily_tasks_all_consumption\n    group by 1,2\n)\n\n-- direct_customers_contracts_users monthly view\n, t1 as (\n    select \n        a.*\n        , date_trunc('month', b.my_date) as dt_month\n    from direct_customers_contracts_details a\n    join public.cal_month_dim b\n        on b.my_date >= a.consumption_startdate\n        and b.my_date <= current_date\n    where 1=1\n        and dt_month != date_trunc('month', current_date) -- exclude the month of query\n    group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22\n    order by account_id, dt_month\n)\n\n, t2 as (\n    select \n        a.*\n        -- , b.account_monthly_tasks\n        -- , lag(b.account_monthly_tasks) over (partition by a.account_id order by a.dt_month) as prev_account_monthly_tasks\n        -- , lag(b.account_monthly_tasks, 2) over (partition by a.account_id order by a.dt_month) as prev_prev_account_monthly_tasks\n        , c.account_monthly_tasks\n        , c.prev_account_monthly_tasks\n        , c.prev_prev_account_monthly_tasks\n        , b.account_cumulative_tasks\n    from t1 a\n    left join account_monthly_tasks_current_consumption b\n        on a.account_id = b.account_id\n        and a.dt_month = b.dt_month\n    left join account_monthly_tasks_all_consumption c -- NEW\n        on a.account_id = c.account_id\n        and a.dt_month = c.dt_month\n    order by a.account_id, a.dt_month\n)\n\n-- select * from t2;\n\n, user_daily_stats_all_dc as (\n    select *\n    from workato_usage.user_daily_stats\n)\n\n, user_daily_stats_all_dc_filtered as (\n    select b.account_id, a.*\n    from user_daily_stats_all_dc a\n    join direct_customers_contracts_users b\n        on a.user_id = b.user_id\n        and a.data_center = b.data_center\n)\n\n, user_billable_recipes_scd as (\n    select \n        row_number() over (partition by a.user_id, a.data_center order by a.time desc) rn\n        , a.account_id\n        , a.user_id\n        , a.data_center\n        , a.time as startdate\n        , iff(rn=1, current_date, dateadd(day, -1, lag(time) over (partition by a.user_id, a.data_center order by a.time desc))) as enddate\n        , a.billable_flow_count\n        , a.last_billable_flow_count\n    from user_daily_stats_all_dc_filtered a\n)\n\n, user_billable_recipe_count_snapshot as (\n    select \n        a.account_id\n        , a.user_id\n        , b.my_date\n        , iff(a.startdate = b.my_date, a.billable_flow_count, a.last_billable_flow_count) as user_daily_billable_flow_count\n    from user_billable_recipes_scd a\n    join public.cal_month_dim b\n        on b.my_date >= a.startdate\n        and b.my_date <= a.enddate\n)\n\n, account_last_day_of_month_billable_count as (\n    select \n        account_id\n        , date_trunc('month', my_date) as dt_month\n        , sum(user_daily_billable_flow_count) as account_last_day_billable_flow_count\n        , lag(account_last_day_billable_flow_count) over (partition by account_id order by dt_month) as prev_account_last_day_billable_flow_count // NEW\n        , lag(account_last_day_billable_flow_count, 2) over (partition by account_id order by dt_month) as prev_prev_account_last_day_billable_flow_count // NEW\n    from user_billable_recipe_count_snapshot\n    where 1=1\n        and my_date = last_day(my_date)\n    group by 1,2\n    order by 1, 2 desc\n)\n\n\n, prev_usage_flag_1 as (\n    select \n        a.entry_date\n        , a.accountid as account_id\n        , a.id as contract_id\n    from workato_business_systems.salesforce_snapshot.cpq_contract a\n    join workato_business_systems.salesforce_snapshot.opportunity b\n        on a.sbqqsc__opportunity__c = b.id\n        and a.entry_date = b.entry_date\n    where 1=1\n        and a.isdeleted = false\n        and coalesce(a.sbcf_cpqcontractstatus__c, a.status) = 'Active'\n        and ifnull(b.type, '') != 'Professional Services'\n    qualify count(distinct a.id) over (partition by a.accountid, a.entry_date) = 1 // only want accounts with one active contracts a day \n)\n\n, prev_usage_flag as (\n    select\n        dt_month\n        , account_id\n        , monthly_lists_cpq_contracts\n        , lag(monthly_lists_cpq_contracts) over (partition by account_id order by dt_month) as prev_monthly_lists_cpq_contracts\n        , lag(monthly_lists_cpq_contracts, 2) over (partition by account_id order by dt_month) as prev_prev_monthly_lists_cpq_contracts\n        , case \n            when equal_null(monthly_lists_cpq_contracts, prev_monthly_lists_cpq_contracts) = true and equal_null(monthly_lists_cpq_contracts, prev_prev_monthly_lists_cpq_contracts) = true then true\n            else false\n            end same_cpq_contract_past_3months\n    from (\n        select \n            date_trunc('month', entry_date) as dt_month\n            , account_id\n            , contract_id\n            , array_agg(distinct contract_id) within group (order by contract_id) over (partition by dt_month, account_id) as monthly_lists_cpq_contracts // its a window function so need to group by to remove duplicate rows\n        from prev_usage_flag_1\n        group by 1,2,3\n    )\n    group by 1,2,3  \n)\n\n-- select * from prev_usage_flag;\n\n, t3 as (\n    select \n        a.*\n        , b.account_last_day_billable_flow_count\n        -- , lag(b.account_last_day_billable_flow_count) over (partition by a.account_id order by a.dt_month) as prev_account_last_day_billable_flow_count // OLD\n        -- , lag(b.account_last_day_billable_flow_count, 2) over (partition by a.account_id order by a.dt_month) as prev_prev_account_last_day_billable_flow_count // OLD\n        , b.prev_account_last_day_billable_flow_count // NEW\n        , b.prev_prev_account_last_day_billable_flow_count // NEW\n        , c.same_cpq_contract_past_3months\n    from t2 a\n    left join account_last_day_of_month_billable_count b\n        on a.account_id = b.account_id\n        and a.dt_month = b.dt_month\n    left join prev_usage_flag c\n        on a.account_id = c.account_id\n        and a.dt_month = c.dt_month\n)\n\n-- select \n--     date(sysdate()) as ingestion_date\n--     , last_day(dateadd('month', -1, current_date)) as reporting_month\n--     , * exclude (account_owner_id, account_owner_name, account_owner_email)\n--     , account_owner_id\n--     , account_owner_name\n--     , account_owner_email\n-- from t3\n-- ;\n\n\n-- select *\n-- from PRODUCT.ITERABLE.USAGE_EMAIL_ALERT_GENERALUSAGE\n-- where account_id = '0013l000025QTgBAAW'\n-- order by 1 desc, 2 desc, 3, dt_month\n-- ;\n\n-- show columns in table PRODUCT.ITERABLE.USAGE_EMAIL_ALERT_GENERALUSAGE;\n\n-------------------------------------------------------------------------------------------------------------------------------------------\n\n, flow_daily_task_count_all_dc as (\n    select \n        data_center\n        , entry_date as dt\n        , date_trunc('month', entry_date) as dt_month\n        , user_id\n        , flow_id\n        , task_count as flow_daily_task_count\n    from product.workato_usage.consumption_usage_fact\n)\n\n-- select *\n-- from flow_daily_task_count_all_dc\n-- where 1=1\n--     and user_id in (1060017,1828197,1828196)\n--     and data_center = 'US';\n    \n\n, top_10_recipes_monthly_1 as (\n    select \n        b.account_id\n        , b.account_name\n        , b.contract_id\n        , b.contract_startdate\n        , b.contract_enddate\n        , b.consumption_startdate\n        , b.consumption_enddate\n        , a.dt\n        , b.user_id\n        , b.user_name_adj as user_name\n        , b.data_center\n        , b.unique_env_workspace\n        , b.environment_type\n        , a.flow_id\n        , a.flow_daily_task_count\n    from flow_daily_task_count_all_dc a\n    join direct_customers_contracts_users b\n        on a.user_id::varchar = b.user_id\n        and a.data_center = b.data_center\n    where 1=1\n        and a.dt >= b.consumption_startdate\n        and a.dt <= b.consumption_enddate\n        and a.dt_month != date_trunc('month', current_date) -- exclude the month of query\n    group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15\n)\n\n, top_10_recipes_monthly_2 as (\n    select *, ifnull(lead(a.dt) over (partition by a.account_id, a.flow_id, a.user_id order by a.dt), current_date) as next_dt\n    from top_10_recipes_monthly_1 a\n)\n\n-- select * from top_10_recipes_monthly_2;\n\n, top_10_recipes_monthly_3 as (\n    select \n        a.*\n        , b.my_date\n        , date_trunc('month', b.my_date) as dt_month\n        , iff(a.dt = b.my_date, a.flow_daily_task_count, 0) as flow_daily_task_count_adj\n    from top_10_recipes_monthly_2 a\n    left join public.cal_month_dim b\n        on b.my_date >= a.dt\n        and b.my_date < a.next_dt\n    where 1=1\n        and date_trunc('month', b.my_date) < date_trunc('month', current_date) -- last day = last day of reporting month\n)\n\n, top_10_recipes_monthly_4 as (\n    select \n        account_id\n        , account_name\n        , contract_id\n        , contract_startdate\n        , contract_enddate\n        , consumption_startdate\n        , consumption_enddate\n        , dt_month\n        , user_id\n        , user_name\n        , data_center\n        , unique_env_workspace\n        , environment_type\n        , flow_id\n        , sum(flow_daily_task_count_adj) as flow_monthly_task_count\n        , sum(flow_monthly_task_count) over (partition by flow_id, user_id order by dt_month) as flow_cumulative_task_count\n    from top_10_recipes_monthly_3\n    group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14\n)\n\n// cumulative ranking\n, top_10_recipes_monthly_5 as (\n    select row_number() over (partition by account_id, dt_month order by flow_cumulative_task_count desc) rn, *\n    from top_10_recipes_monthly_4\n    qualify rn <= 10\n    order by account_id, dt_month, rn\n)\n\n\n\n// new - monthly ranking\n, top_10_recipes_monthly_6 as (\n    select row_number() over (partition by account_id, dt_month order by flow_monthly_task_count desc) rn, *\n    from top_10_recipes_monthly_4\n    qualify rn <= 10\n    order by account_id, dt_month, rn\n)\n\n-- select * from top_10_recipes_monthly_new_6;\n\n, top_10_recipes_monthly as (\n    select a.*, b.name as flow_name, iff(b.deleted_at is not null, true, false) flow_deleted\n    from top_10_recipes_monthly_5 a\n    left join workato_usage_intermediate.flows_persistent b\n        on a.user_id = b.user_id\n        and a.flow_id = b.id\n        and a.data_center = b.data_center\n    order by account_id, dt_month, rn\n)\n\n// scroll to the bottom to see usage_email_alert_flow_name\n, top_10_recipes_monthly_v2 as (\n    select a.*, b.name as flow_name, iff(b.deleted_at is not null, true, false) flow_deleted\n    from top_10_recipes_monthly_6 a\n    left join workato_usage_intermediate.flows_persistent b\n        on a.user_id = b.user_id\n        and a.flow_id = b.id\n        and a.data_center = b.data_center\n    order by account_id, dt_month, rn\n)\n\n\n-- select \n--     date(sysdate()) as ingestion_date\n--     , last_day(dateadd('month', -1, current_date)) as reporting_month\n--     , *\n-- from top_10_recipes_monthly\n-- ;\n\nselect \n    date(sysdate()) as ingestion_date\n    , last_day(dateadd('month', -1, current_date)) as reporting_month\n    , *\nfrom top_10_recipes_monthly_v2\n;", "update_only": "false"}, "block": []}, {"number": 4, "keyword": "action", "provider": "slack", "name": "post_message_to_channel", "as": "2ed0fd60", "skip": false, "input": {"channel": "C05LVU4NVN0", "parse": "false", "text": "Top 10 recipes data V2 has been successfully ingested"}, "block": []}, {"number": 5, "keyword": "catch", "provider": "", "name": "", "as": "6acde0a3", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 6, "keyword": "action", "provider": "slack", "name": "post_message_to_channel", "as": "60a29776", "skip": false, "input": {"channel": "C05LVU4NVN0", "parse": "false", "text": "Top 10 recipes V2 ingestion has failed"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)
RAW_INSERT_SQL = str(_EXPECTED_TREE["block"][0]["block"][0]["input"]["sql"])

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (SUCCESS_POST_AS, "slack", "post_message_to_channel"),
    (CATCH_POST_AS, "slack", "post_message_to_channel"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "slack.post_message",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "outcome",
    "post_text",
    "inserted_row_count",
    "final_snowflake_tables",
    "cleanup_tables",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("success_insert", "empty_insert", "catch_failure")


def validate_124261270(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Twin guards on the exact V1/V2 deltas (target table, final CTE, texts).
    sql_node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == SQL_STEP_AS), None
    )
    sql = str(((sql_node or {}).get("input") or {}).get("sql") or "")
    if not sql.startswith(SQL_PREFIX):
        raise RuntimeError(f"recipe {RECIPE_ID} INSERT target changed (twin drift?)")
    if not sql.rstrip().endswith(SQL_FINAL_TAIL.rstrip()) or not sql.rstrip().endswith(";"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} final select CTE changed (twin drift: monthly-rank "
            "top_10_recipes_monthly_v2 is THIS recipe's tail)"
        )
    for step_as, text in ((SUCCESS_POST_AS, SUCCESS_TEXT), (CATCH_POST_AS, FAILURE_TEXT)):
        node = next(
            (n for n in _walk_nodes(raw) if str(n.get("as") or "") == step_as), None
        )
        node_input = (node or {}).get("input") or {}
        if str(node_input.get("text") or "") != text:
            raise RuntimeError(f"recipe {RECIPE_ID} slack text changed on {step_as} (twin drift?)")
        if str(node_input.get("channel") or "") != SLACK_LITERAL_CHANNEL:
            raise RuntimeError(f"recipe {RECIPE_ID} slack channel changed on {step_as}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "target_table": TARGET_TABLE,
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


def seed_124261270(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124261270(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (the cron payload is "
            f"never dereferenced): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_expect_common(expect, force)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    if expect["outcome"] == "catch_failure":
        _require_catch_variant(seed_in, expect, force)
    else:
        _require_live_variant(seed_in, expect)
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        target_rows = deepcopy(
            expect["final_snowflake_tables"][TARGET_TABLE]["rows"]
        )
        out["_simulated_read_fixtures"] = [
            {
                "tool": "snowflake.run_custom_sql",
                "args": {"sql": RAW_INSERT_SQL, "parameters": {}},
                "result": {
                    "ok": True,
                    "table": TARGET_TABLE,
                    "rows": [
                        {"number of rows inserted": len(target_rows)}
                    ],
                    "records": [
                        {"number of rows inserted": len(target_rows)}
                    ],
                    "count": 1,
                    "rows_affected": len(target_rows),
                },
                "replace_snowflake_tables": {TARGET_TABLE: target_rows},
            }
        ]
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_124261270(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124261270(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a forced "
            "catch error -- nothing to run"
        )
    # Every branch posts to the literal C-channel: refuse to run without the
    # benchmark override (the org channel must never receive live posts).
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
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
            # All 15 registered tables (14 seeded sources + the pre-created
            # INSERT target) are benchmark-owned live objects: drop them even
            # on failure. Twin note: 124258051 shares the 14 source names --
            # the two recipes' live lanes must run serially.
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
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
    result["verifier"] = verify_124261270(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_expect_common(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if (outcome == "catch_failure") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must be present exactly on the "
            "catch_failure outcome (the catch is not naturally reachable)"
        )


def _require_live_variant(seed_in: dict[str, Any], expect: dict[str, Any]) -> None:
    if sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} success/empty variants must seed exactly the "
            f"snowflake_live section; got {sorted(seed_in.keys())}"
        )
    current_date = _require_snowflake_section(seed_in["snowflake_live"])
    outcome = expect["outcome"]
    if "catch_message" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} only catch variants pin catch_message")
    final_tables = expect.get("final_snowflake_tables")
    if not isinstance(final_tables, dict) or sorted(final_tables.keys()) != [TARGET_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_snowflake_tables must pin exactly the "
            f"INSERT target {TARGET_TABLE!r}"
        )
    target_spec = final_tables[TARGET_TABLE]
    rows = target_spec.get("rows") if isinstance(target_spec, dict) else None
    count = target_spec.get("count") if isinstance(target_spec, dict) else None
    if not isinstance(rows, list) or count != len(rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} final target pin must carry count == len(rows)"
        )
    if expect.get("inserted_row_count") != len(rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.inserted_row_count must equal the pinned final "
            f"target rows ({len(rows)})"
        )
    reporting_month = (current_date.replace(day=1) - datetime.timedelta(days=1)).isoformat()
    seen_keys: set[tuple[Any, Any]] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} final target row {idx} must be an object")
        if row.get("INGESTION_DATE") != current_date.isoformat():
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} INGESTION_DATE must be the pinned "
                f"current_time date {current_date.isoformat()} (date(sysdate()) rewrite)"
            )
        if row.get("REPORTING_MONTH") != reporting_month:
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} REPORTING_MONTH must be "
                f"{reporting_month} (last_day of the month before current_date)"
            )
        key = (row.get("DT_MONTH"), row.get("FLOW_ID"))
        if key in seen_keys:
            raise RuntimeError(
                f"recipe {RECIPE_ID} final target rows must be unique per "
                f"(DT_MONTH, FLOW_ID); duplicate {key}"
            )
        seen_keys.add(key)
    expected_shape = {
        "outcome_rows": len(rows) > 0 if outcome == "success_insert" else len(rows) == 0,
        "post_text": expect.get("post_text") == SUCCESS_TEXT,
        "count": expect.get("executed_action_count") == 2,
        "tools": expect.get("tools") == ["snowflake.run_custom_sql", "slack.post_message"],
        "cleanup": expect.get("cleanup_tables")
        == sorted([TARGET_TABLE, *SOURCE_COLUMNS.keys()]),
    }
    if not all(expected_shape.values()):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block inconsistent with outcome {outcome!r}: "
            f"{expected_shape}"
        )


def _require_catch_variant(seed_in: dict[str, Any], expect: dict[str, Any], force: Any) -> None:
    if seed_in != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must seed exactly {{}} (the forced error "
            "fires BEFORE the snowflake adapter -- no live table may be provisioned); "
            f"got {sorted(seed_in.keys())}"
        )
    if str(force.get("step_as") or "") != SQL_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL_STEP_AS!r} "
            "with an explicit error message"
        )
    checks = (
        expect.get("post_text") == FAILURE_TEXT,
        expect.get("catch_message") == force.get("error"),
        expect.get("executed_action_count") == 1,
        expect.get("tools") == ["slack.post_message"],
        expect.get("inserted_row_count") is None,
        expect.get("final_snowflake_tables") is None,
        expect.get("cleanup_tables") is None,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch expect block inconsistent: failure text, "
            f"catch_message == forced error, 1 action, tools [slack.post_message], "
            f"null snowflake pins; got {expect!r}"
        )


def _require_snowflake_section(section: Any) -> datetime.date:
    if not isinstance(section, dict) or sorted(section.keys()) != ["current_time", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly "
            "{'current_time', 'tables'} (the SQL calls sysdate() and current_date ~12x)"
        )
    fixed = str(section.get("current_time") or "")
    parsed = datetime.datetime.fromisoformat(fixed.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} current_time must carry an explicit UTC offset: {fixed!r}"
        )
    tables = section["tables"]
    expected_keys = sorted([TARGET_TABLE, *SOURCE_COLUMNS.keys()])
    if not isinstance(tables, dict) or sorted(tables.keys()) != expected_keys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must register exactly the INSERT target plus the "
            f"14 literal source names: {expected_keys}"
        )
    target = tables[TARGET_TABLE]
    if (
        not isinstance(target, dict)
        or sorted(target.keys()) != ["columns", "rows"]
        or target["rows"] != []
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} INSERT target must be {{'columns': ..., 'rows': []}} "
            "(pre-created empty with the exact 21-column shape)"
        )
    if list(target["columns"].keys()) != list(TARGET_COLUMNS.keys()) or dict(
        target["columns"]
    ) != TARGET_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} target columns must be exactly {list(TARGET_COLUMNS)} "
            "IN ORDER (the INSERT has no column list -- positional mapping)"
        )
    for name, columns in SOURCE_COLUMNS.items():
        _require_typed_table(tables[name], name, columns)
    return parsed.astimezone(datetime.timezone.utc).date()


def _require_typed_table(spec: Any, table: str, columns: dict[str, str]) -> None:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} spec must be {{'columns','rows'}}")
    if spec["columns"] != columns:
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} columns must be exactly {columns}")
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} rows must be a list (may be empty)")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table} row {idx} must be an object")
        extra = sorted(set(row.keys()) - set(columns.keys()))
        if extra:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} uses undeclared columns: {extra}"
            )
        for column, value in row.items():
            kind = columns[column]
            if value is None:
                continue
            if kind == "boolean" and not isinstance(value, bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be boolean"
                )
            if kind == "number" and (isinstance(value, bool) or not isinstance(value, int)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be an integer"
                )
            if kind == "string" and not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be a string"
                )
            if kind == "date":
                try:
                    datetime.date.fromisoformat(str(value))
                except ValueError as exc:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table} row {idx} {column} must be "
                        f"YYYY-MM-DD: {value!r}"
                    ) from exc
            if kind == "timestamp" and not str(value).strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be a "
                    "timestamp string or null"
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


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if not live:
        return {}
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
