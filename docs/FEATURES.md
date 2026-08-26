# FEATURES — every system built, with cvars and status

Status vocabulary in [SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md#status-vocabulary).
Anchors are bug ids or `file:line`. Cvars listed are the ones you would actually touch.

> **Read this first.** Of ~75 systems here, only about 15 carry a recorded human or probe
> confirmation. **The large majority are `SHIPPED-UNVERIFIED` — built, deployed, never playtested.**
> That is the single biggest signal in this record. Some of them were almost certainly tested and
> nobody wrote it down; the record cannot tell the two apart. See
> [SOURCE_OF_TRUTH.md § Confidence](SOURCE_OF_TRUTH.md#7-confidence).

## Domain index

[Core coop](#core) · [AI](#ai) · [Player movement & combat](#movement) · [Camera](#camera) ·
[Audio](#audio) · [Graphics & FX](#graphics) · [UI & HUD](#ui) · [Progression](#progression) ·
[Items & deployables](#items) · [Vehicles](#vehicles) · [World & maps](#world) ·
[Weapons & cosmetics](#weapons) · [Tooling](#tooling) · [Networking](#networking)

---

<a name="core"></a>
## Core coop

**DBNO (Down-But-Not-Out)** — `SHIPPED-VERIFIED`. Downed state with bleedout timer, fade manager and
a movement penalty applied via `dbno_pistol.tik movementspeed 0.55` (not `setspeed`). E tap = medic
callout, E hold = give up, RMB hold = self-revive. Cinematic anim set added later
(`DBNO_COLLAPSE`→`DBNO_IDLE`↔`DBNO_CRAWL`→`DBNO_BLEEDOUT`, `SHIPPED-UNVERIFIED`), replacing a
crouch-walk overlay hack; torso is no longer forced so downed players can aim and fire.
`DBNO_MEDIC` is aliased and stated but **unwired** — reserved for teammate-revive.
Cvars `coop_dbno`, `coop_dbnoCorpseRevive` (10 s killed-while-downed window — **seeded nowhere**),
per-map override `level.coop_dbno_disabled` (jeep maps, t2l2).
*Anchors:* `coop_mod/dbno.scr`; project_build_plan "PLAYER CONFIRMED ALL WORKING".
⚠️ Known open: the crawl animation plays **opposite** to movement — W crawls backward (bug-431).

**Medkit** — `SHIPPED-VERIFIED`. Standing heal (full restore, movement cancel, damage interrupt,
cloth + exhale sounds), self-revive from DBNO, HUD icon slot 36 + count 37, health-pack refill via
delta + 5 s timer scan, enemy drop frequency `level.coop_healthDropFreq = 10` kills.
*Anchor:* `coop_mod/medkit.scr`.

**Key-item preservation through DBNO** — `SHIPPED-UNVERIFIED`. `coop_key_guardian` re-gives an owned
binocular/smoke after any revive (`dbno_enter`'s `takeall` strips it and no revive re-gave it);
`coop_key_onDown` drops heavy weapons (panzerschreck/bazooka) to the world with a `trigger_use`
re-pickup. Deferred: source-tracking so a *given* heavy is restored rather than dropped, and
instant-death paths that skip DBNO. *Anchor:* `coop_mod/keyitems.scr`.

**Corpse persistence + despawn** — `SHIPPED-VERIFIED`. `coop_corpseLife` seconds then alpha fade and
remove; **default 0 = bodies stay forever** (the user's explicit choice). Two engine limiters had to
be fixed for that default to mean anything: `MAX_BODYQUEUE` 5→128 (`fgame/actor.h:306`) and the 10 s
`EV_DeathSinkStart` gated to `GT_SINGLE_PLAYER`. *Anchor:* `coop_mod/corpse.scr`.

**Exact-ammo respawn** — `SHIPPED-UNVERIFIED`. Snapshots combat ammo every 0.5 s while alive and
upright, re-applies 0.5 s after respawn (waiting out the async loadout give). Needed new Sentient
`getammo`/`setammo` events because the stock `ammo` event only **adds**. Reward items deliberately
excluded. Cvar `coop_exactAmmo 1`. *Anchor:* `sentient_combat.cpp`; `itemhandler.scr::coop_ammoSnapshotLoop`.

**Bindable coop command bus** — `SHIPPED-VERIFIED`. The infrastructure every coop bind rides on: a
keypress appends a marker to the player name, `manageNamechange` extracts it, `playerNameCommand`
dispatches. Indices in use: 15 noclip, 16 ammo box, 23–25 emotes, 26 take cover, 35/36 helmet
next/prev, 42–46 loadout. **⭐ Cheat-flavoured actions must route through script** (`self noclip`),
not a direct keybind — the cheat gate is `Entity::CheckEventFlags`, reachable only from the
console/clientcommand path, and `sv_cheats` is latched off on a coop listen server. Known failure
mode: one token per name change, so pileups lose later tokens.
*Anchors:* `ui/BIND.SCR`; `variables.scr::getNameAppendCommands`; `player.scr::playerNameCommand`.

**Coop Lobby (pre-mission staging)** — `SHIPPED-UNVERIFIED`. Mannequin lobby: static shared camera,
4 players, 76-skin A/D cycle, F = ready → 10 s countdown → briefing → m1l1. Input arrives via an
**engine usercmd bridge** (`Player::TickCoopLobbyInput` reads A/D/F) so it works for remote clients
with no binds. Generalised so each `co_lobbyN.scr` supplies its own cam/spawns/props/next-map.
Revert point: tag `checkpoint-lobby-working-20260708` in both repos. `game.dll` deploys **manually**.
⚠️ Every lobby map needs a `spawnlocations.scr` label or dispatch errors (bug-552).
*Anchor:* `coop_mod/lobby.scr`, `lobbyui.scr`, `maps/co_lobby1-3`.

**Per-map respawn loadout** — `OPEN`. The respawn loadout comes from a `switch(level.script)` in
`loadout.scr`, **not** from the map's own item calls — a map that arms via `replace.scr::item`
registers nothing and falls to the default (colt45 + M1 Garand), which is where stray Garands come
from. A per-map `coop_playerJustRespawned` callback races `managePlayerInventory` and usually loses.
Fix pattern: a `case "maps/<map>.scr":` entry. **t1l1 and t3l\* still have this latent.**
*Anchor:* bug-133; `coop_mod/loadout.scr`.

---

<a name="ai"></a>
## AI

> ⚠️ **Read [OPEN.md § Never ran](OPEN.md#never-ran) before trusting any status in this section.**
> Several of these are wired into `main.scr` behind gates testing `== "1"` on cvars that are seeded
> in **no shipped cfg** — they have never executed in a player session.

**Officer boss / reinforcement waves** — `SHIPPED-VERIFIED` (2026-06-21 re-test). A high-HP German
officer spawns mid-map and calls waves by radio; killing the officer or destroying the radio stops
future waves. 8 wave types, bodyguards, sniper, dogs, AT team, death battalions. Confirmed live:
spawn, dogs, heal trigger, stuka. **Post-06-21 tuning batches are unverified.**
*Anchor:* `coop_mod/officer.scr` (188 KB, the largest coop script).

**Officer wave scaling by player count** — `SHIPPED-UNVERIFIED`. Authored wave stats are a
**2-player baseline**; solo scales *down*, 3–4p scale *up* (health/accuracy/unit size). Sets
`coop_waveActor` so wave troops are excluded from the generic cloner (no double-dipping). Cvars
`coop_officerScale`, `coop_officerBasePc 2`, `coop_officerHealthPct 35`, `coop_officerAccPct 15`,
`coop_officerSquadPer 1`, `coop_officerBattalionPer 3`. *Anchor:* `officer.scr ~:1324`.

**Officer German VO, alarm variety, heal-retreat** — `SHIPPED-UNVERIFIED`. Numbered alias pools
(`coop_officer_idle1-4`, `coop_radio_german_reinf1-9`) — **same-name aliascache entries are REJECTED
as duplicates by the engine, never pool by name.** Heal-retreat picks a medkit *behind* the officer
via a dot-product test; thresholds 75%/50% call in place, 30% = battalion + retreat. Poll +
re-issue `runto` replaces `waittill movedone` (pain never fires a clean movedone). Heal count is now
budgeted — an officer breaking line of sight could previously heal to full 1200 HP **unlimited**
times, a plausible contributor to old "bullet sponge" reports. Cvar `coop_officerMaxHeals 2`
(0 disables, negative restores unlimited). *Anchors:* bug-1215; `coop_mod/officer.scr`.

**Enemy count-scaling** — `SHIPPED-UNVERIFIED`. Every German entering the world rolls a
per-extra-player chance to spawn a scattered replica. Excludes officer/waves/turret gunners/dogs.
Replicas inherit model/gun/pristine accuracy/real health but **not BSP keyvalues** (so no grenades).
Cvars `coop_aiScale 1`, `coop_aiScaleChance 50`, `coop_aiScaleTest 1` (solo counts as 2 — required to
see it alone), `level.coop_aiScaleHardCap 80` live actors. ⚠️ **All three cvars are seeded nowhere.**
*Anchor:* `aihandler.scr::coop_tryDuplicateActor`.

**AI dynamics — global enemy personality** — `SHIPPED-CODE-DISABLED`. Root cause it addresses:
MOHAA's default combat think is `THINK_TURRET` (plant and fire) and `THINK_COVER` needs authored
cover PathNodes coop maps lack — enemies were stand-and-shoot turrets. Applies an aggr/cover/flank/
prone role roll to **base map** enemies. Measured: baseline none=35 → aggr=17/cover=12/flank=6/none=0.
Master cvar **`coop_aiDynamic` — seeded in no shipped cfg** (`main.scr:247`). *Anchor:* `aihandler.scr::actorHandler`.

**AI maneuver mover** — `SHIPPED-CODE-DISABLED`. Every 2 s, engaged flank/cover troopers do
`enableEnemy 0` → lateral `runto` → reengage. Bot-measured: repositioned 0.1 → 1.7 (m1l1) / 3.1
(m2l1), avgDist 43–63u → 147–240u = **17–31× more repositioning**. Gated by the same `coop_aiDynamic`
at `main.scr:250`. ⚠️ Previously recorded `SHIPPED-VERIFIED` — but it was verified **only by the bot
rig, which sets the gate cvar itself.** It has never run for a player. Also: bug-1069 found it had a
silent parse error, so every *earlier* "enemies don't move" measurement was reading a dead script.
*Anchor:* `coop_mod/aimaneuver.scr`.

**AI squad brain + last-known-position search** — `SHIPPED-CODE-DISABLED`. SB1 greedy-clusters live
Germans (~900u) and finds a shared threat; SB2 alerts un-engaged cluster members; SS1/SB4 advances a
German that lost its target to `coop_lastKnown` and sweeps. Verified *firing* on m1l1 (5–7 clusters,
33 alerts/run, 13 search moves/run). Cvars `coop_aiSquad`, `coop_aiSearch`, `coop_squadDensity` —
**none seeded** (`main.scr:255`). *Anchor:* `coop_mod/aisquad.scr`.

**Squad morale break** — `SHIPPED-CODE-DISABLED`. A force whittled below `coop_moraleFrac` (0.5) of
peak makes engaged survivors falter (~70%, forced retreat) or berserk (~30%, aggr charge); one
reaction per actor, 4/tick cap. Verified firing on m1l1 (peak 21→12). Cvars `coop_moraleEnable`,
`coop_moraleFrac` — **not seeded** (`main.scr:257`). *Anchor:* `coop_mod/morale.scr`.

**AI tactical retreat under fire** — `SHIPPED-CODE-DISABLED`. Mid-HP band or pain-streak triggers
`enableEnemy 0` → `runto` ~500u away → reengage; crash-safe upright `runto` only,
concurrency-capped. bug-1104: the engaged-check required `self.enemy`, a formal target lock scripted
damage never sets, so it never committed — fixed with a nearest-living-player flee-from fallback.
Cvar `coop_retreatEnable` — **not seeded**. *Anchor:* `wounded.scr::coop_checkTacticalRetreat`.

**Reactive Difficulty Director (DDA)** — `SHIPPED-UNVERIFIED` and **ON by default**. Hidden Ease
Index 0..1 from downs / quiet-time / team-HP / kill-rate, EWMA-smoothed with asymmetric rate limits
(ease fast 0.15, ramp slow 0.05), driving `coop_officerWaveCooldown`,
`coop_officerSquadPer`/`BattalionPer`, `coop_aiScaleChance`. Campaign-persistent via archived
`coop_ddaSkill`. ⚠️ **Records call this "PLANNED, DO NOT BUILD until the user answers 8 decisions."
The code says built, wired unconditionally at `main.scr:134`, and enabled by `autoexec.cfg:381 seta
coop_ddaEnabled 1`.** The inline comment at `main.scr:134` still reads "default OFF" and is itself
stale. It is modulating every live session's pacing with zero recorded feel verification.
*Anchor:* `coop_mod/director.scr` (10.6 KB); stamps at `dbno.scr:164`, `player.scr:1309`, `aihandler.scr:1102`.

**Engine AI combat tuning** — `SHIPPED-UNVERIFIED`. Retarget un-pin, suppress bypass, plant-band,
jink. Cvars `coop_aiRetargetMs` (5000 = vanilla), `coop_aiHideMinMs`/`MaxMs` (4000/15000),
`coop_aiSuppressChance 15`, `coop_aiRunawayRange`/`coop_aiChargeRange` (1.0 = vanilla). The
plant-band is verified *firing* at range edges by the feel rig. Crash-safe verified 100 s. **The
felt effect needs a listen-server playtest** — the bot's fixed ~350u anchor sits in the vanilla
mid-band. game.dll only. *Anchor:* `actor_turret.cpp:151`, `actor_cover.cpp:27`.

**ET3 engine jink** — `OPEN` (built, dormant). `coop_aiJinkMs` default 0 because the rig caught it
**never firing**: ~65% of enemies are on `THINK_COVER` roles, the aggressive band pulls the rest
into `RUN_AWAY`/`CHARGE`, and the un-pin already routes the dueled enemy through `STEP_SIDE`. Dead
member `m_iCoopJinkTime` remains. A re-do needs forcing it from the retarget path or gating to
aggr-role TURRET enemies. **This is the rig's headline catch** — see [TRAPS.md § T3](TRAPS.md#t3).

**AI grenade un-veto** — `SHIPPED-VERIFIED`. Upstream OpenMOHAA bug: `GrenadeWillHurtTeamAt`
compared `.length() < 65536` — any squadmate within 65,536 **units** (the whole map) vetoed the
throw, and actors auto-squad-merge at first shots → ~100% of offensive grenades and the entire
kick/return chain suppressed. Fixed to `.lengthSquared()` (256u blast radius).
*Anchor:* `fgame/actor.cpp:10361`; `actor_grenade.cpp:393/401/408/423`.

**AI prone/crouch postures** — `OPEN`, globally disabled **on purpose**. `aipronechance` /
`aicrouchchance` are engine-reserved read-only stubs, and the crouch routine
`AttackLongRangeCrouch`→`AttackCrouchDodge` spins into "Command overflow. Possible infinite loop" =
**server crash** (repro: shoot the m1l1 barrels). Retail was prone 25% / crouch 60% at range; coop
forces both to 0. Only cosmetic `anim_scripted` prone (officer waves, ~12%) is safe. **Re-enabling
reintroduces the crash.** *Anchors:* `anim/attack.scr:48-62`; `fgame/actor.cpp:8274-8350`.

**Reinforcement natural behaviour** — `SHIPPED-UNVERIFIED`. Personality roll at spawn,
`coop_spread_pos` radius **capped** (was uncapped to ~1240u = the "battalions spawned inside walls"
bug), role-based standoff + lateral fan, `type_attack "runandshoot"` for marching battalions (the
real "storm in" fix), idle German chatter + `type_idle "patrol"` + `lookaroundangle 120` for dug-in
troops, and a hurt-trooper canteen heal (+60). *Anchor:* `officer.scr`, `aihandler.scr::coop_reinf_brain`.

**Bullet-sponge fix (`coop_unsponge`)** — `SHIPPED-UNVERIFIED`. Root cause: `nolongpain`/`enablepain`
left set by retreat scripts. Fixed as **one self-healing reconciliation sweep** folded into the
existing 1.5 s `coop_reinf_brain` loop rather than N per-site patches — explicitly because some
offending sites live in retail scripts the mod does not ship. ⭐ Good architectural precedent: prefer
a reconciling sweep over patching call sites you do not own. ⚠️ Cvar **seeded nowhere**; its
on-by-default status rests on a comment at `aihandler.scr:277` ("unset counts as 1").
*Anchor:* bug-1212.

**Addon-spawner restore** — `SHIPPED-VERIFIED`, the strongest measured win in the project. `addon_*`
markers carry their model in `$ai_model`, not `.model`, so `spawner_create` recorded NIL and the
engine spawned `models/nil.tik` in a loop. Fixed with an `ai_model` fallback + NIL-skip. Measured on
a real 2-player server: spawner storm ~7,000+ → 25 total, zero maps still storming; ~550 German AI
restored trilogy-wide. *Anchor:* `global/spawner.scr:95-138`.

---

<a name="movement"></a>
## Player movement & combat

**Composure/stress scalar + perturbation** — `SHIPPED-UNVERIFIED`. `CoopWFeelStress()` 0..1 from
suppression .45, health .25, stamina .18, speed .12; x0.85 crouched, x0.60 breath-held; spikes 9/s,
bleeds 0.8/s. Reads `r_ppHealthFrac`, **not** raw `STAT_HEALTH` — sidestepping vehicles hijacking it
and DBNO's `healthonly 9999`. Part F (08-24): breathing takes **max**(health-deficit, stress) — max,
not sum, since health is already an input — ADS damping releases as you get rattled, and an
irrational third harmonic stops the hands settling twice in one spot.
`coop_wfeelStress`, `coop_stressBreathAds`, mirror `coop_wfeelStressCur`.

**Sprint-to-slide** — `SHIPPED-UNVERIFIED` (2026-08-24). Sprint + hold crouch: speed decays
quadratically to a crouch-walk over `coop_slideTime`. **Speed change ONLY** — no bbox surgery, no
forced `PMF_DUCKED`, because holding crouch IS the trigger so `PM_CheckDuck` owns the hull as for any
crouch; that is what stops it wedging anyone in geometry. Applied right after the crouch multiplier —
the penalty a slide exists to carry you through. Costs stamina + cooldown, so it cannot out-run
sprinting. `coop_slide`, `coop_slideSpeed` 1.9, `coop_slideTime` 0.75, `coop_slideCooldown` 1.2,
`coop_slideStamina` 0.55. `Player::TickSlide`.

**Quick grenade** — `SHIPPED-UNVERIFIED` (2026-08-24). `bind g "+coopnade"`: tap to throw without
hand-selecting, hold to charge (further) and cook. **A sequencer, not a mechanic** — distance
(`charge_fraction`, `weapon.cpp:2948`), the overcook warning and blowing up in your hand are all stock,
selection posts the same `EV_Sentient_UseWeaponClass "grenade"` the weapon key uses, return is
`EV_Sentient_UseLastWeapon`. A `+`/`-` console command — no usercmd button bits remain
([TRAPS T22](TRAPS.md#t22)); release only records key state, so a tap still throws. Bind is in
`coop_defaults.cfg` so a rebind survives. `coop_quickNade`, `coop_quickNadeReturn` 0.9.

**Hit flinch** — `SHIPPED-UNVERIFIED`. The view weapon jolts when you are hit, along the
real bearing (`STAT_DAMAGEDIR` is `damage_yaw` in TENTHS of a degree). Two edge detectors — health drop
AND bearing change — because either alone misses a case. Translation only (a flinch-scale rotation
pulls the gun out of the hands, bug-105). Cosmetic: never touches the aim vector. `coop_hitFlinch`.

**Directional damage ROLL restored** — `SHIPPED-UNVERIFIED` (bug-2092). `damage_angles.z`
was clamped from `.y`, discarding the computed roll, so `g_viewkick_roll` had never done anything.
Fixed; default retuned 0.15 → 0.08 since 0.15 was untested author intent.

**Sprint / walk / stamina** — `SHIPPED-UNVERIFIED` (game *feel* unverified). Shift (not aiming) =
sprint at `sv_runspeed * coop_sprintMult`; Shift (aiming) = untouched vanilla breath-hold; Alt =
walk. Adds an out-of-breath pant, a 3D gear-rattle loop, and a real `SPRINT_FORWARD` legs state.
Cvars `coop_sprint 1`, `coop_sprintMult 1.3`, `coop_sprintStamina 5` (user runs 30),
`coop_sprintRegen 0.6`, `coop_sprintBreath`/`BreathTime`, `coop_sprintGear`, `cg_sprintLower*`.
The torso weapon-hold experiment is **CLOSED — structurally impossible to layer**; the proper fix is
a Blender re-authored anim. *Anchors:* `player.cpp` `TickSprint ~11851`, `ClientMove ~4062`;
`BUTTON_COOPWALK (1<<12)`.

**ADS on its own button + bash restored** — `SHIPPED-UNVERIFIED`. ADS moved off secondary-fire onto
its own networked bit so the vanilla rifle-butt **bash** (which the AIM state had shadowed) works
again. Defaults: RMB = `+button13` ADS, V = `+attacksecondary` bash, Shift = sprint, Alt = walk.
⚠️ **HARD CONSTRAINT: `usercmd.buttons` is 16-bit and bit 13 was the LAST free bit** (12=COOPWALK,
14=BUTTON_ANY, 15=MOUSE, 7–11=weapon commands). A second custom button needs a protocol change.
*Anchor:* `BUTTON_COOPADS` bit 13; `player_conditionals.cpp CondCoopAds`.

**ADS iron-sight port + per-gun tune table** — `SHIPPED-VERIFIED` (user dialled 45 guns by hand). Two
layers on RMB: a gun-raise via the engine-recognised `charge` `viewmodelanim` token (**custom tokens
silently fall through to idle** — `Player::ViewModelAnim` accepts only a fixed set) plus a cgame
`CG_CalcFov` zoom (`cg_adsZoom 0.70`; server-side `fov`/`setfov` are dead ends). Per-gun
stand/crouch pitch/yaw/roll/shiftX/shiftY baked into `cg_modelanim.c s_adsGunTune[]`.
⚠️ **User rule: a crouch re-bake must edit ONLY the 5 crouch fields.**

**Cover system** — `SHIPPED-UNVERIFIED`, shipped as EXPERIMENTAL with known bugs. Face a wall + press
the bind → auto-turn back-to-wall; crouch low-cover; hold LMB = blindfire (anims pull their own TIKI
trigger, spread × `coop_blindfireSpread 3.0`, steered around a detected corner); RMB = peek. Auto-3P
via `PMF_COOP_COVER` (pm_flags bit 13). Final camera model: **no orbit capture while covered** —
mouse aims directly. Cvars `coop_coverWallDist`/`LowDist`/`Grace`,
`coop_blindfireSpread`/`Raise`/`Yaw`/`Out`, `coop_peekStep`/`Out`.
⚠️ The file is `coop_mod/takecover.scr` — **`cover.scr` is the sandbag deployable.**
*Anchors:* `Player::TickCoopCover`; bugs 303–329.

**Player emotes** — `SHIPPED-UNVERIFIED`. `EMOTE_SALUTE`/`ATEASE`/`STRETCH` legs states reachable
only via `forcelegsstate`, bus indices 23–25, bindable in `ui/BIND.SCR`. Zero engine changes.
⚠️ `.st` parse errors **`ERR_DROP` the server** (opposite of `.scr` silent-fail), and
`LoadStateTable` needs a CLIENT so dedicated boots never parse it — the first *listen* launch after
any `.st` edit is the real test. *Anchor:* `coop_mod/player_legs.st`.

**Weapon weight / view-model lag** — `SHIPPED-UNVERIFIED`. Spring-eased positional yaw/pitch lag
driven by the wrapped delta of `cg.refdefViewAngles`, per-class weight (pistol 0.55 → MG 1.5),
**visual only** (origin nudge, never aim). Cvars `cg_weaponLag 0.7`, `cg_weaponLagMax 3.5`,
`cg_weaponLagStiffness 7`, `cg_weaponLagADS 0.35`. Phase 2 (movement drag + rotational muzzle swing)
not done. *Anchor:* `cg_view.c CG_OffsetFirstPersonView ~771-825`.

---

<a name="camera"></a>
## Camera

**3P free cam** — `SHIPPED-UNVERIFIED`. Mouse orbits 360° (pitch ±85) without turning the character;
ADS drops capture and eases behind the shoulder. **⭐ Key discovery:** the FAKK-era client globals
`camera_offset`/`camera_active` are never written by anything, but `cgi.get_camera_offset()` returns
a live `float*` = a **zero-ABI client→cgame bridge**. v2 auto-face turns the body toward
camera-relative input. Cvars `cl_freecamAutoFace` (default flipped to 1), `cl_freecamTurnRate 480`,
`cl_freecamAimPitch`. Ships as an **exe + cgame pair**. ⚠️ Cvars must be `CVAR_ARCHIVE`-registered in
`CL_Init` to survive quit (bug-317).

**Staged 3P shoulder ADS** — `SHIPPED-UNVERIFIED`. Holding ADS in 3P eases to an over-the-right-
shoulder view; wheel-up flies into full FP irons at `cg_adsFpFlip 0.7`, wheel-down backs out. MOUSE3
swaps shoulders (`cg_adsShoulderRight` — **never `seta` it in autoexec, it is a user preference**,
bug-258). **⭐ `CG_AdsForceFirstPerson` is the SINGLE decider** used by both 3P call sites — edit the
helper, never the sites. Scoped rifles **bypass** the stage via a name-matched zoom-TIK list;
**new zoom weapons MUST be added to that list.**

**Turret 3rd-person camera** — `SHIPPED-UNVERIFIED`. A correctly scoped turret-3P exists after an
earlier blanket override caused the "camera stuck in your body" regression across every coop turret.
Gate is `cg.renderingThirdPerson && PMF_TURRET`; world-gun visibility uses a `u_view3p`
`CVAR_USERINFO` mirror → `SVF_NOTSINGLECLIENT` toggle; vanilla 1P preserved bit-for-bit.
⚠️ **HARD RULE: a 3P feature spans `cg_view.c` (camera position) AND `cg_modelanim.c` (whether to
draw your own model) — they MUST move in lockstep.** A partial revert leaves exactly the orphan that
caused this. Vehicle-turret invisible-to-1P-driver fixed separately at bug-647 (game.dll only).

---

<a name="audio"></a>
## Audio

**Full audio mixer** — `SHIPPED-VERIFIED` (tuned across several user rounds). `s_volume`,
`s_musicvolume`, new HZM engine cvar `s_sfxvolume` 0–2 (scales every effect channel **except**
dialogue and menu/local), engine-native `s_ambientvolume`, `s_dialogscale`. Requires the HZM exe.
The engine now also sanitises `s_openaldevice` once per process so every launch opens the Windows
default device. *Anchor:* `snd_dma_new.cpp S_StartSound`.

**`s_sfxduck` + m3l1a Omaha ramp-drop cinematic** — `SHIPPED-VERIFIED`. A **music-exempt** effects
duck (music channel pointers compared out) plus `AL_MAX_GAIN 8.0` headroom so music can exceed the
master clamp. **⭐ Prerequisite discovery:** server-stuffed SETs of `CVAR_ARCHIVE` cvars are dropped
by `CG_IsSetVariableAllowed` unless whitelisted — two earlier attempts silently did nothing.
Reusable helpers `coop_setClientCvar` / `coop_cvarFade` in `replace.scr`.

**Death voice system** — `SHIPPED-VERIFIED`. Random human death grunt on every AI and player death;
pool 334 → **484** clips, plus 16 muffled distant screams between `coop_deathvox_range 1500` and
`coop_deathvox_farRange 3500`, native VO muted so they don't stack. **⭐ bug-822 root cause with log
proof:** `Actor::Remove` calls `Unregister(STRING_DEATH)`, so `self delete` on a **live scenic
actor** synchronously fires the parked `waittill death` — that is why grunts played at level start.
Health canNOT distinguish removal from a kill (Remove sets health=0); the reliable signal is the
**persistent corpse**. *Anchor:* `ubersound/coop_deathvox.scr`; `coop_mod/deathvox.scr:52`.

**Corpse gurgle + wet blood-leak loop** — `SHIPPED-UNVERIFIED`. A quiet under-body wet trickle on a
bleeding corpse for the tier-2 bleed-out window, forked from `gurgle.scr::play` so it rides every
real corpse on the same post-bug-822 hook. Proximity-gated (`coop_bloodleak_range 900`),
concurrency-capped (~5). pk3-only. *Anchor:* bug-849.

**Headshot kill cue + guaranteed headshot FX** — `SHIPPED-UNVERIFIED` (sandbox-verified 20/20 kills,
play rollout pending). **⭐ 2026-07-28 the hook MOVED from `BulletAttack` to `ArmorDamage`'s
alive→dead edge:** rank-and-file AI carry the `aihandler` 5000-health buffer, so their real killing
blow is `handlePain`'s scripted 150000 overkill, which never passes through `BulletAttack` — the cue
silently skipped most kills. Now also fires `CoopHeadshotKillFx` (blood burst + wall splat traced up
to 140u behind the head). Requires `AL_MAX_GAIN 8.0` in the exe for the alias volume 2.5 to matter.
Cvars `coop_headshotFx`, `coop_headshotFxSplatDist`/`Size`. *Anchor:* bug-1142.

**Tinnitus** — `SHIPPED-UNVERIFIED`. Ring tone + `s_volume` duck when a player loses ≥
`coop_tinnitusMinDamage 60` HP in one frame. 2026-07-18 added **engine** blast proximity because a
pure-script fix is impossible for the behind-cover case (`RadiusDamage`'s sight trace means zero
damage = zero script signal): `RadiusDamage` now stamps `coop_blastPing` on nearby players. Cvars
`coop_tinnitus`, `coop_tinnitusTime`, `coop_tinnitusMuffle`, `coop_tinnitusBaseVol 0.9`,
`coop_tinnitusBlast`/`BlastRange 500`/`BlastFull 0.5`. ⚠️ bug-948: a `VARIABLE_NONE` `floatValue`
throw in this blast-ping path killed `RadiusDamage` chains and stuck the e1l2 artillery objective.

**DBNO heartbeat + gasmask breath** — `SHIPPED-UNVERIFIED`. Per-client 2D loop via
`playlocalsound <alias> 1` so **only the downed player hears it** — an earlier 3D follower-emitter
was removed because teammates could hear it. Fades with the existing bleed-out `s_volume` duck.

**Environmental reverb, HRTF, occlusion, distance gun tails** — `SHIPPED-UNVERIFIED`.
**⭐ Headline: the auto-reverb driver was ALREADY built in the fork and forgotten**
(`coop_autoReverb` default 1) — the only blocker was `s_reverb` defaulting to 0. Shipped: reverb
enabled, HRTF boot log, 3-ray occlusion low-pass (`s_occlusion`, `s_occlusionStrength`), distance gun
tails (`coop_gunTail`, `coop_gunTailDist 1400`), CAS sharpen, corpse impulse. Verify via
`OpenAL: EFX EAXREVERB initialized` in `qconsole.log`. ⚠️ Known pitfall: 2D locals and VO streams
**do** get reverb via sticky send-routing, so DBNO heartbeat / tinnitus could sound wet indoors.
*Anchor:* `cg_view.c:362 CG_UpdateEnvReverb`.

**Fresh recorded gun audio + footsteps + impacts** — `SHIPPED-VERIFIED` (explicit user verdicts). 47
gun sounds across AA/SH/BT plus 13 of 18 imported guns re-sourced; 24 footstep surfaces, 44 surface
impacts, whizbys, casings, thunder, artillery beds; snow bullet impacts made real (stock
`snd_bh_snow` pointed at DIRT files). Distance model switched `INVERSE` →
`LINEAR_DISTANCE_CLAMPED` at context init, restoring Miles-era map-wide gunfire falloff.
⚠️ **Never name the commercial source library publicly — say "fresh recorded gun audio."**

**Warzone explosion variants + VFA wood footsteps** — `REVERTED`. Two user-rejected swaps, both
backed out: the bombing-run explosion pool variants were "too cinematic/sub-heavy for close blasts,"
and the VFA wood-plank footstep slices "sounded bad in-game" so stock wood was restored. Artillery
beds from the same library were **kept** (separate judgement). Close-explosion upgrades remain an
open wishlist item needing a brighter/crunchier library.

**MOH Frontline PS3 asset extraction** — `SHIPPED-UNVERIFIED`. Source is the PS3 HD remaster
decrypted in RPCS3, not a PS2 ISO. **⭐ Recipe:** `main.musx` = multiple EA SCHl songs concatenated →
split by chunk-walking → rename to `.asf` (vgmstream keys on extension) → `vgmstream-cli`. **ffmpeg's
`adpcm_ea_r1` cannot decode these.** SSH texture format cracked (48-byte header, ARGB32, PS3 Morton
swizzle — use OR folding, not XOR). 339 cues / 103 min + 175 ambience beds; stingers and war beds
shipped, ear verdict pending. Still unmined: 495 `.abkx` SFX/VO banks.

---

<a name="graphics"></a>
## Graphics & FX

**gl1 post-process suite** — `SHIPPED-VERIFIED`. Bloom and SSAO on by default with user-tuned values
baked (intensity 1.3, threshold 0.6); DoF, tonemap/grade and FXAA built and opt-in. **⭐ Root cause of
two failed attempts:** the pass used raw `qgl*` calls that desynced the engine's `glState` **cache**
— the fix was driving everything through `GL_State`/`GL_Bind`, **not** `glPushAttrib` (unlinkable in
this DLOPEN renderer). ⚠️ **The 3D→2D hook MUST live in `Set2DWindow` (`tr_draw.c`), not
`RB_SetGL2D`** — cgame enters 2D via the exported `re.Set2DWindow` directly. Any future effect added
to `RB_PostFxApply` is therefore automatically HUD-safe. *Anchor:* `renderergl1/tr_postprocess_gl1.c`.

**renderergl2 migration** — `PLANNED` / in progress in an isolated sandbox at `G:\mohaa-gl2` (own
binaries, junctioned game data, separate homepath, forced `cl_renderer opengl2`). Empirically gl2 is
**healthy** — boots, renders, 0 crashes, 0 real GLSL failures; "breaks everything" was overstated.
Ported so far: bloom, HZM grade, character shadows, MSAA, dynamic-light shadows. **Not ported:**
SSAO, DoF, god rays, FXAA, sharpen, heat haze, rain. See [OPEN.md § gl2](OPEN.md#gl2).
⚠️ `cl_renderer` defaults to `opengl1` (`cl_main.cpp:3231`) — **but a v1.1.51-era
`renderer_opengl2.dll` IS in the shipped manifest**, so a player who switches gets a build predating
every 2026-07-28 gl2 fix.

**Directional decal shadows + auto-sun bridge** — `SHIPPED-VERIFIED`, user-approved. One elongated
azimuth-rotated shadow decal per entity, with the renderer publishing each map's **real** sun
direction (`r_coopSunAz`/`El`/`Valid` from `tr.sunDirection`) so shadows follow the map automatically;
falls back to manual angles on sun-less/indoor maps. Cvars `cg_shadows 2` (required),
`coop_shadowDir`, `coop_shadowAuto`, `coop_shadowAz`/`El`/`Len`.
⚠️ **"Do NOT re-implement"** — this was nearly rebuilt from scratch once. Phase B/C real
shadow-mapping is **not started**.

**Player + AI gore** — `SHIPPED-UNVERIFIED` (all 4 tiers built + deployed, untested in-game).
T1 skin-bit blood tiers (178 composited textures, 51 override TIKs) driven by **accumulated damage,
not health fraction** — rank-and-file HP is faked at 5000. T2 drip + chained growing blood pool. T3
bone-attached wound props via `CM_GetHitLocationInfo`, cap 4. T4 renderer UV wounds.
⚠️ **Decals on skeletal models are IMPOSSIBLE** (`R_MarkFragments` walks world nodes only). Blood
colour authority is `#150200`. Ships **exe + cgame + renderer + game.dll together** (refexport/
refimport pairing). *Anchor:* `renderergl1/tr_gore.c` (836 lines, **untracked in git**).

**Blast decapitation / dismemberment** — `REVERTED` (twice). v1 shipped, "the AI went all glitchy,"
pulled at user request (bug-861). v2 re-implemented **safely** by copying the engine's own dead-body
gib discipline — dead-gated to the `ArmorDamage health<0.1` branch, per-frame budget, short lifetime,
tracked-only, precached (bug-866). Then **reverted from SOURCE again** during the `MAX_MODELS`
three-binary rebuild, so a protocol rebuild could not silently reintroduce it (bug-892); inert `.tik`
assets kept. **Verified this pass: zero `CoopGoreTryDecapitate` / `HeadGibObject` symbols exist in
`openmohaa-hzm/code/`.** ⭐ **The reason for the FIRST revert no longer holds** — the AI glitching was
later attributed to the entity-pool stomp (bugs 914–927), which is fixed. bug-866's safe pattern is
the template for a re-add.

**Gore intensity** — `REVERTED`. Round 4 over-cranked everything (a uniform heavy tier soaking
~60–75% of the cloth, 2–4 drench blobs, 14–20 patches, spray/smear cast-off, a measured-coverage
top-up loop). User verdict: *"dial the blood back… put it to what it originally was, now it's way too
much."* Reverted to the moderate earlier coverage and the spray/smear primitives and coverage loop
removed entirely. ⭐ Lesson: **generated-asset intensity needs a user checkpoint per round, not per
feature.**

**Wounded-AI blood trails** — `SHIPPED-UNVERIFIED`. AI below `coop_bloodTrailHealthFrac 0.5` that is
moving drips ground decals. Throttled by time (0.45 s) **and** distance (56u) — deliberately **no
velocity gate**, because AI move by animation root motion so velocity reads ~0. **⭐ Key engine fact:**
a Decal is a 1-frame server edict (`ET_DECAL` + `PostEvent(EV_Remove, FRAMETIME)`); the client
renders a persistent mark from its auto-recycled pool, so only spawn **rate** needs managing.
Requires `com_blood 1`. game.dll only.

**Suppression screen FX** — `SHIPPED-UNVERIFIED`. Desaturate + dark tunnel vignette when enemy rounds
crack past. **⭐ Key reuse:** the engine's own bullet ZING system already computes each bullet's
closest approach and excludes the first/last 128u of flight — which excludes your own outgoing shots
for free. Cvars `r_ppSuppression 1`, `r_ppSuppressAmount 1.0`, `coop_suppressFade 0.9`. Ships
renderer + cgame.

**Lingering gun smoke** — `SHIPPED-UNVERIFIED`. Additive client-side wisp at `i_vBarrel` and at
bullet impacts, on top of the faint vanilla puff already inline in 34 weapon TIKs. **The LOOK is baked
in the tik** (repack to change size/life); only spawn frequency is live: `coop_smokeWhip 1`,
`coop_smokeWhipMuzzle 0.35`, `coop_smokeWhipImpact 0.35`.

**HD texture packs + DDS override pack** — `SHIPPED-UNVERIFIED`. Own ESRGAN ×4 packs fill the gaps
community packs left (169 char skins, 1133 world textures), plus `zzzzzzz_dds_override.pk3` (872 DXT
`.dds`, 485 MB). **⭐ Root cause that made 881 upscales dead:** `R_LoadImage` rewrites the extension
to `.dds` and tries `LoadDDS` **first** whenever texture compression is on — see
[TRAPS.md § T6](TRAPS.md#t6). Also: `r_uselod 0` (`CVAR_TEMP`, must be set every launch) is the real
max-geometry switch, **not** `r_lodscale`.

---

<a name="ui"></a>
## UI & HUD

**HUD fade** — `SHIPPED-VERIFIED` (four live-report bugs fixed). Health/ammo/weapons/items/hudList +
team logo + huddraw fade after `coop_hudFadeTime` (5) quiet seconds, snapping back on
fire/ADS/health/ammo/weapon/objective/suppression events. **COMPASS is exempt by explicit user
choice**; below 25% health never fades; `PMF_COOP_COVER` keeps it up. ⚠️ **Traps:**
`Menu::GetContainerWidget` returns only item #1 (a Menu is a **flat sibling list**); never fade via
`m_alpha` (urc `fadein` widgets re-pin it every frame) — use the post-Motion `SetHudFadeMul`. Needs
**exe + cgame together**.

**Coop objectives HUD** — `SHIPPED-VERIFIED`. 8 primary slots + dedicated side-objective cvars
`coop_so1`/`so2` (moved off slots 7/8 after a hard collision with e3l2/m4l2 primaries).
**⭐ 2026-07-12 the script-drawn panel was RETIRED** — the user saw both displays at once
("obnoxious"); `coop_objPanel 0` is now the autoexec default and wrapping is done **server-side** into
`coop_oN` + `coop_oNb`. A stale-objective wedge (a dead sender thread leaving
`flag[coopObjectivesSending]` latched forever) was fixed with a self-healing timestamp + NIL guard +
3-pass reconcile — **untested live**. O-key also unfades the whole HUD.

**ARMORY loadout picker (69-gun URC menu)** — `SHIPPED-UNVERIFIED`. 2 primaries + 1 sidearm + 1
grenade from 6 class tabs with live 3D previews and 5 stat bars; picks persist in archived client
cvars and apply at every spawn via itemhandler tier 2. **⭐ bug-587 needed an ENGINE fix** — stacked
`enabledcvar`-gated Buttons were unclickable because `FindResponder` hit-tests in reverse file order
checking only `m_visible`; **the armory REQUIRES that exe.** Three distinct root causes have been
found for near-identical "loadout not applied" reports: wire quote-truncation (bug-758),
thread→waitthread ordering (bug-1204), and a **backslash in a script path** that threw a Script Error
every single time the menu opened and went unnoticed (bug-1205, now fixed at
`loadoutpick.scr:436-440`). ⭐ The one failure mode that reproduces: an empty unlock record
(`coop_mod/save/unlocks_<hash>.dat`) denies every pick and silently falls back to the map default kit
— **diagnostic question for any future report: did an "Armory: X is LOCKED" line flash at spawn?**

**Medals & Badges** — `SHIPPED-UNVERIFIED` (2026-08-07). New Service Record tab, 12 campaign-wide
meta-achievements (one per category + a "complete everything" capstone) purely DERIVED from the
challenge system's own `coop_chalD_<cid>` flags — no new stat tracking, no risk of drifting from
what challenges.scr already knows. `coop_mod/medals.scr::medal_checkAll` runs after every challenge
completion (`chal_grant`) and on load (`chal_ensure`); persistence and toast notification both reuse
challenges.scr's own mechanisms verbatim (`coop_medals_<id>` cvar + file, `chal_notify`). 3×4 icon
grid, each medal a procedurally-drawn ribbon+medallion (PIL, no external assets) with a dark
lock-scrim overlay (`coop_uiML<i>`) until earned. ⚠️ Two deliberate scope cuts, flagged to the user
rather than silently shipped: placeholder art, not the real WW2 medal photography originally
envisioned (needs a verified-public-domain sourcing pass); name+description are always visible
rather than hover-only (same tradeoff as the challenge rows below). *Anchor:* `coop_mod/medals.scr`;
`docs/tools/gen_service_record.py`'s `medals_page_bg`/`draw_medal_icon`.

**Service Record / challenges** — `SHIPPED-UNVERIFIED`. 299 challenges in 11 categories including
90 per-weapon (45 families × 2 tiers sharing one `wpn_<id>` stat). Two surfaces: an in-game live panel
hard-capped at 18 rows, and a paged disconnected menu. **Tab strip reorganized 2026-08-07 (v1.2.2):**
23 category tabs collapsed to **9**, with the 5 weapon categories sharing one WEAPONS tab and a
wraparound pager (`Page x/y` + both arrows always emitted at fixed x, so every page is laid out
identically). `catspec` carries a 5th "tab group" field; `catGroups`/`groupPageIdxs` are built in
catspec order. Last-known progress bridges via archived
`coop_uiB<i>`/`coop_uiN<i>` — ⚠️ **never seed those in autoexec (wipes last-known progress).**
⚠️ bug-461: tabs must flip `enabledcvar` cvars, **not** `popmenu;pushmenu` (`MenuManager m_lock` drops
the push). Reward ("Unlocks: X") is a HOVER reveal (2026-08-07, bug-1532) — not baked into the row at
all, after three earlier same-night attempts to share the row with the description all fell short.
Hovering the row (the same `pinbtn<gi>` Button that already covers it for click-to-pin, since it's
already the frontmost widget receiving mouse events there) swaps in a small pre-baked PNG via
`hovershader` (`textures/mohmenu/coop_sr_reward/r<gi>.tga`, `gen_service_record.py::bake_reward_hover`).
*Anchor:* `coop_mod/challenges.scr`; `ui/coop_sr.urc`; `docs/tools/gen_service_record.py`.

⚠️ **The row checkbox is `pinbox<gi>` + `pinmk<gi>` — an always-drawn `emptybox.tga` and a
`filledbox.tga` marker gated on `coop_uiP<gi>`. Do not "improve" this pair.** Six attempts at adding a
green completion tick (a `coop_uiD` marker, then a single `coop_uiC` shader-path box carrying all three
states) each replaced this working widget and each shipped worse: ticks on every row, then boxes that
did not appear until CLEAR PINS was pressed and no longer repainted on click. All six were reverted
(bug-1544, bug-1546). The root cause was never the widget — `CL_SyncSR_f` (`coop_srsync`) does not
execute from the disconnected menu, so every fix placed inside it was inert; see
[TRAPS.md T3](TRAPS.md#t3). Anything that must run on that menu belongs in `CL_Init`, which is proven
to run, or in `exec` + `seta` builtins (which is why CLEAR PINS works). **A completion tick is still
wanted — but it must be built alongside the working box and seen to render before the box is touched.**

**Named-NPC trilogy skins** — `SHIPPED-UNVERIFIED` (2026-08-07). 11 campaign characters (Ramsey,
McMartin, Johnson, Cappy, Hildebrandt, Wilson, Captain Ike, Claus, Burton, Gobbs, Whittaker) ported
from their retail AI-actor `.tik` into flattened `models/player/*.tik` armory skins, each gated behind
a real survival/completion condition read from the owning map's own script state (not invented) — see
`bug-1521`. A skin must be in all three of `helmet.scr`'s `coop_armorySkins[]`/`coop_cosmeticGatedTok[]`
and `lobby.scr`'s `coop_lobbySkins[]`, or the unlock has no effect. Two characters (Richards, McDevitt)
share Ramsey's exact retail model and were left on their existing generic reward rather than duplicated.
⚠️ A separate pre-existing audit (`task_569adfb0`, not yet run) found ~48 *older* challenge rewards
pointing at `models/player/*.tik` paths that don't exist on disk — unrelated to this batch, unfixed.
*Anchor:* `coop_mod/challenges.scr` (`cc_win_war`, `cc_static_line`, `cc_t1l3_*`, `cc_t2l3_ike`,
`cc_t2l4_captain`, `cc_e1l3_*`, `cc_e3l1_whittaker`); `docs/tools/gen_service_record.py`'s
`REWARD_NAMES` for the Service Record's curated display names.

**Pinned challenges** — `SHIPPED-UNVERIFIED` (2026-08-04). Up to **five** challenges per player,
shown in-mission under the Secondary Objectives with live `x/y` progress and a checkbox that ticks on
completion. The left-edge **quarter-progress popup** (mini HD bar + title + N/T, 25/50/75% milestones,
3.5s fade) is gated to the player's pinned set only (`chal_pin_isPinned`, 2026-08-07 — was every
in-progress counter challenge, which let unrelated weapon-kill counters compete for the same slot).
The checkbox itself is now clickable too (2026-08-07, second Button in the same gutter, lower
ordernumber than the marker so it always wins the click), and a standalone `coop_pinCount` Label
("N/5 Pinned", `docs/tools/gen_service_record.py`) sits in the screen margin outside the panel, kept
in sync by both the connected path (`chal_pin_push`) and the disconnected one (`CL_PinToggle_f`,
`code/client/cl_main.cpp` — required an `openmohaa.exe` rebuild, cl_main.cpp isn't in cgame.dll).
A completed challenge can't be pinned (bug-1537) — three independent layers (`chal_pin_toggle`,
`CL_PinToggle_f`, and `chal_pin_byIndex`'s import-time force-unpin) each refuse it on their own, plus
`chal_grant` auto-unpins on completion — and shows a green checkmark in place of the pin checkbox
(`coop_uiD<gi>`, archived so it survives to the disconnected menu).

**Armory unlock-gate closes the native MP options menu** — `SHIPPED-UNVERIFIED` (2026-08-07). Retail
`ui/multiplayeroptions.urc`'s "Allies Player Model" button wrote straight to `dm_playermodel` via the
native `playermodel`/`ui_applyplayermodel` commands (`cl_ui.cpp:3512-3550`), with zero awareness of
the Armory's unlock system — `player.scr::manageAliveSpawning` already heals a locked worn skin back
on its own, so this was never a hard exploit, but it let the menu "grant" any of ~180 skins that then
silently reverted. Mod now overrides that one `.urc`; every widget is unchanged except that button,
which runs `exec ui/loadout/open.cfg` (opens the Armory) instead of cycling the model in place. Axis
model / rate / name fields untouched. *Anchor:* `ui/multiplayeroptions.urc`. **Pins are per player throughout** — held in `self.flags["coop_pin1..5"]`/`coop_pinN`,
saved to that player's own `coop_pins_<id>.dat` under the challenge identity, and pushed with a
per-player `stufftext`; nothing is a `level.` var, so two players in one session keep entirely
separate lists. Pin by **clicking a challenge row** in the Service Record (same hit box as the
existing hover tooltip); pinned rows are marked `*` and tinted gold, and a sixth pin is refused with
a prompt rather than silently evicting one. Storage is **cids, not catalogue indices** — the index is
file order, so inserting one `chal_def` would re-point every saved pin (bug-1362); `chal_def` now
maintains `level.coop_chal_idx[cid]` for the reverse lookup. Console fallback
`set coop_chal_pin <cid>` resolves to the **host only**, never a broadcast.
*Anchor:* `chal_pin_*` in `coop_mod/challenges.scr`; click path `coop_mod/lobbyui.scr:151`;
widgets `ui/coop_objectives.urc` (`coop_cp1..5`), seeded in `ui/coop_objectives/obj_setup.cfg`.
**Two pin surfaces**, both per player: the lobby Service Record (click a row — direct, instant
feedback), and the disconnected Service Record menu, where all 281 rows are invisible full-row
Buttons emitting `append name ,cp<catalogue index>` on the name bus (token 47) into
`chal_pin_byIndex`. The menu is client-side and cannot know cids, so it sends the baked row index and
the server resolves it. There is **no in-mission pin surface** — see `docs/OPEN.md`.
*Anchor:* generator `docs/tools/gen_service_record.py` (never hand-edit `ui/coop_sr.urc`).

**Coop Settings + Post-FX menus** — `SHIPPED-UNVERIFIED`. Coop world/gameplay toggles as `linkcvar`
checkboxes plus a POST-FX EFFECTS button. Entry = the yellow documents folder on the Options
workbench. ⚠️ **Both hotspot rects are eyeballed estimates over background art** — nudge if clicks
miss. Main-menu desk map: radio=options, doors=multiplayer, projector=credits, folder=briefing,
typewriter=records.

**In-game Report a Bug → Discord webhook** — `SHIPPED-VERIFIED` end-to-end. Main-menu button →
`ui/coop_report.urc` Field → engine cmd `coop_sendreport` writes the payload to a file and spawns a
no-window PowerShell that POSTs it. **This build has NO libcurl at all**, so the original `cl_curl.c`
version was an "Unknown command." ⚠️ **SECRET: the webhook URL lives ONLY as a loose
`maintt/coop_reportwebhook.cfg`, never in the repo or a pk3.** ⚠️ bug-519: an **unregistered font in
a `.urc` crashes the game at UI init** — only `verdana-12` and `facfont-20` are safe.

**Display mode selector** — `SHIPPED-UNVERIFIED`. Windowed / Borderless / Exclusive, setting
`r_fullscreen` + new `r_desktopfullscreen` + `r_noborder`, with hidden `linkcvar` watchers so
`Menu::CheckRestart` fires `vid_restart` on the latched change. Restyled once after the user said the
first version "looks really bad."

**What's New / field-report card** — `SHIPPED-VERIFIED`. Changelog is **baked per release** into the
urc (must be updated at every publish); `autoexec` execs `whatsnew_pending.cfg`, the updater arms it
on update and blanks it when up to date. Manual test: `pushmenu coop_whatsnew`.

**Overhead boss/actor icon** — `SHIPPED-UNVERIFIED`. Vanilla draws the team icon only for `ET_PLAYER`
and only same-team, so the officer never qualified — but **`EF_AXIS` is already set on every German
actor's entity state every frame**, so zero fgame changes were needed (a ~40-line cgame edit).
**There is NO script access to this system at all.** Known follow-up: HD upscaled icon art needs a
scale divisor.

**Menu art edit-kit + Start Game wall board** — `SHIPPED-UNVERIFIED`. Photoshop round-trip:
`menu_export.py` composes a 4× canvas + LAYOUT.json, `menu_stitch.py` slices back to strict type-2
bottom-up TGAs. **⭐ The board hover widget is a 1:1 TEXEL WINDOW, not a stretch** — "there was never a
second camera." Terminal method is erase-first then place content on a VP-consistent quad; **adjust
corners only, never re-measure.** (17-round saga.)

**Font atlas @3x pipeline** — `REVERTED`, then rebuilt. A font swap replaced `gfx/fonts/*.tga` and was
**silently inert**: `renderergl2/tr_font.cpp R_LoadFont_sgl` implements an HZM hi-DPI feature that
builds `<name>@3x` and, when `fonts/<name>@3x.RitualFont` exists, loads **that** and resolves the sheet
as `gfx/fonts/<name>@3x.tga`. The shipped @3x atlases were then found to be **ESRGAN upscales of
low-res bitmaps** — upscaling a bitmap font invents detail and produces uneven stroke weights — and
were regenerated by rendering a real vector font (Bahnschrift) into the existing cell rects.
*Anchors:* bug-1182, bug-1185; cf. bug-157.

---

<a name="progression"></a>
## Progression

**XP / rank system Phase 1** — `SHIPPED-UNVERIFIED` (built + deployed 2026-07-07, untested).
~470-line script-only system: kill/headshot/melee/long-range XP (base kill retuned 10 → 2), assists
(≥25% dmg / 10 s ledger), objective/revive/mission awards, support awards, 13 US ranks Pvt→Col
0–46k XP with 13 generated metallic emblem TGAs. Persistence via `fs_write_content` + `cl_guid`
identity (requires `seta cl_guidServerUniq 0` and the matching exe). HUD v3 = an 8-layer brass XP bar
on huddraw slots 62–69. ⚠️ **Deviation bug-298: the `player userinfo` script command does NOT exist** —
identity comes from an engine-pushed `self.coop_guid`. ⭐ Called threads **inherit `self`** —
`missioncomplete`'s `self` is the exit trigger. *Anchor:* `coop_mod/xp.scr` (68 KB).

**Weapon unlock progression** — `SHIPPED-UNVERIFIED`. Three routes: a rank table R1–R21, challenge
chains (100 kills base→variant, 175 tier-2, 50 pistol), and tree-gated reserves
(MG42/.30cal/bazooka/panzerschreck/PIAT left empty for the user's own tree). Free starters
Garand/Thompson/Colt/M2 frag. `coop_lockLoadout` armed (`server.scr` default 1). Locked armory tiles
show a padlock + hover requirement line.

**Cosmetic unlocks** — `SHIPPED-UNVERIFIED`. 28 armory skins + 34 helmets gated through the same
`coop_chal_unlocks` haystack (42 challenge + 15 rank unlocks, thematically matched). The 48
lobby-only extra skins stay FREE — only shared premium skins lock. Gates all three cycle paths.

**Locked-cosmetic visibility** — `REVERTED` (**by design change, not defect**). Server-pushed per-page
redirect chains **skipped** locked skins/helmets in the armory cycle rather than previewing-then-
refusing (56+68 cvars, 112/136 init.cfg lines). Reversed pre-release at the user's request: cycle ALL
entries again, marking locked ones with a lock icon and unlock-requirement text. All 260 redirect
lines removed with an assertion that zero stale refs remained. **Cost: two full generator rewrites.**
⭐ When classifying REVERTED, separate "it broke" from "the user changed their mind."

**Deployables skill tree** — `PLANNED` → **REJECTED**. Six branches / ~36 nodes (Combat Engineer,
Quartermaster, Field Medic, Forward Observer, Squad Leader, Saboteur; 1 RP per 100 XP). User verdict
2026-07-13: *"Not a big fan… do not build mine"* — they are building their own model. The one durable
finding: the engine already ships `CarryableTurret`/`PortableTurret`
(`portableturret.cpp:65/481`), so a deployable .30cal is **wiring, not new engine work**.

---

<a name="items"></a>
## Items & deployables

**Coop reward items (binoculars airstrike, signal smoke paradrop)** — `SHIPPED-VERIFIED` (fixes driven
by live coop bugs). Per-owner HUD fix (`ihuddraw_*` each target ONE client, so slots 50–53 were
wrongly drawing to everyone; non-owners are now actively cleared), drop-on-death re-pickup carrying
remaining strikes, a red under-glow beacon on the binoc pickup, radio chatter routed to all players.
**⭐ MP AUDIO RULE: for a sound EVERY player must hear regardless of position, use
`loopsound <alias> <vol> levelwide`** — normal minDist emitters are PVS-culled per client.

**Signal smoke stripping German grenades** — `SHIPPED-VERIFIED`. Not a TIK problem: the smoke was
spawned as a **world `Weapon` entity**, so walking over it hit `PickupWeapon`'s MP grenade-class
branch, which forces grenade reselection and **drops** the player's other grenade-class weapon. Fixed
purely in script by spawning a `script_model` + `trigger_multiple` and giving via `item` (the
giveItem path, same as binoculars), which never enters that branch. The earlier
`removeAdditionalStartAmmo` theory was a **red herring**. *Anchor:* `weapon.cpp:2954`.

**Deployable ammo box** — `SHIPPED-UNVERIFIED` (builds; gameplay test pending). One `50cal_crate` per
player per **match** (tracked on the level by entnum so respawns don't reset it), hold USE to
resupply, `coop_ammobox_refills 2` uses per player per box, amount tunable live as a **percent** via
`coop_ammobox_amount`. HUD slots 45–47. ⚠️ **Icon gotchas cost 3 tries:** TGA must be type 2
uncompressed bottom-left (ffmpeg emits type-10 RLE top-down); `drawbox` over a transparent base
yields alpha=0 everywhere; **HUD images are cached at renderer registration so a changed TGA needs a
FULL GAME RESTART.**

**MG42 / mounted turret overheat** — `SHIPPED-UNVERIFIED`. 6.0 s of continuous fire locks the gun out
for a 10 s cooldown with a steam sound and centerprint; heat bleeds off between bursts. **Both
literals are hardcoded, not cvars.** AI-manned turrets got the same cycle plus damage scaled by
`coop_mg42AiDamage 40` (% of TIK damage). `coop_mg42AiAccuracyScale` widens AI aim offset for small
squads (1p ×2.2, 2p ×1.6, 3+ vanilla). *Anchor:* `fgame/weapturret.cpp TurretGun::P_ThinkActive`.

**Deployable sandbag cover** — `SHIPPED-UNVERIFIED`. A notsolid visual bag plus 9 `safesolid`
`script_object` collision boxes; box height raised 48 → 64u because the visible model is 56u tall so
shots sailed over a standing player. Bullets do stop at the boxes (`CONTENTS_SOLID` is in
`MASK_SHOT`). Gated off per-map by `level.coop_noDeployables`.
⚠️ The file is `coop_mod/cover.scr` — **`takecover.scr` is the player cover system.**

**Build mode: 14 geometry primitives + blueprints** — `SHIPPED-UNVERIFIED`. Textured box primitives
(stock `cube_CampFire.skd` + a per-variant shader) to fake the ~1,653 baked `func_crate` BSP brushes
that cannot be spawned as models. Blueprint format `bpv1`; user saves go to homepath `save/`,
**shipped** templates to `coop_mod/bp/` (a different prefix avoids a homepath twin, bug-960).
⚠️ **ENGINE LIMITS: no runtime shader swap** (script `surface` only toggles skin1/skin2/nodraw),
**uniform scale only** (a single float), no runtime BSP brush creation.
**Allied squad survivability (downed-not-dead)** — `SHIPPED-UNVERIFIED`. `coop_mod/allysquad.scr`.
Several retail missions fail when their allied NPC squad is wiped (t2l1's `check_squad_death`), a rule
balanced for **one** player while this mod duplicates enemy spawns by player count — the same three
~100hp NPCs face 2-4x the opposition they were authored against. Two paired changes: health scales on
the same axis enemy counts do (`coop_allyHealthMult`, per extra player), and at zero an ally goes
**DOWN** instead of dying — parked at 1hp with `nodamage` (never 0: bug-1323, an entity at <=0 that
never ran its death is unkillable), `disable_ai`, and playing the **player's own** DBNO animation
(`coop_dbno_collapse` -> `coop_dbno_idle`, both in `models/player/base/anims_shared.txt`, the shared
set, so AI actors can play them). Findable three ways: the spinning medkit + red glow lifted verbatim
from `dbno.scr::dbno_marker_manager`, the cgame overhead star (`rendereffects "+coopboss"`), and an
announcement. Revive is **pure proximity** and costs nothing — no medkit is consumed. Generous
`coop_allyBleedOut` 120s; knobs `coop_allyDownAt` / `coop_allyReviveDist` / `coop_allyReviveFrac`.
A down ally is still `isAlive`, so the retail wipe check does not fire while anyone is recoverable —
which is what made it safe to take the blast shield off.

**Blast shield narrowed to opt-in** — `SHIPPED-UNVERIFIED` (bug-1586). `sentient.cpp` used to drop
**all** world-attributed explosion damage to allied AI in coop, so mortars and artillery could not
wound, gib or scratch them — the damage never arrived and no gore path ran. Now a per-actor flag
(`blastshield 1`, `Sentient::EventCoopBlastShield`); t1l3's captain and private carry it, since that
is the case it was written for (script `radiusdamage` attributes the bombing run to `world`, and one
600-damage bomb one-shot a ~100hp escort NPC). **game.dll only.**

**New-objective toast** — `SHIPPED-UNVERIFIED`. Brief left-hand card when an objective first goes
ACTIVE, once per objective per player (the push is re-run by the reassert loop, the respawn watcher
and every late join). HUD slots **135-149**, the block `_research/hud_slot_map.md` reserves for mid
overlays: nothing else can be on screen in it (bug-553 was the debrief card and XP popup fighting over
62-69) and >=100 is **fade-exempt**, so it still shows if the HUD has faded after five quiet seconds —
exactly when a new objective tends to land. `coop_objToast` / `coop_objToastTime`.

**Ambient barrage** — `SHIPPED-UNVERIFIED`. `coop_ambience_barrage`: shells land 400-1400 units around
a random living player, whistle-in then a ground-traced burst, and **no `radiusdamage` at all** (user
call) so it can never cause an unavoidable death. Off until `coop_ambBarrage 1` or `level.coop_barrage`.
Distinct from the `coop_ambArtillery` sweetener, which is distant audio at 2000-4000 units with no impact.

**Crewed AA emplacements** — `SHIPPED-UNVERIFIED`. All three placeable AA guns now carry an
animated gunner, and the two mannable ones **yield to a player**: the moment someone mounts, the
cannon takes an owner, the script stops firing and the crewman is removed; both return on dismount.
The crew is deliberately **theatre** — there is no mounted-gun think for a flak (only
`machinegunner` mounts a `TurretGun`, and the crewed flak in the Breakthrough maps is scenery whose
actors carry `type_attack "turret"`, the ordinary hold-your-post think). Retail solves it the same
way: e2l1's `FlakGunSetup` `disable_ai`s the crew, poses them, and lets the script aim and fire.
Two mechanisms make this work at runtime: `QueryTurretSlotEntity 0` returns the cannon the base
TIKI's `spawnturret` created (a runtime cannon has no BSP targetname — retail uses the identical
idiom at `aaguns.scr::FlakGunSetup`), and the poses `flak88_driver` / `aagun_driver` live in
`models/player/base/anims_shared.txt`, which **every** human model shares, so no per-model animation
check is needed. Crew placement is cvar-tuned rather than guessed — `coop_aaCrewFwd` /
`coop_aaCrewSide` / `coop_aaCrewUp`, seeded nowhere, starting guesses 20 / 0 / 8, all scaling with
build scale. ⚠️ `startyaw` is re-stated after `.angles` because `m_fStartYaw` is captured when the
turret is *placed*. Each emplacement now costs gun + cannon + crew against the entity pool.

**Placeable AA emplacements** — `SHIPPED-UNVERIFIED`. Three distinct guns, and the distinction is
the whole point (bug-1581): `flak_emplacement` is the **AA-campaign 88**, a `VehicleTurretGun` with
**no seat** that the script aims and fires (`flak88turret.tik` is the only flak model carrying
`fire_scripted`); `aagun_emplacement` and `flak88_manned` are the **Breakthrough** guns from e2l1's
glider drop — the Flakvierling quad-20mm (`P_aagun_base.tik`, `$aagun1/3/5`) and the Flak 88
(`P_flak88.tik`, `$aagun2/4/6`) — both `FixedTurret : VehicleTank : Vehicle`, which is the class a
**player mans**. Each mannable gun is a single spawn: its base TIKI carries
`spawnturret 0 "statweapons/P_*_cannon.tik"` in its own init block, so the cannon attaches and its
slot opens from the TIKI at spawn — the reason this is safe at runtime, where a later `$ent model`
swap would never re-run `OpenSlotsByModel`. No usability wiring is needed (`m_bPlayerUsable` defaults
true, `vehicleturret.cpp:228`); e2l1's extra script exists to *restrict* them. Models live in
`mainta/pak1.pk3`, which mounts under `com_target_game 2`, so they work on AA and SH maps too.
⚠️ All three must stay on `coop_*` targetnames — `global/turret.scr` runs on every map and scans
literal `$flak88` / `$mg42` / `$nebel` arrays.

**Baked build-mode structures per map** — `SHIPPED-UNVERIFIED`. Build mode is a **capture** tool,
not a persistence layer (bug-1554): it appends paste-ready blocks to `coop_mod/save/build_<map>.dat`
and nothing reads that file at runtime, so a placement is gone on the next map load until it is baked
into the map script. Baked so far: `m3l1b` 34 props + 1 manned MG42 nest (`coop_rear_props`),
`m3l2` **2 manned MG42 nests** (`coop_build_structs`, 2026-08-08). Bake from a label threaded at
**prespawn**, not from `main` — `mg_nest_manned` ground-traces and spawns a live actor. Rename the
`.dat` after baking or the next session's capture appends behind the old content and re-bakes it.

⚠️ `blueprint.scr:5-7` still carries an `INERT UNTIL WIRED: nothing threads into this file yet`
header — **it has 22 call sites** (18 in `buildmode.scr`, 4 in `bunker.scr`). The header is stale and
actively misleading. Related open defect: bug-1001, blueprints render as featureless squares.

---

<a name="vehicles"></a>
## Vehicles

**t2l2 halftrack + truck coop seating** — `SHIPPED-VERIFIED` (finalized + committed 2026-07-01).
**⭐ SUPERSEDED HARD RULE: riders are now SOLID and take real damage — do NOT re-apply the old
notsolid workaround.** Enabled by engine fixes: glued riders immune to CRUSH/TELEFRAG/FALLING/VEHICLE,
and **⭐ the smooth-ride root cause** — the rider's VIEW was being interpolated independently of the
vehicle, fixed by `cg_predict.c::CG_LockRiderOriginToVehicle` pegging a `PMF_NO_MOVE` rider to the
nearest `ET_VEHICLE`'s own `lerpOrigin`. Seated crouch driven straight from the crouch axis. 16 seats,
ride reinforcements, German loadout; DBNO/deployables/medkit off.

**m1l3a / m1l3b jeep passenger seating** — `SHIPPED-UNVERIFIED` (untested multi-player). The
multi-passenger system was fully written then **disabled with early `end`s (dead code)** so only ONE
player rode. Re-enabled: invisible seat `script_model`s attached to the jeep's `passenger0` tag at
z=+55, glue on spawn, seat freed on death/respawn. Respawn-into-jeep works via a `script_origin`
attached to the jeep feeding all 8 coop spawn slots every second. Officer and DBNO both disabled on
the pure rail-ride maps.

**King Tiger 2nd-player MG gunner slot** — `SHIPPED-UNVERIFIED` (prototype). A second player mans
turret slot 1 while another drives, fixing "foot players get left behind by an escaping tank." Copied
from the confirmed-working jeep recipe (`attachturretslot` + `perferredweapon` + `detachturretslot`
to eject). Deliberately **exposed** — the gunner is not nodamage/notsolid/hidden. Safely no-ops where
slot 1 is absent. Needs in-game tuning on m5l2a/m5l2b. ⚠️ Runtime `$ent model` never re-runs
`OpenSlotsByModel`; explicit-pos `DetachTurretSlot` is **crew-eject only**.

**Jeep .30cal manning pose** — `PLANNED`, measure-first. World gun visible and correct, but the player
stands in a plain arms-hang idle with the weapon holstered on his back. Explicitly queued as
**measure-first**: instrument the live legs state on a turret, then fix the
`VEHICLE_TURRET_START`/`USING` entry edges in `player_Legs.st`, or force the state from
`EnterTurret`/`TurretMove`. Recorded instruction: *"Do NOT guess condition semantics — measure
first."* *Anchor:* bug-309.

---

<a name="world"></a>
## World & maps

**Dynamic weather v2** — `SHIPPED-UNVERIFIED`. The custom v1 renderer was **retired**;
`coop_mod/weather.scr` is now a thin controller that resolves a theme and execs `global/weather.scr`
for **both** rain and snow, with a random-walk driver over `level.weatherpattern` so storms build and
fade unpredictably. ⚠️ **Never-fired bug:** `coop_weather_init` is threaded from inside
`main.scr::main` but maps set `level.coop_weatherTheme` on the **next** line, so the theme always read
NIL — fixed by waiting for prespawn first. Cvars `coop_dynWeather`, `coop_weatherForce`,
`coop_weatherPin`. Verify via `^~^~^ WEATHER coop=snow`.

**e1l2 invisible walls** — `SHIPPED-VERIFIED` (census-verified: all user trail points 0 blocks). Three
species, all fixed: (1) 33 `trigger_landmine` entities were `damageable=1` and `SetDamageable(true)`
calls `setContentsSolid` — every armed mine was an invisible solid box; changed to
`CONTENTS_WEAPONCLIP` (still in `MASK_SHOT` so shooting mines works, movement passes through, stepping
on one still detonates via trigger touch). (2) The 15cm artillery TIK ships
`setsize (-80 -80 0)(80 80 80)` and stays SOLID; tightened to (-48 -48 0)(48 48 80), cutting 56
blocked grid segments to 20. (3) A 225-segment retail SP-boundary playerclip web on the plateau.
**⭐ FINAL ARCHITECTURE:** regional clip-strip **zones were RETIRED** — see [DECISIONS.md](DECISIONS.md).
**⭐ The SERVER loads `maps/<name>_sml.bsp`**, so the suffix must be stripped. New wall reports are now
pak-only fixes. *Anchors:* `trigger.cpp:3240`, `cm_load.c:856`.

**Destroyable-objective failsafe** — `SHIPPED-UNVERIFIED`. Plant-to-destroy objectives only advance via
the `ThrobbingBox` demolition setthread, so a bombing run or tank shell killing the target **stalled
the mission**. The fix polls the target and fires the box's `BlowUp` (which runs the full canonical
wreck/FX/damage/objective sequence). Wired on t2l1 nebels + tank1, t1l2 flaks, t1l3 flakcannon, e2l1
aaguns, e3l2 cannons. Round 3 added nodamage-until-unlocked protection for objective-critical **tools**
so splash can't soft-lock a map. *Anchor:* `main.scr::coop_watchDestroyable`.

**m3l1b cut FLAK 88 objective** — `SHIPPED-UNVERIFIED`. The level was originally a
destroy-the-emplacements mission whose completion logic still exists in the base script but references
an entity set absent from the shipped BSP; the devs cut it with a block literally labelled
"TEMP TEMP TEMP PREMATURE POOPHEAD ENDING." Re-wired the two 88mm emplacements that **did** ship into
a real objective that gates the exit. v2 wants gun crews, back-field defenders and a plant animation.

**e1l4 alarm silencing** — `SHIPPED-UNVERIFIED`. e1l4 uses a bespoke alarm rather than
`global/alarm_system.scr` and made the switch `nottriggerable` the instant the alarm sounded, so
players could never shut off the sirens. Coop leaves the switch live and routes it through a debounced
toggle with a 3 s arm cooldown so a double-firing switch can't sound-then-silence.

**Officer / paradrop bombing-run flight** — `SHIPPED-UNVERIFIED`. One shared banked diving arc used by
**both** the officer Stuka and the player binocular strike, replacing a straight horizontal
origin-lerp. Attitude from `vector_toangles(velocity)` each tick plus roll banking into the turn; the
envelope **auto-scales from `$world.farplane`** so the plane stays inside each map's fog. Runtime
`SplinePath`/`flypath` (what makes m3l2's bomber look good) was deliberately **not** used to avoid a
static-plane risk, and remains the recommended upgrade. ⚠️ Two watch items: the `$world.farplane`
getter is unverified in-repo, and the bank direction sign may need flipping.

**Cut-content restoration wave 1** — `SHIPPED-UNVERIFIED`. Inventory of ~2,600 unused dialogue aliases,
317 never-aliased MP voice-command wavs, 7 unused music tracks, a cut player-mannable FLAK-88, a cut BT
rowboat assault, cut map t3l3, hidden MP player models. **⭐ The MP hitmarker is DISABLED at retail** —
the engine already plays alias `dm_hit_notify` on damage but it is aliased to `null.wav`, so one alias
line restores it. Wave 1 restored ~15 voiced lines across 5 maps. **⭐ Engine alias PREFIX rule:**
calling `dfr_call_ap4357` auto-randomizes takes 04/05/06.

**Retail objective strand risks** — `OPEN`, no P0s. Two P1s, both on SH **t2l1** — the only genuinely
strandable retail map: the nebelwerfers are immune only to bullet/bash and their objective flag is set
**only** by the sticky-plant path (a grenade kill blocks endlevel forever), and Tiger tank #1 has no
death-thread equivalent to tank2's. The coop throbbox `BlowUp` failsafe covers t2l1 — **verify it
covers grenade-kills before re-fixing.** Fixed in the same pass: `maps/m2l2b.scr:87` called a label
that never existed (retail typo), killing the init thread on the majority path. ⚠️ **Audit gap:** SH
`gags/` sources are absent from the original-scripts tree, so t1l1/t1l3/t2l4 endings are unaudited.

**Unimplemented `addon_*` entity classes** — `OPEN`. ~1,000 entities across ~140 distinct `addon_*`
classes on all 9 SH + 11 BT maps (AA has zero — expansion-era tech); OpenMOHAA implements **none**.
Three fallback tiers: TIKI-declared classname spawns a working class but loses addon extras
(soundset prefix, crew keys, facing); model-only = a visible statue with zero behaviour; no model =
invisible nothing. Highest risk: `turretweapon_german_mg42` ×49 across 13 maps, and large `ai_*`
placements (e2l3 ×50 Italians) that could mean empty battles. **These are candidates prioritised by
playtest reports, not 1,000 confirmed bugs.** e3l3 is the fix template.

---

<a name="weapons"></a>
## Weapons & cosmetics

**18 extra WW2 weapons (S93 pack)** — `SHIPPED-VERIFIED`. 18 net-new guns with zero overwrite of
vanilla/coop assets, each given a unique name/weapontype/weapongroup. Ships as a **standalone
`zzzzz_xw_weapons.pk3` that `build.ps1` does not manage** — source lives at
`C:\mohaa-coop-dev\_xw_weapons\` (untracked, outside both git repos) with its own hand-rolled
`_pre_<feature>_bak` chain, and `publish_release.ps1` stages it from the **deployed** maintt copy, so
source and shipped artefact can silently diverge. **⭐ bug-494 (found in play — only 39 of 71 guns were
reachable): the TIK `rank <order> <power>` FIRST number is a GLOBAL weapon-select slot shared across
weapontypes**, and every import had copied its parent's order. **Any future import must get a unique
order.** ⚠️ Non-Boom sounds are ripped from other games and must be swapped before any public release.

**xw guns hip-fire** — `SHIPPED-UNVERIFIED`. Root cause: the S93 pack ships all 10 pistols with
`semiauto` commented out, so the engine treats them as full-auto and the hip route lands in
`CHECK_PRIMARY_ATTACK_FULLAUTO`, which only routed smg/mg classes — pistol/rifle-class autos bounce to
STAND forever. (ADS states don't test `semiauto`, hence "fires only in ADS.") Fixed at both ends (11
TIKs patched + rifle/pistol fallback rows in the statemap), which also fixed the StG44-scoped and the
vanilla FG42. ⚠️ **`MEMORY.md`'s index still flags this as OPEN while its own topic file records it
SOLVED the same day** — see [90-folklore.md](90-folklore.md). Diagnostic rig `coop_fireDebug 1` kept.

**Visible holstered weapons ("weapons on back")** — `SHIPPED-VERIFIED` (dedicated boot m1l1:
`WEAPDBG ATTACH holster=1 tag=Bip01 Spine2`). **EA shipped the complete visible-holster system and
disabled it with comment slashes** — 79 retail TIKs have commented `holstertag`/`holsteroffset` lines.
Uncommented 27 mod TIKs + class templates for 10 more + all 32 xw pack TIKs. Engine fix:
`holsterOffset` was stored but never passed to `attach()`. **Bonus: idle map AI now visibly carry slung
rifles.** Known minor: a weapon given but never drawn stays hidden until first cycled.

**Helmet unlock gate is now WEAR-time, not just pick-time** — `SHIPPED-UNVERIFIED` (bug-1578).
`armory_helmet_set`'s gate could only *decline* a locked pick; nothing re-checked what was already
equipped, and `helmet_apply` — the single choke point every spawn, revive and skin change passes
through — trusted `flags["coop_helmetIdx"]` with no range check and no unlock check. It now
re-validates and falls back to a **deterministic** index 1 (Standard Issue), never nearest-unlocked,
which would drift a player's look on every map load. The skin half of this was already fixed on the
other side (bug-803, `player.scr::manageAliveSpawning`). No live leak path was demonstrated — every
writer of the index is itself gated — so this closes the class; the **range** check does fix a real
crash-shaped case (a stale index above `coop_helmetCount` reads NIL and the tail `attachmodel` errors
on it). New `helmet_lockNotice` says "locked" once per **distinct** item: `loadoutpick.scr` resends
the archived `,hn` token on every join (:291) and every armory close (:483), so under the intended
SHOW-ALL-WITH-LOCK design a preview parked on a locked helmet used to repeat the same line forever.

**Live helmet switcher** — `SHIPPED-UNVERIFIED`. 12 options; hides the model's baked
`surface us_helmet` and attachmodels a skeleton-less static helmet prop to `Bip01 Head` — both
replicate through entityState so teammates see it. Re-applied every spawn (`InitModel` wipes surfaces
and attachments). **⭐ The definitive placement came from copying the gear helmet that already works:**
`us_helmet.skd`'s 147 verts are all single-weighted to bone 8, so its weight offsets **are** exact
head-local coordinates. ⚠️ bug-533: `surface us_helmet -nodraw` **unquoted** parse-killed `helmet.scr`
and cascaded to kill the **entire name-command bus** (helmet + sandbag + medkit + emotes all silently
dead).

**Helmet pop-off** — `SHIPPED-VERIFIED` (dedicated probe). **Not cut content** — 131 human TIKs carry
`sethelmet`, and pops were firing all along but invisible (5 s despawn, silent, never settled, half the
lateral toss lost). Fixed: `EV_Stop` wired to `HelmetTouch` (`G_Impact` skips `SOLID_NOT` so `EV_Touch`
never arrives), lifetime cvar `g_helmetlife 30`, landing clank, and a vanilla `VectorScale`→`VectorMA`
bug that discarded the first lateral velocity component. Reusable probe: `coop_helmtest 1`.
⚠️ **NOT-POSSIBLE correction: helmet pop can never strip a PLAYER's helmet** — zero of the mod's 28
`models/player/*.tik` carry `sethelmet`, so `WearingHelmet()` is always false. The earlier "verified
working in coop" note was about **actors**.

**Bipod / supported aim** — `PLANNED`. Verdict: **build** a weapon-stance supported aim
(`Player::TickCoopBipod` cloning the `TickCoopCover` recipe + a ledge-top down-trace, yaw ±40 pitch
±15 clamp, spread hook in `Weapon::Shoot`), ~250 LOC game.dll + pk3. **Reject** the turret-swap
approach. Needs **no** new usercmd bit (RMB is bit 13 already), no new PMF (budget FULL), no new stat
(`STAT_MGHEAT` took the last slot). **⭐ Free future unlock:** retail `CarryableTurret`/`PortableTurret`
ships complete in maintt pak1, and the SH `mg42tripod_*` 3P mounted-pose anim grid is already there.

**Limb dismemberment** — `PLANNED`. ⚠️ Read bug-861 and bug-892 **first** — its phase-0 precursor
shipped and was pulled the same week, and the source-level revert was deliberate and thorough.

---

<a name="tooling"></a>
## Tooling

**Map-rotation test harness** — `SHIPPED-VERIFIED`. `coop_maptest 1` = load-time smoke test, `2` =
teleporting patrol through AI areas; `coop_maptest_dwell` tunes dwell. Banners prefixed `^~^~^`.
Launch method and the `g_scriptcheck` crash gotcha: see CLAUDE.md § Running and testing.

**Regression harness** — `SHIPPED-VERIFIED` (produced bugs 1218–1220 on 2026-07-29). Lives at
`C:\mohaa-coop-dev\_research\regression\` (`regress.ps1`, `regress.py`, `hzmreg/`, `roster.json`,
`baselines/`, `runs/`). **Currently the project's only working automated verification.**
⚠️ Sits under `_research`, which `build.ps1` treats as disposable — **promote it out**
([TRAPS T12](TRAPS.md#t12)).

**Autonomous combat-verification rig** — `SHIPPED-VERIFIED`. `coop_botInput 1` injects the HOST
client's usercmd — aims at the nearest visible German and **fires real bullets**, which is what makes
AI genuinely engage (a script `damage` event does **not** — damage attribution is not target
acquisition). Pair with `coop_aiCombat 1/2` and `coop_aiBehav 1/2`. Reliable metric is **cumulative
displacement**, not instantaneous counts. **⭐ Key lesson: an autonomous feel-rig's real value is
catching a feature that SILENTLY DOESN'T FIRE** — which "looks-right, go-check" never would.
⚠️ The documented revert path (`scratchpad/coopaudit/REVERT_botinput.md`) is **gone**, and the engine
change is still live in `player.cpp`.

**Coop self-test suite** — `SHIPPED-UNVERIFIED`, undocumented in every index. **11 files**:
`coop_selftest.scr` (base: `weaptest_run`, `dbnotest_run`, `dbnoteam_run`, `xptest_run`,
`scaletest_run`, `wintest_run`) plus 10 per-subsystem —
`{dbno, engine, keyitems, objectives, officer, scaling, triggers, vehicles, weapons, xp}`. 23
references in `main.scr` across the gated block at `:171-238`. (There is no `_loadout`, `_ai` or
`_medkit` module — earlier records claiming 12/13/14 files are wrong.)

**Coop test menu** — `PLANNED`, the largest designed-but-unexecuted work in the project. 94 tests
across 10 subsystems, each specifying catches / drive / verify / evidence(`file:line`) / risk, most
needing a new cvar-gated probe emitting a `^~^~^ MARKER`. Several named probes **do** exist, so parts
may have been built. **No run log or results file was found.** ⭐ One finding embedded in it worth
permanent watch: `replace.scr:465-470` `player_origin` is an **intentional infinite `while(1)` crash
trap** that hangs the server rather than erroring — its println reads *"outdated func used, crashed
game on purpose."*

**`md5_2_skX` model converter** — `SHIPPED-VERIFIED`, round-trip validated. Unblocks importing
CC0/Blender models with no 3ds Max. The 2012 tool needed a self-contained `skx_format.h` redeclaring
su44's struct names with byte-identical layouts. ⚠️ **RAW OUTPUT IS ENGINE-LETHAL (bug-1002):** it
writes `ofsCollapse`/`ofsCollapseIndex` = 0 and the engine reads both unconditionally →
`TIKI_SortLOD` stack OOB → access violation in `Entity::setModel`. **Every converted skd must go
through `skd_add_collapse.py` + `skx_validate.py`.** It also hardcodes a −90 X roll on the root bone.

**Blender sprint carry-pose edit** — `PLANNED`, paused by the user mid-edit at arm-bone selection.
Pipeline is 100% working (kit + 4 addon patches, including bug-295's multi-root fix — **MOHAA rigs
have 3 roots**, `Bip01` plus both feet as IK goals, and the addon's single-root assumption dropped the
feet from the anim tree). Goal: a weapon-holding sprint anim to replace the one-handed dash.

**Installer** — `PLANNED`, **do not execute until explicitly asked**. Inno Setup 6,
`PrivilegesRequired=lowest` so it installs to `%LOCALAPPDATA%\MOH Coop Trilogy` with no UAC, GOG
registry detection via Pascal scripting, desktop shortcut, built-in uninstaller. Git-tracked in the
allowlist repo (so it has real history, unlike the mod).

**Coop dev tools** — `SHIPPED-VERIFIED`. `coop_dev 1` enables dev features. Cheat-flavoured actions
route through script events (`self noclip` / `self nodamage`) to bypass the latched `sv_cheats` gate.
A give-next-weapon cycle per category covers the imported guns.

---

<a name="networking"></a>
## Networking

**NAT hole-punch rendezvous, Phase 1** — `SHIPPED-UNVERIFIED` (signaling verified end-to-end locally;
no real-world friend test). **⭐ Our stack was already punch-friendly:** one shared UDP socket, the
server answers `getchallenge` from any address, and the **client re-latches the server address to
whoever answers** (`cl_main.cpp:2347`), so NAT port remaps are handled for free. Daemon + engine hooks
built; a fake joiner received a real punch burst from game port 12203. NAT exe deployed but **dormant
by default**. Blocked on the user having no VM. Honest odds 75–85%; symmetric NAT and CGNAT still need
port forwarding. ⚠️ MOHAA OOB packets are `4×FF` + a **direction byte** — omit it and the server
silently runs nothing (bug-1143). ⚠️ The engine-side commit records an unresolved **dedicated-server
crash under investigation** with no follow-up found.

**Dedicated server on bare DM maps** — `OPEN`. `game.dll` crashes loading non-coop maps
(`obj`/`obj_team1`) under a dedicated server; the baseline reproduces with zero rendezvous cvars, so
it is **not** NAT-related. Coop maps load fine — likely a coop hook assuming coop init ran. Fix:
"none yet." ⭐ Also recorded: `omohaaded.exe` has headless env quirks (stalls **with** `fs_homepath`,
dies **without** it); the working dedicated recipe is the **CLIENT exe with `+set dedicated 1`** from
the GOG dir. *Anchor:* bug-330.

---

## Low-health limp (2026-08-02)

**`SHIPPED`, awaiting playtest verdict.** *"when the player gets really low health they should start
playing the same limp animation the actors do, and you should see the limp in first person (camera
should imitate that as you move)."*

Below `coop_limpStart` (0.30) of `max_health`, on the ground, not dead/downed/vehicle/turret:

- **Server is the single authority.** `Player::TickLimp` sets `m_bCoopLimping` and stuffs
  `coop_limpView` to the owning client **on change only**. The client never re-derives a threshold —
  so `coop_limp 0` on a server genuinely disables it everywhere, not just the body.
- **Health signal is `health / max_health`.** Deliberately NOT a peak-health tracker: `healthonly`
  clamps to `max_health` (`entity.cpp`), so DBNO's `9999` can never inflate a peak — see bug-1290 for
  the audit that wrongly claimed otherwise.
- **3P body**: four `LIMP_FORWARD/BACKWARD/LEFT/RIGHT` states built from the real `WALK_*` legs
  blocks. Row order carries the design — **every armed class** gets `rifle_run_injured` (retail's only
  armed injured cycle), unarmed gets the full directional `walk_injured_*` set. The unarmed clip must
  never drive an armed player: a STAND torso takes its animation *from* the legs
  (`player_Torso.st:19-21`), so it would strip weapon posture.
- **Directional aliases fixed**: `walk_injured_back/_left/_right` all pointed at the **forward** clip;
  the real directional `.skc` files ship in retail `Pak0` and were simply never referenced.
- **FP camera** modulates the *existing* bob rather than adding an oscillator. The vertical term's
  `fabs()` gives it one lobe per footstep, so `sign(sin(phase-0.94))` **is** foot parity — one foot's
  dip deepens, the other's shallows, continuously. Plus amplitude-scaled ADS-damped roll and uneven
  step timing. Placed before the `MASK_PLAYERSOLID` traces so a deep dip cannot punch the eye through
  a floor.
- **Speed**: `coop_limpSpeedMult` 0.60 applied *after* the whole multiplier chain as a scale (mid-chain
  it would be overwritten by Alt-walk then re-scaled by `sv_dmspeedmult`). Never freezes — floored at
  `coop_limpMinFrac` 0.35 of run speed but **capped at the pre-limp speed**, so injured is never faster
  than healthy in the same stance. The 3P shoulder-aim floor is *scaled* by the limp mult, not skipped.
- **Dev**: `coop_limptest <frac>` sets health without damage. ⚠️ A large single-frame drop still trips
  DBNO, which derives damage from health deltas — step down with ~2s pauses.

*Anchors:* bug-1291, bug-1292. Cvars: `coop_limp`, `coop_limpStart`, `coop_limpSpeedMult`,
`coop_limpMinFrac`, `cg_limpDepth`, `cg_limpRoll`, `cg_limpRollAds`, `cg_limpDrag`, `cg_limpCamSpeed`.

## AI voice nationality — Russian added, French silenced (2026-08-02)

**`SHIPPED`, awaiting playtest.** *"we should never have any actors/reinforcements speaking the wrong
language."* Audited **all 1481 shipped human tiks** rather than the 111 the scripts name. Result:
American/British/German/Italian detection was already complete — every `allied_uk_*` caught by `_uk_`,
every `sc_al_brit_*` by `brit`. Only two real misroutes existed:

- **5 `soviet_*` models returned `"de"`** — Russian soldiers speaking **German**. MOHAA's team enum has
  only american/german, so Soviets fall through as german (the same reason the health exemption needed
  a model test). Added `"ru"` inside the german branch, plus a 22-alias `coop_av_ru_*` pool across 9
  situations drawn from the retail per-nationality **MP voice reel** (Russian is first-class there: 44
  files in `mainta`, 61 in `maintt`). `mandown`/`reload` stay **silent** — no honest line exists, and
  silence is this codebase's rule. `"ru"` also added to the allied CONTACT gate, which was `us||uk`.
- **French resistance** (`allied_resistance`, `allied_misc_manon`) drew **American** lines; now return
  `""` and stay silent, since no French reel ships.

*Anchor:* bug-1288.

## m1l1 loading screen — corkboard case file - 2026-08-07
SHIPPED-VERIFIED (user confirmed in-game). Replaces the stock two-tile aerial-recon TGA pair with a single BSP-rendered
composite: the aerial recon photo (officer position marked), a clean retypeset of the vanilla m1l1
OSS briefing letter (Col. Stanley Hargrove, found orphaned at `textures/mohmenu/levelbriefing/`,
never wired to any live menu), and 3 photos pulled from the stock `briefing1` slideshow (Torch map,
Grillo's dossier photo, terrain, pill), pinned together with a red string on a corkboard. Single
2048x2048 POT texture via the new `coop_load_m1l1` shader (`scripts/coop_loadscreens.shader`) — see
[DECISIONS.md § Loading screens](DECISIONS.md#loading-screens--single-pot-texture-new-work-only)
for why this replaces the old tile convention. Render pipeline: `_research/maprender/` (BSP extract
+ procedural recon-photo render), generator scripts for the letter/composite are scratch-only so
far, not yet copied into the repo.

## Coverage sweep (covtrace + covwalk) - 2026-08-05
Answer to "our trilogy sweeps missed a lot": absence doesn't log, so the sweep is now
coverage-driven. Engine (game.dll, coop_covtrace 1): one `^~^~^ COV` line per committed trigger
fire (volume centroid + targetname), per sound alias PLAY and per alias MISS, and per maps/*
label thread start. Static side: `_research/cov_manifests.json` (1,773 triggers across 30 BSPs)
+ generated `maps/cov/<map>_walk.scr` lists. `coop_maptest 3` = Phase 3: the rotation tick
teleports every connected player round-robin through every trigger volume, then advances.
`coop_covwalk_force 1` additionally direct-fires named triggers (chaotic - throwaway runs only).
Report: `python _research/cov_report.py` -> `_research/cov_report.md` (never-fired triggers per
map, runtime-confirmed dead aliases, labels run). Static layer 1 results:
`scratchpad dead_aliases_confirmed.json` - 170 dead alias refs on 43 maps, families
(bombtick/plantbomb/pickup_papers/door_locked) look retail-dead = restorable content.

## m2l2a Phase C - the player-initiated CONTAIN (2026-08-10) - SHIPPED, partly verified

`coop_mod/bust.scr` + `itemhandler.scr`. Gated on `coop_stealthStart`, which **ships ON from
the next release** (bug-1698) - it was 0 in 1.2.6, so no player has reached Phase C yet.
⚠ That gate is wider than its name: it also makes m2l2a open UNARMED, papers-only. The contain
cannot be decoupled from it - a player holding a Weapon reads as undisguised, so guards never
challenge them and the contain can never fire. Full design and the
nine defects the playtest found: `docs/proposals/m2l2a_coop_stealth_master_plan_v2.md`
("PHASE C AS PLAYED"), bugs 1682-1691.

An officer stopping you is no longer a fail state - it is a fight you can win quietly, and the
player moves FIRST. Approach an officer and you are told *"Avoid the Officer. Contain him only when
alone."*; inside 112u, *"Press [USE] to Contain The Situation"*. USE plays the retail `punch1/2/3`
pistol foley on him and lands a small non-lethal hit, which is the ONLY lever script has on an
actor's think (`thinkstate` is getter-only; `Actor::EventPain` sets `THINKSTATE_PAIN` at
`THINKLEVEL_PAIN`). He drops to his knees for 4.5s while the silenced pistol is force-drawn, given
ammo, and HELD against the loadout arriving behind it.

- **Killed unseen** -> papers back at once + *"Leave the Area Immediately."*; at +10s clean,
  *"Situation Contained. Proceed with Caution."* and the squad is told who did it.
- **Seen** (the stun OR the body) -> *"Situation Escalated - Weapons Free"* and the map's REAL alarm
  via `trigger $waittrigger_alarm_master`.
- **Not killed in time** -> he recovers and runs for the alarm, as normal.
- **Afterwards** the corpse stays findable for the rest of the mission. Anyone who can see it reacts;
  the first actor safe to interrupt kneels over it. Loiter within 320u on the same floor for 15s and
  cover is blown - the timer resets when you leave.

**VERIFIED in play:** the contain loop end to end; the escalation path handing over the FULL loadout;
the bust-time aggro exemption ("solid timing"); and the body investigation - a guard walks to the
corpse and stays with it ("hes staying near the body so I call that a win").
**STILL UNVERIFIED:** the 15s loiter -> cover-blown escalation, the stun-witness route, and the
Naxos room/hold prompts and sabotage bar.

Status: `SHIPPED-VERIFIED` for the contain loop, escalation loadout and body investigation;
`SHIPPED-UNVERIFIED` for the rest.

## m2l2a stealth foundations (v1.2.5, 2026-08-10) - SHIPPED, verified in play

Not the stealth *feature* (that is Phase C, still on paper) - the layer underneath it, which was broken:

- **Papers checkers no longer freeze.** `coop_paperPassAll` was swapping the guard's disguise think 50ms into his
  ACCEPT state, into a think with no functions. Deleted; the engine already demotes an accepting sentry.
- **Five disguise gates that were always true.** `thread <label>` in a boolean returns a HANDLE, so every
  `anim/disguise_*.scr` coop gate passed unconditionally - and four statements below them were unreachable,
  including the squad-wide papers pass. All six now read the engine's per-target `is_disguised`.
- **Latch-free aggro.** `attackentity` replaces `attackplayer` wherever a real target exists; the latter sets a
  one-way flag that blinds an actor to disguises for the rest of the map and blames the host, not the offender.
- **Scene actors protected** from the AI-personality system (card players, welders, dock crews, scientists, the 14
  alarm runners). Measured, not guessed: A3 instrumentation caught the prone roll landing on the card man, a Naxos
  watcher and an alarm runner. Path-failure warnings went 138 -> 0.
- **Engine:** unguarded NULL deref in the disguise sight trace (a real crash), and the obstacle-bump branch now
  resolves the player who actually bumped, plus holds off rewriting a scripted-animation actor's think map.
- **Quiet Naxos sabotage** (hold USE) no longer strands the scientist mid-scene.

## Ragdoll physics (v1.4.0 opt-in, v1.4.1 ON by default) - SHIPPED, NEWEST SYSTEM

`cg_ragdoll.c`, client-side. A Verlet solver over the character skeleton: 18 angular joint
limits, world and brush-entity collision, per-bone collision radii, and a settle branch in
which the **authored death animation owns the fall and physics owns the landing** - which is
what stopped bodies looking like dropped puppets. Shoot a corpse and the struck limb moves and
KEEPS where the bullet put it (`coop_ragdollStick`, bounded by `coop_ragdollStickMax`);
explosions vary per limb rather than translating the whole body.

Built over six review rounds (r8-r13) across 2026-08-19..21, ~30 commits. The hard-won ones:
bullet impulses must ROTATE a limb, not translate it; the flesh-hit "direction" was never a
direction until it was torque-coupled; a correction that moves `pt` without `ptPrev` INJECTS
velocity, because in Verlet velocity *is* `pt - ptPrev` (this caused a universal slow spin and
forced the torso-twist limit to be reverted outright); and a wall must not latch the body
rotation.

**Default flip was migration-free, and the reason is worth keeping:** `coop_ragdoll` is
CVAR_ARCHIVE, so a saved config normally beats a changed engine default. It did not here only
because the cvar first existed 2026-08-19, two days AFTER v1.3.1 was cut - no shipped client
had ever registered it. Any future default flip on an already-shipped archive cvar needs a
one-shot migration instead (see `docs/TRAPS.md` T7, and bugs 1940 / 2017).

Status: `SHIPPED` and on by default, but the least-settled system in the mod - odd poses and
occasional over-spin are expected. `coop_ragdoll 0` reverts to retail death animations cleanly.
