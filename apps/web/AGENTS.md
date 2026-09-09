# Scoped Agent Instructions: Next.js Web Frontend (`apps/web/`)

This directory contains the Next.js App Router client application for ArogyaRakshak.

## Architectural Guidelines for `apps/web/`

1. **Framework & Architecture**:
   - Built on Next.js 15/16 App Router with React 19 and TypeScript.
   - Core styling utilizes Vanilla CSS / CSS Modules with standard design tokens (`app/globals.css`). Do NOT introduce TailwindCSS unless explicitly requested.

2. **Trilingual Localization Scaffolding**:
   - The UI supports English (EN), Hindi (HI), and Marathi (MR).
   - Never hardcode raw Hindi or Marathi copy without flagging for native-speaker terminology QA review.
   - Maintain translation dictionaries with clean key-value bindings (e.g. `audit.overcharge_detected`).

3. **Server-Sent Events (SSE) Client Consumption**:
   - Document upload status and multi-agent audit progress must be received via native browser `EventSource` connected to the `/api/v1/kadi/cases/{case_id}/stream` endpoint.
   - Handle reconnection, completion events, and error states gracefully.

4. **Validation Requirements**:
   - Always run the linter before completing work:
     ```bash
     cd apps/web
     npm run lint
     ```
   - Verify pages locally using `npm run dev` and navigate the affected routes in the browser.
