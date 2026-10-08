# =============================================================================
# modules/ml_trainer.py — Training 3 model Random Forest (PRD Section 12)
# Data: dataset sekunder CSV + data primer SQLite → 80/20 time-series split
# Output: models/*.pkl + metrik ke tabel model_metrics
# =============================================================================

import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (accuracy_score, classification_report,
                             mean_absolute_error, mean_squared_error, r2_score)

import config
from modules import database, reporting
from modules.air_quality import categorize_pm10, categorize_pm25
from modules.feature_engineer import LAG_VARS, build_supervised, feature_names
from modules.preprocessor import VALUE_COLS, preprocess, to_dataframe

TARGETS = ["pm25", "pm10", "gas"]   # gas → kolom gas_raw


# ---------------------------------------------------------------------------
# LOADING DATA (PRD Section 12.1)
# ---------------------------------------------------------------------------

def load_secondary_csv():
    """Muat ISPU_DKI_Jakarta_2021.csv → kolom (timestamp, pm25, pm10).

    Kolom dikenali fleksibel: 'tanggal', 'PM2.5', 'PM10', dst. (PRD 12.1).
    Return DataFrame mentah (belum dipreproses) atau DataFrame kosong.
    """
    if not os.path.exists(config.CSV_FILE):
        print(f"[trainer] File data latih tidak ada: {config.CSV_FILE}")
        print("[trainer] Belum ada data latih - training akan lanjut dengan data alat saja")
        return pd.DataFrame()

    df = pd.read_csv(config.CSV_FILE)
    rename = {}
    for col in df.columns:
        c = str(col).strip().lower()
        if "tanggal" in c:
            rename[col] = "timestamp"
        elif c in ("pm2.5", "pm25", "pm2,5", "pm 2.5"):
            rename[col] = "pm25"
        elif c == "pm10" or c == "pm 10":
            rename[col] = "pm10"
    df = df.rename(columns=rename)

    if "timestamp" not in df.columns or ("pm25" not in df.columns and "pm10" not in df.columns):
        print(f"[trainer] Kolom CSV tidak dikenali: {list(df.columns)}")
        return pd.DataFrame()

    # Peringatan kejujuran: kalau masih file CONTOH, katakan terang-terangan
    if "CONTOH" in os.path.basename(config.CSV_FILE).upper():
        print("[trainer] !! PERHATIAN: ini file CONTOH buatan, BUKAN data asli.")
        print("[trainer] !! Untuk skripsi: unduh data resmi (satudata.jakarta.go.id),")
        print("[trainer] !! taruh di folder data/, lalu arahkan CSV_FILE di config.py.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")  # deteksi format otomatis
    df = df.dropna(subset=["timestamp"])
    print(f"[trainer] Data latih dari CSV: {len(df)} baris")
    return df


def load_primary():
    """Muat seluruh data primer dari tabel sensor_readings (PRD FR-ML-02)."""
    rows, _ = database.get_readings(limit=1_000_000)
    if not rows:
        return pd.DataFrame()
    print(f"[trainer] Data primer: {len(rows)} baris dari SQLite")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# PIPELINE UTAMA
# ---------------------------------------------------------------------------

def load_and_prepare():
    """Gabungkan + preprocess kedua sumber data (PRD 12.1 strategi merge).

    Kolom yang tidak ada di dataset sekunder (gas, cuaca) diisi median data
    primer; jika data primer belum ada, diisi 0 agar pipeline tetap jalan.

    Return (df_reg, df_cls):
      - df_reg : data dengan outlier removal penuh → untuk model regresi
      - df_cls : data tanpa outlier removal → untuk classifier kategori udara,
                 agar nilai ekstrem (TIDAK SEHAT / SANGAT TIDAK SEHAT / BERBAHAYA)
                 tidak ikut terbuang sebagai outlier IQR
    """
    sec = to_dataframe(load_secondary_csv().to_dict("records"))
    prim = to_dataframe(load_primary().to_dict("records"))

    if sec.empty and prim.empty:
        raise RuntimeError(
            "Tidak ada data untuk dilatih. Letakkan ISPU_DKI_Jakarta_2021.csv "
            "di folder data/ dan/atau jalankan sistem untuk mengumpulkan data sensor."
        )

    # Isi kolom yang seluruhnya kosong (PRD 12.1: median data primer)
    if not sec.empty:
        for col in VALUE_COLS:
            if sec[col].isna().all():
                if not prim.empty and not prim[col].isna().all():
                    fill = float(prim[col].median())
                    print(f"[trainer] Kolom '{col}' CSV kosong -> isi median primer {fill:.1f}")
                else:
                    fill = 0.0
                    print(f"[trainer] Kolom '{col}' CSV kosong & tanpa primer -> isi 0")
                sec[col] = sec[col].fillna(fill)

    frames_reg = []   # untuk regresi: outlier removal aktif
    frames_cls = []   # untuk klasifikasi: hanya resample + fill, tanpa outlier removal

    if not sec.empty:
        df_sec_reg = preprocess(sec, interpolate_limit=3)
        frames_reg.append(df_sec_reg)

        # Versi tanpa outlier removal: hanya resample + interpolasi
        from modules.preprocessor import resample as do_resample, fill_missing
        df_sec_cls = fill_missing(do_resample(sec), limit=3)
        frames_cls.append(df_sec_cls)

    if not prim.empty:
        df_prim_reg = preprocess(prim, interpolate_limit=10)
        frames_reg.append(df_prim_reg)

        from modules.preprocessor import resample as do_resample, fill_missing
        df_prim_cls = fill_missing(do_resample(prim), limit=10)
        frames_cls.append(df_prim_cls)

    # --- df regresi (dengan outlier removal) ---
    df_reg = pd.concat(frames_reg).sort_index()
    df_reg = df_reg[~df_reg.index.duplicated(keep="last")]
    df_reg = df_reg.interpolate(method="linear", limit=3, limit_area="inside").dropna()
    print(f"[trainer] Setelah preprocessing (regresi): {len(df_reg)} baris "
          f"({df_reg.index.min()} s/d {df_reg.index.max()})")

    # --- df klasifikasi (tanpa outlier removal) ---
    df_cls = pd.concat(frames_cls).sort_index()
    df_cls = df_cls[~df_cls.index.duplicated(keep="last")]
    df_cls = df_cls.interpolate(method="linear", limit=3, limit_area="inside").dropna()
    print(f"[trainer] Setelah preprocessing (klasifikasi): {len(df_cls)} baris "
          f"({df_cls.index.min()} s/d {df_cls.index.max()})")

    return df_reg, df_cls


def train():
    """Training + evaluasi + simpan model & metrik. Return dict metrik."""
    df_reg, df_cls = load_and_prepare()

    min_rows = config.N_LAGS + 25   # cukup untuk lag + split 80/20 yang bermakna
    if len(df_reg) < min_rows:
        raise RuntimeError(
            f"Data terlalu sedikit: {len(df_reg)} baris (butuh >= {min_rows}) "
            "setelah preprocessing."
        )

    # --- Regresi: pakai df_reg (outlier removal aktif) ---
    X, y, names = build_supervised(df_reg, LAG_VARS)
    expected = feature_names(LAG_VARS)
    if list(X.columns) != expected:
        raise RuntimeError("Urutan fitur tidak konsisten — periksa feature_engineer")

    if len(X) < 25:
        raise RuntimeError(f"Sampel supervised terlalu sedikit: {len(X)}")

    # Time-series split 80/20 — TANPA shuffle (PRD 12.3 langkah 5)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    print(f"[trainer] Split regresi: {len(X_train)} train / {len(X_test)} test")

    # --- Klasifikasi: pakai df_cls (tanpa outlier removal) ---
    X_cls, y_cls, _ = build_supervised(df_cls, LAG_VARS)
    split_cls = int(len(X_cls) * 0.8)
    X_cls_train = X_cls.iloc[:split_cls]
    X_cls_test  = X_cls.iloc[split_cls:]
    print(f"[trainer] Split klasifikasi: {len(X_cls_train)} train / {len(X_cls_test)} test")

    os.makedirs(config.MODELS_DIR, exist_ok=True)
    trained_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")   # nama file artefak 1 sesi
    split_info = (f"{len(X_train)} train / {len(X_test)} test "
                  "(80/20 time-series, tanpa shuffle)")
    results = {}
    trained_models = {}

    for target in TARGETS:
        y_col = "gas_raw" if target == "gas" else target
        yt = y[y_col]
        if yt.isna().all():
            print(f"[trainer] Target '{target}' kosong — lewati")
            continue

        model = RandomForestRegressor(
            n_estimators=config.N_ESTIMATORS,
            random_state=config.RANDOM_STATE,
            n_jobs=-1,
        )
        model.fit(X_train, yt.loc[X_train.index])
        y_pred = model.predict(X_test)
        y_true = yt.loc[X_test.index]

        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))

        path = os.path.join(config.MODELS_DIR, f"{target}_model.pkl")
        joblib.dump(model, path)
        database.save_model_metrics(target, mae, rmse, r2, trained_at)
        trained_models[target] = model

        print(f"[trainer] {target.upper():5s} — MAE={mae:.3f}  RMSE={rmse:.3f}  "
              f"R²={r2:.3f}  -> {path}")
        results[target] = {"mae": mae, "rmse": rmse, "r2": r2}

        # Grafik aktual vs prediksi + residual (bukti BAB IV)
        reporting.save_actual_vs_pred(y_true, y_pred, target, stamp)

        # Classifier kategori udara: gunakan df_cls agar nilai ekstrem tidak
        # terbuang oleh outlier removal → semua 5 kategori ISPU terwakili
        if target in ("pm25", "pm10"):
            yt_cls = y_cls[y_col]
            _train_classifier(target, X_cls_train, X_cls_test, yt_cls, stamp)

    # Feature importance model PM2.5 — bahan analisis novelty (PRD 15.6)
    if "pm25" in results:
        _print_importance("pm25")
        reporting.save_feature_importance(trained_models["pm25"], "pm25", stamp=stamp)

    # Laporan teks gabungan (bukti evaluasi siap lampir ke laporan)
    reporting.save_text_report(results, split_info, stamp)
    return results


# ---------------------------------------------------------------------------
# KLASIFIKASI KATEGORI (classifier pendamping — confusion matrix & report)
# Regresi tetap algoritma utama (proposal); classifier menghasilkan bukti
# evaluasi kategori: confusion matrix, precision/recall/F1, accuracy.
# ---------------------------------------------------------------------------

def _train_classifier(target, X_train, X_test, yt, stamp):
    """Latih RandomForestClassifier kategori udara untuk 1 polutan.

    Classifier menggunakan nilai PM langsung (bukan lag features) karena
    kategorisasi ISPU bersifat threshold-based, bukan time-series.
    Data diambil dari df_cls (tanpa outlier removal) agar semua 5 kategori
    ISPU terwakili. Model disimpan sebagai {target}_cls_model.pkl.
    Gagal di sini TIDAK menggagalkan training regresi.
    """
    try:
        cat_fn = categorize_pm25 if target == "pm25" else categorize_pm10
        y_col  = target  # 'pm25' atau 'pm10'

        # Ambil nilai langsung dari yt (bukan via lag features)
        y_train_val = yt.loc[X_train.index].dropna()
        y_test_val  = yt.loc[X_test.index].dropna()

        y_train_cat = y_train_val.map(cat_fn)
        y_test_cat  = y_test_val.map(cat_fn)

        if y_train_cat.nunique() < 2:
            print(f"[trainer] Klasifikasi {target}: data latih hanya 1 kategori "
                  "— confusion matrix dilewati")
            return

        # Fitur klasifikasi: nilai pm langsung + lag_1 dan lag_2 saja
        # (cukup untuk memberi konteks tanpa mengaburkan nilai ekstrem)
        X_tr = pd.DataFrame({
            y_col:          y_train_val.values,
            f"{y_col}_lag1": yt.loc[X_train.index].shift(1).bfill().loc[X_train.index].values,
            f"{y_col}_lag2": yt.loc[X_train.index].shift(2).bfill().loc[X_train.index].values,
        }, index=y_train_val.index)

        X_te = pd.DataFrame({
            y_col:          y_test_val.values,
            f"{y_col}_lag1": yt.loc[X_test.index].shift(1).bfill().loc[X_test.index].values,
            f"{y_col}_lag2": yt.loc[X_test.index].shift(2).bfill().loc[X_test.index].values,
        }, index=y_test_val.index)

        # Bobot eksplisit agar kategori langka tidak diabaikan
        class_weight = {
            "BAIK":               1.0,
            "SEDANG":             1.0,
            "TIDAK SEHAT":        3.0,
            "SANGAT TIDAK SEHAT": 5.0,
            "BERBAHAYA":          5.0,
        }

        clf = RandomForestClassifier(
            n_estimators=config.N_ESTIMATORS,
            random_state=config.RANDOM_STATE,
            n_jobs=-1,
            class_weight=class_weight,
            min_samples_leaf=1,
        )
        clf.fit(X_tr, y_train_cat)
        y_pred_cat = clf.predict(X_te)

        acc = float(accuracy_score(y_test_cat, y_pred_cat))
        print(f"[trainer] {target.upper()} classifier — accuracy={acc:.3f}")

        dist = y_test_cat.value_counts().to_dict()
        print(f"[trainer] Distribusi test set ({target}): {dist}")

        joblib.dump(clf, os.path.join(config.MODELS_DIR, f"{target}_cls_model.pkl"))

        rep = reporting.save_confusion_matrix(y_test_cat, y_pred_cat, target, stamp)
        if rep:
            print(f"[trainer] Classification report ({target}):")
            print(rep)
    except Exception as exc:
        import traceback
        print(f"[trainer] Klasifikasi {target} gagal (training lanjut): {exc}")
        traceback.print_exc()


def _print_importance(target="pm25", top=10):
    """Cetak 10 fitur terpenting (dipanggil dari train() saat model pm25 ada)."""
    path = os.path.join(config.MODELS_DIR, f"{target}_model.pkl")
    if not os.path.exists(path):
        return
    model = joblib.load(path)
    names = getattr(model, "feature_names_in_", None)
    if names is None:
        return
    imp = sorted(zip(names, model.feature_importances_), key=lambda t: -t[1])[:top]
    print(f"[trainer] Feature importance ({target}):")
    for name, score in imp:
        marker = "  <- NOVELTY" if name.startswith("pressure") else ""
        print(f"    {name:20s} {score:.4f}{marker}")
