# =============================================================================
# modules/seed.py — Seed data DUMMY ke tabel sensor_readings
# Tujuan: UI langsung terisi saat pengujian (PRD Tahap 2: 50 record).
# Data asli akan mengalir dari sensor via MQTT di Tahap 3.
# Jalankan: python seed_data.py
#
# CATATAN (keputusan 23 Sep 2026): nilai dummy dibuat sendiri dengan profil
# SEAKAN-AKAN dari Kecamatan Buluri, Kota Palu — semi-perkotaan padat
# kendaraan (PM2.5 dasar ± 38-58 μg/m³ sesuai rentang di proposal Bab I)
# dan iklim Palu: panas 27-33°C, lembap 60-80%, tekanan ±1008-1012 hPa.
# Untuk laporan skripsi, data NYATA dari lapangan (DLH Prov. Sulteng,
# sesuai proposal) yang dipakai — data ini hanya alat bantu demo/pengujian.
# =============================================================================

import math
import random
from datetime import datetime, timedelta

import config
from modules import database


def _rush_factor(hour):
    """Pola realistis: polusi naik jam sibuk 07-09 & 17-19, turun malam."""
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        return 1.35
    if hour >= 22 or hour <= 5:
        return 0.65
    return 1.0


def _diurnal(hour, peak_hour):
    """Faktor siklus harian sinus (-1..1), puncak pada peak_hour."""
    return math.sin(2 * math.pi * (hour - peak_hour) / 24.0)


def _make_reading(dt):
    """Satu record sensor dummy profil Buluri, Kota Palu pada waktu dt."""
    rush = _rush_factor(dt.hour)

    # Partikulat: dasar Buluri + lonjakan jam sibuk + noise
    pm25 = 46.0 * rush + random.uniform(-4, 6)
    pm10 = 80.0 * rush + random.uniform(-6, 10)
    # PM1.0 (monitoring saja): umumnya 55-75% dari PM2.5 pada udara perkotaan
    pm1_0 = pm25 * random.uniform(0.55, 0.75)

    # Cuaca mikro khas Palu (pesisir, tropis):
    #   suhu puncak ±14:00, kelembapan berlawanan dengan suhu,
    #   tekanan ±1010 hPa dengan osilasi harian lemah
    temp = 29.5 + 3.0 * _diurnal(dt.hour, 14) + random.uniform(-1.0, 1.0)
    hum = 71.0 - 8.0 * _diurnal(dt.hour, 14) + random.uniform(-4, 4)
    press = 1010.0 + 1.2 * _diurnal(dt.hour, 10) + random.uniform(-0.6, 0.6)

    return {
        "timestamp":   dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "pm1_0":       round(max(0.0, pm1_0), 1),
        "pm25":        round(max(0.0, pm25), 1),
        "pm10":        round(max(0.0, pm10), 1),
        "gas_raw":     random.randint(1600, 2100),
        "temperature": round(temp, 1),
        "humidity":    round(min(100.0, max(0.0, hum)), 1),
        "pressure":    round(press, 1),
    }


def seed(n=50, interval_seconds=30, clear=False):
    """Masukkan n record dummy. clear=True mengosongkan tabel dulu (alat uji).

    PENGAMAN DATA LAPANGAN: saat DATA_MODE='lapangan' (data asli alat sudah
    mengalir), pengecekan penghapusan ditolak agar data penelitian tidak
    hilang keliru. Gunakan clear hanya pada mode simulasi.
    """
    database.init_db()

    if clear and config.DATA_MODE == "lapangan":
        raise RuntimeError(
            "[seed] DITOLAK: DATA_MODE='lapangan' — tabel berisi data asli "
            "penelitian. Seed penghapus data tidak diizinkan. (Ubah DATA_MODE "
            "di config.py hanya jika benar-benar dimaksudkan.)"
        )

    conn = database.get_connection()
    try:
        existing = conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
        if clear and existing > 0:
            conn.execute("DELETE FROM sensor_readings")
            conn.commit()
            print(f"[seed] Tabel dikosongkan ({existing} record lama dihapus)")
    finally:
        conn.close()

    now = datetime.now().replace(second=0, microsecond=0)
    rows = [_make_reading(now - timedelta(seconds=interval_seconds * i))
            for i in range(n, 0, -1)]  # urut lama → baru

    conn = database.get_connection()
    try:
        conn.executemany(
            """INSERT INTO sensor_readings
               (timestamp, pm1_0, pm25, pm10, gas_raw, temperature, humidity, pressure)
               VALUES (:timestamp, :pm1_0, :pm25, :pm10, :gas_raw,
                       :temperature, :humidity, :pressure)""",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return len(rows)


if __name__ == "__main__":
    count = seed()
    print(f"[OK] Seed selesai: {count} record dummy profil Buluri dimasukkan")
