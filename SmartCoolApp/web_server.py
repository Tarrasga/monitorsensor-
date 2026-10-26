"""
Servidor Web Wi-Fi Multi-Thread para o SmartCool Monitor / Master Telemetry
Permite transmitir o painel de telemetria em tempo real para qualquer telemóvel,
tablet (iPad, Android) ou outro computador na mesma rede Wi-Fi, sem necessidade de instalar apps.
Inclui motor NoSleep (Keep-Screen-On) e PWA instalável como App Nativa no Android.
Trata silenciosamente desconexões de telemóveis (WinError 10054 / BrokenPipe) sem poluir a consola.
"""

import os
import io
import sys
import time
import json
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from PIL import Image, ImageDraw
import qrcode


def get_local_ip():
    """Deteta automaticamente o endereço IPv4 local do PC na rede Wi-Fi / Ethernet."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


HTML_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#07090e">
    <title>SmartCool // Master Telemetry</title>
    <link rel="manifest" href="/manifest.json">
    <link rel="icon" type="image/png" href="/icon.png">
    <link rel="apple-touch-icon" href="/icon.png">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            user-select: none;
            -webkit-user-select: none;
        }
        body, html {
            width: 100%;
            height: 100%;
            background-color: #07090e;
            overflow: hidden;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        #stream-container {
            position: relative;
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background: #07090e;
        }
        #dashboard-stream {
            max-width: 100vw;
            max-height: 100vh;
            width: 100%;
            height: auto;
            object-fit: contain;
            display: block;
        }
        #rotate-tip {
            display: none;
            position: absolute;
            bottom: 64px;
            background: rgba(18, 23, 34, 0.9);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.4);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            pointer-events: none;
            z-index: 98;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.9; }
            50% { transform: scale(1.04); opacity: 1; }
        }
        @media (orientation: portrait) {
            #rotate-tip {
                display: block;
            }
        }
        #fullscreen-btn {
            position: absolute;
            bottom: 16px;
            right: 16px;
            background: rgba(18, 23, 34, 0.85);
            color: #10b981;
            border: 1px solid #1e293b;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            transition: opacity 0.3s ease, transform 0.2s;
            z-index: 100;
        }
        #fullscreen-btn:active {
            transform: scale(0.95);
        }
        .fade-out {
            opacity: 0.15;
        }
        #status-pill {
            position: absolute;
            top: 14px;
            left: 14px;
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #10b981;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.5px;
            pointer-events: none;
            z-index: 99;
            transition: opacity 0.4s ease;
        }
    </style>
</head>
<body>
    <!-- Motor NoSleep: Vídeo silencioso contínuo que impede o Android de suspender o ecrã -->
    <video id="nosleep-video" playsinline loop muted autoplay style="position:fixed; top:-999px; left:-999px; width:1px; height:1px; opacity:0.01; pointer-events:none;">
        <source src="data:video/webm;base64,GkXfo0AgQoaBAUL3gQFC8oEEQvOBCEKCQAR3ZWJtQoeBAkKFgQIYU4BnQI0VSalmQCgq17FAAw9CQE2AQAZ3aGFtbXlXQUAGd2hhbW15RIlACECPQAAAAAAAFlSua0AxrkAu14EBY8WBAZyBACK1nEADdW5khkAFVl9WUDglhohAA1ZQOIOBAeBABrCBCLqBCB9DtnVAIueBAKNAHIEAAIAwAQCdASoIAAgAAUAmJaQAA3AA/vz0AAA=" type="video/webm">
    </video>

    <div id="stream-container">
        <div id="status-pill">● TELEMETRIA AO VIVO</div>
        <img id="dashboard-stream" src="/frame.jpg" alt="SmartCool Telemetry Dashboard">
        <div id="rotate-tip">🔄 Vira o telemóvel na horizontal (deitado) para ver em grande</div>
        <button id="fullscreen-btn" onclick="toggleFullscreen()">⛶ TELA CHEIA</button>
    </div>

    <script>
        // 1. Motor NoSleep (Garante que o ecrã NUNCA desliga no telemóvel/tablet)
        const video = document.getElementById('nosleep-video');
        function activateKeepScreenOn() {
            if (video && video.paused) {
                video.play().catch(() => {});
            }
            if ('wakeLock' in navigator) {
                try {
                    navigator.wakeLock.request('screen').catch(() => {});
                } catch(e) {}
            }
        }

        window.addEventListener('load', activateKeepScreenOn);
        document.addEventListener('touchstart', activateKeepScreenOn);
        document.addEventListener('click', activateKeepScreenOn);
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                activateKeepScreenOn();
            }
        });
        setInterval(activateKeepScreenOn, 15000);

        // 2. Alternar Tela Cheia Imersiva
        function toggleFullscreen() {
            activateKeepScreenOn();
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                const el = document.documentElement;
                if (el.requestFullscreen) {
                    el.requestFullscreen();
                } else if (el.webkitRequestFullscreen) {
                    el.webkitRequestFullscreen();
                }
                document.getElementById('fullscreen-btn').innerText = '🗗 SAIR';
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }
                document.getElementById('fullscreen-btn').innerText = '⛶ TELA CHEIA';
            }
        }

        // Esconder o botão suavemente após 3 segundos sem toques
        const btn = document.getElementById('fullscreen-btn');
        const pill = document.getElementById('status-pill');
        let hideTimer;
        function resetFade() {
            btn.classList.remove('fade-out');
            pill.style.opacity = '1';
            clearTimeout(hideTimer);
            hideTimer = setTimeout(() => {
                btn.classList.add('fade-out');
                pill.style.opacity = '0.3';
            }, 3000);
        }
        document.addEventListener('touchstart', resetFade);
        document.addEventListener('mousemove', resetFade);
        document.addEventListener('click', resetFade);
        resetFade();

        // 3. Motor de Atualização Contínua Ultra-Resiliente (Zero Dependências, Zero Bloqueios)
        const streamImg = document.getElementById('dashboard-stream');
        let updateTimer = null;

        function refreshDashboard() {
            const nextImg = new Image();
            nextImg.onload = function() {
                streamImg.src = nextImg.src;
                pill.innerText = '● TELEMETRIA AO VIVO';
                pill.style.color = '#10b981';
                pill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                clearTimeout(updateTimer);
                updateTimer = setTimeout(refreshDashboard, 800);
            };
            nextImg.onerror = function() {
                pill.innerText = '○ A RECONECTAR...';
                pill.style.color = '#f59e0b';
                pill.style.borderColor = 'rgba(245, 158, 11, 0.4)';
                clearTimeout(updateTimer);
                updateTimer = setTimeout(refreshDashboard, 1200);
            };
            nextImg.src = '/frame.jpg?t=' + Date.now();
        }

        refreshDashboard();
    </script>
</body>
</html>
"""

PWA_MANIFEST = {
    "name": "SmartCool Master Telemetry",
    "short_name": "SmartCool",
    "start_url": "/",
    "display": "fullscreen",
    "orientation": "landscape",
    "background_color": "#07090e",
    "theme_color": "#07090e",
    "icons": [
        {
            "src": "/icon.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor HTTP multi-thread que ignora silenciosamente fecho de sockets por telemóveis."""
    daemon_threads = True

    def handle_error(self, request, client_address):
        exctype = sys.exc_info()[0]
        if exctype in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, TimeoutError):
            return


class TelemetryRequestHandler(BaseHTTPRequestHandler):
    """Manipulador HTTP para servir páginas web, PWA manifest, imagens e streams MJPEG."""

    def log_message(self, format, *args):
        return

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, socket.error):
            pass

    def finish(self):
        try:
            super().finish()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, socket.error):
            pass

    def do_GET(self):
        server = self.server

        try:
            if self.path == '/' or self.path.startswith('/index'):
                html_bytes = HTML_PAGE_TEMPLATE.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(html_bytes)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(html_bytes)

            elif self.path == '/manifest.json':
                data = json.dumps(PWA_MANIFEST).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/manifest+json')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(data)

            elif self.path == '/icon.png':
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app_icon_512.png')
                if os.path.exists(icon_path):
                    with open(icon_path, 'rb') as f:
                        icon_bytes = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.send_header('Content-Length', str(len(icon_bytes)))
                    self.send_header('Cache-Control', 'public, max-age=86400')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.wfile.write(icon_bytes)
                else:
                    self.send_response(404)
                    self.send_header('Content-Length', '0')
                    self.send_header('Connection', 'close')
                    self.end_headers()

            elif self.path.startswith('/stream'):
                self.send_response(200)
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                last_version = -1
                while getattr(server, 'is_running', True):
                    with server.lock:
                        curr_version = server.frame_version
                        jpeg_bytes = server.latest_jpeg

                    if curr_version != last_version and jpeg_bytes:
                        last_version = curr_version
                        self.wfile.write(b'--frame\r\n')
                        self.wfile.write(b'Content-Type: image/jpeg\r\n')
                        self.wfile.write(f'Content-Length: {len(jpeg_bytes)}\r\n\r\n'.encode('ascii'))
                        self.wfile.write(jpeg_bytes)
                        self.wfile.write(b'\r\n')
                        self.wfile.flush()

                    time.sleep(0.5)

            elif self.path.startswith('/frame.jpg'):
                with server.lock:
                    jpeg_bytes = server.latest_jpeg

                if jpeg_bytes:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(jpeg_bytes)))
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('Expires', '0')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.wfile.write(jpeg_bytes)
                else:
                    self.send_response(404)
                    self.send_header('Content-Length', '0')
                    self.send_header('Connection', 'close')
                    self.end_headers()

            elif self.path.startswith('/api/stats'):
                with server.lock:
                    stats = server.latest_stats or {}
                data = json.dumps(stats).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)

            elif self.path.startswith('/qrcode'):
                with server.lock:
                    qr_bytes = server.qr_png_bytes

                if qr_bytes:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.end_headers()
                    self.wfile.write(qr_bytes)
                else:
                    self.send_response(404)
                    self.end_headers()

            else:
                self.send_response(404)
                self.end_headers()

        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, socket.error):
            pass


class TelemetryWebServer:
    """Controlador do servidor Web Wi-Fi em segundo plano."""

    def __init__(self, port=8080):
        self.port = port
        self.host_ip = get_local_ip()
        self.server = None
        self.thread = None
        self.is_running = False

        self.latest_jpeg = None
        self.latest_stats = None
        self.frame_version = 0
        self.lock = threading.Lock()

        # Frame inicial de arranque (garante que /frame.jpg NUNCA retorne 404)
        try:
            init_img = Image.new("RGB", (1280, 720), "#07090e")
            draw = ImageDraw.Draw(init_img)
            draw.rectangle([40, 40, 1240, 680], outline="#1e293b", width=2)
            draw.text((640, 320), "SMARTCOOL MASTER TELEMETRY", fill="#10b981", anchor="mm")
            draw.text((640, 370), "A ligar a telemetria do PC em tempo real...", fill="#94a3b8", anchor="mm")
            buf = io.BytesIO()
            init_img.save(buf, format="JPEG", quality=85)
            self.latest_jpeg = buf.getvalue()
            self.frame_version = 1
        except Exception:
            pass

        self.url = f"http://{self.host_ip}:{self.port}"
        self.qr_png_bytes = self._generate_qr_code(self.url)

    def _generate_qr_code(self, url):
        """Gera um QR Code nítido e estético com as cores da aplicação."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="#10b981", back_color="#0a0d14").convert("RGBA")
            buf = io.BytesIO()
            qr_img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            print(f"[WebServer] Erro ao gerar QR Code: {e}")
            return None

    def start(self):
        """Inicia o servidor HTTP multi-thread em background thread."""
        if self.is_running:
            return

        try:
            self.host_ip = get_local_ip()
            self.url = f"http://{self.host_ip}:{self.port}"
            self.qr_png_bytes = self._generate_qr_code(self.url)

            self.server = ThreadedHTTPServer(('0.0.0.0', self.port), TelemetryRequestHandler)
            self.server.lock = self.lock
            self.server.latest_jpeg = self.latest_jpeg
            self.server.latest_stats = self.latest_stats
            self.server.frame_version = self.frame_version
            self.server.qr_png_bytes = self.qr_png_bytes
            self.server.is_running = True

            self.is_running = True
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            print(f"[WebServer] Servidor Wi-Fi ativo em: {self.url}")
        except Exception as e:
            print(f"[WebServer] Erro ao iniciar servidor na porta {self.port}: {e}")
            self.is_running = False

    def stop(self):
        """Para o servidor HTTP de forma segura e não-bloqueante."""
        if self.server:
            self.server.is_running = False
            try:
                s = self.server
                threading.Thread(target=s.shutdown, daemon=True).start()
                s.server_close()
            except Exception:
                pass
        self.is_running = False

    def update_frame(self, pil_image, stats=None):
        """Atualiza a frame e telemetria disponíveis para os telemóveis/tablets."""
        if not pil_image:
            return

        try:
            if pil_image.mode in ("RGBA", "P", "LA"):
                pil_image = pil_image.convert("RGB")

            buf = io.BytesIO()
            pil_image.save(buf, format="JPEG", quality=85, optimize=True)
            jpeg_bytes = buf.getvalue()

            with self.lock:
                self.latest_jpeg = jpeg_bytes
                if stats:
                    self.latest_stats = stats
                self.frame_version += 1

                if self.server:
                    self.server.latest_jpeg = self.latest_jpeg
                    self.server.latest_stats = self.latest_stats
                    self.server.frame_version = self.frame_version

        except Exception as e:
            print(f"[WebServer] Erro ao codificar JPEG: {e}")


if __name__ == "__main__":
    server = TelemetryWebServer(port=8080)
    server.start()
    print("Aceda com o telemóvel a:", server.url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
