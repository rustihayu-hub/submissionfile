import httpx

from app.config import get_settings
from app.services.errors import ServiceError


async def ensure_assignment_exists(assignment_id: str, request_id: str, authorization: str | None = None):
    settings = get_settings()
    path = settings.assignment_validate_path.format(assignment_id=assignment_id)
    try:
        async with httpx.AsyncClient(timeout=settings.dependency_timeout_seconds) as client:
            headers = {"X-Request-ID": request_id}
            if authorization:
                headers["Authorization"] = authorization
            response = await client.get(settings.assignment_service_url.rstrip("/") + path, headers=headers)
    except httpx.TimeoutException as exc:
        raise ServiceError(504, "assignment_timeout", "Assignment Service timeout") from exc
    except httpx.RequestError as exc:
        raise ServiceError(503, "assignment_unavailable", "Assignment Service tidak tersedia") from exc
    if response.status_code >= 500:
        raise ServiceError(503, "assignment_unavailable", "Assignment Service gagal")
    if response.status_code == 404:
        raise ServiceError(400, "invalid_assignment", "assignment_id tidak valid")
    if response.status_code in (401, 403):
        raise ServiceError(502, "invalid_dependency_response", "Assignment Service masih meminta autentikasi")
    if response.status_code != 200:
        raise ServiceError(502, "invalid_dependency_response", "Assignment Service mengembalikan status yang tidak terduga")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ServiceError(502, "invalid_dependency_response", "Respons Assignment Service tidak valid") from exc
    # Expected adapter contract is intentionally explicit and replaceable.
    if not isinstance(payload, dict):
        raise ServiceError(502, "invalid_dependency_response", "Respons Assignment Service tidak valid")
    data = payload.get("data", payload)
    if isinstance(data, list):
        data = next((item for item in data if isinstance(item, dict) and str(item.get("id")) == assignment_id), None)
    if payload.get("success") is False or not isinstance(data, dict) or str(data.get("id")) != assignment_id:
        raise ServiceError(400, "invalid_assignment", "assignment_id tidak valid")
