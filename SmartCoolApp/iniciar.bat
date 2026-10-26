@echo off
title SmartCool 3.5 Monitor - Inicializador
cd /d "%~dp0"

echo ======================================================
echo    SMARTCOOL 3.5 MONITOR // TARRASGA EDITION
echo ======================================================
echo.

:: Fechar qualquer instancia anterior em segundo plano para libertar a porta USB e a porta Wi-Fi 8080
taskkill /F /FI "WINDOWTITLE eq SmartCool*" >nul 2>&1
powershell -NoProfile -Command "Get-Process -Name python,py -ErrorAction SilentlyContinue | Stop-Process -Force" >nul 2>&1

:: 1. Testar python
python --version >nul 2>&1
if not errorlevel 1 goto RUN_PYTHON

:: 2. Testar py (Python Launcher)
py --version >nul 2>&1
if not errorlevel 1 goto RUN_PY

goto NO_PYTHON

:RUN_PYTHON
echo [1/2] A verificar dependencias...
python -m pip install -r requirements.txt --quiet --no-warn-script-location
echo [2/2] A iniciar o SmartCool Monitor...
python app.py
goto END

:RUN_PY
echo [1/2] A verificar dependencias...
py -m pip install -r requirements.txt --quiet --no-warn-script-location
echo [2/2] A iniciar o SmartCool Monitor...
py app.py
goto END

:NO_PYTHON
echo ======================================================
echo [AVISO] O Python ainda nao esta instalado no seu PC!
echo ======================================================
echo.
echo Para executar a sua aplicacao, precisa de ter o Python:
echo.
echo 1. O instalador oficial vai abrir no seu navegador.
echo 2. Execute o ficheiro descarregado.
echo 3. IMPORTANTE: No inicio da instalacao, marque a opcao:
echo    [X] Add python.exe to PATH
echo 4. Depois de instalar, basta voltar a abrir este ficheiro!
echo.
echo A abrir a pagina do Python no navegador...
start https://www.python.org/downloads/
echo.
pause
exit /b 1

:END
echo.
echo ======================================================
echo    SmartCool Monitor terminado.
echo ======================================================
pause

