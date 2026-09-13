"""
BillNyay — Document Integrity & Signing (#66).

SHA-256 content hashing and an HMAC-SHA256 authenticity signature for generated legal
document packages (the appeal PDF).

This is NOT a licensed digital signature certificate (DSC) under the IT Act, 2000 /
Controller of Certifying Authorities — ArogyaRakshak holds no such certificate, and
presenting this as satisfying IRDAI's DSC requirement for a filed document would be a
compliance fabrication. What this provides is honest and useful on its own: proof that
a downloaded PDF is byte-for-byte what ArogyaRakshak generated and stored (anyone can
recompute the SHA-256 hash themselves and compare), and an HMAC signature only a server
holding the signing secret could have produced (detects tampering with the stored
bytes, not third-party forgery of a legally binding instrument).
"""

import hashlib
import hmac


def compute_sha256(data: bytes) -> str:
    """Returns the hex-encoded SHA-256 digest of `data`."""
    return hashlib.sha256(data).hexdigest()


def sign_document(data: bytes, secret_key: str) -> str:
    """Returns a hex-encoded HMAC-SHA256 signature of `data` under `secret_key`."""
    return hmac.new(secret_key.encode("utf-8"), data, hashlib.sha256).hexdigest()


def verify_signature(data: bytes, signature: str, secret_key: str) -> bool:
    """Constant-time check that `signature` is the HMAC-SHA256 of `data` under `secret_key`."""
    expected = sign_document(data, secret_key)
    return hmac.compare_digest(expected, signature)
