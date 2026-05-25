import requests
import json

def main():
    url = "https://api-panelhargav2.badanpangan.go.id/api/cms/eceran"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Data length:", len(data.get("data", [])))
        if data.get("data"):
            print("Contoh data:")
            print(json.dumps(data["data"][:2], indent=2))
            
if __name__ == "__main__":
    main()
