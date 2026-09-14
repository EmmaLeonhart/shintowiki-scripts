@echo off
setlocal EnableExtensions

REM ---------------------------------------------------------------
REM startclaude.bat - launch Claude Code in this repo, NON-elevated.
REM
REM House style, matching pc-manager\startclaude.bat. This is the one
REM that runs at logon (see pc-manager\startup\Install-Startup.ps1).
REM It deliberately does NOT request admin rights.
REM ---------------------------------------------------------------

REM Give the network / PATH a moment to settle after logon.
REM Pass --now as the first argument to skip the wait.
if /i "%~1"=="--now" (
    shift
) else (
    echo Starting Claude Code in 15 seconds. Close this window to cancel.
    timeout /t 15 /nobreak >nul 2>&1
)

REM Work from the repo folder so Claude picks up CLAUDE.md as context.
cd /d "%~dp0"

title Claude Code - shintowiki-scripts

echo ===============================================================
echo  Claude Code - standard user (NOT elevated)
echo  Working dir: %CD%
echo  Context:     CLAUDE.md in this folder
echo ===============================================================
echo.

REM %USERPROFILE% is NOT guaranteed to be set. PowerShell's
REM Start-Process -UseNewEnvironment rebuilds the block from the registry, and
REM on this machine that block is DEGENERATE: USERPROFILE empty, SystemDrive
REM empty, USERNAME=SYSTEM, and System32 off PATH (even findstr is missing).
REM Measured 2026-08-28. Do NOT start this script that way. Use explorer.exe,
REM which also strips the CLAUDE_CODE_* child-session vars but keeps the real
REM logon environment:   Start-Process explorer.exe '"<full path to this .bat>"'
if not defined USERPROFILE (
    if defined HOMEDRIVE if defined HOMEPATH set "USERPROFILE=%HOMEDRIVE%%HOMEPATH%"
)
if not defined USERPROFILE if defined SystemDrive set "USERPROFILE=%SystemDrive%\Users\%USERNAME%"
if not exist "%USERPROFILE%\" (
    echo ERROR: degenerate environment - USERPROFILE could not be resolved.
    echo Start this from the Startup shortcut, Explorer, or a normal console.
    pause
    exit /b 1
)

set "CLAUDE_EXE="
where claude >nul 2>&1
if %errorlevel% equ 0 (
    set "CLAUDE_EXE=claude"
) else if exist "%USERPROFILE%\.local\bin\claude.exe" (
    set "CLAUDE_EXE=%USERPROFILE%\.local\bin\claude.exe"
) else (
    echo ERROR: claude.exe not found on PATH or in %USERPROFILE%\.local\bin
    echo Install Claude Code, or edit this script with the correct path.
    pause
    exit /b 1
)

REM Opening prompt: pick up the work queue. Edit the text below to change
REM what the boot session does; delete it to get a plain idle session.
set "BOOT_PROMPT=Read queue.md and start working the highest-priority item that is not blocked on user action. Follow the queue-driven-workflow skill: finish an item, delete it from queue.md, append a dated devlog.md entry in the same commit, then push. Ask me before anything destructive."

"%CLAUDE_EXE%" "%BOOT_PROMPT%"

REM Keep the window open if Claude exits, so errors stay readable.
echo.
echo Claude Code exited with code %errorlevel%.
pause
