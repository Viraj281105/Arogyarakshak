"""The live OpenAPI schema matches the reviewed contract in docs/api/openapi.json.

Regenerate with `PYTHONPATH=apps/api python scripts/export_openapi.py` after an
intentional change, and review the diff: removed operations or newly required request
fields break the web and mobile clients (docs/api/compatibility.md).
"""

import json
import pathlib

from app.main import app

CONTRACT = pathlib.Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"
METHODS = {"get", "post", "put", "patch", "delete"}


def _operations(schema):
    return {(m.upper(), p) for p, item in schema["paths"].items() for m in item if m in METHODS}


def test_no_operation_was_removed_or_renamed():
    reviewed = json.loads(CONTRACT.read_text(encoding="utf-8"))
    removed = _operations(reviewed) - _operations(app.openapi())
    assert not removed, f"Breaking change — operations removed: {sorted(removed)}. See docs/api/compatibility.md."


def test_live_schema_equals_the_reviewed_contract():
    reviewed = json.loads(CONTRACT.read_text(encoding="utf-8"))
    live = json.loads(json.dumps(app.openapi()))
    added = sorted(_operations(live) - _operations(reviewed))
    assert live == reviewed, (
        "The API contract changed. If intended, run `PYTHONPATH=apps/api python scripts/export_openapi.py` "
        f"and commit docs/api/openapi.json. New operations: {added}"
    )
