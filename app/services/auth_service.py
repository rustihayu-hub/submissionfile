import httpx

from app.config import get_settings
from app.services.errors import ServiceError


async def authenticate(authorization: str | None, request_id: str) -> dict:
    if not authorization or not authorization.lower().startswith("bearer ") or not authorization[7:].strip():
        raise ServiceError(401, "unauthorized", "Bearer token diperlukan")
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.dependency_timeout_seconds) as client:
            response = await client.get(settings.auth_service_url.rstrip("/") + settings.auth_validate_path,
                                        headers={settings.auth_token_header: authorization, "X-Request-ID": request_id})
    except httpx.TimeoutException as exc:
        raise ServiceError(504, "auth_timeout", "Authentication Service timeout") from exc
    except httpx.RequestError as exc:
        raise ServiceError(503, "auth_unavailable", "Authentication Service tidak tersedia") from exc
    if response.status_code in (401, 403):
        raise ServiceError(401, "unauthorized", "Token tidak valid")
    if response.status_code >= 500:
        raise ServiceError(503, "auth_unavailable", "Authentication Service gagal")
    if response.status_code != 200:
        raise ServiceError(502, "invalid_dependency_response", "Authentication Service mengembalikan status yang tidak terduga")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ServiceError(502, "invalid_dependency_response", "Respons Authentication Service tidak valid") from exc
    user = payload.get("data", payload) if isinstance(payload, dict) else None
    user_id = user.get("id", user.get("sub")) if isinstance(user, dict) else None
    if not user_id:
        raise ServiceError(401, "unauthorized", "Token tidak valid")
    return {"id": str(user_id)}
