@echo off
title Gerar Animacao GIF 3D - Monster Energy
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo    A RENDERIZAR LATAS 3D DE MONSTER ENERGY (GIF)
echo ======================================================
echo.

python make_spinning_can_gif.py

echo.
pause
