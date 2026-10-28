"""Application factory and composition root."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine, text

from app.api.errors import register_error_handlers
from app.api.routes import auth, businesses, customers, orders, products, reports, subscriptions, webhooks, whatsapp
from app.application.ports import EmailSender, WhatsAppGateway
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import RateLimiter
from app.infrastructure.db.session import build_engine, build_session_factory
from app.infrastructure.email.console import ConsoleEmailSender
from app.infrastructure.storage.local import LocalFileStorage
from app.infrastructure.whatsapp.credentials import SettingsCredentialProvider
from app.infrastructure.whatsapp.meta_client import MetaCloudApiClient


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    whatsapp_gateway: WhatsAppGateway | None = None,
    email_sender: EmailSender | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    if settings.is_production and (problems := settings.production_problems()):
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))

    engine = engine or build_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(
        title="ShopPilot BD API",
        version="0.1.0",
        description="Multi-tenant commerce + WhatsApp Cloud API backend for Bangladeshi online sellers.",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    app.state.settings = settings
    app.state.session_factory = build_session_factory(engine)
    app.state.rate_limiter = RateLimiter()
    app.state.whatsapp_gateway = whatsapp_gateway or MetaCloudApiClient(settings.meta_http_timeout_seconds)
    app.state.credential_provider = SettingsCredentialProvider(settings)
    app.state.email_sender = email_sender or ConsoleEmailSender()
    app.state.storage = LocalFileStorage(settings.media_dir, settings.media_url_prefix)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Business-Id", "Idempotency-Key", "Authorization"],
    )
    app.add_middleware(BodySizeLimitMiddleware, default_limit=settings.max_request_bytes,
                       path_limits={"/webhooks/": settings.max_webhook_bytes})
    app.add_middleware(SecurityHeadersMiddleware)
    register_error_handlers(app)

    for module in (auth, businesses, products, customers, orders, reports, whatsapp, subscriptions, webhooks):
        app.include_router(module.router)

    @app.get("/api/health", tags=["health"])
    def health():
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    app.mount(settings.media_url_prefix, StaticFiles(directory=settings.media_dir), name="media")
    return app
