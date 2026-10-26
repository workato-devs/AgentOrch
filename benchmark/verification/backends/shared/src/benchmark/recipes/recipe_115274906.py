from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_115274906


RECIPE_ID = "115274906"
SEED_TYPE = "freshdesk_severity_slack_escalation_variant"
TRACK = "webhook_freshdesk_severity_slack_post"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "93dc1a39"
LOOKUP_STEP_AS = "eb098e27"
DECLARE_STEP_AS = "613f2945"
SEVERITY_POST_STEPS: dict[str, str] = {
    "Severity 4": "f46f05e4",
    "Severity 2": "c8daa35f",
    "Severity 3": "ed4ce889",
    "Severity 1": "d8a49677",
}
RAW_CHANNEL = "CCXAQPNPJ"
LIVE_AGENT_EMAIL = "jamie.lee@corp.example"
LIVE_AGENT_USER_ID = "U0B91BSRGF8"


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "93dc1a39",
  "provider": "workato_webhooks",
  "name": "new_event",
  "skip": false,
  "input": {
   "request": {
    "headers_schema": "[{\"control_type\":\"text\",\"label\":\"Accept\",\"type\":\"string\",\"name\":\"accept\"},{\"control_type\":\"text\",\"label\":\"Accept encoding\",\"type\":\"string\",\"name\":\"accept_encoding\"},{\"control_type\":\"text\",\"label\":\"Content length\",\"type\":\"string\",\"name\":\"content_length\"},{\"control_type\":\"text\",\"label\":\"Content type\",\"type\":\"string\",\"name\":\"content_type\"},{\"control_type\":\"text\",\"label\":\"Traceparent\",\"type\":\"string\",\"name\":\"traceparent\"},{\"control_type\":\"text\",\"label\":\"User agent\",\"type\":\"string\",\"name\":\"user_agent\"},{\"control_type\":\"text\",\"label\":\"X amzn trace ID\",\"type\":\"string\",\"name\":\"x_amzn_trace_id\"},{\"control_type\":\"text\",\"label\":\"X correlation ID\",\"type\":\"string\",\"name\":\"x_correlation_id\"},{\"control_type\":\"text\",\"label\":\"X forwarded for\",\"type\":\"string\",\"name\":\"x_forwarded_for\"},{\"control_type\":\"text\",\"label\":\"X forwarded port\",\"type\":\"string\",\"name\":\"x_forwarded_port\"},{\"control_type\":\"text\",\"label\":\"X forwarded proto\",\"type\":\"string\",\"name\":\"x_forwarded_proto\"},{\"control_type\":\"text\",\"label\":\"X request ID\",\"type\":\"string\",\"name\":\"x_request_id\"}]",
    "payload_schema": "[{\"properties\":[{\"control_type\":\"number\",\"label\":\"Ticket ID\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"ticket_id\"},{\"control_type\":\"text\",\"label\":\"Ticket subject\",\"type\":\"string\",\"name\":\"ticket_subject\"},{\"control_type\":\"text\",\"label\":\"Ticket description\",\"type\":\"string\",\"name\":\"ticket_description\"},{\"control_type\":\"text\",\"label\":\"Ticket URL\",\"type\":\"string\",\"name\":\"ticket_url\"},{\"control_type\":\"text\",\"label\":\"Ticket portal URL\",\"type\":\"string\",\"name\":\"ticket_portal_url\"},{\"control_type\":\"text\",\"label\":\"Ticket tags\",\"type\":\"string\",\"name\":\"ticket_tags\"},{\"control_type\":\"text\",\"label\":\"Ticket latest public comment\",\"type\":\"string\",\"name\":\"ticket_latest_public_comment\"},{\"control_type\":\"text\",\"label\":\"Ticket latest private comment\",\"type\":\"string\",\"name\":\"ticket_latest_private_comment\"},{\"control_type\":\"text\",\"label\":\"Ticket group name\",\"type\":\"string\",\"name\":\"ticket_group_name\"},{\"control_type\":\"text\",\"label\":\"Ticket agent name\",\"type\":\"string\",\"name\":\"ticket_agent_name\"},{\"control_type\":\"text\",\"label\":\"Ticket agent email\",\"type\":\"string\",\"name\":\"ticket_agent_email\"},{\"control_type\":\"text\",\"label\":\"Ticket internal group name\",\"type\":\"string\",\"name\":\"ticket_internal_group_name\"},{\"control_type\":\"text\",\"label\":\"Ticket internal agent name\",\"type\":\"string\",\"name\":\"ticket_internal_agent_name\"},{\"control_type\":\"text\",\"label\":\"Ticket internal agent email\",\"type\":\"string\",\"name\":\"ticket_internal_agent_email\"},{\"control_type\":\"text\",\"label\":\"Ticket satisfaction survey\",\"type\":\"string\",\"name\":\"ticket_satisfaction_survey\"},{\"control_type\":\"text\",\"label\":\"Ticket due by time\",\"type\":\"string\",\"name\":\"ticket_due_by_time\"},{\"control_type\":\"text\",\"label\":\"Ticket status\",\"type\":\"string\",\"name\":\"ticket_status\"},{\"control_type\":\"text\",\"label\":\"Ticket priority\",\"type\":\"string\",\"name\":\"ticket_priority\"},{\"control_type\":\"text\",\"label\":\"Ticket source\",\"type\":\"string\",\"name\":\"ticket_source\"},{\"control_type\":\"text\",\"label\":\"Ticket ticket type\",\"type\":\"string\",\"name\":\"ticket_ticket_type\"},{\"control_type\":\"text\",\"label\":\"Ticket cf ticket comments\",\"type\":\"string\",\"name\":\"ticket_cf_ticket_comments\"},{\"control_type\":\"text\",\"label\":\"Ticket cf support plan new\",\"type\":\"string\",\"name\":\"ticket_cf_support_plan_new\"},{\"control_type\":\"text\",\"label\":\"Ticket cf assignment group level\",\"type\":\"string\",\"name\":\"ticket_cf_assignment_group_level\"},{\"control_type\":\"text\",\"label\":\"Ticket cf severity\",\"type\":\"string\",\"name\":\"ticket_cf_severity\"},{\"control_type\":\"text\",\"label\":\"Ticket cf next follow up date\",\"type\":\"string\",\"name\":\"ticket_cf_next_follow_up_date\"},{\"control_type\":\"text\",\"label\":\"Ticket cf resolution summary\",\"type\":\"string\",\"name\":\"ticket_cf_resolution_summary\"},{\"control_type\":\"text\",\"label\":\"Ticket cf escalated\",\"type\":\"string\",\"name\":\"ticket_cf_escalated\"},{\"control_type\":\"text\",\"label\":\"Ticket cf trello card URL\",\"type\":\"string\",\"name\":\"ticket_cf_trello_card_url\"},{\"control_type\":\"text\",\"label\":\"Ticket cf github URL\",\"type\":\"string\",\"name\":\"ticket_cf_github_url\"},{\"control_type\":\"text\",\"label\":\"Ticket cf lvl 4 slack post\",\"type\":\"string\",\"name\":\"ticket_cf_lvl4_slack_post\"},{\"control_type\":\"text\",\"label\":\"Ticket cf other related slack post\",\"type\":\"string\",\"name\":\"ticket_cf_other_related_slack_post\"},{\"control_type\":\"text\",\"label\":\"Ticket trello board\",\"type\":\"string\",\"name\":\"ticket_trello_board\"},{\"control_type\":\"text\",\"label\":\"Ticket trello instructions\",\"type\":\"string\",\"name\":\"ticket_trello_instructions\"},{\"control_type\":\"text\",\"label\":\"Ticket cf agents manager\",\"type\":\"string\",\"name\":\"ticket_cf_agents_manager\"},{\"control_type\":\"text\",\"label\":\"Ticket cf agents lead\",\"type\":\"string\",\"name\":\"ticket_cf_agents_lead\"},{\"control_type\":\"text\",\"label\":\"Ticket cf custom connector URL\",\"type\":\"string\",\"name\":\"ticket_cf_custom_connector_url\"},{\"control_type\":\"text\",\"label\":\"Ticket cf workato email 2\",\"type\":\"string\",\"name\":\"ticket_cf_workato_email_2\"},{\"control_type\":\"text\",\"label\":\"Ticket hr application stage\",\"type\":\"string\",\"name\":\"ticket_hr_application_stage\"},{\"control_type\":\"text\",\"label\":\"Ticket ticket sub type\",\"type\":\"string\",\"name\":\"ticket_ticket_sub_type\"},{\"control_type\":\"text\",\"label\":\"Ticket cf workato email\",\"type\":\"string\",\"name\":\"ticket_cf_workato_email\"},{\"control_type\":\"text\",\"label\":\"Ticket account matters\",\"type\":\"string\",\"name\":\"ticket_account_matters\"},{\"control_type\":\"text\",\"label\":\"Ticket cf business impact\",\"type\":\"string\",\"name\":\"ticket_cf_business_impact\"},{\"control_type\":\"text\",\"label\":\"Ticket cf recipe URL\",\"type\":\"string\",\"name\":\"ticket_cf_recipe_url\"},{\"control_type\":\"text\",\"label\":\"Ticket cf name of custom connector\",\"type\":\"string\",\"name\":\"ticket_cf_name_of_custom_connector\"},{\"control_type\":\"text\",\"label\":\"Ticket cf support tool used\",\"type\":\"string\",\"name\":\"ticket_cf_support_tool_used\"},{\"control_type\":\"text\",\"label\":\"Ticket cf workato user ID\",\"type\":\"string\",\"name\":\"ticket_cf_workato_user_id\"},{\"control_type\":\"text\",\"label\":\"Ticket cf account executive autopopulated\",\"type\":\"string\",\"name\":\"ticket_cf_account_executive_autopopulated\"},{\"control_type\":\"text\",\"label\":\"Ticket cf primary csm auto populated\",\"type\":\"string\",\"name\":\"ticket_cf_primary_csm_auto_populated\"},{\"control_type\":\"text\",\"label\":\"Ticket cf primary csr autopopulated\",\"type\":\"string\",\"name\":\"ticket_cf_primary_csr_autopopulated\"},{\"control_type\":\"text\",\"label\":\"Ticket cf pod territory\",\"type\":\"string\",\"name\":\"ticket_cf_pod_territory\"},{\"control_type\":\"text\",\"label\":\"Ticket cf pod leader autopopulated\",\"type\":\"string\",\"name\":\"ticket_cf_pod_leader_autopopulated\"},{\"control_type\":\"text\",\"label\":\"Ticket cf end customer for partner only\",\"type\":\"string\",\"name\":\"ticket_cf_end_customer_for_partner_only\"},{\"control_type\":\"text\",\"label\":\"Ticket cf partner status autopopulated\",\"type\":\"string\",\"name\":\"ticket_cf_partner_status_autopopulated\"},{\"control_type\":\"text\",\"label\":\"Ticket cf closure resolution summary\",\"type\":\"string\",\"name\":\"ticket_cf_closure_resolution_summary\"},{\"control_type\":\"text\",\"label\":\"Ticket cf user sign up date\",\"type\":\"string\",\"name\":\"ticket_cf_user_sign_up_date\"},{\"control_type\":\"text\",\"label\":\"Ticket cf fsm contact name\",\"type\":\"string\",\"name\":\"ticket_cf_fsm_contact_name\"},{\"control_type\":\"text\",\"label\":\"Ticket cf fsm phone number\",\"type\":\"string\",\"name\":\"ticket_cf_fsm_phone_number\"},{\"control_type\":\"text\",\"label\":\"Ticket cf fsm service location\",\"type\":\"string\",\"name\":\"ticket_cf_fsm_service_location\"},{\"control_type\":\"text\",\"label\":\"Ticket cf fsm appointment start time\",\"type\":\"string\",\"name\":\"ticket_cf_fsm_appointment_start_time\"},{\"control_type\":\"text\",\"label\":\"Ticket cf fsm appointment end time\",\"type\":\"string\",\"name\":\"ticket_cf_fsm_appointment_end_time\"},{\"control_type\":\"text\",\"label\":\"Ticket cf fsm customer signature\",\"type\":\"string\",\"name\":\"ticket_cf_fsm_customer_signature\"},{\"control_type\":\"text\",\"label\":\"Ticket cf hq country autopopulated\",\"type\":\"string\",\"name\":\"ticket_cf_hq_country_autopopulated\"},{\"control_type\":\"text\",\"label\":\"Ticket cf evaluated\",\"type\":\"string\",\"name\":\"ticket_cf_evaluated\"},{\"control_type\":\"text\",\"label\":\"Ticket cf require l 3\",\"type\":\"string\",\"name\":\"ticket_cf_require_l3\"},{\"control_type\":\"text\",\"label\":\"Ticket cf test issue typecustomers only\",\"type\":\"string\",\"name\":\"ticket_cf_test_issue_typecustomers_only\"},{\"control_type\":\"text\",\"label\":\"Ticket cf reported by\",\"type\":\"string\",\"name\":\"ticket_cf_reported_by\"},{\"control_type\":\"text\",\"label\":\"Ticket cf require product fix\",\"type\":\"string\",\"name\":\"ticket_cf_require_product_fix\"},{\"control_type\":\"text\",\"label\":\"Ticket cf closure reason\",\"type\":\"string\",\"name\":\"ticket_cf_closure_reason\"},{\"control_type\":\"text\",\"label\":\"Ticket cf summary\",\"type\":\"string\",\"name\":\"ticket_cf_summary\"},{\"control_type\":\"text\",\"label\":\"Ticket cf issue type\",\"type\":\"string\",\"name\":\"ticket_cf_issue_type\"},{\"control_type\":\"text\",\"label\":\"Ticket company name\",\"type\":\"string\",\"name\":\"ticket_company_name\"},{\"control_type\":\"text\",\"label\":\"Ticket contact name\",\"type\":\"string\",\"name\":\"ticket_contact_name\"},{\"control_type\":\"text\",\"label\":\"Ticket contact email\",\"type\":\"string\",\"name\":\"ticket_contact_email\"},{\"control_type\":\"text\",\"label\":\"Ticket contact last seen\",\"type\":\"string\",\"name\":\"ticket_contact_last_seen\"},{\"control_type\":\"text\",\"label\":\"Ticket contact country\",\"type\":\"string\",\"name\":\"ticket_contact_country\"}],\"label\":\"Freshdesk webhook\",\"type\":\"object\",\"name\":\"freshdesk_webhook\"}]",
    "query_params": "[]",
    "webhook_type": "json"
   },
   "webhook_suffix": "automation-institute-ticket"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "eb098e27",
  "provider": "slack_bot",
  "name": "get_user_by_email",
  "skip": false,
  "input": {
   "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_agent_email\"]}')}"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "613f2945",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "description": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\",\"freshdesk_webhook\",\"ticket_description\"]}').strip_tags"
    },
    "schema": "[{\"name\":\"description\",\"type\":\"string\",\"optional\":true,\"label\":\"description\",\"details\":{\"real_name\":\"description\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"
   }
  }
 },
 {
  "keyword": "if",
  "number": 4,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_severity\"]}')}",
     "operand": "equals_to",
     "rhs": "Severity 4"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "f46f05e4",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Hi @automation-institute,\nRequesting for your assistance. Thank you!\n\n:freshdesk_2: FD: `#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_id\"]}')}` : <#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_portal_url\"]}')}| *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_subject\"]}')}*>\n:large_blue_circle:  Issue Severity: *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_severity\"]}')}* | :pencil: Posted by: <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"eb098e27\",\"path\":[\"id\"]}')}>\n\n*Customer Details*\n:bust_in_silhouette:  Requestor: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_contact_name\"]}')}\n:office: Company Name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_company_name\"]}')}\n:workato: Support Plan: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_support_plan_new\"]}')}\n\n:pencil: Ticket Description:\n_#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"613f2945\",\"path\":[\"description\"]}')}_\n\n```This message is posted using Freshdesk Automation```"
    }
   ],
   "channel": "CCXAQPNPJ"
  }
 },
 {
  "keyword": "if",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_severity\"]}')}",
     "operand": "equals_to",
     "rhs": "Severity 2"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "c8daa35f",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Hi @automation-institute,\nRequesting for your assistance. Thank you!\n\n:freshdesk_2: FD: `#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_id\"]}')}` : <#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_portal_url\"]}')}| *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_subject\"]}')}*>\n:red_circle: Issue Severity: *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_severity\"]}')}* | :pencil: Posted by: <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"eb098e27\",\"path\":[\"id\"]}')}>\n\n*Customer Details*\n:bust_in_silhouette:  Requestor: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_contact_name\"]}')}\n:office: Company Name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_company_name\"]}')}\n:workato: Support Plan: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_support_plan_new\"]}')}\n\n:pencil: Ticket Description:\n_#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"613f2945\",\"path\":[\"description\"]}')}_\n\n```This message is posted using Freshdesk Automation```"
    }
   ],
   "channel": "CCXAQPNPJ"
  }
 },
 {
  "keyword": "if",
  "number": 8,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_severity\"]}')}",
     "operand": "equals_to",
     "rhs": "Severity 3"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "ed4ce889",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Hi @automation-institute,\nRequesting for your assistance. Thank you!\n\n:freshdesk_2: FD: `#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_id\"]}')}` : <#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_portal_url\"]}')} | *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_subject\"]}')}*>\n:large_yellow_circle:  Issue Severity: *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_severity\"]}')}* | :pencil: Posted by: <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"eb098e27\",\"path\":[\"id\"]}')}>\n\n*Customer Details*\n:bust_in_silhouette:  Requestor: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_contact_name\"]}')}\n:office: Company Name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_company_name\"]}')}\n:workato: Support Plan: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_support_plan_new\"]}')}\n\n:pencil: Ticket Description:\n_#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"613f2945\",\"path\":[\"description\"]}')}_\n\n```This message is posted using Freshdesk Automation```"
    }
   ],
   "channel": "CCXAQPNPJ"
  }
 },
 {
  "keyword": "if",
  "number": 10,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_severity\"]}')}",
     "operand": "equals_to",
     "rhs": "Severity 1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "d8a49677",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Hi @automation-institute,\nRequesting for your assistance. Thank you!\n\n:freshdesk_2: FD: `#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_id\"]}')}` : <#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_portal_url\"]}')}| *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_subject\"]}')}*>\n:fire:  Issue Severity: *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_severity\"]}')}* | :pencil: Posted by: <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"eb098e27\",\"path\":[\"id\"]}')}>\n\n*Customer Details*\n:bust_in_silhouette:  Requestor: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_contact_name\"]}')}\n:office: Company Name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_company_name\"]}')}\n:workato: Support Plan: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"93dc1a39\",\"path\":[\"payload\", \"freshdesk_webhook\", \"ticket_cf_support_plan_new\"]}')}\n\n:pencil: Ticket Description:\n_#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"613f2945\",\"path\":[\"description\"]}')}_\n\n```This message is posted using Freshdesk Automation```"
    }
   ],
   "channel": "CCXAQPNPJ"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "workato_runtime.declare_variable",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "slack.post_message",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "severity",
    "agent_user_id",
    "stripped_description",
    "post_step_as",
    "post_text",
)
DEREFERENCED_FIELDS = (
    "ticket_agent_email",
    "ticket_description",
    "ticket_cf_severity",
    "ticket_id",
    "ticket_portal_url",
    "ticket_subject",
    "ticket_contact_name",
    "ticket_company_name",
    "ticket_cf_support_plan_new",
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


def validate_115274906(raw: dict[str, Any]) -> dict[str, Any]:
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


def _require_payload(trigger: dict[str, Any]) -> dict[str, Any]:
    if set(trigger) != {"payload"} or not isinstance(trigger.get("payload"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'payload': {{...}}}}"
        )
    payload = trigger["payload"]
    if set(payload) != {"freshdesk_webhook"} or not isinstance(
        payload.get("freshdesk_webhook"), dict
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload must carry exactly the freshdesk_webhook object"
        )
    webhook = payload["freshdesk_webhook"]
    missing = [field for field in DEREFERENCED_FIELDS if field not in webhook]
    if missing:
        raise RuntimeError(
            f"recipe {RECIPE_ID} freshdesk_webhook payload missing dereferenced fields: {missing}"
        )
    if webhook.get("ticket_agent_email") != LIVE_AGENT_EMAIL:
        raise RuntimeError(
            f"recipe {RECIPE_ID} ticket_agent_email must be the live-proven workspace "
            f"member {LIVE_AGENT_EMAIL!r} (users.lookupByEmail fails fast on unknown "
            f"emails; the workspace bot has no profile email): "
            f"{webhook.get('ticket_agent_email')!r}"
        )
    if not isinstance(webhook.get("ticket_description"), str) or not webhook["ticket_description"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} ticket_description must be a non-empty string (strip_tags input)"
        )
    ticket_id = webhook.get("ticket_id")
    if isinstance(ticket_id, bool) or not isinstance(ticket_id, int):
        raise RuntimeError(
            f"recipe {RECIPE_ID} ticket_id must be an int (NUMBER schema field; an int "
            f"renders without a decimal point): {ticket_id!r}"
        )
    return webhook


def _require_expect(expect: Any, webhook: dict[str, Any]) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    severity = webhook.get("ticket_cf_severity")
    if expect.get("severity") != severity:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.severity must echo the seeded ticket_cf_severity"
        )
    if expect.get("agent_user_id") != LIVE_AGENT_USER_ID:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.agent_user_id must pin {LIVE_AGENT_USER_ID!r}"
        )
    expected_step = SEVERITY_POST_STEPS.get(str(severity))
    if expect.get("post_step_as") != expected_step:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.post_step_as must be {expected_step!r} for "
            f"severity {severity!r}: {expect.get('post_step_as')!r}"
        )
    if (expect.get("post_text") is None) != (expected_step is None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.post_text must be the exact rendered text when a "
            "severity matches and null otherwise"
        )
    if expect.get("executed_action_count") != (3 if expected_step else 2):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be 3 with a post and 2 "
            "without"
        )
    if expected_step is not None:
        text = str(expect.get("post_text") or "")
        for fragment in (
            f"<@{LIVE_AGENT_USER_ID}>",
            f"_{expect.get('stripped_description')}_",
            f"*{severity}*",
        ):
            if fragment not in text:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} expect.post_text must contain {fragment!r}"
                )


def seed_115274906(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_115274906(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    webhook = _require_payload(trigger)
    if data.get("seed") not in (None, {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} takes no seed sections (Slack is live, the webhook "
            f"payload is the trigger): {data.get('seed')!r}"
        )
    _require_expect(data.get("expect"), webhook)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_115274906(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_115274906(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
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
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_115274906(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
