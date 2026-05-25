import os
import sys
import subprocess
import time
import webbrowser
import http.server
import socketserver
import threading
from loguru import logger

# =====================================================================
# Setup Logging
# =====================================================================
logger.remove()
logger.add(
    sys.stdout, 
    level="INFO", 
    format="<cyan>{time:HH:mm:ss}</cyan> | <level>{level:7}</level> | <level>{message}</level>"
)

# Inisialisasi awal ke 0 agar OS mengalokasikan port bebas secara acak
PORT = 0 

def start_local_server():
    """Menjalankan HTTP server lokal di thread latar belakang untuk pratinjau dasbor bebas CORS."""
    global PORT
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            logger.debug(f"HTTP Server - {format%args}")

    try:
        socketserver.TCPServer.allow_reuse_address = True
        # Bind ke port 0 memicu OS untuk mengalokasikan port bebas acak secara dinamis
        with socketserver.TCPServer(("", 0), Handler) as httpd:
            PORT = httpd.server_address[1] # Dapatkan port yang dialokasikan OS
            logger.info(f"Web Server Lokal aktif di port bebas: {PORT}")
            logger.info(f"Pratinjau dasbor di http://127.0.0.1:{PORT}/docs/index.html")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Gagal menyalakan HTTP Server lokal: {str(e)}")

def run_command(command: str, description: str):
    """Mengeksekusi perintah shell secara sinkron dan menampilkan log."""
    logger.info(f"Memulai: {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Selesai: {description} berhasil!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Gagal saat: {description}")
        logger.error(f"Pesan Kesalahan: {e.stderr.decode('utf-8', errors='ignore')}")
        return False

def main():
    logger.info("=========================================================")
    logger.info("  ORKESTRATOR OTOMATIS DASBOR PANGAN SURABAYA (SERVERLESS) ")
    logger.info("=========================================================")
    
    # 1. Install Dependencies
    logger.info("Meninjau pustaka pendukung (requirements.txt)...")
    if not run_command("pip install -r requirements.txt", "Instalasi dependensi Python"):
        logger.error("Gagal menginstal dependensi. Silakan periksa koneksi internet Anda.")
        sys.exit(1)
        
    # 2. Eksekusi Skrip database_init.sql ke Supabase
    logger.info("Menginisialisasi basis data di Supabase Cloud...")
    if not run_command("python init_db.py", "Eksekusi DDL & Migrasi Supabase"):
        logger.error("Gagal menginisialisasi basis data. Pastikan konfigurasi .env Anda valid.")
        sys.exit(1)
        
    # 3. Jalankan Scraper (Sandbox Mode secara default agar cepat mengisi data)
    logger.info("Menjalankan Scraper Surabaya untuk mengisi data historis sampai hari ini...")
    if not run_command("python -m scraper.main --mock", "Pengisian data tiruan Surabaya & Ekspor JSON"):
        logger.error("Gagal menjalankan scraper pengisi data.")
        sys.exit(1)
        
    # 4. Nyalakan HTTP Server Lokal dan Buka Dasbor di Browser
    logger.info("Mempersiapkan dasbor visual untuk pratinjau...")
    server_thread = threading.Thread(target=start_local_server, daemon=True)
    server_thread.start()
    
    # Tunggu maksimal 5 detik sampai server aktif dan mengalokasikan port
    timeout = 5.0
    start_time = time.time()
    while PORT == 0 and (time.time() - start_time) < timeout:
        time.sleep(0.1)
        
    if PORT == 0:
        logger.error("Gagal mendeteksi server lokal aktif dalam 5 detik. Membuka berkas HTML secara langsung (CORS dapat terblokir)...")
        url = "file://" + os.path.abspath("docs/index.html")
    else:
        url = f"http://127.0.0.1:{PORT}/docs/index.html"
        
    logger.info(f"Membuka Dasbor Pangan Surabaya di browser Anda: {url}")
    webbrowser.open(url)
    
    logger.info("=========================================================")
    logger.info("  SISTEM BERJALAN DENGAN SUKSES! ")
    logger.info("  Tekan Ctrl+C di terminal ini untuk mematikan server lokal.")
    logger.info("=========================================================")
    
    # Jaga agar script tidak langsung mati
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Mematikan server lokal. Sampai jumpa!")
        sys.exit(0)

if __name__ == "__main__":
    main()
