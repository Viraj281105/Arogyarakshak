from billnyay.tools.pdf_integrity import compute_sha256, sign_document, verify_signature


def test_sha256_is_deterministic():
    data = b"hello world"
    assert compute_sha256(data) == compute_sha256(data)


def test_sha256_changes_with_content():
    assert compute_sha256(b"a") != compute_sha256(b"b")


def test_sign_and_verify_round_trip():
    data = b"appeal letter contents"
    secret = "test-secret"
    signature = sign_document(data, secret)
    assert verify_signature(data, signature, secret) is True


def test_verify_fails_on_tampered_data():
    data = b"appeal letter contents"
    secret = "test-secret"
    signature = sign_document(data, secret)
    tampered = b"appeal letter CONTENTS"
    assert verify_signature(tampered, signature, secret) is False


def test_verify_fails_with_wrong_secret():
    data = b"appeal letter contents"
    signature = sign_document(data, "secret-a")
    assert verify_signature(data, signature, "secret-b") is False


def test_signature_differs_by_secret():
    data = b"same content"
    assert sign_document(data, "secret-a") != sign_document(data, "secret-b")
