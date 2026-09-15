"""
Evaluate end-to-end document processing latency against the project's 10-second target
(#116: "Eval: Implement system-level latency monitoring to verify End-to-End Processing
Time (< 10 seconds)").

Runs a small set of curated fixture documents through the REAL pipeline — the same
FastAPI app, the same `process_document_background` OCR -> extraction ->
entity-resolution -> database-write path a real upload takes — via an ephemeral SQLite
database, then reads the measured durations back from `GET /api/v1/kadi/metrics/latency`
(app/latency_metrics.py).

    python scripts/evaluate_latency.py                 # human-readable report
    python scripts/evaluate_latency.py --json out.json  # also write the full report as JSON
    python scripts/evaluate_latency.py --repeats 5       # run each fixture N times (default 3)

IMPORTANT — read before citing these numbers:
- Whether GROQ_API_KEY is configured changes which code path is measured. This script
  reports whichever mode the environment is actually in; it never fabricates a number for
  the other mode. With no key (this repo's documented default), every run measures the
  regex-heuristic fallback, not a live LLM call — Groq network latency is NOT included
  in these numbers unless GROQ_API_KEY is set when this script runs.
- Measured on whatever machine runs this script. This is a development-machine
  regression floor, not a production SLA measurement.
- The fixtures are small, synthetic, single-page text documents. Real multi-page scanned
  PDFs processed through EasyOCR will be slower — this script does not claim otherwise.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

FIXTURES = {
    "small_text_bill": (
        b"City Care Clinic\n"
        b"Consultation: 500\n"
        b"Blood Test: 350\n"
        b"Total Amount: 850\n"
    ),
    "multi_item_bill": (
        b"Lifeline Multispeciality Hospital\n"
        b"Patient admitted for evaluation.\n"
        b"Consultation: 900\n"
        b"ICU: 18500\n"
        b"Blood Test: 750\n"
        b"Dolo 650: 33\n"
        b"X-Ray Chest: 1200\n"
        b"Nursing Charges: 2400\n"
        b"Total Amount: 23783\n"
    ),
    "denial_letter": (
        b"Star Health Insurance\n"
        b"Claim Rejection Letter\n"
        b"Denial Code: DEN-4471\n"
        b"Reason: Hospitalisation deemed for investigation only.\n"
        b"Policy Clause: Section 4.1 excludes diagnostic admissions.\n"
        b"Procedure: Laparoscopic Appendectomy\n"
        b"Diagnosis: Acute Appendicitis\n"
    ),
    "prescription_note": (
        b"Apollo Clinic\n"
        b"Diagnosis: Viral Fever\n"
        b"Tab. Dolo 650mg TDS x 5 days\n"
        b"Cap. Amoxicillin 500mg BD after food\n"
        b"Consultation: 400\n"
        b"Total Amount: 400\n"
    ),
}


def _bootstrap_app():
    """Ephemeral SQLite database + FastAPI TestClient, same pattern as apps/api/tests/conftest.py."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.pool import StaticPool
    from fastapi.testclient import TestClient

    from app.main import app as fastapi_app
    from app.database import Base, get_db
    import app.models  # noqa: F401 — registers models with metadata

    db_path = Path(__file__).resolve().parent.parent / "eval_latency_temp.db"
    if db_path.exists():
        db_path.unlink()

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())

    async def override_get_db():
        async with session_local() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = override_get_db
    client = TestClient(fastapi_app)
    return client, engine, db_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repeats", type=int, default=3, help="how many times to run each fixture")
    parser.add_argument("--json", type=Path, help="write the full report to this file")
    args = parser.parse_args()

    client, engine, db_path = _bootstrap_app()
    from app.config import settings
    from app.api.v1.endpoints.kadi import latency_tracker

    latency_tracker.reset()
    groq_configured = bool(settings.groq_api_key)

    print(f"Mode: {'LIVE LLM (GROQ_API_KEY set)' if groq_configured else 'OFFLINE regex/heuristic fallback (GROQ_API_KEY unset)'}")
    print(f"Fixtures: {len(FIXTURES)}, repeats: {args.repeats}\n")

    per_fixture = {}
    for name, payload in FIXTURES.items():
        durations = []
        for _ in range(args.repeats):
            case_res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
            case_id = case_res.json()["id"]
            t0 = time.time()
            upload_res = client.post(
                f"/api/v1/kadi/cases/{case_id}/upload",
                files={"file": (f"{name}.txt", payload)},
            )
            elapsed = time.time() - t0
            if upload_res.status_code != 202:
                print(f"  ! {name}: upload failed with {upload_res.status_code}")
                continue
            durations.append(elapsed)
        per_fixture[name] = durations
        if durations:
            print(f"  {name}: {[round(d, 3) for d in durations]}")

    summary = latency_tracker.summary()
    print("\n--- Aggregate (from GET /api/v1/kadi/metrics/latency) ---")
    print(f"  samples:         {summary.sample_count}")
    print(f"  target:          {summary.target_seconds:.1f}s")
    print(f"  p50:             {summary.p50_seconds}s")
    print(f"  p95:             {summary.p95_seconds}s")
    print(f"  max:             {summary.max_seconds}s")
    print(f"  mean:            {summary.mean_seconds}s")
    print(f"  violations:      {summary.violations}")
    print(f"  compliance_rate: {summary.compliance_rate}")

    if summary.violations:
        print(f"\nFAIL: {summary.violations} of {summary.sample_count} run(s) exceeded the {summary.target_seconds:.0f}s target.")
    else:
        print(f"\nPASS: all {summary.sample_count} run(s) stayed within the {summary.target_seconds:.0f}s target.")

    if args.json:
        report = {
            "groq_configured": groq_configured,
            "repeats": args.repeats,
            "per_fixture_seconds": per_fixture,
            "summary": summary.model_dump(),
        }
        args.json.write_text(json.dumps(report, indent=2))
        print(f"\nFull report written to {args.json}")

    asyncio.run(engine.dispose())
    if db_path.exists():
        db_path.unlink()

    return 1 if summary.violations else 0


if __name__ == "__main__":
    sys.exit(main())
