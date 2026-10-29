"""Pomodoro timer and Japanese-app summary API tests (standard library only)."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from server import get_integration_summary, timer_request_is_same_origin
from timer_service import timer_request

PROJECT = Path(__file__).resolve().parents[1]
TOKEN = "test-integration-token-" + ("x" * 32)
TEST_SETTINGS = {
    "focus": 1,
    "shortBreak": 1,
    "longBreak": 1,
    "autoStartBreaks": False,
    "autoStartFocus": False,
}


def create_timer_database():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE app_data (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE subjects (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, subject_id INTEGER
        );
        CREATE TABLE focus_sessions (
            session_id TEXT PRIMARY KEY,
            started_at REAL NOT NULL,
            status TEXT NOT NULL,
            elapsed_seconds REAL NOT NULL DEFAULT 0,
            segment_started_at REAL,
            ended_at REAL
        );
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            duration INTEGER NOT NULL,
            task_id INTEGER,
            subject_id INTEGER,
            task_name TEXT,
            subject_name TEXT,
            created_at TEXT NOT NULL,
            focus_session_id TEXT
        );
    """)
    db.execute(
        "INSERT INTO app_data (key, value) VALUES (?, ?)",
        ("settings", json.dumps(TEST_SETTINGS)),
    )
    db.commit()
    return db


def timer_action(db, state, action, now, **extra):
    return timer_request(
        db,
        TEST_SETTINGS,
        {"revision": state["revision"], "action": action, **extra},
        now=now,
    )


class FocusLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.db = create_timer_database()

    def tearDown(self):
        self.db.close()

    def test_start_creates_one_session_and_summary_includes_live_elapsed_time(self):
        now = time.time()
        started = timer_action(self.db, {"revision": 0}, "start", now)
        repeated_start = timer_action(self.db, started, "start", now + 5)

        self.assertEqual(started["focus_session_id"], repeated_start["focus_session_id"])
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM focus_sessions").fetchone()[0],
            1,
        )
        summary = get_integration_summary(self.db, now=now + 10)
        self.assertEqual(summary["today"]["sessions"], 1)
        self.assertEqual(summary["today"]["seconds"], 10)
        self.assertEqual(summary["all_time"]["seconds"], 10)

    def test_pause_resume_excludes_paused_time(self):
        now = time.time()
        state = timer_action(self.db, {"revision": 0}, "start", now)
        state = timer_action(self.db, state, "pause", now + 10)
        self.assertFalse(state["running"])
        state = timer_action(self.db, state, "start", now + 30)
        state = timer_action(self.db, state, "pause", now + 45)

        session = self.db.execute(
            "SELECT status, elapsed_seconds, segment_started_at "
            "FROM focus_sessions WHERE session_id=?",
            (state["focus_session_id"],),
        ).fetchone()
        self.assertEqual(session["status"], "paused")
        self.assertEqual(session["elapsed_seconds"], 25)
        self.assertIsNone(session["segment_started_at"])
        self.assertEqual(
            get_integration_summary(self.db, now=now + 100)["today"]["seconds"],
            25,
        )

    def test_completion_is_persisted_once(self):
        started_at = time.time()
        state = timer_action(self.db, {"revision": 0}, "start", started_at)
        finished = timer_request(
            self.db, TEST_SETTINGS, now=started_at + 60
        )
        timer_request(self.db, TEST_SETTINGS, now=started_at + 70)

        session = self.db.execute(
            "SELECT status, elapsed_seconds FROM focus_sessions WHERE session_id=?",
            (state["focus_session_id"],),
        ).fetchone()
        self.assertEqual(session["status"], "completed")
        self.assertEqual(session["elapsed_seconds"], 60)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
            1,
        )
        self.assertIsNone(finished["focus_session_id"])
        self.assertEqual(
            get_integration_summary(self.db, now=started_at + 70)["all_time"],
            {"sessions": 1, "minutes": 1, "seconds": 60},
        )

    def test_reset_cancels_and_records_elapsed_time(self):
        now = time.time()
        state = timer_action(self.db, {"revision": 0}, "start", now)
        cancelled_id = state["focus_session_id"]
        state = timer_action(self.db, state, "reset", now + 12)

        session = self.db.execute(
            "SELECT status, elapsed_seconds, ended_at FROM focus_sessions "
            "WHERE session_id=?",
            (cancelled_id,),
        ).fetchone()
        self.assertEqual(session["status"], "cancelled")
        self.assertEqual(session["elapsed_seconds"], 12)
        self.assertEqual(session["ended_at"], now + 12)
        self.assertIsNone(state["focus_session_id"])
        self.assertEqual(
            get_integration_summary(self.db, now=now + 20)["today"]["seconds"],
            12,
        )

    def test_breaks_do_not_create_focus_sessions(self):
        state = timer_action(self.db, {"revision": 0}, "mode", 100, mode="shortBreak")
        timer_action(self.db, state, "start", 101)

        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM focus_sessions").fetchone()[0],
            0,
        )
        self.assertEqual(
            get_integration_summary(self.db, now=110)["all_time"],
            {"sessions": 0, "minutes": 0, "seconds": 0},
        )


class PomodoroApiTests(unittest.TestCase):
    def test_timer_api_allows_local_and_render_same_origin_only(self):
        with patch.dict(os.environ, {"RENDER_EXTERNAL_HOSTNAME": ""}):
            self.assertTrue(timer_request_is_same_origin(
                "127.0.0.1:8000", "http://127.0.0.1:8000", "same-origin", 8000))
            self.assertFalse(timer_request_is_same_origin(
                "127.0.0.1:8001", "http://127.0.0.1:8001", "same-origin", 8000))

        with patch.dict(os.environ, {"RENDER_EXTERNAL_HOSTNAME": "pomodoro.onrender.com"}):
            self.assertTrue(timer_request_is_same_origin(
                "pomodoro.onrender.com", "https://pomodoro.onrender.com", "same-origin", 8000))
            self.assertFalse(timer_request_is_same_origin(
                "pomodoro.onrender.com", "http://pomodoro.onrender.com", "same-origin", 8000))
            self.assertFalse(timer_request_is_same_origin(
                "evil.onrender.com", "https://evil.onrender.com", "same-origin", 8000))
            self.assertFalse(timer_request_is_same_origin(
                "pomodoro.onrender.com", "https://pomodoro.onrender.com", "cross-site", 8000))

    @classmethod
    def setUpClass(cls):
        import socket

        cls.temp = tempfile.TemporaryDirectory()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.base = "http://127.0.0.1:" + str(cls.port)

        env = os.environ.copy()
        env.update(
            PORT=str(cls.port),
            HOST="127.0.0.1",
            POMODORO_DB=str(Path(cls.temp.name) / "database.db"),
            STUDY_INTEGRATION_TOKEN=TOKEN,
        )
        cls.proc = subprocess.Popen(
            [sys.executable, "-u", "server.py"],
            cwd=PROJECT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(90):
            try:
                if cls.get("/api/health")["status"] == "ok":
                    break
            except Exception:
                time.sleep(0.07)
        else:
            cls.tearDownClass()
            raise RuntimeError("Pomodoro did not start")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "proc"):
            cls.proc.terminate()
            try:
                cls.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        if hasattr(cls, "temp"):
            cls.temp.cleanup()

    @classmethod
    def get(cls, path, headers=None):
        with urlopen(Request(cls.base + path, headers=headers or {}), timeout=3) as result:
            return json.load(result)

    @classmethod
    def post(cls, path, data, headers=None):
        request = Request(
            cls.base + path,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json", **(headers or {})},
        )
        with urlopen(request, timeout=3) as result:
            return json.load(result)

    def test_pomodoro_summary_is_protected_and_returns_real_totals(self):
        with self.assertRaises(HTTPError) as error:
            self.get("/api/integrations/summary")
        self.assertEqual(error.exception.code, 401)

        with self.assertRaises(HTTPError) as error:
            self.get(
                "/api/integrations/summary",
                headers={"Authorization": "Bearer invalid-token"},
            )
        self.assertEqual(error.exception.code, 401)

        summary = self.get(
            "/api/integrations/summary",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertTrue(summary["success"])
        self.assertEqual(summary["service"], "pomodoro")
        for period in ("today", "all_time"):
            self.assertIsInstance(summary[period]["sessions"], int)
            self.assertIsInstance(summary[period]["minutes"], int)
            self.assertGreaterEqual(summary[period]["sessions"], 0)
            self.assertGreaterEqual(summary[period]["minutes"], 0)
            self.assertIsInstance(summary[period]["seconds"], int)
            self.assertGreaterEqual(summary[period]["seconds"], 0)

    def test_summary_counts_focus_session_at_start_and_deduplicates_start(self):
        state = self.get("/api/timer")
        if state["mode"] == "focus":
            state = self.post(
                "/api/timer",
                {"revision": state["revision"], "action": "reset"},
            )
        else:
            state = self.post(
                "/api/timer",
                {"revision": state["revision"], "action": "mode", "mode": "focus"},
            )
        before = self.get(
            "/api/integrations/summary",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        state = self.post(
            "/api/timer",
            {"revision": state["revision"], "action": "start"},
        )
        after_start = self.get(
            "/api/integrations/summary",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(
            after_start["today"]["sessions"],
            before["today"]["sessions"] + 1,
        )

        state = self.post(
            "/api/timer",
            {"revision": state["revision"], "action": "start"},
        )
        after_repeat = self.get(
            "/api/integrations/summary",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        self.assertEqual(
            after_repeat["today"]["sessions"],
            after_start["today"]["sessions"],
        )
        self.post(
            "/api/timer",
            {"revision": state["revision"], "action": "reset"},
        )

    def test_timer_sync_commands_and_stale_revision(self):
        state = self.get("/api/timer")
        self.assertIn(state["mode"], ("focus", "shortBreak", "longBreak"))
        original_duration = state["remaining_seconds"]
        state = self.post("/api/timer", {"revision": state["revision"], "action": "start"})
        self.assertTrue(state["running"])
        state = self.post("/api/timer", {"revision": state["revision"], "action": "pause"})
        self.assertFalse(state["running"])
        self.assertLessEqual(state["remaining_seconds"], original_duration)
        state = self.post(
            "/api/timer",
            {"revision": state["revision"], "action": "mode", "mode": "shortBreak"},
        )
        self.assertEqual(state["remaining_seconds"], state["settings"]["shortBreak"] * 60)
        state = self.post("/api/timer", {"revision": state["revision"], "action": "reset"})
        self.assertEqual(state["mode"], "shortBreak")
        self.assertFalse(state["running"])
        with self.assertRaises(HTTPError) as error:
            self.post("/api/timer", {"revision": state["revision"] - 1, "action": "start"})
        self.assertEqual(error.exception.code, 409)

    def test_existing_timer_ui_and_sync_script_remain(self):
        html = (PROJECT / "index.html").read_text()
        self.assertIn('script.js?v=2.2.1', html)
        self.assertIn('timer-sync.js?v=1', html)
        self.assertIn('id="startButton"', html)
        self.assertIn("Focus", html)
        self.assertNotIn("<iframe", html.lower())

    def test_original_settings_form_updates_durable_timer(self):
        state = self.get("/api/timer")
        settings = {
            "focus": 35,
            "shortBreak": 7,
            "longBreak": 20,
            "autoStartBreaks": False,
            "autoStartFocus": False,
        }
        response = self.post("/api/settings", {"settings": settings})
        self.assertEqual(response["settings"], settings)
        updated = self.get("/api/timer")
        self.assertEqual(updated["settings"], settings)
        self.assertEqual(updated["revision"], state["revision"] + 1)
        self.assertFalse(updated["running"])

    def test_timer_endpoint_rejects_cross_origin_requests(self):
        with self.assertRaises(HTTPError) as error:
            self.get("/api/timer", headers={"Origin": "http://evil.test"})
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError) as error:
            self.post(
                "/api/timer",
                {"action": "start", "revision": 0},
                headers={"Origin": "http://evil.test"},
            )
        self.assertEqual(error.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
