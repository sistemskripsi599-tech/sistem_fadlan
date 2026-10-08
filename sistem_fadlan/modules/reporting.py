# =============================================================================
# modules/reporting.py — Artefak evaluasi untuk BAB IV skripsi
# Menghasilkan (folder reports/, nama ber-suffix timestamp):
#   1. confusion_matrix_<target>.png  — heatmap classifier kategori udara
#   2. feature_importance.png         — bar chart 15 fitur terpenting (novelty)
#   3. actual_vs_pred_<target>.png    — scatter aktual vs prediksi + residual
#   4. laporan_evaluasi_<timestamp>.txt — metrik regresi + classification report
#
# Semua fungsi anti-crash: kegagalan gambar TIDAK boleh menggagalkan training.
# =============================================================================

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")   # tanpa GUI — aman dijalankan di server/laptop mana pun
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix

import config
from modules.air_quality import CATEGORIES

REPORTS_DIR = os.path.join(config.BASE_DIR, "reports")

# Palet gelap konsisten dengan dashboard (slate)
_BG      = "#0f172a"
_PANEL   = "#1e293b"
_TEXT    = "#e2e8f0"
_SUBTEXT = "#94a3b8"
_GRID    = (1, 1, 1, 0.08)   # putih transparan — format tuple matplotlib (bukan CSS rgba)
_ACCENT  = "#22d3ee"
_BANDS   = ["#22c55e", "#eab308", "#f97316", "#ef4444"]  # baik..berbahaya


def _stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _fig_axes(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=150)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_PANEL)
    ax.tick_params(colors=_SUBTEXT)
    for spine in ax.spines.values():
        spine.set_color(_SUBTEXT)
    return fig, ax


def _finish(fig, path):
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"[report] Tersimpan: {path}")


def _ensure_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return REPORTS_DIR


# ---------------------------------------------------------------------------
# 1. CONFUSION MATRIX (classifier kategori udara)
# ---------------------------------------------------------------------------

def save_confusion_matrix(y_true, y_pred, target, stamp=None):
    """Heatmap confusion matrix 4 kategori + file .txt classification report."""
    try:
        from sklearn.metrics import classification_report
        stamp = stamp or _stamp()
        _ensure_dir()

        labels = CATEGORIES
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        total = cm.sum() if cm.sum() else 1
        pct = cm / total * 100.0

        fig, ax = _fig_axes(8.2, 6.6)
        im = ax.imshow(pct, cmap="Blues", vmin=0, vmax=100)

        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=20, ha="right", color=_TEXT)
        ax.set_yticklabels(labels, color=_TEXT)
        ax.set_xlabel("Prediksi Model", color=_TEXT, fontsize=11)
        ax.set_ylabel("Kategori Aktual", color=_TEXT, fontsize=11)
        ax.set_title(f"Confusion Matrix — Klasifikasi Kategori Udara ({target.upper()}, "
                     f"Random Forest, {config.N_ESTIMATORS} pohon)",
                     color=_TEXT, fontsize=12, pad=12)

        for i in range(len(labels)):
            for j in range(len(labels)):
                color = "white" if pct[i, j] > 55 else _TEXT
                ax.text(j, i, f"{cm[i, j]}\n({pct[i, j]:.1f}%)",
                        ha="center", va="center", color=color, fontsize=9)

        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
        cbar.set_label("% dari total sampel", color=_SUBTEXT)
        cbar.ax.tick_params(colors=_SUBTEXT)
        _finish(fig, os.path.join(REPORTS_DIR, f"confusion_matrix_{target}_{stamp}.png"))

        # Classification report → file teks
        rep = classification_report(y_true, y_pred, labels=labels,
                                    zero_division=0, digits=3)
        txt = os.path.join(REPORTS_DIR, f"classification_report_{target}_{stamp}.txt")
        with open(txt, "w", encoding="utf-8") as f:
            f.write(f"CLASSIFICATION REPORT — Klasifikasi Kategori Udara ({target.upper()})\n")
            f.write(f"Dibuat  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Model   : RandomForestClassifier, n_estimators={config.N_ESTIMATORS}\n")
            f.write(f"Kategori: {', '.join(labels)}\n")
            f.write("-" * 62 + "\n")
            f.write(rep)
        print(f"[report] Tersimpan: {txt}")
        return rep
    except Exception as exc:
        print(f"[report] Gagal membuat confusion matrix {target}: {exc}")
        return None


# ---------------------------------------------------------------------------
# 2. FEATURE IMPORTANCE (bukti novelty tekanan udara)
# ---------------------------------------------------------------------------

def save_feature_importance(model, target="pm25", top=15, stamp=None):
    """Bar chart horizontal fitur terpenting; pressure_ diberi warna khusus."""
    try:
        stamp = stamp or _stamp()
        _ensure_dir()
        names = getattr(model, "feature_names_in_", None)
        importances = getattr(model, "feature_importances_", None)
        if names is None or importances is None:
            print("[report] Model tidak menyimpan feature_names — lewati")
            return None

        pairs = sorted(zip(names, importances), key=lambda t: -t[1])[:top]
        pairs = pairs[::-1]   # terbesar di atas saat barh
        labels = [n for n, _ in pairs]
        values = [float(s) for _, s in pairs]
        colors = [_ACCENT if n.startswith("pressure") else "#3b82f6"
                  for n in labels]

        fig, ax = _fig_axes(9.0, max(5.0, 0.38 * len(labels) + 1.6))
        ax.barh(labels, values, color=colors, edgecolor="none")
        ax.set_xlabel("Importance", color=_TEXT)
        ax.set_title(f"15 Fitur Terpenting — Model {target.upper()} "
                     "(cyan = tekanan udara / NOVELTY)", color=_TEXT, fontsize=12, pad=12)
        ax.grid(axis="x", color=_GRID)
        ax.tick_params(colors=_SUBTEXT, labelsize=8.5)
        for spine in ax.spines.values():
            spine.set_visible(False)
        _finish(fig, os.path.join(REPORTS_DIR, f"feature_importance_{target}_{stamp}.png"))
        return labels, values
    except Exception as exc:
        print(f"[report] Gagal membuat feature importance: {exc}")
        return None


# ---------------------------------------------------------------------------
# 3. AKTUAL vs PREDIKSI + RESIDUAL (analisis regresi)
# ---------------------------------------------------------------------------

def save_actual_vs_pred(y_true, y_pred, target, stamp=None):
    """Dua panel: scatter aktual vs prediksi (garis ideal y=x) + histogram residual."""
    try:
        stamp = stamp or _stamp()
        _ensure_dir()
        y_true = np.asarray(y_true, dtype=float)
        y_pred = np.asarray(y_pred, dtype=float)
        resid = y_true - y_pred

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.4), dpi=150)
        for ax in (ax1, ax2):
            fig.patch.set_facecolor(_BG)
            ax.set_facecolor(_PANEL)
            ax.tick_params(colors=_SUBTEXT)
            for spine in ax.spines.values():
                spine.set_color(_SUBTEXT)

        # Panel 1: scatter + garis y=x
        ax1.scatter(y_true, y_pred, s=14, alpha=0.55, color=_ACCENT,
                    edgecolors="none")
        lo = float(min(y_true.min(), y_pred.min()))
        hi = float(max(y_true.max(), y_pred.max()))
        pad = (hi - lo) * 0.05 or 1.0
        ax1.plot([lo - pad, hi + pad], [lo - pad, hi + pad],
                 color="#ef4444", linestyle="--", linewidth=1.2, label="Ideal (y = x)")
        ax1.set_xlim(lo - pad, hi + pad)
        ax1.set_ylim(lo - pad, hi + pad)
        ax1.set_xlabel("Nilai Aktual", color=_TEXT)
        ax1.set_ylabel("Nilai Prediksi", color=_TEXT)
        ax1.set_title(f"Aktual vs Prediksi — {target.upper()}", color=_TEXT, fontsize=12)
        ax1.grid(color=_GRID)
        leg = ax1.legend(facecolor=_PANEL, edgecolor=_SUBTEXT)
        for t in leg.get_texts():
            t.set_color(_TEXT)

        # Panel 2: histogram residual
        ax2.hist(resid, bins=30, color="#3b82f6", edgecolor=_PANEL)
        ax2.axvline(0, color="#ef4444", linestyle="--", linewidth=1.2)
        ax2.set_xlabel("Residual (Aktual − Prediksi)", color=_TEXT)
        ax2.set_ylabel("Frekuensi", color=_TEXT)
        ax2.set_title(f"Distribusi Residual — {target.upper()}", color=_TEXT, fontsize=12)
        ax2.grid(color=_GRID)

        path = os.path.join(REPORTS_DIR, f"actual_vs_pred_{target}_{stamp}.png")
        _finish(fig, path)
        return path
    except Exception as exc:
        print(f"[report] Gagal membuat grafik aktual vs prediksi {target}: {exc}")
        return None


# ---------------------------------------------------------------------------
# 4. LAPORAN TEKS GABUNGAN (bukti evaluasi siap lampir)
# ---------------------------------------------------------------------------

def save_text_report(results, split_info, stamp=None):
    """Simpan ringkasan metrik regresi + catatan split + novelty ke satu file."""
    try:
        stamp = stamp or _stamp()
        _ensure_dir()
        path = os.path.join(REPORTS_DIR, f"laporan_evaluasi_{stamp}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 64 + "\n")
            f.write("LAPORAN EVALUASI MODEL — sistem_fadlan\n")
            f.write("Sistem Monitoring dan Prediksi Kualitas Udara Berbasis IoT\n")
            f.write("=" * 64 + "\n")
            f.write(f"Waktu training : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Algoritma      : Random Forest (n_estimators={config.N_ESTIMATORS}, "
                    f"random_state={config.RANDOM_STATE})\n")
            f.write(f"Lag features   : {config.N_LAGS} step + fitur waktu (hour/dow sin-cos)\n")
            f.write(f"Split data     : {split_info}\n")
            f.write(f"Novelty        : tekanan udara barometrik (pressure_lag_*)\n")
            f.write("-" * 64 + "\n\n")

            f.write("A. EVALUASI REGRESI (prediksi 24 jam — target kontinu)\n")
            f.write(f"{'Target':<8}{'MAE':>10}{'RMSE':>10}{'R²':>10}\n")
            for target, m in results.items():
                f.write(f"{target.upper():<8}{m['mae']:>10.3f}{m['rmse']:>10.3f}{m['r2']:>10.3f}\n")

            f.write("\nB. EVALUASI KLASIFIKASI (kategori udara — classifier pendamping)\n")
            f.write("Lihat classification_report_<target>_<stamp>.txt dan\n")
            f.write("confusion_matrix_<target>_<stamp>.png di folder reports/\n")

            f.write("\nC. INTERPRETASI R² (PRD 12.5)\n")
            f.write("  >= 0.85 Baik | 0.70-0.84 Cukup | < 0.70 Perlu perbaikan\n")
        print(f"[report] Tersimpan: {path}")
        return path
    except Exception as exc:
        print(f"[report] Gagal menyimpan laporan teks: {exc}")
        return None
