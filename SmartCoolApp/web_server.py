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
        .controls-bar {
            position: absolute;
            bottom: 14px;
            right: 14px;
            display: flex;
            gap: 8px;
            z-index: 100;
            transition: opacity 0.3s ease, transform 0.2s;
        }
        .action-btn {
            background: rgba(18, 23, 34, 0.9);
            color: #10b981;
            border: 1px solid #1e293b;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .action-btn:active {
            transform: scale(0.95);
        }
        .action-btn.apk-btn {
            color: #38bdf8;
            border-color: rgba(56, 189, 248, 0.4);
            background: rgba(15, 23, 42, 0.9);
        }
        .action-btn.theme-btn {
            color: #fbbf24;
            border-color: rgba(251, 191, 36, 0.4);
            background: rgba(26, 22, 14, 0.9);
        }
        .fade-out {
            opacity: 0.15;
            pointer-events: none;
        }
        #status-pill {
            position: absolute;
            top: 14px;
            left: 14px;
            background: rgba(16, 185, 129, 0.2);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #10b981;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.5px;
            pointer-events: auto;
            cursor: pointer;
            z-index: 99;
            transition: opacity 0.4s ease;
        }
        #wakelock-pill {
            position: absolute;
            top: 14px;
            right: 14px;
            background: rgba(14, 165, 233, 0.2);
            border: 1px solid rgba(14, 165, 233, 0.4);
            color: #38bdf8;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.5px;
            pointer-events: auto;
            cursor: pointer;
            z-index: 99;
            transition: opacity 0.4s ease;
        }
        /* Setas de Troca de Tema (Touch / Mobile) */
        .theme-nav-arrow {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 44px;
            height: 70px;
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #f8fafc;
            font-size: 36px;
            line-height: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 99;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border-radius: 12px;
            transition: opacity 0.3s ease, background 0.2s, transform 0.15s;
        }
        .arrow-left { left: 10px; }
        .arrow-right { right: 10px; }
        .theme-nav-arrow:active {
            background: rgba(16, 185, 129, 0.65);
            transform: translateY(-50%) scale(0.92);
        }
        /* Toast de Notificação de Tema Ativo */
        .theme-toast {
            position: absolute;
            top: 14px;
            left: 50%;
            transform: translateX(-50%) translateY(-20px);
            background: rgba(15, 23, 42, 0.95);
            border: 1px solid #10b981;
            color: #10b981;
            padding: 6px 18px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            box-shadow: 0 4px 18px rgba(0,0,0,0.7);
            z-index: 105;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            white-space: nowrap;
        }
        .theme-toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
        /* Modal Drawer de Seleção de Temas */
        .modal-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            z-index: 200;
            display: none;
        }
        .modal-backdrop.open { display: block; }
        .theme-drawer {
            position: fixed;
            top: 0;
            right: -340px;
            width: 320px;
            max-width: 85vw;
            height: 100%;
            background: rgba(11, 15, 25, 0.98);
            border-left: 1px solid rgba(56, 189, 248, 0.3);
            box-shadow: -8px 0 30px rgba(0, 0, 0, 0.85);
            z-index: 201;
            display: flex;
            flex-direction: column;
            transition: right 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            color: #f8fafc;
        }
        .theme-drawer.open { right: 0; }
        .drawer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 18px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .drawer-title {
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 0.5px;
            color: #fbbf24;
        }
        .drawer-close {
            background: none;
            border: none;
            color: #94a3b8;
            font-size: 22px;
            cursor: pointer;
            padding: 4px 8px;
            line-height: 1;
        }
        .drawer-content {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .theme-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 13px;
            font-weight: 600;
            color: #e2e8f0;
        }
        .theme-item:active, .theme-item:hover {
            background: rgba(16, 185, 129, 0.2);
            border-color: #10b981;
        }
        .theme-item.active {
            background: rgba(16, 185, 129, 0.25);
            border-color: #10b981;
            color: #10b981;
            font-weight: bold;
        }
        .theme-item-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
            box-shadow: 0 0 8px currentColor;
        }
    </style>
</head>
<body>
    <!-- Motor NoSleep Triplo: Vídeo H.264 minúsculo visível ao compositor + Heartbeat Audio + WakeLock API -->
    <video id="nosleep-video" playsinline webkit-playsinline loop muted autoplay style="position:fixed; bottom:2px; right:2px; width:4px; height:4px; opacity:0.01; pointer-events:none; z-index:9999;">
        <source src="data:video/mp4;base64,AAAAHGZ0eXBpc29tAAAAAGlzb21tcDQxAAAACHZpZGVvAAAAAA==" type="video/mp4">
        <source src="data:video/webm;base64,GkXfo0AgQoaBAUL3gQFC8oEEQvOBCEKCQAR3ZWJtQoeBAkKFgQIYU4BnQI0VSalmQCgq17FAAw9CQE2AQAZ3aGFtbXlXQUAGd2hhbW15RIlACECPQAAAAAAAFlSua0AxrkAu14EBY8WBAZyBACK1nEADdW5khkAFVl9WUDglhohAA1ZQOIOBAeBABrCBCLqBCB9DtnVAIueBAKNAHIEAAIAwAQCdASoIAAgAAUAmJaQAA3AA/vz0AAA=" type="video/webm">
    </video>

    <div id="stream-container">
        <div id="status-pill" onclick="toggleFullscreen()">● TELEMETRIA AO VIVO</div>
        <div id="theme-toast" class="theme-toast">🎨 Master Telemetry</div>
        <div id="wakelock-pill" onclick="manualActivateScreenLock()">💡 ECRÃ: ATIVADO</div>

        <!-- Botões de Troca Rápida de Tema por Toque -->
        <button id="btn-prev-theme" class="theme-nav-arrow arrow-left" onclick="switchTheme('prev')" title="Tema Anterior">‹</button>
        <button id="btn-next-theme" class="theme-nav-arrow arrow-right" onclick="switchTheme('next')" title="Próximo Tema">›</button>

        <img id="dashboard-stream" src="/frame.jpg" alt="SmartCool Telemetry Dashboard">
        <div id="rotate-tip">🔄 Vira o telemóvel na horizontal (deitado) para ver em grande</div>

        <div class="controls-bar" id="controls-bar">
            <button class="action-btn theme-btn" id="theme-btn" onclick="openThemeDrawer()">🎨 TEMAS</button>
            <a class="action-btn apk-btn" href="/download/app.apk" target="_blank" title="Instala a aplicação Android nativa que NUNCA desliga o ecrã">📱 APP ANDROID (.APK)</a>
            <button class="action-btn" id="fullscreen-btn" onclick="toggleFullscreen()">⛶ TELA CHEIA</button>
        </div>
    </div>

    <!-- Modal Drawer de Seleção de Temas -->
    <div id="theme-modal-backdrop" class="modal-backdrop" onclick="closeThemeDrawer()"></div>
    <div id="theme-drawer" class="theme-drawer">
        <div class="drawer-header">
            <div class="drawer-title">🎨 ESCOLHER TEMA</div>
            <button class="drawer-close" onclick="closeThemeDrawer()">✕</button>
        </div>
        <div class="drawer-content" id="theme-list">
            <div style="color:#94a3b8; font-size:12px; padding:8px;">A carregar temas disponíveis...</div>
        </div>
    </div>

    <script>
        // 1. Motor NoSleep Universal (Impede que o ecrã do telemóvel/tablet desligue)
        let audioCtx = null;
        let wakeLock = null;

        function startAudioPulse() {
            try {
                if (!audioCtx) {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }
                if (audioCtx.state === 'suspended') {
                    audioCtx.resume();
                }
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                gain.gain.value = 0.00001;
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.05);
            } catch(e) {}
        }

        async function activateKeepScreenOn() {
            const vid = document.getElementById('nosleep-video');
            if (vid) {
                vid.play().catch(() => {});
            }
            startAudioPulse();

            if ('wakeLock' in navigator) {
                try {
                    if (!wakeLock || wakeLock.released) {
                        wakeLock = await navigator.wakeLock.request('screen');
                        setLockStatus(true);
                        wakeLock.addEventListener('release', () => {
                            setLockStatus(false);
                        });
                    }
                } catch(e) {
                    setLockStatus(true, true);
                }
            } else {
                setLockStatus(true, true);
            }
        }

        function setLockStatus(active, fallback=false) {
            const wl = document.getElementById('wakelock-pill');
            if (!wl) return;
            if (active) {
                wl.innerText = fallback ? '💡 ECRÃ: SEMPRE LIGADO (ATIVO)' : '💡 ECRÃ: SEMPRE LIGADO ✓';
                wl.style.color = '#10b981';
                wl.style.borderColor = 'rgba(16, 185, 129, 0.4)';
            } else {
                wl.innerText = '💡 ECRÃ: TOCA PARA ATIVAR';
                wl.style.color = '#f59e0b';
                wl.style.borderColor = 'rgba(245, 158, 11, 0.4)';
            }
        }

        function manualActivateScreenLock() {
            activateKeepScreenOn();
            setLockStatus(true);
        }

        window.addEventListener('load', activateKeepScreenOn);
        document.addEventListener('touchstart', activateKeepScreenOn, {passive: true});
        document.addEventListener('click', activateKeepScreenOn, {passive: true});
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                activateKeepScreenOn();
            }
        });
        setInterval(activateKeepScreenOn, 10000);

        // 2. Alternar Tela Cheia Imersiva
        function toggleFullscreen() {
            activateKeepScreenOn();
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                const el = document.documentElement;
                if (el.requestFullscreen) {
                    el.requestFullscreen().catch(() => {});
                } else if (el.webkitRequestFullscreen) {
                    el.webkitRequestFullscreen().catch(() => {});
                }
                document.getElementById('fullscreen-btn').innerText = '🗗 SAIR';
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen().catch(() => {});
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen().catch(() => {});
                }
                document.getElementById('fullscreen-btn').innerText = '⛶ TELA CHEIA';
            }
        }

        // Esconder os botões suavemente após 4 segundos sem toques
        const bar = document.getElementById('controls-bar');
        const pill = document.getElementById('status-pill');
        const wl = document.getElementById('wakelock-pill');
        const arrowLeft = document.getElementById('btn-prev-theme');
        const arrowRight = document.getElementById('btn-next-theme');
        let hideTimer;
        function resetFade() {
            if (bar) bar.classList.remove('fade-out');
            if (pill) pill.style.opacity = '1';
            if (wl) wl.style.opacity = '1';
            if (arrowLeft) arrowLeft.classList.remove('fade-out');
            if (arrowRight) arrowRight.classList.remove('fade-out');
            clearTimeout(hideTimer);
            hideTimer = setTimeout(() => {
                if (bar) bar.classList.add('fade-out');
                if (pill) pill.style.opacity = '0.35';
                if (wl) wl.style.opacity = '0.35';
                if (arrowLeft) arrowLeft.classList.add('fade-out');
                if (arrowRight) arrowRight.classList.add('fade-out');
            }, 4000);
        }
        document.addEventListener('touchstart', resetFade, {passive: true});
        document.addEventListener('mousemove', resetFade, {passive: true});
        document.addEventListener('click', resetFade, {passive: true});
        resetFade();

        // 3. Notificação Toast de Tema
        let toastTimer = null;
        function showThemeToast(themeName) {
            const toast = document.getElementById('theme-toast');
            if (!toast) return;
            toast.innerText = '🎨 ' + themeName;
            toast.classList.add('show');
            clearTimeout(toastTimer);
            toastTimer = setTimeout(() => {
                toast.classList.remove('show');
            }, 2500);
        }

        // 4. Controlo Remoto de Temas (Next / Prev / Set)
        let currentThemeActive = "";
        async function switchTheme(action, themeName=null) {
            activateKeepScreenOn();
            resetFade();
            let url = '';
            if (action === 'set' && themeName) {
                url = '/api/theme/set?name=' + encodeURIComponent(themeName);
            } else if (action === 'next') {
                url = '/api/theme/next';
            } else if (action === 'prev') {
                url = '/api/theme/prev';
            }

            try {
                const res = await fetch(url);
                const data = await res.json();
                if (data.ok && data.theme) {
                    currentThemeActive = data.theme;
                    showThemeToast(data.theme);
                    // Força atualização da imagem imediatamente
                    setTimeout(() => {
                        refreshDashboard(true);
                    }, 200);
                    renderThemeList();
                }
            } catch(e) {}
        }

        // 5. Drawer de Seleção de Temas
        let cachedThemes = [];
        async function fetchThemes() {
            try {
                const res = await fetch('/api/themes');
                const data = await res.json();
                if (data.themes) {
                    cachedThemes = data.themes;
                    currentThemeActive = data.current || currentThemeActive;
                    renderThemeList();
                }
            } catch(e) {}
        }

        function renderThemeList() {
            const container = document.getElementById('theme-list');
            if (!container || !cachedThemes.length) return;
            container.innerHTML = '';
            cachedThemes.forEach(t => {
                const item = document.createElement('div');
                item.className = 'theme-item' + (t.name === currentThemeActive ? ' active' : '');
                
                const dot = document.createElement('span');
                dot.className = 'theme-item-dot';
                dot.style.color = t.primary || '#10b981';
                dot.style.backgroundColor = t.primary || '#10b981';

                const label = document.createElement('span');
                label.innerText = t.name;

                item.appendChild(dot);
                item.appendChild(label);

                item.onclick = () => {
                    switchTheme('set', t.name);
                    closeThemeDrawer();
                };
                container.appendChild(item);
            });
        }

        function openThemeDrawer() {
            activateKeepScreenOn();
            fetchThemes();
            document.getElementById('theme-modal-backdrop').classList.add('open');
            document.getElementById('theme-drawer').classList.add('open');
        }

        function closeThemeDrawer() {
            document.getElementById('theme-modal-backdrop').classList.remove('open');
            document.getElementById('theme-drawer').classList.remove('open');
        }

        // Suporte para Gestos de Deslize (Swipe) no Telemóvel
        let touchStartX = 0;
        let touchStartY = 0;
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1) {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            }
        }, {passive: true});

        document.addEventListener('touchend', (e) => {
            if (e.changedTouches.length === 1) {
                const deltaX = e.changedTouches[0].clientX - touchStartX;
                const deltaY = e.changedTouches[0].clientY - touchStartY;
                if (Math.abs(deltaX) > 60 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5) {
                    if (deltaX < 0) {
                        switchTheme('next');
                    } else {
                        switchTheme('prev');
                    }
                }
            }
        }, {passive: true});

        // Suporte para Teclado (Setas Esquerda / Direita)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight') switchTheme('next');
            else if (e.key === 'ArrowLeft') switchTheme('prev');
            else if (e.key === 'Escape') closeThemeDrawer();
        });

        // Pré-carregar lista de temas ao iniciar
        fetchThemes();

        // 6. Motor de Atualização Contínua Ultra-Resiliente
        const streamImg = document.getElementById('dashboard-stream');
        let updateTimer = null;

        function refreshDashboard(immediate=false) {
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

            elif self.path.startswith('/api/themes'):
                data = {"current": "", "themes": []}
                if hasattr(server, 'get_themes_callback') and server.get_themes_callback:
                    try:
                        data = server.get_themes_callback()
                    except Exception as e:
                        data = {"error": str(e)}
                body = json.dumps(data).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(body)

            elif self.path.startswith('/api/theme/next'):
                result = {"ok": False}
                if hasattr(server, 'on_change_theme_callback') and server.on_change_theme_callback:
                    try:
                        new_name = server.on_change_theme_callback('next')
                        result = {"ok": True, "theme": new_name}
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}
                body = json.dumps(result).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(body)

            elif self.path.startswith('/api/theme/prev'):
                result = {"ok": False}
                if hasattr(server, 'on_change_theme_callback') and server.on_change_theme_callback:
                    try:
                        new_name = server.on_change_theme_callback('prev')
                        result = {"ok": True, "theme": new_name}
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}
                body = json.dumps(result).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(body)

            elif self.path.startswith('/api/theme/set'):
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(self.path)
                qs = parse_qs(parsed.query)
                target_name = qs.get('name', [''])[0]
                result = {"ok": False}
                if hasattr(server, 'on_change_theme_callback') and server.on_change_theme_callback and target_name:
                    try:
                        applied = server.on_change_theme_callback('set', target_name)
                        result = {"ok": True, "theme": applied or target_name}
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}
                body = json.dumps(result).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(body)

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

            elif self.path.startswith('/download/app.apk') or self.path.startswith('/app.apk'):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                apk_paths = [
                    os.path.join(base_dir, 'AndroidApp', 'output', 'SmartCool-Master-Telemetry.apk'),
                    os.path.join(base_dir, 'SmartCool-Master-Telemetry.apk'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'SmartCool.apk')
                ]
                found_apk = None
                for p in apk_paths:
                    if os.path.exists(p):
                        found_apk = p
                        break

                if found_apk:
                    with open(found_apk, 'rb') as f:
                        apk_data = f.read()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/vnd.android.package-archive')
                    self.send_header('Content-Length', str(len(apk_data)))
                    self.send_header('Content-Disposition', 'attachment; filename="SmartCool-Master-Telemetry.apk"')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.wfile.write(apk_data)
                else:
                    self.send_response(302)
                    self.send_header('Location', 'https://github.com/Tarrasga/monitorsensor-/releases')
                    self.send_header('Connection', 'close')
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

        self.get_themes_callback = None
        self.on_change_theme_callback = None

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

    def set_theme_callbacks(self, get_themes_fn, change_theme_fn):
        """Regista os callbacks para leitura e alteração remota de temas a partir do telemóvel."""
        self.get_themes_callback = get_themes_fn
        self.on_change_theme_callback = change_theme_fn
        if self.server:
            self.server.get_themes_callback = get_themes_fn
            self.server.on_change_theme_callback = change_theme_fn

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
            self.server.get_themes_callback = self.get_themes_callback
            self.server.on_change_theme_callback = self.on_change_theme_callback
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
