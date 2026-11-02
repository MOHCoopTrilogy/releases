# Archived from docs/OPEN.md on 2026-11-01 (stale: 2.5 months, superseded by later releases)

## Awaiting the next playtest (2026-08-17)

- **PUSH BOT TRAVERSAL** (bot-traversal pins 2829/2830 done + soak-validated 2026-09-22: cellSize 8, e3l2
  `smalldoor1`, m5l1b exploders - see buglog).
  - **USER-REVIEW BATCH 2026-09-23 (bugs 2832-2852; detail in buglog).** m5l1a **USER-VERIFIED** (spawns+zones in
    front of the closed map-end gate, gate cut from the navmesh, intact end-bombing building). m4l2 soak-PASS, awaiting
    user: under-map spawn snap fixed (box trace + 64u drop cap, all maps), radios intact + sparks off, crash train +
    track gates REMOVED (as SP's crash does), road gates north of the truck CLOSED + cut (out of bounds beyond), sandbag
    + barbed-wire crossing removed via cmpatch/m4l2_mp*.txt, spawns re-derived with a soak REACH filter. e3l2 wire +
    walls; e3l3 exploders; m5l3 PULLED. BOTS (all maps): reaction time, slower combat turn, range-scaled misses
    (bug-2840), wounded cover thrash (2841), partial-path handling (2849), 16k A* pool (2850). Titles: invented place
    names corrected against each map's worldspawn title (2851).
    m4l2 round 4 (soak-PASS, awaiting user): 20 depot wire prefabs + floating props gone, 13 doors open, MG42 hill
    slope cut in BOTH halves (2856, 2867), track gates CLOSED + cut; route = yard -> auto-cycling LIFT (navlinks
    `elevator`, 2862) -> tunnel -> station. Lift verified: axis ride both ways; allies ride down incl. under fire (6v2
    soak: 6 rides, hits taken mid-ride - 2866). Even teams: the lift is axis zone 9/10, allies reach it only when
    winning. e3l2 soak-PASS awaiting user (2857/2859: tiled-fallback navmesh; both teams reach the enemy spawn).
  - **HEAT + TRAP + LADDER pass 2026-09-24 (bugs 2865-2874) - awaiting user playtest:** heat costs on all 23 maps; spawns reach BOTH homes on the directed navmesh; bots climb + queue at ladders (m3l1b foot still crowds). **Bot brain A-D** (playerbot.cpp, `bot_*` cvars, BOTEV probe) in heat round 6; **breach** (grenade door/hatch, team holds or covers - `bot_breach*`) + **cover fighting** (hide/peek/lean/bound, `bot_cover*`, BOTPROBE `cov=`) DEPLOYED (2875-2882, `bot_behavior_report.py`). **Soak rounds 9-14 (2883-2901):** hunt/defend, wedge/link-jump/embedded fixes, props cut REVERSIBLY at mesh build, bad jump links dropped, learned steep/no-progress polys, ladder-queue deadlock, Push round reset respawns all. Check nav changes with `nav_sinks.py`. Open: spawns e1l1 axh (jeep box), t1l1 ax8/ax9, e3l1 ax3.
  - **OPEN e3l3 "The River Line"** - pathnode islands: the on-foot mission (SW start -> NW AB41 boarding) is one
    area; the train ride + crash (SE) are tiny isolated pockets. User asked "axis right before the crash?" - check
    whether the NAVMESH (not just pathnodes) reaches the east side on foot; if not, axis home at the AB41 boarding.
  - **OPEN systemic: Push never initialises global/exploder.scr** (script-less arena, level.cpp) - every map's
    destructibles sit intact+smashed+chunks visible/solid at once, and gen_push_gates' default `remove`s BOTH the
    intact and smashed states (bug-2839: wall-less rooms). Fixed per-map on e3l2 (blown) and m5l1a (intact); still
    the default on m5l1b, m5l2a, t1l3, t2l4, e3l3 - pick blown vs intact per map from its SP script.
  - e3l2_mp.txt wall-line clip 6163/5950/3346 - user to confirm no out-of-bounds opened.
  - **RESIDUAL B — intermittent m4l2 NAV-TRAP ledge (bug-2831)** ≈(-5685,4644,z328): ~2 in 8 boots a bot walks up
    and strands (pth=0), no mesh path down. Watershed non-determinism and elevated spawns both DISPROVEN. Cause = no
    off-mesh drop link beyond the JumpFall caps (256u/128u/600u). Fix candidate: a hand `fall` line in
    navlinks/m4l2_mp.txt (bug-2837 mechanism) rather than retuning the caps globally. One soak/map is NOISY.

- **MP fix pass (2026-09-21, bugs 2815-2820; detail in buglog). Deployed, parse/build-verified, needs a real playtest:**
  - **Bots stuck on the tank (2815)** - superseded: parked tanks are cut from the mesh at build (2893).
  - **Loadout DONE 3-5 presses (2816) and m5l1b silent ambient (2817) FIXED** - watch: does ONE press spawn you?
  - **Mount icon repositioned beside MAGS ammo (2819)** and **crosshair shadow-slide reverted (2818, see above).** Both need eyes.
- **PUSH = SINGLE FRONT push-through (2026-09-18; front mechanics in buglog bug-2711).** Ported to the SP maps
  (authored + BSP-derived via `gen_push_from_bsp.py`); side-swap flip disabled (2745, VERIFIED); m5l2b PULLED (2747).
  Being playtested map-by-map by the user (2026-09-23 batch above).

- **MP DYNAMIC WEATHER — DEFAULT OFF (host toggle, like DBNO); server half proven clean, crash-cause UNCONFIRMED
  and evidence says likely-NOT-weather (bug-2710/2735/2736/2737/2738; full findings in buglog).** `coop_mpWeather`
  (`mp_weather.scr`) → shared coop renderer. Headless boots (snow/sand/rain × push/dom/ft/tdm) are 100% server-side
  clean; the whole client render path is defensive by static trace; the one crash was at LOAD before weather renders,
  unreproduced, no dump. FIXED this pass: double-init (2735), dead-on-DM `invalid waittill spawn` (2736), NULL-listener
  loopsound spam (2737). RESIDUAL (2738): 4 non-fatal `set_respawn` errors on m3l3 scene props under weather-ON only.
  **TODO:** one LIVE client boot (`coop_mpWeather 1`, m2l1 Push, watch for the crash) before a host-default flip —
  cannot be done headless. Host-Rules CHECKBOX still to wire (bug-2708/2640).

- **SHADOW BLEED-THROUGH — config mitigation shipped, needs visual verify (bug-2721).** Object shadows render
  through ground at range; reversible one-shot `coop_shadowFixDo` (`r_shadowCastFoliage 0` + bias 4→8). Surgical
  engine fix ready if it remains (per-cascade bias + cascade-4 guard). Needs the user's eyes on a sunlit map.
  **2026-09-21 (bug-2818):** a separate attempt to raise the `shadowmask_fp.glsl` receiver bias 0.5→3.0 made
  shadows SLIDE with the camera and was REVERTED to 0.5 — screen-space receiver-plane bias is the wrong lever
  for bleed-through (a shadow-map resolution / self-shadow problem); options remain `r_sunShadows 0` or the
  per-cascade engine fix above. Deployed, awaiting the user's eyes.

- **MP vehicle system — spawn+respawn verified, INTERACTIVE loops need a playtest (2026-09-15, bug-2643/2646;
  detail in buglog).** Host toggle `coop_mpVehicles 1` (default off), 5 SP arena maps. AT pickups, mannable
  flak88/nebelwerfer, drivable jeep+tank all boot-spawn cleanly; destroy→eject→respawn + crew HUD VERIFIED.
  **Unverified in play:** board/drive/fire, exit/eject, turret manning, PvP capture (hold [USE] to flip an enemy
  vehicle). `veh_*` in `coop_mod/mp_vehicles.scr`.
- **Prop Hunt — mode shipped, human loop needs a playtest (2026-09-15, bug-2641/2659).** AXIS=props (hide as
  stock statics, [USE] cycles shape), ALLIES=hunters (frozen during `coop_mpPhHideTime`). Boot-verified:
  morph, round arm 3v3, hide phase. Unverified: hunter kills a hidden-but-solid prop; full timeout win.
  Vet added a prop-seed draft (`ph_manage` force-joins the last allies player to axis when props=0 &
  hunters≥2, native `join_team`) and a wrong-shot HP penalty (`coop_mpPhShotCost`, default 3). **Best-effort,
  needs a playtest:** the forced draft mid-warmup and the per-shot penalty edge.
- **Symmetric Demolition + Freeze Tag meltgun — need a playtest (2026-09-15, bug-2644/2645/2650/2654/2655).**
  Demolition is two-way (either team plants on the enemy's spawn-derived site; gt2 team board). Vet fixed a
  multi-planter stall (co-planting teammates flip-flopped the timer → never armed), added the `destroy` stat
  credit + `plantbomb`/`explode_tank`/`alarm_switch` audio + a `set_objective_pos` compass marker. FT meltgun
  ranged weld was DEAD (progress zeroed every tick outside 96u) — fixed (bug-2650). Plant/defuse/detonate +
  the weld still need a live playtest.
- **Spawn Protection host-rules UI toggle — deferred (2026-09-15, bug-2640).** The mechanic ships default-ON
  in MP (`coop_mpSpawnProtect`, seeded in mp.scr::main) and is console-toggleable; a board checkbox was NOT
  added because `coop_mphostrules.urc` is full (footer at y422) and a 3-column bottom row truncates the
  "Down But Not Out" label. Add a row only if the board gains vertical space. (2026-09-15 vet: the documented
  move-out early-drop is now implemented — leaving `coop_mpSpawnProtMoveDist` (256u) drops protection, bug-2658.)
- **MP MODE FULL-FUNCTIONALITY VET (2026-09-15, bug-2649–2659).** All 12 MP modes + rounds framework vetted;
  13 fixes shipped (key: round-win credit snapshotted at round-arm via `coop_mpRndTeam`/`mp_awardRoundWin`,
  not last-survivor). Verified by gates+build; **needs a playtest** — S&D detonation credit is a USE-holder
  heuristic, Prop Hunt draft, Demolition audio/marker, round-mode win credits all logic-tested only.
- **REAL UBERMOD BOMB MODES + BUILD-A-BASE MAP FIX — deployed, needs a playtest (2026-09-16, bug-2668/2669).**
  UberMod v8 has only 4 special modes: bb/cyb/snd/ft. S&D and the previously-missing **Cyber Attack** now LOAD
  the real `ubermode/cybersnd.scr` (imported + 5 custom deps under the private `ubermode/` namespace; stock
  `global/earthquake.scr`+`string_format.scr` left to vanilla) off harvested per-map bomb data
  (`cybersnd_sites.tsv` → `gen_cybersnd_maps.py` → `mp_cybersnd_stations.scr`). Freeze Tag stays ours (UberMod's
  ft is logic-only). **Build-A-Base was non-functional as shipped** (bug-2668): its UI offered `dm/mp_*` maps
  that carry no station data (data is authored for the 2001/campaign maps), and the mohdm keys lacked the
  runtime `dm/` prefix. All three now run on **18 maps** via `sv_mpForceArena` (the Base Assault/Push pattern):
  the 7 mohdm* DM maps (bsp spawns) + 11 SP campaign maps that REUSE Base Assault/Push team spawns
  (`gen_arena_spawns.py` → `mp_arena_spawns.scr`). Shared 18-map picker `hzm_arenamaps.urc` (generated), gated
  by `ui_mpIsArena`; Cyber Attack tile added to `multiplayerstart.urc`. **Verified on a dedicated boot:** all
  three engage with zero script errors, "Running <mode> game mode" / "stations placed" on mohdm1 + m1l3a; coop
  map m1l1 still loads coop with MP off and no `g_ubergametype` leak; isolation 22/22. **Needs a playtest with
  real players** (0-player boot can't verify: campaign-map spawn placement, bomb plant/defuse/round flow,
  victory). Minor: `win_snd` challenge is now orphaned (S&D uses UberMod's own scoring, not our progression).
- **MP BOT INTELLIGENCE OVERHAUL (2026-09-17, 6 phases; plan `hzm-mohaa-coop-mod/_research/mp_bot_ai_plan.md`)** -
  in active user playtest on Push; aim retuned 2026-09-23 (bug-2840). All edits in `BotController`/`BotMovement`
  (coop instantiates none) or `mp*.scr` gated on `coop_mpRun`. Still UNVERIFIED: CTF/Dem/Base Assault bots
  pursuing their objective. Unwired modes (delegate to ubermode/htr): Cyber S&D, Cyber Attack, Countdown.
- **Panzerfaust REMOVED (2026-08-18)** - **armory id 73 is a permanent hole, never renumber.**
- **Skin system: built end-to-end, awaiting menu playtest (2026-08-18).** 357 finish variants / 45 guns,
  armory finish strip, 7 finish challenges, server-side unlock gates, 25 model variants gated on each gun's
  Elite challenge; finishes visually approved. STILL OPEN: the in-hand reload magazine keeps the stock skin
  (bug-2241: `Clip` surface reskins but the reload-mag model doesn't; needs a probe).

