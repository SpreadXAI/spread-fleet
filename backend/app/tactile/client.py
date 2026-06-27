"""HTTP client for Tactile production API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from app.config import Settings


class TactileError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(f"Tactile API {status}: {detail}")


class TactileClient:
    def __init__(self, settings: Settings) -> None:
        self.base = settings.tactile_api_base.rstrip("/")
        self.api_key = settings.tactile_api_key

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise TactileError(0, "TACTILE_API_KEY not configured")
        url = f"{self.base}{path}"
        data = None
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }
        if body is not None:
            data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()
            try:
                parsed = json.loads(detail)
                detail = parsed.get("detail", detail)
            except json.JSONDecodeError:
                pass
            raise TactileError(exc.code, str(detail)) from exc

    def create_work(
        self,
        *,
        workspace_id: int,
        agent_id: int,
        name: str,
        content: str,
        dispatch_env_json: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": name,
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "content": content,
        }
        if dispatch_env_json:
            body["dispatch_env_json"] = dispatch_env_json
        return self._request("POST", "/work", body)

    def get_work(self, work_id: int) -> dict[str, Any]:
        return self._request("GET", f"/work/{work_id}")
