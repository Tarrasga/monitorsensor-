@echo off
title Enviar Peugeot 508 SW (Digital i-Cockpit GT) para o Ecra USB
cd /d "%~dp0..\SmartCoolApp"

echo ======================================================
echo    A ENVIAR PEUGEOT 508 SW (DIGITAL I-COCKPIT GT)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py 508
pause
