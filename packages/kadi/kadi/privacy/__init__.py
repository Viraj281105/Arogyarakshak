"""
Kadi privacy primitives — a dependency-free leaf package.

Everything here must import nothing from the rest of ``kadi`` (only the standard library),
so any other Kadi subpackage, including ``kadi.llm``, can depend on it without creating an
import cycle (ADR-027). Direct-identifier redaction lives in ``kadi.privacy.redaction``;
``kadi.redaction`` remains as a compatibility alias for the original import path.
"""
