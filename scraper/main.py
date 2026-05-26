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

from scraper.config import BAPANAS_API_URL, INTERNAL_TOKEN, API_SERVER_URL, DB_CONFIGURED, OFFLINE_MARKETS, OFFLINE_COMMODITIES
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
            for market_name in OFFLINE_MARKETS.keys():
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
    markets = list(OFFLINE_MARKETS.keys())
    
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
# Unified Dashboard JSON Exporter & Local Calculations
# =====================================================================

def generate_dashboard_jsons(records: List[ScrapedPriceRecord]):
    """
    Fungsi terpadu (shared) untuk memproses records (baik dari database maupun offline)
    dan menulis berkas latest_prices.json, anomalies.json, dan trends.json ke folder docs/data/.
    """
    logger.info("=== MEMULAI PEMBUATAN BERKAS JSON STATIS DASBOR ===")
    os.makedirs("docs/data", exist_ok=True)
    
    if not records:
        logger.warning("Tidak ada data records untuk diekspor ke JSON dasbor.")
        return
        
    # Deduplicate records by (market, commodity, date)
    unique_records = {}
    for r in records:
        key = (r.normalized_market_name, r.normalized_commodity_name, r.price_date)
        unique_records[key] = r
    records = list(unique_records.values())
        
    # Ambil tanggal terbaru (max date) dari data
    max_date = max(r.price_date for r in records)
    
    # 1. GENERATE latest_prices.json
    latest_prices_dict = {}
    latest_records = [r for r in records if r.price_date == max_date]
    
    for r in latest_records:
        comm_name = r.normalized_commodity_name
        market_name = r.normalized_market_name
        
        comm_info = OFFLINE_COMMODITIES.get(comm_name)
        market_info = OFFLINE_MARKETS.get(market_name)
        
        if not comm_info or not market_info:
            continue
            
        cid_str = str(comm_info["id"])
        if cid_str not in latest_prices_dict:
            latest_prices_dict[cid_str] = {
                "commodity_id": comm_info["id"],
                "commodity_name": comm_name,
                "target_date": str(max_date),
                "records": []
            }
            
        latest_prices_dict[cid_str]["records"].append({
            "market_id": market_info["id"],
            "market_name": market_name,
            "market_type": market_info["market_type"],
            "latitude": market_info["latitude"],
            "longitude": market_info["longitude"],
            "price": float(r.price),
            "price_date": str(r.price_date),
            "unit": comm_info["unit"]
        })
        
    with open("docs/data/latest_prices.json", "w", encoding="utf-8") as f:
        json.dump(latest_prices_dict, f, indent=2, ensure_ascii=False)
    logger.info("Berhasil menulis docs/data/latest_prices.json")
    
    # 2. GENERATE anomalies.json
    anomalies_dict = {}
    timeframes = {
        "1D": 1,
        "3D": 3,
        "1W": 7,
        "1M": 30
    }
    
    # Pre-group all records by (market, commodity) and date for fast lookup
    records_by_key = {}
    for r in records:
        key = (r.normalized_market_name, r.normalized_commodity_name)
        if key not in records_by_key:
            records_by_key[key] = {}
        records_by_key[key][r.price_date] = float(r.price)
        
    for tf_code, days in timeframes.items():
        anomalies_list = []
        for (market_name, comm_name), date_prices in records_by_key.items():
            if max_date not in date_prices:
                continue
                
            current_price = date_prices[max_date]
            
            # Kumpulkan harga dari hari-hari sebelumnya
            preceding_prices = []
            for d in range(1, days + 1):
                prev_date = max_date - timedelta(days=d)
                if prev_date in date_prices:
                    preceding_prices.append(date_prices[prev_date])
                    
            if preceding_prices:
                avg_price = sum(preceding_prices) / len(preceding_prices)
                if avg_price > 0 and current_price > (avg_price * 1.15):
                    price_increase_pct = ((current_price - avg_price) / avg_price) * 100
                    
                    market_info = OFFLINE_MARKETS.get(market_name)
                    comm_info = OFFLINE_COMMODITIES.get(comm_name)
                    
                    if market_info and comm_info:
                        anomalies_list.append({
                            "market_id": market_info["id"],
                            "market_name": market_name,
                            "market_type": market_info["market_type"],
                            "latitude": market_info["latitude"],
                            "longitude": market_info["longitude"],
                            "commodity_id": comm_info["id"],
                            "commodity_name": comm_name,
                            "price_date": str(max_date),
                            "current_price": current_price,
                            "avg_price_7d": avg_price,
                            "price_increase_pct": price_increase_pct
                        })
                        
        anomalies_list.sort(key=lambda x: x["price_increase_pct"], reverse=True)
        anomalies_dict[tf_code] = {
            "target_date": str(max_date),
            "anomalies": anomalies_list
        }
        logger.info(f"Berhasil memproses {len(anomalies_list)} anomali untuk rentang waktu {tf_code}.")
        
    with open("docs/data/anomalies.json", "w", encoding="utf-8") as f:
        json.dump(anomalies_dict, f, indent=2, ensure_ascii=False)
    logger.info("Berhasil menulis docs/data/anomalies.json")
    
    # 3. GENERATE trends.json
    trends_dict = {}
    start_trend_date = max_date - timedelta(days=30)
    
    trends_by_key = {}
    for r in records:
        if start_trend_date <= r.price_date <= max_date:
            key = (r.normalized_commodity_name, r.price_date)
            if key not in trends_by_key:
                trends_by_key[key] = []
            trends_by_key[key].append(float(r.price))
            
    for (comm_name, p_date), prices in trends_by_key.items():
        comm_info = OFFLINE_COMMODITIES.get(comm_name)
        if not comm_info:
            continue
            
        cid_str = str(comm_info["id"])
        if cid_str not in trends_dict:
            trends_dict[cid_str] = {
                "commodity_id": comm_info["id"],
                "commodity_name": comm_name,
                "trend": []
            }
            
        avg_price = sum(prices) / len(prices)
        trends_dict[cid_str]["trend"].append({
            "price_date": str(p_date),
            "avg_price": round(avg_price, 2)
        })
        
    for cid_str in trends_dict:
        trends_dict[cid_str]["trend"].sort(key=lambda x: x["price_date"])
        
    with open("docs/data/trends.json", "w", encoding="utf-8") as f:
        json.dump(trends_dict, f, indent=2, ensure_ascii=False)
    logger.info("Berhasil menulis docs/data/trends.json")
    logger.info("=== SELURUH DATA JSON STATIS BERHASIL DIEKSPOR SECARA TERPADU! ===")

# =====================================================================
# Database Static JSON Exporter (SQL Mode Wrapper)
# =====================================================================

def export_static_json(db_manager: DatabaseManager):
    """
    Mengekstrak data 60 hari terakhir dari Supabase PostgreSQL 
    dan menyimpannya ke berkas JSON statis menggunakan generator terpadu.
    """
    logger.info("=== MEMULAI EKSPOR DATA DARI DATABASE POSTGRESQL ===")
    conn = db_manager.get_connection()
    
    sql_query = """
        SELECT 
            m.name as market_name,
            c.name as commodity_name,
            ph.price_date,
            ph.price,
            ph.source_url
        FROM price_history ph
        JOIN markets m ON ph.market_id = m.id
        JOIN commodities c ON ph.commodity_id = c.id
        WHERE ph.price_date >= CURRENT_DATE - INTERVAL '60 days';
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql_query)
            rows = cur.fetchall()
            
            records: List[ScrapedPriceRecord] = []
            for m_name, c_name, p_date, price, s_url in rows:
                records.append(ScrapedPriceRecord(
                    external_market_name=m_name,
                    external_commodity_name=c_name,
                    normalized_market_name=m_name,
                    normalized_commodity_name=c_name,
                    price_date=p_date,
                    price=Decimal(str(price)),
                    source_url=s_url
                ))
            
            logger.info(f"Berhasil menarik {len(records)} baris data historis dari database.")
            # Sinkronkan cache offline dengan data terbaru dari database
            save_offline_history(records)
            
            # Ekspor JSON dasbor statis
            generate_dashboard_jsons(records)
            
    except Exception as e:
        logger.error(f"Gagal mengekspor data menggunakan SQL: {str(e)}")
        raise e

# =====================================================================
# Resilient Offline Cache Loader & Saver (Serverless Failover Engine)
# =====================================================================

def load_offline_history() -> List[ScrapedPriceRecord]:
    """
    Membaca data historis dari berkas cache lokal docs/data/history.json.
    Mengembalikan daftar ScrapedPriceRecord.
    """
    cache_path = "docs/data/history.json"
    if not os.path.exists(cache_path):
        logger.info(f"Berkas cache offline {cache_path} belum tersedia.")
        return []
        
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            records = []
            for item in data:
                records.append(ScrapedPriceRecord(
                    external_market_name=item["external_market_name"],
                    external_commodity_name=item["external_commodity_name"],
                    normalized_market_name=item["normalized_market_name"],
                    normalized_commodity_name=item["normalized_commodity_name"],
                    price_date=datetime.strptime(item["price_date"], "%Y-%m-%d").date(),
                    price=Decimal(str(item["price"])),
                    source_url=item.get("source_url")
                ))
            logger.info(f"Berhasil memuat {len(records)} data historis dari cache offline.")
            return records
    except Exception as e:
        logger.warning(f"Gagal memuat cache offline: {str(e)}")
        return []

def save_offline_history(records: List[ScrapedPriceRecord]):
    """
    Menyimpan records ke berkas cache lokal docs/data/history.json dengan pembatasan 45 hari terakhir
    untuk menghemat ruang penyimpanan.
    """
    cache_path = "docs/data/history.json"
    os.makedirs("docs/data", exist_ok=True)
    
    if not records:
        return
        
    # Cari tanggal terbaru dan batasi ke 45 hari ke belakang
    max_date = max(r.price_date for r in records)
    limit_date = max_date - timedelta(days=45)
    
    filtered_records = [r for r in records if r.price_date >= limit_date]
    
    # Hindari duplikasi dengan kombinasi unik (market, commodity, date)
    unique_records = {}
    for r in filtered_records:
        key = (r.normalized_market_name, r.normalized_commodity_name, r.price_date)
        unique_records[key] = r
        
    serialized_data = []
    for r in unique_records.values():
        serialized_data.append({
            "external_market_name": r.external_market_name,
            "external_commodity_name": r.external_commodity_name,
            "normalized_market_name": r.normalized_market_name,
            "normalized_commodity_name": r.normalized_commodity_name,
            "price_date": str(r.price_date),
            "price": float(r.price),
            "source_url": r.source_url
        })
        
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(serialized_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Berhasil memperbarui cache offline di {cache_path} dengan {len(serialized_data)} records.")
    except Exception as e:
        logger.error(f"Gagal menulis cache offline: {str(e)}")

def run_offline_pipeline(new_records: List[ScrapedPriceRecord]):
    """
    Mengeksekusi otomatisasi serverless tanpa database:
    1. Memuat cache history.json
    2. Menggabungkan data baru (hari ini)
    3. Menyimpan kembali cache history.json
    4. Menghasilkan docs/data/*.json dasbor terpadu
    """
    logger.info("=== MEMULAI PIPELINE OFF-LINE RESILIENT (SERVERLESS) ===")
    history_records = load_offline_history()
    
    # Gabungkan data baru dengan data historis
    all_records = history_records + new_records
    
    # Simpan kembali cache history
    save_offline_history(all_records)
    
    # Hasilkan berkas visualisasi dasbor statis
    generate_dashboard_jsons(all_records)

# =====================================================================
# Main Scraper Entry Point
# =====================================================================

async def main():
    parser = argparse.ArgumentParser(description="Sistem Pemantauan Harga Pangan Surabaya - Scraper & Generator CLI")
    parser.add_argument("--mock", action="store_true", help="Gunakan Sandbox Mode (generator data tiruan) mutlak")
    parser.add_argument("--start-date", type=str, default="2026-04-01", help="Tanggal awal untuk Sandbox Generator")
    args = parser.parse_args()
    
    db_manager = DatabaseManager()
    
    logger.info("=== START PENJADWAL SCRAPING HARGA SURABAYA ===")
    
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
            
        # 3. Periksa Ketersediaan Database & Upload
        db_connected = False
        if DB_CONFIGURED:
            try:
                logger.info("Mencoba menghubungkan ke database PostgreSQL...")
                db_manager.get_connection()
                commodity_lookup, market_lookup = db_manager.fetch_master_lookups()
                
                logger.info(f"Memproses {len(scraped_records)} baris data untuk dimasukkan ke database...")
                upserted = db_manager.batch_upsert_prices(
                    records=scraped_records,
                    commodity_lookup=commodity_lookup,
                    market_lookup=market_lookup,
                    default_regency_id="3578" # Surabaya BPS Code
                )
                logger.info(f"Sukses mengunggah {upserted} baris data harga pangan Surabaya ke database.")
                db_connected = True
            except Exception as db_err:
                logger.error(f"[ERROR] Gagal menghubungkan atau mengunggah data ke database PostgreSQL: {str(db_err)}")
                logger.warning("Beralih ke Serverless Resilient Fallback Mode...")
        else:
            logger.warning("[WARNING] Database tidak dikonfigurasi di secrets atau lingkungan lokal.")
            logger.warning("Beralih ke Serverless Resilient Fallback Mode...")

        # 4. Ekspor Data JSON Statis (Docs)
        if db_connected:
            try:
                export_static_json(db_manager)
            except Exception as exp_err:
                logger.error(f"Gagal mengekspor data menggunakan SQL: {str(exp_err)}")
                logger.warning("Beralih ke ekspor data offline menggunakan Python...")
                run_offline_pipeline(scraped_records)
        else:
            run_offline_pipeline(scraped_records)
            
    except Exception as e:
        logger.critical(f"Kesalahan kritis global: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())

