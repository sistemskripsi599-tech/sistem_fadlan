# =============================================================================
# backup.py — Backup data penting proyek sistem_fadlan
# Menyalin: database SQLite, model .pkl, config.py, folder reports/
# Tujuan: backups/backup_YYYY-MM-DD_HH-MM/
# Jalankan: python backup.py   (aman dijalankan berulang, tidak mengubah data)
#
# PENTING: jalankan backup ini SEBELUM training ulang, sebelum mengubah
# konfigurasi besar, atau sesekali saat data lapangan sudah mengalir.
# Folder backups/ sudah masuk .gitignore (tidak ikut ke repositori).
# =============================================================================

import os
import shutil
import sqlite3
from datetime import datetime

import config

BASE = config.BASE_DIR
DEST_ROOT = os.path.join(BASE, "backups")


def _backup_sqlite(dest):
    """Backup SQLite dengan cara aman (bukan sekadar copy file yang sedang dipakai)."""
    src = sqlite3.connect(config.DB_PATH)
    dst_path = os.path.join(dest, "sistem_fadlan.db")
    dst = sqlite3.connect(dst_path)
    src.backup(dst)            # API backup resmi sqlite3 — aman walau server hidup
    dst.close()
    src.close()
    # verifikasi hasil
    chk = sqlite3.connect(dst_path).execute("PRAGMA integrity_check").fetchone()[0]
    print(f"  [OK] database -> sistem_fadlan.db (integritas: {chk})")
    return chk == "ok"


def main():
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dest = os.path.join(DEST_ROOT, f"backup_{stamp}")
    os.makedirs(dest, exist_ok=True)
    print(f"Backup ke: {dest}")

    ok = True

    # 1. Database
    if os.path.exists(config.DB_PATH):
        ok = _backup_sqlite(dest) and ok
    else:
        print("  [!!] database tidak ditemukan")
        ok = False

    # 2. Model .pkl
    if os.path.isdir(config.MODELS_DIR):
        for f in os.listdir(config.MODELS_DIR):
            if f.endswith(".pkl"):
                shutil.copy2(os.path.join(config.MODELS_DIR, f), os.path.join(dest, f))
        print(f"  [OK] models -> {len([f for f in os.listdir(dest) if f.endswith('.pkl')])} file .pkl")
    else:
        print("  [--] folder models kosong (belum ada model) — lewati")

    # 3. config.py (file penting yang tidak di-commit)
    if os.path.exists(os.path.join(BASE, "config.py")):
        shutil.copy2(os.path.join(BASE, "config.py"), os.path.join(dest, "config.py"))
        print("  [OK] config.py")

    # 4. reports/ (bukti evaluasi BAB IV)
    rep_src = os.path.join(BASE, "reports")
    if os.path.isdir(rep_src) and os.listdir(rep_src):
        rep_dst = os.path.join(dest, "reports")
        shutil.copytree(rep_src, rep_dst)
        print(f"  [OK] reports -> {len(os.listdir(rep_dst))} artefak")

    # 5. docs/ (PRD + draft izin — kecil tapi penting)
    docs_src = os.path.join(BASE, "docs")
    if os.path.isdir(docs_src):
        docs_dst = os.path.join(dest, "docs")
        shutil.copytree(docs_src, docs_dst, ignore=shutil.ignore_patterns("_proposal_teks.txt"))
        print(f"  [OK] docs -> {len(os.listdir(docs_dst))} file")

    print()
    print(("[SELESAI] Backup berhasil." if ok else "[PERHATIAN] Backup ada bagian gagal — periksa di atas."))
    print("Saran: salin folder backups/ ke flashdisk / Google Drive secara berkala.")
    return ok


if __name__ == "__main__":
    main()
