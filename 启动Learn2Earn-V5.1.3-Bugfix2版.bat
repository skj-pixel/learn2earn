@echo off
chcp 65001 >nul
setlocal
title Learn2Earn V5.1.3 Bugfix2
set "LEARN2EARN_HISTORY_REPO=%~dp0"
if defined LEARN2EARN_LLM_API_KEY (
  echo [Learn2Earn V5.1.3-Bugfix2] LEARN2EARN_LLM_API_KEY detected; LLM key will be injected from env.
) else (
  echo [Learn2Earn V5.1.3-Bugfix2] WARNING: LEARN2EARN_LLM_API_KEY not set; LLM calls unavailable.
)
echo [Learn2Earn V5.1.3-Bugfix2] Starting local demo in fast mode (no git-worktree)...
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local_demo_fast.ps1"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo [Learn2Earn V5.1.3-Bugfix2] Startup failed. Run "首次准备依赖和构建产物.bat" first if dependencies are missing.
  pause
)
exit /b %EXIT_CODE%
