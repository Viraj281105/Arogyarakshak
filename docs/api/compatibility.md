# API contract and compatibility

The reviewed contract is `docs/api/openapi.json`. `apps/api/tests/test_openapi_contract.py`
fails when the live schema differs from it, and separately (with a "Breaking change" message)
when an operation disappears.

## Making a change

1. Change the route / model.
2. `PYTHONPATH=apps/api python scripts/export_openapi.py`
3. Review the diff of `docs/api/openapi.json` in the PR.

| Change | Compatible? | What to do |
|---|---|---|
| New route, new optional request field, new response field | Yes | Regenerate and commit |
| Removing or renaming a route, response field or enum value | **No** | Add the new shape alongside, migrate web (`apps/web/app`) and mobile (`apps/mobile/src/api`), release, then remove the old one in a later change |
| Making a request field required, narrowing a type | **No** | Same: accept both, migrate clients, then tighten |
| Error payloads | Keep `{"detail": ..., "message": ...}` (string details) and `{"detail", "error_id"}` for 500s | — |

Both clients call the API directly; there is no API gateway and no generated client today, so
a breaking change has to be found in `apps/web/app` and `apps/mobile/src/api` by hand.

## Versioning

All routes are under `/api/v1`. A `/api/v2` is introduced only for a change that cannot be made
additively; `/api/v1` then stays until both clients have moved.

## Change log of contract-affecting framework updates

- 2026-10-19, FastAPI 0.148: file upload fields are described with OpenAPI 3.1
  `contentMediaType` instead of `format: binary`; `ValidationError` gained optional `input` and
  `ctx`. No operation, request field or response field changed. Added `/health/live` and
  `/health/ready`.
- 2026-11-23, accounts (ADR-026): added `/api/v1/kadi/auth/*`, `GET /api/v1/kadi/cases` and
  `POST /api/v1/kadi/cases/{case_id}/claim`. `CaseCreatedResponse.access_token` became nullable
  and gained `owned`: it is `null` only when the request carried a valid account session, so
  existing guest clients (which send no session) always still receive a string. Owned cases
  refuse case tokens on every case route (`403`), which guest clients never meet.
- 2026-11-25, **breaking** (ADR-029): every patient route now requires a session, `access_token`
  from case creation is always `null`, case tokens are accepted only by the claim route, and
  `?access_token=` was removed. Made within `/api/v1` because both first-party clients moved in the
  same change and no third-party client exists. Additive: `GET /api/v1/kadi/auth/config`, the case
  action routes, `is_demo` and `display_name` on the account.
