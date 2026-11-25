"""ADR-030 Gmail delivery: no live network here; the HTTP opener is a recorder."""

import base64
import io
import json
import logging
from concurrent.futures import Executor, Future
from email import message_from_bytes
from email.policy import default as default_policy

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.services.mail import (
    PURPOSE_RESET_PASSWORD,
    PURPOSE_VERIFY_EMAIL,
    AccountMail,
    DisabledMailTransport,
    get_mail_transport,
)
from app.services.mail_gmail import SEND_URL, TOKEN_URL, GmailApiTransport

TOKEN = "single-use-secret-token"
ADDRESS = "patient@example.org"
CREDENTIALS = {
    "sender": "noreply@example.org",
    "client_id": "cid",
    "client_secret": "client-secret-value",
    "refresh_token": "refresh-secret-value",
    "web_base_url": "https://app.example.org/",
}
GMAIL_SETTINGS = {
    "mail_transport": "gmail_api",
    "gmail_sender": "noreply@example.org",
    "gmail_client_id": "cid",
    "gmail_client_secret": "secret",
    "gmail_refresh_token": "refresh",
    "web_app_base_url": "https://app.example.org",
}


class Inline(Executor):
    """Runs the job at once and remembers that delivery was queued, not called directly."""

    def __init__(self):
        self.submitted = 0

    def submit(self, fn, *args, **kwargs):
        self.submitted += 1
        future = Future()
        future.set_result(fn(*args, **kwargs))
        return future


class Recorder:
    def __init__(self, fail=False):
        self.requests = []
        self.fail = fail

    def __call__(self, request, timeout):
        assert timeout > 0
        self.requests.append(request)
        if self.fail:
            raise OSError(f"provider echoed {TOKEN} and {ADDRESS}")
        body = {"access_token": "access"} if request.full_url == TOKEN_URL else {"id": "1"}
        return io.BytesIO(json.dumps(body).encode())


def _transport(opener, executor=None):
    return GmailApiTransport(opener=opener, executor=executor or Inline(), **CREDENTIALS)


def _sent_mail(recorder):
    send = [r for r in recorder.requests if r.full_url == SEND_URL][0]
    assert send.headers["Authorization"] == "Bearer access"
    raw = json.loads(send.data)["raw"]
    return message_from_bytes(base64.urlsafe_b64decode(raw), policy=default_policy)


@pytest.mark.parametrize("purpose,path", [(PURPOSE_RESET_PASSWORD, "/reset-password"), (PURPOSE_VERIFY_EMAIL, "/verify")])
def test_the_link_carries_the_token_only_in_the_fragment(purpose, path):
    recorder, executor = Recorder(), Inline()
    assert _transport(recorder, executor).send(AccountMail(ADDRESS, purpose, TOKEN)) is True
    assert executor.submitted == 1, "delivery is queued off the request thread"
    mail = _sent_mail(recorder)
    assert mail["To"] == ADDRESS and mail["From"] == CREDENTIALS["sender"]
    text = mail.get_content()
    assert f"https://app.example.org{path}#token={TOKEN}" in text
    assert "?token" not in text and TOKEN not in mail["Subject"]
    assert [r.full_url for r in recorder.requests] == [TOKEN_URL, SEND_URL]


def test_the_message_carries_no_healthcare_information():
    text = _transport(Recorder()).compose(AccountMail(ADDRESS, PURPOSE_RESET_PASSWORD, TOKEN)).get_content().lower()
    for word in ("case", "diagnos", "bill", "claim", "medicine", "hospital"):
        assert word not in text


def test_a_failure_is_logged_without_address_token_or_credentials(caplog):
    with caplog.at_level(logging.DEBUG, logger="arogyarakshak"):
        assert _transport(Recorder(fail=True)).send(AccountMail(ADDRESS, PURPOSE_RESET_PASSWORD, TOKEN))
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "was not sent" in text and "OSError" in text
    for secret in (TOKEN, ADDRESS, "client-secret-value", "refresh-secret-value"):
        assert secret not in text


def test_disabled_is_the_default(monkeypatch):
    monkeypatch.setattr(settings, "mail_transport", "disabled")
    assert isinstance(get_mail_transport(), DisabledMailTransport)
    assert Settings(_env_file=None).mail_transport == "disabled"


def test_gmail_is_selected_only_by_configuration(monkeypatch):
    for key, value in GMAIL_SETTINGS.items():
        monkeypatch.setattr(settings, key, value)
    assert isinstance(get_mail_transport(), GmailApiTransport)


@pytest.mark.parametrize("missing", [k for k in GMAIL_SETTINGS if k != "mail_transport"])
def test_incomplete_gmail_configuration_refuses_to_start(missing):
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, **{**GMAIL_SETTINGS, missing: ""})
    assert missing.upper() in str(error.value)


def test_production_requires_https_links():
    values = {**GMAIL_SETTINGS, "web_app_base_url": "http://app.example.org"}
    assert any("WEB_APP_BASE_URL" in e for e in Settings(_env_file=None, app_env="production", **values).production_config_errors())


@pytest.mark.parametrize("transport,expected", [("disabled", False), ("gmail_api", True)])
def test_the_signed_out_web_can_ask_whether_email_is_delivered(monkeypatch, transport, expected):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(settings, "mail_transport", transport)
    res = TestClient(app).get("/api/v1/kadi/auth/config")
    assert res.status_code == 200
    assert res.json() == {"email_delivery": expected}
