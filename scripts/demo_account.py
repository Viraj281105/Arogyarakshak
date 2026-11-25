"""Create or reset the synthetic demo account (docs/DEMO_GUIDE.md).

Run on a demo server only, against the same DATABASE_URL as the API, after the API has
applied its migrations:

    CLINICAL_DEMO_MODE=true PYTHONPATH=apps/api python scripts/demo_account.py

It refuses to run unless demo operations are allowed. Each run rotates the password, erases
the demo account's cases and loads the synthetic documents again. The password is printed
once and, with --save, also written to demo/.demo-credentials.json (git-ignored). Never
commit it and never reuse it anywhere else.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

CREDENTIALS_FILE = ROOT / "demo" / ".demo-credentials.json"


async def _run(save: bool) -> int:
    from app.background import get_background_session
    from app.clinical.demo_account import provision_demo_account
    from app.database import engine

    try:
        async with get_background_session() as db:
            result = await provision_demo_account(db)
    except PermissionError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    finally:
        await engine.dispose()

    print("Synthetic demo account ready (DEMO data only).")
    print(f"  Name:     {result['display_name']} (synthetic identity)")
    print(f"  Email:    {result['email']}")
    print(f"  Password: {result['password']}")
    print(f"  Cases:    {len(result['cases'])} loaded, {result['cases_erased']} erased")
    for case in result["cases"]:
        print(f"    scenario {case['scenario']}: {case['title']}")
    if save:
        CREDENTIALS_FILE.write_text(
            json.dumps({"email": result["email"], "password": result["password"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  Saved to {CREDENTIALS_FILE} (git-ignored; delete it after the demo).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save", action="store_true", help="also write demo/.demo-credentials.json")
    return asyncio.run(_run(parser.parse_args().save))


if __name__ == "__main__":
    raise SystemExit(main())
