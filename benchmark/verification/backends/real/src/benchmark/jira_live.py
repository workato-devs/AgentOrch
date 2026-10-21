from __future__ import annotations

import base64
import json
import urllib.request
from typing import Any

from .config import ENV_FILE


class JiraLiveClient:
    def __init__(self) -> None:
        values = _load_env()
        self.base_url = values.get("JIRA_BASE_URL", "").rstrip("/")
        self.email = values.get("JIRA_EMAIL", "")
        self.token = values.get("JIRA_API_TOKEN", "")
        if not self.base_url or not self.email or not self.token:
            raise RuntimeError("missing Jira credentials")

    def call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {
            "Accept": "application/json",
            "Authorization": "Basic " + base64.b64encode(f"{self.email}:{self.token}".encode()).decode(),
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode()
            body = json.loads(raw) if raw else {}
        return body if isinstance(body, dict) else {"result": body}

    def create_issue(self, args: dict[str, Any]) -> dict[str, Any]:
        project, issue_type = _project_issue_type(str(args.get("project_issuetype") or ""))
        summary = str(args.get("summary") or "").strip()
        if not summary:
            raise RuntimeError("Jira issue summary is empty; refusing to substitute placeholder text")
        fields: dict[str, Any] = {
            "project": {"key": project},
            "issuetype": {"name": issue_type},
            "summary": summary,
        }
        description = str(args.get("description") or "")
        if description:
            fields["description"] = _adf_text(description)
        labels = _labels(args.get("labels"))
        if labels:
            fields["labels"] = labels
        priority = str(args.get("priority") or "").strip()
        if priority:
            fields["priority"] = {"name": priority}
        result = self.call("POST", "/rest/api/3/issue", {"fields": fields})
        return {"ok": True, **result}

    def delete_issue(self, issue_key: str) -> dict[str, Any]:
        if not issue_key:
            raise RuntimeError("missing Jira issue key")
        self.call("DELETE", f"/rest/api/3/issue/{issue_key}")
        return {"ok": True, "key": issue_key}


def _load_env() -> dict[str, str]:
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


def _project_issue_type(value: str) -> tuple[str, str]:
    if "--" in value:
        project, issue_type = value.split("--", 1)
        return project, issue_type
    if "@@" in value:
        _title, project = value.split("@@", 1)
        return project, "Task"
    raise RuntimeError(f"unsupported Jira project_issuetype: {value}")


def _labels(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().replace(" ", "-") for item in value if str(item).strip()]
    text = str(value or "").strip()
    if not text:
        return []
    return [item.strip().replace(" ", "-") for item in text.split(",") if item.strip()]


def _adf_text(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }
