import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def notify_submission(data: dict, request_id: str, authorization: str | None = None):
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.dependency_timeout_seconds) as client:
            headers = {"X-Request-ID": request_id}
            if authorization:
                headers["Authorization"] = authorization
            response = await client.post(settings.notification_service_url.rstrip("/") + settings.notification_submission_path,
                                         json=data, headers=headers)
        if response.status_code >= 400:
            logger.warning("Notification delivery failed: status=%s request_id=%s", response.status_code, request_id)
    except httpx.TimeoutException as exc:
        logger.warning("Notification delivery timed out request_id=%s", request_id)
    except httpx.RequestError as exc:
        logger.warning("Notification delivery failed: %s request_id=%s", type(exc).__name__, request_id)
