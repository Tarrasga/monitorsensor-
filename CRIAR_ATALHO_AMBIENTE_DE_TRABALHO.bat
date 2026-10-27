@echo off
title Criar Atalho Monster Telemetria no Ambiente de Trabalho
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo    A CRIAR ATALHO MONSTER TELEMETRIA NO AMBIENTE DE TRABALHO
echo ======================================================
echo.

python create_desktop_shortcut.py

echo.
echo ======================================================
echo  Atalho 'Monster Telemetria' criado com sucesso!
echo ======================================================
pause
