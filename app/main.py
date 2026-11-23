from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database.connection import init_db
from app.middleware.request_id import RequestIdMiddleware, get_request_id
from app.routes.submissions import router as submissions_router
from app.schemas.submission import ErrorBody, HealthResponse
from app.services.errors import ServiceError
from app.utils.response import success


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Submission File Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={
        "success": False,
        "error": {"code": exc.code, "message": exc.message},
        "meta": {"request_id": get_request_id(request)},
    })


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={
        "success": False,
        "error": {"code": "invalid_request", "message": "Request tidak valid"},
        "meta": {"request_id": get_request_id(request)},
    })


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={
        "success": False,
        "error": {"code": "internal_error", "message": "Terjadi kesalahan internal"},
        "meta": {"request_id": get_request_id(request)},
    })


@app.get("/health", response_model=HealthResponse)
async def health(request: Request):
    return success(request, {"service": get_settings().service_name, "status": "healthy"})


app.include_router(submissions_router, prefix=get_settings().api_prefix)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    # RequestValidationError is mapped to HTTP 400 by this service's handler.
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            responses = operation.get("responses", {})
            if "400" in responses:
                responses.pop("422", None)
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
