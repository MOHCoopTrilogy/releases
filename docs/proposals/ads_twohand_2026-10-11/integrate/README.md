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
