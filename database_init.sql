-- =====================================================================
-- SKRIP INISIALISASI BASIS DATA POSTGRESQL (database_init.sql)
-- Proyek: Sistem Pemantauan Harga Pangan Lokal Kota Surabaya (Serverless)
-- Sasaran: Supabase Cloud Database (Resource-Optimized)
-- =====================================================================

-- 1. PEMBUATAN TABEL MASTER DATA GEOGRAFIS & ENTITAS

-- A. Tabel Provinsi (2-digit Kode BPS)
CREATE TABLE IF NOT EXISTS provinces (
    id CHAR(2) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- B. Tabel Kabupaten / Kota (4-digit Kode BPS)
CREATE TABLE IF NOT EXISTS regencies (
    id CHAR(4) PRIMARY KEY,
    province_id CHAR(2) NOT NULL REFERENCES provinces(id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('Kabupaten', 'Kota')),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- C. Tabel Pasar (Market-level Granularity)
CREATE TABLE IF NOT EXISTS markets (
    id SERIAL PRIMARY KEY,
    regency_id CHAR(4) NOT NULL REFERENCES regencies(id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    market_type VARCHAR(50) NOT NULL CHECK (market_type IN ('Tradisional', 'Modern')),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- D. Tabel Komoditas Pangan
CREATE TABLE IF NOT EXISTS commodities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    unit VARCHAR(20) NOT NULL DEFAULT 'kg',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- 2. PEMBUATAN TABEL TRANSAKSI UTAMA BERPARTISI (PARTITIONED TABLE)
CREATE TABLE IF NOT EXISTS price_history (
    market_id INT NOT NULL REFERENCES markets(id) ON DELETE RESTRICT,
    commodity_id INT NOT NULL REFERENCES commodities(id) ON DELETE RESTRICT,
    price_date DATE NOT NULL,
    price NUMERIC(12, 2) NOT NULL, -- Menghindari floating-point error desimal
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (market_id, commodity_id, price_date)
) PARTITION BY RANGE (price_date);


-- 3. PEMBUATAN TABEL PARTISI DEKLARATIF TAHUNAN
CREATE TABLE IF NOT EXISTS price_history_2026 PARTITION OF price_history
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE TABLE IF NOT EXISTS price_history_2027 PARTITION OF price_history
    FOR VALUES FROM ('2027-01-01') TO ('2028-01-01');


-- 4. PEMBUATAN COMPOSITE INDEX OPTIMIZED
CREATE INDEX IF NOT EXISTS idx_price_history_commodity_date 
ON price_history (commodity_id, price_date) 
INCLUDE (price);


-- 5. SEED DATA MASTER SPESIFIK SURABAYA

-- A. Seed Provinsi Jawa Timur (ID: 35)
INSERT INTO provinces (id, name, latitude, longitude)
VALUES ('35', 'Jawa Timur', -7.2575, 112.7521)
ON CONFLICT (id) DO UPDATE SET 
    name = EXCLUDED.name,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude;

-- B. Seed Kota Surabaya (ID: 3578)
INSERT INTO regencies (id, province_id, name, type, latitude, longitude)
VALUES ('3578', '35', 'Kota Surabaya', 'Kota', -7.2575, 112.7521)
ON CONFLICT (id) DO UPDATE SET 
    province_id = EXCLUDED.province_id,
    name = EXCLUDED.name,
    type = EXCLUDED.type,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude;

-- C. Seed 7 Pasar Jangkar Surabaya dengan Koordinat Eksak
INSERT INTO markets (id, regency_id, name, market_type, latitude, longitude)
VALUES 
    (1, '3578', 'Pasar Wonokromo', 'Tradisional', -7.3017, 112.7373),
    (2, '3578', 'Pasar Keputran', 'Tradisional', -7.2731, 112.7441),
    (3, '3578', 'Pasar Genteng', 'Tradisional', -7.2575, 112.7423),
    (4, '3578', 'Pasar Pabean', 'Tradisional', -7.2309, 112.7381),
    (5, '3578', 'Pasar Tambahrejo', 'Tradisional', -7.2482, 112.7594),
    (6, '3578', 'Pasar Soponyono', 'Tradisional', -7.3275, 112.7758),
    (7, '3578', 'Pasar Blauran', 'Tradisional', -7.2536, 112.7346)
ON CONFLICT (id) DO UPDATE SET 
    regency_id = EXCLUDED.regency_id,
    name = EXCLUDED.name,
    market_type = EXCLUDED.market_type,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude;

-- D. Seed 10 Komoditas Standar
INSERT INTO commodities (id, name, category, unit)
VALUES 
    (1, 'Beras Premium', 'Beras', 'kg'),
    (2, 'Beras Medium', 'Beras', 'kg'),
    (3, 'Cabai Rawit Merah', 'Cabai', 'kg'),
    (4, 'Bawang Merah', 'Bawang', 'kg'),
    (5, 'Telur Ayam Ras', 'Telur', 'kg'),
    (6, 'Daging Sapi', 'Daging', 'kg'),
    (7, 'Daging Ayam Ras', 'Daging', 'kg'),
    (8, 'Minyak Goreng Curah', 'Minyak', 'kg'),
    (9, 'Gula Pasir', 'Gula', 'kg'),
    (10, 'Bawang Putih', 'Bawang', 'kg')
ON CONFLICT (id) DO UPDATE SET 
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    unit = EXCLUDED.unit;

-- Reset sequence serial untuk id market dan commodity
SELECT setval(pg_get_serial_sequence('markets', 'id'), COALESCE(MAX(id), 1)) FROM markets;
SELECT setval(pg_get_serial_sequence('commodities', 'id'), COALESCE(MAX(id), 1)) FROM commodities;


-- 6. PEMBUATAN VIEW SPASIAL-TEMPORAL UNTUK BUSINESS INTELLIGENCE
CREATE OR REPLACE VIEW v_bi_price_history AS
SELECT 
    ph.price_date,
    p.id AS province_id,
    p.name AS province_name,
    r.id AS regency_id,
    r.name AS regency_name,
    r.type AS regency_type,
    m.id AS market_id,
    m.name AS market_name,
    m.market_type,
    m.latitude AS market_latitude,
    m.longitude AS market_longitude,
    c.id AS commodity_id,
    c.name AS commodity_name,
    c.category AS commodity_category,
    c.unit AS commodity_unit,
    ph.price,
    ph.source_url
FROM price_history ph
JOIN markets m ON ph.market_id = m.id
JOIN regencies r ON m.regency_id = r.id
JOIN provinces p ON r.province_id = p.id
JOIN commodities c ON ph.commodity_id = c.id;


-- 7. PENGAMANAN & AKSES USER LEAST PRIVILEGE (db_reporter)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'db_reporter') THEN
        CREATE ROLE db_reporter WITH LOGIN PASSWORD 'ReporterPanganSecure2026!';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE postgres TO db_reporter;
GRANT USAGE ON SCHEMA public TO db_reporter;

-- Cabut seluruh hak akses tabel default demi keamanan
ALTER DEFAULT PRIVILEGES REVOKE ALL ON TABLES FROM db_reporter;

-- Berikan akses SELECT HANYA pada VIEW BI yang denormalisasi
GRANT SELECT ON v_bi_price_history TO db_reporter;
