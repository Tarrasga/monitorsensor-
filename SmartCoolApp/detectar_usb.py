"""
Diagnóstico e Deteção USB para Ecrã SmartCool (VID: 0x2A55, PID: 0x9990)
Verifica os endpoints e testa a comunicação nativa WinUSB/libusb.
"""

import sys

try:
    import libusb_package
    import usb.core
    import usb.util
except ImportError:
    print("[ERRO] Módulos pyusb ou libusb-package não instalados.")
    print("Execute via TESTAR_LIGACAO_USB.bat para instalar automaticamente.")
    sys.exit(1)

VID = 0x2A55
PID = 0x9990

print("=" * 60)
print(f" A PROCURAR ECRÃ SMARTCOOL (VID: 0x{VID:04X}, PID: 0x{PID:04X})...")
print("=" * 60)

dev = libusb_package.find(idVendor=VID, idProduct=PID)

if dev is None:
    print("[FALHA] O ecrã SmartCool (2A55:9990) não foi detetado pelo libusb.")
    print("\nLista de outros dispositivos USB detetados:")
    for d in libusb_package.find(find_all=True):
        print(f" - VID: 0x{d.idVendor:04X} | PID: 0x{d.idProduct:04X}")
    input("\nPressione ENTER para sair...")
    sys.exit(1)

print("\n[SUCESSO] Ecrã SmartCool DETETADO!")
print(f" Fabricante: {dev.manufacturer if dev.manufacturer else 'QTKeJi'}")
print(f" Produto:    {dev.product if dev.product else 'SmatCool'}")
print(f" Serial:     {dev.serial_number if dev.serial_number else 'N/A'}")

print("\n--- Estrutura de Endpoints do Ecrã ---")
for cfg in dev:
    print(f"Configuração {cfg.bConfigurationValue}:")
    for intf in cfg:
        print(f"  Interface #{intf.bInterfaceNumber} (Alt #{intf.bAlternateSetting}):")
        for ep in intf:
            direction = "OUT (Envio PC -> Ecrã)" if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT else "IN (Leitura Ecrã -> PC)"
            ep_type = ["Control", "Isochronous", "Bulk", "Interrupt"][ep.bmAttributes & 0x03]
            print(f"    -> Endpoint 0x{ep.bEndpointAddress:02X} | Tipo: {ep_type} | Direção: {direction} | Tamanho Max Pacote: {ep.wMaxPacketSize} bytes")

print("\n" + "=" * 60)
print("INFORMAÇÕES RECOLHIDAS COM SUCESSO!")
print("Copie ou tire uma foto desta janela para ativarmos o envio direto!")
print("=" * 60)
input("\nPressione ENTER para fechar...")
