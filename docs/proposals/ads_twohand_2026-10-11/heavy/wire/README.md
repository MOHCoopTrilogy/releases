# Wiring the iron-sight FG 42 ("FG 42 Irons") - what is needed; ONLY the recoil rows are staged

User, 2026-10-13: an iron-sight FG 42 as a new weapon beside the scoped one; "all of these new guns will need their
camo/variants too"; "the new guns will also need unlock paths too (refer to how we do this already)". The G 43 Irons
decision applies: its OWN armory entry, not a model variant. **Follow `..\..\rifles\wire\README.md` step for step** -
`..\..\rifles\wire\stage_armory_g43irons.py` is the recipe (one set of text transforms run over the mod tree -> a patch
+ new files, and over the released pak -> the harness overlay). It is anchored on the G43's rows; an FG 42 copy of it
(`stage_armory_fg42irons.py`) is NOT written yet. The facts it needs, read from the mod tree on 2026-10-13:

| what | scoped FG 42 today | FG 42 Irons (to stage) |
|---|---|---|
| roster entry | id **39** (`docs/tools/loadout_weapons.tsv` row 39; `coop_mod/loadoutroster.scr` `roster_get` + `coop_loRosterGive[38]`), tab `heavy` (3), tile "FG 42", "7.92MM / AUTOMATIC RIFLE", hold `coop_hold_rifle` | a new id - **79** (78 = G 43 Irons, 76 / 77 = the MP roster's; check it is still free), same tab, tile **"FG 42 (IRON SIGHTS)"**, "7.92MM / AUTOMATIC RIFLE / IRON SIGHTS", placed directly above the scoped FG 42's tile (the list is in unlock order) |
| unlock rule | **rank 19**: `coop_mod/xp.scr` `coop_xp_rankUnlock[19][0]`; text "Reach rank 19" in the GENERATED `coop_mod/unlockreq_gen.scr` (`docs/tools/armory_unlocks.py --emit`, never hand-edited) | **rank 18** - the rank just before, which unlocks nothing today (`coop_xp_rankUnlockCnt[18] = 0`): `coop_xp_rankUnlock[18][0]`, count 1, and the generator emits "Reach rank 18" |
| finishes | fid 1-7 `coop_mod/loadoutskins.scr` `coop_skinGive["models/weapons/fg42.tik"][1..7]` = gold, chrome, blued, bloody, camo_woodland, camo_winter, camo_desert; reverse map `loadoutskins_base.scr` (generated, `gen_skinbase.py`); unlocked by the FG 42's kill counter in `coop_mod/challenges.scr` | the 7 staged tiks `coop_fg42_irons_<finish>.tik` under the new base tik, same fids; HOW THEY UNLOCK IS NOT FOUND YET: `coop_mod/challenges.scr` has no "fg42" text at all (the G43's finishes go by `containsText "g43"` there) - read `docs/FEATURES.md` lines 510-570 and `docs/tools/armory_unlocks.py` for the scoped FG 42's finish rule and give the irons the same one |
| Service Record | `docs/tools/gen_service_record.py` `REWARD_NAMES` | a "FG 42 (Iron Sights)" reward name for the rank-18 row |
| recoil | `coop_mod/recoil_table.txt` rows `fg42*` (8) | `recoil_table_fg42irons.txt` here (8 rows, the FG 42's values) - STAGED |
| ammo lists | `coop_mod/itemhandler.scr` two `case "models/weapons/fg42.tik":` lists | the new base tik added to both |
| ammo HUD | menus are keyed by weapon NAME | an empty `ui/hud_ammo_FG42Irons.urc` for `hud_ammo_FG 42 Irons` |
| torso state | `coop_mod/player_Torso.st` picks the reload's torso clip by weapon class / name (the FG 42 goes through `RELOAD_MG`, weapontype mg) | **NEEDED**: line 2699 of the mod tree's file reads `coop_reload_fg42 : IS_WEAPON_ACTIVE "mainhand" "FG 42"` - the reload's torso row is picked by the exact NAME, so "FG 42 Irons" falls through to the class default (the G 43 Irons did the same and the rifle left the hand, bug-3739). A one-line state patch `coop_reload_fg42 : IS_WEAPON_ACTIVE "mainhand" "FG 42 Irons"` beside it (as `..\..\rifles\wire\player_torso_g43irons.patch`; a PATCH, the file is shared). Not written, not run: the new gun's hip reload has not been run at all |
| stat bars | TSV row 39: `10 9 0 5` | DMG / RPM the FG 42's; ACC / MOB the BAR's (the tik carries the BAR's accuracy and movement rows) |
| engine | - | cgame `ads-heavy-next` (the commit named in `..\README.md`): weapon name, 8 sight rows, the per-weapon aim-pose row |

Test to run when it is staged (the rifle lane's `run_armory.py`): locked at rank < 18 with the requirement text ->
requirement met -> unlocked -> picked -> spawns with it after a map restart -> a finish applies and survives a restart
-> the Service Record shows the reward; existing unlock records keep what they had.

Not staged either (each keyed on the name "FG 42" or on `fg42.tik`): the loot-feed picture (`cg_coopfeed_loot.h`), the
MP armory (`gen_mp_armory.py`), `global/giveall.scr` / `developer.scr` / `buildmode_catalog.scr`, AI use.
