@echo off
title Enviar Tema Peugeot 508 SW Digital i-Cockpit para o Ecra
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo   A ENVIAR TEMA PEUGEOT 508 SW (DIGITAL i-COCKPIT GT)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py 508
pause
