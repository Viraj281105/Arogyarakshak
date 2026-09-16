# ADR-007: Federated, Privacy-Preserving Case-Context Sharing — Design

## Status
**Proposed — design only. Nothing in this ADR is implemented.** Addresses #87 ("verify patient identity and consent parameters across nodes without decrypting case logs").

## Context
Today ArogyaRakshak is a single deployment with one Postgres database:

- **Consent** is one boolean per case (`kadi_cases.consent_opt_in`). It is set at case creation and enforced per route by `apps/api/app/consent.py` (ADR-003).
- **Nodes:** there are no federated nodes, no inter-node protocol and no service-to-service trust.
- **Authentication:** none exists (see the current-state audit).
- **ABDM:** no integration. Records can be imported from a client-supplied FHIR bundle (#54), but gateway/HIU registration is an external blocker (#46, #56).

So there is nothing yet for a zero-knowledge protocol to protect *between*. This ADR records what federation would require, where zero-knowledge proofs (ZKPs) would and would not help, and the order in which to build it, so that no cryptography is introduced ahead of the system that needs it.

## Actors and assets
- **Actors:**
  - the patient (data principal);
  - an ArogyaRakshak node holding the case;
  - a partner node that wants to use case context (another deployment, a hospital, a TPA);
  - optionally, an ABDM consent manager.
- **Assets:**
  - case entities (diagnoses, procedures, medicines, bill lines);
  - consent state (scope, purpose, validity window);
  - the link between a case and a real identity (ABHA number, name, phone).

## Threat model
| Threat | Example |
|---|---|
| Unauthorized sharing | A partner receives case context the patient never consented to share with it |
| Stale or replayed consent | A revoked or expired consent is presented again |
| Over-disclosure of identity | Verifying consent reveals the patient's ABHA number or name to a partner that only needs a yes/no |
| Linkage | Pseudonymous case IDs are correlated across partners to rebuild a profile |
| Forged consent | A compromised node fabricates a consent record |
| Compromised node | A node leaks decrypted case logs |

## Requirements
- **R1** A verifier can check that consent covers *this* purpose, module and time window.
- **R2** A verifier can check that consent is bound to the patient's identity key **without learning the identity attributes**.
- **R3** The verifier learns only the verification result and the scope it asked about.
- **R4** Consent can be revoked, and verification fails after revocation.
- **R5** Every verification is auditable by the patient.
- **R6** Verification never requires decrypting case logs; case data is shared only *after* verification, and only the consented subset.

## Options considered
| Option | Meets | Cost / caveat |
|---|---|---|
| A. Signed consent receipts (JWS, e.g. Ed25519) with expiry, scope and pseudonymous case ID | R1, R4 (with revocation list), R5, R6 | The verifier sees every claim in the receipt; identity binding needs key management |
| B. ABDM consent artefacts from a consent manager | R1, R4, R5, R6; aligned with national infrastructure | Requires ABDM HIU/HIP registration; scope is visible to the receiver by design |
| C. Salted-hash selective disclosure (SD-JWT style) | R1, R3 (partially), R4, R6 | The holder chooses which claims to reveal; no predicate proofs |
| D. ZKPs: BBS+ selective disclosure or zk-SNARK predicates (e.g. "scope includes BillNyay and expiry > now", "holder controls the key bound to this commitment") | R1–R3 strongly, R6 | Circuit or credential design, audited libraries, key management; some SNARKs need a trusted setup; proof generation cost on mobile |

## Where ZKPs help, and where they do not
- **They help** when a partner must be convinced of a *predicate* over identity or consent attributes it must not see. For example: the holder of the key bound to this case also holds a valid consent for module X until date Y, and the ABHA number is not revealed.
- **They do not** make case data safe to share. Once context is disclosed, it is disclosed.
- **They do not** replace authentication, access control, revocation or audit logging.
- **They add nothing** to a single-node deployment, which is ArogyaRakshak today.

## Proposed decision (staged; each stage has explicit preconditions)
0. **Now:** keep per-case consent enforcement. No federation, no cryptographic consent tokens.
1. **When a second node or partner exists and authentication is in place:**
   - Issue signed, expiring, scope-limited consent receipts (options A and C), keyed to pseudonymous per-partner case identifiers to limit linkage.
   - Add a revocation list and a patient-visible verification log.
2. **When ABDM registration is complete:** accept and verify ABDM consent artefacts (option B) for records pulled through the gateway.
3. **Only if a partner must verify a predicate without learning the attributes:**
   - Adopt BBS+ selective disclosure or zk-SNARK predicates (option D).
   - Use a maintained, independently audited library, never hand-rolled cryptography.
   - Budget proof generation and verification time.

## Non-goals
- Encrypting or sharing case logs between nodes (R6 keeps them local).
- Blockchain or distributed-ledger storage of consent.
- Implementing any ZKP primitive in this repository before stage 3's preconditions hold.

## Verification plan (for when a stage is built)
- Property tests on receipt and proof verification:
  - wrong scope, wrong audience, expired, revoked and tampered inputs must all fail;
  - a valid receipt or proof must pass.
- Replay tests with captured tokens.
- Linkage review: the same patient must not produce correlatable identifiers across two partners.
- External cryptographic review before any stage 3 component ships.
- Performance budget for mobile proof generation.

## Consequences
- #87 is delivered as this design. Implementation is deliberately deferred until federation, authentication and ABDM registration exist.
- Documentation must not describe federated or ZK consent verification as implemented.
