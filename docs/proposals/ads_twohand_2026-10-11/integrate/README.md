# ADS / aimed-reload ROLLOUT - integration PASS 2 (2026-10-13): pistols, G 43 Irons, the shotgun's pump in the aim, + the rain fix

**State: steps 4, 5 and 7 are IN and verified on top of pass 1 (steps 1-3, which is what the user's install runs),
and the cgame also carries the rain fix (`rainfix-next` 5376f59e, coordinator addition, last engine step).
Step 6 (FG 42 pair) and the double-barrel shotgun are NOT in - nothing of either is in the engine branch, the fixes
sources or the mod tree. Nothing is deployed, nothing is published.** Pass 1's text is kept below, unchanged.

| what | where | id |
|---|---|---|
| engine | `C:\mohaa-coop-dev\openmohaa-hzm-integads`, branch `integ-ads` (cgame only) | **14fb0dde** |
| binaries | `<scratchpad>\built_integ9\` = `built_integ8` + the new `cgame.dll` | cgame **e81f6925**8419c4a01ea414de042110e5 |
| mod (code pak) | `hzm-mohaa-coop-mod`, branch `coop-wip` | **17761c3a** (step 4: 99ba8027) |
| fixes pak | `hzm-mohaa-coop-mod\zzzzzzzzzz_coop_fixes.pk3` - 455 members, 12 290 502 bytes | md5 **3a071f44**ef7f6e44a87f47c1efde43ce |
| baseline ("released") | pass 1: `built_integ8` (cgame a7c8c1e6) + mod 02405cef + the deployed fixes pak d1b75d08 (223 members) | docs 76f7b15 |

`built_integ9`, unchanged files: `game.dll` 6b515fbf, `openmohaa.exe` 5cd827eb, `omohaaded.exe` 9ebd2043,
`renderer_opengl1.dll` a15882c4, `renderer_opengl2.dll` 8296bf86. Per-step cgames are kept beside it:
`built_integ9_step4\cgame.dll` a4274429 (pistols only), `built_integ9_step5\cgame.dll` 3a47895e (+ G 43 Irons),
`built_integ9_step7\cgame.dll` d3832aeb (+ shotgun pump = every ADS step, without the rain fix).

| step | engine commits on `integ-ads` | mod commit | docs commit |
|---|---|---|---|
| 4 pistols | 37e5dde8 (merge of `ads-next` e8e199be) | 99ba8027 (state file) | ff293d1 |
| 5 G 43 Irons | 47acac77 (merge of `ads-rifle-next` c7ce5e86, strategy ours), 8327e12b (loot row) | 17761c3a (armory, generators' output) | fb469d7 |
| 7 shotgun pump in the aim | e7860c83 (`heavy/tools/apply_cyclewpn.py`) | none | d2d8295 |
| rain reaches the ground (not an ADS step) | 14fb0dde (merge of `rainfix-next` 5376f59e: `cg_nature.cpp`, `cg_beam.cpp`, `cg_commands.h`; clean, no ADS file touched) | none | none (`docs/proposals/rainfix_2026-10-13/README.md`) |

## What ships, per gun (`FILELIST.txt` = `python integrate_ads.py --dry-run`, 443 files; regenerate, do not edit)
### Step 4 - pistols: the pistol lane's frozen ship cut v2 (`../PISTOLS_SHIP.md`, folder `../ship/`), 98 tiks
Two-handed aim pose, aimed reload rounds-left / emptied, working action; what each pistol gets is the lane's table B.

| pistol | tiks covered |
|---|---|
| Colt 45 | 22: `colt45` + 7 finishes, `colt45_bloodyeic`, `_covert`, `_drbond`, `_guancolt`, `_lv_ttcolt`, `colt45_coltpa` (Pacific), `dbno_pistol` + 7 finishes |
| Silenced Colt .45, Silenced Walther P38, Silenced Beretta, Luger P08, Silenced Luger P08, Nambu Type 14, Walther PPK | 1 each (`colt_silenced`, `p38silenced`, `berettasilenced`, `lugerp08`, `lugerp08silenced`, `nambu`, `ppk` - these 7 tiks live in `zzzzz_xw_weapons.pk3`; none has a finish tik) |
| Walther P38 | 10: `p38` + 7 finishes, `p38_guanp38`, `p38_lv_ttp38` |
| Beretta | 9: `it_w_beretta` + 7 finishes, `it_w_beretta_lv_ttberetta` |
| TT-33 Tokarev / Silenced TT-33 | 8 + 8 (base + 7 finishes each) |
| Welrod | 8 |
| Hi-Standard Silenced | 8 (`silencedpistol` + 7 finishes) |
| Webley Revolver | 9: `webley_revolver` + 7 finishes, `webley_revolver_lv_ttwebley` |
| Nagant Revolver | 8 |
| Webley Mk VI | 1: `colt45_colt1911w` |

Coverage is proved by the script (op `C`: every mod-tree tik of that weapon name). NOT covered, on purpose (held out
by the lane, ship as released): **Mauser C96** + 7 finishes + Trench C96, **S&W M10** + 7 finishes. Not covered and
not a real gun: `p38 - copy.tik` (a stray copy in `zzzzzz-HRRTM_Pak4_Weapons.pk3`). The texture lifts
(`../ship_awaiting_approval/`) are OUT. The Welrod and Luger aim poses ship although the user has not approved them
yet (coordinator's call, lane doc section E).

### Step 5 - G 43 Irons (NEW weapon), 12 tiks
`coop_g43_irons` + 7 finishes + 4 pack skins (`_dhg43fleck`, `_hobbsg43urb`, `_hobbsg43wood`, `_lv_ttg43`), own
mesh with a sight surface, aim pose, aimed reloads, the aim-only gun row `reload_ads_empty`, loot picture - all `new`
members of the fixes pak (nothing of it in the mod tree). Armory: roster id 78 "GEWEHR 43 (IRON SIGHTS)" between the
M1 Carbine and the Kar98k, **rank 2**, 7 finishes on the global finish unlocks, the 4 pack skins as model variants
that share the scoped G43's variant challenges; state-file row, 12 recoil rows, ammo HUD menu, AI alias, dev lists;
the scoped G43's ACC bar 0 -> 9. Applied by `apply_armory5.py` = the rifles lane's `stage_armory_gen.py` transforms
on the real tree + the real generators; **byte-identical to the lane tool's own scratch result** (1355 files).

### Step 7 - shotgun: the pump stroke in the aim (coordinator addition; user: "the shotgun doesnt have the pumping action when in ads")
Heavy lane `../heavy/SHOTGUN_PUMP_FIX.md`, cut frozen at docs a78fd3f and READ FROM THAT COMMIT (the lane folder
holds a re-timed clip 8b09ccff that must not ship): clip `coop_shotgun_cycle_ads.skc` (md5 4f95c41b), 4 added rows
`coopr_shotgun_cycle` / `_cycle_ads` / `_cyclelast` / `_cyclelast_ads`, the cgame patch (same-mesh guard,
last-round row); and the coordinator's decision: in the `fire` row of **all 14 shotgun tiks** the hull leaves 0.35 s
after the shot (was 0.2 s) - one client command, hip and aim alike. No state file, no server-read row.

## What the integration does differently from the lane folders
1. **Pistol-class weapons outside the cut are pinned** (the instruction was "ship per-weapon rows for the colt45
   fallback"; done from the other side, which leaves the lane's tested rows as they are). A scan of every tik the
   game can load (552 in `models/weapons`, 4797 elsewhere) for `weapontype pistol` gives exactly three users that
   are not in the cut: Mauser C96 (+ finishes, Trench; prefix `p38`), S&W M10 (own prefix `m10`, rows untouched)
   and **"Bombing Run" = the coop binoculars** (+ 7 finishes; no named prefix, so the FALLBACK prefix `colt45`).
   Pins: the lane's `coopr_mauser_c96_charge` + the integration's `coopr_mauser_c96_idle`,
   `coopr_bombing_run_idle`, `coopr_bombing_run_charge` (released clips). Proof: `rowpick.py` - C96, Trench, M10,
   Bombing Run resolve to the same clip BYTES in every case (the binoculars have no magazine, their reload cases are
   not compared).
2. **Shared tables are merged, never copied**: `fps_anims_pistol.txt` and `anims_shared.txt` by `git merge-file`
   (op `M`; `anims_shared.txt` = the lane's snapshot of mod 6cf61e58 onto the CURRENT mod-tree file with the
   low-turret rows, shipped in the fixes pak over the pinned mod-tree copy), `coop_mod/player_torso.st` by op `G`
   onto the current file (turret rows + shotgun break-off kept; equal to the lane's `ship_merged/` reference).
3. **ONE client clip clock.** `ads-rifle-next` c7ce5e86 is one commit: the rifles lane's port of the pistol lane's
   clock. Its added lines are the original's (e8e199be) line for line (diff of the two patches: one blank line), so
   it is merged with strategy `ours` - nothing taken, the G 43 Irons' rack clip runs on the pistols' implementation.
   `clock_scope.py`: the clock engages only on Welrod, TT-33 (+ silenced), PPK, Beretta (packed released clip,
   length not readable offline) and the G 43 Irons - on no pass-1 gun.
4. **Shipped steps are frozen** (bug-3885): the rifles lane had rewritten its staged Enfield tiks after pass 1; a
   re-run of step 3 took them. Put back byte-for-byte from the deployed pak; `FROZEN = (1, 2, 3)` keeps the shipped
   copy from now on. Step 7 reads its lane at a commit for the same reason.
5. **A new gun's tiks are looked for in the fixes sources too** (`docs/tools/gen_loadout.py`, `wire_mv2.py`): they
   are not in the mod tree, and `gen_loadout.py check` (build.ps1) would drift without it.
6. **Loot-feed row**: `cg_coopfeed_loot.h` could not be regenerated whole (the use_pickup generator's cached
   silhouettes `tools/sil` are not in the tree); the row is the one the rifles lane computed with that generator's
   own code, inserted where the generator sorts it, and the generator's inputs (`weapons.json`, `SHORT`) carry the
   gun now. `docs/proposals/use_pickup_2026-10-05/` is untracked - those two edits are on disk only.
7. `armory_unlocks.py --emit` rewrote 5 stale requirement TEXTS besides adding the irons (challenge targets had been
   changed without re-emitting - the lane README says so). `ui/coop_loadout.urc` is re-locked in
   `check_mp_isolation.py` (blob 89be4290 @ mod 17761c3a). `gen_loadout.py`, `armory_unlocks.py`,
   `loadout_weapons.tsv` already carried other sessions' uncommitted changes; docs fb469d7 took them along.

## Gates and their evidence (`evidence/pass2/`)
| gate | result |
|---|---|
| 1a server timing, static: `rowlen_check.py --intended <D2 list> --like "coop_g43_irons*.tik=G43.tik"` -> `rowlen_table.txt` | 2132 rows in 228 files, 1555 untouched; every server-read change is a declared one (below); the 12 irons tiks against the released `G43.tik`: only the client-only row `reload_ads_empty` is new. Step 7: the 14 shotgun tiks against docs fb469d7 - 0 rows changed |
| 1b server timing, measured (listen server, 25 ms frames): runs b3 (pass-1 build) / p4 / f5 / s7 / f9 -> `timing_*.txt`, `per_gun_*.txt` | table below |
| 2 regression: `rowpick.py`, `inert_check.py`, `clock_scope.py`, runs f9 / f9b / r9 | all pass; f9 / r9 lines below |
| rain fix: run r9 (`--weather 4` = the downpour pinned, m3l2 yard) | the merged cgame builds; `rainfix_downpour_level_view_r9.jpg` (looked at): streaks down to the ground across the lower half of a level view; 0 Script Error, no new error line. Indoors NOT run here (the lane's run rf19 stands) |
| 3 each gun from the REAL pak: p4 (29 pistol tiks incl. 10 variants / finishes), f5, s7, s7b | hip + aim, fire, hip + aimed reload rounds-left + emptied, crouched; prone for 14 pistols; 0 `Script Error`; error-like lines not in the baseline log: only OpenAL symbol addresses (`errors_*_vs_b3.txt`) |
| 4 dedicated server + one client: run d3 (final build) | boots, mission starts, client joins and spawns; Colt 45, Welrod, TT-33, Webley, G 43 Irons, shotgun (incl. both break-offs): **54 of 54 phases equal to the listen runs**, same shot counts, 0 Script Error on server and client |
| 5 `inert_check.py` | every name the merged cgame reacts to belongs to a rollout gun (or was released) |
| build checks | `check_mp_isolation.py --engine openmohaa-hzm-integads` 22 passed / 0 FAILED (+ selftest), `scrlint`, `check_empty_rhs`, `check_tik_surfaces`, `unlock_audit` (75/75), `ads_audit`, `gen_loadout.py check` EXACT REPRODUCTION, `gen_mp_armory.py check`, `ui_wiring_audit`, `gen_fixes_pak.py check`. `build.ps1` was NOT run |

### Server timing, pass-1 build against integrated (s of server time)
| gun | reload start -> done | magazine filled at | fire state | verdict |
|---|---|---|---|---|
| Colt 45 (+ gold, Guanshire, Pacific, silenced, DBNO pistol) | 2.4 / 2.4 | +0.825 / +0.825 | 0.175 / 0.175 | equal |
| P38 (+ Team Tactics, silenced), Luger (+ silenced), Nambu, PPK | 2.4 / 2.4 | +0.825 / +0.825 | equal | equal |
| TT-33 (+ silenced) | 2.4 / 2.4 | +0.825 / +0.825 | 0.175 / 0.175 | equal |
| Welrod | 2.4 / 2.4 | +0.825 / +0.825 | 0.175 / 0.175 | equal |
| Hi-Standard | 2.4 / 2.4 | +0.825 / +0.825 | 1.05 / 1.05 | equal |
| Beretta (+ silenced) | 2.075 / 2.075 | +2.050 / +2.050 | equal | equal |
| **Webley, Webley Mk VI** (DECLARED) | 2 rounds 2.0 -> **3.05**; 6 rounds 4.0 -> **6.05** | +0.65, then every 0.5 -> **+1.40, then every 0.75** | 0.175 / 0.175 | open 0.5 -> 0.775, one round 0.5 -> 0.75, close 0.5 -> 0.775 |
| **Nagant** (DECLARED) | 2 rounds 2.9 -> **3.45**; 7 rounds 5.775 -> **7.7** | +1.175, then every 0.575 -> **+1.80, then every 0.85** | 0.175 / 0.175 | one round 0.575 -> 0.85 |
| **prone pistol reload** (DECLARED; every pistol incl. the held-out C96 and M10) | 1.4 -> **2.4** (Beretta **2.075**) | +0.875 -> +0.825 (Beretta +2.050, C96 +1.450 = their standing values) | equal | as long as standing |
| Mauser C96, S&W M10 (held out), standing / crouched | 2.4 / 2.4 | +1.450 / +1.850, unchanged | equal | equal; hands clips and sight trace identical to the baseline |
| G 43 Irons (+ gold, Flecktarn) against the scoped G43 | 2.9 / 2.9 | +1.675 / +1.675 | 0.2 / 0.2 | equal (the lane's 1.70 / 2.90) |
| Shotgun (+ gold, winter) with step 7 | 5 shells 5.175 / 5.175; break-offs as pass 1 | +1.200 ... +3.800 / the same | shot to shot 1.15-1.175 / 1.15-1.175 | equal, 18 of 18 phases |
| pass-1 guns and out-of-scope guns, ADS-final cgame d3832aeb (run f9) | BAR 3.25, StG 44 2.75, DP-28 3.25, Silenced MP40 2.5, Kar98 3.35, Mosin 3.05, Thompson 2.6, Sten 3.0, MP18 2.5, Garand 2.0, FG 42 2.325, scoped G43 2.9 | the pass-1 figures | equal | 104 phases equal to b3; the 14 others = the declared prone (5) and Nagant (6) changes, the Sten's burst of 4 instead of 3 (2; pass 1 saw the same jitter) and one Thompson trigger hold 3.3 s against 3.125 (re-run f9b: 3.1, equal) |
| the FINAL cgame e81f6925 (ADS steps + rain fix), downpour pinned (run r9) | Colt 45, Welrod, G 43 Irons, shotgun | | | 36 of 36 phases equal to the step runs p4 / f5 / s7 |

Variants and finishes run: each equals its base gun in all 8 phases (`per_gun_b3_vs_p4.txt`).
**Declared server-side changes - say them to the user** (lane doc D2, coordinator-approved): the Webley / Mk VI /
Nagant per-round pace and the prone pistol reload, numbers above. New in the weapon tiks and server-visible but
without a timing effect (measured): `idle_empty` (1 frame) for P38, TT-33, Luger, Nambu, Silenced Beretta.

### Client side
* Aimed trace (`aimed_client_trace_*.txt`): the new clips are in effect (Colt: the sight line leaves the eye line by
  1.76 deg during the aimed reload, was 1.29; back to 0.00 at the end for every pistol); the revolvers,
  Hi-Standard, emptied Luger / Welrod work the action low by design (14-30 deg, back to 0.00). C96 and M10: the
  baseline's figures to the hundredth. The client's round count matches the server's everywhere.
* G 43 Irons: 3.01 deg during the aimed reload, back to 0.00; `step5_g43irons_aim_f5_and_armory_u5.jpg` (looked at:
  front post in the rear notch; armory tile, name, bars, PRIMARY 1).
* Shotgun: `step7_shotgun_pump_aim_and_hip_s7b.jpg` (looked at) - 0.45 s after aimed shots 1, 3 and 5 (the last
  shell) the hull is in the air and the support hand is at the rear of its stroke; the same after three hip shots.
* Unlock path of the irons (`unlock_*.txt`): empty profile - locked at rank 0 and at rank 1 (1192 XP), a click is
  refused; a real `xp_award` promotes to rank 2 and the server has it unlocked. Rank-5 profile (the connect
  backfill grants it): tile picked (`coop_lo1` 78), the map again: spawns holding `coop_g43_irons.tik`; Flecktarn
  variant locked, then 225 kills on the scoped G43's counter, the map again: spawns holding
  `coop_g43_irons_dhg43fleck.tik`.

## Not verified / open
* **G 43 Irons, the tile right after an in-map promotion (bug-3888):** on the empty profile the CLIENT's padlock
  stayed on for at least 28 s after the promotion (`coop_loLkA78` still locked, click refused) although the server
  had the rifle unlocked; after the next map load the padlock was off. The lane's run rb46 saw the click accepted in
  the same map. Not determined whether the armory's unlock export after a promotion is at fault for every rank
  reward or the harness; nothing in that path was changed. A finish applied through the armory: not run (finishes
  are global challenge unlocks; the gold tik was run directly). Loot picture: not seen in game (no enemy drop in
  the harness).
* Shotgun pump: stills only (shots 1, 3, 5 aimed; 3 at the hip) - the harness cannot trace the client-only cycle
  id on this branch (bug-3889); sprint / weapon switch / aim let go in mid-pump not run; third person not looked at.
* Pistols: leans, braced rows, the vehicle seat, third person, a second client were not run here (the lane's own
  evidence stands); 29 of 98 tiks were run in the engine (all covered by file and row length); sounds not listened
  to. The dedicated run compares server-side phases; the client's own trace was not read for it.
* d3, f9, s7 ran the cgame d3832aeb (every ADS step); the rain-fix merge after them touches three weather files
  only, and r9 re-ran four guns on the final DLL - the dedicated server was not re-run on e81f6925.
* `models/weapons/mp40silenced.tik` (a pass-1 file, as deployed) prints `TIKI_ParseSetup: unknown setup command
  '****...'` on load (9 lines in f9, 8 in pass 1's own run f1) - not from this pass, not fixed here.
* A client WITHOUT this cgame on a server with the new pak; the MP armory for the irons (not staged by the lane).
* Step 6 (FG 42 pair) and the double barrel (`docs/proposals/dbshotgun_2026-10-12/DBS_SHIP.md`): not started.
  `integ-ads` is at 14fb0dde (beyond 8327e12b), so `dbshotgun-next` 1dc10936 is a normal merge now.

## Rebuild / back out
```
python integrate_ads.py --dry-run                 # every file, entry kind, gun (steps 1-3 report "kept" - frozen)
python integrate_ads.py --steps 4,5,7             # fixes sources + manifest (idempotent); --mod-patches for step 4's state file
python apply_armory5.py                           # step 5, code-pak side (idempotent; --verify <lane scratch new tree>)
python ../../../tools/gen_fixes_pak.py restore ; build ; check
git -C hzm-mohaa-coop-mod checkout -- models/player/base/
```
Back out one step (each is separate commits): step 7 = `git revert d2d8295` (docs) + `git revert e7860c83`
(engine), rebuild the pak; step 5 = `git revert 17761c3a` (mod) + docs fb469d7 + engine 8327e12b (47acac77 is an
empty merge); step 4 = mod 99ba8027 + docs ff293d1 + engine merge 37e5dde8 (`git revert -m 1`) - the state file and
the pak's `anims_shared.txt` / `anims_pistol.txt` rows go together. Never `git checkout` a fixes source (autocrlf).

## Engine runs of pass 2 (`run_int.py`, harness `G:\mohaa-hudfeed`, port 12701; dedicated 12702)
b3 = pass-1 build; p4 = step 4; f5 = step 5; u5 / u5b / u5c = unlock path (`run_int.py unlock [--fresh]`);
s7 / s7b = step 7 (`--pumpsheet`); d3 = dedicated (cgame d3832aeb); f9 / f9b = regression (d3832aeb);
r9 = the final cgame e81f6925 with the downpour pinned (`--weather 4`). Run folders:
`H:\hzm_archive\integrate\`.

---

# ADS / aimed-reload ROLLOUT - integration of the finished guns (2026-10-13)

**State: steps 1, 2 and 3 are IN and verified. Nothing is deployed, nothing is published.** The set is staged for the
coordinator: engine branch `integ-ads`, binaries in `built_integ8`, fixes sources + manifest in `docs/tools/assets/fixes`,
the built pak in the mod tree, one mod commit.

| what | where | id |
|---|---|---|
| engine | `C:\mohaa-coop-dev\openmohaa-hzm-integads`, branch `integ-ads` (off `integ-1.10.22` 277bdb9d, which is untouched) | **bb5dc05f** |
| binaries | `<scratchpad>\built_integ8\` = `built_integ7` + the new `cgame.dll` (nothing else rebuilt) | cgame **a7c8c1e6**a0d6c7a8f17db9e69d34fc01 |
| mod (code pak) | `hzm-mohaa-coop-mod`, branch `coop-wip` - `coop_mod/player_torso.st` (shotgun break-off patch) | **02405cef** |
| fixes pak | `hzm-mohaa-coop-mod\zzzzzzzzzz_coop_fixes.pk3` - 223 members, 6 965 416 bytes | md5 **d1b75d08**2122ed947fe1bd66816899bd |
| released reference | docs repo 806c4ae (30 members) = `intlib.RELEASED_REV` | |

Other md5s of `built_integ8` (unchanged from `built_integ7`): `game.dll` 6b515fbf, `openmohaa.exe` 5cd827eb,
`omohaaded.exe` 9ebd2043, `renderer_opengl1.dll` a15882c4, `renderer_opengl2.dll` 8296bf86.

## What ships, per gun (every finish and model-variant tik; the full list with entry kinds is `FILELIST.txt`)
`FILELIST.txt` = `python integrate_ads.py --dry-run` (202 files; regenerate it, do not edit it).

| step | gun | tiks covered | what the player gets |
|---|---|---|---|
| 1 heavy | BAR | 12: `bar`, 7 finishes, `bar_bar1918a` / `a1` / `a2`, `bar_pabar` (the Lewis, `bar_bar1918`, is another gun and untouched) | aimed reload rounds-left / emptied (handle hauled) / braced, new aim pose (BAR only) |
| 1 heavy | StG 44 | 12: `mp44`, 7 finishes, `dhstg44ss`, `guanmp44`, `lv_ttmp44`, `mp44strap` | the same; hip reload no longer cocks with rounds left |
| 1 heavy | DP-28 | 8: `dp28` + 7 finishes | the same (pan), new aim pose |
| 1 heavy | Shotgun | 14: `shotgun`, 7 finishes, `authwinch`, `dhshotblack`, `dhshotchrome`, `guanshotty`, `hobbsshotty`, `lv_ttshotgun` | groove + brass bead sight (one mesh), aimed reload shell by shell, pump only when emptied, **fire breaks the reload off** |
| 2 smg | MP40 | 11: `mp40`, 7 finishes, `guanmp40`, `guanmp40s`, `lv_mp75` | open-bolt handle on the mesh (moves per shot, forward when empty), aimed + hip reloads, aim pose |
| 2 smg | Silenced MP40 | 1: `mp40silenced` (it has no finish tik) | raised-sights mesh + its sight row (in the cgame), reloads, aim pose |
| 2 smg | MP40 R2 | 1: `mp40_mp40r2` | reloads |
| 3 rifles | Kar98 | 19: `kar98`, 7 finishes, `kar98_lite` + its 7, `hobbskarwood`, `hobbskarworn`, `lv_ttkar98` | the bolt cycle between shots stays on the sights (capped gun clip `rechamber_ads`) |
| 3 rifles | Springfield | 1: `springfield_unscoped` | the same |
| 3 rifles | Mosin | 18 | the same |
| 3 rifles | Lee-Enfield | 18 | the same |

Coverage is proved by the script (op `C`: every mod-tree tik whose weapon name is the gun's, or the gun's with a
"(finish)"), not by this table. Left as released ON PURPOSE: `mp40_mp18` (MP18), `kar98_g98`, `enfield_p14` (own
meshes - the cgame's mesh guard keeps them on the hip bolt clip; run `g98` in f2 shows it: 20.6 deg against 1.2).

**NOT shipped** (and proved absent / inert, see the gates): FG 42 + FG 42 Irons, belt-feds, Vickers / Breda aim poses,
Thompson, Sten, MP18 mesh / rows, PPSh / Moschetto / Type 100 aim poses, the Kar98 aimed reload, G 43 Irons, pistols,
the double-barrel shotgun. **The lifted BAR skin is NOT shipped**: `S93_bar.dds` is carried by
`zzzzzzzzzz_coop_hd_m3l1a.pk3`, and the engine's pak order puts `zzzzzzzzzz_coop_fixes` BELOW it (`coop_f` < `coop_h`),
so an override there is dead; that pak is off limits. The BAR ships with its released (dark) skin.

## Three things the integration does differently from the lane folders (all in `integrate_ads.py`, lanes untouched)
1. **Shared-prefix rows became per-weapon rows.** The heavy lane repoints `bar_charge` and the smg lane the generic
   `mp40_*` rows; `bar` is the fallback prefix of every other MG-class gun (Lewis, M1919, MG42 portable) and `mp40` is
   also the Grease Guns, the Silenced PPS-43 and the MP18. Those guns are not part of the rollout, so the generic rows
   and the released clip `MP40/mp40_reload_ads.skc` stay as released, and the same clips ship as `coopr_bar_charge`,
   `coopr_mp40_{charge,reload,reload_empty,reload_ads,reload_empty_ads}` (the aimed clip under its own file name
   `coop_mp40_reload_ads.skc`), `coopr_silenced_mp40_charge`. The MP18's name strips to "MP40", so it is pinned to
   the released aim pose by `coopr_mp40_mp18_charge`. Proof: `rowpick.py`.
2. **The Kar98 tiks lose a block.** The 19 staged Kar98 tiks also carry the gun rows of the Kar98 aimed RELOAD
   (`reload_ads_loaded` / `reload_ads_empty` -> a clip that does not ship); the marked block is cut out.
3. **Cosmetic repairs**: three BAR variant tiks are written with one line ending (the released files are mixed and the
   generator refuses that), the two shotgun sight `.tga` headers get their top-down bit cleared (the engine ignored
   it with a warning on every load), and the MP18 sight row on `integ-ads` is back at the released values (the smg
   lane raised it for a mesh that does not ship).

## Gates and their evidence (`evidence/`)
| gate | tool | result |
|---|---|---|
| 1a server timing, static | `rowlen_check.py --intended "shotgun_reload_break,mp40*.tik:fire,mp40*.tik:fire_empty,mp40*.tik:idle_empty"` -> `rowlen_table.txt` | 889 rows in 116 files: 656 untouched, 172 new client-only rows, 21 repointed rows of the SAME length, and the intended ones below. No `reload` / `reload_single` / `reload_end` / `rechamber` / `idle` row changed length |
| 1b server timing, measured | `run_int.py cmp` -> `timing_measured.txt` (server-side probe: torso state + reserve ammo, 25 ms frames) | 314 phase comparisons, 299 equal within one server frame; the 15 others are the shotgun's intended change (10) and scenario jitter on the Sten (5, see below) |
| 2 regression | `rowpick.py` -> `rowpick.txt`; `inert_check.py` -> `inert.txt`; runs f1 / f2 | 19 weapons outside the rollout resolve to the same hands-clip BYTES in every case; every name the merged cgame newly reacts to belongs to a rollout gun (552 weapon tiks scanned); Colt .45, Thompson, Sten, Garand, FG 42, Lewis, MP18, Grease Gun, Silenced PPS-43, Gewehr 98: same server timing as released |
| 3 each gun in the engine | runs f1 / f2 (integrated build + the REAL pak) -> `aimed_client_trace.txt`, `errors_vs_baseline.txt` | 24 in-scope guns / variants in the final runs (27 tiks with the step runs i1 / i2): hip + aim, fire, hip + aimed reload rounds-left + emptied, crouched; 0 `Script Error`; 0 error-like log lines that the released sessions do not have |
| 4 dedicated server + one client | `run_int.py ded` runs d2 (integrated) and d0 (released) | boots, mission starts, client joins and spawns; BAR, shotgun (incl. both break-offs), MP40, Kar98: 34 phases equal to the listen runs, 16 equal to the released dedicated run; 0 Script Error on server and client |
| 5 build checks | `check_mp_isolation.py --engine openmohaa-hzm-integads` (+ selftest), `scrlint`, `check_empty_rhs`, `check_tik_surfaces`, `ads_audit`, `unlock_audit`, `gen_fixes_pak.py check` | 22 passed, 0 pending, 0 FAILED; scanners clean; pak byte-identical to a rebuild. `build.ps1` was NOT run |

### Server timing, released against integrated (measured; s = seconds of server time)
| gun | reload start -> done | ammo refilled at | fire / bolt state | verdict |
|---|---|---|---|---|
| BAR (+ M1918A2, Pacific) | 3.25 / 3.25 | +1.575 / +1.575 | 20 rounds in 4.075 / 4.075 | equal |
| StG 44 (+ strapped, gold) | 2.75 / 2.75 | +1.350 / +1.350 | 30 rounds in 5.675 / 5.675 | equal |
| DP-28 | 3.25 / 3.25 | equal | equal | equal |
| Shotgun, 2 shells | 3.225 / 3.225 | +0.900, +1.550 / **+1.200, +1.850** | 1.15-1.175 / 1.15-1.175 per shot | total equal; each shell is counted 0.30 s later (INTENDED) |
| Shotgun, 5 shells | 5.175 / 5.175 | +0.900 ... +3.500 / **+1.200 ... +3.800** | | the same |
| MP40 (+ gold) | 2.5 / 2.5 | +2.125 / +2.125 | 32 rounds in 6.0-6.025 / 6.0-6.025 | equal |
| Silenced MP40, MP40 R2 | 2.5 / 2.5 | +2.125 / +2.125 | equal | equal |
| Kar98 (+ lite, winter) | 3.35 / 3.35 | +1.650 / +1.650 | shot 0.2 + bolt 1.1 / the same | equal |
| Springfield | 3.95 (2 rounds) / 3.95 | +1.850, +2.500 / the same | bolt 1.85 / 1.85 | equal |
| Mosin (+ gold, lite) | 3.05 / 3.05 | +2.475 / +2.475 | bolt 1.475 / 1.475 | equal |
| Lee-Enfield (+ gold, lite) | 3.85 / 3.85 | +2.650 / +2.650 | bolt 1.475 / 1.475 | equal |
| out of scope: Colt .45 2.4, Thompson, Sten 3.0, Garand 2.0, FG 42 2.325, Lewis 3.25, MP18, Grease Gun, Silenced PPS-43, Gewehr 98 | equal | equal | equal | equal |

**The two intended server-side changes - say them to the user:**
* **Shotgun** (`anims_shotgun.txt` + the state patch): a shell is counted when it is in the gate (loop frame 14,
  was frame 5) - a full reload takes the same time, a loop broken off before that no longer keeps its shell.
  **Fire breaks the reload off**: with a round chambered 0.35 s of server time from the press to the shot state
  (`RELOAD_SHOTGUN_BREAK_QUICK`), when the gun was empty 1.175 s with the pump (`RELOAD_SHOTGUN_BREAK_END`)
  (`shotgun_breakoff.txt`). The released build ran the reload on. This is in the shared state file
  `coop_mod/player_torso.st`, which the mod's own multiplayer mode uses too (`mp.scr` sets `g_statefile coop_mod/player`).
* **MP40 family** (13 tiks): the gun's `fire` clip is 0.10 s (was 3.03 s / 2.91 s / 0.17 s) and the tiks gain
  `fire_empty` / `idle_empty`, which the server picks for the last round. In fgame the end of the fire clip only calls
  `DoneFiring -> ForceIdle`; the firing state is never tested and the rate of fire runs on `next_fire_time`.
  Measured: no difference (table above), the last round still fires (32 refilled).
The Sten's 5 "different" phases in `timing_measured.txt`: the 250 ms burst fired 4 rounds instead of 3 and the long
trigger hold of the emptied phase (5.70 s) outlasted empty + reload (5.675 s) by a frame, so one more round went
off; its reload (3.0 s) and refill (+2.35 s) are the released figures, and run i2 (same build) has all 8 phases equal.

Client side (`aimed_client_trace.txt`, merged cgame only): the sight line leaves the eye line by 6.2-6.5 deg (BAR),
4.8-5.2 (StG 44), 5.7 (DP-28), 6.9 (shotgun) during the aimed reload and is back where it was; the aimed bolt cycle
stays within 0.8-1.2 deg (Gewehr 98 on the released clip: 20.6); the client's round count matches the server's.

## Rebuild / back out
```
python integrate_ads.py --dry-run            # what would be written
python integrate_ads.py [--steps 1,2,3]      # fixes sources + manifest (idempotent)
python ../../../tools/gen_fixes_pak.py restore ; build ; check
git -C hzm-mohaa-coop-mod checkout -- models/player/base/     # restore rewrites the pinned bases
python integrate_ads.py --reset              # BACK OUT everything to the released sources (added files are moved, not deleted)
```
To drop one step: `--reset`, then `--steps` with the ones that stay, rebuild. Step 1's state patch is backed out
with `git revert 02405cef` in the mod repo (the patched state file plays the row `shotgun_reload_break`, which only
the step-1 pak has - the two go together). The engine merges are separate commits on `integ-ads`
(0517f3f9 heavy, 2fca9d3e smg, fae83add rifles, bb5dc05f MP18 row).
`gen_fixes_pak.py check` at rest (after the `git checkout` above) reports the two pinned row files
`fps_anims_rifle.txt` / `fps_anims_smg.txt` as changed - it did before this work too; it passes after `restore`.
**Trap**: never put a fixes source back with `git checkout` / `git restore` - `core.autocrlf` rewrites its line
endings and the pins are made from the bytes on disk (`released_style.json`, bug-3819).

## Engine runs (`run_int.py`, harness `G:\mohaa-hudfeed`, owner hudfeed, port 12701; dedicated 12702)
b1, b2 = released build (`built_integ7` + fixes @806c4ae + mod 237adcc2); i1 = step 1, i2 = steps 1+2,
f1 / f2 = the final set; d0 / d2 = dedicated, released / final (d1: markers were not logged, superseded).
Run folders: `H:\hzm_archive\integrate\`. One engine screenshot per step in `evidence/`.

## A later step 4 (pistols) - what to watch
* Add `step4()` + one line in `STEPS`; nothing in steps 1-3 changes. `rowlen_check.py` takes any tik list.
* The pistols' blocker is exactly what `rowlen_check.py` fails on: a `reload` row of another length.
* `colt45` is a fallback prefix like `bar` / `mp40`: ship per-weapon rows, extend `rowpick.WEAPONS` and
  `inert_check.OWNERS`, and expect `inert_check` to flag every `*_empty`, `*_cycle_ads` and `coopr_*_charge` row.
* `fps_anims_pistol.txt` is already a fixes source: merge rows (op `R`), never copy the lane file.
* Merged cgame, the places every lane touched (a merge of `ads-next` 2627cb94 lands in all of them):
  `cg_viewmodelanim.c` - `CG_GetVMAnimPrefixIndex`; in `CG_ViewModelAnimation` the per-weapon row block (the rifles
  lane already added `VM_ANIM_CHARGE` to the reload branch "as ads-next does", the smg lane added the `else` for
  every other animation: keep ONE charge condition), the `_empty` block, the heavy lane's `_loaded` / `_break` block
  with `s_coopReloadFromEmpty` / `s_coopReloadBreak`, the `_ads` / `_adsb` choice (with the client-only id
  `COOP_VM_ANIM_CYCLE` 16) behind `CoopAdsClipFitsHeldGun`, and the `CG_VMAdsBolt*` helpers;
  `cg_modelanim.c` - the gun-row swaps (`reload_ads_loaded` / `_empty`, `reload_empty`, `reload_end_ads` /
  `reload_single_ads`, `reload_end_loaded`, `rechamber_ads`); `cg_view.c` - `CG_AdsRigSolve`;
  `cg_adssights.h` - a generated table: merge by rows (the MP18 row is deliberately the released one here).

## Not verified
* Nothing was LOOKED AT beyond one aim still per step: the lanes' own playback evidence stands for how the clips look.
  No sound was listened to. No third-person / second-client view.
* Stances: standing and crouched aimed; prone, leans and the braced rows (`*_adsb`) were not run here (static
  resolution only, `rowpick.txt`).
* Variants run in the engine: a sample (27 of 115 tiks); all 115 are covered by file and by row length.
* `bar_bar1918a` / `a1`, the other StG 44 / shotgun / MP40 finishes, 16 of 19 Kar98, 15 of 18 Mosin / Enfield tiks:
  not run (same mesh, same rows as the ones that were).
* Break-offs other than the shotgun's; weapon switch / sprint during a reload.
* A client WITHOUT this cgame on a server with the new pak (the patch tool says it plays the normal end row).
* The settled aim of the MP40, Kar98, strapped StG 44 and the shotgun sits 0.4-0.7 deg off the eye line by its sight
  row's `delta` - those rows are the released ones (except the shotgun's, by design); not compared by eye.
