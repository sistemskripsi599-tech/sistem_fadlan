# PRODUCT REQUIREMENTS DOCUMENT (PRD)
# Sistem Monitoring dan Prediksi Kualitas Udara Berbasis IoT
## sistem_fadlan

---

| Atribut | Detail |
|---------|--------|
| **Nama Sistem** | sistem_fadlan |
| **Judul Penelitian** | Implementasi Algoritma Random Forest pada Sistem Monitoring dan Prediksi Kualitas Udara Berbasis Internet of Things |
| **Peneliti** | Moh. Fadlan Darul Aksa Nusu — NIM 20220302020 |
| **Institusi** | STMIK Bina Mulia Palu, Program Studi Teknik Informatika |
| **Versi PRD** | 1.2 — Final |
| **Tanggal** | 23 September 2026 |
| **Status** | ✅ Siap Implementasi |

> **⚠️ CATATAN PERUBAHAN SCOPE (v1.2 — mengikuti keputusan terbaru):**
> 1. **Notifikasi bot Telegram DIHAPUS dari scope.** Sistem adalah proyek kuliah, tanpa dependensi layanan eksternal. Pelanggaran ambang batas PM2.5/PM10 cukup **dicatat otomatis ke tabel `alert_log`** dan ditampilkan sebagai banner peringatan di dashboard. Konsekuensi: **Section 14 (Early Warning Telegram), FR-EW-04 s/d FR-EW-06, dan skenario uji T-12, T-13, T-14 dinyatakan tidak berlaku.**
> 2. **Objek penelitian adalah udara di sekitar Kelurahan Buluri, Kota Palu** (lokasi pemasangan alat) — **bukan** DLH, bukan BMKG. Data sekunder ISPU DKI Jakarta 2021 **hanya** berfungsi sebagai bahan latih awal model (data historis), bukan objek penelitian.
> 3. **Stakeholder "Staf DLH" diganti"warga/masyarakat sekitar Kelurahan Buluri"** sebagai pengguna utama.

> **📌 CATATAN PEMBARUAN SCOPE (v1.3 — 23 Sep 2026, keputusan dengan PM + mahasiswa):**
> 1. **Notifikasi Telegram KEMBALI ke scope** (sesuai proposal 1.5.2 & kerangka pikir 2.3) — dengan mode **"kode siap, belum dihubungkan"**: `TELEGRAM_ENABLED = False` di config.py. Saat pelanggaran ambang, pesan diformat lengkap (parameter, nilai, **persentase terhadap ambang**, status, saran tindakan) dan dicatat ke `alert_log` (kolom `sent_status`); tidak ada HTTP keluar. Untuk mengaktifkan: isi token/chat_id lalu ubah ke True.
> 2. **Parameter PM1.0 (PMS5003) ditambahkan — MONITORING SAJA** (kartu dashboard, grafik monitoring, kolom riwayat; payload MQTT field `pm1_0`). Tidak menjadi target prediksi & tidak masuk fitur ML — konsisten Batasan Masalah 1.3 proposal (prediksi hanya PM2.5, PM10, gas).
> 3. **Status udara: 4 kategori** (BAIK/SEDANG/TIDAK SEHAT/BERBAHAYA) dengan breakpoint kerangka ISPU per polutan — PM2.5: 15.5/55.4/150.4; PM10: 50/100/200 μg/m³. Status gabungan = kategori terburuk keduanya. Sumber logika tunggal: `modules/air_quality.py`.
> 4. **Baku mutu & ambang alert TETAP PP No. 22/2021** (PM2.5=55, PM10=75 per 24 jam) — Kota Palu memakai baku mutu nasional; tidak ada baku mutu lokal.
> 5. **Klasifikasi pendamping**: RandomForestClassifier kategori udara (n_estimators=100, class_weight balanced) menghasilkan confusion matrix + classification report sebagai bukti evaluasi tambahan BAB IV — regresi tetap algoritma utama untuk prediksi 24 jam.
> 6. **Artefak evaluasi otomatis** ke folder `reports/`: confusion_matrix_*.png, classification_report_*.txt, feature_importance_*.png (novelty pressure), actual_vs_pred_*.png, laporan_evaluasi_*.txt.
> 7. **Data latih dummy** profil Kecamatan Buluri, Kota Palu (PM2.5 dasar ±46, PM1.0 = 55–75% dari PM2.5, iklim Palu) — alat bantu demo/pengujian; laporan skripsi tetap memakai data nyata lapangan + dataset ISPU DKI Jakarta 2021 asli.
> 8. Database tetap SQLite & frontend tetap Tailwind (catatan skripsi: dipilih setara MySQL/Bootstrap untuk skala penelitian — konfirmasi pembimbing). Modul baru: `telegram_bot.py`, `air_quality.py`, `reporting.py`, `config.example.py`.
> 9. **MODE DATA TRANSPARAN (v1.4)** — `DATA_MODE` di config.py: `"simulasi"` (data buatan profil Buluri untuk pengembangan/uji, banner MODE SIMULASI tampil di semua halaman, hanya setelah izin TERTULIS pembimbing — lihat `docs/draft_izin_pembimbing.md`) atau `"lapangan"` (data asli alat; banner hilang; seed penghapus data otomatis DITOLAK agar data penelitian aman). **Hasil BAB IV wajib dari mode `"lapangan"`.**

---

## DAFTAR ISI

1. [Product Overview](#1-product-overview)
2. [Masalah yang Diselesaikan](#2-masalah-yang-diselesaikan)
3. [Target Pengguna](#3-target-pengguna)
4. [Scope dan Batasan Sistem](#4-scope-dan-batasan-sistem)
5. [Functional Requirements](#5-functional-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Arsitektur Sistem End-to-End](#7-arsitektur-sistem-end-to-end)
8. [Alur Data Lengkap](#8-alur-data-lengkap)
9. [Struktur Modul Backend](#9-struktur-modul-backend)
10. [Struktur Database SQLite](#10-struktur-database-sqlite)
11. [API Endpoints](#11-api-endpoints)
12. [Machine Learning Pipeline](#12-machine-learning-pipeline)
13. [Integrasi Hardware dan MQTT](#13-integrasi-hardware-dan-mqtt)
14. [Early Warning System](#14-early-warning-system)
15. [Struktur Halaman dan Fitur Dashboard](#15-struktur-halaman-dan-fitur-dashboard)
16. [User Flow](#16-user-flow)
17. [Validasi dan Error Handling](#17-validasi-dan-error-handling)
18. [Security Dasar](#18-security-dasar)
19. [Testing dan Acceptance Criteria](#19-testing-dan-acceptance-criteria)
20. [Tahapan Implementasi](#20-tahapan-implementasi)

---

## 1. PRODUCT OVERVIEW

### 1.1 Deskripsi Sistem

**sistem_fadlan** adalah sistem monitoring dan prediksi kualitas udara mikro berbasis Internet of Things (IoT) yang dibangun sebagai penelitian skripsi. Sistem mengintegrasikan sensor node fisik berbasis ESP32 yang dipasang di lokasi penelitian (sekitar Kelurahan Buluri, Kota Palu) untuk mengakuisisi data kualitas udara secara real-time, memproses dan menyimpannya di backend berbasis Python Flask + SQLite, menjalankan prediksi 24 jam ke depan menggunakan algoritma Random Forest Regression, serta menyajikan seluruh informasi melalui dashboard web interaktif; pelanggaran ambang batas dicatat otomatis di database (tanpa notifikasi eksternal).

### 1.2 Tujuan Sistem

> *"Merancang, mengimplementasikan, dan menguji kinerja sistem monitoring serta prediksi kualitas udara mikro berbasis IoT dengan menerapkan algoritma Random Forest Regression pada backend Flask untuk memproyeksikan konsentrasi polutan (PM2.5, PM10, dan gas pencemar) secara kontinu untuk 24 jam ke depan yang divisualisasikan melalui dashboard web interaktif dan early warning system berbasis bot Telegram."*

### 1.3 Novelty Akademik

Penggunaan variabel **tekanan udara barometrik** dari sensor BME280 sebagai fitur masukan baru dalam model Random Forest Regression — fitur yang belum digunakan pada penelitian-penelitian terdahulu yang dijadikan tinjauan pustaka.

### 1.4 Technology Stack (Final)

| Lapisan | Teknologi |
|---------|-----------|
| Firmware IoT | C++ / Arduino IDE |
| Hardware | ESP32 DevKit V1, PMS5003, MQ-135, BME280 |
| Komunikasi IoT | MQTT protocol — Paho-MQTT |
| MQTT Broker | Mosquitto (lokal, localhost) |
| Backend | Python 3.x + Flask |
| Database | SQLite |
| Machine Learning | Scikit-Learn, Pandas, NumPy, joblib |
| Frontend | HTML + Tailwind CSS (CDN) + Chart.js (CDN) |
| Notifikasi | Telegram Bot API |
| Editor | Visual Studio Code |
| Hardware Dev | Arduino IDE |

### 1.5 Keputusan Teknis Final

| Parameter | Keputusan |
|-----------|-----------|
| Interval kirim data sensor | **30 detik** |
| Threshold PM2.5 | **55.0 μg/m³** (PP No. 22/2021) |
| Threshold PM10 | **75.0 μg/m³** (PP No. 22/2021) |
| Gas MQ-135 (early warning) | **Monitoring saja — tidak trigger alert** |
| MQTT Broker | **Mosquitto lokal (localhost:1883)** |
| Server akses | **0.0.0.0:5000** (akses dari semua perangkat se-jaringan) |
| Dashboard akses | **Fully public, tanpa login** |
| Telegram penerima | **1 chat_id dikonfigurasi di config.py** |
| Cooldown alert | **30 menit per polutan** |
| Dataset sekunder | **ISPU DKI Jakarta 2021.csv** (asumsi kolom: tanggal, PM2.5, PM10) |
| Fitur cuaca untuk ML | **Dari data primer (sensor BME280)** |
| Train-test split | **80% training / 20% testing** |
| Lag features (N_LAGS) | **12** |
| Random Forest n_estimators | **100 pohon** |

---

## 2. MASALAH YANG DISELESAIKAN

### 2.1 Konteks Masalah

- Kota Palu mengalami peningkatan volume kendaraan bermotor rata-rata **7,8% per tahun**, dengan lebih dari **12.000 unit kendaraan/hari** pada jam puncak di arteri utama.
- Konsentrasi PM2.5 harian di perkotaan Palu pernah mencapai **38,5–58,2 μg/m³**, di mana angka 58,2 μg/m³ melampaui baku mutu nasional PP No. 22/2021 (55 μg/m³ per 24 jam).
- Paparan polutan berkelanjutan berpotensi memicu **ISPA dan gangguan respirasi** pada masyarakat.

### 2.2 Gap yang Ada Saat Ini

| Kondisi Eksisting | Dampak |
|-------------------|--------|
| Tidak ada stasiun pemantau mikro lokal | Fluktuasi polusi harian tidak terdokumentasi |
| Stasiun makro (BMKG/DLH) mahal dan terbatas | Tidak bisa memantau cakupan mikro pinggir jalan |
| Tidak ada telemetri otomatis | Instansi tidak bisa mengambil tindakan preventif |
| Tidak ada sistem prediksi tren polusi | Tidak ada proyeksi 24 jam ke depan |
| Tidak ada notifikasi otomatis | Masyarakat tidak mengetahui kondisi udara berbahaya |

### 2.3 Solusi yang Dibangun

| Komponen | Solusi |
|----------|--------|
| Sensor node IoT low-cost | Mengambil data PM2.5, PM10, gas, suhu, kelembapan, tekanan secara otomatis |
| Backend Flask + SQLite | Menyimpan dan memproses data time-series |
| Random Forest Regression | Memprediksi tren polutan 24 jam ke depan |
| Dashboard web | Diakses siapa saja via browser, real-time |
| Pencatatan pelanggaran batas (tabel alert_log + banner dashboard) | Peringatan dini saat polutan melampaui batas — tanpa Telegram |

---

## 3. TARGET PENGGUNA

| Pengguna | Peran | Kebutuhan Utama |
|----------|-------|-----------------|
| **Warga sekitar Kelurahan Buluri** | Pengguna utama | Lihat kondisi udara terkini, prediksi, dan catatan pelanggaran batas via browser |
| **Peneliti (Fadlan)** | Developer + operator | Kelola sistem, latih model, dokumentasi skripsi |
| **Perangkat IoT (ESP32)** | Aktor otomatis | Baca sensor dan kirim data tanpa intervensi manusia |

---

## 4. SCOPE DAN BATASAN SISTEM

### 4.1 Yang Termasuk dalam Scope

- Firmware ESP32: baca PMS5003 + MQ-135 + BME280, kirim via MQTT
- Backend Flask: MQTT subscriber + web server + inference engine
- Database SQLite: simpan data time-series, prediksi, alert log, metrik model
- ML Pipeline: preprocessing → training → evaluasi → inferensi prediksi 24 jam
- Dashboard web: 5 halaman (Dashboard, Monitoring, Prediksi, Evaluasi, Riwayat)
- Early warning system: bot Telegram untuk PM2.5 dan PM10
- Black Box Testing: 18 skenario uji fungsional

### 4.2 Yang Tidak Termasuk dalam Scope

- Lebih dari satu sensor node
- Sistem autentikasi / login pengguna
- Deployment ke server publik / VPS / cloud
- Kalibrasi MQ-135 ke satuan ppm (gas hanya ditampilkan sebagai indeks relatif)
- Integrasi data eksternal selain dataset ISPU DKI Jakarta 2021.csv
- Aplikasi mobile native (Android/iOS)
- Informasi lokasi fisik di dalam UI sistem

### 4.3 Batasan dari Proposal

1. ML: hanya **Random Forest Regression** — tidak ada algoritma lain
2. Parameter diprediksi: **PM2.5, PM10, gas polutan** saja
3. Horizon prediksi: **24 jam ke depan** secara kontinu
4. Hardware: **ESP32 + PMS5003 + MQ-135 + BME280** di atas breadboard
5. Koneksi: **Wi-Fi lokal instansi atau tethering**

---

## 5. FUNCTIONAL REQUIREMENTS

### 5.1 FR — Firmware IoT (ESP32)

| ID | Requirement | Prioritas |
|----|-------------|-----------|
| FR-IOT-01 | Firmware membaca PM2.5 dan PM10 dari PMS5003 via UART2 | Wajib |
| FR-IOT-02 | Firmware membaca suhu, kelembapan, tekanan dari BME280 via I2C | Wajib |
| FR-IOT-03 | Firmware membaca nilai gas (raw ADC 0–4095) dari MQ-135 via ADC | Wajib |
| FR-IOT-04 | Firmware mengemas semua nilai sensor ke format JSON payload | Wajib |
| FR-IOT-05 | Firmware menyertakan timestamp dari NTP server dalam payload | Wajib |
| FR-IOT-06 | Firmware terhubung ke Wi-Fi dan reconnect otomatis jika putus | Wajib |
| FR-IOT-07 | Firmware publish payload JSON ke MQTT Broker setiap **30 detik** | Wajib |
| FR-IOT-08 | Firmware reconnect ke MQTT Broker jika koneksi terputus | Wajib |

### 5.2 FR — Backend Flask

| ID | Requirement | Prioritas |
|----|-------------|-----------|
| FR-BE-01 | Backend subscribe ke MQTT Broker dan menerima data via daemon thread | Wajib |
| FR-BE-02 | Backend mem-parse dan memvalidasi payload JSON dari MQTT | Wajib |
| FR-BE-03 | Backend menyimpan data valid ke tabel `sensor_readings` SQLite | Wajib |
| FR-BE-04 | Backend memeriksa PM2.5 dan PM10 terhadap threshold setiap data masuk | Wajib |
| FR-BE-05 | Backend memicu notifikasi Telegram jika PM2.5 > 55 atau PM10 > 75 | Wajib |
| FR-BE-06 | Backend menyediakan endpoint `/api/realtime` untuk data sensor terkini | Wajib |
| FR-BE-07 | Backend menyediakan endpoint `/api/history` untuk data historis | Wajib |
| FR-BE-08 | Backend menyediakan endpoint `/api/chart-data` untuk data grafik | Wajib |
| FR-BE-09 | Backend menyediakan endpoint `/api/predict` untuk prediksi 24 jam | Wajib |
| FR-BE-10 | Backend menyediakan endpoint `/api/model-metrics` untuk metrik evaluasi | Wajib |
| FR-BE-11 | Backend melayani 5 halaman HTML via Flask routing | Wajib |

### 5.3 FR — Machine Learning

| ID | Requirement | Prioritas |
|----|-------------|-----------|
| FR-ML-01 | Pipeline memuat dataset sekunder ISPU DKI Jakarta 2021.csv | Wajib |
| FR-ML-02 | Pipeline memuat data primer dari tabel `sensor_readings` SQLite | Wajib |
| FR-ML-03 | Pipeline membangun lag features (N=12) dari data time-series | Wajib |
| FR-ML-04 | Pipeline melakukan preprocessing: missing values + outlier removal | Wajib |
| FR-ML-05 | Pipeline membagi data: 80% training, 20% testing (time-series split) | Wajib |
| FR-ML-06 | Pipeline melatih 3 model Random Forest terpisah: PM2.5, PM10, gas | Wajib |
| FR-ML-07 | Pipeline menghitung MAE, RMSE, R² untuk setiap model | Wajib |
| FR-ML-08 | Pipeline menyimpan ketiga model ke file `.pkl` via joblib | Wajib |
| FR-ML-09 | Inference engine memuat model `.pkl` dan menghasilkan prediksi 24 titik | Wajib |
| FR-ML-10 | Hasil prediksi 24 titik disimpan ke tabel `predictions` SQLite | Wajib |

### 5.4 FR — Dashboard Frontend

| ID | Requirement | Prioritas |
|----|-------------|-----------|
| FR-FE-01 | Dashboard menampilkan nilai sensor terkini (PM2.5, PM10, gas, suhu, kelembapan, tekanan) | Wajib |
| FR-FE-02 | Dashboard menampilkan badge status kualitas udara (Baik / Sedang / Berbahaya) | Wajib |
| FR-FE-03 | Dashboard menampilkan grafik real-time semua parameter (Chart.js line chart) | Wajib |
| FR-FE-04 | Dashboard menampilkan grafik prediksi PM2.5, PM10, gas untuk 24 jam ke depan | Wajib |
| FR-FE-05 | Dashboard menampilkan tabel metrik evaluasi model (MAE, RMSE, R²) | Wajib |
| FR-FE-06 | Dashboard menampilkan tabel riwayat data historis dengan filter tanggal | Wajib |
| FR-FE-07 | Dashboard dapat diakses via browser tanpa instalasi tambahan | Wajib |
| FR-FE-08 | Dashboard responsif di desktop, tablet, dan smartphone | Wajib |
| FR-FE-09 | Grafik real-time melakukan auto-polling setiap **30 detik** | Wajib |

### 5.5 FR — Early Warning System

| ID | Requirement | Prioritas |
|----|-------------|-----------|
| FR-EW-01 | Sistem cek PM2.5 terhadap threshold 55 μg/m³ (PP No. 22/2021) | Wajib |
| FR-EW-02 | Sistem cek PM10 terhadap threshold 75 μg/m³ (PP No. 22/2021) | Wajib |
| FR-EW-03 | Gas MQ-135 ditampilkan sebagai monitoring saja, tidak trigger alert | Wajib |
| FR-EW-04 | Bot Telegram mengirim notifikasi berisi: parameter, nilai saat ini, threshold, saran tindakan | Wajib |
| FR-EW-05 | Cooldown 30 menit antar notifikasi per polutan (anti-spam) | Wajib |
| FR-EW-06 | Setiap notifikasi terkirim dicatat ke tabel `alert_log` SQLite | Wajib |

---

## 6. NON-FUNCTIONAL REQUIREMENTS

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Akses via browser tanpa instalasi | 100% |
| NFR-02 | Dashboard responsif pada layar ≥ 320px hingga ≥ 1920px | Semua breakpoint |
| NFR-03 | Latency data dari sensor ke dashboard | < 60 detik (sesuai interval 30 detik + polling 30 detik) |
| NFR-04 | Backend Flask + MQTT listener stabil tanpa crash | Minimal 24 jam nonstop |
| NFR-05 | Inferensi prediksi 24 jam selesai dalam waktu wajar | < 5 detik |
| NFR-06 | Notifikasi Telegram terkirim setelah threshold terlampaui | < 30 detik |
| NFR-07 | Data sensor tersimpan tanpa duplikasi | Integritas 100% |
| NFR-08 | Sistem berjalan pada laptop: i5/i7, RAM 8–16 GB, Windows 11 | Ya |
| NFR-09 | Kode terdokumentasi dan mudah dipahami untuk keperluan skripsi | Readable |

---

## 7. ARSITEKTUR SISTEM END-TO-END

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LAYER 1 — HARDWARE IoT                         │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    ESP32 DevKit V1                            │  │
│  │                                                               │  │
│  │  PMS5003 ──(UART2: GPIO16/17)──► PM2.5, PM10 (μg/m³)        │  │
│  │  MQ-135  ──(ADC: GPIO34)───────► gas_raw (0–4095)            │  │
│  │  BME280  ──(I2C: GPIO21/22)────► suhu, kelembapan, tekanan   │  │
│  │                                                               │  │
│  │  Setiap 30 detik:                                             │  │
│  │    1. Baca semua sensor                                       │  │
│  │    2. Ambil timestamp dari NTP                                │  │
│  │    3. Kemas ke JSON payload                                   │  │
│  │    4. Publish ke MQTT Broker via Wi-Fi                        │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────│───────────────────────────────────────┘
                              │ Wi-Fi (TCP/IP)
                              ▼ MQTT publish
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 2 — MQTT BROKER                            │
│            Mosquitto — localhost:1883                               │
│            Topic: air_quality/node01                                │
└─────────────────────────────│───────────────────────────────────────┘
                              │ MQTT subscribe (Paho-MQTT)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 3 — BACKEND FLASK                          │
│                                                                     │
│  Thread 1: MQTT Listener (daemon)                                   │
│    ├─ Parse JSON payload                                            │
│    ├─ Validasi field dan tipe data                                  │
│    ├─ Simpan ke SQLite (sensor_readings)                            │
│    └─ Threshold check → trigger Telegram jika perlu                 │
│                                                                     │
│  Thread 2: Flask HTTP Server (0.0.0.0:5000)                         │
│    ├─ Route halaman HTML (Jinja2 templates)                         │
│    ├─ REST API endpoints (/api/*)                                   │
│    └─ Inference engine: load .pkl → prediksi 24 jam                 │
│                                                                     │
│  Script Terpisah: train_model.py                                    │
│    ├─ Load CSV sekunder + data primer SQLite                        │
│    ├─ Feature engineering + preprocessing                           │
│    ├─ Training 3 RF models                                          │
│    └─ Simpan ke models/*.pkl + metrik ke SQLite                     │
└─────────────────────────────│───────────────────────────────────────┘
                              │ read / write
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 4 — DATABASE SQLite                        │
│                                                                     │
│   sensor_readings  │  predictions  │  alert_log  │  model_metrics   │
└──────────┬─────────┴──────┬────────┴──────┬──────┴─────────────────┘
           │                │               │
           └────────────────┼───────────────┘
                            │ JSON via fetch()
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 5 — FRONTEND DASHBOARD                     │
│          HTML + Tailwind CSS (CDN) + Chart.js (CDN)                 │
│                                                                     │
│   / Dashboard  /monitoring  /prediction  /evaluation  /history      │
│                                                                     │
│   Auto-polling /api/* setiap 30 detik via JavaScript                │
└─────────────────────────────│───────────────────────────────────────┘
                              │ saat threshold PM2.5/PM10 terlampaui
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 6 — TELEGRAM BOT API                       │
│         Notifikasi dikirim ke chat_id yang dikonfigurasi            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. ALUR DATA LENGKAP

### 8.1 Alur Data Real-time (Monitoring)

```
1.  ESP32 baca semua sensor setiap 30 detik
2.  ESP32 sync timestamp dari NTP server
3.  ESP32 kemas JSON payload:
    {
      "node_id"     : "node01",
      "timestamp"   : "2026-09-23T10:00:00",
      "pm25"        : 42.5,
      "pm10"        : 78.3,
      "gas_raw"     : 1820,
      "temperature" : 31.2,
      "humidity"    : 68.5,
      "pressure"    : 1012.4
    }
4.  ESP32 publish ke topic: air_quality/node01
5.  Mosquitto broker meneruskan ke subscriber
6.  Flask MQTT listener (daemon thread) menerima pesan
7.  Parse JSON → validasi semua field
8.  Simpan ke tabel sensor_readings (SQLite)
9.  Threshold check:
      - PM2.5 > 55.0? → trigger alert
      - PM10  > 75.0? → trigger alert
      - Gas: hanya simpan, tidak cek threshold
10. Jika trigger alert:
      - Cek cooldown (30 menit) → jika lewat, kirim Telegram
      - Catat ke tabel alert_log
11. Dashboard frontend polling /api/realtime setiap 30 detik
12. Flask API query sensor_readings → return JSON ke browser
13. JavaScript update kartu nilai + grafik Chart.js
```

### 8.2 Alur Prediksi 24 Jam (ML Inference)

```
1.  User buka halaman /prediction atau browser request GET /api/predict
2.  Flask inference engine:
    a.  Query sensor_readings: ambil 12 data terbaru (N_LAGS = 12)
    b.  Bangun lag feature vector dari data tersebut
    c.  Load: models/pm25_model.pkl
              models/pm10_model.pkl
              models/gas_model.pkl
    d.  Recursive forecasting 24 langkah:
        window = [12 data aktual terakhir]
        for step in 1..24:
            feature_vector = build_features(window)
            pm25_pred = model_pm25.predict(feature_vector)
            pm10_pred = model_pm10.predict(feature_vector)
            gas_pred  = model_gas.predict(feature_vector)
            simpan hasil ke predictions[]
            geser window (masukkan hasil prediksi)
    e.  Simpan 24 titik ke tabel predictions (SQLite)
    f.  Return JSON array 24 titik ke browser
3.  JavaScript render grafik prediksi (area chart Chart.js)
```

### 8.3 Alur Training Model (Script Terpisah, Jalankan Manual)

```
1.  Jalankan: python train_model.py
2.  Load data/ISPU_DKI_Jakarta_2021.csv
    → Identifikasi kolom yang tersedia (PM2.5, PM10)
    → Mapping ke skema fitur
3.  Load data primer dari SQLite (sensor_readings)
    → Gabungkan dengan data sekunder
4.  Preprocessing:
    a. Resample ke interval seragam (per 30 menit atau per jam)
    b. Handle missing values: interpolasi linear untuk gap kecil, drop untuk gap besar
    c. Hapus outlier: IQR method
    d. Tidak perlu normalisasi (RF tidak membutuhkan)
5.  Feature engineering:
    a. Lag features: pm25_lag_1..12, pm10_lag_1..12, gas_lag_1..12,
                     temp_lag_1..12, hum_lag_1..12, pressure_lag_1..12
    b. Fitur waktu (cyclical):
       hour_sin = sin(2π × hour / 24)
       hour_cos = cos(2π × hour / 24)
       dow_sin  = sin(2π × day_of_week / 7)
       dow_cos  = cos(2π × day_of_week / 7)
6.  Time-series split: 80% train (data awal), 20% test (data akhir)
7.  Training:
    model_pm25 = RandomForestRegressor(n_estimators=100, random_state=42)
    model_pm10 = RandomForestRegressor(n_estimators=100, random_state=42)
    model_gas  = RandomForestRegressor(n_estimators=100, random_state=42)
8.  Evaluasi setiap model: MAE, RMSE, R²
9.  Simpan model:
    models/pm25_model.pkl
    models/pm10_model.pkl
    models/gas_model.pkl
10. Simpan metrik evaluasi ke tabel model_metrics (SQLite)
11. Cetak laporan evaluasi ke terminal
```

---

## 9. STRUKTUR MODUL BACKEND

### 9.1 Struktur Folder Project

```
sistem_fadlan/
│
├── app.py                    # Inisialisasi Flask app
├── config.py                 # Semua konfigurasi (MQTT, Telegram, threshold, path)
├── run.py                    # Entry point: start Flask + MQTT thread bersamaan
├── train_model.py            # Script training model (jalankan manual)
│
├── modules/
│   ├── __init__.py
│   ├── database.py           # Koneksi SQLite, semua fungsi CRUD
│   ├── mqtt_listener.py      # Paho-MQTT daemon thread
│   ├── preprocessor.py       # Cleaning, missing values, outlier removal
│   ├── feature_engineer.py   # Lag features + time features
│   ├── ml_trainer.py         # Training + evaluasi 3 model RF
│   ├── ml_inference.py       # Load .pkl + recursive forecasting 24 jam
│   └── telegram_bot.py       # Kirim notifikasi + cooldown logic
│
├── routes/
│   ├── __init__.py
│   ├── pages.py              # Route halaman HTML
│   └── api.py                # Route REST API endpoints
│
├── models/                   # File .pkl hasil training
│   ├── pm25_model.pkl
│   ├── pm10_model.pkl
│   └── gas_model.pkl
│
├── data/
│   └── ISPU_DKI_Jakarta_2021.csv
│
├── database/
│   └── sistem_fadlan.db      # File SQLite
│
├── static/
│   └── favicon.ico           # (opsional)
│
└── templates/
    ├── base.html             # Layout dasar (navbar, Tailwind CDN, Chart.js CDN)
    ├── dashboard.html        # Halaman utama
    ├── monitoring.html       # Grafik real-time
    ├── prediction.html       # Grafik prediksi 24 jam
    ├── evaluation.html       # Tabel metrik model
    └── history.html          # Tabel riwayat data
```

### 9.2 Deskripsi Setiap Modul

#### `config.py`
Menyimpan semua konfigurasi yang dapat diubah tanpa menyentuh kode logika:

```python
# MQTT
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC       = "air_quality/node01"

# Telegram
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID   = "YOUR_CHAT_ID"

# Threshold (PP No. 22/2021)
THRESHOLD_PM25   = 55.0   # μg/m³
THRESHOLD_PM10   = 75.0   # μg/m³
ALERT_COOLDOWN   = 30     # menit

# Database
DB_PATH = "database/sistem_fadlan.db"

# Machine Learning
N_LAGS         = 12
N_ESTIMATORS   = 100
RANDOM_STATE   = 42
MODELS_DIR     = "models/"
DATA_DIR       = "data/"
```

#### `modules/database.py`
- `init_db()` — buat semua tabel jika belum ada
- `insert_reading(data)` — simpan satu record sensor
- `get_latest_reading()` — ambil 1 data terbaru
- `get_recent_readings(n)` — ambil N data terbaru (untuk ML inference)
- `get_readings(limit, offset, start_date, end_date)` — data historis
- `save_predictions(predictions_list)` — simpan hasil prediksi 24 titik
- `get_latest_predictions()` — ambil prediksi terbaru
- `log_alert(pollutant, value, threshold, message)` — catat alert
- `save_model_metrics(target, mae, rmse, r2)` — simpan metrik
- `get_model_metrics()` — ambil semua metrik terbaru

#### `modules/mqtt_listener.py`
- Class `MQTTListener(threading.Thread)` dengan `daemon=True`
- `on_connect` — log sukses, subscribe ke topic
- `on_message` — parse JSON → validasi → `insert_reading()` → `check_threshold()`
- `on_disconnect` — log + reconnect otomatis
- `check_threshold(data)` — cek PM2.5 dan PM10, panggil Telegram jika perlu

#### `modules/ml_inference.py`
- `load_models()` — load ketiga .pkl saat Flask start, simpan di memori
- `build_feature_vector(df_recent)` — buat lag + time features dari data terbaru
- `predict_24h()` — recursive forecasting 24 langkah, return list 24 dict

#### `modules/telegram_bot.py`
- `last_alert_time = {"pm25": None, "pm10": None}`
- `should_send_alert(pollutant)` — cek cooldown 30 menit
- `send_alert(pollutant, value, threshold)` — format pesan + kirim via requests
- `format_message(pollutant, value, threshold)` — return string pesan Telegram

---

## 10. STRUKTUR DATABASE SQLite

### Tabel `sensor_readings`

```sql
CREATE TABLE IF NOT EXISTS sensor_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,   -- ISO 8601: "2026-09-23T10:00:00"
    pm25        REAL    NOT NULL,   -- μg/m³
    pm10        REAL    NOT NULL,   -- μg/m³
    gas_raw     INTEGER NOT NULL,   -- raw ADC value (0–4095)
    temperature REAL    NOT NULL,   -- °C
    humidity    REAL    NOT NULL,   -- % RH
    pressure    REAL    NOT NULL    -- hPa
);

CREATE INDEX IF NOT EXISTS idx_sr_timestamp ON sensor_readings(timestamp);
```

### Tabel `predictions`

```sql
CREATE TABLE IF NOT EXISTS predictions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at  TEXT NOT NULL,   -- kapan prediksi dibuat
    target_hour   TEXT NOT NULL,   -- jam yang diprediksi
    pm25_pred     REAL,            -- prediksi PM2.5 (μg/m³)
    pm10_pred     REAL,            -- prediksi PM10 (μg/m³)
    gas_pred      REAL             -- prediksi gas (skala relatif ADC)
);

CREATE INDEX IF NOT EXISTS idx_pred_generated ON predictions(generated_at);
```

### Tabel `alert_log`

```sql
CREATE TABLE IF NOT EXISTS alert_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    triggered_at TEXT NOT NULL,
    pollutant    TEXT NOT NULL,    -- 'pm25' atau 'pm10'
    value        REAL NOT NULL,    -- nilai saat alert
    threshold    REAL NOT NULL,    -- nilai threshold
    message_sent TEXT              -- isi pesan yang dikirim
);
```

### Tabel `model_metrics`

```sql
CREATE TABLE IF NOT EXISTS model_metrics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trained_at   TEXT NOT NULL,
    model_target TEXT NOT NULL,    -- 'pm25', 'pm10', 'gas'
    mae          REAL NOT NULL,
    rmse         REAL NOT NULL,
    r2_score     REAL NOT NULL,
    n_estimators INTEGER,
    n_lags       INTEGER
);
```

---

## 11. API ENDPOINTS

Semua endpoint API mengembalikan `Content-Type: application/json`.

### 11.1 Endpoint Data Sensor

| Method | Endpoint | Deskripsi | Parameter |
|--------|----------|-----------|-----------|
| GET | `/api/realtime` | Data sensor terbaru (1 record) + status udara | — |
| GET | `/api/chart-data` | Array N data terbaru untuk grafik | `?limit=50` |
| GET | `/api/history` | Data historis dengan filter + pagination | `?limit=50&offset=0&start=YYYY-MM-DD&end=YYYY-MM-DD` |

**Response `/api/realtime`:**
```json
{
  "status": "ok",
  "data": {
    "timestamp"        : "2026-09-23T10:00:00",
    "pm25"             : 42.5,
    "pm10"             : 78.3,
    "gas_raw"          : 1820,
    "temperature"      : 31.2,
    "humidity"         : 68.5,
    "pressure"         : 1012.4,
    "air_quality_label": "SEDANG",
    "air_quality_color": "yellow"
  }
}
```

**Logika status udara:**
```
PM2.5 ≤ 15           → BAIK     (green)
PM2.5 > 15 dan ≤ 55  → SEDANG   (yellow)
PM2.5 > 55           → BERBAHAYA (red)
```

**Response `/api/history`:**
```json
{
  "status" : "ok",
  "total"  : 2880,
  "limit"  : 50,
  "offset" : 0,
  "data"   : [
    { "timestamp": "...", "pm25": 42.5, "pm10": 78.3, "gas_raw": 1820,
      "temperature": 31.2, "humidity": 68.5, "pressure": 1012.4 }
  ]
}
```

### 11.2 Endpoint Prediksi

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/predict` | Jalankan inferensi + kembalikan 24 titik prediksi |

**Response `/api/predict`:**
```json
{
  "status"       : "ok",
  "generated_at" : "2026-09-23T10:05:00",
  "predictions"  : [
    {
      "target_hour" : "2026-09-23T10:30:00",
      "pm25_pred"   : 44.1,
      "pm10_pred"   : 80.2,
      "gas_pred"    : 1890.0
    }
  ]
}
```

**Response jika model belum tersedia:**
```json
{
  "status"  : "model_not_ready",
  "message" : "Model belum dilatih. Jalankan train_model.py terlebih dahulu."
}
```

### 11.3 Endpoint Evaluasi Model

| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| GET | `/api/model-metrics` | Metrik evaluasi model terbaru |

**Response `/api/model-metrics`:**
```json
{
  "status"     : "ok",
  "trained_at" : "2026-09-23T08:00:00",
  "metrics"    : [
    { "target": "pm25", "mae": 3.21, "rmse": 4.87, "r2": 0.89 },
    { "target": "pm10", "mae": 5.14, "rmse": 7.22, "r2": 0.86 },
    { "target": "gas",  "mae": 89.0, "rmse": 120.5, "r2": 0.78 }
  ]
}
```

### 11.4 Route Halaman HTML

| Method | Endpoint | Halaman |
|--------|----------|---------|
| GET | `/` | Dashboard utama |
| GET | `/monitoring` | Grafik real-time |
| GET | `/prediction` | Grafik prediksi 24 jam |
| GET | `/evaluation` | Tabel evaluasi model |
| GET | `/history` | Tabel riwayat data |

---

## 12. MACHINE LEARNING PIPELINE

### 12.1 Dataset

**Dataset Sekunder:**
- File: `data/ISPU_DKI_Jakarta_2021.csv`
- Kolom yang digunakan: `tanggal`, `PM2.5`, `PM10`
- Catatan: dataset ini tidak memiliki kolom cuaca (suhu, kelembapan, tekanan) — fitur cuaca hanya berasal dari data primer

**Dataset Primer:**
- Sumber: tabel `sensor_readings` SQLite
- Kolom: `timestamp`, `pm25`, `pm10`, `gas_raw`, `temperature`, `humidity`, `pressure`
- Mulai tersedia setelah hardware dipasang dan sistem berjalan

**Strategi Penggabungan:**
- Dataset sekunder digunakan sebagai base training historis (sebelum data primer cukup)
- Dataset primer ditambahkan dan digabung untuk meningkatkan representasi kondisi lokal
- Kolom yang tidak ada di dataset sekunder (suhu, kelembapan, tekanan, gas) diisi dengan median dari data primer pada fase merge

### 12.2 Feature Engineering

```
Dari data time-series dengan interval seragam:

Lag features (N_LAGS = 12):
  pm25_lag_1 .. pm25_lag_12
  pm10_lag_1 .. pm10_lag_12
  gas_lag_1  .. gas_lag_12
  temp_lag_1 .. temp_lag_12
  hum_lag_1  .. hum_lag_12
  press_lag_1.. press_lag_12   ← FITUR NOVELTY (tekanan udara)

Fitur waktu (cyclical encoding):
  hour_sin = sin(2π × hour / 24)
  hour_cos = cos(2π × hour / 24)
  dow_sin  = sin(2π × day_of_week / 7)
  dow_cos  = cos(2π × day_of_week / 7)

Total fitur per sampel: 12×6 lag + 4 waktu = 76 fitur
```

### 12.3 Preprocessing

```
1. Resample ke interval seragam (30 menit via mean aggregation)
2. Handle missing values:
   - Gap ≤ 3 interval → interpolasi linear
   - Gap > 3 interval → drop rows
3. Hapus outlier (IQR method):
   - Nilai di luar [Q1 - 1.5×IQR, Q3 + 1.5×IQR] → replace NaN → interpolasi
4. Normalisasi: TIDAK dilakukan (Random Forest tidak memerlukan)
5. Time-series split (bukan random):
   - 80% data awal → training set
   - 20% data akhir → testing set
```

### 12.4 Training

```python
from sklearn.ensemble import RandomForestRegressor
import joblib

model_pm25 = RandomForestRegressor(n_estimators=100, random_state=42)
model_pm10 = RandomForestRegressor(n_estimators=100, random_state=42)
model_gas  = RandomForestRegressor(n_estimators=100, random_state=42)

model_pm25.fit(X_train, y_pm25_train)
model_pm10.fit(X_train, y_pm10_train)
model_gas.fit(X_train,  y_gas_train)

joblib.dump(model_pm25, "models/pm25_model.pkl")
joblib.dump(model_pm10, "models/pm10_model.pkl")
joblib.dump(model_gas,  "models/gas_model.pkl")
```

### 12.5 Evaluasi

```python
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2   = r2_score(y_test, y_pred)
```

Interpretasi R²:
- `≥ 0.85` → Baik (badge hijau di dashboard)
- `0.70 – 0.84` → Cukup (badge kuning)
- `< 0.70` → Perlu peningkatan (badge merah)

### 12.6 Inferensi Prediksi 24 Jam (Recursive Forecasting)

```python
def predict_24h():
    # Ambil 12 data terbaru dari database
    df_recent = get_recent_readings(N_LAGS)

    window = df_recent.copy()
    predictions = []
    current_time = datetime.now()

    for step in range(24):
        feature_vector = build_feature_vector(window)
        pm25 = model_pm25.predict([feature_vector])[0]
        pm10 = model_pm10.predict([feature_vector])[0]
        gas  = model_gas.predict([feature_vector])[0]

        target_hour = current_time + timedelta(hours=step+1)
        predictions.append({
            "target_hour" : target_hour.isoformat(),
            "pm25_pred"   : round(pm25, 2),
            "pm10_pred"   : round(pm10, 2),
            "gas_pred"    : round(gas, 2)
        })

        # Geser window: masukkan prediksi, buang yang paling lama
        new_row = create_synthetic_row(pm25, pm10, gas, target_hour)
        window = pd.concat([window.iloc[1:], new_row])

    save_predictions(predictions)
    return predictions
```

### 12.7 Catatan MQ-135

- Output MQ-135 yang disimpan adalah **raw ADC integer (0–4095)**
- Digunakan sebagai fitur input ML (konsisten karena dari sensor yang sama)
- Ditampilkan di dashboard dengan label **"Indeks Gas (Relatif)"**
- Tidak digunakan untuk trigger alert Telegram
- Untuk dokumentasi skripsi: catat range ADC empiris dari eksperimen lapangan sebagai "kalibrasi observasional"

---

## 13. INTEGRASI HARDWARE DAN MQTT

### 13.1 Wiring ESP32

| Sensor | Pin Sensor | Pin ESP32 | Protokol |
|--------|-----------|-----------|----------|
| PMS5003 | TX | GPIO 16 (RX2) | UART2 |
| PMS5003 | RX | GPIO 17 (TX2) | UART2 |
| PMS5003 | VCC | 5V | Power |
| PMS5003 | GND | GND | Ground |
| BME280 | SDA | GPIO 21 | I2C |
| BME280 | SCL | GPIO 22 | I2C |
| BME280 | VCC | 3.3V | Power |
| BME280 | GND | GND | Ground |
| MQ-135 | AOUT | GPIO 34 (ADC1_CH6) | ADC |
| MQ-135 | VCC | 5V | Power |
| MQ-135 | GND | GND | Ground |
| Adaptor 5V | (+) | VIN | Power |

> GPIO 34 digunakan karena merupakan input-only pin ADC yang bersih untuk pembacaan analog.

### 13.2 Konfigurasi MQTT

| Parameter | Nilai |
|-----------|-------|
| Broker | Mosquitto — localhost:1883 |
| Protocol | MQTT v3.1.1 |
| Topic | `air_quality/node01` |
| QoS | 1 (at least once) |
| Client ID ESP32 | `esp32_node01` |
| Client ID Flask | `flask_subscriber` |
| Clean Session | True |
| TLS | Tidak (jaringan lokal) |

### 13.3 Format JSON Payload (Final)

```json
{
  "node_id"     : "node01",
  "timestamp"   : "2026-09-23T10:00:00",
  "pm25"        : 42.5,
  "pm10"        : 78.3,
  "gas_raw"     : 1820,
  "temperature" : 31.2,
  "humidity"    : 68.5,
  "pressure"    : 1012.4
}
```

### 13.4 Pseudocode Firmware ESP32

```
setup():
  init Serial (115200 baud)
  init UART2 (9600 baud) untuk PMS5003
  init I2C (GPIO21, GPIO22) untuk BME280
  init ADC GPIO34 untuk MQ-135
  connect WiFi (SSID, password)
  sync NTP (pool.ntp.org)
  connect MQTT (localhost:1883, client_id="esp32_node01")
  set timer interval = 30 detik

loop():
  if WiFi putus  → reconnect WiFi
  if MQTT putus  → reconnect MQTT
  if timer tercapai (30 detik):
    pm25, pm10 = baca PMS5003 via UART2
    temp, hum, press = baca BME280 via I2C
    gas_raw = analogRead(GPIO34)
    ts = getNTPTime()
    payload = buildJSON(node01, ts, pm25, pm10, gas_raw, temp, hum, press)
    mqttClient.publish("air_quality/node01", payload, qos=1)
    reset timer
```

---

## 14. EARLY WARNING SYSTEM

### 14.1 Konfigurasi

| Parameter | Nilai |
|-----------|-------|
| Library | `requests` (HTTP POST ke Telegram API) |
| Endpoint | `https://api.telegram.org/bot{TOKEN}/sendMessage` |
| Bot Token | Dikonfigurasi di `config.py` — `TELEGRAM_BOT_TOKEN` |
| Chat ID | Dikonfigurasi di `config.py` — `TELEGRAM_CHAT_ID` |
| Cooldown | 30 menit per polutan |

### 14.2 Threshold

| Polutan | Threshold | Dasar | Trigger Alert |
|---------|-----------|-------|---------------|
| PM2.5 | 55.0 μg/m³ | PP No. 22 Tahun 2021 | ✅ Ya |
| PM10 | 75.0 μg/m³ | PP No. 22 Tahun 2021 | ✅ Ya |
| Gas MQ-135 | — | Tidak ada standar baku | ❌ Tidak |

### 14.3 Logika Cooldown

```python
last_alert_time = {"pm25": None, "pm10": None}

def check_threshold(data):
    pollutants = {
        "pm25": (data["pm25"], THRESHOLD_PM25),
        "pm10": (data["pm10"], THRESHOLD_PM10),
    }
    for pollutant, (value, threshold) in pollutants.items():
        if value > threshold:
            if should_send_alert(pollutant):
                send_alert(pollutant, value, threshold)
                last_alert_time[pollutant] = datetime.now()
                log_alert(pollutant, value, threshold)

def should_send_alert(pollutant):
    if last_alert_time[pollutant] is None:
        return True
    elapsed = (datetime.now() - last_alert_time[pollutant]).seconds / 60
    return elapsed >= ALERT_COOLDOWN  # 30 menit
```

### 14.4 Format Pesan Notifikasi Telegram

```
⚠️ PERINGATAN KUALITAS UDARA

🌫️ Parameter   : PM2.5
📊 Nilai Saat Ini : 67.3 μg/m³
⚠️ Ambang Batas  : 55.0 μg/m³
🔴 Status        : MELEBIHI BATAS AMAN

🕐 Waktu: Rabu, 23 Sep 2026 — 10:32 WIB

⚕️ Saran Tindakan:
• Kurangi aktivitas fisik di luar ruangan
• Gunakan masker jika harus keluar
• Tutup ventilasi sementara jika memungkinkan

— sistem_fadlan 🌿
```

---

## 15. STRUKTUR HALAMAN DAN FITUR DASHBOARD

### 15.1 Design System

#### Palet Warna (Dark Mode — Profesional)

| Elemen | Kelas Tailwind | Keterangan |
|--------|----------------|------------|
| Background halaman | `bg-slate-900` | Hitam kebiruan — terasa tech |
| Background card | `bg-slate-800` | Satu tingkat lebih terang |
| Background card hover | `bg-slate-700` | Interaktif |
| Accent utama | `text-cyan-400` / `bg-cyan-500` | Teknologi, IoT |
| Accent sekunder | `text-blue-400` / `bg-blue-500` | Data, grafik |
| Status BAIK | `bg-green-500` / `text-green-400` | |
| Status SEDANG | `bg-yellow-500` / `text-yellow-400` | |
| Status BERBAHAYA | `bg-red-500` / `text-red-400` | |
| Teks utama | `text-slate-100` | |
| Teks sekunder | `text-slate-400` | Label, subtitle |
| Border | `border-slate-700` | Divider antar elemen |
| Gradient header | `from-slate-900 via-slate-800 to-slate-900` | |

#### Komponen UI

- **Cards** — `rounded-xl border border-slate-700 bg-slate-800 shadow-lg`
- **Badge status** — `rounded-full px-3 py-1 text-xs font-semibold`
- **Grafik** — Chart.js dengan background `transparent`, grid `rgba(255,255,255,0.05)`
- **Tabel** — header `bg-slate-700`, baris alternating `bg-slate-800/50`
- **Navbar** — `fixed top-0 bg-slate-900/95 backdrop-blur border-b border-slate-700`
- **Tombol** — `bg-cyan-500 hover:bg-cyan-400 text-white rounded-lg`

#### Tipografi
- Font: `font-sans` (sistem default Tailwind — Inter/system-ui)
- Nilai sensor besar: `text-4xl font-bold text-white`
- Label: `text-sm font-medium text-slate-400 uppercase tracking-wider`
- Heading halaman: `text-2xl font-bold text-slate-100`

### 15.2 Navbar (Fixed Top)

```
┌─────────────────────────────────────────────────────────────────────┐
│  🌿 sistem_fadlan    Dashboard  Monitoring  Prediksi                 │
│                      Evaluasi   Riwayat               ● Live        │
└─────────────────────────────────────────────────────────────────────┘
```

- Indikator `● Live` — hijau berkedip saat data masuk, merah jika tidak ada data baru >2 menit
- Halaman aktif: underline cyan atau teks `text-cyan-400`
- Mobile: hamburger menu dengan slide-down drawer
- Backdrop blur saat scroll: `backdrop-blur-md`

### 15.3 Halaman 1 — Dashboard Utama (`/`)

**Section 1: Status Bar**
```
┌─────────────────────────────────────────────────────────────────────┐
│  🕐 Terakhir diperbarui: 23 Sep 2026, 10:32 WIB                     │
│  Status Kualitas Udara: ● SEDANG          Sensor: ● Aktif           │
└─────────────────────────────────────────────────────────────────────┘
```

**Section 2: Kartu Nilai Sensor (6 kartu — grid 3×2 desktop, 2×3 tablet, 1×6 mobile)**

```
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│    PM2.5       │  │     PM10       │  │  Indeks Gas    │
│  ──────────    │  │  ──────────    │  │  ──────────    │
│    42.5        │  │    78.3        │  │    1820        │
│    μg/m³       │  │    μg/m³       │  │   (Relatif)    │
│  ● SEDANG      │  │  ⚠ TINGGI     │  │  ─ ─ ─ ─ ─     │
└────────────────┘  └────────────────┘  └────────────────┘

┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│     Suhu       │  │  Kelembapan    │  │   Tekanan      │
│  ──────────    │  │  ──────────    │  │  ──────────    │
│    31.2        │  │    68.5        │  │   1012.4       │
│     °C         │  │      %         │  │     hPa        │
└────────────────┘  └────────────────┘  └────────────────┘
```

- Kartu PM2.5, PM10, Gas: memiliki badge status berwarna
- Kartu cuaca (suhu, kelembapan, tekanan): tanpa badge — hanya info
- Kartu PM10 = merah tipis jika > 75
- Setiap kartu memiliki ikon kecil di pojok kiri atas

**Section 3: Alert Banner (Conditional)**
- Hanya muncul jika ada polutan melebihi threshold
- Kotak merah dengan gradient: `bg-red-900/50 border border-red-500`
- Teks: "⚠️ PM2.5 saat ini 67.3 μg/m³ — Melebihi batas aman 55.0 μg/m³"
- Tersembunyi jika semua normal

**Section 4: Mini Sparkline Chart**
- Dua grafik kecil berdampingan: PM2.5 (60 menit terakhir) dan PM10 (60 menit terakhir)
- Tampilan compact — hanya garis tren, tanpa axis label
- Tujuan: langsung melihat tren tanpa masuk ke halaman Monitoring

**Section 5: Ringkasan Prediksi Singkat**
- 3 kartu kecil: prediksi jam ke+1, ke+6, ke+12
- Label: "1 jam ke depan", "6 jam ke depan", "12 jam ke depan"
- Tombol CTA: `→ Lihat Prediksi Lengkap 24 Jam`

### 15.4 Halaman 2 — Monitoring Real-time (`/monitoring`)

**Section 1: Header + Kontrol**
- Tombol filter rentang waktu: `1 Jam` | `6 Jam` | `12 Jam` | `24 Jam`
- Badge jumlah record yang ditampilkan

**Section 2: Grafik PM Partikulat (PM2.5 + PM10)**
- Chart.js Line Chart
- Dataset 1: PM2.5 — warna `rgb(34, 211, 238)` (cyan)
- Dataset 2: PM10 — warna `rgb(59, 130, 246)` (blue)
- Garis threshold: PM2.5 = 55 (merah putus-putus), PM10 = 75 (oranye putus-putus)
- Legend + tooltip multi-value
- Auto-refresh setiap 30 detik

**Section 3: Grafik Indeks Gas MQ-135**
- Line Chart — warna `rgb(251, 146, 60)` (orange)
- Y-axis label: "Nilai ADC (0–4095)"
- Tooltip: "Indeks Gas Relatif"

**Section 4: Grafik Parameter Cuaca**
- Chart 1: Suhu + Kelembapan (dual-axis)
  - Suhu: `rgb(248, 113, 113)` (merah muda), axis kiri
  - Kelembapan: `rgb(147, 197, 253)` (biru muda), axis kanan
- Chart 2: Tekanan Udara (standalone)
  - Warna: `rgb(167, 139, 250)` (ungu) — tampilkan novelty sensor BME280

### 15.5 Halaman 3 — Prediksi 24 Jam (`/prediction`)

**Section 1: Info Prediksi**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Model     : Random Forest Regression                               │
│  Dibuat    : 23 Sep 2026, 10:05 WIB                                 │
│  Rentang   : 23 Sep 10:00 – 24 Sep 10:00 WIB                        │
│  Fitur     : Lag 12 step + Tekanan Udara (Novelty)                  │
│                                          [ 🔄 Perbarui Prediksi ]   │
└─────────────────────────────────────────────────────────────────────┘
```

**Section 2: Grafik Prediksi PM2.5**
- Chart.js Area Chart — fill `rgba(34, 211, 238, 0.15)`
- Titik data aktual (jam terkini) — warna cyan solid sebagai anchor
- Garis threshold 55 μg/m³ merah putus-putus
- Area di atas threshold: `rgba(239, 68, 68, 0.1)` (merah transparan)

**Section 3: Grafik Prediksi PM10**
- Area Chart biru — fill `rgba(59, 130, 246, 0.15)`
- Garis threshold 75 μg/m³

**Section 4: Grafik Prediksi Gas**
- Area Chart orange — fill `rgba(251, 146, 60, 0.15)`
- Label Y: "Prediksi Indeks Gas (Relatif)"

**Section 5: Tabel Ringkasan Prediksi 24 Baris**

| Jam ke- | Waktu Target | PM2.5 Pred (μg/m³) | PM10 Pred (μg/m³) | Gas Pred | Status |
|---------|-------------|---------------------|-------------------|----------|--------|
| +1 jam | 10:30 WIB | 44.1 | 80.2 | 1890 | ● Sedang |
| +2 jam | 11:00 WIB | 46.8 | 82.1 | 1920 | ● Sedang |
| ... | ... | ... | ... | ... | ... |

- Baris dengan PM2.5 > 55 atau PM10 > 75 diberi highlight `bg-red-900/30`

### 15.6 Halaman 4 — Evaluasi Model (`/evaluation`)

**Section 1: Info Training**
```
Model dilatih: 23 Sep 2026, 08:00 WIB
Dataset: ISPU DKI Jakarta 2021 + Data Primer
Split: 80% Training / 20% Testing
Algoritma: Random Forest Regression (n_estimators=100)
```

**Section 2: Tabel Metrik**

| Model | MAE | RMSE | R² Score | Status |
|-------|-----|------|----------|--------|
| PM2.5 | 3.21 | 4.87 | 0.89 | ● Baik |
| PM10 | 5.14 | 7.22 | 0.86 | ● Baik |
| Gas (Relatif) | 89.0 | 120.5 | 0.78 | ● Cukup |

**Section 3: Penjelasan Metrik**
- Keterangan singkat tiap metrik dalam bahasa yang mudah dipahami
- Catatan tentang novelty: "Tekanan udara barometrik dari BME280 digunakan sebagai fitur tambahan untuk meningkatkan akurasi prediksi"

**Section 4: Feature Importance (Opsional)**
- Bar chart horizontal: 10 fitur terpenting untuk model PM2.5
- Harapan: `pressure_lag_*` masuk top features → validasi novelty

### 15.7 Halaman 5 — Riwayat Data (`/history`)

**Section 1: Filter**
- Input `Dari` (datepicker) + Input `Sampai` (datepicker)
- Tombol `Tampilkan`

**Section 2: Tabel Data Historis**

| Waktu | PM2.5 | PM10 | Gas ADC | Suhu | Kelembapan | Tekanan |
|-------|-------|------|---------|------|------------|---------|
| 23 Sep 10:00 | 42.5 | 78.3 | 1820 | 31.2 | 68.5 | 1012.4 |

- Pagination: 50 record per halaman, tombol Prev/Next
- Baris dengan PM2.5 > 55 atau PM10 > 75: highlight `bg-red-900/20`
- Total record ditampilkan di atas tabel

---

## 16. USER FLOW

### 16.1 Pengguna DLH / Publik — Monitoring Harian

```
Buka browser
    ↓
Akses http://[IP-server]:5000
    ↓
Landing di Dashboard (/)
    ├── Lihat nilai sensor terkini + status udara
    ├── Cek alert banner (jika merah → udara berbahaya)
    └── Lihat mini sparkline PM2.5 / PM10
          ↓
    Klik "Monitoring"
    ├── Pilih rentang waktu (1H / 6H / 12H / 24H)
    └── Baca tren grafik polutan dan cuaca
          ↓
    Klik "Prediksi"
    ├── Baca grafik prediksi 24 jam ke depan
    ├── Perhatikan baris merah di tabel (jam yang diprediksi berbahaya)
    └── Klik "Perbarui Prediksi" jika ingin prediksi terbaru
          ↓
    (Paralel) Terima notifikasi Telegram jika PM2.5/PM10 melebihi batas
```

### 16.2 Peneliti — Setup dan Operasional Sistem

```
SETUP AWAL:
1. Rakit hardware (ESP32 + sensor) di breadboard
2. Upload firmware via Arduino IDE
3. Install dependencies Python: pip install -r requirements.txt
4. Jalankan Mosquitto Broker: mosquitto -v
5. Isi config.py: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
6. Jalankan sistem: python run.py
7. Verifikasi di terminal: data masuk dari MQTT ke SQLite
8. Jalankan training: python train_model.py
9. Verifikasi: models/*.pkl tersedia, metrik tampil di /evaluation

OPERASIONAL HARIAN:
- Pantau terminal untuk log data masuk
- Cek dashboard untuk verifikasi tampilan benar
- Uji notifikasi: simulasikan nilai tinggi → Telegram harus terima

DOKUMENTASI SKRIPSI:
- Screenshot semua halaman dashboard untuk BAB IV
- Catat MAE, RMSE, R² dari halaman Evaluasi
- Foto hardware node di lokasi
- Catat tabel hasil Black Box Testing
```

---

## 17. VALIDASI DAN ERROR HANDLING

### 17.1 Validasi Data MQTT (Backend)

| Kondisi | Penanganan |
|---------|------------|
| JSON tidak valid / parse error | Log warning, skip record, lanjutkan loop |
| Field wajib hilang (pm25, pm10, dll.) | Log warning, skip record |
| Tipe data salah (bukan angka) | Log warning, skip record |
| PM2.5 atau PM10 < 0 | Log warning, skip — nilai tidak valid secara fisik |
| PM2.5 > 500 μg/m³ | Log warning, simpan dengan flag outlier |
| gas_raw < 0 atau > 4095 | Log warning, skip record |
| Timestamp tidak valid atau kosong | Gunakan datetime.now() server sebagai fallback |

### 17.2 Validasi API Response

| Kondisi | Response |
|---------|----------|
| Database kosong / belum ada data | `{ "status": "no_data", "message": "Menunggu data dari sensor..." }` |
| Model .pkl belum tersedia | `{ "status": "model_not_ready", "message": "Jalankan train_model.py" }` |
| Parameter query tidak valid | HTTP 400 + pesan error |
| Error database internal | HTTP 500 + log di terminal |

### 17.3 Error Handling Frontend

| Kondisi | Penanganan UI |
|---------|---------------|
| Fetch API gagal (network error) | Banner atas: "⚠️ Tidak dapat terhubung ke server" |
| Response `no_data` | Placeholder abu-abu: "Menunggu data pertama dari sensor..." |
| Response `model_not_ready` | Info box: "Model ML belum dilatih. Jalankan train_model.py" |
| Grafik tanpa data | Chart kosong dengan teks centered: "Belum ada data tersedia" |

### 17.4 Error Handling Firmware ESP32

| Kondisi | Penanganan |
|---------|------------|
| Wi-Fi putus | Reconnect loop: retry 1s → 5s → 10s |
| MQTT putus | Reconnect loop: retry 1s → 5s → 10s |
| PMS5003 timeout / no response | Log serial, skip pengiriman iterasi ini |
| BME280 tidak terdeteksi di I2C | Log serial error saat setup, kirim nilai -1 sebagai flag |
| NTP sync gagal | Gunakan RTC internal ESP32 (kurang akurat tapi sistem tidak berhenti) |

### 17.5 Error Handling Telegram Bot

| Kondisi | Penanganan |
|---------|------------|
| API Telegram tidak bisa diakses | Log error, catat ke alert_log dengan status "gagal_kirim", jangan crash sistem |
| Token bot tidak valid (HTTP 401) | Log error konfigurasi, nonaktifkan fitur Telegram sementara |
| Chat ID tidak valid (HTTP 400) | Log error, skip pengiriman |

---

## 18. SECURITY DASAR

> Sistem berjalan di jaringan lokal (Wi-Fi instansi) selama periode penelitian. Security enterprise tidak diperlukan, namun praktik minimal diterapkan untuk menjaga integritas penelitian.

| Aspek | Kebijakan |
|-------|-----------|
| Token + Chat ID Telegram | Simpan di `config.py` — **jangan commit ke repositori publik** |
| `.gitignore` | Tambahkan: `config.py`, `database/`, `models/`, `.env` |
| MQTT | Berjalan tanpa TLS (acceptable untuk jaringan lokal) |
| Flask debug mode | **Matikan** `debug=True` saat deployment lapangan → gunakan `debug=False` |
| Input validation | Semua data dari MQTT divalidasi sebelum masuk database |
| File SQLite | Jangan expose path database secara publik |
| CORS | Tidak diperlukan — frontend dan backend satu server |

---

## 19. TESTING DAN ACCEPTANCE CRITERIA

### 19.1 Skenario Black Box Testing

| ID | Skenario | Input | Expected Output | Kriteria Lulus |
|----|----------|-------|-----------------|----------------|
| T-01 | ESP32 konek Wi-Fi dan MQTT | Power on ESP32, SSID tersedia | Serial: "WiFi Connected" + "MQTT Connected" | ✓ Log muncul < 30 detik |
| T-02 | PMS5003 baca PM2.5 + PM10 | ESP32 aktif, sensor terpasang | Nilai PM2.5 > 0 dan PM10 > 0 di serial | ✓ Nilai numerik valid |
| T-03 | BME280 baca suhu, kelembapan, tekanan | ESP32 aktif, sensor terpasang | Suhu 20–50°C, Hum 0–100%, Press 900–1100 hPa | ✓ Nilai dalam rentang wajar |
| T-04 | MQ-135 baca gas ADC | ESP32 aktif, sensor terpasang | gas_raw: integer 0–4095 | ✓ Nilai integer valid |
| T-05 | Payload JSON terkirim via MQTT | ESP32 publish, Mosquitto aktif | JSON muncul di MQTT subscriber | ✓ Payload valid diterima |
| T-06 | Flask simpan data ke SQLite | MQTT publish dari ESP32 | Record baru muncul di sensor_readings | ✓ Data tersimpan < 10 detik |
| T-07 | Dashboard tampilkan data terkini | Browser buka `/` | Kartu nilai menampilkan angka valid | ✓ Angka sesuai database |
| T-08 | Grafik real-time tampil + auto-refresh | Browser buka `/monitoring` | Grafik Chart.js tampil, update 30 detik | ✓ Grafik bergerak saat data baru |
| T-09 | Prediksi 24 jam dihasilkan | Model .pkl tersedia, data cukup | `/api/predict` return 24 objek prediksi | ✓ Array 24 elemen, nilai numerik |
| T-10 | Halaman prediksi tampil grafik | Browser buka `/prediction` | Area chart 24 jam tampil | ✓ Grafik tampil dengan benar |
| T-11 | Evaluasi model tampil | Model terlatih, metrik tersimpan | Tabel 3 baris: PM2.5, PM10, Gas | ✓ MAE, RMSE, R² tampil |
| T-12 | Alert PM2.5 — Telegram terkirim | Simulasikan pm25 = 70.0 (> 55) | Notifikasi Telegram diterima | ✓ Pesan masuk < 30 detik |
| T-13 | Cooldown alert berfungsi | Kirim pm25 = 70.0 dua kali dalam 10 menit | Hanya 1 notifikasi terkirim | ✓ Notifikasi kedua tidak terkirim |
| T-14 | Alert PM10 — Telegram terkirim | Simulasikan pm10 = 90.0 (> 75) | Notifikasi Telegram PM10 diterima | ✓ Pesan masuk |
| T-15 | Riwayat data + filter tanggal | Buka `/history`, filter hari ini | Tabel data sesuai filter | ✓ Data sesuai |
| T-16 | Responsivitas mobile | Akses dari smartphone | Layout tidak rusak di layar ≥ 375px | ✓ Tampilan rapi |
| T-17 | API error handling — no data | Database kosong, akses `/api/realtime` | JSON: `{ "status": "no_data" }` | ✓ Tidak crash, response bersih |
| T-18 | Reconnect MQTT setelah putus | Matikan Mosquitto, nyalakan kembali | Flask listener reconnect otomatis | ✓ Recovery tanpa restart manual |

### 19.2 Acceptance Criteria — Sistem Dinyatakan Berhasil Jika

1. ✅ Semua 18 skenario Black Box Testing lulus
2. ✅ Model RF menghasilkan R² ≥ 0.70 untuk minimal 2 dari 3 target polutan
3. ✅ Dashboard berfungsi di Chrome/Firefox pada laptop dan smartphone
4. ✅ Notifikasi Telegram terkirim < 30 detik saat simulasi threshold terlampaui
5. ✅ Sistem berjalan stabil minimal 24 jam tanpa crash manual
6. ✅ Prediksi 24 jam dapat digenerate dan ditampilkan di dashboard
7. ✅ Data dari sensor tersimpan di SQLite setiap 30 detik

---

## 20. TAHAPAN IMPLEMENTASI

Mengikuti metode **Prototyping** sesuai proposal dengan pendekatan **UI-First + Progressive Integration**.

### Prinsip Utama

> **Setiap tahap HARUS menghasilkan sesuatu yang bisa dijalankan dan dilihat.**
> UI/UX dibangun PERTAMA dengan data dummy — tampilan profesional harus sudah jadi sejak Tahap 1.
> Setiap tahap berikutnya menyambungkan data nyata ke UI yang sudah ada, bukan membangun UI di akhir.

```
TAHAP 1 → UI lengkap + data dummy        = Dashboard sudah kelihatan profesional
TAHAP 2 → Setup backend + database       = Struktur data siap menerima data nyata
TAHAP 3 → Hardware ESP32 + MQTT          = Data sensor nyata mulai mengalir
TAHAP 4 → Integrasi IoT → UI             = Kartu dan grafik bergerak dengan data asli
TAHAP 5 → Machine Learning               = Halaman prediksi terisi hasil model nyata
TAHAP 6 → Telegram + Testing + Deploy    = Sistem penuh berjalan, siap demo dan dokumentasi
```

---

### TAHAP 1 — UI/UX Lengkap + Setup Project (Hari 1–3)

> **Fokus: Bangun tampilan dashboard yang sudah profesional dan lengkap menggunakan data dummy.
> Setelah tahap ini selesai, sistem sudah bisa dibuka di browser dan terlihat seperti produk jadi.**

```
SETUP PROJECT:
  □ Buat struktur folder lengkap: sistem_fadlan/
  □ Buat virtual environment: python -m venv venv
  □ Install dependencies:
      pip install flask paho-mqtt scikit-learn pandas numpy joblib requests
  □ Buat config.py dengan semua parameter konfigurasi
  □ Buat app.py dan run.py (Flask minimal, belum terhubung database)
  □ Buat routes/pages.py — semua 5 route HTML mengembalikan halaman

BANGUN UI — templates/base.html:
  □ Import Tailwind CSS CDN + Chart.js CDN
  □ Navbar fixed top: dark mode, logo "sistem_fadlan", 5 link navigasi
  □ Indikator ● Live (belum fungsional, statis dulu)
  □ Footer minimal
  □ Responsive: hamburger menu untuk mobile

BANGUN UI — templates/dashboard.html (data dummy):
  □ Status bar: timestamp statis + badge status "SEDANG"
  □ 6 kartu sensor dengan nilai dummy:
      PM2.5: 42.5 μg/m³  | badge ● SEDANG (kuning)
      PM10: 78.3 μg/m³   | badge ⚠ TINGGI (merah)
      Gas: 1820 (Relatif) | tanpa badge
      Suhu: 31.2°C        |
      Kelembapan: 68.5%   |
      Tekanan: 1012.4 hPa |
  □ Alert banner merah (dummy — PM10 melebihi batas)
  □ Mini sparkline Chart.js: PM2.5 dan PM10 (data array dummy)
  □ Ringkasan prediksi 3 kartu kecil (nilai dummy)
  □ Tombol "Lihat Prediksi Lengkap →"

BANGUN UI — templates/monitoring.html (data dummy):
  □ Tombol filter: 1H | 6H | 12H | 24H (statis dulu)
  □ Grafik PM2.5 + PM10 (Chart.js line chart, array data dummy)
  □ Garis threshold merah putus-putus di PM2.5=55 dan PM10=75
  □ Grafik Gas MQ-135 (data dummy, warna orange)
  □ Grafik Suhu + Kelembapan (dual axis, data dummy)
  □ Grafik Tekanan Udara (data dummy, warna ungu)

BANGUN UI — templates/prediction.html (data dummy):
  □ Info box: nama model, waktu dibuat, rentang prediksi
  □ Area chart PM2.5 prediksi (24 titik data dummy, warna cyan)
  □ Area chart PM10 prediksi (data dummy, warna biru)
  □ Area chart Gas prediksi (data dummy, warna orange)
  □ Tabel 24 baris prediksi (data dummy, baris merah untuk nilai tinggi)
  □ Tombol "Perbarui Prediksi"

BANGUN UI — templates/evaluation.html (data dummy):
  □ Info training: dataset, split, algoritma
  □ Tabel metrik: PM2.5 (MAE, RMSE, R²), PM10, Gas
  □ Badge R²: hijau/kuning/merah sesuai nilai
  □ Penjelasan singkat tiap metrik

BANGUN UI — templates/history.html (data dummy):
  □ Filter tanggal (input date, statis dulu)
  □ Tabel 10 baris data dummy
  □ Pagination (statis dulu)
  □ Highlight baris dengan nilai melebihi threshold

VERIFIKASI TAHAP 1:
  □ Jalankan: python run.py
  □ Buka http://localhost:5000 di browser
  □ Semua 5 halaman dapat dibuka tanpa error
  □ Tampilan profesional, dark mode konsisten, semua elemen rapi
  □ Uji responsivitas di DevTools (375px, 768px, 1280px)
  □ Uji di smartphone fisik
```

**✅ Output Visual Tahap 1:**
Dashboard sudah terlihat seperti produk monitoring profesional.
Semua 5 halaman dapat di-demo. Data masih dummy tapi tampilan sudah final.

---

### TAHAP 2 — Backend + Database + API (Hari 3–5)

> **Fokus: Bangun pondasi backend dan sambungkan UI ke API.
> Setelah tahap ini, UI mengambil data dari API (masih data dummy dari endpoint, bukan sensor nyata).**

```
DATABASE:
  □ Implementasi modules/database.py (semua fungsi CRUD)
  □ Jalankan init_db() → buat 4 tabel SQLite
  □ Seed data dummy ke tabel sensor_readings (50 record)
    → agar grafik dan tabel langsung terisi saat diuji

BACKEND API:
  □ Implementasi routes/api.py:
      GET /api/realtime    → query sensor_readings terbaru
      GET /api/chart-data  → query N record untuk grafik
      GET /api/history     → query dengan filter + pagination
      GET /api/predict     → return dummy 24 titik (model belum ada)
      GET /api/model-metrics → return dummy metrik
  □ Implementasi modules/telegram_bot.py (fungsi kirim + cooldown)
  □ Implementasi threshold checker (belum aktif, disiapkan saja)

INTEGRASI UI → API:
  □ Update semua template: ganti data dummy hardcoded dengan
    fetch() JavaScript ke endpoint /api/*
  □ Dashboard: fetch /api/realtime setiap 30 detik → update kartu
  □ Monitoring: fetch /api/chart-data → render Chart.js
  □ Prediksi: fetch /api/predict → render area chart + tabel
  □ Evaluasi: fetch /api/model-metrics → render tabel
  □ Riwayat: fetch /api/history dengan filter tanggal → render tabel
  □ Aktifkan indikator ● Live (hijau jika data < 2 menit, merah jika tidak)

VERIFIKASI TAHAP 2:
  □ Semua grafik dan kartu menampilkan data dari API (bukan hardcoded)
  □ Tabel riwayat menampilkan 50 record seed dari SQLite
  □ Filter tanggal dan pagination berfungsi
  □ Auto-refresh 30 detik bekerja (nilai berubah sesuai data terbaru)
  □ Uji endpoint /api/* via browser — semua return JSON valid
```

**✅ Output Visual Tahap 2:**
UI sepenuhnya terhubung ke API. Tampilan identik dengan Tahap 1 tapi sekarang
data bersumber dari database. Grafik, tabel, kartu — semua hidup dari backend.

---

### TAHAP 3 — Firmware ESP32 + MQTT Integration (Hari 5–8)

> **Fokus: Sambungkan hardware ke sistem.
> Setelah tahap ini, sensor nyata mulai mengirim data dan dashboard mulai bergerak dengan data asli.**

```
HARDWARE + FIRMWARE:
  □ Rakit sirkuit di breadboard sesuai tabel wiring (Section 13.1)
  □ Install Arduino IDE + library: ESP32 board, PMS5003, BME280, ArduinoJson
  □ Uji PMS5003 individual di Serial Monitor
  □ Uji BME280 individual di Serial Monitor
  □ Uji MQ-135 individual di Serial Monitor
  □ Implementasi firmware lengkap:
      → Baca semua sensor
      → NTP sync + timestamp
      → Wi-Fi connect + reconnect
      → MQTT publish JSON setiap 30 detik
  □ Upload firmware, verifikasi di Serial Monitor
  □ Install + jalankan Mosquitto Broker (localhost:1883)
  □ Uji: ESP32 publish → verifikasi di terminal Mosquitto

MQTT LISTENER BACKEND:
  □ Implementasi modules/mqtt_listener.py (daemon thread)
  □ Integrasikan ke run.py: jalankan Flask + MQTT thread bersamaan
  □ Uji end-to-end: ESP32 → MQTT → Flask → SQLite
  □ Verifikasi: data sensor nyata masuk ke tabel sensor_readings

AKTIFKAN THRESHOLD:
  □ Aktifkan threshold checker di MQTT listener
  □ Isi TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID di config.py
  □ Uji alert: simulasikan pm25 > 55 → Telegram menerima notifikasi
  □ Uji cooldown 30 menit

VERIFIKASI TAHAP 3:
  □ Data sensor nyata tersimpan di SQLite setiap 30 detik
  □ Dashboard kartu PM2.5, PM10, dll. menampilkan nilai dari sensor fisik
  □ Grafik real-time bergerak dengan data asli dari lapangan
  □ Indikator ● Live berkedip hijau saat data masuk
  □ Notifikasi Telegram terkirim saat simulasi threshold
```

**✅ Output Visual Tahap 3:**
Dashboard sekarang menampilkan data nyata dari sensor ESP32.
Grafik bergerak setiap 30 detik. Nilai PM2.5, PM10, suhu, kelembapan, tekanan
— semua dari hardware fisik. Terlihat seperti sistem monitoring yang benar-benar hidup.

---

### TAHAP 4 — Machine Learning Pipeline (Hari 8–12)

> **Fokus: Sambungkan model AI ke halaman Prediksi.
> Setelah tahap ini, grafik prediksi 24 jam menampilkan hasil model nyata, bukan dummy.**

```
EKSPLORASI DATA:
  □ Buka dan periksa ISPU_DKI_Jakarta_2021.csv (cek kolom yang tersedia)
  □ Analisis data primer dari SQLite yang sudah terkumpul
  □ Dokumentasikan statistik dasar untuk BAB IV skripsi

IMPLEMENTASI PIPELINE:
  □ Implementasi modules/preprocessor.py
      → handle missing values, outlier IQR, resample interval
  □ Implementasi modules/feature_engineer.py
      → lag features 12 step per variabel
      → cyclical time encoding (hour_sin/cos, dow_sin/cos)
      → sertakan pressure_lag sebagai fitur novelty
  □ Implementasi modules/ml_trainer.py
      → 3 RandomForestRegressor (PM2.5, PM10, gas)
      → hitung MAE, RMSE, R²
      → simpan .pkl via joblib
  □ Implementasi train_model.py (script entry point)
  □ Jalankan: python train_model.py
  □ Verifikasi: 3 file .pkl di models/ + metrik di SQLite

IMPLEMENTASI INFERENCE:
  □ Implementasi modules/ml_inference.py
      → load ketiga .pkl saat Flask start
      → recursive forecasting 24 langkah
      → simpan ke tabel predictions SQLite
  □ Update route /api/predict → sambungkan ke inference nyata
  □ Update route /api/model-metrics → ambil dari tabel model_metrics

VERIFIKASI TAHAP 4:
  □ Halaman Prediksi menampilkan grafik 24 jam hasil model nyata
  □ Tabel 24 baris prediksi terisi dengan nilai dari Random Forest
  □ Halaman Evaluasi menampilkan MAE, RMSE, R² nyata dari hasil training
  □ Badge R² berwarna sesuai nilai aktual model
  □ Tombol "Perbarui Prediksi" menghasilkan prediksi baru
```

**✅ Output Visual Tahap 4:**
Halaman Prediksi sekarang menampilkan proyeksi 24 jam dari model Random Forest yang
sesungguhnya. Halaman Evaluasi menampilkan metrik akurasi nyata. Novelty tekanan udara
terlihat sebagai fitur dalam pipeline. Ini adalah bagian inti akademik skripsi yang bisa
di-screenshot untuk BAB IV.

---

### TAHAP 5 — Early Warning Telegram + Refinement UI (Hari 12–14)

> **Fokus: Pastikan Telegram berfungsi penuh dan lakukan polish akhir UI.
> Setelah tahap ini, sistem 100% lengkap secara fungsional.**

```
EARLY WARNING SYSTEM:
  □ Verifikasi ulang semua skenario alert Telegram:
      → PM2.5 > 55 → notifikasi terkirim ✓
      → PM10 > 75 → notifikasi terkirim ✓
      → Cooldown 30 menit berfungsi ✓
      → Log tersimpan di tabel alert_log ✓
  □ Verifikasi format pesan Telegram sesuai spec Section 14.4
  □ Uji dari smartphone: notifikasi diterima dengan benar

UI POLISH & REFINEMENT:
  □ Periksa konsistensi warna, spacing, tipografi di semua halaman
  □ Pastikan semua state edge case ditangani:
      → Kartu menampilkan "--" jika sensor mati / tidak ada data
      → Alert banner hilang jika semua nilai normal
      → Grafik tampil pesan "Belum ada data" jika kosong
  □ Uji responsivitas akhir: 375px (mobile), 768px (tablet), 1280px (desktop)
  □ Uji di smartphone fisik (Android/iOS)
  □ Verifikasi semua animasi dan transisi berjalan halus
  □ Pastikan tidak ada console error JavaScript di browser

VERIFIKASI TAHAP 5:
  □ Sistem berjalan penuh: IoT → MQTT → Flask → SQLite → ML → Dashboard → Telegram
  □ Semua 5 halaman tampil profesional dan responsif
  □ Tidak ada fungsi yang masih menggunakan data dummy
  □ Semua fitur berfungsi end-to-end
```

**✅ Output Visual Tahap 5:**
Sistem 100% lengkap dan fungsional. Semua halaman bersih, profesional, tidak ada data dummy.
Telegram berfungsi. Prediksi berjalan. Monitoring real-time aktif.
**Siap untuk demo ke dosen.**

---

### TAHAP 6 — Black Box Testing + Deployment Lapangan (Hari 14–21)

> **Fokus: Uji formal, perbaikan bug, deployment ke lokasi fisik, dokumentasi untuk skripsi.**

```
BLACK BOX TESTING:
  □ Jalankan semua 18 skenario Black Box Testing (Section 19.1)
  □ Catat hasil di tabel: Skenario | Input | Expected | Actual | Status (✓/✗)
  □ Perbaiki semua bug yang ditemukan
  □ Ulangi skenario yang gagal setelah perbaikan

DEPLOYMENT LAPANGAN:
  □ Pasang hardware node ESP32 di lokasi fisik
  □ Verifikasi koneksi Wi-Fi lokal berfungsi
  □ Jalankan: python run.py di laptop (terhubung ke Wi-Fi yang sama)
  □ Verifikasi akses dashboard dari smartphone se-jaringan:
      http://[IP-laptop]:5000
  □ Observasi stabilitas sistem minimal 24 jam nonstop

DOKUMENTASI SKRIPSI (BAB IV):
  □ Screenshot Dashboard utama (kartu nilai nyata + status udara)
  □ Screenshot halaman Monitoring (grafik real-time bergerak)
  □ Screenshot halaman Prediksi (grafik 24 jam + tabel)
  □ Screenshot halaman Evaluasi (MAE, RMSE, R² nyata)
  □ Screenshot notifikasi Telegram yang diterima
  □ Foto hardware ESP32 + sensor di lokasi
  □ Foto tampilan dashboard di smartphone
  □ Catat semua nilai metrik ML untuk dimasukkan ke laporan

VERIFIKASI AKHIR:
  □ Semua 18 skenario Black Box Testing lulus
  □ R² ≥ 0.70 untuk minimal 2 dari 3 model
  □ Sistem stabil 24 jam di lapangan
  □ Semua dokumentasi screenshot/foto tersedia
```

**✅ Output Visual Tahap 6:**
Sistem berjalan di lokasi fisik dengan data nyata dari lapangan.
Tabel Black Box Testing lengkap untuk BAB IV. Screenshot dan foto dokumentasi siap.
**Penelitian selesai, skripsi siap ditulis.**

---

### Ringkasan Urutan dan Output Per Tahap

| Tahap | Hari | Yang Dibangun | Output yang Bisa Dilihat |
|-------|------|---------------|--------------------------|
| **1** | 1–3 | UI/UX semua halaman + data dummy | ✅ Dashboard profesional bisa dibuka di browser |
| **2** | 3–5 | Backend + database + API | ✅ UI terhubung ke API, data dari SQLite |
| **3** | 5–8 | Firmware ESP32 + MQTT | ✅ Sensor nyata mengalir, grafik bergerak asli |
| **4** | 8–12 | Machine Learning pipeline | ✅ Prediksi 24 jam nyata, metrik evaluasi tampil |
| **5** | 12–14 | Telegram + polish UI | ✅ Sistem 100% lengkap, siap demo ke dosen |
| **6** | 14–21 | Testing + deployment lapangan | ✅ Dokumentasi skripsi lengkap, sistem di lokasi |

---

## RINGKASAN EKSEKUTIF

**sistem_fadlan** dibangun dalam 6 lapisan terintegrasi:

```
ESP32 + Sensor → MQTT → Flask Backend → SQLite → Random Forest → Dashboard + Telegram
```

Stack lengkap yang ditetapkan:
- **Hardware:** ESP32 + PMS5003 + MQ-135 + BME280
- **Backend:** Python + Flask + Paho-MQTT + SQLite
- **ML:** Scikit-Learn RandomForestRegressor + joblib
- **Frontend:** HTML + Tailwind CSS CDN + Chart.js CDN
- **Alert:** Telegram Bot API

Parameter operasional yang sudah final:
- Interval sampling: **30 detik**
- Threshold PM2.5: **55 μg/m³** | PM10: **75 μg/m³**
- Gas MQ-135: **monitoring saja, tidak trigger alert**
- Prediksi: **24 jam ke depan, recursive forecasting**
- Cooldown alert: **30 menit**
- Server: **0.0.0.0:5000** (akses dari semua perangkat se-jaringan)

PRD ini sepenuhnya didasarkan pada **PROPOSAL (Fadlan)** sebagai patokan utama. Tidak ada fitur yang ditambahkan di luar scope penelitian.

---

*PRD_sistem_fadlan.md — Versi 1.1 Final — 23 September 2026*
*Update v1.1: Tahapan implementasi direvisi dengan pendekatan UI-First + Progressive Integration*
*Pendekatan: UI/UX dibangun pertama (Tahap 1), data nyata disambungkan bertahap (Tahap 2–6)*
*Setiap tahap menghasilkan output visual yang dapat dilihat dan didemonstrasikan*
*Siap digunakan sebagai blueprint implementasi sistem_fadlan*
