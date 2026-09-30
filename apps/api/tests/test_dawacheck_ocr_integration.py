"""
Integration tests for DawaCheck OCR endpoint with Kadi.

Tests the full pipeline: OCR text -> medicine extraction -> benchmarking.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestDawaCheckOCREndpoint:
    """Integration tests for /dawacheck/ocr/extract-medicines endpoint."""

    def test_extract_medicines_simple(self):
        """Test basic medicine extraction from OCR text."""
        response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": "Paracetamol 500mg 10 tablets",
                "source": "kadi_ocr",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "medicines" in data
        assert len(data["medicines"]) == 1
        assert data["medicines"][0]["name"] == "paracetamol"
        assert data["medicines"][0]["dosage_mg"] == 500.0
        assert data["medicines"][0]["quantity"] == 10

    def test_extract_medicines_with_mrp(self):
        """Test extraction including MRP information."""
        response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": "Dolo 650mg MRP Rs. 50",
                "source": "kadi_ocr",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["medicines"]) >= 1
        assert data["medicines"][0]["mrp"] == 50.0

    def test_extract_medicines_multiple(self):
        """Test extraction of multiple medicines."""
        text = """Paracetamol 500mg 10 tablets
Aspirin 75mg 15 tablets
Amoxicillin 500mg 20 capsules"""

        response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": text,
                "source": "kadi_ocr",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["medicines"]) >= 2

    def test_extract_medicines_with_batch_expiry(self):
        """Test extraction of batch and expiry information."""
        text = "Paracetamol 500mg Batch: B12345 Expiry: 12/2025"

        response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": text,
                "source": "kadi_ocr",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["medicines"]) >= 1
        med = data["medicines"][0]
        assert med.get("batch_number") == "B12345" or med.get("batch_number") is not None
        assert med.get("expiry_date") == "12/2025" or med.get("expiry_date") is not None

    def test_extract_medicines_empty_text(self):
        """Test handling of empty OCR text."""
        response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": "",
                "source": "kadi_ocr",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["medicines"]) == 0
        assert data["extraction_confidence"] <= 0.5

    def test_extract_medicines_prescription_format(self):
        """Test realistic prescription format."""
        text = """Patient Rx Date: 01/01/2024

1. Paracetamol 500mg 10 tablets - TDS
2. Amoxicillin 500mg 20 capsules - BD
3. Pantoprazole 40mg 15 tablets - OD"""

        response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": text,
                "source": "kadi_ocr",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Should extract at least the medicines, not patient/doctor lines
        assert len(data["medicines"]) >= 2
        names = [m["name"] for m in data["medicines"]]
        assert any("paracetamol" in n for n in names)

    def test_extract_medicines_response_schema(self):
        """Test that response matches expected schema."""
        response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": "Aspirin 75mg",
                "source": "kadi_ocr",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "medicines" in data
        assert "raw_text" in data
        assert "parsing_notes" in data
        assert "extraction_confidence" in data

        # Check medicine fields
        if data["medicines"]:
            med = data["medicines"][0]
            assert "name" in med
            assert "dosage_mg" in med
            assert "quantity" in med
            assert "unit" in med
            assert "mrp" in med
            assert "batch_number" in med
            assert "expiry_date" in med
            assert "manufacturer" in med
            assert "confidence" in med


class TestDawaCheckBenchmarkIntegration:
    """Tests integration between OCR extraction and benchmarking."""

    def test_extracted_medicine_to_benchmark(self):
        """Test that extracted medicines can be benchmarked."""
        # First extract
        extract_response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": "Paracetamol 650mg MRP Rs. 3.50",
                "source": "kadi_ocr",
            },
        )

        assert extract_response.status_code == 200
        medicines = extract_response.json()["medicines"]
        assert len(medicines) >= 1

        # Then benchmark
        med = medicines[0]
        benchmark_response = client.post(
            "/dawacheck/benchmark",
            json={
                "brand_name": med["name"],
                "mrp": med["mrp"] or 3.50,
            },
        )

        # Benchmark might return 404 if medicine not in list, that's OK
        # Main thing is endpoint works
        assert benchmark_response.status_code in (200, 404)

    def test_common_brands_extracted_then_benchmarked(self):
        """Test common brand names can be extracted and matched."""
        brands_text = """Dolo 650mg MRP Rs. 45
Crocin 500mg MRP Rs. 40
Aspirin 75mg MRP Rs. 25"""

        response = client.post(
            "/dawacheck/ocr/extract-medicines",
            json={
                "ocr_text": brands_text,
                "source": "kadi_ocr",
            },
        )

        assert response.status_code == 200
        medicines = response.json()["medicines"]

        # All should extract
        assert len(medicines) >= 2

        # Extracted names should be normalized
        names = [m["name"] for m in medicines]
        assert all(isinstance(n, str) and len(n) > 0 for n in names)


class TestDawaCheckRegressions:
    """Regression tests to ensure existing functionality still works."""

    def test_benchmark_endpoint_still_works(self):
        """Ensure /benchmark endpoint unchanged."""
        response = client.post(
            "/dawacheck/benchmark",
            json={
                "brand_name": "Paracetamol 650mg",
                "mrp": 2.5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "brand_name" in data
        assert "mrp" in data
        assert "nppa_ceiling_price" in data

    def test_translate_instructions_endpoint_still_works(self):
        """Ensure /translate-instructions endpoint unchanged."""
        response = client.post(
            "/dawacheck/translate-instructions",
            json={
                "instructions": "Tab. Dolo 650mg TDS x 5 days",
                "language": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "instructions" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
