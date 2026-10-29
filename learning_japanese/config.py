
"""Application configuration from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

APP_TITLE = "Learning Japanese the Python Way"
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))

# Database configuration
_db_value = os.getenv(
    "JP_LEARNING_DB",
    str(PROJECT_ROOT / "data" / "learning_japanese.db"),
)
DB_PATH = Path(_db_value)

if not DB_PATH.is_absolute():
    DB_PATH = (Path.cwd() / DB_PATH).resolve()

# API security
PARTNER_API_KEY = os.getenv("PARTNER_API_KEY", "").strip()

# CORS configuration: comma-separated origins
_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8080,http://127.0.0.1:8080",
)

CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in _raw_origins.split(",")
    if origin.strip()
]

DEFAULT_LEARNER_ID = "demo-user"
PROJECT_ID = "learning-japanese-python-way"
