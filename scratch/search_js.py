import requests
import re

def search_main_js():
    js_url = "https://panelharga.badanpangan.go.id/main.69d329b558fe5803.js"
    print(f"Mengunduh file JS utama dari Bapanas: {js_url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(js_url, headers=headers)
    if response.status_code != 200:
        print(f"Gagal mengunduh file JS: Status {response.status_code}")
        return
        
    js_content = response.text
    print(f"File JS diunduh. Panjang karakter: {len(js_content)}")
    
    # Cari pola menarik
    patterns = [
        r'(?i)api[-_]?key',
        r'(?i)x[-_]api[-_]key',
        r'(?i)authorization',
        r'(?i)token',
        r'["\'](AIzaSy[A-Za-z0-9-_]{33})["\']', # Google API Key
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, js_content)
        print(f"Pencarian pola '{pattern}': Ditemukan {len(matches)} kecocokan.")
        
    # Cari penugasan header menarik
    # Misalnya header dengan key tertentu
    headers_matches = re.findall(r'headers\s*:\s*\{([^}]+)\}', js_content)
    if headers_matches:
        print(f"Ditemukan {len(headers_matches)} penugasan headers. Cuplikan:")
        for idx, match in enumerate(headers_matches[:10]):
            cleaned = match.strip().replace("\n", " ")
            print(f"  [{idx}] {cleaned[:150]}")
            
    # Temukan string statis dengan panjang tertentu yang mungkin berupa token/API key
    # Misalnya string hexadecimal 32 atau 64 karakter, atau string base64
    # Tapi mari cari baris kode di mana "api-key" atau "X-Api-Key" berada
    for line in js_content.split("\n"):
        if any(keyword in line for keyword in ["api-key", "ApiKey", "API_KEY", "x-api-key", "X-API-KEY", "x_api_key"]):
            # Print cuplikan di sekitar kata tersebut
            for match in re.finditer(r'(?:api-key|ApiKey|API_KEY|x-api-key|X-API-KEY|x_api_key)', line, re.IGNORECASE):
                start = max(0, match.start() - 100)
                end = min(len(line), match.end() + 100)
                print(f"Konteks kecocokan kata kunci:\n  ... {line[start:end]} ...")

if __name__ == "__main__":
    search_main_js()
