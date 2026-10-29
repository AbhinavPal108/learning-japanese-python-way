"""Smoke tests for the REST API and stored quiz workflow.

Run with: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import tempfile
import unittest

_TEST_DIR = tempfile.TemporaryDirectory(prefix="jp-way-test-")
os.environ["JP_LEARNING_DB"] = os.path.join(_TEST_DIR.name, "test.db")
os.environ.pop("PARTNER_API_KEY", None)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from learning_japanese.backend.api import router
from learning_japanese.data.database import init_db, get_connection
from learning_japanese.services.number_service import number_details

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


if __name__ == "__main__":
    unittest.main()
