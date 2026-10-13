# HANDOVER (2026-10-13 early morning, PISTOL lane) - read this first; everything below the next `---` line is history

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
the EMPTIED reload (runs: @@SRUN@@). n/m = not measured.

| gun | stand, loaded | stand, emptied | crouch | prone | lean L | lean R | run (stand) |
|---|---|---|---|---|---|---|---|
@@TABLE@@

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
Bugs of this session: @@BUGS@@.
