@echo off
title Enviar Velocímetros de Carro (Instrument Cluster) para o Ecra USB
cd /d "%~dp0..\SmartCoolApp"

echo ======================================================
echo    A ENVIAR VELOCÍMETROS DE CARRO (INSTRUMENT CLUSTER)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py speedometer
pause
