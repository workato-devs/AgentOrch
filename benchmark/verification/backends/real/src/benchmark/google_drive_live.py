from __future__ import annotations

import json
import os
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


API = "https://www.googleapis.com/drive/v3"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class GoogleDriveError(RuntimeError):
    def __init__(self, status: int, body: Any) -> None:
        self.status = status
        self.body = body
        super().__init__(f"Google Drive {status}: {body}")


class GoogleDriveLiveClient:
    def __init__(self) -> None:
        ca_file = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
        self.ssl_context = (
            ssl.create_default_context(cafile=ca_file)
            if ca_file
            else ssl.create_default_context()
        )
        self.token: str | None = None

    def _auth(self) -> None:
        out = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if out.returncode != 0:
            raise RuntimeError(f"gcloud token failed: {(out.stderr or '')[:200]}")
        token = out.stdout.strip()
        if not token:
            raise RuntimeError("gcloud returned an empty access token")
        self.token = token

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.token:
            self._auth()
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(2):
            request = urllib.request.Request(
                API + path,
                data=data,
                method=method,
                headers={
                    "Authorization": "Bearer " + str(self.token),
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(request, context=self.ssl_context, timeout=60) as response:
                    raw = response.read().decode()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as exc:
                raw_body: Any = exc.read().decode()
                try:
                    raw_body = json.loads(raw_body)
                except Exception:
                    pass
                if exc.code == 401 and attempt == 0:
                    self._auth()
                    continue
                raise GoogleDriveError(exc.code, raw_body) from exc
        raise RuntimeError("unreachable Google Drive retry state")

    def create_folder(self, parent_id: str, name: str) -> dict[str, Any]:
        if not parent_id:
            raise RuntimeError("google_drive.create_folder missing parent folder id")
        if not name:
            raise RuntimeError("google_drive.create_folder missing name")
        query = urllib.parse.urlencode(
            {
                "supportsAllDrives": "true",
                "fields": "id,name,mimeType,parents,webViewLink",
            }
        )
        response = self.request(
            "POST",
            f"/files?{query}",
            {
                "name": name,
                "mimeType": FOLDER_MIME_TYPE,
                "parents": [parent_id],
            },
        )
        folder_id = str(response.get("id") or "")
        if not folder_id:
            raise RuntimeError(f"Google Drive create folder returned no id: {response}")
        return {
            "ok": True,
            "id": folder_id,
            "name": str(response.get("name") or name),
            "mimeType": str(response.get("mimeType") or FOLDER_MIME_TYPE),
            "parents": response.get("parents") if isinstance(response.get("parents"), list) else [parent_id],
            "webViewLink": response.get("webViewLink"),
        }

    def delete_file(self, file_id: str) -> dict[str, Any]:
        if not file_id:
            raise RuntimeError("google_drive.delete_file missing file id")
        query = urllib.parse.urlencode({"supportsAllDrives": "true"})
        self.request("DELETE", f"/files/{urllib.parse.quote(file_id, safe='')}?{query}")
        return {"ok": True, "id": file_id}
