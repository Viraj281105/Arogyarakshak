# ADR-014: Optional client-side password protection for downloaded packages

- **Status:** Accepted (2026-10-15) — implements issue #101 for the DaaviSetu downloads
- **Context:** A downloaded pre-authorization PDF or claim ZIP holds health and policy details
  and often leaves the device by e-mail or messaging. The server must not hold the password
  (ADR-003 zero retention; ADR-008 has no accounts to attach a key to).
- **Decision:** The web client can encrypt a download in the browser before saving it
  (`apps/web/app/lib/packageCrypto.ts`): PBKDF2-HMAC-SHA256 (600,000 iterations, random 16-byte
  salt) → AES-256-GCM (random 12-byte IV), with the whole header authenticated as additional
  data. File extension `.arenc`; the same panel unlocks a file locally. The patient chooses the
  password (minimum 8 characters); it is never sent anywhere and cannot be recovered.
- **Scope:** DaaviSetu pre-auth PDF and claim ZIP downloads, opt-in. **Not** applied to the
  BillNyay appeal PDF: it is a signed document meant to be forwarded to an insurer as-is, and an
  encrypted copy would break the integrity check and the filing workflow.
- **Consequences:** Protects the file at rest and in transit by mail. It does not protect against
  a weak password, malware on the device, or a compromised browser. Mobile has no equivalent yet.
- **Verification:** unit tests (round trip, wrong password, tampered ciphertext/header, hostile
  iteration count) and a manual browser check (protected download → `.pdf.arenc`, unlock → `%PDF-`).
