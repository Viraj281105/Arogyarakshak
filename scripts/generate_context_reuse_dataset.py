"""Regenerates data/evaluation/context_reuse_synthetic.jsonl (#112).

Runs the synthetic demo scenarios A-E through the real upload pipeline and the module calls in
``apps/api/tests/context_flows.py`` against a throwaway SQLite database (created in a temporary
directory, removed afterwards), collects the context reads and ingestion work the production
code reports, and writes one row per scenario. Offline: heuristic extraction, no LLM, no network.

    python scripts/generate_context_reuse_dataset.py

``apps/api/tests/test_context_scenarios.py`` only compares a fresh run with the committed file.
The counts describe SYNTHETIC scenarios, not production traffic.
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "evaluation" / "context_reuse_synthetic.jsonl"

META = {
    "name": "context_reuse_synthetic_v2",
    "synthetic": True,
    "provenance": (
        "Counts collected from the instrumented pipeline while running the committed synthetic demo "
        "documents (scenarios A-E) through upload and the module calls listed per row. Not production "
        "traffic. Regenerate with scripts/generate_context_reuse_dataset.py."
    ),
    "description": "Per scenario: documents, ingestion OCR/extraction passes, and context reads by module and outcome (served/empty).",
}


def main() -> int:
    for pkg in ("kadi", "billnyay", "daavisetu", "bimanyay", "schemesetu", "dawacheck"):
        sys.path.insert(0, str(REPO / "packages" / pkg))
    sys.path.insert(0, str(REPO / "apps" / "api"))  # last, so apps/api/tests wins over packages/*/tests
    work = tempfile.mkdtemp(prefix="ctx-reuse-")
    os.chdir(work)  # the test harness database path is relative to the working directory
    try:
        from app.config import settings
        from app.database import Base
        from tests.auth_test_client import AuthAwareTestClient
        from tests.conftest import engine
        from tests.context_flows import FLOWS, run_scenario
        from app.main import app

        settings.clinical_demo_mode = True  # scenario C replays its recorded OCR
        settings.groq_api_key = ""

        async def create() -> None:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(create())
        client = AuthAwareTestClient(app)
        rows = [run_scenario(sid, client, lambda obj, name, value: setattr(obj, name, value)) for sid in FLOWS]
        asyncio.run(engine.dispose())
    finally:
        os.chdir(REPO)
    lines = [json.dumps({"_meta": META})] + [json.dumps(r, sort_keys=True) for r in rows]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} scenarios to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
