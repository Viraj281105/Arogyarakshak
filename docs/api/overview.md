# API Gateway Reference (`apps/api`)

The **ArogyaRakshak API** is an asynchronous REST API built with FastAPI, providing document auditing, scheme eligibility matching, and medicine pricing endpoints.

---

## 1. Documentation & Interactive Testing

When running locally, FastAPI provides automatic interactive OpenAPI documentation:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON)**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 2. API Endpoints Directory (`/api/v1`)

### System & Health
| Method | Route | Description | Response Code |
|---|---|---|---|
| `GET` | `/health` | API health check & version confirmation | `200 OK` |

### Kadi (Shared Intelligence Layer)
| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/kadi/cases` | Initializes a new patient case session (`consent_opt_in`) | `201 Created` |
| `POST` | `/api/v1/kadi/cases/{id}/upload` | Uploads multipart document buffer for transient OCR & extraction | `202 Accepted` |
| `GET` | `/api/v1/kadi/cases/{id}/stream` | Server-Sent Events (SSE) live progress stream | `200 OK (text/event-stream)` |
| `GET` | `/api/v1/kadi/cases/{id}` | Retrieves all extracted case entities and cross-module insights | `200 OK` |

### BillNyay (Hospital Bill Audit)
| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/billnyay/audit` | Audits bill line items against CGHS rate schedules | `200 OK` |
| `POST` | `/api/v1/billnyay/generate-appeal` | Compiles 5-agent evidence-backed hospital overcharge representation PDF | `200 OK` |

### DaaviSetu (Claim Pre-Authorization)
| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/daavisetu/pre-auth/generate` | Pre-populates standard cashless pre-authorization form from Kadi case context | `200 OK` |

### BimaNyay (Claim Denial Dispute & IRDAI Appeals)
| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/bimanyay/analyze` | Ingests denial letter & policy, identifies IRDAI violations (e.g. 5-yr moratorium) | `200 OK` |
| `POST` | `/api/v1/bimanyay/generate-appeal-pdf`| Generates 3-tier appeal package (GRO Appeal, Bima Bharosa text, Ombudsman Form VI) | `200 OK` |
| `POST` | `/api/v1/bimanyay/grievances` | Registers self-reported grievance tracking session with computed SLAs | `201 Created` |
| `GET` | `/api/v1/bimanyay/grievances/{id}` | Returns active SLA countdowns and escalation eligibility | `200 OK` |

### SchemeSetu (Scheme Eligibility)
| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/schemesetu/eligibility` | Evaluates income, ration card category, and medical needs against PMJAY & MJPJAY | `200 OK` |

### DawaCheck (Medicine Pricing)
| Method | Route | Description | Response Code |
|---|---|---|---|
| `POST` | `/api/v1/dawacheck/benchmark` | Verifies brand drug MRP against NPPA Schedule-I ceiling prices and finds generics | `200 OK` |

---

## 3. Server-Sent Events (SSE) Streaming

For long-running extraction and multi-agent reasoning, clients listen to `/api/v1/kadi/cases/{case_id}/stream`.

### Event Format
```http
event: message
data: {"case_id": "...", "stage": "clinical_review", "progress": 65, "message": "Comparing procedure to CGHS rates"}
```

---

## 4. Standard Error Payloads

All endpoints return uniform, structured error payloads:

```json
{
  "detail": [
    {
      "loc": ["body", "consent_opt_in"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "message": "Request validation failed"
}
```
