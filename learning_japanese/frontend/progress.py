"""Analytics page powered by saved SQLite records."""
from __future__ import annotations

from nicegui import ui

from learning_japanese.config import DEFAULT_LEARNER_ID
from learning_japanese.frontend.theme import render_header, render_footer
from learning_japanese.services.learning_service import get_progress


def render() -> None:
    render_header(
        "progress",
        "Your Learning Progress",
        "See how your Japanese practice and completed quizzes are improving over time.",
    )

    progress = get_progress(DEFAULT_LEARNER_ID)

    with ui.column().classes(
        "w-full max-w-6xl mx-auto px-4 md:px-6 pb-10 gap-5"
    ):
        # ========================================================
        # SUMMARY
        # ========================================================
        with ui.grid(columns=4).classes("w-full gap-3 progress-metrics"):
            metrics = [
                (str(progress["practice_attempts"]), "Practice attempts"),
                (f"{progress['practice_accuracy']:.0f}%", "Practice accuracy"),
                (str(progress["quizzes_taken"]), "Quizzes completed"),
                (f"{progress['best_quiz_score']:.0f}%", "Best quiz score"),
            ]
            for value, label in metrics:
                with ui.card().classes("jp-metric progress-metric-card"):
                    ui.label(value).classes("jp-metric-value")
                    ui.label(label).classes("jp-caption")

        # ========================================================
        # CHARTS
        # ========================================================
        with ui.grid(columns=2).classes("w-full gap-4 progress-charts"):
            with ui.card().classes("jp-card w-full p-5"):
                ui.label("Quiz score trend").classes(
                    "text-lg font-extrabold"
                )
                ui.label(
                    "Your latest completed quizzes, oldest → newest."
                ).classes("text-xs text-gray-500")

                trend = progress["quiz_score_trend"]
                if trend:
                    labels = [f"Q{i}" for i in range(1, len(trend) + 1)]
                    scores = [float(item["score_pct"] or 0) for item in trend]
                    ui.echart({
                        "tooltip": {
                            "trigger": "axis",
                            "formatter": "Quiz {b}: {c}%",
                        },
                        "grid": {
                            "left": 42,
                            "right": 20,
                            "top": 25,
                            "bottom": 35,
                        },
                        "xAxis": {
                            "type": "category",
                            "data": labels,
                            "boundaryGap": False,
                        },
                        "yAxis": {
                            "type": "value",
                            "min": 0,
                            "max": 100,
                            "axisLabel": {"formatter": "{value}%"},
                        },
                        "series": [{
                            "type": "line",
                            "data": scores,
                            "smooth": True,
                            "areaStyle": {"opacity": 0.10},
                            "lineStyle": {"width": 3},
                            "symbolSize": 8,
                        }],
                    }).classes("w-full h-64")
                else:
                    ui.label(
                        "Complete your first quiz to start the score trend."
                    ).classes("text-sm text-gray-500 py-10")

            with ui.card().classes("jp-card w-full p-5"):
                ui.label("Practice accuracy").classes(
                    "text-lg font-extrabold"
                )
                ui.label(
                    "Correct versus incorrect practice attempts."
                ).classes("text-xs text-gray-500")

                attempts = int(progress["practice_attempts"])
                correct = int(progress["practice_correct"])
                incorrect = max(0, attempts - correct)

                if attempts:
                    ui.echart({
                        "tooltip": {"trigger": "item"},
                        "legend": {"bottom": 0},
                        "series": [{
                            "type": "pie",
                            "radius": ["42%", "72%"],
                            "avoidLabelOverlap": True,
                            "data": [
                                {"name": "Correct", "value": correct},
                                {"name": "Incorrect", "value": incorrect},
                            ],
                        }],
                    }).classes("w-full h-64")
                else:
                    ui.label(
                        "Answer practice questions to populate this chart."
                    ).classes("text-sm text-gray-500 py-10")

        # ========================================================
        # QUIZ STATS
        # ========================================================
        with ui.grid(columns=2).classes("w-full gap-4"):
            with ui.card().classes("jp-card w-full p-5"):
                ui.label("Quiz performance").classes(
                    "text-lg font-extrabold"
                )
                ui.label(
                    "Your overall performance across completed quizzes."
                ).classes("text-xs text-gray-500")

                with ui.grid(columns=2).classes("w-full gap-3 mt-4"):
                    with ui.card().classes("progress-stat-card p-4"):
                        ui.label("Average score").classes("text-xs text-gray-500")
                        ui.label(
                            f"{progress['average_quiz_score']:.0f}%"
                        ).classes("text-2xl font-extrabold text-indigo-700 mt-1")
                    with ui.card().classes("progress-stat-card p-4"):
                        ui.label("Best score").classes("text-xs text-gray-500")
                        ui.label(
                            f"{progress['best_quiz_score']:.0f}%"
                        ).classes("text-2xl font-extrabold text-indigo-700 mt-1")

            with ui.card().classes("jp-soft w-full p-5"):
                ui.label("What to do next").classes(
                    "text-lg font-extrabold"
                )
                accuracy = float(progress["practice_accuracy"])
                best = float(progress["best_quiz_score"])
                if not progress["quizzes_taken"]:
                    next_step = "Start a 10-question quiz and establish your first baseline."
                elif best >= 90:
                    next_step = "Excellent. Try 15–20 questions or a shorter timer."
                elif best >= 75:
                    next_step = "Review your missed numbers, then repeat the quiz."
                else:
                    next_step = "Use Learn + Practice mode before increasing quiz difficulty."
                ui.label(next_step).classes(
                    "text-sm text-slate-600 leading-relaxed mt-2"
                )
                ui.label(
                    f"Practice accuracy currently: {accuracy:.0f}%"
                ).classes("text-xs text-slate-400 mt-4")

        # ========================================================
        # RECENT QUIZZES
        # ========================================================
        with ui.card().classes("jp-card w-full p-5"):
            with ui.row().classes(
                "w-full items-center justify-between gap-3 flex-wrap"
            ):
                ui.label("Recent quiz results").classes(
                    "text-lg font-extrabold"
                )
                ui.label(
                    "Latest 10 completed quizzes"
                ).classes("text-xs text-gray-400")

            if progress["recent_quizzes"]:
                rows = []
                for index, row in enumerate(progress["recent_quizzes"], start=1):
                    rows.append({
                        "attempt": f"#{index}",
                        "date": (row["submitted_at"] or "")[:19].replace("T", " "),
                        "score": f"{row['score']} / {row['total_questions']}",
                        "percentage": f"{float(row['score_pct'] or 0):.0f}%",
                        "grade": row["grade"] or "—",
                        "quiz_id": row["quiz_id"],
                    })

                ui.table(
                    columns=[
                        {"name": "attempt", "label": "Quiz", "field": "attempt", "align": "left"},
                        {"name": "date", "label": "Completed", "field": "date", "align": "left"},
                        {"name": "score", "label": "Score", "field": "score", "align": "left"},
                        {"name": "percentage", "label": "Accuracy", "field": "percentage", "align": "left"},
                        {"name": "grade", "label": "Performance", "field": "grade", "align": "left"},
                    ],
                    rows=rows,
                    row_key="quiz_id",
                ).classes("w-full")
            else:
                ui.label(
                    "No completed quizzes yet. Your results will appear here after your first submission."
                ).classes("text-sm text-gray-500 py-4")

        # ========================================================
        # PRACTICE ACTIVITY
        # ========================================================
        with ui.card().classes("jp-card w-full p-5"):
            ui.label("Recent practice activity").classes(
                "text-lg font-extrabold"
            )
            ui.label(
                "Your latest number-recognition attempts."
            ).classes("text-xs text-gray-500")

            if progress["recent_practice"]:
                with ui.column().classes("w-full gap-2 mt-4"):
                    for item in progress["recent_practice"]:
                        correct = bool(item["is_correct"])
                        selected = item["selected_number"]
                        ui.label(
                            f"{'✓' if correct else '✗'}  "
                            f"{item['question_number']} → "
                            f"{selected}  •  "
                            f"{(item['created_at'] or '')[:19].replace('T', ' ')}"
                        ).classes(
                            "text-sm " + (
                                "text-green-700" if correct else "text-red-600"
                            )
                        )
            else:
                ui.label(
                    "No practice attempts yet."
                ).classes("text-sm text-gray-500 py-4")

        with ui.card().classes("jp-soft w-full p-4"):
            ui.label("How progress is calculated").classes("font-extrabold")
            ui.label(
                "Practice accuracy = correct practice answers ÷ all practice attempts. "
                "Quiz accuracy = correct answers ÷ questions in that quiz. "
                "Only submitted quizzes are included in quiz statistics."
            ).classes("text-sm text-gray-600 leading-relaxed")

    ui.add_head_html(
        """
        <style>
            .progress-metric-card {
                min-height: 112px;
            }
            .progress-stat-card {
                border-radius: 16px;
                border: 1px solid #e5e7eb;
                background: #fff;
            }
            @media (max-width: 900px) {
                .progress-metrics {
                    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                }
                .progress-charts {
                    grid-template-columns: 1fr !important;
                }
            }
            @media (max-width: 600px) {
                .progress-metrics {
                    grid-template-columns: 1fr !important;
                }
            }
        </style>
        """
    )

    render_footer()
