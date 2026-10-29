"""Server-side client for the external Pomodoro focus summary."""
from __future__ import annotations

import logging
from typing import Any

import httpx


LOGGER = logging.getLogger(__name__)
SUMMARY_URL = (
    "https://pomodoro-website-python-project.onrender.com/"
    "api/integrations/summary"
)
REQUEST_TIMEOUT_SECONDS = 3.0


def _extract_statistics(payload: Any) -> dict[str, int | float]:
    statistics: dict[str, int | float] = {}

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, nested_value in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                visit(nested_value, child_path)
        elif isinstance(value, list):
            for index, nested_value in enumerate(value):
                visit(nested_value, f"{path} {index + 1}")
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            statistics[path] = value

    if isinstance(payload, dict):
        visit(payload, "")
    return statistics


def get_pomodoro_summary() -> dict[str, int | float] | None:
    """Fetch numeric focus statistics, returning None when the service is unavailable."""
    try:
        response = httpx.get(SUMMARY_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        LOGGER.warning("Pomodoro summary request failed: %s", exc)
        return None
    except ValueError as exc:
        LOGGER.warning("Pomodoro summary returned invalid JSON: %s", exc)
        return None

    statistics = _extract_statistics(payload)
    if not statistics:
        LOGGER.warning("Pomodoro summary did not contain numeric focus statistics")
        return None
    return statistics
