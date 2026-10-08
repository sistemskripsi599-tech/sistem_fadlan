# =============================================================================
# train_model.py — Entry point training model ML (PRD Section 8.3)
# Jalankan manual: python train_model.py
#
# Prasyarat:
#   1. data/ISPU_DKI_Jakarta_2021.csv (dataset sekunder) — kolom tanggal, PM2.5, PM10
#   2. Data primer di database/sistem_fadlan.db (dari sensor / seed_data.py)
#
# Output per sesi training:
#   models/*.pkl                  — 3 model regresi + 2 classifier kategori
#   reports/confusion_matrix_*.png — heatmap kategori (BAIK..BERBAHAYA)
#   reports/classification_report_*.txt — precision/recall/F1 per kategori
#   reports/feature_importance_*.png — 15 fitur terpenting (novelty pressure)
#   reports/actual_vs_pred_*.png  — scatter aktual vs prediksi + residual
#   reports/laporan_evaluasi_*.txt — ringkasan metrik siap lampir BAB IV
# =============================================================================

from modules.ml_trainer import train

if __name__ == "__main__":
    print("=" * 60)
    print("  TRAINING MODEL — Random Forest (Regresi + Klasifikasi Kategori)")
    print("=" * 60)
    try:
        results = train()
        print("-" * 60)
        for target, m in results.items():
            print(f"  {target.upper():5s}  MAE={m['mae']:.3f}  RMSE={m['rmse']:.3f}  R²={m['r2']:.3f}")
        print("-" * 60)
        print("  [OK] Training selesai. Model tersimpan di models/*.pkl")
        print("  [OK] Bukti evaluasi tersimpan di reports/ (confusion matrix,")
        print("       classification report, feature importance, aktual vs prediksi)")
        print("     Restart server (python run.py) untuk mengaktifkan prediksi.")
    except RuntimeError as exc:
        print(f"  [GAGAL] {exc}")
