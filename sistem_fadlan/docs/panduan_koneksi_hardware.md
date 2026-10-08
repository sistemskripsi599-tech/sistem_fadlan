# Panduan Koneksi Hardware — ESP32 ke Laptop (Tahap 3)

## Prinsip Jaringan (PENTING — sering jadi masalah di lapangan)

```
ESP32 ──(WiFi: SSID yang SAMA dengan laptop)──► Mosquitto di IP LAPTOP:1883
                                                      │
Flask (di laptop) ──subscribe──► localhost:1883 ──────┘
```

- **ESP32** memakai **IP laptop** (contoh `192.168.1.4`) — BUKAN `localhost`,
  karena `localhost` di ESP32 berarti ESP32 itu sendiri.
- **Flask** tetap memakai `localhost:1883` di config.py — benar, karena Flask
  jalan DI laptop yang sama dengan broker.
- **Syarat mutlak**: ESP32 dan laptop terhubung ke **WiFi/hotspot yang sama**.
  Hindari "AP isolation" (fitur hotspot yang memisah antar perangkat) — kalau
  ESP32 tidak bisa ping laptop, biasanya ini penyebabnya. Tethering HP umumnya
  aman; hotspot HP dengan "AP isolation" aktif tidak.

---

## Langkah 1 — Cari IP laptop

Windows (CMD/PowerShell):
```
ipconfig
```
Lihat bagian "Wireless LAN adapter Wi-Fi" → **IPv4 Address** → misal `192.168.1.4`.
(IP bisa berubah tiap ganti jaringan — cek ulang tiap pindah WiFi/hotspot.)

Uji cepat dari HP (browser): buka `http://192.168.1.4:5000` → dashboard harus muncul.
Itu membuktikan laptop terjangkau dari perangkat lain di jaringan yang sama.

## Langkah 2 — Install & jalankan Mosquitto di laptop

1. Unduh installer: https://mosquitto.org/download/ (Windows: mosquitto-x.x.x-install-windows-x64.exe)
2. Setelah terpasang, buat file `mosquitto.conf` (mis. di C:\Program Files\mosquitto\):
   ```
   listener 1883 0.0.0.0
   allow_anonymous true
   ```
   (dipakai supaya broker menerima koneksi dari luar localhost — cukup untuk
   jaringan penelitian tertutup, sesuai PRD Section 18)
3. Jalankan broker:
   ```
   net start mosquitto
   ```
   atau mode manual dengan config: `mosquitto -c mosquitto.conf -v`
4. Uji dari CMD (dua jendela):
   - Jendela A: `mosquitto_sub -h localhost -t air_quality/node01 -v`
   - Jendela B: `mosquitto_pub -h localhost -t air_quality/node01 -m "tes"`
   → kalau jendela A menampilkan `tes`, broker siap.

## Langkah 3 — Ubah firmware ESP32 (3 nilai WAJIB diganti)

File: `firmware/sistem_fadlan_node01.ino`, blok KONFIGURASI paling atas:

```cpp
const char* WIFI_SSID     = "NamaWiFiKamu";        // 1. Nama WiFi/hotspot yang SAMA dengan laptop
const char* WIFI_PASSWORD = "PasswordWiFiKamu";    // 2. Password WiFi/hotspot itu
const char* MQTT_BROKER   = "192.168.1.4";         // 3. IP laptop dari Langkah 1 (ipconfig)
```

⚠️ **Semua nilai harus diisi — jangan ada yang tertinggal** `NAMA_WIFI` /
`PASSWORD_WIFI` / `192.168.1.100`. Kalau password salah, ESP32 tidak akan
pernah konek dan Serial Monitor hanya menampilkan titik-titik tanpa batas.

⚠️ **Pastikan kamu memakai firmware versi terbaru** (sudah diperbaiki):
- **PM 1.0 ikut terkirim** (`pm1_0` di payload JSON — kartu dashboard tidak kosong)
- **Offset byte PMS5003 sudah benar** (PM1.0/PM2.5/PM10 sesuai datasheet —
  firmware lama salah baca sehingga nilai partikulat tergeser satu tingkat!)
- Checksum frame PMS divalidasi — data rusak dibuang, tidak masuk database

Upload via Arduino IDE (pilih board: **ESP32 Dev Module**), lalu buka **Serial
Monitor 115200 baud** — harusnya:
```
[wifi] Menghubungkan.... OK, IP: 192.168.x.x
[mqtt] Menghubungkan broker... OK
[mqtt] Terkirim: {"node_id":"node01","pm1_0":22.1,"pm25":34.9,...}
```

Kalau mentok di titik-titik `[wifi]` → SSID/password salah atau sinyal lemah.
Kalau `[mqtt] gagal (rc=-2)` → broker belum jalan atau IP salah (lihat tabel masalah umum di bawah).

## Langkah 4 — Nyalakan sistem di laptop

```
cd sistem_fadlan
./venv/Scripts/python.exe -X utf8 run.py
```
Terminal akan menampilkan:
```
[mqtt] Terhubung ke broker ... — subscribe 'air_quality/node01'
[mqtt] Data masuk: pm1=..., pm25=..., pm10=..., gas=..., t=...
```
Dashboard (localhost:5000) → nilai kartu berubah tiap 30 detik →
indikator ● Live berwarna hijau.

---

## Checklist lapangan (print ini)

- [ ] Laptop & ESP32 di WiFi/hotspot yang SAMA
- [ ] IP laptop sudah dicek ulang (`ipconfig`) — sesuai `MQTT_BROKER` di firmware
- [ ] Mosquitto jalan (`net start mosquitto` / `mosquitto -v`)
- [ ] Dashboard terbuka dari HP: `http://IP-LAPTOP:5000` (bukti jaringan OK)
- [ ] `python run.py` jalan → log `[mqtt] Data masuk` muncul tiap 30 detik
- [ ] `DATA_MODE = "lapangan"` di config.py SETELAH izin pembimbing ada
      → banner MODE SIMULASI hilang otomatis = sistem merekam data asli
- [ ] `python backup.py` — backup harian selama pengambilan data!

## Masalah umum & solusi cepat

| Gejala | Penyebab paling mungkin | Solusi |
|---|---|---|
| ESP32 gagal WiFi | SSID/password salah, sinyal lemah | Cek Serial Monitor; dekatkan ke router |
| WiFi OK tapi MQTT gagal (rc=-2) | Broker mati / IP salah / firewall | `net start mosquitto`; cek IP; izinkan port 1883 di Windows Firewall |
| Broker OK tapi Flask tak terima data | Topic beda / Flask mati / payload ditolak validasi | Topic harus `air_quality/node01`; cek log `run.py`; cek Serial Monitor — kalau ada `[pms] Checksum salah` berulang, cek kabel UART PMS5003 |
| Dashboard "Menunggu alat..." | Data tidak masuk DB | Lihat log `[mqtt] Data masuk`; cek `DATA_MODE` tidak mengunci |
| HP tidak bisa buka dashboard | Beda jaringan / AP isolation | Samakan WiFi; coba tethering HP |
