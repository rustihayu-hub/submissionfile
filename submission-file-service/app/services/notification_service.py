import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def notify_submission(data: dict, request_id: str):
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.dependency_timeout_seconds) as client:
            response = await client.post(settings.notification_service_url.rstrip("/") + settings.notification_submission_path,
                                         json=data, headers={"X-Request-ID": request_id})
        if response.status_code >= 400:
            logger.warning("Notification delivery failed: status=%s request_id=%s", response.status_code, request_id)
    except httpx.HTTPError as exc:
        logger.warning("Notification delivery failed: %s request_id=%s", type(exc).__name__, request_id)
