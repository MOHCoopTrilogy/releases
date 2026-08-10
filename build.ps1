Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$srcDir     = "C:\mohaa-coop-dev\hzm-mohaa-coop-mod"

# [user 2026-08-05] PARSE-KILLER GATE (detector rank 1, static half): a single BOM/em-dash/odd
# quote silently kills a whole .scr - the map then runs with no script. Never ship one again.
python "C:\mohaa-coop-dev\docs\tools\scrlint.py" $srcDir
if ($LASTEXITCODE -ne 0) { Write-Host "BUILD BLOCKED by scrlint" -ForegroundColor Red; exit 1 }
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
$excludeTop = @("_notes", "_research")   # dev notes + research (pipelines, retail extracts) never ship
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

# --- Deploy cfgs. THREE targets: the live launch profile uses fs_homepath G:\mohaa-gl2\home, and a
#     homepath cfg SHADOWS the basepath copy - stale cfgs there silently ate deployed changes (bug-1633). ---
$gl2HomeDir = "G:\mohaa-gl2\home\maintt"
$cfgTargets = @($deployDir, $appDataDir)
if (Test-Path $gl2HomeDir) { $cfgTargets += $gl2HomeDir }
foreach ($destDir in $cfgTargets) {
    Copy-Item -Path $cfgSrc -Destination (Join-Path $destDir "autoexec.cfg") -Force
}
Write-Host "  Deployed autoexec.cfg -> $($cfgTargets.Count) targets"

# --- Deploy coop_defaults.cfg LOOSE (the engine execs it before the saved config so option changes
#     persist; deployed loose like autoexec to guarantee it's found at Com_Init, not just in the pk3) ---
$defSrc = Join-Path $srcDir "coop_defaults.cfg"
if (Test-Path $defSrc) {
    foreach ($destDir in $cfgTargets) {
        Copy-Item -Path $defSrc -Destination (Join-Path $destDir "coop_defaults.cfg") -Force
    }
    Write-Host "  Deployed coop_defaults.cfg -> $($cfgTargets.Count) targets"
}

# --- Deploy engine DLLs. TWO roots (bug-1634): the LIVE install the user launches is
#     G:\mohaa-gl2\openmohaa.exe, which loads game.dll/cgame.dll/renderer from G:\mohaa-gl2\.
#     The GOG root is kept in sync for release-packaging parity, but deploying ONLY there
#     meant a full day of engine builds (auto-cover included) never actually loaded. ---
$gl2Root = "G:\mohaa-gl2"
$binRoots = @($gogRoot)
if (Test-Path (Join-Path $gl2Root "openmohaa.exe")) { $binRoots += $gl2Root }

$binaries = @(
    @{ Name = "cgame.dll";            Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\client\cgame\Release\cgame.dll" },
    @{ Name = "game.dll";             Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\server\fgame\Release\game.dll" },
    @{ Name = "game.pdb";             Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\server\fgame\Release\game.pdb" },
    @{ Name = "renderer_opengl1.dll"; Src = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\renderercommon\renderergl1\Release\renderer_opengl1.dll" }
)
foreach ($bin in $binaries) {
    if (-not (Test-Path $bin.Src)) { continue }
    foreach ($root in $binRoots) {
        try {
            Copy-Item -Path $bin.Src -Destination (Join-Path $root $bin.Name) -Force -ErrorAction Stop
            Write-Host "  Deployed $($bin.Name) -> $root"
        } catch {
            Write-Host "  WARNING: could not deploy $($bin.Name) to $root (game running?)"
        }
    }
}

Write-Host "Done."
