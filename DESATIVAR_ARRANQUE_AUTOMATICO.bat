@echo off
title Desativar Arranque Automatico com o Windows
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo   A DESATIVAR ARRANQUE AUTOMATICO COM O WINDOWS
echo ======================================================
echo.

python remove_startup.py

echo.
echo ======================================================
echo  Concluido! O arranque automatico foi desativado.
echo ======================================================
pause
