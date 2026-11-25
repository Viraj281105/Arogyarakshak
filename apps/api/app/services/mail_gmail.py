"""Gmail delivery for account email (ADR-030).

Sends through the Gmail API over HTTPS with an OAuth 2.0 refresh token belonging to one
dedicated sender mailbox. Standard library only. This is the API's only outbound connection
besides Groq, and it exists only when an operator sets ``MAIL_TRANSPORT=gmail_api``.

Rules (ADR-026 section 8, kept):
- a message carries no healthcare information, only the account link;
- the single-use token travels in the URL fragment, which browsers never send to a server;
- nothing here logs an address, a token, a credential or a provider response body;
- delivery runs off the request thread, so the response time of a reset request does not
  reveal whether the account exists.
"""

import base64
import json
import logging
import urllib.parse
import urllib.request
from concurrent.futures import Executor, ThreadPoolExecutor
from email.message import EmailMessage
from typing import Callable, Optional

from app.config import settings
from app.services.mail import PURPOSE_RESET_PASSWORD, PURPOSE_VERIFY_EMAIL, AccountMail

logger = logging.getLogger("arogyarakshak.accounts")

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
TIMEOUT_SECONDS = 15

# The account stores no language preference, so each message carries all three. Hindi and
# Marathi are machine translations awaiting native-speaker review (docs/localization.md).
_TEMPLATES = {
    PURPOSE_VERIFY_EMAIL: (
        "Confirm your ArogyaRakshak email address",
        "/verify",
        (
            "Open this link to confirm your email address. It works once and expires.",
            "अपना ईमेल पता पुष्ट करने के लिए यह लिंक खोलें। यह एक ही बार काम करता है और इसकी समय-सीमा है।",
            "तुमचा ईमेल पत्ता निश्चित करण्यासाठी ही लिंक उघडा. ती एकदाच चालते आणि तिची मुदत संपते.",
        ),
    ),
    PURPOSE_RESET_PASSWORD: (
        "Reset your ArogyaRakshak password",
        "/reset-password",
        (
            "Open this link to choose a new password. It works once and expires soon.",
            "नया पासवर्ड चुनने के लिए यह लिंक खोलें। यह एक ही बार काम करता है और जल्द समाप्त हो जाता है।",
            "नवीन पासवर्ड निवडण्यासाठी ही लिंक उघडा. ती एकदाच चालते आणि लवकरच तिची मुदत संपते.",
        ),
    ),
}
_IGNORE = (
    "If you did not ask for this, ignore this message.",
    "यदि आपने यह अनुरोध नहीं किया है, तो इस संदेश को अनदेखा करें।",
    "तुम्ही ही विनंती केली नसेल तर हा संदेश दुर्लक्षित करा.",
)

_executor: Optional[ThreadPoolExecutor] = None


def _default_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="account-mail")
    return _executor


class GmailApiTransport:
    name = "gmail_api"

    def __init__(
        self,
        *,
        sender: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        web_base_url: str,
        opener: Optional[Callable] = None,
        executor: Optional[Executor] = None,
    ) -> None:
        self._sender = sender
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._web_base_url = web_base_url.rstrip("/")
        self._opener = opener
        self._executor = executor

    def send(self, message: AccountMail) -> bool:
        """Queues the message. True means handed to the delivery thread, not delivered."""
        if message.purpose not in _TEMPLATES:
            return False
        (self._executor or _default_executor()).submit(self._deliver_safely, message)
        return True

    def compose(self, message: AccountMail) -> EmailMessage:
        subject, path, lines = _TEMPLATES[message.purpose]
        link = f"{self._web_base_url}{path}#token={urllib.parse.quote(message.token, safe='')}"
        mail = EmailMessage()
        mail["To"] = message.to
        mail["From"] = self._sender
        mail["Subject"] = subject
        mail.set_content("\n\n".join([*lines, link, *_IGNORE]) + "\n")
        return mail

    def deliver(self, message: AccountMail) -> None:
        """Sends one message now. Raises on any provider or network failure."""
        access_token = self._access_token()
        raw = base64.urlsafe_b64encode(self.compose(message).as_bytes()).decode("ascii")
        self._post(
            SEND_URL,
            json.dumps({"raw": raw}).encode("utf-8"),
            {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        )

    def _deliver_safely(self, message: AccountMail) -> None:
        try:
            self.deliver(message)
            logger.info("Account email (%s) accepted by Gmail.", message.purpose)
        except Exception as exc:  # the type only: provider errors can echo the request
            logger.error("Account email (%s) was not sent: %s.", message.purpose, type(exc).__name__)

    def _access_token(self) -> str:
        form = urllib.parse.urlencode(
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("ascii")
        body = self._post(TOKEN_URL, form, {"Content-Type": "application/x-www-form-urlencoded"})
        return json.loads(body)["access_token"]

    def _post(self, url: str, data: bytes, headers: dict) -> bytes:
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        opener = self._opener or urllib.request.urlopen
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()


def gmail_transport_from_settings() -> GmailApiTransport:
    return GmailApiTransport(
        sender=settings.gmail_sender,
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        refresh_token=settings.gmail_refresh_token,
        web_base_url=settings.web_app_base_url,
    )
