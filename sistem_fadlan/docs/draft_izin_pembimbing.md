# DRAFT IZIN KEPADA PEMBIMBING — Mode Simulasi Data (Opsi B)

> **Status: MENUNGGU PERSETUJUAN.** Mode simulasi di sistem (`DATA_MODE = "simulasi"`)
> hanya boleh dipakai untuk pengembangan/demo **setelah** ada jawaban "setuju"
> dari pembimbing. Simpan screenshot/bukti jawaban sebagai lampiran riset.
>
> **Cara pakai:** pilih Versi A (WhatsApp — santai) atau Versi B (email — formal),
> kirim ke **Pembimbing I: Emil Salim Podungge, ST.,MM** (cc Pembimbing II:
> Syarifah Allya Rumi, S.Ak., M.Ak bila perlu).

---

## Versi A — WhatsApp (ringkas)

```
Selamat pagi/siang Pak Emil, saya Fadlan (NIM 20220302020) 🙏

Terima kasih bimbingannya sejauh ini. Saya mau konfirmasi terkait data
penelitian skripsi saya (sistem monitoring & prediksi kualitas udara IoT):

Alat sensor (ESP32 + PMS5003 + MQ-135 + BME280) sedang saya finalkan.
Karena pengambilan data lapangan di Buluri membutuhkan waktu (7-14 hari
pengambilan kontinu), untuk tahap PENGEMBANGAN & PENGUJIAN SISTEM dulu,
saya ingin menggunakan DATA SIMULASI dengan profil realistis lokasi
penelitian (rentang nilai sesuai literatur & data DLH).

Rencananya:
1. Tahap sekarang : data simulasi (jelas diberi label "MODE SIMULASI"
   di tampilan sistem, bukan untuk hasil penelitian)
2. Tahap akhir    : alat dinyalakan di lokasi → data asli terkumpul →
   model dilatih ulang dengan data lapangan → hasil BAB IV memakai
   data asli

Apakah Bapak setuju dengan pendekatan ini? Terima kasih Pak 🙏
```

---

## Versi B — Email (formal)

```
Kepada Yth.
Bapak Emil Salim Podungge, ST.,MM
Dosen Pembimbing I

Dengan hormat,

Saya Moh. Fadlan Darul Aksa Nusu (NIM 20220302020), mahasiswa bimbingan
Bapak pada penelitian skripsi berjudul "Implementasi Algoritma Random
Forest pada Sistem Monitoring dan Prediksi Kualitas Udara Berbasis
Internet of Things".

Melalui email ini saya ingin memohon persetujuan terkait strategi data
penelitian sebagai berikut:

1. Latar belakang:
   Alat sensor node (ESP32, PMS5003, MQ-135, BME280) berada pada tahap
   finalisasi. Pengambilan data primer kontinu di lokasi penelitian
   (Kelurahan Buluri, Kota Palu) memerlukan waktu 7-14 hari agar volume
   data memadai untuk pelatihan model Random Forest.

2. Usulan:
   a. Tahap pengembangan dan pengujian sistem menggunakan DATA SIMULASI
      dengan profil realistis lokasi penelitian (rentang nilai mengacu
      pada literatur dan data DLH Provinsi Sulawesi Tengah). Mode
      simulasi ditampilkan secara transparan pada antarmuka sistem
      (banner "MODE SIMULASI") sehingga tidak tertukar dengan data
      lapangan.
   b. Setelah alat terpasang di lokasi, seluruh pengolahan data dan
      hasil BAB IV menggunakan DATA PRIMER hasil pengukuran alat
      secara langsung. Simulasi tidak digunakan sebagai bahan
      kesimpulan penelitian.

3. Permohonan:
   Mohon persetujuan Bapak atas strategi di atas. Bukti persetujuan
   akan saya lampirkan pada dokumen penelitian.

Atas bimbingan dan perhatian Bapak, saya ucapkan terima kasih.

Hormat saya,
Moh. Fadlan Darul Aksa Nusu
NIM 20220302020
Teknik Informatika — STMIK Bina Mulia Palu
```

---

## Setelah disetujui — checklist

- [ ] Screenshot / forward email persetujuan → simpan di `docs/bukti_izin/`
- [ ] Ubah paragraf metodologi skripsi (Bab III, sumber data): tambahkan
      kalimat simulasi berlabel (lihat budi bahasa: "data simulasi digunakan
      pada tahap pengembangan sistem; hasil penelitian menggunakan data primer")
- [ ] Sistem: pastikan banner MODE SIMULASI tampil (sudah otomatis saat
      `DATA_MODE = "simulasi"`)
- [ ] Saat alat siap: ubah `DATA_MODE = "lapangan"` di config.py → banner hilang
- [ ] BAB IV: semua tabel/gambar hasil dibuat dari data `lapangan`
