"""Homepage: entry point and module roadmap."""
from nicegui import ui
from learning_japanese.frontend.theme import render_header, render_footer


def render() -> None:
    render_header("home", "", "")
    with ui.column().classes("w-full max-w-6xl mx-auto px-4 md:px-6 pt-2 pb-8 gap-6"):
        with ui.element("div").classes("jp-hero w-full"):
            ui.label("Learn Japanese the Python Way").classes("text-3xl md:text-4xl font-black leading-tight")
            ui.label("A beginner-friendly Japanese numbers platform.").classes("text-lg mt-2 opacity-95")
            ui.label("日本語  •  Hiragana  •  Romaji  •  Practice  •  Quiz  •  Progress").classes("mt-5 font-semibold")
            ui.button(
    "Start Learning  →",
    on_click=lambda: ui.navigate.to("/learn")
).props("no-caps unelevated") \
 .classes(
     "mt-4 bg-indigo-900 text-white font-bold "
     "rounded-lg px-6 py-3 shadow-lg "
     "hover:bg-indigo-950 transition-all"
 )
        with ui.row().classes("w-full items-end justify-between flex-wrap gap-2"):
            with ui.column().classes("gap-1"):
                ui.label("Your learning workspace").classes("text-xl font-extrabold")
                ui.label("Move from recognition to practice, then measure your progress.").classes("text-sm text-gray-500")
        cards = [
            ("📚", "Learn", "Explore numbers 1–100, kanji, hiragana, Romaji and voice pronunciation.", "/learn", "#edf4ff"),
            ("🎯", "Practice", "Answer random questions and get instant correct/incorrect feedback.", "/practice", "#e9faf5"),
            ("📝", "Quiz", "Take a 10-question assessment with server-side scoring and saved answers.", "/quiz", "#f1edff"),
            ("📊", "Progress", "Review accuracy, quiz score trends, recent attempts and learning activity.", "/progress", "#fff3e7"),
        ]
        with ui.grid(columns=2).classes("w-full gap-4"):
            for icon, title, desc, path, bg in cards:
                with ui.card().classes("jp-card w-full cursor-pointer p-5"):
                    with ui.row().classes("items-center gap-3"):
                        with ui.element("div").style(f"background:{bg};border-radius:14px;padding:12px"):
                            ui.label(icon).classes("jp-module-icon")
                        with ui.column().classes("gap-1 flex-1"):
                            ui.label(title).classes("text-lg font-extrabold")
                            ui.label(desc).classes("text-sm text-gray-600")
                    ui.button(f"Open {title} →", on_click=lambda p=path: ui.navigate.to(p)).props("flat no-caps") \
                        .classes("mt-3 text-indigo-700 font-bold self-start")
        with ui.card().classes("jp-soft w-full p-5"):
            ui.label("How the learning loop works").classes("text-lg font-extrabold")
            with ui.row().classes("w-full items-center justify-between gap-2 flex-wrap mt-3"):
                for i, (name, detail) in enumerate([
                    ("1. Learn", "See + listen"), ("2. Practice", "Try a question"),
                    ("3. Quiz", "Check mastery"), ("4. Progress", "Review results")
                ]):
                    with ui.column().classes("gap-1"):
                        ui.label(name).classes("font-extrabold text-indigo-700")
                        ui.label(detail).classes("text-xs text-gray-500")
                    if i < 3:
                        ui.label("→").classes("text-xl text-gray-400")
        with ui.card().classes("jp-card w-full p-5"):
            ui.label("Partner-project ready").classes("text-lg font-extrabold")
            ui.label("REST endpoints share progress and accept events from another project. Open the API documentation when the server is running.").classes("text-sm text-gray-600")
            ui.button("Open API docs  /docs ↗", on_click=lambda: ui.navigate.to("/docs")).props("outline no-caps").classes("mt-2")
    render_footer()
