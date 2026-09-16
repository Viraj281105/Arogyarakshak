# Testing Strategy & Evaluation Framework

This document outlines the testing architecture, test commands, mock fixtures, and evaluation metrics used across **ArogyaRakshak**.

---

## 1. Test Architecture

The repository employs a multi-tiered testing strategy:

```text
tests/
├── Unit Tests (packages/*/tests/)
│   ├── packages/billnyay/tests/test_agents.py     # 5-agent auditing chain tests
│   ├── packages/bimanyay/tests/test_bimanyay.py   # Claim repudiation & IRDAI appeal tests
│   ├── packages/daavisetu/tests/test_daavisetu.py # Pre-auth form generation tests
│   ├── packages/dawacheck/tests/test_dawacheck.py # NPPA ceiling price tests
│   ├── packages/kadi/kadi/ocr/tests/test_ocr.py  # OCR parser & regex fallback tests
│   └── packages/schemesetu/tests/test_schemesetu.py # PMJAY/MJPJAY rule tests
├── API Integration Tests (apps/api/tests/)
│   ├── apps/api/tests/conftest.py                # Async SQLite fixture & mock client
│   └── apps/api/tests/test_api.py                # Health, upload, stream & endpoints
├── Mobile Client Tests (apps/mobile/src/__tests__/)
│   └── apps/mobile/tests/                       # BYOD, consent, scanner & contract tests
└── Evaluation Metrics (Phase 4.5)
    └── Formal ML & OCR benchmarks (PEA, BMA, CFMA, CRMA, WER/CER)
```

---

## 2. Test Commands

### 2.1 Run All Backend & Package Tests (139 Tests)
```bash
# Run all package unit tests & API integration tests
python -m pytest packages/ apps/api/tests/
```

### 2.2 Run Mobile Client Tests (27 Tests)
```bash
cd apps/mobile
npm test
cd ../..
```

### 2.3 Run Targeted Module Tests
```bash
# BimaNyay only
python -m pytest packages/bimanyay/tests/

# BillNyay only
python -m pytest packages/billnyay/tests/

# DawaCheck only
python -m pytest packages/dawacheck/tests/

# SchemeSetu only
python -m pytest packages/schemesetu/tests/

# DaaviSetu only
python -m pytest packages/daavisetu/tests/

# Kadi OCR only
python -m pytest packages/kadi/kadi/ocr/tests/

# API Integration only
python -m pytest apps/api/tests/
```

---

## 3. Fixtures & Isolation Strategy

Integration tests in `apps/api/tests/conftest.py` use a file-backed **SQLite async engine (`sqlite+aiosqlite:///test_temp.db`)**, created and dropped around each test:
- Tests execute in complete isolation without requiring an active PostgreSQL container.
- All database schemas are created before each test and dropped afterwards; the file is removed at teardown.
- A file-backed database (rather than `:memory:`) is required so the background document-processing task sees the same data as the request that scheduled it.
- FastAPI dependency overrides inject the test database session via `app.dependency_overrides[get_db]`.

---

## 4. Evaluation Benchmark Metrics (Phase 4.5)

For the final academic and production evaluation, ArogyaRakshak measures five primary quantitative metrics:

| Metric | Target | Description & Measurement |
|---|---|---|
| **Procedure Extraction Accuracy (PEA)** | `>= 92%` | Precision of clinical procedure extraction from unstructured hospital bills against ground-truth labels. |
| **Benchmark Mapping Accuracy (BMA)** | `>= 88%` | Accuracy of mapping hospital billing descriptions to official CGHS rate codes. |
| **Claim Form Mapping Accuracy (CFMA)** | `>= 95%` | Precision of DaaviSetu auto-populating coordinates and fields on standardized insurer pre-auth templates. |
| **Claim Rejection Mapping Accuracy (CRMA)**| `>= 90%`| BimaNyay accuracy in matching repudiation clause codes against the IRDAI 2024 Master Circular. |
| **OCR Word Error Rate (WER)** | `< 8%` | Character and word error rate on noisy Devanagari and Latin doctor prescriptions and receipts. |
| **End-to-End Audit Latency** | `< 10 sec` | Total wall-clock time from document upload to completed SSE stream. |

**Status (2026-09-15):** End-to-End Audit Latency now has a working monitoring harness —
`app/latency_metrics.py`, `GET /api/v1/kadi/metrics/latency`, and
`scripts/evaluate_latency.py` — see [`docs/evaluation/latency.md`](../evaluation/latency.md)
for measured results and their limitations (#116). PEA, BMA, CFMA, CRMA, and WER/CER
remain targets with no measurement harness (#102–#115 still open); the table above states
what this project aims for, not what has been verified for those five.

---

## 5. Adding Tests for New Features

When adding new capabilities:
1. Create a unit test file in `packages/<module>/tests/test_<feature>.py`.
2. Mock external Groq API calls using `unittest.mock.patch` or static JSON responses to prevent network dependency during test runs.
3. Assert that outputs match strictly typed Pydantic models.
