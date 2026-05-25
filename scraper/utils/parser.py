import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field

# =====================================================================
# Pydantic Schemas untuk Standardisasi Hasil Scrape
# =====================================================================

class ScrapedPriceRecord(BaseModel):
    """Skema data harga terstandarisasi untuk validasi sebelum disimpan ke DB."""
    external_market_name: str = Field(..., description="Nama pasar asli dari sumber scraper")
    external_commodity_name: str = Field(..., description="Nama komoditas asli dari sumber scraper")
    normalized_market_name: str = Field(..., description="Nama pasar setelah standarisasi")
    normalized_commodity_name: str = Field(..., description="Nama komoditas setelah standarisasi")
    price_date: date = Field(..., description="Tanggal pencatatan harga")
    price: Decimal = Field(..., description="Nilai harga desimal presisi tinggi")
    source_url: Optional[str] = Field(None, description="URL sumber data untuk audit log")


# =====================================================================
# Master Data Alignment / Mapping Trap Dictionaries
# =====================================================================

# Kamus pemetaan nama komoditas eksternal ke nama standar database kita
COMMODITY_MAPPING: Dict[str, str] = {
    # Format: "nama_komoditas_eksternal_lowercase_clean": "Nama Standar DB"
    "beras premium": "Beras Premium",
    "beras premium i": "Beras Premium",
    "beras medium": "Beras Medium",
    "beras medium i": "Beras Medium",
    "beras medium ii": "Beras Medium",
    "cabai rawit merah": "Cabai Rawit Merah",
    "cabe rawit merah": "Cabai Rawit Merah",
    "cabai rawit hijau": "Cabai Rawit Hijau",
    "cabai merah keriting": "Cabai Merah Keriting",
    "cabe merah keriting": "Cabai Merah Keriting",
    "bawang merah": "Bawang Merah",
    "bawang putih": "Bawang Putih",
    "bawang putih ukuran sedang": "Bawang Putih",
    "telur ayam ras": "Telur Ayam Ras",
    "telur ayam ras segar": "Telur Ayam Ras",
    "daging sapi": "Daging Sapi",
    "daging sapi paha belakang": "Daging Sapi",
    "daging ayam": "Daging Ayam Ras",
    "daging ayam ras": "Daging Ayam Ras",
    "daging ayam ras segar": "Daging Ayam Ras",
    "minyak goreng curah": "Minyak Goreng Curah",
    "minyak goreng": "Minyak Goreng Curah",
    "gula pasir": "Gula Pasir",
    "gula kristal putih": "Gula Pasir"
}

# Kamus pemetaan nama pasar eksternal ke nama standar database kita
# Kunci pencarian berupa tuple (nama_pasar_eksternal_clean, id_kabupaten_jika_ada) untuk akurasi spasial
MARKET_MAPPING: Dict[Tuple[str, Optional[str]], str] = {
    # Format: ("nama_pasar_eksternal_lowercase_clean", "regency_id"): "Nama Standar DB"
    ("pasar wonokromo", "3578"): "Pasar Wonokromo",
    ("pasar tradisional wonokromo", "3578"): "Pasar Wonokromo",
    ("pasar keputran", "3578"): "Pasar Keputran",
    ("pasar tradisional keputran", "3578"): "Pasar Keputran",
    ("pasar genteng", "3578"): "Pasar Genteng",
    ("pasar tradisional genteng", "3578"): "Pasar Genteng",
    ("pasar pabean", "3578"): "Pasar Pabean",
    ("pasar tradisional pabean", "3578"): "Pasar Pabean",
    ("pasar tambahrejo", "3578"): "Pasar Tambahrejo",
    ("pasar tradisional tambahrejo", "3578"): "Pasar Tambahrejo",
    ("pasar soponyono", "3578"): "Pasar Soponyono",
    ("pasar tradisional soponyono", "3578"): "Pasar Soponyono",
    ("pasar blauran", "3578"): "Pasar Blauran",
    ("pasar tradisional blauran", "3578"): "Pasar Blauran",
}


# =====================================================================
# Helper Functions untuk Pembersihan & Normalisasi Data
# =====================================================================

def normalize_string(text: str) -> str:
    """
    Melakukan pembersihan string dasar:
    - Lowercase
    - Menghapus karakter non-alphanumeric (kecuali spasi)
    - Menghapus spasi ganda / spasi berlebih di awal/akhir
    """
    if not text:
        return ""
    # Lowercase & strip
    cleaned = text.lower().strip()
    # Hapus spasi ganda dan karakter pemisah selain alfabet/angka
    cleaned = re.sub(r'[^a-z0-9\s-]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()


def clean_price(raw_price: str) -> Optional[Decimal]:
    """
    Mengonversi string harga rupiah ke Decimal presisi tinggi.
    Mampu menangani format:
    - "Rp 12.500"
    - "Rp12.500,-"
    - "12.500,00"
    - "15000"
    Mengembalikan None tanpa raise exception untuk input invalid seperti None, "", dan "KOSONG".
    """
    if raw_price is None:
        return None
        
    price_str = str(raw_price).strip()
    if price_str == "" or price_str.lower() in ("kosong", "none", "null", "-", "tidak ada"):
        return None
        
    # Hapus simbol Rp (dengan atau tanpa titik) dan spasi
    price_str = re.sub(r'(?i)rp\.?\s*', '', price_str)
    # Hapus akhiran ',-' khas Rupiah
    price_str = re.sub(r',-$', '', price_str)
    
    # Deteksi pemisah ribuan dan desimal
    if ',' in price_str and '.' in price_str:
        # Jika posisi titik sebelum koma (Format Indo: 12.500,00)
        if price_str.find('.') < price_str.find(','):
            price_str = price_str.replace('.', '').replace(',', '.')
        else:
            # Format US: 12,500.00
            price_str = price_str.replace(',', '')
    elif ',' in price_str:
        # Koma saja (Format Indo desimal: 12500,50 atau ribuan: 12,500)
        if re.search(r',\d{2}$', price_str):
            price_str = price_str.replace(',', '.')
        else:
            price_str = price_str.replace(',', '')
    elif '.' in price_str:
        # Titik saja (Format Indo ribuan: 12.500 atau desimal US: 12500.00)
        if re.search(r'\.\d{2}$', price_str):
            pass  # Ini desimal, biarkan titiknya
        else:
            price_str = price_str.replace('.', '')
            
    # Hapus karakter non-numeric tersisa kecuali digit dan titik desimal
    price_str = re.sub(r'[^\d.]', '', price_str)
    
    if not price_str:
        return None
        
    try:
        # Konversi ke desimal presisi tinggi bulat 2 desimal
        price_val = Decimal(price_str)
        return price_val.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def parse_date(raw_date: str) -> date:
    """
    Memparsing string tanggal dari berbagai format umum ke objek date Python.
    Format yang didukung antara lain: 'YYYY-MM-DD', 'DD-MM-YYYY', atau 'DD/MM/YYYY'.
    """
    if isinstance(raw_date, date):
        return raw_date
        
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw_date.strip(), fmt).date()
        except ValueError:
            continue
            
    raise ValueError(f"Format tanggal tidak dikenali: '{raw_date}'")


# =====================================================================
# Master Data Mapper Engine
# =====================================================================

def map_commodity_name(external_name: str) -> str:
    """
    Menyelaraskan nama komoditas dari sumber scraper ke nama standar database kita.
    Jika tidak ditemukan pemetaan, mengembalikan nama ter-normalisasi sebagai fallback.
    """
    clean_name = normalize_string(external_name)
    
    # Cari di kamus pemetaan
    if clean_name in COMMODITY_MAPPING:
        return COMMODITY_MAPPING[clean_name]
        
    # Fallback: Buat judul berhuruf kapital pada setiap kata (Title Case)
    return external_name.strip().title()


def map_market_name(external_name: str, regency_id: Optional[str] = None) -> str:
    """
    Menyelaraskan nama pasar dari sumber scraper ke nama standar database kita.
    Menggunakan pasangan (nama_pasar, regency_id) untuk menghindari bentrok nama pasar
    yang serupa di kabupaten berbeda (misal: "Pasar Baru").
    """
    clean_name = normalize_string(external_name)
    
    # Coba cari dengan lookup pasangan (nama_pasar, regency_id)
    if regency_id and (clean_name, regency_id) in MARKET_MAPPING:
        return MARKET_MAPPING[(clean_name, regency_id)]
        
    # Coba cari tanpa regency_id (global search)
    for (m_name, r_id), std_name in MARKET_MAPPING.items():
        if m_name == clean_name and (r_id is None or r_id == regency_id):
            return std_name
            
    # Fallback: Kembalikan nama pasar yang dibersihkan dengan penulisan Title Case
    return external_name.strip().title()


# =====================================================================
# Main Parser Pipeline Function
# =====================================================================

def parse_and_validate_record(
    raw_market: str,
    raw_commodity: str,
    raw_date: str,
    raw_price: str,
    regency_id: Optional[str] = None,
    source_url: Optional[str] = None
) -> ScrapedPriceRecord:
    """
    Fungsi gerbang utama untuk memproses baris data mentah dari scraper:
    1. Membersihkan string & tanggal
    2. Menormalisasi & memetakan nama komoditas dan pasar (Master Data Alignment)
    3. Memparsing & memvalidasi harga rupiah ke Decimal
    4. Mengemas ke dalam Pydantic Model untuk menjamin validitas tipe data
    """
    price_date = parse_date(raw_date)
    price_decimal = clean_price(raw_price)
    
    normalized_commodity = map_commodity_name(raw_commodity)
    normalized_market = map_market_name(raw_market, regency_id)
    
    return ScrapedPriceRecord(
        external_market_name=raw_market,
        external_commodity_name=raw_commodity,
        normalized_market_name=normalized_market,
        normalized_commodity_name=normalized_commodity,
        price_date=price_date,
        price=price_decimal,
        source_url=source_url
    )
