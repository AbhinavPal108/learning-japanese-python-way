"""Business logic for learning events, practice, quizzes, and progress."""
from __future__ import annotations

import json
import random
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from learning_japanese.config import PROJECT_ID
from learning_japanese.data.database import get_connection
from learning_japanese.services.number_service import number_details


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def grade_for_percentage(percentage: float) -> str:
    if percentage >= 90:
        return "Excellent"
    if percentage >= 75:
        return "Good"
    if percentage >= 60:
        return "Developing"
    return "Needs Practice"


def record_learning_event(
    learner_id: str,
    event_type: str,
    number: int | None = None,
    payload: dict[str, Any] | None = None,
    source_project: str = PROJECT_ID,
) -> dict[str, Any]:
    if number is not None and not 1 <= number <= 100:
        raise ValueError("number must be between 1 and 100")
    created_at = utc_now()
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO learning_events
               (learner_id, event_type, number, payload_json, source_project, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (learner_id, event_type, number, json.dumps(payload or {}, ensure_ascii=False), source_project, created_at),
        )
        event_id = cursor.lastrowid
    return {"event_id": event_id, "learner_id": learner_id, "event_type": event_type,
            "number": number, "source_project": source_project, "created_at": created_at}


def record_practice_attempt(
    learner_id: str, question_number: int, selected_number: int,
    source_project: str = PROJECT_ID,
) -> dict[str, Any]:
    if not 1 <= question_number <= 100 or not 1 <= selected_number <= 100:
        raise ValueError("question_number and selected_number must be between 1 and 100")
    created_at = utc_now()
    is_correct = question_number == selected_number
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO practice_attempts
               (learner_id, question_number, selected_number, is_correct, source_project, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (learner_id, question_number, selected_number, int(is_correct), source_project, created_at),
        )
        attempt_id = cursor.lastrowid
    record_learning_event(learner_id, "practice_answer", question_number,
                          {"selected_number": selected_number, "is_correct": is_correct}, source_project)
    return {"attempt_id": attempt_id, "learner_id": learner_id, "question_number": question_number,
            "selected_number": selected_number, "is_correct": is_correct,
            "created_at": created_at, "source_project": source_project}


def _make_options(target: int) -> list[int]:
    distractors = set()
    while len(distractors) < 3:
        candidate = random.randint(1, 100)
        if candidate != target:
            distractors.add(candidate)
    options = list(distractors) + [target]
    random.shuffle(options)
    return options


def create_quiz(learner_id: str, num_questions: int = 10,
                source_project: str = PROJECT_ID) -> dict[str, Any]:
    if not 1 <= num_questions <= 20:
        raise ValueError("num_questions must be between 1 and 20")
    quiz_id = str(uuid.uuid4())
    started_at = utc_now()
    targets = random.sample(range(1, 101), k=num_questions)
    safe_questions: list[dict[str, Any]] = []
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO quiz_sessions
               (quiz_id, learner_id, source_project, started_at, total_questions)
               VALUES (?, ?, ?, ?, ?)""",
            (quiz_id, learner_id, source_project, started_at, num_questions),
        )
        for position, target in enumerate(targets, start=1):
            options = _make_options(target)
            conn.execute(
                """INSERT INTO quiz_questions (quiz_id, position, target_number, options_json)
                   VALUES (?, ?, ?, ?)""",
                (quiz_id, position, target, json.dumps(options)),
            )
            details = number_details(target)
            safe_questions.append({
                "position": position,
                "kanji": details["kanji"],
                "hiragana": details["hiragana"],
                "romaji": details["romaji"],
                "options": options,
            })
    record_learning_event(learner_id, "quiz_started", payload={"quiz_id": quiz_id, "total_questions": num_questions},
                          source_project=source_project)
    return {"quiz_id": quiz_id, "learner_id": learner_id, "started_at": started_at,
            "total_questions": num_questions, "questions": safe_questions}


def submit_quiz(quiz_id: str, answers: list[dict[str, Any]]) -> dict[str, Any]:
    submitted_at = utc_now()
    with get_connection() as conn:
        session = conn.execute("SELECT * FROM quiz_sessions WHERE quiz_id = ?", (quiz_id,)).fetchone()
        if session is None:
            raise KeyError("Quiz not found")
        if session["submitted_at"] is not None:
            raise ValueError("This quiz has already been submitted")
        questions = conn.execute(
            "SELECT * FROM quiz_questions WHERE quiz_id = ? ORDER BY position", (quiz_id,)
        ).fetchall()
        question_by_position = {row["position"]: row for row in questions}
        answer_by_position: dict[int, int | None] = {}
        for item in answers:
            position = int(item["position"])
            if position not in question_by_position:
                raise ValueError(f"Invalid question position: {position}")
            if position in answer_by_position:
                raise ValueError(f"Duplicate answer for question {position}")
            selected = item.get("selected_number")
            if selected is not None:
                selected = int(selected)
                allowed_options = json.loads(question_by_position[position]["options_json"])
                if selected not in allowed_options:
                    raise ValueError(f"Answer {selected} is not an option for question {position}")
            answer_by_position[position] = selected

        correct_count = 0
        answer_details = []
        for question in questions:
            position = question["position"]
            selected = answer_by_position.get(position)
            correct = selected == question["target_number"]
            correct_count += int(correct)
            conn.execute(
                """INSERT INTO quiz_answers
                   (quiz_id, question_id, selected_number, is_correct, answered_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (quiz_id, question["id"], selected, int(correct), submitted_at),
            )
            answer_details.append({
                "position": position,
                "target_number": question["target_number"],
                "selected_number": selected,
                "is_correct": correct,
                "correct_details": number_details(question["target_number"]),
            })
        total = len(questions)
        percentage = round((correct_count / total) * 100, 2) if total else 0.0
        grade = grade_for_percentage(percentage)
        conn.execute(
            """UPDATE quiz_sessions SET submitted_at = ?, score = ?, score_pct = ?, grade = ?
               WHERE quiz_id = ?""",
            (submitted_at, correct_count, percentage, grade, quiz_id),
        )
        result = {
            "quiz_id": quiz_id,
            "learner_id": session["learner_id"],
            "score": correct_count,
            "total_questions": total,
            "percentage": percentage,
            "grade": grade,
            "submitted_at": submitted_at,
            "answers": answer_details,
            "source_project": session["source_project"],
        }
    record_learning_event(result["learner_id"], "quiz_submitted", payload={
        "quiz_id": quiz_id, "score": result["score"], "total_questions": result["total_questions"],
        "percentage": result["percentage"], "grade": result["grade"],
    }, source_project=result["source_project"])
    return result


def get_progress(learner_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        practice = conn.execute(
            """SELECT COUNT(*) AS attempts, COALESCE(SUM(is_correct), 0) AS correct
               FROM practice_attempts WHERE learner_id = ?""", (learner_id,)
        ).fetchone()
        quizzes = conn.execute(
            """SELECT COUNT(*) AS quiz_count, COALESCE(AVG(score_pct), 0) AS avg_score,
                      COALESCE(MAX(score_pct), 0) AS best_score
               FROM quiz_sessions WHERE learner_id = ? AND submitted_at IS NOT NULL""", (learner_id,)
        ).fetchone()
        recent_quizzes = conn.execute(
            """SELECT quiz_id, source_project, started_at, submitted_at, score,
                      total_questions, score_pct, grade
               FROM quiz_sessions WHERE learner_id = ? AND submitted_at IS NOT NULL
               ORDER BY submitted_at DESC LIMIT 10""", (learner_id,)
        ).fetchall()
        trend_rows = conn.execute(
            """SELECT submitted_at, score_pct FROM quiz_sessions
               WHERE learner_id = ? AND submitted_at IS NOT NULL
               ORDER BY submitted_at DESC LIMIT 20""", (learner_id,)
        ).fetchall()
        trend_rows = list(reversed(trend_rows))
        recent_practice = conn.execute(
            """SELECT id, question_number, selected_number, is_correct, source_project, created_at
               FROM practice_attempts WHERE learner_id = ? ORDER BY created_at DESC LIMIT 10""", (learner_id,)
        ).fetchall()
        recent_events = conn.execute(
            """SELECT id, event_type, number, payload_json, source_project, created_at
               FROM learning_events WHERE learner_id = ? ORDER BY created_at DESC LIMIT 10""", (learner_id,)
        ).fetchall()

    attempt_count = int(practice["attempts"])
    correct_practice = int(practice["correct"])
    return {
        "learner_id": learner_id,
        "practice_attempts": attempt_count,
        "practice_correct": correct_practice,
        "practice_accuracy": round(correct_practice * 100 / attempt_count, 2) if attempt_count else 0.0,
        "quizzes_taken": int(quizzes["quiz_count"]),
        "average_quiz_score": round(float(quizzes["avg_score"]), 2),
        "best_quiz_score": round(float(quizzes["best_score"]), 2),
        "recent_quizzes": [dict(row) for row in recent_quizzes],
        "quiz_score_trend": [
            {"date": row["submitted_at"], "score_pct": row["score_pct"]} for row in trend_rows
        ],
        "recent_practice": [dict(row) for row in recent_practice],
        "recent_learning_events": [
            {**dict(row), "payload": json.loads(row["payload_json"])} for row in recent_events
        ],
    }


def get_quiz_result(quiz_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        session = conn.execute("SELECT * FROM quiz_sessions WHERE quiz_id = ?", (quiz_id,)).fetchone()
        if session is None:
            return None
        answers = conn.execute(
            """SELECT q.position, q.target_number, a.selected_number, a.is_correct
               FROM quiz_questions q LEFT JOIN quiz_answers a
               ON a.question_id = q.id AND a.quiz_id = q.quiz_id
               WHERE q.quiz_id = ? ORDER BY q.position""", (quiz_id,)
        ).fetchall()
    return {**dict(session), "answers": [dict(row) for row in answers]}
