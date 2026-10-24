"""Application entry point.

Run from the repository root:

    uvicorn main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware

from src.api.routes import error_response, router
from src.core.cache import ResponseCache
from src.core.config import Settings, get_settings
from src.core.exceptions import EventCraftError
from src.core.security import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TokenBucketLimiter,
)
from src.services.llm_orchestrator import LlmOrchestrator

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "src" / "web" / "templates"
STATIC_DIR = ROOT / "src" / "web" / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI app.

    Args:
        settings: Explicit settings for tests. When omitted, values come from
            the environment and an optional ``.env`` file.

    Returns:
        A FastAPI application with security middleware, the JSON API, and the
        planner page.
    """
    settings = settings or get_settings()
    templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.http = httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=5.0))
        application.state.orchestrator = LlmOrchestrator(
            application.state.settings,
            application.state.http,
        )
        try:
            yield
        finally:
            await application.state.http.aclose()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="Context-aware planner for weddings, birthdays, and community events.",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.cache = ResponseCache(settings.cache_max_entries, settings.cache_ttl_seconds)
    application.state.limiter = TokenBucketLimiter(settings.rate_limit_per_minute)

    # The last middleware added is the outermost. Headers wrap every response,
    # including the 413 and 429 responses from the inner layers.
    application.add_middleware(RateLimitMiddleware)
    application.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(GZipMiddleware, minimum_size=500)

    application.include_router(router)
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @application.get("/", include_in_schema=False)
    def index(request: Request):
        """Serve the planner page."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"request": request, "app_version": settings.app_version},
        )

    @application.exception_handler(EventCraftError)
    async def handle_domain_error(_request: Request, exc: EventCraftError) -> JSONResponse:
        """Map a domain error onto the planner's JSON error shape."""
        return error_response(exc)

    @application.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        """Map a schema failure onto the planner's JSON error shape."""
        details: list[str] = []
        for error in exc.errors()[:8]:
            location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            message = str(error.get("msg", "invalid"))
            details.append(f"{location}: {message}"[:200])
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "The request did not match the planner schema.",
                    "details": details,
                }
            },
        )

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
