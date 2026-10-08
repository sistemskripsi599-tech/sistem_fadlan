# =============================================================================
# modules/telegram_bot.py — Early warning system bot Telegram
# Sesuai proposal (1.5.2 Manfaat Aplikatif + kerangka pikir 2.3):
# notifikasi otomatis saat polutan melewati ambang batas aman kesehatan.
#
# STATUS SAAT INI: kode terpasang tapi BELUM DIHUBUNGKAN ke API Telegram.
#   TELEGRAM_ENABLED = False di config.py → pesan hanya diformat + dicatat ke
#   tabel alert_log (sent_status='disabled'). Tidak ada request HTTP keluar.
# Untuk mengaktifkan: isi TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID, ubah ke True.
#
# Error handling (PRD 17.5): kegagalan API TIDAK boleh membuat sistem crash —
# dicatat ke alert_log dengan sent_status sesuai ('success'/'failed').
# =============================================================================

from datetime import datetime

import requests

import config
from modules import database

# Cooldown per polutan (proposal: anti-spam 30 menit, PRD 14.3)
_last_alert_time = {"pm25": None, "pm10": None}

# Saran tindakan per polutan (PRD 14.4)
_ADVICE = [
    "Kurangi aktivitas fisik di luar ruangan",
    "Gunakan masker saat beraktivitas di luar",
    "Tutup ventilasi sementara bila memungkinkan",
]

_POLLUTANT_LABEL = {"pm25": "PM2.5", "pm10": "PM10"}


# ---------------------------------------------------------------------------
# COOLDOWN (PRD 14.3 — logika cooldown 30 menit per polutan)
# ---------------------------------------------------------------------------

def should_send_alert(pollutant, now=None):
    """True jika sudah lewat ALERT_COOLDOWN_MINUTES sejak alert terakhir."""
    last = _last_alert_time.get(pollutant)
    if last is None:
        return True
    elapsed_min = (now or datetime.now()) - last
    return elapsed_min.total_seconds() >= config.ALERT_COOLDOWN_MINUTES * 60


# ---------------------------------------------------------------------------
# FORMAT PESAN (PRD 14.4 + permintaan: tampilkan persentase terhadap ambang)
# ---------------------------------------------------------------------------

def format_message(pollutant, value, threshold):
    """Susun pesan peringatan: parameter, nilai, ambang, % , status, saran."""
    label = _POLLUTANT_LABEL.get(pollutant, pollutant.upper())
    percent = (value / threshold * 100.0) if threshold else 0.0
    now = datetime.now()
    waktu = now.strftime("%A, %d %b %Y — %H:%M")
    status = _status_label(value, threshold)

    lines = [
        "⚠️ PERINGATAN KUALITAS UDARA — sistem_fadlan",
        "",
        f"🌫️ Parameter   : {label}",
        f"📊 Nilai       : {value:.1f} μg/m³",
        f"⚠️ Ambang Batas: {threshold:.1f} μg/m³ (PP No. 22/2021)",
        f"📈 Persentase  : {percent:.0f}% dari ambang aman",
        f"🔴 Status      : {status}",
        "",
        f"🕐 Waktu: {waktu}",
        "",
        "⚕️ Saran Tindakan:",
    ]
    lines.extend(f"• {a}" for a in _ADVICE)
    lines.append("")
    lines.append("— sistem_fadlan 🌿")
    return "\n".join(lines)


def _status_label(value, threshold):
    """Label status singkat untuk pesan (bukan kategori ISPU penuh)."""
    pct = (value / threshold * 100.0) if threshold else 0.0
    if pct >= 150:
        return "BERBAHAYA"
    if pct >= 100:
        return "TIDAK SEHAT"
    return "PERHATIAN"


# ---------------------------------------------------------------------------
# PENGIRIMAN (kondisional — jangan crash, PRD 17.5)
# ---------------------------------------------------------------------------

def send_alert(pollutant, value, threshold):
    """Kirim alert untuk 1 polutan. Return (sent_status, message).

    sent_status:
      'disabled' → Telegram belum diaktifkan; pesan hanya dicatat
      'no_token' → enabled tapi konfigurasi belum lengkap
      'success'  → pesan terkirim ke API Telegram
      'failed'   → enabled tapi API gagal (network/HTTP error)
    """
    # 1. Cooldown dicek dulu — hemat dan anti-spam
    if not should_send_alert(pollutant):
        return "cooldown", None

    message = format_message(pollutant, value, threshold)
    _last_alert_time[pollutant] = datetime.now()

    # 2. Mode disabled: catat saja (pilihannya eksplisit, bukan exception)
    if not config.TELEGRAM_ENABLED:
        return "disabled", message

    # 3. Enabled tapi konfigurasi belum lengkap
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[telegram] enabled tapi token/chat_id kosong — alert dicatat saja")
        return "no_token", message

    # 4. Kirim ke API Telegram (PRD 14.1)
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
    }
    try:
        resp = requests.post(url, json=payload, timeout=config.TELEGRAM_TIMEOUT_S)
        if resp.status_code == 200:
            return "success", message
        if resp.status_code == 401:
            print("[telegram] Token bot tidak valid (HTTP 401) — cek config.py")
        elif resp.status_code == 400:
            print("[telegram] chat_id tidak valid (HTTP 400) — cek config.py")
        else:
            print(f"[telegram] API Telegram HTTP {resp.status_code}")
        return "failed", message
    except requests.RequestException as exc:
        # API tidak bisa diakses: log, catat gagal, sistem jalan terus (PRD 17.5)
        print(f"[telegram] Gagal mengirim: {exc}")
        return "failed", message


# ---------------------------------------------------------------------------
# INTEGRASI THRESHOLD CHECK (dipanggil dari mqtt_listener.check_threshold)
# ---------------------------------------------------------------------------

def check_and_notify(data):
    """Cek PM2.5 & PM10 → kirim/catat alert bila melewati ambang (PRD 14.3).

    Selalu wrap database.log_alert agar kegagalan DB tidak menjatuhkan caller.
    """
    pollutants = {
        "pm25": (data.get("pm25"), config.THRESHOLD_PM25),
        "pm10": (data.get("pm10"), config.THRESHOLD_PM10),
    }
    for pollutant, (value, threshold) in pollutants.items():
        if value is None or value <= threshold:
            continue
        try:
            sent_status, message = send_alert(pollutant, value, threshold)
        except Exception as exc:
            print(f"[telegram] Error tak terduga pada {pollutant}: {exc}")
            sent_status, message = "failed", None
        try:
            database.log_alert(pollutant, value, threshold, message,
                               sent_status=sent_status)
        except Exception as exc:
            print(f"[telegram] Gagal mencatat alert_log: {exc}")
        print(f"[alert] {pollutant.upper()} {value:.1f} > {threshold:.1f} "
              f"({(value / threshold * 100):.0f}%) — sent_status={sent_status}")
