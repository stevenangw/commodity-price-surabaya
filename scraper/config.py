import os
from dotenv import load_dotenv

# Muat variabel lingkungan dari berkas .env (pencarian ke atas secara otomatis)
load_dotenv()

# Scraper Configuration
DEFAULT_TIMEOUT = 15  # seconds
BASE_DELAY = 2.0      # seconds

# Target URLs (Bapanas / PIHPS endpoints)
BAPANAS_API_URL = os.getenv("BAPANAS_API_URL", "https://panelharga.badanpangan.go.id/api/harga")
PIHPS_API_URL = os.getenv("PIHPS_API_URL", "https://sehati.kemendag.go.id/api/pihps")

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "commodity_monitor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

# Deteksi Kredensial Database di Lingkungan GitHub Actions
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
DB_CONFIGURED = True
if IS_GITHUB_ACTIONS:
    if not os.getenv("DB_HOST") or os.getenv("DB_HOST") in ("localhost", "127.0.0.1", ""):
        DB_CONFIGURED = False

# Token Rahasia Internal untuk Cache Invalidation
INTERNAL_TOKEN = os.getenv("X_INTERNAL_TOKEN", "super-secret-internal-token-2026")
API_SERVER_URL = os.getenv("API_SERVER_URL", "http://localhost:8080")

# Telegram Bot Alerting Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Proxies list (for future rotation if needed)
PROXIES = []

# =====================================================================
# Master Data Metadata Offline untuk Penyelarasan Serverless
# =====================================================================

OFFLINE_MARKETS = {
    "Pasar Wonokromo": {"id": 1, "market_type": "Tradisional", "latitude": -7.3017, "longitude": 112.7373},
    "Pasar Keputran": {"id": 2, "market_type": "Tradisional", "latitude": -7.2731, "longitude": 112.7441},
    "Pasar Genteng": {"id": 3, "market_type": "Tradisional", "latitude": -7.2575, "longitude": 112.7423},
    "Pasar Pabean": {"id": 4, "market_type": "Tradisional", "latitude": -7.2309, "longitude": 112.7381},
    "Pasar Tambahrejo": {"id": 5, "market_type": "Tradisional", "latitude": -7.2482, "longitude": 112.7594},
    "Pasar Soponyono": {"id": 6, "market_type": "Tradisional", "latitude": -7.3275, "longitude": 112.7758},
    "Pasar Blauran": {"id": 7, "market_type": "Tradisional", "latitude": -7.2536, "longitude": 112.7346}
}

OFFLINE_COMMODITIES = {
    "Beras Premium": {"id": 1, "unit": "kg"},
    "Beras Medium": {"id": 2, "unit": "kg"},
    "Cabai Rawit Merah": {"id": 3, "unit": "kg"},
    "Bawang Merah": {"id": 4, "unit": "kg"},
    "Telur Ayam Ras": {"id": 5, "unit": "kg"},
    "Daging Sapi": {"id": 6, "unit": "kg"},
    "Daging Ayam Ras": {"id": 7, "unit": "kg"},
    "Minyak Goreng Curah": {"id": 8, "unit": "kg"},
    "Gula Pasir": {"id": 9, "unit": "kg"},
    "Bawang Putih": {"id": 10, "unit": "kg"}
}

