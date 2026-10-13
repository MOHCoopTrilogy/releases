# Rain that reaches the ground (bug-3881) - 2026-10-13

User, on the build deployed today: *"confirmed the downpour weather works but the rain doesnt really go to the ground,
it stays closer to the top of the screen.."*

Engine: branch `rainfix-next` (worktree `C:\mohaa-coop-dev\openmohaa-hzm-rainfix`), commit `5376f59e`, off
`integ-1.10.22` (277bdb9d). cgame only: `code/cgame/cg_nature.cpp`, `cg_beam.cpp`, `cg_commands.h`. Nothing in the mod.
Built cgame: `C:\mohaa-coop-dev\openmohaa-hzm-rainfix\.cmake\code\client\cgame\Release\cgame.dll`,
md5 `017638163fe942100064962f277e107b` (the baseline build of integ-1.10.22 in the same folder was `b9f03305...`).
Nothing is deployed.

## The cause

A rain streak is one quad drawn from the drop (its head) back **up** its path for `rain_length` units. The drop's
path is cut at the first solid it meets (the wall clamp) and the beam's life is scaled to match, so the whole streak
is removed the moment the head touches the ground - while its upper end is still a streak-length up. Over the last
streak-length above any surface the rain therefore thins to nothing. With ordinary rain (length 90) that is a thin
band at boot height; the downpour tier's streaks are 260 long, and a standing player's eye is 82 over the ground.

Measured on m3l2, standing in the village yard, downpour pinned (`coop_weatherPin 4`), 1600x900, 60 fps cap, with a
measurement build that logs every drawn streak (`coop_rainStats`, not in the commit):

| | before | after |
|---|---|---|
| height of a streak's upper end over the ground when it is removed, downpour | 233 u | 4 u |
| the same, ordinary heavy rain (tier off, length 90) | 95 u | 3.5 u |
| the same, light / medium rain (density 0.8 / 3) | 95 / 96 u | 2.4 / 2.1 u |
| streak cover in the band 0-32 u over the feet, of the full value | 12 % | 99 % |
| ... 64-96 u (eye height) | 40 % | 100 % |
| ... 224-256 u | 100 % | 100 % |
| streak pixels, level view, upper five tenths of the picture | 10.3 12.6 10.7 6.2 1.3 % | 12.4 14.8 13.2 13.4 13.2 % |
| streak pixels, level view, lower five tenths | 0.1 0.0 0.0 0.0 0.0 % | 13.4 11.4 9.4 7.3 5.5 % |
| streak pixels, looking 30 degrees down, whole picture | 0.13 % | 6.7 % |

(Streak pixel = brighter than the per-pixel median of the stills of that view by more than 9 luma; `tools/rainpix.py`.)

The suspects, switched one at a time on the "before" state, same view (streak pixels by tenth of the picture height,
top to bottom):

| setting | picture | upper end over ground at removal |
|---|---|---|
| as deployed | 10.3 12.6 10.7 6.2 1.3 0.1 0.0 0.0 0.0 0.0 | 233 u |
| `coop_rainEndGate 0` | 11.5 12.4 9.9 6.8 1.7 0.2 0.1 0.1 0.2 0.1 | 245 u |
| `coop_rainByTime 0` (half the drops at 60 fps) | 6.6 6.1 5.5 4.0 0.7 0.0 0.0 0.0 0.0 0.0 | 234 u |
| `coop_rainNearCull 0` | 12.0 12.3 10.8 7.1 2.1 0.0 0.0 0.0 0.0 0.0 | 233 u |
| `coop_rainSeed 0` | 6.2 5.4 4.1 2.3 1.4 0.1 0.0 0.0 0.0 0.0 | 233 u |
| `coop_rainSeeOut 0` | 12.1 12.5 9.4 6.4 1.7 0.2 0.2 0.2 0.0 0.0 | 235 u |
| rain shader with the depth test OFF (overlay, `tools/test_nodepth`) | 12 12 10 7 2 0 0 0 0 0 | 234 u |
| unmodified integ-1.10.22 cgame (no stats) | 10.8 12.4 11.0 7.8 2.2 0.0 0.0 0.1 0.0 0.0 | - |
| `coop_rainFloor 1024` alone | 11.8 13.7 10.8 6.1 1.4 0.1 0.0 0.1 0.0 0.0 | 233 u |
| **`coop_rainToGround 1` alone** | 14.2 15.8 13.7 13.4 12.5 13.3 14.4 10.4 9.2 9.1 | 4 u |
| the fix (both) | 12.4 14.8 13.2 13.4 13.2 13.4 11.4 9.4 7.3 5.5 | 4 u |

None of the recent changes is the cause; the wall clamp that removes the streak at impact is older than all of them.
The downpour's 260-unit streaks made it plain.

A second, separate fault of the same kind turned up: the brushless rain's drops are removed 256 units below the eye
whatever is under them. From 300 units up (a rooftop) the upper end of a streak was 312 u over the ground at removal
in the downpour, 286 u in ordinary rain, and snow stopped 138-143 u up.

## The fix

| cvar | default | 0 / old value | what |
|---|---|---|---|
| `coop_rainToGround` | 1 | 0 = as before | the drop lives one streak length longer; the head stops at the surface, the tail runs on into it (cgame beam flag `BEAM_HZM_TAILRUN`); the texture is cut by what has gone in, not squeezed. Nothing is drawn beyond the surface. Both rain paths (map rain brush, brushless). No trace added |
| `coop_rainFloor` | 1024 | 256 = as before | a drop that reaches 256 u below the eye with nothing solid under it carries on along its own line, at its own speed, to the first solid or to that depth. One more trace, only for such a drop. A rain drop of that kind flatter than 60 degrees from the vertical is not drawn (level ground removes the same drops by itself); snowflakes are left as they were. A slow snowflake may live 20 s instead of 10 for the way down |
| `coop_rainMaxBeams` | 4096 | - | rain and snow stop spawning while that many beams are alive; the pool (`MAX_BEAMS`) is 8192 now. Slow snow has always kept the 4096 pool full and draws what it drew before; the longer-lived rain streaks cannot fill the pool; the other 4096 are free for every other beam |

Existing cvars are untouched (`coop_rainEndGate`, `coop_rainSeeOut`, `coop_rainByTime`, `coop_rainRefFps`,
`coop_rainNearCull`, `coop_rainSeed`, `coop_rainSkyStrict`, `coop_rainBrushRoof`). The set of drops that is spawned
on level ground is the same as before: every gate runs as it did, on the same path.

## Numbers, final logic (run rf16, measurement build of the committed source)

Same look at every frame rate (yard, level view; streak pixels by tenth, top to bottom):

| cap | measured | before | after |
|---|---|---|---|
| 30 | 30 | 10.1 10.2 8.2 5.6 1.2 0.0 0.0 0.0 0.0 0.2 | 11.8 14.7 11.8 11.8 12.2 12.3 12.6 10.7 8.1 6.1 |
| 60 | 60 | 9.3 9.4 8.1 6.4 1.6 0.1 0.0 0.1 0.0 0.0 | 15.5 14.1 13.9 11.9 10.9 14.0 15.1 11.9 7.9 5.1 |
| 125 | 125 | 13.9 14.0 10.3 6.4 2.2 0.0 0.0 0.1 0.0 0.0 | 14.1 14.3 13.3 12.7 13.3 12.7 14.6 13.6 10.8 7.3 |
| 240 | 196-231 | 13.6 13.5 10.4 6.6 1.6 0.1 0.0 0.2 0.0 0.0 | 14.2 15.6 12.9 11.4 12.6 14.4 13.2 9.2 6.0 5.1 |

Cost (live streaks = beams alive; times are per frame, on a machine that was running other agents' game clients,
so the spawner time moves by a few tenths of a millisecond between identical runs):

| scene | drops made / s | live streaks | beam pass | rain spawner |
|---|---|---|---|---|
| downpour, yard, 60 fps, before | 11,380-11,860 | 1,700-1,770 | 0.20-0.25 ms | 1.43-1.62 ms |
| downpour, yard, 60 fps, after | 11,750-11,820 | 2,680-2,700 | 0.28-0.34 ms | 1.58-1.68 ms |
| downpour, 30 fps, before / after | 11,290 / 11,280 | 1,810 / 2,700 | 0.26 / 0.28 ms | 2.74 / 2.71 ms |
| downpour, 125 fps, before / after | 11,860 / 11,730 | 1,720 / 2,650 | 0.22 / 0.30 ms | 0.75 / 0.79 ms |
| downpour, 231 fps, before / after | 11,730 / 11,820 | 1,700 / 2,670 | 0.25 / 0.29 ms | 0.70 / 0.48 ms |
| downpour, 300 u up, before / after | 18,350 / 13,180 | 2,920 / 3,850 | 0.38 / 0.41 ms | 1.85 / 1.95 ms |
| ordinary heavy rain, yard, before / after | 3,110 / 3,080 | 610 / 720 | 0.08 / 0.08 ms | 0.39 / 0.37 ms |
| ordinary heavy rain, 300 u up | 4,630 / 4,230 | 980 / 1,460 | 0.11 / 0.15 ms | 0.39 / 0.50 ms |
| light rain (density 0.8), yard | 247 / 252 | 45 / 59 | 0.01 / 0.01 ms | 0.05 / 0.07 ms |
| blizzard (m2l1), ground, before / after | 3,320 / 3,390 | 2,680 / 2,840 | 0.30 / 0.31 ms | 0.40 / 0.45 ms |
| blizzard, 300 u up | 4,000 / 3,450 | 4,020 / 4,040 (at the 4096 share) | 0.51 / 0.38 ms | 0.41 / 0.39 ms |
| ordinary snow (m2l1), ground | 740 / 725 | 4,080 / 4,083 (at the share) | 0.41 / 0.44 ms | 0.09 / 0.09 ms |

Live streaks in the downpour go up by half (a streak is on screen until its tail has landed); drops made a second do
not change. With the pool at 4096 and no share, the same downpour seen from 300 u up filled the pool (858 refusals
a second, run rf03). Ordinary snow asks for 22,500 flakes a second and gets 740: it has always been bound by the pool.
With the pool at 8192 and no share it drew twice the flakes (8,170 live, run rf14) - that is why the share exists.

## Snow / blizzard

Snow does not have the first fault to a visible degree: its streaks are 2 u (flakes) or 13 u (blizzard gusts) long,
so the gap at the ground was 3 u / 13 u. It does have the second one (the floor 256 u under the eye): from 300 u up
flakes stopped 138-143 u over the ground. With the fix: 9 u (ordinary snow), 56 u (blizzard: its flat-flying flakes
are left as they were, the others reach the ground).

## Indoors, roofs, floors (t1l3, final build, run rf19)

Four rooms found by the rain-indoors work of 2026-10-12, each looking out, straight up at the ceiling and down at the
floor. After: ceilings 0.00-0.02 % streak pixels, floors inside 0.00-0.03 % (room 1's floor view, 1.5 %, shows the
rain outside its open window frames at the top of the picture). Before: 0.00 % everywhere except room 1's ceiling
view, 0.19 % (the top of the opening is in the picture). Rain outside is seen from every room that has an opening,
now down to the ground outside (room 3 has none: 0.03 % both ways).

## Evidence (all engine screenshots; final build md5 0176381...; `evidence/`)

Before = `coop_rainToGround 0` + `coop_rainFloor 256` on the same build, which is the deployed behaviour (checked
against the unmodified integ-1.10.22 cgame, table above). m3l2, downpour pinned.

- `16x9_views_sheet_1.jpg`, `16x9_views_sheet_2.jpg` - 1600x900: yard level / down 30 / up 35, tunnel looking out,
  canal between walls (two), canal edge looking down, 300 u up looking down; before left, after right
- `21x9_views_sheet_1.jpg`, `21x9_views_sheet_2.jpg` - the same at 1920x804 (the 3440x1440 shape)
- `16x9_<view>_before_after.jpg`, `21x9_<view>_before_after.jpg` - each of those views at full size
- `16x9_downpour_before_after.gif`, `21x9_downpour_before_after.gif` - 24 stills before / 24 after, yard, 8 degrees
  down. The frames are separate engine screenshots about 0.7 s apart (one `screenshot` per console step), not
  consecutive frames
- `rooms_t1l3_views_sheet_1..3.jpg`, `rooms_t1l3_<room>_<view>_before_after.jpg` - the four rooms (night map)
- `first_look_floating_camera_...jpg` - the first before / after pair (measurement build v1, camera 80 u over the
  ground)

In the stills the soldier at the left edge is the test player's own body (the harness holds the player in place with
physics off). The wide pale streaks are drops within 40-80 u of the eye; `coop_rainNearCull` (36) is unchanged, they
were there before in the upper half of the picture and now cross the lower half as well.

## Not verified

- Not seen by the user; not deployed; not merged into `integ-1.10.22` or `integ-ads`.
- 3440x1440 itself: the test display is 1920 wide, so the 21:9 runs are 1920x804.
- Frame generation (`r_hzmFrameGen`): not run. The change is in which quads the cgame submits; nothing in the
  renderer is touched.
- A map with its own rain BRUSH (the `CG_Rain` path): the code path gets the same tail run, but no brush map was
  run. m5l1a was tried with `coop_weatherPin 1`; the spot the driver took was under the map and it was not raining
  there - that run (rf13) says nothing.
- A second player / a dedicated server: rain is drawn per client from the same configstrings; one listen-server
  client was run.
- The opengl1 renderer.
- 240 fps: the harness reached 196-231.
- Whether the outside deck of t1l3 room 1 (where stubs land in the "after" stills) is open to the sky was checked
  with a script trace only (open sky from 180 u out; roof up to 140 u out).

## Tools (`tools/`)

`rainlib.py` (harness helpers: G:\mohaa-hudfeed2, port 12721), `run03.py` (plans: matrix, fps, tiers, views, gif,
quick, light, probe), `run01_scout.py`, `run02_spots.py`, `coop_selftest_xp.scr` (test driver: camera, scan, weather
strength), `rainpix.py` (streak pixels), `mksheets.py`, `apply_stats.py` (the `coop_rainStats` measurement patch,
never committed to the engine), `test_nodepth/coop_rain.shader` (test only), `buglog_add.py`.
`engine/rainfix-next_5376f59e.diff` = the commit; `engine/rainfix-next_5376f59e_plus_stats.diff` = the measurement
build's source. Run folders: `H:\hzm_archive\rainfix\rf01` .. `rf21` (rf16-rf21 = the final logic).
