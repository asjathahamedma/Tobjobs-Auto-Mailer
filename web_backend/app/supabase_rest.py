from typing import Any
from urllib.parse import quote

import requests
from fastapi import HTTPException

from web_backend.app.settings import get_settings


class SupabaseRest:
    def __init__(
        self,
        access_token: str,
        user_id: str | None = None,
        *,
        service_role: bool = False,
    ):
        settings = get_settings()
        api_key = settings.supabase_service_role_key if service_role else settings.supabase_anon_key
        if not settings.supabase_url or not api_key:
            raise HTTPException(status_code=503, detail="Supabase backend is not configured.")
        self.base_url = settings.supabase_url.rstrip("/")
        self.anon_key = api_key
        self.access_token = access_token
        self.user_id = user_id
        self.service_role = service_role

    def request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,
        headers: dict[str, str] | None = None,
        prefer: str | None = None,
    ) -> Any:
        request_headers = {
            "apikey": self.anon_key,
            "Authorization": (
                f"Bearer {self.access_token}"
                if not self.service_role
                else f"Bearer {self.anon_key}"
            ),
            "Accept": "application/json",
        }
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        if prefer:
            request_headers["Prefer"] = prefer
        if headers:
            request_headers.update(headers)

        try:
            response = requests.request(
                method,
                f"{self.base_url}/rest/v1/{quote(table, safe='(),.*')}",
                params=params,
                json=body,
                headers=request_headers,
                timeout=(5, 25),
            )
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail="Database service is unavailable.") from exc

        if not response.ok:
            try:
                details = response.json().get("message", "Database request failed.")
            except ValueError:
                details = "Database request failed."
            raise HTTPException(status_code=502, detail=details)

        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="Database returned invalid JSON.") from exc

    def count(self, table: str, *, params: dict[str, Any] | None = None) -> int:
        request_headers = {
            "apikey": self.anon_key,
            "Authorization": (
                f"Bearer {self.access_token}"
                if not self.service_role
                else f"Bearer {self.anon_key}"
            ),
            "Prefer": "count=exact",
            "Range": "0-0",
        }
        try:
            response = requests.get(
                f"{self.base_url}/rest/v1/{quote(table, safe='(),.*')}",
                params={"select": "*", **(params or {})},
                headers=request_headers,
                timeout=(5, 25),
            )
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail="Database service is unavailable.") from exc
        if not response.ok:
            raise HTTPException(status_code=502, detail="Could not calculate dashboard analytics.")
        content_range = response.headers.get("Content-Range", "*/0")
        try:
            return int(content_range.rsplit("/", 1)[1])
        except (IndexError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="Database returned an invalid row count.") from exc

    def storage_request(
        self,
        method: str,
        path: str,
        *,
        content: bytes | None = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ):
        headers = {
            "apikey": self.anon_key,
            "Authorization": (
                f"Bearer {self.access_token}"
                if not self.service_role
                else f"Bearer {self.anon_key}"
            ),
        }
        if content_type:
            headers["Content-Type"] = content_type
        if extra_headers:
            headers.update(extra_headers)
        try:
            response = requests.request(
                method,
                f"{self.base_url}/storage/v1/{path.lstrip('/')}",
                data=content,
                headers=headers,
                timeout=(5, 60),
            )
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail="Resume storage is unavailable.") from exc
        if not response.ok:
            raise HTTPException(status_code=502, detail="Resume storage request failed.")
        return response
