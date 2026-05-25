import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from loguru import logger

from server.config import HOST, PORT, CORS_ORIGINS
from server.limiter import limiter
from server.routes.prices import router as prices_router

# =====================================================================
# Inisialisasi Aplikasi FastAPI
# =====================================================================
app = FastAPI(
    title="Sistem Pemantauan Harga Pangan Lokal Indonesia - API Server",
    description="REST API asinkron berkinerja tinggi untuk dashboard spasial-temporal dan bot alerting.",
    version="1.0.0"
)

# Integrasikan slowapi limiter ke state aplikasi
app.state.limiter = limiter

# =====================================================================
# Konfigurasi Event Startup & Shutdown
# =====================================================================

@app.on_event("startup")
async def startup_event():
    """Inisialisasi komponen backend asinkron saat server menyala."""
    # Inisialisasi fastapi-cache2 dengan backend In-Memory lokal
    # Tidak memerlukan Redis, menjaga kompleksitas infrastruktur awal tetap rendah
    FastAPICache.init(InMemoryBackend(), prefix="pangan-cache")
    logger.info("=== FASTAPI SERVER BERHASIL MEMULAI STARTUP ===")
    logger.info("In-Memory Cache (fastapi-cache2) berhasil diaktifkan.")


# =====================================================================
# Registrasi Middleware & Exception Handlers
# =====================================================================

# 1. CORS Middleware (Keamanan lintas origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Custom Handler untuk Rate Limiting Exceeded (Tanggapan HTTP 429 Terstandar)
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Mengembalikan respon JSON yang ramah kepada klien saat ter-rate limit."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Too Many Requests",
            "detail": f"Batas permintaan terlampaui. Maksimal 60 request per menit per alamat IP.",
            "retry_after_seconds": 60
        }
    )


# =====================================================================
# Registrasi Rute/Routers
# =====================================================================
app.include_router(prices_router)


# =====================================================================
# Root Endpoint (Frontend Dashboard & Health Check)
# =====================================================================
@app.get("/", response_class=HTMLResponse, tags=["Frontend Dashboard"])
async def root_dashboard():
    """Menyajikan halaman utama dashboard spasial interaktif Pantau Pangan."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(template_path):
        return HTMLResponse(
            "<h3>Berkas templates/index.html tidak ditemukan pada direktori server.</h3>", 
            status_code=status.HTTP_404_NOT_FOUND
        )
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Endpoint pengecekan kesehatan server."""
    return {
        "status": "online",
        "service": "commodity-price-monitor-api",
        "engine": "FastAPI Async",
        "rate_limiting": "active"
    }


if __name__ == "__main__":
    # Menjalankan server asinkron Uvicorn secara CLI jika berkas dijalankan langsung
    uvicorn.run(
        "server.main:app",
        host=HOST,
        port=PORT,
        reload=True
    )
