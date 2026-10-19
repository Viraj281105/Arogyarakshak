from dawacheck.prescription_strip_ocr import MedicineStripParser
from dawacheck.reference_data import strip_dosage_token, extract_dosage_mg

parser = MedicineStripParser()
text = "Paracetamol 500mg"

# Manually test the parsing step by step
working_line = text
print("Step 0 (original):", repr(working_line))

# Extract dosage
dosage_mg = extract_dosage_mg(working_line)
print("Step 1 (extract_dosage_mg):", dosage_mg)

# Strip dosage
working_line = strip_dosage_token(working_line).strip()
print("Step 2 (after strip_dosage_token):", repr(working_line))

# Clean medicine name
medicine_name = parser._clean_medicine_name(working_line)
print("Step 3 (after _clean_medicine_name):", repr(medicine_name))

# Now test the full parse
analysis = parser.parse_medicine_strip_text("Paracetamol 500mg")
print("\nFull parse result:")
print("Name:", repr(analysis.medicines[0].name))
print("Dosage:", analysis.medicines[0].dosage_mg)
