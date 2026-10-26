"""
Test script to generate and preview the 3 new automotive and aviation themes.
"""
import os
import sys
import math
import time
from PIL import Image, ImageDraw, ImageFont

# Sample telemetry data
stats = {
    "time": "19:45:00",
    "uptime": "3h 24m",
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

def draw_needle(draw, cx, cy, radius, angle_deg, color="#ff3300", width=3, cap_r=8):
    rad = math.radians(angle_deg)
    tx = cx + radius * math.cos(rad)
    ty = cy + radius * math.sin(rad)
    bx = cx - (radius * 0.15) * math.cos(rad)
    by = cy - (radius * 0.15) * math.sin(rad)
    draw.line([(bx, by), (tx, ty)], fill=color, width=width)
    draw.ellipse([cx - cap_r, cy - cap_r, cx + cap_r, cy + cap_r], fill="#1e293b", outline="#cbd5e1", width=2)
    draw.ellipse([cx - cap_r//2, cy - cap_r//2, cx + cap_r//2, cy + cap_r//2], fill=color)

# ==============================================================================
# 1. THEME: SPEEDOMETER (Painel de Instrumentos com Velocímetros)
# ==============================================================================
def render_speedometer_view(stats, width=1280, height=720):
    scale = height / 320.0
    img = Image.new("RGB", (width, height), "#06090e")
    draw = ImageDraw.Draw(img)

    f_title = get_font("ui", 10.5, scale, bold=True)
    f_clock = get_font("mono", 11, scale, bold=True)
    f_num_big = get_font("ui", 26, scale, bold=True)
    f_label = get_font("ui", 9, scale, bold=True)
    f_small = get_font("ui", 8.5, scale, bold=False)
    f_mini = get_font("ui", 7.5, scale, bold=False)

    step = int(16 * scale)
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill="#0a0e17", width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill="#0a0e17", width=1)

    bar_h = int(24 * scale)
    draw.rectangle([0, 0, width, bar_h], fill="#0c121e", outline="#1e293b", width=1)
    draw.text((int(14 * scale), int(4 * scale)), "GT SPORTS // INSTRUMENT CLUSTER", fill="#38bdf8", font=f_title)
    draw.text((width - int(110 * scale), int(4 * scale)), stats["time"], fill="#f8fafc", font=f_clock)

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
    cpu_ang = 135 + (stats["cpu_usage"] / 100.0) * 270
    needle_col = "#ef4444" if stats["cpu_temp"] >= 75 else "#10b981"
    draw_needle(draw, cx1, cy, dial_r - int(12 * scale), cpu_ang, color=needle_col, width=max(2, int(2.5 * scale)), cap_r=int(12 * scale))

    c_cpu_t = "#ef4444" if stats["cpu_temp"] >= 75 else ("#f59e0b" if stats["cpu_temp"] >= 55 else "#10b981")
    draw.text((cx1, cy + int(24 * scale)), f"{stats['cpu_temp']}°C", fill=c_cpu_t, font=f_num_big, anchor="mm")
    draw.text((cx1, cy + int(48 * scale)), f"{stats['cpu_clock']} GHz | {stats['cpu_fan']} RPM", fill="#cbd5e1", font=f_small, anchor="mm")

    draw_gauge_bezel(cx2, cy, dial_r, "SPEEDOMETER", "GPU RTX 4070 Ti")
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

    gpu_ang = 135 + (stats["gpu_usage"] / 100.0) * 270
    draw_needle(draw, cx2, cy, dial_r - int(12 * scale), gpu_ang, color="#38bdf8", width=max(2, int(2.5 * scale)), cap_r=int(12 * scale))

    c_gpu_t = "#ef4444" if stats["gpu_temp"] >= 75 else ("#f59e0b" if stats["gpu_temp"] >= 55 else "#38bdf8")
    draw.text((cx2, cy + int(24 * scale)), f"{stats['gpu_temp']}°C", fill=c_gpu_t, font=f_num_big, anchor="mm")
    draw.text((cx2, cy + int(48 * scale)), f"VRAM: {stats['gpu_vram_used']}/{stats['gpu_vram_total']} GB", fill="#cbd5e1", font=f_small, anchor="mm")

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

    draw.text((mx0 + int(12*scale), aux_y), "TURBO BOOST / POWER", fill="#94a3b8", font=f_mini)
    draw.text((mx1 - int(12*scale), aux_y), f"{stats['gpu_power']} W", fill="#38bdf8", font=f_small, anchor="ra")
    draw.rectangle([mx0 + int(12*scale), aux_y + int(14*scale), mx1 - int(12*scale), aux_y + int(20*scale)], fill="#1e293b")
    boost_pct = min(1.0, stats["gpu_power"] / 285.0)
    draw.rectangle([mx0 + int(12*scale), aux_y + int(14*scale), mx0 + int(12*scale) + int(aux_w * boost_pct), aux_y + int(20*scale)], fill="#0284c7")

    fuel_y = aux_y + int(30 * scale)
    draw.text((mx0 + int(12*scale), fuel_y), "FUEL / DDR5 RAM", fill="#94a3b8", font=f_mini)
    draw.text((mx1 - int(12*scale), fuel_y), f"{stats['ram_usage']}%", fill="#10b981", font=f_small, anchor="ra")
    draw.rectangle([mx0 + int(12*scale), fuel_y + int(14*scale), mx1 - int(12*scale), fuel_y + int(20*scale)], fill="#1e293b")
    draw.rectangle([mx0 + int(12*scale), fuel_y + int(14*scale), mx0 + int(12*scale) + int(aux_w * (stats['ram_usage']/100.0)), fuel_y + int(20*scale)], fill="#10b981")

    oil_y = fuel_y + int(30 * scale)
    draw.text((mx0 + int(12*scale), oil_y), "OIL / SYS TEMP", fill="#94a3b8", font=f_mini)
    draw.text((mx1 - int(12*scale), oil_y), f"{stats['sys_temp']}°C (OK)", fill="#38bdf8", font=f_small, anchor="ra")

    odo_y = oil_y + int(24 * scale)
    draw.rectangle([mx0 + int(8*scale), odo_y, mx1 - int(8*scale), my1 - int(8*scale)], fill="#05080f", outline="#1e293b", width=1)
    draw.text(((mx0+mx1)//2, odo_y + int(10*scale)), "ODOMETER (STORAGE)", fill="#64748b", font=f_mini, anchor="mm")
    draw.text(((mx0+mx1)//2, odo_y + int(24*scale)), f"NVMe C: {stats['disk_c_pct']}% | E: {stats['disk_e_pct']}%", fill="#f8fafc", font=f_small, anchor="mm")
    draw.text(((mx0+mx1)//2, odo_y + int(38*scale)), f"TRIP: {stats['uptime']}", fill="#38bdf8", font=f_mini, anchor="mm")
    draw.text(((mx0+mx1)//2, odo_y + int(50*scale)), f"NET: ↓{stats['net_down_str']}  ↑{stats['net_up_str']}", fill="#10b981", font=f_mini, anchor="mm")

    lamp_y = int(height * 0.93)
    lamp_cols = [
        ("CHECK", "#ef4444" if stats["cpu_temp"] >= 75 else "#334155"),
        ("OIL", "#f59e0b" if stats["sys_temp"] >= 50 else "#334155"),
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

# ==============================================================================
# 2. THEME: AIRPLANE_COCKPIT (Cockpit de Caça Militar / Glass HUD)
# ==============================================================================
def render_airplane_cockpit_view(stats, width=1280, height=720):
    scale = height / 320.0
    img = Image.new("RGB", (width, height), "#02070a")
    draw = ImageDraw.Draw(img)

    f_title = get_font("mono", 11, scale, bold=True)
    f_hud = get_font("mono", 10, scale, bold=True)
    f_hud_big = get_font("mono", 24, scale, bold=True)
    f_hud_med = get_font("mono", 13, scale, bold=True)
    f_hud_small = get_font("mono", 8.5, scale, bold=False)

    c_hud = "#00ff66"      # HUD Green
    c_amber = "#ffb700"    # Tactical Amber
    c_cyan = "#00e5ff"     # Avionics Cyan
    c_dark_green = "#003b17"
    c_grid = "#041512"

    # Grelha de radar tático
    step = int(32 * scale)
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=c_grid, width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=c_grid, width=1)

    # 1. Annunciator Panel Superior (Painel de Alarmes de Voo)
    annun_h = int(24 * scale)
    draw.rectangle([0, 0, width, annun_h], fill="#03120f", outline=c_dark_green, width=1)

    annun_boxes = [
        ("MASTER WARN", "#ef4444" if (stats["cpu_temp"]>=75 or stats["gpu_temp"]>=75) else "#1e293b"),
        ("FIRE DETECT", "#ef4444" if stats["gpu_hotspot"]>=80 else "#1e293b"),
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

    draw.text((width - int(120 * scale), annun_h // 2), f"ZULU {stats['time']}", fill=c_cyan, font=f_title, anchor="lm")

    # 2. PFD CENTRAL: HORIZONTE ARTIFICIAL (Attitude Indicator)
    pfd_w = int(width * 0.38)
    pfd_cx = width // 2
    pfd_cy = int(height * 0.50)
    pfd_r = int(100 * scale)

    # Círculo do horizonte
    draw.ellipse([pfd_cx - pfd_r, pfd_cy - pfd_r, pfd_cx + pfd_r, pfd_cy + pfd_r], fill="#02140e", outline=c_hud, width=2)

    # Linhas de Pitch Ladder (+20, +10, 0, -10, -20)
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

    # Retículo da Aeronave (Aircraft Boresight -o-)
    draw.line([(pfd_cx - int(25*scale), pfd_cy), (pfd_cx - int(8*scale), pfd_cy)], fill=c_amber, width=3)
    draw.line([(pfd_cx + int(8*scale), pfd_cy), (pfd_cx + int(25*scale), pfd_cy)], fill=c_amber, width=3)
    draw.ellipse([pfd_cx - int(5*scale), pfd_cy - int(5*scale), pfd_cx + int(5*scale), pfd_cy + int(5*scale)], outline=c_amber, width=2)

    # Informações em cima do horizonte
    draw.text((pfd_cx, pfd_cy - int(70 * scale)), f"MACH 0.{stats['cpu_usage']:02d}", fill=c_cyan, font=f_hud_med, anchor="mm")
    draw.text((pfd_cx, pfd_cy + int(70 * scale)), f"ALTITUDE FL{stats['gpu_usage']:02d}", fill=c_hud, font=f_hud_med, anchor="mm")

    # 3. FITA LATERAL ESQUERDA: AIRSPEED TAPE (CPU & CLOCK)
    tape_w = int(width * 0.26)
    lx0 = int(14 * scale)
    lx1 = lx0 + tape_w
    ty0 = int(36 * scale)
    ty1 = height - int(20 * scale)
    draw.rectangle([lx0, ty0, lx1, ty1], fill="#020d09", outline=c_hud, width=1)

    draw.rectangle([lx0, ty0, lx1, ty0 + int(24*scale)], fill="#041a12")
    draw.text(((lx0+lx1)//2, ty0 + int(12*scale)), "AIRSPEED // ENGINE 1 (CPU)", fill=c_hud, font=f_hud, anchor="mm")

    # Leitura gigante
    c_c_temp = "#ef4444" if stats["cpu_temp"] >= 75 else c_hud
    draw.text(((lx0+lx1)//2, ty0 + int(60*scale)), f"{stats['cpu_temp']}°C", fill=c_c_temp, font=f_hud_big, anchor="mm")
    draw.text(((lx0+lx1)//2, ty0 + int(88*scale)), f"THRUST: {stats['cpu_usage']}% LOAD", fill=c_amber, font=f_hud_med, anchor="mm")

    # Barra gráfica de impulso
    bar_x = lx0 + int(16 * scale)
    bar_w = tape_w - int(32 * scale)
    bar_y = ty0 + int(106 * scale)
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + int(12*scale)], fill="#041a12", outline=c_dark_green)
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * (stats['cpu_usage']/100.0)), bar_y + int(12*scale)], fill=c_hud)

    # Detalhes do motor CPU
    det_y = bar_y + int(24 * scale)
    cpu_lines = [
        f"CORE CLOCK : {stats['cpu_clock']} GHz",
        f"TURBINE N1 : {stats['cpu_fan']} RPM",
        f"CORES/THR  : {stats['cpu_cores']}",
        f"HYDR SYS   : {stats['sys_temp']}°C NOMINAL",
        f"RAD FAN    : {stats['chassis_fan']} RPM",
        f"TIME STINT : {stats['uptime']}"
    ]
    for j, line in enumerate(cpu_lines):
        draw.text((bar_x, det_y + j * int(18*scale)), line, fill=c_cyan if "CLOCK" in line else c_hud, font=f_hud_small)

    # 4. FITA LATERAL DIREITA: ALTITUDE TAPE (GPU & VRAM)
    rx1 = width - int(14 * scale)
    rx0 = rx1 - tape_w
    draw.rectangle([rx0, ty0, rx1, ty1], fill="#020d09", outline=c_hud, width=1)

    draw.rectangle([rx0, ty0, rx1, ty0 + int(24*scale)], fill="#041a12")
    draw.text(((rx0+rx1)//2, ty0 + int(12*scale)), "ALTITUDE // ENGINE 2 (GPU)", fill=c_hud, font=f_hud, anchor="mm")

    c_g_temp = "#ef4444" if stats["gpu_temp"] >= 75 else c_hud
    draw.text(((rx0+rx1)//2, ty0 + int(60*scale)), f"{stats['gpu_temp']}°C", fill=c_g_temp, font=f_hud_big, anchor="mm")
    draw.text(((rx0+rx1)//2, ty0 + int(88*scale)), f"THRUST: {stats['gpu_usage']}% ({stats['gpu_name']})", fill=c_cyan, font=f_hud_small, anchor="mm")

    rbar_x = rx0 + int(16 * scale)
    draw.rectangle([rbar_x, bar_y, rbar_x + bar_w, bar_y + int(12*scale)], fill="#041a12", outline=c_dark_green)
    draw.rectangle([rbar_x, bar_y, rbar_x + int(bar_w * (stats['gpu_usage']/100.0)), bar_y + int(12*scale)], fill=c_cyan)

    gpu_lines = [
        f"GPU CLOCK  : {stats['gpu_clock']} MHz",
        f"HOTSPOT    : {stats['gpu_hotspot']}°C",
        f"VRAM USED  : {stats['gpu_vram_used']} / {stats['gpu_vram_total']} GB",
        f"POWER DRAW : {stats['gpu_power']} WATTS",
        f"GPU COOLER : {stats['gpu_fan']} RPM",
        f"MEMORY BUS : {stats['gpu_mem_clock']} GHz"
    ]
    for j, line in enumerate(gpu_lines):
        draw.text((rbar_x, det_y + j * int(18*scale)), line, fill=c_amber if "HOTSPOT" in line else c_hud, font=f_hud_small)

    # 5. BOTTOM HSI / COMPASS & NAV DATA
    nav_y = pfd_cy + pfd_r + int(12 * scale)
    nav_w = int(width * 0.40)
    nx0 = (width - nav_w) // 2
    nx1 = nx0 + nav_w
    draw.rectangle([nx0, nav_y, nx1, height - int(20*scale)], fill="#02110c", outline=c_hud, width=1)

    draw.text(((nx0+nx1)//2, nav_y + int(12*scale)), "NAVIGATION // AVIONICS SUBSYSTEMS", fill=c_cyan, font=f_hud_small, anchor="mm")
    draw.text((nx0 + int(14*scale), nav_y + int(28*scale)), f"HDG 072° | FUEL: RAM {stats['ram_used_gb']}/{stats['ram_total_gb']} GB ({stats['ram_usage']}%)", fill=c_hud, font=f_hud_small)
    draw.text((nx0 + int(14*scale), nav_y + int(44*scale)), f"WPT1: NVMe C: {stats['disk_c_pct']}%  |  WPT2: NVMe E: {stats['disk_e_pct']}%", fill=c_amber, font=f_hud_small)
    draw.text((nx0 + int(14*scale), nav_y + int(60*scale)), f"DATALINK: ↓ {stats['net_down_str']}  ↑ {stats['net_up_str']}", fill=c_hud, font=f_hud_small)

    return img

# ==============================================================================
# 3. THEME: GT_COCKPIT (Cockpit de Carro GT / MoTeC Racing Dashboard)
# ==============================================================================
def render_gt_cockpit_view(stats, width=1280, height=720):
    scale = height / 320.0
    img = Image.new("RGB", (width, height), "#05070a")
    draw = ImageDraw.Draw(img)

    f_title = get_font("ui", 10.5, scale, bold=True)
    f_num_giant = get_font("mono", 34, scale, bold=True)
    f_num_big = get_font("mono", 24, scale, bold=True)
    f_val = get_font("ui", 11, scale, bold=True)
    f_lbl = get_font("ui", 9, scale, bold=False)
    f_small = get_font("ui", 8, scale, bold=False)

    # 1. SHIFT LIGHTS SEQUENCIAIS DE CORRIDA (16 LEDs no Topo)
    led_h = int(22 * scale)
    draw.rectangle([0, 0, width, led_h], fill="#0a0d14", outline="#1e293b", width=1)

    num_leds = 16
    led_w = (width - int(40 * scale)) / float(num_leds)
    # A intensidade acende com a carga da CPU/GPU
    active_leds = int((stats["cpu_usage"] / 100.0) * num_leds)

    for i in range(num_leds):
        lx = int(20 * scale) + i * led_w
        ly = int(4 * scale)
        lw = int(led_w - 4 * scale)
        lh = int(led_h - 8 * scale)

        if i < 5:
            base_col, on_col = "#063d1e", "#10b981"  # Verde
        elif i < 10:
            base_col, on_col = "#3d2f06", "#f59e0b"  # Amarelo
        elif i < 14:
            base_col, on_col = "#450a0a", "#ef4444"  # Vermelho
        else:
            base_col, on_col = "#2e1065", "#a855f7"  # Roxo / Shift

        col = on_col if i <= active_leds else base_col
        draw.rectangle([lx, ly, lx + lw, ly + lh], fill=col, outline="#1e293b", width=1)

    # 2. BLOCO CENTRAL DE VELOCIDADE E MARCHA
    mid_w = int(width * 0.30)
    mx0 = (width - mid_w) // 2
    mx1 = mx0 + mid_w
    my0 = led_h + int(10 * scale)
    my1 = my0 + int(120 * scale)
    draw.rectangle([mx0, my0, mx1, my1], fill="#0b0f19", outline="#1e293b", width=2)

    # Caixa da Marcha
    gear_w = int(60 * scale)
    draw.rectangle([mx0 + int(12*scale), my0 + int(12*scale), mx0 + int(12*scale) + gear_w, my1 - int(12*scale)], fill="#1e1b4b", outline="#6366f1", width=2)
    draw.text((mx0 + int(12*scale) + gear_w//2, my0 + int(20*scale)), "GEAR", fill="#a5b4fc", font=f_small, anchor="mm")
    draw.text((mx0 + int(12*scale) + gear_w//2, my0 + int(60*scale)), "6", fill="#ffffff", font=f_num_giant, anchor="mm")

    # Velocidade Digital (KM/H)
    speed_x = mx0 + int(12*scale) + gear_w + int(16*scale)
    draw.text((speed_x, my0 + int(24*scale)), "SPEED / GPU CLOCK", fill="#94a3b8", font=f_small)
    draw.text((speed_x, my0 + int(56*scale)), "284", fill="#f8fafc", font=f_num_giant)
    draw.text((speed_x + int(100*scale), my0 + int(68*scale)), "KM/H", fill="#ef4444", font=f_val)
    draw.text((speed_x, my0 + int(96*scale)), f"DELTA: -0.34s  |  LAP: {stats['time']}", fill="#10b981", font=f_small)

    # 3. PAINEL ESQUERDO: ENGINE // CPU TELEMETRY
    card_w = (width - mid_w - int(48 * scale)) // 2
    px0 = int(14 * scale)
    px1 = px0 + card_w
    draw.rectangle([px0, my0, px1, my1], fill="#0b0f19", outline="#1e293b", width=1)

    draw.rectangle([px0, my0, px1, my0 + int(22*scale)], fill="#111827")
    draw.text((px0 + int(10*scale), my0 + int(11*scale)), "ENGINE // CPU INTEL i7", fill="#10b981", font=f_title, anchor="lm")

    c_cpu_t = "#ef4444" if stats["cpu_temp"] >= 75 else "#10b981"
    draw.text((px0 + int(14*scale), my0 + int(58*scale)), f"{stats['cpu_temp']}°C", fill=c_cpu_t, font=f_num_big)
    draw.text((px1 - int(14*scale), my0 + int(58*scale)), f"{stats['cpu_usage']}%", fill="#f8fafc", font=f_num_big, anchor="ra")

    draw.text((px0 + int(14*scale), my0 + int(94*scale)), f"FREQ: {stats['cpu_clock']} GHz  |  FAN: {stats['cpu_fan']} RPM", fill="#94a3b8", font=f_small)

    # 4. PAINEL DIREITO: POWERTRAIN // GPU TELEMETRY
    gx0 = mx1 + int(12 * scale)
    gx1 = gx0 + card_w
    draw.rectangle([gx0, my0, gx1, my1], fill="#0b0f19", outline="#1e293b", width=1)

    draw.rectangle([gx0, my0, gx0 + card_w, my0 + int(22*scale)], fill="#111827")
    draw.text((gx0 + int(10*scale), my0 + int(11*scale)), "POWERTRAIN // RTX 4070 Ti", fill="#38bdf8", font=f_title, anchor="lm")

    c_gpu_t = "#ef4444" if stats["gpu_temp"] >= 75 else "#38bdf8"
    draw.text((gx0 + int(14*scale), my0 + int(58*scale)), f"{stats['gpu_temp']}°C", fill=c_gpu_t, font=f_num_big)
    draw.text((gx1 - int(14*scale), my0 + int(58*scale)), f"{stats['gpu_usage']}%", fill="#f8fafc", font=f_num_big, anchor="ra")

    draw.text((gx0 + int(14*scale), my0 + int(94*scale)), f"VRAM: {stats['gpu_vram_used']}/{stats['gpu_vram_total']} GB | {stats['gpu_power']} W", fill="#94a3b8", font=f_small)

    # 5. ZONA INFERIOR: TELEMETRIA DE PNEUS / DRIVES (FL, FR, RL, RR)
    bot_y = my1 + int(10 * scale)
    bot_h = height - bot_y - int(12 * scale)
    draw.rectangle([px0, bot_y, gx1, bot_y + bot_h], fill="#080c14", outline="#1e293b", width=1)

    draw.rectangle([px0, bot_y, gx1, bot_y + int(20*scale)], fill="#0f1523")
    draw.text((px0 + int(10*scale), bot_y + int(10*scale)), "TYRES & CHASSIS TELEMETRY // STORAGE & RAM", fill="#94a3b8", font=f_small, anchor="lm")

    # 4 Caixas simulando os 4 Pneus de corrida (FL, FR, RL, RR)
    tyre_box_w = (gx1 - px0 - int(40 * scale)) // 4
    tyres = [
        ("FL [NVMe C:]", f"{stats['disk_c_pct']}% USED", f"{stats['disk_c_used']} GB", "#10b981"),
        ("FR [NVMe E:]", f"{stats['disk_e_pct']}% USED", f"{stats['disk_e_used']} GB", "#10b981"),
        ("RL [RAM CH-A]", f"{stats['ram_usage']}% USED", f"{stats['ram_used_gb']} GB", "#38bdf8"),
        ("RR [SYS CH-B]", f"{stats['sys_temp']}°C OPTIMAL", f"NET: {stats['net_down_str']}", "#f59e0b")
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

print("Rendering previews...")
img1 = render_speedometer_view(stats, 1280, 720)
img1.save(r'e:/Gravi/SmartCoolApp/assets/preview_theme_speedometer.png')
print("Speedometer OK.")

img2 = render_airplane_cockpit_view(stats, 1280, 720)
img2.save(r'e:/Gravi/SmartCoolApp/assets/preview_theme_airplane.png')
print("Airplane Cockpit OK.")

img3 = render_gt_cockpit_view(stats, 1280, 720)
img3.save(r'e:/Gravi/SmartCoolApp/assets/preview_theme_gt.png')
print("GT Cockpit OK.")
