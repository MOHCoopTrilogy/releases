# AI-manned weapon emplacements for build mode

Research pass, read-only. Question: beyond `mg_nest_manned`, which trilogy emplacements can we
add to `coop_mod/bunker.scr` as **buildable, AI-crewed, actually-firing** placements?

Reference implementation: `hzm-mohaa-coop-mod/coop_mod/bunker.scr:339` (`mg_nest_manned`).

---

## Scan provenance

Every number below came from a scan that opened files. Proof of work:

| scan | opened | result |
|---|---|---|
| BSP entity dumps | **54** of 54 `map_entities/*_entities.txt` | **94,678** entity blocks parsed |
| actors with a `turret` key | — | **46** across 13 maps |
| retail pak archives | **41** (`G:\mohaa-gl2\{maintt,main,mainta}`, 3 `co-op_hzm` paks excluded) | **139** emplacement/turret `.tik` read for server `classname` |
| script drivers | `global/*.scr` + `maps/**/*.scr` targeted reads | 5 distinct crewing drivers found |
| engine | `weapturret.cpp`, `actor.cpp`, `actor.h`, `actor_turret.cpp`, `Entities.cpp` | class + think semantics confirmed |

The excluded paks were `zzzzzz_co-op_hzm_mod_assets_snd.pk3`, `..._assets_tex.pk3`, `..._code.pk3`.

---

## The one correction that reframes everything

`type_attack "turret"` is **not** a mounted-turret think. `THINK_TURRET` is enum index 1 in
`code/fgame/actor.h:351`, mapped to `STRING_TURRET` at `code/fgame/actor.cpp:2802`, and
`Actor::Begin_Turret` (`code/fgame/actor_turret.cpp:220`) just does
`TransitionState(ACTOR_STATE_TURRET_COVER_INSTEAD)` — it is the **ordinary hold-a-post ranged
combat** think that nearly every stock rifleman ships with. Do not read `"type_attack" "turret"`
in a BSP block as evidence of a manned gun. `STRING_MACHINEGUNNER` (index 17) is the only think
that mounts a `TurretGun`.

This is why the honest count of BSP-crewed guns is small: of the 94,678 entity blocks, only
**46** actors carry a real `turret` key, and they resolve to exactly **two** models —
`statweapons/mg42_gun.tik` (40) and `statweapons/mg42_gun_fake.tik` (6). Everything else that
gets AI-crewed in the trilogy is crewed **by script**, not by the BSP.

---

## Ranked table

Difficulty is measured against our shipped MG42 recipe: **same** = spawn TurretGun + machinegunner
actor + `startyaw` + thread an existing driver. **needs-work** = a driver or crew-anim rig must be
written. **blocked** = no path to a firing AI emplacement.

| # | Weapon | Model / server `classname` | AI-crewed in a shipped map? | Driver | Crew think | Crew size | Difficulty |
|---|---|---|---|---|---|---|---|
| 1 | **MG42 nest** | `statweapons/mg42_gun.tik` — **TurretGun** | Yes, 40 BSP bindings, 12 maps | `global/mg42_active.scr::mg42` (59 call sites) / `global/turret.scr::mg42_start` / `global/mg42init.scr::AttachGuyToMG42` | `machinegunner` ×4 | 1 (+ optional spotter) | **SHIPPED** |
| 2 | **Allied .30 cal** | `statweapons/30cal.tik` — **TurretGun** | **Yes — 12 guns in e3l4**, crewed by Rangers | `global/mg42init.scr::AttachGuyToMG42` | `machinegunner` ×4 (set by driver) | 1 | **same** |
| 3 | **Italian Breda** | `statweapons/it_w_breda_gun.tik` — **TurretGun** | **Yes — e2l3 BattleHouse**, 2 gunners | `global/mg42init.scr::AttachGuyToMG42` | `machinegunner` ×4 (set by driver) | 1 (+ respawning parade gunner) | **same** |
| 4 | MG42 nest + searchlight | `mg42_gun.tik` + `miscobj/searchlight*.tik` (`animate`) | Yes — the MG half; light is scenery | `global/spotlight.scr::spotwatch` | `machinegunner` ×4 | 1 gunner + 1 light | **same** (it *is* #1, plus a prop) |
| 5 | MG42 "fake" nest | `statweapons/mg42_gun_fake.tik` — **TurretGun**, `spawnflags 1` | Yes — 6 in m3l1a | same as #1 | `machinegunner` ×4 | 1 | **same**, but see note — fires **no real bullets** |
| 6 | **Nebelwerfer battery** | `statweapons/P_nebelwerfer.tik` (**FixedTurret**) + `p_nebelwerfer_cannon.tik` (**VehicleTurretGun**) + `ProjectileGenerator_Heavy` | **Yes — t2l1, 4 launchers**, one crewman each | map-local `maps/t2l1.scr::nebellerThink` + `global/turret.scr::playerturret_proj_think_aim` | *not* machinegunner — `type_attack "cover"`, AI toggles a projgen | 1 | **needs-work** (port the t2l1 think into `bunker.scr`) |
| 7 | Flak 88 (animated crew) | `statweapons/flak88turret.tik` (**VehicleTurretGun**) + `flak88base.tik` (`animate`) | Partly — `global/turret.scr::flak88_start` spawns a 2-man crew, driven off the literal targetname `$flak88` (only m5l3 has one) | `global/turret.scr::flak88_start` (auto-run via `global/auto.scr:22`) | none — crew is `disable_ai` + hand-played `88_aimer_*` / `88_loader_*` anims | 2 (aimer + loader) | **needs-work** — cosmetic crew, damage is a scripted `radiusdamage`, and the name `$flak88` is a global singleton |
| 8 | Nebelwerfer (AA-era) | `statweapons/nebelwerfer.tik` — `animate` | No crew ships; trigger-driven only | `global/turret.scr::turret_start` → `turret_think` → `fire_turret` | n/a (optional `$nebeller` bystander) | 0–1 | **needs-work** — spline-faked rocket, entirely scripted |
| 9 | 20mm / quad flak | `statweapons/20mmflak.tik`, `20mmflak_w.tik` — `animate` | **No.** 6 BSP placements, all pure scenery | none | — | 0 | **blocked** — `animate`, not a turret; no weapon, no driver |
| 10 | Flak 88 (player emplacement) | `statweapons/P_flak88.tik` (**FixedTurret**) + `p_flak88_cannon.tik` (**VehicleTurretGun**) | Cosmetically — e2l1 `FlakGunSetup`/`StartAAGun` | `maps/e2l1/aaguns.scr` | none — crew is `disable_ai`+`physics_off`+`notsolid` glued to `tag_seat` | 3 (guy1/2/3) | **needs-work**, low value — see "fake fire" note |
| 11 | 20mm AA gun (player) | `statweapons/P_aagun_base.tik` (**FixedTurret**) + `p_aagun_cannon.tik` (**VehicleTurretGun**) | Cosmetically — same e2l1 rig | `maps/e2l1/aaguns.scr::AAGunFire` | none | 1 driver | **needs-work**, low value — fires by playing `anim fire_1..4` |
| 12 | Granatwerfer (mortar) | `P_granatwerfer_base.tik` (**FixedTurret**) + `_cannon.tik` (**VehicleTurretGun**) | **No.** 14 BSP placements, all player-usable | none found — only `cache` lines in `*_precache.scr` and `maps/t2l3.scr:116` collision setup | — | 0 | **blocked-ish** — no driver exists anywhere; would be written from scratch |
| 13 | Böhler AT gun | `statweapons/p_bohler.tik` (**FixedTurret**) + `p_bohler_cannon.tik` | **No** — the e1l2 crew *services* the gun; the gun is player-usable | `maps/e1l2/bohler.scr::initGun` | crew has `gun "none"` + `crewThink`; not machinegunner | 2 (crew1 + backup) | **needs-work** — map-hardcoded to `$bohler*` names |
| 14 | 15cm cannon | `statweapons/ax_w_15cm.tik` (**FixedTurret**) + `ax_w_15cm_cannon.tik` | **No** — player-only, "cannonguys" are foot defenders | `maps/e1l2/Artillery.scr::InitGun` | — | 0 | **blocked** as a manned gun |
| 15 | Modello 37 | `p_usemodello37.tik` (**FixedTurret**) + `_cannon.tik` | **No** — player-only | `maps/e3l2/cannons.scr::InitACannon` | — | 0 | **blocked** as a manned gun |
| 16 | MG42 bipod | `mg42_bipod.tik` (`object`), `mg42_bipod_nonstatic.tik` (`animate`) | No — 11 BSP placements, scenery | none | — | 0 | **blocked** — not a weapon class |
| 17 | Breda bipod | `it_w_breda_bipod.tik` — `scriptmodel` | No — 4 placements, scenery | none | — | 0 | **blocked** — but see #3, it is the *prop half* of the Breda |
| 18 | Searchlight | `miscobj/searchlight*.tik`, `animate/searchlight*.tik` — `animate`/`object` | No — never a weapon | `global/spotlight.scr` | — | 0 | **blocked** as a weapon; useful as #4's companion |
| 19 | K5 railgun | `weapons/it_w_k5.tik` — **Vehicle** | No — set piece | none | — | 0 | **blocked** |

### Never-crewed assets that exist in the paks ("free content" shelf)

Read out of the 139 tiks, cross-checked against the 46 BSP crew bindings — these are emplacement
assets that **no shipped map ever puts an AI on**:

- `statweapons/howitzer.tik` (`animate`) — a full howitzer model, **zero** BSP placements in all 54 dumps. Pure unused scenery; no driver would work without writing one.
- `statweapons/15cmcannon.tik` / `15cmcannon_d.tik` (`animate`) — used only as a *model swap* on `turretweapon_german_88mmflakturret` in t1l3. No crew, no driver.
- `statweapons/granwerf_ammcon_cannon.tik` (**VehicleTurretGun**) — an ammo-conveyor granatwerfer variant with no base and no map placement.
- `statweapons/p_flak88_s.tik` / `p_flak88_cannon_s.tik` (**FixedTurret**/**VehicleTurretGun**) — the "small" flak 88 pair, exactly 1 placement (t-series), never crewed.
- `statweapons/aagun_lowcount.tik`, `flak88_lowcount.tik` — LOD-only, no classname block at all.
- `statweapons/it_w_breda_gun_viewmodel.tik` — **TurretGun** class on a viewmodel; do not spawn.
- `statweapons/camera_restrict.tik` — **TurretGun** used as a camera clamp; not a weapon.

Nothing on this shelf has a driver. Every one of them is a "write the driver from scratch" job,
which puts them all below #6 in value.

---

## What a `bunker.scr` builder needs, per top candidate

### 1. `mg_nest_30cal` — Allied .30 cal nest (**recommended first**)

**Proof it is AI-crewed:** `maps/e3l4/Tower.scr:122`

```
$radiomg1 thread global/mg42init.scr::AttachGuyToMG42 $radiomgguy1 NIL 1
```

`$radiomg1` is `map_entities/e3l4_entities.txt:545` —
`"classname" "addon_turretweapon_allied_30cal-3rdperson"`, `"model" "statweapons/30cal.tik"`.
`$radiomgguy1` is `e3l4_entities.txt:1098` — `"classname" "ai_allied_1st-ranger_private"`.
Eleven more of these: `maps/e3l4/Bunker1.scr:170-172`, `Bunker2.scr:59,64,146,147,360,515,628`,
`Bunker3.scr:122,123`, all onto `addon_turretweapon_allied_30cal-3rdperson` entities at
`e3l4_entities.txt:556,575,584,8830,8840,8859,8869,8879,8889,9193,9272`.

**Class:** `models/statweapons/30cal.tik` → `classname TurretGun`, `weapontype mg`,
`name ".30 Cal"`, **`weapongroup mg42`** — it shares the MG42 AI animation group, which is why the
machinegunner think drives it unmodified.

**What the builder does — identical to `mg_nest_manned` with three substitutions:**

1. `spawn "models/statweapons/30cal.tik"` instead of `mg42_gun.tik`. Note the tik has
   `surface material2 +nodraw` and `scale 0.52` in setup, same as MG42 — no scale fixups needed.
2. Keep the whole rest of the recipe verbatim: `pitchCaps` via subtraction (never a bare
   negative literal), `startyaw local.yaw` **after** setting `.angles`
   (`weapturret.cpp:548` captures `m_fStartYaw = angles[1]` at placement), all four
   `type_*` = `"machinegunner"`, and the `<turret>` / `<turret>_gunner` targetname convention.
3. Choose the driver. Two work:
   - `global/mg42_active.scr::mg42 <range>` — what we already thread. Needs the
     `_gunner` targetname convention; also gives free reload cycling and an optional
     `<turret>_spotter` (`global/mg42_active.scr:65,70`).
   - `global/mg42init.scr::AttachGuyToMG42 <guy> NIL 1` — what e3l4 itself uses. The `1` is
     `auto_reattach`, and `gunner_auto_reattach_thread` (`global/mg42init.scr:149`) re-mounts
     the gunner every frame he wanders off. That is strictly better behaviour for a
     drop-anywhere nest than our current one-shot mount. **Consider switching the existing
     `mg_nest_manned` to it too**, or threading both.

**Crew:** 1. Pick the side deliberately — e3l4 crews these with *Allied* rangers, so an
`mg_nest_30cal` reads naturally as a **friendly** emplacement. If you want it friendly, the actor
must be an allied model and the `gun` matters: `mg42init.scr:66` hardcodes `self gun "MG42"` on the
gunner, which puts a MG42 in a Ranger's hands. Either accept it (retail does), set the actor's gun
afterwards, or use `mg42_active.scr` and set `gun ".30cal Machine Gun"` yourself — e3l4 does exactly
that for the jeep gunner at `maps/e3l4/Bunker1.scr:885` (`perferredweapon ".30cal Machine Gun"`).

**Asset risk: none.** `models/statweapons/30cal.tik` is already in the build catalogue at
`coop_mod/buildmode_catalog.scr:434`, so it is already a placeable/precached prop.

---

### 2. `mg_nest_breda` — Italian Breda nest

**Proof it is AI-crewed:** `maps/e2l3/BattleHouse.scr:241`

```
$battleHouseBreda_Front thread global/mg42init.scr::AttachGuyToMG42 $battleHouseGunner_Front
```

plus `BattleHouse.scr:258` → `assignMGGunners` (`:264`), which perpetually re-crews the same gun
from `$pmBattleHouseMG_paradeguy` — a **self-replenishing nest**, the closest thing in the trilogy
to what a coop build piece wants. The BSP side: `map_entities/e2l3_entities.txt:6672`
`"classname" "addon_turretweapon_italian_breda"`, `"model" "statweapons/It_W_Breda_gun.tik"`,
`"target" "battleHouseGunner_Rear"`; the gunner block at `e2l3_entities.txt:6705-6730` is
`"classname" "addon_ai_axis_Ital_infantry"`, `"model" "human/Sc_AX_Ital_Inf.tik"`.

**Class:** `models/statweapons/it_w_breda_gun.tik` → `classname TurretGun`, `name "Breda"`,
`weapongroup mg42`. Ballistics are byte-identical to the MG42 (`bulletdamage 45`,
`firedelay 0.06`, `bulletspread 40 40`, `bulletrange 4000`).

**What the builder does:** exactly `mg_nest_30cal`, with `it_w_breda_gun.tik` and an Axis-Italian
gunner model. Pair it with `models/statweapons/it_w_breda_bipod.tik` (`scriptmodel`) as the visible
mount — that is how e2l3 stages it (`e2l3_entities.txt:6733,6740`), and both tiks are already in
the catalogue (`buildmode_catalog.scr:437,438`).

**Highest-value addition after the .30cal**, because it is a visually distinct nest for the Sicily
/ Italian theatre at literally zero new engineering.

---

### 3. `nebelwerfer_battery` — the one genuinely new mechanic

**Proof it is AI-crewed:** `maps/t2l1.scr:1063-1230`. `nebellerSpawner` (`:1063`) spawns
`models/human/german_winter_Artillery-Crew` with `"type_attack" "cover"`, gives it
`.myNebelwerfer = "nebelwerfer" + N` and `tether`s it to the launcher. `nebellerThink` (`:1161`)
holsters, `runto`s a rally node, `turnto`s the launcher, and threads `nebelwerferFiring` (`:1178`)
which plays `21G798_Tranrun` / `21G800_idle` and calls `self.myNebelwerfer TurnOn`.

**The firing entity is not a turret.** `map_entities/t2l1_entities.txt:15368` —
`"classname" "ProjectileGenerator_Heavy"`, `"$targetname" "nebelwerfer1"`,
`"projectile" "projectiles/nebelwerfersnowproj.tik"`, `"launchsound" "nebelwerfer_launch"`.
Engine class: `code/fgame/Entities.cpp:355` (`ProjectileGenerator`), `:903`
(`_Projectile`), `:1094` (`_Gun`). The player-usable model
(`P_nebelwerfer.tik` = **FixedTurret** + `p_nebelwerfer_cannon.tik` = **VehicleTurretGun**) is a
separate, purely visual entity, kept pointing at the projgen's target by
`global/turret.scr::playerturret_proj_think_aim` (`:758`), wired in `maps/t2l1.scr:108-141`.

**What a builder needs — this is the "needs-work" list:**

1. Spawn three entities, not two: the FixedTurret base `P_nebelwerfer.tik`, its
   `QueryTurretSlotEntity 0` cannon, and a `ProjectileGenerator_Heavy`. The projgen is not
   spawnable from a model path — it must be `spawn ProjectileGenerator_Heavy` with `projectile`,
   `launchsound`, `Accuracy` and spawnflags set as script fields.
2. Spawn a crewman and a rally `script_origin` in front of the launcher; port `nebellerThink` /
   `nebelwerferFiring` / `nebellerDisengaged` into `bunker.scr` as private labels. Do **not**
   call into `maps/t2l1.scr` — those labels read `$nebeller1..4` and `$nebelwerfer1..4` by
   literal name.
3. Reuse t2l1's disengage rule: the battery only fires while **no player is close**
   (`coop_mod/replace.scr::istouching`), and the crewman drops to normal AI when a player closes.
   That is what makes it a stand-off threat rather than an unkillable point-blank rocket pit.
4. Keep the aim-slaving thread (`global/turret.scr::playerturret_proj_think_aim`) so the visible
   launcher tracks — without it the model sits static while rockets come out of it.

**Payoff:** the only indirect-fire, area-denial emplacement available. Nothing else on this list
adds a new *kind* of pressure.

---

## Notes / traps worth carrying forward

- **`mg42_gun_fake.tik` fires nothing.** Its server block sets `spawnflags 1`, and
  `weapturret.cpp:422` reads `m_bFakeBullets = (spawnflags & FAKEBULLETS)`, then `:551` swaps
  `firetype[FIRE_PRIMARY] = FT_FAKEBULLET`. m3l1a uses these for the *distant* Omaha bunkers where
  the tracers are set dressing. Only build it deliberately (e.g. an atmosphere nest that cannot
  kill anyone) — otherwise it is a nest that looks armed and is not.
- **The e2l1 flak/AA "AI crew" is theatre, not combat.** `maps/e2l1/aaguns.scr:648` (`AAGunFire`)
  fires by playing `self.turret anim fire_1 … fire_4` on a 0.15s cycle, aimed at a wandering
  `script_origin` (`adjustFireDirection`, `:680`). `StartAAGun` (`:386`) makes the driver
  `disable_ai` + `physics_off` + `notsolid`, glued to `tag_seat`. Same for `FlakGunSetup` (`:948`)
  and its 3-man crew. Copying this into build mode gets you a diorama that shoots at nothing.
- **`global/turret.scr` runs on every map** — `global/auto.scr:22` execs it, and `main` (`:1`)
  scans the literal targetname arrays `$nebel`, `$nebel_trigger`, `$mg42`, `$flak88`. Any build
  piece that names its gun `mg42` or `flak88` will be **picked up by that scan**, on every map,
  and threaded through `mg42_start` / `flak88_start`. Our existing `coop_mgnest<N>` naming avoids
  this by accident; keep every new builder on a `coop_*`-prefixed name for the same reason.
- **`.turret` takes the entity.** Already recorded in `bunker.scr`, but note `global/spotlight.scr:390`
  does `self.spotter.turret = self.spotter.target` — assigning a *targetname string*. Do not copy
  that line as a pattern.
- **`bunker.scr` has no precache/cache calls at all.** New emplacement models must already be
  reachable, which for `30cal.tik`, `it_w_breda_gun.tik` and `it_w_breda_bipod.tik` they are —
  `coop_mod/buildmode_catalog.scr:434,437,438`. `P_nebelwerfer.tik` is *not* in the catalogue and
  would need checking before a battery builder ships.
- **`addon_turretweapon_german_mg42` markers are still unwired.** 49 of them across 12 SH/BT maps,
  32 with a `target`. Per bug-1481 (`global/turret.scr:59-71`) their `.target` points at an
  `info_pathnode` carrying spawn data, not at an actor, and no addon-spawn framework exists. That
  is a *separate*, larger win than build mode — building the marker→actor resolver would light up
  ~32 dormant retail nests across Spearhead/Breakthrough for free.

---

## Recommendation

Ship **#2 (.30 cal)** and **#3 (Breda)** together — they are the same code as `mg_nest_manned`
with a model string and a crew model swapped, both assets are already catalogued, and both have a
shipped map proving the exact wiring. Then take **#6 (Nebelwerfer battery)** as a real feature.
Everything from #9 down is either scenery misread as a weapon, or a driver that would have to be
invented with no retail precedent to copy — which is exactly what the project's fix methodology
says to avoid.
