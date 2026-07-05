# HZM MOH Coop Trilogy - installer packaging
# Usage:  .\build.ps1 ; .\installer\package_installer.ps1 [-AppVersion "1.0.1"]
# Sources are referenced in-place (deployed pk3s in the GOG maintt + fresh .cmake binaries),
# so ALWAYS run build.ps1 (and any engine builds) first so the payload is current.
param(
    [string]$AppVersion = "1.0.0",
    [string]$ReportWebhook = ""   # Discord webhook URL; empty = reporter falls back to desktop zip
)

$iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw "ISCC.exe not found - install Inno Setup 6" }

$iss = "C:\mohaa-coop-dev\installer\hzm_coop.iss"

# sanity: the binaries the installer ships must exist and be current
$must = @(
    "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\Release\openmohaa.exe",
    "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\client\cgame\Release\cgame.dll",
    "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\server\fgame\Release\game.dll",
    "G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzzz_co-op_hzm_mod_mohaa.pk3"
)
foreach ($m in $must) { if (-not (Test-Path $m)) { throw "missing payload: $m" } }

# bake the report webhook into the shipped reporter (placeholder = desktop-zip fallback)
$rp = "C:\mohaa-coop-dev\installer\report_problem.ps1"
$rpText = Get-Content $rp -Raw
$rpText = $rpText -replace '\$Webhook = ".*"', ('$Webhook = "' + $(if ($ReportWebhook) { $ReportWebhook } else { "__REPORT_WEBHOOK__" }) + '"')
Set-Content $rp $rpText -Encoding utf8

& $iscc "/DAppVer=$AppVersion" $iss
if ($LASTEXITCODE -ne 0) { throw "ISCC failed ($LASTEXITCODE)" }
Get-ChildItem "C:\mohaa-coop-dev\installer\dist" | Sort-Object LastWriteTime | Select-Object -Last 1 Name, @{n="MB";e={[math]::Round($_.Length/1MB)}}
