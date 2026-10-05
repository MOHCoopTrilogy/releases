# Aircraft call-ins: realistic, always-visible, smooth (plan, 2026-10-05)

Scope: the aircraft **we added** - the signal-smoke C-47 paradrop (`coop_mod/paradrop.scr`), the binocular
"Bombing Run" P-47 strike and the officer's Stuka dive (both `coop_mod/officer.scr::coop_air_bombing_run`).
Vanilla map planes (`global/bomber.scr`, `global/autoplane.scr`, `maps/e3l1/planes.scr`, `maps/e2l2/planeGags.scr`)
are out of scope; they are the reference recipe.

Status: **research + design only. Nothing built, nothing deployed, no game run.** Every number below is from code
reading or the offline BSP sweep in `tools/` - none of it has been confirmed in-engine yet. Phase 0 is the in-engine
check.

---

## 1. TL;DR

The planes break in five different ways, and only one of them is about tuning:

1. **They are invisible because they fly above the sky.** The C-47 flies 2200 units over the smoke. On **49 of 54**
   campaign maps the sky brush is lower than that, so the plane sits outside the world. The server never sends an
   entity outside the world: no leaf means no area and no PVS cluster (`sv_world.c:291-335`,
   `sv_snapshot.c:766-771, 789-795`). The loop sound only gets through when it is `levelwide`, and it is not. The
   2026-08-16 tuning happened on m3l3, one of the 5 maps where 2200 is still under the sky (2238 of headroom). That
   is why 2200 looked right there and 2600 "was too high": at 2600 it left the world and disappeared.
2. **They are too low and too big.** The bombing run dives to `0.4 x min(1100, 0.315 x farplane)`. On most maps that
   is **440 units, about 27 ft**, and on the 1500-fog maps only about 190 units. Meanwhile the model is full size: a
   P-47 is about 650 units across and a Stuka about 720. The wingspan is wider than the plane's height above the
   ground.
3. **They judder.** The server runs at 40 Hz (`sv_fps 40`) but the scripts move the plane on `wait 0.05`, which is
   every **second** frame. The lead-in leg uses `wait 0.1`, every **fourth** frame. The client blends between
   40 Hz snapshots (`cg_ents.c:529-546`), so the plane stops and jumps at 20 Hz, or 10 Hz on the lead-in.
4. **Their attitude snaps.** The dive shape `dip = 1 - |2f - 1|` is a V, both vertically and in the sideways
   curve. The plane holds one attitude for 35 ticks, then flips nose-down to nose-up in one tick. Bank is
   `roll = 5 x (change in yaw)`, and yaw only changes at the bottom of the V, so the "bank" is one 35-degree flick
   for a single tick.
5. **They pop in and out.** The plane spawns and is deleted in mid-air:
   - The bombing run ends at full height 900-2600 units from the target, often in plain view.
   - The C-47 path is +-7000/+21000 units. It shows up and vanishes wherever it crosses the world hull.
   - Entity positions are sent as **16-bit values at 1/4-unit precision, so they only cover +-8192**
     (`msg.cpp:34-36, 1174-1196, 2400-2404`). Anything sent beyond that wraps around to the other side of the map.

Other faults:
- Bombs drop straight down at a constant 1900 u/s with no forward speed, from points along the target line. The
  plane is bowed up to 570 units off to the side, so the bombs do not come from the plane.
- The paratroopers' chutes appear already open, 100 units under the plane, at fixed spots around the smoke and 1.5 s
  apart. The plane covers 1050 units in those 1.5 s, so later chutes appear well behind it.

**Recommendation.** Build one shared flight library, `coop_mod/aircraft.scr`, used by all three call-ins:
- **Time-based curves evaluated every server frame.** Position, heading and pitch come from the curve's own
  direction. Bank comes from how sharply it turns, smoothed.
- **`svflags +broadcast`** so the plane is sent regardless of the sky brush and visibility checks. Every position is
  clamped inside +-8000.
- **Per-map heights from a generated table, checked at run time with traces along the actual track.**
- **Entry and exit at the fog edge or the world edge**, never in plain view.
- **A scaled-down model ("forced perspective") with speed scaled to match.** A plane at 0.25-0.30 scale flying
  1000-2400 units up looks exactly like a full-size aircraft at 250-500 ft, which is the real C-47 drop height. Its
  apparent speed matches a real aircraft too.
- **Bombs follow real falling arcs, and paratroopers jump out of the door.**
- **Optional engine work:** a small cgame Doppler pitch shift. A client-side flyby entity is a later option, only if
  Phase 1 still judders at 125 fps.

Cost: about **5-6 working days** of script work plus 6-8 test runs. Add 0.5 day for Doppler, and 2-3 days if the
client-side flyby is ever needed.

---

## 2. History - what has been tried (newest last)

| when / id | what it tried | outcome |
|---|---|---|
| 07-01 `4fa27cd1` | First bombing run: a straight, flat slide moved by origin steps. | Replaced. |
| bug-070 (06-27) | Bombs dropped after the plane was already gone. Release now triggers when the plane crosses the target line (`coop_bombrun_release`). | Still current. It is geometric, not ballistic. |
| 07-05 `dd34fe30` | Strike warnings and a paratrooper buff. | - |
| bug-717 (07-17) | Crater fires were silent on BT/SH maps; switched to `coop_snd_fire_small`. | Fixed. |
| bug-927 (07-20) | The densest entity burst in the mod is the bombing run (about 22 entities). Added NULL guards and `maxentities 1024`. | Still binding: any new design must keep its entity count down. |
| bug-1054 / bug-1259 (07-22, 08-02) | Vanilla `bomber.scr`: a `waittill spawn` and a deleted-plane dereference. | Vanilla planes only. |
| bug-1253 (08-02) | **t3l2 crashed when the plane flew overhead** (renderer2 sky-portal index pointer). | Fixed, but the sky-portal maps t1l1/t3l1/t3l2 need a flyover gate. |
| bug-1323 (08-03) | The airstrike "didnt do shit" to the AB41 and opel; added the vehicle zombie rescue. | Damage side only. |
| bug-1488 (08-06) | The dive scream `coop_stuka_dive` never played; aliased it to retail `M1_PlaneBy.wav`. | Fixed. |
| bug-1514 (08-07) | XP: +5 per Air Strike kill. | - |
| bug-1848 / `c48737f7` (08-16) | User: "make it higher... fly the entire span of the map". C-47 set to 1900, then 2600 ("too high"), then 2200. Run-in 7000, run-out 21000, 700 u/s, cvars `coop_c47Alt/Run/Out/Speed`. | **2200 only works on 5 maps.** See root cause 1. |
| 08-20 user quotes in `officer.scr:3364` / `:4649` | The Stuka lead-in raised 8.2 to 12 s and made louder. The binocular strike given a 5 s lead-in. | The lead-in leg moves on 0.1 s ticks (root cause 3). |
| FEATURES "Officer / paradrop bombing-run flight" | A shared banked, diving arc whose envelope scales with `$world.farplane`. `SHIPPED-UNVERIFIED`; watch items: the farplane getter, and the bank sign. | The getter **does exist** (`worldspawn.cpp` `EV_World_GetFarPlane`). The bank only ever fires for one tick (root cause 4). |
| DECISIONS "Runtime SplinePath/flypath for the bombing run" | Rejected over a "static-plane risk", "remains the recommended upgrade". | Superseded below: a time-based curve on our own per-frame driver gives the same smoothness with no `info_splinepath` spawning. |
| bug-941, 1260, 3309, 3322 | Paratrooper **ground** behaviour: crush immunity, cover, no prone friendly fire, squad brain. | Not about flight; `parasquad.scr` is untouched by this plan. |

Two `officer.scr` comments cite the wrong bug ids: `bug-1172` and `bug-1185` on the strafe-gun lines are a deploy
incident and a font fix. Cosmetic; fix them in passing.

`docs/archive/legacy-root-2026-06/skybox_farplane_research.md` concluded that "the sky is not a height cap". That is
true for **drawing**, but it missed the **sending** side: an entity whose origin box is outside every leaf never gets
transmitted in the first place. That is the piece this plan adds.

---

## 3. How it works today

**Scripts.**
- `paradrop.scr::coop_paradrop_main`: drop height = smoke ground + `coop_c47Alt` (2200). The heading is random. The
  plane goes 7000 units back to 21000 forward at 700 u/s. It waits `run / speed`, then spawns 5 chutes at fixed
  offsets around the smoke, 1.5 s apart.
- `coop_paradrop_c47` moves the plane by stepping its origin every `wait 0.05`. Its angles are set once.
- `officer.scr::coop_air_bombing_run`:
  - Height and approach length come from `$world.farplane`: `alt = min(1100, 0.315 x fp)`,
    `approach = clamp(0.385 x fp, 900, 2600)`, with fp = 0 treated as 8000.
  - An upward ceiling trace runs **at the target only**. A sky hit leaves the height as it was.
  - The lead-in leg moves on `wait 0.1`. The dive is 71 ticks of `wait 0.05`, so it takes 3.55 s.
  - The plane is deleted where the curve ends.
- Bombs (`coop_one_bomb`): a `us_bomb` falls straight down at 1900 u/s from ground + `lowalt`, then explodes as
  `explosion_bombwall` with `radiusdamage 600 900`.

**Models.** `c47fly.tik` and `p47fly.tik` are scale 0.52; the tik says "world is in 16 units per foot", so a C-47 is
about 1552 units across (97 ft). Both tiks have `setsize -32 -32 -32 32 32 32`, so **the box that decides where the
entity is linked is 64 units**, not the visible model. `stuka_strafe.tik` has no `setsize` and uses the animation
bounds. The C-47 has no tags. `stuka_strafe` has `tag_bomb`, `tag_barrel1/2` and smoke tags. The P-47 has
`tag_barrel01-06`.

**Sounds** (`ubersound.scr:1663-1693`):
- `coop_c47_approach` is `c47_loop.wav`, distance 3500/13000.
- `coop_stuka_engine` is `M1_StukaIdle.wav`, 2500/14000.
- `coop_stuka_dive` is `M1_PlaneBy.wav`, which has a Doppler pass baked in.
- None of them are `levelwide`. The engine adds no Doppler: `snd_openal_new.cpp` gets a velocity argument, but
  `cg_ents.c:185` passes `vec3_origin`.

**Engine facts that bound the design.**
- A non-player entity is drawn by blending its origin between snapshots and its angles by quaternion
  (`cg_ents.c:525-546`). Motion is smooth only if the origin changes **every** snapshot.
- The server's distance cull is effectively 12000 units: `SV_SetFarPlane` stores the **square**, so the 12000 clamp
  always wins (`sv_game.c:1477`, `sv_snapshot.c:779-788`).
- The renderer cuts everything beyond `farplane` (fog end), and the fog profiles force `cull 1` on every map.
- `svflags +broadcast` (`entity.cpp:4176`) and `alwaysdraw` (`RF_ALWAYSDRAW`) skip the area, PVS and distance checks
  (`sv_snapshot.c:738-764`).
- Origins are sent as 16-bit values at 1/4-unit precision, so they wrap outside +-8192.
- The sky is drawn at the far depth, so a model beyond the sky brush still draws in front of it. That is standard
  Q3 behaviour and is **unverified here: gate G3**. It is also why volumetric clouds can never cover a plane (section 9).
- `ScriptModel` is a `ScriptSlave` (`scriptslave.h:246`), so the retail `flypath` works on a spawned `script_model`.
  `bomber.scr`, `e3l1/planes.scr` and `hoveringplane.scr` do exactly that, at 1000-2250 u/s with full-scale models.

---

## 4. Root causes (each with its anchor)

| # | cause | anchor | effect the user sees |
|---|---|---|---|
| R1 | The plane flies above the sky brush, so it is never sent. The 2200 drop height is above the sky on 49 of 54 maps; the bombing run's top is above it on 12. | `paradrop.scr:67`, `officer.scr:3211-3227` (a sky hit "keeps alt"), `sv_world.c:291-335`, `sv_snapshot.c:766-795` | "so high you can't see the planes" |
| R2 | The plane flies past the fog distance. A C-47 2200 units up is behind fog that ends at 1500-2300 (e1l1, m6l1a, m6l1b, m6l2b). | `fog_profiles.tsv`; renderer cut at the far plane | Same symptom, on the foggy maps |
| R3 | It dives to `0.4 x alt`, which is 190-440 units, with a full-size model. No obstacle check along the path. | `officer.scr:3250` | "too close to the ground", clips through roofs |
| R4 | It moves every 2nd or 4th server frame against 40 Hz snapshots. | `paradrop.scr:177`, `officer.scr:3291-3296, 3346` | Stutter |
| R5 | The V-shaped curve flips attitude in one tick, and bank comes from the change in yaw. | `officer.scr:3315-3343` | Snap and wobble at the bottom of the dive |
| R6 | It spawns and is deleted in view, appears and vanishes at the world hull, and has a +-8192 wrap risk. | `paradrop.scr:105-110`, `officer.scr:3266-3350`, `msg.cpp:2404` | Pops into and out of mid-air |
| R7 | Speed comes from the length of the curve (500-1500 u/s) and the leg speed differs from the dive speed. The C-47 does 700 u/s, about 30 mph on the 16 u/ft scale. | `officer.scr:3258-3260` | Floaty, or a sudden lurch |
| R8 | Bombs fall straight down with no forward speed and are not released from the plane. Chutes appear open and behind the plane. | `officer.scr:4690-4750`; `paradrop.scr:131-142, 195+` | "unrealistic" |

---

## 5. Per-map envelope

**Method.** Offline, read-only, from the retail BSPs: `tools/sky_envelope.py`, output in `tools/sky_envelope.tsv`.
- **Ground** is measured from outdoor pathnodes: those whose upward column ends in a sky brush.
- **Sky ceiling** is the first height above each outdoor node where a point leaves every valid leaf. That is the
  server's own test for sending an entity.
- **Obstacles** are the highest solid or terrain top under the sky across the play area. Static models such as
  trees are **not** counted, so traces at run time stay mandatory.
- **Fog** is the runtime value from `fog_profiles.tsv`, otherwise the worldspawn `farplane`.

**Rules** (heights in units above the median outdoor ground; 16 u = 1 ft):
- floor = max(obstacles + 384, 640)
- fog cap = 0.5 x fog
- prefer staying under the sky when there is room; otherwise fly above it with broadcast (class C)
- C-47 height H = min(fog cap, 2400)
- model scale s = clamp(H / 8000, 0.25, 1). The plane then "looks like" it is at H/s, aiming for 500 ft.
- speed = s x 2600 u/s, which is 110 mph scaled
- the visible stretch on foggy maps = 2 x sqrt((0.8 x fog)^2 - H^2)
- bomber release height = max(floor, 0.6 x H)

**Classes:**
- **A**: open, little or no fog. Enter and leave at the world or coordinate edge, out of view.
- **B**: fog-limited. Enter and leave at the fog edge.
- **C**: the sky brush is too low. Fly above it with `svflags +broadcast` (needs gate G3).
- **D**: no usable sky. Audio, flak and shadow cues only.

The "Today" column is what the shipped code does on that map.

| map | ground z median (5..95%) | sky ceiling z / clearance | fog | obstacles top95 / max (rel) | C-47 height (scale, looks like) | bomb release | visible stretch | entry / exit | today | class | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| m1l1 | 432 (160..996) | 3454 / +3022 | none | +0 / +1310 | +2400 (s 0.30, looks 500 ft) | +1440 | 16000 u, 20.5 s at 780 u/s | edge, yaw 45: -5760/+12672 | C-47 under sky; bomber ok, dives to 440u | A | isolated tall structure +1310: track trace must clear it |
| m1l2a | -32 (-248..136) | 510 / +542 | none | +286 / +526 | +2400 (s 0.30, looks 500 ft) | +1440 | 14336 u, 18.4 s at 780 u/s | edge, yaw 45: -8320/+6016 | C-47 above sky; bomber peak above sky, dives to 440u | C | sky brush only +542 over ground: fly ABOVE it with svflags +broadcast (gate G3); low-sky pockets (sky 510..1150) |
| m1l2b | -256 (-256..-256) | 1406 / +1662 | none | +0 / +670 | +1534 (s 0.25, looks 383 ft) | +920 | 16000 u, 24.6 s at 650 u/s | edge, yaw 135: -6656/+10112 | C-47 above sky; bomber ok, dives to 440u | A | isolated tall structure +670: track trace must clear it |
| m1l3a | 450 (240..450) | 2606 / +2156 | 4600 | +0 / +0 | +2028 (s 0.25, looks 500 ft) | +1216 | 6141 u, 9.3 s at 659 u/s | fog edge +-4383 | C-47 above sky; bomber ok, dives to 440u | B |  |
| m1l3b | 24 (24..280) | 1742 / +1718 | 4600 | +0 / +0 | +1590 (s 0.25, looks 397 ft) | +954 | 6637 u, 10.2 s at 650 u/s | fog edge +-4560 | C-47 above sky; bomber ok, dives to 440u | B |  |
| m1l3c | 396 (4..1104) | 2110 / +1714 | none | +0 / +482 | +1586 (s 0.25, looks 396 ft) | +951 | 10240 u, 15.8 s at 650 u/s | edge, yaw 30: -3968/+6272 | C-47 above sky; bomber ok, dives to 440u | A |  |
| m2l1 | 544 (0..648) | 2110 / +1566 | 14500 | +334 / +382 | +1438 (s 0.25, looks 359 ft) | +862 | 19072 u, 29.3 s at 650 u/s | fog edge +-15156 | C-47 above sky; bomber ok, dives to 440u | A |  |
| m2l2a | -464 (-468..-144) | 254 / +718 | 15000 | +0 / +398 | +2400 (s 0.30, looks 500 ft) | +1440 | 23515 u, 30.1 s at 780 u/s | fog edge +-15566 | C-47 above sky; bomber peak above sky, dives to 440u | C | sky brush only +718 over ground: fly ABOVE it with svflags +broadcast (gate G3) |
| m2l2b | -460 (-544..-432) | 254 / +714 | 15000 | +0 / +0 | +2400 (s 0.30, looks 500 ft) | +1440 | 23515 u, 30.1 s at 780 u/s | fog edge +-15566 | C-47 above sky; bomber peak above sky, dives to 440u | C | sky brush only +714 over ground: fly ABOVE it with svflags +broadcast (gate G3) |
| m2l2c | - | - | 15000 | - | - | - | - | - | - | D | interior / sky opening too small (0 outdoor nodes): engine audio + flak + shadow only |
| m2l3 | -464 (-480..-400) | 1854 / +2318 | none | +366 / +1422 | +2190 (s 0.27, looks 500 ft) | +1314 | 16000 u, 22.5 s at 711 u/s | edge, yaw 45: -9856/+12416 | C-47 under sky; bomber ok, dives to 440u | A | isolated tall structure +1422: track trace must clear it |
| m3l1a | 176 (-496..176) | 1462 / +1286 | none | +0 / +0 | +1158 (s 0.25, looks 289 ft) | +694 | 16000 u, 24.6 s at 650 u/s | edge, yaw 135: -13056/+7296 | C-47 above sky; bomber ok, dives to 440u | A |  |
| m3l1b | 344 (288..400) | 1462 / +1118 | none | +126 / +222 | +990 (s 0.25, looks 247 ft) | +640 | 16000 u, 24.6 s at 650 u/s | edge, yaw 135: -10496/+11392 | C-47 above sky; bomber ok, dives to 440u | A |  |
| m3l2 | 96 (-128..96) | 1120 / +1024 | 6200 | +0 / +416 | +896 (s 0.25, looks 224 ft) | +640 | 9216 u, 14.2 s at 650 u/s | fog edge +-6448 | C-47 above sky; bomber peak above sky, dives to 440u | A |  |
| m3l3 | -192 (-320..256) | 2046 / +2238 | none | +0 / +0 | +2110 (s 0.26, looks 500 ft) | +1266 | 16000 u, 23.3 s at 685 u/s | edge, yaw 45: -1408/+16128 | C-47 under sky; bomber ok, dives to 440u | A |  |
| m4l0 | 136 (-88..692) | 1726 / +1590 | 13000 | +0 / +598 | +1462 (s 0.25, looks 365 ft) | +877 | 18304 u, 28.2 s at 650 u/s | fog edge +-13571 | C-47 above sky; bomber ok, dives to 440u | A |  |
| m4l1 | 64 (-192..624) | 2078 / +2014 | 3100 | +0 / +1262 | +1550 (s 0.25, looks 387 ft) | +930 | 3871 u, 6.0 s at 650 u/s | fog edge +-2862 | C-47 above sky; bomber ok, dives to 390u | B | isolated tall structure +1262: track trace must clear it |
| m4l2 | 96 (0..368) | 1422 / +1326 | 3100 | +190 / +526 | +1198 (s 0.25, looks 299 ft) | +718 | 4342 u, 6.7 s at 650 u/s | fog edge +-3026 | C-47 above sky; bomber ok, dives to 390u | B |  |
| m4l3 | 56 (-192..232) | 1022 / +966 | 2700 | +0 / +502 | +1350 (s 0.25, looks 337 ft) | +810 | 3372 u, 5.2 s at 650 u/s | fog edge +-2492 | C-47 above sky; bomber ok, dives to 340u | C | sky brush only +966 over ground: fly ABOVE it with svflags +broadcast (gate G3) |
| m5l1a | 88 (0..360) | 958 / +870 | 3500 | +0 / +166 | +1750 (s 0.25, looks 437 ft) | +1050 | 4371 u, 6.7 s at 650 u/s | fog edge +-3231 | C-47 above sky; bomber peak above sky, dives to 440u | C | sky brush only +870 over ground: fly ABOVE it with svflags +broadcast (gate G3) |
| m5l1b | 448 (152..720) | 1598 / +1150 | 3500 | +254 / +446 | +1022 (s 0.25, looks 255 ft) | +640 | 5213 u, 8.0 s at 650 u/s | fog edge +-3530 | C-47 above sky; bomber ok, dives to 440u | B |  |
| m5l2a | 516 (244..516) | 1598 / +1082 | 5500 | +0 / +282 | +954 (s 0.25, looks 238 ft) | +640 | 8590 u, 13.2 s at 650 u/s | fog edge +-5695 | C-47 above sky; bomber peak above sky, dives to 440u | B |  |
| m5l2b | -92 (-212..40) | 1598 / +1690 | 4000 | +0 / +0 | +1562 (s 0.25, looks 390 ft) | +937 | 5585 u, 8.6 s at 650 u/s | fog edge +-3898 | C-47 above sky; bomber ok, dives to 440u | B |  |
| m5l3 | 432 (216..672) | 1790 / +1358 | 15000 | +0 / +0 | +1230 (s 0.25, looks 307 ft) | +738 | 18304 u, 28.2 s at 650 u/s | fog edge +-15701 | C-47 above sky; bomber ok, dives to 440u | A |  |
| m6l1a | 5448 (5392..5814) | 6974 / +1526 | 1500 | +0 / +0 | +750 (s 0.25, looks 187 ft) | +640 | 1873 u, 2.9 s at 650 u/s | fog edge +-1384 | C-47 above sky, past fog; bomber ok, dives to 189u | B |  |
| m6l1b | 1816 (1808..2176) | 3518 / +1702 | 1600 | +0 / +566 | +800 (s 0.25, looks 200 ft) | +640 | 1998 u, 3.1 s at 650 u/s | fog edge +-1477 | C-47 above sky, past fog; bomber ok, dives to 201u | B |  |
| m6l1c | 32 (32..60) | 1470 / +1438 | none | +158 / +206 | +1310 (s 0.25, looks 327 ft) | +786 | 11776 u, 18.1 s at 650 u/s | edge, yaw 15: -2816/+8960 | C-47 above sky; bomber ok, dives to 440u | A |  |
| m6l2a | 16 (-128..192) | 1598 / +1582 | none | +590 / +734 | +1454 (s 0.25, looks 363 ft) | +974 | 9344 u, 14.4 s at 650 u/s | edge, yaw 30: -5248/+4096 | C-47 above sky; bomber ok, dives to 440u | A |  |
| m6l2b | 320 (-80..320) | 1470 / +1150 | 1600 | +0 / +158 | +800 (s 0.25, looks 200 ft) | +640 | 1998 u, 3.1 s at 650 u/s | fog edge +-1477 | C-47 above sky, past fog; bomber ok, dives to 201u | B |  |
| m6l3a | -472 (-552..-464) | -2 / +470 | none | +0 / +614 | +2400 (s 0.30, looks 500 ft) | +1440 | 8448 u, 10.8 s at 780 u/s | edge, yaw 90: -4224/+4224 | C-47 above sky; bomber peak above sky, dives to 440u | C | sky brush only +470 over ground: fly ABOVE it with svflags +broadcast (gate G3); low-sky pockets (sky -2..318); isolated tall structure +614: track trace must clear it |
| m6l3b | - | - | none | - | - | - | - | - | - | D | interior / sky opening too small (12 outdoor nodes): engine audio + flak + shadow only |
| m6l3c | - | - | none | - | - | - | - | - | - | D | interior / sky opening too small (0 outdoor nodes): engine audio + flak + shadow only |
| m6l3d | - | - | none | - | - | - | - | - | - | D | interior / sky opening too small (0 outdoor nodes): engine audio + flak + shadow only |
| m6l3e | -544 (-544..-176) | 318 / +862 | none | +158 / +158 | +2400 (s 0.30, looks 500 ft) | +1440 | 7296 u, 9.4 s at 780 u/s | edge, yaw 105: -3328/+3968 | C-47 above sky; bomber peak above sky, dives to 440u | C | sky brush only +862 over ground: fly ABOVE it with svflags +broadcast (gate G3) |
| e1l1 | 416 (160..896) | 1726 / +1310 | 1500 | +0 / +126 | +750 (s 0.25, looks 187 ft) | +640 | 1873 u, 2.9 s at 650 u/s | fog edge +-1384 | C-47 above sky, past fog; bomber ok, dives to 189u | B |  |
| e1l2 | 544 (192..1248) | 2046 / +1502 | 5000 | +0 / +174 | +1374 (s 0.25, looks 343 ft) | +824 | 7513 u, 11.6 s at 650 u/s | fog edge +-5067 | C-47 above sky; bomber ok, dives to 440u | B |  |
| e1l3 | 176 (128..576) | 1470 / +1294 | 4200 | +590 / +782 | +2100 (s 0.26, looks 500 ft) | +1260 | 5245 u, 7.7 s at 682 u/s | fog edge +-3877 | C-47 above sky; bomber ok, dives to 440u | C | sky brush only +1294 over ground: fly ABOVE it with svflags +broadcast (gate G3) |
| e1l4 | 96 (-288..256) | 590 / +494 | 5000 | +0 / +174 | +2400 (s 0.30, looks 500 ft) | +1440 | 6400 u, 8.2 s at 780 u/s | fog edge +-4669 | C-47 above sky; bomber peak above sky, dives to 440u | C | sky brush only +494 over ground: fly ABOVE it with svflags +broadcast (gate G3) |
| e2l1 | 536 (22..1072) | 1454 / +918 | 2300 | +0 / +0 | +1150 (s 0.25, looks 287 ft) | +690 | 2872 u, 4.4 s at 650 u/s | fog edge +-2123 | C-47 above sky; bomber ok, dives to 289u | C | sky brush only +918 over ground: fly ABOVE it with svflags +broadcast (gate G3); low-sky pockets (sky 1454..1790) |
| e2l2 | 2688 (2544..3024) | 4062 / +1374 | 3000 | +190 / +190 | +1246 (s 0.25, looks 311 ft) | +747 | 4102 u, 6.3 s at 650 u/s | fog edge +-2893 | C-47 above sky; bomber ok, dives to 378u | B |  |
| e2l3 | 128 (-384..128) | 1854 / +1726 | 3000 | +0 / +0 | +1500 (s 0.25, looks 375 ft) | +900 | 3746 u, 5.8 s at 650 u/s | fog edge +-2769 | C-47 above sky; bomber ok, dives to 378u | B |  |
| e3l1 | 143 (40..556) | 958 / +815 | 2200 | +0 / +335 | +1100 (s 0.25, looks 275 ft) | +660 | 2747 u, 4.2 s at 650 u/s | fog edge +-2031 | C-47 above sky; bomber ok, dives to 277u | C | sky brush only +815 over ground: fly ABOVE it with svflags +broadcast (gate G3); low-sky pockets (sky 958..1182) |
| e3l2 | -200 (-720..-96) | 798 / +998 | 2500 | +0 / +630 | +870 (s 0.25, looks 217 ft) | +640 | 3601 u, 5.5 s at 650 u/s | fog edge +-2476 | C-47 above sky; bomber ok, dives to 315u | B | isolated tall structure +630: track trace must clear it |
| e3l3 | 323 (-620..760) | 1198 / +875 | 2400 | +0 / +0 | +1200 (s 0.25, looks 300 ft) | +720 | 2997 u, 4.6 s at 650 u/s | fog edge +-2215 | C-47 above sky; bomber ok, dives to 302u | C | sky brush only +875 over ground: fly ABOVE it with svflags +broadcast (gate G3); ground -620..760: altitude follows LOCAL ground |
| e3l4 | 1664 (832..2432) | 1982 / +318 | 3000 | +0 / +654 | +1500 (s 0.25, looks 375 ft) | +900 | 3746 u, 5.8 s at 650 u/s | fog edge +-2769 | C-47 above sky; bomber peak above sky, dives to 378u | C | sky brush only +318 over ground: fly ABOVE it with svflags +broadcast (gate G3); ground 832..2432: altitude follows LOCAL ground; low-sky pockets (sky 1982..2494); isolated tall structure +654: track trace must clear it |
| t1l1 | -6516 (-6984..-6516) | 7932 / +14448 | 5000 | +0 / +10864 | +2400 (s 0.30, looks 500 ft) | +1440 | 6400 u, 8.2 s at 780 u/s | fog edge +-4669 | C-47 under sky; bomber ok, dives to 440u | B | isolated tall structure +10864: track trace must clear it |
| t1l2 | 160 (48..224) | 1454 / +1294 | 3000 | +0 / +590 | +1166 (s 0.25, looks 291 ft) | +699 | 4195 u, 6.5 s at 650 u/s | fog edge +-2926 | C-47 above sky; bomber ok, dives to 378u | B |  |
| t1l3 | 48 (16..231) | 1214 / +1166 | 6000 | +126 / +750 | +1038 (s 0.25, looks 259 ft) | +640 | 9372 u, 14.4 s at 650 u/s | fog edge +-6213 | C-47 above sky; bomber ok, dives to 440u | A | isolated tall structure +750: track trace must clear it |
| t2l1 | 1291 (300..1949) | 3262 / +1971 | 3500 | +0 / +979 | +1750 (s 0.25, looks 437 ft) | +1050 | 4371 u, 6.7 s at 650 u/s | fog edge +-3231 | C-47 above sky; bomber ok, dives to 440u | B | ground 300..1949: altitude follows LOCAL ground; isolated tall structure +979: track trace must clear it |
| t2l2 | 1120 (16..2144) | 3710 / +2590 | 2750 | +734 / +734 | +1375 (s 0.25, looks 343 ft) | +1118 | 3434 u, 5.3 s at 650 u/s | fog edge +-2539 | C-47 under sky; bomber ok, dives to 346u | B | ground 16..2144: altitude follows LOCAL ground |
| t2l3 | 56 (8..896) | 1214 / +1158 | 2500 | +0 / +0 | +1030 (s 0.25, looks 257 ft) | +640 | 3428 u, 5.3 s at 650 u/s | fog edge +-2414 | C-47 above sky; bomber ok, dives to 315u | B |  |
| t2l4 | 640 (329..640) | 2046 / +1406 | 3600 | +0 / +462 | +1278 (s 0.25, looks 319 ft) | +766 | 5161 u, 7.9 s at 650 u/s | fog edge +-3557 | C-47 above sky; bomber ok, dives to 440u | B |  |
| t3l1 | 164 (-48..456) | 1150 / +986 | 15000 | +0 / +0 | +858 (s 0.25, looks 214 ft) | +640 | 18304 u, 28.2 s at 650 u/s | fog edge +-15726 | C-47 above sky; bomber peak above sky, dives to 440u | A |  |
| t3l2 | 52 (-160..368) | 1150 / +1098 | 16000 | +0 / +0 | +970 (s 0.25, looks 242 ft) | +640 | 16512 u, 25.4 s at 650 u/s | fog edge +-16771 | C-47 above sky; bomber peak above sky, dives to 440u | A |  |

**Totals** (computed against the median ground, so treat them as a guide; the track picker in 6.2 works per strike):
- Class **A** (16): m1l1 m1l2b m1l3c m2l1 m2l3 m3l1a m3l1b m3l2 m3l3 m4l0 m5l3 m6l1c m6l2a t1l3 t3l1 t3l2
- Class **B** (21): m1l3a m1l3b m4l1 m4l2 m5l1b m5l2a m5l2b m6l1a m6l1b m6l2b e1l1 e1l2 e2l2 e2l3 e3l2 t1l1 t1l2 t2l1 t2l2 t2l3 t2l4
- Class **C** (13): m1l2a m2l2a m2l2b m4l3 m5l1a m6l3a m6l3e e1l3 e1l4 e2l1 e3l1 e3l3 e3l4
- Class **D** (4): m2l2c m6l3b m6l3c m6l3d
- **Today's C-47 is above the sky on 49 of 54 maps.** It is only under the sky on m1l1, m2l3, m3l3, t1l1 and t2l2.

**Caveats** (the table is a starting point; the run-time check below is the real one):
- Ground uses the median, but strikes land where players are. The run-time picker measures the ground under the
  actual target.
- Obstacles leave out static models such as trees and props.
- The visible stretch and the edge runs assume a player standing under the middle of the track.
- t1l1 includes its scripted plane-ride volume. Its ground layer at -6516 and its +10864 "structure" are that
  volume, not the battlefield.
- t3l1/t3l2 use the bug-2870 node height cap (z < 500).
- m3l1a/m3l1b (Omaha): this plan only touches flight scripts. No texture, renderer or sky change is involved.

---

## 6. Recommended architecture

### 6.1 One flight library: `coop_mod/aircraft.scr` (new)

All three call-ins become thin callers. Functions:

| function | job |
|---|---|
| `ac_profile local.kind` | Returns the type constants. `c47`: model `c47fly.tik`, real height 500 ft, real speed 110 mph, door offset. `p47`: glide-bomb at 300 mph, release around 1000 ft. `stuka`: 60-degree dive at 350 mph, pull-out around 1500 ft. Each has a scale range and its sounds. |
| `ac_envelope local.target local.kind` | Reads the per-map row from `aircraft_envelope.scr` and measures the **local** ground under the target with a down-trace. Then traces along a candidate track every 512 units: down-traces for obstacles (raising H up to the cap) and up-traces for roofs or sky (picking under-sky, or above-sky with broadcast). Tries up to 8 headings biased toward the long straight run from the table. Returns H, s, v, the heading, entry and exit points, and the class. |
| `ac_track local.env` | Builds a **cubic Bezier** (or straight line + circular arc + straight line for a turn). Entry and exit points are where the slant range to every **current** player is at least 1.05 x fog (class B/C fog maps), or the world/coordinate edge (class A). Every coordinate is clamped to +-8000. |
| `ac_fly local.kind local.track local.s` | Spawns the `script_model`, sets `scale s`, and sets `svflags +broadcast` (for the whole flight on class C, otherwise only while outside valid leaves). Starts the loop sound and threads `ac_drive`. Returns the plane, carrying `ac_t0`, `ac_dur`, the control points and its speed. |
| `ac_drive` | **Every server frame (`waitframe`)**: `u = (level.time - t0) / dur`, so it never drifts and catches up after a hitch. Position is B(u); heading and pitch come from B'(u); roll = atan(v^2 x curvature / g_s), clamped to +-40 degrees, eased from frame to frame. It deletes the plane only after `u >= 1`, which is out of view by construction. |
| `ac_pos local.plane local.t` / `ac_cpa local.plane local.p` | Position or velocity at any time, and the time of closest approach. Bombs, jumpers and the fly-by sound all key off these instead of polling distances. |
| `ac_flyby_snd local.plane` | Plays the baked-Doppler one-shot (`M1_PlaneBy.wav` / `coop_stuka_dive`, plus a C-47 pass alias) at CPA minus the clip's lead. The engine loop stays on the plane. |
| `ac_fallback local.target local.kind` | Class D, or when every track fails its traces: a distant drone (loopsound on a `fx/dummy`, levelwide), flak bursts and a ground shake. A fast-moving ground shadow is optional and needs an asset (question 5). |

Notes:
- **Why not the retail `flypath`?** It would also be smooth: it moves the entity each frame through its velocity.
  But it needs runtime `info_splinepath` chains (the "static plane" risk recorded in DECISIONS), its angle smoothing
  is fixed at 0.33 per frame (`scriptslave.cpp:1630-1650`) so it behaves differently at sv_fps 20 and 40, and it has
  no bank. A time-based curve on our own per-frame driver gives the same smoothness with an exact, queryable
  position. That position is what makes bomb release and jump timing correct. **DECISIONS needs one row updated:**
  "runtime flypath" goes from "recommended upgrade" to "superseded by `aircraft.scr` time-based curves".
- **The scale trick works because, from the ground, apparent size and angular speed are all you can see.** The
  plane is `scale s` and its speed is `s x real speed`, so it covers the same angle per second as the real aircraft
  at H/s. Falling bombs use g_s = s x 512 u/s^2 (32 ft/s^2 x 16 x s), which keeps their arc in the same picture.

### 6.2 Generated per-map data

`docs/tools/gen_aircraft_envelope.py` is a promotion of `tools/sky_envelope.py`. It writes the generated
`coop_mod/aircraft_envelope.scr`: one row per map with ground, sky ceiling, fog source, floor, cap, class, and the
best long-run heading. This follows the OpenWolf rule that anything extractable is generated, never hand-typed.
Optional per-map overrides (`level.coop_ac_heading`, `level.coop_ac_class`) go only in map scripts that need them.

### 6.3 Call sites

| file / function | change |
|---|---|
| `paradrop.scr::coop_paradrop_main` | Asks `aircraft.scr` for the track; the stick is aimed so the **middle** jumper lands on the smoke. |
| `paradrop.scr::coop_paradrop_c47` | Replaced by `ac_fly c47`. |
| `paradrop.scr` jump timing | Jumper k leaves at `t_exit = t_cpa - lead + k x 0.8 s`, from the **door**: plane origin + rotated door offset. The offset is measured in Phase 0 from a still; there is no tag. Each jumper gets 80% of the plane's velocity, decaying, then about 1.0 s of static-line fall scaled by s. The canopy scales up 0.3 to 1 over 0.6 s, then the existing ride-down. Landing points come out of the physics; a final ground snap keeps them out of the void (today's `base_z - 100` guard stays). |
| `officer.scr::coop_air_bombing_run` | Becomes a wrapper: `ac_bomb_run target kind leadin wide`. Lead-in, warnings and XP stay the same. |
| `officer.scr::coop_bombrun_release` | Release time is computed from the ballistic lead (`t_rel = t_over_target - t_fall`), not from crossing a line. |
| `officer.scr::coop_one_bomb` | Ballistic: `p = p0 + v0 t + 1/2 g_s t^2` stepped every frame; the bomb is pitched along its velocity, the model scaled by s, and it starts at the plane's `tag_bomb` (Stuka) or a belly offset (P-47). Impact, blast and damage are unchanged. |
| `officer.scr::coop_stuka_mg_strafe` | Unchanged; it attaches to the plane's tags, so it follows the new motion for free. |
| cvars | `coop_c47Alt/Run/Out/Speed` stay as **overrides** (0 = automatic). New: `coop_acScale` (0 = automatic), `coop_acSpeedMul` (default 1), `coop_acDebug 1`, which prints `^~^~^ AIR map kind H s v class entry exit clip=N` for the maptest monitor. |

### 6.4 Engine (optional, separate small patches)

- **E1, cgame Doppler, about 80 lines, `cg_ents.c` only.** For entities flagged with a new `loopSoundFlags` bit set by
  a script `loopsound ... doppler` variant (`entity.cpp` `LoopSound`), work out the radial speed from the
  `lerpOrigin` change and multiply the pitch by `c / (c - v_r / s)`, with c = 18000 u/s. Using v_r / s makes the
  shift match the **apparent** aircraft speed. The AL speed of sound is never set (`qalSpeedOfSound` at `qal.c:210` is loaded but never called),
  so doing it in cgame pitch avoids changing global AL state. Each client hears its own Doppler.
- **E2, client-side flyby, about 600 lines, only if gate G2 fails.** A server command
  `hzmfly <id> <t0> <dur> <kind> <s> <p0..p3>` is broadcast and added to the `cg_servercmds_filter.cpp` whitelist.
  cgame works the same Bezier out at `cg.time` and draws a local refEntity with the Doppler loop:
  - Smooth at any fps, no snapshot traffic, no +-8192 wrap.
  - The server keeps the same curve for bombs and jumpers.
  - Costs: game.dll + cgame.dll, late joiners miss a flyby already in flight, and a protocol/whitelist entry.

---

## 7. Phased build with in-engine gates

Every phase is staged under this folder with `apply.py --check` (anchored edits, base hashes) per the agent rules.
Checks for every phase: parse-killer scan, brace running-depth, `check_mp_isolation` 22/22, `check_map_compiles`.
One test slot per phase; test clients at com_maxfps 60 unless question 8 allows a 125 fps run.

| phase | content | gate (pass condition) |
|---|---|---|
| **P0 probe** (1 run, slot "planes") | A dev-only `coop_acProbe` thread, no shipped change: (a) the same straight pass driven once with `wait 0.05` and once with `waitframe`; (b) a C-47 at broadcast above the sky on m4l3 and e1l4; (c) print `$world.farplane` on m2l1, m4l3 and e1l1; (d) a still of the C-47 from the side to measure the door offset. | **G1 judder:** with `timescale 0.25` and per-frame `screenshot`, the frame-to-frame screen movement of the plane has a coefficient of variation under 0.10 with `waitframe` and over 0.4 with `wait 0.05` (this confirms R4). **G3 above-sky:** the plane draws over the sky, is not black or unlit, and is never cut by sky faces. **G4:** the farplane getter matches the fog profile. |
| **P1 library + C-47** | `aircraft.scr` (6.1), generated envelope (6.2), paradrop switched over, plane only. | **G2 smoothness** at 60 fps (and 125 if allowed): CV < 0.10, no attitude step over 3 degrees per frame. **G5 height:** an `AIR` line on every class A/B/C map run with `coop_maptest`, `clip=0` (a plane-box sweep trace between successive positions hits nothing), and H inside [floor, cap]. **G6 visibility:** a still at closest approach from the drop point on 6 maps (m3l3, m4l3, e1l1, t2l1, e1l4, m2l1) with the plane fully on screen; no pop (the first and last frames where it is drawn are at the fog or world edge, checked by the slant-distance log). |
| **P2 bombing run** | Stuka/P-47 profiles, ballistic bombs, release from the curve. | **G7:** the first bomb hits within 150 units of the aim point (binoculars) or inside the 120-700 ring (officer); bombs are seen leaving the plane in a 4-frame strip; the lead-in still gives 10 s or more of audible warning (the 08-20 rule). **bug-927 budget:** at most 22 entities per run, checked with the existing entity census. |
| **P3 paratroopers** | Exit from the door, static-line fall, canopy tween. | **G8:** 5 jumpers leave within 4 s, spread along the track, each first appearing within 200 units of the door; all 5 land on walkable ground (the existing landing check), 0 under the map; `parasquad` brain starts as today. |
| **P4 fallbacks** | Class D: audio, flak, shake. | **G9:** m2l2c and m6l3c strike call-ins give audio plus effects, no plane spawned, no script error. |
| **P5 engine (optional)** | E1 Doppler; E2 only if G2 fails. | **G10:** pitch rises then falls through the pass on 2 clients at different spots; `r_gfxProbe`-style A/B shows no change with no aircraft present. |
| **P6 docs** | FEATURES/HISTORY/DECISIONS rows, a TRAPS entry ("entity above the sky brush is never sent", "origins wrap at +-8192"), buglog entries for R1-R8. | `docgen.py check` clean. |

Volumetric clouds: re-run G6 on 2 maps once that work lands (section 9).

---

## 8. Cost

| item | estimate |
|---|---|
| P0 probe | 0.5 day, 1 test run |
| P1 library + generated envelope + C-47 | 2 days, 2 runs (maptest sweep + stills) |
| P2 bombing run | 1 day, 1-2 runs |
| P3 paratroopers | 1 day, 1 run |
| P4 fallbacks | 0.5 day, 1 run |
| P6 docs/buglog | 0.25 day |
| **Script total** | **about 5-6 days, 6-8 test runs** |
| E1 Doppler (optional) | +0.5 day, a cgame rebuild, 1 run |
| E2 client-side flyby (only if needed) | +2-3 days, game + cgame, 2 runs |

Run-time cost:
- One plane, up to 8 bombs and up to 5 chutes each run a cheap per-frame thread at 40 Hz. That is negligible next
  to the AI threads.
- No new assets for P1-P4 (retail models and wavs). The fly-by shadow (question 5) would be the only new asset.

---

## 9. Networking and the volumetric clouds

**Network.**
- A plane moving 650-1000 u/s changes about 16-25 units per frame. That fits the 9-bit small-change encoding per
  axis (`msg.cpp:1174-1196`), so it costs about 10 bytes per frame per client: **about 400 B/s per plane per
  client** at 40 Hz.
- `+broadcast` sends it to every client for the whole flight, about 3 KB/s of server upload with 8 players, for
  10-30 s. Chutes and riders already cost about the same today.
- E2 would cut this to about 100 bytes per flyby.
- Late joiners see a broadcast plane at once; with E2 they would miss a flyby already in progress (acceptable).
- On a listen server the host sees exactly what clients see. Only the snapshot rate matters, and `net_cl.cfg` sets
  `snaps 40`.

**Volumetric clouds** (`proposals/volumetric_clouds_2026-09-26/plan.md`). The clouds are blended in **inside the
sky pass** at the far depth and read no scene depth, so **every model, planes included, always draws in front of
the clouds**. A plane can never fly into, behind or out of a cloud. Consequences:
- **Keep planes below the cloud deck.** That is realistic: C-47 drops were at 400-700 ft under the overcast, and
  dive bombers pull out low.
- Enter low over the horizon, where the cloud plan fades its output from 10 degrees down to 1 degree of elevation,
  or at the fog edge, so a plane never appears in front of a thick cloud.
- A Stuka "breaking out of the clouds" would need an extra pass: cgame fades the plane by the cloud density sampled
  in its screen direction. That needs the cloud density on the CPU or a readback. **Deferred**, noted for the clouds
  work.
- Phase G6 stills should be retaken on 2 maps after the clouds land, to check for a plane drawn over an overcast
  zenith.

---

## 10. Questions for the user

1. **Realism or screen time?** At real apparent speeds a C-47 crosses the visible sky in 3-8 s on foggy maps, and
   only 2-3 s on e1l1, m6l1a, m6l1b and m6l2b. Open maps get 15-30 s. On 08-16 you asked for "a solid 30 seconds".
   Keep real speed by default with a `coop_acSpeedMul` slider, or default it slower?
2. **Shrink the planes to make them look real?** Planes 25-30% of full size, flying 750-2400 units up, look like
   full-size aircraft at 200-500 ft instead of a giant plane just over the rooftops. Chutes and bombs scale to match.
   OK?
3. **Very foggy maps** (fog 1500-1600: e1l1, m6l1a, m6l1b, m6l2b): accept a short glimpse with loud audio, or let
   aircraft show through the fog a little (an engine change that touches only planes)?
4. **Low-sky maps** (class C, 13 maps such as m4l3, e1l4, e3l1): fly the plane **above** the map's sky box (it looks
   identical from the ground and needs broadcast), or keep it under the sky at a lower, less realistic height?
5. **No-sky maps** (m2l2c, m6l3b-d): keep the smoke and binocular call-ins with audio, flak and ground shake only, or
   disable them there? Is a fast ground shadow worth a new asset?
6. **Formations?** C-47s dropped in 3-ship Vs and P-47s flew in pairs. That is 2 more entities per run, inside the
   bug-927 budget.
7. **Engine work:** OK to do the small cgame Doppler patch (E1)? The client-side flyby (E2) stays parked unless the
   smoothness gate fails.
8. **Testing at 125 fps:** may one short test run use com_maxfps 125 to prove smoothness, as an exception to the
   60 fps quiet rule?
9. **Stuka style:** a steep, realistic 60-70 degree dive with a pull-out (more dramatic, and the bombs land about
   2-3 s after release), or the current shallow glide?

---

## 11. Files in this folder

- `PLAN.md`: this plan.
- `tools/sky_envelope.py`: the offline BSP sweep. Read-only on the retail paks. `python sky_envelope.py [maps]`
  writes `sky_envelope.tsv`; `PLAN_TABLE=1 python sky_envelope.py` prints the section 5 table. Runs in about
  20 s for 54 maps, single-threaded.
- `tools/sky_envelope.tsv`: the raw per-map measurements: ground percentiles, sky percentiles, obstacle tops, the
  longest straight run at the chosen height, and what today's code does.
