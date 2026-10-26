@echo off
title Enviar Tema Velocimetros para o Ecra
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo  A ENVIAR TEMA VELOCIMETROS / INSTRUMENT CLUSTER
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py speedometer
pause
