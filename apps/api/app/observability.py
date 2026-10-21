"""Structured logging, request correlation and response hardening headers.

- Every request gets an id (a caller's well-formed ``X-Request-ID`` is reused, otherwise
  a new one), echoed in the response header and attached to every log record emitted
  while the request is handled (work a BackgroundTask runs after the response has been
  sent is not guaranteed to carry it).
- ``LOG_FORMAT=json`` writes one JSON object per line for a log collector.
- The access log names the *route template* (``/api/v1/kadi/cases/{case_id}``), never
  the concrete path or query string, so case ids and search terms stay out of logs.

Nothing here logs request or response bodies, headers other than the request id, or
uploaded document content.
"""

import contextvars
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)

access_logger = logging.getLogger("arogyarakshak.access")

# Applied to every response. The API serves JSON, PDFs and ZIPs that can contain health
# information: nothing should be cached by a browser or an intermediary, sniffed into a
# different type, framed, or leak a referrer.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Cross-Origin-Resource-Policy": "same-site",
}


class RequestContextFilter(logging.Filter):
    """Adds ``request_id`` (or ``-``) to every record so formatters can use it."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str, environment: str):
        super().__init__()
        self.service = service
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service,
            "environment": self.environment,
            "request_id": getattr(record, "request_id", None) or request_id_var.get(),
        }
        for key in ("method", "route", "status_code", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_format: str, level: str, environment: str, service: str = "arogyarakshak-api") -> None:
    """Idempotent root-logger set-up (also used under uvicorn, whose own loggers keep
    their handlers)."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestContextFilter())
    if log_format == "json":
        handler.setFormatter(JsonFormatter(service=service, environment=environment))
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s [req=%(request_id)s] %(message)s")
        )
    root = logging.getLogger()
    for existing in list(root.handlers):
        if getattr(existing, "_arogyarakshak", False):
            root.removeHandler(existing)
    handler._arogyarakshak = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level.upper())


def resolve_request_id(incoming: Optional[str]) -> str:
    if incoming and _VALID_REQUEST_ID.match(incoming):
        return incoming
    return uuid.uuid4().hex


_templates: Optional[List[Tuple[int, re.Pattern, str]]] = None


def _compile_templates(app) -> List[Tuple[int, re.Pattern, str]]:
    compiled = []
    for template in app.openapi().get("paths", {}):
        pattern = "^" + re.sub(r"\\{[^/]+?\\}", "[^/]+", re.escape(template)) + "$"
        literal_segments = sum(1 for seg in template.split("/") if seg and not seg.startswith("{"))
        compiled.append((literal_segments, re.compile(pattern), template))
    # Most literal segments first, so /cases/claim-pack wins over /cases/{case_id}.
    return sorted(compiled, key=lambda item: -item[0])


def warm_route_templates(app) -> None:
    global _templates
    _templates = _compile_templates(app)


def route_template(request: Request) -> str:
    """The route's path template, e.g. ``/api/v1/kadi/cases/{case_id}``, so concrete ids
    never reach the access log. Resolved from the app's public OpenAPI paths; how a
    middleware can see the matched route differs between FastAPI/Starlette versions."""
    global _templates
    if _templates is None:
        _templates = _compile_templates(request.app)
    path = request.url.path
    for _literals, pattern, template in _templates:
        if pattern.match(path):
            return template
    return "<unmatched>"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            template = route_template(request)
            if template != "/health":
                access_logger.info(
                    "%s %s %s",
                    request.method,
                    template,
                    status_code,
                    extra={
                        "method": request.method,
                        "route": template,
                        "status_code": status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                )
            request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response
