# PISTOLS - FOLLOW-UP CUT (ship2), 2026-10-13 afternoon, pistol lane

**Contents: the Mauser C96 and the Trench C96, the two guns cut v2 held out for their stripper clip. Nothing else.**
The folder `ship2/` beside this file is FROZEN from the commit that adds it (built by `tools/shipcut2.py` from the
lane's staged tree). It is ADDITIVE to `ship/` (cut v2): no file of v2 is in it and none is replaced.
Engine: unchanged - `ads-next` **e8e199be**, the engine of cut v2, is enough.

The lane stopped here on the coordinator's budget stop. The S&W M10, the Luger toggle flick, the Welrod bolt sound,
the checks on the shipped pistols and the texture lifts are NOT in this cut and were not finished - see the handover
at the top of `README.md` for what exists of them (staged, not run or not looked at).

Nothing here was played by a person. Every figure is from the engine harness (private copy `G:\mohaa-adsanim`, engine
`screenshot` frames, listen server).

## A. What the two guns have now

* **Hip reload: the released one.** The game already loads the C96 from the top with a stripper clip (hands
  `viewmodel/coop_reload/c96_reload.skc`, torso row `coop_reload_c96`, the prop `models/ammo/coop_c96_stripper_full.tik`
  / `_empty.tik`). The lane's earlier staged rows re-declared that hip row as the P38 magazine clip; that is gone
  (bug-3875). Looked at in the engine, run pa34: the stripper reload plays for the base gun (rounds left and emptied)
  and for the Trench gun (rounds left).
* **Two-handed aim** on its own row `coopr_mauser_c96_charge -> viewmodel/pistol/coop_c96_ads2h.skc`. That clip is
  today a COPY of the P38's two-handed pose under its own name (the mesh is rigged to the P38's hand); it was not
  re-fitted to the broomhandle grip.
* **Aimed reload on the server's own prop and timeline** (torso frames 28 clip in the hand / 41 in the guides / 44 the
  rounds are in / 47 the empty clip taken / 56 gone - a server row, not changed). The gun comes straight down under the
  centre box and is turned so that the eye looks at the side of the clip; the support hand brings the clip of five
  rounds from below the frame, pinched at its top, stands it in the guides, presses, takes the empty clip out and drops
  it to the left; the bolt runs forward as the clip leaves (2.0 u; Trench 2.56 u, the travel of its own fire clip); the
  gun returns to the aim. Rounds left: the support hand draws the bolt back first. The prop never jumps between the
  hand and the gun: `tag_weapon_left` is rigid to the hand with the transform that equals `tag_weapon_right` at frames
  41 and 47 (asserted in `tools/c96.py`).
* **Bolt hold-open on empty** (`idle_empty`), bolt worked in the emptied hip reload (`reload_empty`), and the hip
  `reload` row's gun clip replaced by one of the SAME length in which the bolt is drawn back where the released hip
  hands pull it (base: 73 frames x 1/30 s; Trench: 84 x 0.032 s).
* **Trench C96**: the same states written on the bolt bone its mesh already has (`Bone2`); the white patch at the
  rear = a white surround in `textures/coop_c96trench/stuff2.jpg` around the hammer's ring, filled with the ring's own
  steel (3.9 % of the sheet).

## B. Figures (worst frame's cover of the centre box beyond the settled aim's sway envelope, per cent; bar: under 2)

| gun | reload | stand | crouch | prone | lean L | lean R | runs |
|---|---|---|---|---|---|---|---|
| Mauser C96 | rounds left | 0.00 | 0.00 | 0.10 | 0.70 | 0.90 | pa32 |
| Mauser C96 | emptied | 0.01 | 0.11 | 0.05 | **4.33** | 0.36 | pa30 (stand also pa32: 0.00) |
| Trench C96 | rounds left | 0.00 | 0.00 | 0.10 | 0.20 | 0.30 | pa32 |
| Trench C96 | emptied | 0.00 | 0.06 | 0.10 | 0.33 | 0.24 | stand pa32; the stances pa30, with the LONGER bolt travel (4.7 u) that was replaced afterwards - not re-run |

**The 4.33 % (base gun, emptied, lean left, 13 frames over 2 %)** is in capture frames 300-328, while the gun still
stands in the dry aim and before any hand moves: the frames show the haze of the eight shots drifting across the
door, no hand and no gun part in the box (`evidence/c96_stances_emptied_pa30_rounds_left_pa32.jpg`, row 3). It is
read as muzzle smoke; it was NOT confirmed by a measurement without the smoke (the runner option for that,
`run_2h.py --epause`, is written and not used).

## C. Files (27, 738 kB; `ship2/FILES.txt` has sizes and md5)

| what | files |
|---|---|
| tiks | `models/weapons/mauser_c96.tik`, its 7 finishes (bloody blued camo_desert camo_winter camo_woodland chrome gold), `mauser_c96_c96trench.tik` |
| base gun | `models/weapons/coop_c96/c96.skd` (bolt end + hammer on their own bones, a bolt bar and an open-port patch added), `coop_c96_idle_empty.skc`, `_reload_ads_loaded`, `_reload_ads_empty`, `_reload_empty`, `_reload_hip` |
| Trench gun | `models/weapons/coop_c96trench/coop_c96t_idle_empty.skc`, `_reload_ads_loaded`, `_reload_ads_empty`, `_reload_empty`, `_reload_hip`; `textures/coop_c96trench/stuff2.jpg` |
| hands | `models/human/animation/viewmodel/pistol/coop_c96_ads2h.skc`, `coop_c96_reload_ads.skc`, `coop_c96_reload_empty_ads.skc` |
| new surfaces | `scripts/coop_c96_clip.shader`, `textures/coop_c96/coop_c96_boltbar.tga`, `coop_c96_port.tga` |

Rows - `ship2/ROWS_fps_anims_pistol.txt`, to apply to the `fps_anims_pistol.txt` that carries cut v2:
1. REMOVE the two pin rows of the held-out C96: `coopr_mauser_c96_charge` (-> `viewmodel/p38pose00.skc`) and
   `coopr_mauser_c96_idle` (-> `viewmodel/pistol/coltpose.skc`). Every run above was made without them: the hip idle is
   then the P38's `coop_p38_idle2h.skc`, as for the other pistols on that prefix.
2. ADD four rows: `coopr_mauser_c96_charge`, `_reload_ads`, `_reload_empty` (the RELEASED hip clip again, only so that
   the cgame finds the next one), `_reload_empty_ads`.

No shared table changes: `anims_shared.txt`, `player_Torso.st` and `anims_pistol.txt` are not in this cut. The Trench
gun takes the same hands rows (its name falls back to the base gun's key).

## D. Server side

`python tools/srvrows.py ship2` (run with `IRONSIGHT_EXTRA_PAKS` unset, bug-3878): **9 weapon tiks checked, 0 declared
server-side changes, 0 FAIL** (`evidence/srvrows_ship2.txt`). The only server-read row whose clip FILE changed is
`reload` (the hip gun clip, same length, same server block). The whole staged tree: 115 tiks, 93 declared (the
decisions of cut v2 D2 and the M10), 0 FAIL (`evidence/srvrows_stage_pa34.txt`).
NOT done for these two guns: a dedicated-server run, a second client.

## E. Verified / not verified

Verified in the engine: stand, crouch, prone, both leans, both reloads, both guns (table B; every stance on one sheet,
looked at); the clip going in at full size (`evidence/c96_clip_going_in_contact_pa30.jpg`); hold-open in the dry aim;
bolt back / forward on the lowered gun; the hip reload. Run logs (pa30, pa32, pa34): no script error; the only lines
that name a C96 file are three "Couldn't find image file for shader coop_c96_case / _bullet / _strip" at boot - the
private install's shader preload list from yesterday's runs; no staged file names those shaders.

NOT verified - tell the user:
* braced, crouch-leans, the vehicle seat; sprint / aim dropped / fire / weapon switch during the aimed reload;
* the seven finish tiks (same text as the base tik apart from the shader lines; the bolt bar and the port patch keep
  their own steel-blue / dark colour on every finish, also on gold and the camos);
* the Trench emptied reload in the stances with the final bolt travel; the Trench emptied hip reload;
* the bolt's motion in the HIP reload up close (the hip sheet is small: the choreography is seen, the bolt is not);
* third person / another player's view (they see the released torso reload and the prop, plus the new hip gun clip);
* the lean-left 4.33 % as smoke (above);
* `tools/variants.py` prints "NO: other mesh" for the Trench tik - it has no staged mesh because its own mesh already
  carries the bolt bone; that line is the checker's rule, not a gap.

Known weak points, seen: the rounds leave in one frame when the server swaps the full prop for the empty one (frame
44, under the pressing hand) - the released hip reload does the same; after the hand drops the empty clip the gun is
alone for about 0.2 s while it rises; in the Trench gun's aim the black bolt block sits in the sight picture as in the
released game; a thin light edge shows along the base gun's grip beside the firing hand in the two-handed aim.

## F. Evidence (all in `evidence/`)

| file | what | state |
|---|---|---|
| `c96_aimed_reload_emptied_pa30.gif` | base gun, emptied aimed reload, standing, centre box drawn | finished |
| `c96_aimed_reload_rounds_left_pa32.gif` | base gun, rounds left (bolt drawn first), standing | finished |
| `c96_aimed_reload_rounds_left_pa30_superseded_gun_alone_half_second.gif` | the earlier timing: the lowered gun alone for 0.5 s | superseded, kept |
| `c96_trench_aimed_reload_emptied_pa32.gif` | Trench gun, emptied aimed reload, standing | finished |
| `c96_clip_going_in_contact_pa30.jpg` | contact sheet, the clip and its rounds from the side, every third capture frame | finished |
| `c96_stances_emptied_pa30_rounds_left_pa32.jpg` | 8 rows: emptied then rounds left, each crouch / prone / lean L / lean R | finished |
| `c96_hip_reload_rounds_left_and_emptied_pa34.jpg` | the hip reload = the released stripper reload | finished (small tiles) |
| `srvrows_ship2.txt`, `srvrows_stage_pa34.txt` | checker output | - |

## G. Rebuild / re-check

```
cd tools
set IRONSIGHT_EXTRA_PAKS=<abs>\_ov_wip.pk3;<abs>\_bases.pk3     (bake only; UNSET it for srvrows.py)
cd ..\<stage> & python ..\tools\c96.py . reload,gun             (hands, gun clips, tiks, Trench, rows_p12_c96.txt)
sh c96try.sh out.jpg 30-58:2 empty                              (offline tiles WITH the server's props: c96view.py)
python srvrows.py ..\ship2
python run_2h.py <id> --overlay <ov.pk3> --cgame cgame_adsnext13 --guns mauser_c96,mauser_c96_c96trench --parts demoy --both
       --eshots mauser_c96=8,mauser_c96_c96trench=8 --demoreload 190 --demoreload_e 180 --shots 2 --tail 360:4
       --dstances crouch,prone,standL,standR --lstances crouch,prone,standL,standR      then  python centrebox.py <id>
```
