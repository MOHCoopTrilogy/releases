# PISTOLS - SHIP CUT v2 (2026-10-13, pistol lane)

**v2** (after the coordinator's review of v1, commit a4764af): the two guns that v1 shipped "in a partial state" are
staged and run - `webley_revolver_lv_ttwebley.tik` (the Webley tik with that skin's lines) and the Webley Mk VI
`colt45_colt1911w.tik` (its own gun clips retimed onto the Webley's frames, `tools/mk6.py`); a sample of the finish
tiks written by rule and three model variants were run in the engine (runs pa25, pa27, pa28). Nothing else changed.
The coordinator's calls on v1 are recorded in D2 and E.

**The files of this cut are FROZEN from the commit that adds this version.** The cut is the folder `ship/` beside this
file, built by `tools/shipcut.py` from the lane's staged tree (`assets/` is the lane's full working tree and goes on
changing - do not read the shipped pistols from there). Engine: branch `ads-next` at **e8e199be**.

The server-side blocker is solved and proven (section D). What is IN, what is held OUT, what could not be separated
and what the user has not approved yet is listed below in plain terms. Nothing here was played by a person; every
figure is from the engine harness (private copy `G:\mohaa-adsanim`, engine `screenshot` frames) or from a dedicated
server + one client on this machine.

## A. Pistols in the cut

Aim pose (two-handed) + aimed reload + working action, measured in stand / crouch / prone / lean left / lean right.
Figure = the worst frame's cover of the centre box BEYOND the settled aim's sway envelope, per cent, sway on, an
EMPTIED gun's own locked-back pose counted as part of the reference (the lanes' rule; bar: under 2).

| pistol | loaded reload, stand | emptied reload: stand / crouch / prone / lean L / lean R | runs | notes |
|---|---|---|---|---|
| Colt 45 | 0.0 | 0.8 / 0.1 / 0.1 / 0.3 / 0.2 | pa18, pa20 | stand figure is from before the dry-pose rule |
| Colt 45 (Pacific) | 0.1 | 0.2 / 0.1 / 0.0 / 1.2 / 0.2 | pa18, pa23 | |
| Silenced Colt .45 | 0.0 | 0.1 / 0.1 / 0.0 / **2.4** / 0.2 | pa18, pa23 | lean L: 7 frames at 2.0-2.4 % = the last shot's muzzle smoke drifting through the box; no hand in it, gun as in its dry pose (frames looked at) |
| Walther P38 | 0.1 | 0.1 / 0.1 / 0.1 / 0.3 / 0.3 | pa18, pa23 | breech block fills the slide's rear slot |
| Silenced Walther P38 | 0.0 | 0.1 / 0.1 / 0.2 / 0.4 / 0.3 | pa19, pa23 | steel block fills the open slide's slot (not looked at up close in the engine) |
| Beretta | 0.0 | 1.3 / 0.2 / 0.1 / 0.5 / 0.1 | pa18, pa20 | stand figure is from before the dry-pose rule |
| Silenced Beretta | 0.0 | 0.8 / 0.1 / 0.0 / 0.5 / 0.2 | pa18, pa20 | |
| Luger P08 | 0.0 | 0.0 / 0.1 / 0.1 / 0.3 / 0.3 | pa19, pa20 | toggle on two bones; emptied reload worked under the box; no per-shot toggle flick, front link not articulated; **aim pose not approved yet** |
| Silenced Luger P08 | 0.0 | 0.2 / 0.1 / 0.1 / 0.4 / 0.3 | pa19, pa20 | as the Luger |
| Nambu Type 14 | 0.0 | 0.0 / 0.0 / 0.1 / 0.3 / 0.3 | pa18, pa20 | bolt on its own bone |
| Walther PPK | 0.0 | 0.1 / 0.1 / 0.1 / 0.3 / 0.2 | pa18, pa23 | NEW today: its own emptied hands row (the Colt clip with the support thumb lower); was 1.4 / 2.3 / 2.7 / 2.3 / 0.5. The thumb on the slide stop was not looked at up close |
| TT-33 Tokarev | 0.0 | 0.1 / 0.0 / 0.1 / 0.3 / 0.3 | pa21, pa23 | server rows back to released (section D) |
| Silenced TT-33 | 0.0 | 0.0 / 0.6 / 0.0 / 0.4 / 0.2 | pa21, pa20 | server rows back to released |
| Welrod | 0.0 | 0.0 / 0.5 / 0.3 / 0.3 / 0.2 | pa21, pa20 | bolt worked by the support hand after every aimed shot (0.4 %) and after an emptied reload; server rows back to released; **aim pose not approved yet**; no bolt sound |
| Hi-Standard Silenced | 0.3 (tl8) | 0.5 at most in the five stances (tl8) | tl8 | measured with the EARLIER fixed-reference measure, not the sway envelope; racked by hand after every aimed shot and after a reload; not re-checked today |
| Webley Revolver | 0.2 (tk4) | 0.3 at most in the five stances (tn1) | tn1, ts1 | earlier measure; carries a decided server-side pace change (section D2) |
| Nagant Revolver | 1.7 (tk10) | 1.7 at most in the five stances (tn3) | tn3, tu1 | earlier measure; the cradling forearm is large for 0.1 s at the hand-over; carries a decided server-side pace change (section D2) |
| Webley Mk VI | not measured | not measured | pa28 (stand: aimed + hip, looked at) | v2: on the Webley's rows with its own gun clips retimed; see "Variants and finishes" below |

Not measured against the sway envelope for ANY pistol: the LOADED reload in the stances, braced, crouch-leans, the
vehicle seat (those were run and looked at on stance sheets with the earlier measure: runs pa9, pa13-pa15, pa17).
Not run for any pistol: sprint / aim-dropped out of the aimed reload, the hip view of an emptied gun with the new gun
clips, third person. Run today (pa21, Welrod / TT-33 / silenced TT-33): a fire press during the aimed reload changes
nothing, a weapon switch drops the gun clip with the hands within a frame.

### Variants and finishes (v2: staged and sampled in the engine)

Run on the cut's own overlay, each gun: two aimed shots + aimed reload, then two hip shots + hip reload; no script
error and no failed animation load in any of the three logs; frames looked at on sheets.

| tik | what it is | run | seen |
|---|---|---|---|
| `colt45_colt1911w` (Webley Mk VI) | its own break-top mesh on the Webley hands and states | pa28 | NEW in v2. Its own gun clips retimed onto the Webley's frames: barrel tips over frames 8-19 (hip) / 6-18 (aimed), shuts over 11-20 / 5-15, cylinder turns over 15-23 of the 24-frame loop. Side by side with the Webley at the same capture frames (`evidence/mk6_vs_webley_open_close_pa28.jpg`) the two open and shut in step. The hands still reach for the Webley's barrel and chambers - the gun side is fitted, the hand points are not (as in run tx3). Its first try (pa25, warped to the clip's last frame) shut the barrel 0.2 s early and was replaced |
| `webley_revolver_lv_ttwebley` | a skin on the Webley's mesh | pa25 | NEW in v2 (`finishclone.py --also`): the staged Webley tik with that skin's shader and name lines; plays as the Webley, skin shows |
| `webley_revolver_gold`, `_camo_desert` | finish tiks written by rule | pa25 | play as the Webley, finish shows |
| `nagant_revolver_blued`, `_bloody` | finish tiks written by rule | pa25, pa27 | play as the Nagant, finish shows |
| `colt45_guancolt` | model variant of the Colt | pa27 | two-handed aim, aimed reload stays in the aim, hip reload as released |
| `p38_lv_ttp38` | model variant of the P38 | pa27 | same |
| `dbno_pistol` | the downed-state pistol (Colt rows) | pa27 | same |

Sheets: `evidence/variants_aimed_pa25.jpg` (the Mk VI row there is the replaced first try), `variants_hip_pa25.jpg`,
`variants_aimed_hip_pa27.jpg`, `mk6_aimed_hip_pa28.jpg`. GIF: `evidence/mk6_aimed_reload_pa28.gif`.
NOT run: the other 17 revolver finish tiks (same text as the sampled ones apart from the shader lines), `colt45_drbond`,
`_bloodyeic`, `_covert`, `_lv_ttcolt`, `p38_guanp38`, `it_w_beretta_lv_ttberetta`, the `dbno_pistol` finishes, and no
variant in any stance other than standing. The Mk VI has no measured centre-box figure; on the sheet its aimed reload
is worked under the box like the Webley's. Coverage per tik: `evidence/variants_coverage_ship.md`.

### Held OUT (they ship exactly as released; checked in the engine, run pa24, sheet `evidence/shipcut_heldout_m10_c96_trench_pa24.jpg`)

* **Mauser C96 and Trench C96** - the stripper clip is unfinished. Their tiks, mesh, clips, textures and hands rows are
  not in the cut. They share the P38 prefix, so one pin row keeps their released one-handed aim:
  `coopr_mauser_c96_charge -> viewmodel/p38pose00.skc` (in `ship/models/player/base/fps_anims_pistol.txt`). Their hip
  idle is the P38's new `idle2h` clip: only the left hand's finger channels differ and that hand is out of view.
* **S&W M10 and its seven finishes** - by the code another player always sees six chamber heads (not run). Tiks, mesh,
  textures, shader, hands rows are not in the cut and ONE line of `player_Torso.st` is removed (the line that sends
  the M10 to the round-by-round states), so it reloads on the released line. Three M10 torso clips stay in the cut
  because the shared tables still name them; nothing reaches them. pa24 shows the released one-handed aim and a
  reload that completes; it was not compared frame by frame with a run of the released game.
* The SMG lane's Sten aim files that sat in this tree (`fps_anims_smg.txt`, `viewmodel/sten/*`) are not in the cut.

## B. Files, rows and tiks per pistol

`ship/` holds {{NFILES}} files (5.4 MB); `ship/LEFT_OUT.txt` lists what the cut leaves out of the staged tree.
Shared files - **apply by 3-way merge, never by copying**: they are snapshots of mod-tree files that other lanes also
edit, and the mod tree has moved since (low-turret rows, the heavy lane's shotgun lines):

| file in `ship/` | snapshot of | how to apply |
|---|---|---|
| `coop_mod/player_Torso.st` | mod commit 12e9faf6 (`coop_mod/player_torso.st`) | `git merge-file ours base theirs`; merged cleanly against the mod tree at 09:30 today - that result is in `ship_merged/` for reference only |
| `models/player/base/anims_shared.txt` | mod commit 6cf61e58 | same |
| `models/player/base/fps_anims_pistol.txt` | `docs/tools/assets/fixes/models/player/base/fps_anims_pistol.txt` | built by `tools/mkov.py` = that file with the aim / idle rows repointed and the lane's rows appended; diff against it |
| `models/player/base/anims_pistol.txt` | the live pak's file | three revolver rows changed (section D2) |

{{SHIPLIST}}

New sounds (the "rounds left" reload sound = the gun's own reload sound cut before the slide): `sound/weapons/foley/coop_colt45_reload_loaded.wav`, `coop_p38_reload_loaded.wav`, `coop_beretta_reload_loaded.wav`, `coop_histandard_reload_loaded.wav`.

## C. Engine

Branch `ads-next`, worktree `C:\mohaa-coop-dev\openmohaa-hzm-ads`, cgame target only. `integ-ads` is three commits
behind it; all three are needed:

| commit | what | cvars it adds |
|---|---|---|
| d2a6d31b | revolver chambers fill one by one (only a mesh with `coop_round<N>` surfaces - the M10, which is held out) | `coop_vmRoundSurfaces` 1 |
| 2627cb94 | the per-weapon row `coopr_<weapon key>_<suffix>` also covers the aim pose (`charge`) and the aimed per-shot cycle - Luger and Welrod aim poses, Welrod bolt cycle, the C96 pin row of this cut | none |
| **e8e199be** | the client clip clock: a swapped gun clip that is longer than the server's row keeps playing on the client after the server's row has ended (section D) | `coop_vmGunClipClock` 1 (0 = off, 2 = print start / end); `coop_vmSrvProbe` 0 (test harness only) |

All of it is inert for a gun without the rows: the clock only starts when a tik has `reload_ads_loaded` /
`reload_ads_empty` / `reload_empty` / `fire_ads` AND that clip is longer than the tik's `reload` / `fire`. Local
player, display only; other players see the server's rows. Test DLL of e8e199be: `G:\mohaa-adsanim\cgames\cgame_adsnext13.dll`
(md5 f48a77a8...). Every run of today used it.

## D. Server side

### D1. The blocker

The lane had made the Welrod's `reload` and `fire` and the TT-33's `reload` longer so that the shown clip would not be
cut. The server holds its weapon state for exactly those rows. Now those rows are the released clips again in all 24
tiks (8 Welrod, 16 TT-33), and the long clips are client rows played on the cgame's own clock.

Checker - `python tools/srvrows.py ship` compares every row of every staged weapon tik and of the player tables with
the released file (frames x frame time from the clip headers, and the `server { }` block of each row). Result on the
cut: **{{CHECK}}** (the declared ones are D2). On the tree of the lane's commit 0910dd4 (before the fix) the same
checker gives 33 FAIL. Full output: `evidence/srvrows_ship_v2.txt`.

Dedicated server (`omohaaded` + the install's game.dll on 127.0.0.1, one client of the lane's build, run pa21b; three
arms: the released files, the staged tree after the fix, the staged tree before it). The trigger is pulsed every
100 ms for 18 s with one typed `reload`; the client prints what the server's snapshots say (clip, reserve, hands id,
the weapon entity's animation) with the server's time. Times in ms; the server runs 25 ms frames; shot gaps and "next
shot" hang on the 100 ms pulse, so they are equal within one pulse. `fire` row = how long the weapon entity shows
`fire` after a shot; `reload` row = how long it shows `reload` (0 = shorter than one snapshot).

{{DEDTABLE}}

Staged = released on every measure: 0 figures outside the tolerance (old staged: 25). No double shot in any arm, no
script error in any server log. The clip is refilled 850 ms after the hands' reload starts in every arm - the refill
comes from the player's torso row (`25 weaponcommand mainhand clip_fill`), not from the weapon's `reload` row; what
the old tiks changed was how long the weapon stayed in its reloading / firing state (Welrod 2.4 s and 0.875 s
instead of under 25 ms and 50 ms; TT-33 2.4 s instead of 1.5 s). Raw lines: `evidence/ded_pa21b/`.
In the staged arm the client clock ran every aimed reload to its end (2375-2407 ms of 2400) and every Welrod bolt
cycle to 825-841 ms of 866 (the hands' cycle ends 50 ms early by design).
NOT covered by the dedicated run: the cut itself (the run used the full staged tree before the PPK row, the revolver
finish tiks and the two hold-outs), the stances, the revolvers, two clients.
Seen and not new: the first aimed shot after a reload reports the hip fire id for the hands, so the Welrod shows no
bolt cycle on that one shot (released arm too).

### D2. Server-side changes that are DECIDED and are in the cut

These change what the server does, on purpose. They were decided on 2026-10-12 (coordinator, list item C and the
prone decision) and run on a listen server only. **Coordinator's call on v1 (2026-10-13): they STAY in the cut; the
user is told about them explicitly.** The Webley Mk VI rows are new in v2: the same decision applied to the gun that
wears the Webley's hands and states.

{{DECL}}

`player_Torso.st` carries the states for the above (revolver loops with break-off, per-pistol prone reload aliases):
618 changed lines against the released file.

## E. In the cut and not approved by the user yet

Coordinator's call on v1 (2026-10-13): the Welrod and the Luger ship on their new aim poses, to the user's own
install for testing, marked as awaiting approval; the texture lifts stay out.

| what | separable? | where |
|---|---|---|
| Welrod aim pose (`coopr_welrod_charge`) | no - its reload and bolt-cycle clips are baked on that pose | `ship/models/human/animation/viewmodel/pistol/coop_welrod_*.skc` |
| Luger aim pose (`coopr_luger_p08_charge`, `coopr_silenced_luger_p08_charge`) | no - same reason | `.../viewmodel/pistol/coop_luger_*.skc` |
| Welrod bolt sound | nothing was added (the cycle is silent apart from the shot) | - |
| Texture lifts: Welrod (5 sheets), Nambu (1), Beretta (3 files), silenced P38 (2) | **yes - left OUT of the cut**, they are in `ship_awaiting_approval/textures/`; copy them over `ship/` to include them. The Welrod's and the Beretta's bloody / camo finishes use their own sheets, which were NOT lifted | `ship_awaiting_approval/` |
| The decided server-side changes of D2 | Webley / Nagant: by holding the gun out; prone: by reverting the aliases | section D2 |

## F. Rebuild / re-check

```
cd tools
python shipcut.py ..\ship <test overlay.pk3>      # rebuilds ship\ and ship_awaiting_approval\ from the working stage
python srvrows.py ..\ship                         # exit 1 = a server-read row differs from the released file
python variants.py ..\ship                        # finish / variant coverage
python run_ded.py <id> --arm rel=ovbase_1021.pk3 --arm staged=<overlay.pk3>   then   python dedcmp.py <dir>
```
The working stage is the lane agent's scratch copy (`SCRATCH\ads2h\stage`); `assets/` is its committed image.
