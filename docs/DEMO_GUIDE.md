# Demo guide

For showing the product with **synthetic data only**. Never run demo mode on a server that holds a
real person's documents. A scripted judge walkthrough is in [JUDGE_DEMO.md](JUDGE_DEMO.md).

## The demo account

| | |
|---|---|
| Name | Aarav Sharma (invented person) |
| Email | `demo@arogyarakshak.in` (identifier only; no mail is sent to it) |
| Password | Generated on your machine each time you run the script. Not stored in the repository. |
| Data | Five synthetic cases from `demo/documents/`, with a few tracked actions marked `DEMO:` |

The account exists only when `CLINICAL_DEMO_MODE=true`. That setting is refused with
`APP_ENV=production`; outside demo mode the address cannot sign in or keep a session, and nobody can
register it.

## Set up

All commands from the repository root. Start PostgreSQL and the API with demo mode on:

```powershell
$env:CLINICAL_DEMO_MODE="true"; docker-compose up --build
```

Running the API without Docker (set `DATABASE_URL` to your local database first):

```powershell
$env:CLINICAL_DEMO_MODE="true"; $env:PYTHONPATH="apps/api"; cd apps/api; uvicorn app.main:app --port 8000
```

Create or reset the account, from a second terminal with the same `DATABASE_URL`:

```powershell
$env:CLINICAL_DEMO_MODE="true"; python scripts/demo_account.py --save
```

The password is printed once and, with `--save`, written to `demo/.demo-credentials.json`
(git-ignored). Delete that file after the demonstration. Each run rotates the password, erases the
demo account's cases and loads them again.

Start the web app:

```powershell
npm --prefix apps/web run dev
```

Open `http://localhost:3000/login`. Use `localhost` for both web and API: `127.0.0.1` is a
different site to the sign-in cookie. Over plain HTTP, Chrome accepts the Secure cookie on
`localhost`; if your browser does not, set `SESSION_COOKIE_SECURE=false` for local use only.

## A ten-minute walk

1. **Public site.** The promise, how it works, privacy. Switch to हिंदी or मराठी and say that these
   are machine translations awaiting review.
2. **Sign-in is required.** Open `/app/case` signed out and show the redirect.
3. **Case desk.** The five synthetic cases.
4. **Bill audit (case A).** Findings by group, why each matters, the reference row behind a figure,
   the draft clarification request.
5. **Track it.** Show the recorded response and say it is the person's own record.
6. **Documentation readiness (case B or E).** Missing items; it ends at "package ready" and submits
   nothing.
7. **Uncertain handwriting (case C)** and **safety escalation (case D).** Reviewer work is at
   `/review`.
8. **Delete** a case and show that everything derived from it is gone.

## Say plainly

- Reference data is a small curated subset (27 CGHS rows, 7 NPPA formulations).
- Without a Groq key, extraction uses local rules and appeal letters come from a template.
- Nothing is sent to a hospital or insurer. No outcome is predicted.
- Email delivery is off unless Gmail is configured.

## Check the demo before presenting

The API needs `CLINICAL_DEMO_MODE=true` and a `CLINICAL_GOVERNANCE_ADMIN_KEY`; pass the same key
to the script. It calls the demo reset, so run it **before** creating the demo account.

```powershell
python scripts/demo_runtime_smoke.py --api http://localhost:8000 --admin-key $env:CLINICAL_GOVERNANCE_ADMIN_KEY
```

## Clean up

Delete `demo/.demo-credentials.json`, set `CLINICAL_DEMO_MODE=false`, and drop the demo database.
