"""
ArogyaRakshak API — Configuration.

Reads environment variables for the application. All config is centralised here
so that no module ever hardcodes credentials or model names.

GROQ_MODEL defaults to "openai/gpt-oss-120b".  Never use deprecated model
names (llama3-70b, llama-3.3-70b-versatile) — see AGENTS.md.
"""

from typing import List, Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


INSECURE_SIGNING_SECRET = "dev-insecure-signing-secret-change-in-production"


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    # --- Groq -----------------------------------------------------------------
    groq_model: str = "openai/gpt-oss-120b"
    groq_api_key: str = ""

    # --- Database -------------------------------------------------------------
    database_url: str = "postgresql://arogyarakshak:arogyarakshak@postgres:5432/arogyarakshak"

    # --- Security -------------------------------------------------------------
    cors_origins: str = "*"
    # HMAC key for BillNyay's document integrity signatures (#66) — proves a
    # downloaded appeal PDF is byte-for-byte what this server generated, NOT a
    # licensed digital signature certificate (DSC) under the IT Act, 2000. The
    # insecure default is fine for dev/test; production deployments must override
    # this via the DOCUMENT_SIGNING_SECRET env var.
    document_signing_secret: str = INSECURE_SIGNING_SECRET

    # --- Upload limits --------------------------------------------------------
    # Documents are read fully into RAM for transient parsing, so an unbounded upload is
    # a denial-of-service vector. 10 MB comfortably covers a scanned multi-page bill.
    max_upload_bytes: int = 10 * 1024 * 1024

    # --- Streaming ------------------------------------------------------------
    # The SSE generator polls until the case completes; without a ceiling a request for
    # an unknown case holds a connection open forever.
    sse_timeout_seconds: int = 120

    # --- Rate limiting ----------------------------------------------------------
    # There is no authentication (see docs/architecture/decisions/ADR-008 — accepted
    # risk for this project's scope). Without a request cap, an unauthenticated caller
    # can enumerate CASE-xxxxxxxx ids or hammer the LLM-backed endpoints without limit.
    # Per-client-IP fixed-window count, single process — see app/rate_limit.py.
    rate_limit_per_minute: int = 120

    # How many reverse-proxy hops in front of this API are trusted to prepend the real
    # client IP to X-Forwarded-For (e.g. 1 behind a single nginx/load-balancer). 0
    # (default) means "not deployed behind a trusted proxy" — the header is NEVER
    # consulted at that setting, since any client can forge it. Only raise this when you
    # control every hop between the trusted proxy and this API; see
    # app/rate_limit.py::resolve_client_ip for exactly how it is used.
    trusted_proxy_count: int = 0

    # --- Retention (SEC-03) ----------------------------------------------------
    # How long a case (and everything derived from it — entities, redacted document
    # excerpt, generated PDFs, and any case-linked BimaNyay record) is kept before the
    # server purges it automatically, regardless of whether the client ever presents its
    # access token again. Previously retention was entirely client-initiated (DELETE
    # /cases/{id}, P1-10) — a client that simply lost its one-time token (closed the tab,
    # cleared the app's in-memory token store, uninstalled the app) had no way to ever
    # trigger deletion again, so data was retained forever by default. 90 days is a
    # reasonable default for a short-lived audit/dispute session; override via
    # CASE_TTL_DAYS for a stricter deployment policy.
    case_ttl_days: int = 90

    # How often the background purge sweep runs. Kept well under case_ttl_days so an
    # expired case is not retained much longer than the stated TTL.
    case_purge_interval_seconds: int = 6 * 60 * 60  # 6 hours

    # --- User accounts (ADR-026) ---------------------------------------------------
    # Session lifetime: absolute cap and idle timeout (DB-backed; ADR-019 single process).
    session_lifetime_hours: int = 168
    session_idle_timeout_minutes: int = 120
    # httpOnly SameSite=Strict session cookie for the web client. Secure (and the __Host-
    # name prefix) by default; false only for plain-http local development, refused in
    # production.
    session_cookie_secure: bool = True
    # Extra origins allowed to send cookie-authenticated state-changing requests (and
    # login/registration). Empty = the explicit entries of CORS_ORIGINS. Outside production
    # the API's own (Host-derived) origin is also allowed; under APP_ENV=production it is not.
    auth_trusted_origins: str = ""
    # stdlib hashlib.scrypt parameters (OWASP equivalent-strength row N=2^15, r=8, p=3).
    password_scrypt_n: int = 2**15
    password_scrypt_r: int = 8
    password_scrypt_p: int = 3
    # Stricter per-client-IP bucket for register/login/verification/reset routes.
    auth_rate_limit_per_minute: int = 10
    # Sign-in throttle per (account, client IP) — failures expire after the window; after
    # the free failures each attempt waits an increasing delay (app/services/login_throttle.py).
    login_free_failures: int = 5
    login_failure_window_minutes: int = 15
    login_max_delay_seconds: int = 900
    account_verification_token_ttl_hours: int = 24
    password_reset_token_ttl_minutes: int = 30
    # Email delivery is an OPEN decision (ADR-026 §11): "disabled" is the only transport.
    mail_transport: Literal["disabled"] = "disabled"

    # --- Clinical review & safety governance (ADR-011) --------------------------
    # Operator secret for governance actions only: seating safety-board members,
    # recording a verification attempt, and seeding demo fixtures. Empty (default) means
    # those actions are disabled outright — never "open to anyone".
    clinical_governance_admin_key: str = ""
    # Enables POST /kadi/clinical-demo/seed and the DEMO_VERIFIED status. Off by default;
    # a production deployment must never turn this on.
    clinical_demo_mode: bool = False
    # EasyOCR segments below this confidence become human transcription tasks instead
    # of being trusted.
    ocr_low_confidence_threshold: float = 0.5
    # Independent board approvals (the proposer's own never counts) before a safety rule
    # can be activated.
    safety_rule_required_approvals: int = 1

    # --- Deployment profile & demo kit -------------------------------------------
    # "production" marks a real deployment. Demo mode is refused outright under it (the
    # process will not start), so demo reset/seed/scenario routes and DEMO_VERIFIED can
    # never be reachable against production configuration.
    app_env: str = "development"
    # Where the synthetic demo documents (demo/documents) live, for the demo scenario
    # loaders. Empty = the repository's demo/documents (local runs) or /app/demo/documents
    # (the API image copies them there; they are inert unless demo mode is on).
    demo_documents_dir: str = ""

    # --- Schema management (ADR-020) ----------------------------------------------
    # migrate: upgrade to the latest Alembic revision at start-up (default; single API
    # process only). none: an operator runs `alembic upgrade head` as a release step.
    # create_all: legacy, throwaway local databases only; refused in production.
    schema_management: Literal["migrate", "none", "create_all"] = "migrate"

    # --- Observability -------------------------------------------------------------
    # text: human-readable (local). json: one JSON object per line for a log collector.
    log_format: Literal["text", "json"] = "text"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    def production_config_errors(self) -> List[str]:
        """Settings that are tolerable on a laptop but must never reach a real deployment.
        Under APP_ENV=production the API refuses to start while any remain (app.main).
        Messages name the variable only, never its value."""
        errors: List[str] = []
        if self.document_signing_secret == INSECURE_SIGNING_SECRET or len(self.document_signing_secret) < 32:
            errors.append("DOCUMENT_SIGNING_SECRET is the development default or shorter than 32 characters.")
        if "arogyarakshak:arogyarakshak@" in self.database_url:
            errors.append("DATABASE_URL uses the default development credentials.")
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if not origins or "*" in origins:
            errors.append("CORS_ORIGINS is a wildcard; list the web client's origin(s) explicitly.")
        if self.schema_management == "create_all":
            errors.append("SCHEMA_MANAGEMENT=create_all never migrates existing tables; use migrate or none.")
        if self.clinical_demo_mode:
            errors.append("CLINICAL_DEMO_MODE must be off.")
        if not self.session_cookie_secure:
            errors.append("SESSION_COOKIE_SECURE is false; session cookies would travel over plain HTTP.")
        return errors

    @model_validator(mode="after")
    def _scrypt_parameters_valid(self) -> "Settings":
        n = self.password_scrypt_n
        if n < 2 or n & (n - 1):
            raise ValueError("PASSWORD_SCRYPT_N must be a power of two greater than 1.")
        if self.password_scrypt_r < 1 or self.password_scrypt_p < 1:
            raise ValueError("PASSWORD_SCRYPT_R and PASSWORD_SCRYPT_P must be at least 1.")
        if 128 * n * self.password_scrypt_r > 64 * 1024 * 1024:
            raise ValueError("PASSWORD_SCRYPT_N * PASSWORD_SCRYPT_R needs more than the 64 MiB scrypt memory cap.")
        return self

    @model_validator(mode="after")
    def _demo_mode_never_in_production(self) -> "Settings":
        if self.clinical_demo_mode and self.app_env.strip().lower() == "production":
            raise ValueError(
                "CLINICAL_DEMO_MODE=true is not allowed with APP_ENV=production: demo reviewers, "
                "demo verification labels and the demo reset would be reachable on a real deployment."
            )
        return self

    @property
    def demo_operations_allowed(self) -> bool:
        """Demo seed/reset/scenario routes: demo mode on and not a production profile.
        (Checked at call time too, because tests toggle settings after start-up.)"""
        return bool(self.clinical_demo_mode) and self.app_env.strip().lower() != "production"


settings = Settings()
