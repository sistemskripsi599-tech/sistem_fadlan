# =============================================================================
# routes/api.py — REST API endpoints (PRD Section 11)
# Data dari SQLite; /api/predict dari model RF bila tersedia
#
# Kategori status udara (4 tingkat, keputusan 23 Sep 2026 — berbasis kerangka
# ISPU + baku mutu PP No. 22/2021; Kota Palu memakai baku mutu nasional):
#   BAIK       : PM2.5 <= 15.5  dan PM10 <= 50
#   SEDANG     : PM2.5 <= 55.4  dan PM10 <= 100
#   TIDAK SEHAT: PM2.5 <= 150.4 dan PM10 <= 200
#   BERBAHAYA  : di atas itu
# Status utama = kategori TERBURUK di antara PM2.5 dan PM10.
# =============================================================================

from datetime import datetime

from flask import Blueprint, jsonify, request

import config
from modules import database, ml_inference, mqtt_listener
from modules.air_quality import categorize_pm10, categorize_pm25, classify as _aq_classify

api_bp = Blueprint("api", __name__)

DATE_FMT = "%Y-%m-%d"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _air_quality(pm25, pm10=None):
    """Label + warna status udara (4 kategori) — logika di modules/air_quality."""
    return _aq_classify(pm25, pm10)


def _r2_status(r2):
    """Badge R² (PRD Section 12.5): >=0.85 baik, >=0.70 cukup, else kurang."""
    if r2 >= 0.85:
        return "baik"
    if r2 >= 0.70:
        return "cukup"
    return "kurang"


def _parse_date(value):
    """Validasi parameter tanggal; return string valid atau None jika kosong."""
    if not value:
        return None
    datetime.strptime(value, DATE_FMT)  # melempar ValueError jika format salah
    return value


def _err400(message):
    return jsonify({"status": "error", "message": message}), 400

# ---------------------------------------------------------------------------
# GET /api/realtime — data sensor terbaru + status udara
# ---------------------------------------------------------------------------

@api_bp.route("/realtime")
def realtime():
    row = database.get_latest_reading()
    if row is None:
        return jsonify({
            "status": "no_data",
            "message": "Menunggu data dari sensor...",
        })

    label, color = _air_quality(row["pm25"], row.get("pm10"))
    row["air_quality_label"] = label
    row["air_quality_color"] = color
    # Kategori per polutan (untuk badge di kartu dashboard)
    row["pm25_category"] = categorize_pm25(row["pm25"]) or "--"
    row["pm10_category"] = categorize_pm10(row.get("pm10")) or "--"
    row.pop("id", None)
    return jsonify({"status": "ok", "data": row})

# ---------------------------------------------------------------------------
# GET /api/chart-data?limit=50 — array data untuk grafik
# ---------------------------------------------------------------------------

@api_bp.route("/chart-data")
def chart_data():
    try:
        limit = request.args.get("limit", 50, type=int)
    except ValueError:
        return _err400("Parameter limit harus angka.")
    limit = max(1, min(limit, 500))

    records = database.get_series(limit)
    if not records:
        return jsonify({
            "status": "no_data",
            "message": "Menunggu data dari sensor...",
            "count": 0,
            "data": [],
        })

    for r in records:
        r.pop("id", None)
    return jsonify({"status": "ok", "count": len(records), "data": records})

# ---------------------------------------------------------------------------
# GET /api/history?limit=50&offset=0&start=YYYY-MM-DD&end=YYYY-MM-DD
# ---------------------------------------------------------------------------

@api_bp.route("/history")
def history():
    try:
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)
    except ValueError:
        return _err400("Parameter limit/offset harus angka.")

    if limit < 1 or limit > 500:
        return _err400("limit harus antara 1–500.")
    if offset < 0:
        return _err400("offset tidak boleh negatif.")

    try:
        start = _parse_date(request.args.get("start"))
        end = _parse_date(request.args.get("end"))
    except ValueError:
        return _err400("Format tanggal harus YYYY-MM-DD.")

    rows, total = database.get_readings(limit=limit, offset=offset,
                                        start_date=start, end_date=end)
    for r in rows:
        r.pop("id", None)
    return jsonify({
        "status": "ok",
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": rows,
    })

# ---------------------------------------------------------------------------
# GET /api/predict — prediksi 24 jam ke depan (Random Forest)
# ---------------------------------------------------------------------------

@api_bp.route("/predict")
def predict():
    if database.count_readings() < config.N_LAGS:
        return jsonify({
            "status": "no_data",
            "message": f"Data sensor kurang dari {config.N_LAGS} record. "
                       "Menunggu data dari sensor...",
        })

    result = ml_inference.predict_24h()
    if result is None:
        return jsonify({
            "status": "model_not_ready",
            "message": "Model belum dilatih. Jalankan train_model.py terlebih dahulu.",
        })
    if not result.get("predictions"):
        return jsonify({
            "status": "no_data",
            "message": "Menunggu data dari sensor...",
        })

    return jsonify({
        "status": "ok",
        "generated_at": result["generated_at"],
        "predictions": result["predictions"],
    })

# ---------------------------------------------------------------------------
# GET /api/model-metrics — metrik evaluasi model terbaru
# ---------------------------------------------------------------------------

@api_bp.route("/model-metrics")
def model_metrics():
    trained_at, metrics = database.get_model_metrics()
    if not metrics:
        return jsonify({
            "status": "no_data",
            "message": "Model belum dilatih. Jalankan train_model.py terlebih dahulu.",
        })

    items = []
    for m in metrics:
        items.append({
            "target": m["model_target"],
            "target_label": {"pm25": "Perkiraan Debu Halus",
                             "pm10": "Perkiraan Debu Kasar",
                             "gas": "Perkiraan Gas Tercemar"}.get(m["model_target"],
                                                             m["model_target"]),
            "mae": round(m["mae"], 4),
            "rmse": round(m["rmse"], 4),
            "r2": round(m["r2_score"], 4),
            "r2_status": _r2_status(m["r2_score"]),
        })

    return jsonify({"status": "ok", "trained_at": trained_at, "metrics": items})

# ---------------------------------------------------------------------------
# GET /api/feature-importance — 10 faktor paling berpengaruh saat komputer menebak
# (bahan analisis novelty: tekanan udara diharapkan masuk peringkat atas)
# ---------------------------------------------------------------------------

@api_bp.route("/feature-importance")
def feature_importance():
    import joblib
    import os

    path = os.path.join(config.MODELS_DIR, "pm25_model.pkl")
    if not os.path.exists(path):
        return jsonify({
            "status": "no_data",
            "message": "Model belum dilatih. Jalankan train_model.py terlebih dahulu.",
        })
    try:
        model = joblib.load(path)
        names = getattr(model, "feature_names_in_", None)
        importances = getattr(model, "feature_importances_", None)
        if names is None or importances is None:
            return jsonify({"status": "no_data", "message": "Model tidak menyimpan informasi ini."})
        pairs = sorted(zip(names, importances), key=lambda t: -t[1])[:10]
        return jsonify({
            "status": "ok",
            "features": [
                {"name": n, "importance": round(float(s), 4),
                 "is_pressure": n.startswith("pressure")}
                for n, s in pairs
            ],
        })
    except Exception:
        return jsonify({"status": "error", "message": "Gagal membaca model."}), 500

# ---------------------------------------------------------------------------
# GET /api/status — status sistem (indikator ● Live di navbar)
# ---------------------------------------------------------------------------

@api_bp.route("/status")
def status():
    last = database.get_latest_reading()
    last_data = None
    live = False
    if last:
        last_data = last["timestamp"]
        try:
            age = (datetime.now() - datetime.strptime(last_data, "%Y-%m-%dT%H:%M:%S")).total_seconds()
            live = age <= 120  # hijau jika data < 2 menit (PRD Section 15.2)
        except ValueError:
            pass

    return jsonify({
        "status": "ok",
        "system_online": True,
        "last_data": last_data,
        "live": live,
        "mqtt_connected": mqtt_listener.is_connected(),
        "model_ready": ml_inference.is_ready(),
    })


# ---------------------------------------------------------------------------
# GET /api/admin/stats — statistik DB + konfigurasi aktif (panel admin)
# ---------------------------------------------------------------------------

@api_bp.route("/admin/stats")
def admin_stats():
    conn = database.get_connection()
    try:
        def count(tbl):
            return conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]

        db_stats = {
            "sensor_readings": count("sensor_readings"),
            "alert_log":       count("alert_log"),
            "predictions":     count("predictions"),
            "model_metrics":   count("model_metrics"),
        }

        # 10 alert terbaru untuk ditampilkan di panel
        rows = conn.execute(
            "SELECT pollutant, value, threshold, triggered_at, sent_status "
            "FROM alert_log ORDER BY triggered_at DESC LIMIT 10"
        ).fetchall()
        recent_alerts = [dict(r) for r in rows]
    finally:
        conn.close()

    cfg = {
        "data_mode":        config.DATA_MODE,
        "mqtt_broker":      config.MQTT_BROKER_HOST,
        "mqtt_port":        config.MQTT_BROKER_PORT,
        "mqtt_topic":       config.MQTT_TOPIC,
        "telegram_enabled": config.TELEGRAM_ENABLED,
        "threshold_pm25":   config.THRESHOLD_PM25,
        "threshold_pm10":   config.THRESHOLD_PM10,
        "cooldown_minutes": config.ALERT_COOLDOWN_MINUTES,
    }

    return jsonify({
        "status": "ok",
        "data": {
            "db":            db_stats,
            "config":        cfg,
            "recent_alerts": recent_alerts,
        }
    })


# ---------------------------------------------------------------------------
# GET /api/admin/test-telegram — kirim pesan test ke Telegram
# ---------------------------------------------------------------------------

@api_bp.route("/admin/test-telegram")
def admin_test_telegram():
    if not config.TELEGRAM_ENABLED:
        return jsonify({
            "status": "error",
            "message": "Telegram belum diaktifkan (TELEGRAM_ENABLED=False di config.py)."
        }), 400
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return jsonify({
            "status": "error",
            "message": "Token atau Chat ID belum diisi di config.py."
        }), 400

    import requests as req_lib
    waktu = datetime.now().strftime("%A, %d %b %Y — %H:%M:%S")
    pesan = (
        "✅ *Test Koneksi — sistem\\_fadlan*\n\n"
        f"🕐 Waktu: {waktu}\n"
        "📡 Status: Bot aktif & terhubung\n"
        "🌿 Mode: " + config.DATA_MODE.upper() + "\n\n"
        "Sistem monitoring kualitas udara berjalan normal."
    )
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = req_lib.post(url, json={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": pesan,
            "parse_mode": "Markdown",
        }, timeout=config.TELEGRAM_TIMEOUT_S)
        if resp.status_code == 200:
            return jsonify({"status": "ok", "message": "Pesan test berhasil dikirim ke Telegram!"})
        return jsonify({
            "status": "error",
            "message": f"API Telegram merespons HTTP {resp.status_code}. Cek token/chat_id."
        }), 502
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Gagal terhubung ke Telegram: {exc}"}), 502


# ---------------------------------------------------------------------------
# POST /api/admin/update-threshold — update threshold notifikasi (sesi ini)
# ---------------------------------------------------------------------------

@api_bp.route("/admin/update-threshold", methods=["POST"])
def admin_update_threshold():
    data = request.get_json(silent=True) or {}
    try:
        pm25 = float(data["pm25"])
        pm10 = float(data["pm10"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "message": "Parameter pm25 dan pm10 harus angka."}), 400

    if pm25 <= 0 or pm10 <= 0:
        return jsonify({"status": "error", "message": "Threshold harus lebih dari 0."}), 400
    if pm25 > 500 or pm10 > 500:
        return jsonify({"status": "error", "message": "Threshold tidak boleh melebihi 500."}), 400

    config.THRESHOLD_PM25 = pm25
    config.THRESHOLD_PM10 = pm10

    return jsonify({
        "status": "ok",
        "message": f"Threshold diperbarui — PM2.5: {pm25} | PM10: {pm10} μg/m³",
        "threshold_pm25": pm25,
        "threshold_pm10": pm10,
    })


# ---------------------------------------------------------------------------
# POST /api/admin/clear-data — hapus data dari database
# ---------------------------------------------------------------------------

@api_bp.route("/admin/clear-data", methods=["POST"])
def admin_clear_data():
    data = request.get_json(silent=True) or {}
    clear_type = data.get("type", "")

    if clear_type not in ("sensor", "alerts", "all"):
        return jsonify({"status": "error", "message": "type harus: sensor | alerts | all"}), 400

    if config.DATA_MODE == "lapangan" and clear_type in ("sensor", "all"):
        # Ekstra konfirmasi: mode lapangan = data penelitian asli
        force = data.get("force", False)
        if not force:
            return jsonify({
                "status": "error",
                "message": (
                    "DATA_MODE='lapangan' — ini data penelitian asli. "
                    "Kirim ulang dengan force=true jika benar-benar yakin."
                )
            }), 409

    conn = database.get_connection()
    deleted = {}
    try:
        if clear_type in ("sensor", "all"):
            deleted["sensor_readings"] = conn.execute(
                "SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
            deleted["predictions"] = conn.execute(
                "SELECT COUNT(*) FROM predictions").fetchone()[0]
            conn.execute("DELETE FROM sensor_readings")
            conn.execute("DELETE FROM predictions")
            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name IN ('sensor_readings','predictions')")

        if clear_type in ("alerts", "all"):
            deleted["alert_log"] = conn.execute(
                "SELECT COUNT(*) FROM alert_log").fetchone()[0]
            conn.execute("DELETE FROM alert_log")
            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name='alert_log'")

        if clear_type == "all":
            deleted["model_metrics"] = conn.execute(
                "SELECT COUNT(*) FROM model_metrics").fetchone()[0]
            conn.execute("DELETE FROM model_metrics")
            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name='model_metrics'")

        conn.commit()
    finally:
        conn.close()

    total = sum(deleted.values())
    return jsonify({
        "status": "ok",
        "message": f"Berhasil menghapus {total} record. Detail: {deleted}",
        "deleted": deleted,
    })
