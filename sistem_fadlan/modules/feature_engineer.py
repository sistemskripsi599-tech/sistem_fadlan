# =============================================================================
# modules/feature_engineer.py — Lag features + time features
# (PRD Section 12.2: N_LAGS=12 per variabel + cyclical encoding waktu)
# Urutan fitur HARUS identik antara training dan inference.
# =============================================================================

import numpy as np
import pandas as pd

import config

LAG_VARS = ["pm25", "pm10", "gas_raw", "temperature", "humidity", "pressure"]
TIME_FEATURES = ["hour_sin", "hour_cos", "dow_sin", "dow_cos"]


def _time_features(ts):
    """Cyclical encoding jam & hari (PRD 12.2).
    Menerima pandas Timestamp, datetime.datetime, maupun string ISO."""
    ts = pd.Timestamp(ts)
    hour = ts.hour
    dow = ts.dayofweek  # 0=Senin
    return {
        "hour_sin": np.sin(2 * np.pi * hour / 24),
        "hour_cos": np.cos(2 * np.pi * hour / 24),
        "dow_sin":  np.sin(2 * np.pi * dow / 7),
        "dow_cos":  np.cos(2 * np.pi * dow / 7),
    }


def feature_names(lag_vars):
    """Daftar nama fitur terurut — sumber kebenaran tunggal."""
    names = [f"{v}_lag_{l}" for v in lag_vars for l in range(1, config.N_LAGS + 1)]
    return names + TIME_FEATURES


def build_supervised(df, lag_vars):
    """Tabel supervised untuk training (PRD 8.3 langkah 5).

    Baris waktu t: fitur = nilai t-1..t-N_LAGS + waktu pada t.
    Return (X, y_dict, feature_names) — X dan y sudah ter-dropna & selaras.
    """
    parts, names = [], []
    for v in lag_vars:
        for l in range(1, config.N_LAGS + 1):
            names.append(f"{v}_lag_{l}")
            parts.append(df[v].shift(l).rename(f"{v}_lag_{l}"))

    tf = pd.DataFrame([_time_features(ts) for ts in df.index],
                      index=df.index)[TIME_FEATURES]
    for k in TIME_FEATURES:
        names.append(k)
        parts.append(tf[k].rename(k))

    X = pd.concat(parts, axis=1).dropna()
    y = {v: df[v].reindex(X.index) for v in lag_vars}
    return X, y, names


def build_feature_vector(df_window, lag_vars, target_time):
    """Vektor fitur UNTUK SATU prediksi pada waktu target_time.

    df_window: N_LAGS baris terakhir TERURUT lama → baru.
    lag_l = nilai pada t-l relatif terhadap target (baris paling akhir = lag_1).
    Urutan output = feature_names(lag_vars) — identik dengan training.
    """
    vector = []
    for v in lag_vars:
        col = df_window[v].astype(float)
        for l in range(1, config.N_LAGS + 1):
            vector.append(float(col.iloc[-l]) if len(col) >= l else float(col.iloc[0]))
    tf = _time_features(target_time)
    vector.extend(float(tf[k]) for k in TIME_FEATURES)
    return vector
