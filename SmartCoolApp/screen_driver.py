"""
SmartCool 3.5" (480x320) Screen Driver
Driver Nativo USB SCSI/BOT para QTKeJi SmatCool (VID: 0x2A55, PID: 0x9990).
Implementa o protocolo de envio completo: CBW (0xCD 0x06 0x12) -> RGB565 BE -> Leitura de CSW (0x81).
"""

import time
import struct
from PIL import Image

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import libusb_package
    import usb.core
    import usb.util
    HAS_PYUSB = True
except ImportError:
    HAS_PYUSB = False

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class SmartCoolDriver:
    WIDTH = 480
    HEIGHT = 320

    USB_VID = 0x2A55
    USB_PID = 0x9990
    EP_OUT = 0x01
    EP_IN = 0x81

    def __init__(self, port=None):
        self.port = port
        self.connection_type = None  # 'USB' ou 'SERIAL'
        self.usb_dev = None
        self.serial_conn = None
        self.is_connected = False
        self.tag_counter = 0x12345678
        self.consecutive_errors = 0

    @staticmethod
    def detect_devices():
        """Procura dispositivos compatíveis (USB Nativo e Portas COM)."""
        devices = []

        if HAS_PYUSB:
            try:
                usb_dev = libusb_package.find(idVendor=SmartCoolDriver.USB_VID, idProduct=SmartCoolDriver.USB_PID)
                if usb_dev is not None:
                    devices.append({
                        "id": "USB:2A55:9990",
                        "label": "Ecrã USB SmartCool (2A55:9990) [Nativo]",
                        "type": "USB"
                    })
            except Exception:
                pass

        if HAS_SERIAL:
            try:
                for p in serial.tools.list_ports.comports():
                    devices.append({
                        "id": p.device,
                        "label": f"Porta Série {p.device} ({p.description})",
                        "type": "SERIAL"
                    })
            except Exception:
                pass

        return devices

    def connect(self, target="AUTO"):
        """Liga ao ecrã por USB Nativo ou Porta Série."""
        if target == "AUTO" or target.startswith("USB"):
            if HAS_PYUSB:
                try:
                    self.usb_dev = libusb_package.find(idVendor=self.USB_VID, idProduct=self.USB_PID)
                    if self.usb_dev is not None:
                        try:
                            self.usb_dev.set_configuration()
                        except Exception:
                            pass

                        # Limpar qualquer pacote residual no canal de leitura 0x81
                        try:
                            self.usb_dev.clear_halt(self.EP_OUT)
                            self.usb_dev.clear_halt(self.EP_IN)
                            for _ in range(3):
                                try:
                                    self.usb_dev.read(self.EP_IN, 64, timeout=100)
                                except Exception:
                                    break
                        except Exception:
                            pass

                        self.connection_type = "USB"
                        self.is_connected = True
                        self.consecutive_errors = 0
                        return "USB:2A55:9990"
                except Exception as e:
                    print(f"[Driver] Falha na inicialização USB: {e}")

        # Fallback Porta Série
        if HAS_SERIAL and target != "USB:2A55:9990" and target != "AUTO":
            try:
                self.serial_conn = serial.Serial(port=target, baudrate=115200, timeout=1.0)
                time.sleep(0.1)
                self.connection_type = "SERIAL"
                self.is_connected = True
                return target
            except Exception as e:
                raise ConnectionError(f"Erro ao ligar à porta série {target}: {e}")

        if not self.is_connected:
            raise ConnectionError("Nenhum ecrã SmartCool USB detetado no sistema.")

    def disconnect(self, turn_off=True):
        """Desconecta do dispositivo e desliga o ecrã com moldura preta."""
        if self.is_connected and turn_off:
            try:
                # Enviar frame preto para repouso
                black_frame = Image.new("RGB", (self.WIDTH, self.HEIGHT), "#000000")
                self.display_image(black_frame)
                time.sleep(0.05)
            except Exception:
                pass

        if self.connection_type == "SERIAL" and self.serial_conn:
            try:
                self.serial_conn.close()
            except Exception:
                pass

        if self.connection_type == "USB" and self.usb_dev:
            try:
                usb.util.dispose_resources(self.usb_dev)
            except Exception:
                pass

        self.usb_dev = None
        self.serial_conn = None
        self.is_connected = False
        self.connection_type = None

    def set_brightness(self, percent):
        """Método de compatibilidade (desativado para prevenir colisões no barramento USB)."""
        return True

    def _convert_image_rgb565_be(self, image: Image.Image) -> bytes:
        """Converte imagem PIL para bytes RGB565 Big-Endian (exigido pelo SmatCool)."""
        if image.mode != "RGB":
            image = image.convert("RGB")

        if HAS_NUMPY:
            arr = np.array(image, dtype=np.uint16)
            r = (arr[:, :, 0] >> 3) & 0x1F
            g = (arr[:, :, 1] >> 2) & 0x3F
            b = (arr[:, :, 2] >> 3) & 0x1F
            rgb565 = (r << 11) | (g << 5) | b
            # Big Endian (byte alto primeiro)
            return rgb565.astype(">u2").tobytes()
        else:
            raw = image.tobytes()
            out = bytearray(len(raw) // 3 * 2)
            out_idx = 0
            for i in range(0, len(raw), 3):
                r = (raw[i] >> 3) & 0x1F
                g = (raw[i + 1] >> 2) & 0x3F
                b = (raw[i + 2] >> 3) & 0x1F
                val = (r << 11) | (g << 5) | b
                out[out_idx] = (val >> 8) & 0xFF
                out[out_idx + 1] = val & 0xFF
                out_idx += 2
            return bytes(out)

    def display_image(self, image: Image.Image, x0=0, y0=0):
        """
        Envia imagem completa para o ecrã usando o protocolo SCSI-BOT validado:
        1. Envia CBW (31 bytes com comando 0xCD 0x06 0x12)
        2. Envia Payload em RGB565 BE (blocos de 512 bytes)
        3. Lê CSW (13 bytes no canal 0x81) para fechar o ciclo
        """
        if not self.is_connected or not self.usb_dev:
            return False

        w, h = image.size
        x1 = x0 + w
        y1 = y0 + h

        payload = self._convert_image_rgb565_be(image)
        payload_len = len(payload)

        self.tag_counter = (self.tag_counter + 1) & 0xFFFFFFFF

        # 1. Estrutura do Command Block Wrapper (CBW - 31 bytes)
        cbw_header = struct.pack("<4sIIBB", b"USBC", self.tag_counter, payload_len, 0x00, 0)
        cbw_cmd = bytearray(16)
        cbw_cmd[0] = 0xCD
        cbw_cmd[5] = 0x06
        cbw_cmd[6] = 0x12  # Blit (Desenho de imagem)
        cbw_cmd[7] = x0 & 0xFF
        cbw_cmd[8] = (x0 >> 8) & 0xFF
        cbw_cmd[9] = y0 & 0xFF
        cbw_cmd[10] = (y0 >> 8) & 0xFF
        cbw_cmd[11] = (x1 - 1) & 0xFF
        cbw_cmd[12] = ((x1 - 1) >> 8) & 0xFF
        cbw_cmd[13] = (y1 - 1) & 0xFF
        cbw_cmd[14] = ((y1 - 1) >> 8) & 0xFF

        cbw = cbw_header + bytes([16]) + bytes(cbw_cmd)

        try:
            # 1. Enviar CBW para o Endpoint 0x01
            self.usb_dev.write(self.EP_OUT, cbw, timeout=2000)

            # 2. Enviar dados (payload RGB565 em blocos de 512 bytes para garantir estabilidade)
            chunk_size = 512
            for i in range(0, len(payload), chunk_size):
                self.usb_dev.write(self.EP_OUT, payload[i:i + chunk_size], timeout=2000)

            # 3. Ler o CSW (13 bytes) do Endpoint 0x81 (timeout de 3000ms para dar tempo ao LCD blit)
            self.usb_dev.read(self.EP_IN, 13, timeout=3000)

            self.consecutive_errors = 0
            return True

        except Exception as e:
            self.consecutive_errors += 1
            if self.consecutive_errors <= 2:
                print(f"[Driver] Aviso no ciclo de envio: {e}")

            # Limpar stalls / halts no canal USB
            try:
                self.usb_dev.clear_halt(self.EP_OUT)
                self.usb_dev.clear_halt(self.EP_IN)
                for _ in range(3):
                    try:
                        self.usb_dev.read(self.EP_IN, 64, timeout=100)
                    except Exception:
                        break
            except Exception:
                pass

            # Se houver 3 ou mais erros consecutivos (ex: timeout seguido de pipe ou I/O error),
            # o canal USB perdeu sincronismo ou o cabo foi movido.
            # Executa auto-recuperação limpa sem inundar o terminal.
            if self.consecutive_errors >= 3:
                if self.consecutive_errors == 3:
                    print("[Driver] Canal USB instável. A restabelecer ligação...")
                try:
                    usb.util.dispose_resources(self.usb_dev)
                except Exception:
                    pass
                self.usb_dev = None
                self.is_connected = False

                # Auto-recuperação imediata
                try:
                    time.sleep(0.3)
                    if self.connect("AUTO"):
                        self.consecutive_errors = 0
                        print("[Driver] Comunicação USB restabelecida com sucesso!")
                except Exception:
                    pass

            return False
