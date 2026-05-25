from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_cache.decorator import cache
from fastapi_cache import FastAPICache
from pydantic import BaseModel

from server.database import get_db_session
from server.models import PriceHistory, Market, Commodity
from server.limiter import limiter
from server.config import INTERNAL_TOKEN

router = APIRouter()

# =====================================================================
# Pydantic Response Schemas
# =====================================================================

class PriceHeatmapRecord(BaseModel):
    market_id: int
    market_name: str
    market_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: float
    price_date: date
    unit: str

class LatestPriceResponse(BaseModel):
    commodity_id: int
    commodity_name: str
    target_date: date
    records: List[PriceHeatmapRecord]

class PriceAnomalyRecord(BaseModel):
    market_id: int
    market_name: str
    market_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    commodity_id: int
    commodity_name: str
    price_date: date
    current_price: float
    avg_price_7d: float
    price_increase_pct: float

class PriceAnomaliesResponse(BaseModel):
    target_date: date
    anomalies: List[PriceAnomalyRecord]

class GeneralMessageResponse(BaseModel):
    message: str


# =====================================================================
# Security Dependency untuk Rute Internal
# =====================================================================

async def verify_internal_token(x_internal_token: str = Header(..., alias="X-Internal-Token")):
    """Memverifikasi token statis internal untuk rute khusus scraper."""
    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akses Ditolak: Token internal tidak valid."
        )


# =====================================================================
# REST API Endpoints (Asinkronus & Optimized)
# =====================================================================

@router.get(
    "/api/v1/prices/latest",
    response_model=LatestPriceResponse,
    summary="Mengambil harga terbaru untuk peta heatmap Leaflet.js"
)
@limiter.limit("60/minute")  # IP-based rate limit: 60 requests per minute
@cache(expire=86400)         # Cache hasil query selama 24 jam (in-memory)
async def get_latest_prices(
    request: Request,  # Wajib ada agar slowapi limiter bekerja
    commodity_id: int = Query(..., description="ID komoditas pangan pokok"),
    price_date: Optional[date] = Query(None, description="Tanggal filter harga (opsional)"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Mengambil data harga pangan pokok terkini per pasar di Indonesia.
    Dioptimalkan menggunakan index komposit B-Tree (commodity_id, price_date).
    """
    # 1. Ambil Nama Komoditas & Satuan
    commodity_stmt = select(Commodity).where(Commodity.id == commodity_id)
    commodity_res = (await session.execute(commodity_stmt)).scalar_one_or_none()
    if not commodity_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Komoditas dengan ID {commodity_id} tidak ditemukan."
        )

    # 2. Jika tanggal tidak dispesifikasikan, cari tanggal terbaru yang tersedia untuk komoditas ini
    target_date = price_date
    if not target_date:
        # Query cepat menggunakan index komposit
        max_date_stmt = select(func.max(PriceHistory.price_date)).where(PriceHistory.commodity_id == commodity_id)
        target_date = (await session.execute(max_date_stmt)).scalar()
        
    if not target_date:
        # Jika tidak ada data harga sama sekali di database
        return LatestPriceResponse(
            commodity_id=commodity_id,
            commodity_name=commodity_res.name,
            target_date=date.today(),
            records=[]
        )

    # 3. Jalankan query agregat detail pasar dengan gabungan join lokasi (Latitude/Longitude)
    # Sangat ter-optimasi menggunakan index B-Tree (commodity_id, price_date)
    query_stmt = (
        select(
            PriceHistory.market_id,
            PriceHistory.price,
            PriceHistory.price_date,
            Market.name.label("market_name"),
            Market.market_type,
            Market.latitude,
            Market.longitude
        )
        .join(Market, PriceHistory.market_id == Market.id)
        .where(
            PriceHistory.commodity_id == commodity_id,
            PriceHistory.price_date == target_date
        )
    )
    
    query_result = await session.execute(query_stmt)
    records = query_result.all()

    # 4. Bungkus ke dalam skema respons standar
    heatmap_records = [
        PriceHeatmapRecord(
            market_id=row.market_id,
            market_name=row.market_name,
            market_type=row.market_type,
            latitude=float(row.latitude) if row.latitude else None,
            longitude=float(row.longitude) if row.longitude else None,
            price=float(row.price),
            price_date=row.price_date,
            unit=commodity_res.unit
        )
        for row in records
    ]

    return LatestPriceResponse(
        commodity_id=commodity_id,
        commodity_name=commodity_res.name,
        target_date=target_date,
        records=heatmap_records
    )


@router.get(
    "/api/v1/prices/anomalies",
    response_model=PriceAnomaliesResponse,
    summary="Mendeteksi anomali lonjakan harga pangan > 15% dibanding rata-rata 7 hari terakhir"
)
@limiter.limit("30/minute")  # IP-based rate limit
@cache(expire=3600)          # Cache hasil anomali selama 1 jam
async def get_price_anomalies(
    request: Request,
    price_date: Optional[date] = Query(None, description="Tanggal pengecekan anomali"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Mendeteksi lonjakan harga ekstrem (> 15%) dibandingkan dengan rata-rata bergerak 7 hari terakhir.
    Query dioptimalkan secara spasial-temporal untuk laptop Lenovo S145 dengan membatasi rentang subquery.
    """
    # 1. Tentukan tanggal target
    target_date = price_date
    if not target_date:
        max_date_stmt = select(func.max(PriceHistory.price_date))
        target_date = (await session.execute(max_date_stmt)).scalar()

    if not target_date:
        return PriceAnomaliesResponse(target_date=date.today(), anomalies=[])

    # 2. Batasi irisan data ke 8 hari ke belakang untuk efisiensi RAM/CPU ekstrim pada Lenovo S145
    start_date = target_date - timedelta(days=8)

    # 3. Jalankan Window Function ter-optimasi secara asinkron
    sql_query = text("""
        WITH price_slice AS (
            SELECT market_id, commodity_id, price_date, price, source_url
            FROM price_history
            WHERE price_date BETWEEN :start_date AND :target_date
        ),
        price_averages AS (
            SELECT 
                market_id,
                commodity_id,
                price_date,
                price,
                source_url,
                AVG(price) OVER (
                    PARTITION BY market_id, commodity_id 
                    ORDER BY price_date 
                    RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW
                ) as avg_price_7d
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
            pa.avg_price_7d,
            ((pa.price - pa.avg_price_7d) / pa.avg_price_7d) * 100 as price_increase_pct
        FROM price_averages pa
        JOIN markets m ON pa.market_id = m.id
        JOIN commodities c ON pa.commodity_id = c.id
        WHERE pa.price_date = :target_date
          AND pa.avg_price_7d IS NOT NULL
          AND pa.avg_price_7d > 0
          AND pa.price > (pa.avg_price_7d * 1.15)
        ORDER BY price_increase_pct DESC;
    """)

    result = await session.execute(sql_query, {"start_date": start_date, "target_date": target_date})
    rows = result.all()

    anomaly_records = [
        PriceAnomalyRecord(
            market_id=row.market_id,
            market_name=row.market_name,
            market_type=row.market_type,
            latitude=float(row.latitude) if row.latitude else None,
            longitude=float(row.longitude) if row.longitude else None,
            commodity_id=row.commodity_id,
            commodity_name=row.commodity_name,
            price_date=row.price_date,
            current_price=float(row.current_price),
            avg_price_7d=float(row.avg_price_7d),
            price_increase_pct=float(row.price_increase_pct)
        )
        for row in rows
    ]

    return PriceAnomaliesResponse(target_date=target_date, anomalies=anomaly_records)


# =====================================================================
# Internal API Endpoints (Cache Invalidation)
# =====================================================================

@router.post(
    "/api/v1/internal/cache/clear",
    response_model=GeneralMessageResponse,
    summary="Mengosongkan (invalidasi) cache in-memory secara manual",
    dependencies=[Depends(verify_internal_token)]
)
async def clear_system_cache():
    """
    Rute internal tertutup untuk mengosongkan cache in-memory sistem.
    Dipicu oleh Scraper (main.py) sesaat setelah batch upsert selesai.
    """
    try:
        await FastAPICache.clear()
        return GeneralMessageResponse(message="Seluruh cache in-memory berhasil dibersihkan.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal membersihkan cache: {str(e)}"
        )
