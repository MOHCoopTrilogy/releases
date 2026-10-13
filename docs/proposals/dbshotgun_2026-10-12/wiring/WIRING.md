# Wiring the double-barrel shotgun into the mod - option A, as PATCH SCRIPTS (run in the overlay, not applied to the mod)

The earlier text of this file (options A-E, line numbers read off the mod tree) is superseded by the scripts below;
each carries the exact list of what it changes in its header and refuses to run when an anchor is not found once.

| Script | For | Check |
|---|---|---|
| `patch_wiring_dbs.py --check <mod root>` / `--apply` | the armory switch on the trench gun's page, the name-bus token ` ,db1` / ` ,db0`, the swap in `loadout_finResolve`, the join replay, the two item lists, `coop_dbShotgun`, 74 loadout pages, 4 new cfgs | passes on the mod tree (85 files) and on the installed mod (the overlay is built from the installed files) |
| `patch_wiring_dbs.patch_gen_loadout(text)` | `docs/tools/gen_loadout.py` - so regenerating the pages emits the same lines | compiles; not run into the mod tree |
| `patch_torso_dbs.py <player_Torso.st> [--check]` | third-person rows without the pump stroke, the aimed second barrel | passes on the mod tree and on the installed file; run in every overlay since run rn |
| `patch_cgame_loot_dbs.py <engine worktree>` | the loot picture row and the full-name lookup | applied on `dbshotgun-next`, built (cgame_dbs7 / 8) |

After `--apply`: (1) update the `ui/coop_loadout.urc` checksum in `docs/tools/check_mp_isolation.py` (that file has
no generator); (2) apply `patch_gen_loadout()` to `docs/tools/gen_loadout.py`; (3) re-run the recoil table extractor
(`coop_mod/recoil_table.txt` is generated from the tik's viewkick); (4) append the two rows files (README sec. 10).

Rules as built: the switch is per player, default OFF (the trench gun stays the trench gun until a player switches);
`coop_dbShotgun` (seta 1) is the server's master switch - at 0 the pick is ignored and the player is told so; the
double barrel replaces the trench gun AND any finish / variant picked for it; the trench gun's own unlock still
applies (a locked trench gun cannot be put in the slot, so the switch has nothing to act on).

World: a player's death drop spawns the held tik (log `DEATHDROP ... coop_dbshotgun.tik`, seen) and is picked up by
TOUCH, like every player drop. USE-TO-LOOT is the engine's rule for guns an AI dropped (`m_bCoopUseLoot`, by who
dropped it, not by which gun): no AI carries this gun today, so its prompt was not seen. Its picture
(`w_dbshotgun.tga`) and row are in place for the day a map hands the gun to an AI.

Not done here: an own armory tile, unlock requirement, finish set (not part of option A).

KNOWN DEFECT (README sec. 8): the pick is NOT restored after a map change - the replay sent from `loadout_resend` is lost when it is sent before the first spawn (runs w3-w7); sent by hand after the spawn it lands. To fix: send it from the spawn-kit site.
