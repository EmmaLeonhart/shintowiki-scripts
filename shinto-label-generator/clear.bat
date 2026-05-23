@echo off
setlocal
cd /d "%~dp0"

cls
echo ==========================================
echo Full clear run: Indonesian shrine/temple set
echo ==========================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 fetch_shrines_tokiponize.py
) else (
    python fetch_shrines_tokiponize.py
)

if errorlevel 1 (
    echo.
    echo Pipeline failed. Fix the error above and rerun.
    pause
    exit /b 1
)

echo.
echo Pipeline complete. Output: shrines_tokiponized.csv + quickstatements.txt
exit /b 0
