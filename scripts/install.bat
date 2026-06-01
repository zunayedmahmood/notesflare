@echo off
setlocal EnableDelayedExpansion

echo.
echo ════════════════════════════════════════
echo   NotesFlare — Installation
echo ════════════════════════════════════════
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

echo ^→ Installing Node.js dependencies...
call npm install
if errorlevel 1 ( echo X Node.js dependency install failed. & exit /b 1 )
echo v Node.js dependencies installed.
echo.

IF EXIST ".venv\Scripts\python.exe" (
    echo   (Using existing virtual environment at .venv^)
    set PYTHON="%PROJECT_ROOT%\.venv\Scripts\python.exe"
) ELSE (
    echo   (No .venv found - using system Python^)
    set PYTHON=python
)

echo ^→ Installing Python dependencies...
%PYTHON% -m pip install -r requirements.txt --quiet
if errorlevel 1 ( echo X Python dependency install failed. & exit /b 1 )
echo v Python dependencies installed.
echo.

echo ^→ Preparing optional V1.2 NLP models...
%PYTHON% -m spacy download en_core_web_sm --quiet
if errorlevel 1 (
    echo ! spaCy model download failed. NotesFlare will use fallback parser heuristics.
) ELSE (
    echo v spaCy model ready.
)

%PYTHON% -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" >nul 2>&1
if errorlevel 1 (
    echo ! MiniLM model not cached/available. Formatting still works; semantic paragraph detection is skipped.
) ELSE (
    echo v MiniLM embedding model ready.
)

%PYTHON% -c "import onnxruntime as ort; assert 'CPUExecutionProvider' in ort.get_available_providers()" >nul 2>&1
if errorlevel 1 (
    echo ! ONNX Runtime unavailable. Formatting still works without accelerator support.
) ELSE (
    echo v ONNX Runtime verified.
)

echo.
echo ^→ Creating storage directory...
if not exist storage mkdir storage
echo v Storage directory ready.
echo.

echo ════════════════════════════════════════
echo   Installation complete.
echo   Run scripts\start-dev.bat to launch NotesFlare.
echo ════════════════════════════════════════
echo.
