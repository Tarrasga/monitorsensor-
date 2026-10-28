using System;
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
