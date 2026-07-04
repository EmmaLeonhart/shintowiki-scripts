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

echo [1/11] Generating Toki Pona labels...
%PYTHON% fetch_shrines_tokiponize.py
if errorlevel 1 (
    echo.
    echo ERROR: Toki Pona pipeline failed.
    pause
    exit /b 1
)
echo.

echo [2/11] Generating Korean labels...
%PYTHON% generate_korean_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Korean pipeline failed.
    pause
    exit /b 1
)
echo.

echo [3/11] Generating Chinese labels...
%PYTHON% generate_chinese_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Chinese pipeline failed.
    pause
    exit /b 1
)
echo.

echo [4/11] Generating tr/de/nl/es/it/eu/lt/ru/uk/fa/ar labels...
%PYTHON% generate_multilang_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Multilang pipeline failed.
    pause
    exit /b 1
)
echo.

echo [5/11] Generating Shikinaisha-list labels (Engishiki Jinmyocho + 69 province lists)...
%PYTHON% generate_shikinaisha_list_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Shikinaisha-list pipeline failed.
    pause
    exit /b 1
)
echo.

echo [6/11] Generating kami (deity) labels...
%PYTHON% generate_kami_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Kami pipeline failed.
    pause
    exit /b 1
)
echo.

echo [7/11] Generating shrine-rank labels...
%PYTHON% generate_shrine_rank_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Shrine-rank pipeline failed.
    pause
    exit /b 1
)
echo.

echo [8/11] Generating province labels...
%PYTHON% generate_province_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Province pipeline failed.
    pause
    exit /b 1
)
echo.

echo [9/11] Generating Buddhist deity labels (JP-engine + Sanskrit engine)...
%PYTHON% generate_buddhist_deity_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Buddhist deity pipeline failed.
    pause
    exit /b 1
)
echo.

echo [10/11] Generating Japanese text labels...
%PYTHON% generate_text_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Text pipeline failed.
    pause
    exit /b 1
)
echo.

echo [11/11] Generating misc Shinto term labels (architecture/rituals/sects)...
%PYTHON% generate_misc_terms_quickstatements.py
if errorlevel 1 (
    echo.
    echo ERROR: Misc-term pipeline failed.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  All pipelines complete!
echo  Output in quickstatements/ directory
echo ==========================================
exit /b 0
