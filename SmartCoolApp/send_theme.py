"""
Script utilitário para envio direto de imagem ou tema para o ecrã SmartCool USB.
Uso: python send_theme.py [monster_cans | monster_claw | rog | caminho_da_imagem]
"""

import os
import sys
import time
import struct
from PIL import Image

try:
    import libusb_package
    import usb.core
    import usb.util
except ImportError:
    print("[ERRO] pyusb não instalado.")
    sys.exit(1)

VID = 0x2A55
PID = 0x9990
EP_OUT = 0x01
EP_IN = 0x81

target = sys.argv[1] if len(sys.argv) > 1 else "monster_cans"
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

image_path = None
if target in ("sensors", "sensores", "master"):
    image_path = os.path.join(assets_dir, "master_telemetry_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "master_sensors_preview.png")
elif target in ("monster_gif", "gif", "animado"):
    image_path = os.path.join(assets_dir, "monster_cans_animated.gif")
elif target in ("monster_cans", "cans"):
    image_path = os.path.join(assets_dir, "monster_cans.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "monster_cans_480x320.png")
elif target in ("monster_claw", "claw"):
    image_path = os.path.join(assets_dir, "monster_claw.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "monster_claw_480x320.png")
elif target in ("rog", "tarrasga"):
    image_path = os.path.join(assets_dir, "background.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "tarrasga_rog_480x320.png")
elif target in ("speedometer", "velocimetros", "dials"):
    image_path = os.path.join(assets_dir, "preview_theme_speedometer.png")
elif target in ("airplane", "aviao", "hud", "cockpit_aviao"):
    image_path = os.path.join(assets_dir, "preview_theme_airplane.png")
elif target in ("gt", "cockpit_gt", "racing", "carro"):
    image_path = os.path.join(assets_dir, "preview_theme_gt.png")
elif target in ("xr2", "fiesta", "ford", "hot_hatch"):
    image_path = os.path.join(assets_dir, "preview_theme_xr2_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "preview_theme_xr2.png")
elif target in ("cs2", "counterstrike", "counter-strike"):
    image_path = os.path.join(assets_dir, "preview_theme_cs2_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "preview_theme_cs2.png")
elif target in ("pubg", "battlegrounds", "erangel"):
    image_path = os.path.join(assets_dir, "preview_theme_pubg_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "preview_theme_pubg.png")
elif target in ("508", "peugeot", "peugeot508", "508sw", "icockpit"):
    image_path = os.path.join(assets_dir, "preview_theme_peugeot_508_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "preview_theme_peugeot_508.png")
elif target in ("mixer", "dj", "mesa", "equalizer", "eq", "musica", "audio", "studio"):
    image_path = os.path.join(assets_dir, "preview_theme_mixer_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "preview_theme_mixer.png")
elif target in ("transparente", "transparent", "glass", "overlay", "glass_hud", "hud_transparente"):
    image_path = os.path.join(assets_dir, "preview_theme_transparent_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "preview_theme_transparent.png")
elif target in ("neon_dual", "neon", "dual_neon", "azul_vermelho", "fans", "cyber_neon"):
    image_path = os.path.join(assets_dir, "preview_theme_neon_dual_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "preview_theme_neon_dual.png")
elif target in ("monster_official", "official", "logo", "monster_telemetria", "edicao_oficial", "logo_oficial"):
    image_path = os.path.join(assets_dir, "preview_theme_monster_official_usb.png")
    if not os.path.exists(image_path):
        image_path = os.path.join(assets_dir, "preview_theme_monster_official.png")
else:
    image_path = target

if not os.path.exists(image_path):
    print(f"[ERRO] Imagem não encontrada: {image_path}")
    sys.exit(1)

print("=" * 60)
print(f" A ENVIAR IMAGEM PARA O ECRÃ USB: {os.path.basename(image_path)}")
print("=" * 60)

dev = libusb_package.find(idVendor=VID, idProduct=PID)
if dev is None:
    print("[ERRO] Ecrã não encontrado!")
    sys.exit(1)

# 1. Drenar qualquer pacote ou confirmação CSW pendente de transmissões anteriores
for _ in range(5):
    try:
        dev.read(EP_IN, 64, timeout=100)
    except Exception:
        break

try:
    dev.clear_halt(EP_OUT)
except Exception:
    pass

try:
    dev.clear_halt(EP_IN)
except Exception:
    pass

# 2. Executar reset de barramento suave se necessário para garantir sincronismo
try:
    dev.reset()
    time.sleep(0.5)
    dev = libusb_package.find(idVendor=VID, idProduct=PID)
except Exception:
    pass

try:
    dev.set_configuration()
except Exception:
    pass

try:
    dev.clear_halt(EP_OUT)
    dev.clear_halt(EP_IN)
except Exception:
    pass

img = Image.open(image_path).convert("RGB")
if img.size != (480, 320):
    img = img.resize((480, 320), Image.Resampling.LANCZOS)

raw = img.tobytes()
rgb565_be = bytearray()
for i in range(0, len(raw), 3):
    r = (raw[i] >> 3) & 0x1F
    g = (raw[i+1] >> 2) & 0x3F
    b = (raw[i+2] >> 3) & 0x1F
    val = (r << 11) | (g << 5) | b
    rgb565_be.append((val >> 8) & 0xFF)
    rgb565_be.append(val & 0xFF)

payload_len = len(rgb565_be)
tag = 0x12345678
cbw_header = struct.pack("<4sIIBB", b"USBC", tag, payload_len, 0x00, 0)
cbw_cmd = bytearray(16)
cbw_cmd[0] = 0xCD
cbw_cmd[5] = 0x06
cbw_cmd[6] = 0x12
cbw_cmd[7] = 0
cbw_cmd[8] = 0
cbw_cmd[9] = 0
cbw_cmd[10] = 0
cbw_cmd[11] = (480 - 1) & 0xFF
cbw_cmd[12] = ((480 - 1) >> 8) & 0xFF
cbw_cmd[13] = (320 - 1) & 0xFF
cbw_cmd[14] = ((320 - 1) >> 8) & 0xFF

cbw = cbw_header + bytes([16]) + bytes(cbw_cmd)

# 3. Envio seguro por blocos com confirmação CSW
success = False
for attempt in range(2):
    try:
        # Enviar CBW
        dev.write(EP_OUT, cbw, timeout=2000)

        # Enviar RGB565 em blocos de 512 bytes para garantir compatibilidade com o buffer do controlador
        chunk_size = 512
        for i in range(0, len(rgb565_be), chunk_size):
            dev.write(EP_OUT, rgb565_be[i:i + chunk_size], timeout=2000)

        # Ler confirmação CSW (13 bytes) do Endpoint 0x81
        csw = dev.read(EP_IN, 13, timeout=3000)
        print(f" -> CSW Confirmado ({len(csw)} bytes): {bytes(csw)}")
        success = True
        break
    except Exception as e:
        if attempt == 0:
            print(f" -> A recuperar de timeout anterior ({e})... a tentar novamente...")
            try:
                dev.clear_halt(EP_OUT)
                dev.clear_halt(EP_IN)
                dev.read(EP_IN, 64, timeout=200)
            except Exception:
                pass
            time.sleep(0.3)
        else:
            print(f"[ERRO]: Falha na comunicação USB: {e}")

try:
    usb.util.dispose_resources(dev)
except Exception:
    pass

if success:
    print("\n" + "=" * 60)
    print("[SUCESSO TOTAL!] O ecrã físico foi atualizado com sucesso!")
    print("=" * 60)
else:
    sys.exit(1)
