# Mortar squads (Allied paratrooper mortar, German mortar / Nebelwerfer) - research + design, 2026-10-18

Study only. No mod code written, no game run. Read from: the stock pk3s (main Pak0-Pak6, mainta pak1-5, maintt pak1-4, extracted and read), `hzm-mohaa-coop-mod` scripts, `openmohaa-hzm/code/fgame`, `docs/TRAPS.md`, `docs/ENGINE.md`, `docs/proposals/alarm_halftrack_2026-10-18/FEASIBILITY.md` (format and reuse notes). Items marked PROBE were not proven by any log I read and need one dedicated-server boot before a build relies on them. Map verdicts in section 6 are desk estimates (script flags + knowledge of the stock maps), not walked terrain: the user checks maps in-game, so the first release should be a per-map opt-in list.

Naming: **Spearhead = t-series (mainta), Breakthrough = e-series (maintt)**, proven by the sound alias `maps` lists (`nebelwerfer_launch` on `t2l1 t2l2`, `e3l4` in mainta / maintt respectively). `alarm_halftrack` FEASIBILITY labels these the other way round; this file uses the pack names.

## 0. Verdict in six lines

1. **A German mortar exists.** It is the **Granatwerfer** (the Wehrmacht Granatwerfer 34 in game), in **Spearhead (mainta)**: a static prop, a `FixedTurret` + cannon, a winter variant, a destroyed variant, a live projectile and a damaging explosion, and a crew animation. The Nebelwerfer (Pak0 base game) is a second, heavier option, not a fallback. The Allied mortar tube is `models/static/us_mortar.tik` (mainta). Both load under the normal BT launch (main + mainta + maintt all mounted).
2. **No script or engine "mortar weapon" can be pointed at a target by the AI.** Every vanilla fire is one of three tricks: a map-placed `ProjectileGenerator` (m3l3, t2l3 barrages), a player-mounted turret (t2l3, e2l3 mortars), or `global/turret.scr::fire_turret` - a scripted fake: origin-stepped arc, then `radiusdamage`. The mod's own M3L3 church barrage and the officer's `coop_artillery_barrage` use the same "telegraph, land, damage" idea. That recipe is proven and safe in this mod, so the mortar squads should be **scripted fire missions** (section 4), not engine projectiles.
3. **Scripts alone are enough** for a first release (crew, site, spotter, fire mission, warning, damage, kill-the-crew). Nothing is blocked by C++. One optional engine command (E1, section 7) would make the Allied mortar's team filter and kill credit exact; a script workaround exists.
4. **Best fit:** Allied mortar on the open paratrooper maps (m3l2, m1l3a/b, m6l1a/b, e1l1, e3l2, t3l1, t2l4, t2l1); German mortar on the same plus the Breakthrough hills (e3l2, e3l4, e1l1/e1l2). Never Omaha, never stealth/disguise, never interiors, never maps that already own a barrage (m3l3, t2l1, t2l3 for the German side).
5. **Main risks:** unfair deaths (answered by warning + cap + floor + LOS-gated damage), crew/site placement on maps with no clean open spot, sound alias `maps` filters (new aliases needed), entity-pool cost per shell, the "Full Deck" challenge counting eight wave types, and the radiusdamage-is-world trap for kill credit.
6. **Path:** shared `mortar.scr` fire-mission core, then the German Granatwerfer as a variant of the existing Artillery wave (type 5), then the Allied mortar stick on the paradrop, then Nebelwerfer and the alarm hook (section 9).

## 1. Asset inventory (exact paths, read from the pk3s)

Pack column: main = Pak0..6, ta = mainta (Spearhead), tt = maintt (Breakthrough). "HD" = the live `zzzzz-hd_gunsounds.pk3` override that wins over stock.

### Models

| Asset | Pack | What it is / key facts |
|---|---|---|
| `models/static/granatwerfer.tik` (+ `models/static/granatwerfer/granatwerfer.skd`) | ta pak1 | German mortar as a prop. `classname object`, scale 0.52, idle anim only, QUAKED box 120 x 103 x 52. **Visual for the crew's tube.** |
| `models/statweapons/P_granatwerfer_base.tik`, `P_granatwerfer_cannon.tik`, `P_granatwerfer_d.tik`, `P_granatwerfer_w_base.tik`, `P_granatwerfer_w_cannon.tik` | ta pak1 | The player-usable German mortar: `FixedTurret` base (`spawnturret 0` the cannon, AnimationSet `nebelwerfer_`, SoundSet `granatwerfer_`) + `VehicleTurretGun` cannon (`projectile models/projectiles/granatwerferproj.tik`, `firetype heavy`, `reloaddelay 2.0`, **`pitchcaps -20 20`**, `maxyawoffset 30`). `_d` = destroyed, `_w_` = winter. `QUAKED addon_turretweapon_german_granatwerfer`. |
| `models/projectiles/granatwerferproj.tik` | ta pak1, tt pak1 | **Live `Projectile`**: speed 1920, `gravity 2.5` (lobs), hitdamage 200, explodeontouch, explosion `models/fx/granatwerferexplosion.tik`, shell skin `models/projectiles/mortar_shell/mortar_shell.skd`. Do NOT spawn as a prop (trap T-init). |
| `models/fx/granatwerferexplosion.tik` (+ `_far`) | ta, tt | `Explosion`, **radiusdamage 110, radius 350, knockback 200**, effect `explosioneffect bazooka`. The retail mortar numbers: a sane starting point for tuning. |
| `models/static/us_mortar.tik` (+ `us_mortar/us_mortar.skd`) | ta pak1 | **Allied mortar tube as a prop** (`classname object`). `models/weapons/us_mortar/` also exists (view-model dir, no tik at top level in the packs I read). |
| `models/statweapons/nebelwerfer.tik` (+ `nebelwerfer/nebelwerfer.skd`), `nebelwerfer_d.tik` | **main Pak0** | Six-tube rocket launcher: `classname animate`, setsize (-60 -40 0)(60 40 120), scale 0.52. Base-game asset, so it loads on any mount. `nebelwerfer_w.tik`, `nebelwerfer_w_d.tik` winter (ta). |
| `models/statweapons/P_nebelwerfer_base.tik`, `P_nebelwerfer_cannon.tik` | ta pak1 | Player-mounted Nebelwerfer (m3l3 / t2l2 style). |
| `models/projectiles/nebelwerferproj.tik`, `nebelwerfersnowproj.tik`, `nebelwerferproj_nodamage.tik` | ta, tt | Live rocket projectile (speed 2000, gravity 1, bazooka explosion). |
| `models/fx/fx_nebelwerfer.tik` | main Pak0 | The scripted rocket in `turret.scr::fire_turret`. **Carries `surface all +nodraw`, `hitdamage 200`, `takedamage`, `health 20`, `explosionmodel` in its init - invisible and live.** Do not copy. |
| `models/fx/Nebelwerfer_exhaust.tik`, `exp_Nebelwerfer.tik`, `models/emitters/nebel_snowexplosion.tik`, `nebelwerfer_death.tik` | ta / main | Muzzle exhaust and explosion variants. |
| `models/ammo/bazooka_shell.tik` | main Pak0 | **Inert** round model (no init block, so no side effects): the m3l1a "rocket is a prop" precedent. Usable as the visible rocket / shell body. |
| `models/projectiles/mortar_shell/mortar_shell.skd/.skc` | ta, tt | The mortar round mesh. Only reachable through a live-projectile tik; a coop_ copy of a tik with no init block (data only) would be the clean visual. |
| `models/human/german_winter_Artillery-Crew.tik`, `models/player/german_Ardennes_Artillery_Commander.tik` | ta / tt pak1 | German artillery crewman (winter) and commander. Already used by `autotank.scr`, `thinktank.scr`. Non-winter German: the stock Wehrmacht / Elite actors the officer waves already spawn. |
| `models/human/allied_airborne_soldier.tik`, `allied_usa_c47-paratrooper1.tik`, `dday_ranger_medic.tik` | main / tt | The paratrooper actors (paradrop.scr:238-248). |

### Effects, emitters

| Asset | Pack | Notes |
|---|---|---|
| `models/emitters/mortar_dirt_dustcloud.tik` | main | `effectentity`, no damage. **Already the impact FX of the officer arty and Stuka** (`officer.scr:3271/3445`). Default impact. |
| `models/emitters/mortar_dirt_nebelwerfer.tik` | main, tt | Dirt plume + mist, sound `arty_exp_sand` (map-gated, so silent off `m3l1 m3l3 train`). Used by M3L3 church barrage (with its own `explo_medium` sound). |
| `models/emitters/mortar_higgins.tik`, `mortar_dirt.tik`, `mortar_dirt_nosound.tik` | main, ta, tt | Other dirt bursts. |
| `models/emitters/mortar_snow.tik`, `mortar_snow_cloud.tik`, `mortar_snowDEADLY*.tik`, `mortar_snowNODAMAGE.tik`, `mortar_snowhit*.tik`, `mortar_tree.tik`, `mortar_concrete.tik`, `mortar_hay.tik` | ta pak1 (some tt) | Surface variants for the Ardennes snow maps. **The un-suffixed and `DEADLY` ones carry `Explosion` / radiusdamage; `NODAMAGE` and `_cloud` do not.** Read the tik before use. |
| `models/animate/fx_mortar_dirt.tik`, `fx_mortar_higgins.tik`, `fx_mortar_water.tik`, `models/fx/mortarhit.tik`, `mortarBurst_tree.tik` | main / ta | `animate` impact FX; `fx_mortar_dirt` is the engine-proven `spawn` form (ENGINE.md). |
| `models/fx/hs_artillery_{dirt,snow,concrete,structure,vehicle}.tik` | ta | Hit-surface decals for artillery. |
| `models/projectiles/artilleryshell*.tik`, `artilleryshellDEADLY/2/3`, `artilleryshellNODAMAGE.tik` | ta / tt | Off-map artillery projectiles (`dontdraw`, speed 16000). Not for a visible shell. |

### Animations

| Asset | Pack | Notes |
|---|---|---|
| `models/human/animation/misc/granatwerfer_driver.skc`, `nebelwerfer_driver.skc` | ta pak1 (granatwerfer_driver also tt) | The PLAYER's mounted-gunner pose (`anims_shared.txt`: `nebelwerfer_idle`). No actor loading / drop-a-round animation exists anywhere in the retail anim set. |
| `models/human/animation/deaths/death_mortar_{flip,high,medium,twist}.skc` | main | Death-by-mortar blow-away anims, already used by `bomber.scr:493-511`. |
| actor `grenade_toss` / `grenade_throw` | mod (parasquad.scr:979) | **The "drop a round into the tube" gesture** is this existing underhand toss, plus a kneel/crouch idle. PROBE: look of it at a prop. |

### Sound

| Asset | Pack | Length | Alias state |
|---|---|---|---|
| `sound/weapons/Fire/knee_mortar_fire.wav` | ta pak1, tt pak1 | 0.76 s | alias `granatwerfer_snd_fire`, `maps` = `t2l3 t3l1 dm obj` (ta) / `e1l3 e2l3 dm lib obj` (tt): **silent on every other map**. |
| `sound/weapons/Fire/MortarFire.wav` | tt pak1 | 2.84 s | alias `mortar_fire`, `maps "t2l3"` (ta). |
| `sound/weapons/explo/Exp_LeadIn_06..13.wav` (incoming whistle) | main Pak3 | stock 0.83 - 1.21 s; **HD override (live) 1.1 - 2.7 s** | `arty_leadin2..7` (`m3l1a m3l1b t2l3`), **mod's `coop_arty_incoming` = LeadIn_08 (`maps "m e t"`, 500-6000 range)**, `coop_arty_leadin_far1..6` (`m e t dm obj train`). The mod already has a working whistle. HD lengths: LeadIn_08 1.10, _10 1.11, _09/_11 1.61, _06/_12 2.29, _07/_13 2.72. |
| `sound/weapons/explo/Exp_Dirt_01..04.wav` | main Pak3 (HD longer: 6-10 s) | 3 s | `arty_exp_sand1..4` (`m3l1 m3l3 train`); mod's `coop_arty_hit` (Exp_Dirt_01, `m e t`), `coop_arty_hit01..04` (`coop_explosions.scr`, `m e t dm obj lib train`). |
| `sound/weapons/fire/nebelwerfer1..3.wav` | main Pak3 | 2.1 - 2.3 s | `nebelwerfer_launch1..3`: `m3l3` (main), `t2l1 t2l2` (ta), `e3l4` (tt). Mod also ships its own copies `sound/weapons/fire/nebelwerfer1..3.wav`. The M3L3 church barrage plays `nebelwerfer_launch` (works only on m3l3). **A launch scream is a built-in 2 s warning.** |
| `sound/weapons/Foley/Mortar_{Grab,Release,Mvmt1..3}.wav`, `knee_mortar_reload.wav`, `PIAT_mortar_pickup.wav` | ta, tt | short | `granatwerfer_snd_on/off/reload/move*` (map-gated). Set-up / pack-up foley candidates (need `coop_` aliases). |
| `sound/mechanics/Mec_Whistle_01.wav` (2.05 s) | main Pak3 | | A plain whistle, not the shell; skip. |
| `sound/amb_stereo/Amb_t2l3_MortarsExt.mp3` | mod | | Distant mortar ambience bed (t2l3 / ambience.scr). |

Rule from TRAPS: **a sound alias's `maps` field is a load filter** (off-list = silent, with neither `maps` nor `always` it registers nowhere; tokens are prefixes). Every new mortar alias needs a `coop_` name with `maps "m e t dm obj train"` (the pattern in `coop_audio.scr:213`) and the lengths registered in `coop_mod/sound.scr` if `playsound_wait` is ever used. `fix_vo_pools.py` KEEP_BARE applies (bug-3160).

### Existing mod pieces to build on

| File | Piece |
|---|---|
| `coop_mod/parasquad.scr` (3111 lines) | Squad brain; **the .30 cal emplacement** `mgPlan / mgSetup / mgTend / mgHold / mgPackup / mgFlee / mgLeft` (bug-3562): site search with cover and field-of-fire tests, walk-up, visible unpack, manning, relocation, pack-up, "crew dead, gun stays". Reused as a pseudo-squad by `reinf_mg.scr`. |
| `coop_mod/reinf_mg.scr` | The German MG42 team that is the closest existing analogue to a German mortar crew: crew of 2-3, covers the officer or his radio, fire-controlled from script, fair-play rules (settle time, bursts, stops at barrel limit), relocates when flanked, assistant takes over. |
| `coop_mod/reinf.scr::rnf_entry` | The hidden-entry planner (ground, room for a man, no player within 900 u, no player eye line to the point, path from the point to the nearest player). The rule the user named. |
| `coop_mod/officer.scr::coop_artillery_barrage` (:3406) and `coop_officer_visible_outdoor_player`, `coop_hasOpenSky`, `coop_strike_scatter`, `coop_find_ground` | The existing German off-map artillery: locked seen-outdoor target, 10 s warning, 3 shells with 250-700 u scatter, `radiusdamage 200 300`. Wave type 5. |
| `maps/M3L3.scr` `coop_churchShell / coop_churchBarrage / coop_churchShellHurt` (:6977-7240) | **The vanilla-recipe-with-fixes**: telegraph, impact FX, salvo ripple, damage by distance capped, hand-rolled loop that skips Germans, `sighttrace` occlusion (bug-2022), real `damage` event so the pain flash / damage arc fire (bug-2015), health floor `max_health / 4` (min 60) so shells never finish a player (bug-2015 follow-up). |
| `global/turret.scr::fire_turret` (:600-730) | Retail scripted nebelwerfer shot: 10-point spline, origin-stepped rocket, `radiusdamage` 260/360/460 by skill, `earthquake`. |
| `coop_mod/paradrop.scr`, `aircraft.scr`, `parasquad_gun.scr` | The call-in and the stick; `coop_para_lz` plans each man's landing point while the planes are inbound. |
| `coop_mod/alarm.scr::alm_blocked` | The gate list (stealth, disguise, mp, lobby, maptest, Omaha, own-alarm maps). Copy it. |
| `coop_mod/xp.scr::xp_airstrike_kill`, `aihandler.scr::addKillToPlayer`, `level.coop_airstrike_caller / _pos / _time` | The kill-credit window for world-attributed blasts. |

## 2. German mortar vs Nebelwerfer: the finding

- **German mortar: YES, it exists.** The Granatwerfer is Spearhead content (mainta pak1): prop + `FixedTurret` + cannon + projectile + explosion + winter + destroyed. The Breakthrough pack (maintt) carries the projectile, explosion, `_far` variants, the `granatwerfer_driver` anim and `granatwerfer_snd_*` aliases for `e1l3 e2l3` (the player-usable mortars at Gela). There is **no separate German "Wehrmacht" model** for the tube itself apart from `granatwerfer` and `P_granatwerfer_*`.
- The brief's fallback is therefore not needed as a fallback. **Recommended pairing:**
  - **Granatwerfer** = the default German mortar squad. One tube, 3 men, 81 mm-style lobbed rounds. Works on every campaign terrain (the prop has no regional paint; winter variant for snow maps).
  - **Nebelwerfer** = a rarer, heavier, louder **rocket salvo** variant (6 rounds, long reload), for Normandy / Ardennes / Rhine / Anzio-style maps and for set-piece escalation (alarm wave 3+, officer at 25% HP). `m3l3` has 4 static Nebelwerfers and a coop-made barrage already, so the new squad is not used there.
- Sound: both launch sounds exist (`knee_mortar_fire` 0.76 s for the Granatwerfer; `nebelwerfer1-3` 2.2 s for the rocket). Only the Nebelwerfer sound is already in mod aliases that reach several maps; the Granatwerfer one needs a `coop_` alias (section 8).
- Allied: `us_mortar` prop (mainta) is the only Allied tube. No Allied mortar crew animation or shell sound exists beyond the shared `knee_mortar_*` and `Mortar_*` foley.

## 3. Vanilla and mod recipes to copy (and what to leave)

| Need | Recipe to copy | Where | Leave behind |
|---|---|---|---|
| Visible round in flight, cheap | Origin-stepped inert model along an arc, every frame or every 0.05 s (moveto no-ops on `script_model`) | `turret.scr::fire_turret` spline; `m3l1a/coopified.scr:2143, 9299` ("the rocket is a prop") | `fx_nebelwerfer.tik` (invisible + live), `artilleryshell*.tik` (`dontdraw`), `granatwerferproj.tik` as a prop |
| Telegraph then land | whistle at impact point, wait, FX, damage | `M3L3.scr::coop_churchShell`; `officer.scr::coop_artillery_barrage` | the 10 s officer warning (right for Stuka/arty waves, wrong for a mortar), pinpoint-on-player aim |
| Damage that cannot be a surprise kill | hand-rolled loop, `sighttrace` occlusion, `damage` event, floor at `max_health/4`, damage cap | `M3L3.scr::coop_churchShellHurt` | raw `health -=` (bug-2015), distance-only without occlusion (bug-2022) |
| Salvo ripple | one thread per rocket, 0.4 s apart, damage cut to compensate overlap | `coop_churchBarrage` | one-at-a-time that blocks on its own cleanup |
| Crew + gun site + deploy + pack-up + relocation + crew-dead behaviour | the pseudo-squad over `parasquad.scr` mg code (`mgPlan/mgSetup/mgTend/mgHold/mgPackup/mgFlee/mgLeft`) | `parasquad.scr`, `reinf_mg.scr` (hooks: `rmg_wave`, one flag in `rnf_idle_check`, the `[mgteam]` lines) | the MG-specific parts (belt, barrel heat, bipod, field-of-fire arcs); a mortar needs open sky and a range ring, not a firing arc |
| Where the wave appears | `reinf.scr::rnf_entry` | | n/a |
| Target must be outdoors | `officer.scr::coop_hasOpenSky` + `coop_officer_visible_outdoor_player` | | n/a |
| Safe Allied support | no friendly damage at all by construction; paratrooper grenade rules (>= 450 u from thrower and every player, >= 400 u from allied actors, re-check before release) | `parasquad.scr` header and `nadeWatch` | `radiusdamage` (attacker hardcoded to world; hurts everyone) |
| Call-in plumbing, XP, challenges | `xp_support_call`, `chal_support_call`, `feed_all` | `paradrop.scr:10-36` | n/a |
| Gate | `alm_blocked` style list | `alarm.scr:30-42` | n/a |
| Coop-only, not MP | `level.coop_mpRun`, `docs/tools/check_mp_isolation.py` | | n/a |

Vanilla maps that already fire this kind of thing (do not stack a second layer): `m3l3` (nebelwerfers + coop church barrage), `t2l1` (4 static nebelwerfers are the objective), `t2l2` (nebel1 player turret), `t2l3` (`gags/t2l3_blitzkrieg.scr` projectile-generator barrage + Granatwerfer turret, `medicforcebarrageon`), `e2l3` (player-use mortars `mortarWest/South`), `e1l2` (`maps/e1l2/Artillery.scr`, 3 gun objective), `e1l3` (`Conquest.scr::MortarEmitter`), `m1l2a` (a placed nebelwerfer prop), `e3l4` (nebelwerfer sound set).

## 4. Squad design (shared fire-mission core + two squads)

### 4.1 The fire mission (one routine, both sides)

A **fire mission** is: pick an aim point, telegraph, fly, land, hurt. It is script-only and mirrors the church barrage with a visible arc added.

1. **Aim point** from the spotter's last-seen position of the target (not live tracking), plus scatter.
2. **Launch**: tube flash and thump at the tube (`coop_` alias for `knee_mortar_fire.wav`), a tiny dust puff at the muzzle, crew gesture (`grenade_toss` on the loader).
3. **Flight**: time of flight = clamp(distance / 450, 2.5, 5.5) s. An inert shell model (`models/ammo/bazooka_shell.tik`, or a coop_ tik on the mortar_shell mesh) is origin-stepped on a parabola by one thread (1 entity, deleted at the end). Cosmetic only, never a `Projectile` (no side effects, no stray damage).
4. **Warning**: the incoming whistle, on a script_origin at the **impact point**, started `warn` seconds before landing (default 1.6; HD pack gives LeadIn_09/_11 at 1.61 s; stock gives 0.83-1.21 s, so key the alias to a long file or play two). Players within hearing radius (500-6000 u alias range) get it; players beyond see the launch flash. No ground marker (a marker makes it trivial; open question Q7).
5. **Impact**: `mortar_dirt_dustcloud.tik` (or `_snow_cloud` on snow maps, a damage-free variant chosen after reading the tik), `coop_arty_hit0N`, a small `earthquake` (the `.03 .05` retail value), removed after 3-4 s.
6. **Damage**: not `radiusdamage`. A hand-rolled loop (church recipe) over the target set, with distance falloff, `sighttrace` occlusion, the real `damage` event, a per-shell cap and a floor. The target set differs by side (section 4.4).

### 4.2 German squad (Granatwerfer; Nebelwerfer variant in brackets)

| Item | Granatwerfer squad | Nebelwerfer variant |
|---|---|---|
| Crew | **3**: gunner, loader, spotter (Wehrmacht or winter Artillery-Crew model by theatre). Optionally +1 rifleman escort on 5+ players. | **3**, same roles |
| Tube | `models/static/granatwerfer.tik` (winter: nothing extra needed, the prop is the same) as a `script_model`/object, `health`/`takedamage` set, killed by explosives or enough bullets (PROBE which damage types a script object accepts; use the m3l3 `immune` recipe) | `models/statweapons/nebelwerfer.tik` (Pak0), same |
| Deploy time | walk to site, then **6 s** visible set-up (kneel, tube down, `Mortar_Grab` foley), first round no sooner than 8 s after arrival. Cvar `coop_mortarSetup`. | 9 s |
| Rounds | 18 on the tube; at 6 / min the squad is spent in 3 min, then it falls back to a normal rifle squad that holds the site. | 6-rocket magazine, 1 reload of 40 s, 3 reloads total |
| Fire mission | 1 round (<= 2 players), 2 rounds (3-4), 3 rounds (5+), 2.5 s apart; **mission cooldown 20-30 s**, divided by nothing. | 6 rockets, 0.4 s ripple (church recipe), damage per rocket cut so a salvo is "constant pressure you must move under" |
| **Rounds per minute (hard cap)** | `coop_mortarMaxRpm` = 5 + (players beyond 1, max 3), i.e. 5 / 6 / 7 / 8, enforced by a sliding 60 s counter | one salvo per 40 s |
| Damage | centre 110 (retail `granatwerferexplosion`), linear to 0 at 300 u (retail radius 350 is an outdoor open-ground figure; use 300 for the sighttrace-gated version), cap 140 per shell, **floor `max_health / 4` (min 60)** so the shell can pressure but not finish (church precedent; see Q3) | centre 70, radius 260, cap 90 per rocket |
| Player-count scaling | **frequency scales, lethality does not**: rounds per mission and RPM cap rise with players; per-shell damage is fixed; crew HP uses the existing player scaling (`aihandler.scr` / `rmg_Hp` style, `coop_mortarHp` default 140 before scaling) | same |
| Accuracy / scatter | aim at the last-seen position, **plus a 120-300 u scatter ring**, shrinking 20% per consecutive round on the same target ("ranging in"), reset when the target moves > 400 u. A target who keeps moving is rarely hit. | 250-450 u ring, never ranges in |

**Target selection (never blind map-wide spam).** The spotter is a real crew member standing within ~350 u of the tube (not on it). A fire mission may only start when ALL hold:
- the spotter is alive and `cansee` a living, active, non-downed player (DBNO and spectators excluded), within the tube's range band **500 - 1900 u** (min range keeps it from dropping on its own crew; max range keeps it local);
- the player is **outdoors** (`coop_hasOpenSky`; same test the officer artillery uses) - under a roof or in a doorway nobody is shelled, which is also the players' counter;
- the player has been continuously in view for >= 2 s (no snap shots on a peek);
- the aim point is >= 250 u from every crew member and tube, and has open sky;
- no two consecutive missions on the same player when another is eligible (spreads the fire);
- at most one German mortar mission in flight map-wide, and the global RPM cap above.
With the spotter dead, the gunner may only fire at the **last remembered** aim point with 2x scatter, and stops after 2 such missions. With no spotter and no crew line of sight, no fire. A spotter can be an existing Elite/AT man if the squad shares a wave.

**Fair-play rules:** first fire mission never earlier than 12 s after any player first sees the crew or 25 s after the squad spawns, whichever is later; no mission against a player within 12 s of respawn; nothing fires while a wave's `rnf_entry` ground is within 900 u of a player (the same hidden-entry distance).

**Warning to players:** (1) a feed line on first sight of the tube ("Mortar crew spotted" via `feed.scr::feed_all`, once per mission), (2) the launch thump + flash at the tube, (3) the impact-point whistle at `warn` = 1.6 s, (4) the crew's German shout ("Feuer!") via the existing `rnf_speak` plumbing. A 1-2 s whistle is deliberately short: enough to run or drop prone, not enough to be a free pass; the first mission of a squad uses 2.4 s.

**Crew can be killed; tube can be destroyed.**
- The crew are ordinary actors, marked and tracked the way the MG team's crew are (`reinf_mg.scr`), so wave rosters, XP and idle watchdogs treat them like any wave man.
- Loader dead: rate drops to 60%. Gunner dead and loader alive: loader takes the tube (the `rmg_succ` rule). Spotter dead: remembered-point fire only (above). All dead: the tube stays, **inert and solid cover**, no fire.
- Tube destroyed (explosive, or the crew's last man dies carrying out a `mgFlee`-style abandon): destroyed model `granatwerfer_d` (ta) / `nebelwerfer_d` (Pak0), FX `mortar_higgins` (a bare `radiusdamage 15 96` like `officer.scr:4712` is the only damage allowed).
- Crew relocate when flanked or when a player is within 400 u (the MG team's flank rule), pack up, and re-deploy at the next legal site; losing the tube while relocating is the "destroy it to stop it" window.

### 4.3 Allied paratrooper mortar team

| Item | Design |
|---|---|
| Delivery | the existing C-47 call-in (`paradrop.scr`), as a **stick variant**: with `coop_paraMortarChance` (default 33 %) on an eligible map, men 2 and 4 become **mortar gunner + spotter** instead of Thompson and sniper. Man 1 (BAR), 3 (Garand + .30 cal) and 5 (medic) are unchanged. 5 men total, **no extra entities beyond the tube and one shell**. The stick's `coop_para_lz` landing plans already exist. |
| Crew | 2 (gunner, spotter) plus the BAR / Garand / medic as escort. A 3rd man (loader) is the medic? **No**: medic keeps his own loop. Gunner loads himself. |
| Tube | `models/static/us_mortar.tik` as a prop at the site; destroyable by German fire (same object rules as the German tube). |
| Deploy | the squad brain holds 6 s after landing, then the gunner walks to the **site** (below) and sets up in 5 s (visible, `Mortar_Grab`). First round 11 s after landing at the earliest. |
| Rounds | 12; 5 rounds per minute cap (`coop_paraMortarMaxRpm`); stays active 150 s then packs up; after that the men fight on as ordinary paratroopers. |
| Targets | enemies the **spotter** sees: Germans from `level.coop_wave_actors` (the registered wave roster, officer.scr:1464-1472) plus any hostile the engine reports as the spotter's `enemy` / `lastenemy`; each target must be **>= 450 u from every player and every allied actor** at fire and at landing (the paratrooper grenade rule), 300 - 1700 u from the tube, with open sky. Prefers groups (>= 2 within 250 u) and the officer / MG nests. |
| Friendly fire | **none, by construction**: the damage loop only enumerates enemy-team targets and never touches players or allies; the 450 u check is only so the burst is not drawn on top of a friend. Allied shell, allied crew, allied tube never hurt friends, including the case where the thrower is dead. |
| Kill credit | assign the smoke owner through the existing airstrike window (`level.coop_airstrike_caller / _pos / _time`, `xp_airstrike_kill`) or, with engine command E1, the crew actor as true attacker. XP: `xp_support_call` already pays the call-in. |
| Counterplay | the crew are targetable by German fire; the tube is a target; a spotter killed = remembered-point fire stops. |
| Why not a 6th man | entity budget, `pk[]` door mapping (5 men across 3 aircraft), and `coop_paradrop_squad_monitor`'s fixed 5 slots (`paradrop.scr:116-143`). Replacing two roles is the least invasive change. |

### 4.4 Friendly-fire matrix

| Shell side | Players | Allied actors (paratroopers, escorts) | Germans | Props / vehicles / NPC objectives |
|---|---|---|---|---|
| German mortar / Nebelwerfer | hurt (capped, floored, LOS-gated) | hurt (same loop, so paratroopers can be shelled; they have 550 hp) | **never** (church recipe) | **never** (no `radiusdamage` anywhere: objective NPCs, planted charges and escort vehicles are untouched) |
| Allied mortar | **never** | **never** | hurt | **never** unless a map opts in |

### 4.5 Reachability and the hidden-entry rule

- **German appearance**: the squad is formed with `rnf_entry` (a point no player can see from, >= 900 u away, with a path to the nearest player), walks to its tube **site** (below) and sets up. The tube site is **a different, further point** than the entry: a mortar needs open sky and standoff, not a wall to hide behind.
- **Site rules** (adapted from `mgPlan`): ground (`droptofloor`, slope < 18 degrees), a 4 u radius free of solid, **open sky** (`coop_hasOpenSky`), range band to the player centroid **700 - 1600 u**, on the **enemy side of the players' line of advance** (opposite the players' trail, like `rmg` using `psqAyaw`), >= 1000 u from every player start / spawn point, **a walkable path from the nearest player** (scout test as in `rnf_entry`, so players can always reach and kill it), not inside a doorway, not on a bridge or train, never in a trigger the map uses as an objective (flat-ground check against `$objective*`/`$flak*` names is a PROBE).
- If no site passes: no mortar squad. The wave falls back to the existing Artillery (off-map) wave or an infantry squad. **The squad never spawns without a legal site.**
- **Allied appearance**: the paratroopers' own `coop_para_lz` landing; the tube site is chosen **behind** the players: >= 250 u behind the wedge anchor (the smoke thrower / nearest player), open sky, range to the nearest German group > 450 u, a flat spot within 350 u of the gunner's landing, and never in front of any player's muzzle.
- Not used on: Omaha (`m3l1a`, `m3l1b`), any `level.coop_stealthMap == 1` or `level.coop_enableDisguises` map (`e1l4`, `m2l2a`, `m2l2b`, `m6l1c`, `m6l2a`), interiors, MP arena runs (`level.coop_mpRun`), lobbies, map-tester runs. Same gate shape as `alarm.scr::alm_blocked`.

## 5. Engine and scripting limits (checked)

| Question | Finding |
|---|---|
| Does the engine support an AI mortar? | No dedicated weapon. `Projectile` has `gravity`, `speed`, `explodeontouch`, `hitdamage`, `knockback`; `arctotarget` sets `m_bArcToTarget` and posts Prethink, but **`m_bArcToTarget` is read nowhere else** (`weaputils.cpp:643, 1407-1411`), so it is a no-op stub. A lob comes from `gravity` + launch angle only. |
| Can a script launch a `Projectile`? | Not directly. Projectiles are launched by a `Weapon`/turret `shoot`, `ProjectileGenerator[_Projectile]` (BSP-placed; `ProjectileGenerator_Gun` is script-spawnable, `BattleHouse.scr:392`) or the strafing-gun entity (`script_simplestrafinggunfire`, `projectile` key, used by the Stuka). A live projectile brings `hitdamage`, `knockback` and the explosion's `radiusdamage` with it, all hitting everything. |
| Real turret option | `P_granatwerfer_base/cannon` fires `granatwerferproj` when a **player** or an AI gunner works it. `pitchcaps -20 20` limits the lob unless overridden; `VehicleTurretGun` overrides `Think/UpdateFireControl` so `TurretGun` fixes do not apply (TRAPS). Possible, but you then own friendly-fire, targeting and pathing inside engine classes. **Not recommended.** |
| `radiusdamage` from script | `ScriptThread::EventRadiusDamage` hardcodes inflictor and attacker to `world` (`scriptthread.cpp:4467-4485`). Consequences: it hurts every team, cannot be attributed to a crew actor, and kill credit needs the `coop_airstrike_*` window. It does ping tinnitus and does the sight trace. |
| Entities | `maxentities 2048`, shell cost: 1 script_model (shell) + 1 emitter + 1 script_origin (whistle/impact) = 3 per round, all removed within 5 s. The Stuka run allocates ~22 in 2 s; a 3-round mission is far below that. `spawn` can return NULL: guard every spawn. |
| Cvars | the mod's cvar budget is MAX_CVARS 8192 and archived cvars are expensive; new tunables should be level vars with `getcvar` read live, unset = default, as `reinf_mg.scr` does. |
| Damage feedback | use the `damage` event (not raw health) so the pain flash and damage-direction arc fire (bug-2015); add the `sighttrace` occlusion (bug-2022). |
| Same-team filtering | `Sentient::ArmorDamage` drops damage whose attacker is a same-team sentient in all gametypes, which is why paratrooper bullets cannot hurt players. A `world` attacker bypasses it. |
| Projectile-class spawn from script | `models/projectiles/*.tik` have `classname Projectile` in their init; `spawn script_model model "..."` still runs that init block (TRAPS T-init, bug-2244). Never spawn those as props. |

**Engine edits (all optional, marked E):**
- **E1 (recommended, ~40 LOC, S):** a script command `coop_blast origin radius damage attacker teammask` (new, next to `EventRadiusDamage`) that calls the existing `RadiusDamage(origin, inflictor, attacker, damage, ignore, mod, radius, knockback, constant, weap, hurtOwnerOnly)` with the **real attacker** and a team filter. It gives the Allied mortar exact friendly-fire behaviour and true kill credit, removes the `coop_airstrike_*` guesswork and the hand-rolled loop's per-frame cost. Without it, section 4 works with the hand-rolled loop, which is the only supported route today. Needs a `game.dll` redeploy to `G:\mohaa-gl2\` and the GOG root (CLAUDE.md), and a bump in `docs/ENGINE.md`.
- **E2 (not needed):** an AI-targetable `ProjectileGenerator` spawn - skip.
- **E3 (not needed):** make `arctotarget` real - skip; script arcs are fine.

## 6. Per-map verdicts

Rules applied: campaign maps from the maptest list (54 maps) and `officer_positions.scr`. **Good** = open terrain, paradrop and officer waves active, no vanilla barrage in the way. **Possible** = works only on a hand-picked area, a vanilla set piece, or the map is small/urban. **No** = blocked by a hard rule (Omaha, stealth/disguise, interior, paradrop off for the Allied side, owns its own barrage for the German side). `Allied` needs `coop_feature_paradrop == 1` and a smoke source; `German` needs officer waves on and wave type 5 allowed (`coop_wave_mask` bit 5 set, `level.coop_officer_no_airstrikes != 1`).

| Map (display name) | Series | Terrain | Allied mortar (paradrop) | German mortar / Nebelwerfer | Notes |
|---|---|---|---|---|---|
| m1l1 Rangers Lead the Way | AA | Algerian coast fort | No (officer drops no smoke) | Possible | Mask 57: type 5 allowed; small map |
| m1l2a The Rescue Mission | AA | desert fort/town | Possible (paradrop armed by script) | Possible | Own alarm; fort walls; walk the site |
| m1l2b Sabotage the Motorpool | AA | base compound | Possible | Possible | Compound, little open sky |
| m1l3a Desert Road | AA | open desert | **Good** | **Good** | Long sight lines, tanks |
| m1l3b Grounding the Airfield | AA | airfield | **Good** | **Good** | Large open |
| m1l3c Lighthouse | AA | cliff top | Possible | Possible | Tight |
| m2l1 Secret Documents of the Kriegsmarine | AA | Norwegian port | Possible | Possible | Buildings |
| m2l2a Naxos Prototype / m2l2b Inside the U-529 | AA | disguise maps | **No** | **No** | Hard block (disguise) |
| m2l2c Cover Blown | AA | sub pen interior | **No** | **No** | `no_airstrikes` already set |
| m2l3 Escape from Trondheim | AA | train station | **No** | **No** | Paradrop off, escape map |
| m3l1a / m3l1b Omaha | AA | beach / bunker | **NEVER** | **NEVER** | Omaha rule |
| m3l2 Battle in the Bocage | AA | Normandy hedgerows | **Good** | **Good** | Indirect fire excels here; hedges block LOS so the spotter rule matters |
| m3l3 The Nebelwerfer Hunt | AA | village / church | **Good** (paradrop armed in script) | **No** | Owns a coop Nebelwerfer barrage and 4 static nebels |
| m4l0 Secret Dog Map | AA | - | No | No | Paradrop off |
| m4l1 Rendezvous with the Resistance | AA | French village | Possible | Possible | Alarm-ready map |
| m4l2 Diverting the Enemy | AA | rail / camp | Possible | Possible | Alarm-ready |
| m4l3 The Command Post | AA | chateau, interior heavy | No | No | Adopted vanilla alarm, interiors |
| m5l1a Sniper's Last Stand - Outskirts | AA | ruined town | Possible | Possible | Urban LOS |
| m5l1b Sniper's Last Stand - City Hall | AA | urban | No | No | Tight streets |
| m5l2a The Hunt for the King Tiger - Destroyed Village | AA | village | Possible | Possible | |
| m5l2b The Hunt for the King Tiger - Country Road | AA | country road | No (`coop_feature_paradrop = 0` in `officer_positions.scr`) | **Good** | Open road; German side only |
| m5l3 The Bridge | AA | bridge defence | Possible | Possible | Mask 63 (no AT, no dogs) |
| m6l1a Siegfried Forest - Flak Guns | AA | forest | **Good** | **Good** | Clearings |
| m6l1b Siegfried Forest - Bunker Hill | AA | hill | **Good** | **Good** | |
| m6l1c Das Sturmgewehr | AA | stealth | **No** | **No** | Stealth hard block |
| m6l2a Communications Blackout | AA | stealth | **No** | **No** | No waves |
| m6l2b Schmerzen Express | AA | train | No | No | |
| m6l3a - m6l3e Fort Schmerzen | AA | fort interior / yards | No | No | Interiors; m6l3a owns an alarm |
| e1l1 Battle of Kasserine Pass 1 | BT | desert hills | **Good** | **Good** | Afrika theatre |
| e1l2 Battle of Kasserine Pass 2 | BT | hills + 3 artillery guns | Possible | Possible | `Artillery.scr` objective; do not stack |
| e1l3 Operation Torch - Bizerte Fort | BT | fort | Possible | Possible | Has vanilla `MortarEmitter` |
| e1l4 Operation Torch - Bizerte Harbor | BT | stealth/disguise | **No** | **No** | Hard block |
| e2l1 Sicily | BT | coast / town | Possible | Possible | AB41 objective |
| e2l2 Operation Husky - Caltagirone | BT | hill town | Possible | Possible | |
| e2l3 Operation Husky - Gela | BT | town + tanks | Possible | No | Vanilla player-use mortars `mortarWest/South` |
| e3l1 Invasion of Monte Cassino 1 | BT | town ruins | Possible | Possible | |
| e3l2 Invasion of Monte Cassino 2 | BT | mountain approach | **Good** | **Good** | |
| e3l3 Battle of Anzio | BT | scripted ride + defence | Possible | Possible | Convoy/rail set piece |
| e3l4 Battle of Monte Battaglia | BT | hill assault | No (paradrop off) | **Good** | Nebelwerfer sounds exist in tt |
| t1l1 Operation Overlord 1 | SH (Spearhead) | night fields | No (paradrop off) | Possible | Intro cinematic |
| t1l2 | SH | bridge / town | Possible | Possible | Sky check fails on bridge decks; `coop_binoc_skyCheck 0` precedent |
| t1l3 | SH | town | Possible | Possible | |
| t2l1 Bastogne - Nebelwerfers | SH | snow | **Good** | **No** | The four static Nebelwerfers are the objective |
| t2l2 | SH | snow, player halftrack | No (paradrop off) | No | |
| t2l3 | SH | snow, Granatwerfer + barrage | Possible | **No** | Owns a barrage (`t2l3_blitzkrieg.scr`) |
| t2l4 | SH | snow (mortar ambience bed) | **Good** | **Good** | |
| t3l1 | SH | Rhine, trucks/panzers | **Good** | **Good** | Alarm-ready |
| t3l2 | SH | urban / factory | No (paradrop off) | No | |

Honest caveat: terrain labels are from my knowledge of the stock campaigns; **only the flags (paradrop, mask, stealth, airstrikes) are read from code**. First release = a whitelist (`level.coop_mortarOk = 1` set by hand per map after the user checks it), default off. Start list: m3l2, m1l3a, m1l3b, e1l1, e3l2, m6l1a, m6l1b, t3l1, t2l4 (Allied + German); m3l3, t2l1 (Allied only).

## 7. Squad numbers in one place (all live cvars / level vars, unset = default)

| Name | Default | Meaning |
|---|---|---|
| `coop_mortar` | 1 once shipped, **0 until playtested** | master |
| `coop_mortarChance` | 50 | % of Artillery (type 5) waves that become a mortar crew when a site exists |
| `coop_mortarSetup` | 6 | seconds of visible set-up before the first round |
| `coop_mortarWarn` | 1.6 | whistle seconds before impact (2.4 on a squad's first mission) |
| `coop_mortarMaxRpm` | 5 + extra players (max 8) | hard rounds-per-minute cap, German |
| `coop_mortarDmg` / `coop_mortarCap` / `coop_mortarRad` | 110 / 140 / 300 | centre damage, per-shell cap, radius |
| `coop_mortarFloorDiv` | 4 | player floor = `max_health / 4` (0 = shells may kill) |
| `coop_mortarMinRange` / `MaxRange` | 500 / 1900 | tube range band |
| `coop_paraMortarChance` | 33 | % of paradrop sticks on a whitelisted map that carry the mortar |
| `coop_paraMortarMaxRpm` | 5 | Allied cap |
| `coop_mortarDebug` | 0 | `^~^~^ MORTAR` lines |

## 8. Risks

| Risk | Why | Answer |
|---|---|---|
| Unfair damage | players read incoming shells as cheap | warning >= 1.6 s, short range band, outdoors-only, LOS-gated hand loop, floor at 25 %, per-shell cap, RPM cap, hard first-fire delay; ship with `coop_mortar 0` and play it |
| Pile-on at the spawn | mortars outside the players' view can shell a pinned team | first-fire delay, not within 1000 u of a spawn, no mission on a respawned player for 12 s, max 1 mission in flight |
| Site not found / blocked route | many maps have no clean open spot | no site = no squad, fall back to the existing barrage (type 5) or infantry; per-map whitelist |
| Crew stuck / not killable | open-sky sites can be unreachable | scout path test (`rnf_entry` recipe) at planning time, `mgGiveUp`-style watchdog, remove the squad after 90 s stuck |
| Kill credit and friendly fire (Allied) | `radiusdamage` is world-attributed and hits everyone | hand loop over enemy targets only; `coop_airstrike_*` window; optional E1 engine command |
| Sound silent | alias `maps` load filter; `granatwerfer_snd_fire` is `t2l3 t3l1 dm obj` / `e1l3 e2l3 dm lib obj` | new `coop_` aliases, `maps "m e t dm obj train"`, tested on a map each of m/e/t; HD pack changes lead-in length (0.83-1.2 s stock vs up to 2.7 s) - choose the file by measured length |
| Hidden-live tik | `fx_nebelwerfer`, `granatwerferproj`, `mortar_dirt`, `mortar_snowDEADLY` all carry init blocks that run on `spawn script_model model` (bug-2244) | spawn only inert models (`bazooka_shell`, props); read every tik; the impact FX list uses `dustcloud` / `_cloud` / `NODAMAGE` variants |
| Entity pool | `maxentities 2048` | <= 3 entities per round, deleted in 5 s, NULL-guard every spawn, one mission in flight |
| "Full Deck" challenge | counts eight wave types through `coop_chalDeck_<r>` | keep the mortar crew **a variant of wave 5** and credit `r == 5`; do not add a 9th type (Q2) |
| Alarm / reinf interplay | `alm_waves` caps live men (8) and `rnf_idle_check` watches idle wave men | the crew is counted, spotted by `rnf_idle_check`, and does not exceed the cap; flag the crew `coop_rmgOn`-style to keep the idle watchdog from retiring them |
| Allied squad regression | `paradrop.scr` stick order and `coop_paradrop_squad_monitor` expect 5 roles | replace roles 2 and 4 only; one extra helper `mortar_brain` thread; keep the .30 cal man |
| MP / lobby leakage | the mod's isolation rule | gate on `level.coop_mpRun`, lobbies, maptest; run `docs/tools/check_mp_isolation.py` |
| Script parse killers | em-dash, bare negatives, BOM, brace mismatch | the usual (TRAPS, CLAUDE.md); new file `coop_mod/mortar.scr`, depth-scan it |
| Performance (4-core guard) | `cansee` on 1-4 players per second, `traced` slope tests at planning only | 1 s spotter tick, planning outside the combat tick, the fire mission is one thread per round |
| The look | no real loading animation; the tube prop is big (120 x 103 x 52 u box) | kneel idle + `grenade_toss` gesture; keep the camera view short; judge in game before showing GIFs |
| Download / pk3 impact | none; no new binary asset, only 3 sound aliases and optionally one coop_ tik (data) | lives in `zzzzzz_co-op_hzm_mod_code.pk3` |

## 9. Path (staged, each stage shippable and off by default)

0. **Probes (one dedicated-server boot, ~30 min):** (a) `spawn script_model model "models/static/granatwerfer.tik"` and `us_mortar.tik` and `statweapons/nebelwerfer.tik` render and `takedamage`/`health` work on them; (b) `models/ammo/bazooka_shell.tik` as an origin-stepped round is visible; (c) actor `grenade_toss` beside a prop; (d) the `coop_` Granatwerfer launch alias plays on one m-, one e-, one t-map; (e) that a script object accepts explosive damage.
1. **`coop_mod/mortar.scr` core:** fire mission routine (aim, launch, flight, whistle, impact, hand loop), RPM counter, gate list, debug lines. Test with a developer command that places a tube at a viewpos (the `coop_build` catalogue already places models and statweapons).
2. **German Granatwerfer:** site planner (rnf_entry + mgPlan rules), crew spawn through the pseudo-squad hooks that `reinf_mg.scr` uses, the type-5 dispatch hook in `officer.scr` (one call, falls back to the barrage), whitelist maps.
3. **Allied mortar:** stick variant in `paradrop.scr` (men 2 and 4), `mortar_brain`, shared core in "allied" mode.
4. **Nebelwerfer variant** and the alarm-wave / officer-25 % hook; consider **E1**.
5. Playtest per the harness; GIFs for the release README (weather-style media rule), update `docs/FEATURES.md`, `docs/OPEN.md`, `docs/TRAPS.md` (the new gotchas), `.wolf/buglog.json` for any defect.

## 10. Decision questions

| # | Question | Recommended default |
|---|---|---|
| Q1 | Which squad first? | **German Granatwerfer first** (reuses the officer wave gate and the MG-team code; replaces a blind barrage with a killable crew), Allied mortar second. |
| Q2 | New wave type, or a variant of Artillery (type 5)? | **Variant of type 5** at 50 %, falls back to the existing barrage; keeps "The Full Deck" at eight kinds. A 9th type would need the challenge text and counters changed. |
| Q3 | May a mortar kill a player? | **No for the first release**: floor `max_health / 4`, as the M3L3 church barrage after bug-2015. Revisit with `coop_mortarFloorDiv 0` after a playtest. |
| Q4 | Allied mortar: replace two paratroopers (Thompson + sniper), add two, or a separate smoke? | **Replace roles 2 and 4 on 33 % of sticks on whitelisted maps**; keep BAR, Garand + .30 cal, medic. |
| Q5 | Nebelwerfer: ship in v1? | **Defer to stage 4.** The Granatwerfer covers all maps; the Nebelwerfer is a harder, rarer variant for Normandy / Ardennes / Anzio and alarm escalation. |
| Q6 | Map policy | **Opt-in whitelist** (`level.coop_mortarOk`), default off, built map by map with the user checking in game; hard blocks always win (Omaha, stealth, disguise, interior, mp, lobby, maptest). |
| Q7 | Visible aid for the player? | **Audio + tube flash only** (whistle 1.6 s, 2.4 s on the first); no ground marker. Add a faint dust ring later only if playtests say it is invisible. |
| Q8 | Engine command E1 now? | **Not for v1**; script-only first, E1 only if the hand loop's kill-credit window proves flaky for the Allied side. |

## 11. Ten facts to carry into the build

1. Mortar = Granatwerfer (`models/static/granatwerfer.tik`) in mainta pak1; Allied tube = `models/static/us_mortar.tik`; Nebelwerfer = `models/statweapons/nebelwerfer.tik` in Pak0.
2. Never `spawn script_model model` a `projectiles/` or `fx_nebelwerfer` tik: their init runs, and several are live and invisible.
3. `radiusdamage` is world-attributed, hits all teams, and ignores a crew actor as attacker.
4. The M3L3 church barrage is the reference for damage fairness; reuse its loop, its floor and its cap.
5. Warning = whistle at the impact point; `coop_arty_incoming` exists on `m e t`; the HD pack makes lead-ins up to 2.7 s - choose by length.
6. A new alias must carry `maps "m e t ..."` or it is silent.
7. Crew, site, deploy, pack-up, crew-dead and relocation code already exist (`parasquad.scr` mg code, `reinf_mg.scr`); do not rewrite them.
8. `rnf_entry` is the hidden-entry rule; a legal site or no squad.
9. Gate list = `alarm.scr::alm_blocked` + paradrop flag + wave mask + `no_airstrikes`.
10. Engine: nothing required; E1 (team-aware blast with a real attacker) is the one worthwhile add.

## 12. Build status (2026-10-18, mod branch `mortar-next`, worktree `C:\mohaa-coop-dev\hzm-mod-mortar`)

Built from section 4 with the user's answers (both squads together, no mortar kills, two extra paratroopers, health nerf `coop_paraHealthPct` 80). New file `coop_mod/mortar.scr`; hooks: one block in `officer.scr` (type 5), `paradrop.scr` (health pct, 7-man stick, wtype 6/7), `ubersound/coop_mortar.scr`, `autoexec.cfg` notes; separate commit `68280d42` fixes the m3l3 church barrage hit location. Harness proofs: `tools/` (mz_run.py, mz_probe.py, mz_drv.scr), logs in `tools/logs/`.

- Proven in the private harness (m3l2): German crew spawn out of view, walk, set up, rule A/B target pick, whistle + impact, floor hold (hits from 208 / 250 / 158 / 186 landed on exactly 62 = max/4, never below), Allied team lands, sets up, rounds hit Germans only (hits=3, 2).
- Defects found on the way (bug-4032..4034): damage location 0 = head x4, `mz_para_member` self-call, m1l3a scripted ride (test placement does not stick).
- Final whitelist (site probe, 8 placements per map, `tools/logs/probe_p2.txt`, `probe_p3.txt`): German m3l2, m1l3a, t3l1; Allied also m1l3b, e1l1, e3l2, t2l4, m3l3, t2l1. Dropped: m6l1a, m6l1b (forest), e3l4, m5l2b.
- Not verified: the tube/crew animations (no loading animation exists; the crew stands), the shell's look, nothing run on MP/dedicated, the real officer path (wave 5 -> `mz_g_wave` was called directly by the driver, `coop_call_reinforcements` with mask 32 was never run end to end), Allied kill XP, relocation when flanked (not built), crew pack-up, tube destruction by players, dedicated-server run.
