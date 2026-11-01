"""
Monster Telemetria - Módulo de Sensores Flutuantes Individuais (Floating Mini-HUDs)
Permite ao utilizador ter uma lista com todos os sensores do PC, decidir quais quer usar
individualmente (como nas fotos) e movê-los livremente através de todos os ecrãs (Monitores 1, 2, 3...)
com suporte a fundo transparente (Chroma-Key) e fixação Sempre no Topo.
"""

import os
import sys
import time
import json
import math
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw, ImageFont

class FloatingWidgetWindow:
    CHROMA_KEY = "#010203"

    def __init__(self, manager, widget_id, title, subtitle, width, height, render_fn, default_x, default_y):
        self.manager = manager
        self.widget_id = widget_id
        self.title = title
        self.subtitle = subtitle
        self.width = width
        self.height = height
        self.render_fn = render_fn
        
        # Carregar posições guardadas
        cfg = self.manager.get_widget_config(self.widget_id)
        self.x = cfg.get("x", default_x)
        self.y = cfg.get("y", default_y)
        self.is_topmost = cfg.get("topmost", True)
        self.is_transparent = cfg.get("transparent", True)
        self.is_locked = cfg.get("locked", False)
        
        self.window = None
        self.canvas = None
        self._photo = None
        self._img_item = None
        self._drag_start_x = 0
        self._drag_start_y = 0

    def show(self):
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.deiconify()
            self.window.lift()
            if self.is_topmost:
                try:
                    self.window.attributes("-topmost", True)
                except Exception:
                    pass
            return

        self.window = tk.Toplevel(self.manager.root)
        self.window.title(f"Sensor // {self.title}")
        self.window.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")
        self.window.overrideredirect(True)
        self.window.configure(bg=self.CHROMA_KEY)

        try:
            self.window.attributes("-topmost", self.is_topmost)
        except Exception:
            pass

        if self.is_transparent:
            try:
                self.window.attributes("-transparentcolor", self.CHROMA_KEY)
            except Exception:
                pass

        self.canvas = tk.Canvas(
            self.window,
            width=self.width,
            height=self.height,
            bg=self.CHROMA_KEY if self.is_transparent else "#0a0e14",
            highlightthickness=0,
            cursor="fleur" if not self.is_locked else "arrow"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Suporte para arrastar com o rato entre ecrãs (absoluto via x_root / y_root sem drift)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_drag_release)

        # Menu de contexto no botão direito
        self.canvas.bind("<Button-3>", self._show_context_menu)

        # Atualizar imagem inicial se já houver dados
        if self.manager.last_stats:
            self.update_stats(self.manager.last_stats)

    def hide(self):
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.withdraw()

    def close(self):
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.destroy()
            self.window = None

    def is_visible(self):
        return bool(self.window and tk.Toplevel.winfo_exists(self.window) and self.window.winfo_viewable())

    def update_stats(self, stats):
        if not self.window or not tk.Toplevel.winfo_exists(self.window) or not self.window.winfo_viewable():
            return

        try:
            bg_color = (1, 2, 3) if self.is_transparent else (10, 14, 20)
            img = Image.new("RGB", (self.width, self.height), bg_color)
            draw = ImageDraw.Draw(img)

            # Executa o desenho do sensor individual
            self.render_fn(img, draw, self.width, self.height, stats, self.manager)

            # Botão subtil de fechar no canto superior direito
            f_x = self.manager.app._get_font("ui", 7.0, 1.0, bold=True)
            draw.text((self.width - 12, 10), "✕", fill="#475569", font=f_x, anchor="mm")

            self._photo = ImageTk.PhotoImage(img)
            if self._img_item is None:
                self._img_item = self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
            else:
                self.canvas.itemconfig(self._img_item, image=self._photo)
        except Exception as e:
            print(f"[Widget {self.widget_id}] Erro ao atualizar: {e}")

    def _on_drag_start(self, event):
        # Se clicou no '✕' (canto superior direito), fecha o widget diretamente
        if event.x >= self.width - 24 and event.y <= 24:
            self.manager.toggle_widget(self.widget_id, False)
            return

        if self.is_locked:
            return
        self._drag_start_x = event.x_root - self.window.winfo_x()
        self._drag_start_y = event.y_root - self.window.winfo_y()

    def _on_drag_motion(self, event):
        if self.is_locked:
            return
        new_x = event.x_root - self._drag_start_x
        new_y = event.y_root - self._drag_start_y
        self.window.geometry(f"+{new_x}+{new_y}")

    def _on_drag_release(self, event):
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.x = self.window.winfo_x()
            self.y = self.window.winfo_y()
            self.manager.save_widget_position(self.widget_id, self.x, self.y)

    def move_to_monitor(self, mon_idx):
        monitors = self.manager.get_monitors_list()
        if 0 <= mon_idx < len(monitors):
            m = monitors[mon_idx]
            # Centrar o widget ou colocar no canto superior esquerdo com margem
            new_x = m["left"] + 40
            new_y = m["top"] + 40
            self.x = new_x
            self.y = new_y
            self.manager.save_widget_position(self.widget_id, new_x, new_y)
            if self.window and tk.Toplevel.winfo_exists(self.window):
                self.window.geometry(f"+{new_x}+{new_y}")
                self.window.lift()

    def _show_context_menu(self, event):
        menu = tk.Menu(self.window, tearoff=0, bg="#111827", fg="#f3f4f6", activebackground="#374151")
        
        topmost_lbl = "✓ Sempre no Topo" if self.is_topmost else "  Sempre no Topo"
        menu.add_command(label=topmost_lbl, command=self._toggle_topmost)
        
        trans_lbl = "✓ Fundo Transparente (Overlay)" if self.is_transparent else "  Fundo Transparente (Overlay)"
        menu.add_command(label=trans_lbl, command=self._toggle_transparency)

        lock_lbl = "✓ Bloquear Posição" if self.is_locked else "  Bloquear Posição"
        menu.add_command(label=lock_lbl, command=self._toggle_lock)

        # Submenu: Mover para Monitor
        monitors = self.manager.get_monitors_list()
        if len(monitors) > 1:
            mon_menu = tk.Menu(menu, tearoff=0, bg="#111827", fg="#f3f4f6", activebackground="#374151")
            for idx, m in enumerate(monitors):
                mon_menu.add_command(
                    label=f"🖥️ {m['label']}",
                    command=lambda i=idx: self.move_to_monitor(i)
                )
            menu.add_cascade(label="🖥️ Enviar para Ecrã", menu=mon_menu)

        menu.add_separator()
        menu.add_command(label="✕ Fechar este Sensor", command=lambda: self.manager.toggle_widget(self.widget_id, False))
        menu.add_command(label="⚙ Lista de Todos os Sensores", command=self.manager.open_manager_window)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _toggle_topmost(self):
        self.is_topmost = not self.is_topmost
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.attributes("-topmost", self.is_topmost)
        self.manager.save_widget_opt(self.widget_id, "topmost", self.is_topmost)

    def _toggle_transparency(self):
        self.is_transparent = not self.is_transparent
        if self.window and tk.Toplevel.winfo_exists(self.window):
            if self.is_transparent:
                try:
                    self.window.attributes("-transparentcolor", self.CHROMA_KEY)
                except Exception:
                    pass
                self.canvas.config(bg=self.CHROMA_KEY)
            else:
                try:
                    self.window.attributes("-transparentcolor", "")
                except Exception:
                    pass
                self.canvas.config(bg="#0a0e14")
        self.manager.save_widget_opt(self.widget_id, "transparent", self.is_transparent)
        if self.manager.last_stats:
            self.update_stats(self.manager.last_stats)

    def _toggle_lock(self):
        self.is_locked = not self.is_locked
        if self.canvas:
            self.canvas.config(cursor="arrow" if self.is_locked else "fleur")
        self.manager.save_widget_opt(self.widget_id, "locked", self.is_locked)


class FloatingWidgetsManager:
    """Gestor central de todos os sensores e widgets flutuantes independentes."""

    def __init__(self, root, app_ref):
        self.root = root
        self.app = app_ref
        self.config_file = os.path.join(self.app.base_dir, "widgets_config.json")
        self.config = self._load_config()
        self.last_stats = None
        self.manager_win = None
        
        # Catálogo com todos os 10 Sensores Individuais (correspondentes às fotos)
        self.widgets = {}
        self._init_widgets()

    def get_monitors_list(self):
        from app import get_all_monitors
        try:
            return get_all_monitors()
        except Exception:
            return [{'index': 1, 'label': 'Ecrã 1', 'left': 0, 'top': 0, 'width': 1920, 'height': 1080}]

    def _init_widgets(self):
        # 1. Mostrador CPU Load & Temp (Foto 1)
        self.widgets["cpu_dial"] = FloatingWidgetWindow(
            self, "cpu_dial", "CPU Intel Core (Carga & Temp)",
            "Mostrador circular de carga, temperatura, frequência GHz, consumo Watts e núcleos",
            276, 170, self._render_cpu_dial, default_x=60, default_y=60
        )

        # 2. Mostrador GPU Load & Temp (Foto 2)
        self.widgets["gpu_dial"] = FloatingWidgetWindow(
            self, "gpu_dial", "GPU RTX 4070 Ti (Carga & Temp)",
            "Mostrador circular de carga, temperatura, clock MHz, consumo Watts e VRAM",
            276, 170, self._render_gpu_dial, default_x=350, default_y=60
        )

        # 3. Barra Memória RAM DDR5 (Foto 4)
        self.widgets["ram_bar"] = FloatingWidgetWindow(
            self, "ram_bar", "Memória RAM DDR5",
            "Barra gradativa de uso da memória, percentagem, GB usados e total do sistema",
            276, 105, self._render_ram_bar, default_x=60, default_y=245
        )

        # 4. Barra Ventoinha CPU (Foto 3)
        self.widgets["cpu_fan"] = FloatingWidgetWindow(
            self, "cpu_fan", "Ventoinha CPU (Fan Speed)",
            "Velocidade em RPM, percentagem, modo Auto/Manual e barra segmentada em LEDs",
            276, 105, self._render_cpu_fan, default_x=60, default_y=365
        )

        # 5. Barra Ventoinha GPU (Foto 3)
        self.widgets["gpu_fan"] = FloatingWidgetWindow(
            self, "gpu_fan", "Ventoinha Gráfica (GPU Fan Speed)",
            "Velocidade em RPM, percentagem, modo Auto/Manual e barra segmentada em LEDs Cyan",
            276, 105, self._render_gpu_fan, default_x=350, default_y=365
        )

        # 6. Armazenamento SSD C: & E: (Foto 3)
        self.widgets["storage"] = FloatingWidgetWindow(
            self, "storage", "Discos SSD (C: & E:)",
            "Capacidade ocupada nos discos C: e E: com taxas de leitura e escrita I/O",
            276, 105, self._render_storage, default_x=350, default_y=245
        )

        # 7. Tráfego de Rede Wi-Fi / LAN (Foto 3)
        self.widgets["network"] = FloatingWidgetWindow(
            self, "network", "Tráfego de Rede (Down/Up)",
            "Taxa de transferência em tempo real de Download e Upload Wi-Fi/LAN",
            276, 105, self._render_network, default_x=640, default_y=245
        )

        # 8. Perfis de Arrefecimento & Motherboard (Foto 3)
        self.widgets["cooling_profiles"] = FloatingWidgetWindow(
            self, "cooling_profiles", "Perfis de Arrefecimento & Motherboard",
            "Perfil ativo (Auto/Silêncio/Equilíbrio/Gaming/Turbo) e temperatura da placa-mãe",
            276, 105, self._render_cooling_profiles, default_x=640, default_y=365
        )

        # 9. Emblema Oficial Monster Telemetria (Foto 3)
        self.widgets["monster_emblem"] = FloatingWidgetWindow(
            self, "monster_emblem", "Emblema Oficial Monster Telemetria",
            "Logótipo oficial embutido em 3D com circuitos cibernéticos e estética neon",
            276, 170, self._render_monster_emblem, default_x=640, default_y=60
        )

        # 10. Relógio Digital HUD & Uptime (Foto 3 - Topo)
        self.widgets["clock_uptime"] = FloatingWidgetWindow(
            self, "clock_uptime", "Relógio Digital HUD & Uptime",
            "Relógio com hora de alta precisão e tempo de atividade do Windows (Uptime)",
            276, 80, self._render_clock_uptime, default_x=60, default_y=485
        )

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def get_widget_config(self, widget_id):
        return self.config.get(widget_id, {})

    def save_widget_position(self, widget_id, x, y):
        if widget_id not in self.config:
            self.config[widget_id] = {}
        self.config[widget_id]["x"] = x
        self.config[widget_id]["y"] = y
        self._save_config()

    def save_widget_opt(self, widget_id, key, val):
        if widget_id not in self.config:
            self.config[widget_id] = {}
        self.config[widget_id][key] = val
        self._save_config()

    def toggle_widget(self, widget_id, show_it=None):
        w = self.widgets.get(widget_id)
        if not w:
            return
        if show_it is None:
            show_it = not w.is_visible()
            
        if show_it:
            w.show()
        else:
            w.hide()
            
        self.save_widget_opt(widget_id, "enabled", show_it)
        if self.manager_win and tk.Toplevel.winfo_exists(self.manager_win):
            self._refresh_manager_switches()

    def show_all(self):
        for w_id in self.widgets:
            self.toggle_widget(w_id, True)

    def hide_all(self):
        for w_id in self.widgets:
            self.toggle_widget(w_id, False)

    def set_all_topmost(self, enable=True):
        for w in self.widgets.values():
            w.is_topmost = enable
            if w.window and tk.Toplevel.winfo_exists(w.window):
                w.window.attributes("-topmost", enable)
            self.save_widget_opt(w.widget_id, "topmost", enable)

    def restore_active_widgets(self):
        """Restaura automaticamente no arranque os widgets que o utilizador deixou ligados."""
        for w_id, w in self.widgets.items():
            cfg = self.get_widget_config(w_id)
            if cfg.get("enabled", False):
                w.show()

    def update_all(self, stats):
        self.last_stats = stats
        for w in self.widgets.values():
            if w.is_visible():
                w.update_stats(stats)

    # ==================== RENDERIZADORES INDIVIDUAIS DOS SENSORES ====================

    def _render_cpu_dial(self, img, draw, w, h, stats, mgr):
        # Moldura HUD Bracket Verde
        c_green = "#39ff14"
        mgr.app._draw_hud_bracket_card(draw, 4, 4, w - 4, h - 4, scale=1.0, fill=(8, 16, 10), border=c_green, bracket_len=14)
        
        # Mostrador Circular à Esquerda (Foto 1)
        gauge_cx = int(w * 0.32)
        gauge_cy = h // 2
        gauge_r = 38
        c_temp = c_green if stats["cpu_temp"] < 60 else ("#f59e0b" if stats["cpu_temp"] < 75 else "#ff0055")
        mgr.app._draw_circular_hud_meter(
            draw, gauge_cx, gauge_cy, gauge_r, stats["cpu_usage"], scale=1.0,
            label="CPU LOAD", val_str=f"{stats['cpu_usage']}%", temp_str=f"{stats['cpu_temp']}°C",
            primary_color=c_green, temp_color=c_temp
        )

        # Detalhes textuais à Direita (Foto 1)
        det_x = int(w * 0.58)
        det_y = 22
        f_title = mgr.app._get_font("ui", 8.5, 1.0, bold=True)
        f_small = mgr.app._get_font("ui", 7.5, 1.0, bold=False)
        
        draw.text((det_x, det_y), "INTEL CORE", fill=c_green, font=f_title, anchor="la")
        det_y += 24
        draw.text((det_x, det_y), f"CLOCK: {stats.get('cpu_ghz', 3.5)} GHz", fill="#ffffff", font=f_small, anchor="la")
        det_y += 20
        draw.text((det_x, det_y), f"POWER: {stats.get('cpu_power', 45)} W", fill="#94a3b8", font=f_small, anchor="la")
        det_y += 20
        draw.text((det_x, det_y), f"CORES: {stats.get('cpu_cores', '14C / 20T')}", fill="#94a3b8", font=f_small, anchor="la")

    def _render_gpu_dial(self, img, draw, w, h, stats, mgr):
        # Moldura HUD Bracket Cyan (Foto 2)
        c_cyan = "#00e5ff"
        mgr.app._draw_hud_bracket_card(draw, 4, 4, w - 4, h - 4, scale=1.0, fill=(8, 14, 18), border=c_cyan, bracket_len=14)
        
        gauge_cx = int(w * 0.32)
        gauge_cy = h // 2
        gauge_r = 38
        c_temp = "#10b981" if stats["gpu_temp"] < 55 else ("#f59e0b" if stats["gpu_temp"] < 75 else "#ff0055")
        mgr.app._draw_circular_hud_meter(
            draw, gauge_cx, gauge_cy, gauge_r, stats["gpu_usage"], scale=1.0,
            label="GPU LOAD", val_str=f"{stats['gpu_usage']}%", temp_str=f"{stats['gpu_temp']}°C",
            primary_color=c_cyan, temp_color=c_temp
        )

        det_x = int(w * 0.58)
        det_y = 22
        f_title = mgr.app._get_font("ui", 8.5, 1.0, bold=True)
        f_small = mgr.app._get_font("ui", 7.5, 1.0, bold=False)
        
        draw.text((det_x, det_y), stats.get("gpu_name", "RTX 4070 Ti"), fill=c_cyan, font=f_title, anchor="la")
        det_y += 24
        draw.text((det_x, det_y), f"CLOCK: {stats.get('gpu_clock', 2640)} MHz", fill="#ffffff", font=f_small, anchor="la")
        det_y += 20
        draw.text((det_x, det_y), f"POWER: {stats.get('gpu_power', 28.5)} W", fill="#94a3b8", font=f_small, anchor="la")
        det_y += 20
        draw.text((det_x, det_y), f"VRAM: {stats.get('gpu_vram_used', 2.1)}/{stats.get('gpu_vram_total', 12.0)} GB", fill="#94a3b8", font=f_small, anchor="la")

    def _render_ram_bar(self, img, draw, w, h, stats, mgr):
        # Foto 4
        c_green = "#39ff14"
        mgr.app._draw_hud_bracket_card(draw, 4, 4, w - 4, h - 4, scale=1.0, fill=(8, 16, 10), border=c_green, bracket_len=10)
        
        f_title = mgr.app._get_font("ui", 8.5, 1.0, bold=True)
        f_val = mgr.app._get_font("mono", 10.0, 1.0, bold=True)
        f_micro = mgr.app._get_font("mono", 7.5, 1.0, bold=False)

        draw.text((14, 12), "MEMÓRIA RAM DDR5", fill=c_green, font=f_title, anchor="lt")
        draw.text((w - 28, 12), f"{stats['ram_usage']}%", fill="#ffffff", font=f_val, anchor="rt")

        bar_y = 42
        bar_h = 10
        bar_w = w - 28
        draw.rectangle([14, bar_y, 14 + bar_w, bar_y + bar_h], fill=(12, 26, 16))
        fill_w = int(bar_w * (stats["ram_usage"] / 100.0))
        if fill_w > 0:
            draw.rectangle([14, bar_y, 14 + fill_w, bar_y + bar_h], fill=c_green)

        draw.text((14, bar_y + bar_h + 10), f"USADO: {stats['ram_used_gb']} GB", fill="#94a3b8", font=f_micro, anchor="lt")
        draw.text((w - 28, bar_y + bar_h + 10), f"TOTAL: {stats['ram_total_gb']} GB", fill="#94a3b8", font=f_micro, anchor="rt")

    def _render_cpu_fan(self, img, draw, w, h, stats, mgr):
        mgr.app._draw_fan_speed_bar(
            draw, 4, 4, w - 8, h - 8,
            percent=stats.get("cpu_fan_pct", 60),
            rpm=stats.get("cpu_fan", 1750),
            is_auto=stats.get("cpu_fan_auto", True),
            title="⚡ CPU FAN SPEED",
            primary_color="#39ff14",
            dark_color=(8, 28, 14),
            scale=1.0
        )

    def _render_gpu_fan(self, img, draw, w, h, stats, mgr):
        mgr.app._draw_fan_speed_bar(
            draw, 4, 4, w - 8, h - 8,
            percent=stats.get("gpu_fan_pct", 50),
            rpm=stats.get("gpu_fan_rpm", 1450),
            is_auto=stats.get("gpu_fan_auto", True),
            title="⚡ GPU FAN SPEED",
            primary_color="#00e5ff",
            dark_color=(8, 24, 32),
            scale=1.0
        )

    def _render_storage(self, img, draw, w, h, stats, mgr):
        c_cyan = "#00e5ff"
        mgr.app._draw_hud_bracket_card(draw, 4, 4, w - 4, h - 4, scale=1.0, fill=(8, 14, 18), border=c_cyan, bracket_len=10)
        
        f_title = mgr.app._get_font("ui", 8.5, 1.0, bold=True)
        f_val = mgr.app._get_font("mono", 9.0, 1.0, bold=True)
        f_micro = mgr.app._get_font("mono", 7.5, 1.0, bold=False)

        draw.text((14, 12), "ARMAZENAMENTO (C: & E:)", fill=c_cyan, font=f_title, anchor="lt")
        draw.text((w - 28, 12), f"C: {stats['disk_c_pct']}%  E: {stats['disk_e_pct']}%", fill="#ffffff", font=f_val, anchor="rt")

        bar_y = 42
        bar_h = 10
        bar_w = w - 28
        draw.rectangle([14, bar_y, 14 + bar_w, bar_y + bar_h], fill=(12, 24, 30))
        fill_w = int(bar_w * (stats["disk_c_pct"] / 100.0))
        if fill_w > 0:
            draw.rectangle([14, bar_y, 14 + fill_w, bar_y + bar_h], fill=c_cyan)

        draw.text((14, bar_y + bar_h + 10), f"I/O R: {stats.get('disk_read_str', '0 KB/s')}", fill="#94a3b8", font=f_micro, anchor="lt")
        draw.text((w - 28, bar_y + bar_h + 10), f"I/O W: {stats.get('disk_write_str', '0 KB/s')}", fill="#94a3b8", font=f_micro, anchor="rt")

    def _render_network(self, img, draw, w, h, stats, mgr):
        c_cyan = "#00e5ff"
        c_green = "#39ff14"
        mgr.app._draw_hud_bracket_card(draw, 4, 4, w - 4, h - 4, scale=1.0, fill=(8, 14, 12), border=c_cyan, bracket_len=10)
        
        f_title = mgr.app._get_font("ui", 8.5, 1.0, bold=True)
        f_val = mgr.app._get_font("mono", 9.0, 1.0, bold=True)
        f_small = mgr.app._get_font("ui", 7.5, 1.0, bold=False)

        draw.text((14, 12), "REDE & COMUNICAÇÃO", fill=c_cyan, font=f_title, anchor="lt")
        draw.text((w - 28, 12), "ATIVO", fill=c_green, font=f_title, anchor="rt")

        down_y = 44
        draw.text((14, down_y), "▼ DOWNLOAD:", fill="#94a3b8", font=f_small, anchor="lt")
        draw.text((w - 28, down_y), stats.get("net_down_str", "0 KB/s"), fill=c_green, font=f_val, anchor="rt")

        up_y = down_y + 24
        draw.text((14, up_y), "▲ UPLOAD:", fill="#94a3b8", font=f_small, anchor="lt")
        draw.text((w - 28, up_y), stats.get("net_up_str", "0 KB/s"), fill=c_cyan, font=f_val, anchor="rt")

    def _render_cooling_profiles(self, img, draw, w, h, stats, mgr):
        c_green = "#39ff14"
        mgr.app._draw_hud_bracket_card(draw, 4, 4, w - 4, h - 4, scale=1.0, fill=(8, 14, 12), border=(40, 160, 90), bracket_len=10)
        
        f_title = mgr.app._get_font("ui", 8.0, 1.0, bold=True)
        f_micro = mgr.app._get_font("mono", 6.8, 1.0, bold=False)

        draw.text((14, 10), "PERFIL DE ARREFECIMENTO", fill="#6ee7b7", font=f_title, anchor="lt")

        # Botões de Perfis
        profiles = ["AUTO", "SIL", "EQU", "GAME", "MAX"]
        p_w = (w - 28 - (len(profiles) - 1) * 3) // len(profiles)
        avg_fan = (stats.get("cpu_fan_pct", 50) + stats.get("gpu_fan_pct", 50)) // 2
        cur_prof = "AUTO" if (stats.get("cpu_fan_auto", True) and stats.get("gpu_fan_auto", True)) else ("SIL" if avg_fan <= 40 else ("EQU" if avg_fan <= 60 else ("GAME" if avg_fan <= 85 else "MAX")))
        
        py0 = 36
        for idx, p_name in enumerate(profiles):
            px0 = 14 + idx * (p_w + 3)
            px1 = px0 + p_w
            is_cur = (p_name == cur_prof)
            bg_col = (57, 255, 20) if is_cur else (16, 26, 20)
            fg_col = "#040d06" if is_cur else "#64748b"
            draw.rectangle([px0, py0, px1, py0 + 18], fill=bg_col)
            draw.text(((px0 + px1) // 2, py0 + 9), p_name, fill=fg_col, font=f_micro, anchor="mm")

        draw.text((14, 76), "TEMP MOTHERBOARD:", fill="#94a3b8", font=f_micro, anchor="lt")
        draw.text((w - 28, 76), f"{stats.get('sys_temp', 32)}°C", fill=c_green, font=f_micro, anchor="rt")

    def _render_monster_emblem(self, img, draw, w, h, stats, mgr):
        c_green = "#39ff14"
        mgr.app._draw_hud_bracket_card(draw, 4, 4, w - 4, h - 4, scale=1.0, fill=(7, 14, 10), border=c_green, bracket_len=14)
        
        f_title = mgr.app._get_font("ui", 8.0, 1.0, bold=True)
        f_micro = mgr.app._get_font("mono", 7.0, 1.0, bold=False)

        # Colar o Logótipo Monster
        if mgr.app.monster_official_logo:
            try:
                logo_dim = 96
                logo_resized = mgr.app.monster_official_logo.resize((logo_dim, logo_dim), Image.Resampling.LANCZOS)
                lx = (w - logo_dim) // 2
                ly = 16
                img.paste(logo_resized, (lx, ly), logo_resized)
            except Exception:
                pass

        draw.text((w // 2, 126), "★ MONSTER TELEMETRIA ★", fill=c_green, font=f_title, anchor="mt")
        draw.text((w // 2, 146), "SISTEMA OPERACIONAL // ONLINE", fill="#64748b", font=f_micro, anchor="mt")

    def _render_clock_uptime(self, img, draw, w, h, stats, mgr):
        c_green = "#39ff14"
        mgr.app._draw_hud_bracket_card(draw, 4, 4, w - 4, h - 4, scale=1.0, fill=(6, 14, 9), border=c_green, bracket_len=10)
        
        f_title = mgr.app._get_font("ui", 8.0, 1.0, bold=True)
        f_clock = mgr.app._get_font("mono", 14.0, 1.0, bold=True)
        f_micro = mgr.app._get_font("mono", 8.0, 1.0, bold=False)

        draw.text((14, 14), "HORA DO SISTEMA", fill="#86efac", font=f_title, anchor="lt")
        clock_str = stats.get("time", "12:00:00")
        draw.text((14, 42), clock_str, fill=c_green, font=f_clock, anchor="lt")

        uptime_str = f"UPTIME: {stats.get('uptime', '2h 15m')}"
        draw.text((w - 28, 44), uptime_str, fill="#38bdf8", font=f_micro, anchor="rt")

    # ==================== INTERFACE DO GESTOR DE SENSORES ====================

    def open_manager_window(self):
        if self.manager_win and tk.Toplevel.winfo_exists(self.manager_win):
            self.manager_win.deiconify()
            self.manager_win.lift()
            self.manager_win.focus_force()
            return

        self.manager_win = tk.Toplevel(self.root)
        self.manager_win.title("Lista de Todos os Sensores do PC // Monster Telemetria")
        self.manager_win.geometry("640x700")
        self.manager_win.minsize(580, 500)
        self.manager_win.configure(bg="#0a0d14")

        # Cabeçalho
        hdr = tk.Frame(self.manager_win, bg="#0d111a", padx=18, pady=14)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="🧩 LISTA DE TODOS OS SENSORES DO PC", font=("Segoe UI", 13, "bold"), fg="#39ff14", bg="#0d111a").pack(anchor="w")
        tk.Label(
            hdr,
            text="Decida quais sensores quer usar individualmente como mini-HUDs flutuantes. Arraste qualquer sensor livremente com o rato para qualquer ecrã!",
            font=("Segoe UI", 9), fg="#94a3b8", bg="#0d111a", wraplength=590, justify="left"
        ).pack(anchor="w", pady=(3, 0))

        # Barra de Ações Globais
        act_frame = tk.Frame(self.manager_win, bg="#0a0d14", padx=18, pady=10)
        act_frame.pack(fill=tk.X)

        tk.Button(
            act_frame, text="▶ ABRIR TODOS", command=self.show_all,
            bg="#1e293b", fg="#39ff14", activebackground="#2e3e56", relief=tk.FLAT, font=("Segoe UI", 9, "bold"), padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            act_frame, text="⏹ FECHAR TODOS", command=self.hide_all,
            bg="#1e293b", fg="#ff0055", activebackground="#2e3e56", relief=tk.FLAT, font=("Segoe UI", 9, "bold"), padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            act_frame, text="📌 FIXAR NO TOPO", command=lambda: self.set_all_topmost(True),
            bg="#1e293b", fg="#38bdf8", activebackground="#2e3e56", relief=tk.FLAT, font=("Segoe UI", 9, "bold"), padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            act_frame, text="🔄 REINICIAR POSIÇÕES", command=self._reset_positions,
            bg="#1e293b", fg="#e2e8f0", activebackground="#2e3e56", relief=tk.FLAT, font=("Segoe UI", 9), padx=10, pady=5, cursor="hand2"
        ).pack(side=tk.RIGHT)

        # Contentor com Scrollbar para acomodar todos os 10 sensores confortavelmente
        canvas_wrap = tk.Frame(self.manager_win, bg="#0a0d14")
        canvas_wrap.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))

        m_canvas = tk.Canvas(canvas_wrap, bg="#0a0d14", highlightthickness=0)
        m_scroll = ttk.Scrollbar(canvas_wrap, orient="vertical", command=m_canvas.yview)
        cards_inner = tk.Frame(m_canvas, bg="#0a0d14")

        cards_inner.bind("<Configure>", lambda e: m_canvas.configure(scrollregion=m_canvas.bbox("all")))
        canvas_window = m_canvas.create_window((0, 0), window=cards_inner, anchor="nw")
        
        def _on_canvas_configure(e):
            m_canvas.itemconfig(canvas_window, width=e.width)
        m_canvas.bind("<Configure>", _on_canvas_configure)
        m_canvas.configure(yscrollcommand=m_scroll.set)

        m_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        m_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_wheel(e):
            m_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        m_canvas.bind("<MouseWheel>", _on_wheel)
        cards_inner.bind("<MouseWheel>", _on_wheel)

        # Lista de Sensores
        self._switch_btns = {}
        monitors = self.get_monitors_list()

        for w_id, w in self.widgets.items():
            card = tk.Frame(cards_inner, bg="#0d111a", padx=14, pady=10, highlightthickness=1, highlightbackground="#1e293b")
            card.pack(fill=tk.X, pady=5)

            # Informações do Sensor (Título + Descrição)
            info_frame = tk.Frame(card, bg="#0d111a")
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            title_row = tk.Frame(info_frame, bg="#0d111a")
            title_row.pack(anchor="w")

            color_dot = "●"
            dot_color = "#39ff14" if "cpu" in w_id or "ram" in w_id or "emblem" in w_id or "clock" in w_id else "#00e5ff"
            tk.Label(title_row, text=color_dot, font=("Segoe UI", 11, "bold"), fg=dot_color, bg="#0d111a").pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(title_row, text=w.title, font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#0d111a").pack(side=tk.LEFT)

            tk.Label(info_frame, text=w.subtitle, font=("Segoe UI", 8), fg="#94a3b8", bg="#0d111a", justify="left").pack(anchor="w", pady=(2, 0))

            # Ações à direita: Mover para Monitor + Botão LIGAR/DESLIGAR
            btn_box = tk.Frame(card, bg="#0d111a")
            btn_box.pack(side=tk.RIGHT, padx=(8, 0))

            # Dropdown de Monitores (se houver mais de 1)
            if len(monitors) > 1:
                mon_options = [f"Ecrã {m['index']}" for m in monitors]
                mon_cb = ttk.Combobox(btn_box, values=mon_options, state="readonly", width=8, font=("Segoe UI", 8))
                mon_cb.current(0)
                mon_cb.pack(side=tk.LEFT, padx=(0, 6))
                
                def _do_send(wid=w_id, cb=mon_cb):
                    sel = cb.current()
                    if sel >= 0:
                        self.toggle_widget(wid, True)
                        self.widgets[wid].move_to_monitor(sel)

                tk.Button(
                    btn_box, text="Enviar 🖥️", command=_do_send,
                    bg="#1e293b", fg="#38bdf8", activebackground="#2e3e56", relief=tk.FLAT, font=("Segoe UI", 8, "bold"), padx=6, pady=3, cursor="hand2"
                ).pack(side=tk.LEFT, padx=(0, 8))

            # Botão Switch ON / OFF
            is_active = w.is_visible()
            sw_btn = tk.Button(
                btn_box,
                text="LIGADO [ATIVO]" if is_active else "DESLIGADO",
                command=lambda wid=w_id: self._toggle_switch_clicked(wid),
                bg="#15803d" if is_active else "#1e293b",
                fg="#f0fdf4" if is_active else "#64748b",
                activebackground="#16a34a" if is_active else "#334155",
                relief=tk.FLAT,
                font=("Segoe UI", 8, "bold"),
                width=14,
                pady=4,
                cursor="hand2"
            )
            sw_btn.pack(side=tk.RIGHT)
            self._switch_btns[w_id] = sw_btn

        # Rodapé com Dicas de Utilização
        ftr = tk.Frame(self.manager_win, bg="#0d111a", padx=18, pady=10)
        ftr.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(
            ftr,
            text="💡 Dicas: Arraste com o botão esquerdo para posicionar onde quiser. Clique com o botão direito em qualquer widget para fixar no topo ou gerir transparência.",
            font=("Segoe UI", 8, "italic"), fg="#64748b", bg="#0d111a", wraplength=590, justify="left"
        ).pack(anchor="w")

    def _toggle_switch_clicked(self, widget_id):
        w = self.widgets.get(widget_id)
        if not w:
            return
        new_state = not w.is_visible()
        self.toggle_widget(widget_id, new_state)

    def _refresh_manager_switches(self):
        if not hasattr(self, "_switch_btns"):
            return
        for w_id, btn in self._switch_btns.items():
            w = self.widgets.get(w_id)
            if w and tk.Button.winfo_exists(btn):
                is_active = w.is_visible()
                btn.config(
                    text="LIGADO [ATIVO]" if is_active else "DESLIGADO",
                    bg="#15803d" if is_active else "#1e293b",
                    fg="#f0fdf4" if is_active else "#64748b",
                    activebackground="#16a34a" if is_active else "#334155"
                )

    def _reset_positions(self):
        defaults = {
            "cpu_dial": (60, 60),
            "gpu_dial": (350, 60),
            "ram_bar": (60, 245),
            "cpu_fan": (60, 365),
            "gpu_fan": (350, 365),
            "storage": (350, 245),
            "network": (640, 245),
            "cooling_profiles": (640, 365),
            "monster_emblem": (640, 60),
            "clock_uptime": (60, 485)
        }
        for w_id, (dx, dy) in defaults.items():
            w = self.widgets.get(w_id)
            if w:
                w.x = dx
                w.y = dy
                self.save_widget_position(w_id, dx, dy)
                if w.window and tk.Toplevel.winfo_exists(w.window):
                    w.window.geometry(f"+{dx}+{dy}")
