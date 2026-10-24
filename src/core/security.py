"""Input screening, request-size limits, rate limits, and response headers.

``X-Forwarded-For`` is intentionally ignored. A client can rotate that header
to dodge a per-IP limit, so the limiter uses the connection address only.
Put the app behind a proxy that overwrites the peer address if you need the
real client IP.
"""

from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections.abc import Iterable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.core.exceptions import PromptInjectionError
from src.domain.schemas import EventRequest

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|rules)",
        re.IGNORECASE,
    ),
    re.compile(
        r"disregard\s+(all\s+|any\s+)?(previous|prior|above|your)\s+(instructions|prompts|rules)",
        re.IGNORECASE,
    ),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|my)\s+", re.IGNORECASE),
    re.compile(r"<\s*script\b", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"\bon(error|load|click|mouseover)\s*=", re.IGNORECASE),
    re.compile(r"<\s*iframe\b", re.IGNORECASE),
    re.compile(r"\bdrop\s+table\b", re.IGNORECASE),
    re.compile(r"\bunion\s+select\b", re.IGNORECASE),
    re.compile(r";\s*--"),
    re.compile(r"\bor\s+1\s*=\s*1\b", re.IGNORECASE),
    re.compile(r"<\?(php|=)", re.IGNORECASE),
    re.compile(r"\b(reveal|print|show|dump)\b.{0,40}\b(system|hidden)\s+prompt\b", re.IGNORECASE),
    re.compile(
        r"\bdo\s+not\s+follow\s+(your|the|my)\s+(rules|instructions|prompt)\b",
        re.IGNORECASE,
    ),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    re.compile(r"<\s*svg\b", re.IGNORECASE),
)

_TAG_PATTERN = re.compile(r"<[^>]*>")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# Zero-width and bidi characters can hide a blocked phrase from a naive scan.
_INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]")

SCREENED_FIELDS: tuple[str, ...] = (
    "event_name",
    "host_names",
    "city",
    "vibe",
    "cultural_preferences",
    "dietary_notes",
    "custom_notes",
)

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "Cache-Control": "no-store",
}


def screen_text(value: str, field_name: str) -> str:
    """Reject attack-shaped text and strip leftover markup.

    Args:
        value: Raw user text. May be empty.
        field_name: Field name used in the error message.

    Returns:
        The cleaned string.

    Raises:
        PromptInjectionError: If the text matches a blocked pattern.
    """
    if not value:
        return ""
    cleaned = unicodedata.normalize("NFKC", value)
    cleaned = _INVISIBLE.sub("", cleaned)
    cleaned = _CONTROL_CHARS.sub("", cleaned).strip()
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(cleaned):
            raise PromptInjectionError(
                f"The field '{field_name}' contains instructions or markup "
                "the planner will not send on.",
                details=[field_name],
            )
    without_tags = _TAG_PATTERN.sub("", cleaned)
    return re.sub(r"\s+", " ", without_tags).strip()


def sanitize_event_request(request: EventRequest) -> EventRequest:
    """Screen every free-text field on an event brief.

    Args:
        request: A schema-valid brief.

    Returns:
        A copy with control characters and benign tags removed.

    Raises:
        PromptInjectionError: If any field matches a blocked pattern.
    """
    updates: dict[str, str] = {}
    for field_name in SCREENED_FIELDS:
        updates[field_name] = screen_text(getattr(request, field_name), field_name)
    if len(updates["event_name"]) < 2:
        raise PromptInjectionError(
            "The event name is too short after removing markup.",
            details=["event_name"],
        )
    if len(updates["city"]) < 2:
        raise PromptInjectionError(
            "The city is too short after removing markup.",
            details=["city"],
        )
    return request.model_copy(update=updates)


class TokenBucketLimiter:
    """In-memory token bucket keyed by client address.

    The bucket refills continuously at ``rate_per_minute`` and holds at most
    that many tokens, so a burst cannot exceed the per-minute budget.
    """

    def __init__(self, rate_per_minute: int) -> None:
        """Create a limiter.

        Args:
            rate_per_minute: Sustained request budget for each address.
        """
        self.rate_per_minute = rate_per_minute
        self._capacity = float(rate_per_minute)
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        """Spend one token if the bucket has one.

        Args:
            key: Client identity, usually the connection host.

        Returns:
            A pair of ``(allowed, remaining_tokens)``.
        """
        now = time.monotonic()
        refill_per_second = self.rate_per_minute / 60.0
        with self._lock:
            tokens, last = self._buckets.get(key, (self._capacity, now))
            tokens = min(self._capacity, tokens + (now - last) * refill_per_second)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                self._prune(now)
                return False, 0
            tokens -= 1.0
            self._buckets[key] = (tokens, now)
            self._prune(now)
            return True, int(tokens)

    def _prune(self, now: float) -> None:
        """Drop idle buckets so the map cannot grow without bound."""
        if len(self._buckets) < 4096:
            return
        stale_before = now - 120.0
        stale = [key for key, (_, seen) in self._buckets.items() if seen < stale_before]
        for key in stale:
            del self._buckets[key]


class SecurityHeadersMiddleware:
    """Attach a fixed set of security headers to every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Add the fixed security headers to an HTTP response."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {name.lower() for name, _ in headers}
                for name, value in SECURITY_HEADERS.items():
                    encoded = name.lower().encode("latin-1")
                    if encoded not in existing:
                        headers.append((encoded, value.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodySizeLimitMiddleware:
    """Reject POST bodies whose ``Content-Length`` exceeds the configured cap."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject a write whose Content-Length is above the configured cap."""
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        length = _content_length(scope.get("headers", []))
        if length is not None and length > self.max_bytes:
            response = JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "payload_too_large",
                        "message": "The request body is larger than this planner accepts.",
                        "details": [f"limit_bytes={self.max_bytes}"],
                    }
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply the token bucket to ``/api/`` routes.

    ``/health`` and the HTML page are not counted, so a status check cannot
    lock a person out of the form.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Count ``/api/`` requests against the address that opened the connection."""
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        limiter: TokenBucketLimiter = request.app.state.limiter
        allowed, remaining = limiter.allow(client)
        response: Response
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": (
                            "Too many planning requests from this address. "
                            "Wait a minute and try again."
                        ),
                        "details": [],
                    }
                },
            )
        else:
            response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limiter.rate_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


def _content_length(headers: Iterable[tuple[bytes, bytes]]) -> int | None:
    """Read ``Content-Length`` from raw ASGI headers."""
    for name, value in headers:
        if name.lower() == b"content-length":
            try:
                return int(value.decode("latin-1"))
            except ValueError:
                return None
    return None
