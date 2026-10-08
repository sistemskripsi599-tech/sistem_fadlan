# =============================================================================
# routes/pages.py — Route halaman HTML sistem_fadlan (5 halaman dashboard)
# + penyaji artefak evaluasi dari folder reports/ (bukti BAB IV, 1 klik)
# =============================================================================

import os
from functools import wraps

from flask import (Blueprint, abort, redirect, render_template,
                   request, send_from_directory, session, url_for)

import config
from modules.reporting import REPORTS_DIR

pages_bp = Blueprint("pages", __name__)


# =============================================================================
# HELPER: cek apakah sudah login sebagai admin
# =============================================================================
def login_required(f):
    """Decorator — redirect ke /login jika belum login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("pages.login", next=request.path))
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# AUTENTIKASI
# =============================================================================
@pages_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            next_url = request.args.get("next") or url_for("pages.dashboard")
            return redirect(next_url)
        else:
            error = "Username atau password salah."
    return render_template("login.html", error=error)


@pages_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("pages.publik"))


# =============================================================================
# HALAMAN PUBLIK (tidak perlu login)
# =============================================================================
@pages_bp.route("/")
def index():
    """Root URL langsung redirect ke halaman publik."""
    return redirect(url_for("pages.publik"))


@pages_bp.route("/publik")
def publik():
    """Halaman informasi kualitas udara untuk masyarakat umum — tanpa login."""
    return render_template("publik.html", active="publik")


# =============================================================================
# HALAMAN ADMIN (perlu login)
# =============================================================================
@pages_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@pages_bp.route("/monitoring")
@login_required
def monitoring():
    return render_template("monitoring.html", active="monitoring")


@pages_bp.route("/prediction")
@login_required
def prediction():
    return render_template("prediction.html", active="prediction")


@pages_bp.route("/history")
@login_required
def history():
    return render_template("history.html", active="history")


@pages_bp.route("/admin")
@login_required
def admin():
    return render_template("admin.html", active="admin")


@pages_bp.route("/evaluation")
@login_required
def evaluation():
    # Daftar artefak evaluasi terbaru di folder reports/ (bukti BAB IV)
    # → ditampilkan sebagai tombol "Lihat Bukti Evaluasi" di halaman Evaluasi.
    groups = []   # [{key, title, desc, files:[{name, label}]}]
    try:
        by_key = {}
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            path = os.path.join(REPORTS_DIR, fname)
            if not os.path.isfile(path):
                continue
            key = fname.split("_")[-1].rsplit(".", 1)[0]   # timestamp sesi training
            entry = by_key.setdefault(key, {"key": key, "files": []})
            entry["files"].append({"name": fname, "label": fname})

        # Susun grup: confusion matrix + classification report + actual vs pred
        def _match(files, prefix):
            return [f for f in files if f["name"].startswith(prefix)]

        for key, entry in list(by_key.items()):
            files = entry["files"]
            groups_in_key = []
            for target in ("pm25", "pm10", "gas"):
                cm = _match(files, f"confusion_matrix_{target}_")
                cr = _match(files, f"classification_report_{target}_")
                ap = _match(files, f"actual_vs_pred_{target}_")
                if cm:
                    groups_in_key.append({
                        "key": key, "title": f"Klasifikasi Kategori — {target.upper()}",
                        "desc": "Confusion matrix + classification report (akurasi kategori udara)",
                        "files": cm + cr,
                    })
                if ap:
                    groups_in_key.append({
                        "key": key, "title": f"Regresi — {target.upper()}",
                        "desc": "Grafik aktual vs prediksi + residual",
                        "files": ap,
                    })
            fi = _match(files, "feature_importance_")
            if fi:
                groups_in_key.append({
                    "key": key, "title": "Feature Importance (PM 2.5)",
                    "desc": "15 faktor terpenting — cyan = tekanan udara (novelty)",
                    "files": fi,
                })
            le = _match(files, "laporan_evaluasi_")
            if le:
                groups_in_key.append({
                    "key": key, "title": "Laporan Evaluasi Lengkap",
                    "desc": "Ringkasan metrik siap lampir BAB IV",
                    "files": le,
                })
            groups.extend(groups_in_key)
        groups = groups[:6]   # maksimal 6 grup terbaru agar halaman rapi
    except FileNotFoundError:
        groups = []

    return render_template("evaluation.html", active="evaluation", report_groups=groups)


@pages_bp.route("/reports/<path:filename>")
@login_required
def report_file(filename):
    """Sajikan 1 file bukti dari folder reports/ (whitelist ekstensi aman)."""
    allowed = (".png", ".jpg", ".jpeg", ".txt")
    if not filename.lower().endswith(allowed):
        abort(404)
    return send_from_directory(REPORTS_DIR, filename)
