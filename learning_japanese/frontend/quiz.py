"""Interactive Japanese Numbers Quiz.

Features:
- Choose number of questions
- Choose time per question
- One question at a time
- Japanese text on the left
- Radio-button answers on the right
- No answer revelation during the quiz
- Timer per question
- Automatic timeout handling
- Final score shown only after completion
- Complete answer key shown only after completion
- Performance insights
- Quiz saved through the shared SQLite service
- Robust Japanese browser speech synthesis
"""

from __future__ import annotations

import json

from nicegui import ui

from learning_japanese.config import DEFAULT_LEARNER_ID
from learning_japanese.frontend.theme import (
    render_header,
    render_footer,
)
from learning_japanese.services.learning_service import (
    create_quiz,
    submit_quiz,
)


# ============================================================
# QUIZ CONFIGURATION
# ============================================================

DEFAULT_QUIZ_SIZE = 10
DEFAULT_TIME_LIMIT = 30

QUESTION_CHOICES = [5, 10, 15, 20]
TIME_CHOICES = [15, 30, 45, 60]


# ============================================================
# PAGE
# ============================================================

def render() -> None:

    render_header(
        "quiz",
        "Japanese Numbers Quiz",
        "Test your Japanese number recognition under time pressure.",
    )

    # ========================================================
    # STATE
    # ========================================================

    state: dict = {
        "started": False,
        "finished": False,

        "quiz": None,
        "result": None,

        "question_index": 0,

        "quiz_size": DEFAULT_QUIZ_SIZE,
        "time_limit": DEFAULT_TIME_LIMIT,
        "time_left": DEFAULT_TIME_LIMIT,

        "selected": None,
        "answered": False,

        "answers": {},

        "error": None,
    }

    # ========================================================
    # MAIN PAGE
    # ========================================================

    with ui.column().classes(
        "w-full max-w-7xl mx-auto px-4 md:px-8 pb-12 gap-6"
    ):

        # ====================================================
        # TOP HEADER
        # ====================================================

        with ui.row().classes(
            "w-full items-center justify-between gap-4 flex-wrap"
        ):

            with ui.column().classes("gap-1"):

                ui.label(
                    "QUIZ MODE"
                ).classes(
                    "text-xs font-extrabold tracking-widest text-gray-400"
                )

                ui.label(
                    "Japanese Numbers"
                ).classes(
                    "text-2xl md:text-3xl font-extrabold text-slate-900"
                )

            with ui.row().classes(
                "items-center gap-4 flex-wrap"
            ):

                score_label = ui.label(
                    "⭐ Score: 0"
                ).classes(
                    "font-extrabold text-indigo-700"
                )

                timer_label = ui.label(
                    f"⏱️ {DEFAULT_TIME_LIMIT}s"
                ).classes(
                    "font-extrabold text-red-500 text-lg"
                )

        # ====================================================
        # PROGRESS
        # ====================================================

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            progress_text = ui.label(
                "Ready to begin"
            ).classes(
                "font-bold text-slate-600"
            )

            progress_percent = ui.label(
                "0%"
            ).classes(
                "font-bold text-indigo-700"
            )

        progress_bar = ui.linear_progress(
            value=0
        ).props(
            "color=primary"
        ).classes(
            "w-full"
        )

        # ====================================================
        # SETUP CARD
        # ====================================================

        setup_card = ui.card().classes(
            "quiz-shell w-full p-6 md:p-10"
        )

        with setup_card:

            with ui.column().classes(
                "w-full items-center text-center gap-5"
            ):

                ui.label(
                    "🎌 Japanese Numbers Quiz"
                ).classes(
                    "text-3xl md:text-4xl font-extrabold text-slate-900"
                )

                ui.label(
                    "Choose your challenge before you start."
                ).classes(
                    "text-base text-slate-500"
                )

                # ====================================================
                # SETTINGS
                # ====================================================

                with ui.row().classes(
                    "w-full justify-center gap-5 flex-wrap"
                ):

                    # --------------------------------------------
                    # NUMBER OF QUESTIONS
                    # --------------------------------------------

                    with ui.card().classes(
                        "setup-option-card p-5"
                    ):

                        ui.label(
                            "NUMBER OF QUESTIONS"
                        ).classes(
                            "text-xs font-extrabold "
                            "tracking-widest text-gray-400"
                        )

                        question_select = ui.select(
                            {
                                5: "5 Questions",
                                10: "10 Questions",
                                15: "15 Questions",
                                20: "20 Questions",
                            },
                            value=DEFAULT_QUIZ_SIZE,
                        ).props(
                            "outlined"
                        ).classes(
                            "w-64 mt-3"
                        )

                    # --------------------------------------------
                    # TIME PER QUESTION
                    # --------------------------------------------

                    with ui.card().classes(
                        "setup-option-card p-5"
                    ):

                        ui.label(
                            "TIME PER QUESTION"
                        ).classes(
                            "text-xs font-extrabold "
                            "tracking-widest text-gray-400"
                        )

                        time_select = ui.select(
                            {
                                15: "15 seconds",
                                30: "30 seconds",
                                45: "45 seconds",
                                60: "60 seconds",
                            },
                            value=DEFAULT_TIME_LIMIT,
                        ).props(
                            "outlined"
                        ).classes(
                            "w-64 mt-3"
                        )

                # --------------------------------------------
                # START BUTTON
                # --------------------------------------------

                ui.button(
                    "🚀 Start Quiz",
                    on_click=lambda: start_quiz(),
                ).props(
                    "unelevated no-caps"
                ).classes(
                    "quiz-primary rounded-xl px-10 py-3 "
                    "text-lg font-bold mt-2"
                )

                ui.label(
                    "Your correct answers, answer key and insights "
                    "are revealed only after the quiz."
                ).classes(
                    "text-sm text-slate-400 max-w-2xl"
                )

        # ====================================================
        # QUIZ CARD
        # ====================================================

        quiz_card = ui.card().classes(
            "quiz-shell w-full p-5 md:p-8"
        )

        quiz_card.set_visibility(False)

        with quiz_card:

            # ====================================================
            # QUESTION HEADER
            # ====================================================

            with ui.row().classes(
                "w-full items-center justify-between gap-3"
            ):

                with ui.column().classes("gap-1"):

                    question_status = ui.label(
                        "Question 1"
                    ).classes(
                        "text-xl font-extrabold text-slate-900"
                    )

                    status_label = ui.label(
                        "Not answered"
                    ).classes(
                        "text-sm font-semibold text-slate-400"
                    )

                timer_big = ui.label(
                    f"{DEFAULT_TIME_LIMIT}s"
                ).classes(
                    "quiz-timer text-2xl md:text-3xl font-extrabold"
                )

            ui.separator().classes("my-5")

            # ====================================================
            # TWO COLUMN QUIZ LAYOUT
            # ====================================================

            with ui.row().classes(
                "w-full items-stretch gap-6 quiz-layout"
            ):

                # ==================================================
                # LEFT — QUESTION
                # ==================================================

                with ui.card().classes(
                    "question-panel flex-1 p-6 md:p-8"
                ):

                    ui.label(
                        "WHAT NUMBER IS THIS?"
                    ).classes(
                        "text-xs font-extrabold "
                        "tracking-widest text-gray-400"
                    )

                    # Japanese reading
                    question_kana = ui.label(
                        "いち"
                    ).classes(
                        "jp-quiz-question"
                    )

                    # Kanji + Romaji
                    with ui.row().classes(
                        "items-center justify-center "
                        "gap-3 mt-4 flex-wrap"
                    ):

                        question_kanji = ui.label(
                            "一"
                        ).classes(
                            "jp-quiz-kanji"
                        )

                        question_romaji = ui.label(
                            "ichi"
                        ).classes(
                            "jp-quiz-romaji"
                        )

                    # ==================================================
                    # AUDIO
                    # ==================================================

                    with ui.row().classes(
                        "justify-center gap-2 mt-7"
                    ):

                        ui.button(
                            "🔊 Listen",
                            on_click=lambda: speak_question(),
                        ).props(
                            "unelevated no-caps"
                        ).classes(
                            "quiz-secondary rounded-xl "
                            "px-6 py-3 font-bold"
                        )

                        ui.button(
                            "■ Stop",
                            on_click=lambda: stop_speech(),
                        ).props(
                            "flat no-caps"
                        ).classes(
                            "text-gray-500"
                        )

                    voice_status = ui.label(
                        ""
                    ).classes(
                        "text-xs text-gray-400 "
                        "text-center mt-2 w-full"
                    )

                    ui.label(
                        "Identify the number before "
                        "the timer runs out."
                    ).classes(
                        "text-sm text-slate-400 "
                        "text-center mt-7"
                    )

                # ==================================================
                # RIGHT — ANSWERS
                # ==================================================

                with ui.card().classes(
                    "answer-panel flex-1 p-6 md:p-8"
                ):

                    ui.label(
                        "SELECT YOUR ANSWER"
                    ).classes(
                        "text-xs font-extrabold "
                        "tracking-widest text-gray-400"
                    )

                    ui.label(
                        "Choose one option"
                    ).classes(
                        "text-xl font-extrabold "
                        "text-slate-900 mt-2"
                    )

                    ui.label(
                        "Select the number represented "
                        "by the Japanese reading."
                    ).classes(
                        "text-sm text-slate-500 mt-1"
                    )

                    # ==================================================
                    # RADIO BUTTONS
                    # ==================================================
                    #
                    # ONE radio group containing ALL options.
                    #

                    answer_radio = ui.radio(
                        [],
                        value=None,
                        on_change=lambda event: answer_question(
                            event.value
                        ),
                    ).props(
                        "dense"
                    ).classes(
                        "quiz-radio w-full mt-5"
                    )

                    feedback_label = ui.label(
                        ""
                    ).classes(
                        "text-center font-bold mt-5 w-full"
                    )

                    # ==================================================
                    # NEXT BUTTON
                    # ==================================================

                    with ui.row().classes(
                        "w-full justify-end mt-5"
                    ):

                        next_button = ui.button(
                            "Next Question →",
                            on_click=lambda: next_question(),
                        ).props(
                            "unelevated no-caps"
                        ).classes(
                            "quiz-primary rounded-xl "
                            "px-7 py-3 font-bold"
                        )

                        next_button.set_visibility(False)

        # ====================================================
        # RESULTS CARD
        # ====================================================

        results_card = ui.card().classes(
            "quiz-shell w-full p-6 md:p-10"
        )

        results_card.set_visibility(False)

        with results_card:

            # ==================================================
            # RESULT HEADER
            # ==================================================

            ui.label(
                "🎉 Quiz Complete!"
            ).classes(
                "text-3xl md:text-4xl "
                "font-extrabold text-slate-900 "
                "text-center w-full"
            )

            results_summary = ui.label(
                ""
            ).classes(
                "text-center text-lg text-slate-500 "
                "mt-2 w-full"
            )

            # ==================================================
            # SCORE SUMMARY
            # ==================================================

            with ui.grid(columns=3).classes(
                "w-full gap-4 mt-7"
            ):

                # SCORE

                with ui.card().classes(
                    "result-card p-5 text-center"
                ):

                    ui.label(
                        "SCORE"
                    ).classes(
                        "result-caption"
                    )

                    result_score = ui.label(
                        "0 / 10"
                    ).classes(
                        "result-value"
                    )

                # ACCURACY

                with ui.card().classes(
                    "result-card p-5 text-center"
                ):

                    ui.label(
                        "ACCURACY"
                    ).classes(
                        "result-caption"
                    )

                    result_accuracy = ui.label(
                        "0%"
                    ).classes(
                        "result-value"
                    )

                # AVG TIME

                with ui.card().classes(
                    "result-card p-5 text-center"
                ):

                    ui.label(
                        "AVG. TIME"
                    ).classes(
                        "result-caption"
                    )

                    result_average = ui.label(
                        "—"
                    ).classes(
                        "result-value"
                    )

            result_message = ui.label(
                ""
            ).classes(
                "text-center text-lg "
                "font-bold text-indigo-700 "
                "mt-6 w-full"
            )

            # ==================================================
            # ANSWER KEY
            # ==================================================

            ui.separator().classes(
                "my-8"
            )

            ui.label(
                "📖 Answer Key"
            ).classes(
                "text-2xl font-extrabold text-slate-900"
            )

            ui.label(
                "Review every question after completing the quiz."
            ).classes(
                "text-sm text-slate-500 mt-1"
            )

            # IMPORTANT:
            # All dynamic answer cards will be created
            # INSIDE this container.
            answer_key_container = ui.column().classes(
                "w-full gap-3 mt-5"
            )

            # ==================================================
            # INSIGHTS
            # ==================================================

            insights_container = ui.column().classes(
                "w-full gap-3 mt-6"
            )

            # ==================================================
            # NEW QUIZ
            # ==================================================

            with ui.row().classes(
                "w-full justify-center mt-7"
            ):

                ui.button(
                    "🔄 New Quiz",
                    on_click=lambda: reset_quiz(),
                ).props(
                    "unelevated no-caps"
                ).classes(
                    "quiz-primary rounded-xl "
                    "px-8 py-3 font-bold"
                )

    # ========================================================
    # STYLING
    # ========================================================

    ui.add_head_html(
        """
        <style>

        /* ==================================================
           MAIN QUIZ
           ================================================== */

        .quiz-shell {
            border-radius: 24px;
            border: 1px solid #e5e7eb;
            box-shadow:
                0 10px 35px rgba(15, 23, 42, 0.07);
            background: rgba(255, 255, 255, 0.98);
        }

        .setup-option-card {
            min-width: 280px;
            border-radius: 18px;
            border: 1px solid #e5e7eb;
            box-shadow: none;
            background: #ffffff;
        }

        .question-panel,
        .answer-panel {
            border-radius: 20px;
            border: 1px solid #e5e7eb;
            box-shadow: none;
            background: #ffffff;
        }

        /* ==================================================
           JAPANESE QUESTION
           ================================================== */

        .jp-quiz-question {
            width: 100%;

            white-space: nowrap !important;

            overflow-x: auto;
            overflow-y: hidden;

            text-align: center;

            font-size: clamp(
                2.8rem,
                6vw,
                5.5rem
            );

            line-height: 1.15;

            font-weight: 900;

            color: #111827;

            letter-spacing: 0.04em;

            padding: 50px 5px 25px;

            scrollbar-width: thin;
        }

        .jp-quiz-kanji {
            font-size: 2rem;
            font-weight: 800;
            color: #64748b;
        }

        .jp-quiz-romaji {
            font-size: 1.2rem;
            font-weight: 700;
            color: #64748b;
        }

        /* ==================================================
           BUTTONS
           ================================================== */

        .quiz-primary {
            background: #4f8fd1 !important;
            color: white !important;
        }

        .quiz-primary:hover {
            background: #3f80c4 !important;
        }

        .quiz-secondary {
            background: #eef5ff !important;
            color: #2563eb !important;
        }

        .quiz-secondary:hover {
            background: #e0edff !important;
        }

        /* ==================================================
           RADIO ANSWERS
           ================================================== */

        .quiz-radio {
            width: 100%;
        }

        .quiz-radio .q-radio {
            width: 100%;

            min-height: 68px;

            margin-bottom: 12px;

            padding: 16px 18px;

            border: 2px solid #e2e8f0;

            border-radius: 16px;

            background: #f8fafc;

            transition:
                border-color 0.15s ease,
                background 0.15s ease,
                transform 0.15s ease;
        }

        .quiz-radio .q-radio:hover {
            border-color: #93c5fd;
            background: #eff6ff;
            transform: translateY(-1px);
        }

        .quiz-radio .q-radio__label {
            font-size: 1.2rem;
            font-weight: 800;
            color: #1e293b;
            padding-left: 8px;
        }

        .quiz-radio .q-radio__inner {
            font-size: 30px;
        }

        /* ==================================================
           TIMER
           ================================================== */

        .quiz-timer {
            min-width: 90px;
            text-align: center;
            color: #ef4444;
        }

        /* ==================================================
           RESULTS
           ================================================== */

        .result-card {
            border-radius: 18px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
        }

        .result-caption {
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            color: #94a3b8;
        }

        .result-value {
            font-size: 2rem;
            font-weight: 900;
            color: #312e81;
            margin-top: 8px;
        }

        .answer-key-item {
            border-radius: 18px;
            border: 1px solid #e5e7eb;
            background: #ffffff;
        }

        /* ==================================================
           MOBILE
           ================================================== */

        @media (max-width: 800px) {

            .quiz-layout {
                flex-direction: column !important;
            }

            .question-panel,
            .answer-panel {
                width: 100% !important;
            }

            .jp-quiz-question {
                font-size: 3rem;
                padding-top: 25px;
            }
        }

        </style>
        """
    )

    # ========================================================
    # QUIZ FUNCTIONS
    # ========================================================

    def get_current_question() -> dict:
        """Return the currently active question."""

        return state["quiz"]["questions"][
            state["question_index"]
        ]

    # ========================================================
    # AUDIO
    # ========================================================

    def stop_speech() -> None:
        """Stop all browser speech immediately."""

        ui.run_javascript(
            """
            (() => {
                try {
                    if (window.speechSynthesis) {
                        window.speechSynthesis.cancel();
                    }
                } catch (error) {
                    console.error(
                        "Speech stop error:",
                        error
                    );
                }
            })();
            """
        )

        voice_status.set_text("")

    def speak_question() -> None:
        """
        Speak the current Japanese number.

        Uses the browser's Japanese voice.
        Voices can load asynchronously in Chrome, so
        the code waits/retries before speaking.
        """

        if not state["started"]:
            return

        if state["finished"]:
            return

        question = get_current_question()

        text = str(
            question.get(
                "hiragana",
                ""
            )
        ).replace(
            " ",
            ""
        ).strip()

        if not text:
            voice_status.set_text(
                "⚠️ No Japanese pronunciation available."
            )
            return

        text_json = json.dumps(
            text,
            ensure_ascii=False
        )

        ui.run_javascript(
            f"""
            (() => {{

                const text = {text_json};

                if (!window.speechSynthesis) {{

                    console.error(
                        "Speech synthesis is not supported."
                    );

                    return;
                }}

                const synth =
                    window.speechSynthesis;

                // Stop anything already playing.
                synth.cancel();

                function findJapaneseVoice() {{

                    const voices =
                        synth.getVoices();

                    if (!voices || voices.length === 0) {{
                        return null;
                    }}

                    // First priority:
                    // exact Japanese language.
                    let voice =
                        voices.find(
                            v =>
                                v.lang &&
                                v.lang.toLowerCase() === "ja-jp"
                        );

                    if (voice) {{
                        return voice;
                    }}

                    // Second priority:
                    // any Japanese language.
                    voice =
                        voices.find(
                            v =>
                                v.lang &&
                                v.lang.toLowerCase().startsWith("ja")
                        );

                    if (voice) {{
                        return voice;
                    }}

                    // Third priority:
                    // Japanese in voice name.
                    voice =
                        voices.find(
                            v =>
                                v.name &&
                                (
                                    v.name.toLowerCase().includes("japanese")
                                    ||
                                    v.name.toLowerCase().includes("japan")
                                )
                        );

                    return voice || null;
                }}

                function speakNow() {{

                    const japaneseVoice =
                        findJapaneseVoice();

                    const utterance =
                        new SpeechSynthesisUtterance(text);

                    utterance.lang = "ja-JP";

                    if (japaneseVoice) {{
                        utterance.voice =
                            japaneseVoice;
                    }}

                    // Slightly slower for learning.
                    utterance.rate = 0.78;
                    utterance.pitch = 1.0;
                    utterance.volume = 1.0;

                    utterance.onstart = () => {{

                        console.log(
                            "Japanese speech started:",
                            japaneseVoice
                                ? japaneseVoice.name
                                : "browser default"
                        );
                    }};

                    utterance.onend = () => {{

                        console.log(
                            "Japanese speech finished."
                        );
                    }};

                    utterance.onerror = (event) => {{

                        console.error(
                            "Japanese speech error:",
                            event.error
                        );
                    }};

                    synth.speak(
                        utterance
                    );

                    /*
                     * Chrome occasionally pauses
                     * speechSynthesis unexpectedly.
                     */
                    setTimeout(
                        () => {{

                            try {{

                                if (synth.speaking && synth.paused) {{
                                    synth.resume();
                                }}

                            }} catch (error) {{

                                console.error(
                                    "Speech resume error:",
                                    error
                                );
                            }}

                        }},
                        250
                    );
                }}

                function waitForVoices(
                    attempt = 0
                ) {{

                    const voices =
                        synth.getVoices();

                    if (voices.length > 0) {{

                        speakNow();
                        return;
                    }}

                    if (attempt >= 10) {{

                        // Speak anyway.
                        speakNow();
                        return;
                    }}

                    setTimeout(
                        () => {{
                            waitForVoices(
                                attempt + 1
                            );
                        }},
                        150
                    );
                }}

                /*
                 * Trigger voice loading.
                 */
                synth.getVoices();

                waitForVoices();

            }})();
            """
        )

        voice_status.set_text(
            "🔊 Japanese pronunciation"
        )

    # ========================================================
    # START QUIZ
    # ========================================================

    def start_quiz() -> None:

        stop_speech()

        try:

            quiz_size = int(
                question_select.value
            )

            time_limit = int(
                time_select.value
            )

            if quiz_size not in QUESTION_CHOICES:
                quiz_size = DEFAULT_QUIZ_SIZE

            if time_limit not in TIME_CHOICES:
                time_limit = DEFAULT_TIME_LIMIT

            # ------------------------------------------------
            # CREATE QUIZ THROUGH SHARED SERVICE
            # ------------------------------------------------

            quiz = create_quiz(
                DEFAULT_LEARNER_ID,
                quiz_size,
            )

            # ------------------------------------------------
            # RESET STATE
            # ------------------------------------------------

            state.update(
                started=True,
                finished=False,
                quiz=quiz,
                result=None,
                error=None,

                question_index=0,

                quiz_size=quiz_size,
                time_limit=time_limit,
                time_left=time_limit,

                selected=None,
                answered=False,

                answers={},
            )

            # ------------------------------------------------
            # UPDATE UI
            # ------------------------------------------------

            score_label.set_text(
                "⭐ Score: 0"
            )

            timer_label.set_text(
                f"⏱️ {time_limit}s"
            )

            timer_big.set_text(
                f"{time_limit}s"
            )

            progress_text.set_text(
                f"Question 1 / {quiz_size}"
            )

            progress_percent.set_text(
                "0%"
            )

            progress_bar.value = 0

            setup_card.set_visibility(
                False
            )

            quiz_card.set_visibility(
                True
            )

            results_card.set_visibility(
                False
            )

            load_question()

        except Exception as exc:

            state["error"] = str(exc)

            ui.notify(
                f"Unable to start quiz: {exc}",
                type="negative",
            )

    # ========================================================
    # LOAD QUESTION
    # ========================================================

    def load_question() -> None:

        stop_speech()

        state["answered"] = False
        state["selected"] = None
        state["time_left"] = state["time_limit"]

        question = get_current_question()

        position = int(
            question["position"]
        )

        # ------------------------------------------------
        # HEADER
        # ------------------------------------------------

        question_status.set_text(
            f"Question {position}"
        )

        progress_text.set_text(
            f"Question {position} / "
            f"{state['quiz_size']}"
        )

        # Progress represents current question.
        percent = (
            (position - 1)
            / state["quiz_size"]
        )

        progress_bar.value = percent

        progress_percent.set_text(
            f"{int(percent * 100)}%"
        )

        status_label.set_text(
            "Not answered"
        )

        timer_label.set_text(
            f"⏱️ {state['time_left']}s"
        )

        timer_big.set_text(
            f"{state['time_left']}s"
        )

        # ------------------------------------------------
        # JAPANESE QUESTION
        # ------------------------------------------------

        hiragana = str(
            question.get(
                "hiragana",
                ""
            )
        ).replace(
            " ",
            ""
        )

        question_kana.set_text(
            hiragana
        )

        question_kanji.set_text(
            str(
                question.get(
                    "kanji",
                    ""
                )
            )
        )

        question_romaji.set_text(
            str(
                question.get(
                    "romaji",
                    ""
                )
            )
        )

        # ------------------------------------------------
        # RESET FEEDBACK
        # ------------------------------------------------

        feedback_label.set_text(
            ""
        )

        voice_status.set_text(
            ""
        )

        next_button.set_visibility(
            False
        )

        # ------------------------------------------------
        # LOAD RADIO OPTIONS
        # ------------------------------------------------

        options = question.get(
            "options",
            []
        )

        # Ensure integer values.
        clean_options = []

        for option in options:

            try:
                clean_options.append(
                    int(option)
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        # Remove duplicates while
        # preserving order.
        clean_options = list(
            dict.fromkeys(
                clean_options
            )
        )

        answer_radio.options = {
            option: str(option)
            for option in clean_options
        }

        answer_radio.value = None

        # Force NiceGUI/Quasar update.
        answer_radio.update()

    # ========================================================
    # ANSWER
    # ========================================================

    def answer_question(selected) -> None:

        if state["finished"]:
            return

        if state["answered"]:
            return

        if selected is None:
            return

        try:
            selected = int(selected)
        except (
            TypeError,
            ValueError,
        ):
            return

        question = get_current_question()

        position = int(
            question["position"]
        )

        # ------------------------------------------------
        # SAVE ANSWER LOCALLY
        # ------------------------------------------------

        state["selected"] = selected

        state["answered"] = True

        state["answers"][position] = selected

        # ------------------------------------------------
        # UI
        # ------------------------------------------------

        status_label.set_text(
            "Answer selected"
        )

        feedback_label.set_text(
            "✓ Answer saved — continue to the next question."
        )

        feedback_label.classes(
            "text-indigo-600"
        )

        next_button.set_visibility(
            True
        )

    # ========================================================
    # TIMEOUT
    # ========================================================

    def timeout_question() -> None:

        if state["finished"]:
            return

        if state["answered"]:
            return

        question = get_current_question()

        position = int(
            question["position"]
        )

        state["answered"] = True

        state["selected"] = None

        # None means unanswered.
        state["answers"][position] = None

        status_label.set_text(
            "Time expired"
        )

        feedback_label.set_text(
            "⏰ Time's up — this question will receive 0 marks."
        )

        feedback_label.classes(
            "text-red-600"
        )

        answer_radio.value = None
        answer_radio.update()

        next_button.set_visibility(
            True
        )

    # ========================================================
    # NEXT QUESTION
    # ========================================================

    def next_question() -> None:

        if state["finished"]:
            return

        if not state["answered"]:
            return

        # ------------------------------------------------
        # LAST QUESTION
        # ------------------------------------------------

        if (
            state["question_index"]
            >= state["quiz_size"] - 1
        ):

            finish_quiz()

            return

        # ------------------------------------------------
        # NEXT
        # ------------------------------------------------

        state["question_index"] += 1

        load_question()

    # ========================================================
    # FINISH QUIZ
    # ========================================================

    def finish_quiz() -> None:

        if not state["quiz"]:
            return

        if state["finished"]:
            return

        stop_speech()

        # ------------------------------------------------
        # BUILD SUBMISSION PAYLOAD
        # ------------------------------------------------

        payload = []

        for question in state["quiz"]["questions"]:

            position = int(
                question["position"]
            )

            payload.append(
                {
                    "position": position,
                    "selected_number":
                        state["answers"].get(
                            position
                        ),
                }
            )

        # ------------------------------------------------
        # SUBMIT
        # ------------------------------------------------

        try:

            result = submit_quiz(
                state["quiz"]["quiz_id"],
                payload,
            )

            state["result"] = result

            state["finished"] = True

            state["started"] = False

            state["error"] = None

            show_results()

        except Exception as exc:

            state["error"] = str(exc)

            ui.notify(
                f"Unable to submit quiz: {exc}",
                type="negative",
            )

    # ========================================================
    # RESULTS
    # ========================================================

    def show_results() -> None:

        result = state.get(
            "result"
        )

        if not result:
            return

        # ------------------------------------------------
        # HIDE QUIZ
        # ------------------------------------------------

        quiz_card.set_visibility(
            False
        )

        setup_card.set_visibility(
            False
        )

        # ------------------------------------------------
        # SHOW RESULTS
        # ------------------------------------------------

        results_card.set_visibility(
            True
        )

        percentage = float(
            result.get(
                "percentage",
                0
            )
        )

        score = int(
            result.get(
                "score",
                0
            )
        )

        total_questions = int(
            result.get(
                "total_questions",
                state["quiz_size"]
            )
        )

        # ------------------------------------------------
        # RESULT HEADER
        # ------------------------------------------------

        result_score.set_text(
            f"{score} / {total_questions}"
        )

        result_accuracy.set_text(
            f"{percentage:.0f}%"
        )

        result_average.set_text(
            "—"
        )

        results_summary.set_text(
            f"You completed "
            f"{total_questions} questions "
            f"with {score} correct answers."
        )

        result_message.set_text(
            get_result_message(
                percentage
            )
        )

        # ------------------------------------------------
        # PROGRESS
        # ------------------------------------------------

        progress_text.set_text(
            "Quiz Complete"
        )

        progress_percent.set_text(
            "100%"
        )

        progress_bar.value = 1

        score_label.set_text(
            f"⭐ Score: {score}"
        )

        timer_label.set_text(
            "🏁 Complete"
        )

        # ------------------------------------------------
        # IMPORTANT:
        # RENDER ANSWER KEY AFTER RESULT IS AVAILABLE.
        # ------------------------------------------------

        render_answer_key(
            result
        )

        # ------------------------------------------------
        # RENDER INSIGHTS
        # ------------------------------------------------

        render_insights(
            result
        )

    # ========================================================
    # RESULT MESSAGE
    # ========================================================

    def get_result_message(
        percentage: float,
    ) -> str:

        if percentage >= 90:

            return (
                "🏆 Excellent! "
                "Your Japanese number recognition is strong."
            )

        if percentage >= 75:

            return (
                "🔥 Good work! "
                "Your recognition is developing well."
            )

        if percentage >= 60:

            return (
                "👍 Developing! "
                "Keep repeating the numbers you missed."
            )

        return (
            "📚 Needs practice. "
            "Go back to Learn mode and build "
            "automatic recognition."
        )

    # ========================================================
    # ANSWER KEY
    # ========================================================

    def render_answer_key(
        result: dict,
    ) -> None:

        # ------------------------------------------------
        # CLEAR OLD CONTENT
        # ------------------------------------------------

        for child in list(
            answer_key_container
        ):

            child.delete()

        answers = result.get(
            "answers",
            []
        )

        if not answers:

            with answer_key_container:

                ui.label(
                    "No answer data was returned."
                ).classes(
                    "text-sm text-gray-500 py-4"
                )

            return

        # ==================================================
        # IMPORTANT FIX
        #
        # Dynamic cards MUST be created inside
        # answer_key_container.
        # ==================================================

        with answer_key_container:

            for answer in answers:

                position = answer.get(
                    "position",
                    "?"
                )

                details = answer.get(
                    "correct_details",
                    {}
                )

                selected = answer.get(
                    "selected_number"
                )

                target = answer.get(
                    "target_number"
                )

                is_correct = bool(
                    answer.get(
                        "is_correct",
                        False
                    )
                )

                # --------------------------------------------
                # YOUR ANSWER
                # --------------------------------------------

                if selected is None:

                    your_answer = "No answer"

                else:

                    your_answer = str(
                        selected
                    )

                # --------------------------------------------
                # JAPANESE DETAILS
                # --------------------------------------------

                hiragana = str(
                    details.get(
                        "hiragana",
                        ""
                    )
                ).replace(
                    " ",
                    ""
                )

                kanji = str(
                    details.get(
                        "kanji",
                        ""
                    )
                )

                romaji = str(
                    details.get(
                        "romaji",
                        ""
                    )
                )

                # --------------------------------------------
                # ANSWER CARD
                # --------------------------------------------

                with ui.card().classes(
                    "answer-key-item w-full p-4 md:p-5"
                ):

                    with ui.row().classes(
                        "w-full items-center "
                        "justify-between "
                        "gap-4 flex-wrap"
                    ):

                        # ====================================
                        # LEFT
                        # ====================================

                        with ui.column().classes(
                            "gap-1"
                        ):

                            ui.label(
                                f"QUESTION {position}"
                            ).classes(
                                "text-xs font-extrabold "
                                "tracking-widest "
                                "text-gray-400"
                            )

                            ui.label(
                                hiragana
                            ).classes(
                                "text-2xl md:text-3xl "
                                "font-extrabold "
                                "text-slate-900"
                            )

                            ui.label(
                                f"{kanji}  •  {romaji}"
                            ).classes(
                                "text-sm "
                                "text-gray-500 "
                                "font-semibold"
                            )

                        # ====================================
                        # RIGHT
                        # ====================================

                        with ui.column().classes(
                            "items-end gap-1"
                        ):

                            ui.label(
                                f"Your answer: "
                                f"{your_answer}"
                            ).classes(
                                "font-bold "
                                "text-slate-700"
                            )

                            ui.label(
                                f"Correct answer: "
                                f"{target}"
                            ).classes(
                                "font-extrabold "
                                "text-indigo-700"
                            )

                            if is_correct:

                                ui.label(
                                    "✓ Correct"
                                ).classes(
                                    "font-extrabold "
                                    "text-green-600"
                                )

                            elif selected is None:

                                ui.label(
                                    "⏰ Unanswered"
                                ).classes(
                                    "font-extrabold "
                                    "text-orange-500"
                                )

                            else:

                                ui.label(
                                    "✗ Incorrect"
                                ).classes(
                                    "font-extrabold "
                                    "text-red-500"
                                )

    # ========================================================
    # INSIGHTS
    # ========================================================

    def render_insights(
        result: dict,
    ) -> None:

        # ------------------------------------------------
        # CLEAR OLD CONTENT
        # ------------------------------------------------

        for child in list(
            insights_container
        ):

            child.delete()

        answers = result.get(
            "answers",
            []
        )

        if not answers:
            return

        # ------------------------------------------------
        # COUNTS
        # ------------------------------------------------

        correct_count = sum(
            1
            for answer in answers
            if answer.get(
                "is_correct",
                False
            )
        )

        unanswered_count = sum(
            1
            for answer in answers
            if answer.get(
                "selected_number"
            ) is None
        )

        incorrect_count = sum(
            1
            for answer in answers
            if (
                answer.get(
                    "selected_number"
                ) is not None
                and not answer.get(
                    "is_correct",
                    False
                )
            )
        )

        percentage = float(
            result.get(
                "percentage",
                0
            )
        )

        # ==================================================
        # IMPORTANT FIX
        #
        # Create the insights card INSIDE the container.
        # ==================================================

        with insights_container:

            with ui.card().classes(
                "w-full p-5 result-card"
            ):

                ui.label(
                    "📊 Performance Insights"
                ).classes(
                    "text-xl font-extrabold "
                    "text-slate-900"
                )

                # --------------------------------------------
                # PERFORMANCE COUNTERS
                # --------------------------------------------

                with ui.grid(
                    columns=3
                ).classes(
                    "w-full gap-4 mt-4"
                ):

                    # CORRECT

                    with ui.column().classes(
                        "gap-1"
                    ):

                        ui.label(
                            "CORRECT"
                        ).classes(
                            "text-xs font-extrabold "
                            "tracking-widest "
                            "text-gray-400"
                        )

                        ui.label(
                            str(correct_count)
                        ).classes(
                            "text-2xl "
                            "font-extrabold "
                            "text-green-600"
                        )

                    # INCORRECT

                    with ui.column().classes(
                        "gap-1"
                    ):

                        ui.label(
                            "INCORRECT"
                        ).classes(
                            "text-xs font-extrabold "
                            "tracking-widest "
                            "text-gray-400"
                        )

                        ui.label(
                            str(incorrect_count)
                        ).classes(
                            "text-2xl "
                            "font-extrabold "
                            "text-red-500"
                        )

                    # UNANSWERED

                    with ui.column().classes(
                        "gap-1"
                    ):

                        ui.label(
                            "UNANSWERED"
                        ).classes(
                            "text-xs font-extrabold "
                            "tracking-widest "
                            "text-gray-400"
                        )

                        ui.label(
                            str(unanswered_count)
                        ).classes(
                            "text-2xl "
                            "font-extrabold "
                            "text-orange-500"
                        )

                # --------------------------------------------
                # ACCURACY
                # --------------------------------------------

                ui.separator().classes(
                    "my-5"
                )

                ui.label(
                    f"Accuracy: {percentage:.0f}%"
                ).classes(
                    "text-lg font-extrabold "
                    "text-indigo-700"
                )

                # --------------------------------------------
                # INSIGHT
                # --------------------------------------------

                if percentage >= 90:

                    insight = (
                        "Excellent recognition. "
                        "Your Japanese number recognition "
                        "is becoming automatic. "
                        "Try increasing the number of "
                        "questions or reducing the "
                        "time per question."
                    )

                elif percentage >= 75:

                    insight = (
                        "Your foundation is solid. "
                        "Review the few numbers you missed "
                        "without relying on Romaji."
                    )

                elif percentage >= 60:

                    insight = (
                        "You are building recognition. "
                        "Spend more time in Learn mode on "
                        "the numbers you missed, "
                        "then retry the quiz."
                    )

                else:

                    insight = (
                        "The recognition is not automatic yet. "
                        "Return to Learn mode, listen to "
                        "the numbers, and practice them "
                        "repeatedly before another quiz."
                    )

                ui.label(
                    insight
                ).classes(
                    "text-slate-600 "
                    "mt-5 leading-relaxed"
                )

    # ========================================================
    # RESET QUIZ
    # ========================================================

    def reset_quiz() -> None:

        stop_speech()

        # ------------------------------------------------
        # RESET STATE
        # ------------------------------------------------

        state.update(
            started=False,
            finished=False,

            quiz=None,
            result=None,

            error=None,

            question_index=0,

            selected=None,
            answered=False,

            answers={},

            time_left=DEFAULT_TIME_LIMIT,
        )

        # ------------------------------------------------
        # CLEAR OLD RESULT CONTENT
        # ------------------------------------------------

        for child in list(
            answer_key_container
        ):

            child.delete()

        for child in list(
            insights_container
        ):

            child.delete()

        # ------------------------------------------------
        # RESET VISIBILITY
        # ------------------------------------------------

        setup_card.set_visibility(
            True
        )

        quiz_card.set_visibility(
            False
        )

        results_card.set_visibility(
            False
        )

        # ------------------------------------------------
        # RESET UI
        # ------------------------------------------------

        progress_text.set_text(
            "Ready to begin"
        )

        progress_percent.set_text(
            "0%"
        )

        progress_bar.value = 0

        score_label.set_text(
            "⭐ Score: 0"
        )

        timer_label.set_text(
            f"⏱️ {DEFAULT_TIME_LIMIT}s"
        )

        timer_big.set_text(
            f"{DEFAULT_TIME_LIMIT}s"
        )

    # ========================================================
    # TIMER
    # ========================================================

    def update_timer() -> None:

        if not state["started"]:
            return

        if state["finished"]:
            return

        if state["answered"]:
            return

        state["time_left"] -= 1

        timer_label.set_text(
            f"⏱️ {state['time_left']}s"
        )

        timer_big.set_text(
            f"{state['time_left']}s"
        )

        # ------------------------------------------------
        # TIMER COLOR
        # ------------------------------------------------

        if state["time_left"] <= 5:

            timer_big.classes(
                "text-red-600"
            )

        # ------------------------------------------------
        # TIMEOUT
        # ------------------------------------------------

        if state["time_left"] <= 0:

            timeout_question()

    # ========================================================
    # GLOBAL PAGE TIMER
    # ========================================================

    ui.timer(
        1.0,
        update_timer,
    )

    # ========================================================
    # FOOTER
    # ========================================================

    render_footer()