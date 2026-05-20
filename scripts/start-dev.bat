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

:: Python detection
IF EXIST ".venv\Scripts\python.exe" (
    set PYTHON="%PROJECT_ROOT%\.venv\Scripts\python.exe"
) ELSE (
    set PYTHON=python
)

:: Build frontend
echo ^→ Building frontend...
call npm run build:frontend
if errorlevel 1 ( echo X Frontend build failed. & exit /b 1 )
echo v Frontend built.
echo.

:: Build Electron TypeScript
echo ^→ Compiling Electron TypeScript...
call npm run build:electron
if errorlevel 1 ( echo X Electron compile failed. & exit /b 1 )
echo v Electron compiled.
echo.

:: Start Python backend in new window
echo ^→ Starting Python backend...
start "NotesFlare Backend" /min cmd /c "cd backend && %PYTHON% main.py"
echo   (Backend starting in background window)

:: Wait for backend
echo ^→ Waiting for backend...
:WAIT_LOOP
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 goto WAIT_LOOP
echo v Backend is ready.
echo.

:: Launch Electron
echo ^→ Launching Electron...
echo.
npx electron .
