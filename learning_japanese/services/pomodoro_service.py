"""Local Pomodoro timer state and focus/break cycle."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
import math
import logging
import time
from urllib.parse import urlsplit

import httpx

from learning_japanese.config import POMODORO_URL, STUDY_INTEGRATION_TOKEN
from learning_japanese.data.database import get_connection


TimerMode = Literal["focus", "shortBreak", "longBreak"]
MODE_DURATIONS = {
    "focus": 25 * 60,
    "shortBreak": 5 * 60,
    "longBreak": 15 * 60,
}
LOGGER = logging.getLogger(__name__)
SUMMARY_TIMEOUT_SECONDS = 3.0
SUMMARY_PATH = "/api/integrations/summary"


@dataclass
class PomodoroTimer:
    mode: TimerMode = "focus"
    focus_round: int = 1
    completed_focus_sessions: int = 0
    remaining: float = field(default_factory=lambda: MODE_DURATIONS["focus"])
    started_at: float | None = None

    @property
    def running(self) -> bool:
        return self.started_at is not None

    def remaining_seconds(self, now: float) -> int:
        remaining = self.remaining
        if self.started_at is not None:
            remaining -= now - self.started_at
        return max(0, math.ceil(remaining))

    def start(self, now: float) -> None:
        if self.started_at is None:
            self.started_at = now

    def pause(self, now: float) -> None:
        if self.started_at is not None:
            self.remaining = max(0.0, self.remaining - (now - self.started_at))
            self.started_at = None

    def reset(self) -> None:
        self.started_at = None
        self.remaining = MODE_DURATIONS[self.mode]

    def select_mode(self, mode: str) -> None:
        if mode not in MODE_DURATIONS:
            raise ValueError(f"Unknown Pomodoro mode: {mode}")
        self.mode = mode
        self.reset()

    def finish_interval(self, now: float) -> TimerMode | None:
        if self.started_at is None or self.remaining_seconds(now) > 0:
            return None

        finished_mode = self.mode
        self.started_at = None
        if finished_mode == "focus":
            self.completed_focus_sessions += 1
            if self.focus_round == 4:
                self.focus_round = 1
                self.mode = "longBreak"
            else:
                self.focus_round += 1
                self.mode = "shortBreak"
        else:
            self.mode = "focus"

        self.remaining = MODE_DURATIONS[self.mode]
        return finished_mode


def _read_timer(connection) -> PomodoroTimer:
    row = connection.execute(
        "SELECT mode, focus_round, completed_focus_sessions, remaining, started_at "
        "FROM pomodoro_timer WHERE id = 1"
    ).fetchone()
    if row is None:
        timer = PomodoroTimer()
        _write_timer(connection, timer)
        return timer
    return PomodoroTimer(
        mode=row["mode"],
        focus_round=row["focus_round"],
        completed_focus_sessions=row["completed_focus_sessions"],
        remaining=row["remaining"],
        started_at=row["started_at"],
    )


def _write_timer(connection, timer: PomodoroTimer) -> None:
    connection.execute(
        """
        INSERT INTO pomodoro_timer
            (id, mode, focus_round, completed_focus_sessions, remaining, started_at)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            mode = excluded.mode,
            focus_round = excluded.focus_round,
            completed_focus_sessions = excluded.completed_focus_sessions,
            remaining = excluded.remaining,
            started_at = excluded.started_at
        """,
        (
            timer.mode,
            timer.focus_round,
            timer.completed_focus_sessions,
            timer.remaining,
            timer.started_at,
        ),
    )


def get_pomodoro_timer(now: float | None = None) -> PomodoroTimer:
    """Load timer state from SQLite and advance an interval if its deadline passed."""
    now = time.time() if now is None else now
    with get_connection() as connection:
        timer = _read_timer(connection)
        if timer.finish_interval(now) is not None:
            _write_timer(connection, timer)
        return timer


def start_pomodoro_timer(now: float | None = None) -> PomodoroTimer:
    now = time.time() if now is None else now
    with get_connection() as connection:
        timer = _read_timer(connection)
        timer.finish_interval(now)
        timer.start(now)
        _write_timer(connection, timer)
        return timer


def pause_pomodoro_timer(now: float | None = None) -> PomodoroTimer:
    now = time.time() if now is None else now
    with get_connection() as connection:
        timer = _read_timer(connection)
        timer.finish_interval(now)
        timer.pause(now)
        _write_timer(connection, timer)
        return timer


def reset_pomodoro_timer(now: float | None = None) -> PomodoroTimer:
    now = time.time() if now is None else now
    with get_connection() as connection:
        timer = _read_timer(connection)
        timer.finish_interval(now)
        timer.reset()
        _write_timer(connection, timer)
        return timer


def select_pomodoro_mode(mode: str, now: float | None = None) -> PomodoroTimer:
    now = time.time() if now is None else now
    with get_connection() as connection:
        timer = _read_timer(connection)
        timer.finish_interval(now)
        timer.select_mode(mode)
        _write_timer(connection, timer)
        return timer


def tick_pomodoro_timer(now: float | None = None) -> tuple[PomodoroTimer, TimerMode | None]:
    now = time.time() if now is None else now
    with get_connection() as connection:
        timer = _read_timer(connection)
        finished_mode = timer.finish_interval(now)
        if finished_mode is not None:
            _write_timer(connection, timer)
        return timer, finished_mode


def get_pomodoro_summary() -> dict[str, int] | None:
    """Fetch validated focus totals from Pomodoro without exposing its token."""
    if len(STUDY_INTEGRATION_TOKEN) < 32:
        LOGGER.warning("Pomodoro API token is not configured")
        return None

    try:
        parsed_url = urlsplit(POMODORO_URL)
        hostname = parsed_url.hostname
        _ = parsed_url.port
    except ValueError as exc:
        LOGGER.warning("Pomodoro API URL is invalid: %s", exc)
        return None

    is_loopback = hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        parsed_url.scheme not in {"https", "http"}
        or not hostname
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
        or (parsed_url.scheme != "https" and not is_loopback)
    ):
        LOGGER.warning("Pomodoro API URL must use HTTPS except on localhost")
        return None

    try:
        response = httpx.get(
            f"{POMODORO_URL}{SUMMARY_PATH}",
            headers={"Authorization": f"Bearer {STUDY_INTEGRATION_TOKEN}"},
            timeout=SUMMARY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        LOGGER.warning("Pomodoro API request failed: %s", exc)
        return None
    except ValueError as exc:
        LOGGER.warning("Pomodoro API returned invalid JSON: %s", exc)
        return None

    if (
        not isinstance(payload, dict)
        or payload.get("success") is not True
        or payload.get("service") != "pomodoro"
    ):
        LOGGER.warning("Pomodoro API returned an unexpected response")
        return None

    summary: dict[str, int] = {}
    for period in ("today", "all_time"):
        values = payload.get(period)
        if not isinstance(values, dict):
            LOGGER.warning("Pomodoro API returned invalid %s totals", period)
            return None
        for metric in ("sessions", "minutes"):
            value = values.get(metric)
            if type(value) is not int or value < 0:
                LOGGER.warning("Pomodoro API returned invalid %s %s", period, metric)
                return None
            summary[f"{period}_{metric}"] = value
    return summary
