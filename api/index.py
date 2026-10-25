"""Vercel Python serverless entry: serves the /api routes.
The bundled SQLite DB is copied to writable /tmp on cold start (read-only analytics)."""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_SRC = os.path.join(ROOT, "data", "wind.db")
DB_DST = "/tmp/wind.db"
if not os.path.exists(DB_DST):
    shutil.copy(DB_SRC, DB_DST)
os.environ.setdefault("DB_PATH", DB_DST)
os.environ.setdefault("FRONTEND_DIST", os.path.join(ROOT, "frontend", "dist"))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.main import app  # noqa: E402  (FastAPI ASGI app; Vercel invokes it directly)
