"""Telemetry settings, kept apart from ``app.config`` (Wave 1 conflict rules).

Environment variables: METRICS_ENABLED, OTEL_ENABLED, OTEL_EXPORTER_OTLP_ENDPOINT,
OTEL_SERVICE_NAME, OTEL_TRACES_SAMPLER_RATIO, GRAFANA_ADMIN_PASSWORD, APP_ENV.
"""

from typing import List, Optional
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_GRAFANA_PASSWORD = "arogyarakshak-dev-only"
# Hosts the OTLP exporter may point at: this machine or the collector in the compose stack.
INTERNAL_OTLP_HOSTS = {"localhost", "127.0.0.1", "::1", "otel-collector", "host.docker.internal"}


class TelemetrySettings(BaseSettings):
    # None = follow the environment: exposed in development, off under APP_ENV=production.
    metrics_enabled: Optional[bool] = None
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://127.0.0.1:4318"
    otel_service_name: str = "arogyarakshak-api"
    otel_traces_sampler_ratio: float = 1.0
    grafana_admin_password: str = DEV_GRAFANA_PASSWORD
    app_env: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("otel_traces_sampler_ratio")
    @classmethod
    def _ratio(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("OTEL_TRACES_SAMPLER_RATIO must be between 0 and 1")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def metrics_exposed(self) -> bool:
        return (not self.is_production) if self.metrics_enabled is None else self.metrics_enabled

    def endpoint_is_internal(self) -> bool:
        return (urlparse(self.otel_exporter_otlp_endpoint).hostname or "") in INTERNAL_OTLP_HOSTS

    def production_errors(self) -> List[str]:
        """Settings the observability stack refuses under APP_ENV=production. Names only,
        never values."""
        errors: List[str] = []
        if self.is_production and (self.grafana_admin_password == DEV_GRAFANA_PASSWORD or len(self.grafana_admin_password) < 12):
            errors.append("GRAFANA_ADMIN_PASSWORD is the development default or shorter than 12 characters.")
        return errors


telemetry_settings = TelemetrySettings()
