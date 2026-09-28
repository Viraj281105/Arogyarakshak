"""
ArogyaRakshak API — Configuration.

Reads environment variables for the application. All config is centralised here
so that no module ever hardcodes credentials or model names.

GROQ_MODEL defaults to "openai/gpt-oss-120b".  Never use deprecated model
names (llama3-70b, llama-3.3-70b-versatile) — see AGENTS.md.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    document_signing_secret: str = "dev-insecure-signing-secret-change-in-production"

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
