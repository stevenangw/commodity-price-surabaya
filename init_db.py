import os
import psycopg2
from dotenv import load_dotenv

# Muat variabel lingkungan dari berkas .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "commodity_monitor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

def init_database():
    """
    Mengotomatiskan pembuatan database dan DDL:
    1. Masuk ke default database 'postgres' untuk membuat database target jika belum ada.
    2. Masuk ke database target dan mengeksekusi berkas database_init.sql terpadu.
    Menggunakan kredensial aman dari berkas .env.
    """
    print(f"=== INISIALISASI DATABASE POSTGRESQL LOKAL ===")
    print(f"Menghubungkan ke PostgreSQL di {DB_HOST}:{DB_PORT}...")
    
    # Langkah 1: Cek & Buat Database Target
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"
        )
        conn.autocommit = True
        
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (DB_NAME,))
            db_exists = cur.fetchone()
            if not db_exists:
                print(f"Database '{DB_NAME}' belum ada. Membuat basis data baru...")
                cur.execute(f"CREATE DATABASE {DB_NAME};")
                print(f"Database '{DB_NAME}' sukses dibuat!")
            else:
                print(f"Database '{DB_NAME}' sudah terdaftar.")
        conn.close()
    except Exception as e:
        print(f"Informasi/Peringatan saat memeriksa database: {str(e)}")
        print("Melanjutkan ke eksekusi DDL langsung (mengasumsikan database sudah siap)...")

    # Langkah 2: Eksekusi database_init.sql
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        conn.autocommit = True
        
        sql_path = "database_init.sql"
        if not os.path.exists(sql_path):
            print(f"Kesalahan: Berkas {sql_path} tidak ditemukan!")
            return
            
        print(f"Membaca skrip DDL '{sql_path}'...")
        with open(sql_path, "r", encoding="utf-8") as f:
            sql_queries = f.read()
            
        print("Mengeksekusi DDL, Partisi, VIEW, dan pembuatan user db_reporter...")
        with conn.cursor() as cur:
            cur.execute(sql_queries)
            
        print("=== DATABASE POSTGRESQL SUKSES DIINISIALISASI! ===")
        conn.close()
    except Exception as e:
        print(f"Kesalahan Kritis saat mengeksekusi DDL inisialisasi: {str(e)}")

if __name__ == "__main__":
    init_database()
