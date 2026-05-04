"""
Unified Flask backend for the SE Export Tool.

Hosts four CaseWare SE export tools behind one tabbed UI:
  - Checklists       (xlsx)  → tools.checklist_extract.generate_report_bytes
  - Risk library     (xlsx)  → tools.risk_library_export.generate_report_bytes
  - Notes library    (xlsx)  → tools.note_visibility_report.generate_report_bytes
  - Letter           (docx)  → tools.letter_extract.generate_report_bytes

Source-of-truth resolution
--------------------------
Each tool's core module lives in its own sibling project (the standalone
folders under C:/Users/Kenny/Documents/CaseWare/Claude). Locally we import
those siblings directly via sys.path so edits to a sibling are reflected
immediately. On Vercel siblings aren't reachable, so we fall back to
tools/_synced/ which is populated by scripts/sync.py at deploy time.

For Letter the Vercel path is the Node serverless function api/letter_generate.js;
the Python-side Letter endpoint is local-only.
"""
import importlib
import io
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, send_from_directory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIBLINGS_ROOT = PROJECT_ROOT.parent
SYNCED_ROOT = PROJECT_ROOT / "tools" / "_synced"

load_dotenv(PROJECT_ROOT / ".env")


def _import_tool(sibling_folder: str, module_name: str):
    """
    Import a tool's core module from its sibling project, falling back to
    tools/_synced/ when the sibling isn't present (Vercel).
    Returns the imported module, or None if neither source is available
    (so the unified app can still run partial — that endpoint will 503).
    """
    sibling_tools = SIBLINGS_ROOT / sibling_folder / "tools"
    if sibling_tools.is_dir():
        path = str(sibling_tools)
    elif SYNCED_ROOT.is_dir() and (SYNCED_ROOT / f"{module_name}.py").exists():
        path = str(SYNCED_ROOT)
    else:
        return None
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(module_name)


checklists = _import_tool("Checklist extractor", "checklist_extract")
risk_library = _import_tool("Risk library export", "risk_library_export")
note_visibility = _import_tool("Note visibility", "note_visibility_report")
letter_extract = _import_tool("Letter export", "letter_extract")

app = Flask(__name__, static_folder="static")

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

CW_URL_PATTERN = re.compile(r"https?://([^/]+)/([^/]+)/e/eng/([^/]+)")
CW_DOC_CHECKLIST = re.compile(r"#/(?:efinancials|checklist)/([^/?\s]+)")
CW_DOC_NOTES = re.compile(r"#/efinancials/([^/?\s]+)")
CW_DOC_LETTER = re.compile(r"#/(?:efinancials|letter)/([^/?\s]+)")


def _safe_name(template_name: str) -> str:
    return re.sub(r"[^\w\s-]", "", template_name).strip().replace(" ", "_")


def _parse_engagement(url: str):
    """Parse host/tenant/engagement_id, returning (host, tenant, engagement_id) or None."""
    m = CW_URL_PATTERN.search(url)
    if not m:
        return None
    return f"https://{m.group(1)}", m.group(2), m.group(3)


def _bad_url():
    return jsonify({
        "error": "Invalid Caseware URL. Expected format: "
                 "https://<host>/<tenant>/e/eng/<engagementId>/..."
    }), 400


def _wrap_tool_call(func):
    """Run a tool function and translate exceptions into JSON error responses."""
    try:
        return func(), None
    except ValueError as e:
        return None, (jsonify({"error": str(e)}), 422)
    except RuntimeError as e:
        return None, (jsonify({"error": str(e)}), 502)
    except Exception as e:  # noqa: BLE001
        return None, (jsonify({"error": f"Unexpected error: {e}"}), 500)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/checklists/generate", methods=["POST"])
def generate_checklists():
    if checklists is None:
        return jsonify({"error": "Checklists tool unavailable (no sibling and no synced copy)."}), 503

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required."}), 400
    parsed = _parse_engagement(url)
    if not parsed:
        return _bad_url()
    host, tenant, engagement_id = parsed
    template_name = (data.get("templateName") or "Report").strip()
    doc_match = CW_DOC_CHECKLIST.search(url)
    document_id = doc_match.group(1) if doc_match else ""

    excel_bytes, err = _wrap_tool_call(lambda: checklists.generate_report_bytes(
        engagement_id=engagement_id,
        document_id=document_id,
        host=host,
        tenant=tenant,
    ))
    if err:
        return err

    safe = _safe_name(template_name)
    filename = f"{safe}_checklists.xlsx" if safe else f"checklists_{engagement_id[:8]}.xlsx"
    return send_file(io.BytesIO(excel_bytes), mimetype=XLSX_MIME,
                     as_attachment=True, download_name=filename)


@app.route("/api/risks/generate", methods=["POST"])
def generate_risks():
    if risk_library is None:
        return jsonify({"error": "Risk library tool unavailable (no sibling and no synced copy)."}), 503

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required."}), 400
    parsed = _parse_engagement(url)
    if not parsed:
        return _bad_url()
    host, tenant, engagement_id = parsed
    template_name = (data.get("templateName") or "Report").strip()

    excel_bytes, err = _wrap_tool_call(lambda: risk_library.generate_report_bytes(
        engagement_id=engagement_id,
        host=host,
        tenant=tenant,
    ))
    if err:
        return err

    safe = _safe_name(template_name)
    filename = f"{safe}_risk_library.xlsx" if safe else f"risk_library_{engagement_id[:8]}.xlsx"
    return send_file(io.BytesIO(excel_bytes), mimetype=XLSX_MIME,
                     as_attachment=True, download_name=filename)


@app.route("/api/notes/generate", methods=["POST"])
def generate_notes():
    if note_visibility is None:
        return jsonify({"error": "Notes library tool unavailable (no sibling and no synced copy)."}), 503

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required."}), 400
    parsed = _parse_engagement(url)
    if not parsed:
        return _bad_url()
    host, tenant, engagement_id = parsed
    doc_match = CW_DOC_NOTES.search(url)
    if not doc_match:
        return jsonify({
            "error": "URL must include a document fragment (e.g. #/efinancials/<documentId>)"
        }), 400
    document_id = doc_match.group(1)
    template_name = (data.get("templateName") or "Report").strip()

    excel_bytes, err = _wrap_tool_call(lambda: note_visibility.generate_report_bytes(
        engagement_id=engagement_id,
        document_id=document_id,
        template_name=template_name,
        host=host,
        tenant=tenant,
    ))
    if err:
        return err

    safe = _safe_name(template_name)
    filename = f"{safe}_note_visibility.xlsx" if safe else f"note_visibility_{engagement_id[:8]}.xlsx"
    return send_file(io.BytesIO(excel_bytes), mimetype=XLSX_MIME,
                     as_attachment=True, download_name=filename)


@app.route("/api/letter/generate", methods=["POST"])
def generate_letter():
    # Letter uses Python+Node subprocess locally; on Vercel this route is
    # rewritten to api/letter_generate.js (Node-only) and never reaches Flask.
    if letter_extract is None:
        return jsonify({"error": "Letter tool unavailable (sibling 'Letter export' not found)."}), 503

    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL is required."}), 400
    parsed = _parse_engagement(url)
    if not parsed:
        return _bad_url()
    host, tenant, engagement_id = parsed
    doc_match = CW_DOC_LETTER.search(url)
    if not doc_match:
        return jsonify({
            "error": "URL must include a document fragment (e.g. #/letter/<documentId>)"
        }), 400
    document_id = doc_match.group(1)
    template_name = (data.get("templateName") or "Letter").strip()

    docx_bytes, err = _wrap_tool_call(lambda: letter_extract.generate_report_bytes(
        engagement_id=engagement_id,
        document_id=document_id,
        host=host,
        tenant=tenant,
    ))
    if err:
        return err

    safe = _safe_name(template_name)
    filename = f"{safe}_letter.docx" if safe else f"letter_{engagement_id[:8]}.docx"
    return send_file(io.BytesIO(docx_bytes), mimetype=DOCX_MIME,
                     as_attachment=True, download_name=filename)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", port=5000)
