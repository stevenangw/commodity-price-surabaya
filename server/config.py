import os
from dotenv import load_dotenv

# Muat variabel lingkungan dari berkas .env
load_dotenv()

# Server Configurations
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8080))
CORS_ORIGINS = ["*"]  # Ubah menjadi domain spesifik untuk production

# Database Async URL (asyncpg driver)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/commodity_monitor"
)

# Security Token untuk Internal Endpoint (misal cache invalidation)
INTERNAL_TOKEN = os.getenv("X_INTERNAL_TOKEN", "super-secret-internal-token-2026")
