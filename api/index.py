"""Vercel serverless entrypoint — re-exports the Flask app from web/app.py."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
sys.path.insert(0, str(PROJECT_ROOT / "tools" / "_synced"))

from web.app import app  # noqa: E402,F401 — Vercel looks for `app`
