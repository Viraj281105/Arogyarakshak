# ADR-013: Deployment target — local demo via Docker Compose

- **Status:** Accepted (2026-10-15) — closes the decision in issue #40
- **Context:** Options were a college server, a cloud free tier, or a local demo. ArogyaRakshak
  has no authentication layer (ADR-008, accepted risk), processes bring-your-own-document
  health paperwork (ADR-003), and its network boundary is Groq + local Postgres + package
  registries only. A public host would need auth, TLS, rate-limit proxy configuration
  (`TRUSTED_PROXY_COUNT`) and a data-protection review first.
- **Decision:** The supported target is a **local, single-machine demo** run with
  `docker-compose.yml` plus the `docker-compose.demo.yml` override. All ports bind to
  `127.0.0.1`. Demo mode is allowed only with `APP_ENV != production`.
- **Consequences:** No external hosting is provisioned. A college server or cloud free tier
  remains possible later but is **not** supported until ADR-008 is superseded by real
  authentication and the checklist in `docs/development/deployment.md` §4 is satisfied.
- **Not validated at decision time:** the demo override was checked with
  `docker compose config` only; the Docker daemon was not running when it was written.
