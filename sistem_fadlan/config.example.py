# =============================================================================
# config.example.py — Template konfigurasi sistem_fadlan
# Salin file ini menjadi config.py lalu sesuaikan nilainya.
# config.py TIDAK di-commit (lihat .gitignore, PRD Section 18).
# =============================================================================

import os

# -----------------------------------------------------------------------------
# BASE DIRECTORY
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------------------------------------------
# FLASK
# -----------------------------------------------------------------------------
FLASK_HOST  = "0.0.0.0"
FLASK_PORT  = 5000
FLASK_DEBUG = False   # Matikan (False) saat deployment lapangan

# -----------------------------------------------------------------------------
# DATABASE SQLite
# (Catatan skripsi: proposal Bab II menyebut MySQL; SQLite dipilih karena
#  skala data penelitian kecil, tanpa server terpisah — konfirmasi pembimbing)
# -----------------------------------------------------------------------------
DB_PATH = os.path.join(BASE_DIR, "database", "sistem_fadlan.db")

# -----------------------------------------------------------------------------
# MQTT BROKER (Mosquitto — localhost)
# -----------------------------------------------------------------------------
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC       = "air_quality/node01"
MQTT_CLIENT_ID   = "flask_subscriber"

# -----------------------------------------------------------------------------
# THRESHOLD KUALITAS UDARA (PP No. 22 Tahun 2021 — baku mutu nasional,
# berlaku juga untuk Kota Palu; tidak ada baku mutu lokal)
# -----------------------------------------------------------------------------
THRESHOLD_PM25 = 55.0   # μg/m³ (24 jam)
THRESHOLD_PM10 = 75.0   # μg/m³ (24 jam)
# Gas MQ-135: monitoring saja, tidak trigger alert

# -----------------------------------------------------------------------------
# ALERT COOLDOWN
# -----------------------------------------------------------------------------
ALERT_COOLDOWN_MINUTES = 30   # menit antar notifikasi per polutan

# -----------------------------------------------------------------------------
# TELEGRAM EARLY WARNING (proposal 1.5.2 / kerangka pikir 2.3)
# Kode terpasang tapi BELUM dihubungkan: TELEGRAM_ENABLED = False.
# Isi token + chat id lalu ubah ke True saat siap diuji ke Telegram asli.
# -----------------------------------------------------------------------------
TELEGRAM_ENABLED   = False
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID   = ""
TELEGRAM_TIMEOUT_S = 10

# -----------------------------------------------------------------------------
# MACHINE LEARNING
# -----------------------------------------------------------------------------
N_LAGS       = 12
N_ESTIMATORS = 100
RANDOM_STATE = 42

MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR   = os.path.join(BASE_DIR, "data")

# File data latih. Tulis nama file ASLI di sini (contoh: ISPU_DKI_Jakarta_2021.csv
# dari satudata.jakarta.go.id). Kalau tidak ada, sistem memakai CONTOH buatan.
CSV_FILE   = os.path.join(DATA_DIR, "CONTOH_data_latihan_buatan.csv")

# -----------------------------------------------------------------------------
# SENSOR NODE
# -----------------------------------------------------------------------------
SENSOR_INTERVAL_SECONDS = 30   # interval kirim data dari ESP32

# -----------------------------------------------------------------------------
# MODE DATA: "simulasi" (data buatan berlabel, butuh izin pembimbing) | "lapangan"
# Lihat docs/draft_izin_pembimbing.md untuk aturan pakainya.
# -----------------------------------------------------------------------------
DATA_MODE = "simulasi"
