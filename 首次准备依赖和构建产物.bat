@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"

echo [Learn2Earn] First-time prepare mode.
echo [Learn2Earn] Run this only once, or when dependencies/build outputs are missing.
echo [Learn2Earn] This script installs/checks dependencies and builds frontend\dist.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\prepare_local_demo_once.ps1"

if errorlevel 1 (
  echo.
  echo [Learn2Earn] Preparation failed. Check the error above.
  pause
  exit /b 1
)

echo.
echo [Learn2Earn] Preparation complete. For daily use, double-click:
echo   启动Learn2Earn本地演示版.bat
echo.
pause
endlocal
