import pytest
from dawacheck.checker import benchmark_medicine


def test_benchmark_medicine_overcharged():
    result = benchmark_medicine(brand_name="paracetamol 650mg", mrp=3.5)
    
    assert result is not None
    assert result.active_ingredient == "Paracetamol 650mg"
    assert result.is_overcharged is True
    assert result.deviation_percentage > 0.0
    assert "Jan Aushadhi" in result.generic_substitute_store_info


def test_benchmark_medicine_not_overcharged():
    result = benchmark_medicine(brand_name="amoxicillin 500mg", mrp=5.0)
    
    assert result is not None
    assert result.is_overcharged is False
    assert result.deviation_percentage == 0.0


def test_benchmark_medicine_not_found():
    result = benchmark_medicine(brand_name="unknown brand XYZ", mrp=100.0)
    assert result is None
