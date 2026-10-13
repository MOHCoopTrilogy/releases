# RIFLE lane - aimed (ADS) first-person animations

Lane of `docs/proposals/ads_twohand_2026-10-11` (read the HANDOVER at the top of `../README.md` first: the standard and
the method are the pistol lane's). Rows: the `## rifle` section of `../coverage.md`. Nothing here is in the mod tree or
the fixes pak; everything is staged in this folder and on engine branch `ads-rifle-next`
(worktree `C:\mohaa-coop-dev\openmohaa-hzm-ads-rifle`, build dir `.cmake`, test build `cgames\cgame_rifle4.dll`).

# HANDOVER (2026-10-12 night, fourth stretch) - read this first

**Done: step 1 of the coordinator's list (bolt-cycle clean-up, all four rifles, six stances) and step 2 (Kar98 aimed
reload reworked, six stances). NOT started: aimed reloads of Springfield / Mosin / Enfield, the semi-autos, Carcano /
De Lisle / Arisaka / G98, the scoped sample, and the IRON-SIGHT G43 (new firm request - its section below).** Engine `ads-rifle-next` 2747ecc8 = test build `cgames\cgame_rifle4.dll`.
Overlay of the staged state: `G:\mohaa-adsanim2\ov_rifle_c6.pk3` (`mkov_rifle.py ... --measure`). Run ids used:
rb16-rb23; **rb24 is next**.

## Settled (user / coordinator) - do not reopen
* Bolt cycles between shots: **variant A** - the rifle stays LOCKED on the sights (`ease` 0); the gun's own open bolt in
  the middle of the view is accepted and exempt from the 2 % box bar; hands, stock and any drift still count.
* "Comes down under the box" is allowed for a FULL reload only.
* The recoil is NOT held in a rechamber (section below). No change to recoil recovery.

## What changed in this stretch
1. **No bolt balloons any more (`tools/boltcap.py`, new).** Locked on the sights, the retail FULL stroke brought every
   bolt's rear to 0.0-0.9 u from the eye (Springfield 0.01 u, Mosin 0.55, Kar98 0.70, Enfield 0.94 - `boltnear.py`):
   that was the Mosin's "huge flat grey mass" and the Springfield's "bar to the right edge", and it was true of all four.
   Each rifle now has an AIM-ONLY gun clip, tik row `rechamber_ads`: the same cycle with the bolt's travel scaled so its
   nearest vertex stays **>= max(2.5 u, settled distance / 1.5)** from the eye - never nearer than 2.5 u, never drawn
   more than 1.5 x its size in the settled aim. Stroke kept: Kar98 2.81 of 4.61 u, Springfield 3.00 of 5.49,
   Mosin 3.34 of 5.82, Enfield 1.86 of 3.42. Timing, sound and case are the hip row's; the hip clip keeps its full
   stroke. cgame: the held gun shows `rechamber_ads` exactly while the hands play the aimed bolt clip
   (`CG_VMAdsBoltClip`, third row of the aimed gun-row table in cg_modelanim.c).
2. **Springfield handle**: the retail clip lifts it 80.5 deg; the aimed clip lifts it the real 90 deg (`lift` in
   boltcap.GUNS). The "long bar" was the handle 0.0 u from the eye, gone with the cap. Mosin (54 deg) and Enfield
   (48 deg) lifts are the retail ones - not changed (real: 90 and about 60).
3. **The hand holds the knob (`boltphys.py`: `knob_off` keyed per frame).** The retail grip cups the knob from below
   with the little-finger side of a fist; the old fixed offset (1.2 u right) left the knob OUTSIDE the hand. Now the
   knob sits in the curled fingers while the bolt is hauled back, and the hand opens to the fingertips where the knob
   stands at the box's rim (Kar98 lift + turn-down, Springfield lift + turn-down). Mosin 0.5 / 0.25 and Enfield
   0.3 / 0.15 for the whole cycle. The hand cannot be made small: it is 7 u long and the knob 6 u from the eye.
   Tried and dropped (pictures: `gripx.py`): thumb-and-forefinger hold with the forearm turned (the back of the hand
   becomes a brown slab over the right half), hand rolled above the knob (covers the box).
4. **Hands-only ENGINE figure (`rbox.py`)**: skin-coloured box pixels beyond the settled aim (the bolt is dark / grey,
   the brass case is excluded by its yellow). `HANDS (skin) max` is printed first, the old total after it.
5. **Kar98 aimed reload reworked (`riflereload.py`)**: see its section.

## RESULTS - bolt cycles, six stances each (stand, crouch, prone, lean L, lean R, braced)
Hands-only engine box maximum per stance, in that order:
| rifle | steady (run rb17) | sway on, as played | sight line | front sight, after the recoil | back to |
|---|---|---|---|---|---|
| Kar98 | 0.6 1.0 1.0 1.8 0.7 1.4 | rb20: 1.5 1.3 0.9 1.1 1.3 1.0 | 0.58-0.64 deg (braced 0.33) | 0.26-0.61 | 0.00 |
| Springfield | 1.4 1.2 1.3 1.0 0.9 0.1 | rb18: 1.8 1.4 1.7 1.2 1.5 0.5 | 0.57-0.61 | 0.22-0.39 | 0.00 |
| Mosin | 1.0 1.2 1.1 1.0 1.0 1.0 | rb18: 1.3 2.0 1.2 1.1 1.1 1.1 | 0.60-0.65 (braced 0.36) | 0.31-0.48 | 0.00 |
| Lee-Enfield | 0.7 1.1 1.1 1.0 1.2 0.2 | rb18: 0.9 1.4 0.8 0.8 1.1 0.4 | 0.59-0.66 (braced 0.36) | 0.26-0.61 | 0.00 |

Kar98's steady figures are from rb17, before its lift offset was widened (rb18 with sway read 2.8 % lean left and
2.2 % prone at the lift; rb20 is the staged clip). The total box figure (own bolt included, exempt) is 2-15 %.
Offline (`rpart.py`): hands 0.2 / 0.7 / 0.2 / 0.0 %, front sight within 0.16 deg in the clip alone.
LOOKED AT: stand of all four every 4th capture frame (rb17) and every decoded GIF frame through the action
(Springfield, Mosin; Kar98 reload); the bolt-back frame of every rifle in every stance (stance sheet); the frames with
the highest hands figures. Only measured: the other stances' full playback.
Weak points seen, not hidden:
* the working hand is still LARGE (right third of the picture while the bolt is back); it now holds the knob;
* Springfield: the handle is a thick dark bar from the receiver to the knob at the box's right rim (the mesh);
* Enfield: the knob is hidden inside the hand while the bolt is back;
* the shortened stroke is visible to anyone who knows the rifle (the bolt does not come back far enough to feed).

## Kar98 aimed reload (`kar98_reload_ads`, runs rb19-rb23)
The whole reload is worked JUST UNDER THE CENTRE BOX: the rifle comes down first (drop 1.9 u, 7 deg to the hand), the
bolt is opened there, the rifle sags to the reaching side while the hand is at the pouch (hold `reach`: the "static
half second"), the charger is set and thumbed in at drop 3.5 u (the push holds the rifle down), the hand letting go
springs it back (`hand_off`), the bolt is closed at 1.9 u, then up to the exact aim. Why not locked for the bolt
phases (rb15): the reload's gun clip has the full stroke - bolt 1.1 u from the eye for 0.45 s at each end - and the
loading sat at the bottom edge of the frame (drop 4.3 u).
RESULTS, run rb23 (the staged clip, sway on, six stances: stand, crouch, prone, lean L, lean R, braced):
| | hands-only box max per stance | back to | the rifle's own body in the box |
|---|---|---|---|
| rounds left (one shot, then `reload`) | 0.5 0.5 0.5 0.2 1.3 0.1 % | 0.00 deg | 1.4-6.2 % for 6-12 frames |
| emptied (five shots, automatic reload) | 0.2 0.8 0.2 **2.2** 0.4 0.3 % | 0.00-0.01 deg | 0.8-6.8 % for about 24 frames |

NOT met: the rifle's OWN body reads 2-6 % beyond the settled aim for about 0.1 s as it leaves the aim and again as it
returns (capture frames 18-24 and 210-214 of the rounds-left reload) although the clip goes straight down and straight
up, aligned (offline `rpart.py`: 0.0 %). It is largest in the very first frames - the blend from the aim solve into
the clip (engine side, not looked into). Lean left, emptied: hands 2.2 % in one frame.
An EMPTIED Kar98 works its bolt once more on the sights after the fifth shot (the game's existing sequence: `rechamber`,
then the automatic `reload`) and only then comes down and reloads; the capture of that case ends 0.1 s before the rifle
is back on the aim (`--rframes 330` is too short by a few frames: use 360).
LOOKED AT: the rounds-left reload in every second GIF frame (rb20 clip) and coarse (rb19); the emptied one in every
second GIF frame (rb23); three moments in six stances (stance sheet). The rb23 rounds-left GIF itself (the last entry /
exit change) was only measured.
Weak points seen: the loading is small (the rifle is 3.5 u under the eye line, the charger about 60 px at 1280 wide);
the half second with no working hand in view now has the rifle sagging to the right and coming back, which is slow and
slight; the thumb's two pushes are visible as a dip of the whole rifle, not as a jolt.

## FIRST for the next agent: the iron-sight G43 (user, 2026-10-12: "I'd like an iron sight version of the g43 too")
**NOT built - only the mesh was looked at (this stretch ran out of context).** The coordinator's order: new tik name(s)
only (`coop_g43_irons` + the camo variants that come free from the shared mesh; `G43.tik`, its three camo tiks and
`g43sniper.tik` stay untouched), scope + mount + lens removed from a STAGED copy of `models/weapons/g43/g43.skd`,
`zoom` back to an iron-sight value, sight row through a lane-local override, world / third-person model without the
scope too, staged and switchable. LOOK TEST FIRST (hip, aiming, third person, side view of the mesh before / after)
and send it to the user before any reload work; its aimed reload comes with the semi-autos.
What `tools/g43parts.py` found (gun frame u: x forward, z NEGATIVE = up; the scope, its mount and the lens are SEPARATE
connected components, and the real sights are under them - it looks clean):
* REMOVE (second `g43` surface): scope tube 180 tris (x -1.1..6.8, z -7.1..-5.1), two turrets 22 + 16 tris
  (x 2.3..3.3), two rings 12 + 12 tris (x -0.3..1.1 and 4.5..5.9, z -6.2..-5.5), the mount 58 tris (x 1.0..4.7,
  y -0.5..0.2, z -6.2..-3.6); the whole `svt_lens` surface (8 tris at x -0.8).
* KEEP as the receiver's dovetail rail: 20 tris (x -0.8..5.0, y -0.5..0.3, z -3.6..-3.1). Check the 48-tri piece at
  x -1.5..-0.8, z -3.3..-3.1 in a picture before deciding.
* ALREADY THERE: rear tangent sight on its base ahead of the receiver (70 + 10 + 20 + 12 tris, x 11.5..16.5, top at
  z -5.3), front sight base 38 tris (x 31.5..33.6), front post 10 + 10 tris (x 40.5..42.5, top z -4.4) and its hood
  (`g43cull`, x 41.4..42.5, z -5.1..-4.0). Nothing has to be built unless the look test says the notch is too coarse.
* An skd writer exists in the pistol lane (`../tools/m10build.py`, `m10rounds.py`, `slidesplit.py`) - reuse it; the
  sight row needs the rear notch / front post points for `ironsights_2026-09-28/sights.json`-style rows.

## Next (the coordinator's order)
1. Aimed reloads for Springfield (3-part `springfield_reload` / `_single` / `_end`), Mosin, Enfield: add
   `riflereload.GUNS` entries from the Kar98's (events from `clipinfo.py <tik> reload <view clip> lo,hi`); the same
   under-the-box plan (holds `bolt` / `reach` / `push` / `close`).
2. Semi-autos: Garand (en-bloc from the top, the ping, thumb clear, op-rod really runs), G43, SVT, Johnson; then
   Carcano / De Lisle / Arisaka / G98 (kar98 prefix, own meshes: the cgame mesh guard `CoopAdsClipFitsHeldGun` keeps
   them on the hip clip - own clips under own row names, or a guard entry per mesh; each needs its own
   `rechamber_ads` gun clip: add it to `boltcap.GUNS` / `boltnear.GUNS` / `vmcam.BOLT`).
3. ONE scoped rifle (bolt cycle + reload behind the scope), report before doing the rest.
Left as is: the Gewehrgranate (no aim at all - a later decision).

## Decisions for the user
* The bolt's visible stroke while aiming is 54-61 % of the real one (the cap). Longer = bigger in the view
  (`boltcap.py --near 2.0`), shorter = smaller.
* Mosin / Enfield handle lift is the retail 54 / 48 deg (real 90 / about 60): raise it in the aimed clip as on the
  Springfield? It brings the knob nearer the centre box.
* Everything here is STAGED (assets + engine branch); nothing is in the mod tree or the fixes pak.

## The recoil: NOT held in a bolt cycle - a correction of this lane's earlier report
`tools/ftrack.py` (engine front-sight track against the clip's own offline track, per clip frame), Kar98 A, run rb14:
the shot's recoil peaks at 2.93 deg, 0.96 deg of it is left when the bolt clip starts (0.25 s after the shot) and it
keeps recovering smoothly THROUGH the clip - 0.62 deg at clip frame 5, 0.33 at 13, 0.17 at 21, 0.05 at 34 (an
exponential, tau about 0.3 s: the recoil layer `s_recoil` of cg_view.c, the same curve as after any aimed shot).
Nothing is frozen and there is no step at the clip's start or end. The "0.7 deg held through the clip" in the previous
handover was wrong: most of it was the clip's own muzzle swing (fixed by the front-sight pivot), the rest this normal
recovery. bug-3597 (the rig solve held in the kicked state) is the EMPTIED-gun auto-reload path of the other lanes;
it does not occur in a rechamber. No engine change was made for it. If the first quarter second should sit closer to
the target, the lever is the recoil layer's recovery rate while aiming (a feel change for every aimed shot - a
decision, not a fix).

## Earlier findings that stand
* **Clip-end jitter, fixed in the cgame** (`ads-rifle-next` 18dc8b36; `CG_VMAdsTagRight`, new `CG_VMAdsBoltSolo`,
  `CG_VmTagHandoff`, probe on the off-hand tag): the gun hung on the travelling hand's tag for the whole aimed bolt
  clip and wobbled about 1 deg between clip frames during the reach and the return. bug-3630.
* The hand was in the box because of the GRIP (knob deep in the palm): `knob_off`. bug-3631.
* Break-off (rb10): fire does not interrupt a Kar98 reload, switch puts the rifle away cleanly, sprint continues.
  Hip reload lens fix (bug-3451) holds in five stances (rb11). **Gewehrgranate has no aim at all** (no sight row, no
  `kar98mortar_charge` row): no aimed rows staged, left as a later decision.

## Tools (this lane's, `tools/`)
* `boltphys.py <gun>[,<gun>]` (from `assets/`): `--set ease= | back= | roll= | fskeep= | hold=a,b,c,d`, `--rc k=v`, `--scale`.
* `rpart.py <sight gun> <aim.skc> "<clip>|rechamber"`: OFFLINE box cover per frame by surface; prints **hands max / the
  gun's own surfaces max**; `--track` = signed front-sight elevation per frame; `--sheet --zoom`. Offline under-reads
  the rifle's own body against the engine - use it for the hands figure and for sweeps.
* `ftrack.py <run> <tag> <sight gun> <aim.skc> "<clip>|rechamber"`: engine front sight per clip frame, clip alone, residual.
* `run_rifle.py`: parts `bolt`, `bolt2`, `reload`, `empty`, `hipreload` (`--hipall`), `breakfire / breakswitch /
  breaksprint`, `stills`; `--steady` = breath and sway off (a figure of the clip alone); `--yaw 172` = light wall.
* `rbox.py <run> [tag] --dump --zoom=<dir> --json=`: engine box per frame, where the cover sits, sight line, front sight
  (first frames / from 0.26 s in). **The settled-aim reference is now the UNION of the eight frames before the first
  mark** (was `mean > 0.3` of six: the same pose read 3-19 % "aim covers" between captures and the rifle's own breathing
  counted as cover). Other lanes: the same weakness is in `../tools/centrebox.py`'s settled-aim mask - take the union
  of the settled window, or capture with breath / sway off.
* **New in the fourth stretch:** `staged.py` (import it first: the offline tools then read the staged tiks / gun clips
  under `assets/` as loose files - no overlay pk3 needed); `boltnear.py <gun>[,..] [--anim rechamber_ads] [--clip ..
  --offhand lo,hi]` (how near the bolt comes to the eye, its screen bounding box, per frame); `boltcap.py <guns>
  [--near 2.5]` (writes the aim-only gun clip + the staged tik with `rechamber_ads`; then re-run `nosmoke.py` for the
  measure tiks and `boltphys.py`); `gripx.py` (grip variants side by side, textured), `gripsweep.py` (hands' box
  maximum per `knob_off`); `stances.py` (stance sheet); `rpart.py --cols --frames a:b`.
  `boltphys.py` recipe keys: `knob_off` tuple or {frame: tuple}, `grip_rot` (deg about the knob), `finger_s` (curl
  scale per finger joint), `grip_pin` (absolute hand attitude in the gun frame - tried, unused).
  `rbox.py` prints `HANDS (skin) max` first; an `empty` capture is measured from 26 frames after the last shot.
  `mkov_rifle.py --measure`: a measure tik replaces the staged tik of the same path (it must carry the same rows).
  Build the cgame from Git-Bash with DASH switches: `cmake --build .cmake --config Release --target cgame -- -m:4 -v:m`.
* `riflereload.py`, `rows_rifle.py`, `mkov_rifle.py`, `rsheet.py`, `rgif.py`, `rgif2.py` (panels side by side), `clipinfo.py`.
* Engine run: `set ADS_RUNS=G:/mohaa-adsanim2/runs`; `python tools/mkov_rifle.py G:\mohaa-adsanim2\ov_x.pk3 --measure`;
  `python tools/run_rifle.py <id> --overlay G:\mohaa-adsanim2\ov_x.pk3 --cgame cgame_rifle3 --yaw 172 --guns kar98
  --parts bolt2 --stances stand,crouch,prone,standL,standR,braced --set "set vss_draw 0"`.

## Shared tool, changed with the coordinator's leave
`../tools/coverage.py`: an unknown command (`--help`) printed nothing and ran `build` - it now prints the usage and
exits (`elif cmd == 'build'`). The line-476 crash was already fixed by the owner; `--lane rifles build` works and
writes `rifles/coverage.md`. Still open there: `scan` reads a bolt capture's shot recoil as `edge` and a reload's `end`
as 2.5 where rbox reads 0.03, so this lane's `ok` flags stay false whatever the clip does.

## Files
`assets/` staged view clips + `*_phys.json`, gun clips `models/weapons/<dir>/*_ads.skc` + `*_cap.json`, staged tiks
`models/weapons/{kar98,springfield_unscoped,mosin_nagant_rifle,enfield}.tik` (released tik + the `rechamber_ads` row;
regenerate with `boltcap.py` when the released tik changes), `models/player/base/fps_anims_rifle.txt`;
`coverage_status.json`, `coverage.md`; `evidence/`. Runs `G:\mohaa-adsanim2\runs`: ra1-ra7, rb1-rb15 earlier stretches
(rb14 = locked cycles with the full stroke, rb15 = reload with locked bolt phases, both superseded); rb16 first capped
look; **rb17 = bolt cycles steady, rb18 = with sway (Springfield / Mosin / Enfield final), rb20 = Kar98 cycle final**;
rb19-rb22 Kar98 reload passes; **rb23 = Kar98 reload final, six stances**.
