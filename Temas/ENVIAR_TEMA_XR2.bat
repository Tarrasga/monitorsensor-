@echo off
title Enviar Ford Fiesta XR2 Mk2 (Classic Hot Hatch) para o Ecra USB
cd /d "%~dp0..\SmartCoolApp"

echo ======================================================
echo    A ENVIAR FORD FIESTA XR2 MK2 (CLASSIC HOT HATCH)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py xr2
pause
