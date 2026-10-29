"""Pomodoro timer and Japanese-app summary API tests (standard library only)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from server import timer_request_is_same_origin

PROJECT = Path(__file__).resolve().parents[1]
TOKEN = "test-integration-token-" + ("x" * 32)


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
