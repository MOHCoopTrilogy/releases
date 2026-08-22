<!-- GENERATED FILE - DO NOT EDIT.
     Produced by docs/tools/gen_public_pages.py from buglog.json, challenges.scr,
     the map scripts and the authored docs. Edits here are overwritten. -->

# Features

Every system built for the trilogy coop mod, grouped by domain. Generated from the project's own feature record, so it stays in step with what is actually in the build - including the parts that are shipped but not yet confirmed in play.

**154 systems** across **18 domains**.

| Status | Count |
|---|---:|
| shipped, not yet confirmed in play | 66 |
| shipped, confirmed working in play | 30 |
| planned | 8 |
| open | 5 |
| in the build but switched off | 5 |
| reverted | 5 |

## Core coop

| System | Status | What it does |
|---|---|---|
| **DBNO (Down-But-Not-Out)** | shipped, confirmed working in play | Downed state with bleedout timer, fade manager and |
| **Medkit** | shipped, confirmed working in play | Standing heal (full restore, movement cancel, damage interrupt, |
| **Key-item preservation through DBNO** | shipped, not yet confirmed in play | coop_key_guardian re-gives an owned |
| **Corpse persistence + despawn** | shipped, confirmed working in play | coop_corpseLife seconds then alpha fade and |
| **Exact-ammo respawn** | shipped, not yet confirmed in play | Snapshots combat ammo every 0.5 s while alive and |
| **Bindable coop command bus** | shipped, confirmed working in play | The infrastructure every coop bind rides on: a |
| **Coop Lobby (pre-mission staging)** | shipped, not yet confirmed in play | Mannequin lobby: static shared camera, |
| **engine usercmd bridge** |  | (Player::TickCoopLobbyInput reads A/D/F) so it works for remote clients |
| **Per-map respawn loadout** | open | The respawn loadout comes from a switch(level.script) in |

## AI

| System | Status | What it does |
|---|---|---|
| **Officer boss / reinforcement waves** | shipped, confirmed working in play | (2026-06-21 re-test). |
| **Officer wave scaling by player count** | shipped, not yet confirmed in play | Authored wave stats are a |
| **2-player baseline** |  | ; solo scales *down*, 3–4p scale *up* (health/accuracy/unit size). |
| **Officer German VO, alarm variety, heal-retreat** | shipped, not yet confirmed in play | Numbered alias pools |
| **Enemy count-scaling** | shipped, not yet confirmed in play | Every German entering the world rolls a |
| **AI dynamics — global enemy personality** | in the build but switched off | Root cause it addresses: |
| **AI maneuver mover** | in the build but switched off | Every 2 s, engaged flank/cover troopers do |
| **AI squad brain + last-known-position search** | in the build but switched off | SB1 greedy-clusters live |
| **none seeded** |  | (main.scr:255). |
| **Squad morale break** | in the build but switched off | A force whittled below coop_moraleFrac (0.5) of |
| **AI tactical retreat under fire** | in the build but switched off | Mid-HP band or pain-streak triggers |
| **Reactive Difficulty Director (DDA)** | shipped, not yet confirmed in play | and **ON by default**. Hidden Ease |
| **Engine AI combat tuning** | shipped, not yet confirmed in play | Retarget un-pin, suppress bypass, plant-band, |
| **ET3 engine jink** | open | (built, dormant). |
| **never firing** |  | ~65% of enemies are on THINK_COVER roles, the aggressive band pulls the rest |
| **AI grenade un-veto** | shipped, confirmed working in play | Upstream OpenMOHAA bug: GrenadeWillHurtTeamAt |
| **AI prone/crouch postures** | open | , globally disabled **on purpose**. aipronechance / |
| **server crash** |  | (repro: shoot the m1l1 barrels). |
| **Reinforcement natural behaviour** | shipped, not yet confirmed in play | Personality roll at spawn, |
| **Bullet-sponge fix (`coop_unsponge`)** | shipped, not yet confirmed in play | Root cause: nolongpain/enablepain |
| **Addon-spawner restore** | shipped, confirmed working in play | , the strongest measured win in the project. |

## Player movement & combat

| System | Status | What it does |
|---|---|---|
| **Sprint / walk / stamina** | shipped, not yet confirmed in play | (game *feel* unverified). |
| **ADS on its own button + bash restored** | shipped, not yet confirmed in play | ADS moved off secondary-fire onto |
| **ADS iron-sight port + per-gun tune table** | shipped, confirmed working in play | (user dialled 45 guns by hand). |
| **Cover system** | shipped, not yet confirmed in play | , shipped as EXPERIMENTAL with known bugs. |
| **Player emotes** | shipped, not yet confirmed in play | EMOTE_SALUTE/ATEASE/STRETCH legs states reachable |
| **Weapon weight / view-model lag** | shipped, not yet confirmed in play | Spring-eased positional yaw/pitch lag |
| **visual only** |  | (origin nudge, never aim). |

## Camera

| System | Status | What it does |
|---|---|---|
| **3P free cam** | shipped, not yet confirmed in play | Mouse orbits 360° (pitch ±85) without turning the character; |
| **Staged 3P shoulder ADS** | shipped, not yet confirmed in play | Holding ADS in 3P eases to an over-the-right- |
| **new zoom weapons MUST be added to that list.** |  |  |
| **Turret 3rd-person camera** | shipped, not yet confirmed in play | A correctly scoped turret-3P exists after an |

## Audio

| System | Status | What it does |
|---|---|---|
| **Full audio mixer** | shipped, confirmed working in play | (tuned across several user rounds). |
| **`s_sfxduck` + m3l1a Omaha ramp-drop cinematic** | shipped, confirmed working in play | A **music-exempt** effects |
| **Death voice system** | shipped, confirmed working in play | Random human death grunt on every AI and player death; |
| **persistent corpse** |  | *Anchor:* ubersound/coop_deathvox.scr; coop_mod/deathvox.scr:52. |
| **Corpse gurgle + wet blood-leak loop** | shipped, not yet confirmed in play | A quiet under-body wet trickle on a |
| **Headshot kill cue + guaranteed headshot FX** | shipped, not yet confirmed in play | (sandbox-verified 20/20 kills, |
| **Tinnitus** | shipped, not yet confirmed in play | Ring tone + s_volume duck when a player loses ≥ |
| **DBNO heartbeat + gasmask breath** | shipped, not yet confirmed in play | Per-client 2D loop via |
| **Environmental reverb, HRTF, occlusion, distance gun tails** | shipped, not yet confirmed in play |  |
| **⭐ Headline: the auto-reverb driver was ALREADY built in the fork and forgotten** |  |  |
| **do** |  | get reverb via sticky send-routing, so DBNO heartbeat / tinnitus could sound wet indoors. |
| **Fresh recorded gun audio + footsteps + impacts** | shipped, confirmed working in play | (explicit user verdicts). |
| **Warzone explosion variants + VFA wood footsteps** | reverted | Two user-rejected swaps, both |
| **MOH Frontline PS3 asset extraction** | shipped, not yet confirmed in play | Source is the PS3 HD remaster |

## Graphics & FX

| System | Status | What it does |
|---|---|---|
| **gl1 post-process suite** | shipped, confirmed working in play | Bloom and SSAO on by default with user-tuned values |
| **renderergl2 migration** | planned | / in progress in an isolated sandbox at G:\mohaa-gl2 (own |
| **healthy** |  | boots, renders, 0 crashes, 0 real GLSL failures; "breaks everything" was overstated. |
| **Directional decal shadows + auto-sun bridge** | shipped, confirmed working in play | , user-approved. |
| **Player + AI gore** | shipped, not yet confirmed in play | (all 4 tiers built + deployed, untested in-game). |
| **Blast decapitation / dismemberment** | reverted | (twice). |
| **Gore intensity** | reverted | Round 4 over-cranked everything (a uniform heavy tier soaking |
| **Wounded-AI blood trails** | shipped, not yet confirmed in play | AI below coop_bloodTrailHealthFrac 0.5 that is |
| **Suppression screen FX** | shipped, not yet confirmed in play | Desaturate + dark tunnel vignette when enemy rounds |
| **Lingering gun smoke** | shipped, not yet confirmed in play | Additive client-side wisp at i_vBarrel and at |
| **HD texture packs + DDS override pack** | shipped, not yet confirmed in play | Own ESRGAN ×4 packs fill the gaps |

## UI & HUD

| System | Status | What it does |
|---|---|---|
| **HUD fade** | shipped, confirmed working in play | (four live-report bugs fixed). |
| **exe + cgame together** |  |  |
| **Coop objectives HUD** | shipped, confirmed working in play | 8 primary slots + dedicated side-objective cvars |
| **⭐ 2026-07-12 the script-drawn panel was RETIRED** |  | the user saw both displays at once |
| **ARMORY loadout picker (69-gun URC menu)** | shipped, not yet confirmed in play | 2 primaries + 1 sidearm + 1 |
| **Medals & Badges** | shipped, not yet confirmed in play | (2026-08-07). |
| **Service Record / challenges** | shipped, not yet confirmed in play | 299 challenges in 11 categories including |
| **Named-NPC trilogy skins** | shipped, not yet confirmed in play | (2026-08-07). |
| **Pinned challenges** | shipped, not yet confirmed in play | (2026-08-04). |
| **Armory unlock-gate closes the native MP options menu** | shipped, not yet confirmed in play | (2026-08-07). |
| **Two pin surfaces** |  | , both per player: the lobby Service Record (click a row — direct, instant |
| **Coop Settings + Post-FX menus** | shipped, not yet confirmed in play | Coop world/gameplay toggles as linkcvar |
| **In-game Report a Bug → Discord webhook** | shipped, confirmed working in play | end-to-end. |
| **Display mode selector** | shipped, not yet confirmed in play | Windowed / Borderless / Exclusive, setting |
| **What's New / field-report card** | shipped, confirmed working in play | Changelog is **baked per release** into the |
| **Overhead boss/actor icon** | shipped, not yet confirmed in play | Vanilla draws the team icon only for ET_PLAYER |
| **There is NO script access to this system at all.** |  | Known follow-up: HD upscaled icon art needs a |
| **Menu art edit-kit + Start Game wall board** | shipped, not yet confirmed in play | Photoshop round-trip: |
| **Font atlas @3x pipeline** | reverted | , then rebuilt. |
| **silently inert** |  | renderergl2/tr_font.cpp R_LoadFont_sgl implements an HZM hi-DPI feature that |

## Progression

| System | Status | What it does |
|---|---|---|
| **XP / rank system Phase 1** | shipped, not yet confirmed in play | (built + deployed 2026-07-07, untested). |
| **Weapon unlock progression** | shipped, not yet confirmed in play | Three routes: a rank table R1–R21, challenge |
| **Cosmetic unlocks** | shipped, not yet confirmed in play | 28 armory skins + 34 helmets gated through the same |
| **Locked-cosmetic visibility** | reverted | (**by design change, not defect**). |
| **Deployables skill tree** | planned | → **REJECTED**. Six branches / ~36 nodes (Combat Engineer, |

## Items & deployables

| System | Status | What it does |
|---|---|---|
| **Coop reward items (binoculars airstrike, signal smoke paradrop)** | shipped, confirmed working in play | (fixes driven |
| **Signal smoke stripping German grenades** | shipped, confirmed working in play | Not a TIK problem: the smoke was |
| **Deployable ammo box** | shipped, not yet confirmed in play | (builds; gameplay test pending). |
| **MG42 / mounted turret overheat** | shipped, not yet confirmed in play | 6.0 s of continuous fire locks the gun out |
| **Deployable sandbag cover** | shipped, not yet confirmed in play | A notsolid visual bag plus 9 safesolid |
| **Build mode: 14 geometry primitives + blueprints** | shipped, not yet confirmed in play | Textured box primitives |
| **shipped** |  | templates to coop_mod/bp/ (a different prefix avoids a homepath twin, bug-960). |
| **uniform scale only** |  | (a single float), no runtime BSP brush creation. |
| **Allied squad survivability (downed-not-dead)** | shipped, not yet confirmed in play | coop_mod/allysquad.scr. |
| **DOWN** |  | instead of dying — parked at 1hp with nodamage (never 0: bug-1323, an entity at <=0 that |
| **Blast shield narrowed to opt-in** | shipped, not yet confirmed in play | (bug-1586). |
| **all** |  | world-attributed explosion damage to allied AI in coop, so mortars and artillery could not |
| **New-objective toast** | shipped, not yet confirmed in play | Brief left-hand card when an objective first goes |
| **Ambient barrage** | shipped, not yet confirmed in play | coop_ambience_barrage: shells land 400-1400 units around |
| **Crewed AA emplacements** | shipped, not yet confirmed in play | All three placeable AA guns now carry an |
| **Placeable AA emplacements** | shipped, not yet confirmed in play | Three distinct guns, and the distinction is |
| **no seat** |  | that the script aims and fires (flak88turret.tik is the only flak model carrying |
| **player mans** |  | Each mannable gun is a single spawn: its base TIKI carries |
| **Baked build-mode structures per map** | shipped, not yet confirmed in play | Build mode is a **capture** tool, |
| **prespawn** |  | , not from main — mg_nest_manned ground-traces and spawns a live actor. |

## Vehicles

| System | Status | What it does |
|---|---|---|
| **t2l2 halftrack + truck coop seating** | shipped, confirmed working in play | (finalized + committed 2026-07-01). |
| **m1l3a / m1l3b jeep passenger seating** | shipped, not yet confirmed in play | (untested multi-player). |
| **King Tiger 2nd-player MG gunner slot** | shipped, not yet confirmed in play | (prototype). |
| **Jeep .30cal manning pose** | planned | , measure-first. |
| **measure-first** |  | instrument the live legs state on a turret, then fix the |

## World & maps

| System | Status | What it does |
|---|---|---|
| **Dynamic weather v2** | shipped, not yet confirmed in play | The custom v1 renderer was **retired**; |
| **e1l2 invisible walls** | shipped, confirmed working in play | (census-verified: all user trail points 0 blocks). |
| **⭐ FINAL ARCHITECTURE:** |  | regional clip-strip **zones were RETIRED** — see [DECISIONS.md](DECISIONS.md). |
| **⭐ The SERVER loads `maps/<name>_sml.bsp`** |  | , so the suffix must be stripped. |
| **Destroyable-objective failsafe** | shipped, not yet confirmed in play | Plant-to-destroy objectives only advance via |
| **m3l1b cut FLAK 88 objective** | shipped, not yet confirmed in play | The level was originally a |
| **e1l4 alarm silencing** | shipped, not yet confirmed in play | e1l4 uses a bespoke alarm rather than |
| **Officer / paradrop bombing-run flight** | shipped, not yet confirmed in play | One shared banked diving arc used by |
| **both** |  | the officer Stuka and the player binocular strike, replacing a straight horizontal |
| **Cut-content restoration wave 1** | shipped, not yet confirmed in play | Inventory of ~2,600 unused dialogue aliases, |
| **Retail objective strand risks** | open | , no P0s. |
| **only** |  | by the sticky-plant path (a grenade kill blocks endlevel forever), and Tiger tank #1 has no |

## Weapons & cosmetics

| System | Status | What it does |
|---|---|---|
| **18 extra WW2 weapons (S93 pack)** | shipped, confirmed working in play | 18 net-new guns with zero overwrite of |
| **xw guns hip-fire** | shipped, not yet confirmed in play | Root cause: the S93 pack ships all 10 pistols with |
| **Visible holstered weapons ("weapons on back")** | shipped, confirmed working in play | (dedicated boot m1l1: |
| **Helmet unlock gate is now WEAR-time, not just pick-time** | shipped, not yet confirmed in play | (bug-1578). |
| **Live helmet switcher** | shipped, not yet confirmed in play | 12 options; hides the model's baked |
| **Helmet pop-off** | shipped, confirmed working in play | (dedicated probe). |
| **Bipod / supported aim** | planned | Verdict: **build** a weapon-stance supported aim |
| **Limb dismemberment** | planned | ⚠️ Read bug-861 and bug-892 **first** — its phase-0 precursor |

## Tooling

| System | Status | What it does |
|---|---|---|
| **Map-rotation test harness** | shipped, confirmed working in play | coop_maptest 1 = load-time smoke test across the |
| **⭐ Maps MUST be loaded the real coop way** |  | (set ui_dmmap <m> + exec start_server.cfg / |
| **⭐ Crash gotcha:** |  | G_ArchivePersistant Com_Errors on non-empty coop game.* vars **if |
| **Regression harness** | shipped, confirmed working in play | (produced bugs 1218–1220 on 2026-07-29). |
| **Autonomous combat-verification rig** | shipped, confirmed working in play | coop_botInput 1 injects the HOST |
| **Coop self-test suite** | shipped, not yet confirmed in play | , undocumented in every index. |
| **Coop test menu** | planned | , the largest designed-but-unexecuted work in the project. |
| **`md5_2_skX` model converter** | shipped, confirmed working in play | , round-trip validated. |
| **Blender sprint carry-pose edit** | planned | , paused by the user mid-edit at arm-bone selection. |
| **Installer** | planned | , **do not execute until explicitly asked**. Inno Setup 6, |
| **Coop dev tools** | shipped, confirmed working in play | coop_dev 1 enables dev features. |

## Networking

| System | Status | What it does |
|---|---|---|
| **NAT hole-punch rendezvous, Phase 1** | shipped, not yet confirmed in play | (signaling verified end-to-end locally; |
| **Dedicated server on bare DM maps** | open | game.dll crashes loading non-coop maps |

## Low-health limp (2026-08-02)

| System | Status | What it does |
|---|---|---|
| **`SHIPPED`, awaiting playtest verdict.** |  | *"when the player gets really low health they should start |

## AI voice nationality — Russian added, French silenced (2026-08-02)

| System | Status | What it does |
|---|---|---|
| **`SHIPPED`, awaiting playtest.** |  | *"we should never have any actors/reinforcements speaking the wrong |

## m2l2a Phase C - the player-initiated CONTAIN (2026-08-10) - SHIPPED, partly verified

| System | Status | What it does |
|---|---|---|
| **VERIFIED in play:** |  | the contain loop end to end; the escalation path handing over the FULL loadout; |
| **STILL UNVERIFIED:** |  | the 15s loiter -> cover-blown escalation, the stun-witness route, and the |

## Ragdoll physics (v1.4.0 opt-in, v1.4.1 ON by default) - SHIPPED, NEWEST SYSTEM

| System | Status | What it does |
|---|---|---|
| **Default flip was migration-free, and the reason is worth keeping:** |  | coop_ragdoll is |

