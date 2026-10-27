import os
import winreg

appdata = os.environ.get("APPDATA", "")
startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")

for lnk_name in ["Monster Telemetria.lnk", "SmartCool Monitor.lnk"]:
    shortcut_path = os.path.join(startup_dir, lnk_name)
    if os.path.exists(shortcut_path):
        try:
            os.remove(shortcut_path)
            print(f"[OK] Atalho removido de: {shortcut_path}")
        except Exception as e:
            print(f"[AVISO] Erro ao remover atalho: {e}")

try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    for k in ["MonsterTelemetria", "SmartCoolMonitor"]:
        try:
            winreg.DeleteValue(key, k)
            print(f"[OK] Chave '{k}' removida do Windows Registry (HKCU\\...\\Run).")
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)
except Exception as e:
    print(f"[AVISO] Erro ao aceder ao registo: {e}")

print("[SUCESSO] O arranque automatico com o Windows foi desativado.")
