import os
import winreg

appdata = os.environ.get("APPDATA", "")
startup_dir = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
shortcut_path = os.path.join(startup_dir, "SmartCool Monitor.lnk")

if os.path.exists(shortcut_path):
    try:
        os.remove(shortcut_path)
        print(f"[OK] Atalho removido de: {shortcut_path}")
    except Exception as e:
        print(f"[AVISO] Erro ao remover atalho: {e}")

try:
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    winreg.DeleteValue(key, "SmartCoolMonitor")
    winreg.CloseKey(key)
    print("[OK] Chave removida do Windows Registry (HKCU\\...\\Run).")
except FileNotFoundError:
    print("[INFO] Chave nao estava presente no registo.")
except Exception as e:
    print(f"[AVISO] Erro ao aceder ao registo: {e}")

print("[SUCESSO] O arranque automatico com o Windows foi desativado.")
