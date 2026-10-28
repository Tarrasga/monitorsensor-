import os
import winreg
import subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(base_dir)
assets_dir = os.path.join(base_dir, "assets")
ico_path = os.path.join(assets_dir, "monster_telemetria_icon.ico")
if not os.path.exists(ico_path):
    ico_path = os.path.join(assets_dir, "thermometer.ico")

appdata = os.environ.get("APPDATA", "")
startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")

# 1. Criar o launcher silencioso VBS
vbs_path = os.path.join(base_dir, "iniciar_silencioso.vbs")
vbs_content = f'''Set oWS = CreateObject("WScript.Shell")
oWS.CurrentDirectory = "{root_dir}"
oWS.Run "cmd.exe /c ""{os.path.join(root_dir, 'INICIAR_MONSTER_TELEMETRIA.bat')}""", 0, False
'''

with open(vbs_path, "w", encoding="utf-8") as f:
    f.write(vbs_content)
print(f"[OK] Launcher silencioso criado em: {vbs_path}")

# Remover atalho antigo se existir
old_shortcut = os.path.join(startup_dir, "SmartCool Monitor.lnk")
if os.path.exists(old_shortcut):
    try:
        os.remove(old_shortcut)
        print(f"[OK] Atalho antigo removido da pasta Startup: {old_shortcut}")
    except Exception:
        pass

# 2. Criar Atalho na pasta de Inicializacao (Startup Folder)
shortcut_path = os.path.join(startup_dir, "Monster Telemetria.lnk")
ps_script = f'''$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "wscript.exe"
$s.Arguments = """{vbs_path}"""
$s.WorkingDirectory = "{root_dir}"
$s.IconLocation = "{ico_path},0"
$s.Description = "Monster Telemetria // 2º Ecrã, USB & Wi-Fi [TARRASGA]"
$s.Save()
'''

ps_file = os.path.join(base_dir, "_temp_startup.ps1")
with open(ps_file, "w", encoding="utf-8-sig") as f:
    f.write(ps_script)

res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_file], capture_output=True)
if os.path.exists(shortcut_path):
    print(f"[OK] Atalho adicionado a pasta Startup do Windows: {shortcut_path}")
if os.path.exists(ps_file):
    os.remove(ps_file)

# 3. Atualizar chave no Registo do Windows (HKCU Run)
run_cmd = f'wscript.exe "{vbs_path}"'
try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    # Remover chave antiga se existir
    try:
        winreg.DeleteValue(key, "SmartCoolMonitor")
    except Exception:
        pass
    winreg.SetValueEx(key, "MonsterTelemetria", 0, winreg.REG_SZ, run_cmd)
    winreg.CloseKey(key)
    print(f"[OK] Chave registada no Windows Registry (HKCU\\...\\Run): MonsterTelemetria -> {run_cmd}")
except Exception as e:
    print(f"[AVISO] Nao foi possivel escrever no registo: {e}")

print("[SUCESSO] O Monster Telemetria esta agora configurado para arrancar automaticamente com o Windows!")
