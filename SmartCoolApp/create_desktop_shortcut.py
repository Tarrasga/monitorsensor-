import os
import winreg
import subprocess

def get_user_desktop_path():
    # Apenas a pasta do utilizador atual (evita duplicar com o Desktop Publico que o Windows une no ecra)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        d, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        d_expanded = os.path.expandvars(d)
        if os.path.exists(d_expanded):
            return d_expanded
    except Exception:
        pass

    user_home = os.environ.get("USERPROFILE", "")
    for candidate in [
        os.path.join(user_home, "OneDrive", "Área de Trabalho"),
        os.path.join(user_home, "Área de Trabalho"),
        os.path.join(user_home, "Desktop")
    ]:
        if os.path.exists(candidate):
            return candidate
            
    return None

def create_shortcut():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    target_bat = os.path.join(root_dir, "INICIAR_MONSTER_TELEMETRIA.bat")
    ico_path = os.path.join(base_dir, "assets", "monster_telemetria_icon.ico")
    if not os.path.exists(ico_path):
        ico_path = os.path.join(base_dir, "assets", "thermometer.ico")
    
    # 1. Limpar qualquer duplicado no Desktop Publico (o Windows une o Desktop do Utilizador e o Publico no ecra)
    pub_dir = os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop")
    if os.path.exists(pub_dir):
        for f in os.listdir(pub_dir):
            if f in ("Monster Telemetria.lnk", "SmartCool Monitor.lnk"):
                try:
                    os.remove(os.path.join(pub_dir, f))
                    print(f"[LIMPEZA] Removido duplicado do Desktop Publico: {f}")
                except Exception:
                    pass

    # 2. Obter UNICAMENTE a pasta de Desktop do utilizador
    user_desktop = get_user_desktop_path()
    if not user_desktop:
        print("[ERRO] Nao foi possivel localizar a pasta do Ambiente de Trabalho.")
        return

    # Remover qualquer atalho antigo
    old_lnk = os.path.join(user_desktop, "SmartCool Monitor.lnk")
    if os.path.exists(old_lnk):
        try:
            os.remove(old_lnk)
            print(f"[OK] Atalho antigo removido: {old_lnk}")
        except Exception:
            pass
            
    # Criar APENAS 1 atalho oficial
    new_lnk = os.path.join(user_desktop, "Monster Telemetria.lnk")
    ps_code = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{new_lnk}")
$s.TargetPath = "{target_bat}"
$s.WorkingDirectory = "{root_dir}"
$s.IconLocation = "{ico_path},0"
$s.Description = "Monster Telemetria // 2º Ecrã, USB & Wi-Fi [TARRASGA]"
$s.Save()
'''
    temp_ps1 = os.path.join(base_dir, "_temp_lnk.ps1")
    with open(temp_ps1, "w", encoding="utf-8-sig") as f:
        f.write(ps_code)
        
    res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_ps1], capture_output=True)
    if os.path.exists(temp_ps1):
        os.remove(temp_ps1)
        
    if os.path.exists(new_lnk):
        print(f"[SUCESSO] 1 unico atalho 'Monster Telemetria.lnk' criado em: {new_lnk}")
    else:
        print(f"[ERRO] Falha ao criar atalho em: {new_lnk}")

if __name__ == "__main__":
    create_shortcut()
