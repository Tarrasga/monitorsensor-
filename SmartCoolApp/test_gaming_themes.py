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

def render_cs2_view(stats, width=1280, height=720, assets_dir="assets"):
    scale = height / 320.0
    is_compact = (width <= 640)

    # 1. Carregar Wallpaper CS2
    bg_path = os.path.join(assets_dir, "cs2_wallpaper.jpg")
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

    f_title = get_font("ui", 11, scale, bold=True)
    f_clock = get_font("mono", 11, scale, bold=True)
    f_num_big = get_font("mono", 25, scale, bold=True)
    f_num_med = get_font("ui", 12, scale, bold=True)
    f_label = get_font("ui", 9.5, scale, bold=True)
    f_val = get_font("ui", 9.5, scale, bold=True)
    f_small = get_font("ui", 8.5, scale, bold=False)
    f_badge = get_font("ui", 13, scale, bold=True)

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
    clock_str = f"{stats.get('cpu_clock', 4.8):.2f} GHz" if stats.get("cpu_clock", 0) > 0 else "BOOST ACTIVE"
    draw.text((px0 + int(14*scale), line2_y), f"CLOCK: {clock_str}", fill=c_ct_blue, font=f_val)

    line3_y = line2_y + int(22*scale)
    draw.text((px0 + int(14*scale), line3_y), f"FAN: {stats.get('cpu_fan', 0)} RPM", fill=c_slate, font=f_val)

    # Barra Tática de Carga CPU
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

    # Barra Tática de Carga GPU
    draw.rectangle([rx0 + int(14*scale), bar_y, rx0 + int(14*scale) + bar_w, bar_y + int(10*scale)], fill="#231a10", outline="#334155", width=1)
    fill_gw = int(bar_w * (min(100, max(0, stats.get("gpu_usage", 0))) / 100.0))
    if fill_gw > 0:
        draw.rectangle([rx0 + int(14*scale), bar_y, rx0 + int(14*scale) + fill_gw, bar_y + int(10*scale)], fill=c_cs2_orange)

    # Barra Inferior: Round Stats / net_graph
    bot_y = bot_y0
    bot_h = bot_y1 - bot_y0
    col_w = (width - int(16*scale)) // (3 if not is_compact else 2)

    # 1. RAM / Kevlar & Helmet
    draw.text((int(16*scale), bot_y + int(8*scale)), f"ARMOR // RAM: {stats.get('ram_usage', 0)}% ({stats.get('ram_used_gb', 0)} GB)", fill=c_white, font=f_val)
    draw.text((int(16*scale), bot_y + int(26*scale)), f"SYS TEMP: {stats.get('sys_temp', 38)}°C", fill=c_slate, font=f_small)

    # 2. SSD Storage
    if not is_compact:
        c2_x = int(16*scale) + col_w
        draw.text((c2_x, bot_y + int(8*scale)), f"AMMO DEPOT: C: {stats.get('disk_c_free_gb', 0)} GB LIVRE", fill=c_ct_blue, font=f_val)
        draw.text((c2_x, bot_y + int(26*scale)), f"DRIVE E: {stats.get('disk_e_free_gb', 0)} GB LIVRE", fill=c_slate, font=f_small)

    # 3. net_graph 1 / Conexão
    c3_x = width - int(180*scale)
    draw.text((c3_x, bot_y + int(8*scale)), f"DL: {stats.get('net_down_str', '0.0 KB/s')}", fill=c_green, font=f_val)
    draw.text((c3_x, bot_y + int(26*scale)), f"UL: {stats.get('net_up_str', '0.0 KB/s')}", fill=c_cs2_orange, font=f_small)

    # Badge Central CS2
    badge_w = int(100 * scale)
    badge_h = int(28 * scale)
    badge_x = (width - badge_w) // 2
    badge_y = my1 - int(24 * scale)
    draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill="#0f172a", outline=c_cs2_orange, width=2)
    draw.text((badge_x + badge_w // 2, badge_y + badge_h // 2 - int(2*scale)), "CS2 HUD", fill=c_white, font=f_badge, anchor="mm")

    return img

def render_pubg_view(stats, width=1280, height=720, assets_dir="assets"):
    scale = height / 320.0
    is_compact = (width <= 640)

    # 1. Carregar Wallpaper PUBG
    bg_path = os.path.join(assets_dir, "pubg_wallpaper.jpg")
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

    f_title = get_font("ui", 11, scale, bold=True)
    f_clock = get_font("mono", 11, scale, bold=True)
    f_num_big = get_font("mono", 25, scale, bold=True)
    f_num_med = get_font("ui", 12, scale, bold=True)
    f_label = get_font("ui", 9.5, scale, bold=True)
    f_val = get_font("ui", 9.5, scale, bold=True)
    f_small = get_font("ui", 8.5, scale, bold=False)
    f_badge = get_font("ui", 10.5, scale, bold=True)

    c_hazard_yellow = "#facc15"
    c_airdrop_red = "#ef4444"
    c_white = "#f8fafc"
    c_slate = "#94a3b8"
    c_green = "#22c55e"
    c_blue = "#38bdf8"

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
    clock_str = f"{stats.get('cpu_clock', 4.8):.2f} GHz" if stats.get("cpu_clock", 0) > 0 else "BOOST ACTIVE"
    draw.text((px0 + int(14*scale), line2_y), f"BOOST: {clock_str}", fill=c_hazard_yellow, font=f_val)

    line3_y = line2_y + int(22*scale)
    draw.text((px0 + int(14*scale), line3_y), f"LVL 3 HELMET FAN: {stats.get('cpu_fan', 0)} RPM", fill=c_slate, font=f_val)

    # Barra de Vida / Load CPU
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

    # Barra de Carga GPU
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

    # Badge Central PUBG Chicken Dinner
    badge_w = int(210 * scale)
    badge_h = int(28 * scale)
    badge_x = (width - badge_w) // 2
    badge_y = my1 - int(24 * scale)
    draw.rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], fill="#1c1917", outline=c_hazard_yellow, width=2)
    draw.text((badge_x + badge_w // 2, badge_y + badge_h // 2 - int(1*scale)), "★ WINNER CHICKEN DINNER ★", fill=c_hazard_yellow, font=f_badge, anchor="mm")

    return img

if __name__ == "__main__":
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    mock_stats = {
        "time": "21:30",
        "cpu_temp": 49,
        "cpu_usage": 32,
        "cpu_clock": 4.80,
        "cpu_fan": 1240,
        "gpu_temp": 54,
        "gpu_usage": 45,
        "gpu_mem_used_gb": 4.6,
        "gpu_mem_total_gb": 12.0,
        "gpu_fan": 1380,
        "ram_usage": 48,
        "ram_used_gb": 15.4,
        "sys_temp": 39,
        "disk_c_free_gb": 218,
        "disk_e_free_gb": 845,
        "net_down_str": "6.8 MB/s",
        "net_up_str": "1.2 MB/s",
    }

    # Render CS2 (HD & USB)
    img_cs2_hd = render_cs2_view(mock_stats, 1280, 720, assets_dir)
    img_cs2_hd.save(os.path.join(assets_dir, "preview_theme_cs2.png"))
    img_cs2_usb = render_cs2_view(mock_stats, 480, 320, assets_dir)
    img_cs2_usb.save(os.path.join(assets_dir, "preview_theme_cs2_usb.png"))
    print("[OK] CS2 Previews generated successfully.")

    # Render PUBG (HD & USB)
    img_pubg_hd = render_pubg_view(mock_stats, 1280, 720, assets_dir)
    img_pubg_hd.save(os.path.join(assets_dir, "preview_theme_pubg.png"))
    img_pubg_usb = render_pubg_view(mock_stats, 480, 320, assets_dir)
    img_pubg_usb.save(os.path.join(assets_dir, "preview_theme_pubg_usb.png"))
    print("[OK] PUBG Previews generated successfully.")
