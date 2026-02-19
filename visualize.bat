@echo off
REM Quick launcher for vector store visualization tools

echo.
echo ========================================
echo Vector Store Visualization Tools
echo ========================================
echo.
echo 1. Quick Analysis (fast, works now)
echo 2. Interactive Explorer
echo 3. Full Visualization Suite
echo 4. Install visualization dependencies (uv sync)
echo 5. Exit
echo.

set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    echo.
    echo Running quick analysis...
    uv run quick_viz.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo Starting interactive explorer...
    uv run explore_vector_store.py
    pause
) else if "%choice%"=="3" (
    echo.
    echo Generating full visualizations...
    uv run visualize_vector_store.py
    echo.
    echo Opening visualizations folder...
    start visualizations
    pause
) else if "%choice%"=="4" (
    echo.
    echo Installing visualization dependencies...
    uv sync
    echo.
    echo Installation complete!
    pause
) else if "%choice%"=="5" (
    exit
) else (
    echo Invalid choice!
    pause
)
