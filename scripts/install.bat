@echo off
setlocal

echo.
echo ════════════════════════════════════════
echo   NotesFlare — Installation
echo ════════════════════════════════════════
echo.

:: Navigate to project root
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

:: Node dependencies
echo ^→ Installing Node.js dependencies...
call npm install
if errorlevel 1 (
    echo X npm install failed. Is Node.js 20+ installed?
    exit /b 1
)
echo v Node.js dependencies installed.
echo.

:: Python detection
IF EXIST ".venv\Scripts\python.exe" (
    echo ^→ Using virtual environment at .venv
    set PYTHON="%PROJECT_ROOT%\.venv\Scripts\python.exe"
) ELSE (
    echo ^→ No .venv found — using system Python
    set PYTHON=python
)

:: Python dependencies
echo ^→ Installing Python dependencies...
%PYTHON% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo X pip install failed. Is Python 3.11+ installed?
    exit /b 1
)
echo v Python dependencies installed.
echo.

:: Storage directory
echo ^→ Creating storage directory...
if not exist "storage" mkdir storage
echo v Storage directory ready.
echo.

echo ════════════════════════════════════════
echo   Installation complete.
echo   Run 'scripts\start-dev.bat' to launch.
echo ════════════════════════════════════════
echo.
