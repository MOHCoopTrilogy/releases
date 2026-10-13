# SMG lane of the aimed-animation work (started 2026-10-12)

Scope: the `## smg` rows of `..\coverage.md` (18 weapons). Method = `..\README.md` (the standard, the bake pipeline,
gunphys, the offline centre-box check, staged rows, cgame hooks). Everything here is STAGED: nothing is in the mod
tree or the fixes pak. Engine: worktree `openmohaa-hzm-ads-smg`, branch `ads-smg-next` (= ads-next 94bb3dca + two
generated rows of `cg_adssights.h`, see the handover; `cgame_smg3.dll` in `G:\mohaa-adsanim3\cgames` has both).
Test game: `G:\mohaa-adsanim3` (owner adsanim3, port 12578).

## HANDOVER (2026-10-13 morning, runs se20 - se24) - read this first

Engine unchanged: `ads-smg-next` **9ae4d1b0**, test build `cgame_smg4.dll`. Overlay of these runs:
`SCRATCH\adssmg\ov_g8.pk3` (se20-22), `ov_h3.pk3` (se24, + the M1A1 remodel) = `mkov_smg.py <out> --extra ..\..\..\mp18_skin_2026-10-12\assets`
(the APPROVED MP18 skin is in it). Run ids used: sa1-sd2, se1-se24. **Next: se25.** FROZEN (integration agent is shipping them from this folder): the staged
files, rows and README sections of MP40, Silenced MP40, MP40 R2 - do not touch; `fps_anims_smg.txt` is byte-identical to
commit 11743da but for ONE appended block (the M1A1 remodel's four rows, before the closing brace).
**Do NOT run `stage_rows.py` any more** (bug-3807): it regenerates the file from `docs/tools/assets/fixes/...`, which the
integration now changes, and moved eight MP40-family rows here (caught in the diff, restored from HEAD, never committed).
New rows: `cd assets; python ../tools/append_rows.py <weapon key> "<block title>"` (`--keep` for a second gun before a commit).

| gun | state |
|---|---|
| MP40, MP40 R2, Silenced MP40 | done, FROZEN |
| Thompson, retail mesh (12 tiks) | finished (section below); rows held until all five meshes are built |
| **MP18** | the three open points done and run in all eight stances (below); waits for the user's eyes |
| **Sten** | cocking hand redone, prone now passes; all eight stances (below); waits for the user's eyes |
| **Thompson (M1A1 Remodel)** | built on its own handle, all eight stances run (below) |
| Thompson M1928 / 1928 Tommy / 50rd / 27A1 Commando, PPSh, grease guns, PPS-43, Type 100, Moschetto | NOT started |

### Thompson (M1A1 Remodel), `thompsonsmg_m1a1dk` - built (run se24)

`smggun.OWN['thompson_m1a1']` (its own bone `chamber`: a handle on the right, forward x 3.57, travel 6.1; open-bolt gun
clips for its one tik, the handle rests BACK when cocked) + `smgbake.GUNS['thompson_m1a1']` = the retail-mesh Thompson's
choreography on this gun's sight line (`thompson_m1a1`) and handle, the firing hand with the SIDE hook (closed fist from
below; `y` 1.6, `front` 0.8, `over` -0.2), hip = the retail technique (left hand over the top onto the handle).
**THE ROW KEY IS THE WEAPON'S NAME, NOT THE SIGHT KEY** (bug-3806): the tik says "Thompson (M1A1 Remodel)" -> rows
`coopr_thompson_m1a1_remodel_reload[_empty][_ads]`. Run se23 had them as `coopr_thompson_m1a1_...`: the engine never
asked for them and played the prefix rows (the retail-mesh hand, straight fingers from behind) - its box figures passed
on the wrong clips. Kept as `evidence/thompson_m1a1_PREFIX_rows_played_wrong_key_se23.jpg`. Keys of the others (from
their tiks): 1928 Tommy = `thompson_1928_tommy`, 50rd = `thompson_50rd`, M1928 = `thompson_m1928`, and a SIXTH tik the
survey missed: `thompsonsmg_tommy27a1` "Thompson (27A1 Commando)" = `thompson_27a1_commando` (mesh not looked at yet).

| stance (se24, sway ON, beyond the envelope, no dry reference) | rounds left | emptied, after 0.64 s |
|---|---|---|
| stand | 0.01 % | 0.01 % |
| crouch / prone | 0.00 / 0.00 % | **1.27** / 0.00 % |
| lean left / right | 0.00 / 0.03 % | 0.01 / 0.12 % |
| crouch + lean left / right | 0.00 (whole window 0.34) / 0.80 % | 0.01 / 0.06 % |
| braced | 0.02 % | 0.02 % (whole window 0.56) |
| back on the aim | 0.069-0.077 deg | 0.070-0.076 |

Offline box 2.0 % (emptied, one frame, f64) / 0.7 %; gun between the keys: aimed empty 0.021 u / 0.012 deg; HIP empty
0.22 u / 1.28 deg (the retail hip clip's own motion - not looked into, the same family as the retail mesh's hip row).
LOOKED AT: twelve full-size engine frames of the cocking (`thompson_m1a1_cocking_hand_contact_frames_se24.jpg`: closed fist
up the right side, handle back, home - the eye sits so close to this receiver that most of the hand is hidden behind it),
twelve hip emptied frames at 62 % (`thompson_m1a1_hip_empty_contact_frames_se24.jpg`). ONLY MEASURED: the stance sheets
(`thompson_m1a1_reload_aimed_{empty,roundsleft}_stances_se24.jpg`), the four GIFs (`thompson_m1a1_reload_{aimed,hip}_{empty,roundsleft}_se24.gif`)
were not played back. Break-offs: run in se23 only (on the prefix rows; the engine side is the same), not re-run. Not
listened to (rounds-left sound = the Thompson's cut one). Finishes: this mesh has ONE tik - covered. NOT done on this
gun: a close look at the index on the handle in the engine (hidden behind the receiver from the eye), third person, AI.

### MP18 + Sten, what changed in se20 / se21 (the user's three points)

**a. The cocking hand = the SIDE hook** (`smgbake._HOOK_SIDE` / `_GRAB_SIDE`, `approach_r`, `let_add`; bug-3798). The overhand
hook (`_HOOK_BEHIND`, still used by the Thompson) showed the eye the back of a hand whose first phalanges point away -
the curl was hidden, hence "straight, splayed fingers". Now: a CLOSED FIST, thumb side up, that leaves the grip with next
to no turn (the firing grip already is that fist), comes up from below and behind the handle, the index alone opened to a
right angle: it runs forward past the handle's outer end and turns in across its FRONT face; the last 3 frames are a rise
from below (`approach_r`), the let-go is outward (`let_add`).
* MP18 (bar 2 u out of the right wall, tip y 0.44, front x 8.49): the index's second phalanx lies along the bar's front,
  the bar rests in the crook of the fist. Seen from the eye the fist is UNDER the bar's outer end and the index is hidden
  behind the bar - it reads as a fist holding the bar, not as a finger over it (weak point, said plainly).
* Sten (knob 0.75 u across on a short stem, IN the centre box when forward): only the index's LAST phalanx lies across
  the knob's front, 0.3 u under its centre (`y` 2.85, `front` 1.0, `over` -0.3): the fist is outboard, right of the box,
  the knob's top stays in sight over the finger. First try (`y` 0.75) ran the finger on over the tube's top: 2.2 % (bug-3802).
  During the pull the hand comes 8.8 u toward the eye and is LARGE at the lower right for about 0.15 s (below the box).
* Gun between the keys (`midframe.py`): MP18 aimed empty 0.053 u / 0.012 deg, hip empty 0.043 / 0.014; Sten aimed empty
  0.053 / 0.010 (the hand hardly turns now). Sten HIP empty = the retail clip, 0.36 u / 0.75 deg (retail's own motion, not changed).

**b. The brown mosaic** was the overlay drawing the RELEASED 1000 px sheets (bug-3799). With the approved skin in the overlay the
receiver rear is dark steel in the aim and through the reload (`evidence/mp18_approved_skin_aim_and_reload_fullsize_se20.jpg`,
full size). The rear ring's texels are still stretched (a few 6-8 px steps) - the skin's, not the reload's.

**c. The hand hid the drum** (bug-3800): `sidehold.HOLDS['mp40_mp18']` is now the same Sten template hand turned end for end
along the neck (`yaw` 180), rolled under it (`roll` 100), `out` 0.7 = an UNDERHAND hold: palm up under the neck, fingers up
its far side and over its top toward the eye, thumb on the eye's side beside the drum; the drum stands clear above and
outboard of the hand at the hip, in the aim, firing and through the reload (all five hold rows + both reload pairs rebaked).
`tools/holdtry.py` = the hold tried offline for a list of rolls before baking. The drum is SEEN going out and coming back:
its own `show` points - drawn out along the housing, then LOWERED beside the gun at the lower left, pouch, the new one up
the same way (the shared points carried it off the screen's left edge at once).
The STEN's hold is the retail one and is NOT changed: in its aim the hand and sleeve cover the magazine (decision below).

| stance (sway ON, beyond the envelope) | MP18 rounds left (se20) | MP18 emptied, after 0.64 s (se20) | Sten rounds left (se21) | Sten emptied, after 0.64 s (se21) |
|---|---|---|---|---|
| stand | 0.02 % | 0.05 % | 0.02 % | 0.03 % |
| crouch / prone | 0.02 / 0.01 % | 0.33 / 0.03 % (prone whole window 0.19) | 0.01 / 0.01 % | 0.09 / **0.46 %** (was 2.63) |
| lean left / right | 0.06 / 0.06 % | 0.41 / 0.04 % | 0.39 / 0.13 % (whole window 0.50) | 0.16 / 0.04 % |
| crouch + lean left / right | 0.01 / 0.15 % | 0.04 / 0.04 % | 0.61 / 0.04 % | 0.07 / 0.18 % |
| braced | 0.02 % | 0.02 % | 0.04 % | 0.05 % |
| back on the aim | 0.055-0.062 deg | 0.055-0.065 | 0.054-0.061 | 0.054-0.061 |

(Emptied figures with the dry-gun reference, as before. Offline: MP18 0.2 % both, Sten 0.1 % / 0.0 %. Reload lengths
unchanged: MP18 156 capture frames, Sten 188.)
* Break-off of an EMPTIED gun (se20 at 60 / 118 frames, se21 at 60 / 145 = in the pull): trigger and sprint - the reload
  runs to its end in the aim; next weapon - down at once, the next one comes up; aim let go - the framing goes to the hip
  while the row runs on. As the rounds-left cases.
* LOOKED AT: all eight stances of both guns, emptied, on the stance sheets; sixteen engine frames of the MP18's emptied
  reload; full-size engine crops of the cocking hand at every contact (MP18 standing, Sten standing); the MP18 hip
  emptied reload at fifteen contact frames; the MP18 aimed-empty GIF played back at its own size through the cocking;
  the skin at full size; every Sten finish in the aim; the Sten's switch break-off.
  Also looked at: the Sten's cocking hand PRONE at eight contact frames.
  ONLY MEASURED, not looked at: the rounds-left stance sheets of both guns, the Sten's hip GIFs (its hip clips are
  byte-identical to the commit before), the Sten GIFs played back. Not listened to. No AI run. Third person not re-run
  (the server's animation: the MP18's support hand there is still under the fore-end).
* Finishes: `evidence/sten_mp18_finishes_in_the_aim_se22.jpg` - all 8 Sten tiks (sten, bloody, blued, camo_desert / winter /
  woodland, chrome, gold) run in the engine, each with the cocked knob resting back; MP18 = 1 tik (no finish tik).
  `finishsheet.py` + `run_smg.py --parts stills --stances stand --guns <tik names>` (a key not in the table = that tik).
  NOT covered: the four other Thompson meshes; a per-finish sheet for the MP40 family and the Thompson retail mesh was not
  made in this session (their tiks are covered by script, list in the earlier handover).

Evidence (`evidence/`, all finished unless said): `mp18_reload_{aimed,hip}_{empty,roundsleft}_se20.gif` (560 px),
`mp18_reload_aimed_empty_frames_se20.jpg`, `mp18_cocking_hand_contact_frames_se20.jpg`, `mp18_hip_empty_contact_frames_se20.jpg`,
`mp18_gif_decode_{aimed_empty,aimed_roundsleft,hip_empty}_contacts_se20.jpg`, `mp18_reload_aimed_{empty,roundsleft}_stances_se20.jpg`,
`mp18_approved_skin_aim_and_reload_fullsize_se20.jpg`; `sten_reload_{aimed,hip}_{empty,roundsleft}_se21.gif`,
`sten_cocking_hand_contact_frames_se21.jpg`, `sten_cocking_hand_contact_frames_prone_se21.jpg`,
`sten_reload_aimed_{empty,roundsleft}_stances_se21.jpg` (columns are the MP18's offsets: the Sten's pull is only in the last one),
`sten_mp18_finishes_in_the_aim_se22.jpg`. Everything `_se11 ... _se18` of these two guns is superseded, kept.

**Decisions for the user:** (1) MP18: is the fist under the bar's end enough, or should the index show OVER the bar (costs
about 1 % of the box at the bar's tip, which lies on the box's right edge)? (2) Sten: the retail hold covers the magazine in
the aim - leave it, or give it the MP18's underhand hold (changes a released aim pose)? (3) Sten: the hand is large near
the eye at the end of the 8.8 u pull - accept, or let the hand stop short and the handle run on to the sear by itself?
(4) MP18 third person still shows the mp40 hold (server animation).

**Tool caveats found:** the offline renderer does not hide the gun's own drum / magazine surface during a reload (two drums on
the offline sheets, one in the engine; bug-3801); `eyezoom.py --w` does not scale the render (crop in 1280 x 720 terms only);
`sidehold.py` re-orders `rows_extra.json` (content the same); the bake reads the released `mp40_charge` clip with
`IRONSIGHT_EXTRA_PAKS` unset and the staged one with it set - they differ only in the left arm, which the hold replaces.
Raw frames: se20 - se24 moved to `H:\hzm_archive\smg\` after the evidence was made (se10 - se19 are there too). From Git-Bash
`robocopy //E` does nothing (the switches arrive as paths): run the move from PowerShell.

**Next, in this order:** the other Thompson meshes - 1928 Tommy (its own mesh, no handle bone, prop window f22-60), M1928 and
50rd (actuator on TOP, on the sight line: left hand over as the retail hip clip, gun dipped just under the box; the 50rd's drum
slides in from the side), 27A1 Commando (survey it first) - each with rows under its NAME key; then PPSh, both grease guns, PPS-43, Type 100,
Moschetto; a finish sheet per changed gun.

## Earlier handover (2026-10-13 night, runs se10 - se19) - the MP18 / Sten hook, hold and OPEN-points paragraphs here are superseded by the above

Engine: `ads-smg-next` is at **9ae4d1b0** = 7b4bc029 + ONE commit: per-weapon view rows for EVERY view animation
(`coopr_<weapon key>_<suffix>`: idle, charge, fire ...; cvar `coop_vmPerWeaponRows`). Test build
`G:\mohaa-adsanim3\cgames\cgame_smg4.dll` (smg3 = without it: the MP18's hold rows are then not shown).
Run ids used: sa1-sd2, se1-se19 (se14 never ran: disk full). **Next: se20.** Build (Git-Bash): `cmake --build .cmake --config Release --target cgame -- -m:4 -v:m`
(NOT `/m:4`: bug-3726 - check the dll's time before copying it).

### The lane's measure from now on: AS PLAYED, against the settled aim's SWAY ENVELOPE (user, bug-3718)

A reload may add under 2 % of the centre box beyond everything the settled aim covers through a whole sway period, in
every frame. ONE implementation for all lanes: `..\tools\swayenv.py` (the heavy lane's `boxeng.py --sway` lines as a
function; boxeng itself is untouched, it could import it). Here: `run_smg.py --tail 360:4` (the settled aim for one sway
period after the reload window, mark `DEMO settle`), `reloadbox.py` / `measure_run.py` print `AS PLAYED: beyond the sway
ENVELOPE` and store `env_max`, `env_cover`, `env_tail`; `status_reload.py` passes on it when the tail was captured.
An EMPTIED gun starts its reload in its last shots' smoke with the view still pitching back: its figure is taken after
the first 40 capture frames (0.64 s; `env_after40` = the heavy lane's rule, bug-3719). `measure_run.py --nodry` = without
the dry-gun reference: use it for a gun whose dry pose does not differ INSIDE the box (Thompson) - after a 30-round burst
that reference swallows 19-73 % of the box. Guns passed with the stricter six-frame reading stay passed.

| gun | state |
|---|---|
| MP40, MP40 R2, Silenced MP40 | done, unchanged (below) |
| Thompson, retail mesh (12 tiks) | **finished to the four decisions** - table below. The other four Thompson meshes are NOT built: **do not ship the Thompson rows before all five** |
| MP18 | **REOPENED by the user and reworked with the Sten as one family** (held by the magazine neck; below) |
| Sten | **built** (aimed + hip, open bolt; below) |
| Thompson remodel / M1928 / 1928 Tommy / 50rd, PPSh, grease guns, PPS-43, Type 100, Moschetto | NOT started (order and facts: section 3 and the Thompson survey below) |

### Thompson, retail mesh - the four decisions (runs se10, se12)

1. **Measure**: the envelope (above); the aim framing is untouched.
2. **Knob and slot** (bug-3720): a ROUND knob 0.8 u across standing 0.7 u out of the right wall (`smggun.round_mesh`, own bone
   `coop_bolt` as before); the painted knob ring is gone from the slot's front on STAGED copies of all ten sheets the
   twelve tiks read (`tools/stage_slot.py`: the slot's own rear end mirrored over the ring; `--preview`; the 6.5 MB .tga
   twin of the HD .dds is not staged, `--all` writes it). `evidence/thompson_mesh_round_knob_slot_repainted_side_se10.jpg`.
3. **Pull** (bug-3721): `pullk=(0.6, 0.45)` - the gun comes 0.24 u back (was 0.91), cant and dip kept.
4. **Magazine seen**: `show=` points - in view at the lower left as it leaves (clip f15-22) and arrives (f31-38), never in the box.
5. Also (se12): the firing hand comes to the knob FROM BEHIND (bug-3724, as on the MP18 / Sten) - in se10 it was a large
   flat hand from the right that hid the knob.

| stance (sway ON, envelope) | rounds left (se10; stand also se12) | emptied, after the last shots' 0.64 s, NO dry reference (se12) | back on the aim |
|---|---|---|---|
| stand | 0.00 % (se12: 1.39 %) | 0.01 % | 0.07-0.08 deg |
| crouch / prone | 0.07 / 0.31 % | 0.01 / 0.85 % | 0.07-0.08 |
| lean left / right | 1.20 / 1.49 % | 1.10 / 0.06 % | 0.07-0.08 |
| crouch + lean left / right | 0.09 / 0.01 % | 0.00 / 0.01 % | 0.07-0.08 |
| braced | 0.19 % | 0.03 % | 0.07 |

(The rounds-left clip is the same file in se10 and se12, hash b0b8bc40. se10, emptied, with the old side-on hand: 0.1-2.0 %,
lean right 2.7 % in ONE frame = the 41st after the last shot. Against the old six-frame mask the same captures read
3-12 %: that is the aim's own sway.) Offline: 1.1 % both; gun between the keys 0.09 u / 0.07 deg (`midframe.py`).
Break-off (se10, rounds left at 50 / 105 frames, emptied at 118): trigger and sprint - the reload runs to its end in the
aim; next weapon - the gun goes down at once; aim let go - the framing goes to the hip while the row hands over. As the MP40.
Looked at: eight stances on `evidence/thompson_reload_aimed_empty_stances_se12.jpg`, sixteen engine frames
(`..._frames_se12.jpg`), a zoom of the pull, the lean-right smoke frames of se10; the GIF decode sheets only at thumbnail size.
Evidence: `evidence/thompson_reload_{aimed,hip}_{empty,roundsleft}_se12.gif` (current; the `_se10` set shows the old
hand from the right), `thompson_reload_aimed_{empty,roundsleft}_stances_se12.jpg` (rounds left: stand only; all eight =
`..._roundsleft_stances_se10.jpg`), `thompson_reload_aimed_empty_frames_se12.jpg`, `thompson_mesh_round_knob_slot_repainted_side_se10.jpg`,
`thompson_third_person_se10.jpg` (the gun's LEFT side: the camera cvars do not frame its right side, bug-3666 - the knob is
not shown in third person).
Weak points seen: the index finger lies OVER the knob through the pull, so the knob itself is hidden until the hand
leaves (a small bump right of the receiver after it); a fingertip of the left hand shows inside the box's left edge for
about two frames as that hand leaves the fore-grip (clip f4-5); the knob is one flat dark colour (it samples one texel);
the hip clips were looked at only at thumbnail size; not listened to; the eleven finish tiks were not run one by one
(same mesh, rows and script-made sheets - the ten staged sheets were looked at on `stage_slot.py --preview`).

### MP18 + Sten = one family: HELD BY THE SIDE MAGAZINE (user; bug-3722, runs se11, se13, se14)

**Hold** (`tools/sidehold.py`, rows `coopr_mp40_mp18_idle / charge / fire / fire_secondary / pullout`, need cgame_smg4):
the Sten's own retail hold (hand place on the magazine, rotation, fingers of `sten_idle.skc`) carried onto the MP18's
drum NECK (between housing and drum, 0.85 of the way out, turned by the neck's 34 deg rake); copies of the mp40 clips
with ONLY the left arm changed (asserted per frame). `mp40_putaway` names a clip that is not in the game - no row.
A row must carry the exact suffix the engine asks for: `..._idle`, not `..._idle1` (bug-3723: only rows with `weight`
lose their digit). THIRD PERSON is the server's animation (group mp40): the support hand there is NOT changed.

**Reloads** (`smgbake.py`: `hold=`, `hold_prop`, `hip_proc`, `_GRAB_BEHIND` / `_HOOK_BEHIND`; `smggun.OWN['sten']`):
* the reload starts with the hand ON the magazine: thumb in for the catch (f5-9), magazine / drum drawn out to the LEFT
  along its housing and shown leaving, pouch, the new one in from the left, pushed home, a tug against the catch
  (f47.5; both cases), back in the hold. The prop is rigid in the holding hand and exactly in its seat whenever that
  hand is in the hold (`hold_prop`). Sten only: a palm slap on the magazine's end at f58 (on the sound).
* EMPTY: the firing hand turns into a hook beside the grip, comes to the handle FROM BEHIND (fingers forward over its
  top, index and middle hooked down its front, ring and little finger folded), pulls it back to the sear, lets go, home.
  OPEN BOLT as every SMG here: the handle STAYS BACK after the pull (the coordinator's note asked for "releases, flies
  forward" - that would be a closed bolt; a decision if wanted).
* MP18 hip rows = the SAME story on the hip pose (`hip_proc`; the pack clip neither starts nor ends in the hold).
  Sten hip rows = the RETAIL clip (gun canted, slap, left hand over the top onto the bolt): rounds left to the slap then
  its end pose (no cock); empty = retail, the hand turned onto the handle, the handle on the hand's frames (f68-72).
* Sten sound: the retail reload sound as it is for the EMPTY rows (slap f58, bolt clacks f71 / f74.5: the aimed pull is
  on them, f68-74); rounds left: cut after the slap (`snd_cut` 61-66). The first build tightened the sound on a wrong
  assumption about the reload's length (bug-3725, corrected by bug-3760; `snd_tight` stays in smggun, unused). Not listened to.
* The Sten's cocked handle now RESTS BACK (open bolt): in the settled aim the knob stands right of the tube's rear.

| stance (sway ON, envelope) | MP18 rounds left (se13) | MP18 emptied (se11; dry-gun reference) | Sten rounds left (se16 / se17 / se19) | Sten emptied (se18; dry-gun reference) |
|---|---|---|---|---|
| stand | 0.00 % | 0.54 % | 0.00 % | 0.70 % |
| crouch / prone | 0.01 / 0.01 % | 0.54 / 0.21 % | 0.00 / 0.14 % | 0.92 / **2.63 % - NOT passed** |
| lean left / right | 0.02 / 0.23 % | 1.37 / 0.46 % | 0.01 / 0.05 % | 0.83 / 1.04 % |
| crouch + lean left / right | 0.01 / 0.07 % | 0.03 / 0.59 % | 0.05 / 0.01 % | 0.19 / 1.45 % |
| braced | 0.03 % | 0.05 % | 0.01 % | 0.67 % |
| back on the aim | 0.06 deg | 0.01-0.07 | 0.06 | 0.05-0.06 |

* **Sten, emptied, PRONE: 2.5-3.8 % for 8 capture frames (clip f66-70)** - the index and middle fingertips of the firing
  hand stand in the box's lower right corner as they reach the knob (`evidence` zoom not kept; reloadbox `--dump` on
  `se18 sten__proneadsE__`). Same cure as the coordinator's note 1 below; not done.
* The emptied figures use the dry-gun reference (the forward handle of both guns lies in or at the box); it adds 0.7-18 %
  of the box here, far less than on the Thompson. MP18 se13 re-ran four emptied stances: 0.16-0.88 %.
* Reload length, measured: MP18 156 capture frames (2.5 s = its 76-frame row), **Sten 187 (3.0 s = the WHOLE 91-frame
  row, bug-3760)** - the first Sten build (se11, se14 never ran) assumed f78 and tightened the sound for nothing; the
  current one (se18) pulls on the retail sound's clacks (f68-74), hand home f80-86. Rounds left: all done by f66, the last
  0.8 s is the settled aim (the retail clip fills it with the bolt pull) - shortening it is a server item, a decision.
* Gun between the keys (`midframe.py`): MP18 0.09 u / 0.07 deg, Sten 0.07 u / 0.04 deg, MP18 hip 0.10 u / 0.08 deg.
* Break-off (MP18 se15, Sten se17; rounds left, 105 frames in): trigger / sprint - the reload runs to its end in the aim;
  next weapon - down at once, the next gun comes up; aim let go - the framing goes to the hip while the row hands over.
  Not run: break-off of an emptied gun for these two, an AI with either.
* Looked at: every stance of all four cases on the stance sheets, sixteen engine frames of each emptied reload, zooms of
  both hands (MP18) and of the pull (Sten, also prone), hip rounds-left frames of both, third person of the MP18.
  The GIFs were decoded only at thumbnail size. Not listened to.

Evidence (`evidence/`): `mp18_reload_aimed_{empty,roundsleft}_se13.gif`, `mp18_reload_hip_{empty,roundsleft}_se15.gif`
(the hip idle hold is in from se15 on), `mp18_reload_aimed_roundsleft_stances_se13.jpg`, `mp18_reload_aimed_empty_stances_se11.jpg`,
`mp18_reload_aimed_empty_frames_se13.jpg`, `mp18_third_person_se15.jpg` (the support hand is under the fore-end there:
third person is the server's mp40 animation, not changed); `sten_reload_aimed_empty_se18.gif` (current),
`sten_reload_aimed_roundsleft_se11.gif`, `sten_reload_hip_{empty,roundsleft}_se17.gif`, `sten_reload_aimed_empty_stances_se18.jpg`,
`sten_reload_aimed_roundsleft_stances_se16.jpg` + `_se17.jpg`, `sten_reload_aimed_empty_frames_se18.jpg`, `sten_third_person_se17.jpg`.
Superseded, kept: `sten_reload_aimed_empty_se11.gif`, `sten_reload_hip_*_se11.gif`, `sten_*_se11.jpg` (the f62-68 pull on the
tightened sound), `mp18_*_se6.*` (the one-handed look), `thompson_*_se9/_se10.*`.

**OPEN on this pair (coordinator, 2026-10-13 morning, after the user saw the GIFs) - do these first:**
1. The cocking hand still reads as straight, splayed fingers on the approach (MP18 clip f48-56, Sten f62-70) and closes
   only at the bar: seen from behind, the hooked second phalanges point away from the eye, so index and middle look
   straight, and ring / little finger show their nails. Wanted: fingers curled on the way, the hand coming from BELOW.
   Where: `_GRAB_BEHIND['dir']` (more from below: z positive), `_HOOK_BEHIND` (more flexion at the first joints, read the
   `grab fit` print), `beside` / `turn` in the hook, Sten `y` further out. This also cures the Sten's prone figure.
2. "The MP18's receiver rear shows as a mosaic of big brown squares": the lane's overlay shows the RELEASED sheets
   (`textures/coop_mp18/body.jpg` etc.: 1000 x 1000 JPEGs of 63-110 KB - their 8-pixel JPEG blocks at 12 u from the eye).
   The approved skin (`docs/proposals/mp18_skin_2026-10-12/assets`) is not in the overlay: build it with
   `mkov_smg.py <out> --extra <that assets dir>` and look again. Not done, not verified.
3. The hand on the drum hides the drum from the eye (the back of the hand is toward the eye, the thumb on the far
   side): `sidehold.py` `roll` (SH_ROLL) / `out` turn the hold about the neck; the same look at the Sten's hold.
4. Finishes / variants (user: "all of these new guns will need their camo/variants too"). Covered by script, every tik on
   the mesh: MP40 11 (mp40, bloody, blued, camo_desert / winter / woodland, chrome, gold, guanmp40, guanmp40s, lv_mp75),
   Silenced MP40 1, MP40 R2 1, MP18 1 (it has no finish tik), Sten 8 (sten, bloody, blued, camo_desert / winter / woodland,
   chrome, gold), Thompson retail mesh 12 (thompsonsmg, bloody, blued, camo x3, chrome, gold, guantommy, hobbstomworn,
   lv_famastommy, lv_tttommy; slot repainted on all ten sheets they read). NOT covered: the four other Thompson meshes
   (m1a1dk, tommy1928d, tommy28, thompson50). The per-finish AIM SHEETS the user asked for are NOT made (only
   `stage_slot.py --preview` for the Thompson sheets); the MP18's hold rows answer to the key `mp40_mp18` only.

**Raw frames.** Nothing was deleted. G: filled up twice (bug-3761): se13 and se16 are partial runs (their complete
captures are measured; `measure_run.py` names the incomplete ones), se14 never ran. Finished runs are archived on
`H:\hzm_archive\smg\` (se10 - se19; se10 / se11 went by way of C:). The tools read `G:/mohaa-adsanim3/runs`: move a
folder back (or set `ADS_RUNS` for the tools that take it) to measure it again. An aimed capture with `--tail` is
530-650 frames of 0.54 MB: check `df /g` before a run.

**Next, in this order:** the four OPEN points above; the Sten's prone figure; then the other four Thompson meshes
(survey below; the remodel and the top-knob pair can use `_GRAB_BEHIND`), PPSh, grease guns, then PPS-43 / Type 100 /
Moschetto with a lowered work pose (section 3).

## Earlier handover (2026-10-13, runs se4 - se9) - the MP18 and Thompson paragraphs here are superseded by the above

Engine: `ads-smg-next` is at 7b4bc029 = 94bb3dca + TWO commits, each ONE generated row of `cg_adssights.h`
(`tools/patch_sights_row.py` from `sights_override.json`): f1802d87 the Silenced MP40's (F / R z 0.45 u higher), 7b4bc029
the MP18's (F_root / R_root z 0.3 u higher, eye relief 12.34 u). Built as `G:\mohaa-adsanim3\cgames\cgame_smg3.dll`
(`cgame_smg2` = without the MP18 row, `cgame_smg1` = without either). Each row belongs TOGETHER with its staged mesh
(`mp40silenced.skd`, `coop_mp18/mp18.skd`) - never one without the other (the eye would look over or under the sights).
Run ids used: sa1-sd2, se1-se9. Next: se10. Build: `cmake --build .cmake --config Release --target cgame` in the worktree.

| gun | state |
|---|---|
| MP40 (reference) | done (section 2), unchanged |
| Silenced MP40 | **done** (run se4, sway on, cgame_smg2, eight stances): rounds left 0.1-1.5 %, empty 0.1-0.7 %, settled aim alone 0.0-0.9 %, back on the aim 0.05-0.07 deg. Rear leaf shaped into a notch block (below). Looked at: stance sheets, the four GIFs decoded, third person |
| MP40 R2 | passes (sc4; se2 stand with sway on: 0.1 % rounds left, 1.4 % empty). Per-shot handle travel looked at in the engine (se2) |
| MP18 | **done** (run se6, sway on, cgame_smg3, eight stances): rounds left 0.2-1.0 %, empty 0.2-1.2 % (against the dry gun's own pose), settled aim alone 0.0-0.4 %, back on the aim 0.04-0.06 deg. Eye relief +4 u, sights 0.3 u taller, side-drum physics, left hand closed on the drum, firing hand hooked on the handle bar's end. Table and weak points below |
| Thompson (retail mesh `ThompsonSMG.skd`: Thompson + its eleven finish tiks) | **built; passes with aim sway OFF** in all eight stances (run se9: rounds left 0.3-1.0 %, empty 0.2-1.5 %). **With sway ON it does not pass reliably and cannot: its settled aim ALONE is at 0.1-6.3 % (se8) - a decision for the user, below.** The other four Thompson meshes are NOT built and show these prefix rows meanwhile |
| Thompson remodel / M1928 / 1928 Tommy / 50rd, Sten, PPSh, grease guns, PPS-43, Type 100, Moschetto | NOT started (section 3 has the facts; the Thompson survey is below) |

### Sight raises made (coordinator's blanket rule: the minimum that passes, believable, checked in third person)

| gun | raise | how | before / after | third person |
|---|---|---|---|---|
| Silenced MP40 | both sights 0.45 u (run se1) | `sightraise.py`, then `sightshape.py --surf metal3 --box 6.64,6.85,-1.6,-0.25,-6.35,-5.37 --half 0.55,0.24`: the raised leaf was a plate 0.1 u thick and 0.96 u tall (a spike from the side) - now a notch block 1.1 u long at the foot, 0.48 u at the tip; x only, the eye's picture is the same | `evidence/mp40silenced_aim_before_after_se1.jpg`, side: `mp40silenced_mesh_sights_raised_side.jpg` (spike) -> `mp40silenced_mesh_sights_shaped_side.jpg` | `evidence/mp40silenced_third_person_se4.jpg`: a small block on the receiver, hooded front post; no spike |
| MP18 | both sights 0.3 u + eye relief 8.34 -> 12.34 u | `sightraise.py models/weapons/mp40_mp18.tik ... 0.3 --box Cube1:1.8,2.25,-5.42 --box Cube1:25.3,26.1,-4.2`, then `sightshape.py --surf Cube1 --box 1.86,2.20,-2.8,-2.0,-5.98,-5.32 --scale 3.2,1.5` (run with `IRONSIGHT_EXTRA_PAKS` = an overlay holding the skd being shaped). Search: `sighttry.py` - settled aim alone, worst pair of sway states 3.4 % at relief +4 alone, 2.4 / 2.2 / 2.4 / 2.2 % at 0.2 / 0.3 / 0.45 / 0.6 u (from rest 1.1 -> 0.4 %): 0.3 u is where it stops improving | `evidence/mp18_aim_before_after_se6.jpg`, side: `mp18_mesh_sights_raised_side.jpg` | `evidence/mp18_third_person_se5.jpg`: small rear block and front post, reads as the gun's own sights |

For a release each needs, in ONE deploy: the staged skd + its hunk in `ironsights_2026-09-28/sights.json` (the values in
`sights_override.json`; the MP18 is a root-frame gun: F_root / R_root as well as F / R, and `relief`) + a regenerated
header. The shared sights.json is NOT edited (the lane's tools read `sights_override.json` through smgbake;
`SMG_NO_SIGHT_OVERRIDE=1` switches it off, `SMG_SIGHT_OVERRIDE_FILE` points at a trial file).

### MP18 (run se6) - what it does

Aimed, EMPTY (`coopr_mp40_mp18_reload_empty_ads`, 76 frames):
1. f2-8 the left hand leaves the aim grip LOW and to the left (waypoint `via`, fingers closed), comes up to the drum from
   below-left and closes on it (`magmix` 0.55: the pack clip's spread fingers closed half way to the aim grip);
2. f13-17 the drum is dragged out along the raked housing (`well` (-0.6, -0.8, 0)): the gun is pulled LEFT (side 0.2 u)
   and cants toward the pull (roll 1.2 deg), swings back as the drum comes free; f40-44 the new drum is driven home: the
   gun is pushed RIGHT and forward and cants the other way (`smg_side_*`, class smg; next to no drop: 0.19 u, the muzzle
   sag while the hand is away is 0.9 deg with `shoulder` 0.5);
3. the left hand KEEPS HOLD of the seated drum (f44-63) while the firing hand turns into a hook right beside the grip
   (f43-48), goes up to the END of the handle bar (f55: index over the bar, second phalanx down its front face - hook
   `grab`, the hand = the rigid fit to three index joints), pulls it back to the sear (f55-61, gentle start), lets go
   (f63), goes home and turns back last (f70-74); the left hand returns to its grip (f63-71).
Aimed, rounds left (`..._reload_ads`): 1 and 2, a tug outward on the seated drum, home. No pull.
Hip: rounds left = the pack clip to the seat, then its end pose (no mimed cock); empty = that + the same firing hand
(hook pose + `grab`) on the gun clip's own curve.

| stance (run se6, sway on) | rounds left | empty (dry-gun reference) | settled aim alone | back on the aim |
|---|---|---|---|---|
| stand | 0.5 % | 1.2 % | 0.2 % | 0.04-0.06 deg |
| crouch / prone | 0.2 / 0.3 % | 0.4 / 0.4 % | 0.2 / 0.0 % | 0.06 |
| lean left / right | 1.0 / 0.8 % | 0.4 / 0.5 % | 0.2 / 0.4 % | 0.06 |
| crouch + lean left / right | 0.7 / 0.5 % | 0.3 / 0.7 % | 0.3 / 0.2 % | 0.06 |
| braced | 0.2 % | 0.2 % | 0.1 % | 0.05 |

Offline (every clip frame, drum drawn): 0.2 % both. Looked at: all eight stances on the sheets, twelve full-size engine
frames of the empty reload (`evidence/mp18_reload_aimed_empty_frames_se6.jpg`), the four GIFs decoded.
Weak points seen: the firing hand holds the handle at its very END (thumb and index around the bar's tip - further in,
the fingers over the bar stand in the centre box while the handle is forward); the left hand's index lies along the
drum's rear face as in the pack clip; in the full-frame GIFs (440 px) the hands are small - the frame sheet shows them;
the hip clips were looked at only on the decode sheet and one offline sheet; 0.04-0.06 deg at the row's end (engine item).
Not listened to. Not run: break-off mid-reload for this gun, an AI with it.

### Three things the next gun needs to know (all cost a run or more here)

1. **A firing hand that leaves the grip moves the GUN between the clip's keys** (bug-3659). The weapon tag hangs on that
   hand; the bake counter-keys it on the 30 Hz keys only. Run se5: the gun jumped on every other 16 ms frame (0.64 u /
   1.4 deg at the half-way points; 2-10 % of the box) and the offline tools - integer frames - saw nothing.
   `python ../tools/midframe.py <clip.skc>` prints it; under about 0.1 u / 0.1 deg it is not seen. Cure in the bake: turn
   the hand beside the grip, travel without turning, start the pull gently (`pull_soft` in smggun OWN, shared with
   smgbake's `pull_u`), give the turn frames. Applies to every `cock='R'` gun (Sten, M1A1 remodel) and to bake_hip_right.
2. **gunphys runs with hand=-1 in this lane: roll and side of every event are reversed** (bug-3660). Write a new action
   as it is seen and reverse it under the table, as `smg_side_*` does; check with the SB_TRACE print or the baked tag.
3. **Root-frame guns** (sights.json `frame_used: root` - the Breakthrough / pack meshes): the rig reads F_root / R_root
   (bug-3662), and a prop that is a copy of such a gun's skeleton has to be added to `gungeo.root_skds()` or the offline
   looks draw it 2-3 u off (bug-3661). `topprof.py` reads F / R against root-frame geometry for such a gun: its angles
   are off by the frame offset.

Also new: an EMPTY reload is measured against the DRY gun's own pose as well as the cocked aim (coordinator's decision 3,
bug-3665): `smgbake --box` does it for `*_empty`, `measure_run.py` for every E capture (`--nodry` = off; it prints how
much the dry mask adds - after a long burst that includes lingering smoke, so read it next to the offline figure).
`run_smg.py --parts sdemol` (lower-case L) = rounds left in EVERY stance of `--sstances`; `tpc` = close third-person
stills (the camera cvars do not frame the gun well, bug-3666: crop and enlarge). `evid.py <run> <gun key> <name> <sheet>
--stances` = the four full-frame GIFs + stance sheets + one decode sheet. `smgbake --cu out.jpg --cuhand L|R --cam f,l,u`
= a close look at one hand.

### Thompson, retail mesh (runs se7 / se8 / se9) - built, one decision open

**Gun.** `ThompsonSMG.skd` has one bone and no handle: the cocking slot is painted on the RIGHT of the receiver (x -2.2 ..
3.2, z -3.9) with a knob ring painted at its front end. A knob is ADDED (`smggun.GUNS['thompson']`: box 0.42 x 0.7 x
0.42 u on its own bone `coop_bolt`, standing out of the right wall; back x -1.6 = cocked, forward x 3.4 = inside the
painted ring; existing vertices untouched), open bolt as the MP40 (`coop_thompson_fire` / `_fire_empty` / `_idle_empty` /
`_reload_empty` / `_reload_ads_empty`; the key is in the names). All 12 tiks on this mesh are patched by script. The
reload sound (ThompsonReload1a.wav: magazine out f9-13, in f39 / f45-49, handle f57-65) is cut before the handle for
`reload` (`coop_thompson_snd_reload_loaded`). `evidence/thompson_mesh_handle_added_side.jpg` (back / forward).

**Hands** (`smgbake.GUNS['thompson']`, the PREFIX rows `thompson_reload[_empty][_ads]`):
* aimed: the left hand leaves the fore-grip, magazine out and in as the MP40's (under the gun; in this close aim almost
  all of it is under the frame - the new magazine shows beside the gun on the left for 0.2 s), back to the fore-grip;
  EMPTY: the FIRING hand turns into a hook beside the grip (f47-52), goes up to the knob (f59), pulls it back to the
  sear on the sound's clacks (f59-65), lets go (f67), home by f75. The server ends this reload at f78 of the row's 84
  frames (`end=77`, bug-3683);
* hip: rounds left = the retail clip to the seat, then its end pose (the mimed cock is gone); empty = the RETAIL
  technique - the left hand over the top of the gun, turned about its wrist onto the knob (`hip_cock='L'`), the knob
  follows it (f63.5-66.5).

| stance | rounds left, sway OFF (se9) | empty, sway OFF (se9) | back on the aim |
|---|---|---|---|
| stand | 0.6 % | 1.1 % | 0.07 / 0.14 deg |
| crouch / prone | 0.7 / 0.8 % | 0.2 / 1.0 % | 0.07 |
| lean left / right | 1.0 / 0.3 % | 0.3 / 0.6 % | 0.08 |
| crouch + lean left / right | 0.9 / 0.3 % | 0.4 / 0.6 % | 0.07 |
| braced | 0.3 % | 1.5 % (smoke: nothing of the gun or the hands is in the box in the braced view; se7 read 5.5 % the same way) | 0.07 |

Offline (every frame): 1.1 % rounds left, 1.7 % empty; gun between the keys 0.07 u / 0.06 deg (`midframe.py`).
**With aim sway ON (run se8, cgame_smg3, the same clips but for the last frames):** stand rounds left 2.2 % (5 frames
over), stand empty 0.8 %, crouch empty 0.3 % - and the SETTLED AIM ALONE, nothing happening: 0.8 %, 6.3 % (23 of 52
frames over) and 0.1 % after those three. Offline, settled aim alone: 6.9 % from rest, 20 % between two sway states;
with eye relief +2 / +4 u: 4.2 / 2.3 % from rest, 12.9 / 8.3 % worst pair. The rear aperture with its two guard ears
and the receiver top cover 50 % of the box a few units from the eye, and the sway moves them 15-20 px. This is not a
low-sight case, so no sight was raised. **Decision for the user (bug-3682):** change the Thompson's aim framing (eye
relief +4 u and more - a visible change to the most used gun), or judge its reloads with sway off / against a
reference that follows the sway.

Looked at: all eight stances on the sheets (se9), ten full-size engine frames of the empty reload + third person
(`evidence/thompson_reload_aimed_empty_frames_and_third_person_se7.jpg`), the four GIFs decoded.
Weak points seen: the eye sees next to nothing of the magazine swap (it is under the frame; only the gun's dip and
lift show it); at the pull the gun comes 0.9 u back and cants - in this close aim the whole sight picture swells for
0.15 s (the MP40's figure; `smg_bolt_pull_r` could be made lighter for this gun); the firing hand is a large shape
right of the receiver and hides the knob it holds; the painted knob ring stays at the front of the slot while the real
knob rests back (a 0.42 u square in a 0.9 u ring when forward) - a bigger knob or a repainted slot is a look decision;
the first frames of the "empty" GIF show the view still coming back from the burst. Not run: break-off, AI, the
per-shot knob travel in the engine (same clip set as the MP40's), the finish tiks one by one (same mesh and rows).
Not listened to.

### Thompson family - the other four meshes, NOT started

| tik(s) | mesh | handle | gun clip, magazine hidden | note |
|---|---|---|---|---|
| thompsonsmg, thompsonsmg_gold | `ThompsonSMG/ThompsonSMG.skd` | none (one bone) | 71 fr, f9-47 | add a handle on the RIGHT (the M1A1's place), firing hand, `grab` |
| thompsonsmg_tommy1928d | `coop_tommy1928d/ThompsonSMG.skd` | none | 71 fr, f24-58 (its own prop window f22-60) | its own mesh and timing |
| thompson50 | `Thompson/Thompson50.skd` | `Bolt`, TOP knob, rests back, +5.05 forward | 84 fr, f26-58 | drum; group xw_thompson50; the knob is ON the sight line |
| thompsonsmg_tommy28 | `coop_tommy28/ThompsonSMG.skd` | `Bolt`, top knob | 84 fr x 0.032, f9-47 | as the 50rd |
| thompsonsmg_m1a1dk | `coop_m1a1dk/thompson.skd` | `chamber`, right, forward x 3.2, travel 6.1 | 71 fr, f9-47 | firing hand reaches (75 %) |

Hands row `thompson_reload` = `viewmodel/smg/reload_tommy_stand.skc`, 84 frames; the left hand is away f1-77 (pouch at
f28), the right never leaves the grip; server prop `models/ammo/thompson_clip.tik` on tag_weapon_left f8-46; aim pose
`thompson_charge` = `viewmodel/idle_tommy_stand.skc` (support hand on the fore-grip, 0.3 u from the hip place: nothing to
re-pose). `prop_qa.attach_windows(row, frames, frametime)` gives the prop window of any row (sten 12-43, ppsh 44-60).
A TOP knob on the sight line cannot be worked on the sights: lowered work pose (the standard's second route).

**Next, in this order.** (a) the rest of the Thompson family: the remodel as a `_variant('thompson', ...)` with its own
`chamber` handle (`smggun.OWN`, `cock='R'` + `grab`), the 1928 Tommy (its own mesh, no handle, prop window f22-60), then
the top-knob pair (M1928, 50rd) with a lowered work pose - until then those four show the retail mesh's prefix rows
(a hand on a knob that is not there): **do not ship the Thompson rows before all five are built.** Then Sten (support hand stays on the magazine in the aim), PPSh, grease guns (cover + bolt to build), then the three
out-of-reach guns with a lowered work pose (section 3). Before judging any gun with sway on, run
`python ../tools/swayoff.py <gun>` (needs a `smgbake.GUNS` entry): a gun whose settled aim alone is over about 2 %
there cannot pass any reload - `sighttry.py` finds the raise. Run `midframe.py` on every clip with a moving firing hand.

### Silenced MP40 with sway on - what was wrong, what was done (run se1; unchanged facts)

Aim sway + breath are a TRANSLATION of the whole first-person rig (`cg_view.c`: sway +-0.10 u sideways, +-0.07 u up /
down; breath +-0.105 u up / down, +-0.04 u sideways while aiming), so a part moves on screen by 572 px x shift /
distance from the eye. On `mp40silenced.skd` the rear leaf stood 0.3-0.45 u over the receiver's rear (retail MP40:
0.7 u) and the receiver is 3.2 u wide (retail 2.1): its top was INSIDE the centre box, 5-7 u from the eye. Settled aim
alone, offline, worst pair of sway states: 6.3 % (MP40 1.8 %). Eye relief -3 .. +4 u: 5.5-3.6 %, never under the bar;
lowering the rig works but takes the sights off the eye line; both sights 0.45 u taller: 1.8 % (= the MP40).
`swaybox.py` compares against the reference shifted to each frame's background (the unshifted figures of sd1 are void).
Per-shot handle travel looked at in the engine: Silenced MP40 (se1), MP40 R2 (se2) - back at rest, forward and back on
every shot, forward after the last round (`evidence/mp40silenced_handle_per_shot_se1.jpg`, `mp40r2_handle_per_shot_se2.jpg`).

## 1. Aim poses (`tools/smgpose.py`, rows by `tools/stage_rows.py`)

The released `<prefix>_charge` pose with the support hand put in the hip idle's hand-to-gun relation, left arm
re-solved. Trunk, eye, firing arm, its fingers and the weapon tag are the released pose's (asserted per bake), so the
sight picture cannot change.

| prefix (guns) | hip place | released aim | new aim | centre box, settled aim: released -> new (engine) |
|---|---|---|---|---|
| mp40 (MP40, silenced, PPS-43, grease guns, MP18, MP40 R2) | on the magazine housing | 2.4 u off | **0.0 u** | 11.3 -> 11.4 % |
| ppsh | behind the drum | 4.7 u off | **1.8 u** (same place along the gun; 1.2 u left, 1.4 u lower) | 18.7 -> 18.6 % |
| moschetto (both tiks) | on the fore-end | 2.6 u off | **0.0 u** | 11.4 -> 7.6 % |
| type100 | on the side magazine | 7.4 u off | **1.4 u** (was 2.0 in the pistol lane's pose) | 26.1 -> 21.2 % |
| sten | on the side magazine | - | 0.0 u (pistol lane's clip, taken over unchanged) | 18.2 -> 18.3 % (sway off) |

* PPSh: the hip hand wraps a stock narrower than the hand - at the exact place its thumb and fingertips flank the rear
  sight (9.8 % of the box), 1.2 u lower its fingertips showed on the RIGHT of the receiver (run sa2). Final: 1.2 u to
  the left and 1.4 u lower - nothing right of the gun, 0.1 % of the box. Type 100: exact place = 11.8 % hand in the box.
* Runs: `sa1` released poses; `sa2` new poses, 8 stances, 5 guns (pose 1.00, sight line unchanged in all 40); `sa3`
  the seven guns sharing the rows, standing; `sa5` RELEASED poses braced; `sa6` / `sa7` sway off (Sten, PPSh pairs,
  PPSh in 8 stances). Stills: `evidence/aim_<gun>_before_after.jpg`, `aim_<gun>_stances_*.jpg`,
  `aim_variants_stand_sa3.jpg`, `braced_released_vs_new_sa5_sa2.jpg`.
* **Sten (bug-3585) - settled:** not a pose effect. The stills of sa1 / sa2 were taken with aim sway on; the Sten's
  rear sight is 4.27 u from the eye, so the sway moves its receiver cap 6-7 times further than the front sight. Sway
  off: sight points and the gun's tag point identical to 0.1 px for both poses. The released picture is kept.
* **Braced:** the sights sit at the bottom edge of the box with the RELEASED poses too (front sight 25-33 px below the
  centre for every gun, the same with the new poses) - the braced view's own framing.
* **MP18 flat brown:** the pack's own textures are near-uniform colour fields (body.jpg sd 6 on 8 bits); same with the
  released files. Not a missing texture or shader. A new skin was approved on 2026-10-12 (docs dc7a8d1,
  `docs/proposals/mp18_skin_2026-10-12`); nothing of it is changed or staged in this lane.
* Open: PPSh / Moschetto aim poses borrow the MP40's pistol-grip firing hand (holds air under a rifle stock, bug-3586).

## 2. MP40 reference (`tools/smggun.py`, `tools/smgbake.py`)

**Gun.** The mesh has no cocking handle (the slot is painted: x 4.3 .. 12.0, z -4.25 on the left of the tube). A handle
is ADDED (box 0.36 x 0.8 x 0.36 u on its own bone `coop_bolt`; existing vertices, UVs and weights untouched; it samples
uv 0.547, 0.4185 - the point the weapon-HD lane already holds for an MP40 knob). OPEN BOLT, as it works:

| gun clip (11 tiks on this mesh, patched by script) | handle |
|---|---|
| bind pose / `idle` / `reload` (unchanged retail clips) | back, x 5.0 |
| `fire` -> `coop_fire.skc` (6 frames at 1/60 s) | 5.0 -> 8.6 -> 11.5 -> 8.9 -> 6.3 -> 5.0 on every shot |
| `fire_empty` (server picks it for the last round) / `idle_empty` | runs forward and stays: 11.5 |
| `reload_ads_empty` (aimed, empty) | forward until frame 55, pulled back over 55-61 |
| `reload_empty` (hip, empty) | forward until frame 58, eased back over 58-63.5 (2b: was the retail hand's one frame) |

**Sound (2b).** The reload sound is ONE file (MP40Reload1a.wav: magazine out 0.37 s, in 1.15-1.25 s, handle 1.97 s and
2.15 s). A rounds-left reload must not sound cocked: `reload` now plays `coop_mp40_snd_reload_loaded` (the file faded
out over f51-56, tik-local aliascache, `sound/weapons/foley/` staged); the EMPTY rows keep the retail sound. Not
listened to (no audio in the harness); no load error in the logs. Other players hear the cut one for every reload.

**Hands, aimed** (firing hand never leaves its grip; no gun key set by hand - `gunphys` class `smg`, `smg_*` actions):
1. thumb on the catch, hand slides down onto the magazine (f3-8); magazine dragged down the well (10-14), swung out to
   the LEFT of the gun and seen leaving low-left (15-22): the gun follows it down, then lifts; while the hand is at the
   pouch (25-28) the muzzle hangs 1.3 deg low (shoulder + firing hand carry it - support weight 0.3, not 0);
2. the new magazine comes up BESIDE the gun on the left, in view under the box (31-39), drops under the housing, is
   driven up (44-48). 2b: the weight comes back onto the hand from 4 frames before the seat to 3 after it and the push
   is 0.8 of sb4's over 5.5 frames - the fastest sight-line step at the seat fell from 0.175 to under 0.11 deg per
   capture frame (`reloadbox.py --dump` lists the six fastest steps; the fastest now is the drag at f11, 0.14);
3. rounds left: a tug on the seated magazine (f51, the gun dips), the hand back on the housing (62). EMPTY: the hand
   goes up the receiver's left side, palm DOWN and toward the gun, hooks the handle with the index (55) and pulls it
   back (55-61): the gun comes 1.0 u back into the shoulder and cants 0.8 deg; the sear holds the bolt, the hand
   lets go (63) and is back on the housing (71). The eye sees the knuckles lead up to the handle and the index on
   its front face (`evidence/mp40_cock_closeup_sc1.jpg`; sb4's hand had its palm on the wall = "a fist").

**Hands, hip** (the same story): `mp40_reload` = the retail clip to the seat frame, the palm stays under the magazine
3 frames, then the gun comes back to the hip by f70 (the mimed cock is gone; 0.2 s of settled pose is left, was 0.5);
`mp40_reload_empty` = the retail clip with its cocking hand turned about its own wrist so the index fingertip is ON the
handle; the fingers close as the hand leaves the magazine (three quarters to the hip grip by the reach, run sd2 - it
was a flat open hand in sb4 and still open on the reach in sc3) and ease to the hip grip after the pull (no splay).

**Engine** (`tools/measure_run.py` = `reloadbox.py` per capture; an emptied gun's first 8 frames = its last shot's
flash are left out; reference shifted to each frame's background). Final clips: run sc3 (stand) - sc1 / sc2 ran every
stance with the same hands (sc2's MP40 HANDLE was dead, bug in the tools, fixed: its box figures stand, its pictures
are not used).

| stance, case | centre box beyond the aim (bar 2 %) | sight line max | back on the aim after the row | pose |
|---|---|---|---|---|
| stand, rounds left (sc3) | 0.4 % | 1.39 deg | 0.06 deg | 1.00 |
| stand, empty (sc3) | 1.0 % | 1.39 | 0.06 | 1.00 |
| crouch / prone, empty (sc1; sc2) | 0.4 / 0.4 %; 0.1 / 0.4 % | 1.38 | 0.06 | 1.00 |
| lean left / right, empty | 0.9 / 0.7 %; 0.8 / 1.0 % | 1.38 | 0.06 | 1.00 |
| crouch + lean left / right, empty (new) | 1.2 / 0.8 %; 0.9 / 0.8 % | 1.38 | 0.06 | 1.00 |
| braced, empty | 0.2 %; 0.2 % | 1.38 | 0.06 | 1.00 |

Offline (every frame, magazine prop drawn): 0.0 % rounds left, 0.3 % empty. GIFs (20 fps, centre box drawn), decoded
and looked at: `evidence/mp40_reload_aimed_roundsleft_sc3.gif`, `..._aimed_empty_sc3.gif`, `..._hip_roundsleft_sc3.gif`,
`..._hip_empty_sd2.gif`; every stance on one sheet: `evidence/mp40_reload_aimed_empty_stances_sc1.jpg`.

**Break-off mid-reload** (run sc1 rounds left, sc3 empty; `sbreak`, 0.8 s and 1.7 s into the reload; `brkmarks.py`):

| what | result |
|---|---|
| trigger | nothing: the reload runs to its end in the aim (a magazine reload is not interruptible by fire in this game) |
| sprint (`+speed +forward`) | nothing: the reload runs to its end, aim framing held (pose 1.00) |
| next weapon | the gun goes down at once, the next weapon comes up; no hand, magazine or handle left behind (`evidence/mp40_breakoff_switch_sc1.jpg`) |
| aim let go | the framing goes to the hip in 0.7 s while the row hands over to the hip clip at the same frame; magazine and hand arrive together, ends as the hip clip does (`evidence/mp40_breakoff_aim_dropped_sc1.jpg`) |

Known weak points (seen in playback):
* The first 4 frames of every "empty" GIF: the VIEW is still coming back from the 32-round burst (the wall moves).
* The magazine is on screen 0.25 s going out and 0.3 s coming in - more than sb4's 0.2 s in all, still brisk: the
  server's prop window (f10-48) is fixed and the well itself is under the frame.
* The tug and the hand's return to the housing are under the frame: only the gun's dip shows them.
* 0.06 deg is left when the row ends and eases to 0.00 in 0.8 s (bug-3597, the engine's held rig solve). Bar 0.05.
* In the GIFs the hand's skin is pale (96-colour palette); the full-size crop shows the game's own.

## 3. Each gun's own reload on its own mesh

All of them fire from an open bolt: handle back when ready, forward when dry, cocked after an EMPTY reload only.

**How a gun is built** (`smggun.py <key> .` then `smgbake.py <key> .` then `stage_rows.py`):
* The gun side. Mesh with NO handle: add one (`GUNS`, the MP40). Mesh WITH a moving bone (`OWN`): nothing on the mesh
  changes - every gun clip the tik names is re-issued under `coop_<key>_...` with that bone's channel rewritten to the
  open-bolt story (`fire` = back-forward-back, `fire_empty` / `idle_empty` = forward, `reload` = held back,
  `reload_empty` / `reload_ads_empty` = forward until the pull; every other clip = held back) and the tik rows are
  pointed at them. `rest='back'` for a pack whose clips already rest the bolt back (MP40 R2). Handle modelled but on
  the main bone: `split=(surface,)` gives it its own bone first (PPS-43, tried, not staged). The key is in the clip
  names because several meshes share one model directory (bug: the silenced MP40 once overwrote the MP40's clips).
* The hands. `smgbake.GUNS[key] = _variant('mp40', key, ...)`: the MP40 choreography on that gun's sight line and
  handle (`smggun_<key>.json`), staged as the per-weapon rows `coopr_<key>_reload[_empty][_ads]` (cgame
  `CoopPerWeaponReloadAnim`, already in ads-next: they win over the prefix rows for exactly that weapon).
* `reachcheck.py <key> [L|R]` BEFORE choosing the hand: shoulder, hooked wrist, per cent of the arm.

| gun | state | handle on the mesh | engine: box beyond the aim, stances | open |
|---|---|---|---|---|
| Silenced MP40 (`mp40silenced.skd`; since se1 with both sights 0.45 u taller, see the handover) | built, run sc2 + sc6, **se1** | a real knob on bone `eject`, left; the retail clips slam it back and forward at the END of every reload | sc6 (aim sway off): rounds left 0.0 %, empty 0.3-0.8 % in stand / crouch / prone / leans / crouch-leans / braced; back on the aim 0.06 deg | **se1, sway ON: 0.0-1.0 % in all eight stances** (it was 2.4-4.0 % in three stances of sc2 with the pack's low sights). Hip, empty: the hand closes before the reach since sd2; at the end of the aimed pull the index sits under the knob's stem. Per-shot knob travel looked at (se1) |
| MP40 R2 (`coop_mp40r2`) | built, run sc4 | `Bone1`, left; the pack's clips already rest it back (its reload = the EMPTY story) | sc4: rounds left 0.1 %, empty 0.0-0.7 % in all eight; back on the aim 0.06 deg (braced 0.02) | hip, empty: the hand closes before the reach since sd2. Per-shot travel looked at (se2). The mesh is near-black in the offline renders (its texture), fine in the engine |
| MP18 (`coop_mp18`; staged mesh: sights 0.3 u taller, eye relief 12.34 u) | built, run **se6** | `Bone2`, a bar on the right, forward x 8.3, travel 8.7 (ends about 1.3 u right of the bolt's centre); side drum; the pack's own first-person clip cocks with the RIGHT hand f52-58, 3.7 u ahead of the handle | se6, sway ON: rounds left 0.2-1.0 %, empty 0.2-1.2 % (dry-gun reference) in all eight stances; back on the aim 0.04-0.06 deg | the firing hand holds the bar at its end; break-off and AI not run (see the handover) |
| Silenced PPS-43 (`ppsh43silenced.skd`) | tried offline, NOT staged | `PPS43_lever` (20 vertices, right, x 9.6-10.6) hangs on the main bone -> split works; `eject` moves nothing | - | out of BOTH hands' reach from the aim (below) |
| Grease gun + silenced (`greaser.skd`) | not built | `Bone1` moves 9.4 u in the reload but NO vertex follows it; the cover is a closed surface (`Mesh_MultiAttached4`, on the top-left as modelled), no port, no bolt | - | cover on a hinge bone + a port and bolt to add |
| Thompson M1A1 + finishes (`ThompsonSMG.skd`, 12 tiks) | built, runs se7-se9 | ADDED: a knob on the right, back x -1.6, travel 5.0 | se9, sway OFF: rounds left 0.3-1.0 %, empty 0.2-1.5 % in all eight | with sway ON the settled aim alone is over the bar (bug-3682, decision); see the handover |
| Thompson 1928 Tommy (`coop_tommy1928d`) | not built | none (its own mesh) | - | add a handle; prop window f22-60 |
| Thompson 50rd / M1928 | not built | `Bolt`, top knob at x -0.9, rests BACK already, +5.1 forward in the retail reload | - | `rest='back'`; a knob on the sight line |
| Thompson M1A1 remodel (`coop_m1a1dk`) | not built | `chamber`, right, forward x 3.2, travel 6.1 | - | firing hand reaches (75 %) |
| Sten | **built 2026-10-13** (handover: held by the magazine, runs se16-se19) | `Sten_Bolt`, right, forward x 7.8, travel 8.8 | sway ON, envelope: rounds left 0.0-0.14 %, emptied 0.2-1.5 % in seven stances, PRONE 2.6 % (open) | the four OPEN points of the handover |
| PPSh | not built | welded into the mesh | - | split by box (`split_bone.py --box`) |
| Moschetto / Beretta M38 | not built | `Rechamber`, right, forward x 12.3, travel 4.1 (+ `Eject_Cover`); the real handle does not reciprocate | - | out of the firing hand's reach (107 %) |
| Type 100 | not built | `bolt`, right, forward x 10.3, travel 5.6 | - | out of reach (101 %) |

(`python smggun.py survey <tik>:<bone>:<L|R|T> ...` prints these lines; `gunsurvey.py <tik>` the bones, clips, server
frames and sound of a gun; `handtrace.py <row>` which hand leaves its grip when in a first-person clip.)

**Which hand.** In EVERY retail SMG hip reload (Thompson, drums, Sten, PPSh, Moschetto, Type 100) the right hand never
leaves the grip: the left hand does magazine and handle, reaching over the gun for a right-side handle (Type 100:
index tip at y +2.7 in f51-71). Only the pack-made MP18 clip uses the right hand. In the AIM a hand over the top
crosses the sights, so a right-side handle is the firing hand's - where it can reach:

* the right shoulder is 20 u behind the weapon tag in the aim pose and the arm is 26.8 u long: a hooked wrist reaches a
  handle up to about x 8 (MP18 94 %, Sten 92 %, M1A1 remodel 75 %); PPS-43 (x 10.4) is at 117 % (102 % with the
  fingers forward), Type 100 101 %, Moschetto 107 %;
* a clamped firing arm DRAGS THE GUN: hold_bake's `right_path` keys the weapon tag from the planned hand (PPS-43,
  offline: the gun swung through the view, 24 % of the box). Never accept `IK clamp R` in a bake;
* the left hand UNDER the receiver (`_UNDER` in smgbake, the under-reach) gets to the PPS-43's handle at 92-100 % of
  the arm and only with the forearm through the pistol grip - not usable as tried;
* so for the handles out of reach the route is the standard's second one: the gun comes DOWN under the box into a
  work pose (revbake's `gun_abs` list / the BAR's work pose in `..\heavy`) and is worked there with the retail
  left-hand technique, back to the aim within 0.05 deg. Not built; a decision for the coordinator.

Ready in the tools, exercised only offline: `cock='R'` (aimed: the left hand returns to its grip first, the firing
hand hooks, pulls, returns - mirrored hook and mirrored `smg_*_r` physics; hip: `bake_hip_right`, built on the
rounds-left clip), `handle='R'` + `_UNDER`, `hip_built` (a built left-hand hook over the top at the hip).

Evidence: `evidence/mp40silenced_reload_{aimed,hip}_{roundsleft,empty}_se4.gif` (current, full frame; the `_sc6` / `_sd2` ones show the pack's low sights), `mp40silenced_reload_aimed_{empty,roundsleft}_stances_se4.jpg`, `mp40silenced_aim_before_after_se1.jpg`, `mp40silenced_third_person_se4.jpg`;
`evidence/mp18_reload_{aimed,hip}_{roundsleft,empty}_se6.gif`, `mp18_reload_aimed_{empty,roundsleft}_stances_se6.jpg`, `mp18_reload_aimed_empty_frames_se6.jpg`, `mp18_aim_before_after_se6.jpg`, `mp18_third_person_se5.jpg`;
`evidence/thompson_reload_{aimed,hip}_{roundsleft,empty}_se9.gif` (sway off), `thompson_reload_aimed_{empty,roundsleft}_stances_se9.jpg`, `thompson_reload_aimed_empty_frames_and_third_person_se7.jpg`, `thompson_mesh_handle_added_side.jpg`;
`evidence/mp40r2_reload_{aimed,hip}_{roundsleft,empty}_sc4.gif` (hip empty: `_sd2`), `mp40r2_reload_aimed_empty_stances_sc4.jpg`,
`mp40r2_cock_closeup_sc4.jpg`. All GIFs decoded (gifsheet.py) and looked at; every stance looked at on its sheet.

**AI** (run sc5, `--map m6l1a --spot 6152,-6528,5440,135`: no friendly actor on that map, nearest enemy 1779 u away;
`mapents.py`): a spawned Wehrmacht NCO raises his MP40, fires bursts at the player, reloads (the gun held up, a
magazine on the ground), fires again - 12 s, nothing detached, no animation error in the log
(`evidence/mp40_ai_firing_sc5.jpg`). The handle is under a pixel at that distance: its per-shot travel is checked on
the first-person gun and offline only.

## Tools (`tools/`)

New on 2026-10-13 (se10 - se19): `..\..\tools\swayenv.py` (the sway ENVELOPE, shared by the lanes), `reloadbox.py` env
figures + `run_smg.py --tail N[:step]`, `stage_slot.py` (Thompson slot repaint on every finish sheet), `smggun.round_mesh`
(a round knob), `sidehold.py` (a gun of a shared prefix held by its side magazine: per-weapon idle / charge / fire rows),
`smgbake.py` `hold` / `hold_prop` / `hip_proc` / `pullk` / `show` / `end_e` / `_GRAB_BEHIND`, `smggun` `snd_tight` (unused),
`framesheet.py` (engine frames at given CLIP frames, full or cropped: `framesheet.py se18 sten E out.jpg --clip 62,66,68
--stance prone --crop 380,200,1180,650`), `measure_run.py` skips an incomplete capture and says so. `SB_TRACE=0:0` on a bake
prints the `grab fit` of a hook. Waiting on a run from a shell: the line `[seNN] done` is in the run's own `.out`, the
shared `run.log` only gets `run ended` (two waiters hung on that here).

`takeover.py` regenerates `run_smg.py` (+ `smg_block.py`: `sdemo` / `shipdemo` / `tp` / `ai` / `sbreak` captures; `--map`
/ `--spot`) and the measure tools from `..\tools`, repointed at G:\mohaa-adsanim3. `smgpose.py` (aim poses +
`handsurvey.json`), `smggun.py` (added handle, or `OWN` / `split` for a mesh that has one; open-bolt clips; tik rows for
every tik on a mesh; the cut rounds-left sound; `survey`), `smgbake.py` (aimed + hip hands, `_variant` per weapon;
`--box` offline box check with the magazine drawn, `--cu` close-up of the hand on the handle, `--look`; `SV_RIGHT=1`
looks from the right), `stage_rows.py` (fps_anims_smg.txt = released fixes-pak copy + this lane's rows,
`rows_extra.json` from the bake), `mkov_smg.py` (overlay; `--base` = released rows; adds the AI spawn poll),
`measure_run.py` (every aimed capture of a gun in a run -> `reload_<run>_<gun>.json`, `--status` into
`coverage_status.json`), `reloadbox.py` (one capture; `--dump` = frames over the bar + the fastest sight-line steps),
`stancesheet.py` (every stance of a gun on one sheet), `capcrop.py` (full-size crops of capture frames),
`brkmarks.py` (what the rig did through a break-off), `endpose.py` (is a clip's end the aim pose), `swaybox.py` (the settled aim's own box cover with sway on, engine), `swayoff.py` (the same offline, for every sway state and eye relief), `topprof.py` (a mesh's top behind the rear sight as the eye sees it), `sightraise.py` (taller sights on a staged skd), `sightshape.py` (a thin raised leaf into a block, x only), `sighttry.py` (offline search for the smallest raise that passes with sway on), `midframe.py` (does the gun stay put BETWEEN a clip's keys), `evid.py` (a gun's GIFs + sheets from one run), `patch_sights_row.py` (that gun's row in the worktree's cg_adssights.h), `gifrows.py`, `eyezoom.py` (the eye's picture offline, cropped, at game size),
`reachcheck.py`, `gunsurvey.py`, `handtrace.py`, `mapents.py` (player start + actors of a map: where an AI can be
looked at), `aimpair.py`, `sideview.py` / `eyepair.py` / `gunside.py` (offline looks), `status_merge.py` /
`status_reload.py`, `buglog_add.py`.

    cd smg/assets                       (IRONSIGHT_EXTRA_PAKS must be UNSET for smggun / the bake)
    python ../tools/smggun.py mp40 .  &&  python ../tools/smggun.py silenced_mp40,mp40_reactivated .
    for g in mp40 silenced_mp40 mp40_reactivated; do python ../tools/smgbake.py $g .; done;  python ../tools/stage_rows.py
    python ../tools/mkov_smg.py <SCRATCH>\adssmg\ov_x.pk3
    IRONSIGHT_EXTRA_PAKS=<that pk3> python ../tools/smgbake.py mp40 . --nobake --box --which ads_empty,ads_loaded
    IRONSIGHT_EXTRA_PAKS=<that pk3> python ../tools/eyezoom.py mp40 . ads_empty out.jpg --frames 50:66:2
    cd ../tools; python run_smg.py <id> --overlay <abs pk3> --cgame cgame_smg1 --guns mp40 --parts sdemo,shipdemo,sbreak \
        --sstances stand,crouch,prone,standL,standR,crouchL,crouchR,braced --yaw 160 --hold 235 --rel 215
            (harness gun keys: mp40s, mp40r, mp18, pps43, greasegun ...; --hold = clipsize x sp firedelay / 0.016 + 40:
             300 for the silenced MP40; near-eye guns: add --set "set cg_adsSway 0" --set "set cg_weaponBreath 0")
    python measure_run.py <id> mp40 --dump [--status models/weapons/mp40.tik mp40];  python brkmarks.py <id>
    python dgif.py <id> mp40__adsE__ out.gif --frames 284:470:3 --w 400 --crop 240,120,1040,720 --box
    python gifsheet.py out.gif sheet.jpg 0:64:1;  python stancesheet.py <id> mp40 sheet.jpg
    python run_smg.py <id> --overlay <pk3> --cgame cgame_smg1 --guns mp40 --parts ai --map m6l1a --spot 6152,-6528,5440,135

Reusable by the MG / heavy lane: `smggun.py` (`patch_tik`, `same_mesh_tiks`, the open-bolt clip set, `OWN` for a mesh
with a bolt bone, `cut_wav`), `smgbake.py`'s `hook_rel` (a hand hooked on a handle built from the hand's own geometry,
either hand) and the `smg_*` gunphys actions, `reloadbox.py`, `reachcheck.py`, `smgpose.py`, `gunside.py`.

Harness facts: the coop game fires on the tik's `sp firedelay`; `set cheats 1` does not survive the mod's server start
(no `spawn`, no `notarget`; the harness's `dog 1` has been a no-op); aim sway is ON in the shared runner
(`cg_adsSway 0.1`, `cg_weaponBreath 1`) - it moves a gun that is drawn close to the eye by several pixels and reads as
box cover (silenced MP40); a gun that is not emptied within `--hold` does not reload (and the next capture starts one
round from dry); mp40.skd, mp40silenced.skd and ppsh43silenced.skd share `models/weapons/mp40`.
