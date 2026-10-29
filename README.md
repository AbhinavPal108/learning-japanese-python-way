# Learning Japanese the Python Way

**Project Review 2 — runnable Python web application, REST API, database, and partner integration.**

This project follows the visual direction of the supplied reference: a pale background, a blue/purple/teal gradient hero, a white learning card, and the four main areas **Learn, Practice, Quiz, Progress**. It uses Python for application code and Python frameworks for UI/API. There is no React, Node.js app, or separate JavaScript build step.

## Architecture at a glance

```text
Browser
  │
  ▼
NiceGUI frontend (Python pages)
 Home │ Learn │ Practice │ Quiz │ Progress
  │  calls shared Python services in-process
  ▼
Service layer
 Number readings │ Practice scoring │ Quiz generation/scoring │ Progress analytics
 Pomodoro summary fetched server-side from its authenticated API
  │                              ▲
  ▼                              │
SQLite database                  │ FastAPI REST API (/api/v1)
 lesson/audio events             │ JSON endpoints for partner project
 practice attempts               │
 quiz sessions + each answer     ├── GET /api/v1/partner/export/{learner_id}
 progress aggregates             └── POST /api/v1/partner/events

Partner project ───────────── HTTP + JSON + optional X-Partner-API-Key ────────┘
```

The NiceGUI frontend and FastAPI endpoints run in **one Python process**. A user can interact through the website, while the partner project can use the documented endpoints. Both interfaces call the same service functions, so scoring and persistence stay consistent.

## Technology choices

| Layer | Tool | Why it is used |
|---|---|---|
| Frontend | NiceGUI | Build web pages and controls directly in Python |
| API/backend | FastAPI | Typed REST endpoints, request validation, interactive `/docs` |
| Schemas | Pydantic | Validate JSON received from either frontend or partner project |
| Logic | Python modules | Number readings, quiz generation, scoring and progress |
| Database | SQLite via Python `sqlite3` | Local persistence without a separate database server |
| Web server | Uvicorn via NiceGUI | Serves the UI and API |
| Charts | NiceGUI `ui.echart` component | Quiz trend and practice accuracy visualizations |
| Voice | Browser speech synthesis invoked by a Python callback | Reads Japanese text using the available `ja-JP` voice; availability varies by lab browser/OS |

CSS is used only to style the NiceGUI pages. No frontend build tool is required. Browser speech synthesis is a built-in browser capability and may not have a Japanese voice installed on every lab machine.

## Website roadmap

1. **Homepage (`/`)** — project introduction and navigation to all modules.
2. **Learn (`/learn`)** — number navigation 1–100, kanji, hiragana, Romaji, voice, slider, range jump buttons, and saved lesson/audio events.
3. **Practice (`/practice`)** — random multiple-choice questions, instant feedback, and saved answers.
4. **Quiz (`/quiz`)** — 10 randomized questions, one point each, unanswered questions score zero, server-side scoring, performance grade, and saved individual answers.
5. **Progress (`/progress`)** — attempt totals, practice accuracy, quizzes completed, best score, score trend, practice accuracy chart and recent quiz history.
6. **Pomodoro (`/pomodoro`)** — standalone focus timer with 25-minute focus sessions, 5-minute short breaks, and a 15-minute long break after four focus sessions. Timer state is stored in the Japanese app's SQLite database, so it continues across pages and is restored when the Pomodoro page is reopened. The homepage retrieves today/all-time focus totals from Pomodoro's protected summary API; the integration token stays on the backend.

## Folder structure

```text
learning_japanese_python_review2_updated/
├── learning_japanese/
│   ├── main.py                  # Starts NiceGUI and registers FastAPI router
│   ├── config.py                # Environment-based configuration
│   ├── backend/api.py           # REST routes and partner access guard
│   ├── data/database.py         # SQLite connection and schema creation
│   ├── models/schemas.py        # Pydantic request models
│   ├── services/number_service.py      # Correct readings for 1–100
│   ├── services/learning_service.py    # Event saving, practice, quiz and stats logic
│   ├── services/pomodoro_service.py    # Pomodoro timer and authenticated summary client
│   └── frontend/
│       ├── theme.py             # Shared visual theme and navigation
│       ├── home.py              # Homepage
│       ├── learn.py             # Learn module
│       ├── practice.py          # Practice module
│       ├── quiz.py              # Quiz module
│       ├── progress.py          # Charts and history
│       └── pomodoro.py          # Standalone Pomodoro timer page
├── tests/test_api.py            # API, persistence, Pomodoro integration and number smoke tests
├── docs/API.md                  # Endpoint catalog and curl examples
├── scripts/run_lab.sh           # Linux environment setup and launch helper
├── .env.example                 # Configuration template
├── requirements.txt
└── README.md
```

## Run it in your Linux class lab

### Option A — use the ZIP (recommended)

1. Copy the ZIP into your lab account and extract it. For example, if it is in `~/Downloads`:

   ```bash
   cd ~/Downloads
   unzip learning_japanese_python_review2_updated.zip
   cd learning_japanese_python_review2_updated
   ```

2. Check that Python 3.10 or newer and `venv` are available:

   ```bash
   python3 --version
   python3 -m venv --help
   ```

   On a Debian/Ubuntu lab machine, if `venv` is missing and you have permission, ask the lab admin to install the matching `python3-venv` package.

3. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

   The lab needs package-index/network access for the first installation, or the instructor/admin must provide the required wheels. The runtime itself does not require a separate Node.js installation.

4. Configure the application:

   ```bash
   cp .env.example .env
   nano .env
   ```

   Set a strong `PARTNER_API_KEY` before the companion project uses the partner endpoints. Use the **same secret** in both projects. The `./scripts/run_lab.sh` helper generates a key in `.env` on first setup if it is blank; copy that same value into the partner project securely. Do not commit `.env` or send the secret in a review report.

   To show Pomodoro totals on the Japanese-learning homepage, set
   `POMODORO_URL` to the Pomodoro server's base URL and
   `STUDY_INTEGRATION_TOKEN` to the same value configured on both services.
   The token is used only by the backend and is never
   sent to the browser. If the token is missing or the API is unavailable,
   the homepage shows an unavailable message and Retry button.

5. Launch the app:

   ```bash
   set -a
   source .env
   set +a
   python -m learning_japanese.main
   ```

   Or run `./scripts/run_lab.sh` to create a virtual environment, install requirements, create `.env` when missing and launch it. The script installs packages, so it requires the package source to be reachable if the environment is not already prepared.

6. Open the browser on that lab machine:

   - Website: `http://127.0.0.1:8080`
   - API health: `http://127.0.0.1:8080/api/v1/health`
   - API documentation: `http://127.0.0.1:8080/docs`
   - OpenAPI JSON: `http://127.0.0.1:8080/openapi.json`

   The app binds to `0.0.0.0` by default so it can be reached on the lab network if firewall and lab rules permit. For a local-only session, set `HOST=127.0.0.1` in `.env`. Do not expose a classroom demo beyond the permitted network.

### Option B — start from the source modules in the lab

This is useful if your instructor asks you to demonstrate how it is built:

1. Create a project directory and Python package directories:

   ```bash
   mkdir -p learning_japanese/{backend,data,frontend,models,services} tests docs scripts
   touch learning_japanese/__init__.py
   touch learning_japanese/{backend,data,frontend,models,services}/__init__.py
   ```

2. Copy the corresponding `.py` modules from this submission into their matching directories, plus `requirements.txt` and `.env.example`.
3. Create a virtual environment and install requirements as described in Option A.
4. Read the code in this order so the dependencies are clear:
   - `services/number_service.py` — number readings and edge cases after 10.
   - `data/database.py` — persisted tables and relationships.
   - `services/learning_service.py` — service/business logic and server-side score calculation.
   - `models/schemas.py` — valid API request structure.
   - `backend/api.py` — endpoints for the UI and partner.
   - `frontend/theme.py` and `frontend/*.py` — visual theme and page interactions.
   - `main.py` — composition root that connects frontend, API and database.
5. Start it with `python -m learning_japanese.main`.

The files are intentionally separated by responsibility; do not collapse the backend, UI callbacks and SQL into one giant file.

## Verify the project before review

Activate the virtual environment first:

```bash
source .venv/bin/activate
python -m compileall -q learning_japanese tests
python -m unittest discover -s tests -v
```

The root `pytest` configuration intentionally collects only this app's `tests/`
directory. Pomodoro and Aura Cards are separate projects with their own
dependencies and tests; run those suites from their respective project
directories and virtual environments.

The test suite checks the 1–100 number list, troublesome transition points (10, 11, 20, 42, 99, 100), saved practice, scoring and persistence of every quiz answer, duplicate-submission handling, and partner event import/export. The tests create a temporary database and do not overwrite the classroom demo database.

If the UI import fails because NiceGUI was not installed, install packages inside the active virtual environment with `python -m pip install -r requirements.txt` and retry. If an institutional proxy blocks package download, request approved packages from the lab administrator.

## How to connect your partner's project

### Agree on the contract first

Your partner should agree on a shared learner identifier, event names, fields in each payload, API base URL, and who owns each type of data. Start with one integration test before exchanging real project data.

### Configure both projects

- Deploy or run this project on a host the other project can reach.
- Add `PARTNER_API_KEY` to this project's environment.
- Add the same key to the partner project's environment.
- Set `CORS_ORIGINS` to the exact browser origin only if a partner frontend calls this API directly. A server-to-server call does not need browser CORS.
- Use HTTPS and rotate the key if the app is hosted outside the isolated lab network.

### Data-sharing direction

- **Partner → this app:** `POST /api/v1/partner/events` stores an event with its `source_project` and payload.
- **This app → partner:** partner calls `GET /api/v1/partner/export/{learner_id}` to read aggregated progress and recent activity.
- **Both projects:** use JSON requests/responses and a common learner ID; preserve the `source_project` field to identify provenance.

Example command (replace URL, learner ID and secret):

```bash
curl -X POST http://127.0.0.1:8080/api/v1/partner/events \
  -H 'Content-Type: application/json' \
  -H 'X-Partner-API-Key: YOUR_SHARED_SECRET' \
  -d '{"learner_id":"demo-user","event_type":"module_completed","source_project":"my-partner-project","payload":{"module":"flashcards","completed":true}}'

curl http://127.0.0.1:8080/api/v1/partner/export/demo-user \
  -H 'X-Partner-API-Key: YOUR_SHARED_SECRET'
```

**Do not share the `.db` file or connect both projects to the same SQLite file.** API-based exchange is safer and preserves modularity. If the projects need many simultaneous writers or production-scale multi-instance deployment, plan a PostgreSQL migration; SQLite is suitable for this single-instance review prototype.

## Database records

- `learning_events` — lesson views, audio listen events, quiz lifecycle and incoming partner events.
- `practice_attempts` — learner, question, answer, correctness, source and timestamp.
- `quiz_sessions` — quiz lifecycle, score, percentage and grade.
- `quiz_questions` — server-generated question targets and choices.
- `quiz_answers` — each submitted answer, including unanswered items and correctness.

Database tables are created automatically when the app starts. The database file is local and excluded from the ZIP/git by `.gitignore`; actual records are created when the app runs.

## Scoring policy

A quiz has 10 questions in the website. The backend calculates the grade from percentage: **Excellent** (90–100%), **Good** (75–89.99%), **Developing** (60–74.99%), and **Needs Practice** (below 60%). The API supports quiz lengths from 1 to 20 for integration testing, but the website uses 10. A submitted quiz cannot be submitted a second time.

## Known lab considerations

- A Japanese browser voice may need to be enabled/installed in the lab operating system. The `Listen` button uses browser-native speech synthesis and does not download audio files.
- `PARTNER_API_KEY` should be set for shared use. An empty key means partner routes are intentionally open for local-only testing; the lab launch script auto-generates a key if it finds the value blank.
- Binding to `0.0.0.0` alone does not guarantee network access; lab firewall and institutional network policy still apply.
- For a public deployment, use HTTPS, a strong key, persistent storage, and an appropriate database policy.
