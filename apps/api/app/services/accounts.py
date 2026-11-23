"""User accounts, sessions, verification/reset and case ownership — use cases (ADR-026).

Shared by the account routes (``app.api.v1.endpoints.accounts``), the case-access
dependency (``app.case_auth``), case creation and the retention sweep. Raises the
exceptions below; the HTTP layer maps them to generic responses.

Logging rule (ADR-026 section 7): the ``arogyarakshak.accounts`` logger records user ids
only — never an email address, a password or a token.
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import KadiAccountToken, KadiCase, KadiSession, KadiUser
from app.services.mail import PURPOSE_RESET_PASSWORD, PURPOSE_VERIFY_EMAIL, AccountMail, MailTransport
from app.services.passwords import (
    PasswordPolicyError,
    check_password_policy,
    dummy_verify_async,
    hash_password_async,
    verify_password_async,
)

logger = logging.getLogger("arogyarakshak.accounts")

TRANSPORT_COOKIE = "cookie"
TRANSPORT_BEARER = "bearer"
SESSION_TOUCH_INTERVAL = timedelta(seconds=60)
MAX_EMAIL_CHARS = 254

__all__ = [
    "AccountError",
    "InvalidEmail",
    "InvalidCredentials",
    "InvalidAccountToken",
    "CaseOwnedElsewhere",
    "PasswordPolicyError",
    "Principal",
    "IssuedSession",
    "utcnow",
]


def utcnow() -> datetime:
    """The service clock. Tests monkeypatch this to move time."""
    return datetime.utcnow()


class AccountError(Exception):
    """Base class. Messages are generic and safe to return."""


class InvalidEmail(AccountError):
    pass


class InvalidCredentials(AccountError):
    pass


class InvalidAccountToken(AccountError):
    pass


class CaseOwnedElsewhere(AccountError):
    pass


@dataclass
class Principal:
    user: KadiUser
    session: KadiSession


@dataclass
class IssuedSession:
    token: str
    session: KadiSession
    user: KadiUser


# --- helpers ---------------------------------------------------------------------------


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_token() -> Tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def normalise_email(raw: str) -> str:
    """Trimmed and lower-cased (the whole address — a documented simplification), with a
    structural check only; deliverability is unknowable without sending mail."""
    email = (raw or "").strip().lower()
    if not email or len(email) > MAX_EMAIL_CHARS or any(c.isspace() or ord(c) < 32 for c in email):
        raise InvalidEmail()
    local, sep, domain = email.rpartition("@")
    if not sep or not local or "@" in local or len(local) > 64:
        raise InvalidEmail()
    if "." not in domain or domain.startswith(".") or domain.endswith(".") or ".." in domain:
        raise InvalidEmail()
    return email


async def _user_by_email(db: AsyncSession, email: str) -> Optional[KadiUser]:
    result = await db.execute(select(KadiUser).where(KadiUser.email == email))
    return result.scalar_one_or_none()


def _session_expiry(now: datetime) -> datetime:
    return now + timedelta(hours=settings.session_lifetime_hours)


def _idle_limit() -> timedelta:
    return timedelta(minutes=settings.session_idle_timeout_minutes)


def _create_session(db: AsyncSession, user: KadiUser, transport: str, now: datetime) -> IssuedSession:
    if transport not in (TRANSPORT_COOKIE, TRANSPORT_BEARER):
        raise ValueError("unknown session transport")
    token, token_hash = _new_token()
    session = KadiSession(
        id=secrets.token_hex(16),
        user_id=user.id,
        token_hash=token_hash,
        transport=transport,
        created_at=now,
        last_seen_at=now,
        expires_at=_session_expiry(now),
    )
    db.add(session)
    return IssuedSession(token=token, session=session, user=user)


async def _revoke_all_sessions(db: AsyncSession, user_id: str, now: datetime) -> None:
    await db.execute(
        update(KadiSession)
        .where(KadiSession.user_id == user_id, KadiSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )


async def _issue_account_token(db: AsyncSession, user: KadiUser, purpose: str, now: datetime) -> AccountMail:
    """Creates a single-use token (hash stored) and voids earlier unused ones of the same
    purpose. Returns the message to deliver AFTER the caller commits."""
    await db.execute(
        delete(KadiAccountToken).where(
            KadiAccountToken.user_id == user.id,
            KadiAccountToken.purpose == purpose,
            KadiAccountToken.used_at.is_(None),
        )
    )
    ttl = (
        timedelta(hours=settings.account_verification_token_ttl_hours)
        if purpose == PURPOSE_VERIFY_EMAIL
        else timedelta(minutes=settings.password_reset_token_ttl_minutes)
    )
    token, token_hash = _new_token()
    db.add(
        KadiAccountToken(
            id=secrets.token_hex(16),
            user_id=user.id,
            purpose=purpose,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + ttl,
        )
    )
    return AccountMail(to=user.email, purpose=purpose, token=token)


def _deliver(mail: MailTransport, message: AccountMail, user_id: str) -> None:
    try:
        delivered = mail.send(message)
    except Exception:
        logger.exception("Mail transport failed for an account message (%s, user %s).", message.purpose, user_id)
        return
    if delivered:
        logger.info("Account message (%s) handed to the mail transport for user %s.", message.purpose, user_id)


async def _consume_account_token(db: AsyncSession, token: str, purpose: str, now: datetime) -> KadiAccountToken:
    if not token:
        raise InvalidAccountToken()
    result = await db.execute(
        select(KadiAccountToken).where(
            KadiAccountToken.token_hash == hash_token(token),
            KadiAccountToken.purpose == purpose,
        )
    )
    row = result.scalar_one_or_none()
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise InvalidAccountToken()
    return row


# --- registration and sign-in -------------------------------------------------------------


async def register(db: AsyncSession, email: str, password: str, mail: MailTransport) -> None:
    """Creates an account, or does nothing if the email is taken. The caller answers the
    same way in both cases (enumeration resistance). Raises InvalidEmail or
    PasswordPolicyError for input that is invalid regardless of existing accounts."""
    email = normalise_email(email)
    normalised = check_password_policy(password, email=email)
    # Hash on both paths so the response time does not reveal an existing account.
    password_hash = await hash_password_async(normalised)
    existing = await _user_by_email(db, email)
    if existing is not None:
        logger.info("Registration for an already-registered address ignored (user %s).", existing.id)
        return

    now = utcnow()
    user = KadiUser(
        id=f"USR-{secrets.token_hex(12)}",
        email=email,
        password_hash=password_hash,
        password_changed_at=now,
        failed_login_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        # A concurrent registration for the same address won the race.
        await db.rollback()
        logger.info("Concurrent registration for one address; the second was ignored.")
        return
    message = await _issue_account_token(db, user, PURPOSE_VERIFY_EMAIL, now)
    await db.commit()
    logger.info("Account %s registered.", user.id)
    _deliver(mail, message, user.id)


async def login(db: AsyncSession, email: str, password: str, transport: str) -> IssuedSession:
    """Raises InvalidCredentials for every failure: unknown email, wrong password, or a
    paused account. Each path spends one scrypt verification."""
    try:
        email = normalise_email(email)
    except InvalidEmail:
        await dummy_verify_async(password or "")
        raise InvalidCredentials()
    user = await _user_by_email(db, email)
    if user is None:
        await dummy_verify_async(password or "")
        raise InvalidCredentials()

    now = utcnow()
    if user.login_locked_until is not None and user.login_locked_until > now:
        await dummy_verify_async(password or "")
        raise InvalidCredentials()

    matches, needs_rehash = await verify_password_async(password or "", user.password_hash)
    if not matches:
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= settings.login_max_failures:
            user.login_locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_count = 0
            logger.warning(
                "Sign-in paused for user %s for %d minute(s) after %d consecutive failures.",
                user.id, settings.login_lockout_minutes, settings.login_max_failures,
            )
        await db.commit()
        raise InvalidCredentials()

    user.failed_login_count = 0
    user.login_locked_until = None
    if needs_rehash:
        user.password_hash = await hash_password_async(password)
    issued = _create_session(db, user, transport, now)
    await db.commit()
    logger.info("User %s signed in (%s session).", user.id, transport)
    return issued


async def resolve_session_token(db: AsyncSession, token: Optional[str]) -> Optional[Principal]:
    """The live session and user for a presented token, or None (unknown, revoked,
    expired or idle). Refreshes last_seen_at at most once a minute (flushed; the request's
    own commit persists it)."""
    if not token:
        return None
    result = await db.execute(select(KadiSession).where(KadiSession.token_hash == hash_token(token)))
    session = result.scalar_one_or_none()
    if session is None or session.revoked_at is not None:
        return None
    now = utcnow()
    if now >= session.expires_at or now - session.last_seen_at >= _idle_limit():
        return None
    user = await db.get(KadiUser, session.user_id)
    if user is None:
        return None
    if now - session.last_seen_at >= SESSION_TOUCH_INTERVAL:
        session.last_seen_at = now
        await db.flush()
    return Principal(user=user, session=session)


async def logout(db: AsyncSession, principal: Principal) -> None:
    principal.session.revoked_at = utcnow()
    await db.commit()
    logger.info("User %s signed out.", principal.user.id)


async def change_password(
    db: AsyncSession, principal: Principal, current_password: str, new_password: str
) -> IssuedSession:
    """Revokes every session of the user and issues one fresh session (same transport)."""
    user = principal.user
    matches, _ = await verify_password_async(current_password or "", user.password_hash)
    if not matches:
        raise InvalidCredentials()
    normalised = check_password_policy(new_password, email=user.email)
    now = utcnow()
    user.password_hash = await hash_password_async(normalised)
    user.password_changed_at = now
    await _revoke_all_sessions(db, user.id, now)
    await db.execute(
        delete(KadiAccountToken).where(
            KadiAccountToken.user_id == user.id, KadiAccountToken.purpose == PURPOSE_RESET_PASSWORD
        )
    )
    issued = _create_session(db, user, principal.session.transport, now)
    await db.commit()
    logger.info("User %s changed their password; all earlier sessions revoked.", user.id)
    return issued


# --- verification and reset ----------------------------------------------------------------


async def request_verification(db: AsyncSession, email: str, mail: MailTransport) -> None:
    """Issues a verification token for an existing, unverified account. Silent otherwise."""
    try:
        email = normalise_email(email)
    except InvalidEmail:
        return
    user = await _user_by_email(db, email)
    if user is None or user.email_verified_at is not None:
        return
    message = await _issue_account_token(db, user, PURPOSE_VERIFY_EMAIL, utcnow())
    await db.commit()
    _deliver(mail, message, user.id)


async def confirm_verification(db: AsyncSession, token: str) -> None:
    now = utcnow()
    row = await _consume_account_token(db, token, PURPOSE_VERIFY_EMAIL, now)
    user = await db.get(KadiUser, row.user_id)
    row.used_at = now
    if user is not None and user.email_verified_at is None:
        user.email_verified_at = now
    await db.commit()
    logger.info("User %s verified their email address.", row.user_id)


async def request_password_reset(db: AsyncSession, email: str, mail: MailTransport) -> None:
    try:
        email = normalise_email(email)
    except InvalidEmail:
        return
    user = await _user_by_email(db, email)
    if user is None:
        return
    message = await _issue_account_token(db, user, PURPOSE_RESET_PASSWORD, utcnow())
    await db.commit()
    _deliver(mail, message, user.id)


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> None:
    """Sets the new password, consumes the token, revokes every session and clears a
    sign-in pause. Signs nobody in."""
    now = utcnow()
    row = await _consume_account_token(db, token, PURPOSE_RESET_PASSWORD, now)
    user = await db.get(KadiUser, row.user_id)
    if user is None:
        raise InvalidAccountToken()
    normalised = check_password_policy(new_password, email=user.email)
    user.password_hash = await hash_password_async(normalised)
    user.password_changed_at = now
    user.failed_login_count = 0
    user.login_locked_until = None
    row.used_at = now
    await _revoke_all_sessions(db, user.id, now)
    await db.commit()
    logger.info("User %s reset their password; all sessions revoked.", user.id)


# --- cases ---------------------------------------------------------------------------------


async def list_owned_live_cases(db: AsyncSession, user: KadiUser) -> List[KadiCase]:
    now = utcnow()
    result = await db.execute(
        select(KadiCase)
        .where(KadiCase.owner_user_id == user.id, KadiCase.expires_at.is_not(None), KadiCase.expires_at > now)
        .order_by(KadiCase.created_at.desc())
    )
    return list(result.scalars().all())


async def claim_case(db: AsyncSession, case: KadiCase, user: KadiUser) -> bool:
    """Makes `user` the owner of an unowned case and disables its access token. The
    caller has already proven possession of that token (app.case_auth). Returns True when
    ownership changed, False when the user already owned it."""
    if case.owner_user_id == user.id:
        return False
    if case.owner_user_id is not None:
        raise CaseOwnedElsewhere()
    case.owner_user_id = user.id
    case.access_token_hash = None
    await db.commit()
    logger.info("User %s claimed case %s; its case access token is now disabled.", user.id, case.id)
    return True


async def delete_account(db: AsyncSession, principal: Principal, password: str) -> int:
    """Erases every owned case through the ADR-010 cascade, then the user's sessions,
    tokens and the user row, in one transaction. Returns the number of cases erased."""
    from app.services.case_purge import purge_case

    user = principal.user
    matches, _ = await verify_password_async(password or "", user.password_hash)
    if not matches:
        raise InvalidCredentials()
    result = await db.execute(select(KadiCase.id).where(KadiCase.owner_user_id == user.id))
    case_ids = [row[0] for row in result.all()]
    for case_id in case_ids:
        await purge_case(db, case_id)
    await db.execute(delete(KadiAccountToken).where(KadiAccountToken.user_id == user.id))
    await db.execute(delete(KadiSession).where(KadiSession.user_id == user.id))
    await db.execute(delete(KadiUser).where(KadiUser.id == user.id))
    await db.commit()
    logger.info("Account %s deleted with %d owned case(s).", user.id, len(case_ids))
    return len(case_ids)


async def sweep_expired_account_records(db: AsyncSession) -> int:
    """Deletes revoked, expired or idle sessions and used or expired account tokens.
    Called from the retention sweep. Does not commit."""
    now = utcnow()
    sessions = await db.execute(
        delete(KadiSession).where(
            or_(
                KadiSession.revoked_at.is_not(None),
                KadiSession.expires_at <= now,
                KadiSession.last_seen_at <= now - _idle_limit(),
            )
        )
    )
    tokens = await db.execute(
        delete(KadiAccountToken).where(
            or_(KadiAccountToken.used_at.is_not(None), KadiAccountToken.expires_at <= now)
        )
    )
    return (sessions.rowcount or 0) + (tokens.rowcount or 0)
