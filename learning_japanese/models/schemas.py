"""Pydantic request schemas for stable, documented API contracts."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from learning_japanese.config import DEFAULT_LEARNER_ID, PROJECT_ID


class PracticeAttemptIn(BaseModel):
    learner_id: str = Field(default=DEFAULT_LEARNER_ID, min_length=1, max_length=100)
    question_number: int = Field(ge=1, le=100)
    selected_number: int = Field(ge=1, le=100)
    source_project: str = Field(default=PROJECT_ID, min_length=1, max_length=100)


class QuizStartIn(BaseModel):
    learner_id: str = Field(default=DEFAULT_LEARNER_ID, min_length=1, max_length=100)
    num_questions: int = Field(default=10, ge=1, le=20)
    source_project: str = Field(default=PROJECT_ID, min_length=1, max_length=100)


class QuizAnswerIn(BaseModel):
    position: int = Field(ge=1, le=20)
    selected_number: int | None = Field(default=None, ge=1, le=100)


class QuizSubmitIn(BaseModel):
    answers: list[QuizAnswerIn] = Field(default_factory=list, max_length=20)


class LearningEventIn(BaseModel):
    learner_id: str = Field(default=DEFAULT_LEARNER_ID, min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    number: int | None = Field(default=None, ge=1, le=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    source_project: str = Field(default=PROJECT_ID, min_length=1, max_length=100)


class PartnerEventIn(BaseModel):
    learner_id: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    source_project: str = Field(min_length=1, max_length=100)
