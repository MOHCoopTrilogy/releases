# MOH Coop Trilogy - "YOUR OWN DISCS": converts a mission from the player's OWN Medal of Honor: Frontline (or European
# Assault) disc image into local paks on THIS PC. Started by the game (Settings -> YOUR OWN DISCS -> ADD, engine command
# coop_byoconvert), or by hand. Nothing is downloaded and nothing of the disc ever ships with the mod: the converter
# (hzmconv\hzmconv.exe, our code + LGPL/permissive runtimes, see hzmconv\tools\*\COPYING*) reads the image you pick and
# writes zzzz_coop_<game>_*.pk3 into your maintt folder. Delete those paks to remove the missions again.
#
#   byo_convert.ps1 -Game frontline|ea -GameHome <homepath\maintt> -MohaaBase <game folder> [-Image <iso|zip>] [-NoGui]
#
# -NoGui with -Image converts without a window (tests). -Reconvert (v1.10.69, run hidden by updater.ps1 at launch): for
# every disc remembered in byo_images.txt whose missions were written by an OLDER converter (byo_converted.txt), convert
# again into maintt\byo_pending\ and move the paks into place; a pak the running game holds open stays pending and the
# updater moves it before the next launch. Nothing to do = exits at once. Never shows anything, never fails an update.
# -NoActivate [-Screen 3440x1440] (tests): the window is shown without ever taking focus, not topmost, on that screen.
# The one-line result goes to
# <GameHome>\byo_status.txt, which the game shows in the menu when this window closes; the full log is
# <GameHome>\byo_convert.log.
param(
    [ValidateSet("frontline", "ea")][string]$Game = "frontline",
    [Parameter(Mandatory = $true)][string]$GameHome,
    [Parameter(Mandatory = $true)][string]$MohaaBase,
    [string]$Image = "",
    [switch]$NoGui,
    # QA only: draw the window into this .png without ever showing it (no focus taken), then exit
    [string]$Snapshot = "",
    [switch]$Reconvert,
    [switch]$NoActivate,
    [string]$Screen = "3440x1440"
)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$statusFile = Join-Path $GameHome "byo_status.txt"
$logFile = Join-Path $GameHome "byo_convert.log"
$memFile = Join-Path $GameHome "byo_images.txt"
$verFile = Join-Path $GameHome "byo_converted.txt"      # game|converter version that wrote the current paks
$script:outDir = $GameHome

$G = @{
    frontline = @{ Name = "Medal of Honor: Frontline"; Short = "Frontline"; Key = "frontline"; Missions = "SEALED ORDERS (St. Mathieu, 1944)" }
    ea        = @{ Name = "Medal of Honor: European Assault"; Short = "European Assault"; Key = "european"; Missions = "THEIR DYING BREATH (Stalingrad, 1943)" }
}[$Game]

function Log($m) { try { Add-Content -LiteralPath $logFile -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $m) -Encoding UTF8 } catch {} }
function Set-Result($m) {
    try { Set-Content -LiteralPath $statusFile -Value $m -Encoding ascii } catch {}
    Log "RESULT $m"
}

# --- the converter: hzmconv.zip (updater payload) unpacked once beside it, again whenever the zip changes ---
function Get-Converter {
    $dir = Join-Path $root "hzmconv"
    $exe = Join-Path $dir "hzmconv.exe"
    $zip = Join-Path $root "hzmconv.zip"
    if (Test-Path -LiteralPath $zip) {
        $sha = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower()
        $stamp = Join-Path $dir "zip.sha256"
        $have = if (Test-Path -LiteralPath $stamp) { (Get-Content -LiteralPath $stamp -Raw).Trim() } else { "" }
        if (-not (Test-Path -LiteralPath $exe) -or $have -ne $sha) {
            Log "unpacking hzmconv.zip ($sha)"
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $tmp = "$dir.new"
            if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
            [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, $tmp)
            Set-Content -LiteralPath (Join-Path $tmp "zip.sha256") -Value $sha -Encoding ascii
            if (Test-Path -LiteralPath $dir) { Remove-Item -LiteralPath $dir -Recurse -Force }
            Rename-Item -LiteralPath $tmp -NewName "hzmconv"
        }
    }
    if (-not (Test-Path -LiteralPath $exe)) { return $null }
    return $exe
}

function Get-Candidates($exe) {
    $list = @()
    try {
        $out = & $exe detect 2>$null | Select-Object -Last 1
        $j = $out | ConvertFrom-Json
        $list = @($j.candidates | Where-Object { $_.size -gt 500MB } | ForEach-Object { $_.path })
    } catch { Log "detect failed: $_" }
    $mine = @($list | Where-Object { (Split-Path -Leaf $_) -match $G.Key })
    # a .zip is only offered when its name hints at the game (any big archive would be noise); an .iso always is
    $rest = @($list | Where-Object { $n = Split-Path -Leaf $_; $n -notmatch $G.Key -and ($n -notmatch '\.zip$' -or $n -match 'medal|moh') })
    $last = @()
    if (Test-Path -LiteralPath $memFile) {
        $last = @(Get-Content -LiteralPath $memFile | Where-Object { $_ -like "$Game|*" } | ForEach-Object { $_.Substring($Game.Length + 1) } |
                  Where-Object { Test-Path -LiteralPath $_ })
    }
    return @($last + $mine + $rest | Select-Object -Unique)
}

function Remember($img) {
    try {
        $keep = @()
        if (Test-Path -LiteralPath $memFile) { $keep = @(Get-Content -LiteralPath $memFile | Where-Object { $_ -notlike "$Game|*" }) }
        Set-Content -LiteralPath $memFile -Value (@($keep) + "$Game|$img") -Encoding UTF8
    } catch {}
}

# one hzmconv add run: cmd.exe redirects its stdout (JSON lines) to a file that the window's timer reads. No PowerShell
# event handlers - they never fire while a modal WinForms loop runs.
function Start-Convert($exe, $img) {
    $out = Join-Path $env:TEMP ("hzmconv_{0}.jsonl" -f [guid]::NewGuid().ToString("N"))
    $script:convOut = $out
    $cargs = "add --game $Game --image `"$img`" --mohaa `"$MohaaBase`" --home `"$($script:outDir)`" --films"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $env:SystemRoot "System32\cmd.exe"
    $psi.Arguments = "/d /s /c `"`"$exe`" $cargs >`"$out`" 2>`"$out.err`"`""
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    Log "start: hzmconv $cargs"
    return [System.Diagnostics.Process]::Start($psi)
}

function Read-Progress {
    $lines = @()
    if ($script:convOut -and (Test-Path -LiteralPath $script:convOut)) {
        try { $lines = @(Get-Content -LiteralPath $script:convOut -Encoding UTF8) } catch {}
    }
    $objs = @()
    foreach ($l in $lines) { try { $objs += ($l | ConvertFrom-Json) } catch {} }
    return $objs
}

function Describe($o) {
    if ($o.error) { return "Not added: $($o.error)" }
    switch ($o.step) {
        "unpack" { return "Reading the disc image out of the zip (one temporary copy)..." }
        "convert" { return "Converting the mission (about a minute)..." }
        "films" { if ($o.skipped) { return "Briefing film skipped." } return "Converting the briefing film..." }
        "upscale" { return "Sharpening textures..." }
    }
    if ($o.done) { return "Done." }
    return ""
}

function Get-Converted {
    $m = @{}
    if (Test-Path -LiteralPath $verFile) {
        foreach ($l in (Get-Content -LiteralPath $verFile)) { $kv = $l -split "\|", 2; if ($kv.Count -eq 2) { $m[$kv[0]] = $kv[1] } }
    }
    return $m
}

function Set-Converted($game, $ver) {
    try {
        $m = Get-Converted; $m[$game] = $ver
        Set-Content -LiteralPath $verFile -Value @($m.Keys | Sort-Object | ForEach-Object { "$_|$($m[$_])" }) -Encoding ascii
    } catch {}
}

# move converted paks from maintt\byo_pending into maintt; a pak the game holds open stays for the next launch
function Move-Pending {
    $pd = Join-Path $GameHome "byo_pending"
    if (-not (Test-Path -LiteralPath $pd)) { return }
    foreach ($f in @(Get-ChildItem -LiteralPath $pd -File -Filter "zzzz_*.pk3")) {
        try { Move-Item -LiteralPath $f.FullName -Destination (Join-Path $GameHome $f.Name) -Force; Log "pending -> $($f.Name)" }
        catch { Log "pending kept (in use?): $($f.Name)" }
    }
}

function Finish($p) {
    $objs = Read-Progress
    $err = $objs | Where-Object { $_.error } | Select-Object -Last 1
    $done = $objs | Where-Object { $_.done } | Select-Object -Last 1
    if ($done -and $p.ExitCode -eq 0) {
        foreach ($f in $done.files) { Log "wrote $f" }
        Set-Converted $Game ([string]$done.version)
        Set-Result "$($G.Short) added: $($G.Missions). Restart the game to play it."
        return $true
    }
    $why = if ($err) { $err.error } else { "the converter stopped (exit $($p.ExitCode))" }
    Set-Result "$($G.Short) not added: $why"
    if (Test-Path -LiteralPath "$($script:convOut).err") { Log ("stderr: " + ((Get-Content -LiteralPath "$($script:convOut).err" -Tail 20) -join " | ")) }
    return $false
}

New-Item -ItemType Directory -Force -Path $GameHome | Out-Null
Log "---- $Game  home=$GameHome  base=$MohaaBase"
$exe = $null
try { $exe = Get-Converter } catch { Log "unpack failed: $_" }
if (-not $exe) {
    Set-Result "The disc converter is missing - run launch_coop (the updater) once, then try again."
    if (-not $NoGui -and -not $Reconvert -and -not $Snapshot) {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show("The disc converter (hzmconv) is not installed yet.`nRun launch_coop once so the updater fetches it, then try again.", "Your own discs")
    }
    exit 2
}

# ------------------------------------------------------------------ silent re-convert (updater, hidden)
if ($Reconvert) {
    try {
        $cur = ""
        try { $cur = ((& $exe version 2>$null | Select-Object -Last 1) | ConvertFrom-Json).version } catch {}
        if (-not $cur -or -not (Test-Path -LiteralPath $memFile)) { exit 0 }
        $have = Get-Converted
        $todo = @(Get-Content -LiteralPath $memFile | ForEach-Object { $kv = $_ -split "\|", 2; if ($kv.Count -eq 2) { ,$kv } } |
                  Where-Object { $have[$_[0]] -ne $cur })
        foreach ($kv in $todo) {
            $Game = $kv[0]; $img = $kv[1]
            $G = @{ frontline = @{ Short = "Frontline"; Missions = "SEALED ORDERS" }; ea = @{ Short = "European Assault"; Missions = "THEIR DYING BREATH" } }[$Game]
            if (-not $G) { continue }
            if (-not (Test-Path -LiteralPath $img)) { Log "reconvert $Game skipped: image gone ($img), old paks kept"; continue }
            Log "reconvert $Game (converter $($have[$Game]) -> $cur)"
            $script:outDir = Join-Path $GameHome "byo_pending"
            New-Item -ItemType Directory -Force -Path $script:outDir | Out-Null
            $p = Start-Convert $exe $img
            $p.PriorityClass = "BelowNormal"
            if (-not $p.WaitForExit(30 * 60 * 1000)) { try { & taskkill.exe /T /F /PID $p.Id | Out-Null } catch {}; Log "reconvert $Game timed out"; continue }
            Start-Sleep -Milliseconds 300
            [void](Finish $p)
            Move-Pending
        }
    } catch { Log "reconvert failed: $_" }
    exit 0
}

# ------------------------------------------------------------------ no window (tests)
if ($NoGui) {
    if (-not $Image) { Set-Result "No disc image given."; exit 2 }
    $p = Start-Convert $exe $Image
    while (-not $p.HasExited) { Start-Sleep -Milliseconds 500 }
    $p.WaitForExit()
    Start-Sleep -Milliseconds 300
    $ok = Finish $p
    if ($ok) { Remember $Image }
    exit ($(if ($ok) { 0 } else { 1 }))
}

# ------------------------------------------------------------------ the window
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$ink = [System.Drawing.Color]::FromArgb(40, 28, 14)
$paper = [System.Drawing.Color]::FromArgb(236, 226, 200)

if ($NoActivate) {
    # tests: a form that never takes focus (WS_EX_NOACTIVATE, ShowWithoutActivation) on the chosen test screen
    Add-Type -ReferencedAssemblies System.Windows.Forms -TypeDefinition @"
public class HzmNoActForm : System.Windows.Forms.Form {
    protected override bool ShowWithoutActivation { get { return true; } }
    protected override System.Windows.Forms.CreateParams CreateParams {
        get { var p = base.CreateParams; p.ExStyle |= 0x08000000 | 0x00000080; return p; }   // NOACTIVATE | TOOLWINDOW
    }
}
"@
    $f = New-Object HzmNoActForm
} else {
    $f = New-Object System.Windows.Forms.Form
}
$f.Text = "Your own discs - $($G.Name)"
$f.ClientSize = New-Object System.Drawing.Size(620, 380)
$f.StartPosition = "CenterScreen"
$f.FormBorderStyle = "FixedDialog"
$f.MaximizeBox = $false
$f.TopMost = -not $NoActivate
if ($NoActivate) {
    $wh = $Screen -split "x"
    $scr = [System.Windows.Forms.Screen]::AllScreens | Where-Object { $_.Bounds.Width -eq [int]$wh[0] -and $_.Bounds.Height -eq [int]$wh[1] } | Select-Object -First 1
    if (-not $scr) { Log "no $Screen screen - not showing a test window"; exit 3 }
    $f.StartPosition = "Manual"
    $f.Location = New-Object System.Drawing.Point(($scr.Bounds.X + 40), ($scr.Bounds.Y + 40))
}
$f.BackColor = $paper
$f.Font = New-Object System.Drawing.Font("Segoe UI", 9.5)

$hdr = New-Object System.Windows.Forms.Label
$hdr.Text = "Add $($G.Name) from your own disc"
$hdr.Font = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Bold)
$hdr.ForeColor = $ink
$hdr.SetBounds(16, 12, 590, 28)
$f.Controls.Add($hdr)

$txt = New-Object System.Windows.Forms.Label
$txt.Text = "Pick your Xbox (USA) disc image of $($G.Short) - an .iso, or a .zip holding one. It is converted on this PC into a co-op mission: $($G.Missions). Nothing is downloaded and nothing leaves your PC."
$txt.ForeColor = $ink
$txt.SetBounds(16, 42, 590, 56)
$f.Controls.Add($txt)

$lst = New-Object System.Windows.Forms.ListBox
$lst.SetBounds(16, 102, 480, 140)
$lst.HorizontalScrollbar = $true
$f.Controls.Add($lst)

$browse = New-Object System.Windows.Forms.Button
$browse.Text = "Browse..."
$browse.SetBounds(506, 102, 98, 28)
$f.Controls.Add($browse)

$scan = New-Object System.Windows.Forms.Label
$scan.Text = "Looking in your drives, Downloads, Desktop and Documents..."
$scan.ForeColor = [System.Drawing.Color]::FromArgb(110, 90, 60)
$scan.SetBounds(16, 246, 590, 20)
$f.Controls.Add($scan)

$bar = New-Object System.Windows.Forms.ProgressBar
$bar.SetBounds(16, 274, 588, 16)
$bar.Style = "Marquee"
$bar.MarqueeAnimationSpeed = 0
$f.Controls.Add($bar)

$msg = New-Object System.Windows.Forms.Label
$msg.ForeColor = $ink
$msg.SetBounds(16, 296, 588, 36)
$f.Controls.Add($msg)

$add = New-Object System.Windows.Forms.Button
$add.Text = "ADD"
$add.SetBounds(392, 338, 100, 30)
$add.Enabled = $false
$f.Controls.Add($add)

$close = New-Object System.Windows.Forms.Button
$close.Text = "Close"
$close.SetBounds(504, 338, 100, 30)
$f.Controls.Add($close)
$f.CancelButton = $close

$script:proc = $null
$script:result = $null

$lst.Add_SelectedIndexChanged({ $add.Enabled = ($lst.SelectedIndex -ge 0) -and (-not $script:proc) })
$browse.Add_Click({
    $d = New-Object System.Windows.Forms.OpenFileDialog
    $d.Title = "Your $($G.Short) disc image"
    $d.Filter = "Disc images (*.iso;*.xiso;*.zip)|*.iso;*.xiso;*.zip|All files (*.*)|*.*"
    if ($d.ShowDialog($f) -eq "OK") {
        $i = $lst.Items.IndexOf($d.FileName)
        if ($i -lt 0) { $lst.Items.Insert(0, $d.FileName); $i = 0 }
        $lst.SelectedIndex = $i
    }
})

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 500
$timer.Add_Tick({
    if (-not $script:proc) { return }
    $last = Read-Progress | Select-Object -Last 1
    if ($last) { $t = Describe $last; if ($t) { $msg.Text = $t } }
    if ($script:proc.HasExited) {
        $timer.Stop()
        $script:proc.WaitForExit()
        $ok = Finish $script:proc
        if ($ok) { Remember $script:img }
        $msg.Text = (Get-Content -LiteralPath $statusFile -Raw).Trim()
        $bar.MarqueeAnimationSpeed = 0
        $bar.Style = "Continuous"; $bar.Value = $(if ($ok) { 100 } else { 0 })
        $script:proc = $null
        $add.Enabled = -not $ok
        $browse.Enabled = $true
        $lst.Enabled = $true
        $close.Text = "Close"
    }
})

$add.Add_Click({
    if ($lst.SelectedIndex -lt 0) { return }
    $script:img = [string]$lst.SelectedItem
    $add.Enabled = $false; $browse.Enabled = $false; $lst.Enabled = $false
    $close.Text = "Cancel"
    $bar.Style = "Marquee"; $bar.MarqueeAnimationSpeed = 30
    $msg.Text = "Checking the disc image..."
    try {
        $script:proc = Start-Convert $exe $script:img
        $timer.Start()
    } catch {
        $msg.Text = "Could not start the converter: $_"
        Set-Result "$($G.Short) not added: the converter did not start"
        $script:proc = $null; $add.Enabled = $true; $browse.Enabled = $true; $lst.Enabled = $true
    }
})

$f.Add_FormClosing({
    if ($script:proc -and -not $script:proc.HasExited) {
        # our own child and its children (ffmpeg / vgmstream): stopped by PID, never by name
        try { & taskkill.exe /T /F /PID $script:proc.Id | Out-Null } catch {}
        Set-Result "$($G.Short) not added: cancelled."
    } elseif (-not (Test-Path -LiteralPath $statusFile)) {
        Set-Result "Closed - nothing was added."
    }
})
$close.Add_Click({ $f.Close() })

$f.Add_Shown({
    if (-not $NoActivate) { $f.Activate() }
    $f.Refresh()
    $c = Get-Candidates $exe
    foreach ($x in $c) { [void]$lst.Items.Add($x) }
    if ($lst.Items.Count -gt 0) {
        $lst.SelectedIndex = 0
        $scan.Text = "Found $($lst.Items.Count) disc image(s). Pick yours, or Browse."
    } else {
        $scan.Text = "No disc image found automatically - use Browse."
    }
})

if ($Snapshot) {
    $f.CreateControl()
    foreach ($x in (Get-Candidates $exe)) { [void]$lst.Items.Add($x) }
    if ($lst.Items.Count -gt 0) { $lst.SelectedIndex = 0; $scan.Text = "Found $($lst.Items.Count) disc image(s). Pick yours, or Browse." }
    $add.Enabled = $lst.Items.Count -gt 0
    # the client area, control by control (an unshown form's DrawToBitmap leaves its children out)
    $bmp = New-Object System.Drawing.Bitmap($f.ClientSize.Width, $f.ClientSize.Height)
    $gfx = [System.Drawing.Graphics]::FromImage($bmp); $gfx.Clear($paper); $gfx.Dispose()
    foreach ($ctl in $f.Controls) { $ctl.CreateControl(); $ctl.DrawToBitmap($bmp, $ctl.Bounds) }
    $bmp.Save($Snapshot, [System.Drawing.Imaging.ImageFormat]::Png)
    exit 0
}
if (Test-Path -LiteralPath $statusFile) { Remove-Item -LiteralPath $statusFile -Force }
if ($NoActivate) { [System.Windows.Forms.Application]::Run($f) } else { [void]$f.ShowDialog() }   # Run = Show: honours ShowWithoutActivation
