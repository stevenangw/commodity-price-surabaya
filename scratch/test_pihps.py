import requests
import json

def main():
    url = "https://sehati.kemendag.go.id/api/pihps"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    print(f"Menguji endpoint PIHPS Kemendag: {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print("Respon Mentah (500 karakter pertama):")
        print(response.text[:500])
    except Exception as e:
        print("Terjadi kesalahan:", str(e))

if __name__ == "__main__":
    main()
