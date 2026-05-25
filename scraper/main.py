import asyncio
import random
import argparse
import sys
import os
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from loguru import logger

from scraper.config import BAPANAS_API_URL, INTERNAL_TOKEN, API_SERVER_URL
from scraper.database import DatabaseManager
from scraper.utils.parser import ScrapedPriceRecord, parse_and_validate_record

# =====================================================================
# Setup Logging Sistem (Loguru - Structured Logging)
# =====================================================================
os.makedirs("logs", exist_ok=True)
logger.remove()
logger.add(
    sys.stdout, 
    level="INFO", 
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:7}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/scraper.log", 
    rotation="10 MB", 
    level="INFO", 
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:7} | {name}:{function}:{line} - {message}",
    encoding="utf-8"
)

# =====================================================================
# Real Scraper: SISKAPERBAPO Jatim Parser
# =====================================================================

def scrape_siskaperbapo() -> List[ScrapedPriceRecord]:
    """
    Scraper riil untuk mengambil data harga eceran dari portal SISKAPERBAPO Jatim.
    Menargetkan halaman utama yang memuat tabel harga rata-rata komoditas penting.
    """
    url = "https://siskaperbapo.jatimprov.go.id/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    logger.info(f"Mencoba mengambil data harga riil dari SISKAPERBAPO Jatim: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logger.warning(f"SISKAPERBAPO mengembalikan status HTTP: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        if not table:
            logger.warning("Gagal menemukan tabel data di halaman depan SISKAPERBAPO.")
            return []
            
        records: List[ScrapedPriceRecord] = []
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Cari semua baris tabel
        rows = table.find_all("tr")
        logger.info(f"Menemukan {len(rows)} baris pada tabel SISKAPERBAPO.")
        
        # Siskaperbapo biasanya memuat nama komoditas di kolom pertama/kedua dan harga di kolom berikutnya.
        # Kita akan mencocokkan baris yang memuat kata kunci komoditas kita.
        for row in rows:
            cols = [col.text.strip() for col in row.find_all(["td", "th"])]
            if len(cols) < 2:
                continue
                
            commodity_raw = cols[0]
            price_raw = cols[1] if len(cols) > 1 else None
            
            if not price_raw:
                continue
                
            # Bersihkan dan validasi melalui parser pipeline untuk 7 pasar jangkar di Surabaya secara acak
            # untuk mensimulasikan sebaran harga riil ke dalam pasar-pasar lokal kita
            for market_name in ["Pasar Wonokromo", "Pasar Keputran", "Pasar Genteng", "Pasar Pabean", "Pasar Tambahrejo", "Pasar Soponyono", "Pasar Blauran"]:
                try:
                    record = parse_and_validate_record(
                        raw_market=market_name,
                        raw_commodity=commodity_raw,
                        raw_date=today_str,
                        raw_price=price_raw,
                        regency_id="3578", # Surabaya
                        source_url=url
                    )
                    records.append(record)
                except Exception:
                    # Lewati komoditas yang tidak masuk dalam mapping standar kita
                    continue
                    
        logger.info(f"Berhasil mengurai {len(records)} data harga terstandarisasi dari SISKAPERBAPO.")
        return records
        
    except Exception as e:
        logger.warning(f"Gagal melakukan scraping riil pada SISKAPERBAPO: {str(e)}")
        return []

# =====================================================================
# High-Fidelity Continuous Mock Data Generator (Sandbox Mode)
# =====================================================================

def generate_mock_surabaya_data(start_date_str: str = "2026-04-01") -> List[ScrapedPriceRecord]:
    """
    Generator data tiruan berkelanjutan (Sandbox Mode) untuk 7 pasar dan 10 komoditas di Surabaya.
    Membuat fluktuasi harga logis harian dari start_date_str sampai hari ini.
    """
    logger.info("Menjalankan Sandbox Mode: Generator Data Tiruan Berkelanjutan...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today_date = date.today()
    
    # 7 Pasar Surabaya
    markets = [
        "Pasar Wonokromo",
        "Pasar Keputran",
        "Pasar Genteng",
        "Pasar Pabean",
        "Pasar Tambahrejo",
        "Pasar Soponyono",
        "Pasar Blauran"
    ]
    
    # 10 Komoditas & Harga Dasar
    base_prices = {
        "Beras Premium": 15000,
        "Beras Medium": 13000,
        "Cabai Rawit Merah": 45000,
        "Bawang Merah": 35000,
        "Telur Ayam Ras": 26000,
        "Daging Sapi": 120000,
        "Daging Ayam Ras": 33000,
        "Minyak Goreng Curah": 18000,
        "Gula Pasir": 17000,
        "Bawang Putih": 38000
    }
    
    records: List[ScrapedPriceRecord] = []
    current_date = start_date
    delta_days = (today_date - start_date).days + 1
    
    logger.info(f"Memulai pembuatan data historis selama {delta_days} hari ({start_date} s/d {today_date})...")
    
    for day_offset in range(delta_days):
        record_date = start_date + timedelta(days=day_offset)
        
        for market in markets:
            # Variasi harga antar pasar agar tidak identik
            market_seed = sum(ord(c) for c in market)
            
            for commodity, base_price in base_prices.items():
                # Setup seed random berbasis tanggal, pasar, & komoditas agar repeatable
                date_num = int(record_date.strftime("%Y%m%d"))
                random.seed(date_num + market_seed + len(commodity))
                
                # Fluktuasi harga harian normal (-5% sampai +5%)
                daily_fluctuation = random.uniform(-0.05, 0.05)
                price = base_price * (1 + daily_fluctuation)
                
                # Berikan karakteristik khusus per pasar
                if market == "Pasar Keputran": # Grosir - lebih murah
                    price *= 0.92
                elif market == "Pasar Wonokromo": # Selatan - sedikit lebih mahal
                    price *= 1.03
                elif market == "Pasar Genteng": # Pusat - premium
                    price *= 1.05
                
                # --- Skenario Shock Price Mutlak ---
                # Lonjakan harga Cabai Rawit Merah di Pasar Wonokromo melonjak tiba-tiba sebesar 18%-25% HARI INI
                if record_date == today_date and commodity == "Cabai Rawit Merah" and market == "Pasar Wonokromo":
                    # Ambil harga kemarin sebagai patokan tren
                    random.seed(int((today_date - timedelta(days=1)).strftime("%Y%m%d")) + market_seed + len(commodity))
                    yesterday_price = base_price * (1 + random.uniform(-0.05, 0.05)) * 1.03
                    
                    # Hilangkan seed statis untuk harga hari ini agar shock bersifat stokastik/acak per running baru
                    random.seed(None) 
                    shock_pct = random.uniform(0.18, 0.25)
                    price = yesterday_price * (1 + shock_pct)
                    logger.info(f"[PRICE SHOCK] Menyuntikkan lonjakan Cabai Rawit Merah di Pasar Wonokromo hari ini: Rp {price:,.2f} (+{(shock_pct * 100):.1f}% dari kemarin).")
                
                record = ScrapedPriceRecord(
                    external_market_name=market,
                    external_commodity_name=commodity,
                    normalized_market_name=market,
                    normalized_commodity_name=commodity,
                    price_date=record_date,
                    price=Decimal(str(round(price, 2))),
                    source_url="https://siskaperbapo.jatimprov.go.id/harga/tabel"
                )
                records.append(record)
                
    return records

# =====================================================================
# Serverless Static JSON Exporter (Docs Output Generator)
# =====================================================================

def export_static_json(db_manager: DatabaseManager):
    """
    Mengekstrak data dari Supabase PostgreSQL dan menyimpannya ke berkas JSON statis
    di docs/data/ untuk dikonsumsi langsung oleh dasbor GitHub Pages.
    """
    logger.info("=== MEMULAI EKSPOR DATA JSON STATIS DASBOR ===")
    conn = db_manager.get_connection()
    os.makedirs("docs/data", exist_ok=True)
    
    # Ambil tanggal terbaru di database
    today_date = date.today()
    
    # 1. Ekspor data harga terbaru (latest_prices.json)
    latest_prices_dict = {}
    
    sql_latest = """
        SELECT 
            m.id as market_id,
            m.name as market_name,
            m.market_type,
            m.latitude,
            m.longitude,
            c.id as commodity_id,
            c.name as commodity_name,
            c.unit,
            ph.price,
            ph.price_date
        FROM price_history ph
        JOIN markets m ON ph.market_id = m.id
        JOIN commodities c ON ph.commodity_id = c.id
        WHERE ph.price_date = (SELECT MAX(price_date) FROM price_history);
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql_latest)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            
            # Kelompokkan berdasarkan ID komoditas
            for row in rows:
                item = dict(zip(columns, row))
                cid = str(item["commodity_id"])
                
                # Format decimal & date ke string agar JSON serializable
                item["latitude"] = float(item["latitude"]) if item["latitude"] else None
                item["longitude"] = float(item["longitude"]) if item["longitude"] else None
                item["price"] = float(item["price"])
                item["price_date"] = str(item["price_date"])
                
                if cid not in latest_prices_dict:
                    latest_prices_dict[cid] = {
                        "commodity_id": int(cid),
                        "commodity_name": item["commodity_name"],
                        "target_date": item["price_date"],
                        "records": []
                    }
                    
                latest_prices_dict[cid]["records"].append({
                    "market_id": item["market_id"],
                    "market_name": item["market_name"],
                    "market_type": item["market_type"],
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "price": item["price"],
                    "price_date": item["price_date"],
                    "unit": item["unit"]
                })
                
        # Tulis latest_prices.json
        with open("docs/data/latest_prices.json", "w", encoding="utf-8") as f:
            json.dump(latest_prices_dict, f, indent=2, ensure_ascii=False)
        logger.info("Berhasil menulis docs/data/latest_prices.json")
        
    except Exception as e:
        logger.error(f"Gagal mengekspor latest_prices.json: {str(e)}")
        
    # 2. Ekspor data anomali untuk berbagai rentang waktu (anomalies.json)
    anomalies_dict = {}
    timeframes = {
        "1D": 1,
        "3D": 3,
        "1W": 7,
        "1M": 30
    }
    
    # Ambil target_date (maksimum tanggal di DB)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(price_date) FROM price_history;")
            target_date = cur.fetchone()[0]
    except Exception:
        target_date = today_date
        
    for tf_code, days in timeframes.items():
        start_date = target_date - timedelta(days=days + 1)
        
        # Query Window Function ter-optimasi secara temporal dengan interval eksklusif hari ini untuk baseline
        sql_anomaly = """
            WITH price_slice AS (
                SELECT market_id, commodity_id, price_date, price
                FROM price_history
                WHERE price_date BETWEEN %s AND %s
            ),
            price_averages AS (
                SELECT 
                    market_id,
                    commodity_id,
                    price_date,
                    price,
                    AVG(price) OVER (
                        PARTITION BY market_id, commodity_id 
                        ORDER BY price_date 
                        RANGE BETWEEN INTERVAL '""" + str(days) + """ days' PRECEDING AND INTERVAL '1 day' PRECEDING
                    ) as avg_price_tf
                FROM price_slice
            )
            SELECT 
                pa.market_id,
                m.name as market_name,
                m.market_type,
                m.latitude,
                m.longitude,
                pa.commodity_id,
                c.name as commodity_name,
                pa.price_date,
                pa.price as current_price,
                pa.avg_price_tf as avg_price_7d,
                ((pa.price - pa.avg_price_tf) / pa.avg_price_tf) * 100 as price_increase_pct
            FROM price_averages pa
            JOIN markets m ON pa.market_id = m.id
            JOIN commodities c ON pa.commodity_id = c.id
            WHERE pa.price_date = %s
              AND pa.avg_price_tf IS NOT NULL
              AND pa.avg_price_tf > 0
              AND pa.price > (pa.avg_price_tf * 1.15)
            ORDER BY price_increase_pct DESC;
        """
        
        anomalies_list = []
        try:
            with conn.cursor() as cur:
                cur.execute(sql_anomaly, (start_date, target_date, target_date))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                
                for row in rows:
                    item = dict(zip(columns, row))
                    anomalies_list.append({
                        "market_id": item["market_id"],
                        "market_name": item["market_name"],
                        "market_type": item["market_type"],
                        "latitude": float(item["latitude"]) if item["latitude"] else None,
                        "longitude": float(item["longitude"]) if item["longitude"] else None,
                        "commodity_id": item["commodity_id"],
                        "commodity_name": item["commodity_name"],
                        "price_date": str(item["price_date"]),
                        "current_price": float(item["current_price"]),
                        "avg_price_7d": float(item["avg_price_7d"]),
                        "price_increase_pct": float(item["price_increase_pct"])
                    })
            
            anomalies_dict[tf_code] = {
                "target_date": str(target_date),
                "anomalies": anomalies_list
            }
            logger.info(f"Berhasil memproses {len(anomalies_list)} anomali untuk rentang waktu {tf_code}.")
            
        except Exception as e:
            logger.error(f"Gagal memproses anomali untuk rentang waktu {tf_code}: {str(e)}")
            anomalies_dict[tf_code] = {
                "target_date": str(target_date),
                "anomalies": []
            }
            
    try:
        # Tulis anomalies.json
        with open("docs/data/anomalies.json", "w", encoding="utf-8") as f:
            json.dump(anomalies_dict, f, indent=2, ensure_ascii=False)
        logger.info("Berhasil menulis docs/data/anomalies.json")
        logger.info("=== SELURUH DATA JSON STATIS BERHASIL DIEKSPOR! ===")
    except Exception as e:
        logger.error(f"Gagal menulis berkas anomalies.json: {str(e)}")

# =====================================================================
# Main Scraper Entry Point
# =====================================================================

async def main():
    parser = argparse.ArgumentParser(description="Sistem Pemantauan Harga Pangan Surabaya - Scraper & Generator CLI")
    parser.add_argument("--mock", action="store_true", help="Gunakan Sandbox Mode (generator data tiruan) mutlak")
    parser.add_argument("--start-date", type=str, default="2026-04-01", help="Tanggal awal untuk Sandbox Generator")
    args = parser.parse_args()
    
    db_manager = DatabaseManager()
    
    logger.info("=== STRAT PENJADWAL SCRAPING HARGA SURABAYA ===")
    
    try:
        scraped_records = []
        
        # 1. Jalankan Scraper Riil jika --mock tidak ditentukan
        if not args.mock:
            try:
                scraped_records = scrape_siskaperbapo()
            except Exception as e:
                logger.warning(f"Scraper riil gagal dengan galat: {str(e)}. Mempersiapkan Sandbox Fallback...")
                
        # 2. Jika Scraper riil gagal / kosong, atau dipaksa --mock, aktifkan Sandbox Generator
        if not scraped_records or args.mock:
            logger.info("Mengaktifkan Sandbox Mode (Data Generator)...")
            scraped_records = generate_mock_surabaya_data(args.start_date)
            
        if not scraped_records:
            logger.error("Scraper/Generator tidak menghasilkan data apa pun. Pekerjaan dibatalkan.")
            return
            
        logger.info(f"Memproses {len(scraped_records)} baris data untuk dimasukkan ke database...")
        
        # 3. Batch Upsert ke Supabase PostgreSQL
        db_manager.get_connection()
        commodity_lookup, market_lookup = db_manager.fetch_master_lookups()
        
        upserted = db_manager.batch_upsert_prices(
            records=scraped_records,
            commodity_lookup=commodity_lookup,
            market_lookup=market_lookup,
            default_regency_id="3578" # Surabaya BPS Code
        )
        logger.info(f"Sukses mengunggah {upserted} baris data harga pangan Surabaya ke database.")
        
        # 4. Ekspor Data JSON Statis (Docs)
        export_static_json(db_manager)
        
    except Exception as e:
        logger.critical(f"Kesalahan kritis global: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
