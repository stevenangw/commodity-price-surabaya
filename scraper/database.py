import logging
from datetime import date
import psycopg2
from psycopg2 import extras
from typing import List, Dict, Tuple, Optional
from scraper.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSLMODE
from scraper.utils.parser import ScrapedPriceRecord

logger = logging.getLogger("scraper.database")

# =====================================================================
# Kelas Pengelola Database PostgreSQL
# =====================================================================

class DatabaseManager:
    """
    Mengelola koneksi database PostgreSQL, registrasi master data lookup,
    dan transaksi batch upsert harga pangan dengan performa tinggi.
    """

    def __init__(self):
        self.conn_params = {
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
            "user": DB_USER,
            "password": DB_PASSWORD,
            "sslmode": DB_SSLMODE
        }
        self.connection = None

    def get_connection(self):
        """Membuat atau mengembalikan koneksi PostgreSQL yang aktif."""
        if self.connection is None or self.connection.closed != 0:
            try:
                logger.info(f"Membuka koneksi baru ke database PostgreSQL '{DB_NAME}'...")
                self.connection = psycopg2.connect(**self.conn_params)
                self.connection.autocommit = False  # Menggunakan transaksi manual
            except Exception as e:
                logger.critical(f"Gagal menyambung ke database PostgreSQL: {str(e)}")
                raise e
        return self.connection

    def close(self):
        """Menutup koneksi database secara aman."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Koneksi database berhasil ditutup.")

    def fetch_master_lookups(self) -> Tuple[Dict[str, int], Dict[Tuple[str, str], int]]:
        """
        Mengambil seluruh master data komoditas dan pasar yang ada di database.
        Membangun kamus pencarian (lookup dictionary) untuk memetakan nama ter-normalisasi ke ID primer.
        
        Returns:
            Tuple dari (commodity_lookup, market_lookup)
            - commodity_lookup: {"nama_komoditas_std": id}
            - market_lookup: {("nama_pasar_std", "regency_id"): id}
        """
        conn = self.get_connection()
        commodity_lookup: Dict[str, int] = {}
        market_lookup: Dict[Tuple[str, str], int] = {}

        try:
            with conn.cursor() as cur:
                # 1. Fetch Commodities
                logger.debug("Memuat data master komoditas dari database...")
                cur.execute("SELECT id, name FROM commodities;")
                for cid, name in cur.fetchall():
                    commodity_lookup[name.lower().strip()] = cid

                # 2. Fetch Markets
                logger.debug("Memuat data master pasar dari database...")
                cur.execute("SELECT id, name, regency_id FROM markets;")
                for mid, name, regency_id in cur.fetchall():
                    # Kunci pencarian menggunakan pasangan nama pasar lowercase dan regency_id
                    key = (name.lower().strip(), str(regency_id).strip())
                    market_lookup[key] = mid

            logger.info(f"Master lookup berhasil dimuat: {len(commodity_lookup)} komoditas, {len(market_lookup)} pasar.")
            return commodity_lookup, market_lookup

        except Exception as e:
            logger.error(f"Gagal memuat master lookup dari database: {str(e)}")
            raise e

    def batch_upsert_prices(
        self, 
        records: List[ScrapedPriceRecord], 
        commodity_lookup: Dict[str, int], 
        market_lookup: Dict[Tuple[str, str], int],
        default_regency_id: Optional[str] = None
    ) -> int:
        """
        Melakukan batch upsert data harga pangan ke tabel price_history.
        Memetakan nama pasar/komoditas yang ter-normalisasi ke ID database asli sebelum eksekusi.
        
        Sintaks SQL: ON CONFLICT (market_id, commodity_id, price_date) DO UPDATE.
        
        Returns:
            Jumlah baris data yang berhasil di-upsert.
        """
        if not records:
            logger.warning("Tidak ada data record harga pangan untuk di-upsert.")
            return 0

        conn = self.get_connection()
        upsert_data: List[Tuple[int, int, date, float, str]] = []
        unmapped_markets = set()
        unmapped_commodities = set()

        # 1. Pemetaan Nama ke ID Database
        for idx, record in enumerate(records):
            # Normalisasi kunci untuk lookup
            comm_key = record.normalized_commodity_name.lower().strip()
            market_key_str = record.normalized_market_name.lower().strip()
            
            # Cari regency_id (opsional fallback jika payload scraper tidak menyediakannya)
            reg_id = default_regency_id
            if hasattr(record, 'regency_id') and record.regency_id:
                reg_id = record.regency_id
            elif not reg_id:
                # Cari regency_id default yang cocok dari market lookup jika tersedia secara global
                matching_markets = [r_id for (m_name, r_id) in market_lookup.keys() if m_name == market_key_str]
                if matching_markets:
                    reg_id = matching_markets[0]

            # Dapatkan database ID
            commodity_id = commodity_lookup.get(comm_key)
            market_id = market_lookup.get((market_key_str, str(reg_id).strip() if reg_id else ""))

            # Jika tidak terpetakan di database master, lewati dan catat log audit
            if not commodity_id:
                unmapped_commodities.add(record.normalized_commodity_name)
                continue
            if not market_id:
                unmapped_markets.add(f"{record.normalized_market_name} (Regency: {reg_id})")
                continue

            # Konversi Pydantic record ke tuple database
            upsert_data.append((
                market_id,
                commodity_id,
                record.price_date,
                float(record.price),
                record.source_url or ""
            ))

        # Tampilkan peringatan jika ada master data yang belum ter-align
        if unmapped_commodities:
            logger.warning(f"Komoditas tidak terdaftar di database master (Abaikan baris): {unmapped_commodities}")
        if unmapped_markets:
            logger.warning(f"Pasar tidak terdaftar di database master (Abaikan baris): {unmapped_markets}")

        if not upsert_data:
            logger.error("Semua baris data gagal dipetakan ke Master ID Database. Batch upsert dibatalkan.")
            return 0

        # 2. Eksekusi Batch Upsert menggunakan psycopg2 execute_values (Performa Tinggi)
        sql_query = """
            INSERT INTO price_history (market_id, commodity_id, price_date, price, source_url, updated_at)
            VALUES %s
            ON CONFLICT (market_id, commodity_id, price_date)
            DO UPDATE SET 
                price = EXCLUDED.price,
                updated_at = CURRENT_TIMESTAMP;
        """

        try:
            with conn.cursor() as cur:
                logger.info(f"Memulai eksekusi batch upsert sebanyak {len(upsert_data)} baris data...")
                extras.execute_values(
                    cur, 
                    sql_query, 
                    upsert_data, 
                    template="(%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)",
                    page_size=1000
                )
            
            # Commit transaksi setelah seluruh batch berhasil
            conn.commit()
            logger.info(f"Batch upsert berhasil! {len(upsert_data)} baris data disimpan ke database.")
            return len(upsert_data)

        except Exception as e:
            conn.rollback()  # Batalkan transaksi jika terjadi kesalahan
            logger.error(f"Gagal mengeksekusi batch upsert database (transaksi di-rollback): {str(e)}")
            raise e
