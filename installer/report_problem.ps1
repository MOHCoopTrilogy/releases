# MOH Coop Trilogy - problem reporter (desktop). v2, bugreport_parity_2026-09-29.
# Gathers logs + settings + system/dll info, SCRUBS them (the same rules as the in-game reporter,
# openmohaa-hzm/code/client/cl_bugreport.cpp BR_Scrub), shows the player the exact message and file list, and only
# then posts to the mod team's Discord (webhook from updater.ini). Cancel at any point = nothing sent, nothing kept.
#
#   report_problem.ps1                         normal (dialogs)
#   report_problem.ps1 -DryRun <dir>           build everything, write payload.json / the zip / multipart_body.bin /
#                                              request.txt into <dir>, post nothing (with -NoGui: -Description/-Steps)
#   report_problem.ps1 -SelfTest <corpus> -Out <file> [-ScrubProfile p -User u -Pc c]   scrub a corpus (parity test)
#   report_problem.ps1 -SettingsTest <names> -Out <file>                          the settings allowlist (parity test)
param(
    [string]$DryRun = "",
    [switch]$NoGui,
    [string]$Description = "",
    [string]$Steps = "",
    [string]$Category = "",
    [switch]$IncludeDump,
    [string]$SelfTest = "",
    [string]$SettingsTest = "",
    [string]$Out = "",
    [string]$ScrubProfile = "",
    [string]$User = "",
    [string]$Pc = "",
    [string]$Names = ""
)
$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference = "SilentlyContinue"
$L1 = [Text.Encoding]::GetEncoding(28591)   # bytes <-> chars 1:1, so the rules act on bytes exactly like the C
$W = 'A-Za-z0-9_\x80-\xFF'                  # BR_IsWordChar

# ---------------------------------------------------------------------------------------------------- scrubber
function Id-Variants([string]$s) {
    # the same value as ANSI bytes and as UTF-8 bytes, each seen through Latin-1 (the log may hold either)
    if (-not $s) { return @() }
    return ,@(@($L1.GetString([Text.Encoding]::Default.GetBytes($s)), $L1.GetString([Text.Encoding]::UTF8.GetBytes($s))) | Select-Object -Unique)
}
$script:Ctx = @{
    Profile = Id-Variants $env:USERPROFILE
    User    = Id-Variants $env:USERNAME
    Pc      = Id-Variants $env:COMPUTERNAME
    Names   = @()    # player names (yours from omconfig, others learned from the log) -> <NAME>; set before scrubbing
}

function Replace-CI([string]$t, [string]$lit, [string]$rep, [bool]$whole) {
    if (-not $lit -or $lit.Length -lt 2) { return $t }
    $p = [regex]::Escape($lit)
    if ($whole) { $p = "(?<![$W])" + $p + "(?![$W])" }
    return [regex]::Replace($t, $p, $rep.Replace('$', '$$'), 'IgnoreCase')
}

function Scrub-Text([string]$t) {
    # 0. colour codes go first: "^1password^7 hunter2" must not split a keyword from its value
    $t = [regex]::Replace($t, '\^[0-9]', '')
    # 1. webhook URLs
    $t = [regex]::Replace($t, "[$W.:/-]*api/webhooks/[$W/-]*", '<webhook>', 'IgnoreCase')
    # 2. other players' userinfo
    $t = [regex]::Replace($t, '>>>[^\n]*?<<<', '>>><userinfo><<<')
    # 2b. a bare \name\<value> info-string key
    $t = [regex]::Replace($t, '(\\name\\)[^\\\r\n"]+', '${1}<NAME>', 'IgnoreCase')
    # 3. <sensitive word><sep><value>; "key" / "auth" whole word only, no word-length cap
    $kv = "(?<![$W])((?:(?=[$W]*(?:password|passwd|rcon|token|secret|cdkey|qkey|q3key|apikey|api_key|bearer|webhook|guid|rdv))[$W]+|pass|pw|coop_join|key|auth))(?![$W])" +
          '([ \t=:\\]*(?:(["''])[ \t=:\\]*)?)((?(3)[^\r\n"''\\;<>]+|[^\r\n"''\\;<> \t]+))?'
    $t = [regex]::Replace($t, $kv, [Text.RegularExpressions.MatchEvaluator]{
        param($m)
        if ($m.Groups[4].Success) { return $m.Groups[1].Value + $m.Groups[2].Value + '<redacted>' }
        return $m.Value
    }, 'IgnoreCase')
    # 4. "<host> resolved to"; join codes on rendezvous / coop_join lines
    $t = [regex]::Replace($t, '[^\n]*\n?', [Text.RegularExpressions.MatchEvaluator]{
        param($m)
        $ln = $m.Value
        if (-not $ln) { return $ln }
        $rt = $ln.IndexOf(' resolved to ', [StringComparison]::Ordinal)
        if ($rt -ge 0) {
            $s = $rt
            while ($s -gt 0 -and $ln[$s - 1] -ne ' ' -and $ln[$s - 1] -ne ']') { $s-- }
            return $ln.Substring(0, $s) + '<host>' + $ln.Substring($rt)
        }
        if ($ln -match '(?i)rendezvous|coop_join') { return [regex]::Replace($ln, "'[^'\n]*'", "'<code>'") }
        return $ln
    })
    # 5. cd-key shaped tokens (the desktop never knows the live key; the in-game path also redacts that literal)
    $t = [regex]::Replace($t, "(?<![$W-])[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}(?![$W-])", '<cdkey>')
    # 6. the profile path, 4 spellings per variant (JSON-escaped first, like the C)
    foreach ($pv in $script:Ctx.Profile) {
        if ($pv.Length -lt 4) { continue }
        $b = $pv -replace '/', '\'
        $v0 = $b; $v1 = $b -replace '\\', '/'; $v2 = $b -replace '\\', '\\'
        $v3 = '/' + $b.Substring(0, 1).ToLower() + ($b.Substring(2) -replace '\\', '/')
        foreach ($v in @($v2, $v0, $v1, $v3)) { $t = Replace-CI $t $v '<HOME>' $false }
    }
    # 7. any Users / Documents and Settings folder; OneDrive - <organisation>
    $ud = "(OneDrive - [^\\/""'\r\n]*)|(?:(?<![$W])([A-Za-z]):)?([\\/]+)(users|documents and settings)([\\/]+)([^\\/""'<\r\n]+)"
    $t = [regex]::Replace($t, $ud, [Text.RegularExpressions.MatchEvaluator]{
        param($m)
        if ($m.Groups[1].Success) { return 'OneDrive - <org>' }
        if ($m.Groups[2].Success) { return '<HOME>' }
        return $m.Groups[3].Value + $m.Groups[4].Value + $m.Groups[5].Value + '<USER>'
    }, 'IgnoreCase')
    # 8. user and PC name, whole word, both encodings
    foreach ($i in 0..1) {
        if ($i -lt $script:Ctx.User.Count) { $t = Replace-CI $t $script:Ctx.User[$i] '<USER>' $true }
        if ($i -lt $script:Ctx.Pc.Count) { $t = Replace-CI $t $script:Ctx.Pc[$i] '<PC>' $true }
    }
    foreach ($nm in $script:Ctx.Names) { $t = Replace-CI $t $nm '<NAME>' $true }
    # 9. IPv4 (not loopback / 0.0.0.0 / broadcast), then IPv6 (needs "::" or >= 5 colons: HH:MM:SS never matches)
    $t = [regex]::Replace($t, "(?<![$W.:])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![$W]|\.\d)", [Text.RegularExpressions.MatchEvaluator]{
        param($m)
        $o = @([int]$m.Groups[1].Value, [int]$m.Groups[2].Value, [int]$m.Groups[3].Value, [int]$m.Groups[4].Value)
        foreach ($x in $o) { if ($x -gt 255) { return $m.Value } }
        $k = $m.Value
        if ($k -eq '127.0.0.1' -or $k -eq '0.0.0.0' -or $k -eq '255.255.255.255') { return $k }
        return '<ip>'
    })
    $script:ipsrc = $t
    $t = [regex]::Replace($t, "(?<![$W.:])([0-9A-Fa-f:.]+)(%[$W]*)?", [Text.RegularExpressions.MatchEvaluator]{
        param($m)
        $run = $m.Groups[1].Value
        $core = $run.TrimEnd('.')
        $dots = $run.Substring($core.Length)
        $colons = ($core.ToCharArray() | Where-Object { $_ -eq ':' }).Count
        $hex = $core -match '[0-9A-Fa-f]'
        if (-not ($hex -and $colons -ge 2 -and ($core.Contains('::') -or $colons -ge 5))) { return $m.Value }
        $zone = ''
        if (-not $dots -and $m.Groups[2].Success) { $zone = $m.Groups[2].Value }
        $end = $m.Index + $core.Length + $zone.Length
        if ($end -lt $script:ipsrc.Length -and $script:ipsrc[$end] -match "[$W]") { return $m.Value }
        $rest = $m.Value.Substring($core.Length + $zone.Length)
        return '<ip6>' + $rest
    })
    return $t
}

function Scrub-File([string]$src, [string]$dst, [long]$tail = 0) {
    $b = [IO.File]::ReadAllBytes($src)
    if ($tail -gt 0 -and $b.Length -gt $tail) {
        $b = $b[($b.Length - $tail)..($b.Length - 1)]
        $nl = [Array]::IndexOf($b, [byte]10)
        if ($nl -ge 0) { $b = $b[($nl + 1)..($b.Length - 1)] }
    }
    $s = Scrub-Text ($L1.GetString($b))
    [IO.File]::WriteAllBytes($dst, $L1.GetBytes($s))
    return $s
}

# settings: the in-game allowlist (BR_CvarWithheld + BR_SettingAllowed). The desktop cannot see which coop_* cvars the
# engine registers, so it is stricter: a coop_* cvar passes only if a shipped cfg seeds it.
function Cvar-Withheld([string]$n) {
    $w = $n.ToLower()
    if ($w -eq 'name' -or $w -eq 'cl_playername' -or $w.Length -ge 128) { return $true }
    $w2 = $w.Replace('compass', '')   # coop_compassBar is a HUD setting, not a password (same rule as the C)
    foreach ($s in @('pass','key','rcon','token','secret','webhook','auth','guid','cdkey','socks','connect','rdv','hostname')) { if ($w2.Contains($s)) { return $true } }
    foreach ($p in @('sv_location','sv_dlurl','net_mcast','coop_xp','coop_sbrank','coop_chal','coop_cp','coop_pend_','coop_pin','coop_unlock','coop_mpcnt_','coop_mpprogblob',
                     'coop_mprank','coop_mps_','coop_mptotal','coop_mpuw_','coop_mpa_cos','coop_mpx_cos','coop_prestige','coop_medal',
                     'coop_rank','coop_career','coop_servicerec','g_medal','g_eogmedal','g_lastsave','g_mission','coop_report','coop_lastserver')) {
        if ($w.StartsWith($p)) { return $true }
    }
    if ($w -match '^coop_ui[bdnp][0-9]') { return $true }
    if ($w.StartsWith('coop_lo') -and $w.Substring(7).Contains('lk')) { return $true }
    if ($w -match '^g_[met][0-9]') { return $true }
    if ($w.EndsWith('ip') -or $w.EndsWith('ip6')) { return $true }
    return $false
}
function Setting-Allowed([string]$n, [bool]$engine, [bool]$seeded) {
    if (Cvar-Withheld $n) { return $false }
    if ($n -match '^(?i)coop_') { return ($engine -or $seeded) }
    if ($n -match '^(?i)(r_|gl_|cg_|cl_|com_|s_|snd_|vid_|in_|j_|m_|sv_|net_|fs_|sys_|ui_|bot_|g_|dm_|con_|scr_)') { return $true }
    return @('version','developer','logfile','sensitivity','rate','snaps','dedicated','timescale','fraglimit','timelimit','mapname','skill') -contains $n.ToLower()
}

# player names to remove: your own (omconfig `seta name`) and everyone the log says entered / joined a game
function Add-Name([string]$raw) {
    $n = ($raw -replace '\^[0-9]', '').Trim()
    foreach ($c in @($n, ($n -replace '#.*$', '').Trim(), ($n -replace ' ,.*$', '').Trim())) {
        if ($c.Length -ge 3 -and ($script:Ctx.Names -notcontains $c)) { $script:Ctx.Names += $c }
    }
}
if ($SelfTest) {
    if ($ScrubProfile) { $script:Ctx.Profile = Id-Variants $ScrubProfile }
    if ($User) { $script:Ctx.User = Id-Variants $User }
    if ($Pc) { $script:Ctx.Pc = Id-Variants $Pc }
    if ($Names) { foreach ($nm in ($Names -split '\|')) { Add-Name $nm } }
    $s = Scrub-Text ($L1.GetString([IO.File]::ReadAllBytes($SelfTest)))
    [IO.File]::WriteAllBytes($Out, $L1.GetBytes($s))
    exit 0
}
if ($SettingsTest) {
    $o = foreach ($ln in Get-Content $SettingsTest) {
        $f = $ln -split ' '
        if ($f.Count -ge 3 -and (Setting-Allowed $f[0] ($f[1] -eq '1') ($f[2] -eq '1'))) { $f[0] }
    }
    Set-Content -Path $Out -Value $o -Encoding ASCII
    exit 0
}

# ---------------------------------------------------------------------------------------------------- setup
$app   = Split-Path -Parent $MyInvocation.MyCommand.Path
$home_ = Join-Path $app "home"
$mt    = Join-Path $home_ "maintt"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipName = "MOHCoop-Report-$stamp.zip"
$repRoot = Join-Path $mt "coop_report"
$work  = Join-Path $env:TEMP "mohcoop-report-$stamp"
$files = Join-Path $work "files"

# webhook: updater.ini only (kept off the public repos). Read at send time, never written anywhere.
function Get-Webhook {
    try {
        $m = Select-String -Path (Join-Path $app "updater.ini") -Pattern "^ReportWebhook=(.+)$"
        if ($m) {
            $w = $m.Matches[0].Groups[1].Value.Trim()
            if ($w -match '^https://(ptb\.|canary\.)?discord(app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]+$') { return $w }
        }
    } catch {}
    return $null
}

# rate limit, shared with the in-game reporter: home\maintt\coop_report\state.txt
function Rate-Check {
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); $last = 0; $day = 0; $count = 0
    try {
        $s = Get-Content (Join-Path $repRoot "state.txt") -Raw
        if ($s -match 'last=(\d+)') { $last = [long]$Matches[1] }
        if ($s -match 'day=(\d+)') { $day = [long]$Matches[1] }
        if ($s -match 'count=(\d+)') { $count = [int]$Matches[1] }
    } catch {}
    if ($now -ge $last -and $now - $last -lt 60) { return "Please wait a minute before sending another report." }
    if ($now - $day -ge 86400 -or $now -lt $day) { $day = $now; $count = 0 }
    if ($count -ge 20) { return "Daily report limit reached (20). Please send the zip by hand." }
    $script:rate = @($now, $day, $count)
    return $null
}
function Rate-Record {
    try {
        New-Item -ItemType Directory -Force -Path $repRoot | Out-Null
        Set-Content -Path (Join-Path $repRoot "state.txt") -Encoding ASCII -Value ("last={0} day={1} count={2}" -f $script:rate[0], $script:rate[1], ($script:rate[2] + 1))
    } catch {}
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# ---------------------------------------------------------------------------------------------------- 1. ask
$opt = @{ Log = $true; Cfg = $true; Sys = $true; Crash = $true; Inst = $true; Dump = [bool]$IncludeDump }
if (-not $NoGui) {
    $f = New-Object Windows.Forms.Form
    $f.Text = "MOH Coop Trilogy - Report a Problem"
    $f.Size = New-Object Drawing.Size(560, 560); $f.StartPosition = "CenterScreen"; $f.FormBorderStyle = "FixedDialog"; $f.MaximizeBox = $false
    function Lbl($t, $y, $h = 20) { $l = New-Object Windows.Forms.Label; $l.Text = $t; $l.Location = New-Object Drawing.Point(12, $y); $l.Size = New-Object Drawing.Size(520, $h); $f.Controls.Add($l) }
    function Box($y, $h) { $b = New-Object Windows.Forms.TextBox; $b.Multiline = $true; $b.ScrollBars = "Vertical"; $b.Location = New-Object Drawing.Point(12, $y); $b.Size = New-Object Drawing.Size(520, $h); $f.Controls.Add($b); return $b }
    function Chk($t, $y, $v) { $c = New-Object Windows.Forms.CheckBox; $c.Text = $t; $c.Checked = $v; $c.Location = New-Object Drawing.Point(12, $y); $c.Size = New-Object Drawing.Size(520, 20); $f.Controls.Add($c); return $c }
    $cats = @("Choose one", "Crash / freeze", "Performance / lag / server slow", "Graphics / HUD / crosshair",
              "Gameplay / AI / objectives", "Weapons / aiming", "Map / mission / stuck", "Sound",
              "Menus / settings / controls", "Multiplayer / connection", "Other", "Install / update / launch")
    Lbl "What kind of problem?" 10
    $cb = New-Object Windows.Forms.ComboBox; $cb.DropDownStyle = "DropDownList"; $cb.Location = New-Object Drawing.Point(180, 6)
    $cb.Size = New-Object Drawing.Size(352, 22); [void]$cb.Items.AddRange([object[]]$cats); $cb.SelectedIndex = 0; $f.Controls.Add($cb)
    Lbl "What happened? (map, weapon, what you expected...)" 34
    $tb = Box 54 88
    Lbl "Steps to reproduce (what to do to make it happen again):" 150
    $ts = Box 172 70
    Lbl "Attach (you will see everything before it is sent; personal info is removed):" 252
    $cLog = Chk "Game logs (qconsole.log, the previous session's log)" 274 $true
    $cCfg = Chk "Settings (graphics/sound/gameplay - no passwords, keys, IPs, name or progress)" 296 $true
    $cSys = Chk "System info (Windows version, GPU + driver, CPU, RAM)" 318 $true
    $cCrash = Chk "Crash info (hzm_fatal.log, crash summary, loaded overlay programs)" 340 $true
    $cInst = Chk "Install check (file list of the mod and game folders, updater.log)" 362 $true
    $cDump = Chk "Raw crash dump file - contains game memory, possibly your CD key; tick only if we asked" 384 $opt.Dump
    $ok = New-Object Windows.Forms.Button; $ok.Text = "Review..."; $ok.Location = New-Object Drawing.Point(330, 470); $ok.Size = New-Object Drawing.Size(96, 30); $ok.DialogResult = "OK"
    $cn = New-Object Windows.Forms.Button; $cn.Text = "Cancel"; $cn.Location = New-Object Drawing.Point(436, 470); $cn.Size = New-Object Drawing.Size(96, 30); $cn.DialogResult = "Cancel"
    $f.Controls.AddRange(@($ok, $cn)); $f.AcceptButton = $ok; $f.CancelButton = $cn
    if ($f.ShowDialog() -ne "OK") { exit 0 }   # Cancel / close: nothing collected, nothing sent, nothing kept
    $Description = $tb.Text; $Steps = $ts.Text
    if ($cb.SelectedIndex -gt 0) { $Category = [string]$cb.SelectedItem }
    $opt = @{ Log = $cLog.Checked; Cfg = $cCfg.Checked; Sys = $cSys.Checked; Crash = $cCrash.Checked; Inst = $cInst.Checked; Dump = $cDump.Checked }
}
if (-not $Description.Trim()) {
    if (-not $NoGui) { [Windows.Forms.MessageBox]::Show("Please describe the problem first - nothing was sent.", "Report a Problem") | Out-Null }
    exit 0
}

# ---------------------------------------------------------------------------------------------------- 2. collect
New-Item -ItemType Directory -Path $files -Force | Out-Null
try {
    $p = Join-Path $mt "configs\omconfig.cfg"
    if (Test-Path $p) { foreach ($ln in [IO.File]::ReadAllLines($p, $L1)) { if ($ln -match '(?i)^\s*seta?\s+name\s+"?([^"\r\n]*)') { Add-Name $Matches[1] } } }
    foreach ($lf in @("qconsole.log", "qconsole_prev.log")) {
        $p = Join-Path $mt $lf
        if (Test-Path $p) {
            $bb = [IO.File]::ReadAllBytes($p); if ($bb.Length -gt 2MB) { $bb = $bb[($bb.Length - 2MB)..($bb.Length - 1)] }
            foreach ($mm in [regex]::Matches($L1.GetString($bb), '(?m)^\[[^\]\r\n]*\] ([^\r\n]{3,40}?) has (?:entered the battle|joined the )')) { Add-Name $mm.Groups[1].Value }
        }
    }
} catch {}
$logText = ""
if ($opt.Log) {
    $p = Join-Path $mt "qconsole.log"
    if (Test-Path $p) { $logText = Scrub-File $p (Join-Path $files "qconsole.log") (2MB) }
    $p = Join-Path $mt "qconsole_prev.log"
    if (Test-Path $p) { Scrub-File $p (Join-Path $files "qconsole_prev.log") (1MB) | Out-Null }
} else {
    $p = Join-Path $mt "qconsole.log"   # read (not attached) for the header's build/map/error summary only
    if (Test-Path $p) { $bb = [IO.File]::ReadAllBytes($p); if ($bb.Length -gt 2MB) { $bb = $bb[($bb.Length - 2MB)..($bb.Length - 1)] }; $logText = Scrub-Text ($L1.GetString($bb)) }
}

# the code pak: mod version + the coop_* names the shipped cfgs seed (settings allowlist)
$modVer = "unknown"; $seeded = @{}
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $pak = Get-ChildItem $mt -Filter "zzzzzz_co-op_hzm_mod_code*.pk3" -File | Select-Object -First 1
    if ($pak) {
        $z = [IO.Compression.ZipFile]::OpenRead($pak.FullName)
        foreach ($e in $z.Entries) {
            if ($e.FullName -in @("coop_defaults.cfg", "autoexec.cfg", "ui/coop_version.cfg")) {
                $r = New-Object IO.StreamReader($e.Open(), $L1); $txt = $r.ReadToEnd(); $r.Close()
                if ($e.FullName -eq "ui/coop_version.cfg") { if ($txt -match 'coop_modVersion\s+"([^"]+)"') { $modVer = $Matches[1] } }
                else { foreach ($mm in [regex]::Matches($txt, '(?im)^\s*set[asu]?\s+(coop_[A-Za-z0-9_]+)')) { $seeded[$mm.Groups[1].Value.ToLower()] = 1 } }
            }
        }
        $z.Dispose()
    }
} catch {}

if ($opt.Cfg) {
    $p = Join-Path $mt "configs\omconfig.cfg"
    if (Test-Path $p) {
        $cfgOut = New-Object Collections.Generic.List[string]
        $cfgOut.Add("// MOH Coop desktop report - your saved settings, scrubbed. Only engine/renderer/sound/client settings and")
        $cfgOut.Add("// coop settings the mod ships are included; passwords, keys, IPs, your name and progress never are.")
        $kept = 0; $all = 0
        foreach ($ln in [IO.File]::ReadAllLines($p, $L1)) {
            if ($ln -match '^\s*(seta?|sets|setu)\s+([A-Za-z0-9_]+)\s*(.*)$') {
                $all++
                $n = $Matches[2]
                if (Setting-Allowed $n $false ($seeded.ContainsKey($n.ToLower()))) { $cfgOut.Add((Scrub-Text $ln)); $kept++ }
            } elseif ($ln -match '^\s*bind\s') { $cfgOut.Add((Scrub-Text $ln)) }
        }
        $cfgOut.Add("// $kept of $all settings included")
        [IO.File]::WriteAllLines((Join-Path $files "settings.cfg"), $cfgOut.ToArray(), $L1)
    }
}

# crash: hzm_fatal.log, newest dump summary (raw dump only if ticked)
$dump = $null; $dumpNote = ""; $moduleLines = @()
if ($opt.Crash -or $opt.Dump) {
    $p = Join-Path $app "hzm_fatal.log"
    if ($opt.Crash -and (Test-Path $p)) { Scrub-File $p (Join-Path $files "hzm_fatal.log") (64KB) | Out-Null }
    try {
        $dd = Join-Path $env:LOCALAPPDATA "CrashDumps"
        $dump = Get-ChildItem $dd -Filter "openmohaa.exe.*.dmp" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($dump -and $dump.LastWriteTime -gt (Get-Date).AddHours(-48)) {
            $dumpNote = "crash dump: $($dump.Name) ($([math]::Round($dump.Length/1MB,1)) MB, $($dump.LastWriteTime))"
            if ($opt.Dump) {
                if ($dump.Length -le 60MB) { Copy-Item $dump.FullName (Join-Path $files $dump.Name); $dumpNote += " - ATTACHED (you ticked it)" }
                else { $dumpNote += " - too big to send (Discord limit); send it by hand if asked" }
            } else { $dumpNote += " - summary only (file not attached)" }
        } else { $dump = $null; $dumpNote = "crash dump: none from the last 48 h" }
    } catch { $dumpNote = "crash dump: CrashDumps folder not readable" }
    # [bug-2662/2663/2665] injected-module scan of the minidump MODULE_LIST (file names matched, not paths)
    try {
        if ($dump) {
            $fs = [IO.File]::OpenRead($dump.FullName)
            $br = New-Object IO.BinaryReader($fs)
            if ($br.ReadUInt32() -eq 0x504D444D) {
                $null = $br.ReadUInt32(); $nStreams = $br.ReadUInt32(); $dirRva = $br.ReadUInt32(); $modRva = 0
                for ($i = 0; $i -lt $nStreams -and $i -lt 64; $i++) {
                    $fs.Position = $dirRva + $i * 12
                    if ($br.ReadUInt32() -eq 4) { $null = $br.ReadUInt32(); $modRva = $br.ReadUInt32(); break }
                }
                if ($modRva) {
                    $overlayKeys = @("nvspcap","nvsp","overlay","gameoverlayrenderer","discordhook","rtss","rivatuner","obs-","obs64","fraps","xsplit",
                                     "easyanticheat","beclient","battleye","nahimic","parsec","medal","outplayed","afterburner","reshade","specialk","d3dhook","gfsdk")
                    $fs.Position = $modRva; $nMod = $br.ReadUInt32(); $overlays = @(); $nonMs = @()
                    for ($m = 0; $m -lt $nMod -and $m -lt 1024; $m++) {
                        $fs.Position = $modRva + 4 + $m * 108 + 20; $nameRva = $br.ReadUInt32()
                        $fs.Position = $nameRva; $len = $br.ReadUInt32()
                        if ($len -le 0 -or $len -gt 1040) { continue }
                        $full = [Text.Encoding]::Unicode.GetString($br.ReadBytes($len))
                        $base = (Split-Path $full -Leaf).ToLower()
                        foreach ($k in $overlayKeys) { if ($base -like "*$k*") { $overlays += (Split-Path $full -Leaf); break } }
                        if ($full.ToLower() -notlike "*\windows\*") { $nonMs += $full }
                    }
                    $moduleLines += "=== injected / overlay modules (from crash dump) ==="
                    if ($overlays.Count) {
                        $moduleLines += "!! OVERLAY / CAPTURE / INJECTED SOFTWARE DETECTED - a frequent crash cause:"
                        $overlays | Sort-Object -Unique | ForEach-Object { $moduleLines += "   >> $_" }
                    } else { $moduleLines += "(no known overlay DLLs matched)" }
                    $moduleLines += "=== all non-Microsoft modules loaded at crash ==="
                    $nonMs | Sort-Object -Unique | ForEach-Object { $moduleLines += "   " + (Scrub-Text ($L1.GetString([Text.Encoding]::UTF8.GetBytes($_)))) }
                }
            }
            $br.Close(); $fs.Close()
        }
    } catch { $moduleLines = @("(injected-module scan failed)") }
}

# report_info.txt
$info = New-Object Collections.Generic.List[string]
function Add([string]$s) { $info.Add($s) }
$tagSrc = "MOHCoopReporter|$env:COMPUTERNAME|$env:USERNAME"
$h = [Security.Cryptography.SHA256]::Create()
$tag = ([BitConverter]::ToString($h.ComputeHash([Text.Encoding]::UTF8.GetBytes($tagSrc))) -replace '-', '').Substring(0, 6)
$h.Dispose()
$build = "unknown"
try { $build = (Get-Content (Join-Path $app "installed_manifest.json") -Raw | ConvertFrom-Json).version } catch {}
$engine = ""; $lastMap = ""
if ($logText -match '=> game is version ([^\r\n]+)') { $engine = $Matches[1] }
$mm = [regex]::Matches($logText, 'Server: ([A-Za-z0-9_/.-]+)')
if ($mm.Count) { $lastMap = $mm[$mm.Count - 1].Groups[1].Value }
Add "=== MOH Coop Trilogy report $stamp (desktop) ==="
Add "Report #$tag"
Add "CurrentBuild=$build"; Add "ModVersion=$modVer"; Add "Engine=$engine"; Add "LastMap=$lastMap (from qconsole.log)"
Add "Category=$(if ($Category) { $Category } else { '(not chosen)' })"
# release identity (user requirement): installed manifest version, the mod pak's version, and whether each binary is the
# one the manifest lists (sha256) - a player who launches openmohaa.exe directly never updates
$manSha = @{}
try { foreach ($e in (Get-Content (Join-Path $app "installed_manifest.json") -Raw | ConvertFrom-Json).files) { $manSha[(Split-Path $e.path -Leaf).ToLower()] = ([string]$e.sha256).ToLower() } } catch {}
$exeMd5 = "?"; $exeState = "(no manifest)"; $dllDiff = 0
Add ""; Add "=== binaries: md5, and the sha256 check against installed_manifest.json ==="
foreach ($n in @("openmohaa.exe", "cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll", "omohaaded.exe")) {
    $p = Join-Path $app $n
    if (Test-Path $p) {
        $fi = Get-Item $p; $md5 = (Get-FileHash $p -Algorithm MD5).Hash.ToLower(); $sha = (Get-FileHash $p -Algorithm SHA256).Hash.ToLower()
        $st = if (-not $manSha.Count) { "none" } elseif (-not $manSha.ContainsKey($n)) { "not listed" } elseif ($manSha[$n] -eq $sha) { "MATCH" } else { "DIFFERS" }
        if ($n -eq "openmohaa.exe") { $exeMd5 = $md5.Substring(0, 8); $exeState = @{ "MATCH" = "= manifest"; "DIFFERS" = "**DIFFERS from the manifest**" }[$st]; if (-not $exeState) { $exeState = "(not in a manifest)" } }
        elseif ($st -eq "DIFFERS") { $dllDiff++ }
        Add ("{0,-22} {1,10:N0}  md5 {2}  manifest: {3,-10} {4}" -f $n, $fi.Length, $md5, $st, $fi.LastWriteTime.ToString("yyyy-MM-dd HH:mm"))
    } else { Add ("{0,-22} (not present)" -f $n) }
}
$updAge = ""
try { $ul = Get-Item (Join-Path $app "updater.log"); $updAge = [math]::Round(((Get-Date) - $ul.LastWriteTime).TotalHours, 1) } catch {}
$mv = ($build -replace '^v', ''); $dv = ($modVer -replace '^v', '')
$relLine = "Release: **$(if ($build -and $build -ne 'unknown') { 'v' + $mv } else { 'no manifest (manual/dev install)' })** (installed manifest) | mod $modVer | exe $exeMd5 $exeState | updater last ran: $(if ($updAge -ne '') { "$updAge h ago" } else { 'never (no updater.log)' })"
if ($build -ne 'unknown' -and $modVer -ne 'unknown' -and $mv -ne $dv) { $relLine += " | **VERSION MISMATCH (manifest vs mod pak)**" }
elseif ($dllDiff) { $relLine += " | **a DLL differs from the manifest**" }
Add ""; Add "=== release ==="; Add $relLine
$gpuLine = ""; $osLine = ""
if ($opt.Sys) {
    Add ""; Add "=== system ==="
    $os = Get-CimInstance Win32_OperatingSystem
    $osLine = "$($os.Caption) $($os.Version)"
    Add "OS: $osLine"
    # every adapter in report_info; the headline skips virtual/remote/mirror adapters (Parsec, Meta, RDP, Basic Display)
    foreach ($g in (Get-CimInstance Win32_VideoController | Select-Object -First 4)) {
        Add "GPU: $($g.Name)  driver $($g.DriverVersion)"
        if (-not $gpuLine -and $g.Name -notmatch '(?i)virtual|remote|basic display|parsec|mirror|meta ') { $gpuLine = "$($g.Name) (driver $($g.DriverVersion))" }
    }
    if (-not $gpuLine) { $gpuLine = "(no physical adapter reported)" }
    Add "CPU: $((Get-CimInstance Win32_Processor | Select-Object -First 1).Name)"
    Add ("RAM: {0:N0} MB" -f ($os.TotalVisibleMemorySize / 1KB))
}
if ($opt.Crash -or $opt.Dump) { Add ""; Add "=== crash info ==="; Add $dumpNote; foreach ($l in $moduleLines) { Add $l } }
if ($opt.Inst) {
    Add ""; Add "=== install dir (<app>) ==="
    Get-ChildItem $app -File | ForEach-Object { Add ("{0,12:N0}  {1}  {2}" -f $_.Length, $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm"), $_.Name) }
    Add ""; Add "=== mod content (home\maintt) ==="
    if (Test-Path $mt) { Get-ChildItem $mt -File | ForEach-Object { Add ("{0,12:N0}  {1}" -f $_.Length, $_.Name) } } else { Add "!! home\maintt DOES NOT EXIST !!" }
    $gog = ""
    try { $m = Select-String -Path (Join-Path $app "install_info.txt") -Pattern "^GogPath=(.*)$"; if ($m) { $gog = $m.Matches[0].Groups[1].Value } } catch {}
    if ($gog -and (Test-Path $gog)) {
        Add ""; Add "=== game dir - exe/dll files ==="
        Get-ChildItem $gog -File | Where-Object { $_.Extension -in ".exe", ".dll" } | ForEach-Object { Add ("{0,12:N0}  {1}  {2}" -f $_.Length, $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm"), $_.Name) }
        foreach ($sub in @("main", "mainta", "maintt")) {
            $d = Join-Path $gog $sub
            if (Test-Path $d) { Add ""; Add "=== game dir $sub - pk3/dll/cfg ==="; Get-ChildItem $d -File | Where-Object { $_.Extension -in ".pk3", ".dll", ".cfg" } | ForEach-Object { Add ("{0,12:N0}  {1}" -f $_.Length, $_.Name) } }
        }
    }
    $p = Join-Path $app "updater.log"
    if (Test-Path $p) { Scrub-File $p (Join-Path $files "updater.log") (256KB) | Out-Null }
}
# script errors (same markers as the in-game report)
$errAll = [regex]::Matches($logText, "(?m)^[^\n]*(?:Script Error|Couldn't compile|not properly loaded|parse error)[^\n]*")
$errs = New-Object Collections.Generic.List[string]
foreach ($e in $errAll) {
    $s = ($e.Value -replace '^\[[^\]]{0,46}\]\s*', '') -replace '[\x00-\x1f]', ' '
    if ($s.Length -gt 199) { $s = $s.Substring(0, 199) }
    if (-not $errs.Contains($s)) { $errs.Add($s); if ($errs.Count -gt 20) { $errs.RemoveAt(0) } }
}
Add ""; Add "=== script errors: $($errAll.Count) in the log (last $($errs.Count) distinct) ==="
foreach ($e in $errs) { Add $e }
Add ""; Add "=== privacy ==="
Add "Scrubbed: home paths -> <HOME>, Windows user and PC name, IP addresses, webhook URLs, cd keys, password/rcon/token/guid values, other players' userinfo, join codes."
Add "Never read: the cd-key file, unlock/save files. Settings: allowlist only."
Scrub-Text (($info.ToArray()) -join "`r`n") | ForEach-Object { [IO.File]::WriteAllBytes((Join-Path $files "report_info.txt"), $L1.GetBytes($_)) }
$desc = (Scrub-Text $Description.Trim()); $st = (Scrub-Text $Steps.Trim())
[IO.File]::WriteAllText((Join-Path $files "user_description.txt"), "What happened: $desc`r`nSteps to reproduce: $(if ($st) { $st } else { '(none given)' })`r`n", [Text.Encoding]::UTF8)

# ---------------------------------------------------------------------------------------------------- 3. message
function Clean1([string]$s, [int]$max) { $s = ($s -replace '\^[0-9]', '' -replace '[\x00-\x1f\x7f]', ' ' -replace '`', "'").Trim(); if ($s.Length -gt $max) { $s = $s.Substring(0, $max) }; return $s }
$names = @(Get-ChildItem $files -File | ForEach-Object { $_.Name }) ; $names = [string[]]$names; [Array]::Sort($names, [StringComparer]::Ordinal)
$msg = New-Object Text.StringBuilder
[void]$msg.Append("**MOH Coop report** #$tag ($stamp) - desktop$(if ($Category) { ' - **' + (Clean1 $Category 40) + '**' })`n")
[void]$msg.Append("$relLine`n")
[void]$msg.Append("Last map ``$(Clean1 $lastMap 64)``$(if ($engine) { ' | ' + (Clean1 $engine 90) })`n")
if ($opt.Sys) { [void]$msg.Append("System: $(Clean1 $gpuLine 120) | $(Clean1 $osLine 90)`n") }
$d1 = Clean1 ($desc -replace '\r?\n', ' / ') 900
[void]$msg.Append("**What happened:** $d1`n")
if ($st) { [void]$msg.Append("**Steps:** $(Clean1 ($st -replace '\r?\n', ' / ') 500)`n") }
if ($errAll.Count -gt 0) {
    $blk = "**Script errors:** $($errAll.Count) in log (last $([math]::Min(3, $errs.Count)))`n```````n"
    foreach ($e in ($errs | Select-Object -Last 3)) { $blk += (Clean1 $e 160) + "`n" }
    $blk += "```````n"
    if ($msg.Length + $blk.Length -lt 1740) { [void]$msg.Append($blk) } else { [void]$msg.Append("**Script errors:** $($errAll.Count) in log (see report_info.txt)`n") }
}
[void]$msg.Append("Attached: $zipName ($($names -join ', '))")
if ($DryRun) { [void]$msg.Append("`n(dry run - not posted)") }
$content = $msg.ToString(); if ($content.Length -gt 1990) { $content = $content.Substring(0, 1990) }
$payload = (@{ content = $content; allowed_mentions = @{ parse = @() }; flags = 4 } | ConvertTo-Json -Depth 4 -Compress)
[IO.File]::WriteAllBytes((Join-Path $work "payload.json"), [Text.Encoding]::UTF8.GetBytes($payload))

# ---------------------------------------------------------------------------------------------------- 4. review
if (-not $NoGui) {
    $f = New-Object Windows.Forms.Form
    $f.Text = "Report a Problem - this is exactly what will be sent"
    $f.Size = New-Object Drawing.Size(720, 600); $f.StartPosition = "CenterScreen"; $f.FormBorderStyle = "FixedDialog"; $f.MaximizeBox = $false
    $tv = New-Object Windows.Forms.TextBox; $tv.Multiline = $true; $tv.ReadOnly = $true; $tv.ScrollBars = "Both"; $tv.Font = New-Object Drawing.Font("Consolas", 9)
    $tv.Location = New-Object Drawing.Point(12, 12); $tv.Size = New-Object Drawing.Size(680, 330); $tv.Text = $content -replace "`n", "`r`n"
    $lv = New-Object Windows.Forms.ListBox; $lv.Location = New-Object Drawing.Point(12, 352); $lv.Size = New-Object Drawing.Size(680, 150)
    foreach ($n in $names) { [void]$lv.Items.Add(("{0,-24} {1,10:N0} KB" -f $n, [math]::Ceiling((Get-Item (Join-Path $files $n)).Length / 1KB))) }
    $of = New-Object Windows.Forms.Button; $of.Text = "Open folder"; $of.Location = New-Object Drawing.Point(12, 514); $of.Size = New-Object Drawing.Size(110, 30)
    $of.Add_Click({ Start-Process explorer.exe "`"$files`"" })
    $sd = New-Object Windows.Forms.Button; $sd.Text = "Send"; $sd.Location = New-Object Drawing.Point(476, 514); $sd.Size = New-Object Drawing.Size(100, 30); $sd.DialogResult = "OK"
    $cn = New-Object Windows.Forms.Button; $cn.Text = "Cancel"; $cn.Location = New-Object Drawing.Point(592, 514); $cn.Size = New-Object Drawing.Size(100, 30); $cn.DialogResult = "Cancel"
    $f.Controls.AddRange(@($tv, $lv, $of, $sd, $cn)); $f.CancelButton = $cn
    if ($f.ShowDialog() -ne "OK") { Remove-Item $work -Recurse -Force; exit 0 }
}

# ---------------------------------------------------------------------------------------------------- 5. zip + post
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zp = Join-Path $work $zipName
[IO.Compression.ZipFile]::CreateFromDirectory($files, $zp, [IO.Compression.CompressionLevel]::Optimal, $false)
$zb = [IO.File]::ReadAllBytes($zp)
$pj = [IO.File]::ReadAllBytes((Join-Path $work "payload.json"))
$bd = 'hzmrep' + [Guid]::NewGuid().ToString('N')
$ms = New-Object IO.MemoryStream
function Wr([string]$s) { $x = [Text.Encoding]::ASCII.GetBytes($s); $ms.Write($x, 0, $x.Length) }
Wr ("--$bd`r`nContent-Disposition: form-data; name=`"payload_json`"`r`nContent-Type: application/json`r`n`r`n"); $ms.Write($pj, 0, $pj.Length); Wr "`r`n"
Wr ("--$bd`r`nContent-Disposition: form-data; name=`"files[0]`"; filename=`"$zipName`"`r`nContent-Type: application/zip`r`n`r`n"); $ms.Write($zb, 0, $zb.Length); Wr "`r`n"
Wr "--$bd--`r`n"
$body = $ms.ToArray(); $ct = "multipart/form-data; boundary=$bd"

if ($DryRun) {
    New-Item -ItemType Directory -Force -Path $DryRun | Out-Null
    Copy-Item (Join-Path $work "payload.json") $DryRun -Force
    Copy-Item $zp $DryRun -Force
    [IO.File]::WriteAllBytes((Join-Path $DryRun "multipart_body.bin"), $body)
    $h = [Security.Cryptography.SHA256]::Create(); $hx = ([BitConverter]::ToString($h.ComputeHash($body)) -replace '-', '').ToLower(); $h.Dispose()
    Set-Content -Path (Join-Path $DryRun "request.txt") -Encoding ASCII -Value @('DRY RUN - nothing was sent.', 'POST <webhook withheld>', "Content-Type: $ct",
        "Content-Length: $($body.Length)", "sha256: $hx", 'parts:', "  payload_json  application/json  $($pj.Length) bytes",
        "  files[0]  $zipName  application/zip  $($zb.Length) bytes  ($($names -join ', '))")
    Remove-Item $work -Recurse -Force
    Write-Host "Dry run written to $DryRun"
    exit 0
}

$why = Rate-Check
$Webhook = Get-Webhook
$sent = $false
if (-not $why -and $zb.Length -gt 9961472) { $why = "The report is larger than Discord allows (untick the crash dump)." }
if (-not $why -and $Webhook) {
    Write-Host "Sending report to the mod team..." -ForegroundColor Cyan
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    try {
        Invoke-WebRequest -Uri $Webhook -Method Post -ContentType $ct -Body $body -UseBasicParsing -TimeoutSec 60 -MaximumRedirection 0 | Out-Null
        $sent = $true; Rate-Record
    } catch {
        $code = 0; try { $code = [int]$_.Exception.Response.StatusCode } catch {}
        $why = if ($code -eq 429) { "Discord is busy - try again in a minute." } else { "Sending failed (HTTP $code)." }
    }
}
$Webhook = $null
$zipDesk = Join-Path ([Environment]::GetFolderPath("Desktop")) $zipName
Copy-Item $zp $zipDesk -Force
Remove-Item $work -Recurse -Force
if ($sent) {
    Write-Host ""; Write-Host "Report sent to the mod team. A copy is on your desktop: $zipName" -ForegroundColor Green
} else {
    Write-Host ""; if ($why) { Write-Host $why -ForegroundColor Yellow }
    Write-Host "Report saved to your desktop: $zipName" -ForegroundColor Yellow
    Write-Host "Send that file to the mod team (Discord/email)."
    Start-Process explorer.exe "/select,`"$zipDesk`""
}
Write-Host ""
Read-Host "Press Enter to close"
