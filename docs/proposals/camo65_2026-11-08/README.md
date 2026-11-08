# v1.10.65 camo65: the standard finishes on every Armory gun (2026-11-08)

Mod branch `camo65` (off hotfix-1.10.53 4f626b47). No engine change. The wpnfix pak grows (496 members): build it into the base
checkout at integration (`python docs/tools/gen_wpnfix_pak.py build`).

## Audit (76 Armory guns)

Before: 43 guns had all seven finishes (gold, chrome, blued, bloody, woodland, winter, desert); **33 had none**. Every gun had
either 0 or 7. The 33:

| | guns |
|---|---|
| rifles / snipers (11) | M1 Carbine, Springfield M1903 (unscoped), Arisaka Type 99, M1 Garand Silenced, M1 Garand Scoped, Lee-Enfield Sniper, Carcano Sniper, Arisaka Sniper, Mosin Sniper, Mosin Sniper Silenced, Kar98k Sniper Silenced |
| SMGs (6) | MP40 Silenced, PPS-43 Silenced, M3 Grease Gun, M3 Grease Silenced, Type 100, StG 44 Scoped |
| heavy (3) | M1919 .30 Cal, MG42, Lewis Gun |
| pistols (7) | Colt M1911 Silenced, Walther P38 Silenced, Beretta Silenced, Luger P08, Luger P08 Silenced, Walther PPK, Nambu Type 14 |
| grenades (6) | M2 Frag, Stielhandgranate, Mills Bomb, Breda Mod.35, M18 Smoke, Nebelhandgranate - **not done, see below** |

Why they were missed: their shipped tik is the game's own or an out-of-band pak's copy (stress / scopeglass / wpnfix), never the
mod tree, and `gen_skins.py build` only walks the mod tree.

**Model variants** cannot carry a finish: a slot holds ONE fid (1-7 finish, 8+ variant, `coop_loFin<slot>`), so "variant + camo"
needs a new per-slot state, a second chip strip and a 2-D tik matrix (81 variants x 7). Not done; say if wanted.

**Grenades - not finished, by judgement:** the thrown grenade is a separate projectile model, so a gold or woodland grenade would
turn back to stock the moment it leaves the hand; and the two smoke grenades have no kill stat, so their finishes could never be
earned. Painted (olive / sand / winter) frags would be historically sound once the projectile models are skinned too.

## What was done

27 guns x 7 = **189 finishes** (`gen_skins.py add <stems> write`, multi-gun mode):
- derived from the load-order WINNER (wpnfix source > coop paks > retail), so a finish plays the same animations as the gun;
- a texture another gun already finishes reuses that shader (silenced twins, shared suppressor / scope / mount sheets): same look,
  no second bake; sights shared by 3+ guns stay stock as in `build`;
- the base is the diffuse stage - the first `tcGen environment`-free stage (Soares93's `s93_*` shaders open with a gloss layer);
- bakes use the SHIPPED camo/blood functions (not the staged CC0 pass), at >= 256 px for tiny sheets;
- tiks + 212 bakes ship in the wpnfix pak, shader blocks in `scripts/coop_skins.shader`.

Unlocks: the per-gun finish ladders (`finish_challenges.py`, restored to main from the killchal commit) gain 13 kill stats / 91
challenges (25 -> 500 kills with that gun), seeded from the kills a profile already has. Guns that share a stat with a finished gun
(silenced twins, scoped twins) ride that gun's ladder - anyone with the MP40's gold has the silenced MP40's. They sit after the
Service Record rows, so the SR is unchanged (447). Four models counted kills nowhere and now do: M1 Carbine (own stat), silenced
Colt (Colt), the BAR's M1918/A1/A2 variants (BAR), Lewis gun (own stat).

Not done: the reload-magazine prop of the 27 guns stays stock during a reload (`gen_clip_skins.py` maps only the existing guns'
clips).

Gold / chrome / blued are shader tints over the whole diffuse, as on every existing finish: on a wood-stocked gun the stock reads
as tinted wood, exactly like the shipped M1 Garand / Kar98k / Enfield / Mosin golds (`media/existing_vs_new_wood_guns.jpg`).
Making gold read as metal on wood guns needs a wood/metal mask per sheet - a roster-wide change, not done here. The retail
suppressor sheet (`colt45s2`) stays stock under camo / blood (its bake read as a dark smear on the can).

## QA (private client, DISPLAY2, 0 Script Errors every run)

* viewer contact sheets of all 189 new finishes: `media/new_finishes_1..3_*.jpg`
* coop m2l1, equip + fire + reload (`media/ingame_fire.jpg`): MG42 GOLD (111 shots), M1 Carbine WOODLAND, Walther PPK CHROME,
  Lewis DESERT (82), Type 100 BLUED (60) - each "finish applied"
* gates: gen_loadout check EXACT, gen_lktab EXACT, gen_weapon_viewer 0 stale, finish_challenges --check EXACT, gen_wpnfix_pak OK,
  check_mp_isolation 22/0, tik-surfaces clean, Service Record unchanged (447)
