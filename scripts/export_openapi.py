"""Writes the API's OpenAPI contract to docs/api/openapi.json.

    PYTHONPATH=apps/api python scripts/export_openapi.py

apps/api/tests/test_openapi_contract.py fails whenever the live schema and this file
differ, so every contract change is a reviewed diff of this file. Removing a route or a
response field, or making a request field required, breaks the web and mobile clients:
plan a migration (docs/api/compatibility.md) before regenerating.
"""

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "apps" / "api"))

from app.main import app  # noqa: E402

OUT = REPO / "docs" / "api" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(render())
    print(f"wrote {OUT.relative_to(REPO)}")
