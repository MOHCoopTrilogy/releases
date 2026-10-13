# RIFLE lane - aimed (ADS) first-person animations

Lane of `docs/proposals/ads_twohand_2026-10-11` (read the HANDOVER at the top of `../README.md` first: the standard and
the method are the pistol lane's). Rows: the `## rifle` section of `../coverage.md`. Nothing here is in the mod tree or
the fixes pak; everything is staged in this folder and on engine branch `ads-rifle-next`
(worktree `C:\mohaa-coop-dev\openmohaa-hzm-ads-rifle`, build dir `.cmake`, test build `cgames\cgame_rifle3.dll`).

# HANDOVER (2026-10-12 late night) - state after the third stretch

**The four bolt rifles' between-shot cycles are rebuilt to the user's decision (variant A, locked) and run in six
stances each (run rb14). Aimed reloads: Kar98 only. Semi-autos, the other bolt rifles and the scoped rifle: untouched.**

## The user's rules for a bolt rifle (2026-10-12, in order)
> "Just a reminder, bolt actions should ideally not move much from locking onto target when the bolt is pulled back"
> "Like you can have weight etc but ideally it stays primarily on target"

**DECISION after the A / C GIF: variant A.** The rifle stays LOCKED on the sights while the hand works the bolt; the
open bolt handle and bolt body in the middle of the view are accepted, for EVERY bolt-action rifle (Kar98,
Springfield, Mosin, Enfield, Arisaka, G98, Carcano, De Lisle). No easing of the receiver for the between-shot cycle.
For the centre-box figure of a bolt cycle the rifle's OWN bolt handle and bolt body are exempt from the 2 % bar; hands,
the stock and any drift of the rifle still count; front sight and sight line as close to 0 as possible.
"Comes down under the box" remains allowed only for a full reload's loading phase.

## What is staged (all four: `ease` 0 = locked)
`tools/boltphys.py`: hands = key_bolt's (the right hand rides the gun's bolt bone) with `knob_off` (the knob held by the
fingers; the hand's bulk right of / under the knob), gun = gunphys class `RIFLE` following ONE hold - head back off the
comb along the sight line (Kar98 3 u as shown to the user, Springfield / Mosin 2 u, Enfield 1 u), 2 deg cant about the
SIGHT LINE - and answering the four strokes. **The front sight is the pivot** (`FS_KEEP` 0.25, `FS_LEN` 73.6): the
simulation turns the rifle about the butt, which swung the muzzle (the first on-target clip put the front sight 0.67 deg
high with the bolt back - that was the clip, see "the recoil" below); now each frame's drop is re-solved so the front
sight keeps a quarter of its excursion and the reaction shows at the receiver end, in the roll and the fore-aft tug.
Variant C (receiver eased down) is kept reproducible and unused: `--set ease=1.25 --set back=-2` (0.5 Springfield / Mosin).

## RESULTS, run rb14 (overlay `ov_rifle_b5.pk3`, cgame_rifle3, two shots per capture, `evidence/rb14_box.json`)
| rifle | sight line, six stances | front sight off target: first frames / from 0.26 s in | back to | hands in the box (offline, the bar) | own bolt in the box (engine total, exempt) |
|---|---|---|---|---|---|
| Kar98 | 0.59-0.65 deg (braced 0.34) | 0.73-0.91 / 0.34-0.47 deg (braced 0.24) | 0.00 | 0.3 % | 12-19 % (braced 5.6) |
| Springfield | 0.59-0.65 | 0.62-0.80 / 0.24-0.38 (braced 0.39 / 0.25) | 0.00 | 1.6 % | 3-9 % |
| Mosin | 0.59-0.64 (braced 0.36) | 0.57-0.76 / 0.27-0.37 (braced 0.24) | 0.00 | 0.0 % | 5-7 % |
| Lee-Enfield | 0.58-0.64 (braced 0.36) | 0.59-0.76 / 0.30-0.49 (braced 0.26) | 0.00 | 0.0 % | 1.2-6.1 % |

The hands figure is OFFLINE (`rpart.py`, per surface); the engine measure cannot tell a hand from a bolt, so its total
is listed as the bolt's. GIFs `evidence/<gun>_bolt_aimed_locked_rb14.gif`, stance sheet `bolt_locked_stances_rb14.jpg`,
playback sheet of three `bolt_locked_playback_springfield_mosin_enfield_rb14.jpg`.
Playback, every GIF decoded: no pops on any of the four. Weak points seen:
* Kar98: with the bolt back the bolt body is a large dark mass at the bottom centre and the handle crosses the right
  half of the box (the accepted look); knob and hand large at the right edge.
* Springfield: the hand's back comes close to the right edge of the box at the lift (1.6 %).
* Mosin: with the bolt back the cocking piece is a very large grey mass at the bottom centre (2 u slide; the bolt comes
  back to the eye) - the gun's own part, but big.
* Enfield: the rifle stays put now (the 3.3 u pump is gone); the working hand is in view at the lift and the turn-down
  and off the right edge while the bolt is back.

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
* Kar98 aimed reload: rebaked with the bolt opened and closed LOCKED (run rb15, stand + prone: ends 0.03-0.04 deg;
  offline hands 2.9 % at one point - over; NOT played back yet; `evidence/kar98_reload_aimed_rb9.gif` is the previous,
  eased version). The half second with no right hand in view still looks static.
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
* `riflereload.py`, `rows_rifle.py`, `mkov_rifle.py`, `rsheet.py`, `rgif.py`, `rgif2.py` (panels side by side), `clipinfo.py`.
* Engine run: `set ADS_RUNS=G:/mohaa-adsanim2/runs`; `python tools/mkov_rifle.py G:\mohaa-adsanim2\ov_x.pk3 --measure`;
  `python tools/run_rifle.py <id> --overlay G:\mohaa-adsanim2\ov_x.pk3 --cgame cgame_rifle3 --yaw 172 --guns kar98
  --parts bolt2 --stances stand,crouch,prone,standL,standR,braced --set "set vss_draw 0"`.

## Shared tool, changed with the coordinator's leave
`../tools/coverage.py`: an unknown command (`--help`) printed nothing and ran `build` - it now prints the usage and
exits (`elif cmd == 'build'`). The line-476 crash was already fixed by the owner; `--lane rifles build` works and
writes `rifles/coverage.md`. Still open there: `scan` reads a bolt capture's shot recoil as `edge` and a reload's `end`
as 2.5 where rbox reads 0.03, so this lane's `ok` flags stay false whatever the clip does.

## Next (the coordinator's order)
1. Recoil: see above - nothing held; decide whether the recovery rate while aiming should change.
2. Re-run the four rifles with `--steady` for a clean hands-only engine figure (the union mask is in, not yet run).
3. Aimed reloads for Springfield (3-part: `springfield_reload` / `_single` / `_end`), Mosin, Enfield (stripper clips
   from the top; bolt worked locked, loading eased just under the box, back to exact aim): add `riflereload.GUNS`
   entries (events from `clipinfo.py <tik> reload <view clip> lo,hi`). Kar98 reload: play back rb15, bring the hands
   figure under 2 %, give the body / gun a visible reaction when the hand leaves and at each push of the clip.
4. Semi-autos: Garand (en-bloc from the top, the ping, thumb clear), carbine, silenced Garand, G43, SVT, Johnson; then
   Carcano / De Lisle / Arisaka / G98 (kar98 prefix, own meshes: the cgame mesh guard `CoopAdsClipFitsHeldGun` keeps
   them on the hip clip - own clips under own row names, or a guard entry per mesh); then ONE scoped rifle, report first.
5. Mosin: the cocking piece's size with the bolt back (a longer slide trades against "the rifle stays put").

## Files
`assets/` staged clips + `*_phys.json` + `models/player/base/fps_anims_rifle.txt`; `coverage_status.json`, `coverage.md`
(this lane's rows, generated); `evidence/`. Runs `G:\mohaa-adsanim2\runs`: ra1-ra7 first session; rb1-rb3 before the
engine fix; rb7-rb9 variant C (superseded); rb10 break-off; rb11 hip reload; rb12 Gewehrgranate; rb13 the other three,
eased (superseded); **rb14 = the staged cycles (A)**; rb15 Kar98 reload with locked bolt phases.
