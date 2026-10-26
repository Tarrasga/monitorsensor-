"""
Teste de Diagnóstico de Comunicação e Leitura de CSW (Endpoint 0x81)
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
    print("[ERRO] pyusb ou libusb-package não instalados.")
    sys.exit(1)

VID = 0x2A55
PID = 0x9990
EP_OUT = 0x01
EP_IN = 0x81

print("=" * 60)
print(" DIAGNOSTICO DETALHADO DO ESTADO USB")
print("=" * 60)

dev = libusb_package.find(idVendor=VID, idProduct=PID)
if dev is None:
    print("[ERRO] Ecrã não encontrado!")
    input("Pressione ENTER para sair...")
    sys.exit(1)

# 1. Tentar ler se havia algum pacote pendente no Endpoint 0x81 (ex: CSW)
print("\n[PASSO 1] A verificar se existe resposta pendente no canal 0x81...")
try:
    data_in = dev.read(EP_IN, 64, timeout=500)
    print(f" -> Resposta lida de 0x81 ({len(data_in)} bytes): {bytes(data_in)}")
    if len(data_in) >= 4 and bytes(data_in)[:4] == b"USBS":
        print(" -> Confirmado: O ecrã usa o protocolo SCSI/BOT (Assinatura USBS detetada)!")
except Exception as e:
    print(f" -> Canal 0x81 limpo ou timeout: {e}")

# 2. Fazer reset ao dispositivo para garantir estado limpo
print("\n[PASSO 2] A reiniciar ligação USB (dev.reset)...")
try:
    dev.reset()
    time.sleep(0.5)
    # Re-procurar após reset
    dev = libusb_package.find(idVendor=VID, idProduct=PID)
    dev.set_configuration()
    print(" -> Ecrã reinicializado com sucesso!")
except Exception as e:
    print(f" -> Aviso no reset: {e}")

# 3. Testar envio limpo do protocolo SCSI-CBW com leitura de CSW
print("\n[PASSO 3] A testar Envio com Ciclo Completo (CBW -> DADOS -> CSW)...")
WIDTH = 480
HEIGHT = 320

# Imagem de teste verde Monster
img = Image.new("RGB", (WIDTH, HEIGHT), "#39ff14")
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
cbw_cmd[11] = (WIDTH - 1) & 0xFF
cbw_cmd[12] = ((WIDTH - 1) >> 8) & 0xFF
cbw_cmd[13] = (HEIGHT - 1) & 0xFF
cbw_cmd[14] = ((HEIGHT - 1) >> 8) & 0xFF

cbw = cbw_header + bytes([16]) + bytes(cbw_cmd)

try:
    # 1. Enviar CBW
    dev.write(EP_OUT, cbw, timeout=1000)
    # 2. Enviar Dados em blocos de 512 bytes
    chunk_size = 512
    for i in range(0, len(rgb565_be), chunk_size):
        dev.write(EP_OUT, rgb565_be[i:i + chunk_size], timeout=1000)
    
    # 3. Ler CSW (13 bytes) do Endpoint 0x81
    csw = dev.read(EP_IN, 13, timeout=1000)
    print(f" -> CSW Recebido ({len(csw)} bytes): {bytes(csw)}")
    print(" -> SUCESSO ABSOLUTO! Ciclo SCSI concluído com sucesso!")
except Exception as e:
    print(f" -> Erro no teste SCSI: {e}")

print("\n" + "=" * 60)
print("TESTE TERMINADO.")
print("=" * 60)
input("\nPressione ENTER para fechar...")
