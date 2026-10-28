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
import math
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


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', RECT),
        ('rcWork', RECT),
        ('dwFlags', wintypes.DWORD),
        ('szDevice', wintypes.WCHAR * 32)
    ]


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


def get_all_monitors():
    """Devolve a lista detalhada de todos os monitores conectados ao Windows."""
    monitors = []
    def _enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
        r = mi.rcMonitor
        is_primary = bool(mi.dwFlags & 1)
        w = r.right - r.left
        h = r.bottom - r.top
        dev = mi.szDevice.replace("\\\\.\\", "")
        orient = "Vertical" if h > w else "16:9"
        pri = " [Principal]" if is_primary else ""
        label = f"Ecrã {len(monitors)+1} ({dev}): {w}x{h} ({orient}){pri}"
        monitors.append({
            'index': len(monitors) + 1,
            'device': mi.szDevice,
            'label': label,
            'left': r.left,
            'top': r.top,
            'width': w,
            'height': h,
            'is_primary': is_primary,
            'is_portrait': h > w
        })
        return True

    try:
        MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_enum_proc), 0)
    except Exception:
        pass

    if not monitors:
        monitors.append({
            'index': 1,
            'device': 'DISPLAY1',
            'label': f'Ecrã 1: {user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)} [Principal]',
            'left': 0,
            'top': 0,
            'width': user32.GetSystemMetrics(0),
            'height': user32.GetSystemMetrics(1),
            'is_primary': True,
            'is_portrait': False
        })
    return monitors


class SmartCoolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monster Telemetria // 2º Ecrã, USB & Wi-Fi [TARRASGA]")
        self.root.geometry("1120x740")
        self.root.minsize(880, 600)
        self.root.configure(bg="#0a0d14")

        # Configurar Ícone Oficial na Barra de Tarefas e Título da Janela (Termómetro)
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Tarrasga.MonsterTelemetria.1")
        except Exception:
            pass

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.base_dir, "assets")

        ico_path = os.path.join(self.assets_dir, "monster_telemetria_icon.ico")
        if not os.path.exists(ico_path):
            ico_path = os.path.join(self.assets_dir, "thermometer.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
            try:
                png_ico = os.path.join(self.assets_dir, "monster_telemetria_icon.png")
                if os.path.exists(png_ico):
                    self._app_icon_img = ImageTk.PhotoImage(file=png_ico)
                else:
                    self._app_icon_img = ImageTk.PhotoImage(file=ico_path)
                self.root.iconphoto(True, self._app_icon_img)
            except Exception:
                pass

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
            },
            "Velocímetros de Carro (Instrument Cluster)": {
                "file": os.path.join(self.assets_dir, "preview_theme_speedometer.png"),
                "layout": "SPEEDOMETER",
                "primary": "#38bdf8",
                "dim": "#0a192f",
                "accent": "#ef4444"
            },
            "Cockpit de Avião (Fighter Jet HUD)": {
                "file": os.path.join(self.assets_dir, "preview_theme_airplane.png"),
                "layout": "AIRPLANE_COCKPIT",
                "primary": "#00ff66",
                "dim": "#031d10",
                "accent": "#00e5ff"
            },
            "Cockpit de Carro GT (Racing Telemetry)": {
                "file": os.path.join(self.assets_dir, "preview_theme_gt.png"),
                "layout": "GT_COCKPIT",
                "primary": "#ef4444",
                "dim": "#2a0808",
                "accent": "#10b981"
            },
            "Ford Fiesta XR2 Mk2 (Classic Hot Hatch)": {
                "file": os.path.join(self.assets_dir, "preview_theme_xr2.png"),
                "layout": "XR2_MK2",
                "primary": "#e11d48",
                "dim": "#1c0a10",
                "accent": "#0284c7"
            },
            "Counter-Strike 2 (CS2 Tactical HUD)": {
                "file": os.path.join(self.assets_dir, "preview_theme_cs2.png"),
                "layout": "CS2",
                "primary": "#f59e0b",
                "dim": "#18140f",
                "accent": "#38bdf8"
            },
            "PUBG Battlegrounds (Erangel Survival HUD)": {
                "file": os.path.join(self.assets_dir, "preview_theme_pubg.png"),
                "layout": "PUBG",
                "primary": "#facc15",
                "dim": "#1a1608",
                "accent": "#ef4444"
            },
            "Peugeot 508 SW (Digital i-Cockpit GT)": {
                "file": os.path.join(self.assets_dir, "preview_theme_peugeot_508.png"),
                "layout": "PEUGEOT_508",
                "primary": "#00d2ff",
                "dim": "#081b24",
                "accent": "#d4ff00"
            },
            "Mesa de Mistura DJ (Studio Audio Equalizer)": {
                "file": os.path.join(self.assets_dir, "preview_theme_mixer.png"),
                "layout": "DJ_MIXER",
                "primary": "#10b981",
                "dim": "#081812",
                "accent": "#00d2ff"
            },
            "HUD Overlay Transparente (Glass HUD)": {
                "file": os.path.join(self.assets_dir, "preview_theme_transparent.png"),
                "layout": "TRANSPARENT_HUD",
                "primary": "#00e5ff",
                "dim": "#061522",
                "accent": "#10b981"
            },
            "Cyber Neon Dual (Azul & Vermelho)": {
                "file": os.path.join(self.assets_dir, "preview_theme_neon_dual.png"),
                "layout": "NEON_DUAL",
                "primary": "#00e5ff",
                "dim": "#061826",
                "accent": "#ff0055"
            },
            "Monster Telemetria (Logo Oficial)": {
                "file": os.path.join(self.assets_dir, "preview_theme_monster_official.png"),
                "layout": "MONSTER_OFFICIAL",
                "primary": "#39ff14",
                "dim": "#081c0e",
                "accent": "#00e5ff"
            }
        }

        self.current_theme_name = "Master Telemetry (Todos os Sensores)"
        self.bg_path = self.themes[self.current_theme_name]["file"]

        # Carregar Logótipo Oficial Monster Telemetria
        official_logo_path = os.path.join(self.assets_dir, "monster_telemetria_logo.png")
        if os.path.exists(official_logo_path):
            try:
                self.monster_official_logo = Image.open(official_logo_path).convert("RGBA")
            except Exception:
                self.monster_official_logo = None
        else:
            self.monster_official_logo = None

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

        # Controlo de Transparência e Overlay para o 2º Ecrã
        self.CHROMA_KEY_COLOR = "#010203"
        self.transparent_mode_var = tk.BooleanVar(value=False)
        self.opacity_scale_var = tk.DoubleVar(value=1.0)
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Manter Janela Sempre no Topo (Always on Top)
        self.always_on_top_var = tk.BooleanVar(value=True)
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        # Servidor Web Wi-Fi para Telemóvel / Tablet
        self.wifi_enabled_var = tk.BooleanVar(value=True)
        self.web_server = TelemetryWebServer(port=8080)
        self.web_server.set_theme_callbacks(
            get_themes_fn=self._get_themes_catalog,
            change_theme_fn=self._handle_remote_theme_change
        )
        self.web_server.start()

        # Drivers
        self.driver = SmartCoolDriver()
        self.monitor = HardwareMonitor()
        try:
            from fan_controller import FanController
            self.fan_controller = FanController.get_instance()
        except Exception:
            self.fan_controller = None
        self.device_map = {}

        # Controlo de Threads
        self.running = False
        self.worker_thread = None

        # Carregar fontes padrão para layouts legados
        self._load_legacy_fonts()

        # Construir UI Responsiva
        self._build_ui()
        self._refresh_devices()

        # Estado da Barra Lateral de Controlos
        self.sidebar_visible = True

        # Atalhos de Teclado para 2º Ecrã, Transparência HUD e Menu Lateral
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)
        self.canvas.bind("<F11>", self._toggle_fullscreen)
        self.canvas.bind("<Escape>", self._exit_fullscreen)
        self.root.bind("<t>", self._toggle_transparency_mode)
        self.root.bind("<T>", self._toggle_transparency_mode)
        self.canvas.bind("<t>", self._toggle_transparency_mode)
        self.canvas.bind("<T>", self._toggle_transparency_mode)
        self.root.bind("<m>", self._toggle_sidebar)
        self.root.bind("<M>", self._toggle_sidebar)
        self.canvas.bind("<m>", self._toggle_sidebar)
        self.canvas.bind("<M>", self._toggle_sidebar)

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
        self.header_frame = tk.Frame(self.root, bg="#0d111a", padx=16, pady=10)
        self.header_frame.pack(fill=tk.X)

        self.lbl_title = tk.Label(
            self.header_frame,
            text="MONSTER TELEMETRIA // 2º ECRÃ, USB & WI-FI",
            font=("Segoe UI", 12, "bold"),
            fg="#e2e8f0",
            bg="#0d111a"
        )
        self.lbl_title.pack(side=tk.LEFT)

        subtitle = tk.Label(
            self.header_frame,
            text="27 Sensores // TARRASGA",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0d111a"
        )
        subtitle.pack(side=tk.LEFT, padx=12)

        # Botão para Encolher / Expandir Menu Lateral (Ficar só o Tema)
        self.btn_toggle_sidebar = tk.Button(
            self.header_frame,
            text="◀ RECOLHER MENU (M)",
            command=self._toggle_sidebar,
            bg="#1e293b",
            fg="#38bdf8",
            activebackground="#2e3e56",
            activeforeground="#38bdf8",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4
        )
        self.btn_toggle_sidebar.pack(side=tk.RIGHT, padx=(8, 0))

        # Botão de Tela Cheia para o 2º Ecrã
        self.btn_fullscreen = tk.Button(
            self.header_frame,
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

        # Botão Modo Overlay Transparente (2º Ecrã)
        self.btn_transparency = tk.Button(
            self.header_frame,
            text="✨ OVERLAY (T)",
            command=self._toggle_transparency_mode,
            bg="#1e293b",
            fg="#00e5ff",
            activebackground="#2e3e56",
            activeforeground="#00e5ff",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4
        )
        self.btn_transparency.pack(side=tk.RIGHT, padx=(0, 8))

        # Botão Fixar Sempre no Topo (Always on Top)
        self.btn_topmost = tk.Button(
            self.header_frame,
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
            self.header_frame,
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
        self.content_frame = tk.Frame(self.root, bg="#0a0d14", padx=12, pady=10)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Coluna Esquerda: Ecrã de Pré-visualização Expansível
        self.preview_col = tk.Frame(self.content_frame, bg="#0a0d14")
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

        # Botão Flutuante (quando o menu está recolhido e em modo "Só o Tema" / Transparente)
        self.btn_floating_menu = tk.Button(
            self.canvas,
            text="☰ MOSTRAR MENU (M)",
            command=self._toggle_sidebar,
            bg="#1e293b",
            fg="#39ff14",
            activebackground="#0f172a",
            activeforeground="#39ff14",
            relief=tk.FLAT,
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=4,
            cursor="hand2"
        )

        # Suporte para arrastar a janela clicando no Canvas ou Cabeçalho
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.header_frame.bind("<ButtonPress-1>", self._on_drag_start)
        self.header_frame.bind("<B1-Motion>", self._on_drag_motion)

        # Coluna Direita: Barra Lateral de Controlos (com Scrollbar suave para acomodar todos os controlos)
        self.controls_col = tk.Frame(self.content_frame, bg="#0d111a", width=310)
        self.controls_col.pack(side=tk.RIGHT, fill=tk.Y)
        self.controls_col.pack_propagate(False)

        ctrl_canvas = tk.Canvas(self.controls_col, bg="#0d111a", highlightthickness=0)
        ctrl_scrollbar = ttk.Scrollbar(self.controls_col, orient="vertical", command=ctrl_canvas.yview)
        self.controls_inner = tk.Frame(ctrl_canvas, bg="#0d111a", padx=10, pady=8)

        self.controls_inner.bind("<Configure>", lambda e: ctrl_canvas.configure(scrollregion=ctrl_canvas.bbox("all")))
        ctrl_canvas.create_window((0, 0), window=self.controls_inner, anchor="nw", width=290)
        ctrl_canvas.configure(yscrollcommand=ctrl_scrollbar.set)

        ctrl_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        ctrl_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_ctrl_wheel(e):
            ctrl_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        ctrl_canvas.bind("<MouseWheel>", _on_ctrl_wheel)
        self.controls_inner.bind("<MouseWheel>", _on_ctrl_wheel)

        # Botão Destaque: Encolher Menu Lateral (Ficar Só o Tema)
        self.btn_collapse_ctrl = tk.Button(
            self.controls_inner,
            text="◀ RECOLHER MENU // SÓ O TEMA (M)",
            command=self._toggle_sidebar,
            bg="#1e293b",
            fg="#39ff14",
            activebackground="#0f172a",
            activeforeground="#39ff14",
            relief=tk.FLAT,
            font=("Segoe UI", 9, "bold"),
            pady=6,
            cursor="hand2"
        )
        self.btn_collapse_ctrl.pack(fill=tk.X, pady=(0, 10))

        # Grupo: Seletor de Tema
        lbl_theme = tk.Label(self.controls_inner, text="ESCOLHA O TEMA:", font=("Segoe UI", 9, "bold"), fg="#e2e8f0", bg="#0d111a")
        lbl_theme.pack(anchor="w", pady=(0, 4))

        self.theme_combo = ttk.Combobox(self.controls_inner, state="readonly", values=list(self.themes.keys()))
        self.theme_combo.current(0)
        self.theme_combo.pack(fill=tk.X, pady=(0, 6))
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_changed)

        # Checkbox de Rotação Automática
        self.chk_cycle = tk.Checkbutton(
            self.controls_inner,
            text="🔄 Alternar temas a cada 10s",
            variable=self.auto_cycle_var,
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#0d111a",
            selectcolor="#0a0d14",
            activebackground="#0d111a",
            activeforeground="#10b981"
        )
        self.chk_cycle.pack(anchor="w", pady=(0, 4))

        # Checkbox Sempre no Topo (Always on Top)
        self.chk_topmost = tk.Checkbutton(
            self.controls_inner,
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
        self.chk_topmost.pack(anchor="w", pady=(0, 6))

        # Grupo: Seletor de Monitor (Multi-Monitor Auto-Fit)
        mon_box = tk.LabelFrame(
            self.controls_inner,
            text="🖥️ SELETOR DE MONITOR (AUTO-FIT)",
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#0d111a",
            padx=8,
            pady=8
        )
        mon_box.pack(fill=tk.X, pady=(0, 10))

        lbl_mon = tk.Label(mon_box, text="Enviar ecrã para monitor:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0d111a")
        lbl_mon.pack(anchor="w", pady=(0, 3))

        self.monitors_list = get_all_monitors()
        mon_names = [m["label"] for m in self.monitors_list]
        self.mon_combo = ttk.Combobox(mon_box, state="readonly", values=mon_names)
        if mon_names:
            default_m_idx = 1 if len(mon_names) > 1 else 0
            self.mon_combo.current(default_m_idx)
        self.mon_combo.pack(fill=tk.X, pady=(0, 6))

        mon_btn_row = tk.Frame(mon_box, bg="#0d111a")
        mon_btn_row.pack(fill=tk.X, pady=(2, 0))

        btn_send_mon = tk.Button(
            mon_btn_row,
            text="⛶ EXPANDIR",
            command=self._on_expand_to_selected_monitor,
            bg="#1e293b",
            fg="#10b981",
            activebackground="#2e3e56",
            activeforeground="#10b981",
            relief=tk.FLAT,
            font=("Segoe UI", 8, "bold"),
            pady=3
        )
        btn_send_mon.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        btn_move_win = tk.Button(
            mon_btn_row,
            text="🗗 MOVER",
            command=self._on_move_window_to_selected_monitor,
            bg="#1e293b",
            fg="#38bdf8",
            activebackground="#2e3e56",
            activeforeground="#38bdf8",
            relief=tk.FLAT,
            font=("Segoe UI", 8, "bold"),
            pady=3
        )
        btn_move_win.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        # Grupo: Controlo de Velocidade de Ventoinhas (CPU e GPU)
        fan_box = tk.LabelFrame(
            self.controls_inner,
            text="⚡ CONTROLO DE VENTOINHAS (FANS)",
            font=("Segoe UI", 8, "bold"),
            fg="#00e5ff",
            bg="#0d111a",
            padx=8,
            pady=8
        )
        fan_box.pack(fill=tk.X, pady=(0, 10))

        # CPU Fan Row
        cpu_fan_hdr = tk.Frame(fan_box, bg="#0d111a")
        cpu_fan_hdr.pack(fill=tk.X, pady=(0, 2))
        tk.Label(cpu_fan_hdr, text="CPU Fan:", font=("Segoe UI", 8, "bold"), fg="#00e5ff", bg="#0d111a").pack(side=tk.LEFT)
        self.lbl_cpu_fan_val = tk.Label(cpu_fan_hdr, text="AUTO (Curva)", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#0d111a")
        self.lbl_cpu_fan_val.pack(side=tk.RIGHT)

        self.cpu_fan_slider = tk.Scale(
            fan_box,
            from_=20,
            to=100,
            orient=tk.HORIZONTAL,
            bg="#0d111a",
            fg="#00e5ff",
            highlightthickness=0,
            troughcolor="#1e293b",
            activebackground="#00e5ff",
            command=self._on_cpu_fan_slider
        )
        self.cpu_fan_slider.set(60)
        self.cpu_fan_slider.pack(fill=tk.X, pady=(0, 4))

        # GPU Fan Row
        gpu_fan_hdr = tk.Frame(fan_box, bg="#0d111a")
        gpu_fan_hdr.pack(fill=tk.X, pady=(0, 2))
        tk.Label(gpu_fan_hdr, text="GPU Fan (RTX):", font=("Segoe UI", 8, "bold"), fg="#ff0055", bg="#0d111a").pack(side=tk.LEFT)
        self.lbl_gpu_fan_val = tk.Label(gpu_fan_hdr, text="AUTO (Driver)", font=("Segoe UI", 8, "bold"), fg="#ff3366", bg="#0d111a")
        self.lbl_gpu_fan_val.pack(side=tk.RIGHT)

        self.gpu_fan_slider = tk.Scale(
            fan_box,
            from_=20,
            to=100,
            orient=tk.HORIZONTAL,
            bg="#0d111a",
            fg="#ff0055",
            highlightthickness=0,
            troughcolor="#1e293b",
            activebackground="#ff0055",
            command=self._on_gpu_fan_slider
        )
        self.gpu_fan_slider.set(50)
        self.gpu_fan_slider.pack(fill=tk.X, pady=(0, 4))

        # Botões de Perfis Rápidos
        prof_row = tk.Frame(fan_box, bg="#0d111a")
        prof_row.pack(fill=tk.X, pady=(4, 2))
        for p_lbl, p_code, p_c in [("Auto", "AUTO", "#10b981"), ("Silencioso", "SILENCIOSO", "#38bdf8"), ("Gaming", "GAMING", "#f59e0b"), ("Turbo 100%", "TURBO", "#ef4444")]:
            b = tk.Button(
                prof_row,
                text=p_lbl,
                command=lambda c=p_code: self._apply_fan_profile(c),
                bg="#1e293b",
                fg=p_c,
                activebackground="#334155",
                activeforeground=p_c,
                relief=tk.FLAT,
                font=("Segoe UI", 7, "bold"),
                pady=2
            )
            b.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # Grupo: Modo Transparente & Opacidade para o 2º Ecrã
        trans_box = tk.LabelFrame(
            self.controls_inner,
            text="TRANSPARÊNCIA (2º ECRÃ / OVERLAY)",
            font=("Segoe UI", 8, "bold"),
            fg="#00e5ff",
            bg="#0d111a",
            padx=8,
            pady=8
        )
        trans_box.pack(fill=tk.X, pady=(0, 10))

        self.chk_trans = tk.Checkbutton(
            trans_box,
            text="✨ Fundo Invisível (Chroma HUD)",
            variable=self.transparent_mode_var,
            command=self._on_transparency_changed,
            font=("Segoe UI", 8, "bold"),
            fg="#00e5ff",
            bg="#0d111a",
            selectcolor="#0a0d14",
            activebackground="#0d111a",
            activeforeground="#00e5ff"
        )
        self.chk_trans.pack(anchor="w", pady=(0, 4))

        lbl_alpha = tk.Label(trans_box, text="Opacidade da Janela:", font=("Segoe UI", 8), fg="#94a3b8", bg="#0d111a")
        lbl_alpha.pack(anchor="w", pady=(2, 2))

        alpha_btns_row = tk.Frame(trans_box, bg="#0d111a")
        alpha_btns_row.pack(fill=tk.X, pady=(2, 2))
        for a_val, a_lbl in [(1.0, "100%"), (0.85, "85%"), (0.70, "70%"), (0.50, "50%")]:
            b = tk.Button(
                alpha_btns_row,
                text=a_lbl,
                command=lambda val=a_val: self._set_window_opacity(val),
                bg="#1e293b",
                fg="#cbd5e1",
                activebackground="#334155",
                activeforeground="#00e5ff",
                relief=tk.FLAT,
                font=("Segoe UI", 8, "bold"),
                pady=2
            )
            b.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # Grupo: Servidor Wi-Fi para Telemóvel / Tablet
        wifi_box = tk.LabelFrame(
            self.controls_inner,
            text="TRANSMISSÃO WI-FI (MOBILE)",
            font=("Segoe UI", 8, "bold"),
            fg="#10b981",
            bg="#0d111a",
            padx=8,
            pady=8
        )
        wifi_box.pack(fill=tk.X, pady=(0, 10))

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
        lbl_port = tk.Label(self.controls_inner, text="DISPOSITIVO USB:", font=("Segoe UI", 8, "bold"), fg="#e2e8f0", bg="#0d111a")
        lbl_port.pack(anchor="w", pady=(0, 4))

        port_row = tk.Frame(self.controls_inner, bg="#0d111a")
        port_row.pack(fill=tk.X, pady=(0, 8))

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
            self.controls_inner,
            text="📁 Carregar Outra Imagem...",
            command=self._choose_bg_image,
            bg="#1e293b",
            fg="#cbd5e1",
            relief=tk.FLAT,
            pady=4
        )
        btn_choose_bg.pack(fill=tk.X, pady=(0, 8))

        # Botão Iniciar Transmissão USB & Wi-Fi
        self.btn_toggle = tk.Button(
            self.controls_inner,
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
            self.controls_inner,
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

    def _on_cpu_fan_slider(self, val):
        pct = int(float(val))
        if self.fan_controller:
            res = self.fan_controller.set_cpu_fan(pct, is_auto=False)
            rpm = res.get("target_rpm", self.fan_controller.get_cpu_rpm_for_pct(pct))
            self.lbl_cpu_fan_val.config(text=f"{pct}% ({rpm} RPM)")
        else:
            self.lbl_cpu_fan_val.config(text=f"{pct}%")
        if self.last_stats:
            self.last_stats["cpu_fan_pct"] = pct
            self.last_stats["cpu_fan_auto"] = False
            self.last_stats["cpu_fan"] = self.fan_controller.get_cpu_rpm_for_pct(pct) if self.fan_controller else int(1000 + pct * 15)

    def _on_gpu_fan_slider(self, val):
        pct = int(float(val))
        if self.fan_controller:
            res = self.fan_controller.set_gpu_fan(pct, is_auto=False)
            rpm = res.get("target_rpm", self.fan_controller.get_gpu_rpm_for_pct(pct))
            self.lbl_gpu_fan_val.config(text=f"{pct}% ({rpm} RPM)")
        else:
            self.lbl_gpu_fan_val.config(text=f"{pct}%")
        if self.last_stats:
            self.last_stats["gpu_fan_pct"] = pct
            self.last_stats["gpu_fan_auto"] = False
            self.last_stats["gpu_fan_rpm"] = self.fan_controller.get_gpu_rpm_for_pct(pct) if self.fan_controller else int(pct * 29)

    def _apply_fan_profile(self, profile):
        if not self.fan_controller:
            return
        self.fan_controller.apply_profile(profile)
        p = profile.upper()
        if "AUTO" in p:
            self.lbl_cpu_fan_val.config(text="AUTO (Curva)")
            self.lbl_gpu_fan_val.config(text="AUTO (Driver)")
            self.status_bar.config(text="Ventoinhas: Modo AUTOMÁTICO restaurado (curvas inteligentes do sistema).")
        else:
            c_pct = self.fan_controller.cpu_fan_target
            g_pct = self.fan_controller.gpu_fan_target
            self.cpu_fan_slider.set(c_pct)
            self.gpu_fan_slider.set(g_pct)
            c_rpm = self.fan_controller.get_cpu_rpm_for_pct(c_pct)
            g_rpm = self.fan_controller.get_gpu_rpm_for_pct(g_pct)
            self.lbl_cpu_fan_val.config(text=f"{c_pct}% ({c_rpm} RPM)")
            self.lbl_gpu_fan_val.config(text=f"{g_pct}% ({g_rpm} RPM)")
            self.status_bar.config(text=f"Ventoinhas: Perfil {profile} ativado (CPU: {c_pct}% / GPU: {g_pct}%).")

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

    def move_to_monitor(self, monitor_index, expand=True):
        """Move a janela para o monitor indicado e ajusta automaticamente (Auto-Fit universal)."""
        monitors = get_all_monitors()
        if not (0 <= monitor_index < len(monitors)):
            return
        target = monitors[monitor_index]
        mx, my, mw, mh = target['left'], target['top'], target['width'], target['height']

        if expand:
            if not self.is_fullscreen:
                self.saved_geometry = self.root.geometry()
                self.is_fullscreen = True
                self.controls_col.pack_forget()
                self.header_frame.pack_forget()
                self.status_bar.pack_forget()
                self.content_frame.config(padx=0, pady=0)
                self.preview_col.config(padx=0, pady=0)
                self.btn_fullscreen.config(text="🗗 RESTAURAR (ESC)")

            self.root.overrideredirect(True)
            self.root.geometry(f"{mw}x{mh}+{mx}+{my}")
            try:
                self.root.attributes("-topmost", self.always_on_top_var.get())
            except Exception:
                pass
            self.root.focus_force()
            self.canvas.focus_set()
        else:
            if self.is_fullscreen:
                self._exit_fullscreen()
            win_w = min(1120, int(mw * 0.9))
            win_h = min(740, int(mh * 0.9))
            win_x = mx + (mw - win_w) // 2
            win_y = my + (mh - win_h) // 2
            self.root.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")

        self.root.update_idletasks()
        if self.last_stats:
            self._update_canvas_display(self.last_stats)
        self.status_bar.config(text=f"Ajustado com sucesso para {target['label']}")

    def _on_expand_to_selected_monitor(self):
        sel_idx = self.mon_combo.current()
        if sel_idx >= 0:
            self.move_to_monitor(sel_idx, expand=True)

    def _on_move_window_to_selected_monitor(self):
        sel_idx = self.mon_combo.current()
        if sel_idx >= 0:
            self.move_to_monitor(sel_idx, expand=False)

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

            # 3. Esconder a coluna de controlos, cabeçalho e barra de estado para focar no painel / overlay
            self.controls_col.pack_forget()
            self.header_frame.pack_forget()
            self.status_bar.pack_forget()
            self.content_frame.config(padx=0, pady=0)
            self.preview_col.config(padx=0, pady=0)
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
            self.header_frame.pack(fill=tk.X, before=self.content_frame)
            self.content_frame.config(padx=12, pady=10)
            if self.sidebar_visible:
                self.preview_col.pack_forget()
                self.controls_col.pack(side=tk.RIGHT, fill=tk.Y)
                self.preview_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
            else:
                self.preview_col.pack_configure(padx=0)
            self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
            if self.saved_geometry:
                self.root.geometry(self.saved_geometry)
            self.root.focus_force()

            self.root.update_idletasks()
            if self.last_stats:
                self._update_canvas_display(self.last_stats)

    def _exit_fullscreen(self, event=None):
        if self.is_fullscreen:
            self._toggle_fullscreen()
        elif not self.sidebar_visible:
            self._toggle_sidebar()

    def _toggle_sidebar(self, event=None):
        """Encolhe ou expande o menu lateral de controlos.
        Se o modo transparente estiver ativo, esconde também o cabeçalho e rodapé
        para ficar LITERAMENTE SÓ O TEMA (HUD puro transparente flutuante) sem tapar o 2º ecrã!
        """
        self.sidebar_visible = not self.sidebar_visible
        t_info = self.themes.get(self.current_theme_name, {})
        is_transparent = (self.transparent_mode_var.get() or t_info.get("layout") == "TRANSPARENT_HUD")

        if not self.sidebar_visible:
            # 1. Encolher menu lateral
            self.controls_col.pack_forget()
            self.preview_col.pack_configure(padx=0)
            self.btn_toggle_sidebar.config(text="▶ MOSTRAR MENU (M)", fg="#39ff14")
            if hasattr(self, 'btn_collapse_ctrl'):
                self.btn_collapse_ctrl.config(text="▶ MOSTRAR MENU (M)", fg="#39ff14")

            # 2. Se for transparente, oculta também cabeçalho e barra de estado para ficar SÓ O TEMA
            if is_transparent:
                self.header_frame.pack_forget()
                self.status_bar.pack_forget()
                self.content_frame.config(padx=0, pady=0)
                # Exibir botão flutuante discreto no canto superior do Canvas para reabrir o menu
                self.btn_floating_menu.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
            else:
                self.btn_floating_menu.place_forget()

            self.status_bar.config(text="Menu lateral recolhido. Pressione [M] ou clique em 'Mostrar Menu' para expandir.")
        else:
            # Restaurar menu lateral e moldura completa
            self.btn_floating_menu.place_forget()
            if not self.is_fullscreen:
                self.header_frame.pack(fill=tk.X, before=self.content_frame)
                self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
                self.content_frame.config(padx=12, pady=10)
                self.preview_col.pack_forget()
                self.controls_col.pack(side=tk.RIGHT, fill=tk.Y)
                self.preview_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

            self.btn_toggle_sidebar.config(text="◀ RECOLHER MENU (M)", fg="#38bdf8")
            if hasattr(self, 'btn_collapse_ctrl'):
                self.btn_collapse_ctrl.config(text="◀ RECOLHER MENU // SÓ O TEMA (M)", fg="#39ff14")
            self.status_bar.config(text="Menu lateral expandido.")

        self.root.update_idletasks()
        if self.last_stats:
            self._update_canvas_display(self.last_stats)

    def _on_drag_start(self, event):
        """Regista as coordenadas iniciais ao clicar para arrastar a janela."""
        if not self.is_fullscreen:
            self._drag_start_x = event.x_root - self.root.winfo_x()
            self._drag_start_y = event.y_root - self.root.winfo_y()

    def _on_drag_motion(self, event):
        """Move a janela suavemente ao arrastar com o rato."""
        if not self.is_fullscreen:
            new_x = event.x_root - self._drag_start_x
            new_y = event.y_root - self._drag_start_y
            self.root.geometry(f"+{new_x}+{new_y}")

    def _toggle_transparency_mode(self, event=None):
        """Alterna o modo transparente (Overlay para 2º ecrã)."""
        current = self.transparent_mode_var.get()
        self.transparent_mode_var.set(not current)
        self._on_transparency_changed()

    def _set_window_opacity(self, alpha):
        """Define a opacidade geral da janela (0.2 a 1.0)."""
        self.opacity_scale_var.set(alpha)
        try:
            self.root.attributes("-alpha", alpha)
        except Exception:
            pass
        pct = int(alpha * 100)
        self.status_bar.config(text=f"Opacidade da janela ajustada para {pct}%.")

    def _on_transparency_changed(self):
        """Aplica ou remove o modo de fundo transparente."""
        is_transparent = self.transparent_mode_var.get()
        t_info = self.themes.get(self.current_theme_name, {})
        is_hud_theme = (t_info.get("layout") == "TRANSPARENT_HUD")

        if is_transparent or is_hud_theme:
            try:
                self.root.attributes("-transparentcolor", self.CHROMA_KEY_COLOR)
            except Exception:
                pass
            self.canvas.config(bg=self.CHROMA_KEY_COLOR, highlightthickness=0)
            self.btn_transparency.config(text="✨ OVERLAY ATIVO (T)", fg="#10b981")
            self.status_bar.config(text="Modo Overlay Transparente ATIVO: Fundo invisível para não tapar o 2º ecrã!")
            # Se o menu já estiver recolhido, oculta também cabeçalho/barra para ficar SÓ O TEMA
            if not self.sidebar_visible and not self.is_fullscreen:
                self.header_frame.pack_forget()
                self.status_bar.pack_forget()
                self.content_frame.config(padx=0, pady=0)
                self.btn_floating_menu.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        else:
            try:
                self.root.attributes("-transparentcolor", "")
            except Exception:
                pass
            self.canvas.config(bg="#07090f", highlightthickness=1)
            self.btn_transparency.config(text="✨ OVERLAY TRANSPARENTE (T)", fg="#00e5ff")
            self.status_bar.config(text="Modo transparente desativado. Fundo opaco restaurado.")
            # Se o menu estiver recolhido mas o modo opaco foi restaurado, mostra cabeçalho e barra
            if not self.sidebar_visible and not self.is_fullscreen:
                self.btn_floating_menu.place_forget()
                self.header_frame.pack(fill=tk.X, before=self.content_frame)
                self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
                self.content_frame.config(padx=12, pady=10)

        if self.last_stats:
            self._update_canvas_display(self.last_stats)

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
            layout = t.get("layout", "ALL_SENSORS")
            if layout == "TRANSPARENT_HUD":
                self.transparent_mode_var.set(True)
                self._on_transparency_changed()
            else:
                if not self.transparent_mode_var.get():
                    self._on_transparency_changed()
            self.update_preview()

    def set_theme_by_name(self, name):
        """Muda o tema da aplicação por nome e propaga a alteração."""
        if name in self.themes:
            self.theme_combo.set(name)
            self._on_theme_changed()
            if self.last_stats and self.web_server and self.web_server.is_running:
                t_info = self.themes.get(name, {})
                layout = t_info.get("layout", "ALL_SENSORS")
                w_frame = self.render_frame(self.last_stats, width=1280, height=720) if layout in (
                    "ALL_SENSORS", "SPEEDOMETER", "AIRPLANE_COCKPIT", "GT_COCKPIT", "XR2_MK2", "CS2", "PUBG", "PEUGEOT_508", "DJ_MIXER", "TRANSPARENT_HUD", "NEON_DUAL", "MONSTER_OFFICIAL"
                ) else self.render_frame(self.last_stats, width=480, height=320)
                self.web_server.update_frame(w_frame, self.last_stats)
            return name
        return self.current_theme_name

    def cycle_next_theme(self):
        """Avança para o próximo tema."""
        theme_keys = list(self.themes.keys())
        if not theme_keys:
            return ""
        try:
            curr_idx = theme_keys.index(self.current_theme_name)
            next_idx = (curr_idx + 1) % len(theme_keys)
        except ValueError:
            next_idx = 0
        target = theme_keys[next_idx]
        return self.set_theme_by_name(target)

    def cycle_prev_theme(self):
        """Recua para o tema anterior."""
        theme_keys = list(self.themes.keys())
        if not theme_keys:
            return ""
        try:
            curr_idx = theme_keys.index(self.current_theme_name)
            prev_idx = (curr_idx - 1) % len(theme_keys)
        except ValueError:
            prev_idx = 0
        target = theme_keys[prev_idx]
        return self.set_theme_by_name(target)

    def _get_themes_catalog(self):
        """Devolve o catálogo de temas disponíveis para o telemóvel / tablet."""
        return {
            "current": self.current_theme_name,
            "themes": [
                {
                    "name": k,
                    "layout": v.get("layout", ""),
                    "primary": v.get("primary", "#10b981")
                }
                for k, v in self.themes.items()
            ]
        }

    def _handle_remote_theme_change(self, action, theme_name=None):
        """Processa pedidos HTTP remotos do telemóvel/tablet de forma thread-safe."""
        theme_keys = list(self.themes.keys())
        target_name = self.current_theme_name

        if action == "next" and theme_keys:
            try:
                curr_idx = theme_keys.index(self.current_theme_name)
                target_name = theme_keys[(curr_idx + 1) % len(theme_keys)]
            except ValueError:
                target_name = theme_keys[0]
        elif action == "prev" and theme_keys:
            try:
                curr_idx = theme_keys.index(self.current_theme_name)
                target_name = theme_keys[(curr_idx - 1) % len(theme_keys)]
            except ValueError:
                target_name = theme_keys[0]
        elif action == "set" and theme_name:
            matched = None
            for k in self.themes.keys():
                if k.lower() == theme_name.lower():
                    matched = k
                    break
            if not matched:
                for k in self.themes.keys():
                    if theme_name.lower() in k.lower():
                        matched = k
                        break
            if matched:
                target_name = matched

        self.root.after(0, lambda: self.set_theme_by_name(target_name))
        return target_name

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
        scale = min(width / 568.888, height / 320.0)
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

    def _get_font(self, family, size, scale, bold=False):
        actual_size = max(8, int(size * scale))
        font_name = ("segoeuib.ttf" if bold else "segoeui.ttf") if family == "ui" else ("consolab.ttf" if bold else "consola.ttf")
        try:
            return ImageFont.truetype(font_name, actual_size)
        except Exception:
            return ImageFont.load_default()

    def _draw_gauge_needle(self, draw, cx, cy, radius, angle_deg, color="#ff3300", width=3, cap_r=8):
        rad = math.radians(angle_deg)
        tx = cx + radius * math.cos(rad)
        ty = cy + radius * math.sin(rad)
        bx = cx - (radius * 0.15) * math.cos(rad)
        by = cy - (radius * 0.15) * math.sin(rad)
        draw.line([(bx, by), (tx, ty)], fill=color, width=width)
        draw.ellipse([cx - cap_r, cy - cap_r, cx + cap_r, cy + cap_r], fill="#1e293b", outline="#cbd5e1", width=2)
        draw.ellipse([cx - cap_r//2, cy - cap_r//2, cx + cap_r//2, cy + cap_r//2], fill=color)

    def _draw_led_vu_meter(self, draw, x, y, width, height, level_ratio, num_segments=16, scale=1.0):
        """Desenha uma coluna de LEDs estilo mesa de mistura (Equalizador / VU Meter)."""
        level_ratio = min(1.0, max(0.0, level_ratio))
        gap = max(1, int(2 * scale))
        seg_h = (height - (num_segments - 1) * gap) / float(num_segments)

        c_green = "#10b981"
        c_amber = "#fbbf24"
        c_red = "#ef4444"
        d_green = "#08231a"
        d_amber = "#241806"
        d_red = "#260909"

        for i in range(num_segments):
            seg_ratio = (i + 1) / float(num_segments)
            is_lit = (seg_ratio <= level_ratio)
            if seg_ratio <= 0.60:
                color = c_green if is_lit else d_green
            elif seg_ratio <= 0.82:
                color = c_amber if is_lit else d_amber
            else:
                color = c_red if is_lit else d_red

            sy1 = y + height - int(i * (seg_h + gap))
            sy0 = sy1 - int(seg_h)
            draw.rectangle([x, sy0, x + width, sy1], fill=color)

    def _draw_fader(self, draw, track_x, track_y, track_h, level_ratio, scale=1.0):
        """Desenha a ranhura do fader e o manípulo metálico ajustado ao nível da mesa de mistura."""
        level_ratio = min(1.0, max(0.0, level_ratio))
        slot_w = max(2, int(3 * scale))
        draw.rectangle([track_x - slot_w // 2, track_y, track_x + slot_w // 2, track_y + track_h], fill="#0a0e14", outline="#1e293b", width=1)

        knob_y = track_y + track_h - int(level_ratio * track_h)
        kw = int(22 * scale)
        kh = int(12 * scale)
        kx0 = track_x - kw // 2
        kx1 = track_x + kw // 2
        ky0 = knob_y - kh // 2
        ky1 = knob_y + kh // 2

        draw.rectangle([kx0, ky0, kx1, ky1], fill="#334155", outline="#64748b", width=1)
        draw.line([(kx0 + int(3*scale), knob_y), (kx1 - int(3*scale), knob_y)], fill="#f8fafc", width=max(1, int(1.5*scale)))

    def _draw_hud_bracket_card(self, draw, x0, y0, x1, y1, scale, fill=(6, 12, 18), border=(0, 229, 255), bracket_len=14):
        """Desenha uma caixa HUD estilo cibernético com cantos em suporte [ ] e fundo de vidro fumado."""
        if isinstance(border, str):
            c = border.lstrip("#")
            if len(c) == 6:
                border = (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
            else:
                border = (0, 229, 255)
        draw.rectangle([x0, y0, x1, y1], fill=fill, outline=(border[0]//3, border[1]//3, border[2]//3), width=1)
        bl = int(bracket_len * scale)
        bw = max(1, int(2 * scale))
        # Top-Left
        draw.line([(x0, y0), (x0 + bl, y0)], fill=border, width=bw)
        draw.line([(x0, y0), (x0, y0 + bl)], fill=border, width=bw)
        # Top-Right
        draw.line([(x1 - bl, y0), (x1, y0)], fill=border, width=bw)
        draw.line([(x1, y0), (x1, y0 + bl)], fill=border, width=bw)
        # Bottom-Left
        draw.line([(x0, y1), (x0 + bl, y1)], fill=border, width=bw)
        draw.line([(x0, y1 - bl), (x0, y1)], fill=border, width=bw)
        # Bottom-Right
        draw.line([(x1 - bl, y1), (x1, y1)], fill=border, width=bw)
        draw.line([(x1, y1 - bl), (x1, y1)], fill=border, width=bw)

    def _draw_circular_hud_meter(self, draw, cx, cy, radius, percent, scale, label="CPU", val_str="45%", temp_str="58°C", primary_color="#00e5ff", temp_color="#10b981"):
        """Desenha um mostrador HUD circular de arco com retículo e telemetria central."""
        r = int(radius * scale)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(20, 35, 50), width=max(2, int(4 * scale)))
        start_deg = 135
        total_span = 270
        sweep = int(total_span * (max(0, min(100, percent)) / 100.0))
        if sweep > 0:
            draw.arc([cx - r, cy - r, cx + r, cy + r], start=start_deg, end=start_deg + sweep, fill=primary_color, width=max(3, int(6 * scale)))
        r_outer = r + int(6 * scale)
        for ang in range(135, 406, 27):
            rad = math.radians(ang)
            p1 = (cx + (r_outer - int(2*scale)) * math.cos(rad), cy + (r_outer - int(2*scale)) * math.sin(rad))
            p2 = (cx + (r_outer + int(3*scale)) * math.cos(rad), cy + (r_outer + int(3*scale)) * math.sin(rad))
            draw.line([p1, p2], fill=(60, 90, 120), width=1)
        f_lbl = self._get_font("ui", 8.5, scale, bold=True)
        f_val = self._get_font("mono", 14, scale, bold=True)
        f_temp = self._get_font("ui", 10, scale, bold=True)
        draw.text((cx, cy - int(16 * scale)), label, fill="#94a3b8", font=f_lbl, anchor="mm")
        draw.text((cx, cy + int(2 * scale)), val_str, fill=primary_color, font=f_val, anchor="mm")
        draw.text((cx, cy + int(20 * scale)), temp_str, fill=temp_color, font=f_temp, anchor="mm")

    def render_speedometer_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Velocímetros de Carro' em qualquer resolução (HD ou 480x320)."""
        scale = min(width / 568.888, height / 320.0)
        img = Image.new("RGB", (width, height), "#06090e")
        draw = ImageDraw.Draw(img)

        f_title = self._get_font("ui", 10.5, scale, bold=True)
        f_clock = self._get_font("mono", 11, scale, bold=True)
        f_num_big = self._get_font("ui", 26, scale, bold=True)
        f_label = self._get_font("ui", 9, scale, bold=True)
        f_small = self._get_font("ui", 8.5, scale, bold=False)
        f_mini = self._get_font("ui", 7.5, scale, bold=False)

        step = int(16 * scale)
        for x in range(0, width, step):
            draw.line([(x, 0), (x, height)], fill="#0a0e17", width=1)
        for y in range(0, height, step):
            draw.line([(0, y), (width, y)], fill="#0a0e17", width=1)

        bar_h = int(24 * scale)
        draw.rectangle([0, 0, width, bar_h], fill="#0c121e", outline="#1e293b", width=1)
        draw.text((int(14 * scale), int(4 * scale)), "GT SPORTS // INSTRUMENT CLUSTER", fill="#38bdf8", font=f_title)
        draw.text((width - int(110 * scale), int(4 * scale)), stats.get("time", "00:00:00"), fill="#f8fafc", font=f_clock)

        dial_r = int(95 * scale)
        cy = int(height * 0.52)
        cx1 = int(width * 0.24)
        cx2 = int(width * 0.76)

        def draw_gauge_bezel(cx, cy, r, title, sub):
            draw.ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], outline="#1e293b", width=3)
            draw.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], outline="#334155", width=2)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#0a0e17", outline="#0284c7", width=1)
            draw.text((cx, cy - int(55 * scale)), title, fill="#94a3b8", font=f_label, anchor="mm")
            draw.text((cx, cy - int(42 * scale)), sub, fill="#38bdf8", font=f_small, anchor="mm")

        # Tacómetro CPU
        draw_gauge_bezel(cx1, cy, dial_r, "TACHOMETER", "CPU LOAD x1000 RPM")
        for i in range(9):
            ang = 135 + i * (270 / 8.0)
            rad = math.radians(ang)
            is_red = (i >= 6)
            col = "#ef4444" if is_red else ("#f59e0b" if i >= 5 else "#e2e8f0")
            tick_len = int((12 if i % 2 == 0 else 7) * scale)
            p1x = cx1 + (dial_r - tick_len) * math.cos(rad)
            p1y = cy + (dial_r - tick_len) * math.sin(rad)
            p2x = cx1 + (dial_r - 2) * math.cos(rad)
            p2y = cy + (dial_r - 2) * math.sin(rad)
            draw.line([(p1x, p1y), (p2x, p2y)], fill=col, width=max(1, int(2 * scale)))
            if i % 2 == 0:
                tx = cx1 + (dial_r - int(22 * scale)) * math.cos(rad)
                ty = cy + (dial_r - int(22 * scale)) * math.sin(rad)
                draw.text((tx, ty), str(i), fill=col, font=f_small, anchor="mm")

        draw.arc([cx1 - dial_r + 4, cy - dial_r + 4, cx1 + dial_r - 4, cy + dial_r - 4], start=135 + 6*(270/8), end=405, fill="#ef4444", width=3)
        cpu_u = stats.get("cpu_usage", 25)
        cpu_ang = 135 + (cpu_u / 100.0) * 270
        needle_col = "#ef4444" if stats.get("cpu_temp", 50) >= 75 else "#10b981"
        self._draw_gauge_needle(draw, cx1, cy, dial_r - int(12 * scale), cpu_ang, color=needle_col, width=max(2, int(2.5 * scale)), cap_r=int(12 * scale))

        c_cpu_t = "#ef4444" if stats.get("cpu_temp", 50) >= 75 else ("#f59e0b" if stats.get("cpu_temp", 50) >= 55 else "#10b981")
        draw.text((cx1, cy + int(24 * scale)), f"{stats.get('cpu_temp', 50)}°C", fill=c_cpu_t, font=f_num_big, anchor="mm")
        draw.text((cx1, cy + int(48 * scale)), f"{stats.get('cpu_clock', 4.5)} GHz | {stats.get('cpu_fan', 1200)} RPM", fill="#cbd5e1", font=f_small, anchor="mm")

        # Velocímetro GPU
        draw_gauge_bezel(cx2, cy, dial_r, "SPEEDOMETER", f"GPU {stats.get('gpu_name', 'RTX')}")
        speeds = [0, 50, 100, 150, 200, 250, 300]
        for i, s in enumerate(speeds):
            ang = 135 + i * (270 / 6.0)
            rad = math.radians(ang)
            col = "#38bdf8" if s < 250 else "#ef4444"
            p1x = cx2 + (dial_r - int(11 * scale)) * math.cos(rad)
            p1y = cy + (dial_r - int(11 * scale)) * math.sin(rad)
            p2x = cx2 + (dial_r - 2) * math.cos(rad)
            p2y = cy + (dial_r - 2) * math.sin(rad)
            draw.line([(p1x, p1y), (p2x, p2y)], fill=col, width=max(1, int(2 * scale)))
            tx = cx2 + (dial_r - int(22 * scale)) * math.cos(rad)
            ty = cy + (dial_r - int(22 * scale)) * math.sin(rad)
            draw.text((tx, ty), str(s), fill=col, font=f_mini, anchor="mm")

        gpu_u = stats.get("gpu_usage", 40)
        gpu_ang = 135 + (gpu_u / 100.0) * 270
        self._draw_gauge_needle(draw, cx2, cy, dial_r - int(12 * scale), gpu_ang, color="#38bdf8", width=max(2, int(2.5 * scale)), cap_r=int(12 * scale))

        c_gpu_t = "#ef4444" if stats.get("gpu_temp", 50) >= 75 else ("#f59e0b" if stats.get("gpu_temp", 50) >= 55 else "#38bdf8")
        draw.text((cx2, cy + int(24 * scale)), f"{stats.get('gpu_temp', 50)}°C", fill=c_gpu_t, font=f_num_big, anchor="mm")
        draw.text((cx2, cy + int(48 * scale)), f"VRAM: {stats.get('gpu_vram_used', 6.0)}/{stats.get('gpu_vram_total', 12.0)} GB", fill="#cbd5e1", font=f_small, anchor="mm")

        # Consola Central
        mid_w = int(width * 0.22)
        mx0 = (width - mid_w) // 2
        mx1 = mx0 + mid_w
        my0 = int(height * 0.14)
        my1 = int(height * 0.88)
        draw.rectangle([mx0, my0, mx1, my1], fill="#080c14", outline="#1e293b", width=1)

        gear_box_h = int(58 * scale)
        draw.rectangle([mx0 + int(8*scale), my0 + int(8*scale), mx1 - int(8*scale), my0 + gear_box_h], fill="#0d1424", outline="#0284c7", width=2)
        draw.text(((mx0 + mx1)//2, my0 + int(14*scale)), "GEAR", fill="#94a3b8", font=f_mini, anchor="mm")
        draw.text(((mx0 + mx1)//2, my0 + int(38*scale)), "7", fill="#10b981", font=f_num_big, anchor="mm")

        aux_y = my0 + gear_box_h + int(12 * scale)
        aux_w = (mid_w - int(24 * scale))

        # Turbo Boost / Power
        draw.text((mx0 + int(12*scale), aux_y), "TURBO BOOST / POWER", fill="#94a3b8", font=f_mini)
        draw.text((mx1 - int(12*scale), aux_y), f"{stats.get('gpu_power', 120)} W", fill="#38bdf8", font=f_small, anchor="ra")
        draw.rectangle([mx0 + int(12*scale), aux_y + int(14*scale), mx1 - int(12*scale), aux_y + int(20*scale)], fill="#1e293b")
        boost_pct = min(1.0, float(stats.get('gpu_power', 120)) / 285.0)
        draw.rectangle([mx0 + int(12*scale), aux_y + int(14*scale), mx0 + int(12*scale) + int(aux_w * boost_pct), aux_y + int(20*scale)], fill="#0284c7")

        # Fuel / RAM
        fuel_y = aux_y + int(30 * scale)
        draw.text((mx0 + int(12*scale), fuel_y), "FUEL / DDR5 RAM", fill="#94a3b8", font=f_mini)
        draw.text((mx1 - int(12*scale), fuel_y), f"{stats.get('ram_usage', 50)}%", fill="#10b981", font=f_small, anchor="ra")
        draw.rectangle([mx0 + int(12*scale), fuel_y + int(14*scale), mx1 - int(12*scale), fuel_y + int(20*scale)], fill="#1e293b")
        draw.rectangle([mx0 + int(12*scale), fuel_y + int(14*scale), mx0 + int(12*scale) + int(aux_w * (stats.get('ram_usage', 50)/100.0)), fuel_y + int(20*scale)], fill="#10b981")

        # Oil Temp / Sys Temp
        oil_y = fuel_y + int(30 * scale)
        draw.text((mx0 + int(12*scale), oil_y), "OIL / SYS TEMP", fill="#94a3b8", font=f_mini)
        draw.text((mx1 - int(12*scale), oil_y), f"{stats.get('sys_temp', 32)}°C (OK)", fill="#38bdf8", font=f_small, anchor="ra")

        # Odómetro
        odo_y = oil_y + int(24 * scale)
        draw.rectangle([mx0 + int(8*scale), odo_y, mx1 - int(8*scale), my1 - int(8*scale)], fill="#05080f", outline="#1e293b", width=1)
        draw.text(((mx0+mx1)//2, odo_y + int(10*scale)), "ODOMETER (STORAGE)", fill="#64748b", font=f_mini, anchor="mm")
        draw.text(((mx0+mx1)//2, odo_y + int(24*scale)), f"NVMe C: {stats.get('disk_c_pct', 80)}% | E: {stats.get('disk_e_pct', 80)}%", fill="#f8fafc", font=f_small, anchor="mm")
        draw.text(((mx0+mx1)//2, odo_y + int(38*scale)), f"TRIP: {stats.get('uptime', '0h')}", fill="#38bdf8", font=f_mini, anchor="mm")
        draw.text(((mx0+mx1)//2, odo_y + int(50*scale)), f"NET: ↓{stats.get('net_down_str', '0 KB/s')}  ↑{stats.get('net_up_str', '0 KB/s')}", fill="#10b981", font=f_mini, anchor="mm")

        # Luzes do Painel
        lamp_y = int(height * 0.93)
        lamp_cols = [
            ("CHECK", "#ef4444" if stats.get("cpu_temp", 50) >= 75 else "#334155"),
            ("OIL", "#f59e0b" if stats.get("sys_temp", 32) >= 50 else "#334155"),
            ("BRAKE", "#334155"),
            ("ABS", "#334155"),
            ("TC", "#10b981"),
            ("SPORT+", "#0284c7")
        ]
        total_l = len(lamp_cols)
        lw = int(50 * scale)
        start_lx = (width - (total_l * lw)) // 2
        for i, (l_text, l_col) in enumerate(lamp_cols):
            lx = start_lx + i * lw
            draw.rectangle([lx, lamp_y, lx + lw - int(6*scale), lamp_y + int(14*scale)], fill="#0c121e", outline=l_col, width=1)
            draw.text((lx + (lw - int(6*scale))//2, lamp_y + int(7*scale)), l_text, fill=l_col, font=f_mini, anchor="mm")

        return img

    def render_airplane_cockpit_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Cockpit de Avião' (Fighter Jet / Glass HUD) em qualquer resolução."""
        scale = min(width / 568.888, height / 320.0)
        img = Image.new("RGB", (width, height), "#02070a")
        draw = ImageDraw.Draw(img)

        f_title = self._get_font("mono", 11, scale, bold=True)
        f_hud = self._get_font("mono", 10, scale, bold=True)
        f_hud_big = self._get_font("mono", 24, scale, bold=True)
        f_hud_med = self._get_font("mono", 13, scale, bold=True)
        f_hud_small = self._get_font("mono", 8.5, scale, bold=False)

        c_hud = "#00ff66"
        c_amber = "#ffb700"
        c_cyan = "#00e5ff"
        c_dark_green = "#003b17"
        c_grid = "#041512"

        step = int(32 * scale)
        for x in range(0, width, step):
            draw.line([(x, 0), (x, height)], fill=c_grid, width=1)
        for y in range(0, height, step):
            draw.line([(0, y), (width, y)], fill=c_grid, width=1)

        # Annunciator Superior
        annun_h = int(24 * scale)
        draw.rectangle([0, 0, width, annun_h], fill="#03120f", outline=c_dark_green, width=1)
        annun_boxes = [
            ("MASTER WARN", "#ef4444" if (stats.get("cpu_temp", 50)>=75 or stats.get("gpu_temp", 50)>=75) else "#1e293b"),
            ("FIRE DETECT", "#ef4444" if stats.get("gpu_hotspot", 50)>=80 else "#1e293b"),
            ("ENG 1 (CPU)", c_hud),
            ("ENG 2 (GPU)", c_hud),
            ("AP ENGAGED", c_cyan),
            ("RADAR LOCK", c_hud),
            ("OXY OK", c_hud)
        ]
        aw = int(85 * scale)
        for i, (a_name, a_col) in enumerate(annun_boxes):
            ax = int(10 * scale) + i * aw
            draw.rectangle([ax, int(3*scale), ax + aw - int(6*scale), annun_h - int(3*scale)], fill="#020907", outline=a_col, width=1)
            draw.text((ax + (aw - int(6*scale))//2, annun_h // 2), a_name, fill=a_col, font=f_hud_small, anchor="mm")

        draw.text((width - int(120 * scale), annun_h // 2), f"ZULU {stats.get('time', '00:00')}", fill=c_cyan, font=f_title, anchor="lm")

        # Horizonte Artificial Central
        pfd_cx = width // 2
        pfd_cy = int(height * 0.50)
        pfd_r = int(100 * scale)
        draw.ellipse([pfd_cx - pfd_r, pfd_cy - pfd_r, pfd_cx + pfd_r, pfd_cy + pfd_r], fill="#02140e", outline=c_hud, width=2)

        pitch_spacing = int(24 * scale)
        for p in [-20, -10, 0, 10, 20]:
            py = pfd_cy - int((p / 10.0) * pitch_spacing)
            pw = int((50 if p == 0 else 30) * scale)
            if p == 0:
                draw.line([(pfd_cx - pw, py), (pfd_cx + pw, py)], fill=c_hud, width=2)
                draw.text((pfd_cx - pw - int(12*scale), py), "00", fill=c_hud, font=f_hud_small, anchor="mm")
                draw.text((pfd_cx + pw + int(12*scale), py), "00", fill=c_hud, font=f_hud_small, anchor="mm")
            else:
                draw.line([(pfd_cx - pw, py), (pfd_cx - int(10*scale), py)], fill=c_hud, width=1)
                draw.line([(pfd_cx + int(10*scale), py), (pfd_cx + pw, py)], fill=c_hud, width=1)
                txt = f"+{p}" if p > 0 else f"{p}"
                draw.text((pfd_cx - pw - int(10*scale), py), txt, fill=c_hud, font=f_hud_small, anchor="mm")

        draw.line([(pfd_cx - int(25*scale), pfd_cy), (pfd_cx - int(8*scale), pfd_cy)], fill=c_amber, width=3)
        draw.line([(pfd_cx + int(8*scale), pfd_cy), (pfd_cx + int(25*scale), pfd_cy)], fill=c_amber, width=3)
        draw.ellipse([pfd_cx - int(5*scale), pfd_cy - int(5*scale), pfd_cx + int(5*scale), pfd_cy + int(5*scale)], outline=c_amber, width=2)

        draw.text((pfd_cx, pfd_cy - int(70 * scale)), f"MACH 0.{stats.get('cpu_usage', 20):02d}", fill=c_cyan, font=f_hud_med, anchor="mm")
        draw.text((pfd_cx, pfd_cy + int(70 * scale)), f"ALTITUDE FL{stats.get('gpu_usage', 20):02d}", fill=c_hud, font=f_hud_med, anchor="mm")

        # Fita Lateral Esquerda: Airspeed / CPU
        tape_w = int(width * 0.26)
        lx0 = int(14 * scale)
        lx1 = lx0 + tape_w
        ty0 = int(36 * scale)
        ty1 = height - int(20 * scale)
        draw.rectangle([lx0, ty0, lx1, ty1], fill="#020d09", outline=c_hud, width=1)
        draw.rectangle([lx0, ty0, lx1, ty0 + int(24*scale)], fill="#041a12")
        draw.text(((lx0+lx1)//2, ty0 + int(12*scale)), "AIRSPEED // ENGINE 1 (CPU)", fill=c_hud, font=f_hud, anchor="mm")

        c_c_temp = "#ef4444" if stats.get("cpu_temp", 50) >= 75 else c_hud
        draw.text(((lx0+lx1)//2, ty0 + int(60*scale)), f"{stats.get('cpu_temp', 50)}°C", fill=c_c_temp, font=f_hud_big, anchor="mm")
        draw.text(((lx0+lx1)//2, ty0 + int(88*scale)), f"THRUST: {stats.get('cpu_usage', 30)}% LOAD", fill=c_amber, font=f_hud_med, anchor="mm")

        bar_x = lx0 + int(16 * scale)
        bar_w = tape_w - int(32 * scale)
        bar_y = ty0 + int(106 * scale)
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + int(12*scale)], fill="#041a12", outline=c_dark_green)
        draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * (stats.get('cpu_usage', 30)/100.0)), bar_y + int(12*scale)], fill=c_hud)

        det_y = bar_y + int(24 * scale)
        cpu_lines = [
            f"CORE CLOCK : {stats.get('cpu_clock', 4.5)} GHz",
            f"TURBINE N1 : {stats.get('cpu_fan', 1200)} RPM",
            f"CORES/THR  : {stats.get('cpu_cores', '14C/20T')}",
            f"HYDR SYS   : {stats.get('sys_temp', 32)}°C NOMINAL",
            f"RAD FAN    : {stats.get('chassis_fan', 1100)} RPM",
            f"TIME STINT : {stats.get('uptime', '0h')}"
        ]
        for j, line in enumerate(cpu_lines):
            draw.text((bar_x, det_y + j * int(18*scale)), line, fill=c_cyan if "CLOCK" in line else c_hud, font=f_hud_small)

        # Fita Lateral Direita: Altitude / GPU
        rx1 = width - int(14 * scale)
        rx0 = rx1 - tape_w
        draw.rectangle([rx0, ty0, rx1, ty1], fill="#020d09", outline=c_hud, width=1)
        draw.rectangle([rx0, ty0, rx1, ty0 + int(24*scale)], fill="#041a12")
        draw.text(((rx0+rx1)//2, ty0 + int(12*scale)), "ALTITUDE // ENGINE 2 (GPU)", fill=c_hud, font=f_hud, anchor="mm")

        c_g_temp = "#ef4444" if stats.get("gpu_temp", 50) >= 75 else c_hud
        draw.text(((rx0+rx1)//2, ty0 + int(60*scale)), f"{stats.get('gpu_temp', 50)}°C", fill=c_g_temp, font=f_hud_big, anchor="mm")
        draw.text(((rx0+rx1)//2, ty0 + int(88*scale)), f"THRUST: {stats.get('gpu_usage', 40)}% ({stats.get('gpu_name', 'GPU')})", fill=c_cyan, font=f_hud_small, anchor="mm")

        rbar_x = rx0 + int(16 * scale)
        draw.rectangle([rbar_x, bar_y, rbar_x + bar_w, bar_y + int(12*scale)], fill="#041a12", outline=c_dark_green)
        draw.rectangle([rbar_x, bar_y, rbar_x + int(bar_w * (stats.get('gpu_usage', 40)/100.0)), bar_y + int(12*scale)], fill=c_cyan)

        gpu_lines = [
            f"GPU CLOCK  : {stats.get('gpu_clock', 2600)} MHz",
            f"HOTSPOT    : {stats.get('gpu_hotspot', 55)}°C",
            f"VRAM USED  : {stats.get('gpu_vram_used', 6.0)} / {stats.get('gpu_vram_total', 12.0)} GB",
            f"POWER DRAW : {stats.get('gpu_power', 120)} WATTS",
            f"GPU COOLER : {stats.get('gpu_fan', 1300)} RPM",
            f"MEMORY BUS : {stats.get('gpu_mem_clock', 10.0)} GHz"
        ]
        for j, line in enumerate(gpu_lines):
            draw.text((rbar_x, det_y + j * int(18*scale)), line, fill=c_amber if "HOTSPOT" in line else c_hud, font=f_hud_small)

        # Painel Inferior: Navegação & Armazenamento
        nav_y = pfd_cy + pfd_r + int(12 * scale)
        nav_w = int(width * 0.40)
        nx0 = (width - nav_w) // 2
        nx1 = nx0 + nav_w
        draw.rectangle([nx0, nav_y, nx1, height - int(20*scale)], fill="#02110c", outline=c_hud, width=1)
        draw.text(((nx0+nx1)//2, nav_y + int(12*scale)), "NAVIGATION // AVIONICS SUBSYSTEMS", fill=c_cyan, font=f_hud_small, anchor="mm")
        draw.text((nx0 + int(14*scale), nav_y + int(28*scale)), f"HDG 072° | FUEL: RAM {stats.get('ram_used_gb', 14)}/{stats.get('ram_total_gb', 32)} GB ({stats.get('ram_usage', 44)}%)", fill=c_hud, font=f_hud_small)
        draw.text((nx0 + int(14*scale), nav_y + int(44*scale)), f"WPT1: NVMe C: {stats.get('disk_c_pct', 80)}%  |  WPT2: NVMe E: {stats.get('disk_e_pct', 80)}%", fill=c_amber, font=f_hud_small)
        draw.text((nx0 + int(14*scale), nav_y + int(60*scale)), f"DATALINK: ↓ {stats.get('net_down_str', '0 KB/s')}  ↑ {stats.get('net_up_str', '0 KB/s')}", fill=c_hud, font=f_hud_small)

        return img

    def render_gt_cockpit_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Cockpit de Carro GT' (Racing Telemetry) em qualquer resolução."""
        scale = min(width / 568.888, height / 320.0)
        img = Image.new("RGB", (width, height), "#05070a")
        draw = ImageDraw.Draw(img)

        f_title = self._get_font("ui", 10.5, scale, bold=True)
        f_num_giant = self._get_font("mono", 34, scale, bold=True)
        f_num_big = self._get_font("mono", 24, scale, bold=True)
        f_val = self._get_font("ui", 11, scale, bold=True)
        f_small = self._get_font("ui", 8, scale, bold=False)

        # Sequential Shift Lights
        led_h = int(22 * scale)
        draw.rectangle([0, 0, width, led_h], fill="#0a0d14", outline="#1e293b", width=1)
        num_leds = 16
        led_w = (width - int(40 * scale)) / float(num_leds)
        active_leds = int((stats.get("cpu_usage", 30) / 100.0) * num_leds)

        for i in range(num_leds):
            lx = int(20 * scale) + i * led_w
            ly = int(4 * scale)
            lw = int(led_w - 4 * scale)
            lh = int(led_h - 8 * scale)
            if i < 5:
                base_col, on_col = "#063d1e", "#10b981"
            elif i < 10:
                base_col, on_col = "#3d2f06", "#f59e0b"
            elif i < 14:
                base_col, on_col = "#450a0a", "#ef4444"
            else:
                base_col, on_col = "#2e1065", "#a855f7"
            col = on_col if i <= active_leds else base_col
            draw.rectangle([lx, ly, lx + lw, ly + lh], fill=col, outline="#1e293b", width=1)

        # Bloco Central: Marcha e Velocidade
        mid_w = int(width * 0.30)
        mx0 = (width - mid_w) // 2
        mx1 = mx0 + mid_w
        my0 = led_h + int(10 * scale)
        my1 = my0 + int(120 * scale)
        draw.rectangle([mx0, my0, mx1, my1], fill="#0b0f19", outline="#1e293b", width=2)

        gear_w = int(60 * scale)
        draw.rectangle([mx0 + int(12*scale), my0 + int(12*scale), mx0 + int(12*scale) + gear_w, my1 - int(12*scale)], fill="#1e1b4b", outline="#6366f1", width=2)
        draw.text((mx0 + int(12*scale) + gear_w//2, my0 + int(20*scale)), "GEAR", fill="#a5b4fc", font=f_small, anchor="mm")
        draw.text((mx0 + int(12*scale) + gear_w//2, my0 + int(60*scale)), "6", fill="#ffffff", font=f_num_giant, anchor="mm")

        speed_x = mx0 + int(12*scale) + gear_w + int(16*scale)
        draw.text((speed_x, my0 + int(24*scale)), "SPEED / GPU CLOCK", fill="#94a3b8", font=f_small)
        draw.text((speed_x, my0 + int(56*scale)), "284", fill="#f8fafc", font=f_num_giant)
        draw.text((speed_x + int(100*scale), my0 + int(68*scale)), "KM/H", fill="#ef4444", font=f_val)
        draw.text((speed_x, my0 + int(96*scale)), f"DELTA: -0.34s  |  LAP: {stats.get('time', '00:00:00')}", fill="#10b981", font=f_small)

        # Painel Esquerdo: Engine // CPU
        card_w = (width - mid_w - int(48 * scale)) // 2
        px0 = int(14 * scale)
        px1 = px0 + card_w
        draw.rectangle([px0, my0, px1, my1], fill="#0b0f19", outline="#1e293b", width=1)
        draw.rectangle([px0, my0, px1, my0 + int(22*scale)], fill="#111827")
        draw.text((px0 + int(10*scale), my0 + int(11*scale)), "ENGINE // CPU INTEL i7", fill="#10b981", font=f_title, anchor="lm")

        c_cpu_t = "#ef4444" if stats.get("cpu_temp", 50) >= 75 else "#10b981"
        draw.text((px0 + int(14*scale), my0 + int(58*scale)), f"{stats.get('cpu_temp', 50)}°C", fill=c_cpu_t, font=f_num_big)
        draw.text((px1 - int(14*scale), my0 + int(58*scale)), f"{stats.get('cpu_usage', 30)}%", fill="#f8fafc", font=f_num_big, anchor="ra")
        draw.text((px0 + int(14*scale), my0 + int(94*scale)), f"FREQ: {stats.get('cpu_clock', 4.5)} GHz  |  FAN: {stats.get('cpu_fan', 1200)} RPM", fill="#94a3b8", font=f_small)

        # Painel Direito: Powertrain // GPU
        gx0 = mx1 + int(12 * scale)
        gx1 = gx0 + card_w
        draw.rectangle([gx0, my0, gx1, my1], fill="#0b0f19", outline="#1e293b", width=1)
        draw.rectangle([gx0, my0, gx0 + card_w, my0 + int(22*scale)], fill="#111827")
        draw.text((gx0 + int(10*scale), my0 + int(11*scale)), f"POWERTRAIN // {stats.get('gpu_name', 'GPU')}", fill="#38bdf8", font=f_title, anchor="lm")

        c_gpu_t = "#ef4444" if stats.get("gpu_temp", 50) >= 75 else "#38bdf8"
        draw.text((gx0 + int(14*scale), my0 + int(58*scale)), f"{stats.get('gpu_temp', 50)}°C", fill=c_gpu_t, font=f_num_big)
        draw.text((gx1 - int(14*scale), my0 + int(58*scale)), f"{stats.get('gpu_usage', 40)}%", fill="#f8fafc", font=f_num_big, anchor="ra")
        draw.text((gx0 + int(14*scale), my0 + int(94*scale)), f"VRAM: {stats.get('gpu_vram_used', 6.0)}/{stats.get('gpu_vram_total', 12.0)} GB | {stats.get('gpu_power', 120)} W", fill="#94a3b8", font=f_small)

        # Zona Inferior: Pneus / Drives (FL, FR, RL, RR)
        bot_y = my1 + int(10 * scale)
        bot_h = height - bot_y - int(12 * scale)
        draw.rectangle([px0, bot_y, gx1, bot_y + bot_h], fill="#080c14", outline="#1e293b", width=1)
        draw.rectangle([px0, bot_y, gx1, bot_y + int(20*scale)], fill="#0f1523")
        draw.text((px0 + int(10*scale), bot_y + int(10*scale)), "TYRES & CHASSIS TELEMETRY // STORAGE & RAM", fill="#94a3b8", font=f_small, anchor="lm")

        tyre_box_w = (gx1 - px0 - int(40 * scale)) // 4
        tyres = [
            ("FL [NVMe C:]", f"{stats.get('disk_c_pct', 80)}% USED", f"{stats.get('disk_c_used', 700)} GB", "#10b981"),
            ("FR [NVMe E:]", f"{stats.get('disk_e_pct', 80)}% USED", f"{stats.get('disk_e_used', 1500)} GB", "#10b981"),
            ("RL [RAM CH-A]", f"{stats.get('ram_usage', 50)}% USED", f"{stats.get('ram_used_gb', 14)} GB", "#38bdf8"),
            ("RR [SYS CH-B]", f"{stats.get('sys_temp', 32)}°C OPTIMAL", f"NET: {stats.get('net_down_str', '0 KB/s')}", "#f59e0b")
        ]

        for k, (t_title, t_v1, t_v2, t_col) in enumerate(tyres):
            tx = px0 + int(10*scale) + k * (tyre_box_w + int(8*scale))
            ty = bot_y + int(28*scale)
            th = bot_h - int(36*scale)
            draw.rectangle([tx, ty, tx + tyre_box_w, ty + th], fill="#0d1320", outline=t_col, width=1)
            draw.text((tx + int(8*scale), ty + int(12*scale)), t_title, fill="#cbd5e1", font=f_val)
            draw.text((tx + int(8*scale), ty + int(34*scale)), t_v1, fill=t_col, font=f_val)
            draw.text((tx + int(8*scale), ty + int(56*scale)), t_v2, fill="#94a3b8", font=f_small)

        return img

    def render_xr2_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Ford Fiesta XR2 Mk2' (Fotografia Realista & Telemetria 80s Hot Hatch)."""
        scale = min(width / 568.888, height / 320.0)
        is_compact = (width <= 640)

        # 1. Carregar fotografia do Ford Fiesta XR2 Mk2
        photo_path = os.path.join(self.assets_dir, 'fiesta_xr2_mk2.jpg')
        if not os.path.exists(photo_path):
            photo_path = os.path.join(self.assets_dir, 'fiesta_xr2_480x320.jpg')

        if os.path.exists(photo_path):
            base_img = Image.open(photo_path).convert('RGB')
            base_ratio = base_img.width / float(base_img.height)
            target_ratio = width / float(height)

            if base_ratio > target_ratio:
                nh = height
                nw = int(height * base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                x_off = (nw - width) // 2
                img = base_resized.crop((x_off, 0, x_off + width, height))
            else:
                nw = width
                nh = int(width / base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                y_off = (nh - height) // 2
                img = base_resized.crop((0, y_off, width, y_off + height))
        else:
            img = Image.new('RGB', (width, height), '#070a0e')

        # 2. Camada de transparência para os cartões de telemetria
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        d_ov = ImageDraw.Draw(overlay)

        bar_h = int(26 * scale)
        d_ov.rectangle([0, 0, width, bar_h], fill=(7, 10, 16, 230))

        side_w = int(width * (0.32 if not is_compact else 0.38))
        my0 = bar_h + int(8 * scale)
        my1 = height - int(60 * scale)
        d_ov.rectangle([int(8*scale), my0, side_w, my1], fill=(8, 12, 18, 210), outline=(225, 29, 72, 180), width=max(1, int(1.5*scale)))

        rx0 = width - side_w
        rx1 = width - int(8 * scale)
        d_ov.rectangle([rx0, my0, rx1, my1], fill=(8, 12, 18, 210), outline=(225, 29, 72, 180), width=max(1, int(1.5*scale)))

        bot_y0 = my1 + int(6 * scale)
        bot_y1 = height - int(4 * scale)
        d_ov.rectangle([int(8*scale), bot_y0, width - int(8*scale), bot_y1], fill=(7, 10, 16, 235), outline=(30, 41, 59, 200), width=1)

        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)

        f_title = self._get_font("ui", 11, scale, bold=True)
        f_clock = self._get_font("mono", 11, scale, bold=True)
        f_num_big = self._get_font("mono", 25, scale, bold=True)
        f_num_med = self._get_font("ui", 12, scale, bold=True)
        f_label = self._get_font("ui", 9.5, scale, bold=True)
        f_val = self._get_font("ui", 9.5, scale, bold=True)
        f_small = self._get_font("ui", 8.5, scale, bold=False)
        f_xr_badge = self._get_font("ui", 16, scale, bold=True)

        c_red_ford = "#e11d48"
        c_blue_ford = "#0284c7"
        c_white = "#f8fafc"
        c_slate = "#94a3b8"
        c_green = "#10b981"
        c_amber = "#f59e0b"

        # Barra Superior Motorsport
        stripe_h = max(2, int(3 * scale))
        draw.rectangle([0, 0, width, stripe_h], fill=c_red_ford)
        draw.rectangle([0, stripe_h, int(width * 0.45), stripe_h * 2], fill=c_blue_ford)

        draw.text((int(14 * scale), int(6 * scale)), "FORD FIESTA XR2 // 1.6L CVH HOT HATCH", fill=c_white, font=f_title)
        draw.text((width - int(120 * scale), int(6 * scale)), stats.get("time", "00:00"), fill=c_red_ford, font=f_clock)

        # Painel Esquerdo: Motor 1.6 CVH (CPU)
        px0 = int(8 * scale)
        px1 = side_w
        head_h = int(22 * scale)
        draw.rectangle([px0, my0, px1, my0 + head_h], fill="#131b26")
        draw.rectangle([px0, my0, px0 + int(4*scale), my0 + head_h], fill=c_red_ford)
        draw.text((px0 + int(10*scale), my0 + int(3*scale)), "ENGINE // 1.6 CVH (CPU)", fill=c_white, font=f_label)

        c_cpu_t = c_red_ford if stats.get("cpu_temp", 50) >= 75 else (c_amber if stats.get("cpu_temp", 50) >= 55 else c_green)
        draw.text((px0 + int(14*scale), my0 + int(32*scale)), f"{stats.get('cpu_temp', 50)}°C", fill=c_cpu_t, font=f_num_big)
        draw.text((px1 - int(14*scale), my0 + int(32*scale)), f"{stats.get('cpu_usage', 30)}% LOAD", fill=c_white, font=f_num_med, anchor="ra")

        bar_x = px0 + int(14*scale)
        bar_w = (px1 - px0) - int(28*scale)
        bar_y = my0 + int(68*scale)
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + int(10*scale)], fill="#1e293b")
        u_pct = min(1.0, stats.get("cpu_usage", 30) / 100.0)
        draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * u_pct), bar_y + int(10*scale)], fill=c_red_ford if u_pct >= 0.75 else c_green)

        dy = bar_y + int(18*scale)
        lines_cpu = [
            ("CAMSHAFT / CLOCK", f"{stats.get('cpu_clock', 4.5)} GHz", c_blue_ford),
            ("RADIATOR FAN", f"{stats.get('cpu_fan', 1200)} RPM", c_white),
            ("CYLINDERS / THR", f"{stats.get('cpu_cores', '14C/20T')}", c_white),
            ("WATER TEMPERATURE", f"{stats.get('sys_temp', 32)}°C (NORMAL)", c_green),
            ("SESSION RUNNING", f"{stats.get('uptime', '0h')}", c_slate)
        ]
        for lbl, val, col in lines_cpu:
            draw.text((bar_x, dy), lbl, fill=c_slate, font=f_small)
            draw.text((px1 - int(14*scale), dy), val, fill=col, font=f_val, anchor="ra")
            dy += int(17 * scale)

        # Painel Direito: Transmissão & GPU
        draw.rectangle([rx0, my0, rx1, my0 + head_h], fill="#131b26")
        draw.rectangle([rx1 - int(4*scale), my0, rx1, my0 + head_h], fill=c_red_ford)
        draw.text((rx0 + int(10*scale), my0 + int(3*scale)), f"POWERTRAIN // {stats.get('gpu_name', 'RTX')}", fill=c_white, font=f_label)

        c_gpu_t = c_red_ford if stats.get("gpu_temp", 50) >= 75 else (c_amber if stats.get("gpu_temp", 50) >= 55 else c_blue_ford)
        draw.text((rx0 + int(14*scale), my0 + int(32*scale)), f"{stats.get('gpu_temp', 50)}°C", fill=c_gpu_t, font=f_num_big)
        draw.text((rx1 - int(14*scale), my0 + int(32*scale)), f"{stats.get('gpu_usage', 40)}% LOAD", fill=c_white, font=f_num_med, anchor="ra")

        rbar_x = rx0 + int(14*scale)
        draw.rectangle([rbar_x, bar_y, rbar_x + bar_w, bar_y + int(10*scale)], fill="#1e293b")
        gu_pct = min(1.0, stats.get("gpu_usage", 40) / 100.0)
        draw.rectangle([rbar_x, bar_y, rbar_x + int(bar_w * gu_pct), bar_y + int(10*scale)], fill=c_blue_ford)

        rdy = bar_y + int(18*scale)
        lines_gpu = [
            ("ENGINE HOTSPOT", f"{stats.get('gpu_hotspot', 55)}°C", c_amber),
            ("5-SPEED GEARBOX", f"{stats.get('gpu_clock', 2600)} MHz", c_white),
            ("VRAM BUFFER", f"{stats.get('gpu_vram_used', 6.0)}/{stats.get('gpu_vram_total', 12.0)} GB", c_blue_ford),
            ("FUEL INJECTION", f"{stats.get('gpu_power', 120)} WATTS", c_green),
            ("INTERCOOLER FAN", f"{stats.get('gpu_fan', 1300)} RPM", c_white)
        ]
        for lbl, val, col in lines_gpu:
            draw.text((rbar_x, rdy), lbl, fill=c_slate, font=f_small)
            draw.text((rx1 - int(14*scale), rdy), val, fill=col, font=f_val, anchor="ra")
            rdy += int(17 * scale)

        # Rodapé Inferior: Chassis & Armazenamento
        col_w = (width - int(16*scale) - int(90*scale)) // 3
        bx = int(14 * scale)

        draw.text((bx, bot_y0 + int(8*scale)), "PETROL (RAM DDR5)", fill=c_slate, font=f_small)
        draw.text((bx, bot_y0 + int(24*scale)), f"{stats.get('ram_used_gb', 14)} / {stats.get('ram_total_gb', 32)} GB ({stats.get('ram_usage', 44)}%)", fill=c_green, font=f_val)

        bx += col_w
        draw.text((bx, bot_y0 + int(8*scale)), "FRONT AXLE (NVMe C:)", fill=c_slate, font=f_small)
        draw.text((bx, bot_y0 + int(24*scale)), f"{stats.get('disk_c_used', 700)} / {stats.get('disk_c_total', 930)} GB ({stats.get('disk_c_pct', 80)}%)", fill=c_white, font=f_val)

        bx += col_w
        draw.text((bx, bot_y0 + int(8*scale)), "REAR AXLE (NVMe E:)", fill=c_slate, font=f_small)
        draw.text((bx, bot_y0 + int(24*scale)), f"{stats.get('disk_e_pct', 80)}% | NET: ↓{stats.get('net_down_str', '0KB')} ↑{stats.get('net_up_str', '0KB')}", fill=c_blue_ford, font=f_val)

        badge_x = width - int(95 * scale)
        badge_y = bot_y0 + int(6 * scale)
        badge_w = int(80 * scale)
        badge_h = int(38 * scale)
        draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill="#180408", outline=c_red_ford, width=2)
        draw.text((badge_x + badge_w // 2, badge_y + badge_h // 2 - int(2*scale)), "XR2", fill=c_red_ford, font=f_xr_badge, anchor="mm")

        return img

    def render_cs2_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Counter-Strike 2' (CS2 Tactical HUD)."""
        scale = min(width / 568.888, height / 320.0)
        is_compact = (width <= 640)

        # 1. Carregar Wallpaper CS2
        bg_path = os.path.join(self.assets_dir, "cs2_wallpaper.jpg")
        if os.path.exists(bg_path):
            base_img = Image.open(bg_path).convert("RGB")
            base_ratio = base_img.width / float(base_img.height)
            target_ratio = width / float(height)
            if base_ratio > target_ratio:
                nh = height
                nw = int(height * base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                x_off = (nw - width) // 2
                img = base_resized.crop((x_off, 0, x_off + width, height))
            else:
                nw = width
                nh = int(width / base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                y_off = (nh - height) // 2
                img = base_resized.crop((0, y_off, width, y_off + height))
        else:
            img = Image.new("RGB", (width, height), "#0b1017")

        # 2. Camada Transparência HUD Tático CS2
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d_ov = ImageDraw.Draw(overlay)

        bar_h = int(26 * scale)
        d_ov.rectangle([0, 0, width, bar_h], fill=(11, 16, 24, 235))

        side_w = int(width * (0.33 if not is_compact else 0.40))
        my0 = bar_h + int(8 * scale)
        my1 = height - int(60 * scale)

        # Painel Esquerdo (CT Force / CPU) - Contorno Azul Gelo CS2
        d_ov.rectangle([int(8*scale), my0, side_w, my1], fill=(11, 17, 26, 215), outline=(56, 189, 248, 200), width=max(1, int(1.5*scale)))

        # Painel Direito (T Threat / GPU) - Contorno Âmbar CS2
        rx0 = width - side_w
        rx1 = width - int(8 * scale)
        d_ov.rectangle([rx0, my0, rx1, my1], fill=(18, 14, 11, 215), outline=(245, 158, 11, 200), width=max(1, int(1.5*scale)))

        # Barra Inferior (Economy & Net Graph)
        bot_y0 = my1 + int(6 * scale)
        bot_y1 = height - int(4 * scale)
        d_ov.rectangle([int(8*scale), bot_y0, width - int(8*scale), bot_y1], fill=(10, 14, 20, 235), outline=(30, 41, 59, 200), width=1)

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        f_title = self._get_font("ui", 11, scale, bold=True)
        f_clock = self._get_font("mono", 11, scale, bold=True)
        f_num_big = self._get_font("mono", 25, scale, bold=True)
        f_num_med = self._get_font("ui", 12, scale, bold=True)
        f_label = self._get_font("ui", 9.5, scale, bold=True)
        f_val = self._get_font("ui", 9.5, scale, bold=True)
        f_small = self._get_font("ui", 8.5, scale, bold=False)
        f_badge = self._get_font("ui", 13, scale, bold=True)

        c_cs2_orange = "#f59e0b"
        c_ct_blue = "#38bdf8"
        c_white = "#f8fafc"
        c_slate = "#94a3b8"
        c_green = "#10b981"
        c_red = "#ef4444"

        def temp_color(t):
            if t < 55: return c_green
            elif t < 75: return c_cs2_orange
            else: return c_red

        # Barra de Destaque Superior Tática CS2
        stripe_h = max(2, int(3 * scale))
        draw.rectangle([0, 0, width // 2, stripe_h], fill=c_ct_blue)
        draw.rectangle([width // 2, 0, width, stripe_h], fill=c_cs2_orange)

        draw.text((int(14 * scale), int(6 * scale)), "COUNTER-STRIKE 2 // TACTICAL TELEMETRY HUD", fill=c_white, font=f_title)
        draw.text((width - int(120 * scale), int(6 * scale)), stats.get("time", "00:00"), fill=c_cs2_orange, font=f_clock)

        # Painel Esquerdo: CT SPEC-OPS (CPU Core)
        px0 = int(8 * scale)
        px1 = side_w
        head_h = int(22 * scale)
        draw.rectangle([px0, my0, px1, my0 + head_h], fill="#0284c7")
        draw.text((px0 + int(8*scale), my0 + int(4*scale)), "[ CT ] PROCESSOR // INTEL CORE", fill=c_white, font=f_label)

        cpu_t = stats.get("cpu_temp", 45)
        c_cpu = temp_color(cpu_t)
        draw.text((px0 + int(14*scale), my0 + head_h + int(8*scale)), f"{cpu_t}°C", fill=c_cpu, font=f_num_big)

        line1_y = my0 + head_h + int(48*scale)
        draw.text((px0 + int(14*scale), line1_y), f"LOAD: {stats.get('cpu_usage', 0)}%", fill=c_white, font=f_num_med)

        line2_y = line1_y + int(24*scale)
        clock_val = stats.get("cpu_clock", 4.8)
        clock_str = f"{clock_val:.2f} GHz" if clock_val > 0 else "BOOST ACTIVE"
        draw.text((px0 + int(14*scale), line2_y), f"CLOCK: {clock_str}", fill=c_ct_blue, font=f_val)

        line3_y = line2_y + int(22*scale)
        draw.text((px0 + int(14*scale), line3_y), f"FAN: {stats.get('cpu_fan', 0)} RPM", fill=c_slate, font=f_val)

        bar_y = my1 - int(24*scale)
        bar_w = (px1 - px0) - int(28*scale)
        bar_bx = px0 + int(14*scale)
        draw.rectangle([bar_bx, bar_y, bar_bx + bar_w, bar_y + int(10*scale)], fill="#15202b", outline="#334155", width=1)
        fill_w = int(bar_w * (min(100, max(0, stats.get("cpu_usage", 0))) / 100.0))
        if fill_w > 0:
            draw.rectangle([bar_bx, bar_y, bar_bx + fill_w, bar_y + int(10*scale)], fill=c_ct_blue)

        # Painel Direito: T ORDNANCE (GPU GeForce)
        draw.rectangle([rx0, my0, rx1, my0 + head_h], fill="#d97706")
        draw.text((rx0 + int(8*scale), my0 + int(4*scale)), "[ T ] GRAPHICS // NVIDIA RTX 4070 Ti", fill=c_white, font=f_label)

        gpu_t = stats.get("gpu_temp", 48)
        c_gpu = temp_color(gpu_t)
        draw.text((rx0 + int(14*scale), my0 + head_h + int(8*scale)), f"{gpu_t}°C", fill=c_gpu, font=f_num_big)

        draw.text((rx0 + int(14*scale), line1_y), f"LOAD: {stats.get('gpu_usage', 0)}%", fill=c_white, font=f_num_med)

        vram_str = f"{stats.get('gpu_mem_used_gb', 0):.1f} / {stats.get('gpu_mem_total_gb', 12.0):.1f} GB"
        draw.text((rx0 + int(14*scale), line2_y), f"VRAM: {vram_str}", fill=c_cs2_orange, font=f_val)

        draw.text((rx0 + int(14*scale), line3_y), f"FAN: {stats.get('gpu_fan', 0)} RPM", fill=c_slate, font=f_val)

        draw.rectangle([rx0 + int(14*scale), bar_y, rx0 + int(14*scale) + bar_w, bar_y + int(10*scale)], fill="#231a10", outline="#334155", width=1)
        fill_gw = int(bar_w * (min(100, max(0, stats.get("gpu_usage", 0))) / 100.0))
        if fill_gw > 0:
            draw.rectangle([rx0 + int(14*scale), bar_y, rx0 + int(14*scale) + fill_gw, bar_y + int(10*scale)], fill=c_cs2_orange)

        # Barra Inferior: Round Stats / net_graph
        bot_y = bot_y0
        col_w = (width - int(16*scale)) // (3 if not is_compact else 2)

        draw.text((int(16*scale), bot_y + int(8*scale)), f"ARMOR // RAM: {stats.get('ram_usage', 0)}% ({stats.get('ram_used_gb', 0)} GB)", fill=c_white, font=f_val)
        draw.text((int(16*scale), bot_y + int(26*scale)), f"SYS TEMP: {stats.get('sys_temp', 38)}°C", fill=c_slate, font=f_small)

        if not is_compact:
            c2_x = int(16*scale) + col_w
            draw.text((c2_x, bot_y + int(8*scale)), f"AMMO DEPOT: C: {stats.get('disk_c_free_gb', 0)} GB LIVRE", fill=c_ct_blue, font=f_val)
            draw.text((c2_x, bot_y + int(26*scale)), f"DRIVE E: {stats.get('disk_e_free_gb', 0)} GB LIVRE", fill=c_slate, font=f_small)

        c3_x = width - int(180*scale)
        draw.text((c3_x, bot_y + int(8*scale)), f"DL: {stats.get('net_down_str', '0.0 KB/s')}", fill=c_green, font=f_val)
        draw.text((c3_x, bot_y + int(26*scale)), f"UL: {stats.get('net_up_str', '0.0 KB/s')}", fill=c_cs2_orange, font=f_small)

        badge_w = int(100 * scale)
        badge_h = int(28 * scale)
        badge_x = (width - badge_w) // 2
        badge_y = my1 - int(24 * scale)
        draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill="#0f172a", outline=c_cs2_orange, width=2)
        draw.text((badge_x + badge_w // 2, badge_y + badge_h // 2 - int(2*scale)), "CS2 HUD", fill=c_white, font=f_badge, anchor="mm")

        return img

    def render_pubg_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'PUBG Battlegrounds' (Erangel Survival HUD)."""
        scale = min(width / 568.888, height / 320.0)
        is_compact = (width <= 640)

        # 1. Carregar Wallpaper PUBG
        bg_path = os.path.join(self.assets_dir, "pubg_wallpaper.jpg")
        if os.path.exists(bg_path):
            base_img = Image.open(bg_path).convert("RGB")
            base_ratio = base_img.width / float(base_img.height)
            target_ratio = width / float(height)
            if base_ratio > target_ratio:
                nh = height
                nw = int(height * base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                x_off = (nw - width) // 2
                img = base_resized.crop((x_off, 0, x_off + width, height))
            else:
                nw = width
                nh = int(width / base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                y_off = (nh - height) // 2
                img = base_resized.crop((0, y_off, width, y_off + height))
        else:
            img = Image.new("RGB", (width, height), "#0c100e")

        # 2. Camada Transparência HUD PUBG Battle Royale
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d_ov = ImageDraw.Draw(overlay)

        bar_h = int(26 * scale)
        d_ov.rectangle([0, 0, width, bar_h], fill=(12, 16, 14, 235))

        side_w = int(width * (0.33 if not is_compact else 0.40))
        my0 = bar_h + int(8 * scale)
        my1 = height - int(60 * scale)

        # Painel Esquerdo (Survivor Status / CPU) - Contorno Hazard Amarelo
        d_ov.rectangle([int(8*scale), my0, side_w, my1], fill=(12, 18, 14, 215), outline=(250, 204, 21, 200), width=max(1, int(1.5*scale)))

        # Painel Direito (Airdrop Crate / GPU) - Contorno Vermelho Smoke
        rx0 = width - side_w
        rx1 = width - int(8 * scale)
        d_ov.rectangle([rx0, my0, rx1, my1], fill=(18, 12, 12, 215), outline=(239, 68, 68, 200), width=max(1, int(1.5*scale)))

        # Barra Inferior (Match Telemetry & Chicken Dinner)
        bot_y0 = my1 + int(6 * scale)
        bot_y1 = height - int(4 * scale)
        d_ov.rectangle([int(8*scale), bot_y0, width - int(8*scale), bot_y1], fill=(10, 14, 12, 235), outline=(30, 41, 59, 200), width=1)

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        f_title = self._get_font("ui", 11, scale, bold=True)
        f_clock = self._get_font("mono", 11, scale, bold=True)
        f_num_big = self._get_font("mono", 25, scale, bold=True)
        f_num_med = self._get_font("ui", 12, scale, bold=True)
        f_label = self._get_font("ui", 9.5, scale, bold=True)
        f_val = self._get_font("ui", 9.5, scale, bold=True)
        f_small = self._get_font("ui", 8.5, scale, bold=False)
        f_badge = self._get_font("ui", 10.5, scale, bold=True)

        c_hazard_yellow = "#facc15"
        c_airdrop_red = "#ef4444"
        c_white = "#f8fafc"
        c_slate = "#94a3b8"
        c_green = "#22c55e"

        def temp_color(t):
            if t < 55: return c_green
            elif t < 75: return c_hazard_yellow
            else: return c_airdrop_red

        # Barra Superior Militar
        stripe_h = max(2, int(3 * scale))
        draw.rectangle([0, 0, width // 2, stripe_h], fill=c_hazard_yellow)
        draw.rectangle([width // 2, 0, width, stripe_h], fill=c_airdrop_red)

        draw.text((int(14 * scale), int(6 * scale)), "PUBG: BATTLEGROUNDS // ERANGEL SURVIVAL HUD", fill=c_white, font=f_title)
        draw.text((width - int(120 * scale), int(6 * scale)), stats.get("time", "00:00"), fill=c_hazard_yellow, font=f_clock)

        # Painel Esquerdo: SURVIVOR STATUS (CPU Core)
        px0 = int(8 * scale)
        px1 = side_w
        head_h = int(22 * scale)
        draw.rectangle([px0, my0, px1, my0 + head_h], fill="#ca8a04")
        draw.text((px0 + int(8*scale), my0 + int(4*scale)), "SURVIVOR STATUS // CPU PROCESSOR", fill="#0f172a", font=f_label)

        cpu_t = stats.get("cpu_temp", 45)
        c_cpu = temp_color(cpu_t)
        draw.text((px0 + int(14*scale), my0 + head_h + int(8*scale)), f"{cpu_t}°C", fill=c_cpu, font=f_num_big)

        line1_y = my0 + head_h + int(48*scale)
        draw.text((px0 + int(14*scale), line1_y), f"HEALTH / LOAD: {stats.get('cpu_usage', 0)}%", fill=c_white, font=f_num_med)

        line2_y = line1_y + int(24*scale)
        clock_val = stats.get("cpu_clock", 4.8)
        clock_str = f"{clock_val:.2f} GHz" if clock_val > 0 else "BOOST ACTIVE"
        draw.text((px0 + int(14*scale), line2_y), f"BOOST: {clock_str}", fill=c_hazard_yellow, font=f_val)

        line3_y = line2_y + int(22*scale)
        draw.text((px0 + int(14*scale), line3_y), f"LVL 3 HELMET FAN: {stats.get('cpu_fan', 0)} RPM", fill=c_slate, font=f_val)

        bar_y = my1 - int(24*scale)
        bar_w = (px1 - px0) - int(28*scale)
        bar_bx = px0 + int(14*scale)
        draw.rectangle([bar_bx, bar_y, bar_bx + bar_w, bar_y + int(10*scale)], fill="#1a251c", outline="#334155", width=1)
        fill_w = int(bar_w * (min(100, max(0, stats.get("cpu_usage", 0))) / 100.0))
        if fill_w > 0:
            draw.rectangle([bar_bx, bar_y, bar_bx + fill_w, bar_y + int(10*scale)], fill=c_green)

        # Painel Direito: AIRDROP SUPPLY (GPU GeForce RTX)
        draw.rectangle([rx0, my0, rx1, my0 + head_h], fill="#dc2626")
        draw.text((rx0 + int(8*scale), my0 + int(4*scale)), "AIRDROP CRATE // GPU RTX 4070 Ti", fill=c_white, font=f_label)

        gpu_t = stats.get("gpu_temp", 48)
        c_gpu = temp_color(gpu_t)
        draw.text((rx0 + int(14*scale), my0 + head_h + int(8*scale)), f"{gpu_t}°C", fill=c_gpu, font=f_num_big)

        draw.text((rx0 + int(14*scale), line1_y), f"POWER / LOAD: {stats.get('gpu_usage', 0)}%", fill=c_white, font=f_num_med)

        vram_str = f"{stats.get('gpu_mem_used_gb', 0):.1f} / {stats.get('gpu_mem_total_gb', 12.0):.1f} GB"
        draw.text((rx0 + int(14*scale), line2_y), f"LVL 3 BACKPACK: {vram_str}", fill=c_hazard_yellow, font=f_val)

        draw.text((rx0 + int(14*scale), line3_y), f"CRATE EXHAUST: {stats.get('gpu_fan', 0)} RPM", fill=c_slate, font=f_val)

        draw.rectangle([rx0 + int(14*scale), bar_y, rx0 + int(14*scale) + bar_w, bar_y + int(10*scale)], fill="#251616", outline="#334155", width=1)
        fill_gw = int(bar_w * (min(100, max(0, stats.get("gpu_usage", 0))) / 100.0))
        if fill_gw > 0:
            draw.rectangle([rx0 + int(14*scale), bar_y, rx0 + int(14*scale) + fill_gw, bar_y + int(10*scale)], fill=c_airdrop_red)

        # Barra Inferior: Chicken Dinner & Match Telemetry
        bot_y = bot_y0
        col_w = (width - int(16*scale)) // (3 if not is_compact else 2)

        draw.text((int(16*scale), bot_y + int(8*scale)), f"VEST // RAM: {stats.get('ram_usage', 0)}% ({stats.get('ram_used_gb', 0)} GB)", fill=c_white, font=f_val)
        draw.text((int(16*scale), bot_y + int(26*scale)), f"CASE TEMP: {stats.get('sys_temp', 38)}°C", fill=c_slate, font=f_small)

        if not is_compact:
            c2_x = int(16*scale) + col_w
            draw.text((c2_x, bot_y + int(8*scale)), f"LOOT C: {stats.get('disk_c_free_gb', 0)} GB LIVRE", fill=c_hazard_yellow, font=f_val)
            draw.text((c2_x, bot_y + int(26*scale)), f"LOOT E: {stats.get('disk_e_free_gb', 0)} GB LIVRE", fill=c_slate, font=f_small)

        c3_x = width - int(180*scale)
        draw.text((c3_x, bot_y + int(8*scale)), f"ZONE DL: {stats.get('net_down_str', '0.0 KB/s')}", fill=c_green, font=f_val)
        draw.text((c3_x, bot_y + int(26*scale)), f"ZONE UL: {stats.get('net_up_str', '0.0 KB/s')}", fill=c_airdrop_red, font=f_small)

        badge_w = int(210 * scale)
        badge_h = int(28 * scale)
        badge_x = (width - badge_w) // 2
        badge_y = my1 - int(24 * scale)
        draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill="#1c1917", outline=c_hazard_yellow, width=2)
        draw.text((badge_x + badge_w // 2, badge_y + badge_h // 2 - int(1*scale)), "★ WINNER CHICKEN DINNER ★", fill=c_hazard_yellow, font=f_badge, anchor="mm")

        return img

    def render_peugeot_508_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Peugeot 508 SW' (Digital i-Cockpit GT Cluster)."""
        scale = min(width / 568.888, height / 320.0)
        is_compact = (width <= 640)

        # 1. Carregar Wallpaper do Peugeot 508 SW i-Cockpit
        bg_path = os.path.join(self.assets_dir, "peugeot_508_sw.jpg")
        if os.path.exists(bg_path):
            base_img = Image.open(bg_path).convert("RGB")
            base_ratio = base_img.width / float(base_img.height)
            target_ratio = width / float(height)
            if base_ratio > target_ratio:
                nh = height
                nw = int(height * base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                x_off = (nw - width) // 2
                img = base_resized.crop((x_off, 0, x_off + width, height))
            else:
                nw = width
                nh = int(width / base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                y_off = (nh - height) // 2
                img = base_resized.crop((0, y_off, width, y_off + height))
        else:
            img = Image.new("RGB", (width, height), "#06090e")

        # 2. Camada Transparência HUD i-Cockpit
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d_ov = ImageDraw.Draw(overlay)

        bar_h = int(26 * scale)
        d_ov.rectangle([0, 0, width, bar_h], fill=(6, 9, 14, 230))

        side_w = int(width * (0.33 if not is_compact else 0.40))
        my0 = bar_h + int(8 * scale)
        my1 = height - int(60 * scale)

        # Mostrador Esquerdo: Velocímetro Digital (CPU Clock & Load) - Contorno Ciano Peugeot
        d_ov.rectangle([int(8*scale), my0, side_w, my1], fill=(6, 12, 18, 215), outline=(0, 210, 255, 200), width=max(1, int(1.5*scale)))

        # Mostrador Direito: Conta-Rotações Invertido (GPU VRAM & Load) - Contorno Azul Elétrico
        rx0 = width - side_w
        rx1 = width - int(8 * scale)
        d_ov.rectangle([rx0, my0, rx1, my1], fill=(6, 12, 18, 215), outline=(0, 140, 255, 200), width=max(1, int(1.5*scale)))

        # Barra Inferior: Informações de Condução e Telemetria
        bot_y0 = my1 + int(6 * scale)
        bot_y1 = height - int(4 * scale)
        d_ov.rectangle([int(8*scale), bot_y0, width - int(8*scale), bot_y1], fill=(6, 10, 15, 235), outline=(30, 41, 59, 200), width=1)

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        f_title = self._get_font("ui", 10.5, scale, bold=True)
        f_clock = self._get_font("mono", 11, scale, bold=True)
        f_speed = self._get_font("mono", 28, scale, bold=True)
        f_num_med = self._get_font("ui", 12, scale, bold=True)
        f_label = self._get_font("ui", 9.5, scale, bold=True)
        f_val = self._get_font("ui", 9.5, scale, bold=True)
        f_small = self._get_font("ui", 8.5, scale, bold=False)
        f_badge = self._get_font("ui", 11, scale, bold=True)

        c_cyan = "#00d2ff"
        c_blue = "#0088ff"
        c_lime = "#d4ff00"
        c_white = "#f8fafc"
        c_slate = "#94a3b8"
        c_red = "#ef4444"

        def temp_color(t):
            if t < 55: return "#10b981"
            elif t < 75: return c_cyan
            else: return c_red

        # Faixa Superior Peugeot Sport
        stripe_h = max(2, int(3 * scale))
        draw.rectangle([0, 0, width // 2, stripe_h], fill=c_cyan)
        draw.rectangle([width // 2, 0, width, stripe_h], fill=c_lime)

        draw.text((int(14 * scale), int(6 * scale)), "PEUGEOT 508 SW // DIGITAL i-COCKPIT CLUSTER", fill=c_white, font=f_title)
        draw.text((width - int(120 * scale), int(6 * scale)), stats.get("time", "00:00"), fill=c_cyan, font=f_clock)

        # Painel Esquerdo: Velocímetro (Velocidade do Processador & Temp Motor)
        px0 = int(8 * scale)
        px1 = side_w
        head_h = int(22 * scale)
        draw.rectangle([px0, my0, px1, my0 + head_h], fill="#0284c7")
        draw.text((px0 + int(8*scale), my0 + int(4*scale)), "SPEEDOMETER // CPU CORE i7", fill=c_white, font=f_label)

        clock_val = stats.get("cpu_clock", 4.80)
        clock_str = f"{clock_val:.2f}"
        draw.text((px0 + int(14*scale), my0 + head_h + int(8*scale)), clock_str, fill=c_cyan, font=f_speed)
        draw.text((px0 + int(115*scale), my0 + head_h + int(20*scale)), "GHz", fill=c_slate, font=f_label)

        cpu_t = stats.get("cpu_temp", 48)
        c_cpu = temp_color(cpu_t)
        line1_y = my0 + head_h + int(48*scale)
        draw.text((px0 + int(14*scale), line1_y), f"ENGINE TEMP: {cpu_t}°C", fill=c_cpu, font=f_num_med)

        line2_y = line1_y + int(24*scale)
        draw.text((px0 + int(14*scale), line2_y), f"THROTTLE / LOAD: {stats.get('cpu_usage', 0)}%", fill=c_white, font=f_val)

        line3_y = line2_y + int(22*scale)
        draw.text((px0 + int(14*scale), line3_y), f"FAN RADIATOR: {stats.get('cpu_fan', 0)} RPM", fill=c_slate, font=f_val)

        # Arco do Velocímetro (Barra Progressiva Ciano)
        bar_y = my1 - int(24*scale)
        bar_w = (px1 - px0) - int(28*scale)
        bar_bx = px0 + int(14*scale)
        draw.rectangle([bar_bx, bar_y, bar_bx + bar_w, bar_y + int(10*scale)], fill="#0b1724", outline="#1e293b", width=1)
        fill_w = int(bar_w * (min(100, max(0, stats.get("cpu_usage", 0))) / 100.0))
        if fill_w > 0:
            draw.rectangle([bar_bx, bar_y, bar_bx + fill_w, bar_y + int(10*scale)], fill=c_cyan)

        # Painel Direito: Conta-Rotações Invertido (GPU RTX 4070 Ti & Turbo)
        draw.rectangle([rx0, my0, rx1, my0 + head_h], fill="#0369a1")
        draw.text((rx0 + int(8*scale), my0 + int(4*scale)), "TACHOMETER // NVIDIA RTX 4070 Ti", fill=c_white, font=f_label)

        gpu_load = stats.get("gpu_usage", 0)
        draw.text((rx0 + int(14*scale), my0 + head_h + int(8*scale)), f"{gpu_load}", fill=c_lime, font=f_speed)
        draw.text((rx0 + int(85*scale), my0 + head_h + int(20*scale)), "% RPM", fill=c_slate, font=f_label)

        gpu_t = stats.get("gpu_temp", 50)
        c_gpu = temp_color(gpu_t)
        draw.text((rx0 + int(14*scale), line1_y), f"OIL / GPU TEMP: {gpu_t}°C", fill=c_gpu, font=f_num_med)

        vram_str = f"{stats.get('gpu_mem_used_gb', 0):.1f} / {stats.get('gpu_mem_total_gb', 12.0):.1f} GB"
        draw.text((rx0 + int(14*scale), line2_y), f"VRAM BUFFER: {vram_str}", fill=c_white, font=f_val)

        draw.text((rx0 + int(14*scale), line3_y), f"EXHAUST TURBO: {stats.get('gpu_fan', 0)} RPM", fill=c_slate, font=f_val)

        # Barra do Conta-Rotações
        draw.rectangle([rx0 + int(14*scale), bar_y, rx0 + int(14*scale) + bar_w, bar_y + int(10*scale)], fill="#0b1724", outline="#1e293b", width=1)
        fill_gw = int(bar_w * (min(100, max(0, stats.get("gpu_usage", 0))) / 100.0))
        if fill_gw > 0:
            draw.rectangle([rx0 + int(14*scale), bar_y, rx0 + int(14*scale) + fill_gw, bar_y + int(10*scale)], fill=c_lime)

        # Painel Central: Holograma do 508 SW & Modos de Condução
        center_x = width // 2
        badge_w = int(140 * scale)
        badge_h = int(28 * scale)
        badge_x = center_x - badge_w // 2
        badge_y = my1 - int(24 * scale)
        draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill="#08101a", outline=c_cyan, width=2)
        draw.text((center_x, badge_y + badge_h // 2 - int(1*scale)), "SPORT // D8", fill=c_cyan, font=f_badge, anchor="mm")

        # Barra Inferior: Condução & Computador de Bordo
        bot_y = bot_y0
        col_w = (width - int(16*scale)) // (3 if not is_compact else 2)

        draw.text((int(16*scale), bot_y + int(8*scale)), f"BATTERY // RAM: {stats.get('ram_usage', 0)}% ({stats.get('ram_used_gb', 0)} GB)", fill=c_white, font=f_val)
        draw.text((int(16*scale), bot_y + int(26*scale)), f"CABIN TEMP: {stats.get('sys_temp', 38)}°C", fill=c_slate, font=f_small)

        if not is_compact:
            c2_x = int(16*scale) + col_w
            draw.text((c2_x, bot_y + int(8*scale)), f"TRIP SSD C: {stats.get('disk_c_free_gb', 0)} GB LIVRE", fill=c_cyan, font=f_val)
            draw.text((c2_x, bot_y + int(26*scale)), f"TRIP SSD E: {stats.get('disk_e_free_gb', 0)} GB LIVRE", fill=c_slate, font=f_small)

        c3_x = width - int(180*scale)
        draw.text((c3_x, bot_y + int(8*scale)), f"FLOW DL: {stats.get('net_down_str', '0.0 KB/s')}", fill="#10b981", font=f_val)
        draw.text((c3_x, bot_y + int(26*scale)), f"FLOW UL: {stats.get('net_up_str', '0.0 KB/s')}", fill=c_cyan, font=f_small)

        return img

    def render_mixer_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Mesa de Mistura DJ' (Studio Audio Equalizer)."""
        scale = min(width / 568.888, height / 320.0)
        is_compact = (width <= 640)

        # 1. Carregar Wallpaper de Mesa de Mistura
        bg_path = os.path.join(self.assets_dir, "dj_mixer.jpg")
        if os.path.exists(bg_path):
            base_img = Image.open(bg_path).convert("RGB")
            base_ratio = base_img.width / float(base_img.height)
            target_ratio = width / float(height)
            if base_ratio > target_ratio:
                nh = height
                nw = int(height * base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                x_off = (nw - width) // 2
                img = base_resized.crop((x_off, 0, x_off + width, height))
            else:
                nw = width
                nh = int(width / base_ratio)
                base_resized = base_img.resize((nw, nh), Image.Resampling.LANCZOS)
                y_off = (nh - height) // 2
                img = base_resized.crop((0, y_off, width, y_off + height))
        else:
            img = Image.new("RGB", (width, height), "#080b10")

        # 2. Camada Transparência HUD Mesa de Mistura
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        d_ov = ImageDraw.Draw(overlay)

        bar_h = int(26 * scale)
        d_ov.rectangle([0, 0, width, bar_h], fill=(8, 12, 18, 235))

        bot_h = int(24 * scale)
        d_ov.rectangle([0, height - bot_h, width, height], fill=(8, 12, 18, 240))

        num_channels = 6
        pad_x = int(8 * scale)
        usable_w = width - (2 * pad_x)
        col_w = usable_w / float(num_channels)
        content_y0 = bar_h + int(6 * scale)
        content_y1 = height - bot_h - int(6 * scale)

        for i in range(num_channels):
            cx0 = int(pad_x + i * col_w) + int(2 * scale)
            cx1 = int(pad_x + (i + 1) * col_w) - int(2 * scale)
            d_ov.rectangle([cx0, content_y0, cx1, content_y1], fill=(10, 15, 22, 215), outline=(30, 41, 59, 180), width=1)

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        f_title = self._get_font("ui", 10, scale, bold=True)
        f_clock = self._get_font("mono", 11, scale, bold=True)
        f_ch_title = self._get_font("ui", 8.5, scale, bold=True)
        f_val_giant = self._get_font("mono", 13, scale, bold=True)
        f_val_med = self._get_font("ui", 9.5, scale, bold=True)
        f_small = self._get_font("ui", 8.0, scale, bold=False)
        f_badge = self._get_font("mono", 8.5, scale, bold=True)

        c_cyan = "#00d2ff"
        c_green = "#10b981"
        c_amber = "#fbbf24"
        c_white = "#f8fafc"
        c_slate = "#94a3b8"

        # Barra Superior
        draw.rectangle([0, 0, int(width * 0.35), int(2.5 * scale)], fill=c_cyan)
        draw.rectangle([int(width * 0.35), 0, int(width * 0.70), int(2.5 * scale)], fill=c_green)
        draw.rectangle([int(width * 0.70), 0, width, int(2.5 * scale)], fill=c_amber)

        draw.text((int(12 * scale), int(6 * scale)), "STUDIO MIXER // MASTER TELEMETRY EQUALIZER", fill=c_white, font=f_title)
        if not is_compact:
            draw.text((int(width * 0.52), int(7 * scale)), "24-BIT / 96kHz LIVE BUS", fill=c_slate, font=f_small)
        draw.text((width - int(100 * scale), int(6 * scale)), stats.get("time", "00:00"), fill=c_amber, font=f_clock)

        channels_data = [
            {
                "name": "CH 1: CPU",
                "stat1": f"{stats.get('cpu_clock', 4.80):.2f} GHz",
                "stat2": f"{stats.get('cpu_temp', 47)}°C",
                "val_str": f"{stats.get('cpu_usage', 0)}%",
                "ratio": stats.get("cpu_usage", 0) / 100.0,
                "foot": f"{stats.get('cpu_fan', 0)} RPM",
                "color": c_cyan
            },
            {
                "name": "CH 2: GPU",
                "stat1": "RTX 4070Ti",
                "stat2": f"{stats.get('gpu_temp', 50)}°C",
                "val_str": f"{stats.get('gpu_usage', 0)}%",
                "ratio": stats.get("gpu_usage", 0) / 100.0,
                "foot": f"{stats.get('gpu_fan', 0)} RPM",
                "color": c_green
            },
            {
                "name": "CH 3: RAM",
                "stat1": f"{stats.get('ram_used_gb', 0)} GB",
                "stat2": "DDR5",
                "val_str": f"{stats.get('ram_usage', 0)}%",
                "ratio": stats.get("ram_usage", 0) / 100.0,
                "foot": "MEMORY",
                "color": c_amber
            },
            {
                "name": "CH 4: SSD",
                "stat1": f"C:{stats.get('disk_c_free_gb', 0)}G",
                "stat2": f"E:{stats.get('disk_e_free_gb', 0)}G",
                "val_str": f"{stats.get('disk_c_usage', 56)}%",
                "ratio": stats.get("disk_c_usage", 56) / 100.0,
                "foot": "NVMe M.2",
                "color": c_cyan
            },
            {
                "name": "CH 5: NET",
                "stat1": f"DL {stats.get('net_down_str', '0M')}",
                "stat2": f"UL {stats.get('net_up_str', '0M')}",
                "val_str": "FLOW",
                "ratio": min(1.0, stats.get("net_down_kb", 8400) / 15000.0),
                "foot": "GbE LAN",
                "color": c_green
            },
            {
                "name": "CH 6: MAIN",
                "stat1": f"SYS {stats.get('sys_temp', 38)}°C",
                "stat2": "OUT 0dB",
                "val_str": "MASTER",
                "ratio": max(stats.get("cpu_usage", 0), stats.get("gpu_usage", 0)) / 100.0,
                "foot": f"{stats.get('chassis_fan', 1100)} RPM",
                "color": c_amber
            }
        ]

        for i, ch in enumerate(channels_data):
            cx0 = int(pad_x + i * col_w) + int(2 * scale)
            cx1 = int(pad_x + (i + 1) * col_w) - int(2 * scale)
            mid_x = (cx0 + cx1) // 2

            head_y = content_y0 + int(4 * scale)
            head_h = int(18 * scale)
            draw.rectangle([cx0 + int(4*scale), head_y, cx1 - int(4*scale), head_y + head_h], fill="#0e1726", outline="#1e293b", width=1)
            draw.text((mid_x, head_y + head_h // 2), ch["name"], fill=ch["color"], font=f_ch_title, anchor="mm")

            t_y = head_y + head_h + int(4 * scale)
            draw.text((mid_x, t_y), ch["stat1"], fill=c_white, font=f_val_med, anchor="mt")
            draw.text((mid_x, t_y + int(14 * scale)), ch["stat2"], fill=ch["color"], font=f_small, anchor="mt")

            meter_y = t_y + int(30 * scale)
            meter_h = content_y1 - meter_y - int(40 * scale)

            if not is_compact:
                vu_w = int(14 * scale)
                vu_x1 = mid_x - int(24 * scale)
                vu_x2 = vu_x1 + vu_w + int(3 * scale)
                self._draw_led_vu_meter(draw, vu_x1, meter_y, vu_w, meter_h, ch["ratio"], num_segments=18, scale=scale)
                r_ratio = max(0.0, min(1.0, ch["ratio"] * (0.92 if i % 2 == 0 else 1.05)))
                self._draw_led_vu_meter(draw, vu_x2, meter_y, vu_w, meter_h, r_ratio, num_segments=18, scale=scale)

                fader_x = mid_x + int(24 * scale)
                self._draw_fader(draw, fader_x, meter_y, meter_h, ch["ratio"], scale=scale)
            else:
                vu_w = int(22 * scale)
                vu_x = mid_x - vu_w // 2
                self._draw_led_vu_meter(draw, vu_x, meter_y, vu_w, meter_h, ch["ratio"], num_segments=14, scale=scale)

            val_y = content_y1 - int(34 * scale)
            draw.text((mid_x, val_y), ch["val_str"], fill=c_white, font=f_val_giant, anchor="mm")

            foot_y = content_y1 - int(16 * scale)
            draw.text((mid_x, foot_y), ch["foot"], fill=c_slate, font=f_small, anchor="mm")

        bot_text_y = height - bot_h + int(4 * scale)
        draw.text((int(14 * scale), bot_text_y), "● REC [ACTIVE]   ► PLAY [ON]   SOLO [CUE]   CROSSFADER [CH 1 <---> CH 2]", fill=c_slate, font=f_small)
        draw.text((width - int(14 * scale), bot_text_y), f"BPM: {int(stats.get('cpu_clock', 4.80) * 26.5)} // DSP LOCK", fill=c_green, font=f_badge, anchor="rt")

        return img

    def render_transparent_hud_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'HUD Overlay Transparente (Glass HUD)'.
        Utiliza a cor chroma-key (1, 2, 3) no fundo para transparência 100% nativa no Windows DWM,
        deixando os mostradores e cartões de vidro a flutuar diretamente sobre o 2º ecrã sem colisões de texto!"""
        scale = min(width / 568.888, height / 320.0)
        is_compact = (width <= 640)

        # 1. Fundo Puro Chroma-Key (1, 2, 3) -> 100% transparente no ecrã do PC
        img = Image.new("RGB", (width, height), (1, 2, 3))
        draw = ImageDraw.Draw(img)

        # Fontes escaladas com fator controlado para evitar fontes gigantes e colisões
        f_header = self._get_font("ui", 10.0, scale, bold=True)
        f_clock = self._get_font("mono", 11.5, scale, bold=True)
        f_title = self._get_font("ui", 9.5, scale, bold=True)
        f_val = self._get_font("mono", 10.0, scale, bold=True)
        f_small = self._get_font("ui", 9.0, scale, bold=False)
        f_micro = self._get_font("mono", 8.0, scale, bold=False)

        c_cyan = "#00e5ff"
        c_emerald = "#10b981"
        c_amber = "#f59e0b"
        c_red = "#ef4444"
        c_slate = "#94a3b8"
        c_white = "#f8fafc"

        # Barra Superior Flutuante
        top_h = int(24 * min(1.3, scale))
        self._draw_hud_bracket_card(draw, int(8*scale), int(4*scale), width - int(8*scale), top_h + int(4*scale), scale, fill=(6, 12, 18), border=(0, 229, 255), bracket_len=8)

        dot_r = int(3.5 * min(1.3, scale))
        dot_cx = int(20 * scale)
        dot_cy = (int(4*scale) + top_h + int(4*scale)) // 2
        draw.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r], fill=c_emerald)

        title_text = "HUD OVERLAY // 2º ECRÃ"
        draw.text((int(32 * scale), dot_cy), title_text, fill=c_white, font=f_header, anchor="lm")
        t_bbox = draw.textbbox((int(32 * scale), dot_cy), title_text, font=f_header, anchor="lm")

        clock_str = stats.get("time", "12:00:00")
        c_bbox = draw.textbbox((width - int(18 * scale), dot_cy), clock_str, font=f_clock, anchor="rm")
        draw.text((width - int(18 * scale), dot_cy), clock_str, fill=c_cyan, font=f_clock, anchor="rm")

        # Desenha subtítulo central apenas se houver espaço livre suficiente (garante zero sobreposição)
        sub_text = "[ TARRASGA TELEMETRY // GLASS MODE ]"
        sub_bbox = draw.textbbox((width // 2, dot_cy), sub_text, font=f_small, anchor="mm")
        if t_bbox[2] + 40 < sub_bbox[0] and sub_bbox[2] + 40 < c_bbox[0]:
            draw.text((width // 2, dot_cy), sub_text, fill=c_slate, font=f_small, anchor="mm")

        # Conteúdo Central
        content_y0 = top_h + int(10 * scale)
        bot_h = int(22 * min(1.3, scale))
        content_y1 = height - bot_h - int(8 * scale)

        pad = int(8 * scale)
        usable_w = width - (2 * pad)

        if is_compact:
            # Layout Compacto para USB (480x320) ou janela reduzida
            col_w = (usable_w - pad) / 2.0
            c0_x0 = int(pad)
            c0_x1 = int(pad + col_w)
            c1_x0 = int(pad + col_w + pad)
            c1_x1 = int(width - pad)

            self._draw_hud_bracket_card(draw, c0_x0, content_y0, c0_x1, content_y1, scale, fill=(8, 14, 22), border=(0, 229, 255), bracket_len=12)
            self._draw_hud_bracket_card(draw, c1_x0, content_y0, c1_x1, content_y1, scale, fill=(8, 14, 22), border=(16, 185, 129), bracket_len=12)

            cpu_u = stats.get("cpu_usage", 38)
            cpu_t = stats.get("cpu_temp", 52)
            cpu_t_col = c_red if cpu_t >= 75 else (c_amber if cpu_t >= 60 else c_emerald)
            self._draw_circular_hud_meter(draw, (c0_x0 + c0_x1)//2, content_y0 + int(60*scale), 38, cpu_u, scale, label="CPU LOAD", val_str=f"{cpu_u}%", temp_str=f"{cpu_t}°C", primary_color=c_cyan, temp_color=cpu_t_col)

            draw.text(((c0_x0 + c0_x1)//2, content_y0 + int(115*scale)), f"{stats.get('cpu_clock', 4.50):.2f} GHz  |  {stats.get('cpu_fan', 1200)} RPM", fill=c_white, font=f_small, anchor="mm")
            draw.text(((c0_x0 + c0_x1)//2, content_y0 + int(130*scale)), f"RAM: {stats.get('ram_used_gb', 14.2):.1f}/{stats.get('ram_total_gb', 32.0):.0f} GB ({stats.get('ram_usage_pct', 44)}%)", fill=c_slate, font=f_small, anchor="mm")

            gpu_u = stats.get("gpu_usage", 65)
            gpu_t = stats.get("gpu_temp", 64)
            gpu_t_col = c_red if gpu_t >= 75 else (c_amber if gpu_t >= 60 else c_emerald)
            self._draw_circular_hud_meter(draw, (c1_x0 + c1_x1)//2, content_y0 + int(60*scale), 38, gpu_u, scale, label="GPU LOAD", val_str=f"{gpu_u}%", temp_str=f"{gpu_t}°C", primary_color=c_emerald, temp_color=gpu_t_col)

            draw.text(((c1_x0 + c1_x1)//2, content_y0 + int(115*scale)), f"VRAM: {stats.get('gpu_vram_used', 6.2):.1f}/{stats.get('gpu_vram_total', 12.0):.0f} GB ({stats.get('gpu_vram_pct', 52)}%)", fill=c_white, font=f_small, anchor="mm")
            draw.text(((c1_x0 + c1_x1)//2, content_y0 + int(130*scale)), f"NET DL: {stats.get('net_down_str', '12.4 MB/s')} | PWR: ~{stats.get('gpu_power', 165)}W", fill=c_slate, font=f_small, anchor="mm")

        else:
            # Grelha 2x2 Ampla (Perfeita para 1020x602, 1280x720 e 1920x1080)
            gap_x = int(10 * scale)
            gap_y = int(10 * scale)
            card_w = (usable_w - gap_x) // 2
            card_h = (content_y1 - content_y0 - gap_y) // 2

            # 1. Cartão Top-Left: PROCESSADOR (CPU)
            c0_x0 = pad
            c0_y0 = content_y0
            c0_x1 = c0_x0 + card_w
            c0_y1 = c0_y0 + card_h
            self._draw_hud_bracket_card(draw, c0_x0, c0_y0, c0_x1, c0_y1, scale, fill=(8, 14, 22), border=(0, 229, 255), bracket_len=14)
            draw.text((c0_x0 + int(14*scale), c0_y0 + int(10*scale)), "SYS // PROCESSADOR (CPU)", fill=c_cyan, font=f_title)

            dial_cx = c0_x0 + int(card_w * 0.28)
            dial_cy = (c0_y0 + c0_y1) // 2 + int(6*scale)
            cpu_u = stats.get("cpu_usage", 35)
            cpu_t = stats.get("cpu_temp", 54)
            cpu_t_col = c_red if cpu_t >= 75 else (c_amber if cpu_t >= 60 else c_emerald)
            self._draw_circular_hud_meter(draw, dial_cx, dial_cy, 38, cpu_u, scale, label="CORE LOAD", val_str=f"{cpu_u}%", temp_str=f"{cpu_t}°C", primary_color=c_cyan, temp_color=cpu_t_col)

            rx0 = c0_x0 + int(card_w * 0.54)
            rx1 = c0_x1 - int(16*scale)
            lines_cpu = [
                ("FREQUÊNCIA:", f"{stats.get('cpu_clock', 4.80):.2f} GHz"),
                ("POTÊNCIA:", f"~{stats.get('cpu_power', 65)} W"),
                ("VENTOINHA:", f"{stats.get('cpu_fan', 1280)} RPM"),
                ("CORES:", f"{stats.get('cpu_cores', '14C / 20T')}"),
            ]
            ry = c0_y0 + int(36*scale)
            step_y = max(18, int((c0_y1 - c0_y0 - 52*scale) / len(lines_cpu)))
            for lbl, v in lines_cpu:
                draw.text((rx0, ry), lbl, fill=c_slate, font=f_small, anchor="la")
                draw.text((rx1, ry), v, fill=c_white, font=f_val, anchor="ra")
                ry += step_y

            # 2. Cartão Top-Right: PLACA GRÁFICA (GPU)
            c1_x0 = c0_x1 + gap_x
            c1_y0 = content_y0
            c1_x1 = width - pad
            c1_y1 = c1_y0 + card_h
            self._draw_hud_bracket_card(draw, c1_x0, c1_y0, c1_x1, c1_y1, scale, fill=(8, 14, 22), border=(16, 185, 129), bracket_len=14)
            draw.text((c1_x0 + int(14*scale), c1_y0 + int(10*scale)), f"SYS // {stats.get('gpu_name', 'GEFORCE RTX')}", fill=c_emerald, font=f_title)

            g_dial_cx = c1_x0 + int(card_w * 0.28)
            g_dial_cy = dial_cy
            gpu_u = stats.get("gpu_usage", 72)
            gpu_t = stats.get("gpu_temp", 66)
            gpu_t_col = c_red if gpu_t >= 75 else (c_amber if gpu_t >= 60 else c_emerald)
            self._draw_circular_hud_meter(draw, g_dial_cx, g_dial_cy, 38, gpu_u, scale, label="GPU LOAD", val_str=f"{gpu_u}%", temp_str=f"{gpu_t}°C", primary_color=c_emerald, temp_color=gpu_t_col)

            grx0 = c1_x0 + int(card_w * 0.54)
            grx1 = c1_x1 - int(16*scale)
            lines_gpu = [
                ("FREQUÊNCIA:", f"{stats.get('gpu_clock', 2610)} MHz"),
                ("POTÊNCIA:", f"~{stats.get('gpu_power', 182)} W"),
                ("VENTOINHA:", f"{stats.get('gpu_fan', 1540)} RPM"),
                ("DIRECTX:", "DX12 // RT ON"),
            ]
            gry = c1_y0 + int(36*scale)
            for lbl, v in lines_gpu:
                draw.text((grx0, gry), lbl, fill=c_slate, font=f_small, anchor="la")
                draw.text((grx1, gry), v, fill=c_white, font=f_val, anchor="ra")
                gry += step_y

            # 3. Cartão Bottom-Left: MEMÓRIA RAM & VRAM
            c2_x0 = pad
            c2_y0 = c0_y1 + gap_y
            c2_x1 = c2_x0 + card_w
            c2_y1 = content_y1
            self._draw_hud_bracket_card(draw, c2_x0, c2_y0, c2_x1, c2_y1, scale, fill=(8, 14, 22), border=(56, 189, 248), bracket_len=14)
            draw.text((c2_x0 + int(14*scale), c2_y0 + int(10*scale)), "SYS // MEMÓRIA RAM & VRAM DEDICADA", fill="#38bdf8", font=f_title)

            # RAM Bar
            ram_pct = stats.get("ram_usage_pct", 46)
            my_y0 = c2_y0 + int(34*scale)
            draw.text((c2_x0 + int(16*scale), my_y0), f"RAM DO SISTEMA ({ram_pct}%)", fill=c_white, font=f_small, anchor="la")
            draw.text((c2_x1 - int(16*scale), my_y0), f"{stats.get('ram_used_gb', 14.8):.1f} / {stats.get('ram_total_gb', 32.0):.0f} GB", fill=c_cyan, font=f_val, anchor="ra")

            bx0 = c2_x0 + int(16*scale)
            bx1 = c2_x1 - int(16*scale)
            by0 = my_y0 + int(16*scale)
            by1 = by0 + int(9*scale)
            draw.rectangle([bx0, by0, bx1, by1], fill=(15, 23, 42), outline=(30, 41, 59))
            fill_w = int((bx1 - bx0) * (ram_pct / 100.0))
            if fill_w > 0:
                draw.rectangle([bx0, by0, bx0 + fill_w, by1], fill=c_cyan)
            draw.text((c2_x0 + int(16*scale), by1 + int(4*scale)), f"Memória Livre: {stats.get('ram_free_gb', 17.2):.1f} GB", fill=c_slate, font=f_micro)

            # VRAM Bar
            vram_pct = stats.get("gpu_vram_pct", 58)
            vy_y0 = by1 + int(18*scale)
            draw.text((c2_x0 + int(16*scale), vy_y0), f"VRAM DEDICADA ({vram_pct}%)", fill=c_white, font=f_small, anchor="la")
            draw.text((c2_x1 - int(16*scale), vy_y0), f"{stats.get('gpu_vram_used', 7.0):.1f} / {stats.get('gpu_vram_total', 12.0):.0f} GB", fill=c_emerald, font=f_val, anchor="ra")

            v_by0 = vy_y0 + int(16*scale)
            v_by1 = v_by0 + int(9*scale)
            draw.rectangle([bx0, v_by0, bx1, v_by1], fill=(15, 23, 42), outline=(30, 41, 59))
            vfill_w = int((bx1 - bx0) * (vram_pct / 100.0))
            if vfill_w > 0:
                draw.rectangle([bx0, v_by0, bx0 + vfill_w, v_by1], fill=c_emerald)
            draw.text((c2_x0 + int(16*scale), v_by1 + int(4*scale)), "Placa Gráfica GDDR6X", fill=c_slate, font=f_micro)

            # 4. Cartão Bottom-Right: ARMAZENAMENTO & REDE
            c3_x0 = c2_x1 + gap_x
            c3_y0 = c1_y1 + gap_y
            c3_x1 = width - pad
            c3_y1 = content_y1
            self._draw_hud_bracket_card(draw, c3_x0, c3_y0, c3_x1, c3_y1, scale, fill=(8, 14, 22), border=(245, 158, 11), bracket_len=14)
            draw.text((c3_x0 + int(14*scale), c3_y0 + int(10*scale)), "SYS // ARMAZENAMENTO & REDE", fill=c_amber, font=f_title)

            sub_gap = int(14 * scale)
            sub_w = (card_w - int(32*scale) - sub_gap) // 2
            d_x0 = c3_x0 + int(16*scale)
            d_x1 = d_x0 + sub_w

            # Disco C:
            c_pct = stats.get("disk_c_pct", 82)
            dy0 = c3_y0 + int(34*scale)
            draw.text((d_x0, dy0), f"C: [NVMe] ({c_pct}%)", fill=c_white, font=f_small, anchor="la")
            draw.text((d_x1, dy0), f"{stats.get('disk_c_used', 765)}GB", fill=c_amber, font=f_val, anchor="ra")
            c_bar_y0 = dy0 + int(15*scale)
            c_bar_y1 = c_bar_y0 + int(7*scale)
            draw.rectangle([d_x0, c_bar_y0, d_x1, c_bar_y1], fill=(15, 23, 42), outline=(30, 41, 59))
            if c_pct > 0:
                draw.rectangle([d_x0, c_bar_y0, d_x0 + int((d_x1 - d_x0)*(c_pct/100.0)), c_bar_y1], fill=c_amber)

            # Disco E:
            e_pct = stats.get("disk_e_pct", 79)
            ey0 = c_bar_y1 + int(15*scale)
            draw.text((d_x0, ey0), f"E: [GAMES] ({e_pct}%)", fill=c_white, font=f_small, anchor="la")
            draw.text((d_x1, ey0), f"{stats.get('disk_e_used', 1470)}GB", fill=c_amber, font=f_val, anchor="ra")
            e_bar_y0 = ey0 + int(15*scale)
            e_bar_y1 = e_bar_y0 + int(7*scale)
            draw.rectangle([d_x0, e_bar_y0, d_x1, e_bar_y1], fill=(15, 23, 42), outline=(30, 41, 59))
            if e_pct > 0:
                draw.rectangle([d_x0, e_bar_y0, d_x0 + int((d_x1 - d_x0)*(e_pct/100.0)), e_bar_y1], fill=c_amber)

            # Sub-coluna Direita: Rede & I/O
            net_x0 = d_x1 + sub_gap
            net_x1 = c3_x1 - int(16*scale)
            lines_net = [
                ("DOWNLOAD:", f"▲ {stats.get('net_down_str', '24.6 MB/s')}"),
                ("UPLOAD:", f"▼ {stats.get('net_up_str', '3.8 MB/s')}"),
                ("DISCO LIDO:", stats.get("disk_read_str", "18.5 MB/s")),
                ("DISCO ESCRITO:", stats.get("disk_write_str", "3.2 MB/s")),
            ]
            ny = dy0
            n_step = max(16, int((c3_y1 - c3_y0 - 52*scale) / len(lines_net)))
            for lbl, v in lines_net:
                col_v = c_emerald if "▲" in v else (c_cyan if "▼" in v else c_white)
                draw.text((net_x0, ny), lbl, fill=c_slate, font=f_micro, anchor="la")
                draw.text((net_x1, ny), v, fill=col_v, font=f_val, anchor="ra")
                ny += n_step

        # Barra Inferior de Atalhos HUD
        bot_y0 = height - bot_h - int(4 * scale)
        bot_y1 = height - int(4 * scale)
        self._draw_hud_bracket_card(draw, int(8*scale), bot_y0, width - int(8*scale), bot_y1, scale, fill=(6, 12, 18), border=(0, 229, 255), bracket_len=6)

        mid_bot_y = (bot_y0 + bot_y1) // 2
        draw.text((int(20 * scale), mid_bot_y), "💡 ATALHOS: [F11] TELA CHEIA 2º ECRÃ   |   [T] ALTERNAR TRANSPARÊNCIA HUD   |   [ESC] RESTAURAR JANELA", fill="#94a3b8", font=f_micro, anchor="lm")
        draw.text((width - int(20 * scale), mid_bot_y), f"FPS: {stats.get('fps', 60)}  //  UPTIME: {stats.get('uptime', '2h 45m')}", fill=c_cyan, font=f_micro, anchor="rm")

        return img

    def _draw_fan_speed_bar(self, draw, x0, y0, w, h, percent, rpm, is_auto, title, primary_color, dark_color, scale):
        """Desenha uma barra neon cibernética sem colisões mesmo em larguras reduzidas."""
        self._draw_hud_bracket_card(draw, x0, y0, x0 + w, y0 + h, scale, fill=(10, 14, 22), border=primary_color, bracket_len=8)

        f_title = self._get_font("ui", 7.5, scale, bold=True)
        f_badge = self._get_font("mono", 6.8, scale, bold=True)
        f_val = self._get_font("mono", 10.0, scale, bold=True)
        f_rpm = self._get_font("ui", 7.5, scale, bold=False)
        f_ticks = self._get_font("mono", 6.0, scale, bold=False)

        pad_x = int(8 * scale)
        pad_y = int(5 * scale)

        # Linha 1: Título e Badge de Modo [AUTO / MANUAL] com teste de colisão
        mode_text = "[ AUTO ]" if is_auto else "[ MANUAL ]"
        mode_color = "#10b981" if is_auto else "#f59e0b"

        disp_title = title
        t_bbox = draw.textbbox((x0 + pad_x, y0 + pad_y), disp_title, font=f_title, anchor="lt")
        m_bbox = draw.textbbox((x0 + w - pad_x, y0 + pad_y), mode_text, font=f_badge, anchor="rt")
        if t_bbox[2] + int(8*scale) > m_bbox[0]:
            disp_title = title.split("(")[0].strip()
            t_bbox = draw.textbbox((x0 + pad_x, y0 + pad_y), disp_title, font=f_title, anchor="lt")
            if t_bbox[2] + int(6*scale) > m_bbox[0]:
                disp_title = "CPU FAN" if "CPU" in title else "GPU FAN"

        draw.text((x0 + pad_x, y0 + pad_y), disp_title, fill="#f8fafc", font=f_title, anchor="lt")
        draw.text((x0 + w - pad_x, y0 + pad_y), mode_text, fill=mode_color, font=f_badge, anchor="rt")

        # Linha 2: Valores (% e RPM)
        val_y = y0 + pad_y + int(12 * scale)
        draw.text((x0 + pad_x, val_y), f"{percent}%", fill=primary_color, font=f_val, anchor="lt")
        draw.text((x0 + w - pad_x, val_y + int(2 * scale)), f"{rpm} RPM", fill="#cbd5e1", font=f_rpm, anchor="rt")

        # Linha 3: Barra Segmentada de LEDs
        bar_y0 = val_y + int(14 * scale)
        bar_h = max(5, int(8 * scale))
        bar_w = w - (pad_x * 2)
        bar_x0 = x0 + pad_x

        num_segments = 20
        gap = max(1, int(1.5 * scale))
        seg_w = max(2.0, (bar_w - (num_segments - 1) * gap) / float(num_segments))

        norm_pct = max(0, min(100, percent))
        active_count = int(round(norm_pct / 100.0 * num_segments))

        for i in range(num_segments):
            sx0 = bar_x0 + int(i * (seg_w + gap))
            sx1 = sx0 + int(seg_w)
            if sx1 > bar_x0 + bar_w:
                break
            if i < active_count:
                if i >= num_segments - 3:
                    fill_c = "#ef4444" if primary_color != "#ff0055" else "#ffea00"
                elif i >= num_segments - 6:
                    fill_c = "#f59e0b"
                else:
                    fill_c = primary_color
            else:
                fill_c = dark_color
            draw.rectangle([sx0, bar_y0, sx1, bar_y0 + bar_h], fill=fill_c)

        # Linha 4: Graduação inferior (20%, 40%, 60%, 80%, 100%)
        ticks_y = bar_y0 + bar_h + int(2 * scale)
        for p_mark in [20, 40, 60, 80, 100]:
            tx = bar_x0 + int((p_mark / 100.0) * bar_w) - int(seg_w // 2)
            draw.text((tx, ticks_y), f"{p_mark}%", fill="#64748b", font=f_ticks, anchor="mt")

    def render_neon_dual_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Cyber Neon Dual (Azul & Vermelho)'.
        Layout widescreen cibernético split-tone:
        - Lado Esquerdo: Neon Cyan (#00e5ff) com CPU, RAM e Barra de Controlo de Ventoinha do CPU
        - Centro: Hub de Rede, Motherboard e Perfis de Ventoinhas
        - Lado Direito: Blazing Red (#ff0055) com GPU RTX 4070 Ti, Discos e Barra de Controlo de Ventoinha da Gráfica
        """
        scale = min(width / 568.888, height / 320.0)
        bg_file = os.path.join(self.assets_dir, "neon_dual_bg.jpg")
        if os.path.exists(bg_file):
            try:
                base = Image.open(bg_file).convert("RGB")
                if base.size != (width, height):
                    base = base.resize((width, height), Image.Resampling.LANCZOS)
                img = Image.blend(base, Image.new("RGB", (width, height), (7, 10, 16)), 0.35)
            except Exception:
                img = Image.new("RGB", (width, height), (7, 10, 16))
        else:
            img = Image.new("RGB", (width, height), (7, 10, 16))

        draw = ImageDraw.Draw(img)

        c_cyan = "#00e5ff"
        c_red = "#ff0055"
        c_slate = "#94a3b8"
        c_white = "#f8fafc"
        c_emerald = "#10b981"
        c_amber = "#f59e0b"

        # Fontes calibradas
        f_header = self._get_font("ui", 8.5, scale, bold=True)
        f_clock = self._get_font("mono", 9.5, scale, bold=True)
        f_title = self._get_font("ui", 7.5, scale, bold=True)
        f_val = self._get_font("mono", 8.5, scale, bold=True)
        f_small = self._get_font("ui", 7.0, scale, bold=False)
        f_micro = self._get_font("mono", 6.5, scale, bold=False)

        # 1. Barra Superior Cabeçalho
        top_h = int(22 * min(1.3, scale))
        self._draw_hud_bracket_card(draw, int(6*scale), int(4*scale), width - int(6*scale), top_h + int(4*scale), scale, fill=(8, 12, 18), border=(0, 229, 255), bracket_len=8)
        dot_cy = (int(4*scale) + top_h + int(4*scale)) // 2

        # Lado Esquerdo Header
        left_title = "MONSTER TELEMETRIA // DUAL NEON" if width >= 600 else "MONSTER // NEON"
        draw.ellipse([int(12*scale), dot_cy - int(2.5*scale), int(17*scale), dot_cy + int(2.5*scale)], fill=c_cyan)
        draw.text((int(22*scale), dot_cy), left_title, fill=c_white, font=f_header, anchor="lm")
        t_left_bbox = draw.textbbox((int(22*scale), dot_cy), left_title, font=f_header, anchor="lm")

        # Lado Direito Header
        right_info = f"RTX 4070 Ti // {stats.get('cpu_cores', '14C/20T')}" if width >= 700 else stats.get("gpu_name", "RTX 4070 Ti")
        draw.ellipse([width - int(17*scale), dot_cy - int(2.5*scale), width - int(12*scale), dot_cy + int(2.5*scale)], fill=c_red)
        draw.text((width - int(22*scale), dot_cy), right_info, fill="#ff99bb", font=f_header, anchor="rm")
        t_right_bbox = draw.textbbox((width - int(22*scale), dot_cy), right_info, font=f_header, anchor="rm")

        # Centro Header: Relógio com deteção dinâmica de espaço livre (ZERO colisão)
        clock_str = stats.get("time", "12:00:00")
        uptime_str = f"UPTIME {stats.get('uptime', '2h 15m')}"
        center_text = f"{clock_str}   //   {uptime_str}" if width >= 800 else clock_str
        c_bbox = draw.textbbox((width // 2, dot_cy), center_text, font=f_clock, anchor="mm")

        if t_left_bbox[2] + int(20*scale) < c_bbox[0] and c_bbox[2] + int(20*scale) < t_right_bbox[0]:
            draw.text((width // 2, dot_cy), center_text, fill=c_cyan, font=f_clock, anchor="mm")
        else:
            c_short_bbox = draw.textbbox((width // 2, dot_cy), clock_str, font=f_clock, anchor="mm")
            if t_left_bbox[2] + int(8*scale) < c_short_bbox[0] and c_short_bbox[2] + int(8*scale) < t_right_bbox[0]:
                draw.text((width // 2, dot_cy), clock_str, fill=c_cyan, font=f_clock, anchor="mm")

        # 2. Dimensões das 3 Colunas: Esquerda (CPU - Azul), Centro (Hub), Direita (GPU - Vermelho)
        content_y0 = top_h + int(8 * scale)
        bot_h = int(18 * min(1.2, scale))
        content_y1 = height - bot_h - int(6 * scale)
        avail_h = content_y1 - content_y0

        col_gap = int(8 * scale)
        margin_x = int(6 * scale)
        col_w = (width - (margin_x * 2) - (col_gap * 2)) // 3

        left_x0 = margin_x
        left_x1 = left_x0 + col_w

        mid_x0 = left_x1 + col_gap
        mid_x1 = mid_x0 + col_w

        right_x0 = mid_x1 + col_gap
        right_x1 = width - margin_x

        # ==================== COLUNA ESQUERDA: CPU & RAM (NEON AZUL) ====================
        cpu_card_h = int(avail_h * 0.44)
        self._draw_hud_bracket_card(draw, left_x0, content_y0, left_x1, content_y0 + cpu_card_h, scale, fill=(8, 14, 22), border=(0, 229, 255), bracket_len=12)

        # Mostrador Circular CPU
        gauge_r = min(32, int(cpu_card_h * 0.28))
        gauge_cx = left_x0 + int(col_w * 0.30)
        gauge_cy = content_y0 + int(cpu_card_h * 0.52)
        c_temp_cpu = c_cyan if stats["cpu_temp"] < 60 else (c_amber if stats["cpu_temp"] < 75 else c_red)
        self._draw_circular_hud_meter(draw, gauge_cx, gauge_cy, gauge_r, stats["cpu_usage"], scale, label="CPU LOAD", val_str=f"{stats['cpu_usage']}%", temp_str=f"{stats['cpu_temp']}°C", primary_color=c_cyan, temp_color=c_temp_cpu)

        # Detalhes textuais CPU
        det_x = left_x0 + int(col_w * 0.58)
        det_y = content_y0 + int(12 * scale)
        draw.text((det_x, det_y), "INTEL CORE", fill=c_cyan, font=f_title, anchor="la")
        det_y += int(14 * scale)
        draw.text((det_x, det_y), f"CLOCK: {stats.get('cpu_ghz', 3.5)} GHz", fill=c_white, font=f_small, anchor="la")
        det_y += int(12 * scale)
        draw.text((det_x, det_y), f"POWER: {stats.get('cpu_power', 45)} W", fill=c_slate, font=f_small, anchor="la")
        det_y += int(12 * scale)
        draw.text((det_x, det_y), f"CORES: {stats.get('cpu_cores', '14C / 20T')}", fill=c_slate, font=f_small, anchor="la")

        # BARRA DE VELOCIDADE DA VENTOINHA DO CPU
        cpu_fan_y0 = content_y0 + cpu_card_h + int(5 * scale)
        cpu_fan_h = int(avail_h * 0.26)
        cpu_fan_pct = stats.get("cpu_fan_pct", 60)
        cpu_fan_rpm = stats.get("cpu_fan", 1750)
        cpu_fan_auto = stats.get("cpu_fan_auto", True)
        self._draw_fan_speed_bar(draw, left_x0, cpu_fan_y0, col_w, cpu_fan_h, cpu_fan_pct, cpu_fan_rpm, cpu_fan_auto, title="⚡ CPU FAN SPEED", primary_color=c_cyan, dark_color=(8, 30, 45), scale=scale)

        # CARTÃO RAM MEMÓRIA
        ram_y0 = cpu_fan_y0 + cpu_fan_h + int(5 * scale)
        self._draw_hud_bracket_card(draw, left_x0, ram_y0, left_x1, content_y1, scale, fill=(8, 14, 22), border=(0, 229, 255), bracket_len=8)

        draw.text((left_x0 + int(8*scale), ram_y0 + int(5*scale)), "MEMÓRIA RAM DDR5", fill=c_cyan, font=f_title, anchor="lt")
        draw.text((left_x1 - int(8*scale), ram_y0 + int(5*scale)), f"{stats['ram_usage']}%", fill=c_white, font=f_val, anchor="rt")

        ram_bar_y = ram_y0 + int(20 * scale)
        ram_bar_h = max(4, int(6 * scale))
        ram_bar_w = col_w - int(16 * scale)
        draw.rectangle([left_x0 + int(8*scale), ram_bar_y, left_x0 + int(8*scale) + ram_bar_w, ram_bar_y + ram_bar_h], fill=(12, 24, 34))
        ram_fill_w = int(ram_bar_w * (stats["ram_usage"] / 100.0))
        if ram_fill_w > 0:
            draw.rectangle([left_x0 + int(8*scale), ram_bar_y, left_x0 + int(8*scale) + ram_fill_w, ram_bar_y + ram_bar_h], fill=c_cyan)

        draw.text((left_x0 + int(8*scale), ram_bar_y + ram_bar_h + int(3*scale)), f"USADO: {stats['ram_used_gb']} GB", fill=c_slate, font=f_micro, anchor="lt")
        draw.text((left_x1 - int(8*scale), ram_bar_y + ram_bar_h + int(3*scale)), f"TOTAL: {stats['ram_total_gb']} GB", fill=c_slate, font=f_micro, anchor="rt")


        # ==================== COLUNA CENTRAL: TELEMETRIA GERAL & REDE ====================
        self._draw_hud_bracket_card(draw, mid_x0, content_y0, mid_x1, content_y1, scale, fill=(10, 14, 20), border=(70, 90, 120), bracket_len=10)

        # Cabeçalho Central
        m_pad = int(8 * scale)
        m_cy = content_y0 + int(10 * scale)
        center_hub_title = "CENTRO DE CONTROLO" if col_w < 320 else "CENTRO DE CONTROLO TARRASGA"
        draw.text((mid_x0 + col_w // 2, m_cy), center_hub_title, fill="#38bdf8", font=f_header, anchor="mt")

        # Status dos Perfis de Ventoinhas
        prof_y0 = m_cy + int(16 * scale)
        draw.text((mid_x0 + col_w // 2, prof_y0), "PERFIL ATIVO DE ARREFECIMENTO:", fill=c_slate, font=f_micro, anchor="mt")

        prof_y1 = prof_y0 + int(12 * scale)
        profiles = ["AUTO", "SILÊNCIO", "EQUILÍBRIO", "GAMING", "TURBO"] if col_w >= 300 else ["AUTO", "SIL", "EQU", "GAME", "MAX"]
        avg_fan = (cpu_fan_pct + stats.get("gpu_fan_pct", 50)) // 2
        if cpu_fan_auto and stats.get("gpu_fan_auto", True):
            cur_prof = profiles[0]
        elif avg_fan <= 40:
            cur_prof = profiles[1]
        elif avg_fan <= 60:
            cur_prof = profiles[2]
        elif avg_fan <= 85:
            cur_prof = profiles[3]
        else:
            cur_prof = profiles[4]

        p_w = max(10, (col_w - (m_pad * 2) - (len(profiles) - 1) * int(3*scale)) // len(profiles))
        for idx, p_name in enumerate(profiles):
            px0 = mid_x0 + m_pad + idx * (p_w + int(3*scale))
            px1 = px0 + p_w
            py0 = prof_y1
            py1 = py0 + int(14 * scale)
            is_cur = (p_name == cur_prof)
            bg_col = (0, 229, 255) if (is_cur and idx < 2) else ((255, 0, 85) if (is_cur and idx >= 3) else ((16, 185, 129) if is_cur else (18, 26, 36)))
            fg_col = "#07090e" if is_cur else "#64748b"
            draw.rectangle([px0, py0, px1, py1], fill=bg_col)
            draw.text(((px0 + px1) // 2, (py0 + py1) // 2), p_name, fill=fg_col, font=self._get_font("ui", 6.0, scale, bold=True), anchor="mm")

        # Módulo de Rede
        net_y0 = prof_y1 + int(24 * scale)
        self._draw_hud_bracket_card(draw, mid_x0 + m_pad, net_y0, mid_x1 - m_pad, net_y0 + int(avail_h * 0.28), scale, fill=(12, 18, 26), border=(56, 189, 248), bracket_len=6)
        draw.text((mid_x0 + m_pad + int(6*scale), net_y0 + int(5*scale)), "TRÁFEGO DE REDE WI-FI / LAN", fill="#38bdf8", font=f_title, anchor="lt")

        down_y = net_y0 + int(20 * scale)
        draw.text((mid_x0 + m_pad + int(6*scale), down_y), "▼ DOWNLOAD:", fill=c_slate, font=f_small, anchor="lt")
        draw.text((mid_x1 - m_pad - int(6*scale), down_y), stats.get("net_down_str", "0 KB/s"), fill=c_emerald, font=f_val, anchor="rt")

        up_y = down_y + int(14 * scale)
        draw.text((mid_x0 + m_pad + int(6*scale), up_y), "▲ UPLOAD:", fill=c_slate, font=f_small, anchor="lt")
        draw.text((mid_x1 - m_pad - int(6*scale), up_y), stats.get("net_up_str", "0 KB/s"), fill="#38bdf8", font=f_val, anchor="rt")

        # Módulo Placa-Mãe
        sys_y0 = net_y0 + int(avail_h * 0.28) + int(6 * scale)
        self._draw_hud_bracket_card(draw, mid_x0 + m_pad, sys_y0, mid_x1 - m_pad, content_y1 - int(6*scale), scale, fill=(12, 18, 26), border=(100, 116, 139), bracket_len=6)
        draw.text((mid_x0 + m_pad + int(6*scale), sys_y0 + int(5*scale)), "SENSORES DA MOTHERBOARD", fill="#cbd5e1", font=f_title, anchor="lt")

        s1_y = sys_y0 + int(20 * scale)
        draw.text((mid_x0 + m_pad + int(6*scale), s1_y), "TEMP SISTEMA:", fill=c_slate, font=f_small, anchor="lt")
        draw.text((mid_x1 - m_pad - int(6*scale), s1_y), f"{stats.get('sys_temp', 32)}°C", fill=c_emerald, font=f_val, anchor="rt")

        s2_y = s1_y + int(14 * scale)
        draw.text((mid_x0 + m_pad + int(6*scale), s2_y), "CHASSIS FAN #1:", fill=c_slate, font=f_small, anchor="lt")
        draw.text((mid_x1 - m_pad - int(6*scale), s2_y), f"{stats.get('chassis_fan', 1150)} RPM", fill=c_white, font=f_val, anchor="rt")


        # ==================== COLUNA DIREITA: GPU & DISCOS (NEON VERMELHO) ====================
        self._draw_hud_bracket_card(draw, right_x0, content_y0, right_x1, content_y0 + cpu_card_h, scale, fill=(22, 10, 14), border=(255, 0, 85), bracket_len=12)

        # Mostrador Circular GPU
        gauge_gpu_cx = right_x0 + int(col_w * 0.30)
        gauge_gpu_cy = content_y0 + int(cpu_card_h * 0.52)
        c_temp_gpu = c_emerald if stats["gpu_temp"] < 55 else (c_amber if stats["gpu_temp"] < 75 else c_red)
        self._draw_circular_hud_meter(draw, gauge_gpu_cx, gauge_gpu_cy, gauge_r, stats["gpu_usage"], scale, label="GPU LOAD", val_str=f"{stats['gpu_usage']}%", temp_str=f"{stats['gpu_temp']}°C", primary_color=c_red, temp_color=c_temp_gpu)

        # Detalhes textuais GPU
        gpu_det_x = right_x0 + int(col_w * 0.58)
        gpu_det_y = content_y0 + int(12 * scale)
        draw.text((gpu_det_x, gpu_det_y), stats.get("gpu_name", "RTX 4070 Ti"), fill=c_red, font=f_title, anchor="la")
        gpu_det_y += int(14 * scale)
        draw.text((gpu_det_x, gpu_det_y), f"CLOCK: {stats.get('gpu_clock', 2640)} MHz", fill=c_white, font=f_small, anchor="la")
        gpu_det_y += int(12 * scale)
        draw.text((gpu_det_x, gpu_det_y), f"POWER: {stats.get('gpu_power', 28.5)} W", fill=c_slate, font=f_small, anchor="la")
        gpu_det_y += int(12 * scale)
        draw.text((gpu_det_x, gpu_det_y), f"VRAM: {stats.get('gpu_vram_used', 2.1)}/{stats.get('gpu_vram_total', 12.0)} GB", fill=c_slate, font=f_small, anchor="la")

        # BARRA DE VELOCIDADE DA VENTOINHA DA GRÁFICA / GPU
        gpu_fan_y0 = content_y0 + cpu_card_h + int(5 * scale)
        gpu_fan_pct = stats.get("gpu_fan_pct", 50)
        gpu_fan_rpm = stats.get("gpu_fan_rpm", 1450)
        gpu_fan_auto = stats.get("gpu_fan_auto", True)
        self._draw_fan_speed_bar(draw, right_x0, gpu_fan_y0, col_w, cpu_fan_h, gpu_fan_pct, gpu_fan_rpm, gpu_fan_auto, title="⚡ GPU FAN SPEED", primary_color=c_red, dark_color=(45, 10, 18), scale=scale)

        # CARTÃO ARMAZENAMENTO / DISCOS
        self._draw_hud_bracket_card(draw, right_x0, ram_y0, right_x1, content_y1, scale, fill=(22, 10, 14), border=(255, 0, 85), bracket_len=8)

        disp_disk_title = "ARMAZENAMENTO" if col_w < 300 else "ARMAZENAMENTO (C: & E:)"
        draw.text((right_x0 + int(8*scale), ram_y0 + int(5*scale)), disp_disk_title, fill=c_red, font=f_title, anchor="lt")
        draw.text((right_x1 - int(8*scale), ram_y0 + int(5*scale)), f"C: {stats['disk_c_pct']}%  E: {stats['disk_e_pct']}%", fill=c_white, font=f_val, anchor="rt")

        disk_bar_y = ram_y0 + int(20 * scale)
        draw.rectangle([right_x0 + int(8*scale), disk_bar_y, right_x0 + int(8*scale) + ram_bar_w, disk_bar_y + ram_bar_h], fill=(32, 14, 18))
        disk_fill_w = int(ram_bar_w * (stats["disk_c_pct"] / 100.0))
        if disk_fill_w > 0:
            draw.rectangle([right_x0 + int(8*scale), disk_bar_y, right_x0 + int(8*scale) + disk_fill_w, disk_bar_y + ram_bar_h], fill=c_red)

        draw.text((right_x0 + int(8*scale), disk_bar_y + ram_bar_h + int(3*scale)), f"I/O R: {stats.get('disk_read_str', '0 KB/s')}", fill=c_slate, font=f_micro, anchor="lt")
        draw.text((right_x1 - int(8*scale), disk_bar_y + ram_bar_h + int(3*scale)), f"I/O W: {stats.get('disk_write_str', '0 KB/s')}", fill=c_slate, font=f_micro, anchor="rt")

        # ==================== BARRA INFERIOR / RODAPÉ ====================
        bot_y0 = height - bot_h - int(4 * scale)
        bot_y1 = height - int(4 * scale)
        self._draw_hud_bracket_card(draw, int(6*scale), bot_y0, width - int(6*scale), bot_y1, scale, fill=(8, 12, 18), border=(70, 90, 120), bracket_len=6)

        mid_bot_y = (bot_y0 + bot_y1) // 2
        footer_left = "⚡ CONTROLO TOTAL: BARRAS CPU & GPU  |  [F11] TELA CHEIA  |  [T] OVERLAY" if width >= 700 else "[F11] TELA CHEIA"
        draw.text((int(16 * scale), mid_bot_y), footer_left, fill=c_slate, font=f_micro, anchor="lm")
        draw.text((width - int(16 * scale), mid_bot_y), "MONSTER TELEMETRIA // DUAL NEON", fill=c_cyan, font=f_micro, anchor="rm")

        return img

    def render_monster_official_view(self, stats, width=1280, height=720):
        """Renderiza o tema 'Monster Telemetria (Logo Oficial)'.
        Layout widescreen topo-de-gama com o Logótipo Oficial Monster Telemetria ao centro:
        - Lado Esquerdo: Toxic Neon Green (#39ff14) com CPU Load, Clock, Temperatura e Barra de Ventoinha do CPU
        - Centro: Emblema Oficial Monster Telemetria, Perfis de Arrefecimento e Sensores Motherboard/Rede
        - Lado Direito: Cyber Cyan (#00e5ff) com GPU RTX 4070 Ti, VRAM, Temperatura e Barra de Ventoinha da Gráfica
        """
        scale = min(width / 568.888, height / 320.0)
        bg_file = os.path.join(self.assets_dir, "monster_telemetria_bg.jpg")
        if os.path.exists(bg_file):
            try:
                base = Image.open(bg_file).convert("RGB")
                if base.size != (width, height):
                    base = base.resize((width, height), Image.Resampling.LANCZOS)
                img = Image.blend(base, Image.new("RGB", (width, height), (5, 9, 7)), 0.30)
            except Exception:
                img = Image.new("RGB", (width, height), (5, 9, 7))
        else:
            img = Image.new("RGB", (width, height), (5, 9, 7))

        draw = ImageDraw.Draw(img)

        c_green = "#39ff14"
        c_cyan = "#00e5ff"
        c_slate = "#94a3b8"
        c_white = "#f8fafc"
        c_amber = "#f59e0b"
        c_red = "#ff0055"

        f_header = self._get_font("ui", 8.5, scale, bold=True)
        f_clock = self._get_font("mono", 9.5, scale, bold=True)
        f_title = self._get_font("ui", 7.5, scale, bold=True)
        f_val = self._get_font("mono", 8.5, scale, bold=True)
        f_small = self._get_font("ui", 7.0, scale, bold=False)
        f_micro = self._get_font("mono", 6.5, scale, bold=False)

        # 1. Barra Superior Cabeçalho
        top_h = int(22 * min(1.3, scale))
        self._draw_hud_bracket_card(draw, int(6*scale), int(4*scale), width - int(6*scale), top_h + int(4*scale), scale, fill=(6, 14, 9), border=c_green, bracket_len=8)
        dot_cy = (int(4*scale) + top_h + int(4*scale)) // 2

        # Lado Esquerdo Header
        left_title = "MONSTER TELEMETRIA // EDIÇÃO OFICIAL" if width >= 650 else "MONSTER TELEMETRIA"
        draw.ellipse([int(12*scale), dot_cy - int(2.5*scale), int(17*scale), dot_cy + int(2.5*scale)], fill=c_green)
        draw.text((int(22*scale), dot_cy), left_title, fill=c_white, font=f_header, anchor="lm")
        t_left_bbox = draw.textbbox((int(22*scale), dot_cy), left_title, font=f_header, anchor="lm")

        # Lado Direito Header
        right_info = f"RTX 4070 Ti // {stats.get('cpu_cores', '14C/20T')}" if width >= 700 else stats.get("gpu_name", "RTX 4070 Ti")
        draw.ellipse([width - int(17*scale), dot_cy - int(2.5*scale), width - int(12*scale), dot_cy + int(2.5*scale)], fill=c_cyan)
        draw.text((width - int(22*scale), dot_cy), right_info, fill="#a5f3fc", font=f_header, anchor="rm")
        t_right_bbox = draw.textbbox((width - int(22*scale), dot_cy), right_info, font=f_header, anchor="rm")

        # Centro Header: Relógio com deteção dinâmica de espaço livre
        clock_str = stats.get("time", "12:00:00")
        uptime_str = f"UPTIME {stats.get('uptime', '2h 15m')}"
        center_text = f"{clock_str}   //   {uptime_str}" if width >= 800 else clock_str
        c_bbox = draw.textbbox((width // 2, dot_cy), center_text, font=f_clock, anchor="mm")

        if t_left_bbox[2] + int(20*scale) < c_bbox[0] and c_bbox[2] + int(20*scale) < t_right_bbox[0]:
            draw.text((width // 2, dot_cy), center_text, fill=c_green, font=f_clock, anchor="mm")
        else:
            c_short_bbox = draw.textbbox((width // 2, dot_cy), clock_str, font=f_clock, anchor="mm")
            if t_left_bbox[2] + int(8*scale) < c_short_bbox[0] and c_short_bbox[2] + int(8*scale) < t_right_bbox[0]:
                draw.text((width // 2, dot_cy), clock_str, fill=c_green, font=f_clock, anchor="mm")

        # 2. Dimensões das 3 Colunas: Esquerda (CPU - Verde), Centro (Logo & Hub), Direita (GPU - Cyan)
        content_y0 = top_h + int(8 * scale)
        bot_h = int(18 * min(1.2, scale))
        content_y1 = height - bot_h - int(6 * scale)
        avail_h = content_y1 - content_y0

        col_gap = int(8 * scale)
        margin_x = int(6 * scale)
        col_w = (width - (margin_x * 2) - (col_gap * 2)) // 3

        left_x0 = margin_x
        left_x1 = left_x0 + col_w

        mid_x0 = left_x1 + col_gap
        mid_x1 = mid_x0 + col_w

        right_x0 = mid_x1 + col_gap
        right_x1 = width - margin_x

        # ==================== COLUNA ESQUERDA: CPU & RAM (TOXIC GREEN) ====================
        cpu_card_h = int(avail_h * 0.44)
        self._draw_hud_bracket_card(draw, left_x0, content_y0, left_x1, content_y0 + cpu_card_h, scale, fill=(8, 16, 10), border=c_green, bracket_len=12)

        gauge_r = min(32, int(cpu_card_h * 0.28))
        gauge_cx = left_x0 + int(col_w * 0.30)
        gauge_cy = content_y0 + int(cpu_card_h * 0.52)
        c_temp_cpu = c_green if stats["cpu_temp"] < 60 else (c_amber if stats["cpu_temp"] < 75 else c_red)
        self._draw_circular_hud_meter(draw, gauge_cx, gauge_cy, gauge_r, stats["cpu_usage"], scale, label="CPU LOAD", val_str=f"{stats['cpu_usage']}%", temp_str=f"{stats['cpu_temp']}°C", primary_color=c_green, temp_color=c_temp_cpu)

        det_x = left_x0 + int(col_w * 0.58)
        det_y = content_y0 + int(12 * scale)
        draw.text((det_x, det_y), "INTEL CORE", fill=c_green, font=f_title, anchor="la")
        det_y += int(14 * scale)
        draw.text((det_x, det_y), f"CLOCK: {stats.get('cpu_ghz', 3.5)} GHz", fill=c_white, font=f_small, anchor="la")
        det_y += int(12 * scale)
        draw.text((det_x, det_y), f"POWER: {stats.get('cpu_power', 45)} W", fill=c_slate, font=f_small, anchor="la")
        det_y += int(12 * scale)
        draw.text((det_x, det_y), f"CORES: {stats.get('cpu_cores', '14C / 20T')}", fill=c_slate, font=f_small, anchor="la")

        # BARRA VENTOINHA DO CPU (VERDE MONSTER)
        cpu_fan_y0 = content_y0 + cpu_card_h + int(5 * scale)
        cpu_fan_h = int(avail_h * 0.26)
        cpu_fan_pct = stats.get("cpu_fan_pct", 60)
        cpu_fan_rpm = stats.get("cpu_fan", 1750)
        cpu_fan_auto = stats.get("cpu_fan_auto", True)
        self._draw_fan_speed_bar(draw, left_x0, cpu_fan_y0, col_w, cpu_fan_h, cpu_fan_pct, cpu_fan_rpm, cpu_fan_auto, title="⚡ CPU FAN SPEED", primary_color=c_green, dark_color=(8, 28, 14), scale=scale)

        # CARTÃO RAM
        ram_y0 = cpu_fan_y0 + cpu_fan_h + int(5 * scale)
        self._draw_hud_bracket_card(draw, left_x0, ram_y0, left_x1, content_y1, scale, fill=(8, 16, 10), border=c_green, bracket_len=8)

        draw.text((left_x0 + int(8*scale), ram_y0 + int(5*scale)), "MEMÓRIA RAM DDR5", fill=c_green, font=f_title, anchor="lt")
        draw.text((left_x1 - int(8*scale), ram_y0 + int(5*scale)), f"{stats['ram_usage']}%", fill=c_white, font=f_val, anchor="rt")

        ram_bar_y = ram_y0 + int(20 * scale)
        ram_bar_h = max(4, int(6 * scale))
        ram_bar_w = col_w - int(16 * scale)
        draw.rectangle([left_x0 + int(8*scale), ram_bar_y, left_x0 + int(8*scale) + ram_bar_w, ram_bar_y + ram_bar_h], fill=(10, 24, 14))
        ram_fill_w = int(ram_bar_w * (stats["ram_usage"] / 100.0))
        if ram_fill_w > 0:
            draw.rectangle([left_x0 + int(8*scale), ram_bar_y, left_x0 + int(8*scale) + ram_fill_w, ram_bar_y + ram_bar_h], fill=c_green)

        draw.text((left_x0 + int(8*scale), ram_bar_y + ram_bar_h + int(3*scale)), f"USADO: {stats['ram_used_gb']} GB", fill=c_slate, font=f_micro, anchor="lt")
        draw.text((left_x1 - int(8*scale), ram_bar_y + ram_bar_h + int(3*scale)), f"TOTAL: {stats['ram_total_gb']} GB", fill=c_slate, font=f_micro, anchor="rt")

        # ==================== COLUNA CENTRAL: LOGÓTIPO OFICIAL & HUB TELEMETRIA ====================
        # Cartão Superior Central: LOGÓTIPO OFICIAL MONSTER TELEMETRIA
        logo_card_h = int(avail_h * 0.44)
        self._draw_hud_bracket_card(draw, mid_x0, content_y0, mid_x1, content_y0 + logo_card_h, scale, fill=(7, 14, 10), border=c_green, bracket_len=12)

        if self.monster_official_logo:
            try:
                max_logo_dim = min(col_w - int(24 * scale), logo_card_h - int(34 * scale))
                if max_logo_dim > 16:
                    logo_resized = self.monster_official_logo.resize((max_logo_dim, max_logo_dim), Image.Resampling.LANCZOS)
                    logo_x = mid_x0 + (col_w - max_logo_dim) // 2
                    logo_y = content_y0 + int(6 * scale)
                    img.paste(logo_resized, (logo_x, logo_y), logo_resized)
                    
                    sub_y = logo_y + max_logo_dim + int(3 * scale)
                    badge_str = "MONSTER TELEMETRIA" if col_w < 260 else "★ MONSTER TELEMETRIA OFFICIAL ★"
                    draw.text((mid_x0 + col_w // 2, sub_y), badge_str, fill=c_green, font=f_title, anchor="mt")
            except Exception:
                draw.text((mid_x0 + col_w // 2, content_y0 + logo_card_h // 2), "MONSTER TELEMETRIA", fill=c_green, font=f_header, anchor="mm")
        else:
            draw.text((mid_x0 + col_w // 2, content_y0 + logo_card_h // 2), "MONSTER TELEMETRIA", fill=c_green, font=f_header, anchor="mm")

        # Módulo Perfis de Ventoinhas
        m_pad = int(8 * scale)
        prof_card_y0 = content_y0 + logo_card_h + int(5 * scale)
        prof_card_h = int(avail_h * 0.26)
        self._draw_hud_bracket_card(draw, mid_x0, prof_card_y0, mid_x1, prof_card_y0 + prof_card_h, scale, fill=(8, 14, 12), border=(40, 160, 90), bracket_len=8)

        draw.text((mid_x0 + col_w // 2, prof_card_y0 + int(4*scale)), "PERFIL DE ARREFECIMENTO", fill="#6ee7b7", font=f_title, anchor="mt")

        profiles = ["AUTO", "SILÊNCIO", "EQUILÍBRIO", "GAMING", "TURBO"] if col_w >= 280 else ["AUTO", "SIL", "EQU", "GAME", "MAX"]
        avg_fan = (cpu_fan_pct + stats.get("gpu_fan_pct", 50)) // 2
        if cpu_fan_auto and stats.get("gpu_fan_auto", True):
            cur_prof = profiles[0]
        elif avg_fan <= 40:
            cur_prof = profiles[1]
        elif avg_fan <= 60:
            cur_prof = profiles[2]
        elif avg_fan <= 85:
            cur_prof = profiles[3]
        else:
            cur_prof = profiles[4]

        prof_y1 = prof_card_y0 + int(18 * scale)
        p_w = max(10, (col_w - (m_pad * 2) - (len(profiles) - 1) * int(3*scale)) // len(profiles))
        for idx, p_name in enumerate(profiles):
            px0 = mid_x0 + m_pad + idx * (p_w + int(3*scale))
            px1 = px0 + p_w
            py0 = prof_y1
            py1 = py0 + int(14 * scale)
            is_cur = (p_name == cur_prof)
            bg_col = (57, 255, 20) if is_cur else (16, 26, 20)
            fg_col = "#040d06" if is_cur else "#64748b"
            draw.rectangle([px0, py0, px1, py1], fill=bg_col)
            draw.text(((px0 + px1) // 2, (py0 + py1) // 2), p_name, fill=fg_col, font=self._get_font("ui", 6.0, scale, bold=True), anchor="mm")

        stat_hub_y = prof_y1 + int(18 * scale)
        draw.text((mid_x0 + m_pad, stat_hub_y), "TEMP MOTHERBOARD:", fill=c_slate, font=f_micro, anchor="lt")
        draw.text((mid_x1 - m_pad, stat_hub_y), f"{stats.get('sys_temp', 32)}°C", fill=c_green, font=f_micro, anchor="rt")

        # Módulo Rede e Motherboard (Inferior Central)
        net_y0 = prof_card_y0 + prof_card_h + int(5 * scale)
        self._draw_hud_bracket_card(draw, mid_x0, net_y0, mid_x1, content_y1, scale, fill=(8, 14, 12), border=c_cyan, bracket_len=8)

        draw.text((mid_x0 + int(8*scale), net_y0 + int(4*scale)), "REDE & COMUNICAÇÃO", fill=c_cyan, font=f_title, anchor="lt")
        draw.text((mid_x1 - int(8*scale), net_y0 + int(4*scale)), "STATUS: ATIVO", fill=c_green, font=f_micro, anchor="rt")

        down_y = net_y0 + int(18 * scale)
        draw.text((mid_x0 + int(8*scale), down_y), "▼ DOWNLOAD:", fill=c_slate, font=f_small, anchor="lt")
        draw.text((mid_x1 - int(8*scale), down_y), stats.get("net_down_str", "0 KB/s"), fill=c_green, font=f_val, anchor="rt")

        up_y = down_y + int(13 * scale)
        draw.text((mid_x0 + int(8*scale), up_y), "▲ UPLOAD:", fill=c_slate, font=f_small, anchor="lt")
        draw.text((mid_x1 - int(8*scale), up_y), stats.get("net_up_str", "0 KB/s"), fill=c_cyan, font=f_val, anchor="rt")

        # ==================== COLUNA DIREITA: GPU & DISCOS (CYBER CYAN) ====================
        self._draw_hud_bracket_card(draw, right_x0, content_y0, right_x1, content_y0 + cpu_card_h, scale, fill=(8, 14, 18), border=c_cyan, bracket_len=12)

        gauge_gpu_cx = right_x0 + int(col_w * 0.30)
        gauge_gpu_cy = content_y0 + int(cpu_card_h * 0.52)
        c_temp_gpu = c_green if stats["gpu_temp"] < 55 else (c_amber if stats["gpu_temp"] < 75 else c_red)
        self._draw_circular_hud_meter(draw, gauge_gpu_cx, gauge_gpu_cy, gauge_r, stats["gpu_usage"], scale, label="GPU LOAD", val_str=f"{stats['gpu_usage']}%", temp_str=f"{stats['gpu_temp']}°C", primary_color=c_cyan, temp_color=c_temp_gpu)

        gpu_det_x = right_x0 + int(col_w * 0.58)
        gpu_det_y = content_y0 + int(12 * scale)
        draw.text((gpu_det_x, gpu_det_y), stats.get("gpu_name", "RTX 4070 Ti"), fill=c_cyan, font=f_title, anchor="la")
        gpu_det_y += int(14 * scale)
        draw.text((gpu_det_x, gpu_det_y), f"CLOCK: {stats.get('gpu_clock', 2640)} MHz", fill=c_white, font=f_small, anchor="la")
        gpu_det_y += int(12 * scale)
        draw.text((gpu_det_x, gpu_det_y), f"POWER: {stats.get('gpu_power', 28.5)} W", fill=c_slate, font=f_small, anchor="la")
        gpu_det_y += int(12 * scale)
        draw.text((gpu_det_x, gpu_det_y), f"VRAM: {stats.get('gpu_vram_used', 2.1)}/{stats.get('gpu_vram_total', 12.0)} GB", fill=c_slate, font=f_small, anchor="la")

        # BARRA VENTOINHA DA GRÁFICA / GPU (CYBER CYAN)
        gpu_fan_y0 = content_y0 + cpu_card_h + int(5 * scale)
        gpu_fan_pct = stats.get("gpu_fan_pct", 50)
        gpu_fan_rpm = stats.get("gpu_fan_rpm", 1450)
        gpu_fan_auto = stats.get("gpu_fan_auto", True)
        self._draw_fan_speed_bar(draw, right_x0, gpu_fan_y0, col_w, cpu_fan_h, gpu_fan_pct, gpu_fan_rpm, gpu_fan_auto, title="⚡ GPU FAN SPEED", primary_color=c_cyan, dark_color=(8, 24, 32), scale=scale)

        # CARTÃO ARMAZENAMENTO / DISCOS
        self._draw_hud_bracket_card(draw, right_x0, ram_y0, right_x1, content_y1, scale, fill=(8, 14, 18), border=c_cyan, bracket_len=8)

        disp_disk_title = "ARMAZENAMENTO" if col_w < 300 else "ARMAZENAMENTO (C: & E:)"
        draw.text((right_x0 + int(8*scale), ram_y0 + int(5*scale)), disp_disk_title, fill=c_cyan, font=f_title, anchor="lt")
        draw.text((right_x1 - int(8*scale), ram_y0 + int(5*scale)), f"C: {stats['disk_c_pct']}%  E: {stats['disk_e_pct']}%", fill=c_white, font=f_val, anchor="rt")

        disk_bar_y = ram_y0 + int(20 * scale)
        draw.rectangle([right_x0 + int(8*scale), disk_bar_y, right_x0 + int(8*scale) + ram_bar_w, disk_bar_y + ram_bar_h], fill=(12, 24, 30))
        disk_fill_w = int(ram_bar_w * (stats["disk_c_pct"] / 100.0))
        if disk_fill_w > 0:
            draw.rectangle([right_x0 + int(8*scale), disk_bar_y, right_x0 + int(8*scale) + disk_fill_w, disk_bar_y + ram_bar_h], fill=c_cyan)

        draw.text((right_x0 + int(8*scale), disk_bar_y + ram_bar_h + int(3*scale)), f"I/O R: {stats.get('disk_read_str', '0 KB/s')}", fill=c_slate, font=f_micro, anchor="lt")
        draw.text((right_x1 - int(8*scale), disk_bar_y + ram_bar_h + int(3*scale)), f"I/O W: {stats.get('disk_write_str', '0 KB/s')}", fill=c_slate, font=f_micro, anchor="rt")

        # ==================== BARRA INFERIOR / RODAPÉ ====================
        bot_y0 = height - bot_h - int(4 * scale)
        bot_y1 = height - int(4 * scale)
        self._draw_hud_bracket_card(draw, int(6*scale), bot_y0, width - int(6*scale), bot_y1, scale, fill=(6, 12, 9), border=c_green, bracket_len=6)

        mid_bot_y = (bot_y0 + bot_y1) // 2
        footer_left = "⚡ MONSTER TELEMETRIA  |  BARRAS VENTOINHAS CPU & GPU  |  [F11] TELA CHEIA  |  [T] OVERLAY" if width >= 750 else "[F11] TELA CHEIA  |  MONSTER TELEMETRIA"
        draw.text((int(14*scale), mid_bot_y), footer_left, fill="#86efac", font=f_small, anchor="lm")

        footer_right = f"FPS: {stats.get('fps', 144)}  |  DRIVER USB: {stats.get('driver_status', 'ONLINE')}" if width >= 650 else f"FPS: {stats.get('fps', 144)}"
        draw.text((width - int(14*scale), mid_bot_y), footer_right, fill=c_cyan, font=f_small, anchor="rm")

        return img

    def render_frame(self, stats, width=480, height=320):
        """Renderiza o frame solicitado na resolução desejada."""
        theme_info = self.themes.get(self.current_theme_name, self.themes["Master Telemetry (Todos os Sensores)"])
        layout = theme_info.get("layout", "ALL_SENSORS")

        if layout == "ALL_SENSORS":
            return self.render_sensors_view(stats, width, height)
        elif layout == "SPEEDOMETER":
            return self.render_speedometer_view(stats, width, height)
        elif layout == "AIRPLANE_COCKPIT":
            return self.render_airplane_cockpit_view(stats, width, height)
        elif layout == "GT_COCKPIT":
            return self.render_gt_cockpit_view(stats, width, height)
        elif layout == "XR2_MK2":
            return self.render_xr2_view(stats, width, height)
        elif layout == "CS2":
            return self.render_cs2_view(stats, width, height)
        elif layout == "PUBG":
            return self.render_pubg_view(stats, width, height)
        elif layout == "PEUGEOT_508":
            return self.render_peugeot_508_view(stats, width, height)
        elif layout == "DJ_MIXER":
            return self.render_mixer_view(stats, width, height)
        elif layout == "TRANSPARENT_HUD":
            return self.render_transparent_hud_view(stats, width, height)
        elif layout == "NEON_DUAL":
            return self.render_neon_dual_view(stats, width, height)
        elif layout == "MONSTER_OFFICIAL":
            return self.render_monster_official_view(stats, width, height)

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
        """Atualiza o Canvas com renderização nativa e Auto-Fit universal (ajuste perfeito a qualquer ecrã/monitor)."""
        cw = max(100, self.canvas.winfo_width())
        ch = max(100, self.canvas.winfo_height())

        theme_info = self.themes.get(self.current_theme_name, {})
        layout = theme_info.get("layout", "ALL_SENSORS")
        is_transparent = (layout == "TRANSPARENT_HUD" or self.transparent_mode_var.get())

        is_widescreen = layout in (
            "ALL_SENSORS", "SPEEDOMETER", "AIRPLANE_COCKPIT", "GT_COCKPIT",
            "XR2_MK2", "CS2", "PUBG", "PEUGEOT_508", "DJ_MIXER",
            "TRANSPARENT_HUD", "NEON_DUAL", "MONSTER_OFFICIAL"
        )
        base_w = 1280 if is_widescreen else 480
        base_h = 720 if is_widescreen else 320

        # Auto-Ajuste Proporcional Inteligente (Auto-Fit sem distorções nem colisões)
        fit_scale = min(cw / float(base_w), ch / float(base_h))
        tw = max(160, int(base_w * fit_scale))
        th = max(90, int(base_h * fit_scale))

        # Renderiza o tema exatamente na sua proporção nativa
        frame = self.render_frame(stats, width=tw, height=th)

        # Se as dimensões coincidirem exatamente (ex: fullscreen 16:9), exibe direto
        if tw == cw and th == ch:
            display_frame = frame
        else:
            # Preenche o fundo restante sem distorção (Chroma-Key ou preto #07090f)
            bg_rgb = (1, 2, 3) if is_transparent else (7, 9, 15)
            display_frame = Image.new("RGB", (cw, ch), bg_rgb)
            pos_x = (cw - tw) // 2
            pos_y = (ch - th) // 2
            display_frame.paste(frame, (pos_x, pos_y))

        self.preview_image = ImageTk.PhotoImage(display_frame)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_image)

        # Se a transmissão contínua estiver parada, envia o frame estático inicial para o servidor Wi-Fi
        if not self.running and self.wifi_enabled_var.get() and self.web_server.is_running:
            wifi_frame = self.render_frame(stats, width=1280, height=720) if is_widescreen else frame
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
                        wifi_frame = self.render_frame(stats, width=1280, height=720) if layout in ("ALL_SENSORS", "SPEEDOMETER", "AIRPLANE_COCKPIT", "GT_COCKPIT", "XR2_MK2", "CS2", "PUBG", "PEUGEOT_508", "DJ_MIXER", "TRANSPARENT_HUD", "NEON_DUAL", "MONSTER_OFFICIAL") else usb_frame
                        self.web_server.update_frame(wifi_frame, stats)
                    except Exception as we:
                        print(f"[App] Erro na frame Wi-Fi 720p: {we}")
                        try:
                            self.web_server.update_frame(usb_frame, stats)
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
                else:
                    # Auto-reconectar silenciosamente em segundo plano se o ecrã for reinserido
                    now = time.time()
                    if not hasattr(self, '_last_usb_recon_try') or (now - self._last_usb_recon_try > 4.0):
                        self._last_usb_recon_try = now
                        try:
                            self.driver.connect("AUTO")
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
