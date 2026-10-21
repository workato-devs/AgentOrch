from __future__ import annotations

import datetime
import json
import os
import random
import re
import ssl
import string
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import ENV_FILE, ROOT


API_VERSION = "v59.0"
_CLIENT: SalesforceClient | None = None
SALESFORCE_FIELD_MAP: dict[tuple[str, str], str] = {
    ("Event", "Type"): "Benchmark_Type__c",
    # Task.Type is absent in modern dev-edition orgs (only TaskSubtype
    # exists); reuse the shared Activity stand-in field (batch 08,
    # 118290293/103988481/125214871).
    ("Task", "Type"): "Benchmark_Type__c",
    # OpportunityTeamMember stand-in (batch 05, 124203347): standard fields
    # map to Text custom fields on OpportunityTeamMember__c.
    ("OpportunityTeamMember__c", "OpportunityId"): "OpportunityId__c",
    ("OpportunityTeamMember__c", "UserId"): "UserId__c",
    ("OpportunityTeamMember__c", "TeamMemberRole"): "TeamMemberRole__c",
    # User.Email parent traversal on the stand-in has no relationship to walk
    # (UserId__c is Text); it flattens to a Text column exactly like the
    # QuoteLine__c dotted paths below. Deployed 2026-07-09 (batch 09,
    # 107245441/108350603/108350606/131771938).
    ("OpportunityTeamMember__c", "User.Email"): "User_Email__c",
    # OpportunityFieldHistory audit-object stand-in (batch 08, 87410086).
    ("OpportunityFieldHistory__c", "Field"): "Field__c",
    ("OpportunityFieldHistory__c", "OldValue"): "OldValue__c",
    ("OpportunityFieldHistory__c", "NewValue"): "NewValue__c",
    ("OpportunityFieldHistory__c", "OpportunityId"): "OpportunityId__c",
    # Gong managed fields on the benchmark-owned stand-in (batch 05, 123859779).
    ("Gong_Call__c", "Gong__Primary_Account__c"): "Primary_Account__c",
    ("Gong_Call__c", "Gong__Call_Brief__c"): "Call_Brief__c",
    ("Gong_Call__c", "Gong__Call_Highlights_Next_Steps__c"): "Call_Highlights_Next_Steps__c",
    ("Gong_Call__c", "Gong__Call_ID__c"): "Call_ID__c",
    ("Proj__c", "pse__Is_Template__c"): "Is_Template__c",
    # Bizible (bizible2__) managed fields on the benchmark-owned stand-ins
    # deployed 2026-07-07 for 118427850.
    ("Bizible_Person__c", "bizible2__Contact__c"): "Contact__c",
    ("Bizible_Person__c", "bizible2__Lead__c"): "Lead__c",
    ("Bizible_Person__c", "bizible2__UniqueId__c"): "UniqueId__c",
    ("Bizible_Touchpoint__c", "bizible2__Bizible_Person__c"): "Bizible_Person__c",
    ("Bizible_Touchpoint__c", "bizible2__Marketing_Channel__c"): "Marketing_Channel__c",
    ("Bizible_Touchpoint__c", "bizible2__Marketing_Channel_Path__c"): "Marketing_Channel_Path__c",
    ("Bizible_Touchpoint__c", "bizible2__Landing_Page__c"): "Landing_Page__c",
    ("Bizible_Touchpoint__c", "bizible2__Landing_Page_Raw__c"): "Landing_Page_Raw__c",
    ("Bizible_Touchpoint__c", "bizible2__Form_URL__c"): "Form_URL__c",
    ("Bizible_Touchpoint__c", "bizible2__Form_URL_Raw__c"): "Form_URL_Raw__c",
    ("Bizible_Touchpoint__c", "bizible2__Ad_Destination_URL__c"): "Ad_Destination_URL__c",
    ("Bizible_Touchpoint__c", "bizible2__Ad_Campaign_Name__c"): "Ad_Campaign_Name__c",
    ("Bizible_Touchpoint__c", "bizible2__Referrer_Page__c"): "Referrer_Page__c",
    ("Bizible_Touchpoint__c", "bizible2__Touchpoint_Date__c"): "Touchpoint_Date__c",
    # CPQ (SBQQ__) managed fields on the QuoteLine__c stand-in deployed
    # 2026-07-07 for 117385101. Parent dotted paths are flattened columns.
    ("QuoteLine__c", "SBQQ__EffectiveStartDate__c"): "EffectiveStartDate__c",
    ("QuoteLine__c", "SBQQ__Quote__r.SBQQ__Primary__c"): "Quote_Primary__c",
    ("QuoteLine__c", "SBQQ__Quote__r.SBQQ__Ordered__c"): "Quote_Ordered__c",
    ("QuoteLine__c", "SBQQ__Quote__r.SBQQ__Opportunity2__c"): "Quote_Opportunity2__c",
    ("QuoteLine__c", "SBQQ__Product__r.IsActive"): "Product_IsActive__c",
    ("QuoteLine__c", "SBQQ__Product__r.Product_Sub_Family__c"): "Product_Sub_Family__c",
    ("QuoteLine__c", "SBQQ__Product__r.Family"): "Product_Family__c",
    # Skilljar (skilljar__) managed fields on the Student__c stand-in.
    ("Student__c", "skilljar__Email__c"): "Email__c",
    ("Student__c", "skilljar__First_Name__c"): "First_Name__c",
    ("Student__c", "skilljar__Last_Name__c"): "Last_Name__c",
    ("Student__c", "skilljar__Lead__c"): "Lead__c",
    ("Student__c", "skilljar__Contact__c"): "Contact__c",
}
# PSA managed-package (pse__) logical objects map to benchmark-owned physical
# custom objects provisioned once via mdapi deploy (2026-07-06); the package
# itself cannot be installed in the benchmark org. Bizible stand-ins deployed
# 2026-07-07 (batch-02 wave 3) the same way.
SALESFORCE_SOBJECT_MAP: dict[str, str] = {
    "vh__Hero_Activity__c": "Hero_Activity__c",
    "pse__Proj__c": "Proj__c",
    "pse__Grp__c": "Grp__c",
    "pse__Practice__c": "Practice__c",
    "pse__Region__c": "Region__c",
    "pse__Time_Period__c": "Time_Period__c",
    "bizible2__Bizible_Person__c": "Bizible_Person__c",
    "bizible2__Bizible_Touchpoint__c": "Bizible_Touchpoint__c",
    # Skilljar stand-in deployed 2026-07-07 (batch 03, 88451624).
    "skilljar__Student__c": "Student__c",
    # CPQ quote-line stand-in deployed 2026-07-07 (batch 04, 117385101).
    "SBQQ__QuoteLine__c": "QuoteLine__c",
    # Team Selling is disabled org-wide (an org toggle we must not flip);
    # the standard sobject 404s live. Stand-in pre-exists (batch 05, 124203347);
    # its fields provision via ensure_custom_field schema-in-seed.
    "OpportunityTeamMember": "OpportunityTeamMember__c",
    # Gong managed-package stand-in deployed 2026-07-07 (batch 05, 123859779).
    "Gong__Gong_Call__c": "Gong_Call__c",
    # Audit object (unseedable standard); stand-in deployed 2026-07-08
    # (batch 08, 87410086).
    "OpportunityFieldHistory": "OpportunityFieldHistory__c",
}
# Workato_Task__c (batch 09, 108350603/108350604/131771938) is a benchmark-owned
# custom object deployed 2026-07-09 (Activity_Type__c/Status__c/Opportunity__c
# Text fields + FLS). Recipes reference the physical __c name directly in SOQL,
# so it needs no SOBJECT_MAP entry — the object only has to exist live.

# SELECT-list child-relationship subqueries (batch 09): (parent sobject as
# queried, child relationship name) -> (physical child sobject holding the
# owned rows, child-side FK column joined to the parent row Id). Stand-in
# custom objects carry no real relationship metadata, so the join is declared
# here; a query naming an UNMAPPED child relationship RAISES (no-fallback).
SALESFORCE_CHILD_RELATIONSHIP_MAP: dict[tuple[str, str], tuple[str, str]] = {
    # Team Selling is org-disabled (see SOBJECT_MAP above): OpportunityTeamMembers
    # child rows live on the OpportunityTeamMember__c stand-in, whose FK is the
    # OpportunityId__c Text column (FIELD_MAP above).
    ("Opportunity", "OpportunityTeamMembers"): ("OpportunityTeamMember__c", "OpportunityId__c"),
}


class SalesforceError(Exception):
    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self.body = body
        super().__init__(f"SF {status}: {body}")


class SalesforceClient:
    @staticmethod
    def _soql_escape_static(value: str) -> str:
        return str(value).replace("\\", "\\\\").replace("'", "\\'")

    def __init__(self, org_alias: str | None = None) -> None:
        self.org_alias = org_alias
        self.api = API_VERSION
        self.access_token: str | None = None
        self.instance_url: str | None = None
        self.username: str | None = None
        self.user_id: str | None = None
        ca_file = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
        self.ssl_context = (
            ssl.create_default_context(cafile=ca_file)
            if ca_file
            else ssl.create_default_context()
        )
        self._field_cache: dict[str, set[str]] = {}
        self._field_meta_cache: dict[str, dict[str, dict[str, Any]]] = {}
        self._required_cache: dict[str, dict[str, Any]] = {}

    @classmethod
    def from_cli(cls, org_alias: str | None = None) -> "SalesforceClient":
        client = cls(org_alias)
        client._cli_auth()
        return client

    def _cli_auth(self) -> None:
        display_cmd = ["sf", "org", "display", "--json"]
        if self.org_alias:
            display_cmd += ["--target-org", self.org_alias]
        display = subprocess.run(display_cmd, capture_output=True, text=True)
        try:
            result = json.loads(display.stdout)["result"]
        except Exception as exc:
            raise SalesforceError(
                0,
                "sf CLI org display failed: "
                + (display.stderr or display.stdout or str(exc))[:300],
            ) from exc
        self.instance_url = result["instanceUrl"]
        self.username = result.get("username")
        self.user_id = result.get("userId")

        token_cmd = ["sf", "org", "auth", "show-access-token", "--json"]
        if self.org_alias:
            token_cmd += ["--target-org", self.org_alias]
        token_out = subprocess.run(token_cmd, capture_output=True, text=True)
        try:
            self.access_token = json.loads(token_out.stdout)["result"]["accessToken"]
        except Exception as exc:
            raise SalesforceError(
                0,
                "sf CLI show-access-token failed: "
                + (token_out.stderr or token_out.stdout or str(exc))[:300],
            ) from exc

    def _raw(
        self,
        method: str,
        url: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        tries: int = 4,
    ) -> tuple[int, Any]:
        last: Exception | None = None
        for attempt in range(tries):
            request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
            try:
                with urllib.request.urlopen(request, context=self.ssl_context, timeout=60) as response:
                    raw = response.read().decode()
                    return response.status, (json.loads(raw) if raw else {})
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode()
                try:
                    body = json.loads(raw)
                except Exception:
                    body = raw
                return exc.code, body
            except (urllib.error.URLError, OSError) as exc:
                last = exc
                time.sleep(1.0 * (attempt + 1))
        raise last or RuntimeError("Salesforce request failed")

    def _req(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        if not self.access_token or not self.instance_url:
            self._cli_auth()
        url = str(self.instance_url) + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "Authorization": "Bearer " + str(self.access_token),
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        data = json.dumps(body).encode() if body is not None else None
        status, response = self._raw(method, url, data=data, headers=headers)
        if status == 401:
            self._cli_auth()
            headers["Authorization"] = "Bearer " + str(self.access_token)
            status, response = self._raw(method, url, data=data, headers=headers)
        if status >= 400:
            raise SalesforceError(status, response)
        return response

    def _data(self, path: str) -> str:
        return f"/services/data/{self.api}{path}"

    def describe(self, sobject: str) -> dict[str, Any]:
        return self._req("GET", self._data(f"/sobjects/{sobject}/describe"))

    def get(self, sobject: str, record_id: str, fields: list[str] | None = None) -> dict[str, Any]:
        params = {"fields": ",".join(fields)} if fields else None
        return self._req("GET", self._data(f"/sobjects/{sobject}/{record_id}"), params=params)

    def create(self, sobject: str, data: dict[str, Any]) -> dict[str, Any]:
        # Benchmark seeds intentionally create similar-looking records across
        # runs; org duplicate rules (allowSave=true) must not block them.
        return self._req(
            "POST",
            self._data(f"/sobjects/{sobject}"),
            body=data,
            extra_headers={"Sforce-Duplicate-Rule-Header": "allowSave=true"},
        )

    def update(self, sobject: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self._req("PATCH", self._data(f"/sobjects/{sobject}/{record_id}"), body=data)
        return {"id": record_id, "success": True}

    def delete(self, sobject: str, record_id: str) -> dict[str, Any]:
        self._req("DELETE", self._data(f"/sobjects/{sobject}/{record_id}"))
        return {"id": record_id, "success": True}

    def query(self, soql: str) -> dict[str, Any]:
        return self._req("GET", self._data("/query"), params={"q": soql})


def _client() -> SalesforceClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = SalesforceClient.from_cli(_sf_org())
    return _CLIENT


def _sf_org() -> str:
    values = _load_env_file()
    org = (
        os.environ.get("SF_ORG")
        or os.environ.get("SF_TARGET_ORG")
        or values.get("SF_ORG")
        or values.get("SF_TARGET_ORG")
    )
    if not org:
        raise RuntimeError("missing SF_ORG (set it in benchmark/.env or the environment)")
    return org


def _load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text().splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _new_run_id() -> str:
    today = datetime.date.today()
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"bench_{today:%Y%m%d}_{rand}"


def _same_salesforce_value(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return str(actual).lower() == str(expected).lower()
    return str(actual) == str(expected)


# Tooling CustomField `type` -> the `type` string a REST describe reports for that
# field. Used to prime the describe cache after a field is created so create/search
# immediately treat the new field as physical (avoids Salesforce metadata
# describe-propagation lag).
_SOAP_FIELD_TYPE = {
    "Text": "string",
    "TextArea": "textarea",
    "LongTextArea": "textarea",
    "Number": "double",
    "Currency": "currency",
    "Percent": "percent",
    "Checkbox": "boolean",
    "Date": "date",
    "DateTime": "datetime",
    "Url": "url",
    "Email": "email",
    "Phone": "phone",
}


def _custom_field_metadata(field: str, sf_type: str) -> dict[str, Any]:
    """Tooling-API CustomField Metadata for a benchmark-declared custom field."""
    sf_type = sf_type or "Text"
    if sf_type not in _SOAP_FIELD_TYPE:
        raise RuntimeError(f"unsupported Salesforce custom field type: {sf_type}")
    label = field[:-3].replace("_", " ").strip()[:40] or "Bench Field"
    meta: dict[str, Any] = {"label": label, "type": sf_type}
    if sf_type == "Text":
        meta["length"] = 255
    elif sf_type == "LongTextArea":
        meta["length"] = 32768
        meta["visibleLines"] = 3
    elif sf_type in {"Number", "Currency", "Percent"}:
        meta["precision"] = 18
        meta["scale"] = 2
    elif sf_type == "Checkbox":
        meta["defaultValue"] = False
    return meta


class OwnedSalesforce:
    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.client = _client()
        self.run_id = str((state or {}).get("run_id") or _new_run_id())
        self.owned: dict[str, tuple[str, list[str], str]] = {}
        self.read_only_records: list[dict[str, Any]] = []
        # Opt-in per-recipe behaviors (seed flags; carried through state so the
        # run process sees them). Both default OFF to keep the read-back shape
        # and match semantics of previously verified recipes byte-stable.
        self.expand_relationships = bool((state or {}).get("expand_relationships"))
        self.strict_soql = bool((state or {}).get("strict_soql_conditions"))
        # seed salesforce.user_id_map (resolved at provision time, carried
        # through state as literal live ids so the run process applies the
        # same table). See _load_user_id_map for semantics.
        self.user_id_map: dict[str, str] = {
            str(key): str(value)
            for key, value in ((state or {}).get("user_id_map") or {}).items()
        }
        if state:
            for row in state.get("owned_records") or []:
                self.owned[str(row["id"])] = (
                    str(row["physical_sobject"]),
                    list(row.get("field_names") or []),
                    str(row["logical_sobject"]),
                )
            self.read_only_records = [
                dict(row)
                for row in state.get("read_only_records") or []
                if isinstance(row, dict)
            ]

    def provision(self, section: dict[str, Any]) -> None:
        if section.get("relationship_expansion"):
            self.expand_relationships = True
        if section.get("strict_soql_conditions"):
            self.strict_soql = True
        self._load_user_id_map(section)
        self._provision_schema(section)
        refs: dict[str, str] = self._stable_refs(section)
        current_user = section.get("current_user")
        if isinstance(current_user, dict):
            current = self.add_current_user(
                str(current_user.get("sobject") or "User"),
                current_user.get("read_fields"),
            )
            fields = current.get("fields") if isinstance(current.get("fields"), dict) else {}
            refs["$USER_ID"] = str(current.get("id") or "")
            refs["$CURRENT_USER_ID"] = str(current.get("id") or "")
            refs["$USER_NAME"] = str(fields.get("Name") or "")
            refs["$CURRENT_USER_NAME"] = str(fields.get("Name") or "")
            refs["$USER_EMAIL"] = str(fields.get("Email") or fields.get("Username") or "")
            refs["$CURRENT_USER_EMAIL"] = str(fields.get("Email") or fields.get("Username") or "")
        for spec in section.get("existing_users") or []:
            # Declare PRE-EXISTING org users (e.g. the never-login Integration
            # User) as read-only records so recipe User SOQL can match them.
            # Live SELECT, fail-fast on no match — never fabricated.
            if not isinstance(spec, dict) or not str(spec.get("where") or "").strip():
                raise RuntimeError("salesforce.existing_users entries require a where clause")
            self.add_existing_user(
                str(spec.get("where")),
                str(spec.get("sobject") or "User"),
                spec.get("read_fields"),
            )
        for record in section.get("records") or []:
            if not isinstance(record, dict):
                continue
            logical_sobject = str(record.get("sobject") or "Task")
            created = self.create_record(
                logical_sobject,
                self._replace_seed_refs(dict(record.get("fields") or {}), refs),
            )
            record_id = str(created.get("id") or "")
            if record_id:
                read_fields = [str(f) for f in record.get("read_fields") or []]
                if read_fields:
                    # Explicitly declared DERIVED columns (e.g. ServiceContract
                    # .Status, computed from the term dates) join the live
                    # read-back set without ever being written.
                    physical, field_names, owned_logical = self.owned[record_id]
                    self.owned[record_id] = (
                        physical,
                        list(dict.fromkeys([*field_names, *read_fields])),
                        owned_logical,
                    )
                refs.setdefault(f"${logical_sobject.upper()}_ID", record_id)
                ref = str(record.get("ref") or "").strip()
                if ref:
                    refs[f"${ref.upper()}_ID"] = record_id

    def _load_user_id_map(self, section: dict[str, Any]) -> None:
        """seed salesforce.user_id_map — the Salesforce twin of the
        slack_channel_map literal-mapping precedent. Raw recipes can hardcode
        SOURCE-ORG user ids (e.g. 62905310 #25's OwnerId 0051N000007CXgtQAG)
        that cannot exist in the benchmark org; a live write would fail
        INVALID_CROSS_REFERENCE_KEY, making the action live-unseedable. A
        variant's seed declares {"<foreign-id>": "$CURRENT_USER_ID" |
        "$USER_ID" | "<literal-live-id>"} and every Salesforce write boundary
        (create/update/upsert field values) redirects EXACTLY the declared
        ids to their resolved live targets. Only DECLARED ids are mapped —
        any undeclared foreign id still reaches live Salesforce and surfaces
        its genuine error (fail-fast preserved). Trace/groundtruth args keep
        the raw recipe's literal (the mapping happens BELOW the tool-call
        boundary); only the live materialization is redirected. Tokens
        resolve against the harness's current-user machinery (sf CLI
        userId), never a fabricated value."""
        raw_map = section.get("user_id_map")
        if raw_map is None:
            return
        if not isinstance(raw_map, dict) or not raw_map:
            raise RuntimeError("salesforce seed user_id_map must be a non-empty object")
        resolved: dict[str, str] = {}
        for foreign, target in raw_map.items():
            foreign = str(foreign)
            if not self._looks_sf_id(foreign):
                raise RuntimeError(
                    f"salesforce user_id_map key must be a Salesforce-id-shaped value: {foreign!r}"
                )
            target_text = str(target or "")
            if target_text in ("$CURRENT_USER_ID", "$USER_ID"):
                live_id = self._current_user_id()
            elif self._looks_sf_id(target_text):
                live_id = target_text
            else:
                raise RuntimeError(
                    f"salesforce user_id_map value for {foreign!r} must be "
                    f"$CURRENT_USER_ID/$USER_ID or a literal live Salesforce id: {target!r}"
                )
            resolved[foreign] = live_id
        chained = sorted(set(resolved) & set(resolved.values()))
        if chained:
            # A target that is itself a mapped key would make the mapping
            # order-dependent (and double-application non-idempotent).
            raise RuntimeError(
                f"salesforce user_id_map targets may not themselves be mapped foreign ids: {chained}"
            )
        self.user_id_map = resolved

    def _current_user_id(self) -> str:
        if self.client.user_id:
            return str(self.client.user_id)
        # `sf org display` omits userId for some auth types; the OAuth
        # userinfo endpoint is authoritative for the running user (the same
        # machinery _grant_fls uses).
        user_id = self.client._req("GET", "/services/oauth2/userinfo").get("user_id")
        if not user_id:
            raise RuntimeError(
                "Salesforce did not expose a current user id (needed by user_id_map)"
            )
        self.client.user_id = str(user_id)
        return str(user_id)

    def _map_user_ids(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Redirect DECLARED foreign user ids in write field values (exact
        full-value string match only — ids embedded in longer text are left
        untouched, as are all undeclared values)."""
        if not self.user_id_map:
            return fields
        return {
            key: self.user_id_map.get(value, value) if isinstance(value, str) else value
            for key, value in fields.items()
        }

    def _provision_schema(self, section: dict[str, Any]) -> None:
        """Create benchmark-declared custom fields live before seeding records, so a
        recipe that reads/writes a custom field runs against a real org field rather
        than a fabricated logical-only value. Schema is created once and persists
        across runs (it is schema, not data, so cleanup never removes it). Missing
        custom OBJECTS and managed-package (namespaced) fields are NOT provisioned
        here; those fail fast so the recipe is recorded as needing that package."""
        schema = section.get("schema")
        if schema in (None, []):
            return
        if not isinstance(schema, list):
            raise RuntimeError("salesforce seed schema must be a list")
        for fdef in schema:
            if not isinstance(fdef, dict):
                raise RuntimeError("salesforce schema entry must be an object")
            sobject = self._physical_sobject_name(str(fdef.get("sobject") or ""))
            field = str(fdef.get("field") or "")
            if not sobject or not field:
                raise RuntimeError("salesforce schema entry requires sobject and field")
            self.ensure_custom_field(sobject, field, str(fdef.get("sf_type") or "Text"))

    def _tooling(self, method: str, sobj: str, body: dict[str, Any] | None = None, idv: str = "") -> Any:
        path = f"/services/data/{self.client.api}/tooling/sobjects/{sobj}"
        if idv:
            path += f"/{idv}"
        return self.client._req(method, path, body=body)

    def ensure_custom_field(self, sobject: str, field: str, sf_type: str = "Text") -> None:
        field = str(field)
        if not field.endswith("__c"):
            return  # standard field: assume it exists in the org
        full = f"{sobject}.{field}"
        # Activity has no REST describe endpoint; its custom fields surface on
        # the concrete Task/Event sobjects, so check existence there.
        describe_sobject = "Task" if sobject == "Activity" else sobject
        if field in self._field_names(describe_sobject):
            self._grant_fls(sobject, full)
            return
        if self._tooling_field_exists(describe_sobject, field):
            # mdapi-deployed field with no FLS yet: invisible to describe until
            # the running user's profile gets access. Grant FLS and refresh the
            # caches instead of attempting a (possibly Lookup) re-create.
            self._grant_fls(sobject, full)
            self._register_field_in_caches(sobject, field, sf_type)
            return
        try:
            self._tooling(
                "POST",
                "CustomField",
                {"FullName": full, "Metadata": _custom_field_metadata(field, sf_type)},
            )
        except Exception as exc:  # idempotent: tolerate only an already-created field
            if "DUPLICATE" not in repr(exc).upper():
                raise
        self._grant_fls(sobject, full)
        self._register_field_in_caches(sobject, field, sf_type)

    def _tooling_field_exists(self, sobject: str, field: str) -> bool:
        developer_name = field[:-3] if field.endswith("__c") else field
        query = (
            "SELECT QualifiedApiName FROM FieldDefinition "
            f"WHERE EntityDefinition.QualifiedApiName = '{self._soql_escape(sobject)}' "
            f"AND QualifiedApiName = '{self._soql_escape(field)}'"
        )
        path = f"/services/data/{self.client.api}/tooling/query?q={urllib.parse.quote(query)}"
        try:
            result = self.client._req("GET", path)
        except SalesforceError:
            return False
        records = result.get("records") if isinstance(result, dict) else []
        if records:
            return True
        # FieldDefinition needs both filters; some API versions reject the
        # compound form — fall back to CustomField by developer name.
        query2 = (
            "SELECT Id, TableEnumOrId FROM CustomField "
            f"WHERE DeveloperName = '{self._soql_escape(developer_name)}'"
        )
        path2 = f"/services/data/{self.client.api}/tooling/query?q={urllib.parse.quote(query2)}"
        try:
            result2 = self.client._req("GET", path2)
        except SalesforceError:
            return False
        rows = result2.get("records") if isinstance(result2, dict) else []
        if not rows:
            return False
        tables = {str(row.get("TableEnumOrId") or "") for row in rows if isinstance(row, dict)}
        if sobject in tables:
            return True
        # Custom sobjects appear as CustomObject ids in TableEnumOrId — match
        # THIS sobject's id exactly (a same-named field on another custom
        # object must not count as existing here).
        if sobject.endswith("__c"):
            obj_query = (
                "SELECT Id FROM CustomObject "
                f"WHERE DeveloperName = '{self._soql_escape(sobject[:-3])}'"
            )
            obj_path = f"/services/data/{self.client.api}/tooling/query?q={urllib.parse.quote(obj_query)}"
            try:
                obj_result = self.client._req("GET", obj_path)
            except SalesforceError:
                return False
            obj_rows = obj_result.get("records") if isinstance(obj_result, dict) else []
            obj_ids = {str(row.get("Id") or "") for row in obj_rows if isinstance(row, dict)}
            # Tooling ids may differ in the 15/18-char suffix; compare prefixes.
            return any(t[:15] == o[:15] for t in tables for o in obj_ids if t and o)
        return False

    def _register_field_in_caches(self, sobject: str, field: str, sf_type: str) -> None:
        # keep the describe caches correct so create/search treat the field as live
        cache_sobjects = ("Task", "Event") if sobject == "Activity" else (sobject,)
        for cache_sobject in cache_sobjects:
            self._field_names(cache_sobject).add(field)
            self._field_meta(cache_sobject, field)  # force a full describe load into the cache
            self.client._field_meta_cache.setdefault(cache_sobject, {})[field] = {
                "name": field,
                "createable": True,
                "updateable": True,
                "type": _SOAP_FIELD_TYPE.get(sf_type, "string"),
            }

    def _grant_fls(self, sobject: str, full_field: str) -> None:
        """Grant Read+Edit on the field to the running user's profile permission set
        so reads/writes do not silently fail (a fresh custom field has no FLS)."""
        uid = self.client._req("GET", "/services/oauth2/userinfo").get("user_id")
        rows = self.client.query(
            "SELECT Id FROM PermissionSet WHERE IsOwnedByProfile = true "
            "AND ProfileId IN (SELECT ProfileId FROM User WHERE Id = '%s')" % uid
        ).get("records", [])
        if not rows:
            raise RuntimeError("no profile permission set found to grant field-level security")
        # FieldPermissions rejects SobjectType "Activity"; Activity custom fields
        # are granted per concrete sobject (Task and Event).
        field_name = full_field.split(".")[-1]
        targets = [("Task", f"Task.{field_name}"), ("Event", f"Event.{field_name}")] if sobject == "Activity" else [(sobject, full_field)]
        for target_sobject, target_field in targets:
            try:
                self.client.create(
                    "FieldPermissions",
                    {
                        "ParentId": rows[0]["Id"],
                        "SObjectType": target_sobject,
                        "Field": target_field,
                        "PermissionsRead": True,
                        "PermissionsEdit": True,
                    },
                )
            except SalesforceError as exc:
                if "DUPLICATE" in str(exc.body).upper():
                    continue
                raise

    _RELATED_NAME_LOOKUPS = {
        "RecordTypeId": ("RecordType.Name", "RecordType"),
        "Product2Id": ("Product2.Name", "Product2"),
    }

    _STANDARD_PARENT_RELATIONSHIPS = {
        "AccountId": ("Account", "Account"),
        "CampaignId": ("Campaign", "Campaign"),
        "ContactId": ("Contact", "Contact"),
        "LeadId": ("Lead", "Lead"),
        "OpportunityId": ("Opportunity", "Opportunity"),
        "OwnerId": ("Owner", "User"),
        "CreatedById": ("CreatedBy", "User"),
        "LastModifiedById": ("LastModifiedBy", "User"),
    }

    def _augment_relationships(self, fields: dict[str, Any]) -> None:
        """Derive relationship-path values from live org data so SOQL paths like
        RecordType.Name / Product2.Name evaluate against real ids (never
        fabricated)."""
        for id_field, (path, related_sobject) in self._RELATED_NAME_LOOKUPS.items():
            related_id = fields.get(id_field)
            if related_id and path not in fields:
                name = self._related_name(related_sobject, str(related_id))
                fields[path] = name
                # Nested form too: datapill paths walk ["Product2", "Name"].
                rel_key = path.split(".")[0]
                if not isinstance(fields.get(rel_key), dict):
                    fields[rel_key] = {"Name": name}
        if self.expand_relationships:
            self._expand_parent_relationships(fields)

    def _expand_parent_relationships(self, fields: dict[str, Any]) -> None:
        """Opt-in (seed salesforce.relationship_expansion): attach each parent
        record's live fields one level deep under the relationship name, so
        pill/SOQL paths like Contact.Account.AnnualRevenue, CampaignId→
        Campaign.Name and Account__c→Account__r.Name resolve against real
        read-back data."""
        for key in list(fields):
            value = fields.get(key)
            if not (isinstance(value, str) and self._looks_sf_id(value)):
                continue
            if key in self._STANDARD_PARENT_RELATIONSHIPS:
                rel_name, rel_sobject = self._STANDARD_PARENT_RELATIONSHIPS[key]
            elif key.endswith("__c"):
                rel_name, rel_sobject = key[:-3] + "__r", None
            else:
                continue
            if isinstance(fields.get(rel_name), dict):
                continue
            related = self._related_record_fields(str(value), rel_sobject)
            if related is None:
                continue
            fields[rel_name] = related
            if rel_name.endswith("__r"):
                # Pills sometimes walk the bare name (Account__c → Account.Name).
                bare = rel_name[:-3]
                if bare not in fields:
                    fields[bare] = related
                # Stand-in parity: a mapped standard-FK column (e.g. the
                # OpportunityTeamMember__c stand-in's OpportunityId__c) must
                # ALSO expose the STANDARD relationship name (Opportunity.*),
                # exactly as the real sobject would — strict-SOQL WHERE leaves
                # and result pills traverse the raw recipe's relationship name.
                std = self._STANDARD_PARENT_RELATIONSHIPS.get(bare)
                if std and not isinstance(fields.get(std[0]), dict):
                    fields[std[0]] = related

    def _related_record_fields(self, record_id: str, sobject_hint: str | None) -> dict[str, Any] | None:
        cache = getattr(self.client, "_related_fields_cache", None)
        if cache is None:
            cache = {}
            self.client._related_fields_cache = cache
        if record_id in cache:
            row = cache[record_id]
            return dict(row) if isinstance(row, dict) else None
        if record_id in self.owned:
            physical, field_names, _logical = self.owned[record_id]
            raw = self._read(
                physical,
                record_id,
                list(dict.fromkeys([*field_names, *self._readback_extra_fields(physical)])),
            )
            if raw is None:
                cache[record_id] = None
                return None
            related = {k: v for k, v in raw.items() if k != "attributes" and not isinstance(v, (dict, list))}
            self._logical_aliases(physical, related)
        elif sobject_hint:
            try:
                raw = self.client.get(sobject_hint, record_id, fields=["Id", "Name"])
            except SalesforceError as exc:
                if exc.status == 404:
                    cache[record_id] = None
                    return None
                raise
            related = {k: v for k, v in raw.items() if k != "attributes"}
        else:
            # Custom lookup to a record the benchmark does not own and whose
            # sobject is unknown — nothing faithful to attach.
            cache[record_id] = None
            return None
        cache[record_id] = dict(related)
        return related

    def _related_name(self, related_sobject: str, record_id: str) -> str:
        if related_sobject == "RecordType":
            return self._record_type_name(record_id)
        cache = getattr(self.client, "_related_name_cache", None)
        if cache is None:
            cache = {}
            self.client._related_name_cache = cache
        key = (related_sobject, record_id)
        if key not in cache:
            row = self.client.get(related_sobject, record_id, fields=["Name"])
            cache[key] = str(row.get("Name") or "")
        return cache[key]

    def _record_type_name(self, record_type_id: str) -> str:
        cache = getattr(self.client, "_record_type_cache", None)
        if cache is None:
            cache = {}
            for row in self.client.query("SELECT Id, Name FROM RecordType").get("records", []):
                cache[str(row.get("Id"))] = str(row.get("Name"))
            self.client._record_type_cache = cache
        if record_type_id not in cache:
            raise RuntimeError(f"live org has no RecordType with id {record_type_id}")
        return cache[record_type_id]


    def _stable_refs(self, section: dict[str, Any]) -> dict[str, str]:
        text = json.dumps(section or {})
        refs: dict[str, str] = {}
        if "$STANDARD_PRICEBOOK_ID" in text or "$STANDARD_PRICEBOOK2_ID" in text:
            pricebook_id = self._standard_pricebook_id()
            refs["$STANDARD_PRICEBOOK_ID"] = pricebook_id
            refs["$STANDARD_PRICEBOOK2_ID"] = pricebook_id
        for token in set(re.findall(r"\$RECORD_TYPE:[^\"]+", text)):
            _, rt_sobject, rt_name = token.split(":", 2)
            rows = self.client.query(
                "SELECT Id FROM RecordType WHERE SobjectType = '%s' AND Name = '%s'"
                % (self.client._soql_escape_static(rt_sobject), self.client._soql_escape_static(rt_name))
            ).get("records", [])
            if not rows:
                raise RuntimeError(f"live org has no RecordType {rt_name!r} on {rt_sobject}")
            refs[token] = str(rows[0]["Id"])
        return refs

    def _standard_pricebook_id(self) -> str:
        result = self.client.query("SELECT Id FROM Pricebook2 WHERE IsStandard = true LIMIT 1")
        records = result.get("records") if isinstance(result, dict) else []
        if not records:
            raise RuntimeError("Salesforce Standard Pricebook not found")
        pricebook_id = str(records[0].get("Id") or "")
        if not pricebook_id:
            raise RuntimeError(f"Salesforce Standard Pricebook query returned no Id: {records[0]}")
        return pricebook_id

    def _replace_seed_refs(self, value: Any, refs: dict[str, str]) -> Any:
        if isinstance(value, dict):
            return {key: self._replace_seed_refs(item, refs) for key, item in value.items()}
        if isinstance(value, list):
            return [self._replace_seed_refs(item, refs) for item in value]
        if isinstance(value, str):
            out = value
            for token, replacement in refs.items():
                out = out.replace(token, replacement)
            return out
        return value

    def add_existing_user(self, where: str, logical_sobject: str = "User",
                          extra_field_names: Any = None) -> dict[str, Any]:
        """Register a PRE-EXISTING live org User (matched by the seed's WHERE)
        as a read-only record. Mirrors add_current_user; used for populations
        the benchmark cannot create (SF Users are unseedable) but that exist
        in every org, e.g. the never-login Integration User."""
        field_names = ["Id", "Email", "Username", "Name", "IsActive",
                       "UserType", "LastLoginDate"]
        for extra in extra_field_names or []:
            if str(extra) and str(extra) not in field_names:
                field_names.append(str(extra))
        result = self.client.query(
            "SELECT %s FROM User WHERE %s LIMIT 1" % (", ".join(field_names), where)
        )
        records = result.get("records") if isinstance(result, dict) else []
        if not records:
            raise RuntimeError(f"salesforce.existing_users matched no live User for: {where}")
        raw = dict(records[0])
        raw.pop("attributes", None)
        record_id = str(raw.get("Id") or "")
        if not record_id:
            raise RuntimeError(f"salesforce.existing_users row missing Id: {raw}")
        fields = dict(raw)
        fields["Email"] = fields.get("Email") or fields.get("Username")
        row = {
            "id": record_id,
            "physical_sobject": "User",
            "logical_sobject": str(logical_sobject or "User"),
            "field_names": field_names,
            "fields": fields,
        }
        self.read_only_records.append(row)
        return {"ok": True, "id": record_id, "sobject": row["logical_sobject"], "fields": dict(fields)}

    def add_current_user(self, logical_sobject: str, extra_field_names: Any = None) -> dict[str, Any]:
        if not self.client.username and not self.client.user_id:
            self.client._cli_auth()
        if self.client.user_id:
            where = "Id = '%s'" % self._soql_escape(str(self.client.user_id))
        elif self.client.username:
            where = "Username = '%s'" % self._soql_escape(str(self.client.username))
        else:
            raise RuntimeError("Salesforce CLI did not expose a current user id or username")
        field_names = [
            "Id",
            "Alias",
            "Department",
            "Email",
            "Username",
            "Name",
            "CompanyName",
            "IsActive",
            "ManagerId",
            "Title",
            "TimeZoneSidKey",
        ]
        # Recipes reading CUSTOM User fields (e.g. Sales_Team__c) declare them
        # via seed.salesforce.current_user.read_fields; a missing live field
        # makes this SELECT fail fast at seed time.
        for extra in extra_field_names or []:
            if str(extra) and str(extra) not in field_names:
                field_names.append(str(extra))
        result = self.client.query(
            "SELECT %s FROM User WHERE %s LIMIT 1" % (", ".join(field_names), where)
        )
        records = result.get("records") if isinstance(result, dict) else []
        if not records:
            raise RuntimeError("Salesforce current user query returned no records")
        raw = dict(records[0])
        raw.pop("attributes", None)
        record_id = str(raw.get("Id") or "")
        if not record_id:
            raise RuntimeError(f"Salesforce current user record missing Id: {raw}")
        fields = dict(raw)
        fields["Email"] = fields.get("Email") or fields.get("Username")
        row = {
            "id": record_id,
            "physical_sobject": "User",
            "logical_sobject": logical_sobject,
            "field_names": field_names,
            "fields": fields,
        }
        self.read_only_records.append(row)
        return {"ok": True, "id": record_id, "sobject": logical_sobject, "fields": dict(fields)}

    def create_record(self, logical_sobject: str, fields: dict[str, Any]) -> dict[str, Any]:
        sobject = self._physical_sobject_name(logical_sobject)
        logical = self._map_user_ids(dict(fields or {}))
        if (
            str(logical_sobject) == "CampaignMember"
            and logical.get("ContactId") in (None, "")
            and logical.get("LeadId") in (None, "")
        ):
            # CampaignMember has a one-of relationship constraint that is not
            # represented by either field's individual `required` flag.
            raise RuntimeError(
                "Salesforce CampaignMember requires either ContactId or LeadId"
            )
        physical = self._physical_fields(sobject, logical)
        missing_required = [
            key for key in self._required_field_names(sobject) if key not in physical
        ]
        if missing_required:
            raise RuntimeError(
                f"Salesforce seed record {sobject} is missing required fields {missing_required}; "
                "declare them explicitly in the variant seed"
            )
        data = {
            key: value
            for key, value in physical.items()
            if not (isinstance(value, str) and not value.strip())
        }
        response = self.client.create(sobject, data)
        record_id = response.get("id") or response.get("Id")
        if not record_id:
            raise RuntimeError(f"Salesforce create returned no id: {response}")
        field_names = list(dict.fromkeys(["Id", *data.keys()]))
        self.owned[str(record_id)] = (sobject, field_names, logical_sobject)
        return {"ok": True, "id": str(record_id), "sobject": logical_sobject}

    def update_record(self, logical_sobject: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        # A mutated parent must not serve stale expanded-relationship data.
        getattr(self.client, "_related_fields_cache", {}).clear()
        record_key = str(record_id or "")
        if record_key not in self.owned:
            raise RuntimeError(
                f"refusing to update non-owned Salesforce record {record_key} for {logical_sobject}"
            )
        physical_sobject, field_names, owned_logical = self.owned[record_key]
        if logical_sobject and str(logical_sobject) != owned_logical:
            raise RuntimeError(
                f"refusing to update Salesforce {owned_logical} record {record_key} as {logical_sobject}"
            )
        logical = self._map_user_ids({
            str(key): value
            for key, value in (fields or {}).items()
            if str(key) not in {"Id", "id", "sobject", "sobject_name"}
        })
        physical = self._physical_update_fields(physical_sobject, logical)
        self.client.update(physical_sobject, record_key, physical)
        new_field_names = [
            field
            for field in [*field_names, *physical.keys()]
            if field not in {"id", "sobject", "sobject_name"}
        ]
        self.owned[record_key] = (physical_sobject, list(dict.fromkeys(new_field_names)), owned_logical)
        return {
            "ok": True,
            "id": record_key,
            "sobject": owned_logical,
            "updated_fields": dict(logical),
            "physical_fields": list(physical.keys()),
        }

    def upsert_record(self, logical_sobject: str, key_field: str, fields: dict[str, Any]) -> dict[str, Any]:
        getattr(self.client, "_related_fields_cache", {}).clear()
        key = str(key_field or "")
        if not key:
            raise RuntimeError("Salesforce upsert requires a primary key field")
        # Map BEFORE the key-match search so the match and the write see the
        # same live value (idempotent on the delegated create/update because
        # user_id_map targets are never themselves mapped keys).
        fields = self._map_user_ids(dict(fields or {}))
        key_value = (fields or {}).get(key)
        matches = self.search_records(logical_sobject, "", [{"field": key, "value": key_value}]) if key_value not in (None, "") else []
        if matches:
            record_id = str(matches[0].get("id") or matches[0].get("Id") or "")
            updated = self.update_record(logical_sobject, record_id, fields)
            return {**updated, "status": "updated", "created": False}
        created = self.create_record(logical_sobject, fields)
        return {**created, "status": "created", "created": True}

    _AGG_RE = re.compile(r"\bSUM\(\s*([A-Za-z0-9_.]+)\s*\)", re.I)
    _GROUP_BY_RE = re.compile(r"\bGROUP\s+BY\s+(.+?)(?:\bORDER\b|\bLIMIT\b|$)", re.I | re.S)

    def search_records(self, sobject: str, query: str, filters: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        query_text = str(query or "")
        # `offset` is the connector's PAGINATION parameter, not a record
        # field: no sobject has an offset column, so treating it as an
        # equality filter excludes every row. Applied as a result-list skip.
        offset_skip = 0
        row_filters: list[dict[str, Any]] = []
        for raw_filter in filters or []:
            if isinstance(raw_filter, dict) and str(raw_filter.get("field") or "") == "offset":
                offset_skip = int(float(raw_filter.get("value") or 0))
            else:
                row_filters.append(raw_filter)
        filters = row_filters
        child_specs: list[dict[str, Any]] = []
        if self.strict_soql:
            # SELECT-list child-relationship subqueries are parsed out before
            # WHERE evaluation and materialized onto every matched parent row
            # (strict-only: legacy non-strict recipes keep their byte-stable
            # flat read-back shape).
            query_text, child_specs = self._extract_child_subqueries(sobject, query_text)
        target_sobject = str(sobject or "").lower()
        terms = self._query_terms(query_text)
        out: list[dict[str, Any]] = []
        for record_id, (physical, field_names, logical) in self.owned.items():
            if str(logical).lower() != target_sobject:
                continue
            fields = self._owned_row_fields(record_id)
            if fields is None:
                continue
            if not self._matches_filters(fields, filters or []):
                continue
            if self._matches_query(fields, query_text, terms):
                self._attach_child_subqueries(fields, record_id, child_specs)
                out.append({"sobject": logical, "id": record_id, **fields, "fields": fields})
        for row in self.read_only_records:
            if str(row.get("logical_sobject") or "").lower() != target_sobject:
                continue
            record_id = str(row.get("id") or "")
            physical = str(row.get("physical_sobject") or sobject)
            # Result rows carry the STORED logical sobject (same as owned rows
            # and snapshot()), never the caller's raw argument — alias/casing
            # drift in a search argument must not leak into result labels.
            logical = str(row.get("logical_sobject") or physical)
            field_names = list(row.get("field_names") or ["Id"])
            raw = self._read(physical, record_id, field_names)
            if raw is None:
                raise RuntimeError(f"read-only Salesforce record disappeared: {physical} {record_id}")
            live = {key: value for key, value in raw.items() if key != "attributes"}
            fields = {**dict(row.get("fields") or {}), **{k: v for k, v in live.items() if v is not None}}
            if not self._matches_filters(fields, filters or []):
                continue
            if self._matches_query(fields, query_text, terms):
                self._attach_child_subqueries(fields, record_id, child_specs)
                out.append({"sobject": logical, "id": record_id, **fields, "fields": fields})
        if offset_skip:
            if self.strict_soql:
                # Live SOQL orders BEFORE it offsets (ORDER BY -> OFFSET ->
                # LIMIT). Skipping in seed order here would hand a paged query
                # the wrong row identities: a row already served inside an
                # earlier page could be served again while the true tail row
                # is never returned. Gated on a NON-ZERO connector offset plus
                # the strict flag, so every offset-less query and every legacy
                # (non-strict) recipe keeps its byte-identical result;
                # SalesforceRun re-applies the same stable sort afterwards,
                # which is a no-op on this already-sorted suffix.
                out = self._apply_order_by(query_text, out)
            out = out[offset_skip:]
        return self._apply_aggregates(query_text, out)

    # ORDER BY parsing. The clause boundary is the FIRST `ORDER BY` token in
    # the query text (not quote-aware) — deliberately identical to the clause
    # strip in _matches_query, so the WHERE evaluation and the sort always
    # agree on where the WHERE clause ends (recipe-built strings with stray
    # quotes, e.g. "...') ' ORDER BY CloseDate DESC", stay consistent).
    _ORDER_BY_TAIL_RE = re.compile(r"\bORDER\s+BY\b(.*)$", re.I | re.S)
    # SOQL allows only LIMIT / OFFSET / FOR ... after the sort keys.
    _ORDER_BY_STOP_RE = re.compile(
        r"\b(?:LIMIT|OFFSET)\s+\d+.*$|\bFOR\s+(?:VIEW|UPDATE|REFERENCE)\b.*$",
        re.I | re.S,
    )
    _ORDER_BY_TERM_RE = re.compile(
        r"([A-Za-z_][A-Za-z0-9_.]*)(?:\s+(ASC|DESC))?(?:\s+NULLS\s+(FIRST|LAST))?",
        re.I,
    )
    # SF REST date / datetime read-back shapes (e.g. 2026-08-01,
    # 2026-07-15T22:03:55.000+0000, ...Z, ...+00:00).
    _ORDER_BY_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
    _ORDER_BY_DATETIME_RE = re.compile(
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?"
    )

    @classmethod
    def _parse_order_by(cls, query: str) -> list[tuple[str, bool, bool]]:
        """Parse a SOQL ORDER BY clause into [(field, descending, nulls_last)]
        covering EVERY sort key with per-key direction and null placement
        (SOQL defaults: ASC = NULLS FIRST, DESC = NULLS LAST; explicit
        NULLS FIRST/LAST honored). Raises on any term that is not a plain
        field / relationship path — positional keys, functions, subexpressions
        cannot be faithfully evaluated and must never be silently mis-sorted."""
        text = str(query or "")
        tail_match = cls._ORDER_BY_TAIL_RE.search(text)
        if not tail_match:
            return []
        tail = cls._ORDER_BY_STOP_RE.sub("", tail_match.group(1)).strip()
        if not tail:
            raise RuntimeError(f"empty SOQL ORDER BY clause in: {text!r}")
        specs: list[tuple[str, bool, bool]] = []
        for item in tail.split(","):
            item = item.strip()
            term = cls._ORDER_BY_TERM_RE.fullmatch(item)
            if not term:
                raise RuntimeError(
                    f"unsupported SOQL ORDER BY term {item!r} in: {text!r} "
                    "(supported: <field or relationship.path> [ASC|DESC] "
                    "[NULLS FIRST|NULLS LAST])"
                )
            descending = (term.group(2) or "ASC").upper() == "DESC"
            nulls = term.group(3)
            nulls_last = descending if nulls is None else nulls.upper() == "LAST"
            specs.append((term.group(1), descending, nulls_last))
        return specs

    @classmethod
    def _order_value_class(cls, value: Any, field: str, query: str) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, str):
            if cls._ORDER_BY_DATETIME_RE.fullmatch(value) or cls._ORDER_BY_DATE_RE.fullmatch(value):
                return "temporal"
            return "string"
        raise RuntimeError(
            f"unsortable SOQL ORDER BY value for {field!r} in {query!r}: "
            f"{type(value).__name__} {value!r}"
        )

    @classmethod
    def _order_value_key(cls, kind: str, value: Any, field: str, query: str) -> Any:
        if kind == "boolean":
            return int(value)  # SOQL sorts false before true
        if kind == "number":
            return value
        if kind == "temporal":
            from datetime import datetime, timezone
            text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", str(value)).replace("Z", "+00:00")
            try:
                when = datetime.fromisoformat(text)
            except ValueError as exc:
                raise RuntimeError(
                    f"unparseable date/datetime under SOQL ORDER BY {field!r} "
                    f"in {query!r}: {value!r}"
                ) from exc
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return when
        if kind == "sfid":
            return str(value)  # binary, case-sensitive (live SOQL ID order)
        # SOQL text collation is case-insensitive by default; approximated as
        # casefolded Unicode codepoint order (org-locale collation of exotic
        # characters is NOT emulated). Full ties keep prior order (stable).
        return str(value).casefold()

    @staticmethod
    def _sort_one_key(
        records: list[dict[str, Any]], field: str, descending: bool, nulls_last: bool, query: str
    ) -> list[dict[str, Any]]:
        """One stable sort pass for a single ORDER BY key. Values resolve via
        the SAME _field_lookup the WHERE evaluation uses (relationship paths
        like Account.Name walk the attached parent dicts). Values are compared
        TYPED: numbers numerically, dates/datetimes chronologically, ID
        columns by case-sensitive ID value, other strings case-insensitively.
        None and '' both order as SQL NULL (live SF stores empty text as
        null). A key whose non-null values mix incompatible types cannot be
        faithfully compared and raises."""
        lookup = OwnedSalesforce._field_lookup
        values = [
            lookup(row.get("fields") if isinstance(row.get("fields"), dict) else row, field)
            for row in records
        ]
        non_null = [value for value in values if value is not None and value != ""]
        classes = {
            OwnedSalesforce._order_value_class(value, field, query) for value in non_null
        }
        if classes == {"temporal", "string"}:
            # A text field may hold date-shaped strings next to plain text;
            # live SOQL sorts such a column as text.
            classes = {"string"}
        if classes == {"string"} and all(OwnedSalesforce._looks_sf_id(v) for v in non_null):
            # Live SOQL sorts ID columns (Id / reference fields) by the
            # case-SENSITIVE character value of the ID, unlike text fields
            # (verified against live groundtruth: ...kHXJ < ...kHYv < ...kHaX).
            classes = {"sfid"}
        if len(classes) > 1:
            raise RuntimeError(
                f"mixed-type values under SOQL ORDER BY {field!r} in {query!r}: "
                f"{sorted(classes)} cannot be faithfully compared"
            )
        kind = classes.pop() if classes else "string"
        # Null rank places nulls per SOQL (ASC nulls first / DESC nulls last
        # by default, explicit NULLS FIRST/LAST override). reverse=True flips
        # the whole key tuple, so the rank sign is precomputed against it.
        null_rank = (-1 if nulls_last else 1) if descending else (1 if nulls_last else -1)
        keys: list[tuple[int, Any]] = []
        for value in values:
            if value is None or value == "":
                keys.append((null_rank, 0))
            else:
                keys.append((0, OwnedSalesforce._order_value_key(kind, value, field, query)))
        order = sorted(range(len(records)), key=keys.__getitem__, reverse=descending)
        return [records[index] for index in order]

    @staticmethod
    def _apply_order_by(query: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Full SOQL ORDER BY shared by the strict run-tool path and the
        pre-OFFSET sort: every sort key, per-key ASC/DESC and null placement,
        typed comparison. Applied as chained stable sorts (last key first), so
        re-applying it never reorders and full ties keep their prior order.
        Any construct that cannot be faithfully evaluated raises loudly."""
        specs = OwnedSalesforce._parse_order_by(query)
        out = records
        for field, descending, nulls_last in reversed(specs):
            out = OwnedSalesforce._sort_one_key(out, field, descending, nulls_last, query)
        return out

    def _owned_row_fields(self, record_id: str) -> dict[str, Any] | None:
        """Live read-back of an owned record with the same augmentation a search
        result row gets (relationship paths + logical stand-in aliases). None
        only when the record no longer exists (404)."""
        physical, field_names, _logical = self.owned[record_id]
        raw = self._read(physical, record_id, list(dict.fromkeys([*field_names, *self._readback_extra_fields(physical)])))
        if raw is None:
            return None
        fields = {key: value for key, value in raw.items() if key != "attributes"}
        self._augment_relationships(fields)
        self._logical_aliases(physical, fields)
        return fields

    def _extract_child_subqueries(
        self, sobject: str, text: str
    ) -> tuple[str, list[dict[str, Any]]]:
        """Split `SELECT ..., (SELECT f1, f2 FROM ChildRel WHERE ...) FROM ...`
        into the query without the child subqueries plus one parsed spec per
        subquery. Bare-condition strings and subquery-free SELECTs pass through
        untouched."""
        if not re.match(r"\s*SELECT\b", text, flags=re.I):
            return text, []
        select_match = re.match(r"\s*SELECT\b", text, flags=re.I)
        list_start = select_match.end()
        from_idx = self._find_top_keyword(text, "FROM", start=list_start)
        if from_idx is None:
            return text, []
        items = self._split_top_commas(text[list_start:from_idx])
        plain: list[str] = []
        specs: list[dict[str, Any]] = []
        for item in items:
            if re.match(r"\(\s*SELECT\b", item, flags=re.I):
                specs.append(self._parse_child_subquery(sobject, item))
            else:
                plain.append(item)
        if not specs:
            return text, []
        # A SELECT list cannot be empty; Id is always read back anyway.
        rebuilt = ", ".join(plain) if plain else "Id"
        return f"{text[:list_start]} {rebuilt} {text[from_idx:]}", specs

    def _parse_child_subquery(self, sobject: str, item: str) -> dict[str, Any]:
        inner = self._strip_condition(item)
        parsed = re.fullmatch(
            r"SELECT\s+(.+?)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+WHERE\s+(.+?))?\s*",
            inner,
            flags=re.I | re.S,
        )
        if not parsed:
            raise RuntimeError(f"unsupported SOQL SELECT-list subquery: {item!r}")
        select_fields = [part.strip() for part in parsed.group(1).split(",") if part.strip()]
        for field in select_fields:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", field):
                raise RuntimeError(
                    f"unsupported field in SOQL SELECT-list subquery: {field!r}"
                )
        rel_name = parsed.group(2)
        where = (parsed.group(3) or "").strip() or None
        mapped = None
        for (map_parent, map_rel), value in SALESFORCE_CHILD_RELATIONSHIP_MAP.items():
            if map_parent.lower() == str(sobject).lower() and map_rel.lower() == rel_name.lower():
                mapped = value
                break
        if mapped is None:
            raise RuntimeError(
                f"unknown SOQL child relationship {rel_name!r} on {sobject!r} — "
                "add a SALESFORCE_CHILD_RELATIONSHIP_MAP entry (no-fallback)"
            )
        if where:
            bad = self._first_unsupported_strict_leaf(where)
            if bad is not None:
                raise RuntimeError(
                    "unsupported SOQL condition under strict_soql_conditions "
                    f"(SELECT-list subquery leaf): {bad!r}"
                )
        return {
            "rel_name": rel_name,
            "select_fields": select_fields,
            "child_sobject": mapped[0],
            "fk_field": mapped[1],
            "where": where,
        }

    def _attach_child_subqueries(
        self, fields: dict[str, Any], parent_id: str, specs: list[dict[str, Any]]
    ) -> None:
        """Materialize each SELECT-list child subquery onto the parent row in
        live Salesforce's nested shape ({totalSize, done, records}); an empty
        child result STILL attaches {"records": [], "totalSize": 0} so `.size`
        derefs 0 (live REST returns null there, but the recipes' formulas need
        the records key present)."""
        for spec in specs:
            records: list[dict[str, Any]] = []
            for child_id, (physical, _field_names, _logical) in list(self.owned.items()):
                if physical.lower() != str(spec["child_sobject"]).lower():
                    continue
                child_fields = self._owned_row_fields(child_id)
                if child_fields is None:
                    continue
                fk_value = self._field_lookup(child_fields, spec["fk_field"])
                if str(fk_value or "") != str(parent_id):
                    continue
                if spec["where"] and not self._soql_condition_matches(child_fields, spec["where"]):
                    continue
                records.append(
                    {field: self._field_lookup(child_fields, field) for field in spec["select_fields"]}
                )
            fields[spec["rel_name"]] = {
                "totalSize": len(records),
                "done": True,
                "records": records,
            }

    @staticmethod
    def _split_top_commas(text: str) -> list[str]:
        """Split a SELECT list on commas at paren depth 0, outside quotes."""
        parts: list[str] = []
        depth = 0
        quote = False
        start = 0
        idx = 0
        while idx < len(text):
            char = text[idx]
            if quote:
                if char == "\\":
                    idx += 2
                    continue
                if char == "'":
                    quote = False
            elif char == "'":
                quote = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            elif char == "," and depth == 0:
                parts.append(text[start:idx])
                start = idx + 1
            idx += 1
        parts.append(text[start:])
        return [part for part in (piece.strip() for piece in parts) if part]

    _AGG_SELECT_RE = re.compile(
        r"\b(SUM|COUNT|MAX|MIN|AVG)\(\s*([A-Za-z0-9_.]*)\s*\)(?:\s+([A-Za-z_][A-Za-z0-9_]*))?", re.I
    )
    _GROUP_ALIAS_RE = re.compile(
        r"(?:^|,)\s*([A-Za-z_][A-Za-z0-9_.]*)(?:\s+([A-Za-z_][A-Za-z0-9_]*))?\s*(?=,|$)"
    )

    def _apply_aggregates(self, query_text: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Live-faithful SOQL aggregate evaluation over benchmark-owned rows:
        GROUP BY fields + SUM/COUNT with optional SELECT aliases. Unaliased
        aggregates take Salesforce's exprN names; aliased fields/aggregates
        take the alias."""
        group_match = self._GROUP_BY_RE.search(query_text)
        select_match = re.search(r"\bSELECT\b(.+?)\bFROM\b", query_text, flags=re.I | re.S)
        aggs = self._AGG_SELECT_RE.findall(select_match.group(1)) if select_match else []
        if group_match and not aggs:
            # SOQL GROUP BY without aggregate functions = DISTINCT projection
            # of the group fields (passing raw rows through duplicated them).
            group_fields = [part.strip() for part in group_match.group(1).split(",") if part.strip()]
            seen: set[tuple] = set()
            deduped: list[dict[str, Any]] = []
            for row in rows:
                fields = row.get("fields") if isinstance(row.get("fields"), dict) else row
                key = tuple(str(self._field_lookup(fields, g)) for g in group_fields)
                if key in seen:
                    continue
                seen.add(key)
                projected = {g: self._field_lookup(fields, g) for g in group_fields}
                deduped.append({**projected, "fields": dict(projected)})
            return deduped
        if not group_match or not aggs:
            return rows
        from decimal import Decimal, InvalidOperation
        group_fields = [part.strip() for part in group_match.group(1).split(",") if part.strip()]
        # SELECT-list aliases for group fields (e.g. `Account__c AccountID`).
        group_aliases: dict[str, str] = {}
        if select_match:
            for chunk in select_match.group(1).split(","):
                chunk = chunk.strip()
                if "(" in chunk:
                    continue
                parts = chunk.split()
                if len(parts) == 2 and parts[0] in group_fields:
                    group_aliases[parts[0]] = parts[1]
        expr_index = 0
        agg_keys: list[tuple[str, str, str]] = []  # (func, field, out_key)
        for func, field, alias in aggs:
            if alias:
                out_key = alias
            else:
                out_key = f"expr{expr_index}"
                expr_index += 1
            agg_keys.append((func.upper(), field, out_key))
        grouped: dict[tuple, dict[str, Any]] = {}
        for row in rows:
            fields = row.get("fields") if isinstance(row.get("fields"), dict) else row
            key = tuple(str(self._field_lookup(fields, g)) for g in group_fields)
            bucket = grouped.setdefault(key, {
                **{group_aliases.get(g, g): self._field_lookup(fields, g) for g in group_fields},
                **{out_key: (None if func in ("MAX", "MIN")
                             else (Decimal(0), 0) if func == "AVG"
                             else Decimal(0))
                   for func, _, out_key in agg_keys},
            })
            for func, agg_field, out_key in agg_keys:
                if func == "COUNT":
                    if not agg_field or self._field_lookup(fields, agg_field) not in (None, ""):
                        bucket[out_key] += 1
                    continue
                value = self._field_lookup(fields, agg_field)
                if value in (None, ""):
                    continue
                if func in ("MAX", "MIN"):
                    # Dates/datetimes/strings order lexicographically in their
                    # SF read-back form; numbers order numerically.
                    try:
                        candidate: Any = Decimal(str(value))
                    except (InvalidOperation, ValueError):
                        candidate = str(value)
                    current = bucket[out_key]
                    if current is None:
                        bucket[out_key] = candidate
                    elif isinstance(current, Decimal) != isinstance(candidate, Decimal):
                        raise RuntimeError(
                            f"mixed value types in {func}({agg_field}): {current!r} vs {value!r}"
                        )
                    elif (candidate > current) == (func == "MAX"):
                        bucket[out_key] = candidate
                    continue
                if func == "AVG":
                    total, n = bucket[out_key]
                    try:
                        bucket[out_key] = (total + Decimal(str(value)), n + 1)
                    except (InvalidOperation, ValueError) as exc:
                        raise RuntimeError(f"non-numeric value in AVG({agg_field}): {value!r}") from exc
                    continue
                try:
                    bucket[out_key] += Decimal(str(value))
                except (InvalidOperation, ValueError) as exc:
                    raise RuntimeError(f"non-numeric value in SUM({agg_field}): {value!r}") from exc
        out_rows = []
        for bucket in grouped.values():
            for func, _, out_key in agg_keys:
                dec = bucket[out_key]
                if func == "AVG":
                    total, n = dec
                    dec = (total / n) if n else None
                    bucket[out_key] = None if dec is None else (
                        int(dec) if dec == dec.to_integral_value() else float(dec))
                    continue
                if isinstance(dec, Decimal):
                    bucket[out_key] = int(dec) if dec == dec.to_integral_value() else float(dec)
            out_rows.append({**bucket, "fields": dict(bucket)})
        return out_rows

    def snapshot(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        for record_id, (physical, field_names, logical) in self.owned.items():
            raw = self._read(physical, record_id, list(dict.fromkeys([*field_names, *self._readback_extra_fields(physical)])))
            if raw is None:
                continue
            fields = {key: value for key, value in raw.items() if key != "attributes"}
            self._augment_relationships(fields)
            self._logical_aliases(physical, fields)
            records.append({"sobject": logical, "id": record_id, "fields": fields})
        for row in self.read_only_records:
            record_id = str(row.get("id") or "")
            physical = str(row.get("physical_sobject") or row.get("logical_sobject") or "")
            logical = str(row.get("logical_sobject") or physical)
            field_names = list(row.get("field_names") or ["Id"])
            raw = self._read(physical, record_id, field_names)
            if raw is None:
                raise RuntimeError(f"read-only Salesforce record disappeared: {physical} {record_id}")
            live = {key: value for key, value in raw.items() if key != "attributes"}
            fields = {**dict(row.get("fields") or {}), **{k: v for k, v in live.items() if v is not None}}
            records.append({"sobject": logical, "id": record_id, "fields": fields, "read_only": True})
        return {"salesforce": {"records": records}}

    def scan_owned(self) -> list[dict[str, str]]:
        owned: list[dict[str, str]] = []
        for record_id, (sobject, _field_names, _logical) in self.owned.items():
            if self._read(sobject, record_id, ["Id"]) is not None:
                owned.append({"kind": "salesforce.record", "id": record_id, "location": sobject})
        return owned

    def delete_owned(self) -> list[dict[str, str]]:
        """Delete benchmark-owned records (children first). Required cleanup
        is fail-fast: only an already-gone record (404, e.g. cascade-deleted
        by a parent) is benign; every other deletion error is collected and
        returned so cleanup() can surface it instead of hiding leftovers."""
        failures: list[dict[str, str]] = []
        for record_id, (sobject, _field_names, _logical) in reversed(list(self.owned.items())):
            try:
                self.client.delete(sobject, record_id)
            except SalesforceError as exc:
                if exc.status == 404:
                    continue  # already gone (cascade delete) — cleanup achieved
                failures.append({"id": record_id, "sobject": sobject, "error": str(exc)[:200]})
            except Exception as exc:
                failures.append({"id": record_id, "sobject": sobject, "error": str(exc)[:200]})
        return failures

    def export_state(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "expand_relationships": self.expand_relationships,
            "strict_soql_conditions": self.strict_soql,
            "user_id_map": dict(self.user_id_map),
            "owned_records": [
                {
                    "id": record_id,
                    "physical_sobject": physical,
                    "logical_sobject": logical,
                    "field_names": field_names,
                }
                for record_id, (physical, field_names, logical) in self.owned.items()
            ],
            "read_only_records": [dict(row) for row in self.read_only_records],
        }

    @staticmethod
    def _matches_filters(fields: dict[str, Any], filters: list[dict[str, Any]]) -> bool:
        for raw_filter in filters:
            if not isinstance(raw_filter, dict):
                raise RuntimeError("Salesforce search filter must be an object")
            field = str(raw_filter.get("field") or "")
            if not field:
                raise RuntimeError("Salesforce search filter missing field")
            expected = raw_filter.get("value")
            actual = fields.get(field)
            if not _same_salesforce_value(actual, expected):
                return False
        return True

    def _matches_query(self, fields: dict[str, Any], query: str, terms: set[str]) -> bool:
        if not str(query or "").strip():
            return True
        if self.strict_soql:
            # Opt-in (seed salesforce.strict_soql_conditions): the WHERE clause
            # is evaluated recursively with paren-aware OR/AND splitting; an
            # unsupported leaf RAISES — silently dropping one changes the match
            # set and poisons groundtruth.
            text = str(query or "")
            # The clause starts at the DEPTH-0 WHERE: a WHERE inside an
            # IN (SELECT ... WHERE ...) subquery or a quoted literal must not
            # be mistaken for the outer clause boundary.
            where_idx = self._find_top_keyword(text, "WHERE")
            if where_idx is not None:
                clause = text[where_idx + len("WHERE"):]
            elif re.match(r"\s*SELECT\b", text, flags=re.I):
                # Full SOQL with no WHERE — unfiltered, matches every record.
                return True
            else:
                # search_sobjects_soql passes a BARE condition string (no
                # WHERE keyword) — evaluate it as the clause rather than
                # silently matching all.
                clause = text
            clause = re.sub(r"\bORDER\s+BY\b.+$", "", clause, flags=re.I | re.S)
            clause = re.sub(r"\bGROUP\s+BY\b.+$", "", clause, flags=re.I | re.S)
            clause = re.sub(r"\bLIMIT\s+\d+\s*$", "", clause, flags=re.I | re.S).strip()
            if not clause:
                return True
            return self._soql_condition_matches(fields, clause)
        groups = self._query_condition_groups(query)
        if groups:
            return any(all(self._query_leaf_matches(fields, condition) for condition in group) for group in groups)
        values = " ".join(str(value).lower() for value in fields.values())
        return not terms or any(term in values for term in terms)

    def _soql_condition_matches(self, fields: dict[str, Any], text: str) -> bool:
        text = self._strip_condition(str(text).strip())
        or_parts = self._soql_split_top(text, "OR")
        if len(or_parts) > 1:
            return any(self._soql_condition_matches(fields, part) for part in or_parts)
        and_parts = self._soql_split_top(text, "AND")
        if len(and_parts) > 1:
            return all(self._soql_condition_matches(fields, part) for part in and_parts)
        condition = self._strip_condition(text)
        if condition != text:
            return self._soql_condition_matches(fields, condition)
        negated = re.match(r"NOT\s*(\(.*\)|\S.*)$", condition, flags=re.I | re.S)
        if negated and not re.match(r"NOT\s+IN\b", condition, flags=re.I):
            # SOQL NOT-prefix form: NOT Role LIKE '%x%' / NOT (a OR b).
            return not self._soql_condition_matches(fields, negated.group(1))
        subquery = self._parse_in_subquery(condition)
        if subquery is not None:
            # Handled BEFORE generic admission so an unsupported INNER leaf
            # raises naming that exact leaf (never silently dropped).
            return self._in_subquery_matches(fields, subquery)
        if self._is_supported_query_condition(condition) or self._is_strict_query_condition(condition):
            return self._matches_query_condition(fields, condition)
        raise RuntimeError(
            f"unsupported SOQL condition under strict_soql_conditions: {condition!r}"
        )

    @staticmethod
    def _soql_split_top(text: str, keyword: str) -> list[str]:
        """Split on a boolean keyword at paren depth 0, outside quotes."""
        parts: list[str] = []
        depth = 0
        quote = False
        idx = 0
        start = 0
        upper = keyword.upper()
        while idx < len(text):
            char = text[idx]
            if quote:
                if char == "\\":
                    idx += 2
                    continue
                if char == "'":
                    quote = False
            elif char == "'":
                quote = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and text[idx:idx + len(upper)].upper() == upper:
                before_ok = idx == 0 or not (text[idx - 1].isalnum() or text[idx - 1] == "_")
                after = idx + len(upper)
                after_ok = after >= len(text) or not (text[after].isalnum() or text[after] == "_")
                if before_ok and after_ok:
                    parts.append(text[start:idx])
                    idx = after
                    start = idx
                    continue
            idx += 1
        parts.append(text[start:])
        return [part for part in (piece.strip() for piece in parts) if part] or [text.strip()]

    @staticmethod
    def _find_top_keyword(text: str, keyword: str, start: int = 0) -> int | None:
        """Index of the first word-bounded occurrence of `keyword` at paren
        depth 0, outside quotes; None when absent."""
        depth = 0
        quote = False
        idx = start
        upper = keyword.upper()
        while idx < len(text):
            char = text[idx]
            if quote:
                if char == "\\":
                    idx += 2
                    continue
                if char == "'":
                    quote = False
            elif char == "'":
                quote = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and text[idx:idx + len(upper)].upper() == upper:
                before_ok = idx == 0 or not (text[idx - 1].isalnum() or text[idx - 1] == "_")
                after = idx + len(upper)
                after_ok = after >= len(text) or not (text[after].isalnum() or text[after] == "_")
                if before_ok and after_ok:
                    return idx
            idx += 1
        return None

    # `outer_field [NOT] IN (SELECT inner_field FROM InnerSobject [WHERE ...])`
    _IN_SUBQUERY_RE = re.compile(
        r"([A-Za-z_][A-Za-z0-9_.]*)\s+(NOT\s+)?IN\s*\(\s*(SELECT\b.*)\)\s*",
        re.I | re.S,
    )
    _IN_SUBQUERY_SELECT_RE = re.compile(
        r"SELECT\s+([A-Za-z_][A-Za-z0-9_.]*)\s+FROM\s+([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\s+WHERE\s+(.+?))?\s*",
        re.I | re.S,
    )

    @classmethod
    def _parse_in_subquery(cls, condition: str) -> dict[str, Any] | None:
        """Parse a semi/anti-join leaf; None when the condition is not one
        (including malformed subqueries, which then fail admission and raise
        under strict rather than being evaluated loosely)."""
        outer = cls._IN_SUBQUERY_RE.fullmatch(condition)
        if not outer:
            return None
        inner = cls._IN_SUBQUERY_SELECT_RE.fullmatch(outer.group(3).strip())
        if not inner:
            return None
        return {
            "outer_field": outer.group(1),
            "negated": bool(outer.group(2)),
            "inner_field": inner.group(1),
            "inner_sobject": inner.group(2),
            "inner_where": (inner.group(3) or "").strip() or None,
        }

    @classmethod
    def _first_unsupported_strict_leaf(cls, text: str) -> str | None:
        """Walk a WHERE clause exactly like _soql_condition_matches and return
        the first leaf the strict evaluator could not handle (None when every
        leaf is supported). Pure admission — evaluates nothing."""
        text = cls._strip_condition(str(text).strip())
        or_parts = cls._soql_split_top(text, "OR")
        if len(or_parts) > 1:
            for part in or_parts:
                bad = cls._first_unsupported_strict_leaf(part)
                if bad is not None:
                    return bad
            return None
        and_parts = cls._soql_split_top(text, "AND")
        if len(and_parts) > 1:
            for part in and_parts:
                bad = cls._first_unsupported_strict_leaf(part)
                if bad is not None:
                    return bad
            return None
        condition = cls._strip_condition(text)
        if condition != text:
            return cls._first_unsupported_strict_leaf(condition)
        negated = re.match(r"NOT\s*(\(.*\)|\S.*)$", condition, flags=re.I | re.S)
        if negated and not re.match(r"NOT\s+IN\b", condition, flags=re.I):
            return cls._first_unsupported_strict_leaf(negated.group(1))
        subquery = cls._parse_in_subquery(condition)
        if subquery is not None:
            if subquery["inner_where"] is None:
                return None
            return cls._first_unsupported_strict_leaf(subquery["inner_where"])
        if cls._is_supported_query_condition(condition) or cls._is_strict_query_condition(condition):
            return None
        return condition

    @classmethod
    def _is_admissible_in_subquery(cls, condition: str) -> bool:
        subquery = cls._parse_in_subquery(condition)
        if subquery is None:
            return False
        if subquery["inner_where"] is None:
            return True
        return cls._first_unsupported_strict_leaf(subquery["inner_where"]) is None

    def _in_subquery_matches(self, fields: dict[str, Any], subquery: dict[str, Any]) -> bool:
        if subquery["inner_where"] is not None:
            bad = self._first_unsupported_strict_leaf(subquery["inner_where"])
            if bad is not None:
                raise RuntimeError(
                    "unsupported SOQL condition under strict_soql_conditions "
                    f"(IN-subquery inner leaf): {bad!r}"
                )
        values = self._soql_subquery_values(
            subquery["inner_sobject"], subquery["inner_field"], subquery["inner_where"]
        )
        actual = str(self._field_lookup(fields, subquery["outer_field"]) or "")
        found = actual in values
        return not found if subquery["negated"] else found

    def _soql_subquery_values(
        self, inner_sobject: str, inner_field: str, inner_where: str | None
    ) -> set[str]:
        """Materialize the IN-subquery value set: scan owned + read-only records
        of the inner sobject exactly as a top-level query on it would
        (search_records applies the stand-in read-back + logical aliases), apply
        the inner WHERE with the same strict leaf evaluator, and project the
        inner field. NULL/empty projected values are EXCLUDED from the set:
        real-SOQL semi/anti-joins ignore null FKs, so `X NOT IN (SELECT f ...)`
        still admits rows whose X merely differs from every NON-null f (unlike
        SQL three-valued NOT IN, which a NULL poisons to match nothing)."""
        values: set[str] = set()
        for row in self.search_records(str(inner_sobject), ""):
            row_fields = row.get("fields") if isinstance(row.get("fields"), dict) else row
            if inner_where and not self._soql_condition_matches(row_fields, inner_where):
                continue
            value = self._field_lookup(row_fields, str(inner_field))
            if value in (None, ""):
                continue
            values.add(str(value))
        return values

    def _query_leaf_matches(self, fields: dict[str, Any], condition: str) -> bool:
        """Leaf dispatch for the legacy (non-strict) group evaluator: IN/NOT IN
        (SELECT ...) needs instance state for the inner scan; every other leaf
        keeps the literal classmethod evaluator unchanged."""
        subquery = self._parse_in_subquery(condition)
        if subquery is not None:
            return self._in_subquery_matches(fields, subquery)
        return self._matches_query_condition(fields, condition)

    def _query_condition_groups(self, query: str) -> list[list[str]]:
        text = str(query or "")
        where = re.search(r"\bWHERE\b(.+)$", text, flags=re.I | re.S)
        if where:
            text = where.group(1)
        text = re.sub(r"\bORDER\s+BY\b.+$", "", text, flags=re.I | re.S).strip()
        text = re.sub(r"\bGROUP\s+BY\b.+$", "", text, flags=re.I | re.S).strip()
        text = re.sub(r"\bLIMIT\s+\d+\s*$", "", text, flags=re.I | re.S).strip()
        if not text:
            return []
        groups: list[list[str]] = []
        for raw_group in re.split(r"\s+\bOR\b\s+", text, flags=re.I):
            conditions = [
                self._strip_condition(condition)
                for condition in re.split(r"\s+\bAND\b\s+", raw_group, flags=re.I)
            ]
            parsed = [condition for condition in conditions if self._is_supported_query_condition(condition)]
            if parsed:
                groups.append(parsed)
        return groups

    @staticmethod
    def _is_strict_query_condition(condition: str) -> bool:
        return bool(
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*\s*(?:>=|<=|>|<)\s*'[^']*'", condition, flags=re.S)
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*\s*(?:!=|<>)\s*'[^']*'", condition, flags=re.S)
            or re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_.]*\s*(?:=|!=|<>)\s*(?:TRUE|FALSE|NULL)",
                condition,
                flags=re.I | re.S,
            )
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*\s+NOT\s+LIKE\s+'[^']*'", condition, flags=re.I | re.S)
            or re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_.]*\s+NOT\s+IN\s*\((?:\s*'[^']*'\s*,?)+\)",
                condition,
                flags=re.I | re.S,
            )
            or re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_.]*\s*(?:>=|<=|<>|!=|=|>|<)\s*LAST_N_DAYS\s*:\s*\d+",
                condition,
                flags=re.I | re.S,
            )
            or re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_.]*\s+INCLUDES\s*\((?:\s*'[^']*'\s*,?)+\)",
                condition,
                flags=re.I | re.S,
            )
            # [NOT] IN (SELECT ...) semi/anti-join: admitted ONLY when the
            # inner sobject/field/conditions are themselves fully supported.
            or OwnedSalesforce._is_admissible_in_subquery(condition)
        )

    @staticmethod
    def _strip_condition(condition: str) -> str:
        text = str(condition or "").strip()
        while text.startswith("(") and text.endswith(")"):
            inner = text[1:-1].strip()
            depth = 0
            balanced = True
            for char in inner:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth < 0:
                        balanced = False
                        break
            if not balanced or depth != 0:
                break
            text = inner
        return text

    @staticmethod
    def _is_supported_query_condition(condition: str) -> bool:
        return bool(
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*\s*=\s*'[^']*'", condition, flags=re.S)
            or re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_.]*\s*(?:=|!=|<>)\s*(?:TRUE|FALSE|NULL)",
                condition,
                flags=re.I | re.S,
            )
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*\s+LIKE\s+'[^']*'", condition, flags=re.I | re.S)
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*\s*(?:>=|<=|>|<)\s*-?\d+(?:\.\d+)?", condition, flags=re.S)
            or re.fullmatch(
                r"(?:NOT\s+)?[A-Za-z_][A-Za-z0-9_.]*\s+IN\s*\((?:\s*'[^']*'\s*,?)+\)",
                condition,
                flags=re.I | re.S,
            )
            # [NOT] IN (SELECT ...) semi/anti-join: admitted ONLY when the
            # inner sobject/field/conditions are themselves fully supported.
            or OwnedSalesforce._is_admissible_in_subquery(condition)
        )

    @staticmethod
    def _like_matches(actual: str, pattern: str) -> bool:
        """SOQL LIKE, anchored like live Salesforce: 'Acme%' must not match
        'Big Acme'. `%` spans any run, `_` one character; `\\%`/`\\_` are
        literals. Caller lowercases both sides (SOQL LIKE is
        case-insensitive)."""
        regex = ""
        idx = 0
        while idx < len(pattern):
            char = pattern[idx]
            if char == "\\" and idx + 1 < len(pattern) and pattern[idx + 1] in "%_":
                regex += re.escape(pattern[idx + 1])
                idx += 2
                continue
            if char == "%":
                regex += ".*"
            elif char == "_":
                regex += "."
            else:
                regex += re.escape(char)
            idx += 1
        return re.fullmatch(regex, actual, flags=re.S) is not None

    @classmethod
    def _matches_query_condition(cls, fields: dict[str, Any], condition: str) -> bool:
        exact = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*'([^']*)'", condition, flags=re.S)
        if exact:
            actual = cls._field_lookup(fields, exact.group(1))
            return _same_salesforce_value(
                actual,
                exact.group(2).replace("\\'", "'"),
            )
        like = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.]*)\s+LIKE\s+'([^']*)'", condition, flags=re.I | re.S)
        if like:
            actual = str(cls._field_lookup(fields, like.group(1)) or "").lower()
            pattern = like.group(2).replace("\\'", "'").lower()
            return cls._like_matches(actual, pattern)
        numeric = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_.]*)\s*(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)",
            condition,
            flags=re.S,
        )
        if numeric:
            actual = cls._field_lookup(fields, numeric.group(1))
            try:
                actual_number = float(actual)
                expected_number = float(numeric.group(3))
            except (TypeError, ValueError):
                return False
            op = numeric.group(2)
            if op == ">":
                return actual_number > expected_number
            if op == "<":
                return actual_number < expected_number
            if op == ">=":
                return actual_number >= expected_number
            if op == "<=":
                return actual_number <= expected_number
        in_list = re.fullmatch(
            r"(NOT\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s+IN\s*\((.+)\)",
            condition,
            flags=re.I | re.S,
        )
        if in_list:
            actual = str(cls._field_lookup(fields, in_list.group(2)) or "")
            expected = [item.replace("\\'", "'") for item in re.findall(r"'([^']*)'", in_list.group(3))]
            found = actual in expected
            return not found if in_list.group(1) else found
        not_equal = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_.]*)\s*(?:!=|<>)\s*'([^']*)'", condition, flags=re.S)
        if not_equal:
            actual = cls._field_lookup(fields, not_equal.group(1))
            return not _same_salesforce_value(
                actual,
                not_equal.group(2).replace("\\'", "'"),
            )
        string_compare = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_.]*)\s*(>=|<=|>|<)\s*'([^']*)'", condition, flags=re.S
        )
        if string_compare:
            # SOQL id/string ordering (keyset pagination: Id > '<cursor>').
            actual = str(cls._field_lookup(fields, string_compare.group(1)) or "")
            literal = string_compare.group(3).replace("\\'", "'")
            op = string_compare.group(2)
            if op == ">":
                return actual > literal
            if op == "<":
                return actual < literal
            if op == ">=":
                return actual >= literal
            return actual <= literal
        keyword = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_.]*)\s*(=|!=|<>)\s*(TRUE|FALSE|NULL)",
            condition,
            flags=re.I | re.S,
        )
        if keyword:
            actual = cls._field_lookup(fields, keyword.group(1))
            literal = keyword.group(3).upper()
            if literal == "NULL":
                matches = actual is None
            else:
                matches = str(actual).strip().lower() == literal.lower()
            return matches if keyword.group(2) == "=" else not matches
        last_n_days = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_.]*)\s*(>=|<=|<>|!=|=|>|<)\s*LAST_N_DAYS\s*:\s*(\d+)",
            condition,
            flags=re.I | re.S,
        )
        if last_n_days:
            # SOQL LAST_N_DAYS:n — a RANGE from start of day n days ago through
            # now (UTC). Inequalities compare against the range per SOQL date-
            # literal semantics: >= within-or-after start, > after end,
            # < before start, <= within-or-before end.
            actual = cls._field_lookup(fields, last_n_days.group(1))
            if actual in (None, ""):
                return False
            from datetime import datetime, timedelta, timezone
            text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", str(actual)).replace("Z", "+00:00")
            try:
                when = datetime.fromisoformat(text)
            except ValueError as exc:
                raise RuntimeError(
                    f"unparseable date value for LAST_N_DAYS: {actual!r}"
                ) from exc
            now = datetime.now(timezone.utc)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            window_start = (now - timedelta(days=int(last_n_days.group(3)))).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            operator = last_n_days.group(2)
            if operator == "=":
                return window_start <= when <= now
            if operator in ("<>", "!="):
                return not (window_start <= when <= now)
            if operator == ">=":
                return when >= window_start
            if operator == ">":
                return when > now
            if operator == "<=":
                return when <= now
            return when < window_start
        not_in = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_.]*)\s+NOT\s+IN\s*\((.+)\)",
            condition,
            flags=re.I | re.S,
        )
        if not_in:
            actual = str(cls._field_lookup(fields, not_in.group(1)) or "")
            expected = [item.replace("\\'", "'") for item in re.findall(r"'([^']*)'", not_in.group(2))]
            return actual not in expected
        not_like = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_.]*)\s+NOT\s+LIKE\s+'([^']*)'", condition, flags=re.I | re.S
        )
        if not_like:
            actual = str(cls._field_lookup(fields, not_like.group(1)) or "").lower()
            pattern = not_like.group(2).replace("\\'", "'").lower()
            return not cls._like_matches(actual, pattern)
        includes = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_.]*)\s+INCLUDES\s*\((.+)\)", condition, flags=re.I | re.S
        )
        if includes:
            # Multipicklist: the stored value is semicolon-separated; each
            # quoted argument may itself be a semicolon-joined combination.
            actual_parts = {
                part.strip()
                for part in str(cls._field_lookup(fields, includes.group(1)) or "").split(";")
                if part.strip()
            }
            for item in re.findall(r"'([^']*)'", includes.group(2)):
                wanted = {part.strip() for part in item.replace("\\'", "'").split(";") if part.strip()}
                if wanted and wanted <= actual_parts:
                    return True
            return False
        return False

    @staticmethod
    def _field_lookup(fields: dict[str, Any], field: str) -> Any:
        if field in fields:
            return fields.get(field)
        parts = str(field).split(".")
        if len(parts) > 1:
            # Walk dotted relationship paths into expansion-attached parent
            # dicts (Opportunity.AccountId over an OCR row), case-insensitive
            # per segment.
            node: Any = fields
            for part in parts:
                if not isinstance(node, dict):
                    node = None
                    break
                lower = {str(key).lower(): value for key, value in node.items()}
                node = lower.get(part.lower())
            if node is not None:
                return node
        field_tail = parts[-1]
        if field_tail in fields:
            return fields.get(field_tail)
        lower_map = {str(key).lower(): value for key, value in fields.items()}
        return lower_map.get(str(field).lower(), lower_map.get(field_tail.lower()))

    @staticmethod
    def _soql_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def _readback_extra_fields(self, physical_sobject: str) -> list[str]:
        """Live-readable columns beyond the seeded set: auto-number identifiers
        (CaseNumber/ContractNumber), derived flags (IsClosed), and the record
        name field. These are real org-assigned values recipes filter on and
        verifiers assert; reading them back live is strictly faithful."""
        cache = getattr(self.client, "_readback_extra_cache", None)
        if cache is None:
            cache = {}
            self.client._readback_extra_cache = cache
        if physical_sobject not in cache:
            extras: list[str] = []
            try:
                fields = self.client.describe(physical_sobject).get("fields", [])
            except SalesforceError:
                fields = []
            for f in fields:
                name = str(f.get("name"))
                if (
                    f.get("autoNumber")
                    or f.get("nameField")
                    or name in {"IsClosed", "IsWon", "CreatedDate", "LastModifiedDate"}
                    or name in self._RELATED_NAME_LOOKUPS
                ):
                    extras.append(name)
            cache[physical_sobject] = extras
        return cache[physical_sobject]

    def _logical_aliases(self, physical_sobject: str, fields: dict[str, Any]) -> None:
        """Expose logical field names alongside mapped physical ones (both refer
        to the same live value), so recipe filters/verifiers using the logical
        name resolve against real read-back data."""
        for (map_sobject, logical), physical in SALESFORCE_FIELD_MAP.items():
            if physical in fields and logical not in fields:
                fields[logical] = fields[physical]

    def _read(self, sobject: str, record_id: str, fields: list[str]) -> dict[str, Any] | None:
        """Live record read. Returns None ONLY when the record does not exist
        (404 — e.g. the recipe deleted it); any other live API failure raises
        instead of masquerading as an absent record."""
        cols = ["Id"] + [field for field in fields if field != "Id"]
        try:
            return self.client.get(sobject, record_id, fields=cols)
        except SalesforceError as exc:
            if exc.status == 404:
                return None
            raise

    def _physical_fields(self, sobject: str, fields: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in (fields or {}).items():
            key = str(key)
            if key.startswith("_") or value in (None, "", [], {}):
                continue
            if isinstance(value, (dict, list)):
                continue
            physical_key = self._physical_field_name(sobject, key)
            meta = self._field_meta(sobject, physical_key)
            if not meta:
                raise RuntimeError(f"Salesforce field {sobject}.{physical_key} is not available")
            if not meta.get("createable", False):
                raise RuntimeError(f"Salesforce field {sobject}.{physical_key} is not createable")
            if meta.get("type") == "reference" and not self._looks_sf_id(value):
                raise RuntimeError(f"Salesforce reference field {sobject}.{physical_key} requires a live Salesforce id")
            out[physical_key] = value
        return out

    def _physical_update_fields(self, sobject: str, fields: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in (fields or {}).items():
            key = str(key)
            if key.startswith("_") or key in {"Id", "id"}:
                continue
            if isinstance(value, (dict, list)):
                continue
            physical_key = self._physical_field_name(sobject, key)
            meta = self._field_meta(sobject, physical_key)
            if not meta or not meta.get("updateable", False):
                raise RuntimeError(f"Salesforce field {sobject}.{physical_key} is not updateable")
            if meta.get("type") == "reference" and value not in (None, "") and not self._looks_sf_id(value):
                raise RuntimeError(f"Salesforce reference field {sobject}.{physical_key} requires a live Salesforce id")
            out[physical_key] = None if value == "" else value
        return out

    @staticmethod
    def _physical_field_name(sobject: str, field: str) -> str:
        return SALESFORCE_FIELD_MAP.get((str(sobject), str(field)), str(field))

    @staticmethod
    def _physical_sobject_name(sobject: str) -> str:
        return SALESFORCE_SOBJECT_MAP.get(str(sobject), str(sobject))

    def _required_field_names(self, sobject: str) -> list[str]:
        """Org-required, non-defaulted, createable fields for the sobject.
        Describe failures raise; the harness never invents values for these —
        the variant seed must declare them explicitly."""
        if sobject in self.client._required_cache:
            return self.client._required_cache[sobject]
        fields = self.client.describe(sobject).get("fields", [])
        out = [
            str(field["name"])
            for field in fields
            if field.get("createable")
            and not field.get("nillable")
            and not field.get("defaultedOnCreate")
            and field.get("type") != "boolean"
        ]
        if sobject == "ContentVersion" and "ContentDocumentId" in out:
            # Describe marks it required, but Salesforce DERIVES it when the
            # first version of a new document is created (it must be omitted).
            out.remove("ContentDocumentId")
        self.client._required_cache[sobject] = out
        return out


    def _field_names(self, sobject: str) -> set[str]:
        if sobject not in self.client._field_cache:
            self.client._field_cache[sobject] = {
                str(field.get("name"))
                for field in self.client.describe(sobject).get("fields", [])
            }
        return self.client._field_cache[sobject]

    def _field_meta(self, sobject: str, field: str) -> dict[str, Any]:
        if sobject not in self.client._field_meta_cache:
            self.client._field_meta_cache[sobject] = {
                str(row.get("name")): row
                for row in self.client.describe(sobject).get("fields", [])
            }
        return self.client._field_meta_cache[sobject].get(field) or {}

    @staticmethod
    def _looks_sf_id(value: Any) -> bool:
        return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?", value))

    @staticmethod
    def _query_terms(query: str) -> set[str]:
        raw = str(query or "").lower()
        terms = {term for pair in re.findall(r"'([^']*)'|\"([^\"]*)\"", raw) for term in pair if term}
        stop = {
            "name", "id", "and", "or", "not", "like", "where", "select",
            "from", "in", "null", "true", "false", "contains", "recordtype",
        }
        for word in re.findall(r"[a-z0-9_@.]+", raw):
            if len(word) >= 3 and word not in stop and not word.isdigit():
                terms.add(word)
        return terms


def provision_records(section: dict[str, Any]) -> dict[str, Any]:
    salesforce = OwnedSalesforce()
    try:
        salesforce.provision(section or {})
    except Exception as exc:
        rollback_failures = salesforce.delete_owned()
        if rollback_failures:
            # Surface BOTH the original error and what the rollback left
            # behind — hiding either would violate fail-fast cleanup.
            raise RuntimeError(
                f"Salesforce provisioning failed AND rollback left live records: "
                f"{rollback_failures}"
            ) from exc
        raise
    return {
        "ok": True,
        "state": salesforce.export_state(),
        "snapshot": salesforce.snapshot(),
    }


class SalesforceRun:
    def __init__(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict) or not state.get("run_id"):
            raise RuntimeError("seed file missing Salesforce live state")
        self.salesforce = OwnedSalesforce(state)

    def search_records(
        self,
        sobject: str,
        query: str,
        filters: list[dict[str, Any]] | None = None,
        limit: Any | None = None,
    ) -> dict[str, Any]:
        records = self.salesforce.search_records(str(sobject), str(query or ""), filters or [])
        if self.salesforce.strict_soql:
            # Full SOQL semantics under the strict flag only: ORDER BY applies
            # (keyset pagination cursors depend on it); legacy recipes keep
            # seed order.
            records = OwnedSalesforce._apply_order_by(str(query or ""), records)
        if limit not in (None, ""):
            try:
                limit_int = int(limit)
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"Salesforce search limit must be an integer: {limit}") from exc
            if limit_int < 0:
                raise RuntimeError(f"Salesforce search limit must be non-negative: {limit}")
            records = records[:limit_int]
        return {
            "ok": True,
            "sobject": str(sobject),
            "query": str(query or ""),
            "filters": filters or [],
            "limit": limit,
            "records": records,
            "count": len(records),
            "list_size": len(records),
            "totalSize": len(records),
        }

    def update_record(self, sobject: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(fields, dict):
            raise RuntimeError("Salesforce update fields must be an object")
        return self.salesforce.update_record(str(sobject), str(record_id or ""), fields)

    def create_record(self, sobject: str, fields: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(fields, dict):
            raise RuntimeError("Salesforce create fields must be an object")
        return self.salesforce.create_record(str(sobject), fields)

    def upsert_record(self, sobject: str, key_field: str, fields: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(fields, dict):
            raise RuntimeError("Salesforce upsert fields must be an object")
        return self.salesforce.upsert_record(str(sobject), str(key_field or ""), fields)

    def snapshot(self) -> dict[str, Any]:
        return {"ok": True, **self.salesforce.snapshot()}

    def cleanup(self) -> dict[str, Any]:
        failures = self.salesforce.delete_owned()
        leftovers = self.salesforce.scan_owned()
        if failures or leftovers:
            # Required cleanup is fail-fast (cleanup principle): a leftover
            # live record must ABORT the run loudly — returning ok:false is
            # not enough because ToolRegistry.call does not raise on it and
            # recipe/verifier paths could complete green over leaked state.
            raise RuntimeError(
                f"Salesforce cleanup failed: leftovers={leftovers} "
                f"delete_failures={failures} run_id={self.salesforce.run_id}"
            )
        return {
            "ok": True,
            "leftovers": [],
            "delete_failures": [],
            "run_id": self.salesforce.run_id,
        }
