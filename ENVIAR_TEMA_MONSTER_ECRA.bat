@echo off
title Enviar Tema Monster Energy para o Ecra
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo    A ENVIAR TEMA MONSTER ENERGY PARA O ECRA USB
echo ======================================================
echo.

python send_theme.py monster_cans

pause
