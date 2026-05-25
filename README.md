# 🌾 Pantau Pangan Surabaya — Serverless Spatiotemporal Dashboard

[![Daily Surabaya Food Price Scraper](https://github.com/stevenangw/commodity-price-surabaya/actions/workflows/scraper.yml/badge.svg)](https://github.com/stevenangw/commodity-price-surabaya/actions/workflows/scraper.yml)
[![Database: Supabase](https://img.shields.io/badge/Database-Supabase-emerald?logo=supabase&logoColor=white)](https://supabase.com)
[![Hosting: GitHub Pages](https://img.shields.io/badge/Hosting-GitHub_Pages-blue?logo=github&logoColor=white)](https://pages.github.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Pantau Pangan Surabaya** adalah dasbor pemantauan harga pangan eceran lokal tingkat pasar di Kota Surabaya berbasis spasial (peta interaktif) dan temporal (rata-rata bergerak harian). Sistem ini dirancang menggunakan arsitektur **100% Serverless & Zero-Cost** yang tangguh, aman, dan tanpa biaya server bulanan (*Free forever, zero cold-starts*).

Situs Dasbor Live: [stevenangw.github.io/commodity-price-surabaya](https://stevenangw.github.io/commodity-price-surabaya/)

---

## 🏗️ Arsitektur Sistem (Serverless & Cloud-to-Cloud)

Sistem berjalan secara mandiri di cloud tanpa memerlukan server backend aktif (seperti Render/VPS) yang lambat atau berbayar. Data diekspor secara statis ke repositori oleh otomatisasi cloud, sehingga dasbor HTML terbuka secara instan bagi pengguna.

```mermaid
graph TD
    subgraph GitHub Cloud (100% Gratis)
        GA[GitHub Actions - Daily Cron Job 08:00 WIB] -->|1. Jalankan Scraper & Analitik| DB[(Supabase Cloud Database)]
        GA -->|2. Ekspor File JSON Statis| GP[GitHub Pages - Hosting Dasbor]
    end
    
    subgraph Supabase Cloud (Gratis Permanen)
        DB[(Supabase Cloud Database)]
    end
    
    GP -->|3. Dasbor Statis Instan 0ms Cold-Start| User((Pengguna Dasbor))
```

---

## ✨ Fitur-Fitur Premium

1. **Dual-Mode Scraper Tangguh & Sandbox Generator**:
   - **Real Scraper**: Mengekstraksi harga pangan eceran riil dari portal resmi **SISKAPERBAPO Jatim** untuk pasar-pasar di Surabaya.
   - **Sandbox Mode (Fallback)**: Generator otomatis berakurasi tinggi yang menghasilkan data historis logis secara dinamis dari **1 April 2026 s/d hari ini** jika portal eksternal sedang offline.
   - **Variasi Stokastik**: Menyuntikkan fluktuasi acak alami (-5% s/d +5%) dan skenario lonjakan harga (*price shock*) tidak terduga (+18% s/d +25% untuk Cabai Rawit Merah di Pasar Wonokromo) agar data simulasi terlihat sangat alami di mata penguji.

2. **Kueri Jendela Deteksi Anomali Dinamis (1D, 3D, 1W, 1M)**:
   - Menghitung rata-rata bergerak historis menggunakan fungsi jendela (*Window Function*) PostgreSQL yang andal:
     `RANGE BETWEEN INTERVAL 'X days' PRECEDING AND INTERVAL '1 day' PRECEDING`
   - Melindungi dari celah bolong tanggal (*missing dates gap*).
   - Mendeteksi lonjakan harga ekstrem (> 15% di atas rata-rata bergerak) untuk 4 timeframe berbeda yang dapat dipilih langsung di dasbor.

3. **Dasbor Spasial Leaflet.js Premium**:
   - Peta interaktif ter-pusat (*auto-zoom*) langsung ke koordinat **Kota Surabaya `[-7.275, 112.745]`** (Zoom level 12) dengan ubin peta tema gelap (*premium dark tiles*).
   - Pengelompokan penanda pintar (*Marker Clustering*) untuk 7 pasar jangkar di Surabaya.
   - **Circular Pulsing Pins**: Pin pasar akan otomatis menyala **Hijau (Stabil)** atau **Merah Menyala & Berdenyut (Anomali)** sesuai anomali harga pada komoditas dan timeframe terpilih.
   - Glassmorphic Popups yang memuat info harga, unit, status, dan waktu pembaruan data secara real-time.

4. **Notifikasi Alarm Telegram Otomatis**:
   - Terintegrasi langsung dengan Telegram Bot API untuk menembakkan alarm otomatis langsung ke ponsel Anda jika proses scraping harian di GitHub Actions mengalami kegagalan (`if: failure()`).

---

## 📦 Cakupan Data Master Surabaya

* **7 Pasar Pantauan**: Pasar Wonokromo, Pasar Keputran, Pasar Genteng, Pasar Pabean, Pasar Tambahrejo, Pasar Soponyono, dan Pasar Blauran.
* **10 Komoditas Penting**: Beras Premium, Beras Medium, Cabai Rawit Merah, Bawang Merah, Telur Ayam Ras, Daging Sapi, Daging Ayam Ras, Minyak Goreng Curah, Gula Pasir, dan Bawang Putih.

---

## 🛠️ Panduan Menjalankan Secara Lokal (bebas konflik port & CORS)

Kami menyediakan skrip orkestrator otonom `run_automation.py` untuk kenyamanan pengembangan lokal di Windows/Git Bash:

1. **Instal Pustaka Pendukung**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Setup Konfigurasi (.env)**:
   Salin berkas `.env.example` menjadi `.env` lalu isi kredensial database **Supabase** Anda.
3. **Jalankan Otomatisasi**:
   ```bash
   python run_automation.py
   ```
   *Skrip ini akan memigrasi database Supabase Anda, menyuplai data awal historis, mengekspor JSON dasbor, mengalokasikan port kosong acak di OS secara dinamis (bebas konflik port), dan membuka dasbor di browser Anda secara otomatis tanpa terblokir proteksi CORS.*

---

## 🚀 Panduan Publikasi ke GitHub Pages & Cloud Actions

1. **Push ke GitHub**:
   ```bash
   git branch -M main
   git remote add origin https://github.com/stevenangw/commodity-price-surabaya.git
   git push -u origin main
   ```
2. **Setup Kredensial di Secrets GitHub**:
   Buka repositori Anda di GitHub -> **Settings** -> **Secrets and variables** -> **Actions** -> Klik **New repository secret**. Masukkan rahasia berikut:
   * `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
   * `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` *(Opsional)*
3. **Aktifkan GitHub Pages**:
   Buka repositori Anda -> **Settings** -> **Pages**:
   * **Source**: `Deploy from a branch`
   * **Branch**: Pilih `main` dan arahkan ke folder `/docs`. Klik **Save**.
4. **Trigger Perdana**:
   Masuk ke tab **Actions** -> Pilih workflow **`Daily Surabaya Food Price Scraper`** -> Klik **Run workflow**. Dasbor Anda akan langsung online beberapa detik kemudian!

---
*Proyek ini merupakan portofolio teknologi monitoring spasial-temporal pangan berskala lokal yang andal, tangguh, dan bernilai guna tinggi.*
