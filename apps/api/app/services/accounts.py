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
from app.models import (
    BimaNyayCase,
    BimaNyayGrievance,
    BimaNyayTimelineEvent,
    KadiAccountToken,
    KadiCase,
    KadiSession,
    KadiUser,
)
from app.services.login_throttle import throttle as login_throttle
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
# The synthetic demonstration account (docs/DEMO_GUIDE.md). Reserved: nobody can register it,
# nothing is ever emailed to it, and it works only while demo operations are allowed.
DEMO_ACCOUNT_EMAIL = "demo@arogyarakshak.in"
DEMO_ACCOUNT_NAME = "Aarav Sharma"

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


def is_demo_address(email: str) -> bool:
    return email == DEMO_ACCOUNT_EMAIL


def _demo_address_closed(email: str) -> bool:
    """The demo account outside a demo server: it must behave as if it did not exist."""
    return is_demo_address(email) and not settings.demo_operations_allowed


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


async def _find_usable_account_token(db: AsyncSession, token: str, purpose: str, now: datetime) -> KadiAccountToken:
    """Looks a token up without consuming it (so a reset can fail its password policy and
    the token stays usable)."""
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


async def _consume_account_token_atomically(db: AsyncSession, token_hash: str, purpose: str, now: datetime) -> None:
    """Single use under concurrency: one conditional UPDATE; only the request that flips
    used_at from NULL proceeds (works the same on SQLite and PostgreSQL)."""
    result = await db.execute(
        update(KadiAccountToken)
        .where(
            KadiAccountToken.token_hash == token_hash,
            KadiAccountToken.purpose == purpose,
            KadiAccountToken.used_at.is_(None),
            KadiAccountToken.expires_at > now,
        )
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        await db.rollback()
        raise InvalidAccountToken()


async def _check_password_or_throttle(user: KadiUser, password: str, client: str, now: datetime) -> bool:
    """Verifies ``password`` for ``user`` under the (account, client IP) throttle
    (app.services.login_throttle). Raises InvalidCredentials when throttled or wrong;
    a throttled attempt still spends one scrypt so it looks like any other failure.
    Returns needs_rehash on success. Used by login, password change and deletion."""
    if login_throttle.retry_after_seconds(user.id, client, now) > 0:
        await dummy_verify_async(password or "")
        raise InvalidCredentials()
    matches, needs_rehash = await verify_password_async(password or "", user.password_hash)
    if not matches:
        failures = login_throttle.record_failure(user.id, client, now)
        if failures == settings.login_free_failures:
            logger.warning(
                "Sign-in for user %s from one client is now slowed after %d failures in %d minute(s).",
                user.id, failures, settings.login_failure_window_minutes,
            )
        raise InvalidCredentials()
    login_throttle.record_success(user.id, client)
    return needs_rehash


# --- registration and sign-in -------------------------------------------------------------


async def register(db: AsyncSession, email: str, password: str, mail: MailTransport) -> None:
    """Creates an account, or does nothing if the email is taken. The caller answers the
    same way in both cases (enumeration resistance). Raises InvalidEmail or
    PasswordPolicyError for input that is invalid regardless of existing accounts."""
    email = normalise_email(email)
    normalised = check_password_policy(password, email=email)
    # Hash on both paths so the response time does not reveal an existing account.
    password_hash = await hash_password_async(normalised)
    if is_demo_address(email):
        logger.info("Registration for the reserved demo address ignored.")
        return
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


async def login(
    db: AsyncSession, email: str, password: str, transport: str, client: str = "unknown"
) -> IssuedSession:
    """Raises InvalidCredentials for every failure: unknown email, wrong password, or a
    throttled (account, client IP) pair. Each path spends one scrypt verification.
    ``client`` is the resolved client IP (app.rate_limit.resolve_client_ip)."""
    try:
        email = normalise_email(email)
    except InvalidEmail:
        await dummy_verify_async(password or "")
        raise InvalidCredentials()
    user = await _user_by_email(db, email)
    if user is None or _demo_address_closed(email):
        await dummy_verify_async(password or "")
        raise InvalidCredentials()

    now = utcnow()
    needs_rehash = await _check_password_or_throttle(user, password, client, now)
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
    if user is None or _demo_address_closed(user.email):
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
    db: AsyncSession, principal: Principal, current_password: str, new_password: str, client: str = "unknown"
) -> IssuedSession:
    """Revokes every session of the user and issues one fresh session (same transport).
    Wrong current passwords count toward the sign-in throttle (review L3)."""
    user = principal.user
    now = utcnow()
    await _check_password_or_throttle(user, current_password, client, now)
    normalised = check_password_policy(new_password, email=user.email)
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
    if user is None or user.email_verified_at is not None or is_demo_address(email):
        return
    message = await _issue_account_token(db, user, PURPOSE_VERIFY_EMAIL, utcnow())
    await db.commit()
    _deliver(mail, message, user.id)


async def confirm_verification(db: AsyncSession, token: str) -> None:
    now = utcnow()
    row = await _find_usable_account_token(db, token, PURPOSE_VERIFY_EMAIL, now)
    await _consume_account_token_atomically(db, row.token_hash, PURPOSE_VERIFY_EMAIL, now)
    user = await db.get(KadiUser, row.user_id)
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
    if user is None or is_demo_address(email):
        return
    message = await _issue_account_token(db, user, PURPOSE_RESET_PASSWORD, utcnow())
    await db.commit()
    _deliver(mail, message, user.id)


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> None:
    """Sets the new password, consumes the token, revokes every session and clears a
    sign-in pause. Signs nobody in."""
    now = utcnow()
    row = await _find_usable_account_token(db, token, PURPOSE_RESET_PASSWORD, now)
    user = await db.get(KadiUser, row.user_id)
    if user is None:
        raise InvalidAccountToken()
    normalised = check_password_policy(new_password, email=user.email)
    password_hash = await hash_password_async(normalised)
    # Consumed only now (the policy passed), and atomically: a concurrent second use loses.
    await _consume_account_token_atomically(db, row.token_hash, PURPOSE_RESET_PASSWORD, now)
    user.password_hash = password_hash
    user.password_changed_at = now
    await _revoke_all_sessions(db, user.id, now)
    await db.commit()
    logger.info("User %s reset their password; all sessions revoked.", user.id)


# --- the demonstration account --------------------------------------------------------------


async def reset_demo_user(db: AsyncSession, password: str) -> Tuple[str, int]:
    """Creates the demo account or resets it: new password, every session revoked, every
    owned case and stand-alone record erased. Returns (user id, cases erased). Commits.
    Refused unless demo operations are allowed."""
    from app.services.case_purge import purge_case

    if not settings.demo_operations_allowed:
        raise PermissionError("Demo operations are disabled: CLINICAL_DEMO_MODE is off or APP_ENV is production.")
    normalised = check_password_policy(password, email=DEMO_ACCOUNT_EMAIL)
    password_hash = await hash_password_async(normalised)
    now = utcnow()
    user = await _user_by_email(db, DEMO_ACCOUNT_EMAIL)
    erased = 0
    if user is None:
        user = KadiUser(
            id=f"USR-{secrets.token_hex(12)}",
            email=DEMO_ACCOUNT_EMAIL,
            password_hash=password_hash,
            password_changed_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        await db.flush()
    else:
        user.password_hash = password_hash
        user.password_changed_at = now
        await _revoke_all_sessions(db, user.id, now)
        rows = await db.execute(select(KadiCase.id).where(KadiCase.owner_user_id == user.id))
        for case_id in [row[0] for row in rows.all()]:
            await purge_case(db, case_id)
            erased += 1
        await _purge_owned_bimanyay_records(db, user.id)
    await db.commit()
    return user.id, erased


# --- cases ---------------------------------------------------------------------------------


async def list_owned_live_cases(db: AsyncSession, user: KadiUser) -> List[KadiCase]:
    now = utcnow()
    result = await db.execute(
        select(KadiCase)
        .where(KadiCase.owner_user_id == user.id, KadiCase.expires_at.is_not(None), KadiCase.expires_at > now)
        .order_by(KadiCase.created_at.desc())
    )
    return list(result.scalars().all())


async def claim_case(db: AsyncSession, case: KadiCase, user: KadiUser, presented_token: Optional[str]) -> bool:
    """Makes `user` the owner of an unowned case and disables its access token. The
    caller has already proven possession of that token (app.case_auth). Returns True when
    ownership changed, False when the user already owned it.

    One conditional UPDATE (review M2): it succeeds only while the case is still unowned
    AND still carries the presented token's hash, so of two concurrent claims exactly one
    wins and the other gets CaseOwnedElsewhere, never a false "claimed"."""
    if case.owner_user_id == user.id:
        return False
    if case.owner_user_id is not None or not presented_token:
        raise CaseOwnedElsewhere()
    result = await db.execute(
        update(KadiCase)
        .where(
            KadiCase.id == case.id,
            KadiCase.owner_user_id.is_(None),
            # Case tokens are hashed exactly like account tokens (SHA-256 hex, ADR-009).
            KadiCase.access_token_hash == hash_token(presented_token),
        )
        .values(owner_user_id=user.id, access_token_hash=None, updated_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        await db.rollback()
        raise CaseOwnedElsewhere()
    await db.commit()
    logger.info("User %s claimed case %s; its case access token is now disabled.", user.id, case.id)
    return True


async def delete_account(db: AsyncSession, principal: Principal, password: str, client: str = "unknown") -> int:
    """Erases every owned case through the ADR-010 cascade, the user's own BimaNyay
    records that have no case, then the user's sessions, tokens and the user row, in one
    transaction; afterwards drops each erased case's in-memory processing status, as
    DELETE /kadi/cases/{id} does. Returns the number of cases erased. Wrong passwords
    count toward the sign-in throttle (review L3)."""
    from app.services.case_ingestion import processing_status
    from app.services.case_purge import purge_case

    user = principal.user
    await _check_password_or_throttle(user, password, client, utcnow())
    result = await db.execute(select(KadiCase.id).where(KadiCase.owner_user_id == user.id))
    case_ids = [row[0] for row in result.all()]
    for case_id in case_ids:
        await purge_case(db, case_id)
    await _purge_owned_bimanyay_records(db, user.id)
    await db.execute(delete(KadiAccountToken).where(KadiAccountToken.user_id == user.id))
    await db.execute(delete(KadiSession).where(KadiSession.user_id == user.id))
    await db.execute(delete(KadiUser).where(KadiUser.id == user.id))
    await db.commit()
    for case_id in case_ids:
        processing_status.pop(case_id, None)
    logger.info("Account %s deleted with %d owned case(s).", user.id, len(case_ids))
    return len(case_ids)


async def _purge_owned_bimanyay_records(db: AsyncSession, user_id: str) -> None:
    rows = await db.execute(select(BimaNyayGrievance.id).where(BimaNyayGrievance.owner_user_id == user_id))
    grievance_ids = [row[0] for row in rows.all()]
    if grievance_ids:
        await db.execute(delete(BimaNyayTimelineEvent).where(BimaNyayTimelineEvent.grievance_id.in_(grievance_ids)))
    await db.execute(delete(BimaNyayGrievance).where(BimaNyayGrievance.owner_user_id == user_id))
    await db.execute(delete(BimaNyayCase).where(BimaNyayCase.owner_user_id == user_id))


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
