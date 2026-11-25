"""Account email transport (ADR-026 section 8, ADR-030).

``disabled`` (the default) delivers nothing and logs only that a message of a given purpose
was not delivered. ``gmail_api`` (app.services.mail_gmail) is used only when an operator
configures it. No transport logs the address or the token.

Tests inject ``InMemoryMailTransport`` through the ``get_mail_transport`` dependency to
exercise the full verification and reset flows.
"""

import logging
from dataclasses import dataclass
from typing import List, Protocol

from app.config import settings

logger = logging.getLogger("arogyarakshak.accounts")

PURPOSE_VERIFY_EMAIL = "verify_email"
PURPOSE_RESET_PASSWORD = "reset_password"


@dataclass(frozen=True)
class AccountMail:
    """What a transport needs to compose one message. ``token`` is the plaintext,
    single-use token; a real transport must put it in a URL fragment (#token=...), never
    a query string, and must never log it."""

    to: str
    purpose: str
    token: str


class MailTransport(Protocol):
    name: str

    def send(self, message: AccountMail) -> bool:
        """Returns True when the message was handed to a delivery channel."""
        ...


class DisabledMailTransport:
    name = "disabled"

    def send(self, message: AccountMail) -> bool:
        logger.info(
            "Account email (%s) not delivered: MAIL_TRANSPORT=disabled.",
            message.purpose,
        )
        return False


class InMemoryMailTransport:
    """Test double: keeps messages in a list. Never configured by settings."""

    name = "memory"

    def __init__(self) -> None:
        self.outbox: List[AccountMail] = []

    def send(self, message: AccountMail) -> bool:
        self.outbox.append(message)
        return True


def get_mail_transport() -> MailTransport:
    """FastAPI dependency (tests override it)."""
    if settings.mail_transport == "gmail_api":
        from app.services.mail_gmail import gmail_transport_from_settings  # it imports this module

        return gmail_transport_from_settings()
    return DisabledMailTransport()
