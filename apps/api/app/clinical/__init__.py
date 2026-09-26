"""Persistence and HTTP-facing services for the clinical-review layer (ADR-011).

Domain rules live in packages/kadi/kadi/clinical_review (DB-agnostic); this package binds
them to the ORM models, the credential model and the audit trail.
"""
