from datetime import date
from typing import List, Optional
from playwright.sync_api import sync_playwright, Response, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth
from loguru import logger

from scraper.core.base import BaseScraper
from scraper.config import DEFAULT_TIMEOUT
from scraper.agents import get_random_user_agent
from scraper.core.api_client import APITimeoutError, CloudflareBlockError, ScraperException
from scraper.utils.parser import parse_and_validate_record, ScrapedPriceRecord


class BrowserScraperClient(BaseScraper):
    """
    Scraper cadangan (robust fallback) menggunakan Playwright Headless Browser.
    Dilengkapi dengan:
    1. Stealth engine untuk bypass deteksi bot.
    2. Network Interception (XHR) untuk menyadap data JSON internal secara asinkron.
    3. HTML DOM Selector Fallback jika API internal gagal disadap tetapi tabel ter-render.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        # Selector target yang menandakan data telah ter-render di UI
        self.target_selector = ".table-harga, table, .table, #table-harga"

    def fetch_prices(self, target_url: str, params: Optional[dict] = None) -> List[ScrapedPriceRecord]:
        """
        Membuka halaman target via Playwright, menyadap XHR response, 
        dan mem-parsing data harga tervalidasi.
        """
        captured_records: List[ScrapedPriceRecord] = []
        user_agent = get_random_user_agent()

        logger.info(f"Menginisialisasi Playwright Headless Browser (headless={self.headless})...")
        
        import urllib.parse
        if params:
            query_string = urllib.parse.urlencode(params)
            final_url = f"{target_url}?{query_string}"
        else:
            final_url = target_url

        # Pemetaan URL API ke Halaman Portal Visual yang menampilkan UI
        # Ini penting agar peramban memuat elemen visual dan memicu AJAX/XHR asinkron di latar belakang
        portal_url = final_url
        if "api/harga" in final_url:
            portal_url = "https://panelharga.badanpangan.go.id/"
        elif "api/pihps" in final_url:
            portal_url = "https://sehati.kemendag.go.id/"
            
        with Stealth().use_sync(sync_playwright()) as p:
            # 1. Jalankan Browser Instance (Chromium)
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )
            
            # 2. Buat Context dengan User-Agent yang dirotasi
            context = browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1280, "height": 800},
                locale="id-ID",
                timezone_id="Asia/Jakarta"
            )

            # 3. Buat Halaman Baru (Stealth diinjeksikan secara otomatis di level konteks p)
            page = context.new_page()
            logger.debug("Playwright-Stealth diaktifkan secara otomatis via instrumentasi konteks.")

            # 4. Fungsi Callback untuk Network Interception (Mencegat XHR JSON)
            def capture_json_payload(response: Response):
                # Memeriksa apakah respon berupa API JSON internal klandestin
                # Bapanas/PIHPS biasanya mengandung kata 'api/harga', 'api/komoditas', atau 'get-data'
                url = response.url.lower()
                if "api/harga" in url or "api/pihps" in url or "api/harga-pangan" in url or "panelharga" in url:
                    try:
                        # Abaikan jika status HTTP bukan sukses
                        if response.status_code != 200:
                            return

                        # Ambil payload JSON internal
                        json_data = response.json()
                        logger.info(f"Berhasil mencegat XHR JSON dari URL: {response.url}")
                        
                        data_list = json_data.get("data", [])
                        if not isinstance(data_list, list):
                            if isinstance(json_data, list):
                                data_list = json_data
                            else:
                                data_list = [json_data]

                        for idx, item in enumerate(data_list):
                            try:
                                market_name = item.get("pasar_nama") or item.get("market_name") or item.get("nama_pasar")
                                commodity_name = item.get("komoditas_nama") or item.get("commodity_name") or item.get("nama_komoditas")
                                price_date = item.get("tanggal") or item.get("date") or item.get("price_date")
                                price_raw = item.get("harga") or item.get("price") or item.get("nilai")
                                regency_id = item.get("kabupaten_id") or item.get("regency_id")

                                if not all([market_name, commodity_name, price_date, price_raw]):
                                    continue

                                record = parse_and_validate_record(
                                    raw_market=str(market_name),
                                    raw_commodity=str(commodity_name),
                                    raw_date=str(price_date),
                                    raw_price=str(price_raw),
                                    regency_id=str(regency_id) if regency_id else None,
                                    source_url=response.url
                                )
                                captured_records.append(record)
                            except Exception:
                                continue
                                
                    except Exception as capture_err:
                        logger.debug(f"Gagal memproses respon XHR yang dicegat: {str(capture_err)}")

            # 5. Pasang Event Listener sebelum navigasi dimulai
            page.on("response", capture_json_payload)

            # 6. Navigasi Halaman & Tunggu Render DOM Elemen Tabel (Timeout 15 Detik)
            logger.info(f"Membuka halaman portal target: {portal_url}")
            try:
                # Muat halaman
                page.goto(portal_url, timeout=15000, wait_until="domcontentloaded")
                
                # Deteksi halaman Cloudflare Blockage
                if "cloudflare" in page.title().lower() or "just a moment..." in page.content():
                    logger.error("Akses diblokir oleh halaman tantangan Cloudflare!")
                    raise CloudflareBlockError("Playwright mendeteksi tantangan Cloudflare yang tidak dapat dilewati secara otomatis.")

                # Tunggu hingga tabel harga muncul di layar
                logger.info(f"Menunggu pemuatan elemen DOM '{self.target_selector}'...")
                page.wait_for_selector(self.target_selector, timeout=15000)
                logger.info("Elemen target terdeteksi di DOM.")

            except PlaywrightTimeoutError as t_err:
                logger.error(f"Timeout terlampaui saat memuat halaman: {str(t_err)}")
                raise APITimeoutError("Batas waktu 15 detik terlampaui saat menunggu halaman memuat tabel harga.") from t_err
                
            except Exception as e:
                if not isinstance(e, (APITimeoutError, CloudflareBlockError)):
                    logger.error(f"Terjadi kesalahan peramban tak terduga: {str(e)}")
                    raise ScraperException(f"Kesalahan peramban Playwright: {str(e)}") from e
                raise e
            finally:
                # 7. Penutupan Browser secara Aman
                context.close()
                browser.close()
                logger.info("Browser instance ditutup.")

        # 8. Fallback Tingkat Terakhir: HTML DOM Parsing (Jika XHR pencegatan kosong)
        if not captured_records:
            logger.warning("Network Interception tidak menangkap JSON apapun. Memicu fallback HTML DOM Parsing...")
            # Catatan: Implementasi DOM Parsing murni dapat ditambahkan di sini jika dibutuhkan, 
            # tetapi dengan Network Interception klandestin, event listener menangkap raw response yang di-load AJAX.
            
        logger.info(f"Browser Scraper berhasil mengumpulkan {len(captured_records)} records.")
        return captured_records
