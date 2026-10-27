@echo off
title Enviar Mesa de Mistura DJ (Studio Audio Equalizer) para o Ecra USB
cd /d "%~dp0..\SmartCoolApp"

echo ======================================================
echo    A ENVIAR MESA DE MISTURA DJ (STUDIO AUDIO EQUALIZER)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py mixer
pause
