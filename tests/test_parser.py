import pytest
from decimal import Decimal
from scraper.utils.parser import clean_price, normalize_string, map_commodity_name

def test_clean_price_variations():
    """Memvalidasi kemampuan memparsing berbagai variasi format rupiah lokal."""
    assert clean_price("Rp 12.500") == Decimal("12500.00")
    assert clean_price("Rp12.500,-") == Decimal("12500.00")
    assert clean_price("12.500,00") == Decimal("12500.00")
    assert clean_price("15000") == Decimal("15000.00")
    assert clean_price("Rp 12.500,50") == Decimal("12500.50")
    assert clean_price("Rp. 12,500.00") == Decimal("12500.00")


def test_clean_price_invalid_inputs():
    """Memvalidasi bahwa input invalid mengembalikan None secara aman tanpa memicu exception."""
    assert clean_price(None) is None
    assert clean_price("") is None
    assert clean_price("   ") is None
    assert clean_price("KOSONG") is None
    assert clean_price("none") is None
    assert clean_price("-") is None
    assert clean_price("TIDAK ADA") is None


def test_normalize_string():
    """Memvalidasi normalisasi string dasar."""
    assert normalize_string("  Beras Medium  ") == "beras medium"
    assert normalize_string("Cabai  Rawit   Merah!") == "cabai rawit merah"
    assert normalize_string(None) == ""


def test_map_commodity_name():
    """Memvalidasi alignment master data komoditas pangan pokok."""
    # Case-insensitive dan whitespace stripping
    assert map_commodity_name("  Beras Medium I  ") == "Beras Medium"
    assert map_commodity_name("cabe rawit merah") == "Cabai Rawit Merah"
    assert map_commodity_name("  bawang merah  ") == "Bawang Merah"
    
    # Fallback untuk komoditas baru (Title Case)
    assert map_commodity_name("komoditas baru eksotik") == "Komoditas Baru Eksotik"
