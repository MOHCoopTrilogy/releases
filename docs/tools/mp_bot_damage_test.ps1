# [bug-2574] Bots-only dedicated-server PvP damage probe. Identical for the before and after runs.
# Starts omohaaded on dm/mohdm1 (Team Match) with 4 bots and coop_dmgProbe 1, reads only this run's log lines,
# and reports whether player-on-player hits ever lower a victim's health. Stops the server itself.
param([int]$Seconds = 170, [string]$Map = 'dm/mohdm1', [int]$Gametype = 2)

$dev = 'C:\mohaa-coop-dev'
$gog = 'G:\GOG\Medal of Honor - Allied Assault War Chest'
$srvHome = "$dev\server_home"
$log = "$srvHome\maintt\qconsole.log"
$cfg = "$srvHome\maintt\pvp_probe.cfg"
Set-Content -Path $cfg -Encoding ascii -Value @('set rconpassword kRXYGDbvFdH6arXXaEYjoUGy', 'set sv_maxclients 8', "set g_gametype $Gametype", 'set coop_dmgProbe 1', 'set sv_numbots 4', "map $Map")
$start = 0; if (Test-Path $log) { $start = (Get-Item $log).Length }
$argStr = "+set com_target_game 2 +set fs_basepath `"$gog`" +set com_abnormalExit 0 +set logfile 2 +set dedicated 1 +set fs_homepath `"$srvHome`" +set net_port 12203 +set sv_maxclients 8 +set g_gametype $Gametype +set sv_fps 40 +set sv_maxbots 4 +set sv_numbots 4 +exec pvp_probe.cfg"
$srv = Start-Process -FilePath "$gog\omohaaded.exe" -ArgumentList $argStr -WorkingDirectory $gog -PassThru -WindowStyle Minimized
$deadline = (Get-Date).AddSeconds($Seconds); $txt = ''
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-Path $log) {
        $len = (Get-Item $log).Length; if ($len -lt $start) { $start = 0 }
        $fs = [IO.File]::Open($log, 'Open', 'Read', 'ReadWrite'); [void]$fs.Seek($start, 'Begin')
        $sr = New-Object IO.StreamReader($fs); $txt = $sr.ReadToEnd(); $sr.Close(); $fs.Close()
        if (([regex]::Matches($txt, 'DMG victim=[^\n]*atk=Player')).Count -ge 80) { break }
    }
    if ($srv.HasExited) { break }
}
$exitedEarly = $srv.HasExited
$status = & python "$dev\docs\tools\rcon.py" "status" 2>&1 | Out-String
if (-not $srv.HasExited) { Stop-Process -Id $srv.Id -Force }
$lines = $txt -split "`n"
"server exited on its own: $exitedEarly"
"map load problems: " + (($lines | Select-String -Pattern "Can't find map|ERROR|Error:" | Select-Object -First 3 | ForEach-Object { $_.Line.Trim() }) -join ' || ')
"MP init lines: " + (($lines | Select-String -SimpleMatch 'MP init').Count)
$dmg = @($lines | Where-Object { $_ -match '\^~\^~\^ DMG ' })
"DMG lines: $($dmg.Count)"
$pvp = @($dmg | Where-Object { $_ -match 'atk=Player' })
"PvP DMG lines: $($pvp.Count)"
$hp = @($pvp | ForEach-Object { if ($_ -match 'hp=(-?\d+)') { [int]$Matches[1] } })
"PvP victim hp values seen: " + (($hp | Sort-Object -Unique) -join ',')
"PvP hits on a victim already below 100 hp: " + (@($hp | Where-Object { $_ -lt 100 }).Count)
"--- first PvP lines ---"; $pvp | Select-Object -First 8
"--- team/bot lines ---"; $lines | Select-String -Pattern 'joined|[Bb]ot' | Select-Object -First 8 | ForEach-Object { $_.Line.Trim() }
"Script Error count: " + (($lines | Select-String -SimpleMatch 'Script Error').Count)
"--- rcon status ---"; $status
exit 0
