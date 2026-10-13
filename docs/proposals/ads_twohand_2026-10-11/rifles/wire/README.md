# Wiring the iron-sight G43 ("G 43 Irons") - STAGED, nothing applied

User decision 2026-10-13: its OWN armory entry with an early unlock, not a model variant of the scoped G43.
`wire_mv2_g43irons.patch` (variant 13 of roster id 04) is **SUPERSEDED** - kept for the record, do not apply.

## What to apply, in this order
| step | what | file here |
|---|---|---|
| 1 | game files: 12 tiks, mesh, sight shader + texture, gun clips, aim pose, aimed reload clips | `../assets/` except `coop_mod/` and `models/player/base/` (-> the mod tree / fixes pak, same paths) |
| 2 | the hands rows (5 rows `coopr_g_43_irons_*`) | `../tools/rows_rifle.py` writes `../assets/models/player/base/fps_anims_rifle.txt` from the released fixes copy |
| 3 | torso state row - WITHOUT IT THE HIP RELOAD IS BROKEN (the rifle is handed to the left hand and leaves the picture) | `player_torso_g43irons.patch` (`../tools/g43state.py`) |
| 4 | the armory entry: 14 files changed + the generator's TSV row | `armory_g43irons.patch` |
| 5 | the armory entry: 13 new files (`ui/loadout/p78 t78 w78_s1 w78_s2 req78 finp78_1..7 .cfg`, `ui/hud_ammo_G43Irons.urc`) | `armory_new/` |
| 6 | regenerate, then check | `python docs/tools/gen_loadout.py build` (rewrites the `ui/loadout/*78*` files and the `roster_ids` block from the TSV row - compare with step 5), `gen_skinbase.py`, `armory_unlocks.py`, `gen_service_record.py build`; `gen_loadout.py check` must pass (build.ps1 blocks on drift) |
| 7 | the cgame: `ads-rifle-next` 60e00829 (weapon name, sight rows, per-weapon aim / reload rows) | engine worktree `C:\mohaa-coop-dev\openmohaa-hzm-ads-rifle` |

`stage_armory_g43irons.py` makes steps 4 and 5 (re-run it when the mod tree changes; it asserts every anchor) and the
harness copies `../armory_ov/` from the RELEASED pak (`mkov_rifle.py <pk3> --armory`). On 2026-10-13 the 27 files came
out identical from the mod tree and from the released pak.

## The entry
* Roster id **78** (73 is free in coop, 76 / 77 are the MP roster's), give `models/weapons/coop_g43_irons.tik`, tile
  **"GEWEHR 43 (IRON SIGHTS)"** on the RIFLE tab between the M1 Carbine and the Kar98k (the list is in unlock order; the rows from the Kar98k down move one row lower), slot / ammo / class as the scoped
  G43 (primary, rifle, 70 rounds). The scoped one keeps "GEWEHR 43". Finish previews are named "GEWEHR 43 IRONS (GOLD)" ...
* **Unlock: RANK 2** (Technician Fifth Grade, 1200 XP), `coop_mod/xp.scr` `coop_xp_rankUnlock[2][2]`. Around it:
  M1 Garand free; M1 Carbine rank 1 (500 XP); **G 43 Irons rank 2 (1200)**, with the silenced pistol and the stick
  grenade; Kar98k rank 3 (2200); Sten + Luger rank 4 (3600); scoped Gewehr 43 rank 5 (5500, Sergeant); Lee-Enfield 7;
  Springfield 9; Carcano 10; SVT 12; Mosin 13; Arisaka 15. To move it: `RANK` / `RANK_NAME` at the top of the script.
* **Finishes**: fid 1-7 (gold, chrome, blued, bloody, woodland, winter, desert) -> the 7 staged finish tiks, with the
  generated reverse map (`loadoutskins_base.scr`). They unlock as the G43's do: the kill counter is the G43's (weapon id
  by `containsText "g43"` in `challenges.scr`), so irons kills and scoped kills count together.
* Recoil: the 12 rows of `recoil_table_g43irons.txt` appended to `coop_mod/recoil_table.txt`.
* `coop_mod/itemhandler.scr`: the base tik added to the two rifle-ammo lists.
* `ui/hud_ammo_G43Irons.urc`: the (empty) ammo HUD menu `hud_ammo_G 43 Irons` - menus are keyed by weapon name.

## Run once (rb35, private test install, overlay `ov_rifle_f1.pk3`)
Tile shows; locked for the test player (rank 0) with a lock icon and "UNLOCK: Rank: Technician Fifth Grade"; a click
while locked opens the inspect page and the pick is refused (`coop_lo1` stays empty); with the gate off
(`coop_lockLoadout 0` - the test install has no way to grant XP from the console) the lock goes, the click puts it in
PRIMARY 1 (`coop_lo1` = 78, `coop_loS1` = the tik); after a map restart the player spawns holding it; finish 6
(Winter) applies and survives a second map restart. Stills: `../evidence/g43irons/g43irons_armory_rb35.jpg`,
`g43irons_armory_tile_rb35.jpg`.
NOT tested: the rank-2 grant itself (reaching 1200 XP) - only the lock state it feeds and the requirement text;
a second client / dedicated server; the MP armory.

## NOT staged (each is a row keyed on the NAME "G 43" or on `g43.tik` that the new weapon does not have)
* the 4 pack skins (`coop_g43_irons_dhg43fleck / hobbsg43wood / hobbsg43urb / lv_ttg43.tik`): on the scoped G43 they
  are MODEL VARIANTS (fid 9-12, `wire_mv2.py`, each behind a kill challenge). For the irons they need an entry in
  `wire_mv2.py` (`("coop_g43_irons", [...], "<elite challenge id>")`) and base + elite challenges - the tiks are staged
  and unused until then;
* loot-feed picture: `cg_coopfeed_loot.h` matches the exact name "G 43" - "G 43 Irons" shows no picture (cgame row);
* its own kill statistic / challenges (it shares the G43's);
* `itemhandler.scr` grenade-count list by weapon name (`case "g 43":`), `global/weapon.scr` AI alias,
  `ubermode/get_player_weaponclass.scr`, `global/giveall.scr`, `developer.scr`, `buildmode_catalog.scr`;
* the MP armory (`gen_mp_armory.py`, `mp_armory_roster.tsv`);
* German riflemen carrying it (`coop_aiG43Chance` in `aihandler.scr` arms a share of Kar98 soldiers with `g43.tik`;
  the irons tik there would put it on the ground for pick-up) - a separate option, not staged;
* stat bars: DMG / RPM are the scoped G43's (5 / 4), ACC / MOB the M1 Garand's (8 / 10: the tik carries the Garand's accuracy and movement rows). The scoped G43's own TSV row has ACC 0 - its panel shows an empty ACC bar today (not touched).
