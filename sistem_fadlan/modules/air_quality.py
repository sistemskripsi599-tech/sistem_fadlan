# =============================================================================
# modules/air_quality.py — Sumber kebenaran tunggal kategori kualitas udara
# 5 kategori sesuai standar ISPU KLHK (PermenLHK No. 14 Tahun 2020):
#   BAIK / SEDANG / TIDAK SEHAT / SANGAT TIDAK SEHAT / BERBAHAYA
# Berlaku nasional termasuk Kota Palu, Sulawesi Tengah.
# Dipakai oleh: routes/api.py (status dashboard), ml_trainer (label klasifikasi),
#               reporting (confusion matrix), telegram_bot (status pesan).
# =============================================================================

# Urutan = tingkat keparahan (indeks kecil = paling baik)
CATEGORIES = ["BAIK", "SEDANG", "TIDAK SEHAT", "SANGAT TIDAK SEHAT", "BERBAHAYA"]

COLORS = {
    "BAIK":               "green",
    "SEDANG":             "blue",
    "TIDAK SEHAT":        "yellow",
    "SANGAT TIDAK SEHAT": "red",
    "BERBAHAYA":          "gray",
}

# Breakpoint konsentrasi (μg/m³) — standar ISPU KLHK PermenLHK No. 14/2020:
#   PM2.5: <=15.5  Baik | <=55.4  Sedang | <=150.4 Tidak Sehat
#          <=250.4 Sangat Tidak Sehat     | > 250.4 Berbahaya
#   PM10 : <=50    Baik | <=150   Sedang | <=350   Tidak Sehat
#          <=420   Sangat Tidak Sehat     | > 420   Berbahaya
BANDS = {
    "pm25": [
        (15.5,  "BAIK"),
        (55.4,  "SEDANG"),
        (150.4, "TIDAK SEHAT"),
        (250.4, "SANGAT TIDAK SEHAT"),
    ],
    "pm10": [
        (50.0,  "BAIK"),
        (150.0, "SEDANG"),
        (350.0, "TIDAK SEHAT"),
        (420.0, "SANGAT TIDAK SEHAT"),
    ],
}


def categorize_pm25(value):
    """Kategori satu nilai PM2.5 → label kategori."""
    return _categorize("pm25", value)


def categorize_pm10(value):
    """Kategori satu nilai PM10 → label kategori."""
    return _categorize("pm10", value)


def _categorize(pollutant, value):
    if value is None:
        return None
    for limit, label in BANDS[pollutant]:
        if value <= limit:
            return label
    return "BERBAHAYA"


def worst_category(labels):
    """Dari beberapa label kategori, ambil yang paling parah."""
    present = [l for l in labels if l in CATEGORIES]
    if not present:
        return None
    return max(present, key=CATEGORIES.index)


def classify(value_pm25, value_pm10):
    """(label, color) status gabungan = kategori terburuk PM2.5 & PM10."""
    label = worst_category([categorize_pm25(value_pm25),
                            categorize_pm10(value_pm10)])
    if label is None:
        return "--", "slate"
    return label, COLORS[label]
