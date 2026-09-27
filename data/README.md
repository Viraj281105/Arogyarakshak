# Reference Datasets & Ingestion Pipelines (`data/`)

This directory contains public government rate schedules, policy circulars, test document benchmarks, and data ingestion pipelines for **ArogyaRakshak**.

---

## Provenance & Data Hygiene Policy

In accordance with project rules, every record and benchmark must cite an authentic public source document:
- **CGHS Rate Schedules**: Public notifications issued by the Ministry of Health and Family Welfare (MoHFW), Government of India.
- **NPPA Ceiling Prices**: Gazette notifications and DPCO Price Orders issued by the National Pharmaceutical Pricing Authority.
- **PMJAY / MJPJAY Parameters**: Official scheme operational guidelines and empanelled hospital lists published by the National Health Authority (NHA) and State Health Assurance Society (SHAS), Maharashtra.
- **IRDAI Regulations**: Circulars and master directions issued by the Insurance Regulatory and Development Authority of India.

---

## Dataset Inventory (`data/raw/`)

| Dataset / File | Format | Associated Module | Description / Provenance |
|---|---|---|---|
| `cghs_rates.pdf` | PDF (6.4 MB) | `billnyay` | Official CGHS procedure rate schedules across city tiers. |
| `insurance_companies.pdf` | PDF | `daavisetu`, `bimanyay` | Directory of registered Indian general & health insurers and TPAs. |
| `invoices_receipts_ocr/` | Images & Annotations | `kadi`, `billnyay` | Ground-truth dataset for hospital billing layout and OCR token extraction. |
| `prescriptions_handwritten/` | Images | `kadi`, `dawacheck` | 5 images from the public Hugging Face dataset `chinmays18/medical-prescription-dataset` (`download_actual_data.py`). They are computer-rendered in handwriting-style fonts with fictional clinic/patient names — synthetic, not real prescriptions. Used for OCR stress-testing only. |
| `indian_medical_insurance_policy/` | PDFs / Text | `bimanyay`, `daavisetu` | Representative Indian retail health insurance policy terms & exclusions. |
| `health_insurance_claims_synthetic/`| CSV / Structured | `bimanyay` | **Mock scaffold** (2 rows written by `download_datasets.py`), not a dataset. |
| `healthcare_fraud_detection/` | Tabular | `billnyay` | **Mock scaffold** (2 rows written by `download_datasets.py`), not a dataset. |
| `mendeley_insurance_claims/` | Tabular / Text | `bimanyay`, `daavisetu` | **Mock scaffold** (1 row of a motor-insurance fraud schema written by `download_datasets.py`). It is not a claim-dispute benchmark and contains no dispute outcomes. |
| `sparcs_inpatient_discharges/` | Tabular | `kadi` | **Mock scaffold** (2 rows written by `download_datasets.py`), not a dataset. |

> No historical IRDAI / Insurance Ombudsman dispute-outcome data exists in this repository, which is why BillNyay's outcome estimator (#90) returns `INSUFFICIENT_EVIDENCE`. The Kadi entity-resolution evaluation set (`packages/kadi/tests/fixtures/entity_pairs_curated_synthetic.jsonl`) is hand-curated and synthetic.

---

## Bring-Your-Own-Document (BYOD) Compliance

The data assets in this directory are strictly **reference benchmarks and synthetic evaluation sets**. Under no circumstances should real patient documents or identifying private health information (PHI) be committed to this folder.
