"""Vercel serverless entrypoint for the AutoTracker API.

Vercel's Python runtime picks up the module-level ``app`` and serves it as an
ASGI application. ``vercel.json`` rewrites ``/api/*`` and ``/health`` here, so
FastAPI still sees the original path and its normal ``/api`` router prefixes.

The backend package lives in ``backend/`` (kept there so Docker/Render/local
dev are unaffected), hence the sys.path insert below.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# Serverless has no long-lived process and a read-only filesystem outside
# /tmp: the APScheduler sweep and the Telegram polling thread cannot run here.
os.environ["SERVERLESS"] = "true"

from app.main import app  # noqa: E402  (import must follow the sys.path setup)

__all__ = ["app"]
