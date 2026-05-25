import time
import random
import requests
from datetime import date
from typing import List, Optional
from loguru import logger
from scraper.core.base import BaseScraper
from scraper.config import DEFAULT_TIMEOUT, BASE_DELAY
from scraper.agents import get_headers
from scraper.utils.parser import parse_and_validate_record, ScrapedPriceRecord


# =====================================================================
# Definisi Custom Exceptions untuk Sinyal Orchestrator Fallback
# =====================================================================

class ScraperException(Exception):
    """Base exception untuk seluruh modul scraper."""
    pass

class APIConnectionError(ScraperException):
    """Terjadi kegagalan koneksi jaringan atau DNS resolver."""
    pass

class APITimeoutError(ScraperException):
    """Permintaan HTTP melebihi batas waktu (timeout)."""
    pass

class APIHTTPError(ScraperException):
    """API mengembalikan status code error (4xx atau 5xx)."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP Error {status_code}: {message}")

class CloudflareBlockError(ScraperException):
    """Terdeteksi halaman blokir atau verifikasi Cloudflare."""
    pass

class InvalidJSONResponseError(ScraperException):
    """Payload respon sukses 200 tetapi format JSON rusak/tidak valid."""
    pass


# =====================================================================
# Kelas Utama API Scraper (Requests Client)
# =====================================================================

class APIScraperClient(BaseScraper):
    """
    Scraper utama yang menembak internal API (klandestin) target.
    Menggunakan requests.Session untuk reuse koneksi TCP dan rotasi header modern.
    """

    def __init__(self):
        self.session = requests.Session()

    def _apply_jitter_delay(self):
        """Menerapkan random delay jitter untuk menghindari deteksi pola bot."""
        jitter = random.uniform(0.5, 3.0)
        total_delay = BASE_DELAY + jitter
        logger.debug(f"Mengaktifkan jitter delay selama {total_delay:.2f} detik...")
        time.sleep(total_delay)

    def _detect_cloudflare(self, response: requests.Response) -> bool:
        """Memeriksa apakah halaman diblokir atau diarahkan ke Cloudflare challenge."""
        headers = response.headers.get("Server", "").lower()
        if "cloudflare" in headers:
            # Memeriksa teks khas Cloudflare pada body respon HTML
            if response.status_code in (403, 503) or "cf-browser-verification" in response.text or "Just a moment..." in response.text:
                return True
        return False

    def fetch_prices(self, target_url: str, params: Optional[dict] = None) -> List[ScrapedPriceRecord]:
        """
        Melakukan HTTP request ke API internal dan mengurai data ke format standar.
        
        Args:
            target_url: Endpoint API internal tujuan.
            params: Query parameters untuk API (misal: tanggal, id_komoditas).
            
        Returns:
            List dari data record harga yang telah tervalidasi Pydantic.
        """
        # 1. Terapkan jeda waktu acak sebelum request
        self._apply_jitter_delay()

        # 2. Siapkan request headers yang telah dirotasi
        headers = get_headers()
        
        logger.info(f"Mengirim permintaan ke: {target_url} dengan params: {params}")

        try:
            # 3. Eksekusi HTTP Request
            response = self.session.get(
                target_url,
                headers=headers,
                params=params,
                timeout=DEFAULT_TIMEOUT
            )
            
            # 4. Deteksi Blokir Cloudflare
            if self._detect_cloudflare(response):
                logger.error("Terdeteksi proteksi/blokir Cloudflare (Anti-Bot Aktif)!")
                raise CloudflareBlockError("Akses ditolak oleh Cloudflare Anti-Bot Challenge.")

            # 5. Penanganan Status Code Error
            if response.status_code != 200:
                logger.warning(f"Respon non-200 terdeteksi: {response.status_code}")
                raise APIHTTPError(response.status_code, response.text)

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout ke {target_url}: {str(e)}")
            raise APITimeoutError(f"Timeout setelah {DEFAULT_TIMEOUT} detik.") from e
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Gagal menyambungkan ke {target_url}: {str(e)}")
            raise APIConnectionError("Kegagalan koneksi jaringan.") from e
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Terjadi kesalahan requests tak terduga: {str(e)}")
            raise ScraperException(f"Kesalahan internal request: {str(e)}") from e

        # 6. Parsing Payload JSON
        try:
            json_data = response.json()
        except ValueError as e:
            logger.error("Gagal mengurai respon HTTP menjadi JSON!")
            raise InvalidJSONResponseError("Format response body bukan JSON yang valid.") from e

        # 7. Pemrosesan Data & Validasi Pydantic
        scraped_records: List[ScrapedPriceRecord] = []
        
        # Ekstraksi struktur data generik (Disesuaikan berdasarkan real payload Bapanas/PIHPS)
        # Catatan: Asumsi payload memiliki root key 'data' berupa list harga
        data_list = json_data.get("data", [])
        if not isinstance(data_list, list):
            # Fallback jika json_data langsung berupa list
            if isinstance(json_data, list):
                data_list = json_data
            else:
                logger.warning("Struktur data JSON tidak memiliki array list 'data'. Mencoba parsing manual.")
                data_list = [json_data]

        for idx, item in enumerate(data_list):
            try:
                # Ambil nilai string mentah dari payload JSON sumber
                # Key di bawah ini disesuaikan dengan skema payload standar Bapanas/PIHPS
                market_name = item.get("pasar_nama") or item.get("market_name") or item.get("nama_pasar")
                commodity_name = item.get("komoditas_nama") or item.get("commodity_name") or item.get("nama_komoditas")
                price_date = item.get("tanggal") or item.get("date") or item.get("price_date")
                price_raw = item.get("harga") or item.get("price") or item.get("nilai")
                regency_id = item.get("kabupaten_id") or item.get("regency_id")

                # Lewatkan jika komponen data wajib bernilai kosong
                if not all([market_name, commodity_name, price_date, price_raw]):
                    logger.debug(f"Mengabaikan entri indeks {idx} karena data wajib tidak lengkap.")
                    continue

                # Jalankan fungsi parser pipeline (Cleaning, Mapping, & Pydantic Validation)
                record = parse_and_validate_record(
                    raw_market=str(market_name),
                    raw_commodity=str(commodity_name),
                    raw_date=str(price_date),
                    raw_price=str(price_raw),
                    regency_id=str(regency_id) if regency_id else None,
                    source_url=target_url
                )
                
                scraped_records.append(record)

            except Exception as parsing_err:
                logger.debug(f"Gagal memproses entri ke-{idx}: {str(parsing_err)}")
                continue

        logger.info(f"Berhasil mengurai {len(scraped_records)} data harga tervalidasi menggunakan API Scraper.")
        return scraped_records
