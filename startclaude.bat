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

REM Remote Control: the logon sessions are the ones Emma drives from another
REM device, and without this flag they open WITHOUT it and her workflows stop.
REM The name is given EXPLICITLY. --remote-control takes an OPTIONAL value, so
REM a bare flag immediately before "%BOOT_PROMPT%" would swallow the prompt as
REM the session name and the session would open idle. Measured 2026-09-16:
REM   claude --remote-control "<name>" -p "<prompt>"  ->  prompt runs, name set.
REM ---------------------------------------------------------------
REM MEMORY REAPER OPT-OUT. Emma's call, 2026-09-19, taken with AskUserQuestion.
REM
REM Claude Code kills BACKGROUND shell commands when system memory runs
REM critically low while the session is idle. It is a harness feature, not
REM Windows and not the command: the killed process has done nothing wrong and
REM the notice says so. On 2026-09-19 it killed a ~30-minute elevated test
REM suite mid-section, and then a 56.8 GB robocopy at 36.85 GB. Both had to be
REM resumed by hand, and this machine routinely runs multi-GB dump copies and
REM long suites in the background.
REM
REM IT MUST BE SET BEFORE claude STARTS. Setting it from a shell command inside
REM a running session has NO EFFECT, which is why it lives in the launcher and
REM cannot be fixed from a prompt.
REM
REM The trade-off Emma accepted: nothing now stops a runaway background job
REM driving the machine into swap. If that starts happening, delete this line
REM rather than working around it.
set "CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1"

"%CLAUDE_EXE%" --remote-control "shintowiki-scripts" "%BOOT_PROMPT%"

REM Keep the window open if Claude exits, so errors stay readable.
echo.
echo Claude Code exited with code %errorlevel%.
pause
