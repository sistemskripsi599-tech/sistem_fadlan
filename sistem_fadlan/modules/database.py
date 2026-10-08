# =============================================================================
# modules/database.py — Koneksi SQLite + semua fungsi CRUD
# Tabel: sensor_readings, predictions, alert_log, model_metrics (PRD Section 10)
#
# Catatan skema (keselarasan dengan proposal):
#   - sensor_readings.pm1_0 : PM1.0 dari PMS5003 — MONITORING SAJA (Batasan
#     Masalah 1.3 proposal: prediksi hanya PM2.5, PM10, gas).
#   - alert_log.sent_status : status pengiriman Telegram
#     ('disabled'|'no_token'|'success'|'failed'|'cooldown').
# =============================================================================

import os
import sqlite3
from datetime import datetime

import config

# ---------------------------------------------------------------------------
# KONEKSI
# ---------------------------------------------------------------------------

def get_connection():
    """Buka koneksi SQLite baru (baris berbentuk dict-like)."""
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row):
    return dict(row) if row is not None else None


def _rows_to_list(rows):
    return [dict(r) for r in rows]

# ---------------------------------------------------------------------------
# INISIALISASI TABEL
# ---------------------------------------------------------------------------

def init_db():
    """Buat 4 tabel + index jika belum ada (skema PRD Section 10)."""
    conn = get_connection()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            pm1_0       REAL,
            pm25        REAL    NOT NULL,
            pm10        REAL    NOT NULL,
            gas_raw     INTEGER NOT NULL,
            temperature REAL    NOT NULL,
            humidity    REAL    NOT NULL,
            pressure    REAL    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sr_timestamp ON sensor_readings(timestamp);

        CREATE TABLE IF NOT EXISTS predictions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at  TEXT NOT NULL,
            target_hour   TEXT NOT NULL,
            pm25_pred     REAL,
            pm10_pred     REAL,
            gas_pred      REAL
        );

        CREATE INDEX IF NOT EXISTS idx_pred_generated ON predictions(generated_at);

        CREATE TABLE IF NOT EXISTS alert_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            triggered_at TEXT NOT NULL,
            pollutant    TEXT NOT NULL,
            value        REAL NOT NULL,
            threshold    REAL NOT NULL,
            message_sent TEXT,
            sent_status  TEXT
        );

        CREATE TABLE IF NOT EXISTS model_metrics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            trained_at   TEXT NOT NULL,
            model_target TEXT NOT NULL,
            mae          REAL NOT NULL,
            rmse         REAL NOT NULL,
            r2_score     REAL NOT NULL,
            n_estimators INTEGER,
            n_lags       INTEGER
        );
        """)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate(conn):
    """Migrasi otomatis DB lama: tambah kolom baru jika belum ada.

    Aman dipanggil berulang — hanya ALTER TABLE bila kolom belum ditemukan.
    Data lama tidak disentuh; kolom baru akan bernilai NULL untuk record lama.
    """
    def _columns(table):
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    if "pm1_0" not in _columns("sensor_readings"):
        conn.execute("ALTER TABLE sensor_readings ADD COLUMN pm1_0 REAL")
        print("[db] Migrasi: kolom sensor_readings.pm1_0 ditambahkan")

    if "sent_status" not in _columns("alert_log"):
        conn.execute("ALTER TABLE alert_log ADD COLUMN sent_status TEXT")
        print("[db] Migrasi: kolom alert_log.sent_status ditambahkan")

# ---------------------------------------------------------------------------
# SENSOR READINGS
# ---------------------------------------------------------------------------

def insert_reading(data):
    """Simpan satu record sensor. data: dict 7 field PRD + pm1_0 (opsional).

    pm1_0 boleh None (firmware lama) — hanya untuk monitoring, bukan prediksi.
    """
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO sensor_readings
               (timestamp, pm1_0, pm25, pm10, gas_raw, temperature, humidity, pressure)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["timestamp"], data.get("pm1_0"),
                data["pm25"], data["pm10"],
                int(data["gas_raw"]), data["temperature"],
                data["humidity"], data["pressure"],
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_latest_reading():
    """Ambil 1 data terbaru (untuk /api/realtime)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM sensor_readings ORDER BY timestamp DESC, id DESC LIMIT 1"
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_recent_readings(n):
    """Ambil N data terbaru TERURUT lama → baru (untuk window ML inference)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM sensor_readings ORDER BY timestamp DESC, id DESC LIMIT ?) "
            "ORDER BY timestamp ASC, id ASC",
            (int(n),),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def get_readings(limit=50, offset=0, start_date=None, end_date=None):
    """Data historis + filter tanggal + pagination. Return (rows, total)."""
    conn = get_connection()
    try:
        where, params = [], []
        if start_date:
            where.append("timestamp >= ?")
            params.append(start_date)                      # "YYYY-MM-DD"
        if end_date:
            where.append("timestamp < date(?, '+1 day')")  # inklusif s/d akhir hari
            params.append(end_date)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM sensor_readings {where_sql}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""SELECT * FROM sensor_readings {where_sql}
                ORDER BY timestamp DESC, id DESC
                LIMIT ? OFFSET ?""",
            params + [int(limit), int(offset)],
        ).fetchall()
        return _rows_to_list(rows), total
    finally:
        conn.close()


def get_series(limit=50):
    """N data terbaru terurut lama → baru (untuk grafik /api/chart-data)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM (SELECT * FROM sensor_readings ORDER BY timestamp DESC, id DESC LIMIT ?) "
            "ORDER BY timestamp ASC, id ASC",
            (int(limit),),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


def count_readings():
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# PREDICTIONS
# ---------------------------------------------------------------------------

def save_predictions(predictions_list, generated_at=None):
    """Simpan hasil prediksi 24 titik. Dipanggil oleh inference engine."""
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn = get_connection()
    try:
        conn.executemany(
            """INSERT INTO predictions
               (generated_at, target_hour, pm25_pred, pm10_pred, gas_pred)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    generated_at, p["target_hour"],
                    p.get("pm25_pred"), p.get("pm10_pred"), p.get("gas_pred"),
                )
                for p in predictions_list
            ],
        )
        conn.commit()
        return generated_at
    finally:
        conn.close()


def get_latest_predictions(max_age_minutes=15):
    """Prediksi batch terbaru. Return (status, generated_at, list).

    status: 'ok' bila ada dan cukup segar, 'stale' bila sudah kadaluarsa,
    'no_data' bila belum ada prediksi sama sekali.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT generated_at FROM predictions ORDER BY generated_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return "no_data", None, []

        generated_at = row["generated_at"]
        fresh = True
        try:
            age_min = (datetime.now() - datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%S")).total_seconds() / 60
            fresh = age_min <= max_age_minutes
        except ValueError:
            pass

        rows = conn.execute(
            "SELECT target_hour, pm25_pred, pm10_pred, gas_pred "
            "FROM predictions WHERE generated_at = ? ORDER BY id ASC",
            (generated_at,),
        ).fetchall()
        return ("ok" if fresh else "stale"), generated_at, _rows_to_list(rows)
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# ALERT LOG
# ---------------------------------------------------------------------------

def log_alert(pollutant, value, threshold, message, triggered_at=None,
              sent_status=None):
    """Catat satu alert ke alert_log. Return id record.

    sent_status: 'disabled'|'no_token'|'success'|'failed'|'cooldown'
    (None untuk pemanggil lama yang tidak melapor status pengiriman).
    """
    triggered_at = triggered_at or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO alert_log
               (triggered_at, pollutant, value, threshold, message_sent, sent_status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (triggered_at, pollutant, float(value), float(threshold), message,
             sent_status),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# MODEL METRICS
# ---------------------------------------------------------------------------

def save_model_metrics(target, mae, rmse, r2_score, trained_at=None):
    """Simpan metrik evaluasi satu model (pm25 / pm10 / gas)."""
    trained_at = trained_at or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO model_metrics
               (trained_at, model_target, mae, rmse, r2_score, n_estimators, n_lags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (trained_at, target, float(mae), float(rmse), float(r2_score),
             int(config.N_ESTIMATORS), int(config.N_LAGS)),
        )
        conn.commit()
        return trained_at
    finally:
        conn.close()


def get_model_metrics():
    """Metrik batch training terbaru. Return (trained_at, list) atau (None, [])."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT trained_at FROM model_metrics ORDER BY trained_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None, []
        rows = conn.execute(
            "SELECT model_target, mae, rmse, r2_score, trained_at "
            "FROM model_metrics WHERE trained_at = ? ORDER BY model_target ASC",
            (row["trained_at"],),
        ).fetchall()
        return row["trained_at"], _rows_to_list(rows)
    finally:
        conn.close()
