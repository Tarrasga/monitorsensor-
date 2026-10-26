@echo off
title Enviar Tema CS2 Tactical HUD para o Ecra
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo    A ENVIAR TEMA COUNTER-STRIKE 2 (CS2 HUD)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py cs2
pause
