
"""Application entry point: NiceGUI frontend and FastAPI endpoints."""

from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from nicegui import app, ui

from learning_japanese.config import (
    APP_TITLE,
    CORS_ORIGINS,
    HOST,
    PORT,
)
from learning_japanese.data.database import init_db
from learning_japanese.backend.api import router
from learning_japanese.frontend import (
    home,
    learn,
    practice,
    quiz,
    progress,
    pomodoro,
)

# Initialize the database.
init_db()

# Configure API cross-origin access.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-Partner-API-Key",
        "Authorization",
    ],
)

# Register backend endpoints.
app.include_router(router)


@app.get("/openapi.json", include_in_schema=False)
def openapi_json() -> JSONResponse:
    return JSONResponse(content=app.openapi())


@app.get("/docs", include_in_schema=False)
def api_docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{APP_TITLE} - API Docs",
    )


# Register NiceGUI pages.
@ui.page("/")
def homepage() -> None:
    home.render()


@ui.page("/learn")
def learn_page() -> None:
    learn.render()


@ui.page("/practice")
def practice_page() -> None:
    practice.render()


@ui.page("/quiz")
def quiz_page() -> None:
    quiz.render()


@ui.page("/progress")
def progress_page() -> None:
    progress.render()


@ui.page("/pomodoro")
def pomodoro_page() -> None:
    pomodoro.render()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title=APP_TITLE,
        host=HOST,
        port=PORT,
        reload=False,
        show=False,
    )
