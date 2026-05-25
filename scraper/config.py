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

# Token Rahasia Internal untuk Cache Invalidation
INTERNAL_TOKEN = os.getenv("X_INTERNAL_TOKEN", "super-secret-internal-token-2026")
API_SERVER_URL = os.getenv("API_SERVER_URL", "http://localhost:8080")

# Telegram Bot Alerting Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Proxies list (for future rotation if needed)
PROXIES = []
