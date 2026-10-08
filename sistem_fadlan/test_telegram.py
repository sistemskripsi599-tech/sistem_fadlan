# =============================================================================
# test_telegram.py — Script percobaan kirim data ke Telegram
# Menguji koneksi dan pengiriman pesan ke bot Telegram secara langsung
# =============================================================================

import sys
import requests
from datetime import datetime

# Tambah path project agar bisa import config
sys.path.insert(0, ".")
import config

def test_kirim_pesan_sederhana():
    """Test 1: Kirim pesan teks biasa."""
    print("\n[TEST 1] Kirim pesan sederhana...")
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": (
            "🧪 *TEST KONEKSI — sistem_fadlan*\n\n"
            f"✅ Sistem berhasil terhubung ke Telegram!\n"
            f"🕐 Waktu: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}\n\n"
            "— Tes dari script `test_telegram.py`"
        ),
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=config.TELEGRAM_TIMEOUT_S)
        if resp.status_code == 200:
            print("  ✅ Berhasil! Pesan terkirim.")
            return True
        else:
            print(f"  ❌ Gagal — HTTP {resp.status_code}: {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"  ❌ Error koneksi: {e}")
        return False


def test_kirim_data_sensor():
    """Test 2: Kirim contoh data sensor (simulasi data dari ESP32)."""
    print("\n[TEST 2] Kirim data sensor simulasi...")

    # Data contoh seperti yang dikirim ESP32
    data_sensor = {
        "timestamp": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
        "pm25": 42.5,
        "pm10": 68.3,
        "gas_mq135": 0.72,
        "suhu": 31.4,
        "kelembaban": 78.2,
        "node": "node01"
    }

    pesan = (
        "📡 *DATA SENSOR — sistem_fadlan*\n\n"
        f"🕐 Waktu     : `{data_sensor['timestamp']}`\n"
        f"🌫️ PM2.5     : `{data_sensor['pm25']} μg/m³`\n"
        f"🌫️ PM10      : `{data_sensor['pm10']} μg/m³`\n"
        f"💨 Gas MQ-135: `{data_sensor['gas_mq135']:.2f} V`\n"
        f"🌡️ Suhu      : `{data_sensor['suhu']} °C`\n"
        f"💧 Kelembaban : `{data_sensor['kelembaban']} %`\n"
        f"📍 Node      : `{data_sensor['node']}`\n\n"
        "— sistem\\_fadlan 🌿"
    )

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": pesan,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=config.TELEGRAM_TIMEOUT_S)
        if resp.status_code == 200:
            print("  ✅ Berhasil! Data sensor terkirim.")
            return True
        else:
            print(f"  ❌ Gagal — HTTP {resp.status_code}: {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"  ❌ Error koneksi: {e}")
        return False


def test_kirim_alert_polutan():
    """Test 3: Kirim alert peringatan polutan (simulasi nilai melebihi ambang)."""
    print("\n[TEST 3] Kirim alert polutan (simulasi PM2.5 melebihi ambang)...")

    # Import modul telegram_bot yang sudah ada
    from modules.telegram_bot import format_message, send_alert

    # Simulasi: PM2.5 = 85 μg/m³ (melebihi threshold 55 μg/m³)
    pm25_value = 85.0
    threshold  = config.THRESHOLD_PM25

    pesan = format_message("pm25", pm25_value, threshold)
    print(f"\n  Isi pesan yang akan dikirim:\n{'─'*50}")
    print(pesan)
    print('─'*50)

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": pesan,
    }
    try:
        resp = requests.post(url, json=payload, timeout=config.TELEGRAM_TIMEOUT_S)
        if resp.status_code == 200:
            print("  ✅ Berhasil! Alert polutan terkirim.")
            return True
        else:
            print(f"  ❌ Gagal — HTTP {resp.status_code}: {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"  ❌ Error koneksi: {e}")
        return False


def cek_info_bot():
    """Cek info bot Telegram (getMe) untuk validasi token."""
    print("\n[INFO] Mengecek info bot...")
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe"
    try:
        resp = requests.get(url, timeout=config.TELEGRAM_TIMEOUT_S)
        if resp.status_code == 200:
            data = resp.json()
            bot = data.get("result", {})
            print(f"  ✅ Bot valid!")
            print(f"     Nama    : {bot.get('first_name')}")
            print(f"     Username: @{bot.get('username')}")
            print(f"     ID      : {bot.get('id')}")
            return True
        else:
            print(f"  ❌ Token tidak valid — HTTP {resp.status_code}: {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"  ❌ Error koneksi: {e}")
        return False


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  PERCOBAAN KIRIM DATA KE TELEGRAM — sistem_fadlan")
    print("=" * 60)
    print(f"  Bot Token : ...{config.TELEGRAM_BOT_TOKEN[-10:]}")
    print(f"  Chat ID   : {config.TELEGRAM_CHAT_ID}")
    print(f"  Enabled   : {config.TELEGRAM_ENABLED}")

    # Cek info bot dulu
    bot_ok = cek_info_bot()

    if not bot_ok:
        print("\n⛔ Token bot tidak valid. Cek TELEGRAM_BOT_TOKEN di config.py")
        sys.exit(1)

    # Jalankan semua test
    hasil = {
        "Pesan Sederhana": test_kirim_pesan_sederhana(),
        "Data Sensor"    : test_kirim_data_sensor(),
        "Alert Polutan"  : test_kirim_alert_polutan(),
    }

    # Ringkasan
    print("\n" + "=" * 60)
    print("  RINGKASAN HASIL TEST")
    print("=" * 60)
    semua_berhasil = True
    for nama, ok in hasil.items():
        status = "✅ BERHASIL" if ok else "❌ GAGAL"
        print(f"  {status}  — {nama}")
        if not ok:
            semua_berhasil = False

    print()
    if semua_berhasil:
        print("  🎉 Semua test berhasil! Telegram siap digunakan.")
    else:
        print("  ⚠️  Ada test yang gagal. Cek koneksi internet atau config.")
    print("=" * 60)
