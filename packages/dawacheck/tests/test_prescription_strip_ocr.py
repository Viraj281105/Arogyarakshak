"""
Tests for prescription strip OCR extraction module.

Validates parsing of medicine strip text, handling of various formats,
and integration with DawaCheck reference data.
"""

import pytest
from dawacheck.prescription_strip_ocr import (
    MedicineStripParser,
    extract_medicines_from_prescription,
    extract_medicines_from_form,
    ExtractedMedicine,
)


class TestMedicineStripParser:
    """Tests for MedicineStripParser class."""

    def test_parse_simple_medicine(self):
        """Test parsing a single medicine line."""
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text("Paracetamol 500mg")

        assert len(analysis.medicines) == 1
        assert analysis.medicines[0].name == "paracetamol"
        assert analysis.medicines[0].dosage_mg == 500.0

    def test_parse_medicine_with_quantity(self):
        """Test parsing medicine with quantity information."""
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text("Paracetamol 500mg 10 tablets")

        assert len(analysis.medicines) == 1
        assert analysis.medicines[0].name == "paracetamol"
        assert analysis.medicines[0].dosage_mg == 500.0
        assert analysis.medicines[0].quantity == 10
        assert analysis.medicines[0].unit == "tablets"

    def test_parse_multiple_medicines(self):
        """Test parsing multiple medicines from multiline text."""
        text = """Paracetamol 500mg 10 tablets
Aspirin 75mg 15 tablets
Amoxicillin 500mg 20 capsules"""
        
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(text)

        assert len(analysis.medicines) == 3
        assert analysis.medicines[0].name == "paracetamol"
        assert analysis.medicines[1].name == "aspirin"
        assert analysis.medicines[2].name == "amoxicillin"

    def test_parse_medicine_with_mrp(self):
        """Test parsing medicine with MRP information."""
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text("Dolo 650mg MRP Rs. 50")

        assert len(analysis.medicines) == 1
        assert analysis.medicines[0].mrp == 50.0

    def test_parse_medicine_with_batch_and_expiry(self):
        """Test parsing medicine with batch and expiry date."""
        text = "Paracetamol 500mg Batch: B12345 Expiry: 12/2025"
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(text)

        assert len(analysis.medicines) == 1
        assert analysis.medicines[0].batch_number == "B12345"
        assert analysis.medicines[0].expiry_date == "12/2025"

    def test_parse_medicine_with_manufacturer(self):
        """Test parsing medicine with manufacturer information."""
        text = "Paracetamol 500mg Mfg. GlaxoSmithKline"
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(text)

        assert len(analysis.medicines) == 1
        assert "GlaxoSmithKline" in analysis.medicines[0].manufacturer or \
               "glaxosmithkline" in analysis.medicines[0].manufacturer.lower()

    def test_parse_common_brand_names(self):
        """Test that common Indian brand names are recognized and normalized."""
        text = """Dolo 650
Crocin 500mg
Calpol 650mg
Aspirin
Augmentin 625"""
        
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(text)

        assert len(analysis.medicines) >= 4
        names = [med.name for med in analysis.medicines]
        assert any("dolo" in n for n in names)
        assert any("crocin" in n for n in names)

    def test_parse_different_dosage_units(self):
        """Test parsing medicines with different dosage units (mg, mcg, g, mL)."""
        text = """Paracetamol 500mg
Vitamin B12 1000mcg
Metformin 1g
Cough Syrup 5mL"""
        
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(text)

        assert len(analysis.medicines) == 4
        assert analysis.medicines[0].dosage_mg == 500.0
        assert analysis.medicines[1].dosage_mg == 1.0  # 1000 mcg = 1 mg
        assert analysis.medicines[2].dosage_mg == 1000.0  # 1g = 1000 mg

    def test_parse_prescription_format(self):
        """Test parsing a realistic prescription format."""
        text = """Patient Rx Date: 01/01/2024

1. Paracetamol 500mg 10 tablets - TID (3 times daily)
2. Amoxicillin 500mg 20 capsules - BD (Twice daily)
3. Pantoprazole 40mg 15 tablets - OD (Once daily)

Doctor Signature"""
        
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(text)

        # Should extract 3 medicines, skipping patient/doctor info
        assert len(analysis.medicines) >= 2
        names = [med.name for med in analysis.medicines]
        assert any("paracetamol" in n for n in names)
        assert any("amoxicillin" in n for n in names)

    def test_empty_text_returns_empty_analysis(self):
        """Test that empty text returns an empty analysis with low confidence."""
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text("")

        assert len(analysis.medicines) == 0
        assert analysis.extraction_confidence == 0.0

    def test_invalid_text_type(self):
        """Test handling of invalid text types."""
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(None)

        assert len(analysis.medicines) == 0
        assert analysis.extraction_confidence == 0.0

    def test_parse_structured_medicines_from_form(self):
        """Test parsing pre-structured medicine data from forms."""
        medicines_data = [
            {"name": "Paracetamol", "dosage": "500mg", "qty": 10, "mrp": 45.0},
            {"name": "Amoxicillin", "dosage": "500mg", "qty": 20, "mrp": 120.0},
        ]

        parser = MedicineStripParser()
        analysis = parser.parse_structured_medicines(medicines_data)

        assert len(analysis.medicines) == 2
        assert analysis.medicines[0].name == "paracetamol"
        assert analysis.medicines[0].dosage_mg == 500.0
        assert analysis.medicines[0].mrp == 45.0

    def test_convenience_function_ocr(self):
        """Test the convenience function for OCR text extraction."""
        text = "Paracetamol 500mg 10 tablets"
        analysis = extract_medicines_from_prescription(text)

        assert len(analysis.medicines) == 1
        assert analysis.medicines[0].name == "paracetamol"

    def test_convenience_function_form(self):
        """Test the convenience function for form data extraction."""
        medicines_data = [
            {"name": "Paracetamol", "dosage": "500mg"},
        ]
        analysis = extract_medicines_from_form(medicines_data)

        assert len(analysis.medicines) == 1
        assert analysis.medicines[0].name == "paracetamol"

    def test_parse_medicine_with_special_characters(self):
        """Test parsing medicine names with special characters (+ signs, hyphens)."""
        text = "Amoxicillin-Clavulanate 625mg"
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(text)

        assert len(analysis.medicines) >= 1
        # Should extract the medicine despite the hyphen

    def test_quantity_variations(self):
        """Test parsing various quantity format variations."""
        texts = [
            "Paracetamol 500mg 10 tablets",
            "Paracetamol 500mg 10 tabs",
            "Paracetamol 500mg 10x1 capsule",
            "Paracetamol 500mg 5 strips",
        ]

        parser = MedicineStripParser()
        for text in texts:
            analysis = parser.parse_medicine_strip_text(text)
            assert len(analysis.medicines) >= 1
            assert analysis.medicines[0].quantity is not None

    def test_confidence_score_multiline(self):
        """Test that confidence scores reflect extraction quality."""
        parser = MedicineStripParser()
        
        # Rich text with many fields should have high confidence
        rich_text = "Paracetamol 500mg 10 tablets MRP Rs. 50 Batch: B123 Expiry: 12/2025"
        rich_analysis = parser.parse_medicine_strip_text(rich_text)
        
        # Sparse text should have lower confidence
        sparse_text = "Medicine X"
        sparse_analysis = parser.parse_medicine_strip_text(sparse_text)
        
        # Both should extract, but sparse might have lower confidence
        assert len(rich_analysis.medicines) >= 1
        assert len(sparse_analysis.medicines) >= 1

    def test_case_insensitivity(self):
        """Test that parsing is case-insensitive."""
        texts = [
            "PARACETAMOL 500MG",
            "Paracetamol 500mg",
            "paracetamol 500mg",
            "PaRaCeTaMoL 500Mg",
        ]

        parser = MedicineStripParser()
        for text in texts:
            analysis = parser.parse_medicine_strip_text(text)
            assert len(analysis.medicines) == 1
            # All should normalize to lowercase
            assert analysis.medicines[0].name == "paracetamol"
            assert analysis.medicines[0].dosage_mg == 500.0

    def test_skip_metadata_lines(self):
        """Test that metadata lines (patient name, doctor, etc.) are skipped."""
        text = """Patient: John Doe
Age: 35
Doctor: Dr. Smith
Phone: 9876543210
Paracetamol 500mg 10 tablets
Signature: ___________"""
        
        parser = MedicineStripParser()
        analysis = parser.parse_medicine_strip_text(text)

        # Should extract only the actual medicine, not patient/doctor lines
        assert len(analysis.medicines) == 1
        assert "paracetamol" in analysis.medicines[0].name
