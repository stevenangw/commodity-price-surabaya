import os
import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger("scraper.telegram_alerter")

# Configuration (Dapat disuplai via environment variables)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_message(message: str) -> bool:
    """
    Mengirim pesan teks terformat HTML ke chat/channel Telegram target.
    
    Args:
        message: Konten pesan dalam format string HTML.
        
    Returns:
        True jika berhasil, False jika gagal.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram Bot Token atau Chat ID tidak terkonfigurasi. Pengiriman notifikasi dibatalkan.")
        return False

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(api_url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Notifikasi Telegram berhasil dikirim!")
            return True
        else:
            logger.error(f"Gagal mengirim notifikasi Telegram. Status Code: {response.status_code}, Respon: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Kesalahan jaringan saat mengirim pesan Telegram: {str(e)}")
        return False


def format_and_send_anomalies_alert(anomalies: List[Dict[str, Any]], target_date: str) -> bool:
    """
    Memformat daftar data anomali harga pangan menjadi pesan alarm HTML yang estetik dan mengirimkannya.
    """
    if not anomalies:
        logger.info("Tidak ada anomali lonjakan harga terdeteksi hari ini. Notifikasi alarm dilewati.")
        # Kirim laporan harian biasa
        report_msg = (
            f"✅ <b>LAPORAN HARIAN KOMODITAS PANGAN</b>\n"
            f"📅 Tanggal: {target_date}\n\n"
            f"Semua harga pangan pokok nasional terpantau <b>STABIL & AMAN</b> hari ini. "
            f"Tidak ditemukan adanya lonjakan harga anomali (> 15%) di pasar tradisional/modern di Indonesia."
        )
        return send_telegram_message(report_msg)

    # Header pesan dengan ornamen visual/emoji menarik
    msg_header = (
        f"🚨 <b>PERINGATAN LONJAKAN HARGA ANOMALI!</b> 🚨\n"
        f"📅 Tanggal Analisis: <b>{target_date}</b>\n"
        f"⚠️ Terdeteksi <b>{len(anomalies)} pasar</b> dengan lonjakan harga pangan > 15% dibandingkan rata-rata 7 hari terakhir:\n\n"
    )

    items_msg = []
    # Ambil maksimal 10 anomali tertinggi untuk membatasi panjang pesan Telegram
    for idx, item in enumerate(anomalies[:10]):
        market_name = item.get("market_name", "Pasar")
        commodity_name = item.get("commodity_name", "Komoditas")
        current_price = item.get("current_price", 0)
        avg_price_7d = item.get("avg_price_7d", 0)
        increase_pct = item.get("price_increase_pct", 0)
        
        # Format harga rupiah
        curr_price_str = f"Rp {int(current_price):,}".replace(",", ".")
        avg_price_str = f"Rp {int(avg_price_7d):,}".replace(",", ".")
        
        item_text = (
            f"{idx + 1}. 📌 <b>{commodity_name}</b>\n"
            f"   🏢 Tempat: <b>{market_name}</b>\n"
            f"   📈 Harga Hari Ini: <b>{curr_price_str}</b>\n"
            f"   📉 Rata-rata 7 Hari: {avg_price_str}\n"
            f"   ⚠️ Kenaikan: <b style='color:#ef4444;'>+{increase_pct:.2f}%</b> (Shock Price!)\n"
        )
        items_msg.append(item_text)

    msg_footer = "\n🔔 <i>Segera lakukan langkah intervensi pasar / operasi pasar di wilayah terdampak!</i>"
    
    full_message = msg_header + "\n".join(items_msg) + msg_msg_if_truncated(anomalies) + msg_footer
    return send_telegram_message(full_message)

def msg_msg_if_truncated(anomalies: List[Dict[str, Any]]) -> str:
    """Mengembalikan teks tambahan jika data anomali dipotong untuk keterbatasan panjang chat."""
    if len(anomalies) > 10:
        return f"\n...dan <b>{len(anomalies) - 10} anomali lainnya</b> telah dicatat pada sistem."
    return ""
