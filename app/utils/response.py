from fastapi import Request
from fastapi.responses import JSONResponse

from app.middleware.request_id import get_request_id


def success(request: Request, data: dict, status_code: int = 200) -> JSONResponse:
    """Build the standard successful API response envelope."""
    return JSONResponse(status_code=status_code, content={
        "success": True,
        "data": data,
        "meta": {"request_id": get_request_id(request)},
    })
