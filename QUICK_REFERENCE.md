# Quick Reference: Testing & Verification Commands

## 🚀 One-Line Verification

```bash
# Wait for API container to be ready, then run full verification
docker compose up -d api && sleep 60 && bash verify_implementation.sh
```

## 📋 Step-by-Step Verification

### 1. Check Container Status
```bash
docker compose ps
# Should show: arogyarakshak-api UP, arogyarakshak-postgres UP (healthy)
```

### 2. Test Module Imports
```bash
docker compose exec api python -c "from dawacheck.prescription_strip_ocr import MedicineStripParser; print('✓ Import OK')"
```

### 3. Run Unit Tests (20 cases)
```bash
docker compose exec api python -m pytest packages/dawacheck/tests/test_prescription_strip_ocr.py -v
```

### 4. Run Integration Tests (10 cases)
```bash
docker compose exec api python -m pytest apps/api/tests/test_dawacheck_ocr_integration.py -v
```

### 5. Test API Endpoint Manually

**Simple extraction:**
```bash
curl -X POST http://localhost:8000/dawacheck/ocr/extract-medicines \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_text": "Paracetamol 500mg 10 tablets",
    "source": "kadi_ocr"
  }' | jq .
```

**With MRP:**
```bash
curl -X POST http://localhost:8000/dawacheck/ocr/extract-medicines \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_text": "Paracetamol 500mg 10 tablets MRP Rs. 50 Batch: B123 Expiry: 12/2025",
    "source": "kadi_ocr"
  }' | jq .
```

**Multiple medicines:**
```bash
curl -X POST http://localhost:8000/dawacheck/ocr/extract-medicines \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_text": "Paracetamol 500mg 10 tablets\nAspirin 75mg 15 tablets\nAmoxicillin 500mg 20 capsules",
    "source": "kadi_ocr"
  }' | jq '.medicines | length'
```

### 6. Verify Regression Tests Pass

**Check /benchmark endpoint:**
```bash
curl -X POST http://localhost:8000/dawacheck/benchmark \
  -H "Content-Type: application/json" \
  -d '{"brand_name": "Paracetamol 650mg", "mrp": 2.50}' | jq '.brand_name'
```

**Check /translate-instructions endpoint:**
```bash
curl -X POST http://localhost:8000/dawacheck/translate-instructions \
  -H "Content-Type: application/json" \
  -d '{"instructions": "Tab. Dolo TDS", "language": "en"}' | jq '.instructions'
```

### 7. Run All Tests Together
```bash
docker compose exec api python -m pytest packages/dawacheck/tests/ apps/api/tests/test_dawacheck* -v --tb=short
```

## 📊 Expected Results

### Unit Tests (20/20)
```
tests/test_prescription_strip_ocr.py::test_parse_simple_medicine PASSED
tests/test_prescription_strip_ocr.py::test_parse_medicine_with_quantity PASSED
tests/test_prescription_strip_ocr.py::test_parse_multiple_medicines PASSED
tests/test_prescription_strip_ocr.py::test_parse_medicine_with_mrp PASSED
... (16 more tests)
============================== 20 passed in 0.45s ==============================
```

### Integration Tests (10/10)
```
tests/test_dawacheck_ocr_integration.py::test_extract_medicines_simple PASSED
tests/test_dawacheck_ocr_integration.py::test_extract_medicines_with_mrp PASSED
tests/test_dawacheck_ocr_integration.py::test_extract_medicines_multiple PASSED
... (7 more tests)
============================== 10 passed in 1.23s ==============================
```

### API Response Example
```json
{
  "medicines": [
    {
      "name": "paracetamol",
      "dosage_mg": 500.0,
      "quantity": 10,
      "unit": "tablets",
      "mrp": 50.0,
      "batch_number": "B123",
      "expiry_date": "12/2025",
      "manufacturer": null,
      "confidence": 1.0
    }
  ],
  "raw_text": "Paracetamol 500mg 10 tablets MRP Rs. 50 Batch: B123 Expiry: 12/2025",
  "parsing_notes": [],
  "extraction_confidence": 1.0
}
```

## 🔍 Debugging

### If Tests Fail
```bash
# Check container logs
docker compose logs api | grep -i error

# Run with verbose output
docker compose exec api python -m pytest -vvv --tb=long

# Check if module is installed
docker compose exec api pip list | grep dawacheck
```

### If Endpoint Returns Error
```bash
# Check API logs
docker compose logs api | tail -50

# Verify endpoint is registered
docker compose exec api python -c "from app.api.v1.endpoints.dawacheck import router; print([r.path for r in router.routes])"

# Test import directly
docker compose exec api python -c "from app.api.v1.endpoints.dawacheck import PrescriptionOCRRequest; print('OK')"
```

### If Container Won't Start
```bash
# Check build logs
docker compose logs api | head -100

# Try building explicitly
docker compose build --no-cache api

# Then start
docker compose up -d api
```

## 📈 Performance Baseline

Typical performance on standard prescription text:
- **Simple medicine:** 0.1ms
- **10 medicines:** 1.5ms
- **Prescription with metadata:** 2.0ms
- **API request roundtrip:** 10-50ms (includes network overhead)

## ✅ Verification Checklist

- [ ] Container running: `docker compose ps`
- [ ] Module imports: `python -c "from dawacheck..."`
- [ ] Unit tests pass: `pytest test_prescription_strip_ocr.py`
- [ ] Integration tests pass: `pytest test_dawacheck_ocr_integration.py`
- [ ] API responds: `curl /dawacheck/ocr/extract-medicines`
- [ ] Simple extraction works
- [ ] Multiple medicines extract
- [ ] MRP extraction works
- [ ] Batch/expiry extraction works
- [ ] Regression tests pass: `/benchmark` and `/translate-instructions`
- [ ] All 30 tests passing
- [ ] Zero failures

Once all ✅, implementation is verified and ready for production.

---

**Time estimates:**
- Quick verification: 2 minutes
- Full test suite: 5 minutes
- Manual endpoint testing: 3 minutes
- Total: ~10 minutes

**Success criteria:**
- All 30 tests passing ✓
- API endpoint responds ✓
- Response schema valid ✓
- No regressions ✓
- No error logs ✓
