"""Practice page with randomized multiple-choice questions and immediate feedback."""
import random
from nicegui import ui
from learning_japanese.config import DEFAULT_LEARNER_ID
from learning_japanese.frontend.theme import render_header, render_footer
from learning_japanese.services.number_service import number_details
from learning_japanese.services.learning_service import record_practice_attempt


def render() -> None:
    render_header("practice", "Practice Japanese Numbers", "Recognize the Japanese number, choose the matching digit, and get instant feedback.")
    state: dict = {"number": None, "options": [], "answered": False, "feedback": None, "last_correct": None}

    def new_question() -> None:
        target = random.randint(1, 100)
        distractors = set()
        while len(distractors) < 3:
            value = random.randint(1, 100)
            if value != target:
                distractors.add(value)
        options = list(distractors) + [target]
        random.shuffle(options)
        state.update(number=target, options=options, answered=False, feedback=None, last_correct=None)
        practice_content.refresh()

    def choose(selected: int) -> None:
        if state["answered"]:
            return
        result = record_practice_attempt(DEFAULT_LEARNER_ID, state["number"], selected)
        state["answered"] = True
        state["last_correct"] = result["is_correct"]
        state["feedback"] = (
            f"Correct! {state['number']} = {number_details(state['number'])['hiragana']} ({number_details(state['number'])['romaji']})"
            if result["is_correct"] else
            f"Not quite. The correct answer is {state['number']} — {number_details(state['number'])['hiragana']} ({number_details(state['number'])['romaji']})."
        )
        practice_content.refresh()

    @ui.refreshable
    def practice_content() -> None:
        if state["number"] is None:
            with ui.card().classes("jp-card w-full p-6"):
                ui.label("Ready to practice?").classes("text-xl font-extrabold")
                ui.label("Each question uses a random number from 1 to 100.").classes("text-sm text-gray-500")
                ui.button("Start practice →", on_click=new_question).props("unelevated no-caps").classes("jp-primary mt-3")
            return
        details = number_details(state["number"])
        with ui.card().classes("jp-card w-full p-6 md:p-8"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("QUESTION").classes("text-xs font-extrabold tracking-widest text-gray-400")
                ui.label("Multiple choice • instant feedback").classes("text-xs text-gray-500")
            ui.label("Which number matches this Japanese reading?").classes("text-lg font-bold mt-3")
            ui.label(str(details["kanji"])).classes("text-3xl font-extrabold text-gray-500")
            ui.label(str(details["hiragana"])).classes("jp-kana")
            ui.label(str(details["romaji"])).classes("jp-romaji")
            with ui.grid(columns=2).classes("w-full gap-3 mt-4"):
                for option in state["options"]:
                    ui.button(str(option), on_click=lambda value=option: choose(value)).props("outline no-caps") \
                        .classes("w-full text-lg font-bold py-2").set_enabled(not state["answered"])
            if state["feedback"]:
                with ui.element("div").classes("w-full rounded-xl p-4 mt-4").style(
                    "background:#e9faf1;border:1px solid #b9eed0" if state["last_correct"] else
                    "background:#fff1f0;border:1px solid #ffd2cf"
                ):
                    ui.label("✓  " + state["feedback"]).classes("font-bold " + ("text-green-800" if state["last_correct"] else "text-red-800"))
                ui.button("Next question →", on_click=new_question).props("unelevated no-caps").classes("jp-primary mt-3")
    with ui.column().classes("w-full max-w-4xl mx-auto px-4 md:px-6 pb-8 gap-4"):
        practice_content()
        with ui.row().classes("w-full gap-3 flex-wrap"):
            with ui.card().classes("jp-soft p-4 flex-1"):
                ui.label("What is saved?").classes("font-extrabold")
                ui.label("Target number, selected answer, correctness, timestamp and learner ID.").classes("text-sm text-gray-600")
            with ui.card().classes("jp-soft p-4 flex-1"):
                ui.label("Practice scoring").classes("font-extrabold")
                ui.label("Feedback is immediate. Practice attempts contribute to your accuracy chart.").classes("text-sm text-gray-600")
    render_footer()
