# kirim_test.py — Test singkat kirim data ke Telegram
import sys
import requests
from datetime import datetime

sys.path.insert(0, ".")
import config

print("=== TEST KIRIM KE TELEGRAM ===")
print(f"Token  : ...{config.TELEGRAM_BOT_TOKEN[-10:]}")
print(f"Chat ID: {config.TELEGRAM_CHAT_ID}")

# 1. Validasi token bot
url_me = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe"
r = requests.get(url_me, timeout=10)
if r.status_code == 200:
    bot = r.json()["result"]
    print(f"Bot OK : {bot['first_name']} (@{bot['username']})")
else:
    print(f"Bot GAGAL: HTTP {r.status_code}")
    sys.exit(1)

# 2. Kirim pesan data sensor
url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
waktu = datetime.now().strftime("%d %b %Y, %H:%M:%S")
pesan = (
    "TEST - sistem_fadlan\n\n"
    f"Koneksi Telegram berhasil!\n"
    f"Waktu: {waktu}\n\n"
    "--- Data Sensor Simulasi ---\n"
    "PM2.5     : 42.5 ug/m3\n"
    "PM10      : 68.3 ug/m3\n"
    "Gas MQ135 : 0.72 V\n"
    "Suhu      : 31.4 C\n"
    "Kelembaban: 78.2 %\n"
    "Node      : node01\n\n"
    "-- sistem_fadlan"
)

resp = requests.post(url, json={"chat_id": config.TELEGRAM_CHAT_ID, "text": pesan}, timeout=10)
if resp.status_code == 200:
    print("BERHASIL! Pesan terkirim ke Telegram.")
else:
    print(f"GAGAL: HTTP {resp.status_code}")
    print(resp.text)
