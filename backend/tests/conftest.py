"""Test fixtures. Configures a throwaway SQLite DB + local storage + no OCR/bot
*before* importing the app so settings pick up the right values.
"""
from __future__ import annotations

import os
import tempfile

# --- Environment must be set before importing app modules -------------------
_TMP = tempfile.mkdtemp(prefix="autotracker-test-")
os.environ.update(
    DATABASE_URL=f"sqlite:///{_TMP}/test.db",
    STORAGE_BACKEND="local",
    LOCAL_STORAGE_DIR=f"{_TMP}/storage",
    OCR_ENABLED="false",
    SCHEDULER_ENABLED="false",
    TELEGRAM_BOT_TOKEN="",
    SINGLE_USER="true",
    SINGLE_USER_EMAIL="tester@autotracker.local",
    SECRET_KEY="test-secret",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def vehicle(client):
    resp = client.post(
        "/api/vehicles",
        json={"registration_number": "KA01AB1234", "make": "Toyota", "model": "Corolla"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
