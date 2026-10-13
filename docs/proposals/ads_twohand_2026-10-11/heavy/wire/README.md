# Wiring the iron-sight FG 42 ("FG 42 Irons") - STAGED through the generators, nothing applied

User, 2026-10-13: an iron-sight FG 42 as a new weapon beside the scoped one; "all of these new guns will need their
camo/variants too"; "the new guns will also need unlock paths too (refer to how we do this already)". Its OWN armory
entry (the G 43 Irons decision). Made by `stage_armory_fg42irons.py` - the rifle lane's generator-based recipe
(`..\..\rifles\wire\stage_armory_gen.py`, used as a library): the sources a person authors are edited in a SCRATCH
copy of the repo, the mod's own generators run there as copies (two of them patched), and only what differs from the
same run on the untouched tree is staged. `unlockreq_gen.scr`, `loadoutskins_base.scr`, the `roster_ids` block and
the `ui/loadout` pages are never written by hand.

## What to apply, in this order
| step | what | file here |
|---|---|---|
| 1 | game files: 16 tiks (8 irons + 8 scoped), 2 meshes, sight shader + texture, gun clip, aim pose, 6 hands clips | `../assets/` except `coop_mod/` and `models/player/base/` (same paths) |
| 2 | the hands rows (2 `fg42_*`, 7 `coopr_fg_42_irons_*`) | `../tools/stage_rows.py` writes `../assets/models/player/base/fps_anims_mg.txt` |
| 3 | torso state row - WITHOUT IT the irons' reload takes the class default torso row | `patch_fg42irons_state.py <tree>` (a patch: the lane's staged state file is the shotgun's) |
| 4 | generator patches (`armory_unlocks.py` honours `HZM_MOD` - identical to the rifle lane's; `gen_service_record.py` REWARD_NAMES "FG 42 (Iron Sights)") + the TSV row | `gen/generators.patch` |
| 5 | the armory entry: 17 mod-tree files changed | `gen/armory_fg42irons.patch` |
| 6 | the armory entry: 12 new files (`ui/loadout/p79 t79 w79_s1 w79_s2 req79 finp79_1..7 .cfg`) | `gen/new/` |
| 7 | regenerate and check (must reproduce steps 5 / 6) | `python docs/tools/gen_loadout.py build`, `gen_skinbase.py`, `armory_unlocks.py --emit`, `gen_loadout.py check` |
| 8 | the cgame: `ads-heavy-next` (weapon name, 8 sight rows, per-weapon aim / reload rows, the long reload row) | engine worktree `C:\mohaa-coop-dev\openmohaa-hzm-ads-heavy` |

The patches are against the mod tree AS IT IS on 2026-10-13, WITHOUT the G 43 Irons (id 78). Both guns edit the
roster count, the `lktab` files and a tile list: apply one, then RE-RUN the other's script (every anchor is a name
and is asserted). `gen/report.txt` = the run's log: 19 files changed, 12 new, 0 overlay files whose mod-tree original
differs from the released pak; one generated file already drifts in the tree (`unlockreq_gen.scr`, not staged).

## The entry
* Roster id **79**, give `models/weapons/coop_fg42_irons.tik`, tile **"FG 42 (IRON SIGHTS)"** on the HEAVY tab
  directly above the scoped FG 42 (the list is in unlock order; the rows from "FG 42" down move 19 px lower), slot /
  ammo / class as the scoped FG 42 (primary, rifle ammunition 70, heavy). Description "7.92MM / AUTOMATIC / IRON
  SIGHTS" (with "AUTOMATIC RIFLE" the line was cut on both sides, run hj34). Bars DMG 10 / RPM 9 (the FG 42's), ACC 8 /
  MOB 6 (the BAR's: the tik carries the BAR's accuracy and movement rows).
* **Unlock: RANK 18** (Major General, 260000 XP in the test install), `coop_mod/xp.scr` `coop_xp_rankUnlockCnt[18]`
  0 -> 1 and `coop_xp_rankUnlock[18][0]`; the generator emits "Reach rank 18". The scoped FG 42 stays rank 19. Rank 18
  already grants a glove and three uniforms (appended further down the file; untouched).
* **Finishes**: fid 1-7 -> the 7 staged finish tiks (`coop_skinGive`, + the generated reverse map). **How they
  unlock: fid 1-7 are GLOBAL, not per gun** - `challenges.scr` `fin_gold` (250 kills), `fin_chrome` (a mission with
  no deaths), `fin_blued` (150 headshots), `fin_bloody` (150 melee kills), `fin_woodland` / `fin_winter` /
  `fin_desert` (150 kills in the US campaign / on snow maps / in North Africa) put `finish_<key>` into the player's
  unlock store; `loadoutpick.scr::loadout_finish` asks only `loadout_finUnlocked <fid>` and for a `coop_skinGive`
  row of the slot's gun. So the irons' finishes are unlocked exactly when the scoped FG 42's are. (The scoped FG 42
  has no kill counter of its own in `challenges.scr` and no model variants; neither has the irons.)
* Recoil: the 8 rows of `recoil_table_fg42irons.txt` appended to `coop_mod/recoil_table.txt`.
* `coop_mod/itemhandler.scr`: the base tik added to the two lists the scoped FG 42 is in;
  `ubermode/get_player_weaponclass.scr` ("rifle"), `coop_mod/buildmode_catalog.scr`, `global/giveall.scr`: one row each.
* No ammo HUD menu file: the scoped FG 42 has none either (`ui/hud_ammo_*` has no FG 42 entry).

## Run (hj34 full, hj38 = the menu steps again after two fixes; `../tools/run_unlock_h.py`, lock gate ARMED)
Overlay = the reload overlay + `../armory_ov/` + a measure-only probe script. Rank 0 as found: tile locked with its
padlock, "UNLOCK: Rank: Major General", a click is refused (`coop_lo1` stays empty). One award under rank 18 (rank
flag 17, 259992 XP): still locked. A REAL `xp_award` of 10 kills: "Promoted: Major General", `loadout_isUnlocked` 1
for the irons and 0 for the scoped FG 42, the padlock is gone, the click puts it in PRIMARY 1 (`coop_lo1` 79). The
map again: spawns holding it. Winter finish: `loadout_finUnlocked 6` is 0; after 150 kills on the snow-map counter
(`chal_bump "kill_snow"` - the call the kill hook makes; "Challenge complete") it is 1, the finish is applied and
after a second map restart the player spawns with the Winter gun. The test player's save files were put back as
found. Stills: `../evidence/fg42/fg42irons_armory_tile_hj38.jpg`, `fg42irons_unlock_path_hj34_hj38.jpg`.
Two defects found by the run and fixed in the script: the tile had NO padlock (its `vstr coop_loLkA79` was written
into `lktab0.cfg`, the rifle tab's file - it belongs in the tile's own tab file, `lktab3.cfg`); the description line
was cut.
NOT tested: that a click on a LOCKED finish is refused (the client cvar kept 6 and the server logs nothing - the
gate is the mod's own and not new); the other six finishes' challenges; the Service Record row (generator patched,
not run); a second client / dedicated server; the MP armory.

## NOT staged (each is a row keyed on the NAME "FG 42" or on `fg42.tik` that the new weapon does not have)
* loot-feed picture (`cg_coopfeed_loot.h` matches the exact name), the MP armory (`gen_mp_armory.py`),
  `coop_mod/developer.scr`'s list, AI use, a kill statistic / challenges of its own;
* the scoped FG 42's ACC bar is 0 in the TSV (an empty bar on its panel today) - not touched.
