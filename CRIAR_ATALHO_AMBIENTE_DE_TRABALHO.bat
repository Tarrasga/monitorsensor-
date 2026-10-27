@echo off
title Criar Atalho SmartCool no Ambiente de Trabalho
cd /d "%~dp0SmartCoolApp"

echo ======================================================
echo    A CRIAR ATALHO NO AMBIENTE DE TRABALHO
echo ======================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File create_shortcut.ps1

echo.
echo ======================================================
echo  Atalho com icone de termometro criado com sucesso!
echo ======================================================
pause
