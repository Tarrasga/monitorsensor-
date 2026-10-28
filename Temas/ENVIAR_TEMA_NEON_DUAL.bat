@echo off
title Enviar Cyber Neon Dual (Azul & Vermelho) para o Ecra USB
cd /d "%~dp0..\SmartCoolApp"

echo ======================================================
echo    A ENVIAR CYBER NEON DUAL (AZUL & VERMELHO)
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine like '%%app.py%%'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

python send_theme.py neon_dual
pause
