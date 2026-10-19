# Alarm vehicle arrival (MG halftrack and other Axis vehicles) - feasibility + design, 2026-10-18

Study only. No mod code written, no game run. Everything below is read from: the stock pk3 `.tik` files (main/mainta/maintt, extracted and read), the BSP entity lumps of every campaign map (parsed offline), `hzm-mohaa-coop-mod` scripts, `openmohaa-hzm/code/fgame`, `docs/TRAPS.md`, `docs/ENGINE.md`, `.wolf/buglog.json`. Statements marked PROBE were not proven by any log and need one dedicated-server boot before the build relies on them.

Series labels follow `atsupply.scr`: AA = m-maps, SH = e-maps, BT = t-maps.

## 0. Verdict in five lines

1. **A reusable "vehicle arrives on the alarm" is feasible with scripts only.** The three pieces already exist and are proven in this mod: a script-spawned `DrivableVehicle`/`VehicleTank` with a turret (`mp_vehicles.scr::veh_jeep`, `veh_tank`), a retail-style autopilot (`vehicle drive <waypoint chain> speed accel reach lookahead`, used 30+ times in `maps/`), and an infinite rocket pickup (`atsupply.scr::coop_atSupply_place`). The hidden-entry test is a copy of `reinf.scr::rnf_entry`'s eye-trace.
2. **The Opel Blitz troop truck is the safe default** (every part is retail: crew loading, unload anims, death). **The MG halftrack is the showpiece** and works too (m3l3 ships it in coop), but needs the most probing and the most tuning.
3. **There are only two real "vehicle with a gun" Axis choices in the stock game: Sd.Kfz. 251 (MG42) and the tanks.** No Kubelwagen, no motorcycle sidecar, no Sd.Kfz. 222, no flak truck exists as a model. Those are "asset work", not engine work.
4. **The route is the hard part, not the engine.** Only 5 alarm-ready maps have any vanilla vehicle chain; the other alarm maps need a hand-authored route (about 5 min a map with the build tool, same as alarm switches).
5. **Engine work is optional everywhere.** Nothing on the shortlist is blocked by C++. Three engine items would improve it (section 5); none is required for a first release.

## 1. Vehicle inventory (every stock Axis vehicle that can arrive and shoot)

"Script-drive" = can an AI driver move it along a waypoint chain with `drive`. "Gun" = a usable turret/gunner seat. All hit points below are what the tik or the vanilla think-script sets; the counter column says what a player needs.

| Vehicle | Tik (pack) | Class / script-drive / gun | Destroyable how | Vanilla maps | Counter-weapon | Engine? | Verdict |
|---|---|---|---|---|---|---|---|
| **Sd.Kfz. 251 halftrack, MG42** | `sdkfz.tik` (Pak0), `sdkfz_afrika`, `sdkfz_grau` (HRRTM), `sdkfz_no_cannon` (no gun) | `drivablevehicle`, hp 500 in tik, speed 200 (maps pass 800 to `drive`). Tik `spawnturret 0 sdkfz_mg42.tik` = `VehicleTurretGun` MG42, 45 dmg, 0.06 s. Gunner seat = passenger slot 1 (`AttachPassengerSlot 1`), +2 passenger slots | m3l3 recipe: `immune bullet/fast_bullet/grenade`, hp 300, so **rocket / explosion** kill it (`enemy_half-trak_think`). Wrecks exist: `sdkfz_d`, `sdkfz_green_d`, `sdkfz_desert_d`, `sdkfz_grau_d` | **m3l3** (BSP `halftrack`, `halftrack_gunner`, path `halftrack_path`; coop-tuned: bug-1806, 1940, 1950, 3210), **m5l2a** (`s3_halftrak`, 21-node road), m3l2 (2 STATIC `script_model`s, `scene4_halftrack` commented out), m1l2a (2 static `coop_build` props `sdkfz_afrika`, lines 4546/4658) | bazooka / panzerschreck, 2-3 rockets at hp 300 (tune; measure) | none | **Showpiece. Script-only.** |
| **Snow halftrack (BT)** | `halftrack_winter.tik` (+ `_d`), `halftrack_driveable(_mg42).tik` (player ride variants) | `drivablevehicle`, no gun in tik; `global/halftrack.scr::halftrackinit` spawns an `mg42_gun`, `AttachTurretSlot 0`, loads gunner (`turret`, `type_attack machinegunner`) and 2 passengers who bail out with `21G700_Jumpout` (bug-3196, include fix staged) | `halftrackinit` health arg (500-1000 on t2l1); t2l1 makes it immune to bullet/fast_bullet/grenade, kill by Nebelwerfer | **t2l1** (`halftrack1`, 8-node path), **t2l2** (2 enemy halftracks + player ride), **t2l3** (`halftrack1`, 10-node path) | rocket (t2l1 uses Nebelwerfer bomb script) | none | Script-only; **the only recipe with a self-driving AI gunner + passengers who dismount**. Winter art. |
| **Opel Blitz truck (troops)** | `opeltruck`, `opeltruckgreen(_canopy)`, `opeltruckgray(_canopy)`, `opel_truck_brown` (mod), `AX_V_Opel_Main`, `Opel_Truck_2_1/2_2` | `drivablevehicle`, speed 1000; no gun. `vehicles_thinkers::enemy_truck_think hp pax path trigger type guy_type` loads driver (`AttachDriverSlot 0`, `opel_driver` anim) and 1-6 passengers, drives, then `truck_unload` | hp argument (default **4000**, always pass one), `truck_killed` explosion + crew death; rockets, grenades, explosives, bullets (hp-gated) | m1l2a/b, m1l3a/b/c, **m4l1** (`truck01`, 4 pax), **m4l2** (`camptruck`), m4l3 (`realtruck`), e1l3, e2l1-3, e3l1 (4), e3l2 (8), e3l3 (8), t1l1, t1l2, t2l1-3, **t3l1** (16, `gags/t3l1_enemyspawn.scr::TruckDrive`), t3l2; `autotruck.scr` family (e3l1, e3l3, t3l1) | none needed; rocket speeds the kill, grenades/bullets work | none | **Safest. Script-only. Default vehicle.** |
| Italian troop truck | `It_V_TroopTruck.tik` | `drivablevehicle`, Opel anim/sound set | as Opel | e1l3 x4, mp_castello | none | none | Same as Opel with Italian paint. Low priority. |
| **Panzer IV / "panzer_tank"** | `panzer_tank`, `_europe(_slow)`, `_fast`, `_drivable`, `Panzer_Brown_base` (BT), `PanzerIV_w_base` (winter) | `VehicleTank`, speed 200, cannon turret slot 0 (`VehicleTurretGun`, fires every 5 s). **`PanzerIV_w_base` is the only Axis hull with a hull MG** (slot 1 `PanzerIV_w_mg42`). AI think: `enemy_tank_think` / `autotank.scr` | `MakeImmune` leaves rocket + explosion open; objective tanks have 4500 hp (t1l1) | t3l1 x16 incl. 7 hunter panzers, t3l2 x18, e3l1/e3l4 (drivable), e3l2 x5, e1l1/e1l3, m1l2b, m1l3b, t2l1-4 (winter), m3l3 (dead hulks) | several rockets (4-8) | none | **Too heavy for a recurring alarm response**; only fits t3l1 where 7 are already scripted. Set piece. |
| **Tiger I** | `tigertank`, `tigertankdsrt`, `tigertank_weak`, `tiger_base` (+`tiger_cannon`, `tiger_mg` VehicleTurretGun) | `VehicleTank`; cannon; `tiger_mg` MG slot exists in the BT pack | as Panzer | m4l2 x3 static, m5l2a/b, m1l2b x3, t3l2 x4, t1l3 | 6+ rockets | none | Static scenery / set pieces. No. |
| **King Tiger** | `kingtank` + `kingcannon` + `kingsmgun`/`axis_kingsmgun` (hull MG, `TurretGun`) | `VehicleTank` | rocket / explosion | m5l1b, m5l2a/b, m5l3, m4l3 (2 static cannons) | 8+ rockets | none | Boss-only (coop already auto-drives it on m5l2b). No. |
| **Panzerwerfer 42** (rocket halftrack) | `panzerwerfer_base(_snow/_t1l1)` + `panzerwerfer_cannon` | `vehicletank` with cannon-class rocket turret, fire every 6 s | rocket / explosion | t1l1 (end), t2l2, t2l4, t3l2 x6, e3l3 | rockets | none | Artillery set piece. No. |
| **AB41 armoured car (Italian = Axis)** | `ab_base.tik` + `ab_turret_main` + `ab_turret_mini` (MG, `VehicleTurretGun`) | `drivablevehicle`, two turret slots | e2l1 objective model: **immune bullet + bash**, dies to rocket; objective completes on its death | **e2l1** (rail "AB41", it is the mission objective) | rocket (atsupply spot already placed at e2l1 (3731,-3121,22)) | none | **Closest stock thing to an armoured car with an MG.** Reusable as a second SH vehicle only on e2l1-style maps; sound set `ab41_`. PROBE. |
| Italian tank | `It_V_CarroP40_Base` + turret | `VehicleTank`, mass 25000 | rocket | e2l3 x11 (ride-ending map) | rockets | none | No (e2l3 excluded). |
| **BMW motorcycle** | `bmwbike`, `AX_V_bmwbike`, `bmwbike_camo/_grau` | `drivablevehicle`, speed 750, **solo rider, no sidecar, no gun**; `enemy_bike_think` exists | bullets (hp small), `bmwbike_d` wreck | m1l3b x2, e1l3 x2, e2l2 x5, t1l3 (scripted), t2l2 | none | none | Cheap "scout" arrival if wanted. Not a fighting vehicle. |
| Mercedes staff car | `mercedes.tik` | **`Animate` = static prop, not drivable** | n/a | e1l3, t3l1 x4, mp_flughafen | n/a | tik override could set `drivablevehicle` (data-only, PROBE: wheel tags). No gun seat | Prop. Drivable only with a tik override; gun needs a glued MG (bruteForceMGOrigin hack from m3l3). **Only-with-extra-work.** |
| European civilian cars / delivery trucks | `european_car_*`, `european_delivery_truck_*` | `drivablevehicle` but civilian | - | t1l3 | - | none | No. |
| Sd.Kfz. flak / 20mm flak truck, sidecar bike, Kubelwagen, Sd.Kfz. 222 | **do not exist** | - | - | - | - | none (needs a new model) | Out of scope; asset work, not engine work. |
| Static emplacements (88mm, 20mm, nebelwerfer, MG42 nests) | `flak88turret`, `p_flak88`, `20mmflak`, `p_nebelwerfer` | `FixedTurret` / `TurretGun`, mannable by AI, **not mobile** | rocket / explosion (flak), bullets (MG) | m1l2a, m3l2, m5l2a/b, t3l1, t3l2 | - | none | Cannot arrive. A 20mm flak glued on an Opel bed is a **script-only hack** (bunker.scr gluing recipe); unverified, not recommended first. |
| Aircraft (Stuka, FW190, C-47), trains (`bp44train`), boats | many | scripted fly-bys / rail | - | - | - | - | Out of scope (not "arrives by road"). |

**Not Axis, ignore:** Willys jeep, GMC truck, Sherman, Churchill, T-34 (Allied/Soviet in BT), Higgins boats.

### What each blocker needs

| Blocker | Script-only? | If engine: where, size |
|---|---|---|
| Spawn a drivable halftrack/truck at runtime (not from the BSP) | **Yes.** `mp_vehicles.scr::veh_jeep` (DrivableVehicle + `spawnturret 0`) and `veh_tank` (VehicleTank, model set AT SPAWN) are live. Halftrack not yet proven by name: PROBE-1 `spawn DrivableVehicle model "models/vehicles/sdkfz.tik"` then `spawnturret 0`. Engine already forces `PlaceTurret` for post-level turrets (`vehicle.cpp:5375`). Caveat from t2l2 (`halftrack_driveable.tik` comment): a tik `spawnturret` line nulls the vehicle in MP at BSP time; sdkfz.tik has that line, m3l3 coop works with it, so only a post-level spawn needs checking. | If PROBE-1 fails: `Vehicle::SpawnTurret` / DrivableVehicle spawn path, S (~50 LOC, 0.5 day) |
| Autopilot along a runtime-built route | **Yes.** `drive` takes any `SimpleEntity` chain; `spawn info_waypoint targetname n1 target n2 origin ...` is a documented-working pattern (CLAUDE.md). PROBE-2: `Vehicle::SetupPath` walks `ent->Next()`; confirm a chain spawned after level spawn links (mod already copies chains at runtime for actors). | If it does not link: `vehicle.cpp::SetupPath` (~3600), S |
| AI gunner shooting from a vehicle MG | **Yes, two proven recipes.** (a) m3l3: gunner AI disabled, MG fired by script (`setaimtarget` on a wandering `script_origin`, `startfiring`, tuned damage/spread: bugs 1806/1940/1950); (b) `halftrack.scr`: `gunner turret mg`, `type_attack machinegunner`. Engine already scatters/limits `VehicleTurretGun` for AI (bug-1950). **Trap:** AI fires every frame at `sv_fps`, not `firedelay` (bug-3638), `coopaibelt 1` gates it. | Better target selection / suppress-and-burst = `actor_turret.cpp` + `vehicleturret.cpp`, M (2-4 days). Optional. |
| Vehicle engine sound | **Mostly data.** `sdkfz_snd_*` aliases are scoped to `maps "m3l3 m5l2a t2l2 t2l1"` (ubersound.scr 415-424); `opeltruck_snd_idle` to `m1l2 m1l3b m1l3c m4 t1l1 t1l2 t2l2` (so **m4l2/m4l1 ok, t3l1 run only, e3 maps silent**); `tank_snd_idle` to `m1l2b m3l3 m5 t3l1 t3l2 train t1l3`; `bmwbike_snd_idle` to e1l3/e1l4/e2l2. On every other map the vehicle is **silent** (same trap as alarmbell). Widen the `maps` lists (data-only, remember `fix_vo_pools.py` KEEP_BARE, bug-3160). Also bug-1478 (OPEN): spawn-time sounds resolve to nothing because the alias table is empty during entity spawn; runtime-spawned vehicles are NOT affected. | The known "flapping" `snd_start/stop/idle` state machine (`vehicle.cpp` 2276, 2432, 3539, 3610, 5796-5846) is undiagnosed in the logs I read. Script workaround (DECISIONS.md:131): silence the SoundSet and run `autotruck.scr`'s own `loopsound`. Engine fix S-M after diagnosis. |
| Destroy + wreck | **Yes.** `removeondeath 0` + `immune` set + `waittill death` + wreck model (`sdkfz_green_d`) + `damaged_collision` is the m3l3 / `vehicles_thinkers::enemy_half-trak_think` code. `Vehicle::CoopZombieRescue` (bug-1323) already stops "entombed at hp<=0". | none |
| Make a placed static vehicle drivable (m3l2 sdkfz x2, m1l2a decor) | **Yes by replacement**, not conversion (a `script_model` cannot change class): remove the prop, spawn a `DrivableVehicle` at its pose (`scene2::KFiveInit` recipe). | none |
| Mercedes / civilian car drivable | tik override to `drivablevehicle` (data) + glued gun | wheel-tag layout unknown: PROBE; if hopeless, new asset. **Only possible with extra work.** |
| Sidecar MG bike, Kubelwagen, flak truck | **No model exists.** | New asset (+ a tik); not an engine change. |
| Infantry/AI pathing around a stopped hull | Vanilla fix: a brush `script_object` mask + `setcollisionentity` + `disconnect_paths` (m3l3 `halftrack_mask`). A runtime vehicle has no brush model. PROBE-3: does the vehicle's own hull block AI? Else park it at a spot where it does not cut the only route, and call `disconnect_paths` on arrival. | Bot navmesh is world-only (bug-2842); campaign AI uses pathnodes. Dynamic obstacle = engine M. Avoid by choosing stop points off the main route. |
| Player steals the parked halftrack | `Vehicle::DriverUse` lets a player take the driver slot (`vehicle.cpp:4016`). Keep an AI driver seated, or `lock` the vehicle (bug-1258 recipe). | none |

**Candidates that become possible ONLY with engine or asset work:** armoured car with MG on non-e2l1 maps is script-only (AB41); sidecar/Kubelwagen/Sd.Kfz. 222/flak truck = new assets; Mercedes staff car = tik override (data) with a PROBE; none needs C++ to exist. **Engine work improves quality, not feasibility** (section 5).

## 2. Existing systems this plugs into (what to reuse, not reinvent)

- **Alarm lifecycle** - `coop_mod/alarm.scr` (459 lines, defaults off: `coop_alarm 0`). `alm_waves` runs while `level.coop_alarmLive == 1`, gap `coop_alarmWaveGap` 40 s, cap `coop_alarmCap` 8 alive, size 3/4/5 by 1-2 / 3-4 / 5+ players, entry from `reinf.scr::rnf_entry`, men from `coop_counter.scr::counter_squad ... "alarm"`. Gate `alm_blocked` already refuses stealth (`level.coop_stealthMap`), disguise (`level.coop_enableDisguises`), own-alarm maps (m1l2a m2l3 m6l1c m6l2a m6l3a e1l4 m2l2a), Omaha, mp, maptest, lobby. **The vehicle hook belongs inside `alm_waves` (one extra "vehicle wave" call at wave 2 or 3) and inherits the whole gate and the shut-off (shoot the bell = vehicle withdraws).** Alarm-ready maps (alarm_points.json): m1l1, m2l1, m3l2, m4l1, m4l2, e3l1, e3l2, t1l1, t3l1 (e2l1 armed with 0 points) plus m4l3 adopted via the vanilla `alarmer.scr`.
- **Hidden-entry test** - `reinf.scr::rnf_entry`: candidate must have ground, room for a man, no living player within 900 u, **no player eye (+60 z) with a solid-world line (`traced ... mask 1`, fraction >= 1.0 rejects) to the point (+50 z)**, and a scout finds a path to the nearest player. Copy the trace, not the scout (vehicles use their own route).
- **Vanilla "vehicle parked out of sight, then moved to the road"** - `maps/m4l1.scr::truck01_drive`: truck waits at (2080,-224,-800) under the map, then `.origin = (1823 225 -120)`, `.angles = (359 105 0)`, then `enemy_truck_think 3000 4 $truck01_path NULL green "human//german_wehrmact_soldier.tik"`. The coop dev had to add a player-kill loop there because **a player standing on the spawn spot made the mission stick** (comment "someone will stand where the truck spawns"). Our version must test a clear volume instead of killing players.
- **Rocket supply** - `coop_mod/atsupply.scr::coop_atSupply_place pos yaw kind tag shells`: real launcher tik + `item_heavy_ammobox` shells, engine `set_respawn` so each player can take one and it refills (10 s). `kind` "bazooka" gives bazooka (US), PIAT (British) or panzerschreck (German-uniform missions) via `coop_atSupply_model`. Existing spots to reuse: t3l1 x4 (5511,-1756,-44), (3392,-4384,24), (536,-4878,20), (-1956,-3105,0); e2l1 (3731,-3121,22); t1l1, t1l3, m5l1b, m5l3. m3l3 has retail panzerschreck + shells in the BSP (`scene0_`/`scene4_panzerschreck`).
- **Reinforcement crews** - `vehicles_thinkers.scr::truck_load/truck_unload` (driver + passengers, default crew model `german_afrika_private`, bug-1277), `halftrack.scr::halftrack_loadpassengers/passenger_unloader`.

## 3. Per-map assessment (all campaign maps; Omaha excluded)

Verdict key: **EASY** = alarm-ready map AND a vanilla vehicle + drivable chain exist in the BSP (reuse it, no authoring). **POSSIBLE** = needs a hand-authored route (drive/place nodes with the build tool) or alarm points, or vehicle precedent without a road. **NO** = excluded (stealth/disguise/Omaha/ride-or-cutscene ending/own alarm) or no usable road.

Route facts are node counts and end coordinates from the BSP; "road is drivable and wide enough" is **assumed from the vanilla truck/tank using it, not measured** for any map. Where I list a vehicle chain I did not verify the player spawn distance; the runtime visibility test decides.

| Map | Alarm-ready | Vehicle precedent in BSP / script | Vanilla drive chains | Verdict | Reason |
|---|---|---|---|---|---|
| m1l1 | yes (2 sw) | intro Opel trucks as scripted script_models | none | POSSIBLE | night fort, truck only in the intro cutscene; route must be authored |
| m1l2a | own alarm (go-loud klaxon) | Opel x2; 2 static sdkfz_afrika props | `truckpath1` 11n (5688,-3968,8)->(4184,-1568,64); `latertruckpath` 15n (1536,-464,-88)->(1244,2842,-120) | POSSIBLE | blocked from the generic alarm by `ownalarm`; hook the existing klaxon instead; two real truck roads |
| m1l2b | no | Opel, 3 desert Tigers, panzer, jeep | `truck01_path` 17n (1664,1833,-248)->(-1672,3272,-224); `jeep_path` 8n; `tank02_path` 13n | POSSIBLE | roads exist; needs alarm points |
| m1l3a / b / c | no | jeep/truck escort rides | `weez_juice` 15n etc. | NO | ride maps (counter_denied) |
| m2l1 | yes (2 sw) | none | none | POSSIBLE | no vehicle or road precedent; author a route |
| m2l2a / m2l2b | no | - | - | NO | stealth / disguise |
| m2l2c | no | none | none | NO | no vehicle precedent, disguise family |
| m2l3 | own alarm | train | - | NO | own alarm, train leaves |
| m3l1a / m3l1b | - | Higgins | - | NO | Omaha, never |
| m3l2 | yes (3 sw) | **2 static `sdkfz` script_models at (-1921,1208,-145)**, 4 dead PzIV | only infantry runto chains `scene3_*` | POSSIBLE | halftrack prop exists (replace by a real one), no vehicle road |
| **m3l3** | no (needs points) | **sdkfz ambush + gunner**, Tiger `scene4_tank`, dead PzIV; panzerschreck + shells in BSP | `halftrack_path` 6n (-904,5240,-136)->(-1648,4576,-136); `scene4_tank_path` 14n (3000,888,-304)->(2912,1520,-264) | EASY on the vehicle side | all parts proven in coop; short road; mission-fixed halftrack so a second one is spawned; needs alarm points |
| **m4l1** | yes (2 sw) | Opel `truck01` (4 pax) | `truck01_path` 12n (1776,384,-144)->(2688,3184,328) | **EASY (truck)** / POSSIBLE (halftrack) | vanilla "parked below the map, then moved" recipe; mission truck uses the chain (clone the coordinates) |
| **m4l2** | yes (3 sw) | Opel canopy `camptruck`, 3 static Tigers | `camptruck_pathgate` 8n (5240,-800,264)->(6624,1904,40); `camptruck_pathpark` 10n (6624,2184,8)->(4424,4456,264) | **EASY (truck)** | gate-to-camp road; alarm switches are west (x -3000..-6500) so pick the chain by distance |
| m4l3 | adopted (vanilla alarmer) | Opel `realtruck`, 2 static King cannons | `realtruck_path` 42n (-3712,-4416,56)->(-2112,1664,56) | POSSIBLE | long road but it starts at the player start (opening truck ride): entry would be seen |
| m5l1a | no | burnt car | none | NO | no vehicle, no road |
| m5l1b | no | King Tiger | - | NO | tank ending |
| m5l2a | no | **sdkfz `s3_halftrak` (5712,3561,257)** | `s3_halftrakpath` 21n (5442,3540,304)->(-6487,6665,304) | NO for alarm (tank ride) | but the **best long-road hidden-entry test bed** |
| m5l2b / m5l3 | no | King Tiger / panzers | tank paths | NO | tank ending / bridge set piece |
| m6l1a, m6l1b, m6l2b, m6l3b | no | none | none | NO | no vehicle precedent (m6l2b train) |
| m6l1c, m6l2a, m6l3a | own alarm / stealth | - | - | NO | stealth / own alarm |
| m6l3c-e | no | - | elevator waypoints | NO | interior |
| e1l1 | no | jeep ride | - | NO | ride |
| e1l2 | no | Sherman | - | NO | outro cutscene |
| e1l3 | no | 12 Opel, Italian troop trucks, panzers, bikes, Mercedes | none | NO | truck-escape ending |
| e1l4 | no | trucks | - | NO | stealth / disguise |
| e2l1 | armed, **0 points** | **AB41 armoured car (rail objective)**, Opel x2, gliders | `searchlight_alertpath` 5n | POSSIBLE | rocket spot already placed at (3731,-3121,22); needs alarm points; AB41 is the mission objective so a second hull would be spawned |
| e2l2, e2l3 | no | scooters, Veltro, P40 tanks | patrol paths | NO | FinalJeep / tank endings |
| e3l1 | yes (2 sw) | Opel x4, drivable panzer, jeep, GMC | `campgermanparadeorigin` 4n only | POSSIBLE | vehicles present, no road chain; author a route |
| e3l2 | yes (3 sw) | **Opel x8**, panzer_europe x5 | none (generic `t###` nodes only) | POSSIBLE | many trucks, no chain; author a route (a scripted truck already trapped a bot, bug-2899) |
| e3l3, e3l4 | no | K5 train / jeep ride | - | NO | ride endings |
| t1l1 | yes (3 sw) | Opel x1 (`gags/t3l1_enemyspawn.scr::TruckDrive $truck_1path`), end tank | chain not resolvable from the BSP (script-created) | POSSIBLE | truck driven by script; end tank has its own AT spot |
| t1l2 | no | Opel x2, boats | none | POSSIBLE | small; no alarm points |
| t1l3 | no | Tigers, bikes, trains | `tank1path1` 27n | NO | scripted train/bridge ending |
| t2l1 | no (**allysquad compile error**, bug-3984) | **halftrack1 + gunner, parked_halftrack**, winter Pz IV x6 | `halftrack1_path` 8n (1800,-3056,544)->(-1160,-4584,448) | POSSIBLE | halftrack is the mission objective (Nebelwerfer kill), compile bug must be cleared first |
| t2l2 | no | 2 enemy halftracks + player ride | - | NO | ride |
| **t2l3** | no (needs points) | **halftrack1 + gunner**, winter panzers | `halftrack1_path` 10n (2544,3056,56)->(1892,808,80); `panzertank_path` 17n | EASY on the vehicle side | halftrack + `halftrack.scr` crew recipe; sdkfz sounds not scoped to t2l3 (widen) |
| t2l4 | no | Panzerwerfer, winter Pz IV x3 | strafe path | POSSIBLE | low priority |
| **t3l1** | yes (2 sw) | **Opel x16**, 7 hunter panzers, Mercedes, **AT supply x4 already placed** | `s10_truck3_path` 11n (1388,6724,200)->(1530,2652,200); `s10_truck_path` 17n (6084,-1040,56)->(3531,3780,56); `s10_truck1_path` 9n (4152,-5772,56)->(5023,-3924,56); `s10_truck2_path` 34n (-2744,-4852,56)->(-2108,-6308,56) + 7 tank paths | **EASY (truck)** / POSSIBLE (halftrack) | best-supported alarm map: four truck roads, crews, rocket supply, already armour-heavy |
| t3l2 | no | tanks, King Tigers | many tank paths | NO | tank ride |
| training, co_lobby*, credits, void | - | - | - | NO | not missions |

## 4. Top 5 candidates (exact entry / route / stop)

Entry = first node of the chain (a vehicle is created there only if the visibility test passes). Stop = last node. Cover/space is a judgment from the alarm point coordinates, not a measured clear volume: every stop needs the PROBE-3 "hull fits and AI does not clip" check.

1. **t3l1 (BT) - truck default, halftrack probe-able.** Entry `s10_truck3_path` head (1388,6724,200), road south through (1384,6258) (1384,5872) (1376,5400) ... (1396,2744) to **stop (1530,2652,200)**, 11 nodes, ~4100 u. Alarm switch 2 is at (1581,3091,236), 440 u from the stop: the truck stops at the alarm. BSP truck `s10_truck3` at (1390,6992,192) is the vanilla start. Second option `s10_truck_path` (6084,-1040,56)->(3531,3780,56). Rockets: existing atsupply spots; add one near (1530,2652) behind the nearest wall. Sound: `opeltruck_snd_run` lists t3l1, `_idle` does not: widen.
2. **m4l1 (AA) - 4-troop truck.** Vanilla hidden start (2080,-224,-800) then pose (1823,225,-120) angles (359,105,0); `truck01_path` (1776,384,-144) ... **stop (2688,3184,328)**, 12 nodes. Switches (2707,-3853,244) and (3788,4935,620): the stop is ~2070 u from the second. Recipe verbatim: `enemy_truck_think 3000 4 <path> NULL green "human//german_wehrmact_soldier.tik"` (use hp 400-800, not 3000). Mission truck uses the chain: clone the coordinates into our own `info_waypoint`s, do not reuse the named entities.
3. **m4l2 (AA) - camp truck, gate arrival.** Entry the gate node (5240,-800,264), `camptruck_pathgate` 8n to (6624,1904,40), continue `camptruck_pathpark` (6624,2184,8) ... **stop (4424,4456,264)**. Total ~18 nodes. Weakness: alarm switches are at (-4931,1927), (-2997,4421), (-6484,3235), about 9000 u west of this road, so it only fits when the squad is in the east camp: the route chooser must pick "stop nearest the squad", and the vehicle is skipped otherwise.
4. **m3l3 (AA) - the one proven halftrack with MG and the rockets next to it.** BSP `halftrack` (vehicles//sdkfz.tik) at (-729.9,5373.4,-136) angle 220, gunner `halftrack_gunner` (waffenss_shutze) at (-702,5390,-72), path `halftrack_path` (-904,5240,-136) -> (-1032,5128) -> (-1192,4984) -> (-1392,4808) -> (-1544,4672) -> (-1648,4576,-136) (6 nodes, only ~900 u; extend it). Panzerschreck `scene0_panzerschreck` / `scene4_panzerschreck` + 7 shells already coop-replaced (`coop_replaceBazookaPickup`, respawn 5 / 10 s). Not alarm-ready (needs switch points) and the vanilla halftrack is a mission set piece, so the alarm halftrack would be a second hull spawned with the same recipe. **Use as the halftrack test bed.**
5. **t2l3 (BT) - snow halftrack with self-driving gunner and dismounting infantry.** BSP `halftrack1` (vehicles/halftrack_winter.tik) at (2543.7,3288.4,96) angle 270, gunner `halftrack1_gunner`; `halftrack1_path` (2544,3056,56) ... **stop (1892,808,80)**, 10 nodes. Recipe is the retail `global/halftrack.scr` (`halftrackinit`, `halftrack_loadpassengers`, `halftrack_drive ... unloadpassengers=1`). Needs bug-3196's `level_t2l1.tik` include fix for the dismount and the sdkfz sound maps widened. Not alarm-ready.

Honourable: **m5l2a** `s3_halftrakpath` 21 nodes (5442,3540,304) -> (-6487,6665,304), the longest road with an sdkfz on it; a tank-ride map, so only a hidden-entry test bed. **m4l3** `realtruck_path` 42 nodes (-3712,-4416) -> (-2112,1664) starts on the player start, so unusable for hidden entry.

## 5. Design

### 5.1 Hidden spawn (never visible, never on a player)

Data: `docs/tools/alarm_vehicle_routes.json`, per map a list of routes `{name, kind: truck|halftrack, nodes:[[x,y,z],...], stop:[x,y,z]}` (generated like `alarm_points.json`; vanilla chains are copied by coordinate, authored routes captured in build mode). A generator `gen_alarm_vehicle_routes.py` writes the script data.

At vehicle-wave time (inside `alm_waves`, never before wave 2 and never in the first 60 s):
1. Pick routes whose **stop is within 600-2200 u of the nearest living player** and which have not been used this pull.
2. **Entry test** for a route: (a) no living player within 1800 u of node 1 (a halftrack is large; the drawn model pops from far), (b) for each living player, `traced (eye + 60 z) -> (node1 + 70 z) mask 1`: fraction must be < 1.0 (same call and mask as `rnf_entry`), done twice at hull height and at ground height, (c) the same for node 2 and node 3 (first ~600 u of road, so it cannot roll into view from a corner within the first second), (d) `traced` hull box (-90 -70 0)-(190 70 80) at node 1 is clear of solid and of any player (do NOT kill players in the way, as m4l1 does).
3. If nothing passes: retry every 2 s for up to 20 s, then try the next route, then **skip the vehicle** (log `^~^~^ ALMVEH skip: no hidden entry`). Never spawn at a "fallback distance".
4. Create the vehicle hidden and not solid, settle two frames on the ground, **re-run the eye trace**, then show and start the engine. If a player appeared in view during the settle, delete and go back to step 3.
5. After arrival the vehicle is visible by design (that is the point). A watchdog (every 1 s) removes it if it has moved < 40 u in 10 s while driving (stuck), or if it has been idle with no player within 3000 u for 90 s and nobody has line of sight.

### 5.2 Vehicle and crew

- Truck (default): `enemy_truck_think hp pax path NIL type guy_type` with hp 600 / 900 / 1200 by player count, pax 3 / 4 / 5 (cap 6), existing `truck_unload` at the stop, men join the alarm cap (`flags["coop_waveSrc"] = "alarm"`).
- Halftrack (maps with a probed route): `spawn DrivableVehicle` + `spawnturret 0 "vehicles/sdkfz_mg42.tik"` (PROBE-1), AI driver on `AttachDriverSlot 0`, gunner on passenger slot 1, MG recipe = m3l3 (script-driven burst with wandering aim point, `coop_htSpread` 110, damage ~50) so it cannot out-shoot a coop squad, `immune bullet/fast_bullet/grenade`, health 300 / 450 / 600, rocket and explosion open. 0-2 passengers dismount with `Jumpout` at the stop.
- One alarm vehicle alive at a time; one per pull; none while a mission-critical vehicle scene is running (`level.halftrack_alive` on m3l3).
- Coop-specific: `rendereffects "-shadow"`, driver/gunner `physics_off` + `dontdropweapons` (bug-3051/3052: holster drivers), `lock` the vehicle so a player cannot drive it, `disconnect_paths` on arrival (retail), wreck `sdkfz_green_d` with `damaged_collision`, remove wreck after 90 s.
- Sound: widen the `sdkfz_snd_*` / `opeltruck_snd_*` `maps` lists to the target map, and add `autotruck`-style `loopsound` as the fallback if the engine state machine flaps.

### 5.3 Rockets (so the squad can actually fight it)

- At alarm start (before the vehicle is chosen) call `atsupply.scr::coop_atSupply_place` at a **fixed logical spot per map** stored with the route (a guard post / ammo crate on the players' side, behind real cover, 300-900 u from the stop, never in the vehicle's line of fire). Use the existing spots where there is one (t3l1, e2l1). The weapon kind comes from `coop_atSupply_model` (panzerschreck on German-uniform missions, bazooka/PIAT otherwise); shells x3; infinite respawn is already the system's behaviour.
- Feed line once: "Rocket crate marked" (small feed, like m3l3's `feed_all`). Radar/objective pointer is optional.
- Never rely on the player already carrying a launcher. If no supply spot is defined for the map, **the vehicle does not come** (hard rule: no unbeatable halftrack).
- Anti-soft-lock: if the vehicle is alive 150 s after arrival it drives off along the reversed route and counts as "repelled"; kill gives XP via the existing vehicle-kill counter (bug-724 path).

### 5.4 Scaling

| Players | Halftrack hp | MG | Troop truck pax | Alive cap |
|---|---|---|---|---|
| 1-2 | 300 | spread 110, 40% AI dmg | 3 | 8 incl. wave men (existing `coop_alarmCap`) |
| 3-4 | 450 | same | 4 | same |
| 5+ | 600 | same | 5 | same |

Pulls: max 2 per mission (existing `coop_alarmMaxPulls`); vehicle on pull 1 wave 2-3, and on pull 2 only if the first vehicle is dead or gone.

### 5.5 Exclusions

Inherit `alm_blocked` (stealth, disguise, own-alarm, Omaha, mp, maptest, lobby). Add: any map in `coop_counter.scr::counter_denied` (ride / cutscene endings), maps with `level.coop_noCounter`, no route/no supply spot, fewer than 1 living player, a vehicle set piece in progress. Hard-blocked list for this feature: m2l2a, m2l2b, m6l1c, e1l4 (stealth); m1l2a, m2l3, m6l2a, m6l3a (own alarm); m3l1a, m3l1b (Omaha); all ride-ending maps.

### 5.6 Risks

| Risk | Kind | Mitigation |
|---|---|---|
| Halftrack spawn path not proven (PROBE-1) | script, maybe S engine | one boot on m3l3 before building |
| Runtime waypoint chain does not link (PROBE-2) | script, maybe S engine | spawn the chain with `target` links at map start, hold it |
| Hull blocks AI/players, no brush mask (PROBE-3) | script (stop off-route) / M engine | choose stops off the main route; `disconnect_paths` |
| Silent vehicle (alias `maps` scoping) | data | widen lists; check `fix_vo_pools.py --check` |
| Flapping engine sound | script workaround | autotruck loopsound, or S-M engine fix after diagnosis |
| MG shreds a squad (AI fires at sv_fps, bug-3638) | tuning | copy m3l3's spread/damage block, `coopaibelt` |
| Stuck vehicle on unmeasured geometry | script | position watchdog + removal |
| Player in the spawn spot | script | clear-volume test, no kill |
| Entity count | script | one vehicle + crew (~6-10 ents) per pull; cap 1 |
| t2l1 `allysquad.scr` compile error (bug-3984) | existing bug | not on the critical path (t2l1 is not first) |
| Alarm itself unproven in playtest (defaults 0) | schedule | this feature rides on it; ship behind `coop_alarmVeh 0` |

## 6. Build recipe (each step a dedicated-server boot, feature off by default)

0. **Probes** (1 boot each on m3l3 and m4l1): PROBE-1 spawn `sdkfz.tik` as `DrivableVehicle` + `spawnturret`, print `queryturretslotentity 0`; PROBE-2 spawn a 6-node `info_waypoint` chain after level spawn, `drive` it, check `waittill drive` fires; PROBE-3 park it, trace a scout actor past it. Log `^~^~^ ALMVEH probe ...`.
1. `coop_mod/alarmveh.scr` skeleton: `veh_pick_route`, `veh_entry_ok` (the section 5.1 test, tested with a dummy player at a known position), no spawn. Cvars `coop_alarmVeh 0`, `coop_alarmVehDebug`.
2. Truck path end to end on **t3l1** (`s10_truck3_path`): spawn, drive, unload, death, wreck. Count Script Errors = 0.
3. Rocket crate at alarm start via `coop_atSupply_place`; verify respawn and one pickup per player.
4. Halftrack on **m3l3** (BSP reused for coordinates only): MG burst script (copy `halftrack_mg_targeting` and `halftrack_aim_wander`), health scaling by `coop_aiScaleTest 1/2/4`, kill with a rocket, wreck.
5. Route data + generator for m4l1, m4l2, t3l1, then authored routes for the POSSIBLE alarm maps (m1l1, m2l1, m3l2, e3l1, e3l2, t1l1).
6. Sound ubersound widen + `fix_vo_pools.py --check`; engine-flap fallback.
7. Regression: stealth/disguise maps (m2l2a, e1l4) print no `ALMVEH`; ride maps print `ALMGATE blocked`; Omaha untouched.
8. User playtest, then decide defaults.

Effort estimate (agent time, script only): probes 0.5 day, steps 1-4 2-3 days, step 5 about 4 hours per authored map, step 6 0.5 day. Engine items, if wanted, are separate.

## 7. Optional engine items (not required)

| Item | Where | Size |
|---|---|---|
| Diagnose and fix the vehicle idle/start/stop sound flapping | `fgame/vehicle.cpp` 2276, 2432, 3539, 3610, 5796-5846 | S-M, needs a log-captured repro first |
| Better AI gunner (burst/pause, target switching, no free spread tuning) | `fgame/actor_turret.cpp`, `vehicleturret.cpp` | M |
| Vehicle as a dynamic AI obstacle (hull blocks campaign AI like a brush mask) | `navigation_recast_obstacles` family / `VehicleCollisionEntity` | M |
| Autopilot stuck detection | `Vehicle::EventDriveInternal` / think | S (scripts can do it) |

## 8. Open questions for the user (defaults in bold)

1. Is a **troop truck (3-5 infantry, no MG) the standard alarm vehicle on most maps, with the MG halftrack only on the 2-3 maps where a halftrack route is proven** (m3l3, t2l3, later t3l1)? Default: **yes**.
2. May the halftrack come only on maps that already have a **fixed rocket crate spot**, or should the crate be placed per alarm? Default: **fixed spot per map, crate marked at alarm start**.
3. Who authors routes for the 6 alarm maps with no chain (m1l1, m2l1, m3l2, e3l1, e3l2, t1l1)? Default: **you drive/place nodes with the build tool, agent turns them into the route file**, same as the alarm switches.
4. If nobody kills the vehicle: **it withdraws after 150 s** (no soft lock) vs stays until killed. Default: **withdraws**.
5. Halftrack difficulty: **spread 110 and 40% AI damage as on m3l3 now**, one gunner, 300/450/600 hp by squad size. OK?
6. Should the first release include the **armoured car (AB41)** on SH maps, or only truck + halftrack? Default: **only truck + halftrack**.
7. Engine work: **none for the first release**; use the sound-alias widening and loop-sound fallback. Approve the sound-state diagnosis only if it still flaps in playtest?
8. Timing: vehicle at alarm wave 2-3 (**about 50-70 s after the pull**) and at most one per pull, none in the first 60 s of a map. OK?
9. If no hidden entry exists at that moment: **skip the vehicle** (never spawn it in view). OK?
10. Should the m1l2a own-alarm (go-loud klaxon) also bring a truck? Default: **no for now** (own-alarm maps stay out).
