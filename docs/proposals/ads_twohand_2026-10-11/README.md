# HANDOVER (2026-10-13 morning, PISTOL lane, after the server-side fix and the SHIP CUT) - read this first

**SHIP CUT v2 (later the same morning):** `webley_revolver_lv_ttwebley.tik` staged (`finishclone.py --also`), the Webley Mk VI `colt45_colt1911w.tik` staged on the Webley's rows with its own gun clips retimed (`tools/mk6.py`), a sample of the finish tiks and three model variants run in the engine (pa25, pa27, pa28; pa26 = an empty folder, started by mistake while pa25 was still running - the wait loop had matched the previous run's `run ended` line; the second runner stopped at the busy log file and nothing was lost). **pa29 is next.** The coordinator's calls: the decided server-side changes stay in, Welrod / Luger ship on their new aim poses for the user's test, texture lifts stay out. Runs pa18-pa24 were moved to `H:\hzm_archive\pistols\`; pa25-pa28 are still in `G:\mohaa-adsanim\runs`.

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

**DO NOT SHIP the staged pistol tree as it is.** Two blockers, both written up below: (1) the Welrod / TT-33 /
silenced TT-33 tiks change SERVER-read animation lengths and that does feed server state (read from the code, NOT run
on a dedicated server); (2) the C96's stripper clip is unfinished. The C96 files of commit deb932d (clip under the
palm, nothing seen, 0.42 u bolt) are the last state that was looked at in every stance: `git show deb932d:<path>`.

* Engine: unchanged, `ads-next` 2627cb94 = `G:\mohaa-adsanim\cgames\cgame_adsnext11.dll`. No engine edit this session.
* Commits of this session: checkpoint 349d814 (tools, assets, evidence), then this handover + coverage.
* RUN IDS: pa18, pa19, pa20 used; **pa21 is next**. A session that is cut off leaves its frames in
  `G:\mohaa-adsanim\home\maintt\screenshots` and the log in `home\maintt\qconsole.log` - move them into `runs\<id>`
  before the next boot, and release the slot (`harness_guard.release_slot("adsanim")`).
* Working copies: `SCRATCH\ads2h`, synced into `tools/` at the commit. Last overlay `SCRATCH\ads2h\ov_e1.pk3`
  (rebuild: `sh build_ov.sh ov_x.pk3`; `assets/` = `MKOV_EMIT=<abs>\assets sh build_ov.sh x.pk3`).
* One shared tool was touched outside this folder: `ads_bolt_2026-10-04/tools/hold_bake.py` - the gun's work pose
  (`dip`) takes an optional 6th value, yaw in degrees about the view's up axis; absent = 0, nothing else changes.

## 1. Measurement: DONE (runs pa18, pa19, pa20)

The lanes' standard is wired in: `run_2h.py --tail 360:4` captures one whole sway period of the settled aim after the
reload (mark `DEMO settle`), `centrebox.py` compares every frame with the model-less reference SHIFTED to that frame's
own background and reports the cover beyond the settled aim's SWAY ENVELOPE (`swayenv.py`). With a tail, `xmax` /
`xfr` in `centrebox.json` are the envelope figures (`env: true`; the six-frame figures stay as `x6max` / `x6fr`), and
`coverage.py` prints "beyond the aim's sway envelope". `run_2h.py --dstances crouch,prone,standL,standR --nostand`
runs the emptied demo in a stance (key `<gun>@<stance>_empty`; braced is not possible there - the mount needs the
railing spot, the demo stands at the light wall).

**What moved the Colt in pa11 (and every other "moves 1-3 points between runs"):** the aim's own sway and breath.
`probecmp.py pa8 pa11 colt45__yaw160e` - same demo, same clips: the grip point and the rear sight differ by a smooth
-11 px (mid reload) .. +9 px (after it) while the sight line is identical to 0.01 deg; in pa18 the settled aim alone
swings 13-18 px vertically and 8-15 px sideways over one 5.9 s tail with the sight line within 0.004 deg (10 px =
0.19 u at the Colt's eye relief). `ADSSETTLE` is zero because nothing is wrong with the rig target: the whole rig is
carried by `cg_adsSway` / `cg_weaponBreath`, and the reload starts at a random phase of it. The Beretta's "15 shots
walk the view" is the second half: the view pitch after the string differs run to run (pa8 -1.80, pa11 -1.19 deg) and
one fixed reference then no longer fits - the shifted reference takes that out.

Box cover beyond the sway envelope, worst frame, per cent (bar: under 2). Standing = loaded / emptied demo; stances =
the EMPTIED reload (runs: pa20). n/m = not measured.

| gun | stand, loaded | stand, emptied | crouch | prone | lean L | lean R | run (stand) |
|---|---|---|---|---|---|---|---|
| Welrod | 0.00 | 0.00 | 0.90 | 0.30 | 0.30 | 0.30 | pa18 |
| Luger P08 | 0.00 | 0.00 | 0.20 | 0.10 | 0.30 | 0.30 | pa19 |
| Silenced Luger P08 | 0.00 | 0.20 | 0.10 | 0.10 | 0.40 | 0.30 | pa19 |
| Mauser C96 (clip parts, UNFINISHED) | 0.00 | 0.00 | 0.10 | 0.10 | 0.50 | 0.20 | pa19 |
| Walther PPK | 0.00 | 1.40 | 2.30 | 2.70 | 2.30 | 0.50 | pa18 |
| TT-33 | 0.00 | 0.40 | n/m | n/m | n/m | n/m | pa18 |
| Silenced TT-33 | 0.00 | 0.10 | 0.60 | 0.10 | 0.40 | 0.30 | pa18 |
| Colt 45 (Pacific) | 0.10 | 0.90 | n/m | n/m | n/m | n/m | pa18 |
| Silenced Colt .45 | 0.00 | 0.60 | n/m | n/m | n/m | n/m | pa18 |
| Silenced Beretta | 0.00 | 0.80 | 0.20 | 0.00 | 0.50 | 0.60 | pa18 |
| Nambu Type 14 | 0.00 | 0.00 | 0.10 | 0.10 | 0.40 | 0.30 | pa18 |
| Silenced Walther P38 | 0.00 | 0.10 | n/m | n/m | n/m | n/m | pa19 |
| Colt 45 | 0.00 | 0.80 | 0.90 | 1.10 | 0.70 | 0.30 | pa18 |
| Walther P38 | 0.10 | 0.80 | n/m | n/m | n/m | n/m | pa18 |
| Beretta | 0.00 | 1.30 | 1.30 | 0.50 | 0.90 | 3.40 | pa18 |
| Mauser C96 (Trench C96) | 0.90 | 1.30 | n/m | n/m | n/m | n/m | pa19 |

Welrod per-shot bolt cycle (pa18): 0.3 %, sights back to 0.01 deg. The per-shot window now skips 10 frames after
each shot (flash + the shot's own recoil; the 3-5 % read at +5..+8 was the kick with both hands on the gun - frames
looked at). **The six guns marked "no" (Welrod, silenced TT-33, silenced Beretta, Nambu, Colt 45, Beretta) pass
standing with no clip changed.** Two findings from the stance run:
* **PPK emptied is OVER the bar in crouch / prone / lean L (2.3 / 2.7 / 2.3 %, in 2.5-3.8 % of the frames)**, at
  capture frame 393-397 = clip frame 51, the support thumb's sweep of the slide stop (standing 1.42 % at the same
  frame). NOT fixed: the PPK plays the Colt's hands rows; it needs its own emptied row baked with a lower thumb
  (`PB_THUMB` under 0.45, a `coopr_walther_ppk_reload_empty_ads` row). `coverage.md` has the PPK "on target: no".
* Beretta emptied, lean R: 3.4 % in 16 frames at the very START of the window. Frames looked at
  (`picks.py pa20 x.jpg "beretta__standR_yaw160e:505,520,528,536,700"`): it is the emptied gun's own pose - slide
  locked back, gun still high from the 15-shot string - with no hand in the box. With the SMG lane's rule (the dry
  gun's pose belongs to the reference; `centrebox.py --dry`, opt-in) the four stances read 0.18 / 0.05 / 0.54 /
  0.11 %. The table shows the figure WITHOUT that rule.
The pa20 session died at 00:01 in the 11th gun (TT-33, lean L) - the coordinator's restart; its frames were moved
from the harness home into `runs/pa20` by hand, the ten finished guns measured. **Not measured in the stances: TT-33,
Colt 45 (Pacific), silenced Colt, silenced P38, P38.** Not measured against the envelope at all: braced, crouch-leans,
the vehicle seat, and the LOADED reload in the stances.

## 2. C96 stripper clip: NOT DONE (staged unfinished, run pa19)

* **Found too late: the mod already has the clip.** `models/ammo/coop_c96_stripper_full.tik` / `_empty.tik` and a
  server attach timeline in `models/player/base/anims_shared.txt:1249-1257` (frame 28 full clip on `tag_weapon_left`,
  41 on `tag_weapon_right` = in the guides, 44 swapped for the empty one, 47 back to the left hand, 56 removed).
  The earlier handover's "no clip mesh exists" was wrong; `c96.py` parks `tag_weapon_left` under the view for the
  whole aimed clip (`tag_park`), which is why it was never seen. The project's own recipe is: un-park the tag and
  re-time the aimed hands to 28 / 41 / 44 / 47 / 56 so that the EXISTING prop is carried. Not done.
* What is staged instead (`tools/c96clip.py`, `c96.py`): bones `coop_rounds` / `coop_clip` / `coop_port` and five
  surfaces on `coop_c96/c96.skd` (eight cartridges, a brass strip, a bolt bar, a dark open-port patch; all hidden at
  rest), shaders `scripts/coop_c96_clip.shader`, textures `textures/coop_c96/`; the clip's channels are read from the
  BAKED hands clip (rigid to the support hand from the pouch, stands in the guides, the rounds sink 4.1 u, the strip
  leaves with the hand and is flicked away). Bolt travel 2.0 u (was 0.42), hammer 78 deg. The lowered gun is rolled
  35 deg and turned 30 deg about the view's up axis, drop 4.8 u; rounds left: lowered in two steps so that it keeps
  moving while the hand is at the pouch.
* What the engine shows (pa19, `evidence/c96_clip_contact_pa19_unfinished.jpg`, the GIF beside it): the strip is
  seen standing out of the hand, as a flat mustard bar. **The rounds are not readable** (the eye is behind the clip:
  the strip's back and the hand cover them), the hand does NOT travel down with the rounds, the bolt bar and the open
  port were not looked at up close, the gun sits low and rolled. Four hand / pose variants were tried offline
  (`c96try.sh`, `C96_LOW` / `C96_YAW` / `C96_HOLD` / `C96_HSIDE` / `C96_HTRAV`); with the muzzle turned left the
  support forearm crosses the whole view. Box figures still pass (0.01 / 0.01 %).
* Trench C96 (pa19): takes the same hands rows, has none of the new parts; 0.88 / 1.27 %. In its reload the gun is
  below the frame for the whole time the hand works. A white patch at the rear of its frame and a black block as rear
  sight are there in every frame, also before the reload - that variant's own look in the harness copy, not looked
  into.

## 3. Luger: partly (run pa19)

The emptied gun starts down on the reload's first frame and is under the box by frame 5 (was 1 -> 7). Offline the
open toggle is in the box for frames 0-3 (was 0-4) and frame 0 is the dry gun's own settled aim - by the lanes' rule
the dry pose belongs to the reference; engine 0.04 / 0.04 % (silenced 0.02 / 0.18 %). NOT done: front link, toggle
flick per shot (needs a client-only gun fire clip, see 6).

## 4. Silenced P38 slot: DONE (run pa19)

`p12.py` split option `fill`: a steel block on its own bone under the slide, parked 0.9 u forward inside it, comes
flush with the rear face in proportion to the slide's travel - the closed gun's rear is unchanged. Offline rear view
looked at closed / open; engine 0.04 / 0.12 %, GIF `evidence/p38_silenced_aimed_reload_empty_pa19.gif` (decoded at
sheet size only - the slot was NOT looked at up close in the engine).

## 5. Checks nobody ran: STILL NOT RUN

Weapon switch / sprint / fire / aim-dropped out of the new clips; loaded reloads and crouch-leans in the stances; hip
view of emptied guns; Hi-Standard after its re-bake; Welrod second shot during the cycle, bolt sound, hip side; M10
in third person. None of it was started.

## 6. Server side: NOT TESTED - and by the code the staged tiks DO change server state

No dedicated server was started. Read from `openmohaa-hzm-ads/code/fgame/weapon.cpp`:
* `StartReloading` = `SetWeaponAnim("reload", EV_Weapon_DoneReloading)`; `weaponstate` is `WEAPON_RELOADING` until
  the weapon tik's `reload` animation ENDS. Staged: Welrod 1 -> 73 frames, TT-33 / silenced TT-33 7 -> 73: 2.43 s
  instead of 0.03 / 0.23 s. That state is read in `player.cpp` (16059, 16192, 16485, 16815-16837, 17116, 17496:
  quick-draw and reload-window logic) and `sentient.cpp:4449`.
* `Shoot` = `SetWeaponAnim(fire, EV_Weapon_DoneFiring)` -> `ForceIdle` at the END of `fire`: 0.87 s after a Welrod
  shot instead of 0.03 s.
* The fire RATE is not touched (`ReadyToFire` has no weaponstate gate, only `firedelay`, unchanged in the tiks).
* Why the lengths were changed: the cgame swap (`cg_modelanim.c` ~3022-3112) only replaces the anim INDEX in the
  slots where the server plays `fire` / `reload`; when the server's short clip ends, the client clip is cut.
* What has to happen: the cgame keeps its own clock for the swapped clip (latched when the server's slot appears,
  played for the client clip's length while the first-person hands are still in that row, dropped on weapon change;
  behind a cvar, only when the client clip is longer than the server's), then `fire` / `reload` go back to the
  released clips in those three tiks, THEN the dedicated run (fire rate, reload duration, ammo, reload-done time).
* Every tik staged from `zzzzz_xw_weapons.pk3` also gained an `idle_empty` - same test.

## Also fixed

`p12.patch_tik` was not idempotent: a tik that lives only in a pak is read back through the wip overlay, so every
re-run stacked another block of reload animations (commit deb932d already had FIVE in `LugerP08.tik`,
`lugerp08silenced.tik`; `p38silenced.tik` got five here). Earlier blocks are removed first now; all 91 staged tiks
scanned: one block each.

## Awaiting the user (unchanged, reversible)

Welrod and Luger aim poses; texture lifts (Welrod, Nambu, Beretta, silenced Beretta, silenced P38); C96: carry the
existing prop (B) or keep gun-side parts (A); a bolt sound for the Welrod.

## The list from here

0. PPK: its own emptied hands row with a lower thumb, then the stance demo again (`--dstances`); the five guns the
   stance run did not reach.
1. Server side (6): the cgame latch, the three tiks back to released lengths, the dedicated-server comparison.
2. C96 on the existing prop and timeline; a hand pose made for it (the eye has to see the rounds: clip seen from
   the side, hand behind it); Trench C96 with it.
3. The checks of 5.
4. Luger front link / toggle flick (with the latch of 1 a client-only fire clip is possible).
Bugs of this session: bug-3733 (sway envelope), 3734 (per-shot recoil window), 3735 (C96: existing prop not used), 3736 (server-read lengths, not fixed), 3737 (silenced P38 filler), 3738 (tik patch not idempotent).

---

# HANDOVER (2026-10-12 night, PISTOL lane, after list items D and E) - superseded by the section above; history from here on

**State: D is done for the mechanisms and measured standing; D and E stance runs are done and looked at (crouch, prone,
both leans, braced; vehicle seat: see the table). Open points are listed under "Not done / not verified" - read them.**
Nothing is in the mod tree or the fixes pak; all of it is staged here (`assets/` = the whole staged tree, emitted by
`MKOV_EMIT=<abs>\assets sh build_ov.sh x.pk3`).
* Engine: branch `ads-next` at **2627cb94** (worktree `openmohaa-hzm-ads`) = test cgame `G:\mohaa-adsanim\cgames\cgame_adsnext11.dll`.
  New in it: the per-weapon row override `coopr_<weapon key>_<suffix>` also covers the aim pose (`charge`) and the
  client-only per-shot cycle (`cycle`), so ONE gun of a shared prefix can have its own pose (Luger, Welrod) and its own
  bolt cycle (Welrod). `coop_vmAdsAnims`, `coop_vmAimedCycle`, `coop_vmAimedReloadGun` gate them as before.
* RUN IDS: prefix `pa`; pa7-pa17 are used, **pa18 is next**. The runners refuse an existing id.
* Working copies: `SCRATCH\ads2h` (this session's scratchpad), synced into `tools/` at each commit - EXCEPT
  `tools/coverage.py`, which the rifle lane edited on 2026-10-12 20:01: the copy in `tools/` is the current one.
* Last overlay: `SCRATCH\ads2h\ov_d4.pk3` (= `assets/` + harness plumbing). Rebuild: `sh build_ov.sh ov_x.pk3`.

## D + E: what each pistol has now (centre box = worst frame, engine, standing, wooden-door backdrop)

| gun | aimed loaded reload | aimed emptied reload | per shot | the action, and who works it | stances looked at | evidence |
|---|---|---|---|---|---|---|
| Welrod | 0.6 (pa8) / 2.8 (pa10) / 1.3 (pa11) | 0.5 / 1.7 / 0.8 | bolt worked after EVERY aimed shot: 0.87 s, the gun leaves the sights by 16 deg under the box and is back to 0.01 deg; frames over 2 %: the recoil frame after each shot, and in pa11 four frames at 2-3 % as the hand comes off | BOLT ACTION, support hand: gun down under the box, hand over the rear, knob turned 55 deg, bolt pulled 2.0 u, run forward, turned shut (bolt surface on a bone; the case leaves at the pull). Emptied reload ends in the same cycle; loaded reload: no bolt work. Own aim pose 3.4 u further out; five sheets level-lifted (the knob is a ringed steel disc, not a black one) | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa13) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `welrod_aimed_cycle_reload_d.gif`, `welrod_aimed_reload_empty_d.gif`, `welrod_stances_emptied_pa9.jpg` |
| Luger P08 | 0.9 (pa8, pa10) | 4.3 (pa8) -> 1.6 (pa10, hand approach lowered) | - | TOGGLE on two bones (rear link + knobs, breech): up 50 deg / breech back 1.7 u while empty (idle_empty), the emptied gun is held under the box for the reload, the support hand takes the knobs from above, pulls and lets go - it snaps shut. Own aim pose 2.2 u further out (base cover 18 -> 13 %) | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa14) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `luger_aimed_reload_empty_d.gif`, `luger_aimed_reload_loaded_d.gif`, `luger_stances_emptied_pa9.jpg`, `luger_toggle_offline.jpg` |
| Silenced Luger P08 | 0.5 / 0.7 | 2.9 (pa8) -> 0.6 (pa10) | - | as the Luger (same clips, its own split mesh) | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa13) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `luger_silenced_aimed_reload_empty_d.gif`, `pistols_stances_emptied_pa9_4.jpg` |
| Mauser C96 | 1.0 (pa8); was 7.2 (pa6) | 0.7 (pa8) | - | own reload: gun straight down under the box, support hand strips a clip in from the top (clip UNDER THE PALM - no clip mesh exists), bolt end forward 0.42 u as the clip leaves, hammer down with it; loaded: the hand draws the bolt back first. Sights leave by 13.6 deg by design, back to 0.01 | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa13) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `c96_aimed_reload_loaded_d.gif`, `c96_aimed_reload_empty_d.gif`, `c96_stances_emptied_pa9.jpg` |
| Walther PPK | 1.4 (pa8) | 5.1 (pa7) -> 1.9 (pa8, thumb lowered) | - | slide (Bone3) locked back when empty, forward at the support thumb's sweep; loaded: no slide action | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa13) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `ppk_aimed_reload_empty_d.gif`, `pistols_stances_emptied_pa9_0.jpg` |
| TT-33 | 1.9 (pa8) | 3.7 (pa7) -> 1.2 (pa8) | - | slide (selfcock) as the PPK; the gun's `reload` is 73 frames now (was 7) and it has an `idle_empty` | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa13) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `tt33_aimed_reload_empty_d.gif`, `pistols_stances_emptied_pa9_0.jpg` |
| Silenced TT-33 | 1.6 (pa8) / 1.4 (pa10); was 2.7 (pa6) | 2.3 (pa8) / 1.8 (pa10) | - | as the TT-33 | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa13) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `tt33_silenced_aimed_reload_empty_d.gif`, `pistols_stances_emptied_pa9_1.jpg` |
| Colt 45 (Pacific) | 1.2 (pa8); was 3.1 (pa6) | 1.3 (pa8) | - | slide (chamber) as the Colt: still when loaded (it snapped back before), locked back / forward at the thumb when empty | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa14) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `colt_pacific_aimed_reload_loaded_d.gif`, `pistols_stances_emptied_pa9_1.jpg` |
| Silenced Colt .45 | 1.6 (pa8) | 1.3 (pa8) | - | as the Colt (tik staged from the pak) | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa14) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `colt_silenced_aimed_reload_empty_d.gif`, `pistols_stances_emptied_pa9_2.jpg` |
| Silenced Beretta | 1.7 (pa8) / 0.9 (pa10) | 1.7 (pa8) / 3.1 (pa10) | - | slide (Rechamber) locked back / forward at the thumb, own `idle_empty`; sheet gamma-lifted (blued steel with highlights, was a black shape) | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa14) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `beretta_silenced_aimed_reload_empty_d.gif`, `pistols_stances_emptied_pa9_2.jpg` |
| Nambu Type 14 | 1.4 (pa8) / 3.1 (pa10) / 2.2 (pa11) | 1.2 / 0.9 / 0.4 | - | BOLT with its round knob cut out onto a bone: back 1.9 u when empty, forward at the thumb; sheet gamma-lifted | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa14) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `nambu_aimed_reload_empty_d.gif`, `pistols_stances_emptied_pa9_3.jpg` |
| Silenced Walther P38 | 1.6 / 0.7 / 0.5 | 1.3 / 1.0 / 0.5 | - | slide cut out onto a bone (S93 remodel): back 2.3 u when empty; sheets gamma-lifted. The open slide shows a dark slot down the middle (no filler on this mesh) | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa15) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `p38_silenced_aimed_reload_empty_d.gif`, `pistols_stances_emptied_pa9_3.jpg` |
| E: Colt 45 | 2.2 (pa8) / 1.0 (pa11); 1.6 before (td8) | 1.4 (pa8) / 4.3 (pa11); 3.2 before (td9) | - | unchanged technique; seat push x0.6, thumb x0.45 | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa15) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `colt45_aimed_reload_empty_e.gif`, `pistols_stances_emptied_pa9_4.jpg` |
| E: Walther P38 | 1.8 (pa8) / 0.3 (pa11) | 2.8 (pa8) / 0.7 (pa11); 4.0 before (te2) | - | unchanged technique; a steel breech block added inside the slide's rear slot (add_part.py) - the open slide no longer shows a black gap from behind | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa15) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `p38_aimed_reload_empty_e.gif`, `pistols_stances_emptied_pa9_5.jpg`, `pistols_readable_rears_pa11.jpg` |
| E: Beretta | 2.1 (pa8) / 0.9 (pa10) / 2.0 (pa11); 2.1 before (te6) | 3.4 / 4.8 / 2.4 - the 15 shots walk the view, the reference no longer fits (1.6 in te7) | - | unchanged technique; sheet gamma-lifted AND written as `.dds` (the lifted `.jpg` lost to a `.dds` in the HD pack) | crouch, prone, lean L / R, braced (pa9), vehicle seat (pa15) - emptied reload, sheets looked at; settled aim 0.0 deg in 8 stances (pa17, numbers) | `beretta_aimed_reload_empty_e.gif`, `pistols_stances_emptied_pa9_5.jpg` |

Bar: under 2 % of the centre box beyond the settled aim in every frame, back to within 0.05 deg. All of them end at
0.00-0.01 deg. **The figure moves by about 1 point between runs of the SAME clips** (the aim breathes; a big rear
silhouette then shows a crescent outside the grown aim mask: Welrod loaded 0.6 % in pa8, 2.8 % in pa10, same files) -
a figure between 1.5 and 3 is "at the bar", not a pass and not a defect. Offline (`offbox.py`, no breathing) every
clip of this table is under 2 %, except the first 5 frames of the Luger's emptied reload (the open toggle stands in the
aim until the gun has come down).

## How D was built (reuse it)

* `tools/p12.py` - the GUN side for every pistol that borrows the Colt / P38 hand rows: `reload_ads_loaded` (slide
  still), `reload_ads_empty` (locked back, forward at the thumb sweep), `reload_empty` + `idle_empty` where the gun had
  none, and a 73-frame `reload` where the retail gun clip is shorter than the hands' (TT-33: 7 frames). Tiks are read
  from the mod tree, else from the live install's paks (six of the twelve live only in `zzzzz_xw_weapons.pk3`).
  `split=` cuts a slide / bolt out of a mesh that has none (silenced P38, Nambu).
* `tools/bonefit.py` - `split()` (islands onto new bones; ALWAYS from the original mesh: it drops
  `IRONSIGHT_EXTRA_PAKS`), `fit()` (the new bone's frame = its parent's, fitted from the mesh), `chan()` (a turn about a
  gun-space pivot + a move -> the bone's pos / rot; the engine applies a bone quaternion as rows). Luger toggle = two
  bones, C96 = bolt end + hammer, Welrod = bolt turned about the bore.
* `tools/welrod.py`, `tools/luger.py`, `tools/c96.py` - one module per gun with its own choreography: gun clips, tik
  patch, hands (through `pistolbake.spec` with the rack hooks replaced), rows file `rows_p12_<gun>.txt` (picked up by
  `build_ov.sh`). Offline loop before any engine run: `sh woff.sh cycle,reload sheet.jpg`, `sh loff.sh sheet.jpg`,
  `sh coff.sh sheet.jpg` (bake, wip overlay, `offbox.py` over every frame, sheet).
* `tools/pushpose.py <src pose> <sight key> <D> <out>` - an aim pose with both arms `D` u further out (Luger 2.2,
  Welrod 3.4); `tools/eyedist.py` prints eye -> rear sight per gun (Colt 14.4 u; Luger was 12.8, Welrod 11.0).
* `tools/weltex.py` (Welrod: level lift of five sheets at 0-60 of 255) and `tools/gamtex.py` (gamma lift: TT Beretta,
  silenced Beretta, silenced P38, Nambu). **`.dds` beats `.jpg` / `.tga`**: the TT Beretta sheet has a `.dds` in
  `zzzzzzz_dds_hdmem.pk3`, so gamtex also writes a full-mip DXT1 `.dds`; the lifted `.jpg` alone changed nothing (pa9).
  When this ships, the pak that carries it has to sort after the HD packs.
* `tools/pistolbake.py`: `PB_SEAT` 0.6 (the seat push; was 1.0) and `PB_THUMB` 0.45 (how high the support thumb rides
  before the sweep; was 1.0) - both because smaller guns on the Colt clip went over the bar.
* Engine runs: `python run_2h.py <id> --overlay <abs>\ov.pk3 --cgame cgame_adsnext11 --guns a,b --parts demoy --both
  --eshots welrod=6,colt45=7,beretta=15 --gungap welrod=62 --demoreload 190 --demoreload_e 180 --shots 2`
  (`--both` = loaded demo + the same gun fired empty, tag `yaw160e`). Stances: `--parts reloads --rstances
  crouch,prone,standL,standR,braced --rempty --remptyonly --revery 5`. Vehicle seat: add `--ride` (t2l2 halftrack bed,
  `--rstances ride`). Then `centrebox.py <id> --dump --cycle --json=centrebox.json`, `stsheet.py <id> <gun> out.jpg
  --empty` (stances x frames), `picks.py` (chosen frames of several guns), `dgif.py` + `gifsheet.py`.

## Not done / not verified (tell the user; do not hide)

* **Run-to-run spread of the centre-box figure** (above). Worst cases with identical clips: Colt emptied 1.4 % (pa8) / 4.3 %
  in half of the frames (pa11) - the gun sits about 0.25 u higher for the whole reload in pa11 and drops at its end;
  Nambu loaded 1.4 / 3.1 / 2.2 - in pa10 the gun sits 8-10 px lower BEFORE the reload than after it. `ADSSETTLE` prints
  zero in both runs (so not bug-3597's frozen rig target). Not understood. Until it is, "under 2 % in every frame" is not
  proven for: Colt (both), Beretta (both), Nambu loaded, Welrod loaded, silenced Beretta emptied, silenced TT emptied.
  `coverage.md` marks those "on target: no".
* **Welrod**: no sound for the bolt (the P38 reload sample's slide click falls on the pull); at the HIP nothing changed
  (no bolt work, as before); the server's `fire` is now 26 frames and `reload` 73 (were 1) - a SERVER-side tik change;
  the per-shot cycle was not tried with a second shot pressed during it; the aim pose is new and NOT approved.
* **Luger**: the aim pose is new and NOT approved. The emptied gun shows its open toggle in the centre box for the
  0.2 s before the gun has come down (14 % offline) - a real open toggle does stand there. The breech block and front
  link are ONE piece that slides back level under the raised rear link (no articulated front link). The toggle does not
  flick on a shot (the retail fire clip is static). The releasing hand hangs open beside the gun for about 0.15 s.
* **C96**: the stripper clip is never seen (no mesh); only the bolt's rear end moves, 0.42 u (the rest of the bolt is
  part of the body mesh); the hammer rises again with the closing bolt; with the hand at the pouch the lowered gun is
  alone at the bottom of the frame for about 0.35 s, the firing hand below the edge. The Trench C96 variant takes
  the same hands rows by name (`mauser_c96` after the finish is stripped) but keeps its own gun clip - NOT run.
* **TT-33 / Welrod / every tik staged from `zzzzz_xw_weapons.pk3`**: the staged tiks carry server-visible changes
  (animation lengths, idle_empty). Not tested on a dedicated server or with a second client.
* **Silenced P38**: the open slide's dark middle slot is still there (the filler was added to the retail P38 mesh only).
* **PPK**: the hammer (Bone2) is held where the empty clip has it for the whole emptied reload.
* **Textures**: Welrod (5 sheets), TT Beretta (`.jpg` + `.dds`), silenced Beretta, silenced P38 (2), Nambu were lifted
  by a curve, nothing repainted; seen only on m3l2 by day and on t2l2 in snow. The TT-33 and silenced Colt still read
  dark. When shipped, the pak has to sort after `zzzzzzz_dds_hdmem.pk3` or the Beretta `.dds` loses again.
* **Hip reloads** of all fifteen: not touched, not re-run (the staged `reload_empty` clips change what an EMPTIED gun
  shows at the hip: slide / toggle / bolt back until the retail magazine seats) - not looked at.
* **Stances**: every stance sheet is of the EMPTIED reload (it contains the loaded one's hand path plus the action); the
  loaded reload was looked at standing only. Crouch-lean stances not run. Hi-Standard: re-baked with the 0.6 seat push
  and NOT re-run. The vehicle seat is seat 2 of the t2l2 halftrack (moving); `tools/run_2h.py --ride` survives about
  seven guns per session before the ride ends - run at most five.
* **M10** (list item E): hip reload and both break-off states were run with the per-chamber heads (pa12: the
  chambers fill one by one at the hip too, a break-off closes on the heads that are in, `m10_hip_and_breakoff_pa12.jpg`).
  THIRD PERSON was not run: by the code (`cg_modelanim.c`, the rule is under `s1->parent == cg.snap->ps.clientNum`)
  another player always sees all six heads, also while that player's cylinder is open and empty. Not fixed - the
  other client does not know that player's rounds.
* A second client, real latency, weapon switch / sprint out of the new clips (Welrod cycle, Luger, C96): not run.
* Settled aim in the stances (stand, crouch, prone, both leans, both crouch-leans, braced; run pa17): the NUMBERS are in
  (pose 1.00, 0.0 deg for all fifteen) - those stills were not opened; the aim was looked at in the reload sheets only.
* `pistols_vehicle_seat_pa13.jpg` shows the dead end of that session for the guns after the 7th; the nine missing guns
  are in `pistols_vehicle_seat_pa14_pa15.jpg`.
* A wandering NPC of the map walks through some frames; it is the map's.

## The list from here

1. The run-to-run spread = the aim's own sway / breath. `tools/swayenv.py` appeared in this folder on 2026-10-12 22:20
   (NOT written by this lane; the heavy lane's measure made shared - its header calls it the standard): a reload is
   judged against the ENVELOPE of the settled aim over one whole sway period (5.7 s = 357 game frames captured after
   the reload, sparsely). The pistol lane has NOT used it: `run_2h.py` captures no such tail and `centrebox.py` still
   compares against six frames. Do this first - add the tail to `demo()` (a `DEMO settle` mark, 360 frames every 4th),
   call `swayenv.envelope_extra` from `centrebox.py`, re-measure all fifteen, then re-decide the six "on target: no".
   The un-explained part stays: pa11 Colt emptied, the gun about 0.25 u higher for the whole reload
   (`picks.py pa11 x.jpg "colt45__yaw160e:250,300,340,380,430"` against the same frames of pa8).
2. User decisions: the Welrod and Luger aim poses; the texture lifts; whether the C96 gets a clip mesh (`add_part.py`
   can add one to the hand side or the gun); a bolt sound for the Welrod.
3. A second-client / dedicated-server pass of the staged tiks (TT-33, Welrod: animation lengths).
4. Hip view of the emptied guns with the new `reload_empty` / `idle_empty`; Hi-Standard re-run; crouch-lean stances;
   loaded reloads in the stances.
5. Silenced P38 slot filler; Luger front link; Trench C96.
A pistol row is DONE only with: aim pose, aimed reload (loaded + empty), per-shot cycle where the gun has one, all
stances run and looked at, the three yes columns, a run id.

---

# HANDOVER (2026-10-12 late evening, PISTOL lane) - read this first, the rest of the file is the history

**(superseded by the section above) State then: A, B and C of the list done and committed (engine `ads-next` d2a6d31b = test cgame `cgame_adsnext10`).
D and E not started.** Nothing is in the mod tree or the fixes pak; all of it is staged here.
RUN IDS: use the prefix `pa` (pa1-pa6 used; pa7 is next). `boot_session` deletes an existing run folder - ids tm1-tm3 and tn1 of
earlier sessions were lost that way on 2026-10-12; `run_2h.py` / `run_break2.py` now refuse an existing id.
The work is split into four lanes since 2026-10-12: this folder's root is the PISTOL lane (pistols + revolvers) and it
OWNS `tools/` and `coverage.md`; `rifles/`, `smg/`, `heavy/` are the other lanes (own harness copies, own
`coverage_status.json`, merged by `tools/coverage.py build`; they read `tools/` as a library - keep changes there
backward compatible; the runs folder of every shared tool comes from `ADS_RUNS`).

## B, done (runs tl1-tl8)
| what | result | evidence |
|---|---|---|
| Prone pistol reloads | full length now: `tools/patch_prone_reload.py` - one prone torso alias per standing alias (Colt + sharers, P38, Hi-Standard, Beretta, C96) on the prone body clip retimed to the standing length (`coop_pistol_prone_reload_73.skc` / `_63.skc`) with the standing alias's own commands. View reload in prone: 150 frames for Colt / P38 / Hi-Standard (was 88), Beretta 129; hip AND aimed (the hip reload had the same cut). Revolvers have no prone line, unchanged. GAMEPLAY: prone pistol reload 1.50 s -> 2.43 s (Beretta 2.10 s). | `evidence/histandard_prone_reload_aimed.gif`, `histandard_reload_stances_tl8.jpg` |
| Hi-Standard rack | the releasing hand is a relaxed curl coming off to the left (was a splayed hand lifting straight up); the PER-SHOT rack is now inside the bar - it had never been measured: 7.9 % / 13.5 % of frames in run ti2, 25 % offline. Now engine tl8: per-shot max 0.5 %, reload max 0.3 %, back to 0.01 deg; offline 0.0 % / 0.2 %. | `evidence/histandard_aimed_cycle_reload.gif` |
| Pass bar | `coverage.py`: a weapon flagged `lowered` (declared rack / open-cylinder phase) passes a stance when the capture ends within 0.05 deg, pose >= 0.9 and the centre box (loaded, empty, per-shot cycle) is <= 2 %; no box figure = not passed. `centrebox.py --cycle` measures the per-shot segment. | `coverage.md` |
| Revolver break-off, second client | `tools/run_break2.py` (host serves, a joiner of the same install is driven by posted keys in real time and captured; overlay on `ovbase_1021_p2.pk3` = `MKOV_BASE`), `tools/breakmarks.py` (animation + `clip=` trace). FOUND AND FIXED: a press in FETCH closed, fired - and the gun opened again by itself 0.1-0.2 s later (the `reload` latch of CHECK_CONTINUE; `tools/patch_breakfire.py`: `donereloading` in `RELOAD_*_BREAK_FIRE`). Run tl7, Webley / M10 / Nagant, press in FETCH and in SEAT with 4 rounds in: close, owed shot, no restart, every round accounted for. Loopback only (no real latency). A second press DURING the close is absorbed into the one owed shot. | `evidence/breakoff_2nd_client_*.gif` |

Harness facts learned in B: a cfg `wait N` is only N ms under fixedtime (the host with `coop_isFixed 16`); on a free
running client time the capture from Python and post keys (run_break2.py). ADSFRAME carries `clip=` / `ammo=` from
cgame_adsnext8 on. `run_2h.py --parts reloads --rstances prone --rhip --revery 3` = aimed + hip reload in a stance.

## C, done (runs tl9, tl10, tn1-tn3, pa1, pa2; overlay recipe unchanged: `sh build_ov.sh ov_x.pk3`)
| gun | change | engine (emptied gun, aimed) | evidence |
|---|---|---|---|
| Webley | open and close states 0.53 s -> 0.8 s, HIP AND AIM (`tools/webslow.py`, then `revbake.py webley_hip / webley_ads`): the barrel tips over 12 frames (was 4), shuts over 10; hands re-keyed, sounds / cases moved with it. A Webley reload is 0.27 s longer at each end. | box max 0.3 %, 0.00 deg, 5 stances (tn1) | `evidence/webley_reload_aimed_c.gif` |
| S&W M10 | dump pose raised 1.4 u and flattened (cylinder face fully in frame), cases thrown up and left; chambers fill one by one | box max 0.7 %, 0.00 deg (pa5), 5 stances (tn2) | `evidence/m10_reload_aimed_c.gif` |
| Nagant | worked 1.8 u higher (gate 5.6 u under the eye line - the limit of the 2 % bar), feeding hand comes from below, lower support elbow; in prone the gun and both hands are in frame now | box max 0.3 %, 0.00 deg, 5 stances (tn3) | `evidence/nagant_reload_aimed_c.gif`, `revolver_stances_tn.jpg` |

M10 cases "vanishing near the top of their arc": they do not - the evidence GIF's crop (x from 240) cut them off on
the left. Full frames of run pa2: out at f276, top of the arc f282, out of the bottom-left of the frame f286 = 0.17 to
0.2 s, which is what brass does at that distance under the game's gravity (800 u/s2); left as it is, the GIF is
re-cut (crop from x 140) so the arc is in it. Capture frames are 16 ms; a GIF frame of dgif `:3` is 48 ms.
Still weak, seen in playback: the Nagant's left forearm is still large for
about 0.1 s at the hand-over; the Webley hip open / close were looked at only at coarse scale.
M10 chambers fill ONE BY ONE now (run pa5, cgame `cgame_adsnext10` = ads-next d2a6d31b): `tools/m10rounds.py` (after
m10face / m10build) appends six surfaces `coop_round1..6` to the staged skd (round k on the chamber k index steps
behind the feed chamber, round 6 on the feed chamber), makes the loop clip turn the cylinder one chamber over its last
four frames, and fixes the tik (the old all-six surface is hidden in `init`: a surface FLAG in `setup` is ignored).
cgame (`cg_modelanim.c`, held-gun block; applied after `model.surfaces` is copied from the entity state): a
`coop_round<N>` surface is drawn iff N <= rounds in the gun - all of them outside a reload and until an emptied gun's
cases are dumped (0.70 s into the opening clip), latched in the loop so the new head shows at the loop's restart.
`coop_vmRoundSurfaces 0` = off. The Webley / Nagant could get the same surfaces. Not checked: third-person view
(another player sees all six heads - the rule is local), the break-off states with the heads.
Gun frame axes for particle rows: x forward, y right, z DOWN.

bug-3597 (does the rig-solve target freeze mid-recoil on an emptied gun?): measured, NOT confirmed - see the buglog
entry and `cg_view.c` CG_AdsRigSolve; `cg_adsSightDebug 2` prints `ADSSETTLE`, `tools/sightend.py <run>` prints the
sight line at and after the clip's end. The Colt's 0.08 deg at the end of its empty reload is the baked physics tail.

## The standard (every aimed reload / cycle, all three)
1. ON TARGET - centre box (middle 20 % of the screen) covered beyond the settled aim under 2 % in every frame; where
   the mechanism cannot be worked on the sights the gun comes DOWN under the box and returns to within 0.05 deg.
2. THE WEAPON REACTS with weight - every motion from a cause, through `tools/gunphys.py`, never decorative keys.
3. THE ACTION REALLY WORKS on the model, by the hand that suits the real control; reproduce the hip technique.

## What passes now (revolvers, aimed, runs tk11-tk13 on cgame_adsnext7 + `G:\mohaa-adsanim\ov_revolvers_default.pk3`)
| gun | engine box max | offline box max (every frame) | back to | per round | GIF (20 fps, centre box drawn) |
|---|---|---|---|---|---|
| Webley | 0.2 % (empty tk13, 3 rounds tk4) | 0.2 % | 0.00 deg | 2.5 deg swing | `evidence/webley_reload_aimed_low_small.gif` |
| S&W M10 | 1.6 % (tk11), 0.3 % (3 rounds tk4) | 0.2 % | 0.00 deg | 2.5 deg swing | `evidence/m10_reload_aimed_low_small.gif` |
| Nagant | 0.4 % (tk12) | 0.0 % | 0.00 deg | 0.8 u shove + 1.1 deg (from the clip) | `evidence/nagant_reload_aimed_low_small.gif` |

M10 run tk13 read 4.5 % in its first five measured frames: that is the last shot's smoke over the brown door (the
model is outside the box there - offline 0.2 %, partial reload 0.3 %). The hip reloads were not touched.

Known weak points, seen in playback (tell the user, do not hide them):
* Webley close: the gun turns upright in about 0.1 s (two GIF frames) - brisk; the support hand lands on the grip in
  the last two frames of the rise. Open: the barrel still tips in about 0.1 s (eased, was 3 frames linear).
* M10: cases are in view for about 0.16 s, low left, in front of the sleeve; the dump's cylinder sits at the bottom edge.
* Nagant: the whole work is at the bottom edge of the frame (gate just in view); during the hand-over the left
  forearm comes in large from the left edge for about 0.2 s.
* Break-off states: re-run from a second client with the new clips in B (below) - one defect found and fixed.

## How A was done (reuse this for every other gun)
* `tools/revbake.py`: aimed sets now use a list of `gun_abs` poses - `Tlo` (the aim dropped straight down, aligned)
  then the work pose. Leaving: Tlo weight 0->1 first, work pose after; returning: work pose off first, then Tlo->aim.
  A gun that rises / falls aligned stays inside the aim's own silhouette, so the box cover is zero by construction.
  `curl()` = finger_add for a hand on a thin part. Physics event frames per family in the set's `phys` dict;
  `REV_SEAT` (default 2.0) scales the per-round reaction; `gate_seat` / `cyl_turn` are the Nagant's actions.
* Gun-side clips: `tools/retime.py ... warp new:old,...` moves / eases a part of a gun clip; the staged tiks carry
  `reload_ads_loaded` / `reload_ads_empty` (aimed open), `reload_end_ads`, `reload_single_ads`
  (`tools/patch_tik_ads.py`, `patch_tik_nagant_single.py`); cgame ads-next shows them in an aimed reload.
* Check OFFLINE first: `sh tools/rev.sh <webley|m10|nagant> [sheet.jpg]` bakes, builds `_ov_wip.pk3` and runs
  `tools/offbox.py` (box cover over EVERY clip frame; needs `IRONSIGHT_EXTRA_PAKS=<overlay>` for staged gun clips).
  The engine measure (`centrebox.py`) skips the first 20 capture frames of an emptied gun and still counts smoke.
* Engine run (the working copies live in `SCRATCH\ads2h`, synced into `tools/` at each commit; no lock / slot needed):
  `sh build_ov.sh ov_x.pk3` then
  `python run_2h.py <id> --overlay <abs path>\ov_x.pk3 --cgame cgame_adsnext7 --guns webley,m10_revolver --parts demoy --demoempty --demoreload 450 --shots 6`
  (Nagant: `--guns nagantrev --shots 7 --demoreload 500`; partial reload: drop `--demoempty`, `--shots 3 --demoreload 260`).
  Never give 7 shots to a 6-round gun: the 7th press is a break-off. Then `python centrebox.py <id> --dump`,
  `python loopreact.py <id>`, `python animmarks.py <id>` (ADSFRAME `anim` / `sight` do not describe a gun on the
  off-hand tag: the Nagant reads 6 -> 8 and 0.00 deg while its loop plays).
* GIF: `python dgif.py <id> <gun> out.gif --frames a:b:3 --w 400 --crop 240,120,1040,720 --box` (delta frames, about
  2 MB for 130 frames), then `python gifsheet.py out.gif sheet.jpg a:b:1` and LOOK at every frame of the transitions.
* Python patch scripts are written with the file tool - a heredoc mangled `\t` / `\s` again today (bug-3581).

## D, first pass only (run pa6: the 12 pistols on shared clips, standing, two aimed shots + aimed loaded reload)
Measured in the engine for the first time (`tools/centrebox.json`, `evidence/pistols_shared_pa6.jpg` = settled aim and
mid-reload of each). All return to 0.01 deg. Centre box max: p38silenced 0.3, lugerp08 0.5, welrod 0.5 (reload only),
lugerp08silenced 0.6, nambu 1.1, tt33 1.3, ppk 1.7, berettasilenced 1.8, colt_silenced 1.9 - under the bar;
**tt33silenced 2.7 % (3 frames), colt45_coltpa 3.1 % (11 frames), mauser_c96 7.2 % (18 frames)** - over it.
Seen in the frames: the Luger (both) sits large and close - its toggle block fills the lower half of the centre box
in the settled aim (base cover 16-18 %); the Welrod's rear is a near-black disc under tiny sights (base 17 %); the
Beretta silenced reads near-black like the Beretta; the C96's reload takes the gun right out of the aim (it runs the
P38-prefix re-bake, not its stripper-clip technique). No silencer met the support hand in these frames.
NOT done in D: the Welrod's bolt cycle (per shot and after the reload), the C96's own aimed stripper-clip reload, the
empty reloads and the stances of these twelve, the trims of the three over the bar, a pose for the Luger.

## The list as it stood then (D and E are done since: see the top)
D. Welrod (bolt action after EVERY shot and after the reload; knob at the rear on the sight line: lower / roll the
   gun as for the Hi-Standard). Then Mauser C96 (stripper clip from the top), Luger, PPK, TT-33, Nambu, the silenced
   variants: each needs its own in-engine run (the 15 pistols sharing the Colt / P38 clips were only checked
   offline; add harness keys). Silencers must not meet the support hand or the box.
E. Trim the Colt and P38 empty reloads and the Beretta loaded one (each a few frames over 2 %); the Beretta reads
   near-black (seen again in run tl3, prone); the P38 open slide shows a dark gap from behind; braced and
   vehicle-seat stances for every pistol; every stance LOOKED AT.
A pistol row is DONE only with: aim pose, aimed reload (loaded + empty), per-shot cycle where the gun has one, all
stances run and looked at, the three yes columns, a run id. Hi-Standard: all of that except braced / vehicle seats.

---

# Two-handed pistol aim (2026-10-11)

User: *"We were supposed to also have two hands holding handguns in ads btw"* - part of the "everything under aimed
reloads" order. Continues `docs/proposals/ads_bolt_2026-10-04` (same harness, same baker).

**Status: Colt .45 done end to end and tested in the engine; STAGED ONLY, waiting for the user to approve the pose
before the other five handguns are built.** Nothing is in `docs/tools/assets/fixes`, nothing is in the mod tree,
nothing deployed, no engine change.

## 1. How the pistol aim pose works today (from the code)

* Aiming plays the gun's `<prefix>_charge` row of `models/player/base/fps_anims_pistol.txt`: a ONE-frame pose clip
  (`viewmodel/coltpose00.skc` for the Colt, Beretta, Webley, Nagant and M10; `p38pose00.skc`; `hs_pistol00.skc`).
  Hip idle to aim is the row's 0.3 s crossblend. The three clips are the same pose within 0.6 u.
* In those clips the left arm hangs at the hip (left hand 30 u below and 20 u left of the eye) - the pistol is
  held one-handed. The rifles get their left hand from their own aim clip in exactly the same way.
* Aimed fire plays no clip (`player_Torso.st` `ATTACK_PISTOL_PRIMARY_AIM` -> `viewmodelanim charge`); the kick is the
  procedural muzzle flip of `cg_view.c` (`cg_adsPistolKick`), which turns the WHOLE first-person rig about the wrist.
  So a support hand keyed into the aim pose rides the recoil with the gun by construction.
* The off hand is drawn while aiming for every gun that has a sight row (`CG_AdsRigSolveOwns`); a pistol without one
  keeps today's hidden off hand (`cg_adsHideOffHand`) and simply stays one-handed.
* Every pistol that has no prefix of its own (Luger, TT-33, PPK, Nambu, Welrod, C96 via `p38`, the silenced ones, the
  Colt variants) uses `colt45_*` or `p38_*`, so it inherits the pose of that row.

So the two-handed hold is DATA only: a new one-frame aim clip per row, and the aimed reload re-baked to start and end
on it. No cgame change.

## 2. The pose (`tools/mk2h.py`, recipe `assets/colt45_recipe.json`)

A wrap-around support grip: the left palm on the left grip panel over the firing hand's fingertips, left fingers
around the front of the firing hand's fingers with the index pressed up under the trigger guard, left thumb forward
along the frame under the slide, outboard of the right thumb. Nothing on the slide, nothing near the sights.

Built, not hand-keyed, so it can be repeated per gun:
1. **Mirror** the firing hand's grip through the gun's vertical centre plane. The plane and the axes are the SIGHT
   LINE's (rear sight -> front sight, the sight row's up), not the weapon tag's, because the Breakthrough pistols are
   root-frame meshes with other axes. The rig's left/right bones are mirror frames with local z flipped
   (`F = diag(1,1,-1)`, measured from the hand meshes by `tools/mirconv.py`; finger flexion is +z on both sides).
2. **Move it into a support grip**: 0.7 u forward, 0.5 u out, 1.4 u down (index under the guard), then 25 deg of yaw
   about the front strap so the wrist swings out to the left and the fingers reach further round.
3. **Fingers**: the index takes the middle finger's curl (the mirrored trigger finger would lie in the guard), all
   four opened 12 / 25 / 15 deg at knuckle / middle / tip to go around the firing hand; the thumb's three bones are
   aimed at points on the frame.
4. **Left arm** by two-bone IK. The retail pose's left shoulder sits 2 u in FRONT of the eye (it was posed for a
   hanging arm), which forces a 65-90 deg wrist; the shoulder is turned back (clavicle 121 deg, to about where the
   right one is) and the elbow put out to the left. Wrist bend 8 deg (the firing hand's is 33).
5. Everything else - trunk, eye, the whole right arm and its fingers, `tag_weapon_right` - is bit-identical to the
   source pose (`right_same 0.0`), so the rig solve and the sight picture cannot change. `tag_weapon_left` is keyed
   onto the gun, as the `_ads` clips do.

Offline previews (`--view`, the calibrated ADS camera of `ads_bolt` + close-ups) agreed with the engine stills to
within what can be seen; `evidence/colt45_grip_closeups_offline.jpg` is the fit check from the side, front and top.

## 3. The aimed reload on that pose (`hold_bake.py` `left_grip`, `tools/bake_p.py`)

The shipped Colt aimed reload (`fixed_right`, bug-3467) is reproduced byte for byte by `bake_p.py colt45_reload`
(md5 ebe2bb7b) and is still reproduced after the change below.

With a hand on the gun the old bake threw it out of view in two frames: it blends toward the retail left hand, which
starts and ends hanging at the hip. New recipe option `left_grip {fa, fb, way, hold}`: the support hand travels from
the aim grip straight to where the retail art has it at frame `fa` (12) and from frame `fb` (61, the palm under the
magazine floor) back onto the grip, on a smootherstep with a sideways bulge so the fingers come off the firing hand
before the hand drops; its fingers open on the same track, twice as fast. Between `fa` and `fb` the retail relation
is untouched. First and last frame are the aim pose exactly.

## 4. Engine runs (private install `G:\mohaa-adsanim`, slot word `adsbolt`, m3l2 harness spot, 1280x720)

The install was refreshed first: exe / game / gl1 / gl2 and `cgames/cgame_1022d.dll` from `SCRATCH\built_1022d` (the
released v1.10.21 set: exe affd0767, game 689d0db1, gl2 4bc77ba0, cgame 6d6799b2), and its `pristine` autoexec /
coop_defaults from the released copies. The old files are in `G:\mohaa-adsanim\bak_pre1022d\`. The harness plumbing
(`coop_mod/weather.scr` + marker shader) was rebuilt on the RELEASED weather.scr (`tools/mkbase.py`); the overlays up
to ab60 carried a copy from before 2026-09-28.

Overlay = plumbing + the released fixes-pak `fps_anims_pistol.txt` with `colt45_charge` repointed + the two clips
(`tools/mkov.py`; `G:\mohaa-adsanim\ov_2h_c.pk3` md5 58e2771f). Released cgame, no test build.

| run | what | result |
|---|---|---|
| th1 | first pose (mirror, hand under the guard, shoulder untouched) | plays, but reads as one lump of flesh from the eye |
| th2 | hand yawed out, thumb forward, shoulder back | reads as two hands; a detached sliver of left cuff at the bottom edge |
| th3 | elbow further out (final) | below |

th3 (2026-10-12 01:10, 4.1 min, 1488 shots, 0 script errors, window clean), `logcheck.py th3` and
`tools/democheck.py th3`:

| scenario | ADS pose factor | sight line |
|---|---|---|
| settled aim: stand, crouch, prone, lean L, lean R, crouch-lean L, crouch-lean R | 1.00 | 0.0 deg |
| demo, raise (50 frames) | 0.23 -> 1.00 | settles to 0.01 deg |
| demo, two aimed shots | 1.00 | kick 3.93 / 3.98 deg, back to 0.01 deg |
| demo, aimed reload (170 frames) | 1.00 | max 1.30 deg (logcheck gate 6), 0.35 deg in its last sixth |
| aimed reload: crouch, prone, lean L, lean R | 1.00 | max 1.3 deg, edges 0.6 - STAYS IN ADS |

Looked at, frame by frame (sheets in `G:\mohaa-adsanim\gifs\twohand\`):
* raise - the support hand comes up from the lower left at about 2/3 of the raise and closes on the gun; it never
  crosses the lens. Two fingers show open for one or two frames just before it lands (f26).
* fire - both hands ride the flip as one piece; the slide cycles between the thumbs; nothing separates.
* aimed reload - starts and ends on the pose; the hand leaves down-left, comes back open from the left and wraps.
* lower - the hand is off the gun and out of view within eight frames, the gun is at the hip by frame 20.

## 5. Not verified / known weak points

* **Only the Colt .45 mesh was looked at.** `colt45_charge` is also the pose of every pistol that falls back to the
  Colt prefix (Luger, TT-33, PPK, Nambu, Welrod, silenced Colt / TT / Luger / Beretta, the Colt variants) - not one of
  them was run. The support hand wraps the firing HAND, which is the same on all of them, so first-order it fits; a
  longer grip or a fatter frame can still poke through.
* P38, Hi-Standard, Beretta, Webley, Nagant: not built yet.
* The magazine exchange itself happens below the frame, as in the shipped clip: for about 1.5 s only the firing hand
  and the gun are on screen. That is the next step's work (retune the aimed pistol reloads), not changed here.
* Braced and vehicle seats: not run for the pistol.
* Hip to aim while moving, sprint-out and weapon switch from the aim: not captured.
* A wandering NPC walks into two of the stance stills; it is the map's, not an artefact.

## 6. Shipping it (after approval)

Per gun: the pose clip -> `docs/tools/assets/fixes/models/human/animation/viewmodel/pistol/<gun>_ads2h.skc`, the
`<gun>_charge` row of the fixes-pak `fps_anims_pistol.txt` repointed (the mod-tree copy stays the released one, as the
`gen_fixes_pak.py restore` recipe needs), the re-baked `<gun>_reload_ads.skc` over the shipped one, manifest entries.
`coop_vmAdsAnims` does not gate the pose (it is the aim row itself); a one-key A/B would need a cvar-selected row.

## Files

`tools/` (working copies in `SCRATCH\ads2h`): mk2h.py (pose builder), var.py (variant sheets), mirconv.py /
insp.py / gungeo_q.py / lpath.py (measurements), bake_p.py (pistol reload bake), clipview.py / blendsim.py (offline
frames), mkbase.py / mkov.py (overlay), run_2h.py + go.sh (harness run under the heavy lock + slot), democheck.py
(per-segment numbers), sheet.py (sheets, GIFs). `assets/`: the recipe and the two Colt clips (pose a97b8330, reload
ca75453b). `evidence/`: stills. Sheets, GIF and MP4: `G:\mohaa-adsanim\gifs\twohand\`.
