@echo off
setlocal EnableDelayedExpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

echo.
echo ════════════════════════════════════════
echo   NotesFlare — Starting Dev Environment
echo ════════════════════════════════════════
echo.

IF EXIST ".venv\Scripts\python.exe" (
    set PYTHON="%PROJECT_ROOT%\.venv\Scripts\python.exe"
) ELSE (
    set PYTHON=python
)

echo ^→ Checking V1.2 optional NLP dependencies...
%PYTHON% -c "missing=[]; import importlib.util as u; missing += ([] if u.find_spec('spacy') else ['spaCy']); missing += ([] if u.find_spec('sentence_transformers') else ['sentence-transformers']); missing += ([] if u.find_spec('onnxruntime') else ['onnxruntime']); print('  Optional NLP missing: ' + ', '.join(missing) if missing else '  Full NLP stack available.'); print('  NotesFlare still runs with fallback formatting when optional NLP is missing.' if missing else '')"
echo.

echo ^→ Starting Python backend...
start "NotesFlare Backend" /min cmd /c "cd /d "%PROJECT_ROOT%\backend" && %PYTHON% main.py"

echo ^→ Waiting for backend...
:WAIT_BACKEND
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 goto WAIT_BACKEND
echo v Backend is ready.
echo.

echo ^→ Starting Next.js frontend...
start "NotesFlare Frontend" /min cmd /c "cd /d "%PROJECT_ROOT%" && set NEXT_TELEMETRY_DISABLED=1 && npm run dev:frontend"

echo ^→ Waiting for frontend...
:WAIT_FRONTEND
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:3000 >nul 2>&1
if errorlevel 1 goto WAIT_FRONTEND
echo v Frontend is ready.
echo.

echo ^→ Compiling Electron TypeScript...
call npm run build:electron
if errorlevel 1 ( echo X Electron compile failed. & exit /b 1 )
echo v Electron compiled.
echo.

echo ^→ Launching Electron...
set NODE_ENV=development
npx electron . --no-sandbox
