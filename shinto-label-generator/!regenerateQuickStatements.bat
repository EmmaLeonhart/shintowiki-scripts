@echo off
setlocal
cd /d "%~dp0"

cls
echo ==========================================
echo  Multi-Language QuickStatements Generator
echo ==========================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=py -3
) else (
    set PYTHON=python
)

echo [1/5] Generating Toki Pona labels...
%PYTHON% fetch_shrines_tokiponize.py
if errorlevel 1 (
    echo.
    echo ERROR: Toki Pona pipeline failed.
    pause
    exit /b 1
)
echo.

echo [2/5] Generating Korean labels...
%PYTHON% generate_korean_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Korean pipeline failed.
    pause
    exit /b 1
)
echo.

echo [3/5] Generating Chinese labels...
%PYTHON% generate_chinese_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Chinese pipeline failed.
    pause
    exit /b 1
)
echo.

echo [4/5] Generating tr/de/nl/es/it/eu/lt/ru/uk/fa/ar labels...
%PYTHON% generate_multilang_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Multilang pipeline failed.
    pause
    exit /b 1
)
echo.

echo [5/5] Generating Shikinaisha-list labels (Engishiki Jinmyocho + 69 province lists)...
%PYTHON% generate_shikinaisha_list_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Shikinaisha-list pipeline failed.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  All pipelines complete!
echo  Output in quickstatements/ directory
echo ==========================================
exit /b 0
