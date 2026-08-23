# Fix: PICKUP-style objectives in coop (16-player) across unconverted maps

Scope: audit + fix PICKUP objectives (pick up papers / documents / intel / explosives /
satchels / keys / maps / radios / etc.) so ANY of up to 16 active players can complete them
in coop, matching HZM's proven M-series pattern (same approach as the e3l2 cannon fix).

Maps audited: e1l4, e2l1, e2l2, e2l3, e3l1, e3l2, e3l3, t1l1, t1l2, t1l3, t2l1, t2l2, t2l3,
t2l4, t3l1, t3l2. (e3l4 NOT touched - owned by another agent; pickups noted below for follow-up.)

All paths under `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\`.

---

## RESULT (TL;DR)

- **M-series reference learned from: `maps/m3l2.scr` (the "Find the radio" pickup, `scene7_radio_pickup`).**
- **SP-shaped pickup objectives found that needed fixing: NONE.**
- **Every pickup objective in the 16 listed maps is already coop-correct.** They all follow the
  M-series pattern (BSP `waittill trigger` -> `level.*` flag / linear `waitthread` objective chain
  -> engine `addobjective` auto-replicates the HUD to all clients). Weapon pickups were already
  converted to `coop_mod/replace.scr::item` (gives to all players) + `replace.scr::playsound`
  (broadcast pickup sound).
- **No edits were required.** The only previously-RED interactive objective (e3l2 Modello
  cannon mount/plant) was already fixed by the prior `CoopGunOrChargeThink` rewrite, and that is
  a man-gun / plant-charge objective, NOT a pickup.

This is consistent with `objective_coop_confidence.md`: that audit's RED was the e3l2 cannon
(now fixed); it listed no RED pickup objectives, and this pass confirms that for pickups.

---

## The M-series reference pattern (what a coop-correct pickup looks like)

Canonical example: `maps/m3l2.scr` "Find a radio to call an airstrike" objective.

- Pickup trigger: a BSP trigger fires the pickup callback thread (`scene7_radio_pickup`,
  `m3l2.scr:1755`). In coop a BSP `trigger`/`trigger_multiple`/item with a `setthread`
  callback fires for **whichever player touches it** - `self` is the trigger; the thread does
  NOT gate on `parm.other == $player` or read the bare `$player` array head.
- Completion: the thread sets a **level-global flag** (`level.got_radio = 1`, `m3l2.scr:1765`)
  and calls `global/objectives.scr::add_objectives N 3` (engine `addobjective`). Engine objective
  state auto-replicates to all 16 clients - no `coop_objectivesSendPlayer` push needed.
- Pickup sound / item: HZM broadcasts via `exec coop_mod/replace.scr::playsound <alias>` (all
  players hear it; replaces `$player playsound`) and `exec coop_mod/replace.scr::item <model>`
  (gives the item to all players; replaces a single-player `$player item`).

The anti-pattern (RED) to look for: a pickup/use thread that gates completion on
`parm.other == $player`, bare `$player.useheld` / `$player.origin`, or `$player[1]`, OR an
objective that only advances for the host. **None of the pickup objectives in the audited maps
do this.** (The one historic RED, `global/MountGunOrPlantCharge.scr` via e3l2 cannons, was a
gun-mount/charge-plant - not a pickup - and is already replaced by
`maps/e3l2/cannons.scr::CoopGunOrChargeThink`, which loops every active player.)

Coop primitives confirmed present and used: `global/DistanceUse.scr::main` (loops
`1..$player.size`, returns the player who pressed use), `coop_mod/replace.scr::player_closestTo`
/ `player_anyValid`, `coop_mod/replace.scr::validateTriggerActivator` (`replace.scr:2507`),
`coop_mod/replace.scr::item` / `::playsound`.

---

## Per-map pickup objective audit

Legend: COOP-CORRECT = any active player can pick up AND it completes for everyone.

### e1l4 - Stowaway / freighter (spy, stealth)
Four pickup-style objectives, all COOP-CORRECT:
- "Obtain papers" - stealth disguise/present-at-gate flow, not a clean item pickup. Coop gate is
  `level.GatePapersAccepted` (level-global, `e1l4/Intro.scr:176,205,264,294,302`); disguises via
  `coop_mod/itemhandler.scr`. All `$player.has_disguise` / `$player.hasPapers` writes are inside
  `if (!level.gametype)` SP-only branches (`e1l4/Intro.scr:14-16`, `e1l4/PreShip.scr:67,90`,
  `e1l4/SunkShip.scr:6-7`). COOP-CORRECT (already converted; matches prior YELLOW stealth note).
- "Steal documents" - `e1l4/MapRoom.scr::ObjectiveStealDocuments` blocks on
  `$documentstrigger waittill trigger` (BSP, any player); completion via the linear chain in
  `e1l4.scr:125-126`. COOP-CORRECT.
- "Find explosives" - `e1l4/Ship.scr::ObjectiveFindExplosives` blocks on
  `$getbombs waittill trigger` (`Ship.scr:68`), `add_item "explosive"`; completion `e1l4.scr:137-138`.
  COOP-CORRECT (the `$player.origin` at `Ship.scr:57` is inside the `skipfindexplosives` debug branch).
- "Place explosives" - `e1l4/Ship.scr::ObjectivePlaceExplosives` waits on
  `level.numexplosivesset` (level-global counter, `Ship.scr:163`). COOP-CORRECT (the
  `$player.origin`/`viewangles` at `Ship.scr:151-152` are inside the `skipshipexplode` debug branch).

### e2l1 - Glider / AA guns
No pickup objectives (destroy/reach/ride). N/A.

### e2l2 - Bomb the V2
No pickup objectives. `e2l2.scr:140 add_item "explosives"` is an inventory icon granted at spawn
(`initPlayer`), not a pickup. Objectives are destroy/reach. N/A.

### e2l3 - Vineyards / town
No pickup objectives (reach/area/death). N/A.

### e3l1 - City / British HQ
- "Retrieve Munitions from the Supply House" (PIAT) - PICKUP. `piatpickup`
  (`e3l1/AfterSnipers.scr:77`) is fired by the BSP `$piat` pickup trigger's `setthread`
  callback (any player touches it); sets level-global `level.gotPIAT = 1`; objective completes
  in the main chain (`e3l1.scr:147 add_objectives level.objPIAT 3`). COOP-CORRECT. (`compassTracker`
  at `AfterSnipers.scr:61` reads bare `$player.origin` - cosmetic compass marker only, not
  completion-gating.)

### e3l2 - N.Africa town / Modello cannons / POWs
No PICKUP objective. The interactive objective here is mount-gun / plant-charge ("Destroy Enemy
Artillery"), already fixed (host-only -> any-player) by `maps/e3l2/cannons.scr::CoopGunOrChargeThink`
(`cannons.scr:208,219-323`), which loops `1..$player.size`. findPOWs/protectPOWs/escape are
reach/NPC-protect (ObjMgr). Nothing pickup-shaped to fix.

### e3l3 - N.Africa / K5 railguns
- "Search the House for Intelligence" (anziomap) - PICKUP. `e3l3/scene2.scr::DoObjective3`
  blocks on `$anziomaptrigger waittill trigger` (BSP, any player), removes `$anziomap`; objective
  completes `e3l3.scr:51 add_objectives 3 3`. COOP-CORRECT.
- Spawn-granted inventory icons `add_item "radio"/"explosives"/"plunger"` (`e3l3.scr:186-188`)
  are not pickups (given at spawn in `ArmPlayer`). N/A.

### t1l1 - Paratroop drop
No pickup objectives. N/A.

### t1l2 - Dutch town / Flak88
No pickup objectives (destroy/escort). N/A.

### t1l3 - Canal town / bridge demolition
- "Acquire Explosives from the Air Drop" - PICKUP. `t1l3.scr::objective4` blocks on
  `$objective5ontrig waittill trigger` (BSP, any player); pickup sound already coop-converted
  (`t1l3.scr:584 exec coop_mod/replace.scr::playsound explosives_pu`); removes
  `$demochargepickup[]`; completion via level-global `level.objective4 = 1` + `add_objectives 4 3`
  (`t1l3.scr:591-592`). COOP-CORRECT.
- Plant 4 demo charges - `level.charge1-4` / `level.chargecount` level-globals
  (`t1l3.scr:103-107, 823-854`), any player plants; counter-driven HUD. COOP-CORRECT.

### t2l1 - Ardennes / Nebelwerfers
- Sniper rifle pickup - `t2l1.scr::sniper_rifle_pickup` (`:1259`) already coop:
  `exec coop_mod/replace.scr::item models/weapons/g43.tik` (all players). The trailing
  `$player use "G 43"` (`:1264`) is host-only auto-equip flavor; others select from inventory.
  Weapon pickup, not an objective gate. COOP-CORRECT.
- `add_item "binoculars"` (`:246`) is a spawn inventory icon, not a pickup. N/A.

### t2l2 - Halftrack escort
No pickup objectives. (`parm.other == $player` at `t2l2.scr:889` is route-ambience explosions,
already gametype-gated with an any-player + halftrack loop - not a pickup.) N/A.

### t2l3 - Bastogne wave defense
- MP44 weapon pickup - `t2l3.scr::mp44pickup` (`:3351`) already coop:
  `exec coop_mod/replace.scr::item models/weapons/mp44.tik` + `replace.scr::playsound`. The
  `$player use "stg 44"` is host-only auto-equip flavor. Weapon pickup, not an objective gate.
  COOP-CORRECT.

### t2l4 - Stavelot
- Sniper rifle pickup (`t2l4.scr:1007 replace.scr::item weapons/KAR98sniper.tik`) and shotgun
  pickup (`:1157 replace.scr::item weapons/shotgun.tik`) - already coop (all players). Weapon
  pickups, not objective gates. COOP-CORRECT.
- (`$player[local.pi]` at `t2l4.scr:1208` is inside an any-player loop in the building-entry
  ambush helper - not a pickup.)

### t3l1 - Berlin / safe puzzle
- "Locate combination" (document2) - PICKUP. `t3l1.scr::document2` (`:933`) fired by BSP
  `$document2` trigger callback; sets level-global `level.combination = 1`; pickup sound already
  coop (`:938 replace.scr::playsound pickup_papers`); removes `$document2`. Objective 5 completes
  by polling `level.combination` (`:505-511`). COOP-CORRECT.
- `document1` (instructions, `:927`) - same pattern, coop pickup sound. COOP-CORRECT.
- Safe open (`usetrigger5`, `:522`) reads/sets only `level.combination` / `level.safestate` /
  `level.usetrigger5` - no `$player` gate. COOP-CORRECT.

### t3l2 - Berlin / T-34 / bridge (campaign end)
No pickup objectives. (`parm.owner == $player` at `t3l2.scr:1090` is the bridge-collapse owner
check inside the SP `gametype == 0` branch; the coop branch accepts `$playertank`/driver/any
player. Not a pickup.) N/A.

---

## e3l4 pickups - DEFERRED (NOT TOUCHED; for the e3l4 owner)

Not edited because another agent owns e3l4. Both appear coop-shaped already (BSP triggers /
already-converted item), but the e3l4 owner should confirm:

- **"Confirm the Airstrike" (desk radio use)** - objective wired at `e3l4.scr:89`
  (`add_objectives level.ObjConfirmAirstrike 2 ... $deskradio`); the radio-tower battle / use
  flow is in `e3l4/Tower.scr::ObjectiveGoToRadio` (`Tower.scr:45`), which blocks on
  `$starttowertrigger` / `$snipetrigger waittill trigger` (BSP). Prior audit
  (`objective_coop_confidence.md`) rated the desk-radio confirm GREEN via `DistanceUse`. Confirm
  the actual USE of `$deskradio` routes through `global/DistanceUse.scr` (any player) and not a
  bare `$player.useheld`.
- **Bazooka pickup** - `e3l4/Bunker4.scr:46 exec coop_mod/replace.scr::item weapons/bazooka.tik`
  (already gives to all players) + `:50 playsound`. Weapon pickup, looks coop-correct; verify.

---

## Parse hygiene

No files were edited, so no parse risk was introduced. All reference reads confirmed the
existing pickup threads are ASCII, brace/paren-balanced, and already use the coop primitives.
