# HZM MOH Coop Trilogy - installer packaging
# Usage:  .\build.ps1 ; .\installer\package_installer.ps1 [-AppVersion "1.1.0"] [-ReportWebhook "<discord url>"]
# Sources are referenced in-place (freshly built pk3s in the mod tree, HD pk3s in the GOG maintt,
# fresh .cmake binaries), so ALWAYS run build.ps1 (and any engine builds) first.
param(
    [string]$AppVersion = "1.1.0",
    [string]$ReportWebhook = ""   # Discord webhook URL; empty = reporter falls back to desktop zip
)
$ErrorActionPreference = "Stop"

$iscc = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw "ISCC.exe not found - install Inno Setup 6" }

$dev = "C:\mohaa-coop-dev"
$gog = "G:\GOG\Medal of Honor - Allied Assault War Chest"
$bin = "$dev\openmohaa-hzm\.cmake"
$mod = "$dev\hzm-mohaa-coop-mod"
$iss = "$dev\installer\hzm_coop.iss"

# sanity: the payload the installer ships must exist and be current
$must = @(
    "$bin\Release\openmohaa.exe",
    "$bin\code\client\cgame\Release\cgame.dll",
    "$bin\code\server\fgame\Release\game.dll",
    "$bin\code\renderercommon\renderergl1\Release\renderer_opengl1.dll",
    "$mod\zzzzzz_co-op_hzm_mod_code.pk3",
    "$mod\zzzzzz_co-op_hzm_mod_assets_snd.pk3",
    "$mod\zzzzzz_co-op_hzm_mod_assets_tex.pk3",
    "$dev\updater\updater.ps1",
    "$dev\updater\launch_coop.vbs"
)
foreach ($m in $must) { if (-not (Test-Path $m)) { throw "missing payload: $m" } }

# bake the report webhook into the shipped reporter (placeholder = desktop-zip fallback)
$rp = "$dev\installer\report_problem.ps1"
$rpText = Get-Content $rp -Raw
$rpText = $rpText -replace '\$Webhook = ".*"', ('$Webhook = "' + $(if ($ReportWebhook) { $ReportWebhook } else { "__REPORT_WEBHOOK__" }) + '"')
Set-Content $rp $rpText -Encoding utf8

# --- seed installed_manifest.json: hashes of EXACTLY what this installer ships, so the
# --- first post-install launch diffs clean and never bootstrap-hashes 5 GB.
Write-Host "Generating seed manifest..."
$stage = [ordered]@{}
$stage["openmohaa.exe"]        = "$bin\Release\openmohaa.exe"
$stage["cgame.dll"]            = "$bin\code\client\cgame\Release\cgame.dll"
$stage["game.dll"]             = "$bin\code\server\fgame\Release\game.dll"
$stage["renderer_opengl1.dll"] = "$bin\code\renderercommon\renderergl1\Release\renderer_opengl1.dll"
$stage["renderer_opengl2.dll"] = "$bin\code\renderercommon\renderergl2\Release\renderer_opengl2.dll"
$stage["updater.ps1"]          = "$dev\updater\updater.ps1"
$stage["launch_coop.vbs"]      = "$dev\updater\launch_coop.vbs"
foreach ($p in @("zzzzzz_co-op_hzm_mod_assets_snd.pk3","zzzzzz_co-op_hzm_mod_assets_tex.pk3","zzzzzz_co-op_hzm_mod_code.pk3")) {
    $stage["home/maintt/$p"] = "$mod\$p"
}
$stage["home/maintt/autoexec.cfg"] = "$mod\autoexec.cfg"
$hdPaks = @(
    "zzzzz-AA_HD_Project_Pak1.pk3","zzzzz-AA_HD_Project_Pak2.pk3","zzzzz-AA_HD_Project_Pak3.pk3",
    "zzzzz-AA_HD_Project_Pak4.pk3","zzzzz-hd_gunsounds.pk3","zzzzz_geared_soldiers.pk3",
    "zzzzz_hd_foliage.pk3","zzzzzz-HRRTM_Pak1_Models.pk3","zzzzzz-HRRTM_Pak2_Models_misc.pk3",
    "zzzzzz-HRRTM_Pak3_Textures.pk3","zzzzzz-HRRTM_Pak4_Weapons.pk3","zzzzzz-HRRTM_Pak4c_WeaponTGA.pk3",
    "zzzzzz_hd_charskins.pk3","zzzzzz_hd_fx.pk3","zzzzzz_hd_skybox.pk3","zzzzzz_hd_world.pk3",
    "zzzzzzz-HRRTM_Blood_effects_Addon.pk3","zzzzzzz_dds_override.pk3"
)
foreach ($p in $hdPaks) { $stage["home/maintt/$p"] = "$gog\maintt\$p" }

$files = @()
foreach ($k in $stage.Keys) {
    $src = $stage[$k]
    if (-not (Test-Path $src)) { throw "seed manifest source missing: $src" }
    $files += [pscustomobject]@{
        path   = $k
        size   = (Get-Item $src).Length
        sha256 = (Get-FileHash -Path $src -Algorithm SHA256).Hash.ToLower()
        url    = ""
    }
}
$seed = [pscustomobject]@{
    manifestVersion = 1
    version = $AppVersion
    created = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    files = $files
    delete = @()
}
$seed | ConvertTo-Json -Depth 5 | Set-Content "$dev\installer\installed_manifest_seed.json" -Encoding utf8
Write-Host "  seed manifest: $($files.Count) entries"

try {
    $whArg = if ($ReportWebhook) { "/DReportWebhook=$ReportWebhook" } else { "/DReportWebhook=" }
    & $iscc "/DAppVer=$AppVersion" $whArg $iss
    if ($LASTEXITCODE -ne 0) { throw "ISCC failed ($LASTEXITCODE)" }
} finally {
    # NEVER leave a real webhook in the working tree (public repo!) - restore the placeholder
    $rpText = Get-Content $rp -Raw
    $rpText = $rpText -replace '\$Webhook = ".*"', '$Webhook = "__REPORT_WEBHOOK__"'
    Set-Content $rp $rpText -Encoding utf8
}
Get-ChildItem "$dev\installer\dist" | Sort-Object LastWriteTime | Select-Object -Last 1 Name, @{n="MB";e={[math]::Round($_.Length/1MB)}}
