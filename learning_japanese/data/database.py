"""SQLite persistence; all queries live in this module or service functions."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from learning_japanese.config import DB_PATH


def _connect() -> sqlite3.Connection:
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    """Create tables and indexes if they do not exist yet."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS learning_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learner_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                number INTEGER,
                payload_json TEXT NOT NULL DEFAULT '{}',
                source_project TEXT NOT NULL DEFAULT 'learning-japanese-python-way',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS practice_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learner_id TEXT NOT NULL,
                question_number INTEGER NOT NULL CHECK(question_number BETWEEN 1 AND 100),
                selected_number INTEGER NOT NULL CHECK(selected_number BETWEEN 1 AND 100),
                is_correct INTEGER NOT NULL CHECK(is_correct IN (0, 1)),
                source_project TEXT NOT NULL DEFAULT 'learning-japanese-python-way',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quiz_sessions (
                quiz_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL,
                source_project TEXT NOT NULL DEFAULT 'learning-japanese-python-way',
                started_at TEXT NOT NULL,
                submitted_at TEXT,
                total_questions INTEGER NOT NULL,
                score INTEGER,
                score_pct REAL,
                grade TEXT
            );

            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id TEXT NOT NULL REFERENCES quiz_sessions(quiz_id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                target_number INTEGER NOT NULL CHECK(target_number BETWEEN 1 AND 100),
                options_json TEXT NOT NULL,
                UNIQUE(quiz_id, position)
            );

            CREATE TABLE IF NOT EXISTS quiz_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id TEXT NOT NULL REFERENCES quiz_sessions(quiz_id) ON DELETE CASCADE,
                question_id INTEGER NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
                selected_number INTEGER,
                is_correct INTEGER NOT NULL CHECK(is_correct IN (0, 1)),
                answered_at TEXT NOT NULL,
                UNIQUE(quiz_id, question_id)
            );

            CREATE TABLE IF NOT EXISTS pomodoro_timer (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                mode TEXT NOT NULL CHECK (mode IN ('focus', 'shortBreak', 'longBreak')),
                focus_round INTEGER NOT NULL CHECK (focus_round BETWEEN 1 AND 4),
                completed_focus_sessions INTEGER NOT NULL DEFAULT 0,
                remaining REAL NOT NULL,
                started_at REAL
            );

            CREATE INDEX IF NOT EXISTS idx_events_learner_time
                ON learning_events(learner_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_practice_learner_time
                ON practice_attempts(learner_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_quiz_learner_time
                ON quiz_sessions(learner_id, started_at);
            """
        )
