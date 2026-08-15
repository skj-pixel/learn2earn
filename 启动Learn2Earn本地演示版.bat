@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if defined LEARN2EARN_LLM_API_KEY (
echo [Learn2Earn] LEARN2EARN_LLM_API_KEY detected; LLM key will be injected from env.
) else (
echo [Learn2Earn] WARNING: LEARN2EARN_LLM_API_KEY not set; LLM calls unavailable.
)
echo [Learn2Earn] Starting local demo in fast mode...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local_demo_fast.ps1"
if errorlevel 1 goto fail
endlocal
echo [Learn2Earn] Launcher exited. Press any key to close.
pause
exit /b 0
:fail
echo [Learn2Earn] Startup failed. Run the first-time prepare script manually.
endlocal
pause
exit /b 1