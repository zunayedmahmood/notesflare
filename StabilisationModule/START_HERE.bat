@echo off
setlocal
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

IF EXIST ".venv\Scripts\python.exe" (
    set PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe
) ELSE (
    set PYTHON=python
)

%PYTHON% StabilisationModule\run_stabilisation_benchmark.py %*
