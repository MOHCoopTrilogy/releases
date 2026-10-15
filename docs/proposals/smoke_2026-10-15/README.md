# Reinforcement smoke screens (2026-10-15) - handover

Branch `smoke-next` (worktree `C:\mohaa-coop-dev\hzm-mod-smoke`, from `combo-1.10.29`). User: "when these reinforcements throw
their smoke grenades they usually dont work effectively or obstruct view, the point is to conceal."

## Status: BUILT + PROVEN in a private harness (not deployed, not played by the user)
Media: `media/smoke_screen.gif` (27 frames, player's view: thrown, builds, squad hidden, men run out of the bank), stills
`media/smoke_0..4_*.jpg`, contact sheets `media/contact_x7*.jpg`. Raw runs (frames + qconsole) moved to
`H:\hzm_archive\smoke_2026-10-15\runs`.

## What was wrong (code reading)
- Elite squad (`coop_elite_smoke_barrage`): smoke at the squad's OWN spawn point, 10-18 s after landing, removed after 20 s.
- Grenadier (`coop_grenade_lob_loop`): every 4th throw put the smoke on the TARGET PLAYER's feet, removed after 16 s.
- Both used `tehao_thickSmoke` (dark grey 3/s wisp, life 8, rises at accel z 60 = a campfire) + a stock M18 pop (spawnrate 1.5,
  ~100u puffs): no bank, no height, no duration. Nothing waited for the cloud.

## What it does now
- `coop_mod/smokescreen.scr` (new). `squad_screen` (elite squad, called from `coop_spawn_elite_squad`): 0.5 s after landing, as soon as
  the nearest player is within 1900u (and >= 700u), a 3-canister wall (380u apart, across the line) goes at 55% of the gap
  (400..1100u out from the squad, >= 300u from the player). The squad is HELD 8 s for the bank to close, then released through it.
  `lob` (grenadier, every 4th throw in `coop_grenade_lob_loop`): same placement thrower -> target, thrower held 6 s; returns 0 when no
  screen is possible (< 700u / budget) and the loop throws a normal grenade instead. Budget: <= 2 screens alive, one per 20 s level-wide.
- `models/fx/coop_screensmoke.tik` (fixes pak; `docs/tools/assets/fixes/...` + manifest entry "new"): a real engine `SmokeGrenade`.
  Server half = SmokeSprites (radius = scale/2 = 200u, growth start*scalerate per s) which `Actor::CanSee` -> `G_VisualObfuscation`
  counts, `maxalpha 1` = one sprite on the eye-to-eye ray blocks it, so AI inside/behind the cloud do NOT see the players (requirement 3
  is met by the engine's own recipe, no engine change). Client half = white-grey `vsssource.spr` puffs (diameter 330-435u growing),
  offset +-130u wide and 20-160u high, 6/s per canister (~150 live), life 26, drift 10u/s: low bank. Emitter life 60 + spawnlife 26 =
  opaque from ~+10 s to ~+60 s, gone by ~+86 s. No new texture/model: sprite, canister model and sounds are stock.
- Hold = `flags["coop_smokeHold"]` (read by `coop_wave_hunt`) + `enableEnemy 0` + `anim_scripted "idle"` + `coop_aiDisabled 1`.
  All four are needed (bug-3976): a run already ordered survives enableEnemy 0, and `reinf.scr::rnf_idle_watch` kicks a still man after
  ~10 s unless `coop_aiDisabled` is set. Release undoes them and re-aims (`attackplayer`).
- The overhead star (`+coopboss`, cgame) is dropped while a man hides and returns 9 s after release (`coop_smokeMarker 1` keeps it
  on): the star otherwise marks the squad THROUGH the cloud. ASSUMPTION - say if the user wants the markers always on.

## Proof (m3l2, clearing at pair candidate 4, player (-4295,-6770), squad staged 1350u east; harness `tools/`)
- Real flow (`SSREAL=1 SSCAND=4 python tools/ss_fxrun.py x7 m3l2`): throw at +0.5 s, `n=3` canisters, squad held at 1106u for 8 s,
  released, closes 915 -> 161u through the bank. Frames: first puffs +2 s, ~closed by +8-10 s, solid white wall, squad invisible, men
  appear only as they come out of the left end. Frame time flat at ~17 ms (60 fps cap) before / while the bank stands (RTX 5070 Ti).
- AI visibility A/B (`SSAB=A|B`, enemy switch on, men pinned): no wall -> `cansee` 3/3 men; wall closed between them -> 0/3 for the first
  ~4 s, then climbs back as they walk out of / around it.
- Grenadier path (`SSLOB=1`): `lob` returns 1, one screen, thrower released after 6 s. The in-loop wiring itself is a 6-line call.
- 0 script errors in all final runs; brace-depth scan of smokescreen.scr / officer.scr clean (0 at end, never negative).

## Not done / follow-ups
- Not played live; tuning knobs are all in `coop_screensmoke.tik` (size/density/duration) and the constants at the top of `ss_place`
  / `squad_screen` (1900 trigger, 0.55, 1100 cap, 8 s hold). Only elite squads and grenadiers throw; the Wehrmacht infantry squad
  never did and still does not.
- In the harness the stock `M18` hiss loop plays from each of the 3 canisters (3 overlapping loops, not judged by ear).
- Docs budgets: TRAPS (70/70), FEATURES (90/90) and OPEN (over) are at their ceilings and carry other sessions' uncommitted edits, so
  nothing was added there. Candidate TRAPS lines to merge at integration: (1) "hold a reinforcement" recipe above; (2) the cfg `wait N`
  is milliseconds in this engine; (3) a SmokeGrenade tik's SERVER block is what blinds AI, the client emitter is only the picture.

## Integration
- Run `python docs/tools/gen_fixes_pak.py build` (the tik is a "new" member and must NOT sit in the mod tree). `gen_fixes_pak.py check`
  currently fails on three UNRELATED pinned fps_anims files from other sessions; the screensmoke entry itself is clean.
- Mod commit on `smoke-next`: `officer.scr` (wave_hunt hold check, elite spawn call, grenadier loop; removed `coop_elite_smoke_barrage`
  and `coop_smoke_cleanup`), `precache.scr` (+1 line), new `smokescreen.scr`. reinf.scr untouched.

## Harness
`tools/smokelib.py` (private client `G:\mohaa-hudfeed4\smoke\` = GOG-root release DLLs + exe copy, homepath `hudfeed4\home`, slot
hudfeed4, port 12761, overlay = driver + worktree files + the tik), `ss_drv.scr` (commands: pairs/usepair/fxspot/fxsquad/fxreal/wall/lob/
fxen/...), `ss_fxrun.py` (controlled + real-flow proof), `ss_run.py`, `ss_survey.py`, `contact.py`. Gotchas: bug-3977.
