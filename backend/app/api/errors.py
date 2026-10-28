"""Maps domain errors and framework errors to a consistent JSON shape:
{"error": {"code": str, "message": str, "details": {...}}}"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain import errors as e

log = logging.getLogger(__name__)

STATUS_BY_ERROR: list[tuple[type[e.DomainError], int]] = [
    (e.ValidationError, 422),
    (e.NotFoundError, 404),
    (e.ConflictError, 409),
    (e.AuthenticationError, 401),
    (e.PermissionDeniedError, 403),
    (e.PlanLimitError, 402),
    (e.MessagingPolicyError, 422),
    (e.ConfigurationError, 409),
    (e.RateLimitedError, 429),
    (e.ExternalServiceError, 502),
]


def _body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(e.DomainError)
    async def domain_error(_: Request, exc: e.DomainError):
        status = next((code for cls, code in STATUS_BY_ERROR if isinstance(exc, cls)), 400)
        return JSONResponse(status_code=status, content=_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(_: Request, exc: RequestValidationError):
        fields = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        message = fields[0]["message"] if fields else "Invalid request."
        return JSONResponse(status_code=422, content=_body("validation_error", message, {"fields": fields}))

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        code = {400: "bad_request", 401: "not_authenticated", 403: "forbidden", 404: "not_found",
                405: "method_not_allowed", 413: "payload_too_large"}.get(exc.status_code, "http_error")
        return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)),
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content=_body("internal_error", "Something went wrong. Please try again."))
