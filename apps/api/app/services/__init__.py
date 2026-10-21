"""Application use cases shared across entry points (ADR-018).

A function lives here when more than one entry point needs it — an HTTP route, Kadi's
auto-triggers, the Claim Pack, the retention sweep, the demo kit or the evaluation
harness. Route modules in ``app.api.v1.endpoints`` stay thin: they authorise the caller,
enforce consent and translate errors to HTTP, then call into this package.

Rules (enforced by import-linter, see ``.importlinter``):

- nothing here imports ``app.api`` (no FastAPI routers, no route modules);
- domain rules stay in ``packages/<module>``; this layer loads rows, calls the package
  and shapes the result.
"""
