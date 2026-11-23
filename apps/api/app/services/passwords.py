"""Password policy and hashing with stdlib scrypt (ADR-026 section 3).

Hash format: ``scrypt$<n>$<r>$<p>$<salt b64>$<key b64>``. The parameters travel with the
hash so they can be raised later; ``verify_password`` reports when a stored hash used
weaker parameters than the current settings so the caller can re-hash it.

Hashing is CPU- and memory-bound (~32 MiB per call at the defaults): call the ``*_async``
wrappers from request handlers so the event loop is never blocked.
"""

import asyncio
import base64
import hashlib
import hmac
import secrets
import unicodedata
from typing import Optional, Tuple

from app.config import settings

SCHEME = "scrypt"
SALT_BYTES = 16
KEY_BYTES = 64
MAXMEM = 64 * 1024 * 1024

MIN_PASSWORD_CHARS = 12
MAX_PASSWORD_CHARS = 128


class PasswordPolicyError(ValueError):
    """The password does not meet the policy. The message is safe to show the user and
    never contains the password."""


def normalise_password(password: str) -> str:
    """NFKC, so the same password typed with different input methods verifies the same."""
    return unicodedata.normalize("NFKC", password)


def check_password_policy(password: str, *, email: Optional[str] = None) -> str:
    """Returns the normalised password or raises PasswordPolicyError. Length-based only
    (NIST SP 800-63B): no composition rules, no rotation."""
    normalised = normalise_password(password)
    if len(normalised) < MIN_PASSWORD_CHARS:
        raise PasswordPolicyError(f"Use a password of at least {MIN_PASSWORD_CHARS} characters.")
    if len(normalised) > MAX_PASSWORD_CHARS:
        raise PasswordPolicyError(f"Use a password of at most {MAX_PASSWORD_CHARS} characters.")
    if not normalised.strip():
        raise PasswordPolicyError("The password cannot be only spaces.")
    if email and normalised.strip().lower() == email.strip().lower():
        raise PasswordPolicyError("The password cannot be your email address.")
    return normalised


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        normalise_password(password).encode("utf-8"), salt=salt, n=n, r=r, p=p, maxmem=MAXMEM, dklen=KEY_BYTES
    )


def _current_params() -> Tuple[int, int, int]:
    return settings.password_scrypt_n, settings.password_scrypt_r, settings.password_scrypt_p


def hash_password(password: str) -> str:
    n, r, p = _current_params()
    salt = secrets.token_bytes(SALT_BYTES)
    key = _derive(password, salt, n, r, p)
    return f"{SCHEME}${n}${r}${p}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, stored: str) -> Tuple[bool, bool]:
    """Returns (matches, needs_rehash). A malformed stored hash never matches."""
    try:
        scheme, n_s, r_s, p_s, salt_s, key_s = stored.split("$")
        if scheme != SCHEME:
            return False, False
        n, r, p = int(n_s), int(r_s), int(p_s)
        salt = base64.b64decode(salt_s)
        expected = base64.b64decode(key_s)
    except (ValueError, TypeError):
        return False, False
    candidate = _derive(password, salt, n, r, p)
    matches = hmac.compare_digest(candidate, expected)
    return matches, matches and (n, r, p) != _current_params()


_dummy_hash: Optional[str] = None


def dummy_verify(password: str) -> None:
    """Spends the same work as a real verification, for an email that has no account, so
    response time does not reveal whether an account exists."""
    global _dummy_hash
    if _dummy_hash is None or _dummy_hash.split("$")[1:4] != [str(v) for v in _current_params()]:
        _dummy_hash = hash_password(secrets.token_urlsafe(16))
    verify_password(password, _dummy_hash)


async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(password: str, stored: str) -> Tuple[bool, bool]:
    return await asyncio.to_thread(verify_password, password, stored)


async def dummy_verify_async(password: str) -> None:
    await asyncio.to_thread(dummy_verify, password)
