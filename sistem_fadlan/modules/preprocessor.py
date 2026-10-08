# =============================================================================
# modules/preprocessor.py — Cleaning + missing values + outlier removal
# (PRD Section 12.3: resample 30 menit, interpolasi gap kecil, outlier IQR)
# =============================================================================

import numpy as np
import pandas as pd

VALUE_COLS = ["pm25", "pm10", "gas_raw", "temperature", "humidity", "pressure"]
RESAMPLE_INTERVAL = "30min"   # PRD 12.3 langkah 1


def to_dataframe(records):
    """list[dict] (CSV/SQLite) → DataFrame datetime-indexed + kolom numerik."""
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=VALUE_COLS)
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    for col in VALUE_COLS:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.set_index("timestamp")[VALUE_COLS]


def resample(df, interval=RESAMPLE_INTERVAL):
    """Resample ke interval seragam via mean (PRD 12.3 langkah 1)."""
    return df[VALUE_COLS].resample(interval).mean()


def fill_missing(df, limit=3):
    """Gap ≤ limit interval → interpolasi linear; lebih → drop (PRD 12.3 langkah 2).

    Catatan implementasi: trainer memakai limit lebih besar untuk menjembatani
    interval dataset sekunder yang harian (lihat ml_trainer.load_and_prepare).
    """
    df = df.interpolate(method="linear", limit=limit, limit_area="inside")
    return df.dropna()


def remove_outliers(df, k=1.5):
    """Outlier IQR → NaN → interpolasi ulang (PRD 12.3 langkah 3)."""
    out = df.copy()
    for col in VALUE_COLS:
        q1 = out[col].quantile(0.25)
        q3 = out[col].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or np.isnan(iqr):
            continue
        mask = (out[col] < q1 - k * iqr) | (out[col] > q3 + k * iqr)
        out.loc[mask, col] = np.nan
    return out.interpolate(method="linear", limit=3, limit_area="inside")


def preprocess(df, interpolate_limit=3):
    """Pipeline lengkap: resample → missing → outlier → rapikan."""
    df = resample(df)
    df = fill_missing(df, limit=interpolate_limit)
    df = remove_outliers(df)
    df = fill_missing(df, limit=interpolate_limit)
    return df
