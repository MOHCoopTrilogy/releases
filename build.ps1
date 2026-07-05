Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$srcDir  = "C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
$pk3Name = "zzzzzz_co-op_hzm_mod_mohaa.pk3"
$pk3Out  = Join-Path $srcDir $pk3Name
$deployDir    = "G:\GOG\Medal of Honor - Allied Assault War Chest\maintt"
$pk3Dest      = Join-Path $deployDir $pk3Name
$cfgSrc       = Join-Path $srcDir "autoexec.cfg"
$cfgDest      = Join-Path $deployDir "autoexec.cfg"
$appDataDir   = "$env:APPDATA\openmohaa\maintt"
$pk3AppData   = Join-Path $appDataDir $pk3Name
$cfgAppData   = Join-Path $appDataDir "autoexec.cfg"
# cgame.dll is loaded from the GOG ROOT install dir (NOT maintt) - confirmed in qconsole.log
$gogRoot      = "G:\GOG\Medal of Honor - Allied Assault War Chest"
$cgameSrc     = "C:\mohaa-coop-dev\openmohaa-hzm\.cmake\code\client\cgame\Release\cgame.dll"
$cgameDest    = Join-Path $gogRoot "cgame.dll"

# --- Pack ---
Write-Host "Packing $srcDir ..."
$stream  = [System.IO.File]::Open($pk3Out, [System.IO.FileMode]::Create)
$archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Create)

$files = Get-ChildItem -Path $srcDir -Recurse -File | Where-Object { $_.Name -ne $pk3Name -and $_.Extension -ne '.bak' }
foreach ($file in $files) {
    $entryName = $file.FullName.Substring($srcDir.Length + 1).Replace('\', '/')
    $entry = $archive.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
    $es = $entry.Open()
    $fs = [System.IO.File]::OpenRead($file.FullName)
    $fs.CopyTo($es)
    $fs.Dispose()
    $es.Dispose()
}
$archive.Dispose()
$stream.Dispose()

$sizeMB = [math]::Round((Get-Item $pk3Out).Length / 1MB, 2)
Write-Host "  Packed $($files.Count) files -> $pk3Name ($sizeMB MB)"

# --- Deploy pk3 ---
Copy-Item -Path $pk3Out -Destination $pk3Dest -Force
Write-Host "  Deployed pk3 -> $pk3Dest"

# --- Deploy pk3 to AppData (homepath â€” takes priority over GOG basepath) ---
Copy-Item -Path $pk3Out -Destination $pk3AppData -Force
Write-Host "  Deployed pk3 -> $pk3AppData"

# --- Deploy autoexec.cfg ---
Copy-Item -Path $cfgSrc -Destination $cfgDest -Force
Write-Host "  Deployed cfg -> $cfgDest"

# --- Deploy autoexec.cfg to AppData homepath (dedicated server reads it here) ---
Copy-Item -Path $cfgSrc -Destination $cfgAppData -Force
Write-Host "  Deployed cfg -> $cfgAppData"

# --- Deploy cgame.dll to GOG root (the path the engine actually loads from) ---
if (Test-Path $cgameSrc) {
    try {
        Copy-Item -Path $cgameSrc -Destination $cgameDest -Force -ErrorAction Stop
        Write-Host "  Deployed cgame.dll -> $cgameDest"
    } catch {
        Write-Host "  WARNING: could not deploy cgame.dll (game running?) -> $cgameDest"
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
} else {
    Write-Host "  (cgame.dll build output not found, skipping DLL deploy)"
}

Write-Host "Done."

