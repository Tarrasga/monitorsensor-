@echo off
title Enviar SmartCool para o GitHub
cd /d "%~dp0"

echo ======================================================================
echo    SMARTCOOL MASTER TELEMETRY // PUBLICAR NO GITHUB
echo ======================================================================
echo.
echo  Configuracao Git Detetada:
echo  - Utilizador: Tarrasga
echo  - Email:      cac.7.84@gmail.com
echo  - Branch:     main
echo.
echo ======================================================================
echo.

git remote get-url origin >nul 2>&1
if not errorlevel 1 goto PUSH_EXISTING

echo  Ainda nao esta configurado o link do repositorio GitHub.
echo.
echo  1. Cria um repositorio novo no teu GitHub (ex: SmartCool-Master-Telemetry)
echo  2. Copia o link HTTPS do repositorio (ex: https://github.com/Tarrasga/SmartCool-Master-Telemetry.git)
echo.
set /p REPO_URL="Cola aqui o link do repositorio GitHub: "

if "%REPO_URL%"=="" (
    echo [ERRO] Nenhum link introduzido. Operacao cancelada.
    pause
    exit /b 1
)

git remote add origin %REPO_URL%
echo.
echo [OK] Repositorio remoto adicionado: %REPO_URL%
echo.

:PUSH_EXISTING
echo A enviar ficheiros e historico para o GitHub...
echo.
git add .
git commit -m "Update SmartCool Master Telemetry" >nul 2>&1
git push -u origin main

if errorlevel 1 (
    echo.
    echo ======================================================================
    echo [AVISO] O envio falhou ou precisa de autenticacao no navegador.
    echo Podes tentar novamente ou verificar as permissoes da conta GitHub.
    echo ======================================================================
) else (
    echo.
    echo ======================================================================
    echo [SUCESSO TOTAL!] O projeto foi enviado com sucesso para o teu GitHub!
    echo ======================================================================
)

echo.
pause
