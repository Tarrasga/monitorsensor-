"""
Gerador de Animação 3D Fotorrealista de Latas Monster Energy.
Frente: Logótipo original autêntico da Monster Energy com gotas de condensação.
Traseira: Nome personalizado 'TARRASGA' em tipografia esports neon com painel técnico.
Renderiza os 12 frames 3D cilíndricos com reflexos metálicos e iluminação cilíndrica.
"""

import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def build_photorealistic_can_texture(tex_w=640, tex_h=300):
    """Constrói a textura unificada 360 graus a partir dos renders fotorrealistas."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")

    p_front = os.path.join(assets_dir, "can_front_clean.png")
    p_back = os.path.join(assets_dir, "can_back_clean.png")

    if not os.path.exists(p_front) or not os.path.exists(p_back):
        raise FileNotFoundError("Assets de frente e traseira das latas não encontrados.")

    f_img = Image.open(p_front).convert("RGB")
    b_img = Image.open(p_back).convert("RGB")

    half_w = tex_w // 2
    f_scaled = f_img.resize((half_w, tex_h), Image.Resampling.LANCZOS)
    b_scaled = b_img.resize((half_w, tex_h), Image.Resampling.LANCZOS)

    # Textura completa 360: Metade esquerda Frente, Metade direita Traseira (TARRASGA)
    tex = Image.new("RGB", (tex_w, tex_h), "#080a09")
    tex.paste(f_scaled, (0, 0))
    tex.paste(b_scaled, (half_w, 0))
    
    tex_path = os.path.join(assets_dir, "can_360_texture.png")
    tex.save(tex_path)
    return tex


def render_all_can_frames(tex_img, num_frames=12, radius=37, height=195):
    """Pré-renderiza os frames 3D de rotação contínua da lata em formato numpy array."""
    tex_arr = np.array(tex_img, dtype=np.float32)
    tex_h, tex_w, _ = tex_arr.shape
    can_w = radius * 2

    can_frames = []
    indices_y = np.linspace(0, tex_h - 1, height).astype(np.int32)

    for f in range(num_frames):
        angle_deg = f * (360.0 / num_frames)
        ang_rad = math.radians(angle_deg)
        can_frame = np.zeros((height, can_w, 3), dtype=np.uint8)

        for xi in range(can_w):
            nx = (xi - radius) / float(radius)
            if abs(nx) >= 1.0:
                continue
            phi = math.asin(nx)
            u = ((phi + ang_rad) / (2.0 * math.pi)) % 1.0
            tx = int(u * tex_w) % tex_w

            diffuse = 0.45 + 0.55 * math.cos(phi)
            spec = max(0.0, math.cos(phi - 0.25)) ** 8 * 95.0

            col = tex_arr[:, tx, :]
            col_resampled = col[indices_y] * diffuse + spec
            can_frame[:, xi, :] = np.clip(col_resampled, 0, 255).astype(np.uint8)

        can_frames.append(can_frame)

    return can_frames


def generate_animated_theme_gif(output_path=None, num_frames=12):
    """Gera o ficheiro GIF final 480x320 com as latas fotorrealistas a rodar."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")

    if output_path is None:
        output_path = os.path.join(assets_dir, "monster_cans_animated.gif")

    print("[1/3] A preparar textura 360 graus fotorrealista (Frente Monster + Trás TARRASGA)...")
    tex = build_photorealistic_can_texture()

    print(f"[2/3] A renderizar {num_frames} frames 3D cilíndricos com física de iluminação...")
    can_frames = render_all_can_frames(tex, num_frames=num_frames, radius=37, height=195)

    print(f"[3/3] A compor HUD e a guardar GIF em {output_path}...")
    half_offset = num_frames // 2
    frames = []

    # Fontes
    try:
        font_head = ImageFont.truetype("arialbd.ttf", 15)
        font_sub = ImageFont.truetype("consolab.ttf", 10)
    except Exception:
        font_head = font_sub = ImageFont.load_default()

    for f in range(num_frames):
        frame = Image.new("RGB", (480, 320), "#080a09")
        draw = ImageDraw.Draw(frame)

        # Grelha de fundo
        for x in range(0, 480, 24):
            draw.line([(x, 0), (x, 320)], fill="#0f1411")
        for y in range(0, 320, 24):
            draw.line([(0, y), (480, y)], fill="#0f1411")

        # Painel Central
        draw.rectangle([105, 14, 375, 306], fill="#0d120f", outline="#1c4020", width=2)
        draw.rectangle([105, 14, 375, 46], fill="#111813", outline="#39ff14", width=1)
        draw.text((118, 23), "MONSTER ENERGY", fill="#39ff14", font=font_head)
        draw.text((276, 26), "TARRASGA RIG", fill="#80b085", font=font_sub)

        # Caixa CPU
        draw.rectangle([115, 56, 236, 172], fill="#111713", outline="#1c3022")
        # Caixa GPU
        draw.rectangle([244, 56, 365, 172], fill="#111713", outline="#1c3022")
        # Caixa RAM/Sys
        draw.rectangle([115, 182, 365, 296], fill="#111713", outline="#1c3022")

        # Sombras com brilho verde neon sob as latas
        draw.ellipse([14, 255, 96, 275], fill="#0a180e", outline="#39ff14")
        draw.ellipse([384, 255, 466, 275], fill="#0a180e", outline="#39ff14")

        # Lata Esquerda (Ângulo atual)
        can_l = Image.fromarray(can_frames[f])
        frame.paste(can_l, (18, 62))

        # Lata Direita (Desfasamento de 180°: quando a esquerda mostra Frente, a direita mostra TARRASGA!)
        r_idx = (f + half_offset) % num_frames
        can_r = Image.fromarray(can_frames[r_idx])
        frame.paste(can_r, (388, 62))

        frames.append(frame)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=300,
        loop=0,
        optimize=True
    )
    print(f"[SUCESSO!] Novo GIF fotorrealista guardado com sucesso: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_animated_theme_gif()
