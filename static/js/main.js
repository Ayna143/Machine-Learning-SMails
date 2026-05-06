const $ = id => document.getElementById(id);
const show = el => el && el.classList.remove('hidden');
const hide = el => el && el.classList.add('hidden');

const navLinks = document.querySelectorAll('.nav-link[data-section]');
const sections = document.querySelectorAll('.page-section');
navLinks.forEach(link => link.addEventListener('click', e => {
    const target = document.getElementById(link.dataset.section);
    if (target) {

        target.scrollIntoView({ behavior: 'smooth' });
    }
}));
window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(sec => { if (sec.getBoundingClientRect().top <= 120) current = sec.id; });
    navLinks.forEach(l => l.classList.toggle('active', l.dataset.section === current));
}, { passive: true });
document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    const target = document.getElementById('tab-' + tab.dataset.tab);
    if (target) target.classList.add('active');
}));

const animEls = document.querySelectorAll('.anim-on-scroll');
if (animEls.length) {
    if ('IntersectionObserver' in window) {
        const animObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    animObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.12 });
        animEls.forEach(el => animObserver.observe(el));
    } else {
        animEls.forEach(el => el.classList.add('visible'));
    }
}

const loader = $('loader');
function showLoader() { show(loader); }
function hideLoader() { hide(loader); }

async function safeJson(res) {
    const text = await res.text();
    try { return JSON.parse(text); }
    catch { return { error: 'Server returned invalid JSON.' }; }
}
function prettyErrorMessage(res, data, fallback) {
    if (data && data.error) return data.error;
    if (!res.ok) return `Request failed (${res.status}).`;
    return fallback;
}
function setLoading(btn, on, label = 'Analyzing...') {
    if (!btn) return;
    if (on) {
        if (!btn.dataset.orig) btn.dataset.orig = btn.textContent;
        btn.textContent = label;
        btn.disabled = true;
    } else {
        btn.textContent = btn.dataset.orig || btn.textContent;
        btn.disabled = false;
    }
}
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
}

function validateSenderOrAlert(senderRaw) {
    const s = (senderRaw || '').trim();
    if (!s) {
        alert('Sender email is required. Enter who sent this message (e.g. noreply@company.com).');
        return false;
    }
    if (!/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/.test(s)) {
        alert('Enter a sender that includes an email address, e.g. name@domain.com or Name <name@domain.com>.');
        return false;
    }
    return true;
}

function formatFeatureLabel(key) {
    return String(key || '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, ch => ch.toUpperCase());
}

function formatFeatureValue(val) {
    if (typeof val === 'number') {
        if (Number.isInteger(val)) return String(val);

        return Number(val).toFixed(4).replace(/\.?0+$/, '');
    }
    if (typeof val === 'boolean') return val ? 'Yes' : 'No';
    return String(val ?? '-');
}

let metricsSummary = {};
async function loadMetricsSummary() {
    try {
        const res = await fetch('/model_metrics_summary');
        const data = await safeJson(res);
        if (res.ok && !data.error) metricsSummary = data.metrics_summary || {};
    } catch (_) {}
}
loadMetricsSummary();

function bestModelByHistF1(resultsByModel) {
    const names = Object.keys(resultsByModel || {});
    let best = names[0] || null;
    let bestF1 = -1;
    names.forEach(name => {
        const f1 = metricsSummary[name] && metricsSummary[name].f1_score;
        const val = typeof f1 === 'number' ? f1 : -1;
        if (val > bestF1) { bestF1 = val; best = name; }
    });
    return best;
}

function analyzeVotes(resultsByModel) {
    let spam = 0;
    let ham = 0;
    Object.values(resultsByModel || {}).forEach(r => {
        if (r && r.is_spam) spam += 1;
        else ham += 1;
    });
    const total = spam + ham;
    if (!total) return { spam, ham, total: 0, tie: true, unanimous: true, majoritySpam: false };
    const tie = spam === ham;
    const unanimous = spam === 0 || ham === 0;
    const majoritySpam = spam > ham;
    return { spam, ham, total, tie, unanimous, majoritySpam };
}

function mostConfidentModel(resultsByModel) {
    let bestName = null;
    let bestC = -1;
    Object.entries(resultsByModel || {}).forEach(([name, r]) => {
        const c = r && r.confidence;
        if (typeof c === 'number' && c > bestC) {
            bestC = c;
            bestName = name;
        }
    });
    if (!bestName) return null;
    return { name: bestName, confidence: bestC, result: resultsByModel[bestName] };
}

function avgConfidenceAgreeing(resultsByModel, majorityIsSpam) {
    const vals = Object.values(resultsByModel || {})
        .filter(r => r && r.is_spam === majorityIsSpam)
        .map(r => r.confidence)
        .filter(c => typeof c === 'number');
    if (!vals.length) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function pickDetailModel(resultsByModel, vote, historicalBest) {
    const hb = historicalBest;
    if (!resultsByModel || !Object.keys(resultsByModel).length) return hb;
    if (vote.tie) return hb;
    const wantSpam = vote.majoritySpam;
    const agreeers = Object.entries(resultsByModel).filter(([, r]) => r && r.is_spam === wantSpam);
    let bestName = null;
    let bestC = -1;
    agreeers.forEach(([name, r]) => {
        const c = r.confidence;
        if (typeof c === 'number' && c > bestC) {
            bestC = c;
            bestName = name;
        }
    });
    return bestName || agreeers[0]?.[0] || hb;
}

function buildConsensusState(resultsByModel, historicalBest) {
    const vote = analyzeVotes(resultsByModel);
    const names = Object.keys(resultsByModel || {});
    const hb = (historicalBest && resultsByModel[historicalBest]) ? historicalBest : (names[0] || null);
    if (!hb) return null;

    let finalIsSpam = false;
    if (vote.total === 0) {
        finalIsSpam = false;
    } else if (vote.tie) {
        finalIsSpam = !!resultsByModel[hb].is_spam;
    } else {
        finalIsSpam = vote.majoritySpam;
    }

    const avgAgree = !vote.tie && vote.total
        ? avgConfidenceAgreeing(resultsByModel, finalIsSpam)
        : null;

    const detailModelName = pickDetailModel(resultsByModel, vote, hb);
    const detailResult = resultsByModel[detailModelName] || resultsByModel[hb];
    const mostConf = mostConfidentModel(resultsByModel);

    let headlineLine = '';
    if (vote.total === 0) headlineLine = '';
    else if (vote.tie) {
        headlineLine = `Split vote (${vote.spam} spam / ${vote.ham} not spam). Tiebreaker: ${hb} (best on past tests).`;
    } else if (vote.unanimous) {
        headlineLine = `All ${vote.total} models agree.`;
    } else {
        const n = Math.max(vote.spam, vote.ham);
        headlineLine = `${n} of ${vote.total} models say ${finalIsSpam ? 'spam' : 'not spam'} (majority vote).`;
    }

    const showDisagree = vote.total > 0 && !vote.unanimous;
    const disagreeText = vote.tie
        ? 'Models are split. We used the best overall model as tiebreaker.'
        : 'Models are not fully aligned. We used the majority vote.';

    return {
        vote,
        historicalBest: hb,
        mostConfident: mostConf,
        finalIsSpam,
        headlineLine,
        showDisagreeAlert: showDisagree,
        disagreeText,
        avgAgree,
        detailModelName,
        detailResult,
    };
}

let singleChart = null;
let imageChart = null;
let batchChart = null;
function upsertBarChart(existingChart, canvasId, labels, values, label) {
    const canvas = $(canvasId);
    if (!canvas) return existingChart;
    const ctx = canvas.getContext('2d');
    if (existingChart) existingChart.destroy();
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label,
                data: values,
                backgroundColor: ['#3b82f6aa', '#16a34aaa', '#f59e0baa', '#8b5cf6aa'],
                borderColor: ['#3b82f6', '#16a34a', '#f59e0b', '#8b5cf6'],
                borderWidth: 1.5,
                borderRadius: 6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true, max: 100, ticks: { callback: v => `${v}%` } } },
            plugins: { legend: { display: false } },
        },
    });
}

const HISTORY_KEY = 'spam_detector_history';
function getHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) || []; }
    catch { return []; }
}
function renderHistory() {
    const section = $('history-section');
    const list = $('history-list');
    const items = getHistory();
    if (!items.length) { hide(section); list.innerHTML = ''; return; }
    show(section);
    list.innerHTML = items.map(h => {
        const tagClass = h.is_spam === null ? 'neutral' : (h.is_spam ? 'spam' : 'ham');
        const conf = h.confidence == null ? '-' : `${(h.confidence * 100).toFixed(1)}%`;
        return `<div class="history-item">
            <div class="history-body">
                <span class="history-kind">${escapeHtml(h.kind)}</span>
                <span class="history-text">${escapeHtml(h.text)}</span>
                <div class="history-sub">${escapeHtml(h.subtitle || '')}</div>
            </div>
            <div class="history-meta">
                <span class="tag ${tagClass}">${escapeHtml(h.prediction || 'info')}</span>
                <span class="history-conf">${conf}</span>
                <span class="history-model">${escapeHtml(h.model || '')}</span>
            </div>
        </div>`;
    }).join('');
}
function pushHistory(entry) {
    const items = getHistory();
    items.unshift(entry);
    if (items.length > 40) items.length = 40;
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
    renderHistory();
}
$('btn-clear-history')?.addEventListener('click', () => {
    localStorage.removeItem(HISTORY_KEY);
    renderHistory();
});
window.addEventListener('storage', e => { if (e.key === HISTORY_KEY) renderHistory(); });
renderHistory();

$('btn-check')?.addEventListener('click', async () => {
    const text = $('email-input').value.trim();
    if (!text) { alert('Please enter an email to analyze.'); return; }
    if (!validateSenderOrAlert($('sender-input').value)) return;

    showLoader();
    setLoading($('btn-check'), true, 'Checking...');
    hide($('result-card'));
    try {
        const res = await fetch('/predict_all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email_text: text,
                sender: $('sender-input').value.trim(),
                device: $('device-input').value.trim(),
            }),
        });
        const data = await safeJson(res);
        const err = prettyErrorMessage(res, data, 'Failed to analyze.');
        if (!res.ok || data.error) { alert(err); return; }
        renderSingleComparison(data);
    } catch (e) {
        console.error(e);
        alert('Failed to connect to server.');
    } finally {
        hideLoader();
        setLoading($('btn-check'), false);
    }
});

function renderSingleComparison(data) {
    metricsSummary = data.metrics_summary || metricsSummary;
    const results = data.results_by_model || {};
    const modelNames = Object.keys(results);
    if (!modelNames.length) return;

    const historicalBest = data.recommended_model || bestModelByHistF1(results);
    const cs = buildConsensusState(results, historicalBest);
    if (!cs) return;

    const detail = cs.detailResult;

    $('result-banner').className = 'banner ' + (cs.finalIsSpam ? 'spam' : 'ham');
    $('result-icon').textContent = cs.finalIsSpam ? '\u26A0\uFE0F' : '\u2705';
    $('result-label').textContent = cs.finalIsSpam ? 'SPAM DETECTED' : 'NOT SPAM (HAM)';

    if (cs.avgAgree != null) {
        $('result-confidence').textContent = `Confidence: ${(cs.avgAgree * 100).toFixed(1)}%`;
    } else if (cs.mostConfident) {
        $('result-confidence').textContent = `Confidence: ${(cs.mostConfident.confidence * 100).toFixed(1)}%`;
    } else {
        $('result-confidence').textContent = '';
    }
    $('result-subline').textContent = cs.headlineLine || '';
    $('result-model-used').textContent = `Details shown from: ${cs.detailModelName}`;

    const disagree = $('single-disagree-alert');
    if (cs.showDisagreeAlert) {
        disagree.textContent = cs.disagreeText;
        show(disagree);
    } else {
        disagree.textContent = '';
        hide(disagree);
    }

    $('single-suggestion').innerHTML = `Best overall model (highest historical F1): <strong>${escapeHtml(cs.historicalBest)}</strong><br>Most confident now (info only): <strong>${cs.mostConfident ? `${escapeHtml(cs.mostConfident.name)} (${(cs.mostConfident.confidence * 100).toFixed(1)}%)` : '—'}</strong>`;

    const tbody = document.querySelector('#single-model-table tbody');
    tbody.innerHTML = '';
    modelNames.forEach(name => {
        const r = results[name];
        const rowClass = cs.mostConfident && name === cs.mostConfident.name ? 'row-most-confident' : '';
        tbody.innerHTML += `<tr class="${rowClass}">
            <td>${escapeHtml(name)}</td>
            <td><span class="tag ${r.is_spam ? 'spam' : 'ham'}">${escapeHtml(r.prediction)}</span></td>
            <td>${r.confidence != null ? (r.confidence * 100).toFixed(1) + '%' : '-'}</td>
            <td>${(metricsSummary[name] && typeof metricsSummary[name].accuracy === 'number') ? (metricsSummary[name].accuracy * 100).toFixed(2) + '%' : '-'}</td>
        </tr>`;
    });
    singleChart = upsertBarChart(singleChart, 'single-chart', modelNames, modelNames.map(n => (results[n].confidence || 0) * 100), 'Confidence');

    const reasonsDiv = $('result-reasons');
    reasonsDiv.innerHTML = detail.reasons?.length
        ? `<h4>Why (${escapeHtml(cs.detailModelName)})</h4><ul>${detail.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>`
        : '';

    const grid = $('result-features');
    grid.innerHTML = '';
    if (detail.features) {
        Object.entries(detail.features).forEach(([key, val]) => {
            grid.innerHTML += `<div class="feat-item"><div class="feat-label">${escapeHtml(formatFeatureLabel(key))}</div><div class="feat-value">${escapeHtml(formatFeatureValue(val))}</div></div>`;
        });
    }
    show($('result-card'));
    pushHistory({
        kind: 'email',
        text: textPreview($('email-input').value, 150),
        subtitle: $('sender-input').value.trim() || 'All models compared',
        prediction: cs.finalIsSpam ? 'spam' : 'not spam',
        is_spam: cs.finalIsSpam,
        confidence: cs.avgAgree != null ? cs.avgAgree : (cs.mostConfident ? cs.mostConfident.confidence : null),
        model: cs.detailModelName,
    });
}

const imageUploadArea = $('image-upload-area');
const imageFileInput = $('image-file-input');
const btnScanImage = $('btn-scan-image');
let selectedImage = null;

imageUploadArea?.addEventListener('click', () => imageFileInput.click());
imageUploadArea?.addEventListener('dragover', e => { e.preventDefault(); imageUploadArea.classList.add('dragover'); });
imageUploadArea?.addEventListener('dragleave', () => imageUploadArea.classList.remove('dragover'));
imageUploadArea?.addEventListener('drop', e => {
    e.preventDefault();
    imageUploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) { imageFileInput.files = e.dataTransfer.files; imageSelected(e.dataTransfer.files[0]); }
});
imageFileInput?.addEventListener('change', () => { if (imageFileInput.files.length) imageSelected(imageFileInput.files[0]); });
function imageSelected(file) {
    selectedImage = file;
    $('image-file-name').textContent = file.name;
    btnScanImage.disabled = false;
    const reader = new FileReader();
    reader.onload = e => {
        const img = $('image-preview');
        const wrap = $('image-preview-wrap');
        if (img && wrap) {
            img.src = e.target.result;
            show(wrap);
        }
    };
    reader.readAsDataURL(file);
}

btnScanImage?.addEventListener('click', async () => {
    if (!selectedImage) return;
    if (!validateSenderOrAlert($('image-sender-input').value)) return;
    const fd = new FormData();
    fd.append('image', selectedImage);
    fd.append('sender', $('image-sender-input').value.trim());
    fd.append('device', ($('image-device-input').value || '').trim());
    showLoader();
    setLoading(btnScanImage, true, 'Scanning...');
    hide($('image-result'));
    try {
        const res = await fetch('/predict_image_all', { method: 'POST', body: fd });
        const data = await safeJson(res);
        const err = prettyErrorMessage(res, data, 'Failed to process image.');
        if (!res.ok || data.error) { alert(err); return; }
        renderImageComparison(data);
    } catch (e) {
        console.error(e);
        alert('Failed to connect to server.');
    } finally {
        hideLoader();
        setLoading(btnScanImage, false);
    }
});

function renderImageComparison(data) {
    metricsSummary = data.metrics_summary || metricsSummary;
    const results = data.results_by_model || {};
    const names = Object.keys(results);
    if (!names.length) return;

    const historicalBest = data.recommended_model || bestModelByHistF1(results);
    const cs = buildConsensusState(results, historicalBest);
    if (!cs) return;

    const detail = cs.detailResult;

    $('image-result-banner').className = 'banner ' + (cs.finalIsSpam ? 'spam' : 'ham');
    $('image-result-icon').textContent = cs.finalIsSpam ? '\u26A0\uFE0F' : '\u2705';
    $('image-result-label').textContent = cs.finalIsSpam ? 'SPAM DETECTED' : 'NOT SPAM (HAM)';

    if (cs.avgAgree != null) {
        $('image-result-confidence').textContent = `Confidence: ${(cs.avgAgree * 100).toFixed(1)}%`;
    } else if (cs.mostConfident) {
        $('image-result-confidence').textContent = `Confidence: ${(cs.mostConfident.confidence * 100).toFixed(1)}%`;
    } else {
        $('image-result-confidence').textContent = '';
    }
    $('image-result-subline').textContent = cs.headlineLine || '';

    const disagree = $('image-disagree-alert');
    if (cs.showDisagreeAlert) {
        disagree.textContent = cs.disagreeText;
        show(disagree);
    } else {
        disagree.textContent = '';
        hide(disagree);
    }

    $('image-suggestion').innerHTML = `Best overall model (highest historical F1): <strong>${escapeHtml(cs.historicalBest)}</strong><br>Most confident now (info only): <strong>${cs.mostConfident ? `${escapeHtml(cs.mostConfident.name)} (${(cs.mostConfident.confidence * 100).toFixed(1)}%)` : '—'}</strong>`;
    $('ocr-text').textContent = data.extracted_text || '(no text extracted)';

    const tbody = document.querySelector('#image-model-table tbody');
    tbody.innerHTML = '';
    names.forEach(name => {
        const r = results[name];
        const rowClass = cs.mostConfident && name === cs.mostConfident.name ? 'row-most-confident' : '';
        tbody.innerHTML += `<tr class="${rowClass}">
            <td>${escapeHtml(name)}</td>
            <td><span class="tag ${r.is_spam ? 'spam' : 'ham'}">${escapeHtml(r.prediction)}</span></td>
            <td>${r.confidence != null ? (r.confidence * 100).toFixed(1) + '%' : '-'}</td>
            <td>${(metricsSummary[name] && typeof metricsSummary[name].accuracy === 'number') ? (metricsSummary[name].accuracy * 100).toFixed(2) + '%' : '-'}</td>
        </tr>`;
    });
    imageChart = upsertBarChart(imageChart, 'image-chart', names, names.map(n => (results[n].confidence || 0) * 100), 'Confidence');
    $('image-result-reasons').innerHTML = detail.reasons?.length
        ? `<h4>Why (${escapeHtml(cs.detailModelName)})</h4><ul>${detail.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>`
        : '';
    show($('image-result'));

    pushHistory({
        kind: 'image',
        text: textPreview(data.extracted_text || selectedImage?.name || 'image', 140),
        subtitle: [$('image-sender-input').value.trim(), selectedImage?.name].filter(Boolean).join(' · '),
        prediction: cs.finalIsSpam ? 'spam' : 'not spam',
        is_spam: cs.finalIsSpam,
        confidence: cs.avgAgree != null ? cs.avgAgree : (cs.mostConfident ? cs.mostConfident.confidence : null),
        model: cs.detailModelName,
    });
}

const uploadArea = $('upload-area');
const fileInput = $('file-input');
const btnUpload = $('btn-upload');
let selectedFile = null;
uploadArea?.addEventListener('click', () => fileInput.click());
uploadArea?.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
uploadArea?.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
uploadArea?.addEventListener('drop', e => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; fileSelected(e.dataTransfer.files[0]); }
});
fileInput?.addEventListener('change', () => { if (fileInput.files.length) fileSelected(fileInput.files[0]); });
function fileSelected(file) {
    selectedFile = file;
    $('file-name').textContent = file.name;
    btnUpload.disabled = false;
}

btnUpload?.addEventListener('click', async () => {
    if (!selectedFile) return;
    const fd = new FormData();
    fd.append('file', selectedFile);
    showLoader();
    setLoading(btnUpload, true, 'Analyzing...');
    hide($('batch-result'));
    try {
        const res = await fetch('/predict_batch_all', { method: 'POST', body: fd });
        const data = await safeJson(res);
        const err = prettyErrorMessage(res, data, 'Failed to process file.');
        if (!res.ok || data.error) { alert(err); return; }
        renderBatchComparison(data);
    } catch (e) {
        console.error(e);
        alert('Failed to connect to server.');
    } finally {
        hideLoader();
        setLoading(btnUpload, false);
    }
});

function renderBatchComparison(data) {
    metricsSummary = data.metrics_summary || metricsSummary;
    const perModel = data.per_model || {};
    const names = Object.keys(perModel);
    const recommended = data.recommended_model || names[0];
    const top = perModel[recommended];
    if (!top) return;

    const spamCounts = names.map(n => perModel[n].spam_count);
    const hamCounts = names.map(n => perModel[n].ham_count);
    const spamUnanimous = spamCounts.every(c => c === spamCounts[0]);
    const hamUnanimous = hamCounts.every(c => c === hamCounts[0]);
    const allAgreeCounts = spamUnanimous && hamUnanimous;

    $('batch-suggestion').innerHTML = `Best overall model (highest historical F1): <strong>${escapeHtml(recommended)}</strong><br>${allAgreeCounts ? 'All models gave the same spam/ham totals.' : 'Models gave different totals. Check each row.'}`;
    $('stat-total').textContent = top.total;
    $('stat-spam').textContent = top.spam_count;
    $('stat-ham').textContent = top.ham_count;
    $('stat-acc').textContent = top.accuracy != null ? `${top.accuracy}%` : 'N/A';

    const modelBody = document.querySelector('#batch-model-table tbody');
    modelBody.innerHTML = '';
    names.forEach(name => {
        const m = perModel[name];
        const rowClass = name === recommended ? 'row-most-confident' : '';
        modelBody.innerHTML += `<tr class="${rowClass}">
            <td>${escapeHtml(name)}</td>
            <td>${m.total}</td>
            <td>${m.spam_count}</td>
            <td>${m.ham_count}</td>
            <td>${m.accuracy != null ? m.accuracy + '%' : 'N/A'}</td>
            <td>${(metricsSummary[name] && typeof metricsSummary[name].f1_score === 'number') ? (metricsSummary[name].f1_score * 100).toFixed(2) + '%' : '-'}</td>
        </tr>`;
    });

    const chartValues = names.map(n => {
        const v = perModel[n].accuracy;
        if (typeof v === 'number') return v;
        const histAcc = metricsSummary[n] && metricsSummary[n].accuracy;
        return typeof histAcc === 'number' ? histAcc * 100 : 0;
    });
    batchChart = upsertBarChart(batchChart, 'batch-chart', names, chartValues, 'Accuracy');

    const previewBody = document.querySelector('#batch-table tbody');
    previewBody.innerHTML = '';
    (data.preview || []).forEach(row => {
        const tagClass = row.prediction === 'spam' ? 'spam' : 'ham';
        const conf = row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : '-';
        previewBody.innerHTML += `<tr><td>${row.index}</td><td>${escapeHtml(row.text)}</td><td><span class="tag ${tagClass}">${row.prediction}</span></td><td>${conf}</td></tr>`;
    });
    show($('batch-result'));

    pushHistory({
        kind: 'batch',
        text: selectedFile?.name || 'dataset',
        subtitle: `${top.total} rows · ${top.spam_count} spam · ${top.ham_count} ham`,
        prediction: 'import',
        is_spam: null,
        confidence: null,
        model: recommended,
    });
}

function textPreview(s, maxLen) {
    const t = (s || '').trim();
    return t.length > maxLen ? t.slice(0, maxLen) + '...' : t;
}

let compData = null;
let compChart = null;

const DATASET_TAB_ORDER = ['SMS Spam', 'Enron Email', 'SpamAssassin', 'Third dataset', 'Combined'];

function sortDatasetTabKeys(keys) {
    return [...keys].sort((a, b) => {
        const ia = DATASET_TAB_ORDER.indexOf(a);
        const ib = DATASET_TAB_ORDER.indexOf(b);
        return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });
}

function avgMetric(models, metric) {
    const vals = Object.values(models || {})
        .map(m => m && m[metric])
        .filter(v => typeof v === 'number');
    if (!vals.length) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
}

async function loadComparison() {
    const loading = $('comp-loading');
    try {
        const res = await fetch('/comparison', { cache: 'no-store' });
        if (!res.ok) {
            if (loading) loading.textContent = 'No metrics found yet. Run training first.';
            return;
        }
        compData = await res.json();
        renderComparison();
    } catch (err) {
        if (loading) loading.textContent = 'Failed to load comparison.';
        console.error(err);
    }
}

function renderComparison() {
    const loading = $('comp-loading');
    const content = $('comp-content');
    const tabsContainer = $('dataset-tabs');
    if (!compData || !tabsContainer) return;

    if (loading) hide(loading);
    if (content) show(content);

    const datasets = sortDatasetTabKeys(Object.keys(compData || {}));
    tabsContainer.innerHTML = '';
    if (!datasets.length) {
        tabsContainer.innerHTML = '<p>No metrics data found.</p>';
        return;
    }

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
    const models = compData && compData[dsName];
    if (!models) return;
    const modelNames = Object.keys(models);

    const tbody = $('comp-table-body');
    if (tbody) {
        tbody.innerHTML = '';
        modelNames.forEach(name => {
            const m = models[name];
            tbody.innerHTML += `<tr>
                <td>${escapeHtml(name)}</td>
                <td>${typeof m.accuracy === 'number' ? (m.accuracy * 100).toFixed(2) + '%' : '-'}</td>
                <td>${typeof m.precision === 'number' ? (m.precision * 100).toFixed(2) + '%' : '-'}</td>
                <td>${typeof m.recall === 'number' ? (m.recall * 100).toFixed(2) + '%' : '-'}</td>
                <td>${typeof m.f1_score === 'number' ? (m.f1_score * 100).toFixed(2) + '%' : '-'}</td>
                <td>${typeof m.cv_f1_mean === 'number' ? (m.cv_f1_mean * 100).toFixed(2) + '%' : '-'}</td>
            </tr>`;
        });
    }

    const chartCanvas = $('metrics-chart');
    if (chartCanvas) {
        const ctx = chartCanvas.getContext('2d');
        if (compChart) compChart.destroy();
        compChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Accuracy', 'Precision', 'Recall', 'F1'],
                datasets: modelNames.map((name, i) => ({
                    label: name,
                    data: ['accuracy', 'precision', 'recall', 'f1_score'].map(k => (models[name][k] || 0) * 100),
                    backgroundColor: ['#3b82f6', '#16a34a', '#f59e0b'][i % 3] + '88',
                    borderColor: ['#3b82f6', '#16a34a', '#f59e0b'][i % 3],
                    borderWidth: 1.5,
                    borderRadius: 6,
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { y: { min: 0, max: 100, ticks: { callback: v => `${v}%` } } },
            },
        });
    }

    const cm = $('confusion-matrices');
    if (cm) {
        cm.innerHTML = '';
        modelNames.forEach(name => {
            const mat = models[name].confusion_matrix;
            if (!mat || mat.length < 2) return;
            cm.innerHTML += `<div class="cm-card"><h4>${escapeHtml(name)}</h4>
                <table class="cm-table"><thead><tr><th></th><th>Pred Ham</th><th>Pred Spam</th></tr></thead>
                <tbody>
                    <tr><th>Actual Ham</th><td class="cm-cell cm-tn">${mat[0][0]}</td><td class="cm-cell cm-fp">${mat[0][1]}</td></tr>
                    <tr><th>Actual Spam</th><td class="cm-cell cm-fn">${mat[1][0]}</td><td class="cm-cell cm-tp">${mat[1][1]}</td></tr>
                </tbody></table></div>`;
        });
    }
}

const aboutSection = $('section-about');
if (aboutSection) {
    const ob = new IntersectionObserver((entries) => {
        if (entries[0] && entries[0].isIntersecting) loadComparison();
    }, { threshold: 0.15 });
    ob.observe(aboutSection);
}

loadComparison();
