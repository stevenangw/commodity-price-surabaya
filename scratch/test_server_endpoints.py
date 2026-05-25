import requests
import json

def test_endpoints():
    base_url = "http://127.0.0.1:8088"
    print(f"=== MENGUJI REST API SERVER FASTAPI LOKAL: {base_url} ===")
    
    # 1. Health Check
    url_health = f"{base_url}/health"
    print(f"\n1. Mengirim GET ke {url_health}...")
    try:
        r = requests.get(url_health)
        print(f"   Status: {r.status_code}")
        print("   Body:", r.json())
    except Exception as e:
        print("   Gagal:", str(e))
        
    # 2. Get Latest Prices
    url_prices = f"{base_url}/api/v1/prices/latest"
    params = {"commodity_id": "1"}
    print(f"\n2. Mengirim GET ke {url_prices} dengan params {params}...")
    try:
        r = requests.get(url_prices, params=params)
        print(f"   Status: {r.status_code}")
        data = r.json()
        print(f"   Jumlah records: {len(data.get('records', []))}")
        if data.get('records'):
            print("   Contoh Record Pertama:")
            print(json.dumps(data['records'][0], indent=2))
    except Exception as e:
        print("   Gagal:", str(e))
        
    # 3. Get Price Anomalies
    url_anomalies = f"{base_url}/api/v1/prices/anomalies"
    print(f"\n3. Mengirim GET ke {url_anomalies}...")
    try:
        r = requests.get(url_anomalies)
        print(f"   Status: {r.status_code}")
        data = r.json()
        print(f"   Jumlah anomali: {len(data.get('anomalies', []))}")
        if data.get('anomalies'):
            print("   Daftar Anomali Terdeteksi:")
            print(json.dumps(data['anomalies'], indent=2))
    except Exception as e:
        print("   Gagal:", str(e))

if __name__ == "__main__":
    test_endpoints()
