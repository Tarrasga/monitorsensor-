
$ws = New-Object -ComObject WScript.Shell

$destList = @(
    "C:\Users\cac_7\OneDrive\Área de Trabalho",
    "C:\Users\Public\Desktop"
)

foreach ($d in $destList) {
    if (Test-Path -LiteralPath $d) {
        $lnkPath = Join-Path $d "SmartCool Monitor.lnk"
        $s = $ws.CreateShortcut($lnkPath)
        $s.TargetPath = "E:\Gravi\INICIAR_APP_SMARTCOOL.bat"
        $s.WorkingDirectory = "E:\Gravi"
        $s.IconLocation = "E:\Gravi\SmartCoolApp\assets\thermometer.ico,0"
        $s.Description = "SmartCool Monitor // Master Telemetry [TARRASGA]"
        $s.Save()
        Write-Output "[OK] Atalho criado com sucesso em: $lnkPath"
    } else {
        Write-Output "[INFO] Nao existe: $d"
    }
}
