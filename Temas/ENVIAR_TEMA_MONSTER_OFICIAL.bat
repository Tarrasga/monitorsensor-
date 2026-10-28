@echo off
title Enviar Monster Telemetria (Logo Oficial) para o Ecra USB
cd /d "%~dp0..\SmartCoolApp"

echo ======================================================
echo    A ENVIAR MONSTER TELEMETRIA (LOGO OFICIAL)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py monster_official
pause
