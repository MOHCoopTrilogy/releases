# Alarm snipers - 2026-10-18 (SHIPPED-UNVERIFIED, nothing deployed)

User request: when an alarm goes off, random enemy snipers take rooftops and other high places. Branch `alarmsnipers-next` (worktree
`hzm-mod-alarmsnipers`, off coop-wip). New code lives in new files; the only edit to existing code is one hook line in
`coop_mod/alarm.scr::alm_start` plus seven `seta` lines in `autoexec.cfg`. The alarm panel placement data (`alarm_points.json`,
`alarmpoints.scr`) is untouched.

## What it does
- `alm_start` threads `coop_mod/alarmsnipers.scr::asn_alarm <pull>`. The alarm module already refuses stealth / disguise / own-alarm /
  Omaha / mp / lobby / maptest maps (`alm_blocked`), so snipers never appear there.
- Count = `coop_alarmSnipersBase` (2) + `coop_alarmSnipersPer` (1) per extra player, capped at `coop_alarmSnipersMax` (5). A second pull
  only tops up to the wanted number. Never two on one spot (350 u apart, spots are 350+ u apart offline).
- Spot choice, each time: not held; **solid-ground rule re-run (`asn_floor`)**, a failing spot is skipped, logged and never retried;
  600..2300 u from the nearest player; a line from a player's eye to the sniper's head (so he can be shot back); **no player with a line to it
  is looking toward it** (copy of `reinf.scr::rnf_entry`'s "never pop in in view" rule); prefers a building and a side no live sniper uses.
- Kit (copy of `officer.scr::coop_spawn_sniper`): vanilla `german_wehrmact_sniper` model, `mauser kar 98d sniper`, accuracy
  `coop_alarmSnipersAcc` (55) then `coop_reinf_scale` (the existing player-count / difficulty scaling), leash 24 u, `mindist 0`, no
  `runto` anywhere, so he stays on his spot. Arrival cue: a scope glint (entity `light`, 3 flashes), a German shout (`coop_av_de_backup1..6`)
  and a feed line. Smoke was NOT reused: smoke blocks `Actor::CanSee` both ways and would blind the sniper.
- `asn_hold` watches each sniper: more than 6 u off his floor (a mover took him) = removed and the spot dropped.

## Cvars (defaults)
`coop_alarmSnipers 1`, `coop_alarmSnipersBase 2`, `coop_alarmSnipersPer 1`, `coop_alarmSnipersMax 5`, `coop_alarmSnipersAcc 55`,
`coop_alarmSnipersMin 600`, `coop_alarmSnipersRange 2300`, test only `coop_alarmSnipersSim 0` (pretend N players). `coop_alarm` (the alarm itself) still decides
whether any of it runs. Debug lines: `coop_alarmDebug 1` prints `^~^~^ ASNIPER ...`.

## Spots: how they were found (docs/tools/gen_sniper_spots.py, uses bsptrace.py)
1. Every upward face (normal z > 0.7) of a solid world brush, sampled on a 48 u grid inset 24 u from the edges.
2. Hard ground rule (mirrored at spawn time in script): trace down from spot+16, a **world-brush** floor within 2 u, flat (normal z > 0.7 and the
   four corners +-12 u within 3 u), shader not sky / water / nodraw; the AI bbox (-15 -15 0)..(15 15 72) not start-solid; >= 72 u headroom.
3. High place: floor >= 128 u above the nearest route anchor's floor (<= 1500 u), >= 8 of 16 samples 200 / 320 u round the spot fall >= 140 u, floor shader not ground-like (snow, street, earth, crate...), open-sky test and type tag (see below).
4. Fire exchange: head visible from >= 6 route anchors (pathnodes, player start, switches, AI) 450..2300 u away, body from >= 4.
5. Dynamic things: not inside a `func_*` mover's bounds (+64 u), not within 350 u of vehicle / train path points, plus a hand deny box on m4l2
   (`sniper_spots_deny.json`).
6. Greedy spread pick, <= 14 per map, building cluster (700 u) and side tags. Terrain is NOT traced, so terrain ridges are never offered.
Result: see the final count below (`docs/tools/sniper_spots.json`, generated `coop_mod/alarmsnipers_spots.scr`).

## FINAL: every spot audited in the engine (2026-10-18, "snipers float in the sky")
A sniper floating in the sky was real: the engine-side roof scan had offered the top of **invisible brushes** (caulk / nodraw / the map-cap slab; m4l1 spots 4-8 sat 500 u above the town) and
surfaces that bullets hit but actors fall through (tree and terrain models: on m2l1 / m1l1 snipers dropped 100-1500 u). Fixes: surface shader names (nodraw, caulk, sky, clip, hint, common/) are rejected
for engine-scan points, and **every kept spot is now proven in the engine** (`tools/asn_chk.py`, one harness turn per few maps): a sniper is spawned on EVERY kept spot at once, 3 s later each is judged:
- z drop > 4 u = FAIL; air under the feet > 4 u (trace down from the feet) = FAIL; the actor-mask floor above the solid floor by > 4 u (standing on a monsterclip volume) = FAIL; sky surface = FAIL;
  any of 8 ring points 39 u out (bbox 15 + 24 u) with no floor within 8 u = a roof edge within 24 u = FAIL. (`nodrawflag` is only logged: the 0x80 surface bit is also set on ordinary wooden floors.)
- every survivor gets a side-on shot at 300 u level with the feet; the camera direction is chosen by an image test (screenshot with the sniper shown vs hidden: the difference region must be a whole body inside the frame). No visible angle = FAIL.
- I then looked at every tile and dropped four more by hand (sniper hidden in the tile, street-level arch, indoor-looking room): reasons are in `spotcheck/*.json` (`manual QA`).
- Failed spots are removed from `docs/tools/sniper_spots.json` (kept under `dropped`) and from the generated `alarmsnipers_spots.scr`. Maps that were not audited are no longer emitted at all.
The generator also got the same edge rule (ring of 8 points at 39 u) and the engine-failure memory (`merge-rf` never offers a point within 96 u of an audit failure, and skips engine-scan candidates on a map where all of them failed).

Audit result per alarm map (last audit round; earlier rounds in `tools/spotcheck/_round1..3`):

| map | spots audited (last round) | passed | dropped (reason: count) | final kept |
|---|---:|---:|---|---:|
| e2l1 | 1 | 1 | - | 1 |
| e3l1 | 4 | 2 | manual QA: 1, no visible angle: 1 | 2 |
| e3l2 | 2 | 0 | manual QA: 2 | 0 |
| m1l1 | 2 | 0 | manual QA: 1, gone: 1 | 0 |
| m2l1 | 8 | 0 | dropped: 7, edge: 2 | 0 |
| m3l2 | 1 | 0 | no visible angle: 1 | 0 |
| m4l1 | 1 | 0 | dropped: 1, air: 1, onclip: 1, edge: 1 | 0 |
| m4l2 | 7 | 4 | manual QA: 1, no visible angle: 2 | 4 |
| m4l3 | 1 | 0 | edge: 1 | 0 |
| t1l1 | 1 | 0 | no visible angle: 1 | 0 |
| t3l1 | 1 | 0 | edge: 1 | 0 |

**Final: 7 spots on 3 maps (e2l1 1, e3l1 2, m4l2 4).** Every other alarm map gets no alarm snipers (its alarm still brings infantry and the MG team). Sheets (floor contact visible in every tile, dark tiles gamma-lifted):
`media/sheet_spots_m4l2.jpg`, `media/sheet_spots_e3l1.jpg`, `media/sheet_spots_e2l1.jpg`. Honest notes: m4l2 spots are ridge / path surfaces rather than roofs; the m4l2 tile for spot 7 has a tree trunk beside him, the contact is visible;
the e3l1 spots are terrace / roof-edge ledges with railings. Not Omaha. The earlier widened-search text below is history.

## Proof (earlier rounds; the final audit above supersedes the spot lists and counts quoted here)
- (older, superseded by the audit sheets above) Contact sheet: `media/contact_sheet_alarm_snipers.jpg` (m2l1 snow ridge, t3l1 roof, m3l2 wall top, e3l1 roof from the pre-widening capture; left = sniper at his spot, right = from the player's place at fov 28; dark rows are gamma-lifted, the test driver adds a dlight on the filmed sniper). Honest notes: the **m3l2 row does not show the sniper** (the close camera ended up behind the wall he stands on; the log proves two snipers at floor z 616 / 692, dz 0.000, stable); the e3l1 and m4l2 right views are dominated by guards / a dog, the sniper is small in them; e3l2 and m1l1 could not be placed in the harness this round.
- Progress GIF: `media/progress_m2l1_snipers_on_gantry.gif`.
- Per sniper in the harness (`ASN SN` lines): the floor trace under him, `dz=0.000`, `startsolid=0` on every sniper that was not removed.
- Log excerpt, one alarm pull at **1 simulated player (want 2)** and one at **3 (want 4)**, m2l1 (`tools/logs/run_m2l1f.txt`):
```
^~^~^ ALARM LIVE pull 1 switches=2
^~^~^ ASNIPER pull 1 players=1 want=2 alive=0 spots=4
^~^~^ ASNIPER SNIPER 1 spot=4 at=( 4120.000 7320.000 176.125 ) floorz=176.125 cluster=1 side=2 alive=1
^~^~^ ASNIPER SNIPER 2 spot=3 at=( 3688.000 6840.000 176.125 ) floorz=176.125 cluster=1 side=2 alive=2
^~^~^ ASNIPER pull 1 done made=2 alive=2 tries=0
^~^~^ ASN SN 1 ent=363 spot=4 origin=( 4120.000 7320.000 176.125 ) floorz=176.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=player dist=1304
^~^~^ ASN SN 2 ent=375 spot=3 origin=( 3688.000 6840.000 176.125 ) floorz=176.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=player dist=854
^~^~^ ALARM LIVE pull 2 switches=2
^~^~^ ASNIPER pull 2 players=1 want=4 alive=0 spots=4
^~^~^ ASNIPER SNIPER 1 spot=1 at=( 4184.000 6960.000 304.125 ) floorz=304.125 cluster=1 side=2 alive=1
^~^~^ ASNIPER SNIPER 2 spot=3 at=( 3688.000 6840.000 176.125 ) floorz=176.125 cluster=1 side=2 alive=2
^~^~^ ASNIPER SNIPER 3 spot=4 at=( 4120.000 7320.000 176.125 ) floorz=176.125 cluster=1 side=2 alive=3
^~^~^ ASNIPER SNIPER 4 spot=2 at=( 3592.000 7320.000 176.125 ) floorz=176.125 cluster=1 side=2 alive=4
^~^~^ ASNIPER pull 2 done made=4 alive=4 tries=0
^~^~^ ASN SN 1 ent=364 spot=1 origin=( 4183.711 6960.008 304.125 ) floorz=304.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=none dist=1343
^~^~^ ASN SN 2 ent=338 spot=3 origin=( 3687.864 6844.686 176.125 ) floorz=176.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=none dist=853
^~^~^ ASN SN 3 ent=413 spot=4 origin=( 4120.012 7320.074 176.125 ) floorz=176.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=none dist=1304
^~^~^ ASN SN 4 ent=383 spot=2 origin=( 3591.864 7324.686 176.125 ) floorz=176.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=none dist=803
```
  e3l1 (`tools/logs/run_e3l1g.txt`), same two pulls:
```
^~^~^ ASNIPER pull 1 players=1 want=2 alive=0 spots=5
^~^~^ ASNIPER SNIPER 1 spot=5 at=( -296.000 4056.000 224.125 ) floorz=224.125 cluster=1 side=2 alive=1
^~^~^ ASNIPER SNIPER 2 spot=3 at=( -872.000 2776.000 224.125 ) floorz=224.125 cluster=3 side=3 alive=2
^~^~^ ASNIPER pull 1 done made=2 alive=2 tries=0
^~^~^ ASN SN 1 ent=153 spot=5 origin=( -296.000 4056.000 224.125 ) floorz=224.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=player dist=1139
^~^~^ ASN SN 2 ent=596 spot=3 origin=( -872.000 2776.000 224.125 ) floorz=224.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=player dist=786
^~^~^ ASNIPER pull 2 players=1 want=4 alive=0 spots=5
^~^~^ ASNIPER SNIPER 1 spot=1 at=( 312.000 4008.000 224.125 ) floorz=224.125 cluster=1 side=2 alive=1
^~^~^ ASNIPER SNIPER 2 spot=3 at=( -872.000 2776.000 224.125 ) floorz=224.125 cluster=3 side=3 alive=2
^~^~^ ASNIPER SNIPER 3 spot=4 at=( 504.000 4920.000 448.125 ) floorz=448.125 cluster=4 side=2 alive=3
^~^~^ ASNIPER SNIPER 4 spot=5 at=( -296.000 4056.000 224.125 ) floorz=224.125 cluster=1 side=2 alive=4
^~^~^ ASNIPER pull 2 done made=4 alive=4 tries=0
^~^~^ ASN SN 1 ent=597 spot=1 origin=( 314.993 4010.746 224.125 ) floorz=224.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=none dist=1169
^~^~^ ASN SN 2 ent=254 spot=3 origin=( -870.840 2778.494 224.125 ) floorz=224.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=none dist=785
^~^~^ ASN SN 3 ent=673 spot=4 origin=( 504.000 4920.000 448.125 ) floorz=448.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=none dist=2114
^~^~^ ASN SN 4 ent=535 spot=5 origin=( -296.136 4060.687 224.125 ) floorz=224.125 dz=0.000 startsolid=0 hp=65.000 acc=55.000 enemy=none dist=1143
```
- Solid-ground failures seen and fixed: a sniper at a train/tank crossing on m4l2 was lifted 224 u then 90 u (hence the mover exclusion, the lift watch and the deny box; the watch itself fired correctly: "moved 90u off his floor ... removed, spot dropped"). Early spots that were ground level (rail bed, hillside street, crate tops) were removed by the high-place test.

## Per-spot trace results (the 7 surviving spots; in-engine audit lines)

| map | spot (x y floor-z) | type | z before -> after 3 s | air under feet | clip dz | edge ring bad | verdict |
|---|---|---|---|---:|---:|---:|---|
| e2l1 | -4216 -4056 424.12 | outdoor-high | 424.120 -> 424.125 | 0.000 | 0.000 | 0 | PASS |
| e3l1 | -200 4200 224.12 | outdoor-high | 224.120 -> 224.125 | 0.000 | 0.000 | 0 | PASS |
| e3l1 | -824 3592 224.12 | roof | 224.120 -> 224.125 | 0.000 | 0.000 | 0 | PASS |
| m4l2 | -3112 4472 304.12 | outdoor-high | 304.120 -> 304.125 | 0.000 | 0.000 | 0 | PASS |
| m4l2 | -1688 1336 248.12 | outdoor-high | 248.120 -> 248.125 | 0.000 | 0.000 | 0 | PASS |
| m4l2 | 2720 880 248.12 | outdoor-high | 248.120 -> 248.125 | 0.000 | 0.000 | 0 | PASS |
| m4l2 | 1504 624 242.63 | outdoor-high | 242.630 -> 242.333 | 0.131 | -0.000 | 0 | PASS |

## Unverified
- A real alarm trigger (the harness forced `alm_start`), real player fire at / from the snipers, 2+ real players, a public server, the effect on mission balance.
- Terrain maps: terrain is not in the offline trace; the runtime line-of-sight uses the engine trace, so a spot behind terrain is rejected live.
- m1l1, m4l3, e2l1 and m4l1 shots (ride intro / no spots); m3l2, t1l1, t3l1 have a single spot, so only one sniper can appear.
- `coop_alarmSnipers` defaults to 1 but `coop_alarm` gates it; nothing has been deployed.

## Re-run
`python docs/tools/gen_sniper_spots.py scan <map...>`, then `build --mod <mod tree>`. Harness: `tools/asn_run.py <label:map>... shots` (waits for its harness_turn),
driver `tools/asn_drv.scr`, sheet `tools/make_sheet.py`, GIF `tools/make_gif.py`.
