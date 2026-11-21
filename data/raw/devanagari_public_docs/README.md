# Real public Devanagari documents (QA corpus, #35 / #37)

Downloaded **2026-11-21** from official Government of India / Government of Maharashtra
publishers, over **verified TLS only** (no certificate checks were disabled). These are public
records, **not patient documents**: no real patient, bill or prescription is in here. The PDFs are
git-ignored (`.gitignore`); this manifest records where each came from and its SHA-256 so anyone can
re-download and verify. Re-download with `curl -fsSL -A "Mozilla/5.0" <url>` and compare the hash.

| Directory / file | Publisher | Source URL | Size | SHA-256 | Language | Pages |
|---|---|---|---|---|---|---|
| `mh_gr_2026-01` | Public Health Dept, Govt of Maharashtra (GR, 06 Jan 2026) | https://cdnbbsr.s3waas.gov.in/s3feecee9f1643651799ede2740927317a/uploads/2026/01/202601192013825870.pdf | 219,118 | `c23431a7cb53…` | Marathi | 8 |
| `mh_gr_2025-09` | Public Health Dept, Govt of Maharashtra (GR, Sep 2025) | https://cdnbbsr.s3waas.gov.in/s3feecee9f1643651799ede2740927317a/uploads/2025/09/20250926994270252.pdf | 160,226 | `893af468ffed…` | Marathi | 4 |
| `mahabocw_gr_2017-06` | Maharashtra Building & Other Construction Workers Welfare Board (GR, 2017) | https://mahabocw.in/wp-content/uploads/2019/06/201706021314126517.pdf | 3,481,857 | `f5dfecd30bd5…` | Marathi | 3 |
| `pib_pmjay_2025-11` | Press Information Bureau, GoI (PM-JAY document, Nov 2025) | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc2025111682201.pdf | 2,730,878 | `5f5786b45af9…` | Hindi | 11 |
| `ombudsman_rules_2017_gazette` | Council for Insurance Ombudsmen (Gazette, Insurance Ombudsman Rules 2017) | https://cioins.co.in/notification/Ombudsman%20Rules,%202017.pdf | 351,639 | `528676ffbe1c…` | Hindi + English | 13 |
| `irdai_complaint_registration_form` | IRDAI policyholder portal (complaint registration form, 2021) | https://policyholder.gov.in/documents/37343/620662/policyholder+complaints+registration+form29092021.pdf/5ff5e0af-a34e-6cba-91d2-fe053b076624?t=1633587167192 | 699,862 | `4306ea4b9e5b…` | Hindi + English | 4 |

Full hashes are in `sha256.txt` next to this file's table source (`sha256sum */*.pdf` reproduces them).

## What was measured (2026-11-21, PyMuPDF text layer + one OCR probe)
| File | Devanagari share of text layer | Text layer quality | Use |
|---|---|---|---|
| `mh_gr_2026-01`, `mh_gr_2025-09`, `mahabocw_gr_2017-06` | 64–74 % | **Corrupted**: wrong glyph mapping (`विस्तावरत` for `विस्तारित`, `अरोग्य` for `आरोग्य`, `बाांधकाम` for `बांधकाम`) | Real Marathi OCR test pages (rasterise, transcribe by hand) |
| `pib_pmjay_2025-11` | 44 % | **Partly garbled** (`साव$भौ'मक`, `आरो4य`) + 5 embedded images | Real Hindi OCR test pages |
| `ombudsman_rules_2017_gazette` | 28 % | **Legacy font encoding** (`jftLVªh`, `vlk/kj.k`): the Hindi text is unreadable as extracted | Worst-case "bad text layer" fixture; Hindi must come from OCR |
| `irdai_complaint_registration_form` | 38 % | Mostly readable with errors (`सिे िं.115/1`) | Real bilingual **form** layout |

**Consequence:** these real documents cannot supply automatic ground truth from their text layer, and a
text-layer-first PDF path would feed garbage to extraction. Ground truth must be human-transcribed
from the rendered page, or cross-checked between OCR and a clean source.

One OCR probe (page 1 of `mh_gr_2026-01`, 200 dpi, EasyOCR `["hi","mr","en"]`, CPU): 86 segments in 32 s,
mean confidence 0.65, 26 segments below the 0.5 review threshold; headings such as `महाराष्ट्र शासन`,
`सार्वजनिक आरोग्य विभाग` and `दिनांकः ०६ जानेवारी , २०२६` were read correctly. A probe, not a benchmark:
no reference transcription exists yet, so no WER/CER is claimed.

## Tried and not obtained
| Wanted | Why not |
|---|---|
| Maharashtra MJPJAY GRs on `www.jeevandayee.gov.in` (8 documents) | Host does not accept connections from this machine (connect timeout). Newer GRs were found on the NIC mirror above. |
| IRDAI (Protection of Policyholders' Interests) Regulations, 2017 / 2024, bilingual | `www.policyholder.gov.in/uploads/…` has an **expired TLS certificate** (not bypassed); the Finance Ministry host returned its 404 page for every path. A human can supply the official PDF. |
| NHA *Adhikar Patra* (PM-JAY beneficiary rights, Hindi/English) | The URL returned a 3.8 KB HTML page, not a PDF. |
| Parliament Hindi PM-JAY PDF (`eparlib.nic.in`) | No connection. |

## Not available to an engineer
Real **patient** documents (hospital bills, prescriptions, denial letters) in Hindi/Marathi. They need
donors, written consent, redaction and a retention decision: see
`docs/planning/phase4-expansion-plan.md`, workstream B.

## Local model weights (not in the repo)
EasyOCR's Devanagari recognition model (`devanagari.pth`, 215 MB, shared by Hindi and Marathi) was
downloaded to the EasyOCR cache (`D:\Installed\Caches\easyocr\model` on the maintainer's machine, set by
`EASYOCR_MODULE_PATH`) from the official EasyOCR release, next to `craft_mlt_25k.pth` (83 MB) and
`english_g2.pth` (15 MB).
