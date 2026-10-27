import os
import shutil

root_dir = os.path.dirname(os.path.abspath(__file__))
temas_dir = os.path.join(root_dir, "Temas")
previews_dir = os.path.join(temas_dir, "Previsualizacoes")

os.makedirs(temas_dir, exist_ok=True)
os.makedirs(previews_dir, exist_ok=True)

# 1. Mover imagens soltas de previsualizacao da raiz para Temas/Previsualizacoes
root_preview_files = [
    "fiesta_xr2_preview_hd.png",
    "fiesta_xr2_preview_usb.png",
    "master_sensors_preview.png",
    "master_telemetry_hd.png",
    "monster_cans_480x320.png",
    "monster_cans_animated.gif",
    "monster_cans_preview.png",
    "monster_claw_480x320.png",
    "monster_claw_preview.png",
    "preview_flames_hot.png",
    "preview_hd_test.png",
    "preview_theme_cs2.png",
    "preview_theme_mixer.png",
    "preview_theme_mixer_usb.png",
    "preview_theme_peugeot_508.png",
    "preview_theme_peugeot_508_usb.png",
    "preview_theme_pubg.png",
    "tarrasga_rog_480x320.png",
    "tarrasga_rog_preview.png",
    "qrcode_wifi_telemovel.png",
    "visualizador.html"
]

for fname in root_preview_files:
    fpath = os.path.join(root_dir, fname)
    if os.path.exists(fpath):
        dest = os.path.join(previews_dir, fname)
        shutil.move(fpath, dest)
        print(f"[MOVIDO] {fname} -> Temas/Previsualizacoes/")

# 2. Catalogo de temas para gerar os ficheiros .bat dentro da pasta Temas
themes_catalog = [
    ("Mesa de Mistura DJ (Studio Audio Equalizer)", "mixer", "ENVIAR_TEMA_MESA_MISTURA.bat"),
    ("Peugeot 508 SW (Digital i-Cockpit GT)", "508", "ENVIAR_TEMA_PEUGEOT_508.bat"),
    ("Ford Fiesta XR2 Mk2 (Classic Hot Hatch)", "xr2", "ENVIAR_TEMA_XR2.bat"),
    ("Counter-Strike 2 (CS2 Tactical HUD)", "cs2", "ENVIAR_TEMA_CS2.bat"),
    ("PUBG Battlegrounds (Erangel Survival HUD)", "pubg", "ENVIAR_TEMA_PUBG.bat"),
    ("Velocímetros de Carro (Instrument Cluster)", "speedometer", "ENVIAR_TEMA_VELOCIMETROS.bat"),
    ("Cockpit de Carro GT (Racing Telemetry)", "gt", "ENVIAR_TEMA_COCKPIT_GT.bat"),
    ("Cockpit de Avião (Fighter Jet HUD)", "airplane", "ENVIAR_TEMA_AVIAO.bat"),
    ("Monster Energy (Com Latas)", "monster_cans", "ENVIAR_TEMA_MONSTER_LATAS.bat"),
    ("Monster Energy (Claw / Garra)", "monster_claw", "ENVIAR_TEMA_MONSTER_GARRA.bat"),
    ("ROG Dark Gaming (TARRASGA)", "rog", "ENVIAR_TEMA_ROG.bat"),
    ("Master Telemetry (Todos os Sensores)", "sensors", "ENVIAR_TEMA_SENSORES.bat"),
]

for title_desc, alias, bat_name in themes_catalog:
    bat_path = os.path.join(temas_dir, bat_name)
    bat_content = f'''@echo off
title Enviar {title_desc} para o Ecra USB
cd /d "%~dp0..\\SmartCoolApp"

echo ======================================================
echo    A ENVIAR {title_desc.upper()}
echo ======================================================
echo.

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"CommandLine like '%%app.py%%'\\" | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}" >nul 2>&1

python send_theme.py {alias}
pause
'''
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"[CRIADO] Temas/{bat_name}")

# 3. Mover GERAR_GIF_LATAS_3D.bat se existir
old_gif_bat = os.path.join(root_dir, "GERAR_GIF_LATAS_3D.bat")
if os.path.exists(old_gif_bat):
    shutil.move(old_gif_bat, os.path.join(temas_dir, "GERAR_GIF_LATAS_3D.bat"))
    print("[MOVIDO] GERAR_GIF_LATAS_3D.bat -> Temas/")

# 4. Criar Menu Mestre Interativo em Temas/MENU_SELETOR_DE_TEMAS.bat
menu_bat_path = os.path.join(temas_dir, "MENU_SELETOR_DE_TEMAS.bat")
menu_content = '''@echo off
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
'''
with open(menu_bat_path, "w", encoding="utf-8") as f:
    f.write(menu_content)
print("[CRIADO] Temas/MENU_SELETOR_DE_TEMAS.bat")

# Criar atalho direto do menu na raiz para conveniência: ESCOLHER_TEMA_ECRA.bat
root_selector = os.path.join(root_dir, "ESCOLHER_TEMA_ECRA.bat")
root_selector_content = '''@echo off
cd /d "%~dp0Temas"
call MENU_SELETOR_DE_TEMAS.bat
'''
with open(root_selector, "w", encoding="utf-8") as f:
    f.write(root_selector_content)
print("[CRIADO] ESCOLHER_TEMA_ECRA.bat (na raiz)")

# 5. Remover ficheiros .bat antigos de temas da raiz (agora estão todos em Temas/)
old_bats = [
    "ENVIAR_TEMA_AVIAO_ECRA.bat",
    "ENVIAR_TEMA_COCKPIT_GT_ECRA.bat",
    "ENVIAR_TEMA_CS2_ECRA.bat",
    "ENVIAR_TEMA_MESA_MISTURA_ECRA.bat",
    "ENVIAR_TEMA_MONSTER_ECRA.bat",
    "ENVIAR_TEMA_PEUGEOT_508_ECRA.bat",
    "ENVIAR_TEMA_PUBG_ECRA.bat",
    "ENVIAR_TEMA_ROG_ECRA.bat",
    "ENVIAR_TEMA_SENSORES_ECRA.bat",
    "ENVIAR_TEMA_VELOCIMETROS_ECRA.bat",
    "ENVIAR_TEMA_XR2_ECRA.bat",
]

for b in old_bats:
    bp = os.path.join(root_dir, b)
    if os.path.exists(bp):
        os.remove(bp)
        print(f"[LIMPO DA RAIZ] {b}")

print("\n[CONCLUIDO COM SUCESSO] Todos os temas foram arrumados na pasta 'Temas/'!")
