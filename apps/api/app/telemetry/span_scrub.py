"""Removes request- and data-specific content from spans before they leave the process.

The standard instrumentations record, among other things, the raw request target (which holds
the case id in ``/api/v1/kadi/cases/{case_id}/...``), the query string, the SQL text, and the
full message of any exception (a SQLAlchemy error message includes the bound parameters). None
of that may reach a collector. ``ScrubbingExporter`` wraps the real exporter and rewrites every
span just before export (``ReadableSpan`` attributes are immutable after the span ends, so a
copy is built):

- attributes ``http.target``, ``http.url``, ``url.full``, ``url.path``, ``url.query``,
  ``db.statement``, ``db.query.text`` are dropped; ``http.route`` (the template) is kept;
- every remaining string value has ``CASE-<id>`` tokens redacted;
- exception events keep ``exception.type`` only (message and stacktrace are dropped);
- a status description is dropped (the status code is kept);
- the span name has ``CASE-<id>`` tokens redacted (instrumentation already names server spans
  ``METHOD /route/{template}``).

The collector applies the same rules (``otel-collector/config.yml``) as a second layer.
"""

import re
from typing import Any, Mapping, Sequence

from opentelemetry.sdk.trace import Event, ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace.status import Status

DROPPED_ATTRIBUTES = frozenset(
    {"http.target", "http.url", "url.full", "url.path", "url.query", "db.statement", "db.query.text"}
)
DROPPED_EXCEPTION_ATTRIBUTES = frozenset({"exception.message", "exception.stacktrace"})
_CASE_ID = re.compile(r"CASE-[A-Za-z0-9_-]+")
REDACTED_CASE = "CASE-<redacted>"


def scrub_value(value: Any) -> Any:
    return _CASE_ID.sub(REDACTED_CASE, value) if isinstance(value, str) else value


def scrub_attributes(attributes: Mapping[str, Any] | None, *, exception: bool = False) -> dict:
    dropped = DROPPED_ATTRIBUTES | (DROPPED_EXCEPTION_ATTRIBUTES if exception else frozenset())
    return {k: scrub_value(v) for k, v in (attributes or {}).items() if k not in dropped}


def scrub_span(span: ReadableSpan) -> ReadableSpan:
    events: Sequence[Event] = tuple(
        Event(
            name=scrub_value(e.name),
            attributes=scrub_attributes(e.attributes, exception=(e.name == "exception")),
            timestamp=e.timestamp,
        )
        for e in span.events
    )
    status = span.status
    return ReadableSpan(
        name=scrub_value(span.name),
        context=span.context,
        parent=span.parent,
        resource=span.resource,
        attributes=scrub_attributes(span.attributes),
        events=events,
        links=span.links,
        kind=span.kind,
        instrumentation_info=span.instrumentation_info,
        status=Status(status.status_code, None),
        start_time=span.start_time,
        end_time=span.end_time,
        instrumentation_scope=span.instrumentation_scope,
    )


class ScrubbingExporter(SpanExporter):
    def __init__(self, inner: SpanExporter):
        self._inner = inner

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return self._inner.export([scrub_span(s) for s in spans])

    def shutdown(self) -> None:
        self._inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._inner.force_flush(timeout_millis)
