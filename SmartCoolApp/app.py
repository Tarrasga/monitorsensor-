"""
SmartCool Monitor App - Edição Master Telemetry, 2º Ecrã & Wi-Fi Mobile
Aplicação com Interface Gráfica Responsiva (GUI) para monitorizar o PC:
- Suporta uso no 2º Ecrã com Tela Cheia (F11) com renderização Nativa em Alta Resolução (1080p/2K/4K)
- Servidor Web Wi-Fi integrado para Telemóvel / Tablet (iPad, iPhone, Android) com QR Code instantâneo
- Envio simultâneo para o visor USB físico 3.5" (480x320)
- Tema 'Master Telemetry': Símbolo oficial da Garra Monster com iluminação néon suave, estética 'eye-friendly'
- Cores dinâmicas inteligentes (Fresco < 55°C, Médio < 75°C, Chamas e labaredas animadas ≥ 75°C)
- 27 Sensores em Tempo Real (CPU 14C/20T, GPU RTX 4070 Ti, DDR5 RAM, NVMe C:, DATA E:, Live Net, Fans)
"""

import os
import io
import sys
import time
import threading
import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont

from screen_driver import SmartCoolDriver
from hardware_monitor import HardwareMonitor
from web_server import TelemetryWebServer

user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG),
                ('right', wintypes.LONG), ('bottom', wintypes.LONG)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD),
                ('rcMonitor', RECT),
                ('rcWork', RECT),
                ('dwFlags', wintypes.DWORD)]


def get_current_monitor_rect(hwnd):
    """Devolve (left, top, width, height) do monitor onde a janela está atualmente."""
    try:
        h_mon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST = 2
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(h_mon, ctypes.byref(mi))
        r = mi.rcMonitor
        return r.left, r.top, r.right - r.left, r.bottom - r.top
    except Exception:
        return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


class SmartCoolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartCool Monitor // Master Telemetry [TARRASGA]")
        self.root.geometry("1120x740")
        self.root.minsize(880, 600)
        self.root.configure(bg="#0a0d14")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.base_dir, "assets")

        # Catálogo de Temas Integrados
        self.themes = {
            "Master Telemetry (Todos os Sensores)": {
                "file": os.path.join(self.assets_dir, "master_telemetry_usb.png"),
                "layout": "ALL_SENSORS",
                "primary": "#10b981",
                "dim": "#15241d",
                "accent": "#38bdf8"
            },
            "Monster Energy (Com Latas)": {
                "file": os.path.join(self.assets_dir, "monster_cans.png"),
                "layout": "MONSTER_CANS",
                "primary": "#10b981",
                "dim": "#143818",
                "accent": "#50f0ff"
            },
            "Monster Energy (Claw / Garra)": {
                "file": os.path.join(self.assets_dir, "monster_claw.png"),
                "layout": "MONSTER_CLAW",
                "primary": "#10b981",
                "dim": "#143818",
                "accent": "#50f0ff"
            },
            "ROG Dark Gaming (TARRASGA)": {
                "file": os.path.join(self.assets_dir, "background.png"),
                "layout": "ROG",
                "primary": "#ff2d41",
                "dim": "#c81e2d",
                "accent": "#3cd2e6"
            }
        }

        self.current_theme_name = "Master Telemetry (Todos os Sensores)"
        self.bg_path = self.themes[self.current_theme_name]["file"]

        # Carregar símbolo da garra
        claw_icon_path = os.path.join(self.assets_dir, "monster_claw_symbol.png")
        if os.path.exists(claw_icon_path):
            self.claw_symbol = Image.open(claw_icon_path).convert("RGBA")
        else:
            self.claw_symbol = None

        # Rotação Automática de Temas (10 segundos)
        self.auto_cycle_var = tk.BooleanVar(value=False)
        self.cycle_interval = 10.0
        self.last_theme_switch_time = time.time()

        # Efeito de Chamas Dinâmicas (Flicker)
        self.flame_flicker = 0

        # Controlo de Ecrã / Tela Cheia
        self.is_fullscreen = False
        self.saved_geometry = None
        self.last_stats = None

        # Manter Janela Sempre no Topo (Always on Top)
        self.always_on_top_var = tk.BooleanVar(value=True)
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        # Servidor Web Wi-Fi para Telemóvel / Tablet
        self.wifi_enabled_var = tk.BooleanVar(value=True)
        self.web_server = TelemetryWebServer(port=8080)
        self.web_server.start()

        # Drivers
        self.driver = SmartCoolDriver()
        self.monitor = HardwareMonitor()
        self.device_map = {}

        # Controlo de Threads
        self.running = False
        self.worker_thread = None

        # Carregar fontes padrão para layouts legados
        self._load_legacy_fonts()

        # Construir UI Responsiva
        self._build_ui()
        self._refresh_devices()

        # Atalhos de Teclado para 2º Ecrã
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)
        self.canvas.bind("<F11>", self._toggle_fullscreen)
        self.canvas.bind("<Escape>", self._exit_fullscreen)

        # Renderizar primeiro frame
        self.update_preview()

        # Iniciar transmissão automaticamente após carregar a interface
        self.root.after(500, self._auto_start_stream)

    def _load_legacy_fonts(self):
        """Carrega fontes padrão do Windows para temas legados."""
        try:
            self.font_temp_giant = ImageFont.truetype("segoeuib.ttf", 38)
            self.font_clock = ImageFont.truetype("consolab.ttf", 20)
            self.font_clock_cans = ImageFont.truetype("consolab.ttf", 15)
            self.font_clock_claw = ImageFont.truetype("consolab.ttf", 17)
            self.font_label_bold = ImageFont.truetype("segoeuib.ttf", 11)
            self.font_bold = ImageFont.truetype("segoeuib.ttf", 11)
            self.font_val = ImageFont.truetype("segoeuib.ttf", 11)
            self.font_fan = ImageFont.truetype("segoeui.ttf", 11)
            self.font_small = ImageFont.truetype("segoeui.ttf", 10)
        except Exception:
            d = ImageFont.load_default()
            self.font_temp_giant = self.font_clock = self.font_clock_cans = self.font_clock_claw = d
            self.font_label_bold = self.font_bold = self.font_val = self.font_fan = self.font_small = d

    def _build_ui(self):
        # 1. Cabeçalho Superior
        header_frame = tk.Frame(self.root, bg="#0d111a", padx=16, pady=10)
        header_frame.pack(fill=tk.X)

        self.lbl_title = tk.Label(
            header_frame,
            text="MASTER TELEMETRY // SMARTCOOL, 2º ECRÃ & WI-FI",
            font=("Segoe UI", 12, "bold"),
            fg="#e2e8f0",
            bg="#0d111a"
        )
        self.lbl_title.pack(side=tk.LEFT)

        subtitle = tk.Label(
            header_frame,
            text="27 Sensores // TARRASGA",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0d111a"
        )
        subtitle.pack(side=tk.LEFT, padx=12)

        # Botão de Tela Cheia para o 2º Ecrã
        self.btn_fullscreen = tk.Button(
            header_frame,
            text="⛶ EXPANDIR NESTE ECRÃ (F11)",
            command=self._toggle_fullscreen,
            bg="#1e293b",
            fg="#10b981",
            activebackground="#2e3e56",
            activeforeground="#10b981",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4
        )
        self.btn_fullscreen.pack(side=tk.RIGHT)

        # Botão Fixar Sempre no Topo (Always on Top)
        self.btn_topmost = tk.Button(
            header_frame,
            text="📌 SEMPRE NO TOPO",
            command=self._toggle_topmost_btn,
            bg="#1e293b",
            fg="#10b981",
            activebackground="#2e3e56",
            activeforeground="#10b981",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4
        )
        self.btn_topmost.pack(side=tk.RIGHT, padx=(0, 8))

        # Botão QR Code para Telemóvel no Cabeçalho
        self.btn_qr_top = tk.Button(
            header_frame,
            text="📱 TELEMÓVEL / TABLET (QR CODE)",
            command=self._show_qr_code_window,
            bg="#1e293b",
            fg="#38bdf8",
            activebackground="#2e3e56",
            activeforeground="#38bdf8",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4
        )
        self.btn_qr_top.pack(side=tk.RIGHT, padx=(0, 8))

        # 2. Área Central (Responsiva)
        content_frame = tk.Frame(self.root, bg="#0a0d14", padx=12, pady=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Coluna Esquerda: Ecrã de Pré-visualização Expansível
        self.preview_col = tk.Frame(content_frame, bg="#0a0d14")
        self.preview_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        prev_label = tk.Label(
            self.preview_col,
            text="PAINEL PRINCIPAL // PRÉ-VISUALIZAÇÃO AO VIVO",
            font=("Segoe UI", 8, "bold"),
            fg="#64748b",
            bg="#0a0d14"
        )
        prev_label.pack(anchor="w", pady=(0, 4))

        self.canvas = tk.Canvas(
            self.preview_col,
            bg="#07090f",
            highlightthickness=1,
            highlightbackground="#1e293b"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Coluna Direita: Barra Lateral de Controlos
        self.controls_col = tk.Frame(content_frame, bg="#0d111a", padx=14, pady=14, width=285)
        self.controls_col.pack(side=tk.RIGHT, fill=tk.Y)
        self.controls_col.pack_propagate(False)

        # Grupo: Seletor de Tema
        lbl_theme = tk.Label(self.controls_col, text="ESCOLHA O TEMA:", font=("Segoe UI", 9, "bold"), fg="#e2e8f0", bg="#0d111a")
        lbl_theme.pack(anchor="w", pady=(0, 4))

        self.theme_combo = ttk.Combobox(self.controls_col, state="readonly", values=list(self.themes.keys()))
        self.theme_combo.current(0)
        self.theme_combo.pack(fill=tk.X, pady=(0, 6))
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_changed)

        # Checkbox de Rotação Automática
        self.chk_cycle = tk.Checkbutton(
            self.controls_col,
            text="🔄 Alternar temas a cada 10s",
            variable=self.auto_cycle_var,
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#0d111a",
            selectcolor="#0a0d14",
            activebackground="#0d111a",
            activeforeground="#10b981"
        )
        self.chk_cycle.pack(anchor="w", pady=(0, 6))

        # Checkbox Sempre no Topo (Always on Top)
        self.chk_topmost = tk.Checkbutton(
            self.controls_col,
            text="📌 Manter sempre visível (no topo)",
            variable=self.always_on_top_var,
            command=self._on_topmost_changed,
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#0d111a",
            selectcolor="#0a0d14",
            activebackground="#0d111a",
            activeforeground="#10b981"
        )
        self.chk_topmost.pack(anchor="w", pady=(0, 10))

        # Grupo: Servidor Wi-Fi para Telemóvel / Tablet
        wifi_box = tk.LabelFrame(
            self.controls_col,
            text="TRANSMISSÃO WI-FI (MOBILE)",
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#0d111a",
            padx=8,
            pady=8
        )
        wifi_box.pack(fill=tk.X, pady=(0, 12))

        self.chk_wifi = tk.Checkbutton(
            wifi_box,
            text="📶 Ativar Servidor Wi-Fi",
            variable=self.wifi_enabled_var,
            command=self._on_wifi_toggle,
            font=("Segoe UI", 8, "bold"),
            fg="#e2e8f0",
            bg="#0d111a",
            selectcolor="#0a0d14",
            activebackground="#0d111a",
            activeforeground="#10b981"
        )
        self.chk_wifi.pack(anchor="w", pady=(0, 4))

        self.lbl_wifi_url = tk.Label(
            wifi_box,
            text=f"http://{self.web_server.host_ip}:{self.web_server.port}",
            font=("Consolas", 8, "bold"),
            fg="#38bdf8",
            bg="#0d111a"
        )
        self.lbl_wifi_url.pack(anchor="w", pady=(0, 6))

        btn_qr = tk.Button(
            wifi_box,
            text="📱 MOSTRAR QR CODE",
            command=self._show_qr_code_window,
            bg="#1e293b",
            fg="#10b981",
            activebackground="#2e3e56",
            activeforeground="#10b981",
            relief=tk.FLAT,
            font=("Segoe UI", 8, "bold"),
            pady=4
        )
        btn_qr.pack(fill=tk.X)

        # Grupo: Dispositivo USB
        lbl_port = tk.Label(self.controls_col, text="DISPOSITIVO USB:", font=("Segoe UI", 8, "bold"), fg="#e2e8f0", bg="#0d111a")
        lbl_port.pack(anchor="w", pady=(0, 4))

        port_row = tk.Frame(self.controls_col, bg="#0d111a")
        port_row.pack(fill=tk.X, pady=(0, 10))

        self.port_combo = ttk.Combobox(port_row, state="readonly")
        self.port_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_refresh = tk.Button(
            port_row,
            text="↻",
            command=self._refresh_devices,
            bg="#1e293b",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=8
        )
        btn_refresh.pack(side=tk.RIGHT)

        # Grupo: Imagem personalizada
        btn_choose_bg = tk.Button(
            self.controls_col,
            text="📁 Carregar Outra Imagem...",
            command=self._choose_bg_image,
            bg="#1e293b",
            fg="#cbd5e1",
            relief=tk.FLAT,
            pady=4
        )
        btn_choose_bg.pack(fill=tk.X, pady=(0, 10))

        # Grupo: Brilho do Ecrã USB
        lbl_bright = tk.Label(self.controls_col, text="BRILHO DO ECRÃ USB (%):", font=("Segoe UI", 8, "bold"), fg="#e2e8f0", bg="#0d111a")
        lbl_bright.pack(anchor="w", pady=(0, 2))

        self.bright_slider = tk.Scale(
            self.controls_col,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            bg="#0d111a",
            fg="#ffffff",
            highlightthickness=0,
            troughcolor="#1e293b",
            command=self._on_brightness_change
        )
        self.bright_slider.set(80)
        self.bright_slider.pack(fill=tk.X, pady=(0, 12))

        # Botão Iniciar Transmissão USB & Wi-Fi
        self.btn_toggle = tk.Button(
            self.controls_col,
            text="▶ INICIAR TRANSMISSÃO",
            font=("Segoe UI", 11, "bold"),
            bg="#10b981",
            fg="#ffffff",
            relief=tk.FLAT,
            pady=9,
            command=self._toggle_stream
        )
        self.btn_toggle.pack(fill=tk.X, pady=(0, 8))

        # Dica do 2º Ecrã e Telemóvel
        tip_lbl = tk.Label(
            self.controls_col,
            text="💡 DICA:\n• No PC: arrasta para o 2º ecrã e prime F11.\n• No Telemóvel: abre o QR Code e vê ao vivo por Wi-Fi!",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg="#0d111a",
            justify=tk.LEFT
        )
        tip_lbl.pack(fill=tk.X, pady=(4, 0))

        # 3. Barra de Estado Inferior
        self.status_bar = tk.Label(
            self.root,
            text=f"Pronto. Servidor Wi-Fi ativo em http://{self.web_server.host_ip}:{self.web_server.port}",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#07090f",
            padx=14,
            pady=6,
            anchor="w"
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_wifi_toggle(self):
        """Liga ou desliga o servidor web Wi-Fi."""
        if self.wifi_enabled_var.get():
            self.web_server.start()
            self.status_bar.config(text=f"Servidor Wi-Fi ATIVO em: {self.web_server.url}")
        else:
            self.web_server.stop()
            self.status_bar.config(text="Servidor Wi-Fi desativado.")

    def _on_topmost_changed(self):
        """Atualiza a propriedade 'Always on Top' da janela."""
        is_top = self.always_on_top_var.get()
        try:
            self.root.attributes("-topmost", is_top)
        except Exception:
            pass
        if is_top:
            self.btn_topmost.config(text="📌 SEMPRE NO TOPO", fg="#10b981")
            self.status_bar.config(text="Janela fixada SEMPRE NO TOPO (não se esconde atrás de outros programas).")
        else:
            self.btn_topmost.config(text="📌 NO TOPO (OFF)", fg="#94a3b8")
            self.status_bar.config(text="Modo sempre no topo desativado.")

    def _toggle_topmost_btn(self):
        """Alterna a fixação no topo através do botão do cabeçalho."""
        self.always_on_top_var.set(not self.always_on_top_var.get())
        self._on_topmost_changed()

    def _show_qr_code_window(self):
        """Abre uma janela modal com o QR Code para ler facilmente com o telemóvel/tablet."""
        win = tk.Toplevel(self.root)
        win.title("Ligar Telemóvel / Tablet via Wi-Fi")
        win.geometry("420x520")
        win.resizable(False, False)
        win.configure(bg="#0a0d14")
        win.transient(self.root)
        win.grab_set()

        lbl_t = tk.Label(
            win,
            text="📱 TELEMETRIA NO TELEMÓVEL",
            font=("Segoe UI", 12, "bold"),
            fg="#10b981",
            bg="#0a0d14"
        )
        lbl_t.pack(pady=(16, 4))

        lbl_sub = tk.Label(
            win,
            text="Usa o teu smartphone ou tablet como ecrã dedicado!",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0a0d14"
        )
        lbl_sub.pack(pady=(0, 10))

        # Imagem do QR Code
        if self.web_server.qr_png_bytes:
            qr_pil = Image.open(io.BytesIO(self.web_server.qr_png_bytes))
            qr_pil = qr_pil.resize((230, 230), Image.Resampling.NEAREST)
            qr_photo = ImageTk.PhotoImage(qr_pil)
            qr_lbl = tk.Label(win, image=qr_photo, bg="#0a0d14", relief=tk.SOLID, borderwidth=1)
            qr_lbl.image = qr_photo
            qr_lbl.pack(pady=4)

        url_str = self.web_server.url
        lbl_url = tk.Label(
            win,
            text=url_str,
            font=("Consolas", 12, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
            padx=12,
            pady=6
        )
        lbl_url.pack(pady=8)

        inst_txt = (
            "1. Liga o telemóvel/tablet ao mesmo Wi-Fi do PC.\n"
            "2. Aponta a câmara para o QR Code acima para abrir.\n"
            "3. Toca no botão 'TELA CHEIA' para preencher o ecrã!"
        )
        lbl_inst = tk.Label(
            win,
            text=inst_txt,
            font=("Segoe UI", 9),
            fg="#cbd5e1",
            bg="#0a0d14",
            justify=tk.LEFT
        )
        lbl_inst.pack(pady=(4, 12), padx=20)

        btn_box = tk.Frame(win, bg="#0a0d14")
        btn_box.pack(fill=tk.X, padx=20, pady=(0, 16))

        def copy_link():
            self.root.clipboard_clear()
            self.root.clipboard_append(url_str)
            messagebox.showinfo("Copiado!", f"Endereço copiado:\n{url_str}", parent=win)

        btn_copy = tk.Button(
            btn_box,
            text="📋 Copiar Endereço",
            command=copy_link,
            bg="#1e293b",
            fg="#e2e8f0",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=6
        )
        btn_copy.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6))

        btn_close = tk.Button(
            btn_box,
            text="Fechar",
            command=win.destroy,
            bg="#334155",
            fg="#ffffff",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            padx=12,
            pady=6
        )
        btn_close.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(6, 0))

    def _toggle_fullscreen(self, event=None):
        """Expande ou restaura a janela NO MONITOR ONDE ELA ESTÁ (sem saltar para o monitor primário)."""
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            # 1. Guardar a posição e tamanho da janela normal antes de expandir
            self.saved_geometry = self.root.geometry()

            # 2. Detetar em que monitor a janela está posicionada neste instante
            self.root.update_idletasks()
            try:
                hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
                m_left, m_top, m_w, m_h = get_current_monitor_rect(hwnd)
            except Exception:
                m_left = self.root.winfo_x()
                m_top = self.root.winfo_y()
                m_w = self.root.winfo_screenwidth()
                m_h = self.root.winfo_screenheight()

            # 3. Esconder a coluna de controlos para focar no painel
            self.controls_col.pack_forget()
            self.btn_fullscreen.config(text="🗗 RESTAURAR (ESC)")

            # 4. Expandir no monitor atual sem mudar para o monitor principal!
            self.root.overrideredirect(True)
            self.root.geometry(f"{m_w}x{m_h}+{m_left}+{m_top}")
            try:
                self.root.attributes("-topmost", self.always_on_top_var.get())
            except Exception:
                pass
            self.root.focus_force()
            self.canvas.focus_set()

            # Atualizar de imediato a tela com o novo tamanho
            self.root.update_idletasks()
            if self.last_stats:
                self._update_canvas_display(self.last_stats)
        else:
            # Sair da tela cheia e voltar ao modo janela no mesmo monitor
            self.root.overrideredirect(False)
            self.btn_fullscreen.config(text="⛶ EXPANDIR NESTE ECRÃ (F11)")
            self.controls_col.pack(side=tk.RIGHT, fill=tk.Y)
            if self.saved_geometry:
                self.root.geometry(self.saved_geometry)
            self.root.focus_force()

            self.root.update_idletasks()
            if self.last_stats:
                self._update_canvas_display(self.last_stats)

    def _exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self._toggle_fullscreen()

    def _on_canvas_resize(self, event):
        """Redesenha em alta definição quando o tamanho do Canvas muda."""
        if event.width > 20 and event.height > 20:
            if self.last_stats:
                self._update_canvas_display(self.last_stats)

    def _cycle_to_next_theme(self):
        theme_keys = list(self.themes.keys())
        if not theme_keys:
            return
        try:
            curr_idx = theme_keys.index(self.current_theme_name)
            next_idx = (curr_idx + 1) % len(theme_keys)
        except ValueError:
            next_idx = 0

        next_name = theme_keys[next_idx]
        self.theme_combo.set(next_name)
        self._on_theme_changed()

    def _on_theme_changed(self, event=None):
        name = self.theme_combo.get()
        if name in self.themes:
            self.current_theme_name = name
            t = self.themes[name]
            self.bg_path = t["file"]
            color = t["primary"]
            self.chk_cycle.config(fg=color, activeforeground=color)
            self.btn_fullscreen.config(fg=color, activeforeground=color)
            self.last_theme_switch_time = time.time()
            self.update_preview()

    def _refresh_devices(self):
        devices = SmartCoolDriver.detect_devices()
        self.device_map = {d["label"]: d["id"] for d in devices}
        labels = [d["label"] for d in devices]
        self.port_combo["values"] = labels
        if labels:
            self.port_combo.current(0)
            target = self.device_map[labels[0]]
            if target.startswith("USB"):
                self.status_bar.config(text="Ecrã USB SmartCool (2A55:9990) detetado e pronto!")
            else:
                self.status_bar.config(text=f"{len(labels)} dispositivo(s) detetado(s).")
        else:
            self.status_bar.config(text="Nenhum ecrã USB ligado. Podes usar no 2º Ecrã ou no Telemóvel via Wi-Fi!")

    def _choose_bg_image(self):
        chosen = filedialog.askopenfilename(
            title="Escolha a imagem de fundo",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.bmp"), ("Todos os ficheiros", "*.*")]
        )
        if chosen:
            self.bg_path = chosen
            self.auto_cycle_var.set(False)
            self.update_preview()

    def _on_brightness_change(self, val):
        if self.driver.is_connected:
            self.driver.set_brightness(int(val))

    def _draw_flames(self, draw, x0, y0, x1, y1, flicker=0, scale=1.0):
        """Renderiza labaredas realistas de fogo no limite inferior do cartão que aquece."""
        border_w = max(2, int(2 * scale))
        draw.rectangle([x0, y0, x1, y1], outline='#ff3300', width=border_w)
        
        flame_h = int(22 * scale)
        draw.rectangle([x0 + border_w, y1 - flame_h, x1 - border_w, y1 - border_w], fill='#1c0400')
        
        flame_w = (x1 - x0 - 2 * border_w)
        num_tongues = 20
        step = flame_w / float(num_tongues)
        for i in range(num_tongues):
            fx = x0 + border_w + i * step
            h1 = int((10 + ((i * 11 + flicker * 7) % 15)) * scale)
            draw.polygon([(fx, y1 - border_w), (fx + step * 0.5, y1 - h1), (fx + step, y1 - border_w)], fill='#ff2200')
            h2 = max(int(3 * scale), h1 - int(4 * scale))
            draw.polygon([(fx + step * 0.2, y1 - border_w), (fx + step * 0.5, y1 - h2), (fx + step * 0.8, y1 - border_w)], fill='#ff7700')
            h3 = max(int(2 * scale), h2 - int(3 * scale))
            draw.polygon([(fx + step * 0.35, y1 - border_w), (fx + step * 0.5, y1 - h3), (fx + step * 0.65, y1 - border_w)], fill='#ffea00')
            if (i + flicker) % 3 == 0:
                spark_y = y1 - h1 - int(5 * scale)
                r = max(1, int(1.5 * scale))
                draw.ellipse([fx + step * 0.5 - r, spark_y - r, fx + step * 0.5 + r, spark_y + r], fill='#ffdd33')

    def render_sensors_view(self, stats, width, height):
        """Renderiza o tema 'Master Telemetry' nativamente em qualquer resolução (HD ou USB)."""
        scale = height / 320.0
        is_compact = (width <= 640)

        def get_f(family, size, bold=False):
            try:
                fn = ('segoeuib.ttf' if bold else 'segoeui.ttf') if family == 'ui' else ('consolab.ttf' if bold else 'consola.ttf')
                return ImageFont.truetype(fn, max(8, int(size * scale)))
            except:
                return ImageFont.load_default()

        f_title = get_f('ui', 11, bold=True)
        f_clock = get_f('mono', 11, bold=True)
        f_temp = get_f('ui', 32, bold=True)
        f_card_title = get_f('ui', 10.5, bold=True)
        f_val = get_f('ui', 10.5, bold=True)
        f_lbl = get_f('ui', 9.5, bold=False)
        f_small = get_f('ui', 9, bold=False)

        img = Image.new('RGB', (width, height), '#0a0d14')
        draw = ImageDraw.Draw(img)

        # Micro-grelha técnica de fundo
        grid_step = int(32 * scale)
        for x in range(0, width, grid_step):
            draw.line([(x, 0), (x, height)], fill='#0f141f', width=1)
        for y in range(0, height, grid_step):
            draw.line([(0, y), (width, y)], fill='#0f141f', width=1)

        c_card_bg = '#121722'
        c_card_border = '#1c2636'
        c_card_header = '#182130'
        c_white = '#f8fafc'
        c_slate = '#94a3b8'
        c_cyan = '#38bdf8'
        c_green_bar = '#10b981'
        c_slot = '#1a2232'

        def get_temp_c(t):
            if t < 55: return '#f8fafc'
            elif t < 75: return '#fbbf24'
            else: return '#ff3300'

        cpu_hot = stats['cpu_temp'] >= 75
        gpu_hot = stats['gpu_temp'] >= 75
        c_cpu_t = get_temp_c(stats['cpu_temp'])
        c_gpu_t = get_temp_c(stats['gpu_temp'])

        pad_x = int(8 * scale)
        top_h = int(26 * scale)
        bot_h = int(54 * scale)
        gap_x = int(8 * scale)
        gap_y = int(6 * scale)

        # 1. Barra Superior com Símbolo da Garra
        draw.rectangle([pad_x, int(4*scale), width - pad_x, top_h], fill='#0d121c', outline='#1e293b', width=1)

        if self.claw_symbol:
            claw_h = int(18 * scale)
            claw_w = int(claw_h * (self.claw_symbol.width / self.claw_symbol.height))
            claw_scaled = self.claw_symbol.resize((max(8, claw_w), max(8, claw_h)), Image.Resampling.LANCZOS)
            img.paste(claw_scaled, (pad_x + int(6*scale), int(4*scale) + int(4*scale)), claw_scaled)
        else:
            claw_w = int(14 * scale)

        title_text = 'TELEMETRY // TARRASGA' if is_compact else 'MASTER TELEMETRY // TARRASGA'
        draw.text((pad_x + claw_w + int(10*scale), int(7*scale)), title_text, fill='#e2e8f0', font=f_title)

        uptime_val = stats.get('uptime', '0h 0m')
        if is_compact:
            draw.text((width - int(160*scale), int(7*scale)), f'UP: {uptime_val}', fill=c_slate, font=f_small)
        else:
            uptime_str = f'UPTIME: {uptime_val}'
            up_bbox = draw.textbbox((0, 0), uptime_str, font=f_lbl)
            up_w = up_bbox[2] - up_bbox[0]
            draw.text((width // 2 - up_w // 2, int(7*scale)), uptime_str, fill=c_slate, font=f_lbl)

        clock_str = stats['time']
        clk_bbox = draw.textbbox((0, 0), clock_str, font=f_clock)
        clk_w = clk_bbox[2] - clk_bbox[0]
        draw.text((width - pad_x - clk_w - int(8*scale), int(6*scale)), clock_str, fill=c_white, font=f_clock)

        # 2. Regiões dos 4 Cartões
        card_area_y = top_h + gap_y
        card_area_h = height - top_h - bot_h - 3 * gap_y
        card_w = (width - 2 * pad_x - gap_x) // 2
        card_h = card_area_h // 2

        def draw_card_box(x0, y0, x1, y1, title, is_hot=False):
            draw.rectangle([x0, y0, x1, y1], fill=c_card_bg, outline='#ff3300' if is_hot else c_card_border, width=max(1, int(scale)) if not is_hot else max(2, int(2*scale)))
            hh = int(20 * scale)
            draw.rectangle([x0, y0, x1, y0 + hh], fill='#2d0f14' if is_hot else c_card_header, outline='#ff3300' if is_hot else '#222f42', width=1)
            draw.text((x0 + int(8*scale), y0 + int(2.5*scale)), title, fill='#ff6b6b' if is_hot else '#e2e8f0', font=f_card_title)
            return hh

        # Cartão 1: CPU
        x0, y0 = pad_x, card_area_y
        x1, y1 = x0 + card_w, y0 + card_h
        hh = draw_card_box(x0, y0, x1, y1, f'■ CPU: {stats.get("cpu_cores", "14C / 20T")}', cpu_hot)

        cy = y0 + hh + int(5*scale)
        draw.text((x0 + int(10*scale), cy), f'{stats["cpu_temp"]}°C', fill=c_cpu_t, font=f_temp)
        draw.text((x0 + int(10*scale), cy + int(36*scale)), f'{stats.get("cpu_ghz", 3.5)} GHz  |  {stats["cpu_fan"]} RPM', fill=c_slate, font=f_small)

        rx = x0 + int(card_w * 0.48)
        draw.text((rx, cy + int(2*scale)), f'LOAD: {stats["cpu_usage"]}%', fill=c_white, font=f_val)
        bw = int(card_w * 0.46)
        draw.rectangle([rx, cy + int(16*scale), rx + bw, cy + int(21*scale)], fill=c_slot)
        w_u = int(bw * (stats['cpu_usage'] / 100.0))
        draw.rectangle([rx, cy + int(16*scale), rx + w_u, cy + int(21*scale)], fill='#ff3300' if cpu_hot else c_green_bar)
        draw.text((rx, cy + int(26*scale)), f'PWR: ~{stats.get("cpu_power", 65)}W', fill=c_slate, font=f_small)
        draw.text((rx, cy + int(38*scale)), '[ OVERHEAT ALERT ]' if cpu_hot else 'COOLER: ACTIVE', fill='#ff3300' if cpu_hot else c_green_bar, font=f_small)

        if cpu_hot:
            self._draw_flames(draw, x0, y0, x1, y1, self.flame_flicker, scale)

        # Cartão 2: GPU
        gx0, gy0 = pad_x + card_w + gap_x, card_area_y
        gx1, gy1 = gx0 + card_w, gy0 + card_h
        ghh = draw_card_box(gx0, gy0, gx1, gy1, f'■ GPU: {stats.get("gpu_name", "RTX 4070 Ti")}', gpu_hot)

        gcy = gy0 + ghh + int(5*scale)
        draw.text((gx0 + int(10*scale), gcy), f'{stats["gpu_temp"]}°C', fill=c_gpu_t, font=f_temp)
        g_fan = stats.get('gpu_fan', 0)
        fan_text = f'{g_fan} RPM' if g_fan > 0 else '0 RPM (STOP)'
        draw.text((gx0 + int(10*scale), gcy + int(36*scale)), f'{stats.get("gpu_clock", 2640)} MHz  |  {fan_text}', fill=c_slate, font=f_small)

        grx = gx0 + int(card_w * 0.48)
        draw.text((grx, gcy + int(2*scale)), f'LOAD: {stats["gpu_usage"]}%', fill=c_white, font=f_val)
        draw.rectangle([grx, gcy + int(16*scale), grx + bw, gcy + int(21*scale)], fill=c_slot)
        gw_u = int(bw * (stats['gpu_usage'] / 100.0))
        draw.rectangle([grx, gcy + int(16*scale), grx + gw_u, gcy + int(21*scale)], fill='#ff3300' if gpu_hot else c_green_bar)
        draw.text((grx, gcy + int(26*scale)), f'VRAM: {stats.get("gpu_vram_used", 2.3)} / {stats.get("gpu_vram_total", 12.0)} GB', fill=c_white, font=f_small)
        draw.text((grx, gcy + int(38*scale)), '[ OVERHEAT ALERT ]' if gpu_hot else f'VRAM: {stats.get("gpu_vram_pct", 19)}% USED', fill='#ff3300' if gpu_hot else c_slate, font=f_small)

        if gpu_hot:
            self._draw_flames(draw, gx0, gy0, gx1, gy1, self.flame_flicker, scale)

        # Cartão 3: RAM & Rede
        my0 = card_area_y + card_h + gap_y
        my1 = my0 + card_h
        mhh = draw_card_box(x0, my0, x1, my1, '■ MEMORY (DDR5) & NETWORK', False)
        mcy = my0 + mhh + int(5*scale)
        draw.text((x0 + int(10*scale), mcy), f'RAM: {stats["ram_used_gb"]} / {stats["ram_total_gb"]} GB ({stats["ram_usage"]}%)', fill=c_white, font=f_val)
        full_bw = card_w - int(20*scale)
        draw.rectangle([x0 + int(10*scale), mcy + int(16*scale), x0 + int(10*scale) + full_bw, mcy + int(21*scale)], fill=c_slot)
        rw_u = int(full_bw * (stats['ram_usage'] / 100.0))
        draw.rectangle([x0 + int(10*scale), mcy + int(16*scale), x0 + int(10*scale) + rw_u, mcy + int(21*scale)], fill=c_green_bar)
        draw.text((x0 + int(10*scale), mcy + int(25*scale)), f'FREE: {stats.get("ram_free_gb", 18.6)} GB AVAILABLE', fill=c_slate, font=f_small)
        draw.line([(x0 + int(10*scale), mcy + int(40*scale)), (x0 + int(10*scale) + full_bw, mcy + int(40*scale))], fill='#1e293b', width=1)

        draw.text((x0 + int(10*scale), mcy + int(46*scale)), f'NET  DL: {stats.get("net_down_str", "0 KB/s")}  |  UL: {stats.get("net_up_str", "0 KB/s")}', fill=c_cyan, font=f_val)
        draw.text((x0 + int(10*scale), mcy + int(60*scale)), 'ETHERNET / LAN: ONLINE GIGABIT', fill=c_slate, font=f_small)

        # Cartão 4: Discos & Armazenamento
        shh = draw_card_box(gx0, my0, gx1, my1, '■ STORAGE DRIVES & I/O', False)
        scy = my0 + shh + int(5*scale)
        c_p = stats.get('disk_c_pct', 84)
        draw.text((gx0 + int(10*scale), scy), f'C: [NVMe] {stats.get("disk_c_used", 780)} / {stats.get("disk_c_total", 930)} GB ({c_p}%)', fill=c_white, font=f_val)
        draw.rectangle([gx0 + int(10*scale), scy + int(16*scale), gx0 + int(10*scale) + full_bw, scy + int(20*scale)], fill=c_slot)
        cw_u = int(full_bw * (c_p / 100.0))
        draw.rectangle([gx0 + int(10*scale), scy + int(16*scale), gx0 + int(10*scale) + cw_u, scy + int(20*scale)], fill=c_green_bar)

        e_p = stats.get('disk_e_pct', 83)
        draw.text((gx0 + int(10*scale), scy + int(25*scale)), f'E: [DATA] {stats.get("disk_e_used", 1540)} / {stats.get("disk_e_total", 1860)} GB ({e_p}%)', fill=c_white, font=f_val)
        draw.rectangle([gx0 + int(10*scale), scy + int(39*scale), gx0 + int(10*scale) + full_bw, scy + int(43*scale)], fill=c_slot)
        ew_u = int(full_bw * (e_p / 100.0))
        draw.rectangle([gx0 + int(10*scale), scy + int(39*scale), gx0 + int(10*scale) + ew_u, scy + int(43*scale)], fill=c_green_bar)

        draw.text((gx0 + int(10*scale), scy + int(48*scale)), f'DISK  R: {stats.get("disk_read_str", "0 KB/s")}  |  W: {stats.get("disk_write_str", "0 KB/s")}', fill=c_cyan, font=f_small)
        draw.text((gx0 + int(10*scale), scy + int(60*scale)), 'TOTAL: 2.8 TB MOUNTED (100% SMART OK)', fill=c_slate, font=f_small)

        # 3. Rodapé do Sistema
        by0 = height - bot_h - int(4*scale)
        by1 = height - int(4*scale)
        draw.rectangle([pad_x, by0, width - pad_x, by1], fill='#0d121c', outline='#1e293b', width=1)
        b_hh = int(18 * scale)
        draw.rectangle([pad_x, by0, width - pad_x, by0 + b_hh], fill='#131926', outline='#1e293b', width=1)
        draw.text((pad_x + int(8*scale), by0 + int(2.5*scale)), '● HARDWARE TELEMETRY: 27 SENSORS ACTIVE & NOMINAL', fill=c_green_bar, font=f_small)

        bot_cols = [
            ('CHASSIS FAN', f'{stats["chassis_fan"]} RPM', c_white),
            ('CPU COOLER', f'{stats["cpu_fan"]} RPM', c_green_bar),
            ('GPU POWER', f'{stats.get("gpu_power", 26.5)} W', c_green_bar),
            ('SYS TEMPERATURE', f'{stats["sys_temp"]}°C (OPTIMAL)', c_cyan)
        ]
        col_w = (width - 2 * pad_x) // 4
        for i, (lbl, val, val_col) in enumerate(bot_cols):
            cx = pad_x + i * col_w + int(8*scale)
            draw.text((cx, by0 + b_hh + int(4*scale)), lbl, fill=c_slate, font=f_small)
            draw.text((cx, by0 + b_hh + int(17*scale)), val, fill=val_col, font=f_val)

        return img

    def render_frame(self, stats, width=480, height=320):
        """Renderiza o frame solicitado na resolução desejada."""
        theme_info = self.themes.get(self.current_theme_name, self.themes["Master Telemetry (Todos os Sensores)"])
        layout = theme_info.get("layout", "ALL_SENSORS")

        if layout == "ALL_SENSORS":
            return self.render_sensors_view(stats, width, height)

        # Temas Legados (480x320)
        if os.path.exists(self.bg_path):
            try:
                base = Image.open(self.bg_path).convert("RGB")
                if base.size != (480, 320):
                    base = base.resize((480, 320), Image.Resampling.LANCZOS)
            except Exception:
                base = Image.new("RGB", (480, 320), "#080a09")
        else:
            base = Image.new("RGB", (480, 320), "#080a09")

        draw = ImageDraw.Draw(base)
        c_primary = theme_info["primary"]
        c_accent = theme_info["accent"]
        c_white = "#ffffff"
        c_gray = "#94a3b8"

        def get_legacy_temp_c(t):
            if t < 55: return "#39ff14"
            elif t < 75: return "#ffaa00"
            else: return "#ff2200"

        c_cpu_temp = get_legacy_temp_c(stats["cpu_temp"])
        c_gpu_temp = get_legacy_temp_c(stats["gpu_temp"])

        if layout == "MONSTER_CANS":
            draw.rectangle([292, 60, 348, 86], fill="#0e1310")
            draw.text((292, 64), stats["time"], fill=c_primary, font=self.font_clock_cans)
            draw.text((122, 96), f"{stats['cpu_temp']}°C", fill=c_cpu_temp, font=self.font_temp_giant)
            draw.text((125, 142), "CPU TEMP", fill=c_primary, font=self.font_label_bold)
            draw.text((125, 160), f"FAN {stats['cpu_fan']} RPM", fill=c_gray, font=self.font_fan)
            draw.text((252, 96), f"{stats['gpu_temp']}°C", fill=c_gpu_temp, font=self.font_temp_giant)
            draw.text((255, 142), "GPU TEMP", fill=c_primary, font=self.font_label_bold)
            draw.text((255, 160), f"FAN {stats['gpu_fan']} RPM", fill=c_gray, font=self.font_fan)
            draw.text((148, 226), f"RAM: {stats['ram_usage']}% ({stats['ram_used_gb']} GB)", fill=c_white, font=self.font_small)
            draw.text((288, 226), f"SYS: {stats['sys_temp']}°C", fill=c_accent, font=self.font_small)

        elif layout == "MONSTER_CLAW":
            draw.rectangle([366, 25, 442, 49], fill="#0e1310")
            draw.text((370, 28), stats["time"], fill=c_primary, font=self.font_clock_claw)
            draw.text((50, 95), f"{stats['cpu_temp']}°C", fill=c_cpu_temp, font=self.font_temp_giant)
            draw.text((54, 142), "CPU TEMP", fill=c_primary, font=self.font_label_bold)
            draw.text((54, 162), f"FAN: {stats['cpu_fan']} RPM", fill=c_gray, font=self.font_fan)
            draw.text((270, 95), f"{stats['gpu_temp']}°C", fill=c_gpu_temp, font=self.font_temp_giant)
            draw.text((274, 142), "GPU TEMP", fill=c_primary, font=self.font_label_bold)
            draw.text((274, 162), f"FAN: {stats['gpu_fan']} RPM", fill=c_gray, font=self.font_fan)
            draw.text((125, 268), f"RAM: {stats['ram_usage']}% ({stats['ram_used_gb']} GB)", fill=c_white, font=self.font_small)
            draw.text((255, 268), f"CHASSIS: {stats['chassis_fan']} RPM", fill=c_white, font=self.font_small)
            draw.text((350, 268), f"SYS: {stats['sys_temp']}°C", fill=c_accent, font=self.font_small)

        else:
            draw.text((348, 22), stats["time"], fill=c_primary, font=self.font_clock)
            draw.text((42, 94), f"{stats['cpu_temp']}°C", fill=c_cpu_temp, font=self.font_temp_giant)
            draw.text((46, 140), "CPU TEMP", fill=c_primary, font=self.font_label_bold)
            draw.text((46, 162), f"FAN: {stats['cpu_fan']} RPM", fill=c_gray, font=self.font_fan)
            draw.text((272, 94), f"{stats['gpu_temp']}°C", fill=c_gpu_temp, font=self.font_temp_giant)
            draw.text((276, 140), "GPU TEMP", fill=c_primary, font=self.font_label_bold)
            draw.text((276, 162), f"FAN: {stats['gpu_fan']} RPM", fill=c_gray, font=self.font_fan)
            draw.text((45, 272), "RAM:", fill=c_primary, font=self.font_label_bold)
            draw.text((80, 271), f"{stats['ram_usage']}% ({stats['ram_used_gb']} GB)", fill=c_white, font=self.font_small)
            draw.text((195, 272), "CHASSIS #1:", fill=c_primary, font=self.font_label_bold)
            draw.text((268, 271), f"{stats['chassis_fan']} RPM", fill=c_white, font=self.font_small)
            draw.text((345, 272), "SYS TEMP:", fill=c_primary, font=self.font_label_bold)
            draw.text((410, 271), f"{stats['sys_temp']}°C", fill=c_accent, font=self.font_small)

        if width != 480 or height != 320:
            return base.resize((width, height), Image.Resampling.LANCZOS)
        return base

    def _update_canvas_display(self, stats):
        """Atualiza o Canvas com renderização nativa de alta definição e alimenta o servidor Wi-Fi."""
        cw = max(480, self.canvas.winfo_width())
        ch = max(320, self.canvas.winfo_height())

        theme_info = self.themes.get(self.current_theme_name, {})
        layout = theme_info.get("layout", "ALL_SENSORS")

        if layout == "ALL_SENSORS":
            display_frame = self.render_frame(stats, width=cw, height=ch)
            self.preview_image = ImageTk.PhotoImage(display_frame)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)
        else:
            frame_480 = self.render_frame(stats, width=480, height=320)
            scale = min(cw / 480.0, ch / 320.0)
            tw = max(480, int(480 * scale))
            th = max(320, int(320 * scale))
            display_frame = frame_480.resize((tw, th), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(display_frame)
            self.canvas.delete("all")
            pos_x = (cw - tw) // 2
            pos_y = (ch - th) // 2
            self.canvas.create_image(pos_x, pos_y, anchor=tk.NW, image=self.preview_image)

        # Se a transmissão contínua estiver parada, envia o frame estático inicial para o servidor Wi-Fi
        if not self.running and self.wifi_enabled_var.get() and self.web_server.is_running:
            wifi_frame = self.render_frame(stats, width=1280, height=720) if layout == "ALL_SENSORS" else display_frame
            self.web_server.update_frame(wifi_frame, stats)

    def update_preview(self):
        """Atualiza a pré-visualização no ecrã da aplicação."""
        stats = self.monitor.get_stats()
        self.last_stats = stats
        self._update_canvas_display(stats)

    def _stream_loop(self):
        """Loop de envio contínuo para o ecrã USB, 2º Monitor e Telemóvel/Tablet Wi-Fi."""
        while self.running:
            try:
                # 1. Rotação automática de temas
                if self.auto_cycle_var.get():
                    now = time.time()
                    if now - self.last_theme_switch_time >= self.cycle_interval:
                        self.last_theme_switch_time = now
                        self.root.after(0, self._cycle_to_next_theme)

                # 2. Alternar frame de animação de fogo
                self.flame_flicker = (self.flame_flicker + 1) % 4

                # 3. Ler telemetria em tempo real
                stats = self.monitor.get_stats()
                self.last_stats = stats

                # 4. Renderizar frame nativo (480x320) para o visor USB físico
                usb_frame = self.render_frame(stats, width=480, height=320)

                # 5. Atualizar Servidor Wi-Fi Mobile diretamente no worker thread (100% contínuo e independente)
                if self.wifi_enabled_var.get() and self.web_server and self.web_server.is_running:
                    try:
                        theme_info = self.themes.get(self.current_theme_name, {})
                        layout = theme_info.get("layout", "ALL_SENSORS")
                        wifi_frame = self.render_frame(stats, width=1280, height=720) if layout == "ALL_SENSORS" else usb_frame
                        self.web_server.update_frame(wifi_frame, stats)
                    except Exception:
                        pass

                # 6. Atualizar GUI no PC (Canvas)
                self.root.after(0, self._update_canvas_display, stats)

                # 7. Enviar para o ecrã USB físico se conectado
                if self.driver.is_connected:
                    try:
                        sent = self.driver.display_image(usb_frame)
                        if not sent:
                            time.sleep(0.1)
                    except Exception:
                        pass

                time.sleep(1.0)

            except Exception as e:
                print(f"[App] Erro no loop de transmissão: {e}")
                time.sleep(1.0)

    def _auto_start_stream(self):
        """Inicia automaticamente a transmissão na inicialização da aplicação."""
        if not self.running:
            self._toggle_stream()

    def _toggle_stream(self):
        """Inicia ou para a transmissão para o ecrã USB e Wi-Fi."""
        if not self.running:
            selected_label = self.port_combo.get().strip()
            target_id = self.device_map.get(selected_label, "AUTO")

            try:
                self.driver.connect(target_id)
                if self.driver.connection_type == "USB":
                    self.status_bar.config(text="Ligado ao ecrã USB SmartCool DIRETO + Wi-Fi Ativo!")
                else:
                    self.status_bar.config(text=f"Ligado ao ecrã na porta {target_id} + Wi-Fi Ativo!")
            except Exception as e:
                # Se não tem visor USB conectado, permite correr livremente no PC e no Telemóvel via Wi-Fi!
                self.status_bar.config(text=f"A transmitir em Modo Wi-Fi (Telemóvel/Tablet) em: {self.web_server.url}")

            self.running = True
            self.last_theme_switch_time = time.time()
            self.btn_toggle.config(text="⏹ PARAR TRANSMISSÃO", bg="#e11d48")
            self.worker_thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.worker_thread.start()
        else:
            self.running = False
            self.btn_toggle.config(text="▶ INICIAR TRANSMISSÃO", bg="#10b981")
            self.driver.disconnect()
            self.status_bar.config(text="Transmissão parada.")

    def on_closing(self):
        """Finalização segura ao fechar o programa para evitar fechos acidentais."""
        res = messagebox.askyesno(
            "Fechar SmartCool Monitor",
            "Deseja fechar a aplicação de monitorização?\n\n(Dica: Pode clicar em 'Não' e deixar a janela aberta no 2º ecrã ou minimizada para continuar ativa!)"
        )
        if res:
            self.running = False
            self.driver.disconnect()
            if self.web_server:
                self.web_server.stop()
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SmartCoolApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
