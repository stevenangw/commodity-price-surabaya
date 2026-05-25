import sys
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def run():
    print("Memulai Playwright Network Interceptor Debugger...")
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        # Simpan semua response yang terdeteksi
        responses = []
        
        def handle_response(response):
            url = response.url
            status = response.status
            content_type = response.headers.get("content-type", "")
            print(f"[Response] Status: {status} | Content-Type: {content_type} | URL: {url[:100]}")
            if "json" in content_type or "api" in url:
                try:
                    # Ambil cuplikan json atau text
                    text = response.text()
                    print(f"   -> Body Length: {len(text)} | Sample: {text[:200]}")
                except Exception as e:
                    print(f"   -> Gagal membaca body: {str(e)}")
        
        page.on("response", handle_response)
        
        url = "https://panelharga.badanpangan.go.id/"
        print(f"Navigasi ke {url}...")
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
            print("Navigasi selesai. Menunggu pemuatan tabel...")
            page.wait_for_selector(".table-harga, table, .table, #table-harga", timeout=10000)
            print("Tabel terdeteksi!")
        except Exception as e:
            print(f"Terjadi kesalahan saat memuat: {str(e)}")
        finally:
            browser.close()
            print("Browser ditutup.")

if __name__ == "__main__":
    run()
