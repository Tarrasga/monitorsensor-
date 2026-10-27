
$ws = New-Object -ComObject WScript.Shell

$destList = @(
    "C:\Users\cac_7\OneDrive\Área de Trabalho",
    "C:\Users\Public\Desktop"
)

foreach ($d in $destList) {
    if (Test-Path -LiteralPath $d) {
        # 1. Remover atalho antigo com nome desatualizado se existir
        $oldLnk = Join-Path $d "SmartCool Monitor.lnk"
        if (Test-Path -LiteralPath $oldLnk) {
            Remove-Item -LiteralPath $oldLnk -Force -ErrorAction SilentlyContinue
            Write-Output "[OK] Atalho antigo removido: $oldLnk"
        }

        # 2. Criar novo atalho oficial Monster Telemetria
        $lnkPath = Join-Path $d "Monster Telemetria.lnk"
        $s = $ws.CreateShortcut($lnkPath)
        $s.TargetPath = "E:\Gravi\INICIAR_MONSTER_TELEMETRIA.bat"
        $s.WorkingDirectory = "E:\Gravi"
        $s.IconLocation = "E:\Gravi\SmartCoolApp\assets\thermometer.ico,0"
        $s.Description = "Monster Telemetria // 2º Ecrã, USB & Wi-Fi [TARRASGA]"
        $s.Save()
        Write-Output "[OK] Atalho criado com sucesso em: $lnkPath"
    } else {
        Write-Output "[INFO] Nao existe: $d"
    }
}
