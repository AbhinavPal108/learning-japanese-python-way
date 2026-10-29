@echo off
setlocal
set "POMODORO_ROOT=%~dp0"
for %%I in ("%POMODORO_ROOT%..\..") do set "JAPANESE_ROOT=%%~fI"

if not exist "%JAPANESE_ROOT%\.venv\Scripts\python.exe" (
    echo Japanese Learning App dependencies are not installed.
    echo Create its virtual environment and install requirements.txt first.
    exit /b 1
)

for /f "usebackq delims=" %%T in (`python -c "import secrets; print(secrets.token_urlsafe(32))"`) do set "STUDY_INTEGRATION_TOKEN=%%T"
if not defined STUDY_INTEGRATION_TOKEN (
    echo Could not create the shared integration token. Check that Python is installed.
    exit /b 1
)

set "POMODORO_URL=http://127.0.0.1:8000"
start "Pomodoro" cmd /k "cd /d ""%POMODORO_ROOT%"" && set HOST=127.0.0.1 && set PORT=8000 && set STUDY_INTEGRATION_TOKEN=%STUDY_INTEGRATION_TOKEN% && python server.py"
start "Japanese Learning App" cmd /k "cd /d ""%JAPANESE_ROOT%"" && set PORT=8080 && set POMODORO_URL=%POMODORO_URL% && set STUDY_INTEGRATION_TOKEN=%STUDY_INTEGRATION_TOKEN% && .venv\Scripts\python.exe -m learning_japanese.main"

echo Pomodoro: http://127.0.0.1:8000
echo Japanese Learning App: http://127.0.0.1:8080
echo Close each server window to stop that service.
