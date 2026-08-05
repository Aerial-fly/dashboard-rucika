let machineCharts = {};
let activeMachines = [];
let isTvMode = true;
let currentSlideIndex = 0;
let slideTimer = null;

// STATUS API UNTUK JAM REAL-TIME
let apiError = false;

// MEMORI V2: Simpan preferensi Per-Line
let lineMeta = {};
let dashboardPrefs = JSON.parse(localStorage.getItem('spc_prefs_v2')) || {};

const commonChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    scales: {
        y: { grid: { color: '#E9ECEF' }, ticks: { color: '#6C757D', font: { size: 10 } }, grace: '15%' },
        x: { grid: { display: false }, ticks: { color: '#6C757D', font: { size: 10 }, maxRotation: 0 } }
    }
};

function toggleMode() {
    isTvMode = !isTvMode;
    const btn = document.getElementById('btn-mode');
    const body = document.body;

    if (isTvMode) {
        btn.innerText = "Live monitoring";
        btn.className = "btn btn-warning btn-sm fw-bold me-2";
        body.classList.add('tv-mode');
        runSlideshow();
        refreshDashboardEngine();
    } else {
        btn.innerText = "Mode Review";
        btn.className = "btn btn-secondary btn-sm fw-bold me-2";
        body.classList.remove('tv-mode');
        clearTimeout(slideTimer);
        document.querySelectorAll('.machine-block').forEach(el => el.classList.remove('active-slide'));
    }
    setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 150);
}

function runSlideshow() {
    clearTimeout(slideTimer); // Clear at the very beginning to prevent race conditions

    if (!isTvMode || activeMachines.length === 0) {
        return;
    }

    // Pastikan index tidak out of bounds jika ada mesin yang dihapus
    if (currentSlideIndex >= activeMachines.length) {
        currentSlideIndex = 0;
    }

    document.querySelectorAll('.machine-block').forEach(el => el.classList.remove('active-slide'));

    const currentMachine = activeMachines[currentSlideIndex];
    const block = document.getElementById(`machine-block-${currentMachine}`);
    if (block) {
        block.classList.add('active-slide');
    }

    setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 1200);

    // Siapkan index untuk slide berikutnya
    currentSlideIndex++;
    if (currentSlideIndex >= activeMachines.length) {
        currentSlideIndex = 0;
    }

    slideTimer = setTimeout(runSlideshow, 15000); // SLIDESHOW GANTI MESIN TIAP 15 DETIK
}

function toNum(val) {
    const n = parseFloat(val);
    return isNaN(n) ? null : n;
}

// ==========================================
// RENDER MODAL UI (Berdasarkan Line)
// ==========================================
function renderFilterModal() {
    const container = document.getElementById('filter-dynamic-body');
    const modalEl = document.getElementById('modalFilterDashboard');

    if (modalEl.classList.contains('show')) return;

    let html = '';
    for (const [msn, meta] of Object.entries(lineMeta)) {
        const msn_asli = msn.split('-')[0];
        const prefs = dashboardPrefs[msn] || { showLine: true, params: {} };
        const isLineChecked = prefs.showLine !== false ? 'checked' : '';

        html += `
        <div class="card mb-3 border-0 shadow-sm">
            <div class="card-header d-flex justify-content-between align-items-center" style="background-color: #e9ecef;">
                <div class="form-check form-switch mb-0">
                    <input class="form-check-input filter-line-cb" type="checkbox" id="cb-line-${msn}" value="${msn}" ${isLineChecked}>
                    <label class="form-check-label fw-bold text-dark" style="font-size: 1.05rem;" for="cb-line-${msn}">🏭 Line ${msn_asli}</label>
                </div>
            </div>
            <div class="card-body p-3 bg-white">
        `;

        Array.from(meta.params).forEach(p => {
            const pPref = prefs.params[p] || { show: true, type: 'Line' };
            const isParamChecked = pPref.show !== false ? 'checked' : '';
            const isBar = pPref.type === 'Bar';
            const safeP = p.replace(/[^a-zA-Z0-9]/g, '_');

            html += `
                <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                    <div class="form-check mb-0">
                        <input class="form-check-input filter-param-cb-${msn}" type="checkbox" id="cb-param-${msn}-${safeP}" data-param="${p}" ${isParamChecked}>
                        <label class="form-check-label fw-bold text-secondary" for="cb-param-${msn}-${safeP}">${p}</label>
                    </div>
                </div>
            `;
        });
        html += `</div></div>`;
    }

    if (html !== '') container.innerHTML = html;
}

function applyDashboardFilter() {
    for (const msn of Object.keys(lineMeta)) {
        const lineCb = document.getElementById(`cb-line-${msn}`);
        if (!lineCb) continue;

        if (!dashboardPrefs[msn]) dashboardPrefs[msn] = { params: {} };
        dashboardPrefs[msn].showLine = lineCb.checked;

        const paramCbs = document.querySelectorAll(`.filter-param-cb-${msn}`);

        paramCbs.forEach(cb => {
            const p = cb.dataset.param;
            if (!dashboardPrefs[msn].params[p]) dashboardPrefs[msn].params[p] = {};
            dashboardPrefs[msn].params[p].show = cb.checked;
            dashboardPrefs[msn].params[p].type = 'Line'; // Paksa selalu Line
        });
    }

    localStorage.setItem('spc_prefs_v2', JSON.stringify(dashboardPrefs));

    activeMachines = [];
    document.querySelectorAll('.machine-block').forEach(block => {
        const msn = block.id.replace('machine-block-', '');
        if (dashboardPrefs[msn] && dashboardPrefs[msn].showLine === false) {
            block.style.display = 'none';
            block.classList.remove('active-slide');
        } else {
            block.style.display = isTvMode ? '' : 'block';
            activeMachines.push(msn);
        }
    });

    currentSlideIndex = 0;
    if (isTvMode) runSlideshow();
    refreshDashboardEngine();
}

// ==========================================
// MESIN PENARIK DATA UTAMA (TIAP 5 DETIK)
// ==========================================

function calculateSPCStats(dataArray) {
    let valid = dataArray.filter(d => d !== null && !isNaN(d));
    if (valid.length === 0) return { cl: 0, std: 0, ucl: 0, lcl: 0 };
    let sum = valid.reduce((a, b) => a + b, 0);
    let cl = sum / valid.length;
    let varianceSum = valid.reduce((a, b) => a + Math.pow(b - cl, 2), 0);
    let std = valid.length > 1 ? Math.sqrt(varianceSum / (valid.length - 1)) : 0;
    return {
        cl: cl.toFixed(2),
        std: std.toFixed(2),
        ucl: (cl + (3 * std)).toFixed(2),
        lcl: (cl - (3 * std)).toFixed(2)
    };
}
async function refreshDashboardEngine() {
    if (!isTvMode) return; // Label mode manual diurus sama jam real-time

    try {
        const response = await fetch('/api/qc-data');
        const result = await response.json();

        if (result.status === 'success') {
            apiError = false; // Reset status error API
            const mainContainer = document.getElementById('dynamic-dashboard');
            let newlyDiscovered = false;

            if (!result.data || result.data.length === 0) {
                mainContainer.innerHTML = '<div class="alert alert-info text-center mt-5"><h4>Belum ada data QC.</h4><p>Data masih kosong. Silakan input data melalui halaman utama.</p></div>';
                document.getElementById('filter-dynamic-body').innerHTML = '<div class="text-center py-4 text-muted">Belum ada line yang aktif.</div>';
                return;
            }

            result.data.forEach(mObj => {
                const msn = mObj.mesin;
                const msn_asli = msn.split('-')[0];
                const blockId = `machine-block-${msn}`;

                let paramDin = {};
                try { paramDin = JSON.parse(mObj.current.parameter_dinamis) || {}; } catch (e) { }

                let stdParams = {};
                try {
                    (JSON.parse(mObj.current.standar_parameter) || []).forEach(sp => { stdParams[sp.name] = sp; });
                } catch (e) { }

                let keys = Object.keys(stdParams);
                if (keys.length === 0) {
                    keys = Object.keys(paramDin);
                }

                // DAFTARKAN METADATA LINE BARU
                if (!lineMeta[msn]) {
                    lineMeta[msn] = { params: new Set() };
                    newlyDiscovered = true;
                }
                keys.forEach(k => {
                    if (!lineMeta[msn].params.has(k)) {
                        lineMeta[msn].params.add(k);
                        newlyDiscovered = true;
                    }
                });

                // INIT PREFS DEFAULT (Jika belum ada)
                if (!dashboardPrefs[msn]) {
                    dashboardPrefs[msn] = { showLine: true, params: {} };
                }
                keys.forEach(k => {
                    if (!dashboardPrefs[msn].params[k]) {
                        dashboardPrefs[msn].params[k] = { show: true, type: 'Line' };
                    }
                });

                // 1. BUAT KOTAK MESIN JIKA BELUM ADA
                if (!document.getElementById(blockId)) {
                    machineCharts[msn] = { charts: {} };
                    const structureHtml = `
                        <div id="${blockId}" class="machine-block">
                            <div class="machine-header d-flex flex-column gap-3">
                                <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
                                    <div class="d-flex flex-column flex-md-row align-items-md-center gap-2 gap-md-3">
                                        <span class="machine-title">LINE ${msn_asli} <span id="txt-produk-${msn}" class="badge bg-warning text-dark ms-0 ms-md-2">📦 Memuat...</span></span>
                                        <span id="badge-status-${msn}" class="badge status-badge bg-secondary align-self-start align-self-md-center">WAITING DATA</span>
                                    </div>
                                    <div class="d-flex gap-2 flex-wrap text-nowrap">
                                        <div class="stat-tag">Shift: <span id="txt-shift-${msn}" class="fw-bold">-</span> / Grup: <span id="txt-grup-${msn}" class="fw-bold">-</span></div>
                                        <div class="stat-tag text-muted" id="txt-time-${msn}">-</div>
                                    </div>
                                </div>
                                <div class="d-flex gap-2 flex-wrap text-nowrap" id="tags-container-${msn}">
                                </div>
                            </div>
                            <div class="charts-grid" id="charts-container-${msn}">
                            </div>
                        </div>
                    `;
                    mainContainer.insertAdjacentHTML('beforeend', structureHtml);

                    if (dashboardPrefs[msn].showLine === false) {
                        document.getElementById(blockId).style.display = 'none';
                    } else {
                        if (!activeMachines.includes(msn)) activeMachines.push(msn);
                        if (activeMachines.length === 1 && isTvMode) runSlideshow();
                    }
                }

                const timelineLabels = mObj.history.map(h => {
                    const d = new Date(h.tanggal);
                    return `${d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })} (${h.waktu})`;
                });

                document.getElementById(`txt-produk-${msn}`).innerText = `${mObj.current.nama_produk}`;
                document.getElementById(`txt-time-${msn}`).innerText = mObj.current.waktu_update;
                let rawShift = mObj.current.shift_aktif || '';
                let numShift = String(rawShift).replace(/[^0-9]/g, '');
                document.getElementById(`txt-shift-${msn}`).innerText = numShift || rawShift;
                document.getElementById(`txt-grup-${msn}`).innerText = mObj.current.grup_aktif;

                const bStatus = document.getElementById(`badge-status-${msn}`);
                bStatus.innerText = mObj.current.status;
                bStatus.className = mObj.current.status === "NORMAL" ? "badge status-badge bg-success" : "badge status-badge bg-danger animate-pulse";

                const tagsHtml = keys.map(k => {
                    let val = paramDin[k];
                    return `<div class="stat-tag">${k}: <span class="text-primary fw-bold">${val !== undefined && val !== null ? val : '-'}</span></div>`;
                }).join('');
                document.getElementById(`tags-container-${msn}`).innerHTML = tagsHtml;

                let subcontainer = document.getElementById(`charts-container-${msn}`);

                // OPTIMASI BROWSER: Jika line ini di-hide oleh user, jangan render chart sama sekali (hemat RAM 90%)
                if (dashboardPrefs[msn].showLine === false) return;

                keys.forEach((key) => {
                    let safeKey = key.replace(/[^a-zA-Z0-9]/g, '_');
                    let cid = `c-chart-${msn}-${safeKey}`;
                    let boxId = `box-chart-${msn}-${safeKey}`;

                    let pref = dashboardPrefs[msn].params[key] || { show: true, type: 'Line' };

                    if (pref.show === false) {
                        if (document.getElementById(boxId)) {
                            document.getElementById(boxId).remove();
                            if (machineCharts[msn].charts[key]) {
                                machineCharts[msn].charts[key].destroy();
                                delete machineCharts[msn].charts[key];
                            }
                        }
                        return;
                    }

                    if (!document.getElementById(boxId)) {
                        subcontainer.insertAdjacentHTML('beforeend', `
                            <div class="chart-box" id="${boxId}">
                                <div class="height-main"><canvas id="${cid}"></canvas></div>
                                <div class="mt-2 text-center" style="font-size: 11.5px; background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; border-radius: 6px; padding: 5px;">
                                    <span class="me-3"><strong>CL: <span class="text-dark" id="spc-cl-${boxId}">-</span></strong></span>
                                    <span class="me-3">StdDev: <strong class="text-dark" id="spc-std-${boxId}">-</strong></span>
                                    <span class="me-3">UCL: <strong class="text-dark" id="spc-ucl-${boxId}">-</strong></span>
                                    <span>LCL: <strong class="text-dark" id="spc-lcl-${boxId}">-</strong></span>
                                </div>
                            </div>
                        `);
                    }

                    let lastKnownValue = null;
                    let cData = mObj.history.map(h => {
                        try {
                            let pd = JSON.parse(h.parameter_dinamis) || {};
                            if (pd[key] !== undefined && pd[key] !== null && String(pd[key]).trim() !== '') {
                                lastKnownValue = parseFloat(pd[key]);
                            }
                        } catch (e) { }
                        return lastKnownValue; // Forward fill visual
                    });

                    // Update ringkasan SPC di UI secara real-time
                    let stats = calculateSPCStats(cData);
                    document.getElementById(`spc-cl-${boxId}`).innerText = stats.cl;
                    document.getElementById(`spc-std-${boxId}`).innerText = stats.std;
                    document.getElementById(`spc-ucl-${boxId}`).innerText = stats.ucl;
                    document.getElementById(`spc-lcl-${boxId}`).innerText = stats.lcl;

                    let stdP = stdParams[key] || {};
                    const lsl = toNum(stdP.lcl);
                    const usl = toNum(stdP.ucl);
                    const isBar = pref.type === 'Bar';
                    const chartType = isBar ? 'bar' : 'line';

                    const pointColors = cData.map(val => (lsl !== null && val < lsl) || (usl !== null && val > usl) ? '#dc3545' : '#0d6efd');
                    const pointSizes = cData.map(val => (lsl !== null && val < lsl) || (usl !== null && val > usl) ? 4 : 3);

                    if (!machineCharts[msn].charts[key]) {
                        const ctx = document.getElementById(cid).getContext('2d');
                        machineCharts[msn].charts[key] = new Chart(ctx, {
                            type: chartType,
                            data: {
                                labels: timelineLabels,
                                datasets: [
                                    { label: key, data: cData, borderColor: '#0d6efd', backgroundColor: isBar ? 'rgba(13,110,253,0.65)' : 'rgba(13,110,253,0.08)', borderWidth: 2, pointRadius: isBar ? 0 : pointSizes, pointBackgroundColor: pointColors, pointBorderColor: pointColors, fill: !isBar, tension: 0, order: 2 },
                                    { label: lsl !== null ? `LSL (${lsl})` : 'LSL', data: Array(cData.length).fill(lsl), borderColor: '#dc3545', borderWidth: 2, pointRadius: 0, borderDash: [5, 5], hidden: lsl === null, order: 1, type: 'line' },
                                    { label: usl !== null ? `USL (${usl})` : 'USL', data: Array(cData.length).fill(usl), borderColor: '#dc3545', borderWidth: 2, pointRadius: 0, borderDash: [5, 5], hidden: usl === null, order: 1, type: 'line' }
                                ]
                            },
                            options: {
                                ...commonChartOptions,
                                plugins: {
                                    title: { display: true, text: key, font: { size: 16, weight: 'bold' }, color: '#1F4E78', padding: { bottom: 15 } },
                                    legend: { display: true, position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } }
                                }
                            }
                        });
                    } else {
                        let ch = machineCharts[msn].charts[key];
                        ch.config.type = chartType;
                        ch.data.labels = timelineLabels;

                        ch.data.datasets[0].type = chartType;
                        ch.data.datasets[0].label = key;
                        ch.data.datasets[0].data = cData;
                        ch.data.datasets[0].backgroundColor = isBar ? 'rgba(13,110,253,0.65)' : 'rgba(13,110,253,0.08)';
                        ch.data.datasets[0].fill = !isBar;
                        ch.data.datasets[0].pointRadius = isBar ? 0 : pointSizes;
                        ch.data.datasets[0].pointBackgroundColor = pointColors;
                        ch.data.datasets[0].pointBorderColor = pointColors;
                        ch.data.datasets[0].tension = 0;

                        ch.data.datasets[1].data = Array(cData.length).fill(lsl);
                        ch.data.datasets[1].label = lsl !== null ? `LSL (${lsl})` : 'LSL';
                        ch.data.datasets[1].hidden = lsl === null;

                        ch.data.datasets[2].data = Array(cData.length).fill(usl);
                        ch.data.datasets[2].label = usl !== null ? `USL (${usl})` : 'USL';
                        ch.data.datasets[2].hidden = usl === null;

                        ch.update();
                    }
                });
            });

            if (newlyDiscovered) renderFilterModal();
        }
    } catch (err) {
        apiError = true; // Kalau API gagal, trigger status merah
    }
}

// ==========================================
// JAM REAL-TIME (JALAN TIAP 1 DETIK)
// ==========================================
setInterval(() => {
    const syncBadge = document.getElementById('global-sync');
    if (!isTvMode) {
        syncBadge.innerText = "Sedang Ditinjau";
        syncBadge.className = "badge bg-warning text-dark me-2";
    } else if (apiError) {
        syncBadge.innerText = "PUTUS API";
        syncBadge.className = "badge bg-danger me-2";
    } else {
        const timeNow = new Date().toLocaleTimeString('id-ID'); // Format: HH.MM.SS
        syncBadge.innerText = "LIVE : " + timeNow;
        syncBadge.className = "badge bg-light text-dark me-2";
    }
}, 1000);

// Jalanin API pertama kali
refreshDashboardEngine();

// TARIK DATA DARI SERVER TETAP TIAP 5 DETIK
setInterval(refreshDashboardEngine, 5000);