@echo off
title Enviar Tema Ford Fiesta XR2 Mk2 para o Ecra
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo  A ENVIAR TEMA FORD FIESTA XR2 MK2 HOT HATCH
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py xr2
pause
