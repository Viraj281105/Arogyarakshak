"""User accounts, sessions and account tokens (ADR-026).

Accounts are shared infrastructure, so the tables carry the ``kadi_`` prefix. The only
personal datum is the login email. Session and account tokens are stored as SHA-256 hashes
only. Case ownership is ``KadiCase.owner_user_id`` (app/models/kadi.py).
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, String

from app.database import Base


class KadiUser(Base):
    __tablename__ = "kadi_users"

    id = Column(String, primary_key=True)
    # Normalised (trimmed, lower-cased) at the service layer before it reaches this column.
    email = Column(String(254), nullable=False, unique=True)
    # "scrypt$<n>$<r>$<p>$<salt b64>$<key b64>" (app/services/passwords.py).
    password_hash = Column(String, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class KadiSession(Base):
    __tablename__ = "kadi_sessions"
    __table_args__ = (
        CheckConstraint("transport IN ('cookie', 'bearer')", name="ck_kadi_sessions_transport"),
    )

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("kadi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    transport = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


class KadiAccountToken(Base):
    """Single-use email verification / password reset token (hash only)."""

    __tablename__ = "kadi_account_tokens"
    __table_args__ = (
        CheckConstraint("purpose IN ('verify_email', 'reset_password')", name="ck_kadi_account_tokens_purpose"),
    )

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("kadi_users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String, nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
