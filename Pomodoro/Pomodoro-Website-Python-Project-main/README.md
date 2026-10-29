# Pomodoro

Pomodoro is a standalone Python standard-library web app with a durable timer,
subjects and tasks, notes, study analytics, and an optional Gemini Study
Sidekick. Its only service integration is with the Japanese Learning App:
Pomodoro exposes an authenticated focus-summary API, and the Japanese app
fetches that summary from its backend.

## Run Pomodoro locally

From this directory, start the server:

```powershell
$env:HOST = "127.0.0.1"
$env:PORT = "8000"
$env:STUDY_INTEGRATION_TOKEN = "<same strong token configured in the Japanese app>"
python server.py
```

Open <http://127.0.0.1:8000>. The timer state and focus sessions are persisted
in `pomodoro.db`.

To run both services on Windows, `start_both.bat` creates a temporary shared
token and opens Pomodoro and the Japanese Learning App in separate terminals.
The Japanese app's virtual environment must already be installed.

## Japanese Learning App integration

Pomodoro exposes `GET /api/integrations/summary`. It returns today's and
all-time completed focus-session counts and minutes. Requests require:

```http
Authorization: Bearer <STUDY_INTEGRATION_TOKEN>
```

Configure these variables for the Japanese Learning App's backend:

- `POMODORO_URL` — Pomodoro base URL, such as `https://your-pomodoro-host`
  or `http://127.0.0.1:8000` for local development.
- `STUDY_INTEGRATION_TOKEN` — the same strong token configured on the
  Pomodoro server.

Pomodoro reads `STUDY_INTEGRATION_TOKEN`. The Japanese app reads
`POMODORO_URL` and `STUDY_INTEGRATION_TOKEN`. The token is backend-only and
must not be put into browser code or committed. Remote URLs must use HTTPS;
HTTP is allowed only for loopback development.

The summary route returns HTTP 503 when the Pomodoro token is not configured
and HTTP 401 when the supplied bearer token does not match. The Japanese
homepage shows real summary values only after a successful, validated response.

### Troubleshoot HTTP 401

A 401 means the Pomodoro service is running with a configured token, but the
token in the request does not match it. In the Render dashboard, copy the
`STUDY_INTEGRATION_TOKEN` value from the Pomodoro service's environment and
use that same raw value in the Japanese app's environment. Do not include
`Bearer ` in either environment variable; it is added only to the request
header. Never paste the token into a shared log, commit it, or send it in chat.

To test from PowerShell without putting the token in command history:

```powershell
$secureToken = Read-Host "Enter the Pomodoro STUDY_INTEGRATION_TOKEN" -AsSecureString
$token = [System.Net.NetworkCredential]::new("", $secureToken).Password
Invoke-RestMethod "https://pomodoro-website-python-project-4dm0.onrender.com/api/integrations/summary" `
  -Headers @{ Authorization = "Bearer $token" }
Remove-Variable token, secureToken
```

If this still returns 401, verify the value is from the currently deployed
Pomodoro service and that the Japanese app has the exact same value. A 503
instead means the Pomodoro service has no valid integration token configured.

## Tests

Run the Pomodoro server and browser-script tests:

```powershell
python -m unittest discover -s tests -v
node tests/test_timer_sync.cjs
```

The API tests use temporary databases and a test-only token.
