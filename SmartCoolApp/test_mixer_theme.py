import os
import sys
import math
from PIL import Image, ImageDraw, ImageFont

def get_font(font_type, size_pt, scale, bold=False):
    actual_size = max(7, int(size_pt * scale))
    font_names = {
        "ui": ["segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf"],
        "mono": ["consola.ttf", "consolab.ttf" if bold else "consola.ttf", "cour.ttf"]
    }
    for fname in font_names.get(font_type, ["arial.ttf"]):
        fpath = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", fname)
        if os.path.exists(fpath):
            try:
                return ImageFont.truetype(fpath, actual_size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_led_vu_meter(draw, x, y, width, height, level_ratio, num_segments=16, scale=1.0):
    """
    Desenha uma coluna de LEDs estilo mesa de mistura de estúdio (VU Meter / Equalizador).
    Verde na base, Âmbar a meio e Vermelho no topo (Peak/Clip).
    """
    level_ratio = min(1.0, max(0.0, level_ratio))
    gap = max(1, int(2 * scale))
    seg_h = (height - (num_segments - 1) * gap) / float(num_segments)

    # Cores ativas
    c_green = "#10b981"
    c_cyan = "#00d2ff"
    c_amber = "#fbbf24"
    c_red = "#ef4444"

    # Cores desligadas (dim)
    d_green = "#08231a"
    d_amber = "#241806"
    d_red = "#260909"

    for i in range(num_segments):
        # i = 0 é a base, i = num_segments - 1 é o topo
        seg_ratio = (i + 1) / float(num_segments)
        is_lit = (seg_ratio <= level_ratio)

        # Determinar cor do segmento
        if seg_ratio <= 0.60:
            color = c_green if is_lit else d_green
        elif seg_ratio <= 0.82:
            color = c_amber if is_lit else d_amber
        else:
            color = c_red if is_lit else d_red

        sy1 = y + height - int(i * (seg_h + gap))
        sy0 = sy1 - int(seg_h)

        draw.rectangle([x, sy0, x + width, sy1], fill=color)

def draw_fader(draw, track_x, track_y, track_h, level_ratio, scale=1.0):
    """Desenha a ranhura do fader e o manípulo metálico ajustado ao nível."""
    level_ratio = min(1.0, max(0.0, level_ratio))
    # Ranhura
    slot_w = max(2, int(3 * scale))
    draw.rectangle([track_x - slot_w // 2, track_y, track_x + slot_w // 2, track_y + track_h], fill="#0a0e14", outline="#1e293b", width=1)
    
    # Posição do manípulo (0 = fundo, 1 = topo)
    knob_y = track_y + track_h - int(level_ratio * track_h)
    kw = int(22 * scale)
    kh = int(12 * scale)
    kx0 = track_x - kw // 2
    kx1 = track_x + kw // 2
    ky0 = knob_y - kh // 2
    ky1 = knob_y + kh // 2

    # Corpo metálico do fader
    draw.rectangle([kx0, ky0, kx1, ky1], fill="#334155", outline="#64748b", width=1)
    # Linha branca central do manípulo
    draw.line([(kx0 + int(3*scale), knob_y), (kx1 - int(3*scale), knob_y)], fill="#f8fafc", width=max(1, int(1.5*scale)))

def render_mixer_view(stats, width=1280, height=720, assets_dir="assets"):
    scale = height / 320.0
    is_compact = (width <= 640)

    # 1. Carregar Wallpaper de Mesa de Mistura
    bg_path = os.path.join(assets_dir, "dj_mixer.jpg")
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

    # Barra Superior Studio Master
    bar_h = int(26 * scale)
    d_ov.rectangle([0, 0, width, bar_h], fill=(8, 12, 18, 235))

    # Barra Inferior Console Status
    bot_h = int(24 * scale)
    d_ov.rectangle([0, height - bot_h, width, height], fill=(8, 12, 18, 240))

    # 6 Canais de Áudio / Telemetria
    num_channels = 6
    pad_x = int(8 * scale)
    usable_w = width - (2 * pad_x)
    col_w = usable_w / float(num_channels)
    content_y0 = bar_h + int(6 * scale)
    content_y1 = height - bot_h - int(6 * scale)

    # Fundo translúcido para cada canal para garantir legibilidade de nível de estúdio
    for i in range(num_channels):
        cx0 = int(pad_x + i * col_w) + int(2 * scale)
        cx1 = int(pad_x + (i + 1) * col_w) - int(2 * scale)
        d_ov.rectangle([cx0, content_y0, cx1, content_y1], fill=(10, 15, 22, 215), outline=(30, 41, 59, 180), width=1)

    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Fontes
    f_title = get_font("ui", 10, scale, bold=True)
    f_clock = get_font("mono", 11, scale, bold=True)
    f_ch_title = get_font("ui", 8.5, scale, bold=True)
    f_val_giant = get_font("mono", 13, scale, bold=True)
    f_val_med = get_font("ui", 9.5, scale, bold=True)
    f_small = get_font("ui", 8.0, scale, bold=False)
    f_badge = get_font("mono", 8.5, scale, bold=True)

    c_cyan = "#00d2ff"
    c_green = "#10b981"
    c_amber = "#fbbf24"
    c_red = "#ef4444"
    c_white = "#f8fafc"
    c_slate = "#94a3b8"

    # Barra de Título Superior
    # Faixa colorida EQ
    draw.rectangle([0, 0, int(width * 0.35), int(2.5 * scale)], fill=c_cyan)
    draw.rectangle([int(width * 0.35), 0, int(width * 0.70), int(2.5 * scale)], fill=c_green)
    draw.rectangle([int(width * 0.70), 0, width, int(2.5 * scale)], fill=c_amber)

    draw.text((int(12 * scale), int(6 * scale)), "STUDIO MIXER // MASTER TELEMETRY EQUALIZER", fill=c_white, font=f_title)
    if not is_compact:
        draw.text((int(width * 0.52), int(7 * scale)), "24-BIT / 96kHz LIVE BUS", fill=c_slate, font=f_small)
    draw.text((width - int(100 * scale), int(6 * scale)), stats.get("time", "00:00"), fill=c_amber, font=f_clock)

    # Dados de cada canal
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
            "stat1": f"RTX 4070Ti",
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

    # Renderizar cada canal
    for i, ch in enumerate(channels_data):
        cx0 = int(pad_x + i * col_w) + int(2 * scale)
        cx1 = int(pad_x + (i + 1) * col_w) - int(2 * scale)
        mid_x = (cx0 + cx1) // 2

        # 1. Cabeçalho do Canal
        head_y = content_y0 + int(4 * scale)
        head_h = int(18 * scale)
        draw.rectangle([cx0 + int(4*scale), head_y, cx1 - int(4*scale), head_y + head_h], fill="#0e1726", outline="#1e293b", width=1)
        draw.text((mid_x, head_y + head_h // 2), ch["name"], fill=ch["color"], font=f_ch_title, anchor="mm")

        # 2. Informação Primária e Secundária
        t_y = head_y + head_h + int(4 * scale)
        draw.text((mid_x, t_y), ch["stat1"], fill=c_white, font=f_val_med, anchor="mt")
        draw.text((mid_x, t_y + int(14 * scale)), ch["stat2"], fill=ch["color"], font=f_small, anchor="mt")

        # 3. Equalizador LED (VU Meter) e Fader
        meter_y = t_y + int(30 * scale)
        meter_h = content_y1 - meter_y - int(40 * scale)

        # Se for compacto (480x320 USB LCD), o VU meter ocupa a largura toda
        # Se for normal (1280x720), desenha lado a lado: VU Meter à esquerda e Fader à direita!
        if not is_compact:
            # Lado esquerdo: VU Meter com 2 barras stereo
            vu_w = int(14 * scale)
            vu_x1 = mid_x - int(24 * scale)
            vu_x2 = vu_x1 + vu_w + int(3 * scale)
            draw_led_vu_meter(draw, vu_x1, meter_y, vu_w, meter_h, ch["ratio"], num_segments=18, scale=scale)
            # Ligeira variação no canal R para parecer stereo real
            r_ratio = max(0.0, min(1.0, ch["ratio"] * (0.92 if i % 2 == 0 else 1.05)))
            draw_led_vu_meter(draw, vu_x2, meter_y, vu_w, meter_h, r_ratio, num_segments=18, scale=scale)

            # Lado direito: Fader
            fader_x = mid_x + int(24 * scale)
            draw_fader(draw, fader_x, meter_y, meter_h, ch["ratio"], scale=scale)
        else:
            # Modo compacto 480x320: Barra LED larga de 16 segmentos
            vu_w = int(22 * scale)
            vu_x = mid_x - vu_w // 2
            draw_led_vu_meter(draw, vu_x, meter_y, vu_w, meter_h, ch["ratio"], num_segments=14, scale=scale)

        # 4. Valor em Percentagem / Nível
        val_y = content_y1 - int(34 * scale)
        draw.text((mid_x, val_y), ch["val_str"], fill=c_white, font=f_val_giant, anchor="mm")

        # 5. Rodapé do Canal
        foot_y = content_y1 - int(16 * scale)
        draw.text((mid_x, foot_y), ch["foot"], fill=c_slate, font=f_small, anchor="mm")

    # Rodapé Principal do Console
    bot_text_y = height - bot_h + int(4 * scale)
    draw.text((int(14 * scale), bot_text_y), "● REC [ACTIVE]   ► PLAY [ON]   SOLO [CUE]   CROSSFADER [CH 1 <---> CH 2]", fill=c_slate, font=f_small)
    draw.text((width - int(14 * scale), bot_text_y), f"BPM: {int(stats.get('cpu_clock', 4.80) * 26.5)} // DSP LOCK", fill=c_green, font=f_badge, anchor="rt")

    return img

if __name__ == "__main__":
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    mock_stats = {
        "time": "01:45",
        "cpu_temp": 47,
        "cpu_usage": 38,
        "cpu_clock": 4.80,
        "cpu_fan": 1280,
        "gpu_temp": 52,
        "gpu_usage": 45,
        "gpu_mem_used_gb": 4.8,
        "gpu_mem_total_gb": 12.0,
        "gpu_fan": 1350,
        "ram_usage": 46,
        "ram_used_gb": 14.8,
        "sys_temp": 38,
        "chassis_fan": 1100,
        "disk_c_free_gb": 218,
        "disk_c_usage": 56,
        "disk_e_free_gb": 845,
        "disk_e_usage": 48,
        "net_down_str": "8.4 MB/s",
        "net_up_str": "1.5 MB/s",
        "net_down_kb": 8400,
        "net_up_kb": 1500,
    }

    img_hd = render_mixer_view(mock_stats, 1280, 720, assets_dir)
    img_hd.save(os.path.join(assets_dir, "preview_theme_mixer.png"))
    img_hd.save(os.path.join(".", "preview_theme_mixer.png"))

    img_usb = render_mixer_view(mock_stats, 480, 320, assets_dir)
    img_usb.save(os.path.join(assets_dir, "preview_theme_mixer_usb.png"))
    img_usb.save(os.path.join(".", "preview_theme_mixer_usb.png"))
    print("[OK] Previews da Mesa de Mistura / Equalizador geradas com sucesso.")
