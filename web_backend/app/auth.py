from dataclasses import dataclass
from typing import Annotated

import requests
from fastapi import Depends, Header, HTTPException

from web_backend.app.settings import get_settings
from web_backend.app.supabase_rest import SupabaseRest


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    access_token: str


def require_user(authorization: Annotated[str | None, Header()] = None) -> AuthenticatedUser:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Supabase authentication is not configured.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    try:
        response = requests.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"},
            timeout=(5, 15),
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Authentication service is unavailable.") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Your session is invalid or has expired.")
    try:
        payload = response.json()
        user_id = str(payload["id"])
        email = str(payload.get("email") or "")
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Authentication service returned invalid data.") from exc
    return AuthenticatedUser(id=user_id, email=email, access_token=token)


def supabase_for_user(user: Annotated[AuthenticatedUser, Depends(require_user)]) -> SupabaseRest:
    return SupabaseRest(user.access_token, user.id)
