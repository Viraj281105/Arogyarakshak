from billnyay.tools.bima_bharosa_crawler import check_registration_status_mock


def test_mock_check_always_declares_itself_mock():
    result = check_registration_status_mock("BB-123456")
    assert result.source == "mock"


def test_mock_check_with_valid_reference_reports_registered():
    result = check_registration_status_mock("BB-123456")
    assert result.is_registered is True
    assert result.complaint_reference == "BB-123456"
    assert "MOCK" in result.note


def test_mock_check_with_empty_reference():
    result = check_registration_status_mock("")
    assert result.is_registered is False
    assert result.source == "mock"


def test_mock_check_with_none_reference():
    result = check_registration_status_mock(None)
    assert result.is_registered is False


def test_mock_check_strips_whitespace():
    result = check_registration_status_mock("  BB-999  ")
    assert result.complaint_reference == "BB-999"
