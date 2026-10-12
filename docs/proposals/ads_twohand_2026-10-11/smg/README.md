# SMG lane of the aimed-animation work (started 2026-10-12)

Scope: the `## smg` rows of `..\coverage.md` (18 weapons). Method = `..\README.md` (the standard, the bake pipeline,
gunphys, the offline centre-box check, staged rows, cgame hooks). Everything here is STAGED: nothing is in the mod
tree or the fixes pak. Engine: worktree `openmohaa-hzm-ads-smg`, branch `ads-smg-next` (= ads-next 94bb3dca, no change
yet; built as `G:\mohaa-adsanim3\cgames\cgame_smg1.dll`). Test game: `G:\mohaa-adsanim3` (owner adsanim3, port 12578).

## State

| step | state |
|---|---|
| 1. support hand in the aim where the hip has it | **done, engine-run in every stance** (below) |
| 2. MP40 reference reload (loaded + empty) | gun side built in a scratch tree only (`tools/smggun.py`); hands not baked yet |
| 3. Thompson family, Sten, PPSh, grease gun, Moschetto, Type 100, MP18 | not started |

## 1. Aim poses (`tools/smgpose.py`, rows by `tools/stage_rows.py`)

The released `<prefix>_charge` pose with the support hand put in the hip idle's hand-to-gun relation, left arm
re-solved. Trunk, eye, firing arm, its fingers and the weapon tag are the released pose's bit for bit (asserted per
bake), so the sight picture cannot change.

| prefix (guns) | hip place | released aim | new aim | centre box, settled aim: released -> new (engine) |
|---|---|---|---|---|
| mp40 (MP40, silenced, PPS-43, grease guns, MP18, MP40 R2) | (10.9, -3.4, 1.6) on the magazine housing | 2.4 u off | **0.0 u** | 11.3 -> 11.4 % |
| ppsh | (4.4, -3.0, 1.3) behind the drum | 4.7 u off | **1.2 u** (1.2 u lower, see below) | 20.1 -> 17.1 % |
| moschetto (both tiks) | (6.6, -3.8, 1.2) on the fore-end | 2.6 u off | **0.0 u** | 11.4 -> 7.6 % |
| type100 | (14.1, -7.9, -2.1) on the side magazine | 7.4 u off | **1.4 u** (was 2.0 in the pistol lane's pose) | 26.1 -> 21.2 % |
| sten | on the side magazine | - | 0.0 u (pistol lane's clip, taken over unchanged) | 29.4 -> 14.9 % |

* PPSh: at the exact hip place the thumb and fingertips stand up either side of the rear sight (9.8 % of the box,
  offline); 1.2 u lower it is out of the box. Type 100: exact place = 11.8 % hand in the box; (0, 1.05, -0.95) keeps
  it inside the matrix's 1.5 u for 1.9 %.
* Runs: `sa1` = released poses (before), `sa2` = new poses, stand / crouch / prone / lean L / lean R / crouch-lean
  L / R / braced, 5 guns - pose factor 1.00 and the sight line where the released pose has it in all 40;
  `sa3` = the seven guns that share the rows (silenced MP40, PPS-43, both grease guns, MP18, MP40 R2, Beretta M38),
  standing. Stills: `evidence/aim_<gun>_before_after.jpg`, `evidence/aim_<gun>_stances_sa2.jpg`,
  `evidence/aim_variants_stand_sa3.jpg`.
* Seen and NOT fixed: (a) Sten - the taken-over pose draws the gun about 45 px lower than the released pose does
  (front sight now visible over the receiver cap) although the probe reads the same sight line and relief: open,
  bug log. (b) PPSh / Moschetto - the aim poses borrow the MP40's pistol-grip firing hand, which holds air under a
  rifle stock (hidden in the settled aim; will show in reloads). (c) braced: the sights sit at the bottom edge of the
  centre box for every gun (taken to be the braced view's own framing; the released poses were not run braced). (d) MP18 looks untextured
  (flat brown) in its aim still.

## 2. MP40 reference - what is decided so far

* The MP40 mesh has NO cocking handle: the slot is only painted on the left of the receiver (x 4.3 .. 12.0, z -4.25).
  `tools/smggun.py` adds one (a box on its own bone, existing vertices untouched), generates the gun's action clips
  and patches all 11 tiks that use the mesh.
* Open bolt, modelled as it works: handle BACK while the gun is ready, forward and back on every shot, FORWARD after
  the last round (`fire_empty` / `idle_empty` - the server already picks them). So an empty reload is cocked after the
  magazine goes in and a reload with rounds left is not. **Needs a yes from the coordinator** (the alternative is
  the retail mime: pull and let it run forward every time).
* Timeline is the server's: 76 frames, magazine prop in the left hand frames 10-48, the gun's own magazine hidden for
  the same frames; the cock has frames 48-76.

## Tools (`tools/`)

`takeover.py` regenerates `run_smg.py` and the measure tools from `..\tools` repointed at G:\mohaa-adsanim3;
`smgpose.py` (aim poses + `handsurvey.json`), `stage_rows.py` (fps_anims_smg.txt = released fixes-pak copy + this
lane's rows), `mkov_smg.py` (overlay; `--base` = released rows for a "before" run), `aimpair.py` (before / after
stills, stance sheets, engine numbers), `sideview.py` / `eyepair.py` / `gunside.py` (offline looks: hands on the gun,
eye view with box contents, the mesh with a ruler), `smggun.py` (handle + action clips + tik rows),
`status_merge.py`, `buglog_add.py`. Run a session:
`python run_smg.py <id> --overlay <abs pk3> --cgame cgame_smg1 --guns mp40,ppsh --parts stills --braced --yaw 160`.

Reusable by the MG / heavy lane: `smgpose.py` (any prefix: add a GUNS row), `gunside.py`, `sideview.py`,
`aimpair.py`, `smggun.py`'s `patch_tik` / `same_mesh_tiks` (open-bolt rows for every tik on a mesh).
