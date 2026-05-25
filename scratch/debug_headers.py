import sys
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

def run():
    print("Memulai Playwright Request Headers Capturer...")
    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        def handle_request(request):
            url = request.url
            if "harga-pangan-informasi" in url or "harga-peta-provinsi" in url:
                print(f"\n[REQUEST DETECTED] URL: {url}")
                print("Method:", request.method)
                print("Headers:")
                for k, v in request.headers.items():
                    print(f"  {k}: {v}")
                    
        def handle_response(response):
            url = response.url
            if "harga-pangan-informasi" in url or "harga-peta-provinsi" in url:
                print(f"\n[RESPONSE DETECTED] URL: {url}")
                print("Status:", response.status)
                try:
                    text = response.text()
                    print(f"Status Text / JSON Sample: {text[:200]}")
                except Exception as e:
                    print("Failed to read body:", str(e))
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        url = "https://panelharga.badanpangan.go.id/"
        print(f"Navigasi ke {url}...")
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
            print("Navigasi selesai. Menunggu 5 detik untuk background requests...")
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Terjadi kesalahan: {str(e)}")
        finally:
            browser.close()
            print("Browser ditutup.")

if __name__ == "__main__":
    run()
