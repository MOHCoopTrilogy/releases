Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$srcDir     = "C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
$deployDir  = "G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"
$appDataDir = "$env:APPDATA\openmohaa\maintt"
$gogRoot    = "G:\GOG\Medal of Honor - Allied Assault War Chest"
$cfgSrc     = Join-Path $srcDir "autoexec.cfg"
$cacheDir   = "C:\mohaa-coop-dev\build_out"   # last-built pk3 per bucket + input digest

# Packing must be DETERMINISTIC (bug-237): auto-update asset reuse compares pk3 sha256
# against the released manifest, so an unchanged bucket must produce the identical file.
# Rules: sorted entries, entry mtime = source file mtime (never "now"), git files excluded,
# and a digest cache that skips repacking entirely when a bucket's inputs are unchanged.
$packerVersion = "packer-v2-mtime-sorted-gitless"

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
$excludeNames = @(".gitignore", ".gitattributes", "README.md")   # repo housekeeping never ships

function Get-TopDir($relPath) {
    $i = $relPath.IndexOf('/')
    if ($i -lt 0) { return "" }
    return $relPath.Substring(0, $i)
}

# NEVER deploy under a running game: the engine memory-maps the pk3s at launch, and
# overwriting them mid-session makes it read garbage at stale offsets (bug-241: phantom
# 'label does not exist' errors and a watchdog server crash mid-playtest).
$clientRunning = Get-CimInstance Win32_Process -Filter "Name='openmohaa.exe'" | Where-Object { $_.CommandLine -notlike '*dedicated 1*' }
if ($clientRunning) {
    Write-Host 'ABORTED: openmohaa.exe is running - close the game before deploying.' -ForegroundColor Red
    exit 1
}

Write-Host "Packing $srcDir (3-way split, deterministic)..."
if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }
$allFiles = Get-ChildItem -Path $srcDir -Recurse -File | Where-Object {
    $_.Extension -ne '.bak' -and $_.Extension -ne '.pk3' -and
    $_.FullName -notmatch '\\\.git(\\|$)' -and
    $excludeNames -notcontains $_.Name
}

# bucket files
$buckets = @{}
foreach ($p in $paks) { $buckets[$p.Name] = New-Object System.Collections.ArrayList }
foreach ($file in $allFiles) {
    $rel = $file.FullName.Substring($srcDir.Length + 1).Replace('\', '/')
    $top = Get-TopDir $rel
    if ($excludeTop -contains $top) { continue }
    if ($top -eq "sound") { [void]$buckets[$paks[0].Name].Add(@($rel, $file)) }
    elseif ($assetDirs -contains $top) { [void]$buckets[$paks[1].Name].Add(@($rel, $file)) }
    else { [void]$buckets[$paks[2].Name].Add(@($rel, $file)) }
}

$sha = [System.Security.Cryptography.SHA256]::Create()
foreach ($p in $paks) {
    $list = @($buckets[$p.Name] | Sort-Object { $_[0] })
    # input digest: relpath|size|mtime of every member (this is exactly what the zip stores,
    # so digest-equal implies byte-equal output)
    $lines = @($packerVersion) + @($list | ForEach-Object { "{0}|{1}|{2}" -f $_[0], $_[1].Length, $_[1].LastWriteTimeUtc.Ticks })
    $digest = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes(($lines -join "`n")))).Replace("-", "").ToLower()

    $outPath   = Join-Path $srcDir $p.Name
    $cachePk3  = Join-Path $cacheDir $p.Name
    $cacheSig  = Join-Path $cacheDir ($p.Name + ".inputs")
    $cachedSig = if (Test-Path $cacheSig) { (Get-Content $cacheSig -Raw).Trim() } else { "" }

    if ($cachedSig -eq $digest -and (Test-Path $cachePk3)) {
        Copy-Item $cachePk3 $outPath -Force
        $sizeMB = [math]::Round((Get-Item $outPath).Length / 1MB, 2)
        Write-Host ("  Cache hit  {0} files -> {1} ({2} MB, unchanged)" -f $list.Count, $p.Name, $sizeMB)
        continue
    }

    $stream  = [System.IO.File]::Open($outPath, [System.IO.FileMode]::Create)
    $archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Create)
    foreach ($pair in $list) {
        $entry = $archive.CreateEntry($pair[0], [System.IO.Compression.CompressionLevel]::Optimal)
        $entry.LastWriteTime = [DateTimeOffset]$pair[1].LastWriteTime   # source mtime, not build time
        $es = $entry.Open()
        $fs = [System.IO.File]::OpenRead($pair[1].FullName)
        $fs.CopyTo($es)
        $fs.Dispose()
        $es.Dispose()
    }
    $archive.Dispose()
    $stream.Dispose()
    Copy-Item $outPath $cachePk3 -Force
    Set-Content -Path $cacheSig -Value $digest -Encoding ascii
    $sizeMB = [math]::Round((Get-Item $outPath).Length / 1MB, 2)
    Write-Host ("  Packed {0} files -> {1} ({2} MB)" -f $list.Count, $p.Name, $sizeMB)
}
$sha.Dispose()

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
