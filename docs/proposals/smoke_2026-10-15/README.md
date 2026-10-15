# Reinforcement smoke screens (2026-10-15) - handover

Branch `smoke-next` (worktree `C:\mohaa-coop-dev\hzm-mod-smoke`, from `combo-1.10.29`). User: "when these reinforcements throw
their smoke grenades they usually dont work effectively or obstruct view, the point is to conceal."

## Status
- STEP 1 (code, unproven in-engine): new `coop_mod/smokescreen.scr`, `officer.scr` hooks, `precache.scr` line, fixes-pak tik
  `docs/tools/assets/fixes/models/fx/coop_screensmoke.tik` (+ manifest entry "new"). Harness `tools/` (ss_run.py, ss_drv.scr, smokelib.py).
- NEXT: harness proof (screens + AI cansee numbers), tuning, buglog.

## What was wrong (code reading)
- Elite squad (`coop_elite_smoke_barrage`): smoke at the squad's OWN spawn point, 10-18 s after landing, removed after 20 s.
- Grenadier (`coop_grenade_lob_loop`): every 4th throw put the smoke on the TARGET PLAYER's feet, removed after 16 s.
- Both used `tehao_thickSmoke` (dark grey 3/s wisp, rises at accel z 60, life 8) + a stock M18 pop: reads as a campfire.
- Nothing waited for the cloud.

## What it does now
- `smokescreen.scr::squad_screen` (elite squad): when the nearest player is within 1900u, a 3-canister wall (300u apart, across the
  line) goes at 55% of the gap (400..1100u from the squad, >=300u from the player); the squad is held (`flags["coop_smokeHold"]`,
  honoured by `coop_wave_hunt`) for 5 s, then advances through it. Budget: <=2 screens alive, one per 20 s level-wide.
- `smokescreen.scr::lob` (grenadier): same placement from thrower to target; thrower held 4 s; falls back to a normal grenade when
  no screen is possible (<700u, budget).
- `models/fx/coop_screensmoke.tik`: a real engine `SmokeGrenade` (server SmokeSprites -> `Actor::CanSee` obfuscation, so AI inside
  or behind the cloud do NOT see the players: fair both ways, requirement 3 is met by this, not by new code) with `maxalpha 1`,
  72 live puffs, life 60 + spawnlife 24 (opaque ~+3..+60 s, thins by ~+84 s), slow drift, low; client bank = vsssource.spr
  (white-grey), same recipe as `coop_smokescreen.tik`. Server radius = scale/2; growth = start*scalerate/s on both halves.

## Integration
- Run `python docs/tools/gen_fixes_pak.py build` (the tik is a "new" member; must NOT sit in the mod tree).
- officer.scr touches: wave_hunt hold check, elite spawn call, grenadier loop; removed `coop_elite_smoke_barrage`, `coop_smoke_cleanup`.
