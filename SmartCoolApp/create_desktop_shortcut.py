import os
import winreg
import subprocess

def get_desktop_paths():
    paths = []
    # 1. User Desktop via Registry
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        d, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        d_expanded = os.path.expandvars(d)
        if os.path.exists(d_expanded) and d_expanded not in paths:
            paths.append(d_expanded)
    except Exception:
        pass

    # 2. Public Desktop
    pub = os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop")
    if os.path.exists(pub) and pub not in paths:
        paths.append(pub)
        
    return paths

def create_shortcut():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    target_bat = os.path.join(root_dir, "INICIAR_MONSTER_TELEMETRIA.bat")
    ico_path = os.path.join(base_dir, "assets", "thermometer.ico")
    
    desktop_dirs = get_desktop_paths()
    print(f"Pastas de Desktop encontradas: {desktop_dirs}")
    
    for d in desktop_dirs:
        # Remover atalho antigo se existir
        old_lnk = os.path.join(d, "SmartCool Monitor.lnk")
        if os.path.exists(old_lnk):
            try:
                os.remove(old_lnk)
                print(f"[OK] Atalho antigo removido: {old_lnk}")
            except Exception as e:
                print(f"[AVISO] Nao foi possivel remover atalho antigo: {e}")
                
        # Criar novo atalho Monster Telemetria.lnk
        new_lnk = os.path.join(d, "Monster Telemetria.lnk")
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
            print(f"[SUCESSO] Atalho 'Monster Telemetria.lnk' criado em: {new_lnk}")
        else:
            print(f"[ERRO] Falha ao criar atalho em: {new_lnk}")

if __name__ == "__main__":
    create_shortcut()
