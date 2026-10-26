# m2l2c "Cover Blown" finale objectives - DESIGN / status (2026-10-25)

Branch `m2l2c-objectives` (worktree `H:\hzm_work\m2l2c_mod`, off `objectives2-next`; the objectives2 worktree was busy with m1l3b WIP).
Commits `128e8b6e` + the mesh-gate update. Nothing merged, pushed or deployed. 4 files: new `coop_mod/objx_m2l2c.scr`, hooks in `coop_mod/objx.scr`,
`maps/m2l2c.scr`, `coop_mod/coop_counter.scr` (m2l2c added to the generic counter-attack deny list, consistent with fix1025-mod).

## What the user sees (all MAIN objectives, the map's own list)
1. **Operate control panel A** - a red wall switch on the walkway east of slip A. Hold Use 2 s (actprompt "hand" ring).
2. **Operate control panel B** - same, east walkway of slip B. A and B can be done in either order or at once.
3. **Radio the Allies and hold the room** (appears when 1+2 are done) - the radio stands on the bench in the fuel-drum storage room
   (screenshot 1). Hold Use 3 s, then hold the zone until the Allies confirm the train (counter-attack clock, "HOLD m:ss").
4. **Exfiltrate through the vents** (appears when 1-3 are done; the old vanilla "Exfiltrate." slot, now slot 4). The mission-end
   gate (`objx_gate`) refuses the exit until 1-3 are done (verified: "GATE closed 0/3").

## Crane cycle (a real sequence, defended)
Operating a panel starts the cycle; progress is a pure function of a 0..1 counter, so pausing = not advancing:
trolley (rusty slab under the ceiling) glides to the load 0-22 % - hook block comes down 22-36 % - load made fast 36-42 % -
lifted 42-54 % - carried over the U-boat 54-84 % - released: load falls with gravity, impact blast (explosion_tank + conflagration +
bombwall, `earthquake`), fire + smoke along the hull (stock emitters, persistent). Sound: `crane_run` loop on the trolley while it
moves, `gate_iron_open1` on release. HUD (own slots 121/122): "DEFEND THE CONTROL PANEL" + `CRANE A 62 PCT   CRANE B 18 PCT`. **The `%` sign cannot be shown**: every HUD font (facfont-20, verdana-12/14, courier-15) draws `%` as `.` and `%%` as `..` (engine string filter), so it reads "PCT".
* **Defend:** from 4 s in, Axis waves (3/4/5/6 men for 1/2-3/4-5/6+ players, spawn slots 800-1100 u away on the two walkways / pier
  ends, never in a player's view, alive cap 14 = `coop_counterCap`) hunt the squad. Any wave man within 560 u of the panel for 4 s
  **jams** the crane (stops, `gate_iron_locked`, red HUD line, feed). A player clears them (none within 700 u) and holds Use 1.5 s
  again to restart it. Verified in the harness (jam -> killwave -> re-activate -> "Crane A is moving again" -> impact).
* **Cycle length** (user: 30-60 s): 30 s (1 player), 40 s (2), 50 s (3-4), 60 s (5+). Override `coop_m2CraneSecs`.
* Parts are stock only: `electrical_switch_pulse` (x2.5), `shape_slab_ibeam` (trolley), `static_cablespool_full` (hook),
  14 x `shape_post_iron` (cable), **`coop_build/shape_cube_crate` x3 = a big wooden cargo crate as the load**, all `+fullbright`
  (the slips are unlit above the lamps). Model check (20 candidates, `media/recon/sheet_load*.jpg`): crate_carry, cube_crate, supplydrop, nazi_crate,
  88shell, fuel_tanks render in the air; the torpedo / exp_crate / box_crate_* did not in this map's lighting.

## Radio hold, gate, Axis
* Hold length = 150 s x (0.45 / 0.7 / 1.0 for 1 / 2 / 3+ players) = **67 s / 105 s / 150 s** (existing `ox_hold_scale`; `coop_objxHoldSecs` overrides).
  Clock runs only while a defender stands in the zone (r 360 around the storage room), pauses, winds back, "zone lost" rules unchanged.
* Radio calls (feed text + `coop_radio_on` + `m2l2_radio1` static, no invented VO): at the call, at 66 %, at 33 %, "train confirmed" at 0.
* Waves every 30-40 s, size 4/6/8 (+carry) split over three entries, rotating which gets the extra man:
  **stairs** (spawn on the deck above, walk down the staircase into the room: (3612 -4016 -260)), **north** (outside the pens, north
  corridor: (3412 -2952 -496)), **pier** (north end of the east pier: (3190 -2150 -496)). Entries in view of a player are skipped.
* **Mesh gate (user decision 2026-10-26): left SHUT, untouched.** It is static world clip (stills `mesh_gate_still_*.jpg`), so the fake-lift clones were
  removed. That wave uses the nearest REAL doorway instead: the red arch into the barrel room (west wall x 3423, y -3580), which has no door
  in the map. A clone of the gate2 mesh brush stands in it: open while the squad walks in, **shut when the radio is used**, and on each wave it
  slides 150 u along the wall (motor rattle, `gate_iron_open1/2`) when the FIRST wave of the hold comes (feed "They're breaking through the door!") and then STAYS OPEN for the rest of the hold, so no entry ever queues outside it. Door-wave men are staged in the corridor beside it (3367 -3330..-3480, hidden by the room wall, never in a player's line of sight) and are sent INTO the room by `m2_door_guide` (runto goal points at the arch, squad hunt paused while it guides; a man that stalls 3 polls is set in front of the arch, one that stalls there steps through it).
  Proof: `m2l2c_barrel_door_burst.gif` (door in the arch, slides open, Axis step through, door closes; run d2 log: a man at (3406 -3359) -> (3620 -3732) inside the room).
  Also kept: the stairwell gate (foot of the staircase to the deck room): closed from map start, lifts when the radio is used.
  A soft barrier pushes players back from both gates while the hold runs ("players can't cross").
* Entries per wave now: **barrel-room door, stairs, north (outside the pens), pier (outside the pens)**; men are split over them and the extra
  man rotates. 1 player = 1 man each (4/wave); 3+ players 6-8 per wave; alive cap 14.

## Deviations / things the user should decide (honest list)
* **(superseded by the mesh-gate section above)** The stairwell gate was first built because the screenshot-2 gate was taken to be elsewhere. **The mesh gate in screenshot 2 is world geometry** (the big X-braced fence with barbed wire at the north-east of the pens: no
  entity). The map's only movable gate is `gate2` (script_object `*51`, origin (-2718 -6344 -380)), but it and `gate1` (world, x -1485,
  next to the spawn) enclose a dead-end corridor: harness proof - an AI spawned between the gates jitters in place and cannot reach
  the start area; the player cannot pass gate1. Moving `$gate2` lets a player through (tested) but nothing behind it can path out.
  Closest alternative implemented: a clone of that same brush at the staircase foot, which really moves and really matters.
  If you prefer a different doorway (e.g. the red door frame into the radio room, 130 wide: the panel overlaps the wall) it is one
  data line (`m2_gate`, `m2_gateyaw`).
* **No crane exists in the BSP** (entity lump + static-model lump checked: two U-boat hull models, lamps, no gantry). The crane is
  built from stock parts (above); `subcrane.tik`, `crane_grey.tik` and a moved `exp_crate1` did not render in the slips (bug-4274).
* Only **two** U-boats remain (UB1 x 260, UB2 x 2760) so there are two crane objectives. They burn but do not sink (static models).
* Wave men stop at their stand-off (350-500 u) instead of walking onto the panel, so "reached the panel" = pressing within 560 u.
* Single-player harness only: the 2+ player scaling is arithmetic from the existing helpers, not play-tested.
* The vent exit is the existing ladder in the deck room; "vents open" = the stairwell gate staying open and the barrier gone.

## Placement log (z = floor -512 unless noted; `media/placement_m2l2c.png`, `tools/placement_audit_m2.py`: fails 0, warns 5)
| item | position | note |
|---|---|---|
| panel A / B (switch) | (792 -3740 -452) / (3225 -3600 -452), yaw 0 | on the wall face x 799 / 3231, walkway x~748 / ~3190 |
| load A / B | (738 -3880) / (3185 -3720) | walkway, not solid |
| hook park A / B | (500 -3880 -120) / (2935 -3720 -120) | carry z -120, trolley z 225 |
| drop point A / B | (260 -3800) / (2760 -3400), deck z -449 | blast + fire along the hull |
| radio | (3656 -3540 -482), on the bench | Use point reach 110 |
| zone | (3615 -3850) r 360 | storage room |
| stairwell gate / barrier | (3372 -3856 -380) yaw 90 / box (3300 -3950)-(3435 -3780) | foot of the stairs |
| barrel-room door (clone) | (3423 -3580 -380) yaw 0, slide +150 in y | red arch; shut during the hold, opens per wave |
| door wave staging | (3367 -3330..-3420 -512) | corridor beside the door |
Audit warns (accepted): panel B 158 u from vanilla AI t1478; B load and the radio have 5/8 clear directions (narrow walkway / bench by the wall); a vanilla barrel inside the radio footprint.

## Proof (in `media/`, logs in `tools/logs/`, frames in `H:\hzm_work\m2l2c_work\runs`)
* `m2l2c_crane_cycle_defend.gif` - one full crane A cycle incl. a wave that jams it, re-activation, release, impact, fire.
* `m2l2c_barrel_door_burst.gif` - the barrel-room door wave (3 extra men via `coop_m2MeshBoost` for the GIF).
* stills: `hud_main_objectives.jpg`, `crane_panel_prompt.jpg`, `crane_impact.jpg`,
  `radio_hold_use.jpg`, `gate_closed.jpg`, `gate_open.jpg`, `radio_room_hold_hud.jpg`, `recon/` contact sheets (map survey).
* Runs: `run_e3` (latest full flow incl. mesh waves, "Next map is: m2l3"), `run_e2` (full flow, fast cvars): cranes A+B done (jam handled), radio held 40 s, `OBJX ALL DONE`, exit trigger -> "Next map is: m2l3";
  `run_x1` exit refused with 0/3; `run_f2/e1` full flows; `run_j8` defend/jam loop; **0 Script Errors in every run** (dedicated harness
  = the listen-server boot of the private client; a separate dedicated-server run was not made).

## Next (polish, awaiting your call)
A frame/posts on the clone edges to blend with the static X-braced frame, a spark/steam fx on the jammed panel, voice via existing Allied radio aliases if you pick lines,
2-4 player playtest of timings, optional second Axis door at the pens fence, hold the stairs wave until the gate is fully up.
Harness tooling is in `tools/` (`m2run.py` stages: start,craneA,craneB,jam,radio,gategif,exit; `M2FLAGS=test` starts the radio at once;
`M2EXTRA="set coop_m2CraneSecs 20;..."`). Debug cvars: `coop_m2CraneSecs`, `coop_m2WaveGap`, `coop_m2Test`.

## Update 2026-10-26 (user decisions: fake the mesh gate; HUD text; crane load)
Done: mesh-gate fake + waves (above), stairwell gate kept as an extra entry, wooden cargo crate load, own HUD. Open point for you: the opening reads
as a fake layer lifting off the fence (the real fence is solid and stays), because world clip cannot be removed; a genuinely walkable
opening needs a different doorway.

## Update 2026-10-26b
Mesh gate left shut (clones removed); that wave now bursts through a sliding door clone in the barrel-room arch (above). Stairs / north / pier entries unchanged.
Side effect: the door is shut for most of the hold, so men from the other entries wait outside it until the next burst opens it (every ~30-40 s).

## Update 2026-10-26c
Door now opens on the first wave and stays open (no queueing). Door-wave men are guided into the room (run d11: 3 of 4 inside the room within ~15 s of the burst, the 4th
walking back in; `m2l2c_barrel_door_burst.gif` re-captured). Without the guide only 1 of 4 reached the room (the hunt loop idles in the corridor / detours via the pier).

## Update 2026-10-26d
No-pop-in rule: `m2_door_guide` repositions a man (set in front of the arch / through the doorway) only when `m2_los_any` says no living player has a clear line to
EITHER his current spot or the destination (head height, any distance, any view direction); otherwise he keeps walking. The wave placement in the corridor is checked the same way.
Localization: `global/localization_coop.txt` now has entries for 'DEFEND THE CONTROL PANEL', 'CRANE A/B JAMMED - CLEAR THE PANEL, USE IT AGAIN' and 'Hold: the storage room'
(the log's LOCALIZATION ERROR); run d12 shows none left for these.

## Update 2026-10-26e - the REAL mesh gate ($mesh_gate, edited BSP) - verification checklist
Wiring (`coop_mod/objx_m2l2c.scr`): `m2_rg_init` finds `$mesh_gate` (NIL on the stock map = fallback: mesh entry skipped, barrel-room door + stairs + north + pier as before),
`disconnect_paths` at start; the mesh entry of a wave spawns its men behind the closed gate (never in any player's LOS, `m2_los_any`), `m2_rg_open` lifts it 180 u in 1.5 s
(`gate_iron_open1/2`, `elevator_run` loop, feed "The Axis are forcing the mesh gate!"), `connect_paths`; 20 s later it lowers and `disconnect_paths`. A soft barrier keeps players off the open gate during the hold.
Shipped files: `maps/m2l2c.bsp` (md5 ea4d151c...) + `maps/m2l2c.pth` (md5 19b7b35d..., from H:\hzm_work\maprebuild\final) in the mod worktree (the build catch-all packs them), test pak `H:\hzm_work\m2l2c_work\zzzzzzzzzz_coop_maps.pk3`. Harness used an overlay pk3 with the same two files.

| # | check | result | evidence |
|---|---|---|---|
| 1 | AI path through the open gate, blocked when closed (final .pth) | **PASS** | `run_ve3`: AI at x 3730 goal x 3560: closed -> stays at 3725.9; open -> reaches 3591. `run_gm1`: wave men cross x 3636 within 2 s of the lift (3745 -> 3577). Only 2-3 of 4 men cross before it closes (others idle at the standoff behind it) |
| 2 | full playthrough on the edited map | **PASS** | `run_f9`: cranes A+B (B jammed, cleared, re-run), radio hold 75 s with wave 1 entries mesh+door+stairs+north (wave 2 door/stairs/north/pier), `OBJX ALL DONE`, exit -> "Next map is: m2l3", **0 Script Errors** |
| 3 | closed gate vs stock: bullets / explosions / AI sight / sound | **PASS (bullets by data, not by shot)** | explosion: radiusdamage 300 at x 3600, target behind at 3680: hp 823 on BOTH maps; `cansee` through the fence = 1 on both; `traced` through the fence identical (0.892 = the man behind it, both maps). Bullets: my +attackprimary damage probe never damaged even the CONTROL target in front (test invalid), so the proof is structural: the moved brushes keep the stock brush/side shader indices (2487 -> 3798 etc., `bspedit` dump: shader 39/22/36 and every side's shader identical), i.e. the same content flags (clip, not SOLID) and Phase 2 measured bullets passing on retail. Sound: not measured (no engine path from brushes to sound occlusion was found; unchanged by the edit) |
| 4 | player clip | **PASS** | `run_vs2` (stock) vs `run_ve2/ve3` (edited), identical numbers: east-bound walk / jump / crouch at y -3480 .. -3145 incl. both gate edges: stops at x 3617-3622 (y -3480 = the side wall, 3560); west-bound from behind stops at x 3653-3671. No squeeze found |
| 5 | gl1 renderer | **PASS** | `media/gate_closed_edited_gl1.jpg` (and `recon/sheet_vis.jpg`): fence + barbwire drawn, no missing faces; (gl2 stock/edited identical) |
| 6 | dedicated server + client; stock client | **PARTIAL** | dedicated (`omohaaded`, private home, edited BSP): loads, `$mesh_gate` found, 0 Script Errors (`run_ded3`). The harness client cannot JOIN a dedicated at all (it reaches CS_PRIMED then drops while restarting its client game) - reproduced identically on the stock map (`run_ded4`), so it is not caused by the edit; the rcon open/close view on a client was therefore not seen. Stock client on a patched server: not tested; from the code (PHASE2.md): no content check, the client would meet entity model *73 it does not have = bad submodel / drop. Every player needs the same pak (or the fallback does not apply to the client) |
| 7 | vis / area portals / HOM | **PASS** | 10 views around the gate (both sides, edges, oblique) stock vs edited gl2: identical except weapon/HUD (mean abs diff 0.1-1.7; 18-27 on three views were checked by eye: blood/AI/weapon sway only, `recon/sheet_vis.jpg`); no missing faces |

`media/m2l2c_mesh_gate_wave.gif`: the real gate lifting and Axis coming through it (3 extra men via `coop_m2MeshBoost`, spawn LOS check off for the GIF).

## Update 2026-10-26f
Mesh gate policy changed: after its first wave it STAYS OPEN for the rest of the hold (like the barrel-room door), so stragglers always get through and later mesh waves reuse it with no
timer; it lowers and `disconnect_paths` 6 s after the hold is won (`m2_rg_close`). Chosen over "close when every man is through" because the men idle at their standoff
and a per-man tracker would keep the gate hostage to them. GIF re-captured (`m2l2c_mesh_gate_wave.gif`): the observer was untargeted (`notarget`) while the gate lifted (clean frames),
targeting switched back on once it was open so the men come through; the blood tint returns in the last third when they start hitting him (the damage flash cannot be disabled even in god mode).
Test cvar `coop_m2OnlyMesh 1` limits waves to the mesh entry (GIFs only).

## Update 2026-10-26g - user v3 playtest fixes + U-boat sinking (edited map 33eda311)
* **Real crane objects.** Diagnosis of "models do not render" (bug-4274): script-spawned stock models get no light grid in the slips and render black against the dark hall; a per-entity
  `light 1 0.9 0.75 <radius>` (rides with the entity) fixes it. Rig now = real dockyard gantry `miscobj/crane_grey` (x2.77, across the slip), real hook block with cable `miscobj/subcrane`,
  real torpedo `items/torpedo` as the load, cable of iron posts; all non-solid (walkway walk test with/without rig identical: A 3019/4584 vs 3019/4580, B 3036/4565 vs 3039/4560).
* **Jam/resume.** `m2_foes_los` counts only LIVING men within 400 u with a trace to the panel; jam after 4 s; automatic resume after 3 s clear (60 s cap); HUD "CRANE A JAMMED - CLEAR THE AREA" /
  "CRANE A RESUMING" + feed. Harness `jamtest`: man behind the pier wall and a dead body do NOT jam; 3 jam -> auto-resume cycles (4.7 s) and the crane completes.
* **No clones on the edited map**: the stairwell gate / barrel-room door clones are built only when `$mesh_gate` is missing (stock fallback).
* **Mesh wave** now starts DEEP behind the gate: three spots in the east block (4020,-4136), (4244,-4376), (4020,-4888) - hidden from every sampled defender position (`losgrid`),
  9-11 s of running over the rebaked graph, staggered 3 s, gate lifts ~6 s after the first appear; men are walked with `runto` to the front of the gate (squad hunt paused, enemy off while guided).
* **U-boats sink** (edited map: `uboat_a` / `uboat_b` submodels + `_up`/`_low` visuals; `bind` does NOT move the visuals here, they follow by hand): blast + fires, then 5 s later list (9 deg), bow roll 4 deg,
  sink 560 u over 32 s (`coop_m2SinkSecs`), groans (`vent_squeak1-5`, `king_vehicle_crash1`), ripples/spray/steam at the waterline (`waterRing`, `fx_oceanspray`, `pipe_steam` spawned as script_models, cached in
  `m2l2c_precache.scr`), anybody on the hull is set on the nearest quay every 0.2 s, visuals + fires hidden once under. Stock map: burn only. Lit hulls (`light 0.8 0.75 0.65 500` + `lightOn`) vs stock:
  `media/uboat_lit_vs_stock.jpg` (close, a little greener/greyer on the tower). Full playthrough on the final build: both boats sink, gate wave, `ALL DONE`, "Next map is: m2l3", 0 Script Errors.

## Update 2026-10-26h - officer reinforcements, radio audio, hold length, scaling

**Officer reinforcements (all maps).** `officer.scr::coop_call_reinforcements`: for on-foot waves (types 0/1/3/6) `reinf.scr::rnf_entry` now takes the officer position and path-probes to HIM (not just the nearest player). No hidden point now -> wait 5 s and retry (up to 2 min); the authored zone is used only if `rnf_unseen` (no living player has a trace to head or feet, none within 600 u). Otherwise the wave is dropped, never placed in view. Log: `OFFICER wave r spawn=... visible=0 retries=n`.
On m2l2c (`level.coop_officer_wavehook`, set in `m2_load`): `m2_officer_wave` sends the men through the real mesh gate (the hidden east-block spots, gate lifts for them) and `m2_off_guide` runs each to his own slot on a ring (140 u) round the officer, re-ordering when stalled (after 3 stalls: runs to the officer himself), then hands him to normal combat. Per-man log `OFFMAN w=.. #.. spawned/ARRIVED/FAILED`. Harness, 3 calls x 4 men: 12/12 arrived (21-48 s, within 260 u of the officer; one slot was off the path graph and fell back to "run to the officer"). Stock map: first unseen entry (stairs/north/pier), same guide. Other maps: officer.scr path only; the 3-map check (`tools/m2other.py`, `rnftest`) gave m1l1 pick visible=0, m3l1a and m4l1 "no hidden point right now" (retry path, nothing spawned in view).

**Radio audio** (`sound/hzm/m2l2c/*.wav`, aliases in `ubersound/coop_audio.scr`, ship in `zzzzzz_co-op_hzm_mod_assets_snd.pk3`; credits in `SOURCES.txt`: voice by the user with ElevenLabs, gunfire from stock MOHAA sounds): `m2l2c_radio_call` (use), `m2l2c_radio_mid` (~50% of the hidden hold, +-3 s), `m2l2c_radio_confirm` (hold won), `m2l2c_radio_burst` (4 variants, every 20-40 s between voices), `m2l2c_radio_static` (idle loop). Everything is `playsound` on the radio model (positional, min 300 / max 1400 u), nothing local/HUD (the old hold-start `coop_radio_on` to every player is skipped for this objective). `m2_say` keeps one clip at a time. Harness log: call t=58.6, burst 99.9, mid 123.8, burst 135.1/165.1, confirm 181.6, no overlaps, 0 Script Errors. Volume/falloff by distance was NOT audibly verified (headless harness); values are the alias distances above.

**Hold length / HUD.** Hidden timer (1p 120 s, 2p 180, 3-4p 240, 5+ 300; log `radio hold length`; verified 1p `total=120s`, faked 4p `total=240s`, mid clip due 62 s / 118 s). The HUD says `HOLD THE RADIO ROOM` (no digits); the hold ends with the confirmation transmission. Waves: gap 25 s (+0-10), size = `counter_wavesize` + 1 man every 3 waves (max +3), alive cap 14.

### Scaling by player count (m2l2c; `m2_pc` = `counter_players`, test cvar `coop_m2Players`)
| | 1 | 2 | 3-4 | 5+ |
|---|---|---|---|---|
| radio hold (hidden) | 120 s | 180 s | 240 s | 300 s |
| wave size (`counter_wavesize`, +ramp) | 4 | 4 | 6 | 8 |
| wave gap | 25-35 s | same | same | same |
| alive cap (`coop_counterCap`) | 14 | 14 | 14 | 14 |
| crane cycle (`m2_cycle_secs`) | 30 s | 40 s | 50 s | 60 s (5+) |
| men per crane wave (`m2_crane_men`) | 3 | 4 | 4 (5 at 4) | 5-6 |
| crane jam sensitivity | fixed: living Axis within 400 u with LOS, resumes after 3 s clear (60 s cap) |
| officer reinforcement count | `counter_wavesize` per call (officer.scr `coop_reinf_*` helpers elsewhere) |
Sampled: hold length and crane cycle when each starts; wave size/cap every wave with the LIVE count (late joiners/leavers count from the next wave).

**Other objectives2 maps (m1l1, m1l2a/b, m1l3a/b/c)** share `objx.scr::ox_hold_run`: hold = authored secs x `ox_hold_scale` (1p x0.45, 2p x0.7, 3+ x1.0; authored 120/150/150/150/150/120+90+150 s -> 1p 54-68 s, 2p 84-105 s, 3+ full), wave size `counter_wavesize` (4/4/6/8), gap 30 s (+0-10), cap 14, sampled live per wave and at hold start for the length. Snipers/MG42 teams and officer waves follow their own `coop_reinf_*` / `reinf_mg.scr` scaling, unchanged. I did not re-verify those maps in-engine this round.

## Update 2026-10-26i - officer routing is global
`officer.scr::coop_reinf_route` / `coop_reinf_guide` (all maps, cvar `coop_reinfRoute 0` = off): after a type 0/1/3/6 wave spawns, each reinf-class man near the spawn point runs (`runto`, re-ordered when stalled, after 3 stalls straight to the officer) to his own slot on a 140 u ring round the officer, then fights (`attackplayer`); a player within 350 u hands him to combat early; 90 s cap. One log line per man (`REINF man w=.. #.. spawned/ARRIVED/ENGAGED/FAILED`). `rnf_entry` now also samples 14 candidates 1200-3500 u round the officer, path-probes them to him (28 probes / 12 paths), and prefers entries with no sight line to the officer (open-sight ones are the fallback). Maps with `coop_officer_waves_at_zone` keep their authored zone but now wait until no player sees it (retry 5 s x24, then drop).
Real-officer harness runs (`tools/m2off.py`, `coop_reinfMg 0`, mask = infantry): m4l1 4/4 ARRIVED (7-13 s), visible=0; m1l1 wave 2 ARRIVED (wave 1 men died 1.5-6 s after spawn at a hidden point with no player within 600 u - cause not found, open); m2l3 authored zone 250 u from the officer (map author's choice), visible=0, men arrive instantly. m3l1a has officer policy "none" (user request), so it has no officer to test.

## Update 2026-10-26j - v4 playtest pass (objective names, bar HUD, crane redesign, spawns, gate, radio)

**Objectives.** The two main objectives read "Destroy U-622" (crane A) and "Destroy U-355" (crane B); done text "U-622 is destroyed"; feeds "Use the crane on U-622 - hold Use at the control panel", "... is hit!", "U-622 is going down!". Panel prompt keeps "CRANE A/B". Stock-map fallback uses the same strings (names do not depend on the BSP).
**Marker.** `m2_marker` re-issues `current_objectives` after every `ox_set` of a main objective (m3l1a recipe): first main objective that is published and not done (A, B, radio), so either crane order works. Log: `marker -> main objective N (id) location (...)`; verified A -> B in the harness (radio follows when it publishes).
**HUD.** Title ("DEFEND THE PANEL" / "CRANE JAMMED" / "CRANE RESUMING"), the boat name(s), and one progress bar per running crane (QTE plate + fill shaders, slots 124/125 and 127/128; green running, amber jammed, "CLEAR THE AREA" in jam). Hold timer: the in-zone HUD branch still drew "HOLD m:ss" (one `counter_hud` call was missed in 3f052602); fixed, the radio HUD says "HOLD THE RADIO ROOM" only.
**Smooth motion.** Crane pose and U-boat sink now step every server frame with a time-based fraction (was 10 Hz / 5 Hz); jam logic on a 0.2 s timer. Log proof (`coop_m2SinkDbg 1`): dz grows 0.001, 0.004, 0.009 ... per 25 ms frame (ease-in), no stepping.

**Crane rig - measured, redesigned.** Ceiling underside (grid trace) is flat z 255 over both slips; slip A: west quay x -250..-200, water -150..0, ledge 50..100, hull 150..350 (collision top -189), ledge 400..450, water 500..650, east walkway 700..750, roof slab from x ~775 (underside -136). Slip B is the same shifted +2500 in x (+500 in y); its east slab starts at ~3195. The old rig stood a stock gantry (`crane_grey`, native 157x523x365, scaled x2.77 = 1012 tall: through the roof) on the water and lowered the hook onto the walkway. Now: bridge beam of 8 stock iron posts laid along x at z 235 (roof 255), end trucks + two 6-post runway rails at the walls (A x -225..735, B 2275..3170, i.e. clear of the slabs), a trolley under the beam, 14-post cable, real hook block, real torpedo. The load is pre-hung (nothing is lowered to a walkway); carry at z 110, hook never below z 40, boat collision top -189. `m2_sweep` box-traces hook block, load (400 long), trolley, cable and the beam span at 61 poses per crane: **0 intersections for both cranes** (control box inside a hull registers solid). Stills: `media/crane_views_A_start_mid_late.jpg` (panel / north quay / west quay at start, mid-carry, drop).
**Crane waves.** Crane-defend men no longer use fixed quay points through a view-cone test: `m2_cw_pick` = the officer picker (`rnf_entry`, now with the quay walkways as curated candidates) then the crane's own quay points; `m2_cw_ok` = floor under it, hull fits, no sight line from any living player (head and feet), >= 900 u, then ONE man at a time set on the floor. Log per man `crane A wave N man k spawn=(...) grounded=1 visible=0` (all grounded=1, visible=0 in the runs), `... ARRIVED at the panel after 15 s`. When no point is hidden the wave waits and retries (never in view); with the player standing at the open quay this delays waves - accepted.
**All wave men.** `coop_ground_watch` (counter_squad and officer routing): grounded now, re-checked for 5 s, floating men put on the floor below; one `GROUND ... grounded= fixed=` line each (harness: all grounded=1 fixed=0).
**Mesh gate.** The soft barrier now starts when the REAL gate opens (it only started with the stairwell clone, i.e. never on the edited map): a player set into the opening is put back at x 3566 (verified). The wave spawns deeper: (4000,-5600), (4500,-5200), (4000,-5000), path to the gate 2200-2600 u (scout `pathdist`, gate open), gate opens 9 s in.
**Radio.** Native scale (the x2.0 set overhung the bench), yaw 270 (back to the north wall, panel toward the room), solid with a symmetric box that turns with the model (TRAPS T9); stills `media/radio_native_scale_views.jpg`. Subtitles ([Radio], g_subtitle), dialog-channel voice clips, late clip + static loop as in 2026-10-26h/i.
**Props.** `.tik` script_models are SOLID_BBOX by default (TRAPS T9): the objectives2 scene props are solid already; m2l2c's radio and wall switches are explicitly solid; the crane parts are non-solid on purpose (they hang over the water, out of reach). A full per-prop audit table for the six other maps was NOT produced (only the one `prop` entry in objx_points and the work props exist as data; `coop_objxPropLog 1` logs bounds / grounded / clips for scene props).
