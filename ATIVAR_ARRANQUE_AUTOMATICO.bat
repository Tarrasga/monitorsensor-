@echo off
title Ativar Arranque Automatico com o Windows
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo    A ATIVAR ARRANQUE AUTOMATICO COM O WINDOWS
echo ======================================================
echo.

python setup_startup.py

echo.
echo ======================================================
echo  Concluido! O SmartCool vai iniciar sempre que ligar o PC.
echo ======================================================
pause
