# Double-barrel shotgun (`coop_dbshotgun`) - SHIP CUT for the integration agent

State 2026-10-13, fourth pass. Everything below is STAGED in `docs/proposals/dbshotgun_2026-10-12/`; nothing is in the
mod tree, `docs/tools/assets/fixes`, `docs/tools`, the shared `sights.json` or a live install.
**The files named here are FROZEN**: `DBS_SHIP.manifest.tsv` holds size + sha256 of every one of them
(`python tools/ship_manifest.py --check` = exit 0 while nothing moved). Change one = re-run the checks of sec. 9.

Roster ids of the three new guns: **G 43 Irons 78, FG 42 Irons 79, double barrel 80**. While this pass ran, **id 78
landed in the mod tree** (17761c3a, 12:53): the staged patches were RE-MADE on that tree at 13:03
(`stage_armory_dbs.py --sr`, both `git apply --check` pass, generators reproduce exactly, 75 -> 76 weapons) and run in
the engine (run a4). **Id 79 is not in the tree: when it lands, re-run the script again (sec. 4).**

## 1. Assets (copy `assets/<path>` to `<path>`; 44 files, all NEW names - no existing file is replaced)

| where | files |
|---|---|
| `models/weapons/` | `coop_dbshotgun.tik` + 7 finishes `coop_dbshotgun_{gold,chrome,blued,bloody,camo_woodland,camo_winter,camo_desert}.tik` (all eight carry the item name `"Shotgun (Double Barrel)"`, ranks 645 and 3000-3006) |
| `models/weapons/coop_dbshotgun/` | `coop_dbshotgun.skd`; 8 gun clips `coop_dbs_{idle,fire,fire_empty,reload,reload_empty,reload_single,reload_single_first,reload_end}.skc` |
| `models/human/animation/viewmodel/coop_dbshotgun/` | 13 first-person hand clips `dbs_{idle,fire,charge,pullout,putaway,reload,reload_single,reload_single_l,reload_end,reload_ads,reload_single_ads,reload_single_l_ads,reload_end_ads}.skc`; 3 third-person torso clips `coop_dbs_tps_{fire,fire_crouch,reload_end}.skc` |
| `textures/models/weapons/coop_dbshotgun/` | `coop_dbshotgun.jpg`, `_parts.jpg`, `_bloody.jpg`, `_camo_woodland.jpg`, `_camo_winter.jpg`, `_camo_desert.jpg`, `_fmask.jpg` |
| `scripts/` | `coop_dbshotgun.shader`, `coop_dbshotgun_finish.shader` (uses the mod's `textures/coop_skins/env_sheen.tga`) |
| `textures/hud/loot/` | `w_dbshotgun.tga` (the use-to-loot picture) |
| `textures/hud/clip/` | `clip_2.tga` (the armory's 2-round picture) |

Which pak: the weapon files where the mod's other own guns live (mod tree); the hand / torso clips and the two alias
blocks of sec. 2 belong with the files they extend (fixes pak). The fixes pak sorts below
`zzzzzzzzzz_coop_hd_m3l1a.pk3`; none of these names exists in another pak (checked against the GOG folder through
`weapon_hd/vfs.py`), so the sort order does not matter for them.

New since the third pass (fourth pass): the row `reload_ads_empty` in all 8 tiks (sec. 6), nothing else in `assets/`.

## 2. Rows to append (text blocks, additions only)

| block | goes into | what |
|---|---|---|
| `rows/fps_rows_coop_dbshotgun.txt` | `models/player/base/fps_anims_shotgun.txt` (fixes pak copy), before its last `}` | 13 hands rows `coopr_shotgun_double_barrel_*` |
| `rows/tps_rows_coop_dbshotgun.txt` | `models/player/base/anims_shotgun.txt`, before its last `}` (its last `$path` is `models/human/animation`) | 3 torso aliases `coop_dbs_stand_fire`, `coop_dbs_crouch_fire`, `coop_dbs_reload_end` |

`tools/mkov_dbs.py` does exactly this for the test overlay (lines "the first-person rows" / "third person"): copy it.
Fourth pass: `coop_dbs_reload_end` got the heavy lane's `first removeattachedmodel tag_weapon_left 0
models/ammo/shotgunshell.tik` (a reload broken off with the third-person shell still in the hand).

## 3. Patches, in apply order, each with its check

| # | patch | target | check (writes nothing) |
|---|---|---|---|
| 1 | `wiring/patch_torso_dbs.py <file>` | `coop_mod/player_Torso.st` | `python wiring/patch_torso_dbs.py <file> --check` ; `python tools/torso_check.py --rows` runs it on the DEPLOYED file and on the mod TREE's and shows every row (both: 6 clip rows, 1 aimed-refire row + state `COOP_DBS_REFIRE_AIM`, 2 break-off routing rows, 0 other lines changed, idempotent) |
| 2 | `wiring/gen/generators.patch` | `docs/tools/loadout_weapons.tsv` (row id 80), `armory_unlocks.py` (HZM_MOD), `gen_service_record.py` (HZM_MOD + `REWARD_NAMES`) | `git apply --check docs/proposals/dbshotgun_2026-10-12/wiring/gen/generators.patch` from `C:\mohaa-coop-dev` (passes on docs 0188d2b) |
| 3 | `wiring/gen/armory_dbs.patch` | 18 mod files (list: `wiring/gen/report.txt`) | `git apply --check docs/proposals/dbshotgun_2026-10-12/wiring/gen/armory_dbs.patch` from `C:\mohaa-coop-dev` (passes on mod tree 17761c3a = with id 78; the patch made on 99ba8027 stopped applying the moment 78 landed - 10 files - which is what sec. 4 is about) |
| 4 | `wiring/gen/new/` | 12 new files `ui/loadout/{p80,t80,w80_s1,w80_s2,req80,finp80_1..7}.cfg` | copy |
| 5 | regenerate | - | `gen_loadout.py build`, `gen_skinbase.py`, `armory_unlocks.py --emit`, `gen_service_record.py build` (build.ps1 runs the last); `gen_loadout.py check` must say EXACT REPRODUCTION (it does in the scratch repo, `wiring/gen/report.txt`) |
| 6 | checksum | `docs/tools/check_mp_isolation.py`, `LOCKS["ui/coop_loadout.urc"]` | sec. 5 |

The mod tree's torso patch state today: **not applied**; the patch was run in the engine against the mod TREE's file
(99ba8027; 17761c3a in run a4) in runs w2 / w3 / rs1 / rs2 / a4 (overlay `mkov_dbs.py --tree`).
**Watch:** the heavy lane staged a SHOTGUN PUMP FIX (docs a78fd3f, "no pump stroke in the aim") that is not in the tree
yet. If it changes the rows this patch anchors on (`shotgun_crouch_fire : POSITION_TYPE "crouching"` in the two
`ATTACK_SHOTGUN_PRIMARY*` states, `shotgun_reload_end : default`, the `RELOAD_SHOTGUN_BREAK_QUICK : +ATTACK_PRIMARY
HAS_AMMO_IN_CLIP "mainhand"` rows) the patch stops with an assert naming the count - it never guesses. Apply the heavy
lane's fix first, then this patch, then `tools/torso_check.py --rows`; the pump gun comparison of sec. 7 was made
WITHOUT that fix.
`unlockreq_gen.scr` had generator drift in the tree before this gun (report.txt): re-running the generators is the clean way.

## 4. Order against the other two new guns (78, 79)

All three edit the roster count, `ui/loadout/lktab0-5.cfg`, the tile list of `ui/coop_loadout.urc`, `loadoutroster.scr`,
the TSV. They do not merge as text. Rule: **apply one gun completely (patches + generators), then RE-RUN the next gun's
staging script on the tree as it then is, and apply what it writes.** For this gun:

```
python wiring/stage_armory_dbs.py --sr      # reads the tree AS IT IS, rewrites wiring/gen/* and armory_ov/
```

Every anchor in it is a name and is asserted; it fails loudly rather than guess. What it computes from the tree at that
moment: the roster count (75 -> 76 with id 78 in), the tile's place = **the LAST tile of the heavy tab** (y = that
tab's last tile + 19; today 327, under DP-28; it asserts y <= 403 = the longest tab of the menu), the lock / tile
cvars in the six lktab files. Because the tile is last and moves no other tile (fourth pass), the order 78 -> 79 -> 80
or any other gives the same picture; if the FG 42 Irons lands on the heavy tab after this gun, ITS script decides where
it goes and this tile stays last only if this script is re-run after it. Suggested: **79 next, then 80 last.**
This was done once for real in this pass (78 landed mid-run): the re-run took 40 s, changed only
`wiring/gen/armory_dbs.patch` + `generators.patch` (and `armory_ov/`), and `ship_manifest.py --check` reported exactly
those two as changed - expected; a new manifest was written.

## 5. `ui/coop_loadout.urc` checksum

The file has no generator and is locked by checksum. After ALL new guns are applied:

```
python docs/tools/check_mp_isolation.py --print-lock ui/coop_loadout.urc
```

prints the line for `LOCKS` (sha256_lf / sha256_crlf / lf_bytes / eol); fill `blob` (`git hash-object`), `commit`,
`locked`. For reference, mod tree 17761c3a (id 78 in) + THIS gun (the file in `armory_ov/ui/`): lf_bytes 76913,
sha256_lf `462a8a4568f0b4ca5135bf75cc7ef1f10ef05caa4656cad41c9f70ede1c15697`,
sha256_crlf `67f089273e907e2d753ea2cf9443c7df2a7bbdd8c60cda47710f841b9f72a98e`, eol crlf. With 79 applied the
numbers differ: print them, do not copy these.

## 6. Engine: `dbshotgun-next` **1dc10936** = `integ-ads` 8327e12b + this gun (cgame only, 75 lines in 5 files)

Worktree `C:\mohaa-coop-dev\openmohaa-hzm-dbs`. The branch already CONTAINS integ-ads: merge commit 45373131 (integ-ads
37e5dde8; built, run in the engine in every run after w1 as harness DLL `cgame_dbs9`, md5 db892524), then 1dc10936
(integ-ads moved to 8327e12b during this pass - one loot-feed row for the G 43 Irons, no conflict; built as
`cgame_dbs10`, md5 0f68fb50, NOT run). Merging the branch into integ-ads is a fast-forward as long as integ-ads is
still 8327e12b (`git merge-base --is-ancestor integ-ads dbshotgun-next`). `git diff integ-ads dbshotgun-next --stat`:

```
 code/cgame/cg_adssights.h     |  1 +     one sight row (tools/sightrow_dbs.py <cg_adssights.h>, from sights_override.json)
 code/cgame/cg_coopfeed.c      | 12 ++-   loot picture looked up by the FULL weapon name first
 code/cgame/cg_coopfeed_loot.h |  1 +     {"Shotgun (Double Barrel)", "w_dbshotgun", "Double Barrel", ...}
 code/cgame/cg_modelanim.c     | 48 +     the block below
 code/cgame/cg_viewmodelanim.c | 15 +     hands: a per-weapon reload_single row that starts on an EMPTY clip plays <row>_l
```

No fgame change, no protocol change. If integ-ads has moved, merge again and resolve the same three places the same way:

**cg_adssights.h** - take integ-ads's table, then `python tools/sightrow_dbs.py <path>/cg_adssights.h` (adds the one row).

**cg_viewmodelanim.c** - take integ-ads's side of the conflict (its per-weapon rows for every view animation,
`coop_vmPerWeaponRows`, replace this branch's old unconditional lookup), then add directly after the closing `}` of
its `if (... VM_ANIM_RELOAD ...) { CoopPerWeaponReloadAnim(...) } else { ... }` and before the comment
`// HZM coop [revolver reload 2026-10-12] EMPTY GUN`:

```c
        if (cgi.anim->g_iLastVMAnim == VM_ANIM_RELOAD_SINGLE && cg.snap && cg.snap->ps.stats[STAT_CLIPAMMO] == 0
            && !Q_strncmp(szAnimName, "coopr_", 6)) {
            char szFirst[MAX_QPATH];
            Com_sprintf(szFirst, sizeof(szFirst), "%s_l", szAnimName);
            if (cgi.Anim_NumForName(pTiki, szFirst) != -1) {
                Q_strncpyz(szAnimName, szFirst, sizeof(szAnimName));
            }
        }
```

**cg_modelanim.c, `CG_ModelAnim` - MERGE NOTE (supersedes README sec. 6).** Git merges the file without a conflict
and leaves two blocks; that is not what is wanted. What was found by reading integ-ads's function:
* integ-ads's block (`// HZM coop [aimed reload 2026-10-12] THE GUN'S OWN ANIMATION IN AN AIMED RELOAD`, from right
  after `CG_InterpolateAnimParms(s1, sNext, &model);` to `CoopGunLatchApply(s1->number, &model);`) OWNS the `reload`
  row: decided once per reload from `STAT_CLIPAMMO == 0` and `CG_AimingDownSights()` - hip + empty -> `reload_empty`,
  aiming + empty -> `reload_ads_empty`, aiming + rounds left -> `reload_ads_loaded`, each only if the tik has that row.
* So an emptied double barrel reloaded WHILE AIMING found no `reload_ads_empty` and would have thrown out one case.
  Fixed in the tiks, not in C: all 8 tiks now carry `reload_ads_empty` = the `reload_empty` clip under that name.
* This branch's block therefore no longer touches `reload`. It keeps ONE row and sits AFTER integ-ads's block.
  The earlier note ("each block would swap the other's result back") was wrong - neither does.

The exact merged block, placed between `CoopGunLatchApply(s1->number, &model); }` and
`if (cent->currentState.parent != ENTITYNUM_NONE) {`:

```c
    if (cg.snap && s1->parent == cg.snap->ps.clientNum && cg.snap->ps.stats[STAT_MAXCLIPAMMO] > 0) {
        static const char *const s_dbsRows[1][2] = {
            {"reload_single", "reload_single_first"}
        };
        static int s_dbsEnt[1] = {-1}, s_dbsSeen[1] = {0}, s_dbsChoice[1] = {0};
        int        r, k;

        for (r = 0; r < 1; r++) {
            int      iAlt = cgi.Anim_NumForName(model.tiki, s_dbsRows[r][1]);
            int      iRow;
            qboolean bRow = qfalse;
            float    fT   = 999.0f;

            if (iAlt == -1) {
                continue;
            }
            iRow = cgi.Anim_NumForName(model.tiki, s_dbsRows[r][0]);
            for (k = 0; k < MAX_FRAMEINFOS && iRow != -1; k++) {
                if (model.frameInfo[k].weight && model.frameInfo[k].index == iRow) {
                    bRow = qtrue;
                    if (model.frameInfo[k].time < fT) {
                        fT = model.frameInfo[k].time;
                    }
                }
            }
            if (!bRow) {
                continue;
            }
            if (s_dbsEnt[r] != s1->number || cg.time - s_dbsSeen[r] > 250 || cg.time < s_dbsSeen[r] || fT < 0.05f) {
                s_dbsChoice[r] = (cg.snap->ps.stats[STAT_CLIPAMMO] == 0) ? 1 : 0;
            }
            s_dbsEnt[r]  = s1->number;
            s_dbsSeen[r] = cg.time;
            for (k = 0; k < MAX_FRAMEINFOS && s_dbsChoice[r]; k++) {
                if (model.frameInfo[k].weight && model.frameInfo[k].index == iRow) {
                    model.frameInfo[k].index = iAlt;
                }
            }
        }
    }
```

(the comment above it in the branch says the same). Only a tik that HAS `reload_single_first` is touched: no other gun.
Not looked at in the engine with the merged DLL: the aimed emptied reload's two cases in the air as a still (the
stance GIF of run rs2 shows the reload; the row choice itself is by code reading + the tik row).

## 7. The gun's numbers

Weapon (tools/dbs_tik.py): 2 shells; one barrel per pull, fire delay 0.30 s; 26 pellets x 14 = 364 per barrel (pump
gun 20 x 14); spread 115 115 135 135; pellet range 650; move speed 1.00; view kick -23 -26 / +-2 / recentre 12; start
ammo 40; ammo type `shotgun` (pool max 50, shared with the pump gun); class heavy; rank 645; name `"Shotgun (Double
Barrel)"`. Armory: id 80, tile DOUBLE BARREL (last on the HEAVY tab), DMG 10 / RPM 3 / ACC 6 / MOB 10, unlock =
challenge "Both Barrels" (60 kills with the Shotgun, `wpn_shotgun_v`), finishes gated as the pump gun's, master
switch `coop_dbShotgun` (default 1).

**Server-read rows** (tools/dbs_rowlen.py; the 8 tiks are equal row for row):

| row | clip | length |
|---|---|---|
| idle, secondaryfire | coop_dbs_idle.skc | 1 frame |
| fire / fire_empty | coop_dbs_fire.skc / _fire_empty.skc | 10 frames, 0.333 s |
| reload / reload_empty / reload_ads_empty | coop_dbs_reload.skc / _reload_empty.skc (x2) | 23 frames, 0.767 s |
| reload_single / reload_single_first | coop_dbs_reload_single.skc / _first.skc | 20 frames, 0.667 s |
| reload_end | coop_dbs_reload_end.skc | 32 frames, 1.067 s |

Torso rows: `coop_dbs_stand_fire` 36 frames 1.200 s = `shotgun_stand_fire`; `coop_dbs_crouch_fire` 35 frames 1.167 s =
`shotgun_crouch_fire`; `coop_dbs_reload_end` 36 frames 1.200 s = `shotgun_reload_end` (EQUAL, asserted). The gun's
reload start and per-shell rows are the SHARED `shotgun_reload_start` (23 frames) and `shotgun_reload_loop` (20
frames, shell counted on frame 14 since the heavy lane's change) - not changed by this gun.

**Server timings, measured** (run w2: listen server, fixedtime 16, sv_fps 40 = 0.025 s steps; a script reads the torso
state and the shell pool every server frame, coop_fireDebug marks each shot; mod TREE's state file + this patch;
`build/time_w2.txt`). Hip and aimed agree within one frame.

| what | time |
|---|---|
| second barrel after the first | 0.375 s (hip) / 0.400 s (aimed) with the trigger pulled again 0.21 s and 0.42 s after the first shot; the tik's fire delay is 0.30 s |
| after the LAST shell is fired: the reload starts by itself | 1.200 s after that shot (the fire torso clip) |
| reload, emptied gun: start -> shell 1 counted -> shell 2 counted -> end row -> ready | 0 -> 1.200 -> 1.850 -> 2.050 -> 3.225 s |
| reload, one shell left: start -> shell counted -> end row -> ready | 0 -> 1.200 -> 1.400 -> 2.575 s |
| a reload broken off by the trigger (a shell in the gun): trigger -> shot | 1.150 s (through RELOAD_SHOTGUN_BREAK_END: the gun is shut first) |
| for comparison, the pump gun: shells counted at 1.200 s, then every 0.650 s; end row 0.200 s after the last; ready 1.175 s later; broken off: trigger -> shot 0.325 s | same shared rows |

**The pump gun with and without this patch** (run w2 = patched, run wb = the same build with the tree's state file
unpatched; `build/time_w2_vs_wb.txt`): six segments (hip / aimed x one shot + reload, emptied + reload, reload broken
off) - the SAME sequence of states, shells and shots in every one (9 / 24 / 10 / 11 / 24 / 10 events), largest time
difference 0.025 s = one server frame (when the key landed). Other weapons: the torso patch only INSERTS rows (0 other
lines changed, `tools/torso_check.py`), every inserted row is conditioned on the exact name `"Shotgun (Double
Barrel)"`; the two alias blocks are appended text with new names. No other weapon was run.

## 8. Aimed reload against the settled aim's sway envelope

Re-measured with the merged cgame (`cgame_dbs9`) on today's deployed build + the mod tree's state file, sway and
breath on, `tools/box_dbs.py <run> dbs --sway [--empty]` (the heavy lane's `boxeng.py`): share of the centre box the
reload covers BEYOND everything the settled aim covers in its sway. Bar: under 2 % in every frame.

| | stand | crouch | prone | lean L | lean R | braced | frames over 2 % | sight line at the end |
|---|---|---|---|---|---|---|---|---|
| one shell left (run rs1, 162 frames per stance) | 0.00 | 0.02 | 0.02 | 0.66 | 0.44 | 0.04 | 0 | 0.00 deg in all six |
| emptied, from the reload's start (run rs2, `BOXENG_AFTER=66`) | 0.71 | 0.21 | 0.12 | 0.71 | 1.12 | 0.13 | 0 | 0.00 deg in all six |
| emptied, the tool's default window (starts 28-40 frames after the LAST SHOT) | 1.97 | 7.52 | 14.44 | 1.91 | 1.12 | 5.00 | crouch 8, prone 11, braced 5 | - |

The last row is the second shot's smoke, not the reload (third pass, looked at then: `build/_re5p.jpg`; the same
stances, the same order of size: 0.79 / 2.00 / 12.18 / 1.90 / 1.83 / 5.42). The settled aim itself covers 12.5-17.5 %
of the box (braced 4.4-5.2 %). Third pass, old cgame: 0.01-0.59 % and 0.07-1.55 %.
Looked at: `media/dbs_reload_one_left_aimed_v4.gif`, `media/dbs_reload_empty_aimed_v4.gif` (stand; frames laid out and
checked: the gun opens low, shells go in, shut, back on the bead). The other five stances were measured, not looked at
this pass (the clips are byte-identical to the third pass's, whose stance sheets were looked at).

The aimed work pose was NOT raised (item 2 of the fourth pass): offline renders show the top of the loading hand
already on the centre box's lower edge (60 % line) with the chambers at 85 %; 1 u higher puts the hand in the box.
Bringing the hand from straight below would allow about 0.7 u (chambers at ~78 %) but the hand then covers the
breech - not taken, a choice for the user (`media/dbs_aimed_work_pose_options_offline.jpg`). The hip reload's large
loading hand was not changed either (knobs for both are now in `dbs_hands.py`: env `DBS_ADS_CHAM`, `DBS_WRIST_ADS`,
`DBS_WRIST_HIP`; with none set the bake is byte-identical to the frozen clips).

## 9. Verified / not verified

| item | state | how |
|---|---|---|
| death drop lies where the player died; only one such gun exists | verified | LOOKED AT (run w1, `media/dbs_world_death_drop_touch_pickup.jpg`) + log (0 in the world before, 1 after the death, 0 after the pickup) |
| touch pickup of a player's drop by a player whose kit has no shotgun | verified | LOOKED AT (in the hand) + log (`coop_hasitem` 0 -> 1, `Picked Up Shotgun (Double Barrel)`) |
| `cannot be picked up` line (bug-3813) | cause found, NOT this gun, harmless | log: the same line for the pump gun in the same run; code reading (`Weapon::PickupWeapon` returns before the `pickup` notify for a placed item); 81 more in other lanes' logs. Nothing to fix in the staged wiring |
| an AI armed through `aihandler.scr::coop_actorArm`, fires it, drops it when killed | verified | LOOKED AT (aiming it) + log (it shot the test player dead in run w1); killed by a damage event with the player as attacker |
| Use prompt on an AI drop with OUR picture and the name "Double Barrel" | verified | LOOKED AT (`media/dbs_world_loot_prompts.jpg`) |
| tap = take the gun (kit without a shotgun) | verified | log (`LOOT picked ... asNewGun=1`, 2 in the clip) + LOOKED AT in the hand |
| hold = take its shells | verified | log (`LOOT ammotake ... pool 10 -> 12`, the gun is consumed) + prompt LOOKED AT |
| with a PUMP gun in the kit the AI drop gives shells only (tap refused) | found, by design of the loot rule (names cut at " (") - fgame, not changed | log (run w2) + prompt LOOKED AT. Choice for the user |
| shells shared with the pump gun, both ways | verified | log: double barrel reload 20 -> 18; pump gun one shot + reload 50 -> 49; switching back leaves the pool; walking over a pump gun with the double barrel held: "Got 5 Shotgun Rounds", pump gun consumed; walking over a double barrel with the pump gun held: "Got 2 Shotgun Rounds", consumed |
| second barrel, reload, weapon switch right after picking it up | verified | LOOKED AT (stills) + log |
| server timing of the gun; pump gun unchanged | verified | measured (sec. 7) |
| torso patch on the CURRENT mod tree's file | verified | run in the engine (w2, w3, rs1, rs2) + `--check` |
| merged cgame (integ-ads + this gun) | built and run | every run of this pass after w1 |
| heavy tab without a gap when the switch is off | verified | LOOKED AT (`media/dbs_armory_heavy_tab_switch_on_off.jpg`) |
| a respawn brings up PRIMARY 2 first | general behaviour, not this gun | code reading: `itemhandler.scr` raises `coop_lastWeapon` (the gun in the hand at death) before slot 1; consistent with run a1 (after a map load slot 1 is in the hand). Not re-run |
| Service Record hover text | NOT exercised | the hover is the engine's `hovershader` (no mouse in the harness); the picture it shows was looked at as a file, the page in game (third pass) |
| aimed reload in six stances with the merged cgame | SEE sec. 8 | measured |
| sounds | NOT heard | aliases resolve, harness is muted |
| a second client / a dedicated server / the main-menu armory / the MP armory | NOT tested | - |
| the armory entry re-made on the tree WITH id 78 (17761c3a), merged cgame | verified, short form | run a4 (`coop_lockLoadout 1`): unlocked by the challenge through `chal_bump` (v=60), picked (slot 1 = the tik, id 80), respawned with it in the hand, tile last on the tab, gone with the switch off - LOOKED AT (`media/dbs_armory_restaged_on_tree_with_id78.jpg`) + log, 0 script errors. The long form of the third pass (finish, map restart, map change, Service Record) was NOT re-run |
| the 7 finishes with the merged cgame | NOT re-run | tiks changed by one alias row only |
| third-person view of the broken-off reload, the AI's own animations with this gun | NOT looked at closely | - |

## 10. Runs of this pass (archived: `H:\hzm_archive\dbs\<run>\`)

w1 world (death drop, touch, shells by touch; old cgame_dbs8) - w2 world from the AI part with a pump gun in the kit +
server timing (cgame_dbs9) - w3 world from the AI part without a shotgun + heavy tab tiles - wb pump gun timing
baseline (state file unpatched) - rs1 / rs2 six-stance aimed reloads (one shell left / emptied) - a4 armory entry
re-made on the tree with id 78. Facts of the runs: `build/evidence4/`. All ran with 0 script errors and a clean window
report. Bugs of this pass: bug-3851 .. bug-3860.

## 11. Limits of the harness to keep in mind

The harness's game paks are the DEPLOYED build; the overlay put the mod tree's `player_Torso.st` (patched) and
whatever `docs/tools/assets/fixes` had beyond the deployed fixes pak on top (219 files at the time: the pistol step in
flight). The harness home has its own `coop_defaults.cfg`, so `coop_dbShotgun` was never seeded there: the script
treats an unset switch as on (run a4), and `set coop_dbShotgun 0` as off. The real seed line is in the patched
`coop_defaults.cfg`.
