import os
import psycopg2
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "commodity_monitor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

def run_seeder():
    conn_params = {
        "host": DB_HOST,
        "port": DB_PORT,
        "database": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD
    }
    
    print("=== PROGRAM PENYEMAI DATA MASTER & SIMULASI HARGA HARIAN ===")
    print(f"Menghubungkan ke PostgreSQL: {DB_HOST}:{DB_PORT}...")
    
    try:
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = False
        cur = conn.cursor()
        
        # 1. Seed Provinces
        print("Menyemai data master Provinsi...")
        provinces = [
            ("31", "DKI Jakarta", -6.2088, 106.8456),
            ("35", "Jawa Timur", -7.2575, 112.7521)
        ]
        for pid, name, lat, lon in provinces:
            cur.execute("""
                INSERT INTO provinces (id, name, latitude, longitude)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    name = EXCLUDED.name,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude;
            """, (pid, name, lat, lon))
            
        # 2. Seed Regencies
        print("Menyemai data master Kabupaten/Kota...")
        regencies = [
            ("3171", "31", "Kota Jakarta Pusat", "Kota", -6.1865, 106.8436),
            ("3175", "31", "Kota Jakarta Timur", "Kota", -6.2250, 106.9004),
            ("3578", "35", "Kota Surabaya", "Kota", -7.2575, 112.7521)
        ]
        for rid, pid, name, rtype, lat, lon in regencies:
            cur.execute("""
                INSERT INTO regencies (id, province_id, name, type, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    province_id = EXCLUDED.province_id,
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude;
            """, (rid, pid, name, rtype, lat, lon))
            
        # 3. Seed Markets
        print("Menyemai data master Pasar...")
        markets = [
            (1, "3171", "Pasar Senen", "Tradisional", -6.1744, 106.8443),
            (2, "3175", "Pasar Induk Kramat Jati", "Tradisional", -6.2738, 106.8686),
            (3, "3578", "Pasar Wonokromo", "Tradisional", -7.3005, 112.7383)
        ]
        for mid, rid, name, mtype, lat, lon in markets:
            cur.execute("""
                INSERT INTO markets (id, regency_id, name, market_type, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    regency_id = EXCLUDED.regency_id,
                    name = EXCLUDED.name,
                    market_type = EXCLUDED.market_type,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude;
            """, (mid, rid, name, mtype, lat, lon))
            
        # 4. Seed Commodities
        print("Menyemai data master Komoditas...")
        commodities = [
            (1, "Beras Medium", "Beras", "kg"),
            (2, "Cabai Rawit Merah", "Cabai", "kg"),
            (3, "Bawang Merah", "Bawang", "kg"),
            (4, "Daging Ayam Ras", "Daging", "kg"),
            (5, "Telur Ayam Ras", "Telur", "kg")
        ]
        for cid, name, cat, unit in commodities:
            cur.execute("""
                INSERT INTO commodities (id, name, category, unit)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    unit = EXCLUDED.unit;
            """, (cid, name, cat, unit))
            
        # Commit master data
        conn.commit()
        print("Master data sukses disemai!")
        
        # 5. Seed Price History (Simulasi 30 hari terakhir sampai hari ini)
        print("\nMenyemai data simulasi harga pangan historis (30 hari terakhir)...")
        
        # Hapus data lama agar bersih
        cur.execute("TRUNCATE TABLE price_history;")
        
        base_prices = {
            1: 12500, # Beras Medium
            2: 45000, # Cabai Rawit Merah
            3: 32000, # Bawang Merah
            4: 35000, # Daging Ayam Ras
            5: 27000  # Telur Ayam Ras
        }
        
        # Rentang hari
        today = datetime.now().date()
        start_date = today - timedelta(days=30)
        
        price_records = []
        
        # Loop setiap hari
        for d in range(31):
            current_date = start_date + timedelta(days=d)
            
            # Loop setiap pasar
            for mid in [1, 2, 3]:
                # Loop setiap komoditas
                for cid in [1, 2, 3, 4, 5]:
                    # Tambahkan sedikit variasi acak (-3% sampai +3%) harian
                    base = base_prices[cid]
                    
                    # Berikan fluktuasi berdasarkan pasar agar harga antar pasar berbeda
                    market_factor = 1.0
                    if mid == 1: # Pasar Senen (Normal)
                        market_factor = 0.98
                    elif mid == 2: # Pasar Kramat Jati (Grosir - Murah)
                        market_factor = 0.93
                    elif mid == 3: # Pasar Wonokromo (Jawa Timur - Sedikit fluktuatif)
                        market_factor = 1.02
                        
                    # Dapatkan harga dasar ter-faktor
                    daily_base = base * market_factor
                    
                    # Fluktuasi acak per hari
                    # Gunakan seed random berbasis tanggal & pasar agar repeatable tetapi variatif
                    random.seed(int(current_date.strftime("%Y%m%d")) + mid * 100 + cid * 10)
                    fluctuation = random.uniform(-0.04, 0.04)
                    
                    price = daily_base * (1 + fluctuation)
                    
                    # Tambahkan anomali lonjakan harga khusus (>15% dari rata-rata sebelumnya) untuk hari ini!
                    # Ini berguna untuk memicu skrip anomaly detector dan alert Telegram Bot secara instan!
                    if current_date == today:
                        # Cabai Rawit Merah di Pasar Wonokromo melonjak 25% hari ini
                        if cid == 2 and mid == 3:
                            price = daily_base * 1.28
                            print(f"  [ANOMALI] Memicu lonjakan harga Cabai Rawit Merah di Pasar Wonokromo sebesar Rp {price:,.0f} (+28%) hari ini.")
                        # Bawang Merah di Pasar Senen melonjak 20% hari ini
                        elif cid == 3 and mid == 1:
                            price = daily_base * 1.22
                            print(f"  [ANOMALI] Memicu lonjakan harga Bawang Merah di Pasar Senen sebesar Rp {price:,.0f} (+22%) hari ini.")
                            
                    price_records.append((
                        mid,
                        cid,
                        current_date,
                        round(price, 2),
                        "https://panelharga.badanpangan.go.id/"
                    ))
                    
        # Batch insert
        print(f"Menyimpan {len(price_records)} data record harga historis ke database...")
        from psycopg2.extras import execute_values
        execute_values(
            cur,
            """
            INSERT INTO price_history (market_id, commodity_id, price_date, price, source_url)
            VALUES %s;
            """,
            price_records
        )
        
        conn.commit()
        print("=== DATABASE BERHASIL DISEMAI DENGAN DATA MASTER & SIMULASI PENUH! ===")
        print("Sistem visualisasi peta spasial dan grafik kini siap digunakan sepenuhnya.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print("Gagal menyemai database:", str(e))

if __name__ == "__main__":
    run_seeder()
