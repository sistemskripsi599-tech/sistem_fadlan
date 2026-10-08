# =============================================================================
# seed_data.py — Entry point seeding data dummy (PRD Tahap 2)
# Data dummy profil: Kecamatan Buluri, Kota Palu (lihat modules/seed.py)
# Jalankan: python seed_data.py
# =============================================================================

from modules.seed import seed

if __name__ == "__main__":
    count = seed(clear=True)   # reset dulu agar idempotent saat pengujian
    print(f"[OK] Seed selesai: {count} record dummy profil Buluri dimasukkan")
