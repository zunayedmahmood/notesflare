@echo off
setlocal EnableDelayedExpansion
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
cd /d "%PROJECT_ROOT%"

IF EXIST ".venv\Scripts\python.exe" (
    set PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe
) ELSE (
    set PYTHON=python
)

set MODE=%1
if "%MODE%"=="" set MODE=all

if "%MODE%"=="original" (
    shift
    %PYTHON% StabilisationModule\run_stabilisation_benchmark.py %*
    goto :eof
)

if "%MODE%"=="continuous" (
    shift
    %PYTHON% StabilisationModule\run_stabilisation_benchmark.py --input StabilisationModule\examples_1000_continuous_stream.json --output StabilisationModule\outputs\formatted_results_continuous.json --summary StabilisationModule\outputs\benchmark_summary_continuous.json --benchmark-db StabilisationModule\outputs\stabilisation_benchmark_continuous.db %*
    goto :eof
)

if "%MODE%"=="progressive" (
    shift
    %PYTHON% StabilisationModule\generate_progressive_usage_examples.py
    %PYTHON% StabilisationModule\run_stabilisation_benchmark.py --input StabilisationModule\examples_1000_progressive_usage.json --output StabilisationModule\outputs\formatted_results_progressive_usage.json --summary StabilisationModule\outputs\benchmark_summary_progressive_usage.json --benchmark-db StabilisationModule\outputs\stabilisation_benchmark_progressive_usage.db --simulate-decisions --reset-progressive-profile --study-old-data %*
    goto :eof
)

if "%MODE%"=="all" (
    shift
    %PYTHON% StabilisationModule\run_stabilisation_benchmark.py %*
    %PYTHON% StabilisationModule\run_stabilisation_benchmark.py --input StabilisationModule\examples_1000_continuous_stream.json --output StabilisationModule\outputs\formatted_results_continuous.json --summary StabilisationModule\outputs\benchmark_summary_continuous.json --benchmark-db StabilisationModule\outputs\stabilisation_benchmark_continuous.db %*
    %PYTHON% StabilisationModule\generate_progressive_usage_examples.py
    %PYTHON% StabilisationModule\run_stabilisation_benchmark.py --input StabilisationModule\examples_1000_progressive_usage.json --output StabilisationModule\outputs\formatted_results_progressive_usage.json --summary StabilisationModule\outputs\benchmark_summary_progressive_usage.json --benchmark-db StabilisationModule\outputs\stabilisation_benchmark_progressive_usage.db --simulate-decisions --reset-progressive-profile --study-old-data %*
    goto :eof
)

%PYTHON% StabilisationModule\run_stabilisation_benchmark.py %*
