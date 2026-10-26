from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_85944334


RECIPE_ID = "85944334"
SEED_TYPE = "salesforce_recipe_function_partner_account_team_variant"
TRACK = "live_salesforce_recipe_function_partner_account_team"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "3b05163b"
ACCOUNT_SEARCH_AS = "65c57f83"
ATM_SEARCH_AS = "def5d0b7"
ACCUMULATE_AS = "64b09d22"
RETURN_AS = "67cd7068"
ATM_SOBJECT = "AccountTeamMember"
ACCOUNT_TOKEN = "$ACCOUNT_ID"
ATM_QUERY_TEMPLATE = (
    "AccountId = '$ACCOUNT_ID' AND (TeamMemberRole LIKE '%Consultant' "
    "OR TeamMemberRole = 'Partner Manager')"
)


USER_ZIJIE = "005g5000006qRIPAA2"  # Zijie Liu (the CLI/integration user)
USER_ORGFARM = "005g5000006ezEDAAY"  # OrgFarm EPIC
USER_INTEGRATION = "005g5000006f03pAAA"  # Integration User
ALLOWED_ATM_USER_IDS = {USER_ZIJIE, USER_ORGFARM, USER_INTEGRATION}

ALLOWED_ROLES = {
    "Primary Solutions Consultant",
    "Supporting Solutions Consultant",
    "Primary Automation Consultant",
    "Supporting Automation Consultant",
    "Partner Manager",
    "Account Executive",  # excluded by the SOQL fragment
    "Consultant Lead",  # excluded: LIKE '%Consultant' is END-anchored
}

SF_SCHEMA: list[dict[str, str]] = [
    {"sobject": "Account", "field": "Go_Live_Date__c", "sf_type": "Text"},
    {"sobject": "Account", "field": "Partner_Status__c", "sf_type": "Text"},
    {"sobject": "Account", "field": "Region__c", "sf_type": "Text"},
    {"sobject": "Account", "field": "Partner_Tier__c", "sf_type": "Text"},
    {"sobject": "Account", "field": "Billing_Contact_Email__c", "sf_type": "Text"},
    {"sobject": "Account", "field": "Billing_Contact_Name__c", "sf_type": "Text"},
    {"sobject": "Account", "field": "Partner_Referral_Discount__c", "sf_type": "Text"},
]
ACCOUNT_SEED_FIELDS = (
    "Name",
    "Description",
    "Type",
    "BillingStreet",
    "BillingCity",
    "BillingState",
    "BillingPostalCode",
    "BillingCountry",
    "Go_Live_Date__c",
    "Partner_Status__c",
    "Region__c",
    "Partner_Tier__c",
    "Billing_Contact_Email__c",
    "Billing_Contact_Name__c",
    "Partner_Referral_Discount__c",
)
ACCOUNT_READ_FIELDS = ["OwnerId", "LastModifiedById", "RecordTypeId", "BillingAddress"]
ALLOWED_BILLING_STATES = {"Texas", "California", "New York", "Illinois", "Washington"}
REQUIRED_BILLING_COUNTRY = "United States"

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_runtime.accumulate_list_items",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
CASES = (
    "primary_wins_over_supporting",
    "supporting_fallback",
    "pm_only_no_consultants",
    "no_team_at_all",
    "non_consultant_roles_excluded",
)
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "account_list_size",
    "atm_rows",
    "atm_excluded_user_ids",
    "consultant_if_taken",
    "list_item",
    "return_result",
    "steps_absent_from_trace",
)
_REF_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "3b05163b",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"control_type\": \"text\", \"label\": \"ID\", \"name\": \"id\", \"type\": \"string\", \"optional\": false}]",
   "result_schema_json": "[{\"control_type\": \"text\", \"label\": \"Account name\", \"name\": \"accountName\", \"type\": \"string\", \"optional\": false}, {\"control_type\": \"text\", \"label\": \"Account ID\", \"name\": \"accountId\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Description\", \"name\": \"description\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Photo URL\", \"name\": \"photo_url\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"date\", \"label\": \"Go-live date\", \"render_input\": \"date_conversion\", \"parse_output\": \"date_conversion\", \"name\": \"go-live_date\", \"type\": \"date_time\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Last-modified by\", \"name\": \"last-modified_by\", \"type\": \"string\", \"optional\": false}, {\"control_type\": \"text\", \"label\": \"Owner ID\", \"name\": \"owner_id\", \"type\": \"string\", \"optional\": false}, {\"control_type\": \"text\", \"label\": \"Direct presales csr\", \"name\": \"direct_presales_csr\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Direct postsales csr\", \"name\": \"direct_postsales_csr\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Oem presales csr\", \"name\": \"oem_presales_csr\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Oem postsales csr\", \"name\": \"oem_postsales_csr\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Account type\", \"name\": \"account_type\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Partner status\", \"name\": \"partner_status\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Record type ID\", \"name\": \"record_type_id\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Region\", \"name\": \"region\", \"type\": \"string\", \"optional\": true}, {\"name\": \"files\", \"type\": \"array\", \"of\": \"object\", \"label\": \"Files\", \"optional\": true, \"properties\": [{\"control_type\": \"text\", \"label\": \"File ID\", \"name\": \"file_id\", \"type\": \"string\", \"optional\": false}, {\"control_type\": \"text\", \"label\": \"File name\", \"name\": \"file_name\", \"type\": \"string\", \"optional\": false}]}, {\"control_type\": \"text\", \"label\": \"Partner tier\", \"name\": \"partner_tier\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Partner manager\", \"name\": \"partner_manager\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Billing address\", \"name\": \"billing_address\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Billing contact name\", \"name\": \"billing_contact_name\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"text\", \"label\": \"Billing email\", \"name\": \"billing_email\", \"type\": \"string\", \"optional\": true}, {\"control_type\": \"number\", \"label\": \"Partner referral percent\", \"parse_output\": \"float_conversion\", \"name\": \"partner_referral_percent\", \"type\": \"number\", \"optional\": true}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "65c57f83",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3b05163b\",\"path\":[\"parameters\", \"id\"]}')}",
   "field_list": "Id\nName\nDescription\nPhotoUrl\nGo_Live_Date__c\nLastModifiedById\nOwnerId\nPartner_Status__c\nType\nRecordTypeId\nRegion__c\nPartner_Tier__c\nBillingAddress\nBilling_Contact_Email__c\nBilling_Contact_Name__c\nPartner_Referral_Discount__c",
   "limit": "150",
   "sobject_name": "Account"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "def5d0b7",
  "provider": "salesforce",
  "name": "search_sobjects_soql",
  "skip": false,
  "input": {
   "field_list": "UserId\nId\nAccountId\nTeamMemberRole",
   "limit": "150",
   "query": "AccountId = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3b05163b\",\"path\":[\"parameters\", \"id\"]}')}' AND (TeamMemberRole LIKE '%Consultant' OR TeamMemberRole = 'Partner Manager')",
   "sobject_name": "AccountTeamMember"
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
     "lhs": "=_('data.salesforce.def5d0b7.AccountTeamMember').where(TeamMemberRole: /.+Consultant$/).length",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "64b09d22",
  "provider": "workato_list",
  "name": "accumulate_list_items",
  "skip": false,
  "input": {
   "list_item": {
    "data": {
     "automation_consultant": "=_('data.salesforce.def5d0b7.AccountTeamMember').where(TeamMemberRole: 'Primary Automation Consultant').pluck('UserId').first or _('data.salesforce.def5d0b7.AccountTeamMember').where(TeamMemberRole: 'Supporting Automation Consultant').pluck('UserId').first ",
     "solutions_consultant": "=_('data.salesforce.def5d0b7.AccountTeamMember').where(TeamMemberRole: 'Primary Solutions Consultant').pluck('UserId').first or _('data.salesforce.def5d0b7.AccountTeamMember').where(TeamMemberRole: 'Supporting Solutions Consultant').pluck('UserId').first "
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"Solutions Consultant\",\"name\":\"solutions_consultant\",\"type\":\"string\",\"optional\":true},{\"name\":\"automation_consultant\",\"type\":\"string\",\"optional\":true,\"label\":\"Automation Consultant\",\"control_type\":\"text\"}]"
   },
   "name": "CS Reps"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "67cd7068",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "accountId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
    "accountName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
    "account_type": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Type\"]}')}",
    "billing_address": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"BillingAddress\", \"street\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"BillingAddress\", \"city\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"BillingAddress\", \"state\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"BillingAddress\", \"postalCode\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"BillingAddress\", \"country\"]}')}",
    "billing_contact_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Billing_Contact_Name__c\"]}')}",
    "billing_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Billing_Contact_Email__c\"]}')}",
    "description": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Description\"]}')}",
    "direct_postsales_csr": "=if _('data.salesforce.65c57f83.Account.first.RecordTypeId') == '0123l000001ha4wAAA'\nskip\nelse\n_('data.workato_list.64b09d22.list_items.first.automation_consultant')\nend",
    "direct_presales_csr": "=if _('data.salesforce.65c57f83.Account.first.RecordTypeId') == '0123l000001ha4wAAA'\nskip\nelse\n_('data.workato_list.64b09d22.list_items.first.solutions_consultant')\nend",
    "files": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"CombinedAttachments\", \"records\"]}')}",
     "file_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"CombinedAttachments\", \"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
     "file_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"CombinedAttachments\", \"records\", {\"path_element_type\": \"current_item\"}, \"Title\"]}')}"
    },
    "go-live_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Go_Live_Date__c\"]}')}",
    "last-modified_by": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"LastModifiedById\"]}')}",
    "oem_postsales_csr": "=if _('data.salesforce.65c57f83.Account.first.RecordTypeId') == '012o0000000teVpAAI'\nskip\nelse\n_('data.workato_list.64b09d22.list_items.first.automation_consultant')\nend",
    "oem_presales_csr": "=if _('data.salesforce.65c57f83.Account.first.RecordTypeId') == '012o0000000teVpAAI'\nskip\nelse\n_('data.workato_list.64b09d22.list_items.first.solutions_consultant')\nend",
    "owner_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"OwnerId\"]}')}",
    "partner_manager": "=_('data.salesforce.def5d0b7.AccountTeamMember').where(TeamMemberRole: \"Partner Manager\").pluck('UserId').first",
    "partner_referral_percent": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Partner_Referral_Discount__c\"]}')}",
    "partner_status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Partner_Status__c\"]}')}",
    "partner_tier": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Partner_Tier__c\"]}')}",
    "photo_url": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"PhotoUrl\"]}')}",
    "record_type_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"RecordTypeId\"]}')}",
    "region": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"65c57f83\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Region__c\"]}')}"
   }
  }
 }
]"""

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
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_85944334(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
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
    # Semantic pins on the drift-prone pieces of the analysis above.
    atm_pin = next(pin for pin in actual if pin["as"] == ATM_SEARCH_AS)
    query = str(atm_pin["input"].get("query") or "")
    if (
        "AccountId = '#{" not in query
        or "(TeamMemberRole LIKE '%Consultant' OR TeamMemberRole = 'Partner Manager')" not in query
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} ATM WHERE fragment changed -- the strict-SOQL "
            f"paren-OR analysis no longer holds: {query!r}"
        )
    accumulate_pin = next(pin for pin in actual if pin["as"] == ACCUMULATE_AS)
    data = ((accumulate_pin["input"].get("list_item") or {}).get("data") or {})
    for field, primary, supporting in (
        ("solutions_consultant", "Primary Solutions Consultant", "Supporting Solutions Consultant"),
        ("automation_consultant", "Primary Automation Consultant", "Supporting Automation Consultant"),
    ):
        formula = str(data.get(field) or "")
        if primary not in formula or supporting not in formula or " or " not in formula:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {field} or-chain changed: {formula!r}"
            )
    if_pin = next(pin for pin in actual if pin["keyword"] == "if")
    conditions = if_pin["input"].get("conditions") or []
    if (
        len(conditions) != 1
        or "/.+Consultant$/" not in str(conditions[0].get("lhs") or "")
        or str(conditions[0].get("operand") or "") != "greater_than"
        or str(conditions[0].get("rhs") or "") != "0"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF-4 regex condition changed: {conditions!r}")
    return_pin = next(pin for pin in actual if pin["as"] == RETURN_AS)
    result_fields = set((return_pin["input"].get("result") or {}).keys())
    if len(result_fields) != 22 or not {
        "accountId",
        "billing_address",
        "direct_presales_csr",
        "oem_postsales_csr",
        "partner_manager",
        "record_type_id",
        "files",
    } <= result_fields:
        raise RuntimeError(
            f"recipe {RECIPE_ID} return_result field map changed: {sorted(result_fields)}"
        )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "atm_sobject": ATM_SOBJECT,
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


def _soql_fragment_matches(role: str) -> bool:
    # Faithful strict-matcher semantics for the pinned role set: LIKE
    # '%Consultant' is END-anchored ('Consultant Lead' does NOT match --
    # offline-probed against the real OwnedSalesforce strict matcher).
    return role.endswith("Consultant") or role == "Partner Manager"


def _if_regex_matches(role: str) -> bool:
    # /.+Consultant$/ -- at least one char before the anchored literal.
    return re.search(r".+Consultant$", role) is not None


def _first_user(rows: list[dict[str, str]], role: str) -> str | None:
    for row in rows:
        if row["TeamMemberRole"] == role:
            return row["UserId"]
    return None


def _derive_ground_truth(
    account_fields: dict[str, Any],
    seeded_atms: list[dict[str, str]],
) -> dict[str, Any]:
    matched = [row for row in seeded_atms if _soql_fragment_matches(row["TeamMemberRole"])]
    excluded = [row for row in seeded_atms if not _soql_fragment_matches(row["TeamMemberRole"])]
    if_taken = any(_if_regex_matches(row["TeamMemberRole"]) for row in matched)
    list_item: dict[str, Any] | None = None
    if if_taken:
        # The engine's Ruby value-`or`: the Primary chain wins whenever it is
        # non-nil; only a nil Primary falls through to Supporting (fix
        # re-probed 19/19 with the recipe's verbatim formulas this build).
        list_item = {
            "solutions_consultant": (
                _first_user(matched, "Primary Solutions Consultant")
                or _first_user(matched, "Supporting Solutions Consultant")
            ),
            "automation_consultant": (
                _first_user(matched, "Primary Automation Consultant")
                or _first_user(matched, "Supporting Automation Consultant")
            ),
        }
    partner_manager = _first_user(matched, "Partner Manager")
    solutions = list_item["solutions_consultant"] if list_item else None
    automation = list_item["automation_consultant"] if list_item else None
    billing_address = " ".join(
        str(account_fields[key])
        for key in ("BillingStreet", "BillingCity", "BillingState", "BillingPostalCode", "BillingCountry")
    )
    return_result = {
        "accountId": ACCOUNT_TOKEN,
        "accountName": account_fields["Name"],
        "account_type": account_fields["Type"],
        "billing_address": billing_address,
        "billing_contact_name": account_fields["Billing_Contact_Name__c"],
        "billing_email": account_fields["Billing_Contact_Email__c"],
        "description": account_fields["Description"],
        # RT skip-arms are dead (RecordTypeId null) -- always the else arm.
        "direct_postsales_csr": automation,
        "direct_presales_csr": solutions,
        "files": [],
        "go-live_date": account_fields["Go_Live_Date__c"],
        "last-modified_by": "__ANY__",
        "oem_postsales_csr": automation,
        "oem_presales_csr": solutions,
        "owner_id": "__ANY__",
        "partner_manager": partner_manager,
        "partner_referral_percent": account_fields["Partner_Referral_Discount__c"],
        "partner_status": account_fields["Partner_Status__c"],
        "partner_tier": account_fields["Partner_Tier__c"],
        "photo_url": None,
        "record_type_id": None,
        "region": account_fields["Region__c"],
    }
    return {
        "atm_rows": [
            {"UserId": row["UserId"], "TeamMemberRole": row["TeamMemberRole"]} for row in matched
        ],
        "atm_excluded_user_ids": [row["UserId"] for row in excluded],
        "consultant_if_taken": if_taken,
        "list_item": list_item,
        "return_result": return_result,
    }


def _derive_tool_expectations(derived: dict[str, Any]) -> list[dict[str, Any]]:
    result_contains = {
        key: value for key, value in derived["return_result"].items() if key != "files"
    }
    # files [] is exact-pinned by the recipe verifier (subset semantics cannot
    # prove list emptiness); result_contains carries the scalar fields.
    return [
        {
            "tool": "salesforce.search_records",
            "args_contains": {
                "sobject": "Account",
                "limit": "150",
                "filters": [{"field": "Id", "value": ACCOUNT_TOKEN}],
            },
            "result_count": 1,
        },
        {
            "tool": "salesforce.search_records",
            "args_contains": {
                "sobject": ATM_SOBJECT,
                "limit": "150",
                "query": ATM_QUERY_TEMPLATE,
            },
            "result_count": len(derived["atm_rows"]),
        },
        {
            "tool": "workato_recipe_function.return_result",
            "result_contains": result_contains,
        },
    ]


def seed_85944334(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85944334(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    if data.get("job_context") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} never reads job_context (dead seed state)")
    trigger = trigger_input(ctx)
    if trigger != {"parameters": {"id": ACCOUNT_TOKEN}}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly "
            f"{{'parameters': {{'id': {ACCOUNT_TOKEN!r}}}}} (the trigger dereferences "
            f"parameters.id only); got {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["salesforce"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry exactly the salesforce section"
        )
    account_fields, seeded_atms = _require_salesforce_seed(seed_in["salesforce"])
    expect = data.get("expect")
    _require_expect(expect, account_fields, seeded_atms)
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _ref_ids(provision, len(seeded_atms))
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": dict(refs),
        "trigger": _replace_tokens(trigger, refs),
        "expect": _replace_tokens(deepcopy(expect), refs),
    }
    _require_no_tokens(out["trigger"], "trigger")
    _require_no_tokens(out["expect"], "expect")
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_85944334(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85944334(raw)
    live_state = seed.get("salesforce_live")
    if not isinstance(live_state, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not live_state.get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(the paren OR-group of the ATM fragment is silently dropped otherwise)"
        )
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
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
    cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = dict(ctx.tools.call("harness.salesforce.snapshot", {}))
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["final_snapshot"] = dict(ctx.tools.call("harness.salesforce.snapshot", {}))
    finally:
        # Required cleanup: owned Account + AccountTeamMember seeds must not
        # leak into later runs (the recipe itself only reads).
        cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
    details["cleanup_response"] = {"salesforce": cleanup}
    if not (cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup}")
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
    result["verifier"] = verify_85944334(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_salesforce_seed(section: Any) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != [
        "records",
        "schema",
        "strict_soql_conditions",
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly {{'strict_soql_conditions', "
            f"'schema', 'records'}}; got "
            f"{sorted(section.keys()) if isinstance(section, dict) else section!r}"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(the ATM fragment's paren OR-group is strict-only; the legacy matcher "
            "leaks non-matching roles in -- probe-verified)"
        )
    if section.get("schema") != SF_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must be the pinned 7-column "
            "Account FLS re-ensure set"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    account = records[0]
    if (
        not isinstance(account, dict)
        or account.get("sobject") != "Account"
        or str(account.get("ref") or "") != "account"
        or account.get("read_fields") != ACCOUNT_READ_FIELDS
        or not isinstance(account.get("fields"), dict)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} records[0] must be the Account seed "
            f"{{sobject: Account, ref: 'account', read_fields: {ACCOUNT_READ_FIELDS}, "
            f"fields: ...}}; got {account!r}"
        )
    account_fields = account["fields"]
    if sorted(account_fields.keys()) != sorted(ACCOUNT_SEED_FIELDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} Account seed must carry exactly the pinned writable "
            f"columns {sorted(ACCOUNT_SEED_FIELDS)}; got {sorted(account_fields.keys())}"
        )
    for key, value in account_fields.items():
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} Account seed field {key} must be a non-empty "
                f"string (custom columns are TEXT in the bench org); got {value!r}"
            )
    if account_fields["BillingCountry"] != REQUIRED_BILLING_COUNTRY:
        raise RuntimeError(
            f"recipe {RECIPE_ID} BillingCountry must be {REQUIRED_BILLING_COUNTRY!r} "
            "(state/country picklists are org-validated; codes/foreign combos throw "
            "FIELD_INTEGRITY_EXCEPTION -- triage probe)"
        )
    if account_fields["BillingState"] not in ALLOWED_BILLING_STATES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} BillingState must be one of "
            f"{sorted(ALLOWED_BILLING_STATES)}; got {account_fields['BillingState']!r}"
        )
    seeded_atms: list[dict[str, str]] = []
    seen_users: set[str] = set()
    for idx, record in enumerate(records[1:]):
        if (
            not isinstance(record, dict)
            or record.get("sobject") != ATM_SOBJECT
            or not isinstance(record.get("fields"), dict)
            or "read_fields" in record
            or str(record.get("ref") or "") != f"atm_{idx}"
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} records[{idx + 1}] must be an AccountTeamMember "
                f"seed with ref 'atm_{idx}'; got {record!r}"
            )
        fields = record["fields"]
        if sorted(fields.keys()) != ["AccountId", "TeamMemberRole", "UserId"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} ATM seed {idx} must carry exactly AccountId/"
                f"UserId/TeamMemberRole; got {sorted(fields.keys())}"
            )
        if fields["AccountId"] != ACCOUNT_TOKEN:
            raise RuntimeError(
                f"recipe {RECIPE_ID} ATM seed {idx} AccountId must be the "
                f"{ACCOUNT_TOKEN} token"
            )
        user_id = str(fields["UserId"])
        if user_id not in ALLOWED_ATM_USER_IDS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} ATM seed {idx} UserId must be one of the pinned "
                f"active org users {sorted(ALLOWED_ATM_USER_IDS)}; got {user_id!r}"
            )
        if user_id in seen_users:
            raise RuntimeError(
                f"recipe {RECIPE_ID} ATM seeds need DISTINCT users: SF collapses "
                f"same (AccountId, UserId) pairs to one row, last role wins "
                f"(probed live); duplicate {user_id!r}"
            )
        seen_users.add(user_id)
        role = str(fields["TeamMemberRole"])
        if role not in ALLOWED_ROLES:
            raise RuntimeError(
                f"recipe {RECIPE_ID} ATM seed {idx} role must be one of the pinned "
                f"set {sorted(ALLOWED_ROLES)}; got {role!r}"
            )
        seeded_atms.append({"UserId": user_id, "TeamMemberRole": role})
    return account_fields, seeded_atms


def _require_expect(
    expect: Any,
    account_fields: dict[str, Any],
    seeded_atms: list[dict[str, str]],
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("case") not in CASES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must be one of {CASES}")
    derived = _derive_ground_truth(account_fields, seeded_atms)
    for key in ("atm_rows", "atm_excluded_user_ids", "consultant_if_taken", "list_item", "return_result"):
        if expect.get(key) != derived[key]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.{key} contradicts the seed-derived ground "
                f"truth:\nderived: {json.dumps(derived[key], sort_keys=True)}\n"
                f"pinned:  {json.dumps(expect.get(key), sort_keys=True)}"
            )
    if expect.get("account_list_size") != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.account_list_size must be 1")
    if_taken = derived["consultant_if_taken"]
    if expect.get("executed_action_count") != (4 if if_taken else 3):
        raise RuntimeError(
            f"recipe {RECIPE_ID} executed_action_count must be {4 if if_taken else 3} "
            f"(2 searches {'+ accumulate ' if if_taken else ''}+ return_result)"
        )
    if expect.get("tools") != ALLOWED_TOOLS[:1] * 2 + ALLOWED_TOOLS[1:]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be the fixed allowed-call sequence "
            "[search, search, return_result] (accumulate is Workato-internal)"
        )
    if expect.get("steps_absent_from_trace") != ([] if if_taken else [ACCUMULATE_AS]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} steps_absent_from_trace must pin the accumulate step "
            "exactly when IF-4 is false"
        )
    if expect.get("tool_expectations") != _derive_tool_expectations(derived):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must equal the derived "
            f"pins:\n{json.dumps(_derive_tool_expectations(derived), sort_keys=True)}"
        )


def _ref_ids(provision: dict[str, Any], atm_count: int) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    records = ((snapshot.get("salesforce") or {}).get("records") or [])
    owned = [record for record in records if isinstance(record, dict) and not record.get("read_only")]
    accounts = [record for record in owned if record.get("sobject") == "Account"]
    atms = [record for record in owned if record.get("sobject") == ATM_SOBJECT]
    if len(accounts) != 1 or len(atms) != atm_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected exactly 1 Account + {atm_count} ATM "
            f"provisioned records (distinct users prevent SF pair-collapse); got "
            f"{len(accounts)} + {len(atms)}"
        )
    live_id = str(accounts[0].get("id") or "")
    if not re.fullmatch(r"[a-zA-Z0-9]{15,18}", live_id):
        raise RuntimeError(f"recipe {RECIPE_ID} provisioned Account id looks invalid: {live_id!r}")
    return {ACCOUNT_TOKEN: live_id}


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


def _require_no_tokens(value: dict[str, Any], label: str) -> None:
    leftover = _REF_TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")
