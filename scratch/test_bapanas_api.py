import requests
import json

def test_api():
    url = "https://api-panelhargav2.badanpangan.go.id/api/front/harga-pangan-informasi"
    # Gunakan x-api-key yang kita temukan di JS
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "x-api-key": "zHWbt7U2qvPoUDkiUgvnOqYrtj3zClR7unnH2G4apE7HcMV4QyNC6BSD0yV3uvSHqS91TxwE8aMDTiCznmGceEX3zQmO1Xwq7TJblotIt2CpwvK6YjRKDJwcgMJwav9p4RshM3nfuFyurSQQv9BhueMJ0HJ778oD",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://panelharga.badanpangan.go.id",
        "Referer": "https://panelharga.badanpangan.go.id/"
    }
    
    # Coba level_harga_id=3 (eceran)
    params = {
        "province_id": "",
        "city_id": "",
        "level_harga_id": "3" # 3 untuk eceran, 1 produsen, 2 grosir
    }
    
    print(f"Mengirim request ke {url} dengan params {params}...")
    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Respon sukses! Jumlah entri data:", len(data.get("data", [])))
        if data.get("data"):
            print("Contoh entri data pertama:")
            print(json.dumps(data["data"][0], indent=2))
    except Exception as e:
        print(f"Gagal membaca JSON: {str(e)}")
        print("Respon Mentah (500 karakter pertama):")
        print(response.text[:500])

if __name__ == "__main__":
    test_api()
