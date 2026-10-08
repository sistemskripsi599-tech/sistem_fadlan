// =============================================================================
// common.js — Helper aplikasi (dipakai semua halaman)
// Tema Chart.js dark mode + fetch API + indikator Live + status udara
// (Data dummy Tahap 1 sudah diganti fetch /api/* — PRD Tahap 2)
// =============================================================================

// ---- Tema Chart.js dark mode ----
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
Chart.defaults.font.family = "ui-sans-serif, system-ui, sans-serif";

// ---- Threshold (harus sama dengan config.py, PRD Section 1.5) ----
const TH_PM25 = 55.0;   // μg/m³ (PP No. 22/2021)
const TH_PM10 = 75.0;   // μg/m³

// ---- Kategori status udara: 4 tingkat (BAIK/SEDANG/TIDAK SEHAT/BERBAHAYA) ----
// Breakpoint kerangka ISPU per polutan — SAMA dengan modules/air_quality.py:
//   PM2.5: <=15.5 Baik | <=55.4 Sedang | <=150.4 Tidak Sehat | > Berbahaya
//   PM10 : <=50   Baik | <=100  Sedang | <=200   Tidak Sehat | > Berbahaya
const AQ_BANDS = {
    pm25: [[15.5, 'BAIK'], [55.4, 'SEDANG'], [150.4, 'TIDAK SEHAT']],
    pm10: [[50.0, 'BAIK'], [100.0, 'SEDANG'], [200.0, 'TIDAK SEHAT']]
};
const AQ_CLASS = {
    'BAIK':        'bg-green-500/20 text-green-400',
    'SEDANG':      'bg-yellow-500/20 text-yellow-400',
    'TIDAK SEHAT': 'bg-orange-500/20 text-orange-400',
    'BERBAHAYA':   'bg-red-500/20 text-red-400'
};

function aqCat(value, pollutant) {
    if (value == null || isNaN(value)) return null;
    const bands = AQ_BANDS[pollutant] || AQ_BANDS.pm25;
    for (const [limit, label] of bands) {
        if (value <= limit) return { label: label, cls: AQ_CLASS[label] };
    }
    return { label: 'BERBAHAYA', cls: AQ_CLASS['BERBAHAYA'] };
}

// Status gabungan = kategori TERBURUK dari PM2.5 & PM10 yang tersedia
function aqStatus(pm25, pm10) {
    const cats = [aqCat(pm25, 'pm25'), aqCat(pm10, 'pm10')].filter(Boolean);
    if (!cats.length) return { label: '--', cls: 'bg-slate-700 text-slate-400' };
    const order = ['BAIK', 'SEDANG', 'TIDAK SEHAT', 'BERBAHAYA'];
    return cats.sort((a, b) => order.indexOf(b.label) - order.indexOf(a.label))[0];
}

// ---- Format waktu dari timestamp ISO server ----
function fmtDateTime(ts) {
    if (!ts) return '--';
    const d = new Date(ts);
    if (isNaN(d)) return ts;
    return d.toLocaleString('id-ID', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
function fmtTime(ts) {
    if (!ts) return '--';
    const d = new Date(ts);
    if (isNaN(d)) return ts;
    return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

// ---- Isi kartu angka (PRD 17.3: tampilkan "--" jika tidak ada data) ----
function setCard(id, val, decimals = 1) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = (val == null || isNaN(val)) ? '--' : Number(val).toFixed(decimals);
}

function setBadge(id, pm25, pm10) {
    const el = document.getElementById(id);
    if (!el) return;
    const st = aqStatus(pm25, pm10);
    el.className = 'rounded-full px-3 py-1 text-xs font-semibold ' + st.cls;
    el.textContent = '● ' + st.label;
}

// ---- Banner error koneksi (PRD 17.3) ----
let _bannerTimer = null;
function showApiBanner(show) {
    const el = document.getElementById('api-banner');
    if (!el) return;
    el.classList.toggle('hidden', !show);
    if (show) {
        clearTimeout(_bannerTimer);
        _bannerTimer = setTimeout(() => el.classList.add('hidden'), 10000);
    }
}

// ---- fetch JSON dari API; null jika gagal (banner muncul otomatis) ----
async function fetchJSON(url) {
    try {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        showApiBanner(false);
        return await resp.json();
    } catch (err) {
        console.warn('fetchJSON gagal:', url, err);
        showApiBanner(true);
        return null;
    }
}

// ---- Indikator Live navbar (PRD 15.2: hijau jika data < 2 menit) ----
function updateLiveUI(statusResp) {
    const dot  = document.getElementById('nav-live-dot');
    const txt  = document.getElementById('nav-live-text');
    const wrap = dot ? dot.closest('span') : null;
    if (!dot || !statusResp) return;

    const live     = !!statusResp.live;
    const mqttConn = !!statusResp.mqtt_connected;
    const lastData = statusResp.last_data;

    // Warna dot: hijau = data segar <2 menit | kuning = MQTT konek tapi nunggu | merah = offline
    if (live) {
        dot.className = 'live-dot w-2 h-2 rounded-full inline-block bg-green-500';
    } else if (mqttConn) {
        dot.className = 'live-dot w-2 h-2 rounded-full inline-block bg-yellow-400';
    } else {
        dot.className = 'live-dot w-2 h-2 rounded-full inline-block bg-red-500';
    }

    // Label teks
    if (txt) {
        if (live) {
            txt.textContent = 'ESP32 Online';
            txt.className = 'text-green-400 font-semibold';
        } else if (mqttConn) {
            txt.textContent = 'Menunggu ESP32...';
            txt.className = 'text-yellow-400';
        } else {
            txt.textContent = 'ESP32 Offline';
            txt.className = 'text-red-400';
        }
    }

    // Tooltip waktu data terakhir (hover)
    if (wrap) {
        if (lastData) {
            wrap.title = 'Data terakhir: ' + new Date(lastData).toLocaleString('id-ID');
        } else if (mqttConn) {
            wrap.title = 'MQTT broker terhubung — menunggu data dari ESP32...';
        } else {
            wrap.title = 'Broker MQTT belum terhubung. Pastikan Mosquitto sudah berjalan.';
        }
    }
}

function startStatusPolling(intervalMs = 30000) {
    const poll = async () => {
        const s = await fetchJSON('/api/status');
        if (s) updateLiveUI(s);
    };
    poll();
    setInterval(poll, intervalMs);
}

// ---- Tampilkan/sembunyikan pesan "Belum ada data" di area chart ----
function toggleChartEmpty(canvasId, empty, message) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const wrap = canvas.parentElement;
    let el = document.getElementById(canvasId + '-empty');
    if (!el && wrap) {
        el = document.createElement('div');
        el.id = canvasId + '-empty';
        el.className = 'absolute inset-0 flex items-center justify-center text-sm text-slate-500 text-center px-4';
        wrap.appendChild(el);
        wrap.classList.add('relative');
    }
    canvas.classList.toggle('invisible', !!empty);
    if (el) {
        el.textContent = message || 'Belum ada data tersedia';
        el.classList.toggle('hidden', !empty);
    }
}

// ---- Opsi dasar Chart.js line dark mode ----
function baseLineOpts(extra = {}) {
    return Object.assign({
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { boxWidth: 12 } } },
        scales: {
            x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
            y: { grid: { color: 'rgba(255,255,255,0.05)' } }
        }
    }, extra);
}

// ---- Dataset garis threshold (putus-putus horizontal) ----
function thresholdDataset(label, value, color, count) {
    return {
        label: label,
        data: Array(count).fill(value),
        borderColor: color,
        borderDash: [6, 6],
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0
    };
}
