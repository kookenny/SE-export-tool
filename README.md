# SE Export Tool

**Live:** https://kookenny-se-export-tool.vercel.app/

A single web app that hosts four Caseware SE export tools behind tabs:

| Tab | Output | Source-of-truth |
|---|---|---|
| Checklists | `.xlsx` | sibling `Checklist extractor/` |
| Risk Library | `.xlsx` | sibling `Risk library export/` |
| Notes Library | `.xlsx` | sibling `Note visibility/` |
| Letter | `.docx` | sibling `Letter export/` (Python + Node) |

The four standalone projects under `C:/Users/Kenny/Documents/CaseWare/Claude/` remain the canonical implementations. This unified tool imports their core modules live from disk, so a change in any sibling is reflected here on the next request.

## Layout

```
SE export tool/
├── web/app.py              # Flask app — 4 endpoints
├── web/static/             # tabbed HTML UI + JS + shared CSS
├── scripts/sync.py         # copies sibling code into deploy folder for Vercel
├── api/index.py            # Vercel Python entry (re-exports web.app:app)
├── api/letter_generate.js  # (gitignored, synced) Vercel Node handler for Letter
├── tools/__init__.py
├── tools/_synced/          # (gitignored, synced) Python fallback for Vercel
├── vercel.json
├── requirements.txt        # Python deps
├── package.json            # Node deps (Letter only)
└── .env                    # CW_* secrets (gitignored)
```

## Setup

```powershell
cd "SE export tool"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm install
copy .env.example .env       # then fill in CW_* values
```

## Run locally

```powershell
python web/app.py
# → http://localhost:5000
```

The page loads with four tabs. Each tab paste-a-URL → click → file downloads. The originals (sibling project folders) keep working independently on their own ports if you ever want to fall back.

## Deploy to Vercel

Vercel only uploads what's inside `SE export tool/` — sibling code isn't reachable from a deployed function. Run the sync script before deploying so the four sibling files are copied into the deploy bundle:

```powershell
python scripts/sync.py
vercel deploy
```

`scripts/sync.py` copies:

- `Checklist extractor/tools/checklist_extract.py` → `tools/_synced/checklist_extract.py`
- `Risk library export/tools/risk_library_export.py` → `tools/_synced/risk_library_export.py`
- `Note visibility/tools/note_visibility_report.py` → `tools/_synced/note_visibility_report.py`
- `Letter export/tools/letter_extract.py` → `tools/_synced/letter_extract.py`
- `Letter export/tools/generate_docx.js` → `tools/_synced/generate_docx.js`
- `Letter export/api/generate.js` → `api/letter_generate.js`

All targets are gitignored — they are build artifacts, refreshed each deploy.

Set the same `CW_*` env vars in the Vercel project settings.

### Credentials and regions

Each request derives OAuth credentials from the pasted URL, trying:

1. `CW_<TENANT-PREFIX>_*` — e.g. tenant `uk-develop` → `CW_UK_CLIENT_ID` / `CW_UK_CLIENT_SECRET`
2. `CW_<HOST-PREFIX>_*` — e.g. host `eu.cwcloudpartner.com` → `CW_EU_CLIENT_ID` / `CW_EU_CLIENT_SECRET`
3. Generic `CW_CLIENT_ID` / `CW_CLIENT_SECRET`

Currently configured: Canada (`CW_CA_*`), United States (`CW_US_*`), Europe (`CW_EU_*`), United Kingdom (`CW_UK_*` — UK tenants run on the EU host). Add credentials for a new region/tenant by setting the matching prefixed env vars locally and on Vercel; no code change needed.

## How sibling-vs-synced resolution works

`web/app.py` defines a `_import_tool(folder, module)` helper that tries the sibling first (`../<folder>/tools/<module>.py`) and falls back to `tools/_synced/<module>.py`. Locally the sibling exists; on Vercel only the synced copy exists. Either way the same Flask routes work.

For Letter, the Python+Node subprocess pipeline only runs locally. On Vercel the `/api/letter/generate` route is rewritten to `api/letter_generate.js` (a pure-Node serverless function) — same pattern as the standalone `Letter export` project.

## Adding a fifth tab

See `workflows/add_new_tool.md`.
