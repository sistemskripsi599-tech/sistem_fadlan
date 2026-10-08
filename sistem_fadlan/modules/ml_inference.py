# =============================================================================
# modules/ml_inference.py — Load model .pkl + recursive forecasting 24 jam
# (PRD Section 9.2 / 12.6)
# =============================================================================

import os
from datetime import datetime, timedelta

import joblib
import pandas as pd

import config
from modules import database
from modules.feature_engineer import LAG_VARS, build_feature_vector, feature_names

# Model dimuat sekali saat proses start, dipakai berulang
_models = {"pm25": None, "pm10": None, "gas": None}
_loaded = False


def load_models():
    """Muat ketiga model .pkl dari MODELS_DIR. Return True jika lengkap."""
    global _loaded
    paths = {
        "pm25": os.path.join(config.MODELS_DIR, "pm25_model.pkl"),
        "pm10": os.path.join(config.MODELS_DIR, "pm10_model.pkl"),
        "gas":  os.path.join(config.MODELS_DIR, "gas_model.pkl"),
    }
    try:
        for key, path in paths.items():
            if os.path.exists(path):
                _models[key] = joblib.load(path)
            else:
                _models[key] = None
        _loaded = True
    except Exception as exc:
        print(f"[inference] Gagal memuat model: {exc}")
        _loaded = False
    return all(_models.values())


def is_ready():
    """True jika ketiga model tersedia di memori."""
    if not _loaded:
        load_models()
    return all(_models.values())


def _create_synthetic_row(pm25, pm10, gas, temperature, humidity, pressure, timestamp):
    """Baris sintetis hasil prediksi untuk menggeser window (PRD 12.6)."""
    return pd.DataFrame([{
        "timestamp":   timestamp,
        "pm25":        pm25,
        "pm10":        pm10,
        "gas_raw":     gas,
        "temperature": temperature,
        "humidity":    humidity,
        "pressure":    pressure,
    }])


def predict_24h():
    """Recursive forecasting 24 langkah (PRD 8.2 / 12.6).

    Return dict {generated_at, predictions} atau None jika model belum siap.
    """
    if not is_ready():
        return None

    # Ambil N_LAGS data terbaru, urut lama → baru
    recent = database.get_recent_readings(config.N_LAGS)
    if len(recent) < config.N_LAGS:
        return None

    df_window = pd.DataFrame(recent)
    df_window = df_window.sort_values("timestamp").reset_index(drop=True)

    # Model dilatih dengan urutan fitur tertentu — validasi sebelum predict
    expected = feature_names(LAG_VARS)
    trained_names = getattr(_models["pm25"], "feature_names_in_", None)
    if trained_names is not None and list(trained_names) != expected:
        print("[inference] Urutan fitur model tidak cocok — muat ulang perlu training ulang")
        return None

    # Asumsi cuaca jam berikutnya = cuaca terakhir (persistence)
    last_weather = df_window.iloc[-1][["temperature", "humidity", "pressure"]]

    predictions = []
    generated_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    current_time = datetime.now()

    for step in range(1, 25):
        target_time = current_time + timedelta(hours=step)
        ts = target_time.strftime("%Y-%m-%dT%H:%M:%S")

        # Feature vector dari window saat ini (waktu target = jam prediksi)
        # Dikirim sebagai DataFrame bernama kolom agar sklearn tidak warning
        features = build_feature_vector(df_window, LAG_VARS, target_time)
        feature_vector = pd.DataFrame([features], columns=feature_names(LAG_VARS))

        pm25 = float(_models["pm25"].predict(feature_vector)[0])
        pm10 = float(_models["pm10"].predict(feature_vector)[0])
        gas  = float(_models["gas"].predict(feature_vector)[0])

        # Nilai fisik tidak mungkin negatif
        pm25 = max(0.0, pm25)
        pm10 = max(0.0, pm10)
        gas = max(0.0, gas)

        predictions.append({
            "target_hour": ts,
            "pm25_pred":   round(pm25, 2),
            "pm10_pred":   round(pm10, 2),
            "gas_pred":    round(gas, 2),
        })

        # Geser window: buang baris terlama, masukkan baris sintetis hasil prediksi
        new_row = _create_synthetic_row(
            pm25, pm10, gas,
            float(last_weather["temperature"]),
            float(last_weather["humidity"]),
            float(last_weather["pressure"]),
            ts,
        )
        df_window = pd.concat([df_window.iloc[1:], new_row], ignore_index=True)

    # Simpan ke tabel predictions (FR-ML-10)
    try:
        database.save_predictions(predictions, generated_at)
    except Exception as exc:
        print(f"[inference] Gagal simpan predictions: {exc}")

    return {"generated_at": generated_at, "predictions": predictions}
