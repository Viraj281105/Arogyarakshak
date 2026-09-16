"""
Auth-aware TestClient (ADR-009 test-infrastructure shim).

Adding real per-case authorization (app/case_auth.py) means every case-scoped request
now needs an `X-Case-Access-Token` header. Hand-editing that into several hundred
pre-existing `client.get(...)`/`client.post(...)` call sites across test_api.py would be
enormous churn for a concern orthogonal to what most of those tests actually verify
(redaction, audit math, PDF content, consent, ...).

`AuthAwareTestClient` closes that gap the same way a real single-page-app client would:
it remembers the token returned by the most recent case it created, on this same client
instance, and attaches it automatically to any later request whose URL path names that
case id — UNLESS the caller already set the header explicitly (which is exactly how the
new adversarial tests in test_case_authorization.py prove real denial: they pass an
explicit missing/wrong/foreign token, which is never overridden).

This shim does not weaken the security property being tested. The actual boundary is
enforced entirely server-side in app/case_auth.py; this class only saves whoever holds
ITS OWN client instance from re-typing a header on every call — precisely what a real
browser tab does by keeping the token in its own memory/state.
"""

import re
from typing import Dict

from fastapi.testclient import TestClient

_CASE_ID_IN_PATH = re.compile(r"/cases/([^/?]+)")
_TOKEN_HEADER = "X-Case-Access-Token"


class AuthAwareTestClient(TestClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._case_tokens: Dict[str, str] = {}

    def request(self, method, url, *args, **kwargs):
        headers = kwargs.get("headers")
        header_keys_lower = {k.lower() for k in headers} if headers else set()

        if _TOKEN_HEADER.lower() not in header_keys_lower:
            match = _CASE_ID_IN_PATH.search(str(url))
            if match:
                token = self._case_tokens.get(match.group(1))
                if token:
                    headers = dict(headers or {})
                    headers[_TOKEN_HEADER] = token
                    kwargs["headers"] = headers

        response = super().request(method, url, *args, **kwargs)

        if method.upper() == "POST" and str(url).rstrip("/").endswith("/kadi/cases") and response.status_code == 201:
            try:
                data = response.json()
                if "id" in data and "access_token" in data:
                    self._case_tokens[data["id"]] = data["access_token"]
            except ValueError:
                pass

        return response

    def forget_token(self, case_id: str) -> None:
        """Used by adversarial tests to simulate a client that never had this case's
        token — e.g. a different browser/device holding only the case id."""
        self._case_tokens.pop(case_id, None)
