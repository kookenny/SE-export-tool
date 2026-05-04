/**
 * SE Export Tool — unified frontend.
 * Tab switching + per-tool form handlers.
 */

const ENGAGEMENT_PATTERN = /https?:\/\/([^/]+)\/([^/]+)\/e\/eng\/([^/]+)/;

const TOOLS = {
    checklists: {
        endpoint: '/api/checklists/generate',
        defaultFilename: 'checklists.xlsx',
        docPattern: /#\/(?:efinancials|checklist)\/([^/?\s]+)/,
        docRequired: false,
        defaultName: 'Report',
    },
    risks: {
        endpoint: '/api/risks/generate',
        defaultFilename: 'risk_library.xlsx',
        docPattern: null,
        docRequired: false,
        defaultName: 'Report',
    },
    notes: {
        endpoint: '/api/notes/generate',
        defaultFilename: 'note_visibility.xlsx',
        docPattern: /#\/efinancials\/([^/?\s]+)/,
        docRequired: true,
        defaultName: 'Report',
    },
    letter: {
        endpoint: '/api/letter/generate',
        defaultFilename: 'letter.docx',
        docPattern: /#\/(?:efinancials|letter)\/([^/?\s]+)/,
        docRequired: true,
        defaultName: 'Letter',
    },
};

// ── Tab switching ───────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach(b => {
            const active = b.dataset.tab === target;
            b.classList.toggle('active', active);
            b.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        document.querySelectorAll('.tab-panel').forEach(p => {
            const active = p.dataset.panel === target;
            p.classList.toggle('active', active);
            p.hidden = !active;
        });
    });
});

// ── Live URL parsing feedback ───────────────────────────────────────────────
document.querySelectorAll('input[data-tool]').forEach(input => {
    const tool = input.dataset.tool;
    const cfg = TOOLS[tool];
    const info = document.querySelector(`[data-info="${tool}"]`);
    const defaultMsg = info.textContent;

    input.addEventListener('input', () => {
        const value = input.value.trim();
        input.classList.remove('input-error');
        if (!value) {
            info.textContent = defaultMsg;
            info.classList.remove('parsed-success');
            return;
        }
        const eng = value.match(ENGAGEMENT_PATTERN);
        if (!eng) {
            info.textContent = 'URL not recognized — expected a Caseware engagement URL';
            info.classList.remove('parsed-success');
            return;
        }
        let summary =
            'Tenant: ' + eng[2] +
            '  |  Engagement: ' + eng[3].slice(0, 12) + '…';
        if (cfg.docPattern) {
            const doc = value.match(cfg.docPattern);
            if (doc) {
                summary += '  |  Document: ' + doc[1].slice(0, 12) + '…';
            } else if (cfg.docRequired) {
                info.textContent = 'Missing document fragment — expected #/' +
                    (tool === 'letter' ? 'letter' : 'efinancials') + '/<documentId>';
                info.classList.remove('parsed-success');
                return;
            }
        }
        info.textContent = summary;
        info.classList.add('parsed-success');
    });

    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            const btn = document.querySelector(`[data-submit="${tool}"]`);
            if (btn) btn.click();
        }
    });
});

// ── Submit handlers ─────────────────────────────────────────────────────────
document.querySelectorAll('[data-submit]').forEach(btn => {
    btn.addEventListener('click', () => submitTool(btn.dataset.submit, btn));
});

async function submitTool(tool, btn) {
    const cfg = TOOLS[tool];
    const urlInput = document.getElementById(`${tool}-url`);
    const nameInput = document.getElementById(`${tool}-name`);
    const statusEl = document.querySelector(`[data-status="${tool}"]`);
    const errorEl = document.querySelector(`[data-error="${tool}"]`);
    const successEl = document.querySelector(`[data-success="${tool}"]`);

    clearMessages(errorEl, successEl, urlInput);

    const url = urlInput.value.trim();
    if (!url) {
        showMessage(errorEl, 'Please paste a Caseware URL.');
        urlInput.classList.add('input-error');
        urlInput.focus();
        return;
    }
    if (!ENGAGEMENT_PATTERN.test(url)) {
        showMessage(errorEl, 'Invalid URL format. Expected https://<host>/<tenant>/e/eng/<engagementId>/...');
        urlInput.classList.add('input-error');
        urlInput.focus();
        return;
    }
    if (cfg.docRequired && cfg.docPattern && !cfg.docPattern.test(url)) {
        showMessage(errorEl, 'URL is missing the required document fragment.');
        urlInput.classList.add('input-error');
        urlInput.focus();
        return;
    }

    const templateName = nameInput.value.trim() || cfg.defaultName;

    setLoading(btn, statusEl, true);
    try {
        const response = await fetch(cfg.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, templateName }),
        });

        if (!response.ok) {
            let errMsg = 'An error occurred while generating the report.';
            try {
                const err = await response.json();
                errMsg = err.error || errMsg;
            } catch (_) { /* response wasn't JSON */ }
            throw new Error(errMsg);
        }

        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;

        const disposition = response.headers.get('Content-Disposition');
        const filenameMatch = disposition && disposition.match(/filename="?([^"]+)"?/);
        a.download = filenameMatch ? filenameMatch[1] : cfg.defaultFilename;

        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(blobUrl);

        showMessage(successEl, 'Report downloaded successfully.');
    } catch (e) {
        showMessage(errorEl, e.message);
    } finally {
        setLoading(btn, statusEl, false);
    }
}

function setLoading(btn, statusEl, loading) {
    btn.disabled = loading;
    statusEl.hidden = !loading;
}

function showMessage(el, msg) {
    el.textContent = msg;
    el.hidden = false;
}

function clearMessages(errorEl, successEl, urlInput) {
    errorEl.hidden = true;
    successEl.hidden = true;
    urlInput.classList.remove('input-error');
}
