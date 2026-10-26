@echo off
title Desbloquear Acesso Wi-Fi no Firewall do Windows
cd /d "%~dp0"

echo ======================================================================
echo    DESBLOQUEAR ACESSO DO TELEMOVEL / TABLET NO FIREWALL DO WINDOWS
echo ======================================================================
echo.

:: Verificar se tem permissoes de Administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] A solicitar autorizacao de Administrador do Windows...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo A abrir a porta 8080 no Windows Defender Firewall...
netsh advfirewall firewall delete rule name="SmartCool Web Server" >nul 2>&1
netsh advfirewall firewall add rule name="SmartCool Web Server" dir=in action=allow protocol=TCP localport=8080

echo.
echo ======================================================================
echo  [SUCESSO TOTAL!] 
echo  A porta 8080 foi autorizada no Firewall do Windows.
echo.
echo  Agora:
echo  1. Confirma que o teu telemovel esta ligado ao mesmo Wi-Fi de casa.
echo  2. Abre a app no PC: INICIAR_SERVIDOR_WIFI_TELEMOVEL.bat
echo  3. Aponta a camara do telemovel para o QR Code (ou abre http://192.168.1.65:8080).
echo ======================================================================
echo.
pause
