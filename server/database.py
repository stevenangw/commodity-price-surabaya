from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from server.config import DATABASE_URL

# Declarative base untuk model SQLAlchemy
Base = declarative_base()

# Async Engine dengan connection pool kecil dioptimalkan untuk mesin lokal (Lenovo S145)
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,           # Diperkecil dari 20 menjadi 5 koneksi
    max_overflow=2,        # Diperkecil dari 10 menjadi 2 koneksi tambahan
    pool_recycle=1800,     # Reset koneksi setiap 30 menit
    pool_pre_ping=True     # Validasi koneksi sebelum query dijalankan
)

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db_session():
    """
    Dependency generator untuk menyuntikkan (inject) database session ke endpoint FastAPI.
    Menjamin pembersihan session (cleanup) yang aman setelah request selesai.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
