import subprocess
import os

cs_code = r'''using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace MonsterTelemetria
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string smartCoolDir = Path.Combine(baseDir, "SmartCoolApp");
                string batPath = Path.Combine(smartCoolDir, "iniciar.bat");

                if (!File.Exists(batPath))
                {
                    batPath = Path.Combine(baseDir, "INICIAR_MONSTER_TELEMETRIA.bat");
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = "cmd.exe";
                psi.Arguments = "/c \"" + batPath + "\"";
                psi.WorkingDirectory = smartCoolDir;
                psi.WindowStyle = ProcessWindowStyle.Hidden;
                psi.CreateNoWindow = true;
                psi.UseShellExecute = false;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Erro ao iniciar Monster Telemetria: " + ex.Message, "Monster Telemetria", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
'''

base_dir = r"E:\Gravi"
cs_file = os.path.join(base_dir, "MonsterTelemetria.cs")
exe_file = os.path.join(base_dir, "MonsterTelemetria.exe")
ico_file = os.path.join(base_dir, "SmartCoolApp", "assets", "monster_telemetria_icon.ico")

with open(cs_file, "w", encoding="utf-8") as f:
    f.write(cs_code)

csc_path = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
cmd = [
    csc_path,
    "/target:winexe",
    "/platform:anycpu",
    f"/win32icon:{ico_file}",
    f"/out:{exe_file}",
    cs_file
]

res = subprocess.run(cmd, capture_output=True, text=True)
print("CSC Return Code:", res.returncode)
print("CSC Output:", res.stdout)
if res.stderr:
    print("CSC Error:", res.stderr)
print("EXE created successfully:", os.path.exists(exe_file))
