import os
import sys
import math
import time
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

def draw_hud_bracket_card(draw, x0, y0, x1, y1, scale, fill=(8, 14, 10), border=(57, 255, 20), bracket_len=10):
    if x1 <= x0 or y1 <= y0:
        return
    b_len = max(4, int(bracket_len * scale))
    draw.rectangle([x0, y0, x1, y1], fill=fill)
    b_rgb = border
    if isinstance(border, str):
        if border.startswith("#"):
            c = border.lstrip("#")
            b_rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
    dim_border = (max(5, b_rgb[0] // 5), max(5, b_rgb[1] // 5), max(5, b_rgb[2] // 5))
    draw.rectangle([x0, y0, x1, y1], outline=dim_border, width=1)
    # 4 Cantos destacados
    draw.line([(x0, y0), (x0 + b_len, y0)], fill=border, width=2)
    draw.line([(x0, y0), (x0, y0 + b_len)], fill=border, width=2)
    draw.line([(x1, y0), (x1 - b_len, y0)], fill=border, width=2)
    draw.line([(x1, y0), (x1, y0 + b_len)], fill=border, width=2)
    draw.line([(x0, y1), (x0 + b_len, y1)], fill=border, width=2)
    draw.line([(x0, y1), (x0, y1 - b_len)], fill=border, width=2)
    draw.line([(x1, y1), (x1 - b_len, y1)], fill=border, width=2)
    draw.line([(x1, y1), (x1, y1 - b_len)], fill=border, width=2)

def draw_circular_hud_meter(draw, cx, cy, radius, percent, scale, label="CPU", val_str="45%", temp_str="55°C", primary_color="#39ff14", temp_color="#39ff14"):
    r = max(15, int(radius * scale))
    bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.arc(bbox, start=135, end=405, fill=(15, 30, 20), width=max(3, int(4 * scale)))
    norm_pct = max(0, min(100, percent))
    span_angle = int(270 * (norm_pct / 100.0))
    if span_angle > 0:
        draw.arc(bbox, start=135, end=135 + span_angle, fill=primary_color, width=max(3, int(4 * scale)))
    f_pct = get_font("mono", 8.0, scale, bold=True)
    f_lbl = get_font("ui", 6.5, scale, bold=True)
    f_tmp = get_font("mono", 7.0, scale, bold=False)
    draw.text((cx, cy - int(9 * scale)), label, fill="#94a3b8", font=f_lbl, anchor="mm")
    draw.text((cx, cy + int(1 * scale)), val_str, fill="#f8fafc", font=f_pct, anchor="mm")
    draw.text((cx, cy + int(11 * scale)), temp_str, fill=temp_color, font=f_tmp, anchor="mm")

def draw_fan_speed_bar(draw, x0, y0, w, h, percent, rpm, is_auto, title, primary_color, dark_color, scale):
    draw_hud_bracket_card(draw, x0, y0, x0 + w, y0 + h, scale, fill=(10, 16, 12), border=primary_color, bracket_len=8)
    f_title = get_font("ui", 7.5, scale, bold=True)
    f_badge = get_font("mono", 6.8, scale, bold=True)
    f_val = get_font("mono", 10.0, scale, bold=True)
    f_rpm = get_font("ui", 7.5, scale, bold=False)
    f_ticks = get_font("mono", 6.0, scale, bold=False)

    pad_x = int(8 * scale)
    pad_y = int(5 * scale)

    mode_text = "[ AUTO ]" if is_auto else "[ MANUAL ]"
    mode_color = "#39ff14" if is_auto else "#f59e0b"

    disp_title = title
    t_bbox = draw.textbbox((x0 + pad_x, y0 + pad_y), disp_title, font=f_title, anchor="lt")
    m_bbox = draw.textbbox((x0 + w - pad_x, y0 + pad_y), mode_text, font=f_badge, anchor="rt")
    if t_bbox[2] + int(8*scale) > m_bbox[0]:
        disp_title = "CPU FAN" if "CPU" in title else "GPU FAN"

    draw.text((x0 + pad_x, y0 + pad_y), disp_title, fill="#f8fafc", font=f_title, anchor="lt")
    draw.text((x0 + w - pad_x, y0 + pad_y), mode_text, fill=mode_color, font=f_badge, anchor="rt")

    val_y = y0 + pad_y + int(12 * scale)
    draw.text((x0 + pad_x, val_y), f"{percent}%", fill=primary_color, font=f_val, anchor="lt")
    draw.text((x0 + w - pad_x, val_y + int(2 * scale)), f"{rpm} RPM", fill="#cbd5e1", font=f_rpm, anchor="rt")

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
                fill_c = "#ff0055"
            elif i >= num_segments - 6:
                fill_c = "#f59e0b"
            else:
                fill_c = primary_color
        else:
            fill_c = dark_color
        draw.rectangle([sx0, bar_y0, sx1, bar_y0 + bar_h], fill=fill_c)

    ticks_y = bar_y0 + bar_h + int(2 * scale)
    for tick_pct, tick_label in [(0, "0"), (50, "50"), (100, "100%")] if w < 250 else [(0, "0"), (25, "25"), (50, "50"), (75, "75"), (100, "100%")]:
        tx = bar_x0 + int(bar_w * (tick_pct / 100.0))
        t_anchor = "la" if tick_pct == 0 else ("ra" if tick_pct == 100 else "ma")
        draw.text((tx, ticks_y), tick_label, fill="#64748b", font=f_ticks, anchor=t_anchor)

def render_monster_official_view(stats, assets_dir, width=1280, height=720):
    scale = min(width / 568.888, height / 320.0)
    bg_file = os.path.join(assets_dir, "monster_telemetria_bg.jpg")
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

    f_header = get_font("ui", 8.5, scale, bold=True)
    f_clock = get_font("mono", 9.5, scale, bold=True)
    f_title = get_font("ui", 7.5, scale, bold=True)
    f_val = get_font("mono", 8.5, scale, bold=True)
    f_small = get_font("ui", 7.0, scale, bold=False)
    f_micro = get_font("mono", 6.5, scale, bold=False)

    # 1. Barra Superior Cabeçalho
    top_h = int(22 * min(1.3, scale))
    draw_hud_bracket_card(draw, int(6*scale), int(4*scale), width - int(6*scale), top_h + int(4*scale), scale, fill=(6, 14, 9), border=c_green, bracket_len=8)
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

    # 2. Dimensões das 3 Colunas: Esquerda (CPU - Verde), Centro (Logo Oficial & Hub), Direita (GPU - Cyan)
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
    draw_hud_bracket_card(draw, left_x0, content_y0, left_x1, content_y0 + cpu_card_h, scale, fill=(8, 16, 10), border=c_green, bracket_len=12)

    gauge_r = min(32, int(cpu_card_h * 0.28))
    gauge_cx = left_x0 + int(col_w * 0.30)
    gauge_cy = content_y0 + int(cpu_card_h * 0.52)
    c_temp_cpu = c_green if stats["cpu_temp"] < 60 else (c_amber if stats["cpu_temp"] < 75 else c_red)
    draw_circular_hud_meter(draw, gauge_cx, gauge_cy, gauge_r, stats["cpu_usage"], scale, label="CPU LOAD", val_str=f"{stats['cpu_usage']}%", temp_str=f"{stats['cpu_temp']}°C", primary_color=c_green, temp_color=c_temp_cpu)

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
    draw_fan_speed_bar(draw, left_x0, cpu_fan_y0, col_w, cpu_fan_h, cpu_fan_pct, cpu_fan_rpm, cpu_fan_auto, title="⚡ CPU FAN SPEED", primary_color=c_green, dark_color=(8, 28, 14), scale=scale)

    # CARTÃO RAM
    ram_y0 = cpu_fan_y0 + cpu_fan_h + int(5 * scale)
    draw_hud_bracket_card(draw, left_x0, ram_y0, left_x1, content_y1, scale, fill=(8, 16, 10), border=c_green, bracket_len=8)

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
    draw_hud_bracket_card(draw, mid_x0, content_y0, mid_x1, content_y0 + logo_card_h, scale, fill=(7, 14, 10), border=c_green, bracket_len=12)

    # Carregar e colar o logótipo oficial redimensionado
    logo_path = os.path.join(assets_dir, "monster_telemetria_logo.png")
    if os.path.exists(logo_path):
        try:
            raw_logo = Image.open(logo_path).convert("RGBA")
            # Dimensão do logótipo preservando 1:1
            max_logo_dim = min(col_w - int(24 * scale), logo_card_h - int(34 * scale))
            if max_logo_dim > 16:
                logo_resized = raw_logo.resize((max_logo_dim, max_logo_dim), Image.Resampling.LANCZOS)
                logo_x = mid_x0 + (col_w - max_logo_dim) // 2
                logo_y = content_y0 + int(6 * scale)
                img.paste(logo_resized, (logo_x, logo_y), logo_resized)
                
                # Legenda do Logótipo Oficial
                sub_y = logo_y + max_logo_dim + int(3 * scale)
                badge_str = "MONSTER TELEMETRIA" if col_w < 260 else "★ MONSTER TELEMETRIA OFFICIAL ★"
                draw.text((mid_x0 + col_w // 2, sub_y), badge_str, fill=c_green, font=f_title, anchor="mt")
        except Exception as e:
            print("Erro ao carregar logótipo:", e)
    else:
        draw.text((mid_x0 + col_w // 2, content_y0 + logo_card_h // 2), "MONSTER TELEMETRIA", fill=c_green, font=f_header, anchor="mm")

    # Módulo Perfis de Ventoinhas
    m_pad = int(8 * scale)
    prof_card_y0 = content_y0 + logo_card_h + int(5 * scale)
    prof_card_h = int(avail_h * 0.26)
    draw_hud_bracket_card(draw, mid_x0, prof_card_y0, mid_x1, prof_card_y0 + prof_card_h, scale, fill=(8, 14, 12), border=(40, 160, 90), bracket_len=8)

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
        draw.text(((px0 + px1) // 2, (py0 + py1) // 2), p_name, fill=fg_col, font=get_font("ui", 6.0, scale, bold=True), anchor="mm")

    stat_hub_y = prof_y1 + int(18 * scale)
    draw.text((mid_x0 + m_pad, stat_hub_y), "TEMP MOTHERBOARD:", fill=c_slate, font=f_micro, anchor="lt")
    draw.text((mid_x1 - m_pad, stat_hub_y), f"{stats.get('sys_temp', 32)}°C", fill=c_green, font=f_micro, anchor="rt")

    # Módulo Rede e Motherboard (Inferior Central)
    net_y0 = prof_card_y0 + prof_card_h + int(5 * scale)
    draw_hud_bracket_card(draw, mid_x0, net_y0, mid_x1, content_y1, scale, fill=(8, 14, 12), border=c_cyan, bracket_len=8)

    draw.text((mid_x0 + int(8*scale), net_y0 + int(4*scale)), "REDE & COMUNICAÇÃO", fill=c_cyan, font=f_title, anchor="lt")
    draw.text((mid_x1 - int(8*scale), net_y0 + int(4*scale)), "STATUS: ATIVO", fill=c_green, font=f_micro, anchor="rt")

    down_y = net_y0 + int(18 * scale)
    draw.text((mid_x0 + int(8*scale), down_y), "▼ DOWNLOAD:", fill=c_slate, font=f_small, anchor="lt")
    draw.text((mid_x1 - int(8*scale), down_y), stats.get("net_down_str", "0 KB/s"), fill=c_green, font=f_val, anchor="rt")

    up_y = down_y + int(13 * scale)
    draw.text((mid_x0 + int(8*scale), up_y), "▲ UPLOAD:", fill=c_slate, font=f_small, anchor="lt")
    draw.text((mid_x1 - int(8*scale), up_y), stats.get("net_up_str", "0 KB/s"), fill=c_cyan, font=f_val, anchor="rt")


    # ==================== COLUNA DIREITA: GPU & DISCOS (CYBER CYAN) ====================
    draw_hud_bracket_card(draw, right_x0, content_y0, right_x1, content_y0 + cpu_card_h, scale, fill=(8, 14, 18), border=c_cyan, bracket_len=12)

    gauge_gpu_cx = right_x0 + int(col_w * 0.30)
    gauge_gpu_cy = content_y0 + int(cpu_card_h * 0.52)
    c_temp_gpu = c_green if stats["gpu_temp"] < 55 else (c_amber if stats["gpu_temp"] < 75 else c_red)
    draw_circular_hud_meter(draw, gauge_gpu_cx, gauge_gpu_cy, gauge_r, stats["gpu_usage"], scale, label="GPU LOAD", val_str=f"{stats['gpu_usage']}%", temp_str=f"{stats['gpu_temp']}°C", primary_color=c_cyan, temp_color=c_temp_gpu)

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
    draw_fan_speed_bar(draw, right_x0, gpu_fan_y0, col_w, cpu_fan_h, gpu_fan_pct, gpu_fan_rpm, gpu_fan_auto, title="⚡ GPU FAN SPEED", primary_color=c_cyan, dark_color=(8, 24, 32), scale=scale)

    # CARTÃO ARMAZENAMENTO / DISCOS
    draw_hud_bracket_card(draw, right_x0, ram_y0, right_x1, content_y1, scale, fill=(8, 14, 18), border=c_cyan, bracket_len=8)

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
    draw_hud_bracket_card(draw, int(6*scale), bot_y0, width - int(6*scale), bot_y1, scale, fill=(6, 12, 9), border=c_green, bracket_len=6)

    mid_bot_y = (bot_y0 + bot_y1) // 2
    footer_left = "⚡ MONSTER TELEMETRIA  |  BARRAS VENTOINHAS CPU & GPU  |  [F11] TELA CHEIA  |  [T] OVERLAY" if width >= 750 else "[F11] TELA CHEIA  |  MONSTER TELEMETRIA"
    draw.text((int(14*scale), mid_bot_y), footer_left, fill="#86efac", font=f_small, anchor="lm")

    footer_right = f"FPS: {stats.get('fps', 144)}  |  DRIVER USB: {stats.get('driver_status', 'ONLINE')}" if width >= 650 else f"FPS: {stats.get('fps', 144)}"
    draw.text((width - int(14*scale), mid_bot_y), footer_right, fill=c_cyan, font=f_small, anchor="rm")

    return img

if __name__ == "__main__":
    assets_dir = r"E:\Gravi\SmartCoolApp\assets"
    dummy_stats = {
        "cpu_usage": 38,
        "cpu_temp": 52,
        "cpu_ghz": 4.8,
        "cpu_power": 65,
        "cpu_cores": "14C / 20T",
        "cpu_fan_pct": 65,
        "cpu_fan": 1850,
        "cpu_fan_auto": True,
        "gpu_name": "RTX 4070 Ti",
        "gpu_usage": 45,
        "gpu_temp": 48,
        "gpu_clock": 2680,
        "gpu_power": 120,
        "gpu_vram_used": 3.8,
        "gpu_vram_total": 12.0,
        "gpu_fan_pct": 55,
        "gpu_fan_rpm": 1550,
        "gpu_fan_auto": True,
        "ram_usage": 42,
        "ram_used_gb": 13.4,
        "ram_total_gb": 31.8,
        "disk_c_pct": 54,
        "disk_e_pct": 38,
        "disk_read_str": "12.4 MB/s",
        "disk_write_str": "4.1 MB/s",
        "net_down_str": "8.5 MB/s",
        "net_up_str": "1.2 MB/s",
        "sys_temp": 34,
        "chassis_fan": 1200,
        "fps": 165,
        "driver_status": "CONECTADO",
        "time": "20:30:15",
        "uptime": "4h 20m"
    }

    # Render at 1280x720
    im_720p = render_monster_official_view(dummy_stats, assets_dir, 1280, 720)
    im_720p.save(r"E:\Gravi\SmartCoolApp\assets\preview_theme_monster_official.png")
    im_720p.save(r"E:\Gravi\Temas\Previsualizacoes\TEMA_15_MONSTER_OFICIAL.png")
    print("Saved preview 720p successfully!")

    # Render at 480x320 (USB display)
    im_usb = render_monster_official_view(dummy_stats, assets_dir, 480, 320)
    im_usb.save(r"E:\Gravi\SmartCoolApp\assets\preview_theme_monster_official_usb.png")
    im_usb.save(r"E:\Gravi\Temas\Previsualizacoes\TEMA_15_MONSTER_OFICIAL_USB.png")
    print("Saved preview USB successfully!")

    # Also save to artifact directory for presentation
    art_dir = r"C:\Users\cac_7\.gemini\antigravity\brain\2950ecb9-2ce0-438a-a6ff-acc66792f61a"
    im_720p.save(os.path.join(art_dir, "preview_monster_official_720p.png"))
    im_usb.save(os.path.join(art_dir, "preview_monster_official_480x320.png"))
    print("Saved previews to artifact dir!")
