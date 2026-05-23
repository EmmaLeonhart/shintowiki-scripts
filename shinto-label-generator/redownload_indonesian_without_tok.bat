@echo off
setlocal
cd /d "%~dp0"

cls
echo ==========================================
echo Redownloading Indonesian-labeled shrines
echo without Toki Pona labels...
echo ==========================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 fetch_shrines_tokiponize.py
) else (
    python fetch_shrines_tokiponize.py
)

echo.
echo Done.
pause
