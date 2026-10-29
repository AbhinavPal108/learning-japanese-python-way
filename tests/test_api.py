"""Smoke tests for the REST API and stored quiz workflow.

Run with: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

import httpx

_TEST_DIR = tempfile.TemporaryDirectory(prefix="jp-way-test-")
os.environ["JP_LEARNING_DB"] = os.path.join(_TEST_DIR.name, "test.db")
os.environ.pop("PARTNER_API_KEY", None)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from learning_japanese.backend.api import router
from learning_japanese.data.database import init_db, get_connection
from learning_japanese.services.number_service import number_details
from learning_japanese.services.pomodoro_service import (
    MODE_DURATIONS,
    PomodoroTimer,
    get_pomodoro_summary,
    get_pomodoro_timer,
    reset_pomodoro_timer,
    start_pomodoro_timer,
    tick_pomodoro_timer,
)

_test_app = FastAPI()
_test_app.include_router(router)
client = TestClient(_test_app)


class NumberTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()

    def test_full_number_range(self) -> None:
        response = client.get("/api/v1/numbers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 100)
        self.assertEqual(len(response.json()["items"]), 100)

    def test_edge_number_readings(self) -> None:
        self.assertEqual(number_details(10)["hiragana"], "じゅう")
        self.assertEqual(number_details(11)["hiragana"], "じゅういち")
        self.assertEqual(number_details(20)["hiragana"], "にじゅう")
        self.assertEqual(number_details(42)["hiragana"], "よんじゅうに")
        self.assertEqual(number_details(99)["kanji"], "九十九")
        self.assertEqual(number_details(100)["hiragana"], "ひゃく")

    def test_invalid_number_returns_error(self) -> None:
        self.assertEqual(client.get("/api/v1/numbers/101").status_code, 422)


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()

    def test_practice_attempt_is_saved(self) -> None:
        response = client.post("/api/v1/practice/attempts", json={
            "learner_id": "test-learner", "question_number": 42,
            "selected_number": 42, "source_project": "unit-test",
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["is_correct"])
        progress = client.get("/api/v1/progress/test-learner").json()
        self.assertEqual(progress["practice_attempts"], 1)
        self.assertEqual(progress["practice_accuracy"], 100.0)

    def test_quiz_scoring_saves_each_answer(self) -> None:
        started = client.post("/api/v1/quizzes/start", json={
            "learner_id": "quiz-learner", "num_questions": 10,
        })
        self.assertEqual(started.status_code, 201)
        quiz = started.json()
        self.assertEqual(len(quiz["questions"]), 10)
        with get_connection() as conn:
            targets = conn.execute(
                "SELECT position, target_number FROM quiz_questions WHERE quiz_id = ? ORDER BY position",
                (quiz["quiz_id"],),
            ).fetchall()
        payload = {"answers": [{"position": row["position"], "selected_number": row["target_number"]}
                               for row in targets]}
        submitted = client.post(f"/api/v1/quizzes/{quiz['quiz_id']}/submit", json=payload)
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["score"], 10)
        self.assertEqual(submitted.json()["percentage"], 100.0)
        self.assertEqual(len(submitted.json()["answers"]), 10)
        progress = client.get("/api/v1/progress/quiz-learner").json()
        self.assertEqual(progress["quizzes_taken"], 1)
        duplicate = client.post(f"/api/v1/quizzes/{quiz['quiz_id']}/submit", json=payload)
        self.assertEqual(duplicate.status_code, 409)

    def test_partner_exchange_endpoints(self) -> None:
        incoming = client.post("/api/v1/partner/events", json={
            "learner_id": "shared-user", "event_type": "module_completed",
            "source_project": "partner-project", "payload": {"module": "flashcards"},
        })
        self.assertEqual(incoming.status_code, 201)
        self.assertTrue(incoming.json()["accepted"])
        exported = client.get("/api/v1/partner/export/shared-user")
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.json()["source_project"], "learning-japanese-python-way")
        self.assertTrue(any(event["source_project"] == "partner-project"
                            for event in exported.json()["recent_learning_events"]))


class PomodoroTimerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()

    def test_focus_cycle_uses_long_break_after_four_sessions(self) -> None:
        timer = PomodoroTimer()

        for expected_session in range(1, 5):
            timer.start(now=0)
            self.assertEqual(timer.finish_interval(now=MODE_DURATIONS["focus"]), "focus")
            self.assertEqual(timer.completed_focus_sessions, expected_session)

            expected_break = "longBreak" if expected_session == 4 else "shortBreak"
            self.assertEqual(timer.mode, expected_break)
            self.assertEqual(timer.remaining, MODE_DURATIONS[expected_break])

            timer.start(now=1000)
            self.assertEqual(
                timer.finish_interval(now=1000 + MODE_DURATIONS[expected_break]),
                expected_break,
            )
            self.assertEqual(timer.mode, "focus")

    def test_pause_resume_and_invalid_mode(self) -> None:
        timer = PomodoroTimer()
        timer.start(now=10)
        timer.pause(now=20)
        self.assertEqual(timer.remaining_seconds(now=20), MODE_DURATIONS["focus"] - 10)

        timer.start(now=30)
        self.assertEqual(timer.remaining_seconds(now=35), MODE_DURATIONS["focus"] - 15)
        with self.assertRaises(ValueError):
            timer.select_mode("invalid")

    def test_running_timer_persists_and_expires_after_page_reload(self) -> None:
        reset_pomodoro_timer(now=100)
        started = start_pomodoro_timer(now=100)

        restored = get_pomodoro_timer(now=110)
        self.assertTrue(restored.running)
        self.assertEqual(restored.started_at, started.started_at)
        self.assertEqual(
            restored.remaining_seconds(now=110),
            MODE_DURATIONS["focus"] - 10,
        )

        completed, finished_mode = tick_pomodoro_timer(
            now=100 + MODE_DURATIONS["focus"]
        )
        self.assertEqual(finished_mode, "focus")
        self.assertEqual(completed.completed_focus_sessions, 1)
        self.assertEqual(completed.mode, "shortBreak")
        self.assertFalse(completed.running)

    def test_api_summary_returns_today_and_all_time_focus_statistics(self) -> None:
        response = httpx.Response(
            200,
            json={
                "success": True,
                "service": "pomodoro",
                "today": {"sessions": 2, "minutes": 50},
                "all_time": {"sessions": 10, "minutes": 250},
            },
            request=httpx.Request("GET", "https://pomodoro.test/api/integrations/summary"),
        )
        with (
            patch(
                "learning_japanese.services.pomodoro_service.POMODORO_URL",
                "https://pomodoro.test",
            ),
            patch(
                "learning_japanese.services.pomodoro_service.STUDY_INTEGRATION_TOKEN",
                "t" * 40,
            ),
            patch(
                "learning_japanese.services.pomodoro_service.httpx.get",
                return_value=response,
            ) as get,
        ):
            summary = get_pomodoro_summary()

        self.assertEqual(
            summary,
            {
                "today_sessions": 2,
                "today_minutes": 50,
                "all_time_sessions": 10,
                "all_time_minutes": 250,
            },
        )
        self.assertTrue(
            get.call_args.kwargs["headers"]["Authorization"].startswith("Bearer ")
        )
        self.assertEqual(get.call_args.kwargs["timeout"], 3.0)

    def test_api_failures_return_unavailable(self) -> None:
        request = httpx.Request("GET", "https://pomodoro.test/api/integrations/summary")
        failures = (
            httpx.ConnectError("connection failed", request=request),
            httpx.Response(503, request=request),
            httpx.Response(200, text="invalid JSON", request=request),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with (
                    patch(
                        "learning_japanese.services.pomodoro_service.POMODORO_URL",
                        "https://pomodoro.test",
                    ),
                    patch(
                        "learning_japanese.services.pomodoro_service.STUDY_INTEGRATION_TOKEN",
                        "t" * 40,
                    ),
                    patch(
                        "learning_japanese.services.pomodoro_service.httpx.get",
                        side_effect=failure if isinstance(failure, Exception) else None,
                        return_value=failure if isinstance(failure, httpx.Response) else None,
                    ),
                ):
                    self.assertIsNone(get_pomodoro_summary())

    def test_api_rejects_non_https_remote_url_before_request(self) -> None:
        with (
            patch(
                "learning_japanese.services.pomodoro_service.POMODORO_URL",
                "http://pomodoro.example",
            ),
            patch(
                "learning_japanese.services.pomodoro_service.STUDY_INTEGRATION_TOKEN",
                "t" * 40,
            ),
            patch("learning_japanese.services.pomodoro_service.httpx.get") as get,
        ):
            self.assertIsNone(get_pomodoro_summary())
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
