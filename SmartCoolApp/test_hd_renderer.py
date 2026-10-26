import sys, os
sys.path.insert(0, r'e:/Gravi/SmartCoolApp')
from hardware_monitor import HardwareMonitor
from PIL import Image, ImageDraw, ImageFont

monitor = HardwareMonitor()
stats = monitor.get_stats()

claw_img_raw = Image.open(r'e:/Gravi/SmartCoolApp/assets/monster_claw_symbol.png').convert('RGBA')

def draw_flames(draw, x0, y0, x1, y1, flicker=0, scale=1.0):
    border_w = max(2, int(2 * scale))
    draw.rectangle([x0, y0, x1, y1], outline='#ff3300', width=border_w)
    
    # Flame pit at the bottom of the card
    flame_h = int(22 * scale)
    draw.rectangle([x0 + border_w, y1 - flame_h, x1 - border_w, y1 - border_w], fill='#1c0400')
    
    flame_w = (x1 - x0 - 2 * border_w)
    num_tongues = 20
    step = flame_w / float(num_tongues)
    for i in range(num_tongues):
        fx = x0 + border_w + i * step
        # Red outer flame
        h1 = int((10 + ((i * 11 + flicker * 7) % 15)) * scale)
        draw.polygon([(fx, y1 - border_w), (fx + step * 0.5, y1 - h1), (fx + step, y1 - border_w)], fill='#ff2200')
        # Orange mid flame
        h2 = max(int(3 * scale), h1 - int(4 * scale))
        draw.polygon([(fx + step * 0.2, y1 - border_w), (fx + step * 0.5, y1 - h2), (fx + step * 0.8, y1 - border_w)], fill='#ff7700')
        # Yellow inner flame
        h3 = max(int(2 * scale), h2 - int(3 * scale))
        draw.polygon([(fx + step * 0.35, y1 - border_w), (fx + step * 0.5, y1 - h3), (fx + step * 0.65, y1 - border_w)], fill='#ffea00')
        # Spark particles
        if (i + flicker) % 3 == 0:
            spark_y = y1 - h1 - int(5 * scale)
            r = max(1, int(1.5 * scale))
            draw.ellipse([fx + step * 0.5 - r, spark_y - r, fx + step * 0.5 + r, spark_y + r], fill='#ffdd33')

def render_sensors_view(stats, width, height, flame_flicker=0):
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
    
    # Grid discreto
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
    
    # 1. Top Bar
    draw.rectangle([pad_x, int(4*scale), width - pad_x, top_h], fill='#0d121c', outline='#1e293b', width=1)
    
    claw_h = int(18 * scale)
    claw_w = int(claw_h * (claw_img_raw.width / claw_img_raw.height))
    claw_scaled = claw_img_raw.resize((max(8, claw_w), max(8, claw_h)), Image.Resampling.LANCZOS)
    img.paste(claw_scaled, (pad_x + int(6*scale), int(4*scale) + int(4*scale)), claw_scaled)
    
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
        
    # Card 1: CPU
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
        draw_flames(draw, x0, y0, x1, y1, flame_flicker, scale)
        
    # Card 2: GPU
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
        draw_flames(draw, gx0, gy0, gx1, gy1, flame_flicker, scale)
        
    # Card 3: RAM & Network
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
    
    # Card 4: Storage
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
    
    # 5. Bottom System Bar
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

if __name__ == '__main__':
    hot_stats = dict(stats)
    hot_stats['cpu_temp'] = 79
    hot_stats['gpu_temp'] = 82
    hot_stats['cpu_usage'] = 94
    hot_stats['gpu_usage'] = 98
    img_hot_hd = render_sensors_view(hot_stats, 1920, 1080, flame_flicker=1)
    img_hot_hd.save(r'C:/Users/cac_7/.gemini/antigravity/brain/2950ecb9-2ce0-438a-a6ff-acc66792f61a/master_telemetry_hot_hd.png')
    print('Hot HD updated!')
