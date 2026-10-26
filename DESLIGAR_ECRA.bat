@echo off
title Desligar Ecra SmartCool
cd /d "%~dp0SmartCoolApp"

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python desligar_ecra.py

echo.
echo Operacao concluida. Pressione qualquer tecla para sair...
pause >nul
