Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$srcDir     = "C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
$deployDir  = "G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"
$appDataDir = "$env:APPDATA\openmohaa\maintt"
$gogRoot    = "G:\GOG\Medal of Honor - Allied Assault War Chest"
$cfgSrc     = Join-Path $srcDir "autoexec.cfg"

# --- 3-way pk3 split (auto-update research, _research/auto_update.md section 5) ---
# Load order preserved: assets_snd < assets_tex < code (ASCII), all in the monolith's old
# alphabetical slot between zzzzzz-HRRTM_* and zzzzzz_hd_*. Code overrides assets.
$oldMonolith = "zzzzzz_co-op_hzm_mod_mohaa.pk3"
$paks = @(
    @{ Name = "zzzzzz_co-op_hzm_mod_assets_snd.pk3"; Dirs = @("sound") },
    @{ Name = "zzzzzz_co-op_hzm_mod_assets_tex.pk3"; Dirs = @("textures","models","gfx","env") },
    @{ Name = "zzzzzz_co-op_hzm_mod_code.pk3";       Dirs = @() }   # everything else (catch-all)
)
$assetDirs = @("sound","textures","models","gfx","env")
$excludeTop = @("_notes")   # dev notes never ship

function Get-TopDir($relPath) {
    $i = $relPath.IndexOf('/')
    if ($i -lt 0) { return "" }
    return $relPath.Substring(0, $i)
}

Write-Host "Packing $srcDir (3-way split)..."
$allFiles = Get-ChildItem -Path $srcDir -Recurse -File | Where-Object {
    $_.Extension -ne '.bak' -and $_.Extension -ne '.pk3' -and
    $_.FullName -notmatch '\\\.git(\\|$)'
}

# bucket files
$buckets = @{}
foreach ($p in $paks) { $buckets[$p.Name] = New-Object System.Collections.ArrayList }
foreach ($file in $allFiles) {
    $rel = $file.FullName.Substring($srcDir.Length + 1).Replace('\', '/')
    $top = Get-TopDir $rel
    if ($excludeTop -contains $top) { continue }
    if ($top -eq "sound") { [void]$buckets[$paks[0].Name].Add(@($rel, $file.FullName)) }
    elseif ($assetDirs -contains $top) { [void]$buckets[$paks[1].Name].Add(@($rel, $file.FullName)) }
    else { [void]$buckets[$paks[2].Name].Add(@($rel, $file.FullName)) }
}

foreach ($p in $paks) {
    $outPath = Join-Path $srcDir $p.Name
    $stream  = [System.IO.File]::Open($outPath, [System.IO.FileMode]::Create)
    $archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Create)
    foreach ($pair in $buckets[$p.Name]) {
        $entry = $archive.CreateEntry($pair[0], [System.IO.Compression.CompressionLevel]::Optimal)
        $es = $entry.Open()
        $fs = [System.IO.File]::OpenRead($pair[1])
        $fs.CopyTo($es)
        $fs.Dispose()
        $es.Dispose()
    }
    $archive.Dispose()
    $stream.Dispose()
    $sizeMB = [math]::Round((Get-Item $outPath).Length / 1MB, 2)
    Write-Host ("  Packed {0} files -> {1} ({2} MB)" -f $buckets[$p.Name].Count, $p.Name, $sizeMB)
}

# --- Deploy pk3s to both targets; retire the old monolith ---
foreach ($destDir in @($deployDir, $appDataDir)) {
    foreach ($p in $paks) {
        Copy-Item -Path (Join-Path $srcDir $p.Name) -Destination (Join-Path $destDir $p.Name) -Force
    }
    $mono = Join-Path $destDir $oldMonolith
    if (Test-Path $mono) {
        Remove-Item $mono -Force -Confirm:$false
        Write-Host "  Retired old monolith -> $mono"
    }
    Write-Host "  Deployed 3 pk3s -> $destDir"
}

# --- Deploy autoexec.cfg ---
Copy-Item -Path $cfgSrc -Destination (Join-Path $deployDir "autoexec.cfg") -Force
Copy-Item -Path $cfgSrc -Destination (Join-Path $appDataDir "autoexec.cfg") -Force
Write-Host "  Deployed autoexec.cfg -> both targets"

# --- Deploy cgame.dll to GOG root (the path the engine actually loads from) ---
$cgameSrc = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\client\cgame\Release\cgame.dll"
if (Test-Path $cgameSrc) {
    try {
        Copy-Item -Path $cgameSrc -Destination (Join-Path $gogRoot "cgame.dll") -Force -ErrorAction Stop
        Write-Host "  Deployed cgame.dll -> $gogRoot"
    } catch {
        Write-Host "  WARNING: could not deploy cgame.dll (game running?)"
    }
}

# renderer modules are separate DLLs (USE_RENDERER_DLOPEN=ON) loaded from the GOG root like
# cgame.dll - deploy them too or renderer changes (post-FX etc.) silently never go live
$rendSrc = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\renderercommon\renderergl1\Release\renderer_opengl1.dll"
if (Test-Path $rendSrc) {
    try {
        Copy-Item -Path $rendSrc -Destination (Join-Path $gogRoot "renderer_opengl1.dll") -Force -ErrorAction Stop
        Write-Host "  Deployed renderer_opengl1.dll -> $gogRoot"
    } catch { Write-Host "  WARNING: could not deploy renderer_opengl1.dll (game running?)" }
}

Write-Host "Done."
