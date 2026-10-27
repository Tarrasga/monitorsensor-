
$ws = New-Object -ComObject WScript.Shell

# 1. Limpar duplicado do Desktop Publico
$pubLnk = "C:\Users\Public\Desktop\Monster Telemetria.lnk"
if (Test-Path -LiteralPath $pubLnk) {
    Remove-Item -LiteralPath $pubLnk -Force -ErrorAction SilentlyContinue
}
$pubOld = "C:\Users\Public\Desktop\SmartCool Monitor.lnk"
if (Test-Path -LiteralPath $pubOld) {
    Remove-Item -LiteralPath $pubOld -Force -ErrorAction SilentlyContinue
}

# 2. Obter apenas o Desktop do Utilizador
$userDesktop = "C:\Users\cac_7\OneDrive\Área de Trabalho"
if (-not (Test-Path -LiteralPath $userDesktop)) {
    $userDesktop = $ws.SpecialFolders.Item("Desktop")
}

if (Test-Path -LiteralPath $userDesktop) {
    $oldLnk = Join-Path $userDesktop "SmartCool Monitor.lnk"
    if (Test-Path -LiteralPath $oldLnk) {
        Remove-Item -LiteralPath $oldLnk -Force -ErrorAction SilentlyContinue
    }

    $lnkPath = Join-Path $userDesktop "Monster Telemetria.lnk"
    $s = $ws.CreateShortcut($lnkPath)
    $s.TargetPath = "E:\Gravi\INICIAR_MONSTER_TELEMETRIA.bat"
    $s.WorkingDirectory = "E:\Gravi"
    $s.IconLocation = "E:\Gravi\SmartCoolApp\assets\thermometer.ico,0"
    $s.Description = "Monster Telemetria // 2º Ecrã, USB & Wi-Fi [TARRASGA]"
    $s.Save()
    Write-Output "[OK] 1 unico atalho no Ambiente de Trabalho: $lnkPath"
}
