# Clinical Review, Safety Governance & Human OCR Resolution

Decision record: [ADR-011](decisions/ADR-011-clinical-review-and-safety-governance.md).

> **The principle.** Machine-derived evidence and accountable human judgment are different
> kinds of thing. ArogyaRakshak routes cases to named humans where judgment is needed,
> keeps the two apart all the way into the documents a patient files, and never lets
> software write, sign, or imply a clinician's opinion.

---

## 1. Who does what

| Task | Software (AI / rules) | Named human |
|---|---|---|
| Extract diagnoses, procedures, medicines, bill lines | ✅ Kadi OCR + extraction (`AI_DERIVED`) | — |
| Flag diagnosis ↔ intervention inconsistency | ✅ plausibility check (bounded, cited) | — |
| Say whether an intervention was *clinically justified* | ❌ never | ✅ doctor's own statement (`HUMAN_AUTHORED`) |
| Detect that a denial turns on clinical judgment | ✅ BimaNyay trigger | — |
| Write the clinical rebuttal to that denial | ❌ never | ✅ doctor's own statement |
| List documents commonly needed for pre-auth | ✅ checklist (baseline + institution playbook) | desk staff author private playbooks |
| Confirm a clinical fact the claim relies on | ❌ never marked satisfied by software | ✅ doctor's decision (`HUMAN_REVIEWED`) |
| Read an illegible prescription word | ❌ low-confidence OCR is not trusted | ✅ pharmacist / transcriptionist / annotator, two blind readings for medication fields |
| Decide which red flags stop an admin workflow | ❌ | ✅ rules adapted from published protocols, approved by a named board |
| Show a red-flag escalation | ✅ evaluates ACTIVE rules | — |
| Verify a reviewer's registration | ❌ no registry integration exists | — (shown as self-declared) |

Humans are not approving AI output anywhere in this layer. They either **author** something
AI is not allowed to produce (statements, fact decisions, readings, rules) or they are not
involved.

---

## 2. Architecture

```mermaid
flowchart TD
    Docs["Patient documents"] --> Kadi["Kadi: OCR (+ per-segment confidence), extraction"]
    Kadi -->|entities, AI_DERIVED| Ctx["Case context"]
    Kadi -->|low-confidence OCR segments| TR["Transcription tasks (redacted text only)"]

    Ctx --> BN["BillNyay plausibility"]
    Ctx --> BM["BimaNyay clinical-denial trigger"]
    Ctx --> DS["DaaviSetu readiness"]
    Ctx --> SR["Safety rules (ACTIVE)"]

    BN -->|CLINICAL_REVIEW_REQUIRED| REQ["Review request<br/>(consent + frozen evidence packet)"]
    BM --> REQ
    DS -->|clinical facts| REQ
    SR -->|escalation| Patient["Patient UI"]

    REQ -->|case holder assigns| Doc["Named doctor<br/>(X-Reviewer-Token)"]
    Doc -->|COI, then evidence| ST["Statement / fact decision<br/>HUMAN_AUTHORED / HUMAN_REVIEWED"]
    TR -->|case holder assigns| Reader["Pharmacist / transcriptionist"]
    Reader -->|2 blind readings| TRR["Resolved reading HUMAN_REVIEWED"]

    ST --> Annex["Deterministic annex<br/>(verbatim, attributed)"]
    Annex --> Pkg["BillNyay appeal PDF / BimaNyay annex / DaaviSetu package"]
    TRR --> DC["DawaCheck benchmark"]
    Board["Safety board (named doctors)"] -->|propose, approve, version| SR
```

| Layer | Location |
|---|---|
| Domain rules (DB-agnostic) | `packages/kadi/kadi/clinical_review/` — `types`, `lifecycle`, `evidence`, `verification`, `safety`, `transcription`, `annex` |
| Module logic | `packages/billnyay/billnyay/plausibility.py`, `packages/bimanyay/bimanyay/clinical_triggers.py`, `packages/daavisetu/daavisetu/readiness.py` |
| Persistence & services | `apps/api/app/clinical/` — `auth`, `audit`, `serializers`, `context`, `service`, `safety_service`, `transcription_service`, `purge`, `demo`; `apps/api/app/daavisetu_playbooks.py` |
| HTTP | `apps/api/app/api/v1/endpoints/clinical_review.py`, `clinical_safety.py`, `clinical_transcription.py`, `clinical_demo.py` (all under `/api/v1/kadi`); additions in `billnyay.py`, `bimanyay.py`, `daavisetu.py`, `dawacheck.py`, `kadi.py` |
| Web | `apps/web/app/lib/clinical.ts`, `app/components/clinical/*`, `app/clinical-review/page.tsx` (reviewer workspace) |
| Mobile | `apps/mobile/src/components/ClinicalReviewCard.tsx`, `ClinicalWorkflowCards.tsx`; screen integrations |

### Tables (all new; no existing table altered)

| Table | Scope | Purpose |
|---|---|---|
| `kadi_clinical_reviewers` | global | Named reviewer, category, declared registration, verification status, credential hash, board seat |
| `kadi_clinical_reviews` | case | Consented request, frozen evidence packet, COI context, assignment, COI declaration |
| `kadi_clinical_statements` | case | Versioned statement, reviewer snapshot, confirmation, content hash |
| `kadi_clinical_fact_confirmations` | case | Clinical fact + reviewer decision |
| `kadi_clinical_audit_events` | case / global | Append-only events; ids, statuses and counts only |
| `kadi_safety_rules`, `kadi_safety_rule_approvals` | global | Versioned rules, attributable approvals bound to a content hash |
| `kadi_safety_scan_results` | case | Upload-time full-text rule matches: rule id, version, matched terms only |
| `kadi_transcription_tasks`, `_assignments`, `_submissions` | case | Uncertain readings, assigned readers, one reading per reader |
| `daavisetu_institutions`, `daavisetu_playbooks` | global (institution-private) | Desk credential; versioned private checklists |

---

## 3. Credentials and authorization

There are still no user accounts (ADR-008). Three bearer credentials exist, each shown
once and stored only as a SHA-256 hash:

| Credential | Header | Holder | Grants |
|---|---|---|---|
| Case token | `X-Case-Access-Token` | patient / case holder | their case, as before (ADR-009) |
| Reviewer credential | `X-Reviewer-Token` (header only) | a registered reviewer | only the reviews/tasks a case holder **assigned to them** |
| Institution credential | `X-Institution-Token` (header only) | a hospital desk | only its own playbooks |
| Governance key | `X-Governance-Admin-Key` | operator | seat board members, attempt verification, seed demo; **disabled when unset** |

Object-level checks on every request:
- case-holder routes load reviews by `(case_id, review_id)` — an id from another case is 404;
- reviewer routes require `assigned_reviewer_id == reviewer`, an accessible state, and the
  case still existing with consent — otherwise 404 (ids cannot be probed);
- reviewer-facing review responses (queue, detail, accept) omit the `case_id`: a reviewer
  reaches case data only through the review, never by the patient's case identifier;
- statement routes additionally require `statement.reviewer_id == reviewer` — a reviewer
  cannot edit or finalize another reviewer's draft (403);
- playbook routes filter by the caller's institution — another hospital's playbook is 404.

---

## 4. Reviewer verification — what is and is not known

| Status | How it is reached | Label shown everywhere |
|---|---|---|
| `UNVERIFIED` | registered without a registration number | "Identity and registration not verified" |
| `SELF_DECLARED` | registered with a registration number | "Self-declared registration — not verified by ArogyaRakshak" |
| `DEMO_VERIFIED` | operator, only with `CLINICAL_DEMO_MODE=true` | "Demo verification only — not checked against any real medical registry" |
| `EXTERNALLY_VERIFIED` | only a real `RegistryVerificationAdapter` — **none exists** | "Registration verified against {source} on {date}" |

`POST /kadi/clinical-reviewers/{id}/verification {"mode": "external"}` calls the shipped
`UnavailableRegistryAdapter`, which returns `EXTERNAL_VERIFICATION_UNAVAILABLE` and changes
nothing. Anyone can register claiming to be a doctor, so self-registration is never
treated as trustworthy by listing:

- `GET /kadi/clinical-reviewers` lists **only** `EXTERNALLY_VERIFIED` reviewers (none exist
  in this build) — plus demo fixtures while `CLINICAL_DEMO_MODE` is on. A self-declared
  "Dr. <real name>" therefore never appears to patients as a choice.
- A patient assigns their own doctor/pharmacist by the **reviewer ID** that person gives
  them (shown in the reviewer workspace). The looked-up profile, with its honest label, is
  shown before assigning.
- Demo reviewers are unusable (not listed, not look-up-able, credential rejected) the
  moment demo mode is turned off.

A finalized statement freezes the reviewer's verification state at signing time.

---

## 5. Conflict of interest

Declared per review, before any clinical evidence is visible:
`TREATING_DOCTOR`, `HOSPITAL_AFFILIATED`, `INSURER_AFFILIATED`, `INDEPENDENT_REVIEWER`,
`OTHER` (free-text disclosure required). Reviewers may also record standing disclosures on
their profile. The COI is frozen into each statement / fact decision and printed wherever
it appears — patient UI, appeal annex, readiness package.

---

## 6. Statement lifecycle

```mermaid
stateDiagram-v2
    [*] --> DRAFT: reviewer writes (own words, cites packet items)
    DRAFT --> UNDER_REVIEW: lock for finalization
    UNDER_REVIEW --> DRAFT: back to editing
    DRAFT --> FINALIZED: confirmation sentence + own credential
    UNDER_REVIEW --> FINALIZED: confirmation sentence + own credential
    FINALIZED --> SUPERSEDED: a new version is finalized
    FINALIZED --> WITHDRAWN: author retracts (reason required)
```

- Required confirmation, sent by the reviewer: *"I confirm that this statement represents
  my own professional judgment based on the information reviewed."*
- `evidence_reviewed` may only cite items from the review's frozen packet.
- Finalization stores a reviewer snapshot and a SHA-256 over the statement's content.
- The case holder sees only FINALIZED / SUPERSEDED / WITHDRAWN versions; drafts are private.
- Only a FINALIZED statement on a non-cancelled review is ever presented as a current
  opinion or put in a package.

---

## 7. Plausibility review (BillNyay)

`GET /api/v1/billnyay/cases/{id}/clinical-plausibility` → `PLAUSIBLE`,
`INSUFFICIENT_INFORMATION`, `POTENTIAL_INCONSISTENCY` or `CLINICAL_REVIEW_RECOMMENDED`, plus
`clinical_review.status = CLINICAL_REVIEW_REQUIRED | NOT_REQUIRED`. Every result lists the
evidence used and the reference used (the project-curated ICD-10 table, labelled as such),
carries `is_necessity_determination: false` and the disclaimer *"This is a limited
plausibility assessment and is not a clinical necessity determination."* Guideline
citations can only come from a registered guideline record; none is registered, so none
is cited. An active safety escalation raises the case to review.

Bill lines that are administrative charges (room, bed, nursing, consultation, ICU stay,
diet, pharmacy, …) are set aside as `excluded_administrative_items`, never treated as
interventions. A PLAUSIBLE result lists every billed intervention the curated table does
not cover as `not_assessed_items` (`coverage: PARTIAL`) and says in its summary that they
were not assessed — so "appendectomy + MRI brain" is not presented as all-clear. A
diagnosis whose code cannot be read or is outside the table is also listed there (and
makes coverage PARTIAL) whenever another diagnosis was assessed, so one covered diagnosis
never hides an unassessed one behind `FULL`; the summary says such diagnoses are not
treated as compatible.

A billed intervention that the table lists for a *different* diagnosis which is not
documented (e.g. cholecystectomy billed with only appendicitis documented) is a conflict:
it is returned in `conflicting_items` (never as "not assessed"), and a result where one
intervention matches while another conflicts is `CLINICAL_REVIEW_RECOMMENDED`, never
`PLAUSIBLE`. If the safety evaluation fails, the result carries
`safety_check_status: UNAVAILABLE` and a review reason; the response's `safety_check`
says so.

## 8. Preauth readiness (DaaviSetu)

`POST /api/v1/daavisetu/cases/{id}/readiness` evaluates a generic baseline plus, with the
institution's credential, one of its ACTIVE, in-date playbooks. Item statuses: `PRESENT`,
`MISSING`, `NEEDS_CLINICAL_CONFIRMATION`, `CONFIRMED_BY_REVIEWER`, `REJECTED_BY_REVIEWER`,
`REVIEWER_COULD_NOT_DETERMINE`. Keyword evidence is reported as `KEYWORD_MATCH` (weak).
Keywords are searched only in the extracted entities and the first 1,000 characters of each
document (the redacted excerpt that is kept); every report carries `evidence_scope_note`
saying so, and "missing" means "not found there", not "absent from your documents".
Clinical facts are routed with
`POST .../readiness/clinical-confirmations` — the fact wording comes from the server-side
checklist, never the request. The claim package ZIP now includes `preauth_readiness.txt`
reflecting real reviewer decisions. No output mentions approval probability.

## 9. Safety governance

```mermaid
stateDiagram-v2
    [*] --> DRAFT: board member adapts a published protocol
    DRAFT --> UNDER_REVIEW: submit (content hash frozen)
    UNDER_REVIEW --> DRAFT: reject (reason required)
    UNDER_REVIEW --> APPROVED: independent approval(s) on this hash
    APPROVED --> ACTIVE: activate (previous ACTIVE version -> SUPERSEDED)
    ACTIVE --> RETIRED: retire (reason required)
```

Each rule stores `source_name`, `source_reference`, `source_version`, `source_section`,
`limitations`, `effective_date`, `review_due_date`, `changelog`. Triggers are structured
keyword lists over case text (validated; no code). Escalations return only matched terms —
never surrounding patient text — plus source, version, limitations, a negation caveat and
the floor disclaimer. `GET /kadi/cases/{id}/safety-escalations` is not consent-gated; with
no active rules it says *"the absence of an escalation is therefore not a safety
assessment of any kind."*

**Coverage.** Every uploaded document is scanned **in full** against the rules active at
upload time, while it is still in memory; only the rule id, version and matched terms are
stored (`kadi_safety_scan_results`, erased with the case). Rules activated later see only
the extracted entities and the 1,000-character excerpt. A result recorded under a version
that was since superseded carries forward to the ACTIVE version of the same `rule_key` for
every stored term that version still lists (a new version has a new rule id; without this a
red flag beyond the excerpt vanished on re-versioning). Terms the new version adds are not
checked against the full text of earlier uploads. Results of retired rules, and terms the
new version dropped, are ignored. The response's `scope_note` states this. If the check
fails, web and mobile say so explicitly — a failure never renders like "no escalation".

**Retirement is four-eyes.** Retiring removes an escalation from every case, so the
first board member's `POST .../retire` only records a retirement request (audit event
`RULE_RETIREMENT_REQUESTED`; the rule stays ACTIVE and keeps escalating;
`retirement_requested_by` shows it); a different board member's call confirms it. The
requester cannot confirm their own request (409); each call needs a reason.

**Failure is explicit.** `GET .../safety-escalations` returns `status: EVALUATED`, or
`status: UNAVAILABLE` (with `active_rule_count: null`) when the rules could not be
evaluated — the evaluation runs in a SAVEPOINT so a failure does not poison the request.
Web and mobile render UNAVAILABLE (or a failed request) as "Safety check unavailable".

**Approval rounds.** The submitted content hash includes a submission round (counted from
the rule's own `RULE_SUBMITTED` audit events). After a rejection, resubmitting unchanged
content starts a fresh round: earlier approvals no longer count and the reviewer who
rejected can decide again.

## 10. Human OCR resolution and the medicine trust gate

**Invariant:** an uncertain OCR reading of a medicine never lets that medicine become a
trusted, benchmarkable fact until humans have settled it.

### 10.1 From uncertain segment to task or held-back entry
- Kadi keeps EasyOCR's per-segment confidence (`ocr_segments`). A segment below
  `OCR_LOW_CONFIDENCE_THRESHOLD` is a candidate **only if** it carries no direct
  identifier and is not a prescriber/identity line ("Dr.", degrees, registration no.), is
  not a bare marker ("Rx", "Tab.") or too short to settle, and is not a non-clinical field
  (amount, date). Context shows only neighbouring medication-looking lines (redacted),
  and the reader view shows the line position on the original.
- `kadi.clinical_review.transcription.plan_ocr_uncertainty` then decides for **every**
  medication-risk candidate (nothing is dropped):

| Reading … | Outcome |
|---|---|
| names exactly **one** medicine by whole tokens (either direction; markers, dose pattern "1-0-1" and duration ignored; "40" = "40mg" but "40mcg" ≠ "40mg"), within the cap | a two-reader **task** linked to it |
| the same, beyond `MAX_TASKS_PER_DOCUMENT` (10, counted after linking) | medicine held back: `OVER_CAP` |
| names **two or more** medicines ("Pan" with "Pan 40" and "Pan-D") | all of them held back: `AMBIGUOUS` — software never picks one |
| names none but **resembles** one or more (edit similarity / shared prefix, or the strength stored separately) — typically an extractor normalisation "Amoxycilin" → "Amoxicillin" | held back: `POSSIBLE_MATCH` — a normalisation is not a confirmation |
| names and resembles nothing | `unplaced`; every medicine **from this document** whose name is not in the clearly read OCR text is held back: `UNGROUNDED` |
| is not medication-related (non-clinical fields) | ignored (counted) |

A held-back medicine carries `meta.ocr_uncertainty = {status: "UNRESOLVED", reasons,
readings, explanation, next_step}`; later uploads can add reasons, never clear them.

### 10.2 Readers and consensus
- `MEDICINE_NAME`, `STRENGTH`, `FREQUENCY`, `ROUTE`, `DURATION` and `UNCLASSIFIED` are HIGH
  risk: two independent readings from different readers must agree (normalised for
  case/spacing/units). HIGH-risk readers never see the OCR guess or another reader's answer.
  Disagreement or "unreadable" → `HUMAN_ESCALATION_REQUIRED`.
- A task stores the redacted candidate, the masked context and a location hint — **no
  image** (ADR-003). Readers read the original the patient holds, so today this works in
  person, not remotely.
- A case holder can flag a whole extracted medicine entry (partial-field flags are refused).

### 10.3 Applying an agreed reading (`substitute_reading`)
- Replaces only the uncertain part of the name; a leading "Tab."/"Cap." is ignored.
- If the uncertain reading was the entry's whole line — its name-bearing tokens are exactly
  the entry's name, the rest markers/dose pattern/duration — the readers' line minus those
  fragments becomes the name ("Tab Augmentin 625mg 1-0-1 x 5 days" → "Augmentin 625mg").
  If the line carries more than the entry (e.g. a strength stored separately), it is not
  placed.
- A reading that is only a marker, or any result that no longer names a drug ("Tab. 40"),
  is refused.
- Not placeable → `human_transcription.status = NOT_APPLIED`; the task shows
  `outcome: NOT_APPLIED` ("Readers agreed, but the reading could not be applied") — never a
  green "confirmed".

### 10.4 The trust gate (`kadi.clinical_review.medicine_trust.decide_medicine_trust`)
Used by DawaCheck and by reviewer evidence packets. First match wins; blocking states beat
settled ones:

1. open task (`OPEN`, `AWAITING_SECOND_REVIEW`) → `AWAITING_HUMAN_READING` — blocked
2. escalated task → `READERS_DISAGREED` — blocked, unless a whole-entry reading resolved
   **after** the most recent escalation
3. `NOT_APPLIED` → `READING_NOT_APPLIED` — blocked
4. `ocr_uncertainty` UNRESOLVED → `OCR_UNCERTAIN` — blocked (reasons listed)
5. placed human reading → `HUMAN_RESOLVED`, benchmarked with `name_provenance: HUMAN_REVIEWED`
6. otherwise → `MACHINE_EXTRACTED`, benchmarked as `AI_DERIVED`

States 3 and 4 are settled **only** by a whole-entry reading (a case-holder flag, or an OCR
reading that was the entire entry) placed by two readers; a partial reading never clears
them. When several tasks exist for one entry, an OPEN one is reported first, otherwise the
most recently escalated one. DawaCheck rows carry `trust = {state, label, benchmarkable,
reasons}`; evidence packets show held-back medicines as "unsettled" with `AI_DERIVED`
provenance.

### 10.5 Entity resolution guard
For medicines, a variant letter on only one side is a conflict ("Pan-D" is not "Pan 40");
without this, resolution auto-merged the two and one medicine silently disappeared from the
case. The entity-resolution evaluation is unchanged (0 false merges, identical recall).

---

## 11. Threat model (tested in `apps/api/tests/test_clinical_security.py`)

| Threat | Mitigation |
|---|---|
| IDOR / cross-case reviewer access | reviewer access requires assignment; case routes key on `(case_id, review_id)`; 404 on mismatch |
| Case A statement in case B | statements load by case; appeal/annex/context queries filter by case |
| Finalizing another reviewer's draft | `statement.reviewer_id` check → 403; declined reviewer loses access (404) |
| Token confusion / query-string tokens | separate headers; reviewer/institution credentials header-only |
| Consent bypass | stored `consent_opt_in` + per-request `share_with_reviewer_consent`; request-body `consent_opt_in` ignored |
| Reviewer impersonation / fake verification | verification cannot be self-set; board seat needs the governance key; labels never upgraded |
| Privilege escalation to safety board | `is_safety_board_member` ignored at registration; board routes require seat + DOCTOR |
| Cross-tenant playbook leakage | institution filter on every playbook read/write; readiness requires that institution's credential |
| Unauthorized evidence access | evidence only after acceptance + COI; cancel revokes immediately |
| Malicious transcription | length bound, control-char strip, one reading per reader (DB unique), stored as literal text |
| Prompt injection via documents/statements | evidence delivered as data with a warning; statements never enter an LLM prompt; Barrister rule forbids implying clinician opinions |
| Unsafe PDF generation | annex XML-escaped before any markup, same as the letter |
| Stale opinion in a signed PDF | finalize / withdraw / supersede / cancel re-renders the stored appeal PDF annex and re-signs it (`app.clinical.events` listener); an older download fails `.../appeal/verify` |
| Insurer-facing self-harm | the "no clinician statement" notice is patient-facing only (`clinical_statement_notice`); the PDF carries an annex only when a statement exists |
| Impersonation via the directory | only independently verified (or demo, in demo mode) reviewers are listed; others are assigned by the ID they share |
| Sensitive audit logging | `audit.sanitize_details` keeps only short scalars; tests assert no statement text, evidence value or name appears |
| Retention | `purge_case` (DELETE and TTL sweep) removes every case-scoped clinical row |

## 12. Limitations and what is NOT claimed

- **No registry verification.** No integration with NMC/State Medical Councils/Pharmacy
  Council exists; `EXTERNALLY_VERIFIED` is unreachable in this build.
- **No identity proofing.** A reviewer is whoever holds the credential; a case holder is
  whoever holds the case token. The system cannot prove the case holder is the patient.
- **No medical-necessity determination, no approval or outcome prediction.**
- **Safety rules are a floor.** Keyword triggers miss paraphrase and ignore negation;
  there is no claim of comprehensive coverage. Demo rules name their sources by title only
  and must be verified by a real board.
- **Readiness baseline is generic**, not insurer-specific; keyword presence is weak evidence,
  and only the 1,000-character excerpt per document is searched.
- **Transcription readers see text, not the image**: the original stays with the patient,
  so reading works in person, not remotely. Two agreeing non-prescriber readers is still
  weaker than confirmation by the dispensing pharmacist.
- **Plausibility covers 6 ICD-10 codes**; most real cases return INSUFFICIENT_INFORMATION.
- **DawaCheck compares a per-unit price** with per-unit NPPA ceilings; it does not convert a
  strip/pack total on a bill into a unit price, so pack totals look overcharged.
- **OCR uncertainty is only as good as EasyOCR's confidence**: a confidently misread word is
  not flagged. `UNGROUNDED` compares tokens, so a legitimately abbreviated extraction can be
  held back (conservative).
- **English-only clinical UI** pending native-speaker review of Hindi/Marathi wording.
- **No notifications**: reviewers poll their queue; patients press "Refresh status".
- **No payments / marketplace**, by design.
- **Mobile**: patient-side flows only; reviewer administration is web-only.

## 13. Demo walkthrough (Scenarios A–D)

The deterministic demo kit lives in [`demo/`](../../demo/README.md): synthetic documents,
one script per scenario (starting state, steps, expected output, real vs demo-only,
limitations) and the fixtures list. Scenarios are pinned by
`apps/api/tests/test_demo_documents.py` (A, B, D — real upload pipeline with rule-based
extraction) and `apps/api/tests/test_demo_scenario_c.py` (C — demo-mode OCR replay of the
committed synthetic prescription image). The older API-only walkthrough remains in
`apps/api/tests/test_clinical_demo_scenarios.py`.

## 14. Future work

- A real `RegistryVerificationAdapter` once an authorised registry API exists.
- Reviewer notifications; statement signing with a licensed DSC (IT Act, 2000).
- Transient, patient-held image crops for readers (would need an ADR-003 amendment).
- Hindi/Marathi clinical copy after native-speaker review.
- Scoped, revocable consent receipts (ADR-007 stage 1) replacing the boolean + flag.
