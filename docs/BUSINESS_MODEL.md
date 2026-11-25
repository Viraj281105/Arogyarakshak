# Business model (proposal)

**Status, 2026-11-25:** a planning note. Nothing here is implemented: the product has no payments,
paywall, plans or billing. **No market research, user interview, pricing test or legal opinion has
been done.** Everything below is an assumption to test, and contains no revenue or market figures.

## 1. Problem and value

A patient or family receives a bill, an insurer letter or a pre-authorisation request and cannot
tell what happened, what is worth questioning, or what to do next. The product reads the document,
explains it, compares what it can with published references, prepares drafts and keeps a record of
follow-up. Its value is **clarity and preparation**. It does not promise money back, approval or
eligibility.

## 2. Who it is for

| Group | Need | Pays? |
|---|---|---|
| Patients and families | Understand and act on their own documents | Not for the core journey (proposed) |
| Patient-support NGOs, helplines, community health workers | Help many people consistently, in their language | Possibly, per organisation |
| Employers or benefit administrators | Help employees understand claims | Possibly; consent and confidentiality must be designed first |
| Hospital insurance desks | Fewer incomplete pre-authorisation requests | Possibly, but see conflicts below |
| Colleges and researchers | Teaching and evaluation | Grants |

## 3. Candidate models

| Model | For | Against | First test |
|---|---|---|---|
| Free for individuals, funded by grants or CSR | No barrier at a stressful moment | Depends on funders | Talk to 5 to 10 organisations |
| Organisation licence (NGO, employer) | Predictable, matches support work | Long sales, data-protection terms | One unpaid pilot with written consent terms |
| Hospital desk tool (readiness only) | Clear operational benefit | The same hospital's bills are what patients question | Keep strictly separate; decide whether to do it at all |
| Optional paid human review | Real expert time costs money | Liability, verification of reviewers, regulation | Legal opinion first |
| Self-hosted deployment support | Fits privacy-sensitive institutions | Small market, support load | Ask during pilots |

**Recommendation:** keep the individual journey free, seek grant or CSR support, and test an
organisation licence through one pilot before building anything commercial.

## 4. Rules any model must keep

1. No sale or sharing of patient data, documents or derived profiles. No advertising.
2. No payment from insurers, hospitals or pharmacies that could change a finding.
3. No fee tied to a refund or claim result. It would reward overstating findings.
4. The explanation of a person's own documents, deletion and export of their work stay free.
5. No dark patterns: no urgency, no locked result after upload.

## 5. Cost drivers

Language model calls, hosting (one API process by design, ADR-019), OCR compute, database,
reference-data upkeep, human review, translation review, support and security work. Costs per case
have not been measured.

## 6. Questions that block charging anyone

- Does any part count as insurance intermediation, legal practice or medical advice in India?
- What do the DPDP Act and its rules require for an organisation acting for patients?
- Are the reference datasets licensed for commercial use, and who keeps them current?
- Who is accountable when a finding is wrong?
- Can translations be reviewed and maintained?

## 7. What to measure in a pilot

With consent and without health content in analytics (the web app has none today): whether people can
state their next step after reading a result, how many findings they could act on, how often
"unable to assess" appears, and what they record as the outcome. Self-reported outcomes are not
proof of effect.

## 8. Not ready for

Payments, public launch or production use. See the open items in
[IMPLEMENTATION_STATUS](transformation/IMPLEMENTATION_STATUS.md).
