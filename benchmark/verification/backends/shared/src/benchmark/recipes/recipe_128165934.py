from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_128165934


RECIPE_ID = "128165934"
SEED_TYPE = "salesforce_domain_account_matcher_variant"
TRACK = "live_salesforce_domain_account_matcher"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "500fcde0"
FQDN_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$"
)
_SF_ID_RE = re.compile(r"[a-zA-Z0-9]{15,18}")
_REF_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*_ID")

ACCOUNT_REQUIRED_FIELDS = ("Name", "Active_Subscription__c")
ACCOUNT_OPTIONAL_FIELDS = ("Subscription_Start_Date__c", "Current_Plan__c")
DOMAIN_SOBJECT = "Domain__c"

REQUIRED_SCHEMA: list[dict[str, str]] = [
    {"sobject": "Account", "field": "Active_Subscription__c", "sf_type": "Checkbox"},
    {"sobject": "Account", "field": "Subscription_Start_Date__c", "sf_type": "Date"},
    {"sobject": "Account", "field": "Current_Plan__c", "sf_type": "Text"},
    {"sobject": DOMAIN_SOBJECT, "field": "Domain__c", "sf_type": "Text"},
    {"sobject": DOMAIN_SOBJECT, "field": "Account__c", "sf_type": "Lookup"},
]

SEED_SALESFORCE_KEYS = {"relationship_expansion", "strict_soql_conditions", "schema", "records"}
EXPECT_KEYS = (
    "tools",
    "tool_expectations",
    "trace_tools",
    "executed_action_count",
    "skipped_steps",
    "formatted_domains",
    "smart_list_sqls",
    "return_accounts",
)
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_smart_list.create_list",
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_smart_list.query_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
SKIPPED_STEP_NUMBERS = [14, 15]

_STRUCTURE_PINS_JSON = r'''
[
 {
  "as": "500fcde0",
  "input": {
   "parameters_schema_json": "[{\"name\":\"emails\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Email\"}],\"of\":\"object\",\"label\":\"Emails\"}]",
   "result_schema_json": "[{\"name\":\"accounts\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Accounts\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false}]}]"
  },
  "keyword": "trigger",
  "name": "execute",
  "number": 1,
  "provider": "workato_recipe_function",
  "skip": false
 },
 {
  "as": "50b34065",
  "input": {
   "list_item_schema_json": "[{\"name\":\"email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Email\"},{\"name\":\"domain\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Domain\"},{\"name\":\"account\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Account\"}]",
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"500fcde0\",\"path\":[\"parameters\", \"emails\"]}')}",
    "account": "=\"\"",
    "domain": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"500fcde0\",\"path\":[\"parameters\",\"emails\",{\"path_element_type\":\"current_item\"},\"email\"]}').split(\"@\").last.strip",
    "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"500fcde0\",\"path\":[\"parameters\", \"emails\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}"
   },
   "name": "domains"
  },
  "keyword": "action",
  "name": "declare_list",
  "number": 2,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"500fcde0\",\"path\":[\"parameters\", \"emails\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 3,
  "provider": null,
  "skip": false
 },
 {
  "as": "6fed7cb3",
  "input": {
   "list_name": "domains",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"50b34065\",\"path\":[\"list_items\"]}')",
   "primary_index": "email"
  },
  "keyword": "action",
  "name": "create_list",
  "number": 4,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "1e14f05d",
  "input": {
   "variables": {
    "data": {
     "formatted_domains": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"50b34065\",\"path\":[\"list_items\"]}')&.where('domain': /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$/)&.pluck('domain')&.compact&.uniq&.smart_join(\"','\")"
    },
    "schema": "[{\"name\":\"formatted_domains\",\"type\":\"string\",\"optional\":true,\"label\":\"Formatted Domains\",\"control_type\":\"text\"}]"
   }
  },
  "keyword": "action",
  "name": "declare_variable",
  "number": 5,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1e14f05d\",\"path\":[\"formatted_domains\"]}').presence",
     "operand": "present",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 6,
  "provider": null,
  "skip": false
 },
 {
  "as": "1eb1d81a",
  "input": {
   "field_list": "Account__c\nDomain__c\nAccount__r$Account.Name\nAccount__r$Account.Active_Subscription__c\nAccount__r$Account.CreatedDate\nAccount__r$Account.Subscription_Start_Date__c\nAccount__r$Account.Current_Plan__c",
   "limit": "2000",
   "query": "Domain__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1e14f05d\",\"path\":[\"formatted_domains\"]}')}')",
   "sobject_name": "Domain__c",
   "table_list": "Account"
  },
  "keyword": "action",
  "name": "search_sobjects_soql",
  "number": 7,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 8,
  "provider": null,
  "skip": false
 },
 {
  "as": "bc4e7d4e",
  "input": {
   "name": "case_statement",
   "type": "string",
   "value": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\"]}').format_map(\"WHEN '%{Domain__c}' THEN '%{Account__c}'\").join(\"\\n\")"
  },
  "keyword": "action",
  "name": "declare_variable",
  "number": 9,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "9efe4d51",
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "UPDATE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"list_name\"]}')}\nSET #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"account\"]}')} = CASE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"domain\"]}')}\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"bc4e7d4e\",\"path\":[\"value\"]}')}\nEND"
  },
  "keyword": "action",
  "name": "query_list",
  "number": 10,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "ca2cc2ef",
  "input": {
   "list_item_schema_json": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"account_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account name\",\"name\":\"account_name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"checkbox\",\"label\":\"Active subscription\",\"render_input\":{},\"parse_output\":{},\"name\":\"active_subscription\",\"type\":\"boolean\",\"optional\":true,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Active subscription\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"active_subscription\",\"type\":\"boolean\",\"optional\":true}},{\"control_type\":\"text\",\"label\":\"Created date\",\"name\":\"created_date\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Domain\",\"name\":\"domain\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"date\",\"label\":\"Subscription start date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"subscription_start_date\",\"type\":\"date_time\",\"optional\":true},{\"control_type\":\"checkbox\",\"label\":\"Isembedded\",\"render_input\":{},\"parse_output\":{},\"name\":\"isembedded\",\"type\":\"boolean\",\"optional\":true,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Isembedded\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"isembedded\",\"type\":\"boolean\",\"optional\":true}}]",
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\"]}')}",
    "account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}",
    "account_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\", {\"path_element_type\": \"current_item\"}, \"Account__r\", \"Name\"]}')}",
    "active_subscription": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"Active_Subscription__c\"]}')",
    "created_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\", {\"path_element_type\": \"current_item\"}, \"Account__r\", \"CreatedDate\"]}')}",
    "domain": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\", {\"path_element_type\": \"current_item\"}, \"Domain__c\"]}')}",
    "isembedded": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"Name\"]}').include?(\" - Embedded\") or (_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"Current_Plan__c\"]}')&.include?(\"ISV/OEM\")).is_true?\ntrue\nelse\nfalse\nend",
    "subscription_start_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1eb1d81a\",\"path\":[\"Domain__c\", {\"path_element_type\": \"current_item\"}, \"Account__r\", \"Subscription_Start_Date__c\"]}')}"
   },
   "name": "Domain _list"
  },
  "keyword": "action",
  "name": "declare_list",
  "number": 11,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "ed56c48d",
  "input": {
   "list_name": "domain_list",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"ca2cc2ef\",\"path\":[\"list_items\"]}')",
   "primary_index": "account_id"
  },
  "keyword": "action",
  "name": "create_list",
  "number": 12,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "ba2c37f4",
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"email\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Email\"},{\"name\":\"domain\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Domain\"},{\"name\":\"account_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"row_number\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Row number\"}]",
   "sql": "WITH duplicate_domain AS (\n    SELECT \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"account_id\"]}')} as domain_account_id,\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"account_name\"]}')} as account_name,\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"isembedded\"]}')} as IsEmbedded,\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"active_subscription\"]}')} as active_subscription,\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"subscription_start_date\"]}')} as subs_start_date,\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"domain\"]}')} as domain,\n        ROW_NUMBER() OVER (\n            PARTITION BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"domain\"]}')}\n            ORDER BY \n          #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"active_subscription\"]}')} DESC,\n          #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"isembedded\"]}')} DESC,\n          #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"columns\", \"subscription_start_date\"]}')} DESC\n        ) AS row_num\n    FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed56c48d\",\"path\":[\"list_name\"]}')}\n)\n\nSELECT\nd.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"email\"]}')},\nd.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"domain\"]}')},\ndl.domain_account_id,\ndl.row_num as rownumber\n\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"list_name\"]}')} d\nLEFT JOIN  duplicate_domain dl\nON dl.domain = d.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"domain\"]}')}\nWHERE dl.row_num = 1"
  },
  "keyword": "action",
  "name": "query_list",
  "number": 13,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "0eea15a1",
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"account_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"account\"]}')}, #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"email\"]}')}\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"list_name\"]}')}\nWHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"account\"]}')} IS NOT NULL AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6fed7cb3\",\"path\":[\"columns\", \"account\"]}')} != ''"
  },
  "keyword": "action",
  "name": "query_list",
  "number": 14,
  "provider": "workato_smart_list",
  "skip": true
 },
 {
  "as": "2534a57a",
  "input": {
   "result": {
    "accounts": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0eea15a1\",\"path\":[\"rows\"]}')}",
     "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0eea15a1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0eea15a1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}"
    }
   }
  },
  "keyword": "action",
  "name": "return_result",
  "number": 15,
  "provider": "workato_recipe_function",
  "skip": true
 },
 {
  "as": "537c1278",
  "input": {
   "result": {
    "accounts": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ba2c37f4\",\"path\":[\"rows\"]}')}",
     "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ba2c37f4\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ba2c37f4\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}"
    }
   }
  },
  "keyword": "action",
  "name": "return_result",
  "number": 16,
  "provider": "workato_recipe_function",
  "skip": false
 }
]
'''
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)


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
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_128165934(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    if raw.get("filter") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} grew a trigger filter: {raw.get('filter')!r}")
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
                "skip": pin["skip"],
            }
            for pin in actions
        ],
    }


def _require_trigger_shape(trigger: dict[str, Any]) -> list[str]:
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly 'parameters'; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger["parameters"]
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != ["emails"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.parameters must carry exactly 'emails'"
        )
    emails = parameters["emails"]
    if not isinstance(emails, list):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.parameters.emails must be a list")
    addresses: list[str] = []
    for idx, entry in enumerate(emails):
        if not isinstance(entry, dict) or sorted(entry.keys()) != ["email"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} emails[{idx}] must be exactly {{'email': ...}}: {entry!r}"
            )
        address = entry["email"]
        if not isinstance(address, str) or "@" not in address:
            raise RuntimeError(
                f"recipe {RECIPE_ID} emails[{idx}].email must contain '@' "
                f"(step 2 derives domain via split('@').last): {address!r}"
            )
        addresses.append(address)
    return addresses


def _require_expect_shape(expect: Any) -> dict[str, Any]:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown}")
    if not tools or tools[-1] != "workato_recipe_function.return_result":
        raise RuntimeError(
            f"recipe {RECIPE_ID} the active step-16 return_result is unconditional and terminal; "
            "expect.tools must end with workato_recipe_function.return_result"
        )
    if expect.get("skipped_steps") != SKIPPED_STEP_NUMBERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.skipped_steps must pin the deactivated raw steps "
            f"{SKIPPED_STEP_NUMBERS} (skip:true in the raw recipe): {expect.get('skipped_steps')!r}"
        )
    if not isinstance(expect.get("trace_tools"), list) or not expect["trace_tools"]:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.trace_tools must pin the full raw trace")
    if not isinstance(expect.get("formatted_domains"), str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.formatted_domains must pin the step-5 value "
            "(may be the empty string on the IF#6-false branches)"
        )
    if not isinstance(expect.get("smart_list_sqls"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.smart_list_sqls must be a list")
    if not isinstance(expect.get("return_accounts"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.return_accounts must be a list")
    for idx, row in enumerate(expect["return_accounts"]):
        if not isinstance(row, dict) or sorted(row.keys()) != ["email", "id"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.return_accounts[{idx}] must be exactly "
                f"{{'email','id'}}: {row!r}"
            )
    return expect


def _require_salesforce_seed(section: Any, email_domains: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    unexpected = sorted(set(section) - SEED_SALESFORCE_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    if section.get("relationship_expansion") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true "
            "(the five Account__r parent pills read the expanded parent)"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(the bare Domain__c IN (...) condition must be evaluated exactly)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare REQUIRED_SCHEMA verbatim"
        )
    records = section.get("records")
    if not isinstance(records, list):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a list")
    accounts: list[dict[str, Any]] = []
    domain_rows: list[dict[str, Any]] = []
    refs_seen: set[str] = set()
    for idx, record in enumerate(records):
        if not isinstance(record, dict) or not isinstance(record.get("fields"), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed record {idx} must carry a fields object")
        sobject = str(record.get("sobject") or "")
        fields = record["fields"]
        if sobject == "Account":
            if domain_rows:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Account seeds must precede Domain__c seeds "
                    "(the lookup token resolves from earlier records)"
                )
            ref = str(record.get("ref") or "").strip()
            if not ref:
                raise RuntimeError(f"recipe {RECIPE_ID} Account seed {idx} requires a ref")
            if ref.upper() in refs_seen:
                raise RuntimeError(f"recipe {RECIPE_ID} duplicate Account ref {ref!r}")
            refs_seen.add(ref.upper())
            allowed = set(ACCOUNT_REQUIRED_FIELDS) | set(ACCOUNT_OPTIONAL_FIELDS)
            unexpected_fields = sorted(set(fields) - allowed)
            if unexpected_fields:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Account seed {ref!r} has unexpected fields: {unexpected_fields}"
                )
            if not str(fields.get("Name") or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} Account seed {ref!r} requires a Name")
            if not isinstance(fields.get("Active_Subscription__c"), bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Account seed {ref!r} must declare Active_Subscription__c "
                    "as an explicit boolean (first ROW_NUMBER ordering key)"
                )
            start = fields.get("Subscription_Start_Date__c")
            if start is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(start)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Account seed {ref!r} Subscription_Start_Date__c must be "
                    f"YYYY-MM-DD (third ROW_NUMBER ordering key): {start!r}"
                )
            accounts.append(record)
        elif sobject == DOMAIN_SOBJECT:
            if sorted(fields.keys()) != ["Account__c", "Domain__c"]:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Domain__c seed {idx} must set exactly "
                    f"Domain__c + Account__c: {sorted(fields.keys())}"
                )
            domain = str(fields.get("Domain__c") or "")
            if not FQDN_RE.fullmatch(domain):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Domain__c seed {idx} value {domain!r} fails the recipe's "
                    "FQDN regex -- it could never be matched (dead seed state)"
                )
            if domain not in email_domains:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Domain__c seed {idx} value {domain!r} is not among the "
                    f"trigger email domains {sorted(email_domains)} (dead seed state)"
                )
            token = str(fields.get("Account__c") or "")
            if not (
                _REF_TOKEN_RE.fullmatch(token)
                and token[1:-3].upper() in refs_seen
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Domain__c seed {idx} Account__c must thread a seeded "
                    f"Account's $<REF>_ID token: {token!r}"
                )
            domain_rows.append(record)
        else:
            raise RuntimeError(f"recipe {RECIPE_ID} unexpected seed sobject {sobject!r}")
    referenced = {str(row["fields"]["Account__c"])[1:-3].upper() for row in domain_rows}
    dead_accounts = sorted(refs_seen - referenced)
    if dead_accounts:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded Accounts never referenced by a Domain__c row "
            f"(dead seed state): {dead_accounts}"
        )
    return accounts, domain_rows


def _require_branch_consistency(
    expect: dict[str, Any],
    domain_rows: list[dict[str, Any]],
) -> None:
    tools = expect["tools"]
    search_items = [
        item for item in expect["tool_expectations"]
        if isinstance(item, dict) and item.get("tool") == "salesforce.search_records"
    ]
    if "salesforce.search_records" in tools:
        if len(search_items) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} exactly one salesforce.search_records expectation is required"
            )
        result_count = search_items[0].get("result_count")
        if result_count != len(domain_rows):
            raise RuntimeError(
                f"recipe {RECIPE_ID} search result_count must pin the seeded Domain__c row count "
                f"({len(domain_rows)}): {result_count!r}"
            )
    else:
        if domain_rows:
            raise RuntimeError(
                f"recipe {RECIPE_ID} variants that never reach step 7 (IF#6 false) must not "
                "seed Domain__c rows (dead seed state)"
            )
    if expect["smart_list_sqls"] and (not domain_rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} smart_list_sqls imply the IF#8 branch ran, which requires "
            "matched Domain__c rows"
        )
    if domain_rows and len(expect["smart_list_sqls"]) != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} matched variants must pin BOTH resolved query_list SQLs "
            "(the step-10 UPDATE..CASE and the step-13 ROW_NUMBER CTE)"
        )
    if not domain_rows and expect["return_accounts"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} with no matched Domain__c rows the return must be accounts: []"
        )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_records = [
        record
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id") and not record.get("read_only")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_records) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_records)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        live_id = str(live_records[idx].get("id") or "")
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
        if ref:
            refs[f"${ref.upper()}_ID"] = live_id
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
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


def seed_128165934(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128165934(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    addresses = _require_trigger_shape(trigger)
    email_domains = {address.split("@")[-1].strip() for address in addresses}
    expect = _require_expect_shape(data.get("expect"))
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["salesforce"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must carry exactly the salesforce section")
    _accounts, domain_rows = _require_salesforce_seed(seed_in["salesforce"], email_domains)
    _require_branch_consistency(expect, domain_rows)
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    _require_no_tokens(trigger, "trigger_input")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "trigger": trigger,
        "expect": resolved_expect,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_128165934(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128165934(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    cleanup_response: dict[str, Any] | None = None
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    try:
        details["initial_snapshot"] = ctx.tools.call("harness.salesforce.snapshot", {})
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = ctx.tools.call("harness.salesforce.snapshot", {})
    finally:
        # Snapshot-then-cleanup: the owned Accounts + Domain__c rows are
        # deleted after verification reads; leftovers fail the run loudly.
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not (cleanup_response or {}).get("ok"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} Salesforce cleanup left live records: {cleanup_response}"
        )
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_128165934(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
