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
| `GET` | `/api/v1/kadi/cases/{case_id}/timeline` | Plain-language case history built only from persisted records (`events[]` with `at`, `label`, `detail`, `actor` = `MACHINE`/`HUMAN`/`PATIENT`), plus `in_progress` / `failure` from the live processing status and `now` (current medicine trust counts). A step is never listed before its record exists. | `200 OK` |

A case may hold several documents: upload again to the same case (the web's "Add another
document to this case"). A byte-identical re-upload is reported as a duplicate and adds nothing.

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
      "item_name": "ICU (1 day)",
      "charged": 18500.0,
      "cghs_benchmark": 5400.0,      // null when not benchmarked
      "deviation_percentage": 242.59,
      "is_deviation": true,
      "benchmarked": true,
      "status": "overcharged",       // overcharged | within_benchmark | bundled | not_benchmarked
      "benchmark_basis": "₹5,400 per day × 1 day",
      "not_benchmarked_reason": null
    }
  ]
}
```

**Rate basis (ADR-012).** Each CGHS entry has a `billing_unit` (`per_day`, `per_visit`,
`per_session`, `per_shift`, `per_bottle`, `per_service`). A recurring rate is applied only
to a count the line states ("3 days", "2 visits", "x 2", "Qty 2"); "ICU 18500" with no day
count is `not_benchmarked` with `not_benchmarked_reason` ("The reference rate is per day,
and this bill line does not say how many days…"). Per-service lines (a scan, a package) are
compared as one service unless a count is stated. CGHS rates are reference rates for CGHS
beneficiaries, not a legal cap on private hospitals; clients say so.

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
| `POST` | `/api/v1/dawacheck/benchmark` | Checks a billed medicine price against NPPA ceiling prices | `200 OK` / `404 Not Found` / `422` |
| `GET` | `/api/v1/dawacheck/cases/{case_id}/benchmark` | The case's medicines: trust decision per medicine, then a per-unit price check (consent required) | `200 OK` |

Backed by a small in-code ceiling-price table (7 formulations), not the full NPPA Schedule-I
list. Unknown brands return `404`.

**Price basis (ADR-012).** NPPA ceilings are per tablet/capsule/vial. `/benchmark` accepts
`price_basis` (`PER_UNIT` | `PER_STRIP` | `PER_PACK` | `LINE_TOTAL` | `UNKNOWN`),
`units_per_pack` and `quantity`; without `price_basis` the legacy contract (per unit) applies
unless the name states a pack ("(15s)"). Case medicines use what the document stated (bill
line or a "Rate per tablet" heading) and never the legacy default. Responses carry
`comparison_status` (`COMPARED` | `CANNOT_COMPARE`), `price_basis`, `price_basis_label`
("per strip of 15"), `basis_source` (`DECLARED` | `DOCUMENT_LINE` | `DOCUMENT_HEADER` |
`API_DEFAULT` | `NONE`), `basis_evidence`, `mrp` (amount as billed), `billed_unit_price`,
`nppa_ceiling_price` (per `unit_label`), `comparison_reason_code`, `comparison_note`.
When not compared, `is_overcharged`, `deviation_percentage` and `billed_unit_price` are
`null` — clients must not render a verdict.

---

### Clinical Review, Safety Governance & Human OCR Resolution (ADR-011)

Design, credential model and threat model: [`docs/architecture/clinical-review.md`](../architecture/clinical-review.md).
Headers: case holder `X-Case-Access-Token`; reviewer `X-Reviewer-Token`; hospital desk
`X-Institution-Token`; operator `X-Governance-Admin-Key` (routes return `503` when
`CLINICAL_GOVERNANCE_ADMIN_KEY` is unset). Reviewer and institution credentials are
header-only and shown once at registration.

**Reviewers** (`/api/v1/kadi`)

| Method | Route | Auth | Description |
|---|---|---|---|
| `POST` | `/clinical-reviewers` | none | Self-register; returns the credential once. Status is at most `SELF_DECLARED` |
| `GET` | `/clinical-reviewers?category=&specialty=` | none | Directory of **independently verified** reviewers only (plus demo fixtures in demo mode). Self-declared reviewers are never listed |
| `GET` | `/clinical-reviewers/{id}` · `/clinical-reviewers/me` | none · reviewer | Profile by the ID a reviewer shares with their patient; `404` for inactive, or for demo reviewers outside demo mode |
| `POST` | `/clinical-reviewers/me/deactivate` | reviewer | Deactivate own credential |
| `POST` | `/clinical-reviewers/{id}/safety-board` | governance | Seat/unseat a doctor on the safety board |
| `POST` | `/clinical-reviewers/{id}/verification` | governance | `external` → `EXTERNAL_VERIFICATION_UNAVAILABLE` (no registry integration); `demo` only in demo mode |

**Case holder** (`/api/v1/kadi/cases/{case_id}/...`, case token)

| Method | Route | Description |
|---|---|---|
| `POST` | `/clinical-reviews` | Request a statement. Needs case consent **and** `share_with_reviewer_consent: true`; freezes the evidence packet |
| `GET` | `/clinical-reviews[?source_module=]` · `/clinical-reviews/{review_id}` | Status, evidence shared, published statements only |
| `POST` | `/clinical-reviews/{review_id}/assign` | Assign a doctor (`reviewer_id`) |
| `POST` | `/clinical-reviews/{review_id}/cancel` | Revoke sharing; reviewer access ends immediately |
| `GET` | `/clinical-reviews/{review_id}/audit` | Audit trail (no clinical text) |
| `GET` | `/clinical-context` | All human-review outputs + safety signals, each with provenance |
| `GET` | `/safety-escalations` | Escalations from ACTIVE rules (not consent-gated), including upload-time full-text matches; `scope_note` states what text was checked. `status` is `EVALUATED`, or `UNAVAILABLE` (`active_rule_count: null`) when the rules could not be evaluated — render as "Safety check unavailable", never as "no escalation" |
| `GET`/`POST` | `/transcriptions` | List tasks / flag a whole extracted medicine entry as possibly misread (`field_type` must be `MEDICINE_NAME`). A RESOLVED task has `outcome`: `APPLIED`, or `NOT_APPLIED` when the agreed reading could not be placed (the entry stays unsettled) |
| `POST` | `/transcriptions/{task_id}/assign` · `/cancel` | Assign a reader (`share_with_reviewer_consent` required) / cancel |

**Reviewer** (`/api/v1/kadi`, reviewer credential; only assigned work is visible, otherwise `404`)

| Method | Route | Description |
|---|---|---|
| `GET` | `/clinical-reviews/assigned` · `/clinical-reviews/{review_id}` | Queue; detail with COI context, own statements, confirmation sentences |
| `POST` | `/clinical-reviews/{review_id}/accept` · `/decline` | Accept with mandatory `coi_category` (+ `coi_disclosure`) / decline |
| `GET` | `/clinical-reviews/{review_id}/evidence` | Frozen evidence packet (`409` until COI declared) |
| `POST`/`PUT` | `/clinical-reviews/{review_id}/statements[/{statement_id}]` | Create / edit own DRAFT |
| `POST` | `.../statements/{statement_id}/submit` · `/return-to-draft` | Lock / unlock |
| `POST` | `.../statements/{statement_id}/finalize` | `{"confirmation": true, "confirmation_text": "<exact sentence>"}` — `422` otherwise |
| `POST` | `.../statements/{statement_id}/revise` · `/withdraw` | New version / retract (`reason`) |
| `POST` | `/clinical-reviews/{review_id}/facts/{fact_id}/decision` | `CONFIRMED` / `REJECTED` / `CANNOT_DETERMINE` + confirmation; immutable |
| `GET` | `/transcriptions/assigned` · `/transcriptions/{task_id}` | Blind task view (HIGH-risk hides the OCR guess) |
| `POST` | `/transcriptions/{task_id}/readings` | One independent reading per reader |

**Safety governance** (`/api/v1/kadi`)

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/safety-rules[?status=ACTIVE\|SUPERSEDED\|RETIRED\|ALL_PUBLIC]` · `/{rule_id}` · `/{rule_id}/versions` · `/{rule_id}/audit` | none | Published rules, history, audit |
| `GET` | `/safety-rules/workspace` | board | All rules incl. drafts |
| `POST`/`PUT` | `/safety-rules` · `/{rule_id}` | board | Propose / edit own DRAFT (source, version, section, limitations, review date required) |
| `POST` | `/{rule_id}/submit` · `/decisions` · `/activate` · `/retire` · `/new-version` | board | Lifecycle; proposer cannot approve own rule; approvals bound to content hash. `/retire` is four-eyes: the first call records a request (rule stays ACTIVE, `retirement_requested_by` set), a different board member's call retires it |
| `GET` | `/clinical-demo/status` | none | `demo_mode`, banner text, the live "what is simulated" list and scenario scripts. Discloses nothing when demo mode is off |
| `POST` | `/clinical-demo/seed` | governance + demo mode | Demo reviewers, institution, playbooks (`playbook_id` for Scenario B, `diabetes_playbook_id` for Scenario E), rules (rotates credentials) |
| `POST` | `/clinical-demo/reset` | governance + demo mode | Body `{"confirm": "RESET DEMO"}`. Deletes cases holding a committed synthetic demo document (others are kept), removes demo safety rules and re-seeds them ACTIVE, rotates credentials; returns them. Idempotent, serialised |
| `POST` | `/clinical-demo/scenarios/{A-E}` | governance + demo mode | Fresh consented case with the scenario's synthetic documents run through the real upload pipeline; returns `case_id`, `access_token`, per-document processing outcome |

Demo routes return `403` unless `CLINICAL_DEMO_MODE=true` **and** `APP_ENV` is not
`production` (the API also refuses to start with both).

**Module additions**

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/v1/billnyay/cases/{case_id}/clinical-plausibility` | Bounded plausibility check; `CLINICAL_REVIEW_REQUIRED` when indicated. Never a necessity determination. `assessment.conflicting_items` lists interventions the reference expects for an undocumented diagnosis; `safety_check.status` / `assessment.safety_check_status` report `UNAVAILABLE` when the safety evaluation failed |
| `POST` | `/api/v1/billnyay/cases/{case_id}/appeal` | Now also returns `human_clinical_statement_attached`, `clinical_statements`, `clinical_annex` (verbatim, empty when none) and `clinical_statement_notice` (patient-facing only). The PDF carries the annex only when a statement exists, and is re-rendered and re-signed whenever a BillNyay statement is finalized, withdrawn or its review cancelled |
| `POST` | `/api/v1/bimanyay/analyze` | Result now includes `clinical_review` (does the denial turn on clinical judgment?) |
| `GET` | `/api/v1/bimanyay/cases/{case_id}/clinical-statements` | Finalized statements + verbatim `annex_text` for the appeal tiers |
| `POST` | `/api/v1/daavisetu/institutions` | Register a hospital desk; credential shown once |
| `GET`/`POST`/`PUT` | `/api/v1/daavisetu/playbooks[/{id}]` | Institution-private playbooks |
| `POST` | `/api/v1/daavisetu/playbooks/{id}/activate` · `/new-version` · `/retire` | Playbook lifecycle (immutable once ACTIVE) |
| `POST` | `/api/v1/daavisetu/cases/{case_id}/readiness` | Documentation checklist; optional `playbook_id` + institution credential |
| `POST` | `/api/v1/daavisetu/cases/{case_id}/readiness/clinical-confirmations` | Route clinical-fact items to a doctor |
| `GET` | `/api/v1/daavisetu/cases/{case_id}/claim/package` | ZIP now includes `preauth_readiness.txt` |
| `GET` | `/api/v1/dawacheck/cases/{case_id}/benchmark` | Benchmarks only medicines the trust gate allows (`clinical-review.md` §10.4). Each row carries `trust = {state, label, benchmarkable, reasons}`: `MACHINE_EXTRACTED` / `HUMAN_RESOLVED` are benchmarked; `AWAITING_HUMAN_READING`, `READERS_DISAGREED`, `READING_NOT_APPLIED` and `OCR_UNCERTAIN` (reasons `AMBIGUOUS`, `POSSIBLE_MATCH`, `OVER_CAP`, `UNGROUNDED`) are not, and `note` says why. Also `name_provenance`, `transcription_status` (`OPEN`, …, `NOT_APPLIED`, `OCR_UNCERTAIN`). Prices are compared per unit |

## 3. Server-Sent Events (SSE) Streaming

Clients listen to `GET /api/v1/kadi/cases/{case_id}/stream` during document processing.

### Event Payload Schema

```json
{ "status": "extraction_start", "progress": 60, "log": "Extracting clinical & billing entities..." }
```

### Pipeline Stages

| `status` | `progress` | Meaning |
|---|---|---|
| `idle` | 100 | Sent at once when nothing has been queued for this case in this API process (e.g. a module screen opened later). Not a claim that anything was processed |
| `upload_received` | 10 | Multipart body accepted and queued |
| `ocr_start` | 30 | OCR / text extraction running |
| `demo_fixture` | 35 | `CLINICAL_DEMO_MODE` only: the committed Scenario C document's OCR/extraction was replayed from a fixture |
| `extraction_start` | 60 | Kadi entity extraction running |
| `database_write` | 80 | Persisting extracted entities |
| `entity_resolution` · `transcription_flags` · `module_checks` | 85–90 | Resolution summary; unclear readings sent to human readers / medicines held back; auto-triggered module checks |
| `completed` | 100 | Processing finished |
| `failed` | 100 | Processing failed; `log` carries the reason |
| `timeout` | 100 | Stream exceeded `SSE_TIMEOUT_SECONDS` and was closed |

The stream terminates on `idle`, `completed`, `failed` or `timeout`. Processing status is held
in memory by one API process: with several workers or after a restart a client can receive
`idle` for a document that was processed elsewhere — clients then read the case normally. No domain-module analysis runs
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
- ADR-011: `POST /api/v1/kadi/cases/{case_id}/clinical-reviews` (plus `share_with_reviewer_consent: true`),
  `POST .../transcriptions/{task_id}/assign` (same flag), `GET /api/v1/billnyay/cases/{case_id}/clinical-plausibility`,
  `GET /api/v1/bimanyay/cases/{case_id}/clinical-statements`, `POST /api/v1/daavisetu/cases/{case_id}/readiness`
  and `.../readiness/clinical-confirmations`. Reviewer access to evidence is re-checked against the stored consent
  on every request. `GET /api/v1/kadi/cases/{case_id}/safety-escalations` is deliberately **not** consent-gated.

Without it these return **`403 Forbidden`**. Enforcement reads the persisted case row, so a
client cannot grant itself access by sending `consent_opt_in` in the module request body. An
unknown case still returns `404`, not `403`.
