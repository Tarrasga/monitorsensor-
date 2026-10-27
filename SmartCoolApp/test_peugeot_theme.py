import os
import sys
from PIL import Image, ImageDraw, ImageFont

def get_font(font_type, size_pt, scale, bold=False):
    actual_size = max(8, int(size_pt * scale))
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

def render_peugeot_508_view(stats, width=1280, height=720, assets_dir="assets"):
    scale = height / 320.0
    is_compact = (width <= 640)

    # 1. Carregar Wallpaper do Peugeot 508 SW i-Cockpit
    bg_path = os.path.join(assets_dir, "peugeot_508_sw.jpg")
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

    f_title = get_font("ui", 10.5, scale, bold=True)
    f_clock = get_font("mono", 11, scale, bold=True)
    f_speed = get_font("mono", 28, scale, bold=True)
    f_num_med = get_font("ui", 12, scale, bold=True)
    f_label = get_font("ui", 9.5, scale, bold=True)
    f_val = get_font("ui", 9.5, scale, bold=True)
    f_small = get_font("ui", 8.5, scale, bold=False)
    f_badge = get_font("ui", 11, scale, bold=True)
    f_mode = get_font("ui", 9, scale, bold=True)

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

if __name__ == "__main__":
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    mock_stats = {
        "time": "22:05",
        "cpu_temp": 47,
        "cpu_usage": 35,
        "cpu_clock": 4.80,
        "cpu_fan": 1280,
        "gpu_temp": 52,
        "gpu_usage": 42,
        "gpu_mem_used_gb": 4.8,
        "gpu_mem_total_gb": 12.0,
        "gpu_fan": 1350,
        "ram_usage": 46,
        "ram_used_gb": 14.8,
        "sys_temp": 38,
        "disk_c_free_gb": 218,
        "disk_e_free_gb": 845,
        "net_down_str": "8.4 MB/s",
        "net_up_str": "1.5 MB/s",
    }

    img_hd = render_peugeot_508_view(mock_stats, 1280, 720, assets_dir)
    img_hd.save(os.path.join(assets_dir, "preview_theme_peugeot_508.png"))
    img_usb = render_peugeot_508_view(mock_stats, 480, 320, assets_dir)
    img_usb.save(os.path.join(assets_dir, "preview_theme_peugeot_508_usb.png"))
    print("[OK] Peugeot 508 SW Previews generated successfully.")
