# HANDOVER (2026-10-13 morning, PISTOL lane, after the server-side fix and the SHIP CUT) - read this first

**`PISTOLS_SHIP.md` is the ship cut; the folder `ship/` is FROZEN** (an integration agent reads it). Rebuild it only
with `tools/shipcut.py` and only when told to. `assets/` stays the lane's full working image (C96, M10 included).

* Engine: `ads-next` **e8e199be** = `G:\mohaa-adsanim\cgames\cgame_adsnext13.dll` (client clip clock + server probe).
  `cgame_adsnext12.dll` is an intermediate build of the same morning (no second start): do not use it.
* RUN IDS used today: pa21 (stand, Welrod / TT-33 / silenced TT-33 + interruptions), pa22 (aborted at boot, empty
  folder - wrong shot count), pa23 (stances: PPK, TT-33, Pacific Colt, silenced Colt, silenced P38, P38), pa24 (the
  cut's hold-outs). Dedicated: pa21s / pa21t / pa21u (harness bring-up), pa21a (cgame 12), **pa21b** (the proof).
  **pa25 is next.**
* Run folders: pa1-pa17 were moved to `G:\_hzm_delete_me\pistols\` at 08:1x and from there by the coordinator to
  `H:\hzm_archive\pistols\`. pa18-pa24 are still in `G:\mohaa-adsanim\runs`; finished ones go to `H:\hzm_archive\pistols\`
  (move, in the background; nothing is deleted). The dedicated logs are in `SCRATCH\pistols\ded\<id>` (small).
* Working copies: `SCRATCH\ads2h` (synced into `tools/`). Overlays: `ov_f2.pk3` = the full stage (PPK row, revolver
  finish tiks), `ov_cut2.pk3` = the ship cut, `ovbase_1021.pk3` = harness plumbing only (= the released game).

## 1. Server side: DONE and proven (bug-3782)

* What it was, measured: the weapon entity of the old staged Welrod showed `fire` for 875 ms after a shot (released
  50) and `reload` for 2400 ms (released: shorter than a snapshot); the TT-33 `reload` 2400 ms (released 1500). The
  clip refill (850 ms after the hands' reload starts) and the shot gaps were NOT changed - the refill comes from the
  torso row's `clip_fill` frame command, not from the weapon's row (the earlier handover had that wrong, bug-3783).
* Fix: `reload` / `fire` are the released clips again in 8 Welrod + 16 TT-33 tiks (`tools/patch_srvrows.py` patches
  `p12.py` / `welrod.py`); the 73- / 26-frame clips are client rows only. cgame: `CoopGunLatchSee / Apply`
  (`cg_modelanim.c`): a swapped clip longer than the server's row is kept on a client clock; a second start from the
  hands' VM_ANIM_RELOAD because a one-frame server row is never seen in a snapshot on a dedicated server.
  `coop_vmGunClipClock` 2 prints `GUNCLOCK start / end`.
* Checker: `python tools/srvrows.py <tree>` - every row of every staged weapon tik and player table against the
  released file; exit 1 on a difference. `DECLARED` in it = the decided server-side changes (revolver pace, prone
  reload, M10 round by round); `BASES` = the mod commits the shared snapshots were taken from (3-way merge).
  Stage and ship: 0 FAIL.
* Dedicated proof: `python tools/run_ded.py <id> --arm rel=ovbase_1021.pk3 --arm staged=<ov> [--arm old=<ov>]`, then
  `python tools/dedcmp.py SCRATCH\pistols\ded\<id>`. Table: `evidence/ded_pa21b/dedcmp.md`, condensed in
  `PISTOLS_SHIP.md` D1. Harness facts that cost runs: `wait N` is MILLISECONDS; several rcon lines in one frame are
  dropped (one `rcon exec`); the first give lands before the spawn is complete (thrown away); a `reload` typed inside
  a fire delay is dropped.

## 2. What else changed today

* **PPK**: own emptied hands row `coopr_walther_ppk_reload_empty_ads` (`rows_p12_ppk.txt`; the Colt clip baked with
  `PB_THUMB=0.15` into a temp root, copied as `coop_ppk_reload_empty_ads.skc`). pa23: 0.1 / 0.1 / 0.1 / 0.3 / 0.2 %.
  The thumb on the slide stop was not looked at up close.
* **`centrebox.py`**: the dry-pose rule is the default for emptied reloads (`--nodry` = the old figure). pa20 re-read:
  everything under 2 % (Beretta lean R 0.1).
* **Stances measured** (pa23): TT-33, Pacific Colt, silenced Colt (lean L 2.4 % = muzzle smoke, frames looked at),
  silenced P38, P38. Table in `PISTOLS_SHIP.md` A.
* **Finish / variant coverage** (user: "all of these new guns will need their camo/variants too"):
  `tools/variants.py <tree>` lists it; `tools/finishclone.py <tree> <base>` staged the 21 revolver finish tiks (M10,
  Webley, Nagant - not run). OPEN: Trench C96, Webley Mk VI (`colt45_colt1911w`), `webley_revolver_lv_ttwebley` have
  no staged tik; the Welrod's and the Beretta's bloody / camo finishes use their own sheets, not lifted
  (`evidence/variants_coverage_pa21.md`).
* **Shared snapshots**: `anims_shared.txt` and `player_Torso.st` in the stage are snapshots of mod 6cf61e58 /
  12e9faf6; the mod tree has moved (bug-3788). Never copy them over the mod tree: 3-way merge.

## 3. NOT done (the list from here, in the coordinator's order)

1. **C96 on the existing prop** - not started. Recipe: `tools/c96.py` parks `tag_weapon_left` (`tag_park`); instead
   key it rigid to the support hand with the transform that makes it equal `tag_weapon_right` at frame 41
   (inv(hand_41) x tag_right_41), re-time `K` to the server's timeline in `anims_shared.txt` (28 clip on the left
   tag, 41 on the gun, 44 swapped for the empty one + ammo, 47 back to the hand, 56 gone), drop the gun-side strip /
   rounds surfaces of `c96clip.py` (keep the bolt bar, 2.0 u, and the port), turn the lowered gun so the clip is seen
   from the side with the hand behind it. CHECK FIRST: `rows_p12_c96.txt` re-declares `coopr_mauser_c96_reload` as
   `reload_p38.skc` while the released table has it as `viewmodel/coop_reload/c96_reload.skc` (the phase-B hip
   stripper reload) - which row wins was not looked at; the staged HIP reload of the C96 may be a regression.
   Trench C96: same parts + the white patch at the rear.
2. The five checks nobody ran (item 5 of the brief): sprint / aim-dropped out of the new clips, hip view of emptied
   guns, Hi-Standard after its re-bake, Welrod second shot during the cycle / bolt sound / hip side, M10 in third
   person. Done of it today (pa21): fire and weapon switch during an aimed reload of Welrod / TT-33.
3. Luger per-shot toggle flick (a client-only `fire_ads` now works on the clock), front link.
4. Braced / crouch-leans / seat / LOADED reloads in the stances against the sway envelope, for all.
5. Finish gaps above; texture lifts for the finishes' own sheets if the lifts are approved.

## Awaiting the user

Welrod and Luger aim poses (in the cut, not separable); texture lifts (out of the cut, `ship_awaiting_approval/`);
Welrod bolt sound; the decided server-side changes of `PISTOLS_SHIP.md` D2 if "exactly as released" is meant for
them too; whether the M10 may ship with six heads seen by other players.

Bugs of this session: bug-3782 (server rows, fixed), 3783 (handover's released figures wrong), 3784 (`wait` is ms,
rcon, harness), 3785 (heredoc newline in C strings, repeat), 3786 (v14 clip header hang), 3787 (revolver finish tiks
never staged), 3788 (shared snapshots would revert other lanes).

---

# HANDOVER (2026-10-13 early morning, PISTOL lane) - SUPERSEDED by the section above; history from here on
