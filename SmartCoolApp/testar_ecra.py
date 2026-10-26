"""
Teste de Transmissão Direta para Ecrã SmartCool (VID: 0x2A55, PID: 0x9990)
Testa os protocolos USB conhecidos no Endpoint 0x01.
"""

import sys
import time
import struct
from PIL import Image, ImageDraw

try:
    import libusb_package
    import usb.core
    import usb.util
except ImportError:
    print("[ERRO] pyusb ou libusb-package não instalados.")
    sys.exit(1)

VID = 0x2A55
PID = 0x9990
EP_OUT = 0x01
EP_IN = 0x81

print("=" * 60)
print(f" A LIGAR AO ECRÃ SMARTCOOL (0x{VID:04X}:0x{PID:04X})...")
print("=" * 60)

dev = libusb_package.find(idVendor=VID, idProduct=PID)
if dev is None:
    print("[ERRO] Ecrã não encontrado!")
    input("Pressione ENTER para sair...")
    sys.exit(1)

# Desanexar driver kernel se necessário e definir configuração
try:
    dev.set_configuration()
    print("[OK] Configuração USB 1 ativada com sucesso.")
except Exception as e:
    print(f"[AVISO] set_configuration: {e}")

# Criar uma imagem de teste sólida (Vermelho ROG com texto branco)
WIDTH = 480
HEIGHT = 320
img = Image.new("RGB", (WIDTH, HEIGHT), "#e60026")
draw = ImageDraw.Draw(img)
draw.rectangle([20, 20, 460, 300], fill="#111317", outline="#ffffff", width=3)
draw.text((120, 140), "TARRASGA // SMARTCOOL", fill="#ff3344")

# Converter para RGB565 Little-Endian e Big-Endian
raw = img.tobytes()
rgb565_le = bytearray()
rgb565_be = bytearray()

for i in range(0, len(raw), 3):
    r = (raw[i] >> 3) & 0x1F
    g = (raw[i+1] >> 2) & 0x3F
    b = (raw[i+2] >> 3) & 0x1F
    val = (r << 11) | (g << 5) | b
    # Little-Endian
    rgb565_le.append(val & 0xFF)
    rgb565_le.append((val >> 8) & 0xFF)
    # Big-Endian
    rgb565_be.append((val >> 8) & 0xFF)
    rgb565_be.append(val & 0xFF)

print("\n[TESTE 1/2] A testar Protocolo Nativo SmartCool (Turing Direct)...")
try:
    # 1. Comandos de ativação
    dev.write(EP_OUT, bytes([109]), timeout=1000) # Screen ON
    time.sleep(0.05)
    dev.write(EP_OUT, bytes([110, 80]), timeout=1000) # Brightness 80%
    time.sleep(0.05)
    dev.write(EP_OUT, bytes([121, 2]), timeout=1000) # Landscape
    time.sleep(0.05)

    # 2. Comando Bitmap (197)
    header = bytes([
        197,
        0, 0, 0, 0,
        ((WIDTH - 1) >> 8) & 0xFF, (WIDTH - 1) & 0xFF,
        ((HEIGHT - 1) >> 8) & 0xFF, (HEIGHT - 1) & 0xFF
    ])
    dev.write(EP_OUT, header, timeout=1000)

    # Enviar payload em blocos de 64 bytes
    chunk_size = 64
    for i in range(0, len(rgb565_le), chunk_size):
        dev.write(EP_OUT, rgb565_le[i:i + chunk_size], timeout=1000)

    print("[SUCESSO NO ENVIO!] Verifique se o ecrã físico acendeu com o teste vermelho.")
except Exception as e:
    print(f"[TESTE 1 FALHOU]: {e}")

print("\n[TESTE 2/2] A testar Protocolo SCSI-CBW (Buildwin/AX206)...")
try:
    payload_len = len(rgb565_be)
    # CBW 31 bytes
    tag = 0x12345678
    cbw_header = struct.pack("<4sIIBB", b"USBC", tag, payload_len, 0x00, 0)
    # 16 bytes SCSI Command Block: 0xCD, 0, 0, 0, 0, 0x06, 0x12, x0, y0, x1, y1
    cbw_cmd = bytearray(16)
    cbw_cmd[0] = 0xCD
    cbw_cmd[5] = 0x06
    cbw_cmd[6] = 0x12
    cbw_cmd[7] = 0   # x0 low
    cbw_cmd[8] = 0   # x0 high
    cbw_cmd[9] = 0   # y0 low
    cbw_cmd[10] = 0  # y0 high
    cbw_cmd[11] = (WIDTH - 1) & 0xFF
    cbw_cmd[12] = ((WIDTH - 1) >> 8) & 0xFF
    cbw_cmd[13] = (HEIGHT - 1) & 0xFF
    cbw_cmd[14] = ((HEIGHT - 1) >> 8) & 0xFF

    cbw = cbw_header + bytes([16]) + bytes(cbw_cmd)
    dev.write(EP_OUT, cbw, timeout=1000)

    for i in range(0, len(rgb565_be), chunk_size):
        dev.write(EP_OUT, rgb565_be[i:i + chunk_size], timeout=1000)

    print("[SUCESSO NO ENVIO SCSI-CBW!] Verifique se o ecrã físico reagiu.")
except Exception as e:
    print(f"[TESTE 2 FALHOU]: {e}")

print("\n" + "=" * 60)
print("TESTES CONCLUÍDOS!")
print("=" * 60)
input("\nPressione ENTER para fechar...")
