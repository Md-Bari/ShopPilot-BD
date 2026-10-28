"""Public Meta webhook endpoints. Authenticity is proven by the verify token (GET)
and the X-Hub-Signature-256 HMAC of the raw body (POST)."""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.concurrency import run_in_threadpool

from app.api.deps import DbDep, SettingsDep
from app.application.whatsapp.webhooks import WebhookProcessor, mark_webhook_verified
from app.core.security import constant_time_equals
from app.infrastructure.whatsapp.signature import verify_signature

log = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": {}}})


@router.get("/webhooks/whatsapp/", response_class=PlainTextResponse)
@router.get("/webhooks/whatsapp", response_class=PlainTextResponse, include_in_schema=False)
def verify_webhook(
    db: DbDep,
    settings: SettingsDep,
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge", max_length=200)] = None,
):
    if not settings.meta_verify_token:
        return _error(503, "not_configured", "META_VERIFY_TOKEN is not configured.")
    if mode == "subscribe" and verify_token and challenge and constant_time_equals(verify_token,
                                                                                   settings.meta_verify_token):
        mark_webhook_verified(db)
        return PlainTextResponse(challenge)
    return _error(403, "verification_failed", "Webhook verification failed.")


@router.post("/webhooks/whatsapp/")
@router.post("/webhooks/whatsapp", include_in_schema=False)
async def receive_webhook(request: Request, db: DbDep, settings: SettingsDep):
    if not settings.meta_app_secret:
        # Never accept unsigned webhooks.
        return _error(503, "not_configured", "META_APP_SECRET is not configured.")
    raw_body = await request.body()
    if not verify_signature(settings.meta_app_secret, raw_body, request.headers.get("X-Hub-Signature-256")):
        log.warning("Rejected webhook with invalid signature from %s", request.client.host if request.client else "?")
        return _error(401, "invalid_signature", "Invalid webhook signature.")
    try:
        payload = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        return _error(400, "malformed_payload", "Webhook body is not valid JSON.")

    summary = await run_in_threadpool(WebhookProcessor(db).process, payload)
    if summary["failed"]:
        log.error("Webhook processed with failures: %s", summary)
    return {"received": True, **summary}
