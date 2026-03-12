/* ================================================================
   NAV: smooth scroll + scroll-spy for active link highlighting
   ================================================================ */

const navLinks = document.querySelectorAll('.nav-link[data-section]');
const sections = document.querySelectorAll('.page-section');

navLinks.forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        const target = document.getElementById(link.dataset.section);
        if (target) target.scrollIntoView({ behavior: 'smooth' });
    });
});

function updateActiveNav() {
    let current = '';
    sections.forEach(sec => {
        const top = sec.getBoundingClientRect().top;
        if (top <= 120) current = sec.id;
    });
    navLinks.forEach(l => l.classList.toggle('active', l.dataset.section === current));
}

window.addEventListener('scroll', updateActiveNav, { passive: true });
updateActiveNav();

/* ================================================================
   SCROLL-TRIGGERED ANIMATIONS for .anim-on-scroll elements
   ================================================================ */

const animEls = document.querySelectorAll('.anim-on-scroll');
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.15 });
animEls.forEach(el => observer.observe(el));

/* ================================================================
   TOOL TABS (inside Home section)
   ================================================================ */

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active', 'fade-in'));

        tab.classList.add('active');
        const target = document.getElementById('tab-' + tab.dataset.tab);
        if (target) {
            target.classList.add('active');
            requestAnimationFrame(() => target.classList.add('fade-in'));
        }

        if (tab.dataset.tab === 'comparison') loadComparison();
    });
});

/* ===== Helpers ===== */
const $ = id => document.getElementById(id);
const show = el => el.classList.remove('hidden');
const hide = el => el.classList.add('hidden');
const loader = $('loader');
function showLoader() { show(loader); }
function hideLoader() { hide(loader); }

function setLoading(btn, on, label = 'Analyzing...') {
    if (!btn) return;
    if (on) {
        if (!btn.dataset.orig) btn.dataset.orig = btn.textContent;
        btn.textContent = label;
        btn.classList.add('is-loading');
        btn.disabled = true;
    } else {
        if (btn.dataset.orig) btn.textContent = btn.dataset.orig;
        btn.classList.remove('is-loading');
        btn.disabled = false;
    }
}

function animateCardPop(el) {
    if (!el) return;
    el.classList.remove('card-pop');
    void el.offsetWidth;
    el.classList.add('card-pop');
}

const FEATURE_LABELS = {
    suspicious_keyword_count: 'Suspicious Keywords',
    url_count: 'URLs Found',
    special_char_count: 'Special Characters',
    uppercase_ratio: 'Uppercase Ratio',
    email_length: 'Word Count',
    has_html: 'HTML Content',
    has_suspicious_domain: 'Suspicious Domain',
    exclamation_count: 'Exclamation Marks',
    dollar_sign_count: 'Dollar Signs',
    digit_ratio: 'Digit Ratio',
    sender_domain_suspicious: 'Sender Domain Suspicious',
    sender_has_numbers: 'Sender Has Numbers',
    sender_domain_length: 'Sender Domain Length',
    device_is_unknown: 'Unknown Device',
    device_is_mobile: 'Mobile Device',
    device_is_automated: 'Automated Sender',
};

function formatValue(key, val) {
    if (key.includes('ratio')) return (val * 100).toFixed(1) + '%';
    if (val === 1 && key.startsWith('has_') || val === 1 && key.startsWith('sender_') && key !== 'sender_domain_length' || val === 1 && key.startsWith('device_')) return 'Yes';
    if (val === 0 && key.startsWith('has_') || val === 0 && key.startsWith('sender_') && key !== 'sender_domain_length' || val === 0 && key.startsWith('device_')) return 'No';
    if (typeof val === 'number' && !Number.isInteger(val)) return val.toFixed(3);
    return val;
}

/* ================================================================
   TAB 1 — SINGLE EMAIL CHECK
   ================================================================ */

$('btn-check').addEventListener('click', async () => {
    const text = $('email-input').value.trim();
    if (!text) { alert('Please enter an email to analyze.'); return; }

    const sender = $('sender-input').value.trim();
    const device = $('device-input').value.trim();
    const modelName = $('model-select-single').value;
    const btn = $('btn-check');

    showLoader();
    setLoading(btn, true, 'Checking...');
    hide($('result-card'));

    try {
        const res = await fetch('/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_text: text, sender, device, model_name: modelName }),
        });
        const data = await res.json();
        if (data.error) { alert(data.error); return; }
        renderResult(data);
        addToHistory(text, data);
    } catch (err) {
        alert('Failed to connect to server.');
        console.error(err);
    } finally {
        hideLoader();
        setLoading(btn, false);
    }
});

function renderResult(data) {
    const card = $('result-card');
    const banner = $('result-banner');
    const isSpam = data.is_spam;

    banner.className = 'banner ' + (isSpam ? 'spam' : 'ham');
    $('result-icon').textContent = isSpam ? '\u26A0\uFE0F' : '\u2705';
    $('result-label').textContent = isSpam ? 'SPAM DETECTED' : 'NOT SPAM (HAM)';
    $('result-confidence').textContent = data.confidence != null ? 'Confidence: ' + (data.confidence * 100).toFixed(1) + '%' : '';
    $('result-model-used').textContent = 'Model: ' + (data.model_used || 'best');

    const reasonsDiv = $('result-reasons');
    if (data.reasons && data.reasons.length) {
        reasonsDiv.innerHTML = '<h4>Analysis</h4><ul>' + data.reasons.map(r => '<li>' + escapeHtml(r) + '</li>').join('') + '</ul>';
    } else {
        reasonsDiv.innerHTML = '';
    }

    const grid = $('result-features');
    grid.innerHTML = '';
    if (data.features) {
        for (const [key, val] of Object.entries(data.features)) {
            const label = FEATURE_LABELS[key] || key;
            grid.innerHTML += `<div class="feat-item"><div class="feat-label">${label}</div><div class="feat-value">${formatValue(key, val)}</div></div>`;
        }
    }
    show(card);
    animateCardPop(card);
}

/* ===== History (localStorage) ===== */
const HISTORY_KEY = 'spam_detector_history';
const MAX_HISTORY = 15;

function getHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; }
    catch { return []; }
}

function addToHistory(text, data) {
    const history = getHistory();
    history.unshift({
        text: text.substring(0, 120),
        prediction: data.prediction,
        is_spam: data.is_spam,
        confidence: data.confidence,
        model: data.model_used,
        time: new Date().toLocaleTimeString(),
    });
    if (history.length > MAX_HISTORY) history.length = MAX_HISTORY;
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    renderHistory();
}

function renderHistory() {
    const history = getHistory();
    const section = $('history-section');
    const list = $('history-list');

    if (!history.length) { hide(section); return; }
    show(section);

    list.innerHTML = history.map(h => {
        const tagClass = h.is_spam ? 'spam' : 'ham';
        const conf = h.confidence != null ? (h.confidence * 100).toFixed(0) + '%' : '';
        return `<div class="history-item">
            <span class="history-text">${escapeHtml(h.text)}</span>
            <div class="history-meta">
                <span class="tag ${tagClass}">${h.prediction}</span>
                <span class="history-conf">${conf}</span>
            </div>
        </div>`;
    }).join('');
}

$('btn-clear-history').addEventListener('click', () => {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
});

renderHistory();

/* ================================================================
   TAB 2 — IMAGE SCAN (OCR)
   ================================================================ */

const imageUploadArea = $('image-upload-area');
const imageFileInput = $('image-file-input');
const btnScanImage = $('btn-scan-image');
let selectedImage = null;

imageUploadArea.addEventListener('click', () => imageFileInput.click());
imageUploadArea.addEventListener('dragover', e => { e.preventDefault(); imageUploadArea.classList.add('dragover'); });
imageUploadArea.addEventListener('dragleave', () => imageUploadArea.classList.remove('dragover'));
imageUploadArea.addEventListener('drop', e => {
    e.preventDefault();
    imageUploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) { imageFileInput.files = e.dataTransfer.files; imageSelected(e.dataTransfer.files[0]); }
});
imageFileInput.addEventListener('change', () => { if (imageFileInput.files.length) imageSelected(imageFileInput.files[0]); });

function imageSelected(file) {
    selectedImage = file;
    $('image-file-name').textContent = file.name;
    btnScanImage.disabled = false;
    const reader = new FileReader();
    reader.onload = e => { $('image-preview').src = e.target.result; show($('image-preview-wrap')); };
    reader.readAsDataURL(file);
}

btnScanImage.addEventListener('click', async () => {
    if (!selectedImage) return;
    const btn = btnScanImage;
    showLoader(); setLoading(btn, true, 'Scanning...');
    hide($('image-result'));
    const formData = new FormData();
    formData.append('image', selectedImage);
    formData.append('model_name', $('model-select-image').value);
    try {
        const res = await fetch('/predict_image', { method: 'POST', body: formData });
        const text = await res.text();
        let data;
        try { data = JSON.parse(text); } catch (_) { data = { error: 'Server error (invalid response). Check the terminal where the app is running.' }; }
        if (!res.ok || data.error) { alert(data.error || 'Request failed (' + res.status + ').'); hideLoader(); setLoading(btn, false); return; }
        renderImageResult(data);
    } catch (err) { alert('Request failed. Check your connection and the server console.'); console.error(err); }
    finally { hideLoader(); setLoading(btn, false); }
});

function renderImageResult(data) {
    const isSpam = data.is_spam;
    const banner = $('image-result-banner');
    banner.className = 'banner ' + (isSpam ? 'spam' : 'ham');
    $('image-result-icon').textContent = isSpam ? '\u26A0\uFE0F' : '\u2705';
    $('image-result-label').textContent = isSpam ? 'SPAM DETECTED' : 'NOT SPAM (HAM)';
    $('image-result-confidence').textContent = data.confidence != null ? 'Confidence: ' + (data.confidence * 100).toFixed(1) + '%' : '';
    $('ocr-text').textContent = data.extracted_text || '(no text extracted)';
    const reasonsDiv = $('image-result-reasons');
    if (data.reasons && data.reasons.length) { reasonsDiv.innerHTML = '<h4>Analysis</h4><ul>' + data.reasons.map(r => '<li>' + escapeHtml(r) + '</li>').join('') + '</ul>'; }
    else { reasonsDiv.innerHTML = ''; }
    show($('image-result'));
    animateCardPop($('image-result'));
}

/* ================================================================
   TAB — DOCUMENT (PDF / WORD)
   ================================================================ */

const documentUploadArea = $('document-upload-area');
const documentFileInput = $('document-file-input');
const btnAnalyzeDocument = $('btn-analyze-document');
let selectedDocument = null;

documentUploadArea.addEventListener('click', () => documentFileInput.click());
documentUploadArea.addEventListener('dragover', e => { e.preventDefault(); documentUploadArea.classList.add('dragover'); });
documentUploadArea.addEventListener('dragleave', () => documentUploadArea.classList.remove('dragover'));
documentUploadArea.addEventListener('drop', e => {
    e.preventDefault(); documentUploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) { documentFileInput.files = e.dataTransfer.files; documentSelected(e.dataTransfer.files[0]); }
});
documentFileInput.addEventListener('change', () => { if (documentFileInput.files.length) documentSelected(documentFileInput.files[0]); });

function documentSelected(file) {
    const ext = (file.name || '').toLowerCase().split('.').pop();
    if (!['pdf', 'docx', 'doc'].includes(ext)) return;
    selectedDocument = file;
    $('document-file-name').textContent = file.name;
    btnAnalyzeDocument.disabled = false;
}

btnAnalyzeDocument.addEventListener('click', async () => {
    if (!selectedDocument) return;
    const btn = btnAnalyzeDocument;
    showLoader(); setLoading(btn, true, 'Analyzing...');
    hide($('document-result'));
    const formData = new FormData();
    formData.append('document', selectedDocument);
    formData.append('model_name', $('model-select-document').value);
    try {
        const res = await fetch('/predict_document', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.error) { alert(data.error); hideLoader(); return; }
        renderDocumentResult(data);
    } catch (err) { alert('Failed to process the document.'); console.error(err); }
    finally { hideLoader(); setLoading(btn, false); }
});

function renderDocumentResult(data) {
    const isSpam = data.is_spam;
    const banner = $('document-result-banner');
    banner.className = 'banner ' + (isSpam ? 'spam' : 'ham');
    $('document-result-icon').textContent = isSpam ? '\u26A0\uFE0F' : '\u2705';
    $('document-result-label').textContent = isSpam ? 'SPAM DETECTED' : 'NOT SPAM (HAM)';
    $('document-result-confidence').textContent = data.confidence != null ? 'Confidence: ' + (data.confidence * 100).toFixed(1) + '%' : '';
    const raw = (data.extracted_text || '').trim();
    $('document-extracted-text').textContent = raw.length > 3000 ? raw.slice(0, 3000) + '\n\n... (truncated)' : raw || '(no text extracted)';
    const reasonsDiv = $('document-result-reasons');
    if (data.reasons && data.reasons.length) { reasonsDiv.innerHTML = '<h4>Analysis</h4><ul>' + data.reasons.map(r => '<li>' + escapeHtml(r) + '</li>').join('') + '</ul>'; }
    else { reasonsDiv.innerHTML = ''; }
    show($('document-result'));
    animateCardPop($('document-result'));
}

/* ================================================================
   TAB — BATCH FILE IMPORT
   ================================================================ */

const uploadArea = $('upload-area');
const fileInput = $('file-input');
const btnUpload = $('btn-upload');
let selectedFile = null;

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea.addEventListener('drop', e => {
    e.preventDefault(); uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; fileSelected(e.dataTransfer.files[0]); }
});
fileInput.addEventListener('change', () => { if (fileInput.files.length) fileSelected(fileInput.files[0]); });

function fileSelected(file) { selectedFile = file; $('file-name').textContent = file.name; btnUpload.disabled = false; }

btnUpload.addEventListener('click', async () => {
    if (!selectedFile) return;
    const btn = btnUpload;
    showLoader(); setLoading(btn, true, 'Analyzing...');
    hide($('batch-result'));
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('model_name', $('model-select-batch').value);
    try {
        const res = await fetch('/predict_batch', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.error) { alert(data.error); hideLoader(); return; }
        renderBatch(data);
    } catch (err) { alert('Failed to process the file.'); console.error(err); }
    finally { hideLoader(); setLoading(btn, false); }
});

function renderBatch(data) {
    $('stat-total').textContent = data.total;
    $('stat-spam').textContent = data.spam_count;
    $('stat-ham').textContent = data.ham_count;
    $('stat-acc').textContent = data.accuracy != null ? data.accuracy + '%' : 'N/A';
    const tbody = document.querySelector('#batch-table tbody');
    tbody.innerHTML = '';
    data.preview.forEach(row => {
        const tagClass = row.prediction === 'spam' ? 'spam' : 'ham';
        const conf = row.confidence != null ? (row.confidence * 100).toFixed(1) + '%' : '-';
        tbody.innerHTML += `<tr><td>${row.index}</td><td>${escapeHtml(row.text)}</td><td><span class="tag ${tagClass}">${row.prediction}</span></td><td>${conf}</td></tr>`;
    });
    show($('batch-result'));
    animateCardPop($('batch-result'));
}

/* ================================================================
   TAB — MODEL COMPARISON DASHBOARD
   ================================================================ */

let compData = null;
let compChart = null;
let compLoaded = false;

async function loadComparison() {
    if (compLoaded) return;
    try {
        const res = await fetch('/comparison');
        if (!res.ok) { $('comp-loading').textContent = 'No metrics found. Run training first.'; return; }
        compData = await res.json();
        compLoaded = true;
        renderComparison();
    } catch (err) { $('comp-loading').textContent = 'Failed to load metrics.'; console.error(err); }
}

function renderComparison() {
    hide($('comp-loading'));
    show($('comp-content'));
    const datasets = Object.keys(compData);
    const tabsContainer = $('dataset-tabs');
    tabsContainer.innerHTML = '';
    datasets.forEach((ds, i) => {
        const btn = document.createElement('button');
        btn.className = 'ds-tab' + (i === 0 ? ' active' : '');
        btn.textContent = ds;
        btn.addEventListener('click', () => {
            tabsContainer.querySelectorAll('.ds-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderDatasetComparison(ds);
        });
        tabsContainer.appendChild(btn);
    });
    renderDatasetComparison(datasets[0]);
}

function renderDatasetComparison(dsName) {
    const models = compData[dsName];
    const modelNames = Object.keys(models);
    const tbody = $('comp-table-body');
    tbody.innerHTML = '';
    let bestF1 = 0, bestModel = '';
    modelNames.forEach(name => { if (models[name].f1_score > bestF1) { bestF1 = models[name].f1_score; bestModel = name; } });
    modelNames.forEach(name => {
        const m = models[name];
        const isBest = name === bestModel;
        tbody.innerHTML += `<tr${isBest ? ' style="background:#f0fdf4"' : ''}>
            <td><strong>${name}</strong>${isBest ? ' <span class="tag ham">BEST</span>' : ''}</td>
            <td>${(m.accuracy * 100).toFixed(2)}%</td><td>${(m.precision * 100).toFixed(2)}%</td>
            <td>${(m.recall * 100).toFixed(2)}%</td><td>${(m.f1_score * 100).toFixed(2)}%</td>
            <td>${(m.cv_f1_mean * 100).toFixed(2)}%</td></tr>`;
    });
    const ctx = $('metrics-chart').getContext('2d');
    if (compChart) compChart.destroy();
    const metrics = ['accuracy', 'precision', 'recall', 'f1_score'];
    const colors = ['#3b82f6', '#16a34a', '#f59e0b'];
    compChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Accuracy', 'Precision', 'Recall', 'F1-Score'],
            datasets: modelNames.map((name, i) => ({
                label: name,
                data: metrics.map(metric => models[name][metric] * 100),
                backgroundColor: colors[i % colors.length] + '88',
                borderColor: colors[i % colors.length],
                borderWidth: 2, borderRadius: 6,
            })),
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { y: { beginAtZero: false, min: 60, max: 100, ticks: { callback: v => v + '%' } } },
            plugins: { legend: { position: 'top' }, tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(2) + '%' } } },
        },
    });
    const cmContainer = $('confusion-matrices');
    cmContainer.innerHTML = '';
    modelNames.forEach(name => {
        const cm = models[name].confusion_matrix;
        if (!cm || cm.length < 2) return;
        const tn = cm[0][0], fp = cm[0][1], fn = cm[1][0], tp = cm[1][1];
        cmContainer.innerHTML += `<div class="cm-card"><h4>${name}</h4><table class="cm-table"><thead><tr><th></th><th>Pred Ham</th><th>Pred Spam</th></tr></thead><tbody><tr><th>Actual Ham</th><td class="cm-cell cm-tn">${tn}</td><td class="cm-cell cm-fp">${fp}</td></tr><tr><th>Actual Spam</th><td class="cm-cell cm-fn">${fn}</td><td class="cm-cell cm-tp">${tp}</td></tr></tbody></table></div>`;
    });
}

/* ===== Utility ===== */
function escapeHtml(str) { const div = document.createElement('div'); div.textContent = str; return div.innerHTML; }
