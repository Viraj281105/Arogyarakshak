# API Gateway Reference (`apps/api`)

The **ArogyaRakshak API** is an asynchronous REST API built with FastAPI, providing document
ingestion, hospital bill auditing, insurance denial analysis, claim pre-authorization,
scheme eligibility and medicine pricing endpoints.

> Routes below are enumerated from the running application. The authoritative machine-readable
> contract is `/openapi.json`; regenerate this page from it after any route change.

> **Authorization (ADR-009, added 2026-09-16):** every `/cases/{case_id}/...` route
> across every module now requires the case's access token, returned exactly once in
> `POST /api/v1/kadi/cases`'s response body as `access_token`. Send it on every
> subsequent request for that case as the `X-Case-Access-Token` header (the sole
> exception is `GET /cases/{case_id}/stream`, which also accepts `?access_token=` as a
> query parameter because the browser's native `EventSource` cannot set custom
> headers). A case id alone is no longer sufficient — missing the header returns `401`,
> a wrong token returns `403`. This note is a stopgap; the per-route tables below have
> not yet been individually regenerated to show this requirement on each row.

---

## 1. Documentation & Interactive Testing

When running locally, FastAPI provides automatic interactive OpenAPI documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 2. API Endpoints Directory

### System & Health

| Method | Route | Description | Response Code |
|---|---|---|---|
| `GET` | `/health` | Health check, version, and LLM availability | `200 OK` |

```json
{
  "status": "ok",
  "version": "1.0.0",
  "groq_configured": false,
  "groq_model": "openai/gpt-oss-120b"
}
```

`groq_configured` is `false` when `GROQ_API_KEY` is unset. In that state Kadi extraction
falls back to regex heuristics and BillNyay appeal letters are a statutory template rather
than an LLM draft. Treat it as a degraded-mode indicator, not decoration.

### Kadi (Shared Intelligence Layer)

| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/kadi/cases` | Creates a case session. Body: `{"consent_opt_in": bool}` | `201 Created` |
| `POST` | `/api/v1/kadi/cases/{case_id}/upload` | Multipart document upload; schedules transient OCR + extraction | `202 Accepted` |
| `GET` | `/api/v1/kadi/cases/{case_id}/stream` | Server-Sent Events processing progress | `200 OK (text/event-stream)` |
| `GET` | `/api/v1/kadi/cases/{case_id}` | Returns the case and its extracted entities | `200 OK` |

**Consent.** `consent_opt_in` defaults to `false` when omitted. It is stored on the case and
enforced by every module that reads Kadi context — see §5.

**Upload constraints.** Allowed extensions: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`,
`.txt`, `.csv`. Maximum size is `MAX_UPLOAD_BYTES` (default 10 MB).

| Condition | Status |
|---|---|
| Unsupported extension | `415 Unsupported Media Type` |
| Body exceeds the size limit | `413 Request Entity Too Large` |
| Empty body | `400 Bad Request` |

### BillNyay (Hospital Bill Audit)

| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/billnyay/cases/{case_id}/audit` | Audits billing line items against CGHS rates | `200 OK` |
| `POST` | `/api/v1/billnyay/cases/{case_id}/appeal` | Runs the agent chain and returns an IRDAI appeal letter | `200 OK` |
| `POST` | `/api/v1/billnyay/cases/{case_id}/grievance` | Drafts a Bima Bharosa complaint package + portal deep link | `200 OK` |

**`AuditResponse`** distinguishes three outcomes per line. An item with no CGHS counterpart is
reported as `not_benchmarked` with a `null` benchmark — it is **not** "fair", and clients must
not render it as such.

```jsonc
{
  "case_id": "CASE-a1b2c3d4",
  "total_charged": 20183.0,          // every audited line
  "total_benchmark": 6000.0,         // benchmarked lines only
  "benchmarked_charged": 20150.0,    // charged total for benchmarked lines only
  "potential_savings": 14150.0,      // benchmarked_charged - total_benchmark, floored at 0
  "deviations_count": 3,
  "benchmarked_count": 3,
  "unmatched_count": 1,
  "unmatched_amount": 33.0,
  "audit_items": [
    {
      "item_name": "ICU",
      "charged": 18500.0,
      "cghs_benchmark": 5400.0,      // null when not benchmarked
      "deviation_percentage": 242.59,
      "is_deviation": true,
      "benchmarked": true,
      "status": "overcharged"        // overcharged | within_benchmark | bundled | not_benchmarked
    }
  ]
}
```

**`AppealResponse`** carries `llm_backed`, which is `false` when the letter is the offline
statutory template rather than an LLM draft grounded in the case.

```json
{
  "case_id": "CASE-a1b2c3d4",
  "appeal_letter": "SUBJECT: Formal Notice of Representation ...",
  "scorecard": { "overall_score": 88, "status": "approve", "sub_scores": {}, "issues": [] },
  "status": "approve",
  "llm_backed": false
}
```

### DaaviSetu (Claim Pre-Authorization)

| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/daavisetu/cases/{case_id}/claim` | Submits and persists the pre-auth form | `200 OK` |
| `GET` | `/api/v1/daavisetu/cases/{case_id}/claim/pdf` | Downloads the Annexure-B PDF rendered from the submitted claim | `200 OK (application/pdf)` |

The POST persists the submitted form to `daavisetu_claims` (one row per case; re-submitting
updates it). The PDF renders **only** from that persisted claim — no field is re-derived or
invented at download time. Requesting the PDF before submitting a claim returns **`409
Conflict`** rather than a form containing a fabricated policy number.

### BimaNyay (Claim Denial Dispute & IRDAI Appeals)

| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/bimanyay/analyze` | Audits a repudiation against IRDAI rules; drafts 3-tier appeals. Optional `?language=en\|hi\|mr` | `200 OK` |
| `POST` | `/api/v1/bimanyay/timeline` | Computes statutory GRO / Bima Bharosa / Ombudsman SLA deadlines | `200 OK` |

These take all input from the request body and read no Kadi case context, so they are not
subject to the consent gate.

### SchemeSetu (Scheme Eligibility)

| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/schemesetu/eligibility` | Provisional PMJAY & MJPJAY eligibility with cited official sources | `200 OK` |

A deterministic rule set with no income threshold. Neither scheme defines an annual income ceiling
in the cited official sources, so `income` is listed under `non_determinative_factors` and never
decides a verdict. PMJAY is always `ambiguous` (its criteria — SECC-2011 listing, ASHA/AWW/AWH
family, age 70+ — are not collected); MJPJAY is `eligible` for a stated Maharashtra resident. Each
result carries `criteria_provenance` and `sources` (URL, document, publisher, date). The former
`confidence_score` field was removed. `category` and `medical_need` are accepted but do not
influence the result.

`PUT /api/v1/schemesetu/cases/{case_id}/income-profile` (#92, consent-gated) returns a `trigger`
with `status` `FIRE` | `NO_CHANGE` | `INSUFFICIENT_EVIDENCE`, `schemes_applicable`,
`newly_applicable` and `income_role: "NON_DETERMINATIVE"`. It fires when a scheme newly applies
(first saved profile, or a move into Maharashtra); an income change alone never fires.

### DawaCheck (Medicine Pricing)

| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/dawacheck/benchmark` | Checks a brand MRP against NPPA ceiling prices | `200 OK` / `404 Not Found` |

Backed by a small in-code ceiling-price table, not the full NPPA Schedule-I list. Unknown
brands return `404`.

---

## 3. Server-Sent Events (SSE) Streaming

Clients listen to `GET /api/v1/kadi/cases/{case_id}/stream` during document processing.

### Event Payload Schema

```json
{ "status": "extraction_start", "progress": 60, "log": "Extracting clinical & billing entities..." }
```

### Pipeline Stages

| `status` | `progress` | Meaning |
|---|---|---|
| `upload_received` | 10 | Multipart body accepted and queued |
| `ocr_start` | 30 | OCR / text extraction running |
| `extraction_start` | 60 | Kadi entity extraction running |
| `database_write` | 80 | Persisting extracted entities |
| `completed` | 100 | Processing finished |
| `failed` | 100 | Processing failed; `log` carries the reason |
| `timeout` | 100 | Stream exceeded `SSE_TIMEOUT_SECONDS` and was closed |

The stream terminates on `completed`, `failed` or `timeout`. No domain-module analysis runs
during this stream — audit, appeal and claim generation are separate client-initiated calls.

---

## 4. Standard Error Payloads

Validation errors (`422`):

```json
{ "detail": [{ "loc": ["body", "policy_number"], "msg": "field required" }],
  "message": "Request validation failed" }
```

Unhandled server errors (`500`) return a correlation id and **never** the exception text:

```json
{ "detail": "An unexpected server error occurred.", "error_id": "9f2c1a7b4e08" }
```

Search the API logs for the `error_id` to find the corresponding stack trace.

---

## 5. Consent Enforcement

Modules that read Kadi case context require the case to have been created with
`consent_opt_in: true`:

- `POST /api/v1/billnyay/cases/{case_id}/audit`
- `POST /api/v1/billnyay/cases/{case_id}/appeal`
- `POST /api/v1/billnyay/cases/{case_id}/grievance`
- `POST /api/v1/daavisetu/cases/{case_id}/claim`
- `GET /api/v1/daavisetu/cases/{case_id}/claim/pdf`

Without it these return **`403 Forbidden`**. Enforcement reads the persisted case row, so a
client cannot grant itself access by sending `consent_opt_in` in the module request body. An
unknown case still returns `404`, not `403`.
