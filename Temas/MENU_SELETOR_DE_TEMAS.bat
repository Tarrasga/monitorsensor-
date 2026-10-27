@echo off
title Menu Seletor de Temas // SmartCool USB
:MENU
cls
echo ================================================================
echo        SMARTCOOL // SELECAO DE TEMAS PARA O ECRA USB
echo ================================================================
echo.
echo   [1]  Mesa de Mistura DJ (Studio Audio Equalizer)
echo   [2]  Peugeot 508 SW (Digital i-Cockpit GT)
echo   [3]  Ford Fiesta XR2 Mk2 (Classic Hot Hatch)
echo   [4]  Counter-Strike 2 (CS2 Tactical HUD)
echo   [5]  PUBG Battlegrounds (Erangel Survival HUD)
echo   [6]  Velocimetros de Carro (Instrument Cluster)
echo   [7]  Cockpit de Carro GT (Racing Telemetry)
echo   [8]  Cockpit de Aviao (Fighter Jet HUD)
echo   [9]  Monster Energy (Com Latas)
echo   [10] Monster Energy (Claw / Garra)
echo   [11] ROG Dark Gaming (TARRASGA)
echo   [12] Master Telemetry (Todos os Sensores)
echo.
echo   [0]  Sair
echo ================================================================
set /p opcao="Escolha o numero do tema pretendido [0-12]: "

if "%opcao%"=="1" (call ENVIAR_TEMA_MESA_MISTURA.bat & goto MENU)
if "%opcao%"=="2" (call ENVIAR_TEMA_PEUGEOT_508.bat & goto MENU)
if "%opcao%"=="3" (call ENVIAR_TEMA_XR2.bat & goto MENU)
if "%opcao%"=="4" (call ENVIAR_TEMA_CS2.bat & goto MENU)
if "%opcao%"=="5" (call ENVIAR_TEMA_PUBG.bat & goto MENU)
if "%opcao%"=="6" (call ENVIAR_TEMA_VELOCIMETROS.bat & goto MENU)
if "%opcao%"=="7" (call ENVIAR_TEMA_COCKPIT_GT.bat & goto MENU)
if "%opcao%"=="8" (call ENVIAR_TEMA_AVIAO.bat & goto MENU)
if "%opcao%"=="9" (call ENVIAR_TEMA_MONSTER_LATAS.bat & goto MENU)
if "%opcao%"=="10" (call ENVIAR_TEMA_MONSTER_GARRA.bat & goto MENU)
if "%opcao%"=="11" (call ENVIAR_TEMA_ROG.bat & goto MENU)
if "%opcao%"=="12" (call ENVIAR_TEMA_SENSORES.bat & goto MENU)
if "%opcao%"=="0" exit
goto MENU
