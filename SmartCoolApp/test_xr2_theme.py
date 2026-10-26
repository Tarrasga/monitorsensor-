"""
Test and render the Ford Fiesta XR2 Mk2 Theme.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

stats = {
    "time": "20:10:00",
    "uptime": "3h 45m",
    "cpu_temp": 52,
    "cpu_usage": 38,
    "cpu_clock": 4.8,
    "cpu_fan": 1250,
    "cpu_cores": "14C / 20T",
    "gpu_name": "RTX 4070 Ti",
    "gpu_temp": 58,
    "gpu_hotspot": 67,
    "gpu_usage": 64,
    "gpu_vram_used": 6.8,
    "gpu_vram_total": 12.0,
    "gpu_vram_pct": 57,
    "gpu_fan": 1420,
    "gpu_power": 185.0,
    "gpu_clock": 2610,
    "gpu_mem_clock": 10.5,
    "ram_used_gb": 14.2,
    "ram_total_gb": 32.0,
    "ram_free_gb": 17.8,
    "ram_usage": 44,
    "disk_c_used": 760,
    "disk_c_total": 930,
    "disk_c_pct": 82,
    "disk_e_used": 1540,
    "disk_e_total": 1860,
    "disk_e_pct": 83,
    "disk_read_str": "14.2 MB/s",
    "disk_write_str": "8.5 MB/s",
    "net_down_str": "5.4 MB/s",
    "net_up_str": "1.8 MB/s",
    "sys_temp": 34,
    "chassis_fan": 1100
}

def get_font(family, size, scale, bold=False):
    actual_size = max(8, int(size * scale))
    font_name = ("segoeuib.ttf" if bold else "segoeui.ttf") if family == "ui" else ("consolab.ttf" if bold else "consola.ttf")
    try:
        return ImageFont.truetype(font_name, actual_size)
    except Exception:
        return ImageFont.load_default()

def render_xr2_view(stats, width=1280, height=720):
    scale = height / 320.0
    is_compact = (width <= 640)

    # 1. Carregar fotografia do Ford Fiesta XR2 Mk2
    photo_path = r'e:/Gravi/SmartCoolApp/assets/fiesta_xr2_mk2.jpg'
    if os.path.exists(photo_path):
        base_img = Image.open(photo_path).convert('RGB')
        # Redimensionar mantendo proporção com corte inteligente
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

    # 2. Criar camada de transparência (Vinheta e caixas de vidro HUD)
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    d_ov = ImageDraw.Draw(overlay)

    # Gradiente / vinheta escura lateral e inferior para dar máxima legibilidade às métricas
    # Barra Superior
    bar_h = int(26 * scale)
    d_ov.rectangle([0, 0, width, bar_h], fill=(7, 10, 16, 230))
    # Faixa lateral esquerda (CPU)
    side_w = int(width * (0.32 if not is_compact else 0.38))
    my0 = bar_h + int(8 * scale)
    my1 = height - int(60 * scale)
    d_ov.rectangle([int(8*scale), my0, side_w, my1], fill=(8, 12, 18, 210), outline=(225, 29, 72, 180), width=max(1, int(1.5*scale)))

    # Faixa lateral direita (GPU)
    rx0 = width - side_w
    rx1 = width - int(8 * scale)
    d_ov.rectangle([rx0, my0, rx1, my1], fill=(8, 12, 18, 210), outline=(225, 29, 72, 180), width=max(1, int(1.5*scale)))

    # Rodapé inferior (Chassis / Storage / Fuel)
    bot_y0 = my1 + int(6 * scale)
    bot_y1 = height - int(4 * scale)
    d_ov.rectangle([int(8*scale), bot_y0, width - int(8*scale), bot_y1], fill=(7, 10, 16, 235), outline=(30, 41, 59, 200), width=1)

    # Mesclar overlay no fundo
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    f_title = get_font("ui", 11, scale, bold=True)
    f_clock = get_font("mono", 11, scale, bold=True)
    f_num_big = get_font("mono", 25, scale, bold=True)
    f_num_med = get_font("ui", 12, scale, bold=True)
    f_label = get_font("ui", 9.5, scale, bold=True)
    f_val = get_font("ui", 9.5, scale, bold=True)
    f_small = get_font("ui", 8.5, scale, bold=False)
    f_xr_badge = get_font("ui", 16, scale, bold=True)

    c_red_ford = "#e11d48"    # Vermelho clássico XR2
    c_blue_ford = "#0284c7"   # Azul clássico Ford
    c_white = "#f8fafc"
    c_slate = "#94a3b8"
    c_green = "#10b981"
    c_amber = "#f59e0b"

    # --- 1. BARRA SUPERIOR MOTORSPORT ---
    # Friso tricolor Ford Motorsport (Azul + Branco + Vermelho)
    stripe_h = max(2, int(3 * scale))
    draw.rectangle([0, 0, width, stripe_h], fill=c_red_ford)
    draw.rectangle([0, stripe_h, int(width * 0.45), stripe_h * 2], fill=c_blue_ford)

    draw.text((int(14 * scale), int(6 * scale)), "FORD FIESTA XR2 // 1.6L CVH HOT HATCH", fill=c_white, font=f_title)
    draw.text((width - int(120 * scale), int(6 * scale)), stats.get("time", "00:00"), fill=c_red_ford, font=f_clock)

    # --- 2. PAINEL ESQUERDO: ENGINE (CPU INTEL) ---
    px0 = int(8 * scale)
    px1 = side_w
    head_h = int(22 * scale)
    draw.rectangle([px0, my0, px1, my0 + head_h], fill="#131b26")
    draw.rectangle([px0, my0, px0 + int(4*scale), my0 + head_h], fill=c_red_ford)
    draw.text((px0 + int(10*scale), my0 + int(3*scale)), "ENGINE // 1.6 CVH (CPU)", fill=c_white, font=f_label)

    # Temperatura & Carga da CPU
    c_cpu_t = c_red_ford if stats.get("cpu_temp", 50) >= 75 else (c_amber if stats.get("cpu_temp", 50) >= 55 else c_green)
    draw.text((px0 + int(14*scale), my0 + int(32*scale)), f"{stats.get('cpu_temp', 50)}°C", fill=c_cpu_t, font=f_num_big)
    draw.text((px1 - int(14*scale), my0 + int(32*scale)), f"{stats.get('cpu_usage', 30)}% LOAD", fill=c_white, font=f_num_med, anchor="ra")

    # Barra de Tacómetro / RPM (0 a 7000 RPM)
    bar_x = px0 + int(14*scale)
    bar_w = (px1 - px0) - int(28*scale)
    bar_y = my0 + int(68*scale)
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + int(10*scale)], fill="#1e293b")
    u_pct = min(1.0, stats.get("cpu_usage", 30) / 100.0)
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * u_pct), bar_y + int(10*scale)], fill=c_red_ford if u_pct >= 0.75 else c_green)

    # Detalhes do motor
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

    # --- 3. PAINEL DIREITO: TRANSMISSION & TURBO (GPU RTX 4070 Ti) ---
    draw.rectangle([rx0, my0, rx1, my0 + head_h], fill="#131b26")
    draw.rectangle([rx1 - int(4*scale), my0, rx1, my0 + head_h], fill=c_red_ford)
    draw.text((rx0 + int(10*scale), my0 + int(3*scale)), f"POWERTRAIN // {stats.get('gpu_name', 'RTX')}", fill=c_white, font=f_label)

    c_gpu_t = c_red_ford if stats.get("gpu_temp", 50) >= 75 else (c_amber if stats.get("gpu_temp", 50) >= 55 else c_blue_ford)
    draw.text((rx0 + int(14*scale), my0 + int(32*scale)), f"{stats.get('gpu_temp', 50)}°C", fill=c_gpu_t, font=f_num_big)
    draw.text((rx1 - int(14*scale), my0 + int(32*scale)), f"{stats.get('gpu_usage', 40)}% LOAD", fill=c_white, font=f_num_med, anchor="ra")

    # Barra de Carga GPU
    rbar_x = rx0 + int(14*scale)
    draw.rectangle([rbar_x, bar_y, rbar_x + bar_w, bar_y + int(10*scale)], fill="#1e293b")
    gu_pct = min(1.0, stats.get("gpu_usage", 40) / 100.0)
    draw.rectangle([rbar_x, bar_y, rbar_x + int(bar_w * gu_pct), bar_y + int(10*scale)], fill=c_blue_ford)

    # Detalhes da transmissão GPU
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

    # --- 4. RODAPÉ INFERIOR: CHASSIS & STORAGE (PNEUS / DISCOS / PETROL) ---
    col_w = (width - int(16*scale) - int(90*scale)) // 3
    bx = int(14 * scale)

    # 1. Combustível / RAM
    draw.text((bx, bot_y0 + int(8*scale)), "PETROL (RAM DDR5)", fill=c_slate, font=f_small)
    draw.text((bx, bot_y0 + int(24*scale)), f"{stats.get('ram_used_gb', 14)} / {stats.get('ram_total_gb', 32)} GB ({stats.get('ram_usage', 44)}%)", fill=c_green, font=f_val)

    # 2. Eixo Frontal / NVMe C:
    bx += col_w
    draw.text((bx, bot_y0 + int(8*scale)), "FRONT AXLE (NVMe C:)", fill=c_slate, font=f_small)
    draw.text((bx, bot_y0 + int(24*scale)), f"{stats.get('disk_c_used', 700)} / {stats.get('disk_c_total', 930)} GB ({stats.get('disk_c_pct', 80)}%)", fill=c_white, font=f_val)

    # 3. Eixo Traseiro / NVMe E: & Rede
    bx += col_w
    draw.text((bx, bot_y0 + int(8*scale)), "REAR AXLE (NVMe E:)", fill=c_slate, font=f_small)
    draw.text((bx, bot_y0 + int(24*scale)), f"{stats.get('disk_e_pct', 80)}% | NET: ↓{stats.get('net_down_str', '0KB')} ↑{stats.get('net_up_str', '0KB')}", fill=c_blue_ford, font=f_val)

    # Emblema clássico XR2 no canto inferior direito
    badge_x = width - int(95 * scale)
    badge_y = bot_y0 + int(6 * scale)
    badge_w = int(80 * scale)
    badge_h = int(38 * scale)
    draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill="#180408", outline=c_red_ford, width=2)
    draw.text((badge_x + badge_w // 2, badge_y + badge_h // 2 - int(2*scale)), "XR2", fill=c_red_ford, font=f_xr_badge, anchor="mm")

    return img

print("Rendering XR2 theme preview (1280x720)...")
img_preview = render_xr2_view(stats, 1280, 720)
img_preview.save(r'e:/Gravi/SmartCoolApp/assets/preview_theme_xr2.png')

print("Rendering XR2 USB preview (480x320)...")
img_usb = render_xr2_view(stats, 480, 320)
img_usb.save(r'e:/Gravi/SmartCoolApp/assets/preview_theme_xr2_usb.png')

print("XR2 Mk2 theme rendered successfully!")
