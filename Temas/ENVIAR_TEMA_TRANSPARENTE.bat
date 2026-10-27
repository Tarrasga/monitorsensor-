@echo off
title Enviar HUD Overlay Transparente (Glass HUD) para o Ecra USB
cd /d "%~dp0..\SmartCoolApp"

echo ======================================================
echo    A ENVIAR HUD OVERLAY TRANSPARENTE (GLASS HUD)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py transparente
pause
