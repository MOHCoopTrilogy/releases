# DEATH_HANG Fix (outstanding item #4)

Date: 2026-06-24
Status: STAGED ONLY (no rebuild/launch; a re-test is running)

## Problem
During the Phase-2 death test, the player intermittently failed to respawn
within the 15s single-sample verify window (seen on m2l1 / m4l2 / m6l2b / t3l1),
logging `MAPTEST2_DEATH_HANG`.

Root cause: the spawn_clicker's mid-map respawn click sometimes missed
(`[CLICKER] SDL window not found - skipping spawn click`), and the script-side
verify was a single check at +15s with no retry. One missed click = false HANG.

## Files edited (only these two)
- `hzm-mohaa-coop-mod/coop_mod/maptest_phase2.scr`  (the .scr at C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod\)
- `spawn_clicker.ps1`  (C:\mohaa-coop-dev\spawn_clicker.ps1)

No other coop_mod files, main.scr, player.scr, watchdog, maptest.scr, or
maptest_waypoints.scr were touched.

---

## 1) maptest_phase2.scr - bounded-poll death verify (replaces `wait 15` + one-shot)

Old behavior: emit `MAPTEST2_RESPAWN_NEEDED`, `wait 15`, then a single check of
`$player[1].health`. A single missed clicker click in that 15s window =
false `MAPTEST2_DEATH_HANG`.

New behavior (mohaa-script-safe: flag + counter in the while condition, no
`break`, single-line conditions only):

```
println( "^~^~^ MAPTEST2_RESPAWN_NEEDED " + local.cur )

local.alive   = 0
local.dtick   = 0
while( local.alive == 0 && local.dtick < 20 ){
	wait 2
	local.dtick = local.dtick + 1
	if( $player.size > 0 && $player[1].health > 0 ){ local.alive = 1 }
	if( local.alive == 0 && int( local.dtick / 3 ) * 3 == local.dtick ){ println( "^~^~^ MAPTEST2_RESPAWN_NEEDED " + local.cur ) }
}

if( local.alive == 1 ){
	println( "^~^~^ MAPTEST2_DEATH_OK " + local.cur )
} else {
	if( $player.size > 0 ){
		println( "^~^~^ MAPTEST2_DEATH_HANG " + local.cur + " health=0" )
	} else {
		println( "^~^~^ MAPTEST2_DEATH_HANG " + local.cur + " no player" )
	}
}
```

Logic:
- Poll up to ~40s: 20 iterations x `wait 2` = 40s ceiling (vs. the old single 15s).
- Declare `MAPTEST2_DEATH_OK` as SOON as `$player[1].health > 0` (early exit via
  the `local.alive == 0` while condition - no `break`, which mohaa script cannot use).
- Re-emit `MAPTEST2_RESPAWN_NEEDED` every 3 ticks (`int(dtick/3)*3 == dtick`, the
  same modulo idiom the file already uses for batch_limit) = ~every 6s, so the
  clicker keeps getting fresh respawn triggers. The initial emit before the loop
  fires the clicker immediately.
- Only log `MAPTEST2_DEATH_HANG` if still dead after the full ~40s. Keeps the
  existing two HANG variants (`health=0` vs `no player`) and the existing
  `MAPTEST2_DEATH_OK` banner.

Parse hygiene verified: ASCII, no BOM (file starts with `//`), single-line
`&&`/`||` conditions, `$player` 1-indexed, braces balanced (40 open / 40 close).

---

## 2) spawn_clicker.ps1 - harden window find + mid-map respawn click

### a) Retry the EnumWindows lookup before giving up (Click-GameCenter)
Previously a single `Find-SDLWindow` miss logged "SDL window not found - skipping
spawn click" and bailed. Now it retries 5 times (~400ms apart) so transient
un-findable states (alt-tab, focus churn, transient minimize) right when the
respawn click is due no longer skip:

```
$hwnd = [IntPtr]::Zero
for ($try = 1; $try -le 5; $try++) {
    $hwnd = Find-SDLWindow
    if ($hwnd -ne [IntPtr]::Zero) { break }
    Log "SDL window not found (try $try/5) - retrying..."
    Start-Sleep -Milliseconds 400
}
if ($hwnd -eq [IntPtr]::Zero) { Log "SDL window not found after 5 tries - skipping spawn click"; return }
```

The click mechanism that already works on map-load (ShowWindow restore +
SetForegroundWindow + SetCursorPos center + mouse_event left down/up) is
UNCHANGED below this point - only the window acquisition was hardened.

### b) Mid-map respawn now uses the same reliable click, twice
The `MAPTEST2_RESPAWN_NEEDED` branch already routed through `Click-GameCenter`
(identical mechanism to `MAPTEST_LOADED`). Hardened so a single missed click
doesn't cost a whole script poll cycle:

```
if ($newText -match '\^\~\^\~\^ MAPTEST2_RESPAWN_NEEDED (\S+)') {
    $map = $Matches[1]
    Log "MAPTEST2_RESPAWN_NEEDED: $map - waiting 4s then clicking respawn..."
    Start-Sleep -Seconds 4
    Click-GameCenter
    Start-Sleep -Milliseconds 800
    Click-GameCenter
    $mapActive = $true
    $lastClick = Get-Date
}
```

Changes vs. old:
- Wait reduced 8s -> 4s (script now re-emits ~every 6s, so we don't need to sit
  on the first signal as long).
- Two clicks with an 800ms settle (each via the retrying Click-GameCenter, which
  always does SetForegroundWindow + center left-click on the SDL window).
- `$mapActive = $true` so the existing 10s heartbeat ALSO keeps re-clicking during
  recovery (previously the respawn branch left mapActive as-is).

PowerShell 5.1 valid: no `&&`/`||`, no ternary; full-file parse verified clean
via `[Parser]::ParseFile` (0 errors). (The pre-existing UTF-8 BOM on line 1 was
already present and is harmless for a .ps1.)

---

## Combined effect
- Clicker is far less likely to skip the respawn click (5x window-find retry +
  double-click + heartbeat during recovery).
- Even if a click is still missed, the script polls for up to 40s and re-fires
  the respawn signal ~every 6s, declaring DEATH_OK the instant the player is alive.
- `MAPTEST2_DEATH_HANG` now only logs after a genuine ~40s failure to respawn,
  eliminating the single-sample false positives on m2l1 / m4l2 / m6l2b / t3l1.
