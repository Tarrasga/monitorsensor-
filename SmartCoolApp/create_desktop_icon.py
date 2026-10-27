import os
import sys
import subprocess
import winreg
from PIL import Image, ImageDraw

def get_desktop_paths():
    """Obtém os caminhos válidos do Ambiente de Trabalho (Desktop) do utilizador."""
    paths = []
    
    # 1. Via Registo do Windows (a fonte mais fiável, trata pastas locais e OneDrive)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        val, _ = winreg.QueryValueEx(key, "Desktop")
        expanded = os.path.expandvars(val)
        if os.path.exists(expanded) and expanded not in paths:
            paths.append(expanded)
    except Exception:
        pass

    # 2. Via pasta de perfil padrão
    user_prof = os.environ.get("USERPROFILE", "")
    if user_prof:
        d1 = os.path.join(user_prof, "Desktop")
        if os.path.exists(d1) and d1 not in paths:
            paths.append(d1)
        d2 = os.path.join(user_prof, "OneDrive", "Desktop")
        if os.path.exists(d2) and d2 not in paths:
            paths.append(d2)

    # 3. Via Public Desktop (fallback)
    pub = os.environ.get("PUBLIC", "")
    if pub:
        d3 = os.path.join(pub, "Desktop")
        if os.path.exists(d3) and d3 not in paths:
            paths.append(d3)

    return paths

def generate_icons(src_jpg_path, assets_dir, root_dir):
    """Gera ficheiros .ico multi-resolução e PNG a partir da imagem do termómetro."""
    img = Image.open(src_jpg_path).convert("RGBA")
    w, h = img.size

    # Máscara de cantos arredondados (squircle elegante para ambiente de trabalho moderno)
    corner_radius = int(w * 0.22)
    mask_sq = Image.new("L", (w * 4, h * 4), 0)
    d_sq = ImageDraw.Draw(mask_sq)
    d_sq.rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=corner_radius * 4, fill=255)
    mask_sq = mask_sq.resize((w, h), Image.Resampling.LANCZOS)

    img_icon = img.copy()
    img_icon.putalpha(mask_sq)

    # Destinos dos ficheiros
    ico_assets = os.path.join(assets_dir, "thermometer.ico")
    png_assets = os.path.join(assets_dir, "thermometer.png")
    ico_root = os.path.join(root_dir, "thermometer.ico")
    png_root = os.path.join(root_dir, "thermometer.png")

    # Resoluções padrão do Windows Icon: 256, 128, 64, 48, 32, 16
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    
    img_icon.save(ico_assets, format="ICO", sizes=icon_sizes)
    img_icon.save(png_assets, format="PNG")
    img_icon.save(ico_root, format="ICO", sizes=icon_sizes)
    img_icon.save(png_root, format="PNG")

    print(f"[OK] Ícones gerados:\n - {ico_assets}\n - {ico_root}")
    return ico_assets

def create_windows_shortcut(target_bat, icon_ico, shortcut_name="SmartCool Monitor"):
    """Cria o atalho .lnk no Ambiente de Trabalho usando WScript.Shell."""
    desktop_dirs = get_desktop_paths()
    if not desktop_dirs:
        print("[ERRO] Nao foi possivel localizar a pasta do Ambiente de Trabalho.")
        return False

    created = 0
    work_dir = os.path.dirname(target_bat)

    for desktop in desktop_dirs:
        shortcut_path = os.path.join(desktop, f"{shortcut_name}.lnk")
        vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_bat}"
oLink.WorkingDirectory = "{work_dir}"
oLink.Description = "SmartCool Monitor // Master Telemetry [TARRASGA]"
oLink.IconLocation = "{icon_ico}, 0"
oLink.Save
'''
        vbs_temp = os.path.join(work_dir, "_temp_shortcut.vbs")
        try:
            with open(vbs_temp, "w", encoding="utf-8") as f:
                f.write(vbs_script.strip())
            res = subprocess.run(["cscript", "//Nologo", vbs_temp], capture_output=True, text=True)
            if os.path.exists(shortcut_path):
                print(f"[OK] Atalho criado no Ambiente de Trabalho: {shortcut_path}")
                created += 1
        except Exception as e:
            print(f"[AVISO] Erro ao criar atalho em {desktop}: {e}")
        finally:
            if os.path.exists(vbs_temp):
                try:
                    os.remove(vbs_temp)
                except Exception:
                    pass

    return created > 0

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    assets_dir = os.path.join(base_dir, "assets")

    src_img = os.path.join(r"C:\Users\cac_7\.gemini\antigravity\brain\2950ecb9-2ce0-438a-a6ff-acc66792f61a", "smartcool_app_icon_1793063416464.jpg")
    if not os.path.exists(src_img):
        # Fallback se a imagem estiver na pasta assets
        src_img = os.path.join(assets_dir, "smartcool_app_icon_1793063416464.jpg")

    ico_path = generate_icons(src_img, assets_dir, root_dir)
    target_bat = os.path.join(root_dir, "INICIAR_APP_SMARTCOOL.bat")
    success = create_windows_shortcut(target_bat, ico_path)
    if success:
        print("[SUCESSO] Atalho com ícone de termómetro configurado no Ambiente de Trabalho!")
    else:
        print("[FALHA] Nao foi possivel criar o atalho.")
