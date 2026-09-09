# Testing Strategy & Evaluation Framework

This document outlines the testing architecture, test commands, mock fixtures, and evaluation metrics used across **ArogyaRakshak**.

---

## 1. Test Architecture

The repository employs a multi-tiered testing strategy:

```text
tests/
├── Unit Tests (packages/*/tests/)
│   ├── packages/billnyay/tests/test_agents.py     # 5-agent auditing chain tests
│   ├── packages/daavisetu/tests/test_daavisetu.py # Pre-auth form generation tests
│   ├── packages/dawacheck/tests/test_dawacheck.py # NPPA ceiling price tests
│   ├── packages/kadi/kadi/ocr/tests/test_ocr.py  # OCR parser tests
│   └── packages/schemesetu/tests/test_schemesetu.py # PMJAY/MJPJAY rule tests
├── API Integration Tests (apps/api/tests/)
│   ├── apps/api/tests/conftest.py                # Async SQLite fixture & mock client
│   └── apps/api/tests/test_api.py                # Health, upload, stream & endpoints
└── Evaluation Metrics (Phase 4.5)
    └── Formal ML & OCR benchmarks (PEA, BMA, CFMA, CRMA, WER/CER)
```

---

## 2. Test Commands

### 2.1 Run All Tests Across Monorepo
```bash
# Run all package unit tests
python -m pytest packages/

# Run API integration tests
cd apps/api
python -m pytest tests/
cd ../..
```

### 2.2 Run Targeted Module Tests
```bash
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
```

---

## 3. Fixtures & Isolation Strategy

Integration tests in `apps/api/tests/conftest.py` use an in-memory **SQLite async engine (`sqlite+aiosqlite:///:memory:`)**:
- Tests execute in complete isolation without requiring an active PostgreSQL container.
- All database schemas are automatically created in memory before each test and torn down after.
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

---

## 5. Adding Tests for New Features

When adding new capabilities:
1. Create a unit test file in `packages/<module>/tests/test_<feature>.py`.
2. Mock external Groq API calls using `unittest.mock.patch` or static JSON responses to prevent network dependency during test runs.
3. Assert that outputs match strictly typed Pydantic models.
