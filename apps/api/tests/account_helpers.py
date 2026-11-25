"""Shared helpers for the account tests (ADR-026).

Fixtures (fast scrypt, fake clock, in-memory mail outbox, relaxed auth limit) live in
conftest.py. Web clients run on https://testserver so the Secure ``__Host-`` session cookie is stored
and sent, and carry the API's own Origin so cookie-authenticated writes pass the CSRF
check. Tests that probe the Origin check build their own requests.
"""

import asyncio
from datetime import datetime, timedelta
from itertools import count

from fastapi.testclient import TestClient

from app.background import get_background_session
from app.main import app

WEB_ORIGIN = "https://testserver"
PASSWORD = "correct horse battery staple"
_emails = count(1)


def fresh_email() -> str:
    return f"patient{next(_emails)}@example.org"


def web_client() -> TestClient:
    return TestClient(app, base_url=WEB_ORIGIN, headers={"Origin": WEB_ORIGIN})


def plain_client() -> TestClient:
    return TestClient(app)


def register(client: TestClient, email: str, password: str = PASSWORD):
    res = client.post("/api/v1/kadi/auth/register", json={"email": email, "password": password})
    assert res.status_code == 202, res.text
    return res


def login(client: TestClient, email: str, password: str = PASSWORD, transport: str = "cookie"):
    return client.post(
        "/api/v1/kadi/auth/login",
        json={"email": email, "password": password, "session_transport": transport},
    )


def signed_in_web(email: "str | None" = None) -> "tuple[TestClient, str]":
    email = email or fresh_email()
    client = web_client()
    register(client, email)
    res = login(client, email)
    assert res.status_code == 200, res.text
    return client, email


def bearer_for(email: "str | None" = None) -> "tuple[dict, str]":
    """Registers (if new) and signs in with a bearer session. Returns (headers, email)."""
    email = email or fresh_email()
    client = plain_client()
    client.post("/api/v1/kadi/auth/register", json={"email": email, "password": PASSWORD})
    res = login(client, email, transport="bearer")
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}, email


def other_account() -> "dict":
    """Headers of a second, unrelated signed-in account."""
    return bearer_for()[0]


def run_db(fn):
    async def runner():
        async with get_background_session() as session:
            return await fn(session)

    return asyncio.run(runner())


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime.utcnow()

    def advance(self, **delta) -> None:
        self.now += timedelta(**delta)

    def __call__(self) -> datetime:
        return self.now


__all__ = [
    "PASSWORD",
    "WEB_ORIGIN",
    "FakeClock",
    "bearer_for",
    "fresh_email",
    "login",
    "other_account",
    "plain_client",
    "register",
    "run_db",
    "signed_in_web",
    "web_client",
]
