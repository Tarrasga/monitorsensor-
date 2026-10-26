"""
Teste Rápido de Reprodução de GIF Animado no Ecrã SmartCool USB.
Utiliza envio otimizado de buffer único e sincronização com o hardware do ecrã.
"""

import os
import sys
import time
import struct
from PIL import Image, ImageSequence

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

print("=" * 60)
print(" TESTE DE ANIMAÇÃO 3D NO ECRÃ SMARTCOOL")
print("=" * 60)

dev = libusb_package.find(idVendor=VID, idProduct=PID)
if dev is None:
    print("[ERRO] Ecrã não encontrado!")
    input("Pressione ENTER para sair...")
    sys.exit(1)

try:
    dev.set_configuration()
    dev.clear_halt(EP_OUT)
    dev.clear_halt(EP_IN)
    dev.read(EP_IN, 64, timeout=100)
except Exception:
    pass

gif_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "monster_cans_animated.gif")
if not os.path.exists(gif_path):
    print(f"[ERRO] GIF não encontrado em {gif_path}")
    sys.exit(1)

print(f"[1/3] A carregar frames do GIF: {os.path.basename(gif_path)}...")
gif = Image.open(gif_path)
frames_payload = []

WIDTH = 480
HEIGHT = 320

# Carregar frames intercalados para rotação suave e ágil
for frame_idx, frame in enumerate(ImageSequence.Iterator(gif)):
    img = frame.convert("RGB")
    if img.size != (WIDTH, HEIGHT):
        img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    
    raw = img.tobytes()
    rgb565_be = bytearray()
    for i in range(0, len(raw), 3):
        r = (raw[i] >> 3) & 0x1F
        g = (raw[i+1] >> 2) & 0x3F
        b = (raw[i+2] >> 3) & 0x1F
        val = (r << 11) | (g << 5) | b
        rgb565_be.append((val >> 8) & 0xFF)
        rgb565_be.append(val & 0xFF)
    frames_payload.append(bytes(rgb565_be))

print(f" -> {len(frames_payload)} frames prontos na memória.")

payload_len = len(frames_payload[0])
tag = 0x77777777

cbw_header = struct.pack("<4sIIBB", b"USBC", tag, payload_len, 0x00, 0)
cbw_cmd = bytearray(16)
cbw_cmd[0] = 0xCD
cbw_cmd[5] = 0x06
cbw_cmd[6] = 0x12
cbw_cmd[7] = 0
cbw_cmd[8] = 0
cbw_cmd[9] = 0
cbw_cmd[10] = 0
cbw_cmd[11] = (WIDTH - 1) & 0xFF
cbw_cmd[12] = ((WIDTH - 1) >> 8) & 0xFF
cbw_cmd[13] = (HEIGHT - 1) & 0xFF
cbw_cmd[14] = ((HEIGHT - 1) >> 8) & 0xFF
cbw = cbw_header + bytes([16]) + bytes(cbw_cmd)

print("\n[2/3] A reproduzir a rotação das latas 3D no ecrã...")

# Reproduzir 12 frames selecionados (1 volta completa a 360 graus)
selected_frames = frames_payload[::2]  # Salta de 2 em 2 para rotação dinâmica
for idx, payload in enumerate(selected_frames):
    print(f" -> A desenhar frame {idx + 1} de {len(selected_frames)}...")
    dev.write(EP_OUT, cbw, timeout=1000)
    dev.write(EP_OUT, payload, timeout=2000)
    dev.read(EP_IN, 13, timeout=1000)

print("\n" + "=" * 60)
print("[SUCESSO!] Animacao 3D concluida no ecra fisico!")
print("=" * 60)

try:
    usb.util.dispose_resources(dev)
except Exception:
    pass
