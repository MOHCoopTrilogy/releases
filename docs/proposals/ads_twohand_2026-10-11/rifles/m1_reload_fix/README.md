# M1 Garand + Mosin aimed (ADS) reload: keep the gun up (2026-11-17, user: "Fix the reload")

STAGED ONLY. Nothing deployed, nothing in the mod tree or in either fixes tree. bug-11374.

## What was wrong
The shipped aimed reloads (`coopr_m1_garand_reload_ads`, `coopr_m1_garand_pacific_reload_ads` -> `coop_garand_reload_ads.skc`;
`mosin_reload_ads` -> `mosin_reload_ads.skc`, rifle lane 2026-10-13, runs rb60 / rb53) lower the rifle 3.5-4.2 u straight
down for the whole loading (holds `reach` drop 3.9, `push` drop 3.5, plus the `body_reach` knock). The front sight ends up
just under the centre box, but by perspective the receiver - the part being worked - goes under the bottom of the picture:
offline, the Garand's rear sight sits at 0.97-1.22 of the screen height through frames 8-54 (mean 1.04 = off screen); in the
engine only the barrel, the fore-end and the hand are seen. The Mosin does the same, less (rear sight 0.76-0.85; its action
is at the bottom edge and leaves the picture during the pouch trip and after the charger push).

The shipped clips are byte-identical to `../tools/riflereload.py garand / mosin` rebaked today (md5 9e61ba18 / 6a08c56a), and
they live ONLY in the archived fixes tree `H:\hzm_archive\root\hzm-root-adsfg42\docs\tools\assets\fixes` (bug-11370), not in
main's `docs/tools/assets/fixes`.

## The fix (`tools/upreload.py`, recipes `garand_up` / `mosin_up` on top of the shipped ones)
Every hand key, prop pin, event time and the clip lengths (61 / 92 frames = the server's timing) are the shipped recipe's.
Only where the rifle is held changes:
* butt kept in the shoulder, rifle a little forward, muzzle lowered 4-5.5 deg about the butt (still pointing at the target);
* pouch trip and operating-rod / bolt phases: the rifle stays UP (receiver in the lower third of the picture);
* the clip / charger loading: the rifle is lowered to the height the HAND allows - the clip and thumb stand above the action,
  so the action can come no higher than the hand's top at the box's lower edge (one notch higher put the Garand's clip hand
  over 16-24 % of the box);
* the pouch-trip cant halved (body knocks x2.0 -> x1.0, hold roll 25 -> 14 deg): the shipped ~28 deg roll was unseen while the
  receiver was under the frame; in view it read as the gun tipped over to show its action. Peak roll now 17 / 15 deg.

Offline figures (`tools/vmeasure.py`, no sway; `evidence/*_offline_{before,after}.json`):

| | rear sight (screen height, loading frames) | front sight lowest | worst box cover, loading | entry / exit frames |
|---|---|---|---|---|
| Garand before | max 1.22, mean 1.04 (under the frame) | 0.559 | 0.79 % | 3.9 % (unchanged) |
| Garand after | max 0.91, mean 0.78 | 0.559 | 0.75 % | 3.9 % (unchanged) |
| Mosin before | max 0.85, mean 0.78 | 0.583 | 1.04 % | 10.7 % (unchanged) |
| Mosin after | max 0.81, mean 0.71 | 0.585 | 0.98 % | 10.7 % (unchanged) |

## PAK MEMBERS (merge onto the SHIPPED zzzzzzzzzz_coop_fixes.pk3 at the next release)
Replace, same paths, no row change (the rows already point at these paths; no `newanim/` copy exists for either):

| member | shipped md5 | staged md5 | source |
|---|---|---|---|
| `models/human/animation/viewmodel/rifle/coop_garand_reload_ads.skc` | 9e61ba18 | 77ee70fb | `stage/models/human/animation/viewmodel/rifle/` |
| `models/human/animation/viewmodel/mosin_nagant/mosin_reload_ads.skc` | 6a08c56a | 18ea85c0 | `stage/models/human/animation/viewmodel/mosin_nagant/` |

Not pak members: the `*_phys.json` beside them. `models/player/base/fps_anims_rifle.txt` is NOT changed. The Garand clip is
also what the Pacific Garand plays (same row target). Whoever reconciles the two fixes trees (bug-11370) should copy these two
files into whichever tree builds the pak - the archived tree is the one that holds the shipped versions today.

## Evidence (`evidence/`)
* `garand_reload_ads_before_after_stand.gif`, `mosin_reload_ads_before_after_stand.gif` - standing, before | after, real time.
* `garand_reload_ads_before_after_stances.gif`, `mosin_reload_ads_before_after_stances.gif` - stand, crouch, prone, lean L,
  lean R, braced; before | after per stance, real time.
* `garand_reload_ads_stills_stances.jpg`, `mosin_reload_ads_stills_stances.jpg` - six moments x six stances, before above after.
Engine runs: private client `H:\hzm_work\m1reload\client` (the v1.10.86 binaries copied read-only from the live install,
basepath = the GOG install read-only, own home, muted, 60 fps, screen slot held), m3l2 rifle spot, one aimed shot then
`reload`, one screenshot per 16 ms. Runs `H:\hzm_work\m1reload\runs\gb` / `ga3` (Garand before / after), `mb` / `ma3` (Mosin).

## Not tested
* No playtest by a person; no emptied (last-round) reload captured - the hands clip is the same row, the Garand's emptied
  state only differs by the bolt locked back.
* Dedicated server / second client: not run (client-side hands clip only; length unchanged, so the server's timing is not touched).
* Pacific Garand and finish tiks: not run (same clip through the per-weapon rows).
* Sway on as played (`cg_adsSway 0.1`, breath on) in the engine runs; no box measurement in the engine (a frame-minus-
  reference mask did not work: the no-viewmodel reference does not match the ADS view) - the box figures are offline.

## Reproduce
    cd rifles/assets; python ../m1_reload_fix/tools/upreload.py garand_up,mosin_up --root ../m1_reload_fix/stage
    python ../m1_reload_fix/tools/vmeasure.py garand ../m1_reload_fix/stage/models/human/animation/viewmodel/rifle/coop_garand_reload_ads.skc
    cd ../m1_reload_fix/tools; python run_m1.py <sess> before|after --guns garand --stances stand,crouch,prone,standL,standR,braced
    python compose.py garand <before sess> <after sess> ../evidence
