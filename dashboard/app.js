/* ═══════════════════════════════════════════════════════════════
   P R I S M  —  Incident Post-Mortem Platform
   ═══════════════════════════════════════════════════════════════ */

let currentIncidentId = null;
let pollTimer = null;

/* ── Navigation ───────────────────────────────────────────────── */
function nav(viewName) {
    document.querySelectorAll('.page-view').forEach(el => {
        el.style.display = 'none';
        el.classList.remove('active');
    });

    document.querySelectorAll('#nav-items .nav-item').forEach(el => {
        el.classList.remove('text-primary', 'bg-primary-container/10', 'border-primary');
        el.classList.add('text-on-surface-variant', 'border-transparent');
    });

    const activePage = document.getElementById(`page-${viewName}`);
    if (activePage) {
        activePage.style.display = 'block';
        activePage.classList.add('active');
    }

    const activeNav = document.querySelector(`#nav-items [data-view="${viewName}"]`);
    if (activeNav) {
        activeNav.classList.remove('text-on-surface-variant', 'border-transparent');
        activeNav.classList.add('text-primary', 'bg-primary-container/10', 'border-primary');
    }

    const titles = {
        'dashboard': 'Incidents',
        'new': 'New Incident Analysis',
        'pipeline': 'Incident Analysis',
        'report': 'Post-Mortem Report',
        'integrations': 'Integrations'
    };
    const titleEl = document.getElementById('view-title');
    if (titleEl && titles[viewName]) {
        titleEl.textContent = titles[viewName];
    }

    if (viewName === 'dashboard') loadList();
    if (viewName === 'integrations') loadInts();
}

/* ── API Client ───────────────────────────────────────────────── */
async function api(path, options = {}) {
    const res = await fetch(path, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
    }
    return res.json();
}

/* ── Incident List ────────────────────────────────────────────── */
async function loadList() {
    try {
        const { incidents = [] } = await api('/api/incidents');
        
        const total = incidents.length;
        const reportsCount = incidents.filter(i => i.has_report).length;
        const runningCount = incidents.filter(i => ['running', 'collecting'].includes(i.pipeline?.status)).length;

        // Metric counts
        document.getElementById('total-incidents').textContent = total;
        document.getElementById('total-reports').textContent = reportsCount;
        document.getElementById('stat-total').textContent = total;
        document.getElementById('stat-reports').textContent = reportsCount;
        document.getElementById('stat-running').textContent = runningCount;
        
        const subRunning = document.getElementById('stat-running-sub');
        if (subRunning) {
            subRunning.textContent = runningCount > 0 ? `${runningCount} Running` : 'Idle';
        }

        // Table
        const tbody = document.getElementById('incidents-table-body');
        const emptyState = document.getElementById('empty-state');

        if (total === 0) {
            tbody.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        emptyState.style.display = 'none';

        tbody.innerHTML = incidents.map(inc => {
            const sev = inc.severity || 'P2';
            const status = inc.pipeline?.status || inc.status || 'pending';
            const scores = inc.quality_scores || {};
            const rootCause = inc.root_cause_summary || '';
            const dt = new Date(inc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });

            const sevColorMap = {
                'P0': 'bg-error-container/20 text-error border-error',
                'P1': 'bg-secondary-container/20 text-secondary border-secondary',
                'P2': 'bg-primary-container/20 text-primary border-primary',
                'P3': 'bg-on-surface-variant/20 text-on-surface-variant border-on-surface-variant'
            };

            let statusChip = '';
            if (status === 'completed') {
                statusChip = `
                    <div class="inline-flex items-center gap-1.5 bg-primary-container/10 border-l-2 border-primary px-2.5 py-1 rounded-sm">
                        <span class="w-1.5 h-1.5 rounded-full bg-primary"></span>
                        <span class="font-label-sm text-xs text-primary font-semibold">Report Ready</span>
                    </div>
                `;
            } else if (status === 'running' || status === 'collecting') {
                statusChip = `
                    <div class="inline-flex items-center gap-1.5 bg-secondary-container/10 border-l-2 border-secondary px-2.5 py-1 rounded-sm">
                        <span class="w-1.5 h-1.5 rounded-full bg-secondary pulse-dot"></span>
                        <span class="font-label-sm text-xs text-secondary font-semibold">Analyzing...</span>
                    </div>
                `;
            } else if (status === 'failed') {
                statusChip = `
                    <div class="inline-flex items-center gap-1.5 bg-error-container/20 border-l-2 border-error px-2.5 py-1 rounded-sm">
                        <span class="font-label-sm text-xs text-error font-semibold">Failed</span>
                    </div>
                `;
            } else {
                statusChip = `
                    <div class="inline-flex items-center gap-1.5 bg-surface-container border-l-2 border-outline px-2.5 py-1 rounded-sm">
                        <span class="font-label-sm text-xs text-on-surface-variant font-semibold">Pending</span>
                    </div>
                `;
            }

            const blameless = scores.blameless_score ? `${scores.blameless_score}/100` : '—';
            const completeness = scores.completeness_score ? `${scores.completeness_score}/100` : '—';

            return `
                <tr class="row-item border-b border-[#1E293B]" onclick="openIncident('${inc.id}')">
                    <td class="px-6 py-3.5 h-12">
                        <span class="font-mono text-xs font-bold px-2 py-0.5 rounded border ${sevColorMap[sev] || sevColorMap['P2']}">${sev}</span>
                    </td>
                    <td class="px-6 py-3.5 h-12">
                        <div class="font-semibold text-on-surface text-sm">${escapeHtml(inc.title)}</div>
                        <div class="text-xs text-on-surface-variant font-mono flex items-center gap-2 mt-0.5">
                            <span>${dt}</span>
                            ${rootCause ? `<span class="text-on-surface-variant/70">• ${escapeHtml(rootCause.slice(0, 75))}...</span>` : ''}
                        </div>
                    </td>
                    <td class="px-6 py-3.5 h-12 font-mono text-xs text-on-surface-variant">
                        ${inc.has_report ? `
                            <div class="flex items-center gap-2 text-primary font-medium">
                                <span class="material-symbols-outlined text-[16px]">description</span>
                                <span>Report Available</span>
                            </div>
                        ` : '<span class="text-on-surface-variant/40">In analysis</span>'}
                    </td>
                    <td class="px-6 py-3.5 h-12">
                        ${statusChip}
                    </td>
                </tr>
            `;
        }).join('');

        // Live polling if running
        if (runningCount > 0 && !pollTimer) {
            pollTimer = setInterval(() => {
                const dash = document.getElementById('page-dashboard');
                if (dash && dash.classList.contains('active')) loadList();
            }, 3000);
        } else if (runningCount === 0 && pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    } catch (err) {
        toast('Failed to load incidents: ' + err.message, 'err');
    }
}

/* ── Open Incident / Show Report / Show Pipeline ──────────────── */
async function openIncident(incidentId) {
    try {
        const { incident, report, pipeline } = await api(`/api/incidents/${incidentId}`);
        currentIncidentId = incidentId;

        if (report?.report_markdown) {
            renderReport(incident, report);
        } else if (pipeline && ['running', 'collecting'].includes(pipeline.status)) {
            showPipeline(incident, pipeline);
        } else if (pipeline?.status === 'failed') {
            toast('Analysis failed: ' + (pipeline.error || 'Unknown error'), 'err');
        } else {
            toast('Report is still being generated', 'info');
        }
    } catch (err) {
        toast('Failed to load incident: ' + err.message, 'err');
    }
}

function renderReport(incident, report) {
    document.getElementById('rpt-title').textContent = incident.title;
    const timing = JSON.parse(report.timing || '{}');

    document.getElementById('rpt-meta').innerHTML = `
        <div class="px-3 py-1 bg-surface-container-low border border-[#1E293B] rounded text-xs font-mono text-primary flex items-center gap-1.5">
            <span class="material-symbols-outlined text-[14px]">timer</span>
            <span>Analysis Latency: ${timing.total_seconds ?? '—'}s</span>
        </div>
        <div class="px-3 py-1 bg-surface-container-low border border-[#1E293B] rounded text-xs font-mono text-on-surface flex items-center gap-1.5">
            <span class="material-symbols-outlined text-[14px]">check_circle</span>
            <span>Post-Mortem Ready</span>
        </div>
    `;

    document.getElementById('rpt-body').innerHTML = marked.parse(report.report_markdown || '*No report generated.*');
    nav('report');
}

function showPipeline(incident, pipelineData) {
    document.getElementById('pipe-title').textContent = incident.title;
    updatePipelineUI(pipelineData);
    nav('pipeline');

    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
        try {
            const data = await api(`/api/incidents/${incident.id}/status`);
            updatePipelineUI(data);

            if (data.status === 'completed') {
                clearInterval(pollTimer);
                pollTimer = null;
                toast('Post-mortem report ready', 'ok');
                setTimeout(() => openIncident(incident.id), 800);
            } else if (data.status === 'failed') {
                clearInterval(pollTimer);
                pollTimer = null;
                toast('Analysis failed', 'err');
            }
        } catch (_) {}
    }, 2000);
}

function updatePipelineUI(data) {
    const progress = data.progress || 0;
    const phase = data.current_phase || 'Analyzing data sources...';

    document.getElementById('pipe-pct').textContent = `${progress}%`;
    document.getElementById('pipe-phase').textContent = phase;

    const ringFill = document.getElementById('pipe-fill');
    if (ringFill) {
        const circumference = 326.7;
        ringFill.style.strokeDashoffset = circumference - (circumference * progress / 100);
    }

    document.querySelectorAll('#pipe-steps-box .pipe-step').forEach(step => {
        const threshold = parseInt(step.dataset.t, 10);
        const dot = step.querySelector('.rounded-full');
        const lbl = step.querySelector('.status-lbl');

        if (progress >= threshold + 12) {
            step.classList.remove('bg-surface-container-low', 'border-primary');
            step.classList.add('bg-primary-container/10', 'border-primary/40');
            dot.className = 'w-2 h-2 rounded-full bg-primary';
            lbl.textContent = 'DONE';
            lbl.className = 'status-lbl text-primary font-bold text-[10px] tracking-wider';
        } else if (progress >= threshold) {
            step.classList.add('bg-surface-container-high', 'border-primary');
            dot.className = 'w-2 h-2 rounded-full bg-primary pulse-dot';
            lbl.textContent = 'RUNNING';
            lbl.className = 'status-lbl text-primary font-bold text-[10px] tracking-wider';
        } else {
            step.classList.remove('bg-primary-container/10', 'bg-surface-container-high', 'border-primary', 'border-primary/40');
            step.classList.add('bg-surface-container-low');
            dot.className = 'w-2 h-2 rounded-full bg-outline';
            lbl.textContent = 'PENDING';
            lbl.className = 'status-lbl text-on-surface-variant text-[11px]';
        }
    });
}

/* ── Incident Creation Handler ────────────────────────────────── */
async function handleCreate(e) {
    e.preventDefault();
    const btn = document.getElementById('submit-btn');
    const origHTML = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined text-[16px] animate-spin">refresh</span> Analyzing...`;

    const logFile = document.getElementById('f-logfile').files[0];
    let logsText = document.getElementById('f-logs').value.trim();
    if (logFile && !logsText) {
        logsText = await readFile(logFile);
    }

    const tVal = document.getElementById('f-time').value;
    const isoTime = tVal ? new Date(tVal).toISOString() : '';

    try {
        const { incident } = await api('/api/incidents', {
            method: 'POST',
            body: JSON.stringify({
                title: document.getElementById('f-title').value.trim(),
                severity: document.getElementById('f-sev').value,
                incident_time: isoTime,
                time_window_hours: parseInt(document.getElementById('f-window').value, 10),
                github_repo: document.getElementById('f-repo').value.trim(),
                logs_text: logsText,
                slack_text: document.getElementById('f-chat').value.trim(),
                alerts_json: document.getElementById('f-alerts').value.trim()
            })
        });

        toast('Incident analysis started', 'ok');
        showPipeline(incident, { status: 'running', progress: 0, current_phase: 'Collecting data...' });
        document.getElementById('incident-form').reset();
    } catch (err) {
        toast('Error starting analysis: ' + err.message, 'err');
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHTML;
    }
}

/* ── Integrations ─────────────────────────────────────────────── */
async function loadInts() {
    try {
        const { integrations = [] } = await api('/api/integrations');
        integrations.forEach(item => {
            const badge = document.getElementById(`${item.provider}-badge`);
            if (!badge) return;

            const t = item.test_result || {};
            if (t.status === 'connected') {
                badge.textContent = 'CONNECTED';
                badge.className = 'text-[11px] font-mono px-2 py-0.5 rounded bg-primary-container/20 border border-primary text-primary font-bold';
            } else if (t.status === 'error') {
                badge.textContent = 'ERROR';
                badge.className = 'text-[11px] font-mono px-2 py-0.5 rounded bg-error-container/20 border border-error text-error font-bold';
            } else if (item.updated_at) {
                badge.textContent = 'CONFIGURED';
                badge.className = 'text-[11px] font-mono px-2 py-0.5 rounded bg-primary-container/20 border border-primary text-primary font-bold';
            } else {
                badge.textContent = 'UNCONFIGURED';
                badge.className = 'text-[11px] font-mono px-2 py-0.5 rounded bg-surface-container border border-[#1E293B] text-on-surface-variant';
            }
        });

        const whEl = document.getElementById('pd-webhook-url');
        if (whEl) whEl.textContent = `${location.origin}/webhooks/pagerduty`;

        const gh = integrations.find(i => i.provider === 'github');
        const gs = document.getElementById('github-status');
        if (gs && gh?.test_result?.status === 'connected') gs.textContent = '✓ Connected';

        const sl = integrations.find(i => i.provider === 'slack');
        const ss = document.getElementById('slack-status');
        if (ss && sl?.test_result?.status === 'connected') ss.textContent = '✓ Connected';
    } catch (_) {}
}

async function saveInt(provider) {
    let body = {};
    if (provider === 'github') body = { repo_url: val('int-github-repo'), token: val('int-github-token') };
    else if (provider === 'slack') body = { bot_token: val('int-slack-token'), default_channel: val('int-slack-channel') };
    else if (provider === 'pagerduty') body = { api_key: val('int-pd-apikey') };
    else return;

    try {
        const { test_result = {} } = await api(`/api/integrations/${provider}`, {
            method: 'POST',
            body: JSON.stringify(body)
        });
        toast(test_result.status === 'connected' ? `${provider} connected successfully` : `Saved (${test_result.message || 'Warning'})`, test_result.status === 'connected' ? 'ok' : 'err');
        loadInts();
    } catch (err) {
        toast(err.message, 'err');
    }
}

async function testInt(provider) {
    try {
        const { test_result = {} } = await api(`/api/integrations/test/${provider}`, { method: 'POST' });
        toast(test_result.status === 'connected' ? `${provider} connection OK` : (test_result.message || 'Error'), test_result.status === 'connected' ? 'ok' : 'err');
        loadInts();
    } catch (err) {
        toast(err.message, 'err');
    }
}

/* ── Copy Markdown Report ─────────────────────────────────────── */
async function copyRpt() {
    if (!currentIncidentId) return;
    try {
        const { report_markdown } = await api(`/api/incidents/${currentIncidentId}/report`);
        await navigator.clipboard.writeText(report_markdown);
        toast('Report markdown copied to clipboard', 'ok');
    } catch (err) {
        toast(err.message, 'err');
    }
}

/* ── Utility Functions ────────────────────────────────────────── */
function filePick(input, previewId) {
    const f = input.files[0];
    const el = document.getElementById(previewId);
    if (el) el.textContent = f ? `✓ ${f.name} (${(f.size / 1024).toFixed(1)} KB)` : '';
}

function readFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error('File read error'));
        reader.readAsText(file);
    });
}

function escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function val(id) {
    return document.getElementById(id)?.value?.trim() || '';
}

function toast(msg, type = 'info') {
    const container = document.getElementById('toasts');
    if (!container) return;

    const el = document.createElement('div');
    el.className = `toast-msg pointer-events-auto px-4 py-2.5 rounded border text-xs font-mono flex items-center gap-2 shadow-lg backdrop-blur-md ${
        type === 'ok' ? 'bg-surface-container-high text-primary border-primary/40' :
        type === 'err' ? 'bg-error-container/30 text-error border-error/50' :
        'bg-surface-container-high text-on-surface border-[#1E293B]'
    }`;

    const icon = type === 'ok' ? 'check_circle' : type === 'err' ? 'error' : 'info';
    el.innerHTML = `<span class="material-symbols-outlined text-[16px]">${icon}</span> <span>${escapeHtml(msg)}</span>`;

    container.appendChild(el);
    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(-6px)';
        el.style.transition = 'all 0.2s ease';
        setTimeout(() => el.remove(), 200);
    }, 3500);
}

/* ── Theme Switcher ───────────────────────────────────────────── */
function initTheme() {
    const savedTheme = localStorage.getItem('prism-theme') || 'dark';
    if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
    updateThemeIcon();
}

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('prism-theme', isDark ? 'dark' : 'light');
    updateThemeIcon();
    toast(`Switched to ${isDark ? 'Dark' : 'Light'} Theme`, 'info');
}

function updateThemeIcon() {
    const iconEl = document.getElementById('theme-btn-icon');
    if (iconEl) {
        const isDark = document.documentElement.classList.contains('dark');
        iconEl.textContent = isDark ? 'light_mode' : 'dark_mode';
    }
}

/* ── Initial Load ─────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadList();
    loadInts();
});
