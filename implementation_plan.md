# Implementation Plan - Serverless Static Surabaya Food Price Dashboard

This is the final approved plan to build a **100% Free, Zero-Server, High-Performance** local food price monitoring system for Surabaya. 

By leveraging **Supabase** (Postgres), **GitHub Actions** (Daily Cron + JSON Generator), and **GitHub Pages** (Static Frontend HTML), we eliminate the need for paid servers (like Render) and avoid cold starts.

```mermaid
graph TD
    subgraph GitHub Cloud (100% Free)
        GA[GitHub Actions - Daily Cron Job]
        GP[GitHub Pages - Docs Folder / index.html]
    end
    subgraph Supabase Cloud (100% Free)
        DB[(Supabase PostgreSQL Database)]
    end
    
    GA -- 1. Scrape Siskaperbapo Jatim daily --> DB
    GA -- 2. Query anomalies & Export static JSON --> GP
    GP -- 3. Fast static load of index.html & JSONs --> User((User Dashboard))
```

---

## Proposed Changes

### 1. Database Schema
#### [MODIFY] [database_init.sql](file:///c:/dev/commodity-price-monitor/database_init.sql)
We will modify the database initialization DDL file to:
- Establish the Surabaya-only master geography (Province ID `'35'` for Jawa Timur, Regency ID `'3578'` for Kota Surabaya).
- **Seed 7 Markets in Surabaya**:
  * **Pasar Wonokromo** (Lat: `-7.3017`, Long: `112.7373`, Type: `'Tradisional'`)
  * **Pasar Keputran** (Lat: `-7.2731`, Long: `112.7441`, Type: `'Tradisional'`)
  * **Pasar Genteng** (Lat: `-7.2575`, Long: `112.7423`, Type: `'Tradisional'`)
  * **Pasar Pabean** (Lat: `-7.2309`, Long: `112.7381`, Type: `'Tradisional'`)
  * **Pasar Tambahrejo** (Lat: `-7.2482`, Long: `112.7594`, Type: `'Tradisional'`)
  * **Pasar Soponyono** (Lat: `-7.3275`, Long: `112.7758`, Type: `'Tradisional'`)
  * **Pasar Blauran** (Lat: `-7.2536`, Long: `112.7346`, Type: `'Tradisional'`)
- **Seed 10 Commodities**:
  1. `Beras Premium`
  2. `Beras Medium`
  3. `Cabai Rawit Merah`
  4. `Bawang Merah`
  5. `Telur Ayam Ras`
  6. `Daging Sapi`
  7. `Daging Ayam Ras`
  8. `Minyak Goreng Curah`
  9. `Gula Pasir`
  10. `Bawang Putih`
- Define the `v_bi_price_history` view and `db_reporter` user.

### 2. Dual-Mode Scraper & Static JSON Exporter
#### [MODIFY] [scraper/main.py](file:///c:/dev/commodity-price-monitor/scraper/main.py)
We will refactor the scraper:
- **SISKAPERBAPO Jatim Scraper**: Target `https://siskaperbapo.jatimprov.go.id/` using BeautifulSoup and Requests to parse real Surabaya market prices.
- **Continuous Mock Generator (Fallback)**: If siskaperbapo is offline/rate-limited or `--mock` is specified, generate synthetic price data starting from **April 1, 2026, up to the current date (`today`)**.
- **Price Shock**: Spikes `Cabai Rawit Merah` at `Pasar Wonokromo` by 20% on `today`.
- **JSON Exporter Function**: After saving prices to Supabase, run calculations for latest prices and active anomalies for all four timeframes (`1D`, `3D`, `1W`, `1M`), then export them to static JSON files in `docs/data/latest_prices.json` and `docs/data/anomalies.json`.

### 3. Serverless Leaflet.js Frontend Dashboard
#### [NEW] [docs/index.html](file:///c:/dev/commodity-price-monitor/docs/index.html)
We will create a beautiful, modern, dark-themed static frontend in the `docs/` folder (standard for GitHub Pages):
- Centered on Surabaya at `[-7.275, 112.745]` (zoom level 12).
- Dropdown selector for all 10 commodities.
- Marker clustering using `leaflet.markercluster` for the 7 markets.
- **Dynamic Timeframe Selector**: Toggle between `1D`, `3D`, `1W`, and `1M` timeframes.
- **Dynamic Anomaly Colors**: Pins are styled in emerald-green (stable) or glowing red (active anomaly) by comparing with the pre-generated static `anomalies.json` for the chosen timeframe.
- Displays key statistics (average, highest, lowest, active anomalies) instantly.

### 4. GitHub Actions Workflow
#### [NEW] [.github/workflows/scraper.yml](file:///c:/dev/commodity-price-monitor/.github/workflows/scraper.yml)
We will create a GitHub Action configuration file:
- Wakes up daily on a Cron schedule (e.g. every day at 01:00 UTC / 08:00 WIB).
- Pulls secrets from GitHub Repository Secrets (`DB_HOST`, `DB_PASSWORD`, etc.).
- Runs the scraper to get real data, updates the Supabase DB, exports static JSON files, and commits the JSONs back to the `docs/data/` folder.
- Triggers GitHub Pages to publish the updated dashboard.

### 5. Supabase-Compatible Root Orchestrator
#### [NEW] [run_automation.py](file:///c:/dev/commodity-price-monitor/run_automation.py)
We will provide a local orchestrator for your Lenovo S145:
1. Detect and install Python dependencies.
2. Initialize and run `init_db.py` to push database schemas directly to **Supabase**.
3. Run the scraper to populate your Supabase DB and generate the initial static JSON files under `docs/data/`.
4. Open the local `docs/index.html` file in your browser to view the beautiful dashboard instantly.

---

## Verification Plan

### Automated/Manual Testing Steps
1. **Initialize System**: Execute `python run_automation.py` in Git Bash.
2. **Verify Database**: Check Supabase to see that 7 markets and 10 commodities are successfully populated with continuous price records.
3. **Verify Static JSONs**: Check that `docs/data/latest_prices.json` and `docs/data/anomalies.json` are successfully generated.
4. **Verify UI**: Open `docs/index.html` in your browser. Verify the centering on Surabaya, test the commodity selection dropdown, and check that toggle timeframes (1D, 3D, 1W, 1M) correctly color the pins.
