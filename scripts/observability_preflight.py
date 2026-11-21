#!/usr/bin/env python3
"""Checks run before `docker compose -f docker-compose.yml -f docker-compose.observability.yml up`.

Refuses (exit 1) when APP_ENV=production and GRAFANA_ADMIN_PASSWORD is still the development
default or shorter than 12 characters. The Grafana container applies the same rule in its
entrypoint, so skipping this script does not weaken the guard; it just fails earlier.
Reads the process environment, then ./.env for variables not already set. Prints variable
names only, never values.
"""

import os
import sys
from pathlib import Path

DEV_GRAFANA_PASSWORD = "arogyarakshak-dev-only"


def read_dotenv(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def check(env: dict) -> list:
    errors = []
    if env.get("APP_ENV", "development").strip().lower() == "production":
        password = env.get("GRAFANA_ADMIN_PASSWORD") or DEV_GRAFANA_PASSWORD
        if password == DEV_GRAFANA_PASSWORD or len(password) < 12:
            errors.append("GRAFANA_ADMIN_PASSWORD is the development default or shorter than 12 characters.")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    env = {**read_dotenv(root / ".env"), **os.environ}
    errors = check(env)
    for message in errors:
        print(f"observability preflight: refusing under APP_ENV=production: {message}", file=sys.stderr)
    if not errors:
        print("observability preflight: ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
