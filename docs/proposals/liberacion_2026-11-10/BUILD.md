# LIBÉRATION - a Field Operations contract (v1.10.75 lane, 2026-11-10)

Status: **BUILT, harness verification pending** (branches `liberacion` in the mod and engine repos, off the v1.10.73 bases:
mod `3280c803`, engine `85f6d3fd`). Merge `hotfix-1.10.53` (opsfix2-hotfix, the MP DEPLOY spawn fix) once v1.10.74 is out.

## What it is (user 2026-11-10)
A Live Operations contract like TDM and OBJ: same clock-seeded roll, pins, hover slip, dispatch card (DEPLOY / FILE AWAY),
launch path, result stamps, return, capped XP and flat chooser. Only the rules differ:
- **solo, one life**: the player alone, Allied, no bots on his side; death = OPERATION FAILED at once (DBNO off).
- **the CO-OP kit**: primary, sidearm, grenades and finishes from the co-op Armory, the co-op gloves, the engraving (client
  side, follows the gun in hand); no MP weapon pick, no team menu.
- **Germans that never respawn** (12-25 by map and skill), placed on the map's own spawn points out of the player's sight,
  grounded, on navigable ground; they hold rooms, a third patrol, and once he is heard the nearest push to where he was.
- objective **"Liberate the area of Axis soldiers."** on the co-op objective line; Germans remaining is a separate HUD line.
- **radio briefing** "Alright soldier, we get one shot at this." (the user's ElevenLabs clip, radio-treated, subtitled).
- **time limit** per map and German count (card LIMIT line, HUD clock, warnings at 2:00 and 0:30, running out = failed).
- **XP** through `xp.scr::xp_award_mp`: 2x the TDM win XP of the skill (200 / 250 / 300 / 400), a failure pays 0.

## Pieces
| Piece | Where |
|---|---|
| pool, roll, weights, limits, stamp texture, tables, `libpoints` extractor | `../livemap_2026-11-09/gen_ops.py` (`LIB_POOL`, `entry_weights`, `lib_bots`, `lib_limit`, `lib_points`) |
| hunt spots (BSP spawn points, deduplicated) | `../livemap_2026-11-09/lib_points.json` (generated: `gen_ops.py libpoints`) |
| card / slip / strip / deploy / return | engine `code/client/cl_hzm_ops.cpp` + generated `cl_hzm_ops_table.h` |
| the match | mod `coop_mod/mp_ops.scr` (LIB block), `mp_ops_table.scr` (`libpts`, `libally`), `mp_ops_text.scr` (the accented word) |
| seams | `mp.scr` (no armory hold, co-op kit on the spawn edge), `mp_bots.scr` (25 cap), `mp_dbno.scr` (off) |
| the co-op kit bridge | `coop_mod/libbridge.scr` (a COOP file; read-only, isolation clause 19; allowlisted `lib_kit`, `lib_objective`) |
| radio | `sound/coop_vo/den_coop_lib_briefing.wav` (out-of-band snd pak), alias in `ubersound/coop_audio.scr`, `tools/radiofx_lib.py` |
| tests | `tools/lib_sweep.py` (dedicated: `fight`, `place`), `../livemap_2026-11-09/tools/liveops_test.py --lane lib lib` |

## Rebuild
```
python -P -E ../livemap_2026-11-09/gen_ops.py libpoints            # only when the installed MP maps change
python -P -E ../livemap_2026-11-09/gen_ops.py check  --sheet H:/hzm_work/liveops-warmap
python -P -E ../livemap_2026-11-09/gen_ops.py engine <engine checkout>
python -P -E ../livemap_2026-11-09/gen_ops.py mp     <mod checkout>
python ../sp3camp_2026-11-08/make_ng3campaigns.py --mod <mod checkout> --sheet H:/hzm_work/liveops-warmap
ffmpeg -i H:/hzm_work/liberacion/src/radio_briefing_src.mp3 -ac 1 -ar 44100 src44.wav
python -P -E tools/radiofx_lib.py src44.wav <mod>/sound/coop_vo/den_coop_lib_briefing.wav
```
The wav is gitignored (sound/): copy it into the base checkout's `sound/coop_vo/` before `build.ps1`.

## Decisions taken while building
- **Round gametype (gt 3)** instead of TDM + script: the engine itself never respawns anyone once both sides have a spawned
  player. The script decides the result before the engine can (player dead / last German dead / clock), engine limits are 0.
- **Order**: player deployed first behind a black curtain (nodamage), then the Germans join (auto-joined Allies are moved to
  Axis inside `g_allowjointime`), then placement, curtain lifts. Placement never relaxes sight (sighttrace eye -> chest, head).
- **Hunt spots** = every team/DM spawn point of the BSP (spread over the whole map; script cannot enumerate them, so they are
  extracted offline). Bot nav is Recast, built at load for any MP map.
- **Censored places share their existing area**: every "Somewhere in Germany" map rides the V2 slot, every "Somewhere in
  Normandy" one The Hunt's. New marks there merged all of north-west Europe into one exclusion group.
- **Left out by the layout rule** (loop under a campaign tag, no clear spot in the same country): Kasserine, the Tunisian
  desert (bt1), Malta (bt2); Holland (merged the Remagen and Brest groups). Bazaar's approx pin moves to (36.0, 7.0).
- **Mix**: at a place with both kinds, Liberation takes 1 in 4 picks; a Liberation-only place opens 60 % of its windows.
- **No unlock re-check** of the co-op picks in MP (the co-op unlock record is not loaded there); solo listen server only.
