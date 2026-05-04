# Workflow: Add a new tab to the SE Export Tool

Use this when you want to fold a fifth tool (e.g. `Hyperlink identifier`) into the unified UI.

## Assumptions

- The new tool already exists as a standalone Flask project under `C:/Users/Kenny/Documents/CaseWare/Claude/<NewTool>/`, following the same pattern as the existing four:
  - `tools/<module>.py` exposes `generate_report_bytes(...)` returning file bytes
  - `web/app.py` defines a URL regex and the function signature

## Success criteria

- A new tab appears in `web/static/index.html` and is selectable.
- Submitting the form on that tab POSTs to `/api/<slug>/generate` and downloads the file.
- `python scripts/sync.py` copies the new sibling files for Vercel.
- Local dev still works without the sync step.

## Steps

### 1. Read the new sibling's `web/app.py`

You need:
- Module name (e.g. `hyperlink_report`)
- Function signature for `generate_report_bytes(...)`
- URL regex (engagement + optional document fragment)
- Output MIME type and filename suffix

### 2. Edit `web/app.py`

Add an `_import_tool(...)` call at the top:
```python
hyperlinks = _import_tool("Hyperlink identifier", "hyperlink_report")
```

Add a new endpoint:
```python
@app.route("/api/hyperlinks/generate", methods=["POST"])
def generate_hyperlinks():
    if hyperlinks is None:
        return jsonify({"error": "Hyperlinks tool unavailable."}), 503
    # ... parse URL, call hyperlinks.generate_report_bytes(...), send_file
```

If the URL pattern is unique, add a regex constant near the top.

### 3. Edit `web/static/index.html`

Add the tab button:
```html
<button class="tab-btn" role="tab" data-tab="hyperlinks" aria-selected="false">Hyperlinks</button>
```

Add the panel `<main class="card tab-panel" data-panel="hyperlinks" role="tabpanel" hidden>` mirroring the existing four. Use `data-tool="hyperlinks"` on the URL input and `data-submit="hyperlinks"` on the button.

### 4. Edit `web/static/app.js`

Add an entry to the `TOOLS` dictionary:
```js
hyperlinks: {
    endpoint: '/api/hyperlinks/generate',
    defaultFilename: 'hyperlinks.xlsx',
    docPattern: /#\/efinancials\/([^/?\s]+)/, // or null
    docRequired: false,                       // or true
    defaultName: 'Report',
}
```

Tab switching and submit handlers are wired from `data-*` attributes — no extra JS needed.

### 5. Edit `scripts/sync.py`

Append to `COPIES`:
```python
("Hyperlink identifier/tools/hyperlink_report.py",
 "tools/_synced/hyperlink_report.py"),
```

### 6. Test

- `python web/app.py` → click new tab → submit → file downloads
- `python scripts/sync.py` → confirm new file appears under `tools/_synced/`

### 7. Update docs

- Add the row to the table in `README.md`
- Add the row to the endpoint table in `CLAUDE.md`
