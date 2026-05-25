from sqlalchemy import Column, String, Integer, Numeric, Date, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from server.database import Base

class Province(Base):
    __tablename__ = "provinces"
    
    id = Column(String(2), primary_key=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    regencies = relationship("Regency", back_populates="province")


class Regency(Base):
    __tablename__ = "regencies"
    
    id = Column(String(4), primary_key=True)
    province_id = Column(String(2), ForeignKey("provinces.id", ondelete="RESTRICT"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # 'Kabupaten' atau 'Kota'
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    province = relationship("Province", back_populates="regencies")
    markets = relationship("Market", back_populates="regency")


class Market(Base):
    __tablename__ = "markets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    regency_id = Column(String(4), ForeignKey("regencies.id", ondelete="RESTRICT"), nullable=False)
    name = Column(String(100), nullable=False)
    market_type = Column(String(50), nullable=False)  # 'Tradisional' atau 'Modern'
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    regency = relationship("Regency", back_populates="markets")
    prices = relationship("PriceHistory", back_populates="market")


class Commodity(Base):
    __tablename__ = "commodities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(50), nullable=False)
    unit = Column(String(20), nullable=False, default="kg")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    prices = relationship("PriceHistory", back_populates="commodity")


class PriceHistory(Base):
    __tablename__ = "price_history"
    
    # Primary Key Komposit sesuai skema tabel berpartisi
    market_id = Column(Integer, ForeignKey("markets.id", ondelete="RESTRICT"), primary_key=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id", ondelete="RESTRICT"), primary_key=True)
    price_date = Column(Date, primary_key=True)
    price = Column(Numeric(12, 2), nullable=False)
    source_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    market = relationship("Market", back_populates="prices")
    commodity = relationship("Commodity", back_populates="prices")
