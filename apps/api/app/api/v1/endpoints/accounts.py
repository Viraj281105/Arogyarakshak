"""Account routes (ADR-026): register, sign in/out, profile, password change, email
verification, password reset, account deletion, the signed-in user's case list and
claiming a guest case. Mounted under /api/v1/kadi (accounts are Kadi shared infrastructure).

Thin HTTP layer: use cases live in app.services.accounts. Every response for an unknown
account is identical to the one for a known account (enumeration resistance), and no
response, log line or URL ever carries a password or token — except the bearer token in
the login/password-change response a mobile client explicitly asked for.
"""

from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.account_auth import (
    clear_session_cookie,
    reject_untrusted_origin,
    require_principal,
    set_session_cookie,
)
from app.case_auth import CASE_ACCESS_TOKEN_HEADER, require_claimable_case
from app.config import settings
from app.database import get_db
from app.models import KadiCase, KadiUser
from app.rate_limit import limiter, resolve_client_ip
from app.services import accounts
from app.services.accounts import (
    CaseOwnedElsewhere,
    InvalidAccountToken,
    InvalidCredentials,
    InvalidEmail,
    IssuedSession,
    PasswordPolicyError,
    Principal,
)
from app.services.mail import MailTransport, get_mail_transport

router = APIRouter()

AUTH_PREFIX = "/auth"

_ACCEPTED_REGISTRATION = (
    "If this email address can be registered, the account is ready: sign in with it. "
    "If it is already registered, sign in with its existing password."
)
_NO_RESET_YET = " Password reset needs email, which this server is not configured to send (ADR-030)."
_ACCEPTED_EMAIL_REQUEST = "If an account matches, a message is on its way."
_NO_MESSAGE_YET = " Email delivery is not configured on this server (ADR-030), so no message will arrive."


def accepted_registration() -> str:
    return _ACCEPTED_REGISTRATION + ("" if settings.email_delivery_enabled else _NO_RESET_YET)


def accepted_email_request() -> str:
    return _ACCEPTED_EMAIL_REQUEST + ("" if settings.email_delivery_enabled else _NO_MESSAGE_YET)


INVALID_CREDENTIALS_DETAIL = (
    "Email or password is incorrect. After repeated failures, sign-in from this device is slowed down for a few minutes."
)
INVALID_EMAIL_DETAIL = "Enter a valid email address."
INVALID_TOKEN_DETAIL = "This link is invalid or has expired. Request a new one."
CASE_OWNED_ELSEWHERE_DETAIL = "This case already belongs to another account."
AUTH_RATE_LIMITED_DETAIL = "Too many attempts. Wait a minute and try again."

EMAIL_FIELD = Field(..., min_length=1, max_length=320, description="Login email address.")
PASSWORD_FIELD = Field(..., min_length=1, max_length=1024)


def auth_attempt_guard(request: Request) -> None:
    """Stricter per-IP bucket (ADR-026 §7) plus the login-CSRF Origin check."""
    allowed, retry_after = limiter.check(
        f"auth:{resolve_client_ip(request)}", limit=settings.auth_rate_limit_per_minute
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=AUTH_RATE_LIMITED_DETAIL,
            headers={"Retry-After": str(retry_after)},
        )
    reject_untrusted_origin(request)


# --- schemas -------------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: str = EMAIL_FIELD
    password: str = PASSWORD_FIELD


class LoginRequest(BaseModel):
    email: str = EMAIL_FIELD
    password: str = PASSWORD_FIELD
    session_transport: Literal["cookie", "bearer"] = Field(
        default="cookie",
        description="cookie (web): httpOnly session cookie, no token in the body. bearer (mobile): "
        "the token is returned once in `token`; send it as `Authorization: Bearer`.",
    )


class EmailRequest(BaseModel):
    email: str = EMAIL_FIELD


class TokenRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=512)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=512)
    new_password: str = PASSWORD_FIELD


class ChangePasswordRequest(BaseModel):
    current_password: str = PASSWORD_FIELD
    new_password: str = PASSWORD_FIELD


class DeleteAccountRequest(BaseModel):
    password: str = PASSWORD_FIELD


class AcceptedResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    message: str


class UserResponse(BaseModel):
    id: str
    email: str
    email_verified: bool
    email_verified_at: Optional[datetime] = None
    created_at: datetime
    is_demo: bool = Field(False, description="The synthetic demonstration account: its data is not real.")
    display_name: Optional[str] = Field(None, description="Set only for the demonstration account.")


class SessionInfo(BaseModel):
    transport: Literal["cookie", "bearer"]
    expires_at: datetime
    idle_timeout_minutes: int


class SessionResponse(BaseModel):
    user: UserResponse
    session: SessionInfo
    token: Optional[str] = Field(
        None, description="Bearer sessions only, returned once. Always null for cookie sessions."
    )


class StatusResponse(BaseModel):
    status: str


class DeleteAccountResponse(BaseModel):
    deleted: bool = True
    cases_erased: int


class OwnedCaseSummary(BaseModel):
    id: str
    status: str
    consent_opt_in: bool
    total_charged: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class OwnedCaseList(BaseModel):
    cases: List[OwnedCaseSummary]


class ClaimResponse(BaseModel):
    id: str
    owned: bool = True
    claimed: bool = Field(..., description="False when the case already belonged to this account.")


# --- helpers -------------------------------------------------------------------------------


def _user_view(user: KadiUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        email_verified_at=user.email_verified_at,
        created_at=user.created_at,
        is_demo=accounts.is_demo_address(user.email),
        display_name=accounts.DEMO_ACCOUNT_NAME if accounts.is_demo_address(user.email) else None,
    )


def _session_response(issued: IssuedSession, response: Response) -> SessionResponse:
    token = None
    if issued.session.transport == accounts.TRANSPORT_COOKIE:
        set_session_cookie(response, issued.token)
    else:
        token = issued.token
    return SessionResponse(
        user=_user_view(issued.user),
        session=SessionInfo(
            transport=issued.session.transport,
            expires_at=issued.session.expires_at,
            idle_timeout_minutes=settings.session_idle_timeout_minutes,
        ),
        token=token,
    )


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


# --- routes --------------------------------------------------------------------------------


class AuthConfigResponse(BaseModel):
    email_delivery: bool = Field(..., description="Whether this server can send account email.")


@router.get(f"{AUTH_PREFIX}/config", response_model=AuthConfigResponse)
async def auth_config():
    """What the signed-out pages need to say honestly: can this server send email?"""
    return AuthConfigResponse(email_delivery=settings.email_delivery_enabled)


@router.post(
    f"{AUTH_PREFIX}/register",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(auth_attempt_guard)],
)
async def register(
    req: RegisterRequest, db: AsyncSession = Depends(get_db), mail: MailTransport = Depends(get_mail_transport)
):
    """Creates an account. The same 202 answers a new and an already-registered address;
    registration does not sign in (call login next)."""
    try:
        await accounts.register(db, req.email, req.password, mail)
    except InvalidEmail:
        raise _unprocessable(INVALID_EMAIL_DETAIL)
    except PasswordPolicyError as exc:
        raise _unprocessable(str(exc))
    return AcceptedResponse(message=accepted_registration())


@router.post(f"{AUTH_PREFIX}/login", response_model=SessionResponse, dependencies=[Depends(auth_attempt_guard)])
async def login(req: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Signs in. Every failure is the same 401."""
    try:
        issued = await accounts.login(
            db, req.email, req.password, req.session_transport, client=resolve_client_ip(request)
        )
    except InvalidCredentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS_DETAIL)
    return _session_response(issued, response)


@router.post(f"{AUTH_PREFIX}/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(principal: Principal = Depends(require_principal), db: AsyncSession = Depends(get_db)):
    """Revokes the presented session (and clears the cookie for a cookie session)."""
    await accounts.logout(db, principal)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if principal.session.transport == accounts.TRANSPORT_COOKIE:
        clear_session_cookie(response)
    return response


@router.get(f"{AUTH_PREFIX}/me", response_model=UserResponse)
async def me(principal: Principal = Depends(require_principal)):
    return _user_view(principal.user)


# Password-checking routes share the auth bucket, so a stolen session cannot be used to
# guess the current password faster than a login could.
@router.post(f"{AUTH_PREFIX}/password", response_model=SessionResponse, dependencies=[Depends(auth_attempt_guard)])
async def change_password(
    req: ChangePasswordRequest,
    request: Request,
    response: Response,
    principal: Principal = Depends(require_principal),
    db: AsyncSession = Depends(get_db),
):
    """Changes the password, revokes every session and returns one fresh session."""
    try:
        issued = await accounts.change_password(
            db, principal, req.current_password, req.new_password, client=resolve_client_ip(request)
        )
    except InvalidCredentials:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The current password is incorrect.")
    except PasswordPolicyError as exc:
        raise _unprocessable(str(exc))
    return _session_response(issued, response)


@router.post(
    f"{AUTH_PREFIX}/verification/request",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(auth_attempt_guard)],
)
async def request_verification(
    req: EmailRequest, db: AsyncSession = Depends(get_db), mail: MailTransport = Depends(get_mail_transport)
):
    await accounts.request_verification(db, req.email, mail)
    return AcceptedResponse(message=accepted_email_request())


@router.post(
    f"{AUTH_PREFIX}/verification/confirm",
    response_model=StatusResponse,
    dependencies=[Depends(auth_attempt_guard)],
)
async def confirm_verification(req: TokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        await accounts.confirm_verification(db, req.token)
    except InvalidAccountToken:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_DETAIL)
    return StatusResponse(status="verified")


@router.post(
    f"{AUTH_PREFIX}/password-reset/request",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(auth_attempt_guard)],
)
async def request_password_reset(
    req: EmailRequest, db: AsyncSession = Depends(get_db), mail: MailTransport = Depends(get_mail_transport)
):
    await accounts.request_password_reset(db, req.email, mail)
    return AcceptedResponse(message=accepted_email_request())


@router.post(
    f"{AUTH_PREFIX}/password-reset/confirm",
    response_model=StatusResponse,
    dependencies=[Depends(auth_attempt_guard)],
)
async def confirm_password_reset(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Sets a new password and signs out every session. Does not sign in."""
    try:
        await accounts.confirm_password_reset(db, req.token, req.new_password)
    except InvalidAccountToken:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_DETAIL)
    except PasswordPolicyError as exc:
        raise _unprocessable(str(exc))
    return StatusResponse(status="password_reset")


@router.delete(f"{AUTH_PREFIX}/me", response_model=DeleteAccountResponse, dependencies=[Depends(auth_attempt_guard)])
async def delete_account(
    req: DeleteAccountRequest,
    request: Request,
    response: Response,
    principal: Principal = Depends(require_principal),
    db: AsyncSession = Depends(get_db),
):
    """Erases the account: every owned case (ADR-010 cascade), the account's own BimaNyay
    records without a case, sessions, tokens, the user."""
    try:
        erased = await accounts.delete_account(db, principal, req.password, client=resolve_client_ip(request))
    except InvalidCredentials:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The password is incorrect.")
    if principal.session.transport == accounts.TRANSPORT_COOKIE:
        clear_session_cookie(response)
    return DeleteAccountResponse(cases_erased=erased)


@router.get("/cases", response_model=OwnedCaseList)
async def list_my_cases(principal: Principal = Depends(require_principal), db: AsyncSession = Depends(get_db)):
    """The signed-in account's live cases, newest first. Never includes case tokens.
    Expired cases are already purged or about to be (D1a is open, ADR-026 §11)."""
    cases = await accounts.list_owned_live_cases(db, principal.user)
    return OwnedCaseList(cases=[OwnedCaseSummary.model_validate(c, from_attributes=True) for c in cases])


@router.post("/cases/{case_id}/claim", response_model=ClaimResponse)
async def claim_case(
    case_id: str,
    principal: Principal = Depends(require_principal),
    case: KadiCase = Depends(require_claimable_case),
    db: AsyncSession = Depends(get_db),
    x_case_access_token: Optional[str] = Header(None, alias=CASE_ACCESS_TOKEN_HEADER),
):
    """Moves a case started before sign-in was required into the signed-in account. Needs
    the session AND the case's X-Case-Access-Token; afterwards the token is discarded."""
    try:
        claimed = await accounts.claim_case(db, case, principal.user, x_case_access_token)
    except CaseOwnedElsewhere:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=CASE_OWNED_ELSEWHERE_DETAIL)
    return ClaimResponse(id=case.id, claimed=claimed)
