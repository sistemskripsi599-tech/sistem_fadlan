# =============================================================================
# app.py — Inisialisasi Flask app sistem_fadlan
# =============================================================================

from flask import Flask

import config
from routes.api import api_bp
from routes.pages import pages_bp


def create_app():
    app = Flask(__name__)

    # Secret key untuk session login admin
    app.secret_key = config.SECRET_KEY

    # Daftarkan blueprint routes
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    # Variabel global untuk semua template:
    # data_mode = 'simulasi' → banner MODE SIMULASI tampil di semua halaman
    # (transparansi: data buatan TIDAK boleh tertukar dengan data lapangan)
    @app.context_processor
    def inject_data_mode():
        return {"data_mode": config.DATA_MODE}

    return app
