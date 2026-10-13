"""one-off (2026-10-13, third pass): rewrites README sections 8, 10, 11, 12 and adds 13, 14. Already applied."""
import re, sys
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
if '## 13. The finish set' in s:
    print('already applied'); sys.exit(0)


def cut(s, a, b):
    i = s.index(a); j = s.index(b) if b else len(s)
    return i, j


S8 = '''## 8. Armory: own entry, own unlock path - `wiring/stage_armory_dbs.py` (details: `wiring/WIRING.md`)

Roster id **80**, tile **DOUBLE BARREL** on the HEAVY tab under the TRENCH GUN, DMG 10 / RPM 3 / ACC 6 / MOB 10, 2 rounds.
**Unlock rule: challenge "Both Barrels" - Get 60 kills with the Shotgun** (`wpn_shotgun_v`, on the pump gun's existing
kill statistic; the mod's own pattern for a gun's sibling - drum Thompson, silenced MP40, scoped StG - sits between the
base and the elite kill challenge, here 30 and 90). **Finishes** unlock as the pump gun's do (the finish by its own
account-wide challenge; the gun takes finishes once `wpn_shotgun`, 30 shotgun kills, is done) - shared with the pump
gun, no statistic of its own. **Master switch** `coop_dbShotgun` (0 = tile hidden, pick refused).
Made the mod's way: sources edited in a scratch copy of the repo, then `gen_loadout.py build`, `gen_skinbase.py`,
`armory_unlocks.py --emit`, `gen_loadout.py check` (EXACT REPRODUCTION) and, for the test install, the patched
`gen_service_record.py` - as patched COPIES; `docs/tools` and the mod tree are untouched.

Run a1 (private test install, released mod + overlay `mkov_dbs.py --armory`, `coop_lockLoadout 1`, cgame_dbs8, 0 script
errors) and a2; progress was made with the mod's own `chal_bump` (the function a kill calls), not by editing a record:

| Step | Result | Checked by |
|---|---|---|
| fresh record: tile with padlock, hover text "UNLOCK: 60 kills w/ Shotgun (Both Barrels)" | yes | looked at (`dbs_armory_unlock_path.jpg` 1) |
| click while locked | inspect page only, `coop_lo1` stays empty | looked at (2) + cvar |
| an existing record (the pump gun unlocked through ITS challenge) + 59 shotgun kills | still locked (`v=59`) | log |
| the 60th kill | `models/weapons/coop_dbshotgun.tik` added to the record; the record kept everything it had (compared before / after) | log; tile without padlock looked at (3) |
| click | PRIMARY 1 = DOUBLE BARREL, `coop_lo1` = 80, server slot = the tik | looked at (4) + log |
| respawn in the map | in the kit (4 items); in the hand after `useweaponclass heavy` - the game brought up PRIMARY 2 first | looked at (5) |
| finish WINTER (its challenge + `,f16`) | "WINTER finish applied", `coop_loS1F` = 6 | log |
| map RESTART (m3l2) | spawns with the winter double barrel in the hand, slot + finish intact | looked at (6) + log |
| map CHANGE (m3l2 -> m2l1) | the same | looked at (7) + log |
| Service Record | SUPPORT WEAPONS 12/12: "Both Barrels 60/60"; baked hover "Unlocks: Double Barrel Shotgun" | page looked at in game (8); the hover picture looked at as a file - the hover itself not exercised (no mouse in the harness) |
| `coop_dbShotgun 0` | tile gone from the heavy tab (its row stays empty); after a restart "DOUBLE BARREL is switched off on this server", slot empty, spawns without it | looked at (9, 10) + log |

NOT tested: a second client / a dedicated server; the disconnected (main menu) armory; the mod TREE's newer files
(the test install runs the released mod - `player_Torso.st` in the tree has new shotgun reload states since 08:54
today, the torso patch's check passes on it but nothing was run against it); the MP armory (not wired, on purpose).

'''

S10 = '''## 10. Files for integration

* `assets/models/weapons/coop_dbshotgun.tik` + 7 finish tiks `coop_dbshotgun_{gold,chrome,blued,bloody,camo_woodland,camo_winter,camo_desert}.tik`
* `assets/models/weapons/coop_dbshotgun/` (skd + 8 gun clips)
* `assets/models/human/animation/viewmodel/coop_dbshotgun/` : 16 hand clips `dbs_*.skc`, 3 torso clips `coop_dbs_tps_*.skc`
* `assets/textures/models/weapons/coop_dbshotgun/` : `coop_dbshotgun.jpg`, `_parts.jpg`, `_bloody.jpg`, `_camo_woodland.jpg`, `_camo_winter.jpg`, `_camo_desert.jpg`, `_fmask.jpg`
* `assets/scripts/coop_dbshotgun.shader`, `assets/scripts/coop_dbshotgun_finish.shader` (uses the mod's `textures/coop_skins/env_sheen.tga`)
* `assets/textures/hud/loot/w_dbshotgun.tga`, `assets/textures/hud/clip/clip_2.tga`
* `rows/fps_rows_coop_dbshotgun.txt` -> inside `models/player/base/fps_anims_shotgun.txt` (fixes pak copy)
* `rows/tps_rows_coop_dbshotgun.txt` -> inside `models/player/base/anims_shotgun.txt`
* patches: `wiring/patch_torso_dbs.py`; `wiring/gen/armory_dbs.patch` (18 mod files) + `wiring/gen/new/` (12 cfgs) +
  `wiring/gen/generators.patch` (TSV row, `armory_unlocks.py` HZM_MOD, `gen_service_record.py` HZM_MOD + REWARD_NAMES);
  then the generators and the `ui/coop_loadout.urc` checksum (`wiring/WIRING.md` steps 6-7);
  `wiring/patch_cgame_loot_dbs.py` (already on the branch)
* engine: `dbshotgun-next` 96c32bd9; `sights_override.json` + `tools/sightrow_dbs.py`
* NOT for integration: `armory_ov/` (test install), `wiring/superseded/` (option A), `build/`

'''

S11 = '''## 11. Open points (honest list)

1. World behaviour, sec. 14: touch pickup, use-to-loot, shell sharing are not verified; one unexplained log line.
2. The aimed reload plays low on the screen (chambers at about 85 % of the height). NOT raised this pass.
3. Hip reload: the loading hand is large when it crosses to the left chamber. NOT changed this pass.
4. Stage finishes (gold / chrome / blued) read flat on this dark sheet - the same look as the pump gun's (side by side:
   `build/_f2_refs.jpg`), the wood is tinted too, as on every gun. The winter "open" still has the loading hand in it.
5. With the master switch off the tile's row is an empty gap and the PRIMARY card keeps the archived name.
6. A respawn in the map brings up PRIMARY 2 first when the double barrel is PRIMARY 1 (after a map load it is in the
   hand); not looked into - may be the same for any pair of guns.
7. Third person: the hold / aim poses are the pump gun's; the raise clamps the left arm in 5 frames, the lower in 8.
8. Sounds chosen by file, never heard.
9. Recoil table: 8 rows written from the tik's own viewkick line by the staging script (the extractor named in the
   table's header was not found under docs/tools).
10. Not wired (as for the other new guns): `global/weapon.scr` AI alias, `developer.scr` / `buildmode_catalog.scr`
    lists, the MP armory, model variants (pack skins).

'''

S12 = '''## 12. Handover

Knobs: `dbs_hands.py` HOLD / AIM / WORK / LOWERED / PHYS / `GP.ACTIONS` / WRIST_VIEW / BELT_VIEW / LEVER_SHIFT;
`dbs_anim.py` THETA_OPEN / THETA_CLOSE / EJECT_F / EJECT_DIR / SHUT_F; `dbs_skin.py` top block; `dbs_tps.py` JOBS;
`dbs_finish.py` FINISHES / BLOTCH_CM / BORE_MASK; `stage_armory_dbs.py` ID / BARS / CHAL / XFM (env DBS_XFM).
Traps: bug-3774 .. bug-3781 (second pass), bug-3808 .. bug-3813 (this pass).
Runs: finished ones are in `H:\\\\hzm_archive\\\\dbs\\\\<run>\\\\` (f1-f3 finishes, a1 armory, a2 armq + world v1, a3 world v2;
second pass: re2-re5, rh1-rh6, rl1, rm1-rm4). **Loss, bug-3808:** this pass's first archive move put the second pass's
28 run folders into one folder; the 15,117 `ab__<run>__` frames were sorted back, 511 files without a run id in their
names (per-run qconsole.log / notes.json / wire stills / tp, act, ms frames) collided - one copy of each survives in
`H:\\\\hzm_archive\\\\dbs\\\\_merged_no_run_id\\\\`. The media made from them is intact in `media/` and `build/`.
The harness home keeps the test player's unlock record and armory picks between runs (a2 started with 7 unlocks).
Next, in order: (a) world behaviour: kill the test AI another way (shoot it), use-to-loot prompt + picture, touch
pickup by a player who carries no shotgun, shells with readable counts, and the `cannot be picked up` line (bug-3813);
(b) raise the aimed work pose (`WORK['ads']`, six-stance box runs); (c) the hip loading hand; (d) listen to the sounds.
Someone's `zzzzzzzzzzzzzzzz_memorialtest.pk3` in `G:\\\\mohaa-hudfeed4\\\\home\\\\maintt` and the old `runs` folders there were left alone.

'''

S13 = '''## 13. The finish set - `tools/dbs_finish.py`

The seven the pump gun has, by the mod's recipe (`gen_skins.py` / `bake_skins.py` / `gen_weapon_skins.py`, read, not
run): gold / chrome / blued = shader stages over OUR sheet with the mod's tint and sheen numbers; bloody / woodland /
winter / desert = sheets baked from OUR sheet with the mod's colour maths and palettes. Different from the mod, on
purpose: the pattern is laid out in gun space (this atlas has many islands - a UV-space pattern breaks at every seam);
the bores, breech faces, standing breech and muzzle faces keep the base sheet on the baked finishes, and a mask stage
keeps the bores dark under the stage finishes; the bead and the shells are the untouched second surface.
**All eight tiks carry the name "Shotgun (Double Barrel)"** - a second " (Finish)" suffix would resolve to the pump
gun's hands, torso rows and sight row (bug-3809); the armory tells them apart by tik path. Ranks 3000-3006.
`gen_skins.py` skips this gun by itself (a name with " (" is "already a variant"), so it will not overwrite them.

## 14. World behaviour (NOT finished) - runs a2, a3

| Item | State |
|---|---|
| death drop | log `DEATHDROP e0 models/weapons/coop_dbshotgun.tik` at every death with it; a double barrel lying on the ground looked at (`dbs_world_unfinished.jpg`, right) |
| touch pickup of a player's drop | NOT verified: the test player's kit already held the gun (the armory pick persists in the harness home), so "in the hand afterwards" proves nothing |
| `cannot be picked up` | 3 x in run a3: `(itemhandler.scr::handleWeaponPickup) *ERROR*: Weapon with model models/weapons/coop_dbshotgun.tik cannot be picked up by <player>`, each right after a respawn at the place of the own death drop. Cause not established (bug-3813) |
| AI with the gun | armed through `aihandler.scr::coop_actorArm` (log `DBSAI armed`; the AI stands with a long gun at its side, looked at, not close enough to name it) |
| use-to-loot prompt + picture | NOT verified: the script-spawned AI could not be killed by script (`damage 5000`, then `takedamage` + `kill`: it stayed up), so there was no AI drop |
| shells shared with the pump gun | NOT verified by a run. By the tiks: both declare `ammotype "shotgun"` (one pool in the engine); `itemhandler.scr::getAmmoType` answers "shotgun" for the tik (staged) |
'''

i, j = cut(s, '## 8. Wiring option A', '## 9. Sounds')
s = s[:i] + S8 + s[j:]
i, j = cut(s, '## 10. Files for integration', '## 11. Open points')
s = s[:i] + S10 + s[j:]
i, j = cut(s, '## 11. Open points', '## 12. Handover')
s = s[:i] + S11 + s[j:]
i, j = cut(s, '## 12. Handover', None)
s = s[:i] + S12.replace(chr(92) * 2, chr(92)) + S13
s = s.replace('* patches: `wiring/patch_torso_dbs.py`, `wiring/patch_wiring_dbs.py` (+ `patch_gen_loadout`), `wiring/patch_cgame_loot_dbs.py` (already on the branch)\n', '')
open(p, 'w', encoding='utf-8', newline='').write(s)
print('README rewritten')
