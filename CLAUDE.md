# SE Export Tool — Project Notes

A unified Flask app at `web/app.py` that hosts four CaseWare SE export tools (Checklists, Risk Library, Notes, Letter) behind one tabbed UI.

**Live deployment:** https://kookenny-se-export-tool.vercel.app/ (Vercel project name `kookenny-se-export-tool`)

## Architecture

- **Single source of truth lives in sibling project folders**, not here. Each tool's core extraction module is owned by its standalone project (`../Checklist extractor/`, `../Risk library export/`, `../Note visibility/`, `../Letter export/`).
- `web/app.py` imports those sibling modules live via `sys.path` injection. Locally, edits to a sibling are reflected on the next request — no copy step.
- For Vercel deploys, `scripts/sync.py` copies the relevant sibling files into `tools/_synced/` and `api/letter_generate.js`. These are gitignored — build artifacts only.
- Letter is dual-runtime: locally Python shells out to Node (`subprocess.run(["node", "tools/generate_docx.js", ...])` from `letter_extract.py`); on Vercel the route `/api/letter/generate` is rewritten to `api/letter_generate.js` (a pure-Node Vercel serverless function copied from `Letter export/api/generate.js`).

## Local dev loop

```powershell
python web/app.py    # http://localhost:5000
```

Edit a sibling's `tools/<name>.py`, restart Flask, re-trigger from the unified UI. No sync needed for local.

## Deploy loop

```powershell
python scripts/sync.py
vercel deploy
```

## Endpoint map

| Route | Module called | Output |
|---|---|---|
| `POST /api/checklists/generate` | `checklist_extract.generate_report_bytes(engagement_id, document_id, host, tenant)` | xlsx |
| `POST /api/risks/generate` | `risk_library_export.generate_report_bytes(engagement_id, host, tenant)` | xlsx |
| `POST /api/notes/generate` | `note_visibility_report.generate_report_bytes(engagement_id, document_id, template_name, host, tenant)` | xlsx |
| `POST /api/letter/generate` | `letter_extract.generate_report_bytes(engagement_id, document_id, host, tenant)` | docx |

Each accepts `{url, templateName}` JSON. URL parsing patterns are duplicated from the originals (see top of `web/app.py`).

## Quirks

- Note visibility's `generate_report_bytes` takes `template_name` as a kwarg (the others don't); the unified app passes it through.
- Checklist URLs may or may not include a `#/efinancials/<id>` or `#/checklist/<id>` fragment — both are accepted, and missing means "all checklists".
- Letter URLs MUST include a `#/letter/<id>` or `#/efinancials/<id>` fragment.
- Sibling folder names contain spaces ("Checklist extractor"). The path resolver handles this — but if you rename a sibling, update both `web/app.py:_import_tool` calls and `scripts/sync.py:COPIES`.

## Adding a fifth tool (e.g. Hyperlink identifier)

See `workflows/add_new_tool.md` for the recipe.

## What goes where

- **Local edits**: edit the relevant sibling project. The unified tool just consumes.
- **Unification logic**: `web/app.py`, `web/static/*`, `scripts/sync.py`, `vercel.json` live here.
- **Secrets**: one `.env` at this folder's root (gitignored). The four sibling projects keep their own `.env` files independently.
