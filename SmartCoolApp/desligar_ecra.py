"""
Desliga o ecrã SmartCool USB (Modo repouso / ecrã preto) usando o protocolo SCSI/BOT validado.
"""

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
print(" A DESLIGAR ECRÃ SMARTCOOL USB (STANDBY / PRETO)...")
print("=" * 60)

dev = libusb_package.find(idVendor=VID, idProduct=PID)

if dev is None:
    print("[ERRO] Ecrã não encontrado!")
    sys.exit(1)

try:
    dev.set_configuration()
    dev.clear_halt(EP_OUT)
    dev.clear_halt(EP_IN)
    dev.read(EP_IN, 64, timeout=100)
except Exception:
    pass

# 1. Enviar frame preto de 480x320
WIDTH = 480
HEIGHT = 320
black_payload = bytes(WIDTH * HEIGHT * 2)  # Todos os pixels a 0x0000 (preto)
payload_len = len(black_payload)

tag = 0x99999999
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

try:
    # Enviar CBW
    dev.write(EP_OUT, cbw, timeout=1000)
    # Enviar frame preto em blocos de 512
    chunk_size = 512
    for i in range(0, payload_len, chunk_size):
        dev.write(EP_OUT, black_payload[i:i + chunk_size], timeout=1000)
    # Ler CSW
    dev.read(EP_IN, 13, timeout=1000)
    print("[SUCESSO] O ecrã foi colocado em modo repouso (ecrã preto).")
except Exception as e:
    print(f"[ERRO ao desligar]: {e}")

try:
    usb.util.dispose_resources(dev)
except Exception:
    pass

time.sleep(0.3)
