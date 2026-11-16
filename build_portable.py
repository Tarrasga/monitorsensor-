"""
Script de Compilação do Monster Telemetria em Pacote Portátil Standalone
Gera uma versão 100% autónoma que funciona em qualquer computador Windows
SEM NECESSIDADE DE TER O PYTHON INSTALADO!
"""

import os
import sys
import shutil
import zipfile
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "SmartCoolApp")
ASSETS_DIR = os.path.join(APP_DIR, "assets")
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
OUTPUT_NAME = "MonsterTelemetria_Portable"
OUTPUT_DIR = os.path.join(DIST_DIR, OUTPUT_NAME)
ZIP_OUTPUT = os.path.join(BASE_DIR, f"{OUTPUT_NAME}.zip")

print("=" * 60)
print("   COMPILADOR MONSTER TELEMETRIA // STANDALONE SEM PYTHON")
print("=" * 60)
print(f"Diretoria base: {BASE_DIR}")
print(f"Versao Python atual: {sys.version}")

# 1. Limpar pastas anteriores se existirem
if os.path.exists(DIST_DIR):
    try:
        shutil.rmtree(DIST_DIR)
    except Exception as e:
        print(f"[Aviso] Nao foi possivel limpar {DIST_DIR}: {e}")

if os.path.exists(BUILD_DIR):
    try:
        shutil.rmtree(BUILD_DIR)
    except Exception as e:
        print(f"[Aviso] Nao foi possivel limpar {BUILD_DIR}: {e}")

# 2. Comando PyInstaller
ico_path = os.path.join(ASSETS_DIR, "monster_telemetria_icon.ico")
cmd = [
    sys.executable, "-m", "PyInstaller",
    os.path.join(APP_DIR, "app.py"),
    f"--name={OUTPUT_NAME}",
    "--noconsole",
    "--onedir",
    f"--icon={ico_path}",
    f"--add-data={ASSETS_DIR};assets",
    "--collect-all=libusb_package",
    "--hidden-import=PIL",
    "--hidden-import=PIL.Image",
    "--hidden-import=PIL.ImageDraw",
    "--hidden-import=PIL.ImageFont",
    "--hidden-import=PIL.ImageTk",
    "--hidden-import=psutil",
    "--hidden-import=serial",
    "--hidden-import=usb",
    "--hidden-import=numpy",
    "--hidden-import=qrcode",
    "--hidden-import=wmi",
    "--hidden-import=winreg",
    "--noconfirm",
    "--clean"
]

print("\n[1/3] A compilar executavel nativo com PyInstaller...")
res = subprocess.run(cmd, cwd=BASE_DIR)

if res.returncode != 0:
    print(f"\n[ERRO] PyInstaller falhou com codigo {res.returncode}")
    sys.exit(1)

print("\n[2/3] A preparar estrutura do pacote portatil...")
# Copiar widgets_config.json e config.json predefinidos para a pasta de saida
target_app_dir = OUTPUT_DIR
if os.path.exists(target_app_dir):
    default_cfg = os.path.join(APP_DIR, "widgets_config.json")
    if os.path.exists(default_cfg):
        shutil.copy2(default_cfg, os.path.join(target_app_dir, "widgets_config.json"))

    # Criar um ficheiro LEIA-ME simples para o colega
    readme_txt = """===============================================================
 MONSTER TELEMETRIA // EDICAO PORTATIL AUTONOMA (STANDALONE)
===============================================================

Esta versao e 100% autonoma e funciona em qualquer computador com Windows 10 ou 11!
NAO PRECISA DE INSTALAR O PYTHON NEM QUALQUER OUTRO PROGRAMA.

COMO USAR:
1. De duplo clique no ficheiro "MonsterTelemetria_Portable.exe".
2. A aplicacao arranca logo com a interface grafica e os mostradores de telemetria!

CARACTERISTICAS:
- Deteta automaticamente o teu processador (Intel ou AMD)
- Deteta a tua placa grafica (NVIDIA, AMD ou Intel)
- Deteta a memoria RAM e discos do teu PC
- Modo de Manometros Circulares ("So Argolas") para 2o ecra
- Servidor Wi-Fi com QR Code para usar o telemovel como ecrã de telemetria

Desenvolvido por Tarrasga.
"""
    with open(os.path.join(target_app_dir, "COMO_USAR.txt"), "w", encoding="utf-8") as f:
        f.write(readme_txt)

    # 3. Criar arquivo ZIP pronto para envio
    print(f"\n[3/3] A compactar arquivo ZIP final: {ZIP_OUTPUT}...")
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(target_app_dir):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file, os.path.dirname(target_app_dir))
                zipf.write(abs_file, rel_path)

    zip_size_mb = round(os.path.getsize(ZIP_OUTPUT) / (1024 * 1024), 1)
    print("\n" + "=" * 60)
    print(" SUCESSO ABSOLUTO!")
    print(f" Pasta Portatil: {target_app_dir}")
    print(f" Ficheiro ZIP pronto para enviar: {ZIP_OUTPUT} ({zip_size_mb} MB)")
    print(" O teu colega so precisa de descompactar o ZIP e abrir o .exe!")
    print("=" * 60)
else:
    print(f"[ERRO] Pasta de saida nao encontrada: {target_app_dir}")
    sys.exit(1)
