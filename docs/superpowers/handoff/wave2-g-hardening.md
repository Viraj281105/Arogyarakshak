# Wave 2, stream G: API error-path hardening

Fixes the three defects stream E's chaos tests recorded as strict xfails (markers removed; the tests now pass), plus the PHI logging rule.

| Defect | Fix |
|---|---|
| Unhandled 500 had no `X-Request-ID`/hardening headers, log `req=-` | `RequestContextMiddleware.dispatch` catches the exception from `call_next` and answers with `internal_error_response` inside the request context (Starlette's `ServerErrorMiddleware` is outside all user middleware). The `Exception` handler in `main.py` remains as a fallback and calls the same function. |
| 500 and 429 had no `message` | Both now carry `detail` + `message` (500 also `error_id`, 429 also `retry_after_seconds`). 404/405/422/413 already did (tests added). Status codes unchanged. |
| ENOSPC while spooling a large multipart body returned 400 | FastAPI wraps any form-read failure as `HTTPException(400) from e`; `http_exception_handler` inspects `__cause__` and, for `OSError` with errno ENOSPC/EDQUOT/EROFS, answers **507** `{detail, message}` with fixed text. Nothing is written elsewhere. |
| Handler logged exception text (PHI risk) | `internal_error_response` logs type name, route template, `error_id`, `file:line in function`; no message, no traceback text. |

Contract: error responses are not described in `docs/api/openapi.json`, so it is unchanged (OpenAPI contract test passes). The web/mobile API client treats `detail` as before; `message` is additive. Deployers: alert on 507 as a storage fault.

Files: `apps/api/app/observability.py`, `apps/api/app/main.py`, `tests/chaos/test_chaos_database.py`, `tests/chaos/test_chaos_upload.py`, `docs/development/troubleshooting.md`.
