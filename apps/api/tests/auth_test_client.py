"""
Signed-in TestClient (ADR-029 test-infrastructure shim).

Every route needs an account session, so tests about redaction, audit maths, PDF content,
consent and so on use this client: it signs in one synthetic test account and sends its
bearer session with each request, exactly as the mobile client does. A request that sets its
own ``Authorization`` header is sent unchanged.

This does not weaken the property under test. The boundary is enforced server-side
(app/auth_gate.py, app/case_auth.py); signed-out and wrong-account behaviour is tested with
plain clients in test_mandatory_sign_in.py and test_case_authorization.py.

The database is dropped between tests while module-level clients live on, so the session is
re-created whenever conftest.py starts a new test (``SignedInTestClient.new_test``).
"""

from fastapi.testclient import TestClient

from app.services import accounts
from app.services.mail import DisabledMailTransport
from tests.account_helpers import PASSWORD, run_db

SHIM_EMAIL = "test-patient@example.org"


class AuthAwareTestClient(TestClient):
    _generation = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_generation = -1
        self._bearer = ""

    @classmethod
    def new_test(cls) -> None:
        cls._generation += 1

    def auth_headers(self) -> dict:
        """The signed-in account's headers, for tests that build requests another way."""
        if self._session_generation != AuthAwareTestClient._generation:

            async def sign_in(db):
                await accounts.register(db, SHIM_EMAIL, PASSWORD, DisabledMailTransport())
                issued = await accounts.login(db, SHIM_EMAIL, PASSWORD, "bearer", client="test-shim")
                return issued.token

            self._bearer = run_db(sign_in)
            self._session_generation = AuthAwareTestClient._generation
        return {"Authorization": f"Bearer {self._bearer}"}

    def request(self, method, url, *args, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        if "authorization" not in {k.lower() for k in headers}:
            headers.update(self.auth_headers())
            kwargs["headers"] = headers
        return super().request(method, url, *args, **kwargs)
