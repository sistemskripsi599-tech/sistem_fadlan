# =============================================================================
# run.py — Entry point sistem_fadlan
# Jalankan: python run.py   →  start Flask + MQTT thread bersamaan (PRD 9.1)
# =============================================================================

from app import create_app
from config import FLASK_DEBUG, FLASK_HOST, FLASK_PORT
from modules import database, mqtt_listener
from modules.ml_inference import load_models

app = create_app()

# Pastikan skema DB terkini (termasuk migrasi kolom pm1_0 / sent_status)
database.init_db()

if __name__ == "__main__":
    print("=" * 55)
    print("  sistem_fadlan — Monitoring Kualitas Udara Berbasis IoT")
    print("=" * 55)
    print(f"  Server    : http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"  Mode      : {'DEBUG' if FLASK_DEBUG else 'PRODUCTION'}")
    print(f"  Dashboard : http://localhost:{FLASK_PORT}")
    print("=" * 55)

    # Preload model ML (jika sudah dilatih) — PRD 9.2 ml_inference
    if load_models():
        print("[ml] Model .pkl dimuat — prediksi 24 jam siap")
    else:
        print("[ml] Model belum tersedia — jalankan train_model.py (Tahap 4)")

    # Start MQTT listener daemon (Tahap 3) — tidak fatal jika broker mati
    try:
        mqtt_listener.start_listener()
        print("[mqtt] Listener di-start (menunggu koneksi broker...)")
    except Exception as exc:
        print(f"[mqtt] Gagal start listener: {exc}")

    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False)
