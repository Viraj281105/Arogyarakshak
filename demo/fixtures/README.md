# Demo fixtures

The runtime fixtures live in the API package (only `apps/api/app/` and `packages/` are copied
into the API image), not here. This page lists them so a reviewer can audit exactly what is
synthetic.

| Fixture | Location | Used by | Contents |
|---|---|---|---|
| Demo reviewers, institution, playbook, safety rules | `apps/api/app/clinical/demo.py` (`POST /api/v1/kadi/clinical-demo/seed`) | Scenarios A–D | 4 reviewer personas (DEMO_VERIFIED ×2 board members, SELF_DECLARED pharmacist, UNVERIFIED transcriptionist); "Demo Hospital Insurance Desk" + a cholecystectomy playbook; FAST and WHO-ETAT demo rules |
| Scenario C OCR + extraction replay | `apps/api/app/clinical/demo_ocr.py` | Scenario C | Per-segment OCR text + confidences and an extraction result for `demo/documents/C_prescription_uncertain.png`, matched by SHA-256, used only when `CLINICAL_DEMO_MODE=true` |

Both are refused or inert outside demo mode:
- the seed route returns 403 unless `CLINICAL_DEMO_MODE=true` **and** the governance key is sent;
- demo reviewers stop being listed, looked up or accepted the moment demo mode is off;
- the OCR replay returns nothing outside demo mode, so the image goes through real OCR.

If `C_prescription_uncertain.png` is regenerated (`demo/documents/generate_prescription_image.py`)
its bytes can change with the Pillow version; update `DEMO_PRESCRIPTION_SHA256` —
`test_committed_demo_document_matches_the_replay_fixture` fails until you do.
