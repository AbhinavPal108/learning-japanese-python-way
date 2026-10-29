"""Standalone Pomodoro focus timer page."""
from __future__ import annotations

import time

from nicegui import ui

from learning_japanese.frontend.theme import render_footer, render_header
from learning_japanese.services.pomodoro_service import (
    MODE_DURATIONS,
    TimerMode,
    get_pomodoro_timer,
    pause_pomodoro_timer,
    reset_pomodoro_timer,
    select_pomodoro_mode,
    start_pomodoro_timer,
    tick_pomodoro_timer,
)


MODE_LABELS: dict[TimerMode, str] = {
    "focus": "Focus",
    "shortBreak": "Short Break",
    "longBreak": "Long Break",
}


def _format_time(seconds: int) -> str:
    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def render() -> None:
    render_header(
        "pomodoro",
        "Pomodoro Focus Timer",
        "Focus in short intervals, then take a restorative break.",
    )
    timer_state = get_pomodoro_timer()

    with ui.column().classes(
        "w-full max-w-3xl mx-auto px-4 md:px-6 pb-10 gap-5"
    ):
        with ui.card().classes("jp-card w-full p-6 md:p-8"):
            with ui.row().classes("w-full justify-center gap-2 flex-wrap"):
                mode_buttons = {}
                for mode, label in MODE_LABELS.items():
                    mode_buttons[mode] = ui.button(
                        label,
                        on_click=lambda selected=mode: select_mode(selected),
                    ).props("no-caps")

            timer_display = ui.label("25:00").classes(
                "w-full text-center text-6xl md:text-8xl font-black "
                "tracking-tight text-indigo-700 py-8"
            )
            status_display = ui.label("Time to focus.").classes(
                "w-full text-center text-lg font-semibold text-gray-600"
            )
            round_display = ui.label("Focus round 1 of 4").classes(
                "w-full text-center text-sm text-gray-500 mt-2"
            )
            with ui.row().classes("w-full justify-center gap-3 mt-5"):
                start_pause_button = ui.button(
                    "Start", on_click=lambda: toggle_timer()
                ).props("unelevated no-caps").classes("jp-primary px-8")
                ui.button("Reset", on_click=lambda: reset_timer()).props(
                    "outline no-caps"
                )

        with ui.card().classes("jp-soft w-full p-5"):
            ui.label("Pomodoro cycle").classes("text-lg font-extrabold")
            ui.label(
                "Focus for 25 minutes, take a 5-minute short break, "
                "and take a 15-minute long break after four focus sessions."
            ).classes("text-sm text-gray-600 mt-2")
            completed_display = ui.label("Completed focus sessions: 0").classes(
                "text-sm font-semibold text-indigo-700 mt-3"
            )

    def update_display() -> None:
        timer_state = get_pomodoro_timer()
        timer_display.set_text(
            _format_time(timer_state.remaining_seconds(time.time()))
        )
        status_display.set_text(
            {
                "focus": "Time to focus.",
                "shortBreak": "Take a short break.",
                "longBreak": "Take a long break.",
            }[timer_state.mode]
        )
        round_display.set_text(f"Focus round {timer_state.focus_round} of 4")
        completed_display.set_text(
            f"Completed focus sessions: {timer_state.completed_focus_sessions}"
        )
        start_pause_button.set_text("Pause" if timer_state.running else "Start")
        for mode, button in mode_buttons.items():
            button.set_enabled(not timer_state.running)
            button.props(
                "unelevated no-caps"
                if mode == timer_state.mode
                else "flat no-caps"
            )

    def select_mode(mode: TimerMode) -> None:
        nonlocal timer_state
        timer_state = select_pomodoro_mode(mode)
        update_display()

    def reset_timer() -> None:
        nonlocal timer_state
        timer_state = reset_pomodoro_timer()
        tick_timer.deactivate()
        update_display()

    def toggle_timer() -> None:
        nonlocal timer_state
        timer_state = get_pomodoro_timer()
        if timer_state.running:
            timer_state = pause_pomodoro_timer()
            tick_timer.deactivate()
        else:
            timer_state = start_pomodoro_timer()
            tick_timer.activate()
        update_display()

    def tick() -> None:
        nonlocal timer_state
        timer_state, finished_mode = tick_pomodoro_timer()
        update_display()
        if finished_mode is not None:
            tick_timer.deactivate()
            ui.notify(
                f"{MODE_LABELS[finished_mode]} interval complete.",
                type="positive",
            )

    tick_timer = ui.timer(1.0, tick, active=False)
    update_display()
    if timer_state.running:
        tick_timer.activate()
    render_footer()
