# The officer's MG42 team - 2026-10-15

User: "Just like the paratroopers can deploy 30 cals now, I think the mg squad the officer calls should deploy an mg42 covering the
officer. Ideally they are more accurate and lethal than standard mg squads." Then: "should also be called in even after the officer
is killed and radio is active".

**Status (keep current):** BUILT AND PROVEN IN THE PRIVATE HARNESS, not deployed, not pushed. Mod branch `mgteam-next`
(worktree `C:\mohaa-coop-dev\hzm-mod-mgteam`, from `combo-1.10.29` `4c10b581`): commits `8ac5c64c` (the build), `e396f4b9` (staging
walk + takeover walk), `64685ca0` (`coop_reinfMgAim`, last-seat penalty, cvars in autoexec). Brace scans OK on every touched .scr;
`check_mp_isolation.py --mod hzm-mod-mgteam` 21 passed, 0 failed. No file under `textures/` or `models/`. buglog bug-3978..3980.

## What it is

A Wehrmacht or Elite call (wave type 0 / 1) - from the officer, and also from the post-officer radio calls (`reinf.scr::rnf_radio_calls`
goes through the same `coop_call_reinforcements`) - brings, `coop_reinfMgChance` percent of the time, an MG42 team instead of the
rifle squad: gunner, assistant, optional spotter. They walk to the **anchor** (the officer while he lives, else the radio the players must
reach), find a place from which the gun covers it, set the gun up and fire.

* **Placement = the .30 cal's.** `parasquad.scr` mgPlan / mgSetup / mgTend / mgHold / mgPackup / mgFlee / nadeWatch are reused through a
  pseudo-squad (`newSquad`): `level.coop_psqFoe[sid] = "player"` (no hold-fire for a player in the muzzle line, no lane keeping),
  `Apos` = anchor, `Ctr` = search centre (the plan looks round the anchor, not the walking gunner), `Ayaw` = the way the players come
  (centroid of `trail` marks 250-1500 u out, else the nearest player), `Off` = the officer (mateInFront also keeps him out of the muzzle
  line). Cover (A) before sandbags (C); the tripod stays off. The site score is `reinf_mg.scr::rmg_score`: near the anchor (110-380 u),
  high over it, beside/behind rather than in front, gun line down the lane.
* **Gun** = retail `models/statweapons/mg42_gun.tik` (no new asset), retail bipod/sandbags, `mg42ammoboxwbelt` box, belt 250 + 1 spare
  (`parasquad_gun.scr::belt42`: coopammo/coopaibelt, **no** coopheatrates so the MG42's own barrel applies; the gunner stops at 45 of 100).
* **Fire control** (`rmg_fire`, hooked into `mgHold`): instead of the engine's "track the gunner's enemy" (with the global aim wander
  `coop_mg42AiAimOff` 100 = +-100 u at 1000 u, spread 150-450) the script picks the player who threatens the anchor (nearest to it, a
  line to it counts 250, sticky), aims at the chest + velocity * lead, spread 70, then settle -> burst -> pause.
* **Fair:** unpack in plain sight (`coop_reinfMgSetup` 2 s) + lowering (~1.2 s) + mount (~1.5 s) before any round; 0.7 s settle on each
  new target; bursts 0.6-1.1 s, pauses 0.9 s +0..0.7; the MG42 overheat; the gun is a TurretGun with a gunner of 140 hp (scaled), so it
  can be suppressed, flanked, grenaded, killed.
* **Crew:** gunner dies -> assistant (then spotter) walks to the seat and mounts the same gun (`rmg_succ`). Whole team dead -> the gun
  stays, belt as it was (>= 25), `mgLeft`, players can use it. No site after 4 plans, or both belts empty -> the team is released to
  `coop_wave_hunt` as an ordinary section.
* **Relocates** (`rmg_brain` -> `level.coop_rmgReloc[sid]` -> `mgPackup`, new seat != old for 90 s): flanked (a player > 62 degrees off the
  gun line, 80-520 u, line to the gun, 2 ticks), anchor > 650 u away (3 s), no target for 20 s with players within 1500 u of the anchor;
  mgTend's own `enemy_out_of_arc` / `enemy_masked` (25 s); a grenade within 300 u (nadeWatch -> mgFlee: runs, waits, returns).

## Cvars (all in `autoexec.cfg`, read live, unset = default; everything behind `coop_reinfSmart`)

| cvar | default | |
|---|---|---|
| `coop_reinfMg` | 1 | this team (own sub-switch); 0 = never |
| `coop_reinfMgChance` | 50 | percent of Wehrmacht/Elite calls that bring it |
| `coop_reinfMgSpotter` | 1 | third man |
| `coop_reinfMgSpread` | 70 | `aibulletspread` (the .30 cal 150, retail nests 300-450) |
| `coop_reinfMgLead` | 0.25 | seconds of target velocity added to the aim |
| `coop_reinfMgSettle` | 0.7 | seconds from a new target to the first round |
| `coop_reinfMgBurstMin` / `Max` | 0.6 / 1.1 | burst length, s |
| `coop_reinfMgPause` | 0.9 | s between bursts (+0..0.7) |
| `coop_reinfMgSetup` | 2 | s he unpacks before the gun goes down |
| `coop_reinfMgHp` | 140 | gunner health before player scaling |
| `coop_reinfDebug` | 0 | `^~^~^ RMG` lines (this file) and `RNF` lines |

## Files (all under `coop_mod/` unless noted)

* NEW `reinf_mg.scr` - everything above.
* `officer.scr` - one block in `coop_call_reinforcements` before the type-0 dispatch (`rmg_wave`; sets the type to 99 when the team took the call).
* `reinf.scr` - one condition in `rnf_idle_check` (`flags["coop_rmgPost"]`: the posted assistant/spotter are not "idle").
* `parasquad.scr` - the `[mgteam]` lines: `playerInFront` takes an optional sid; `mateInFront` also checks `coop_psqOff`; `mgLane` skips for
  `Foe == "player"`; `mgPlan` search centre; `mgSite` score hook; `mgSetup` unpack beat, gun/crate model, belt42, `rmg_tune`; `mgHold`
  fire-control hook. Every hook is inert unless `local.a.coop_rmgOn == 1` / `Foe == "player"`, so the paratroopers are unchanged.
* `parasquad_gun.scr` - `belt42`.
* `autoexec.cfg` - the cvars.

| `coop_reinfMgAim` | 1 | 0 = the stock engine fire control with the .30 cal's spread (the "standard nest", for A/B and as a fallback) |

## Proof (private harness G:/mohaa-hudfeed5 via `docs/tools/harness_guard.py`, DISPLAY2, engine `screenshotJPEG`; release DLLs = a copy of the live set)

Map m3l2, the map's REAL officer (the player is moved next to him; the driver `tools/mg_drv.scr` kills every non-German actor - the map's
allied captain shoots the team on arrival - and every German but him), wave mask = Wehrmacht only, `coop_reinfMgChance 100`.
Logs: `tools/logs/run_*.txt` (summaries) and `tools/logs/mg_*.rmg.txt` (the RMG / MG / PSQ lines of each qconsole); frames, qconsole and
the raw runs are in `H:\hzm_archive\mgteam\`. **0 Script Errors in every session** (t1-t6, c1-c4, l0/l1/l0b/l1b, r1/r2).

* **Call -> deployed covering the officer (t5, t6, c4).** `RMG team sid=1 n=3 anchor=officer` -> `stage runto pathdist=2172` ->
  `staged` (12-18 s walk from an unseen entry 2000 u away) -> `unpack secs=2` -> `gun up ... mode=C` about 16-27 s after the call. The gun
  stands on the sandbags 220-390 u from the officer and 40 u above him, firing down the lane the player is in
  (e.g. officer (-3098,-2650), gun (-3175,-2795,85), `offd=227`). Stills `media/mgteam_*.jpg`.
* **Engages the player.** `RMG target ... d=796 fromAnchor=781 settle=0.700`, then `burst done len=1.000 ammo=242 heat=24`,
  `burst barrel len=0.600 heat=49` (stops at the barrel limit, the MG42 overheat applies), `burst friend_in_front` (holds fire with the
  officer in the muzzle line). Rhythm: 0.6-1.1 s bursts, ~1.2 s gaps.
* **Gunner dies -> assistant takes over (t6, c2, c4, r1).** `gunner down, k=2 takes over, gun up=1` -> `takeover done k=2` 2.3 s later, the
  same gun, belt as it was (`ammo=201`). `media/mgteam_takeover.gif` (22 frames, QA'd: no clipping, no red hit flash, the dead gunner on the
  gun, the spotter running in, the assistant kneeling at it) and `media/mgteam_gun_assistant_takeover.jpg`.
* **Radio phase (t6).** `killteam` (the gun is left: `team down: gun left for the players`), the officer dies, the radio's own call
  (`RNF radio call n=1 snd=coop_radio_german_reinf4`) -> `RMG team sid=2 n=3 anchor=radio at=(-3172,-2651,94)` -> staged -> `gun up`
  at (-3175,-2795,85) covering the radio, 227 u from it, bursts at the player. `media/mgteam_radio_phase_gun_800u.jpg`.
* **Relocation (r1, r2).** Player steps to the gun's flank 280 u out: `relocate why=flanked` -> `pack up why=flanked` 0.05 s later -> `gun up`
  8-16 s afterwards at a new site facing the new lane (yaw 0.4 -> 12; in r1 the gunner died meanwhile and the assistant did it fresh).
* **Lethality, gun only (l1b vs l0b; officer, guards and the team's riflemen muted; mortal player, 100000 hp, standing in the open 700 u
  from the officer, 61 s of game time, one run each - not statistics):** script fire control (`coop_reinfMgAim 1`) **85 hp/s**, 17 bursts;
  stock engine fire control (`coop_reinfMgAim 0`, the standard nest: aim wander, spread 150, random bursts) **3.9 hp/s**. A 750 hp player
  standing still in the open would last about 9 s of fire from a gun that took ~5 s to set up and 0.7 s to settle on him.

## NOT done / not verified (handover)

1. Other maps, a second player, a dedicated server, any MP map (`rmg_wave` is only reached through the officer's wave dispatch; the
   MP isolation check is green), coop-MP lag with the extra scan (one `nadeWatch` thread per team - 64 entity slots a frame - as for the paras).
2. Mode A (cover/sill) sites were never chosen on m3l2 (every run picked C, sandbags): the A path is the .30 cal's own, proven there.
3. The back-carried gun (`models/weapons/mg42portable.tik` at the .30 cal's offsets) was not looked at close up; the gunner's ammo belt (a
   retail model detail) is visible in `media/mgteam_gunner_ammo_belt.jpg`. The retail `mg42ammoboxwbelt.tik` stands in for the ammo can:
   position/scale not inspected beside the gun.
4. No GIF of the SET-UP (arrival -> unpack -> bipod -> gun -> mount): the harness camera is the player, whom the officer's men shoot (red
   flashes), and the road is hedge-lined; `tools/mg_sess2.py` + `camgun` get a sequence (c1-c4) but the usable one is the takeover.
5. Tuning is one run each. 85 hp/s for a stationary target is the deliberate "more lethal"; if it is too much in play raise
   `coop_reinfMgSpread` (70 -> 100), `coop_reinfMgSettle`, `coop_reinfMgPause`, or lower `coop_reinfMgChance` - all live.
6. The wave type: the team replaces a type-0 / type-1 roll, so the "Full Deck" challenge still credits the rolled type; the feed key is `w_mg`.
7. After the officer dies `coop_call_reinforcements` ends if `level.coop_officer` is NULL (the corpse entity is gone); the radio calls then
   bring nothing for ANY wave type - not changed here (reinf.scr is another agent's), but worth a look when the alarm work lands.
8. `docs/TRAPS.md` / `docs/OPEN.md` are at their ceilings: nothing added. Candidates: *an AI MG's engine track cycle aims with a global
   wander (coop_mg42AiAimOff) and cannot be tightened per gun - script fire control with setAimTarget bypasses it*; *`mgLeg` gives up after 2 s
   without movement: a long walk needs its own re-issuing loop (rmg_goto)*; *a harness stand-in officer is not on the death monitor and the map's
   allies shoot it*.

## Merging

`reinf_mg.scr` is new; the hooks are 1 block in `officer.scr::coop_call_reinforcements` (before `if( local.r == 0 ){`), 1 condition in
`reinf.scr::rnf_idle_check`, the `[mgteam]` lines in `parasquad.scr`, `belt42` in `parasquad_gun.scr`, the cvars after `coop_aiReact` in
`autoexec.cfg`. Nothing else in the mod changes. Tools: `tools/mglib.py` (harness glue), `mg_drv.scr` (test-only overlay driver), `mg_sess1..4.py`
(call+takeover+radio / close-up frames / lethality A/B / relocation), `mk_sheet.py` (contact sheets).
