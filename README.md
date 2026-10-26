# SmartCool Master Telemetry — Tarrasga Edition 🚀

Painel de telemetria de alto desempenho para monitorização de hardware (CPU, GPU, RAM, VRAM, NVMe) com suporte híbrido para:
1. **Ecrã Físico USB 3.5" IPS** (QTKeJi SmatCool `VID: 0x2A55, PID: 0x9990` via protocolo nativo SCSI-BOT).
2. **2º Ecrã / Monitor Secundário do PC** com expansão automática e exclusiva no monitor ativo (`F11`) e suporte a *Always on Top*.
3. **Transmissão Wi-Fi ao Vivo para Telemóvel e Tablet** com motor `NoSleep` e `Screen Wake Lock` para manter o ecrã sempre aceso 24/7.
4. **Aplicação Nativa Android** (`AndroidApp/`) com ecrã total imersivo e `FLAG_KEEP_SCREEN_ON`.

---

## 📸 Temas Incluídos
- **Monster Energy // Todos os Sensores (Master HUD)**:
  - CPU (Temp, Carga, Clock GHz, Consumo W)
  - GPU NVIDIA GeForce (Temp Core, Hotspot, Carga, VRAM 12GB, Consumo W, Ventoinhas RPM)
  - Memória RAM 32GB DDR5 e Armazenamento NVMe (C: & E:)
  - Cores dinâmicas que evoluem com a temperatura (Verde néon → Amarelo → Laranja → Vermelho alerta)
  - Animação de chamas quando o hardware atinge temperaturas elevadas (>75°C)
  - Logótipo tático das garras Monster Energy e assinatura Tarrasga
- **Monster Energy Cans 3D**:
  - Latas clássicas originais em 3D e efeito néon
- **ASUS ROG Tarrasga Edition**:
  - Estética futurista Republic of Gamers

---

## ⚡ Como Executar

### No Computador (Windows):
1. Dê duplo clique em:
   - **`INICIAR_APP_SMARTCOOL.bat`**: Inicia a aplicação completa com deteção do visor USB e painel de controlo.
   - **`INICIAR_SERVIDOR_WIFI_TELEMOVEL.bat`**: Inicia diretamente com o servidor Wi-Fi pronto para ligação mobile.

### No Telemóvel ou Tablet:
1. Ligue o telemóvel ao mesmo Wi-Fi de sua casa.
2. Na aplicação, clique em **`TELEMOVEL / TABLET (QR CODE)`**.
3. Aponte a câmara do telemóvel ao QR Code (ou abra o endereço indicado, ex: `http://192.168.1.65:8080`).
4. Clique em **`⛶ TELA CHEIA`**. O ecrã permanecerá ligado sem nunca desligar ou suspender.

### Como App Android Nativa:
Abra a pasta `AndroidApp` no **Android Studio** e faça *Build APK* para instalar diretamente no telemóvel Android.

---

## 🛠️ Tecnologias
- **Python 3.10+** (Tkinter, Pillow, PyUSB, libusb, psutil, GPUtil, python-wmi)
- **Web**: HTTP Server multi-thread, Web Wake Lock API, Canvas Double-Buffering
- **Android**: Java, Android SDK, WebView com KeepScreenOn permanente
- **Hardware**: USB SCSI Bulk-Only Transport (BOT) com blocos de transferência de alta velocidade RGB565 Big-Endian.

---

Desenvolvido por **Tarrasga** © 2026.
