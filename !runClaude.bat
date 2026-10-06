@echo off
cd /d "%~dp0"

echo ==========================================
echo Launching Claude from repo root:
echo 
echo ==========================================
echo.
REM --remote-control added 2026-10-06 at Emma's request: every launcher must start a session she can reach from her iPhone. The name is explicit because the flag takes an optional value.
claude --remote-control "shintowiki-scripts"
