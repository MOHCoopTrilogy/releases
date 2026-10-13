# Sawn-off double-barrel shotgun (`coop_dbshotgun`) - proposal, STAGED

**Status 2026-10-12: a working weapon in the harness, not finished to the user's bar.** Everything is staged in this
folder and on engine branch `dbshotgun-next` (worktree `C:\mohaa-coop-dev\openmohaa-hzm-dbs`, commit d67ba09e, cgame
only, build dir `.cmake`). Nothing is in the mod tree, the fixes pak or the live install.

## 1. Source and licence

"Double Barrel Shotgun" by Jean PFP, **CC0**, https://opengameart.org/content/double-barrel-shotgun - details, sha256
and how the files are handled: `source/SOURCE.md`. Nothing else was downloaded. Sounds are retail files only.

## 2. What is built

| Part | State | Seen in the engine? |
|---|---|---|
| Mesh: the author's HIGH file, 12,965 triangles, 13 surfaces, 11 bones (barrels on the hinge pin, top lever, two triggers, two shells, three tags), 60 cm long at the retail weapon scale | done | yes (hip, aim, third person, ground) |
| Texture: one 2048 sheet (author's diffuse + glossy sheets projected onto a new UV atlas, our own AO), small 256 sheet for shells / bead | done; plain (little surface detail) | yes |
| Brass bead between the muzzles, sight row (bead over the breech top) | done | yes - bead on the screen centre |
| Weapon tik: numbers (section 4), per-barrel fire rows, ejecting reload rows, own sound aliases | done | fired and reloaded, no script / tiki errors in the logs |
| Gun's own action: triggers, lever, barrels drop 34 deg, fired cases thrown out (one or both), a shell into each empty chamber, shut | done | yes (GIFs) |
| First-person hands, HIP: held-out idle, raise / lower, fire kick, reload (lever-break, shell by shell, swing shut) | first pass - works, **not polished** (section 6) | yes (GIFs) |
| First-person hands, AIMED: own aim pose | first pass, **picture not good yet** | one still |
| AIMED reload, stances (crouch / prone / leans / braced), box measurements (`boxeng.py --sway`), `gunphys.py` weight | **not done** | - |
| Third person | the pump gun's hold / fire / reload rows by name; **fire and reload still show the pump stroke** | hold looked at, fire / reload not |
| Loadout wiring, recoil table row, loot icon | prepared as text only (`wiring/WIRING.md`), **not applied, not run** | - |

It is a HAMMERLESS gun (top lever, tang safety): there are no hammers to thumb back. It is modelled as a boxlock
with selective ejectors, which is how such guns work: opening throws out the fired cases only; a live shell stays.

## 3. Pipeline (reproducible; run from this folder)

```
BL="C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
"%BL%" --background --factory-startup --disable-autoexec --python tools/bl_inspect.py -- source/Shotgun/doubleBarrelHight.blend
"%BL%" --background --factory-startup --disable-autoexec --python tools/bl_build.py -- source/Shotgun build      # parts, UV atlas, bakes (2 min, 4 threads)
python tools/dbs_tex.py          # build/dbs_diffuse.png : steel from the glossy sheet, walnut, AO
python tools/dbs_build.py        # assets/models/weapons/coop_dbshotgun/coop_dbshotgun.skd, textures, shader, build/model.json
set IRONSIGHT_EXTRA_PAKS=<abs>\build\ov.pk3        (the offline hand renderer reads the gun out of an overlay)
python tools/dbs_hands.py bake   # assets/models/human/animation/viewmodel/coop_dbshotgun/dbs_*.skc + build/hand_paths.json
python tools/dbs_anim.py         # assets/models/weapons/coop_dbshotgun/coop_dbs_*.skc (the gun's own clips; uses hand_paths)
python tools/dbs_tik.py          # assets/models/weapons/coop_dbshotgun.tik (numbers at the top of the tool)
python tools/sightrow_dbs.py C:\mohaa-coop-dev\openmohaa-hzm-dbs\code\cgame\cg_adssights.h      # from sights_override.json
cmake --build .cmake --config Release --target cgame -- -m:4 -v:m        (in the worktree; dash switches, bug-3704)
python tools/mkov_dbs.py build/ov.pk3                                    # test overlay = harness plumbing + assets + rows
python tools/run_dbs.py <session> --overlay <abs pk3> --cgame cgame_dbs4 --parts look,action
python tools/dbs_hsheets.py [clip:f,f ...]                               # offline look at the hand clips
```

Tools: `dbs_skx.py` (SKD v5 / SKC v13 writer for N bones and N surfaces - the mod's writers are one-bone containers
or patch an existing file; same byte layout), `dbs_rig.py` (the lanes' rig / IK / offline-render libraries, read
only), `dbslib.py`, `sheet.py`, `mkgif.py`, `buglog_add.py`. Harness: private copy `G:\mohaa-hudfeed4`, owner
`hudfeed4`, port 12761, binaries `openmohaa_integ.exe` + `games/game_integ.dll` + `renderers/gl2_integ.dll` +
`cgames/cgame_dbs4.dll` (= d67ba09e). Runs: look1-4, act1-3 under `G:\mohaa-hudfeed4\runs\`.

## 4. The weapon's numbers (coop uses the `dm` set) - `tools/dbs_tik.py`

| | Pump gun (`shotgun.tik`) | Double barrel | Why |
|---|---|---|---|
| Shells loaded | 5 | **2** | two barrels |
| Trigger | one shot, then the pump (0.75 s) | one barrel per pull, **0.30 s** between | no action to work between the shots |
| Pellets x damage | 20 x 14 = 280 | **26 x 14 = 364** per barrel | "a few more pellets"; both barrels in 0.3 s = 728 |
| Spread (pitch yaw min, max) | 80 80 95 95 | **115 115 135 135** | cylinder bore, 13 in barrels: about 1.4 x the cone |
| Pellet range | 1000 | **650** | short barrels; nothing past 650 u |
| Reload | 0.77 s + 0.67 s per shell + 1.07 s | same clock: **2.5 s for one shell, 3.2 s for two** | timing is the shared third-person shotgun states; two shells for 3.2 s is slow per shot |
| Move speed | 0.99 | 1.00 | short and light |
| View kick | -20 -20 / 0.05 / T / 12 5 10 | **-23 -26 / +-2 / recentre 12 / T / 14 6 12** | sharp flip, some sideways; the first try (-27 -31) threw the view 25 deg up |
| Start ammo (dm) | 60 | 40 | |
| Sounds | - | fire = ShotgunFire1.wav at pitch 0.70 / volume 2.2 (retail 0.80 / 1.95); open = Webley break-top latch; shell = ShotgunFill1; shut = coop_wpn_action_heavy | **not listened to** (the harness is muted); every alias resolved (no alias errors with developer 1) |

Name `"Shotgun (Double Barrel)"`: the engine strips " (..)" wherever a weapon is looked up by name, so the gun
inherits the shotgun's third-person rows, ADS tune, statemap and ammo with no engine change.

## 5. Engine change (branch `dbshotgun-next` d67ba09e, cgame only, 3 files) - needed, and why

1. `cg_viewmodelanim.c`: the per-weapon first-person rows `coopr_<weapon>_<row>` are looked up for EVERY row, not
   only the three reload rows. Without it the hands are the pump gun's: the left hand works a pump after each shot.
   No such row exists for another gun, so nothing else changes.
2. `cg_modelanim.c`: the local player's held gun plays `reload_empty` / `reload_single_first` in place of `reload` /
   `reload_single` when the row starts on an empty clip and the tik has that row (both cases thrown out; left chamber
   first). The SMG lane's `ads-smg-next` swaps `reload` -> `reload_empty` in the same function: merge into one block.
3. `cg_adssights.h`: one row for the new tik (written by `tools/sightrow_dbs.py` from `sights_override.json`; the
   shared ironsights `sights.json` is not edited).
No fgame change, no protocol change, multiplayer untouched (rows and swaps key on rows only this tik has).

## 6. Open points (honest list)

1. **Reload look (hip)**: it reads (breech opens, cases fly, hand brings a shell to each chamber, swung shut) but: the
   grip hand and the stock's wood are a big lump in the lower right (the eye sits beside the grip in the retail
   shotgun rig; the reload pose has little room: arms' reach vs the eye), the loading hand cups the shell rather
   than pinching it, the thumb does not visibly work the lever, one hands clip serves both chambers (0.7 u off).
2. **Aimed picture**: bead on the centre, but the grip wood fills the lower middle and the barrels are hidden behind
   the breech. Needs the aim pose reworked (gun further out / eye higher) and then the aimed reload, all stances, the
   box measure and the physics pass - none of that is started. An aimed reload plays the hip clips today.
3. **Third person**: the shared shotgun rows play the pump stroke on fire and the pump-gun reload. Own statemap rows
   (`IS_WEAPON_ACTIVE "mainhand" "Shotgun (Double Barrel)"` placed before the Shotgun rows) and clips are needed.
4. Texture is plain; the author's sheet uses a quarter of its area. A detail pass (edge wear, engraving) is art work.
5. Sounds chosen by file, never heard. Recoil table row, loot icon, loadout wiring: `wiring/WIRING.md`.
6. Provenance note in `source/SOURCE.md` (Textures.com images inside the author's .blend, not used by us).
7. `_variant_packs/shotgun_doublebarrel.zip` (a third-party "Shotgun of two cannons" pack already on disk) was not
   opened - the user chose this model.
8. 3 IK clamps remain in the far frames of pullout / putaway (arm at full reach; not visible in the raise GIF).

## 7. Files for integration

- `assets/models/weapons/coop_dbshotgun.tik`, `assets/models/weapons/coop_dbshotgun/` (skd + 8 gun clips)
- `assets/models/human/animation/viewmodel/coop_dbshotgun/dbs_*.skc` (8 hand clips)
- `assets/textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg`, `coop_dbshotgun_parts.jpg`
- `assets/scripts/coop_dbshotgun.shader` (two NEW shader names, this file only)
- `rows/fps_rows_coop_dbshotgun.txt` -> append inside `models/player/base/fps_anims_shotgun.txt` (fixes pak copy)
- engine: `dbshotgun-next` d67ba09e; `sights_override.json` + `tools/sightrow_dbs.py` for the header row
- `wiring/WIRING.md` (script / menu edits, options for where the gun is offered)

## 8. Handover

Next steps in order: (a) aim pose + aimed reload rows (`coopr_shotgun_double_barrel_reload_ads` etc. - the `_ads`
suffix is appended to the coopr name by the engine), (b) stances and `boxeng.py --sway`, (c) `gunphys.py` in place of
the simple kick in `dbs_hands.py`, (d) third-person statemap rows, (e) wiring option the user picks, (f) listen to the
sounds. Knobs: `dbs_hands.py` PUSH / RELOAD / PINCH_ROLL / KICK, `dbs_anim.py` OPEN / LEVER, `sights_override.json`.
Traps met: bug-3705 .. bug-3710. Harness copy: someone's `zzzzzzzzzzzzzzzz_memorialtest.pk3` (menu art only) sits
in `G:\mohaa-hudfeed4\home\maintt` and was left alone.
