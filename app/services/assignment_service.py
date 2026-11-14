import httpx

from app.config import get_settings
from app.services.errors import ServiceError


async def ensure_assignment_exists(assignment_id: str, request_id: str):
    settings = get_settings()
    path = settings.assignment_validate_path.format(assignment_id=assignment_id)
    try:
        async with httpx.AsyncClient(timeout=settings.dependency_timeout_seconds) as client:
            response = await client.get(settings.assignment_service_url.rstrip("/") + path,
                                        headers={"X-Request-ID": request_id})
    except httpx.TimeoutException as exc:
        raise ServiceError(504, "assignment_timeout", "Assignment Service timeout") from exc
    except httpx.RequestError as exc:
        raise ServiceError(503, "assignment_unavailable", "Assignment Service tidak tersedia") from exc
    if response.status_code == 404:
        raise ServiceError(400, "invalid_assignment", "assignment_id tidak valid")
    if response.status_code >= 500:
        raise ServiceError(503, "assignment_unavailable", "Assignment Service gagal")
    try:
        payload = response.json()
    except ValueError as exc:
        raise ServiceError(502, "invalid_dependency_response", "Respons Assignment Service tidak valid") from exc
    # Expected adapter contract is intentionally explicit and replaceable.
    if response.status_code != 200 or not isinstance(payload, dict):
        raise ServiceError(502, "invalid_dependency_response", "Respons Assignment Service tidak valid")
    if payload.get("exists") is False or payload.get("success") is False:
        raise ServiceError(400, "invalid_assignment", "assignment_id tidak valid")
