# Stealth / disguise on m2l2a — how it actually works, and what a real stealth route needs

**2026-08-08.** Written after four failed attempts at a "papers in hand, unarmed until it goes loud"
mode on the U-boat pens. Every attempt broke the mission in a different way. This is the system
mapped properly so the next attempt is designed rather than guessed.

---

## 1. The three flags, and why they are not interchangeable

This is the thing that caused every failure. There are **three** disguise flags and they mean
different things:

| Flag | Meaning | Written by |
|---|---|---|
| `has_disguise` | engine-side: the player wears an enemy uniform | `giveUniformToPlayer`, engine |
| `flags["coop_hasDisguise"]` | mod-side: this player is *entitled* to a disguise | `itemhandler.scr` on uniform pickup |
| `flags["coop_isDisguised"]` | **mod-side: the AI cannot see through it right now** | `setIsDisguised` — one site only |

**`coop_isDisguised` is the only one AI detection reads.** `aihandler.scr::canseeUndisguisedPlayers`
tests `!local.player.flags["coop_isDisguised"]`, and every disguise anim
(`disguise_papers`, `disguise_salute`, `disguise_accept`) calls that before deciding to attack.

`setIsDisguised` has exactly one write site (`itemhandler.scr:2301`) and it is **gated**:

```
if (local.player.flags["coop_hasDisguise"] || local.forceState){
    local.player.flags["coop_isDisguised"] = local.bool
}
```

So setting it before the uniform is granted silently does nothing unless `forceState` is passed.

## 2. What actually drives it: weapon state transitions

`setIsDisguised` is called from four places, and the two that matter at runtime are in
`weaponstate.scr`, driven by the **state file** (`.st`):

- `RAISE_WEAPON` -> `setIsDisguised (coop_activeWeapon == NULL)` — a Weapon in hand clears it
- `PUTAWAY_MAIN` -> `setIsDisguised true` — holstering restores it

`returnActiveWeapon` deliberately returns NULL for non-weapons, so **holding papers does not break
the disguise** (`main.scr:1011` states this explicitly: `is_disguised` only trips on a held Weapon).

**The trap this creates:** the disguised state only ever becomes true as a *side effect* of holstering
a weapon. A player who never holds a weapon never fires either transition. Same shape as the
`coop_activeWeapon` NIL bug (bug-1603): state that is only established as a by-product of a code path
you have deliberately skipped.

**Both failures so far are this one trap:**

- **bug-1604** — `takeall` stripped the uniform, so `coop_hasDisguise` was false and `setIsDisguised`
  no-oped even when called.
- **bug-1606** — stripping weapons by class is not a holster, so a player who had raised a gun before
  putting the uniform on stayed flagged undisguised, with no weapon left to holster and therefore no
  way to ever clear it. Fixed by re-asserting `setIsDisguised true true` (forceState) after the strip.

## 3. m2l2a specifics

- **No guard on this map ever asks for papers.** Every `type_disguise` is `"none"` or `"salute"`
  (m2l2a.scr:194-196, 652-653, 688-689, 804-805, 831-833). `anim/disguise_papers.scr` — the sole
  caller of `enableClickablePapers` — therefore never runs here. The only map where a guard genuinely
  asks is e1l3.
- **The "papers" the mission talks about are a GATE, not an interrogation.** `$papers2hint`
  (m2l2a.scr:225-229) prints *"You need a new set of papers to procede past this point"* — it tests
  whether you hold `papers_level2`, obtained at `papers2pickup` (:386-390, which swaps level1 for
  level2). Easy to misread as being asked to show them.
- **Cover is blown by the ALARM**, not by being seen: `global/alarm_system.scr:666` is what calls
  `takeAllDisguises`. Being merely shot at raises no alarm, which is why an arm-on-blown hook tied
  only to that path leaves players unarmed in a firefight (bug-1604).

## 4. The working precedent: e1l3

`maps/e1l3/FinalEscape.scr:703-735` is a **complete, shipped, working** papers-only stealth route:

```
level.coop_e1l3RestoreWeapons = <snapshot of level.coop_weaponLoadout>
<take each weapon by MODEL>
level.coop_noWeapon         = game.true   // managePlayerInventory early-exits: no weapon ever granted
level.coop_forcePapersEquip = game.true   // papers drawn in-hand on every spawn
thread coop_mod/replace.scr::item "models/items/papers.tik" 0
waitthread coop_mod/itemhandler.scr::givePapersFlagToAll "models/items/papers.tik"
```

and `courtyard.scr:148-158` reverses it on blow: clears both flags, restores from the snapshot.

**`coop_noWeapon` is the right mechanism** because it stops weapons being *granted* (four gates:
`itemhandler.scr` :711, :1452, :1487, :1613) rather than taking them away afterwards — so nothing is
ever removed and the uniform survives. `takeall` was the wrong tool and caused bug-1604.

Its one gap for m2l2a: e1l3 takes weapons by **model name**, viable only because its loadout is
fixed. m2l2a's armory can issue any of 69 guns, so the strip must go by **class** — the nine classes
`isWeaponClass` recognises (pistol, heavy, mg, shotgun, rifle, smg, landmine, grenade, agrenade) are
the complete set.

## 5. What a real stealth route on m2l2a needs

1. **Assert `coop_isDisguised` explicitly** at every point the player's weapon state changes outside
   a holster: uniform pickup, weapon strip, respawn, late join. Never rely on the `.st` transition.
2. **`coop_noWeapon` + `coop_forcePapersEquip`** for the papers-in-hand, no-gun state.
3. **Strip already-held weapons by class**, then re-assert the disguise (point 1).
4. **Three independent ways back to armed**, because only the first exists today:
   - the alarm (`takeAllDisguises` -> `coop_armOnBlown`) — works
   - **any player taking damage** — the `coop_stealthArmOnHurt` watchdog
   - **any player firing deliberately** — going loud on purpose, not yet built
5. **Do not gate progression on stealth.** The level-2 papers gate is a normal objective and should
   stay; failing stealth must cost the disguise, never the mission.

## 6. Open question worth settling before the next attempt

`canseeUndisguisedPlayers` returns true if **any** player is undisguised, and the caller then attacks
`self.enemy` — which may be a *different*, still-disguised player. In a four-player squad one
careless man therefore blows it for everyone, and the guard attacks whoever he happened to be looking
at. That is arguably correct (you are a group), but it is not what the per-player flags imply, and it
should be a deliberate decision rather than an accident of the loop.

## 7. Verification method

Static reading found none of these; each was caught by a live probe. Use rcon rather than shipping a
theory:

```
python rcon.py "coop_stealthStart"
python rcon.py "viewpos"
```

and watch `qconsole.log` for `^~^~^ STEALTH`. The blueprint bug took three guesses and one
instrumented run; the instrumented run is what solved it.
