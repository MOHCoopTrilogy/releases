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

## Maps covered, spots kept and their type (final, user rule: NO indoor snipers)
Rules: floor >= 128 u above the nearest route anchor's floor (<= 1500 u); **open sky** above head height (roof or outdoor surface) - interior spots are
removed entirely, a map with no outdoor spot gets no alarm snipers (its alarm still brings infantry and the MG team). Types: `roof` = open sky and
>= 12 of 16 samples drop away, `outdoor-high` = other open-sky surface (tower, wall, ridge, platform, ledge).
Total **44 spots on 12 maps**. Alarm maps with snipers: **e3l1 (4: 2 roof, 2 outdoor-high), m4l2 (2 outdoor-high), m1l1 (1 roof; not re-captured, harness cannot place a player during its intro ride)**.
Alarm maps with none now: m2l1, m4l3, e3l2, m3l2, t1l1, t3l1, e2l1, m4l1.
Per map ("before rules" = `tools/sniper_spots_v3_before_elevation_rule.json`):

| map | before rules | kept | types | kept spots (x y floor-z, dz above route ground) |
|---|---:|---:|---|---|
| e1l1 | 3 | 3 | 1 roof, 2 outdoor-high | 5016 2216 608.12 (+192); -3176 40 400.12 (+304); 3392 1704 600.12 (+184) |
| e1l2 | 2 | 1 | 1 outdoor-high | 4184 4184 448.12 (+256) |
| e1l3 | 11 | 10 | 6 roof, 4 outdoor-high | 792 -5760 400.12 (+216); -648 4312 512.12 (+384); -136 -1080 512.12 (+328); 1176 568 616.12 (+472); 1304 -1704 768.12 (+592); -136 2904 704.12 (+352); 480 3936 432.12 (+280); 104 -1752 768.12 (+231); 264 4312 512.12 (+352); 600 -5432 328.12 (+160) |
| e2l2 | 11 | 4 | 2 roof, 2 outdoor-high | 1128 4464 2800.12 (+240); 1864 3416 3296.12 (+288); 1408 5080 2737.12 (+129); 1480 3416 3296.12 (+288) |
| e3l1 | 5 | 4 | 2 roof, 2 outdoor-high | 216 4008 224.12 (+136); 968 -1272 200.12 (+156); -872 2776 224.12 (+144); -248 4248 224.12 (+184) |
| e3l2 | 9 | 0 | - | none: no outdoor spot, no alarm snipers |
| e3l3 | 1 | 0 | - | none: no outdoor spot, no alarm snipers |
| e3l4 | 1 | 0 | - | none: no outdoor spot, no alarm snipers |
| m1l1 | 2 | 1 | 1 roof | -3944 120 564.12 (+132) |
| m1l3b | 4 | 4 | 4 outdoor-high | -2616 6904 192.12 (+198); -3048 7288 192.12 (+168); -2568 7288 192.12 (+168); -3048 6904 192.12 (+168) |
| m1l3c | 3 | 2 | 1 roof, 1 outdoor-high | -576 -2472 512.12 (+172); 141 -2009 1104.12 (+780) |
| m2l1 | 4 | 0 | - | none: no outdoor spot, no alarm snipers |
| m3l2 | 1 | 0 | - | none: no outdoor spot, no alarm snipers |
| m4l2 | 3 | 2 | 2 outdoor-high | -3256 4424 304.12 (+256); -1544 1240 248.12 (+168) |
| m4l3 | 5 | 0 | - | none: no outdoor spot, no alarm snipers |
| m5l3 | 4 | 3 | 3 outdoor-high | -2184 -2356 648.12 (+224); -2760 -3316 648.12 (+368); -2712 -2884 648.12 (+288) |
| m6l1a | 11 | 0 | - | none: no outdoor spot, no alarm snipers |
| m6l1b | 5 | 3 | 1 roof, 2 outdoor-high | -1852 2776 2408.12 (+208); -2498 2171 2408.12 (+256); -2018 2290 2408.12 (+256) |
| m6l2b | 1 | 0 | - | none: no outdoor spot, no alarm snipers |
| t1l1 | 1 | 0 | - | none: no outdoor spot, no alarm snipers |
| t1l2 | 4 | 0 | - | none: no outdoor spot, no alarm snipers |
| t1l3 | 6 | 7 | 7 outdoor-high | 4512 2860 492.12 (+443); -1416 1504 248.12 (+200); 3784 3224 552.12 (+352); -1249 1904 496.12 (+448); -1249 1132 496.12 (+448); 3936 2860 492.12 (+460); 4600 3224 552.12 (+503) |
| t2l1 | 3 | 0 | - | none: no outdoor spot, no alarm snipers |
| t2l2 | 1 | 0 | - | none: no outdoor spot, no alarm snipers |
| t2l4 | 2 | 0 | - | none: no outdoor spot, no alarm snipers |
| t3l1 | 1 | 0 | - | none: no outdoor spot, no alarm snipers |

## Proof
- Contact sheet: `media/contact_sheet_alarm_snipers.jpg` (e3l1 roof/outdoor, m4l2 outdoor-high; the m2l1 and m4l3 rows are interior spots that were REMOVED by the final rule and are kept only as an old-capture record; left = sniper at his spot, right = from the player's place at fov 28; dark rows are gamma-lifted, the test driver adds a dlight on the filmed sniper). Honest notes: the e3l1 and m4l2 right views are dominated by guards / a dog, the sniper is small in them; e3l2 and m1l1 could not be placed in the harness this round.
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

## Per-spot trace results (offline, bsptrace; `floor dz` is hit height minus spot height)
| map | spots | buildings | sides |
|---|---:|---:|---:|
| e3l1 | 5 | 4 | 3 |
| e3l2 | 9 | 6 | 3 |
| m1l1 | 2 | 1 | 2 |
| m2l1 | 4 | 1 | 1 |
| m3l2 | 1 | 1 | 1 |
| m4l2 | 3 | 3 | 3 |
| m4l3 | 5 | 3 | 3 |
| t1l1 | 1 | 1 | 1 |
| t3l1 | 1 | 1 | 1 |

#### e3l1

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | 312.0 4008.0 224.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | whsflrset1_1b | 156.1 | 83/83 | 1 | 2 |
| 2 | 968.0 -1272.0 200.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | wdflr2a | 150.1 | 80/21 | 2 | 6 |
| 3 | -872.0 2776.0 224.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | concretewall2 | 160.1 | 57/54 | 3 | 3 |
| 4 | 504.0 4920.0 448.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | concretewall2 | 352.1 | 80/56 | 4 | 2 |
| 5 | -296.0 4056.0 224.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | concretewall2 | 160.1 | 68/38 | 1 | 2 |

#### e3l2

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | 4084.0 -11.0 -153.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 171.8 | flrwood1 | 142.1 | 48/46 | 1 | 0 |
| 2 | 888.0 -4120.0 -239.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | wdflr2a | 104.1 | 16/16 | 2 | 6 |
| 3 | 4208.0 -5188.0 -231.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | it_e_3-2wallbeigebase_01-512 | 112.1 | 30/30 | 3 | 7 |
| 4 | 2106.0 -3912.0 -239.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | wdflr2a | 104.1 | 19/14 | 4 | 7 |
| 5 | 954.0 -3032.0 -239.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | wdflr2a | 104.1 | 34/33 | 5 | 6 |
| 6 | 4921.0 -424.0 -140.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 214.8 | flrwood1 | 155.1 | 17/13 | 6 | 0 |
| 7 | 1671.36 -3880.0 -239.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 246.8 | wdflr2a | 104.1 | 18/15 | 4 | 6 |
| 8 | 3988.0 373.0 -153.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 171.8 | flrwood1 | 142.1 | 32/10 | 1 | 0 |
| 9 | 1804.0 -4216.0 -239.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 246.8 | wdflr2a | 104.1 | 19/19 | 4 | 6 |

#### m1l1

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | -3704.0 -159.0 604.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | afrik_wall1a | 164.1 | 59/39 | 1 | 1 |
| 2 | -3944.0 120.0 564.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | afrik_wall1a | 100.1 | 49/47 | 1 | 2 |

#### m2l1

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | 4184.0 6960.0 304.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 142.8 | cr1_top | 288.1 | 20/19 | 1 | 2 |
| 2 | 3592.0 7320.0 176.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | doccrtset_1b | 160.1 | 10/9 | 1 | 2 |
| 3 | 3688.0 6840.0 176.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 214.8 | doccrtset_1b | 160.1 | 16/7 | 1 | 2 |
| 4 | 4120.0 7320.0 176.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 214.8 | doccrtset_1b | 160.1 | 14/7 | 1 | 2 |

#### m3l2

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | -4200.0 3536.0 176.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 158.8 | tiledfloor_manordark2 | 127.1 | 6/6 | 1 | 2 |

#### m4l2

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | -3256.0 4424.0 304.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | dday_bunker_wall1bsml | 288.1 | 78/78 | 1 | 3 |
| 2 | -5632.0 1192.0 376.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | doccrtset_1b | 136.1 | 39/39 | 2 | 4 |
| 3 | -1544.0 1240.0 248.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | dday_bunker_wall1bsml | 232.1 | 44/42 | 3 | 7 |

#### m4l3

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | -2480.0 -1520.0 200.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 246.8 | oldcrpt1 | 152.1 | 14/14 | 1 | 6 |
| 2 | -984.0 -1544.0 208.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 166.8 | frenchfloor_wood1 | 152.1 | 7/6 | 2 | 7 |
| 3 | -2528.0 -752.0 200.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 246.8 | oldcrpt1 | 152.1 | 7/4 | 3 | 3 |
| 4 | -1912.0 -1664.0 200.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 246.8 | oldcrpt1 | 152.1 | 9/8 | 1 | 7 |
| 5 | -2576.0 -1136.0 200.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 157.9 | oldcrpt1 | 152.1 | 10/4 | 1 | 6 |

#### t1l1

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | -3341.0 5244.0 -6719.88 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 192.7 | frenchfloor_wood1 | 231.1 | 10/9 | 1 | 2 |

#### t3l1

| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |
|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|
| 1 | 1544.0 -2828.0 376.12 | 0.12 | 1.0 | [0.0, 0.0, 0.0, 0.0] | 256.0 | jh_conc512damg | 212.1 | 32/29 | 1 | 7 |



## Unverified
- A real alarm trigger (the harness forced `alm_start`), real player fire at / from the snipers, 2+ real players, a public server, the effect on mission balance.
- Terrain maps: terrain is not in the offline trace; the runtime line-of-sight uses the engine trace, so a spot behind terrain is rejected live.
- m1l1, m4l3, e2l1 and m4l1 shots (ride intro / no spots); m3l2, t1l1, t3l1 have a single spot, so only one sniper can appear.
- `coop_alarmSnipers` defaults to 1 but `coop_alarm` gates it; nothing has been deployed.

## Re-run
`python docs/tools/gen_sniper_spots.py scan <map...>`, then `build --mod <mod tree>`. Harness: `tools/asn_run.py <label:map>... shots` (waits for its harness_turn),
driver `tools/asn_drv.scr`, sheet `tools/make_sheet.py`, GIF `tools/make_gif.py`.
