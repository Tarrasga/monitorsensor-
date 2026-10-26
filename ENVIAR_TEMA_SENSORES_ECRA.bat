@echo off
title Enviar Painel Completo de Sensores para o Ecra
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo    A ENVIAR PAINEL DE TODOS OS SENSORES PARA O ECRA
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py sensors

pause
