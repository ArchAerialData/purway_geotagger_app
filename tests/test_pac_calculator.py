import pytest
from purway_geotagger.core.pac_calculator import calculate_pac

def test_calculate_pac_basic():
    # 500 ppm / 25 m = 20.0
    assert calculate_pac(500, 25) == 20.0
    # 1000 ppm / 25 m = 40.0
    assert calculate_pac(1000, 25) == 40.0

def test_calculate_pac_precision():
    # 100 ppm / 3 m = 33.3333... -> 33.33
    assert calculate_pac(100, 3) == 33.33
    assert calculate_pac(100, 3, precision=4) == 33.3333

def test_calculate_pac_invalid_inputs():
    assert calculate_pac(None, 25) is None
    assert calculate_pac(500, None) is None
    assert calculate_pac(None, None) is None

def test_calculate_pac_zero_or_negative_alt():
    assert calculate_pac(500, 0) is None
    assert calculate_pac(500, -5) is None

def test_calculate_pac_zero_ppm():
    assert calculate_pac(0, 25) == 0.0
