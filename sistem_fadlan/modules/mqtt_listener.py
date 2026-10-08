# =============================================================================
# modules/mqtt_listener.py — Paho-MQTT daemon thread
# Terima data sensor ESP32 → validasi (PRD 17.1) → simpan → threshold check
# (PRD Section 9.2 / 13)
# =============================================================================

import json
import threading
from datetime import datetime

import config

# Import paho-mqtt dengan fallback nama (paho-mqtt v1 dan v2)
try:    # paho-mqtt >= 2.0
    from paho.mqtt.client import Client, CallbackAPIVersion
    _PAHO_V2 = True
except ImportError:  # paho-mqtt 1.x
    from paho.mqtt.client import Client
    _PAHO_V2 = False

from modules import database


def check_threshold(data):
    """Threshold check PM2.5/PM10 (proposal: early warning, PRD 14).

    Didelegasikan ke modules/telegram_bot.check_and_notify:
    - Format pesan peringatan (parameter, nilai, ambang, persentase, saran)
    - Cooldown 30 menit per polutan (anti-spam)
    - Pengiriman Telegram kondisional (TELEGRAM_ENABLED=False → catat saja)
    - Setiap pelanggaran tetap tercatat di tabel alert_log
    """
    from modules import telegram_bot
    telegram_bot.check_and_notify(data)

# ---------------------------------------------------------------------------
# STATE (dibaca /api/status)
# ---------------------------------------------------------------------------

_state = {
    "connected": False,
    "last_message_at": None,
}


def is_connected():
    return _state["connected"]


# ---------------------------------------------------------------------------
# VALIDASI PAYLOAD (PRD Section 17.1)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ("pm25", "pm10", "gas_raw", "temperature", "humidity", "pressure")
# PM1.0 opsional (firmware lama belum mengirim) — monitoring saja (Batasan 1.3)
OPTIONAL_NUMERIC_FIELDS = ("pm1_0",)


def validate_payload(payload):
    """Validasi field wajib + tipe + rentang fisik. Return dict bersih atau None."""
    if not isinstance(payload, dict):
        print("[mqtt] Payload bukan JSON object — skip")
        return None

    for field in REQUIRED_FIELDS:
        if field not in payload:
            print(f"[mqtt] Field wajib hilang: {field} — skip")
            return None

    try:
        data = {
            "pm25":        float(payload["pm25"]),
            "pm10":        float(payload["pm10"]),
            "gas_raw":     int(payload["gas_raw"]),
            "temperature": float(payload["temperature"]),
            "humidity":    float(payload["humidity"]),
            "pressure":    float(payload["pressure"]),
        }
    except (TypeError, ValueError):
        print("[mqtt] Tipe data tidak valid — skip")
        return None

    # PM1.0 opsional: validasi bila ada, monitoring saja (bukan fitur prediksi)
    pm1 = payload.get("pm1_0")
    if pm1 is None:
        data["pm1_0"] = None
    else:
        try:
            pm1 = float(pm1)
            if 0 <= pm1 <= 1000:
                data["pm1_0"] = pm1
            else:
                print(f"[mqtt] pm1_0 di luar rentang 0-1000: {pm1} — disimpan NULL")
                data["pm1_0"] = None
        except (TypeError, ValueError):
            data["pm1_0"] = None

    # Rentang fisik (PRD 17.1)
    if data["pm25"] < 0 or data["pm10"] < 0:
        print("[mqtt] Nilai PM negatif — skip")
        return None
    if not (0 <= data["gas_raw"] <= 4095):
        print(f"[mqtt] gas_raw di luar 0-4095: {data['gas_raw']} — skip")
        return None
    if not (-50 <= data["temperature"] <= 80):
        print("[mqtt] Suhu tidak wajar — skip")
        return None
    if not (0 <= data["humidity"] <= 100):
        print("[mqtt] Kelembapan tidak wajar — skip")
        return None
    if not (300 <= data["pressure"] <= 1100):
        print("[mqtt] Tekanan tidak wajar — skip")
        return None

    # Timestamp: pakai dari payload, fallback ke waktu server (PRD 17.1)
    ts = payload.get("timestamp")
    if isinstance(ts, str) and len(ts) >= 19:
        try:
            datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
            data["timestamp"] = ts[:19]
        except ValueError:
            data["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    else:
        data["timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Outlier ekstrem tetap disimpan (PRD: simpan dengan flag) — log saja
    if data["pm25"] > 500:
        print("[mqtt] PM2.5 > 500 ug/m3 (outlier ekstrem) - tetap disimpan")
    return data

# ---------------------------------------------------------------------------
# MQTT CALLBACKS
# ---------------------------------------------------------------------------

def _on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0 or str(reason_code) == "Success":
        _state["connected"] = True
        client.subscribe(config.MQTT_TOPIC, qos=1)
        print(f"[mqtt] Terhubung ke broker {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT} — subscribe '{config.MQTT_TOPIC}'")
    else:
        _state["connected"] = False
        print(f"[mqtt] Gagal konek: {reason_code}")


def _on_disconnect(client, userdata, disconnect_flags=None, reason_code=None, properties=None):
    _state["connected"] = False
    print("[mqtt] Koneksi broker terputus — mencoba reconnect otomatis...")


def _on_message(client, userdata, msg):
    # 1. Parse JSON
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        print("[mqtt] JSON tidak valid — skip")
        return

    # 2. Validasi
    data = validate_payload(payload)
    if data is None:
        return

    # 3. Simpan
    database.insert_reading(data)
    print(f"[mqtt] Data masuk: pm1={data.get('pm1_0')}, pm25={data['pm25']}, "
          f"pm10={data['pm10']}, gas={data['gas_raw']}, t={data['timestamp']}")

    # 4. Threshold check → early warning (Telegram kondisional + alert_log)
    try:
        check_threshold(data)
    except Exception as exc:  # alert TIDAK boleh bikin listener mati
        print(f"[mqtt] Error threshold check: {exc}")

# ---------------------------------------------------------------------------
# THREAD CLASS
# ---------------------------------------------------------------------------

class MQTTListener(threading.Thread):
    """Daemon thread subscriber MQTT. Reconnect otomatis (PRD T-18)."""

    def __init__(self):
        super().__init__(daemon=True, name="mqtt-listener")
        self.client = None

    def run(self):
        if _PAHO_V2:
            self.client = Client(CallbackAPIVersion.VERSION2, client_id=config.MQTT_CLIENT_ID)
        else:
            self.client = Client(client_id=config.MQTT_CLIENT_ID)

        if _PAHO_V2:
            self.client.on_connect = _on_connect
            self.client.on_disconnect = _on_disconnect
        else:
            # Signature v1 — bungkus agar cocok dengan handler di atas
            self.client.on_connect = (
                lambda c, u, f, rc: _on_connect(c, u, f, rc)
            )
            self.client.on_disconnect = (
                lambda c, u, rc: _on_disconnect(c, u, None, rc)
            )
        self.client.on_message = _on_message

        # reconnect_delay_set: retry otomatis 1s → lalu naik sampai 10s
        self.client.reconnect_delay_set(min_delay=1, max_delay=10)

        try:
            self.client.connect_async(config.MQTT_BROKER_HOST, config.MQTT_BROKER_PORT,
                                      keepalive=60)
            self.client.loop_forever(retry_first_connection=True)
        except Exception as exc:
            print(f"[mqtt] Listener berhenti: {exc}")


def start_listener():
    """Buat + start daemon thread. Dipanggil dari run.py."""
    listener = MQTTListener()
    listener.start()
    return listener
