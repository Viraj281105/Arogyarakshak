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
| `prescriptions_handwritten/` | Images | `kadi`, `dawacheck` | Sample doctor prescription dataset for OCR and entity extraction stress-testing. |
| `indian_medical_insurance_policy/` | PDFs / Text | `bimanyay`, `daavisetu` | Representative Indian retail health insurance policy terms & exclusions. |
| `health_insurance_claims_synthetic/`| CSV / Structured | `bimanyay` | Synthetic insurance claims and repudiation logs for grievance evaluation. |
| `healthcare_fraud_detection/` | Tabular | `billnyay` | Procedure code anomaly and overutilization detection dataset. |
| `mendeley_insurance_claims/` | Tabular / Text | `bimanyay`, `daavisetu` | Open-access insurance claim dispute benchmark dataset. |
| `sparcs_inpatient_discharges/` | Tabular | `kadi` | De-identified hospital inpatient discharge dataset for procedure extraction verification. |

---

## Bring-Your-Own-Document (BYOD) Compliance

The data assets in this directory are strictly **reference benchmarks and synthetic evaluation sets**. Under no circumstances should real patient documents or identifying private health information (PHI) be committed to this folder.
