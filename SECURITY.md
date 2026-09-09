# Security Policy — ArogyaRakshak

ArogyaRakshak takes software security and patient health data confidentiality with utmost seriousness. As a healthcare decision-support system dealing with medical bills, prescriptions, and insurance documents, strict data privacy controls are engineered directly into the platform architecture.

---

## Supported Versions

Only the latest release and active development branch receive security updates:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 1.0.x (main)   | :white_check_mark: | Active Development |
| < 1.0   | :x:                | Unsupported |

---

## Foundational Security Architecture: Bring-Your-Own-Document (BYOD)

ArogyaRakshak adheres to a strict **Zero-Retention Patient Data Policy**:
1. **No Persistent Document Storage**: Uploaded hospital bills, prescriptions, policy documents, and rejection letters are held **only in transient memory** during the active extraction session.
2. **Immediate Purge**: Once structured entities are extracted into the transient case model, raw uploaded files are immediately expunged from memory buffers. No document files are saved to the persistent file system or permanent object store unless explicit consent is provided.
3. **Differential Privacy & Anonymization**: All cross-module sharing across Kadi is bounded by per-case patient opt-in consent (`consent_opt_in`).

---

## Reporting a Vulnerability

If you discover a security vulnerability within ArogyaRakshak:

1. **Do NOT file a public issue.**
2. Please report the vulnerability directly and privately to the project maintainer:
   - **GitHub Security Advisories**: Use the "Report a vulnerability" tab under the repository's Security menu.
   - **Contact**: Reach out privately to the repository lead (@Viraj281105).
3. Provide a detailed advisory including:
   - Type of vulnerability (e.g., SSRF, Prompt Injection, Data Leakage, Auth bypass)
   - Step-by-step reproduction instructions
   - Potential impact
   - Proposed fix or mitigation if available

We will acknowledge receipt of your vulnerability report within 48 hours and provide updates on resolution progress.

---

## Secrets & Credential Management

- **Zero Hardcoded Secrets**: Never commit real API keys, Groq tokens, database passwords, or JWT secrets to this repository.
- **Git Pre-commit & Scanners**: Maintainers run automated secret detection (`gitleaks` / GitHub Secret Scanning).
- **Environment Isolation**: All configuration is passed strictly via `.env` files (which are ignored in `.gitignore`) or Docker environment variables.
