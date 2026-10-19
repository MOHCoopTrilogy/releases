# Direction B - "Showroom" (build note)

The inspect preview is the hero (340x176 vx plate, gun with the selected finish, name in delima-30, caliber/clip line, UNLOCKED badge).
Under it: an EQUIP INTO selector of the four slots (what each holds), then a horizontal **filmstrip** of the open category - unlocked guns
first, a LOCKED divider, then dimmed locked cards with padlock and progress line - and a "what unlocks next" ledger (nearest four, with
requirement text and %). Right column = comparison ledger: per stat a big number, a colour delta, and two stacked bars (new, equipped),
then finish swatches and EQUIP. Category strip with counts across the top.

## Stats and unlock text
Identical to Direction A (see BUILD_A.md): `tools/gen_weapon_stats.py` -> `armory_stats.json` from the `.tik` files; unlock text from
`req<id>.cfg`; rank thresholds from `xp.scr`. Mock player data (Sergeant, 6,240 XP, challenge progress, equipped guns) is sample.

## urc only
* The hero = the existing `prevC*` model Label, enabled and enlarged (340x176, `rendermodelfit 1`); finish = model swap, already wired.
* Filmstrip: ~6 fixed card widgets (model Label + name + stat line) bound to `coop_loG<n>` cvars; arrows = two Buttons that run a
  generated `strip<tab>_<page>.cfg` (page offset in a cvar), like the existing tab cfgs.
* Slot selector = the four existing slot cards re-laid as a strip (same `s<N>sel.cfg` handlers).
* Ledger rows, bars (two bgcolor-fill Labels per row, 11-step gated), padlocks, swatches: generator output. New baked bg texture for
  chrome (build-time swap).

## Needs scripting (no cgame change)
* Server pushes, per tab, the player-specific order (`coop_loOrd<tab><n>`) and the **deltas**: because the server already knows what the
  slot holds and exports lock state diff-only, it also exports `coop_loDl<r>` / `coop_loDs<r>` whenever the slot or the inspected gun
  changes (hover would add name-bus traffic; B therefore compares on **click/inspect**, not hover). The latency of one push (~100 ms) is
  already accepted for lock state.
* "What unlocks next": the same server export computes the nearest four locked items (rank thresholds from `xp.scr`, challenge progress
  from the `chal` record) and pushes `coop_loNx<n>` text + percent.

## Compared with A
B has the stronger first impression (one large gun), needs no cgame change, but compares on click rather than hover and shows fewer guns
at once (about 11 of a 13-gun tab). A shows the whole tab at a glance and compares on hover only if the cgame command is added.

Risk: low-medium; all moving parts are server exports in the existing push style.
