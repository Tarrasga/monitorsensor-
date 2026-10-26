"""
Envio Direto do Tema Monster Energy com Ciclo SCSI Validado
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

print("=" * 60)
print(" A CONECTAR AO ECRÃ SMARTCOOL USB...")
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
    # Limpar qualquer lixo
    dev.read(EP_IN, 64, timeout=100)
except Exception:
    pass

# Carregar o preview do Monster Energy com Latas
preview_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "monster_cans_preview.png")
if not os.path.exists(preview_path):
    preview_path = os.path.join(os.path.dirname(__file__), "assets", "monster_cans.png")

print(f"[INFO] A carregar imagem: {preview_path}")
img = Image.open(preview_path).convert("RGB")
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

print("[A ENVIAR] A desenhar o Tema Monster Energy no ecrã pequeno...")

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

# 1. Enviar CBW
dev.write(EP_OUT, cbw, timeout=1000)

# 2. Enviar Dados em blocos de 512 bytes
chunk_size = 512
for i in range(0, payload_len, chunk_size):
    dev.write(EP_OUT, rgb565_be[i:i + chunk_size], timeout=1000)

# 3. Ler confirmação CSW
csw = dev.read(EP_IN, 13, timeout=1000)
print(f" -> Confirmação recebida do ecrã: {bytes(csw)}")

print("\n" + "=" * 60)
print("[SUCESSO TOTAL!] O seu ecrã físico tem agora o tema Monster Energy!")
print("=" * 60)
input("\nPressione ENTER para fechar...")
