"""Shared theme inspired by the supplied blue-purple-teal reference UI."""
from nicegui import ui


CSS = r"""
:root {
    --jp-blue: #5597d4;
    --jp-purple: #7561f7;
    --jp-teal: #1eb49e;
    --jp-ink: #17233a;
    --jp-muted: #667085;
}

body {
    background: linear-gradient(
        135deg,
        #f8f8ff 0%,
        #eef8fb 55%,
        #f0fbf7 100%
    );
    color: var(--jp-ink);
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

/* =========================
   HEADER
   ========================= */

.jp-topbar {
    background: rgba(255, 255, 255, 0.94);
    border-bottom: 1px solid #e7eaf3;
}

.jp-brand {
    font-weight: 850;
    letter-spacing: -0.035em;
    color: #202b45;
}


/* =========================
   HERO
   ========================= */

.jp-hero {
    background: linear-gradient(
        115deg,
        #7660f5 0%,
        #6e83ee 48%,
        #1eb49e 100%
    );
    color: white;
    border-radius: 24px;
    padding: 30px 34px;
    box-shadow: 0 16px 42px rgba(78, 85, 188, 0.20);
}


/* =========================
   CARDS
   ========================= */

.jp-card {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #e5eaf2;
    border-radius: 20px;
    box-shadow: 0 8px 26px rgba(25, 43, 80, 0.045);
}

.jp-soft {
    background: linear-gradient(
        140deg,
        #f5f8ff,
        #effbf8
    );
    border: 1px solid #e1edf2;
    border-radius: 18px;
}


/* =========================
   JAPANESE NUMBER DISPLAY
   ========================= */

.jp-number {
    color: var(--jp-blue);
    font-size: 3.6rem;
    line-height: 1;
    font-weight: 850;
}

.jp-kana {
    font-size: 2rem;
    color: #131827;
    font-weight: 800;
}

.jp-romaji {
    color: #7b8191;
    font-size: 1.05rem;
    min-height: 48px;
}


/* =========================
   PRONUNCIATION HIGHLIGHT
   ========================= */

.pronunciation-container {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
}

.pronunciation-part {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 10px;

    color: #7b8191;
    font-size: 1.05rem;
    font-weight: 600;

    transition:
        background 0.2s ease,
        color 0.2s ease,
        transform 0.2s ease,
        box-shadow 0.2s ease;
}

.active-pronunciation {
    background: #e9ddff !important;
    color: #7c3aed !important;
    font-weight: 800;

    transform: scale(1.06);

    box-shadow:
        0 5px 16px rgba(124, 58, 237, 0.20);
}

.pronunciation-space {
    display: inline-block;
    width: 2px;
}


/* =========================
   NAVIGATION
   ========================= */

.jp-nav {
    border-radius: 12px;
    font-weight: 700;
}

.jp-active {
    background: #eeecff !important;
    color: #5e4ee3 !important;
}


/* =========================
   METRICS
   ========================= */

.jp-metric {
    border: 1px solid #e7ecf4;
    border-radius: 16px;
    background: white;
    padding: 16px;
    min-width: 135px;
}

.jp-metric-value {
    color: #366eaa;
    font-size: 1.75rem;
    line-height: 1.2;
    font-weight: 850;
}

.jp-caption {
    color: var(--jp-muted);
    font-size: 0.85rem;
}


/* =========================
   PAGE TITLE
   ========================= */

.jp-page-title {
    font-size: 1.65rem;
    line-height: 1.2;
    font-weight: 850;
    letter-spacing: -0.025em;
}


/* =========================
   PRIMARY BUTTON
   ========================= */

.jp-primary {
    background: linear-gradient(
        105deg,
        #5d9bd5,
        #6f79e9
    ) !important;

    color: white !important;
    font-weight: 750;
}


/* =========================
   MODULE ICON
   ========================= */

.jp-module-icon {
    font-size: 1.8rem;
}


/* =========================
   FOOTER
   ========================= */

.jp-footer {
    color: #8991a3;
    font-size: 0.8rem;
}


/* =========================
   QUIZ
   ========================= */

.q-tab {
    font-weight: 700;
}


/* =========================
   MOBILE
   ========================= */

@media (max-width: 640px) {

    .jp-hero {
        padding: 22px;
    }

    .jp-number {
        font-size: 2.7rem;
    }

    .jp-kana {
        font-size: 1.65rem;
    }

    .jp-romaji {
        font-size: 0.95rem;
    }

    .pronunciation-part {
        font-size: 0.95rem;
        padding: 4px 8px;
    }
}
.quiz-option {
    background: white !important;
    color: #17233a !important;
    border: 2px solid #e5eaf2 !important;
    transition: all .2s ease;
}

.quiz-option:hover {
    border-color: #7561f7 !important;
    background: #f5f3ff !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(117,97,247,.12);
}
"""


def inject_theme() -> None:
    ui.add_head_html(f"<style>{CSS}</style>")


def render_header(
    active: str,
    page_title: str,
    subtitle: str = ""
) -> None:

    inject_theme()

    with ui.header().classes(
        "jp-topbar items-center justify-between px-4 md:px-8 py-3"
    ):

        with ui.row().classes("items-center gap-3"):

            ui.label("🇯🇵").classes("text-2xl")

            with ui.column().classes("gap-0"):

                ui.label(
                    "Learning Japanese"
                ).classes("jp-brand text-lg")

                ui.label(
                    "The Python Way"
                ).classes("text-xs text-gray-500")

        ui.label(
            "PYTHON • JAPANESE • PROGRESS"
        ).classes(
            "hidden sm:block text-xs tracking-widest text-gray-500"
        )

    with ui.column().classes(
        "w-full max-w-6xl mx-auto px-4 md:px-6 pt-5 gap-4"
    ):

        with ui.row().classes(
            "w-full justify-center flex-wrap gap-2"
        ):

            links = [
                ("🏠 Home", "/", "home"),
                ("📚 Learn", "/learn", "learn"),
                ("🎯 Practice", "/practice", "practice"),
                ("📝 Quiz", "/quiz", "quiz"),
                ("📊 Progress", "/progress", "progress"),
            ]

            for label, path, key in links:

                button = ui.button(
                    label,
                    on_click=lambda p=path: ui.navigate.to(p)
                ).props("flat no-caps")

                button.classes(
                    "jp-nav "
                    + ("jp-active" if active == key else "")
                )

        if page_title:

            with ui.column().classes(
                "gap-1 w-full pt-1"
            ):

                ui.label(
                    page_title
                ).classes("jp-page-title")

                if subtitle:

                    ui.label(
                        subtitle
                    ).classes("text-sm text-gray-500")


def render_footer() -> None:

    ui.separator().classes("mt-8")

    ui.label(
        "Learning Japanese the Python Way • NiceGUI + FastAPI + SQLite"
    ).classes(
        "jp-footer text-center w-full py-4"
    )