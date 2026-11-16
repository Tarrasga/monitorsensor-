@echo off
title Criar Pacote Portatil // Monster Telemetria (Sem Python)
cd /d "%~dp0"

echo ======================================================
echo   A COMPILAR MONSTER TELEMETRIA PORTATIL STANDALONE
echo   (VERSAO QUE NAO PRECISA DE PYTHON NO PC DO COLEGA)
echo ======================================================
echo.

python build_portable.py

if errorlevel 1 (
    echo.
    echo [ERRO] Ocorreu um erro ao criar o pacote portatil.
    pause
    exit /b 1
)

echo.
echo ======================================================
echo   Pacote criado com sucesso em:
echo   %~dp0MonsterTelemetria_Portable.zip
echo ======================================================
pause
