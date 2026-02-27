@echo off
setlocal

rem This .bat should live in: wikibot\shinto_miraheze
rem It runs scripts from parent folder: wikibot
set "WIKIBOT_DIR=%~dp0.."

echo Launching bot scripts from: %WIKIBOT_DIR%
echo.

start "normalize_category_pages" /D "%WIKIBOT_DIR%" cmd /k "python shinto_miraheze\normalize_category_pages.py --apply"
start "migrate_talk_pages" /D "%WIKIBOT_DIR%" cmd /k "python shinto_miraheze\migrate_talk_pages.py --apply"
start "tag_shikinaisha_talk_pages" /D "%WIKIBOT_DIR%" cmd /k "python shinto_miraheze\tag_shikinaisha_talk_pages.py --apply"
start "remove_crud_categories" /D "%WIKIBOT_DIR%" cmd /k "python shinto_miraheze\remove_crud_categories.py"

echo Opened 4 command windows.
echo If needed, close this window.

endlocal
