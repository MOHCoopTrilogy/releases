# MOH Coop Trilogy - problem reporter
# Gathers logs + config + system/dll info into a zip. If a webhook is configured it posts
# the report directly to the mod team's Discord channel; otherwise it lands on the desktop.
$ErrorActionPreference = "SilentlyContinue"

# --- filled at packaging time; empty = desktop-zip fallback only ---
$Webhook = "__REPORT_WEBHOOK__"

$app  = Split-Path -Parent $MyInvocation.MyCommand.Path

# prefer the webhook from updater.ini (kept off the public repos); baked value is the fallback
try {
    $iniPath = Join-Path $app "updater.ini"
    if (Test-Path $iniPath) {
        $m = Select-String -Path $iniPath -Pattern "^ReportWebhook=(.+)$"
        if ($m) { $Webhook = $m.Matches[0].Groups[1].Value.Trim() }
    }
} catch {}

# ask the tester what happened - this context is the most valuable part of the report
$UserDescription = ""
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $f = New-Object System.Windows.Forms.Form
    $f.Text = "MOH Coop Trilogy - Report a Problem"
    $f.Size = New-Object System.Drawing.Size(520, 320)
    $f.StartPosition = "CenterScreen"; $f.FormBorderStyle = "FixedDialog"; $f.MaximizeBox = $false
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Location = New-Object System.Drawing.Point(12, 12)
    $lbl.Size = New-Object System.Drawing.Size(480, 40)
    $lbl.Text = "What happened? What were you doing when it broke? (map, weapon, what you expected...)`r`nThe more detail, the faster it gets fixed."
    $tb = New-Object System.Windows.Forms.TextBox
    $tb.Multiline = $true; $tb.ScrollBars = "Vertical"
    $tb.Location = New-Object System.Drawing.Point(12, 58)
    $tb.Size = New-Object System.Drawing.Size(480, 160)
    $ok = New-Object System.Windows.Forms.Button
    $ok.Text = "Send Report"; $ok.Location = New-Object System.Drawing.Point(290, 236)
    $ok.Size = New-Object System.Drawing.Size(100, 30)
    $ok.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $skip = New-Object System.Windows.Forms.Button
    $skip.Text = "Skip"; $skip.Location = New-Object System.Drawing.Point(396, 236)
    $skip.Size = New-Object System.Drawing.Size(96, 30)
    $skip.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $f.Controls.AddRange(@($lbl, $tb, $ok, $skip))
    $f.AcceptButton = $ok
    if ($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $UserDescription = $tb.Text }
} catch {
    $UserDescription = Read-Host "Describe the problem (or press Enter to skip)"
}
$home_ = Join-Path $app "home"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$work = Join-Path $env:TEMP "mohcoop-report-$stamp"
New-Item -ItemType Directory -Path $work -Force | Out-Null

Write-Host "MOH Coop Trilogy - collecting report..." -ForegroundColor Cyan

# logs + configs: source (relative to home\maintt) -> name inside the zip
$grab = @(
    @("qconsole.log",         "qconsole.log"),
    @("configs\omconfig.cfg", "omconfig.cfg"),
    @("omconfig.cfg",         "omconfig_root.cfg"),
    @("autoexec.cfg",         "autoexec.cfg"),
    @("..\..\updater.log",   "updater.log")
)
foreach ($pair in $grab) {
    $p = Join-Path $home_ ("maintt\" + $pair[0])
    if (Test-Path $p) {
        $dst = Join-Path $work $pair[1]
        if ((Get-Item $p).Length -gt 5MB) {
            # cap huge logs at the last 5 MB - the tail is what matters
            $bytes = [IO.File]::ReadAllBytes($p)
            [IO.File]::WriteAllBytes($dst, $bytes[($bytes.Length - 5MB)..($bytes.Length - 1)])
        } else {
            Copy-Item $p $dst
        }
    }
}

# install + game info: versions, and the full inventory of the install dir INCLUDING the
# home content (missing pk3s are a failure mode), plus the game dir dll/pk3 inventory
# (a stray vanilla OpenMOHAA in the game folder is a known failure mode)
$info = @()
$info += "=== MOH Coop Trilogy report $stamp ==="
$infoFile = Join-Path $app "install_info.txt"
if (Test-Path $infoFile) { $info += Get-Content $infoFile }
# install_info.txt is frozen at install time; the live version comes from the updater state
try {
    $imv = (Get-Content (Join-Path $app "installed_manifest.json") -Raw | ConvertFrom-Json).version
    if ($imv) { $info += "CurrentBuild=$imv" }
} catch {}
$info += ""
$info += "=== install dir ($app) ==="
$info += Get-ChildItem $app -File | ForEach-Object { "{0,12:N0}  {1}  {2}" -f $_.Length, $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm"), $_.Name }
$info += ""
$info += "=== mod content (home\maintt) ==="
$mt = Join-Path $home_ "maintt"
if (Test-Path $mt) {
    $info += Get-ChildItem $mt -File | ForEach-Object { "{0,12:N0}  {1}" -f $_.Length, $_.Name }
    $cfgd = Join-Path $mt "configs"
    if (Test-Path $cfgd) {
        $info += Get-ChildItem $cfgd -File | ForEach-Object { "{0,12:N0}  configs\{1}" -f $_.Length, $_.Name }
    }
} else {
    $info += "!! home\maintt DOES NOT EXIST !!"
}
$gogPath = ""
if (Test-Path $infoFile) {
    $m = Select-String -Path $infoFile -Pattern "^GogPath=(.*)$"
    if ($m) { $gogPath = $m.Matches[0].Groups[1].Value }
}
if ($gogPath -and (Test-Path $gogPath)) {
    $info += ""
    $info += "=== game dir ($gogPath) - exe/dll files ==="
    $info += Get-ChildItem $gogPath -File | Where-Object { $_.Extension -in ".exe",".dll" } |
        ForEach-Object { "{0,12:N0}  {1}  {2}" -f $_.Length, $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm"), $_.Name }
    foreach ($sub in @("main","mainta","maintt")) {
        $d = Join-Path $gogPath $sub
        if (Test-Path $d) {
            $info += ""
            $info += "=== game dir $sub - pk3/dll/cfg files ==="
            $info += Get-ChildItem $d -File | Where-Object { $_.Extension -in ".pk3",".dll",".cfg" } |
                ForEach-Object { "{0,12:N0}  {1}" -f $_.Length, $_.Name }
        }
    }
}
$info += ""
$info += "=== system ==="
$os = Get-CimInstance Win32_OperatingSystem
$info += "OS: $($os.Caption) $($os.Version)"
$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 2
foreach ($g in $gpu) { $info += "GPU: $($g.Name)  driver $($g.DriverVersion)" }
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$info += "CPU: $($cpu.Name)"
$info += "RAM: {0:N0} MB" -f ($os.TotalVisibleMemorySize/1KB)
$info | Set-Content (Join-Path $work "report_info.txt") -Encoding utf8
if ($UserDescription.Trim()) { $UserDescription | Set-Content (Join-Path $work "user_description.txt") -Encoding utf8 }

# zip it
$zipName = "MOHCoop-Report-$stamp.zip"
$zipDesk = Join-Path ([Environment]::GetFolderPath("Desktop")) $zipName
Compress-Archive -Path (Join-Path $work "*") -DestinationPath $zipDesk -Force
Remove-Item $work -Recurse -Force

$sent = $false
if ($Webhook -and $Webhook -notlike "__REPORT_*") {
    Write-Host "Sending report to the mod team..." -ForegroundColor Cyan
    try {
        $desc = if ($UserDescription.Trim()) { $UserDescription.Trim() } else { "(no description given)" }
        if ($desc.Length -gt 1700) { $desc = $desc.Substring(0, 1700) + "..." }
        $msg = "**MOH Coop report** from $env:COMPUTERNAME ($stamp)`n>>> $desc"
        $form = @{ file1 = Get-Item $zipDesk; content = $msg }
        Invoke-RestMethod -Uri $Webhook -Method Post -Form $form | Out-Null
        $sent = $true
    } catch {
        # PowerShell 5.1 has no -Form; fall back to curl.exe (ships with Win10+)
        try {
            & curl.exe -s -F "content=$msg" -F "file1=@$zipDesk" $Webhook | Out-Null
            $sent = ($LASTEXITCODE -eq 0)
        } catch {}
    }
}

if ($sent) {
    Write-Host ""
    Write-Host "Report sent to the mod team. A copy is on your desktop: $zipName" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Report saved to your desktop: $zipName" -ForegroundColor Yellow
    Write-Host "Send that file to the mod team (Discord/email)."
    Start-Process explorer.exe "/select,`"$zipDesk`""
}
Write-Host ""
Read-Host "Press Enter to close"





