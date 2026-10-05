# Reload authenticity audit (2026-10-05)

User: *"review all of our variants and new weapons ... make sure we have no other funky reload styles, including the
fg42 ... The 30 cal and mg42 likely need to be looked at as well to make sure reloads are authentic, and if not, built."*

**Status: AUDIT + PLAN only.** Nothing in `hzm-mohaa-coop-mod/` or `openmohaa-hzm/` was edited. No test-slot runs.
Every finding below is from source plus offline renders. None of it has been seen in the engine.

## How a reload is put together (why this audit found more than bad clips)

A reload has three halves, chosen by **three different name lookups**:

| half | chosen by | decides |
|---|---|---|
| first-person hands | cgame `CG_GetVMAnimPrefixIndex` (cg_viewmodelanim.c) -> `fps_anims_*.txt` `<prefix>_reload` | what the hands do |
| torso reload | server `coop_mod/player_Torso.st` `RELOAD_*` action rows (`IS_WEAPON_ACTIVE` exact name, skin suffix stripped) | **how long the reload lasts**; which hand tag holds the gun (`attachtohand offhand` windows); which **ammo prop** is put in a hand (`attachmodel models/ammo/...`) |
| world gun | the weapon .tik `reload` anim | moving gun parts, magazine surface `+nodraw/-nodraw` frames |

Most new guns got a cgame prefix but **no torso row**, so they fall through to the class default: `rifle_reload` (the
Garand: en-bloc clip prop, gun moved to the LEFT hand at frames 1-57, 2.03 s), `smg_reload` (Thompson stick-magazine
prop), `mg_reload` (BAR magazine prop, 3.27 s) or `pistol_reload` (Colt magazine prop). That causes most of the defects
below, and it is the cheapest to fix.

**Durations (hands clip vs torso clip)**, from `tools/lens.py`. Where the torso is shorter, the torso state ends first
(`ANIMDONE_TORSO`) and the hands clip is cut off. Where it is longer, the player waits with nothing happening:

| gun | hands | torso | effect |
|---|---:|---:|---|
| Breda | 5.73 s | 3.27 s (`mg_reload`) | hands cut at 57 % |
| Arisaka, Arisaka Sniper | 3.40 | 2.03 (`rifle_reload`) | cut at 60 %, gun jumps hands at 1.9 s |
| Lee-Enfield Sniper | 3.87 | 2.03 | cut at 52 %, gun flies at ~1.9 s |
| Mosin-Nagant Sniper (+silenced) | 3.07 | 2.03 | cut, gun swap mismatch |
| G43 Sniper | 2.93 | 2.03 | cut, gun flies |
| StG44 Scoped | 2.77 | 2.03 | cut, gun flies, en-bloc clip in hand |
| Carcano Sniper | 3.33 | 2.03 | cut |
| Springfield M1903 (unscoped), Silenced Kar98 Sniper | start clip only (1.63) | 2.03 | no round is ever loaded on screen |
| FG42 | 2.34 | 3.27 (`fg42_reload` = BAR torso) | 0.9 s dead time |
| Type 100, Beretta M38 | 2.43 / 2.30 | 2.67 | small dead time |

## Method

- Inventory: `docs/tools/loadout_weapons.tsv` (armory), every `models/weapons/*.tik` in the live VFS (read-only
  over the pk3s via `ironsights_2026-09-28/tools/vfs.py`). There are 247 finish skins (`_bloody/_blued/_camo_*/_chrome/_gold`).
  They share the base gun's mesh and are resolved to it by both cgame and the server (suffix strip), so each one
  inherits its base gun's verdict. Named model variants with their own mesh were rendered on their own.
- Renders: `tools/sheet.py`, built on the ADS agent's calibrated preview (`ads_bolt_2026-10-04/tools`: vmcam,
  prep_frames, bl_preview, Blender Workbench). 8 frames per reload; split reloads get 3 start, 2 single and 3 end
  frames. Two rows per frame:
  - **EYE**: the calibrated shooter's-eye hip view.
  - **TOP**: looking straight down on the gun, muzzle up the screen and the gun's left on screen-left. A side
    magazine sticks out sideways in this view; a bottom one hides under the gun.

  Each sheet includes the torso's hand-tag windows, its ammo props and the gun's own reload anim, with its surface
  toggles applied. The labels show the frame, the time, the tag holding the gun (`gun@L/R`) and the props.
- **Limitation:** the clips imported from Team Assault (TA) are Carcano, DeLisle, Moschetto, Vickers-Berthier, Breda
  and the Beretta M1934. In the preview they show the gun at an odd angle (pointing up or crosswise), probably because
  of a weapon-tag convention the preview does not model. They are graded on retail status plus props and timing, not
  visually.
- Historical notes: from general knowledge, not checked against sources. Facts I'm not sure of are marked (?).

## Verdict table

OK = authentic enough. minor = the right motion with a wrong prop or timing, or a small mechanical mismatch.
wrong = the wrong feed system, or the gun visibly breaks. missing = no reload of its own; it borrows another gun's.
Sheets are in `sheets/<key>.jpg`.

| weapon (variants) | real feed / action | hands clip (prefix) / torso | verdict | what's wrong | sheet |
|---|---|---|---|---|---|
| M1 Garand (+Silenced, Sniper, Pacific, skins) | 8-rd en-bloc, top; op-rod R | garand / rifle_reload | OK | - | garand |
| **M1 Carbine** | 15-rd detachable box, bottom; handle R | garand (fallback) / rifle_reload | **wrong** | Garand en-bloc clip pushed into the top. The carbine's box magazine never leaves the gun | carbine |
| Kar98k (+G98, skins, Gewehrgranate) | 5-rd stripper, top; bolt R | kar98 / kar98_reload | OK | - | kar98, kar98_g98 |
| **Arisaka Type 99, Arisaka Sniper** | stripper, top (the sniper scope blocks clips: single rounds) | kar98 / **rifle_reload** | **wrong** | gun is handed back to the right hand at 1.9 s mid-clip (flies across the screen), clip cut at 60 %, Garand en-bloc prop | arisaka |
| KAR98 Sniper (+3 variants) | single rounds (scope) | kar98sniper / springfield split | OK | - | kar98sniper |
| **Silenced Kar98 Sniper** | single rounds | kar98sniper / **rifle_reload** | **wrong** | the client gets only the `reload` token: the start clip plays and no round is loaded; en-bloc prop | kar98snsil |
| Springfield '03 Sniper (+12 variants incl. M1903, SMLE scoped) | single rounds (scope) | springfield split | OK | - | springfield, springfield_smlescope |
| **Springfield M1903 (unscoped)** | 5-rd stripper, top | springfield / **rifle_reload** | **wrong** | the start clip only (no rounds go in), en-bloc prop, 2.03 s | springfield_unscoped |
| Lee-Enfield (+skins) | 2x5 chargers, top | enfield / enfield_reload | OK | - | enfield |
| Lee-Enfield (P14) | 5-rd chargers, top | enfield / enfield_reload | minor | two chargers for a 5-round magazine (the tik also says clipsize 10) | enfield_p14 |
| **Lee-Enfield Sniper** | No.4(T): single rounds or chargers (?) | enfield / **rifle_reload** | **wrong** | gun flies at ~2 s, clip cut at 52 % | enfieldsniper |
| Mosin Nagant (+skins) | 5-rd stripper | mosin / mosin_reload | OK | - | mosin |
| **Mosin-Nagant Sniper, Silenced Mosin Sniper** | single rounds (scope over the action) | mosin / **rifle_reload** | **wrong** | cut 2.03/3.07 s, wrong hand-swap window, en-bloc prop | nagant_sniper |
| SVT-40 | 10-rd detachable box, bottom (stripper top-up) | svt / svt_reload | OK | - | svt |
| G43 (+skins) | 10-rd detachable box, bottom | g43 / g43_reload | OK | - | g43 |
| **G43 Sniper** | same | g43 / **rifle_reload** | **wrong** | gun swapped to the left hand at f1, which this clip does not expect: the gun floats off and flies (f12-f50) | g43sniper |
| Carcano (TA) | 6-rd en-bloc, top | carcano / carcano_reload | OK (preview inconclusive) | - | carcano |
| **Carcano Sniper** | en-bloc | carcano / **rifle_reload** | **wrong** | cut at 61 %, Garand clip prop, the TA clip's whole-reload offhand window replaced by f1-57 | (as carcano) |
| DeLisle (TA, +2) | 7-rd box, bottom | delisle / delisle_reload | OK (preview inconclusive) | - | delisle |
| Enfield L42A1 (+camo) | 10-rd box, bottom | enfieldl42a1 | OK | - | l42a1 |
| Johnson M1941 | 10-rd rotary, loaded from the RIGHT with 5-rd strippers; bolt R | johnson (East) / **rifle_reload** | minor | the hands do a right-side load, consistent under the Garand hand-swap. The torso adds a Garand en-bloc prop (f4-42), and the gun's own stripper shows f28-48. Likely the cause of ADS run ab13 "gun drops out of frame" | johnson |
| **StG44 Scoped** | 30-rd box, bottom | mp44 / **rifle_reload** (class rifle) | **wrong** | Garand clip prop, gun swapped to the left hand: a huge gun in the camera at 1.6 s, cut at 73 % | mp44scoped |
| Thompson (+skins, 27A1, M1A1 remodel, M1928) | 20/30 stick, bottom | thompson / smg_reload | OK (M1928 mesh looks stick-fed, low confidence) | - | thompson, tommy28 |
| **Thompson 50rd** | 50-rd Type L DRUM, slid in from the side (?) | thompson / smg_reload | **wrong** | stick-magazine reload from below on a drum gun | thompson50 |
| **Thompson (1928 Tommy)** | drum | thompson / smg_reload | **wrong** | same | tommy1928d |
| MP40 (+skins, Reactivated, MP 75) | 32-rd box, bottom; handle L | mp40 / mp40_reload | OK | - | mp40 |
| **MP40 (MP18)** | 32-rd snail DRUM (TM08), LEFT side | mp40 / mp40_reload | **wrong** | straight MP40 magazine pushed up from below, while the mesh's drum sticks out to the left | mp18 |
| Silenced MP40 | as MP40 | mp40 / **smg_reload** | minor | Thompson stick prop instead of an MP40 magazine | mp40silenced |
| Silenced PPS-43 | 35-rd curved box, bottom; handle R (?) | mp40 / smg_reload | minor | Thompson prop; MP40 cocks on the left | pps43s |
| M3 Grease Gun (+silenced) | 30-rd box, bottom; crank R | mp40 / smg_reload | minor | Thompson prop; cocks a left-side handle instead of the right crank | greasegun |
| Sten Mk II | 32-rd box, LEFT, horizontal | sten / sten_reload | OK (left side confirmed in TOP) | - | sten |
| PPSh-41 | 71-rd drum, bottom | ppsh / ppsh_reload | OK | - | ppsh |
| Moschetto (TA) | 40-rd box, bottom | moschetto / moschetto_reload | OK (preview inconclusive) | - | moschetto |
| Beretta M38 (xw) | bottom box | moschetto / **smg_reload** | minor | Thompson prop; torso 0.37 s longer than the hands | beretta_m38 |
| **Type 100 SMG** | 30-rd curved box, LEFT, horizontal | type100 / **smg_reload** | **wrong** (known, queued with the ADS agent) | the gun's own magazine is correctly on the left (TOP f0). The hand pulls it and brings back a vertical Thompson stick prop (f11-f43); the curved magazine pops back at gun f48. Plus the user's off-hand findings | type100 |
| BAR (+M1918 Classic/A1/A2/Pacific) | 20-rd box, bottom | bar / mg_reload | OK | - | bar |
| **"BAR (M1918 WWI)"** | the mesh is a **LEWIS GUN** (shaders `coop_bar1918_lewis1/lewismag`): 47-rd pan on TOP | bar / mg_reload | **wrong** | BAR box magazine from below on a top-pan gun; the gun's own `lewis_reload.skc` moves the pan bone 67 u | bar1918 |
| StG 44 (+4) | 30-rd box, bottom; handle L | mp44 / mp44_reload | OK | - | mp44 |
| FG42 | 20-rd box, LEFT, horizontal; handle R | fg42 (DaRKaNGeL) / fg42_reload (= BAR torso) | **minor** | the hands are right: the magazine goes out and in on the left (TOP). Wrong: a tan BAR magazine prop held vertically (0.5-1.65 s), shown together with the gun's own magazine from 1.32 s (two magazines); 0.9 s dead time; no right-side charging | fg42 |
| Vickers-Berthier (TA) | 30-rd curved box, TOP | vickers / vickers_reload | OK (preview inconclusive) | - | vickers |
| **Breda 30 (TA)** | fixed RIGHT-side magazine, swung forward, 20-rd stripper; handle R (?) | breda / **mg_reload** | **wrong** | its own `breda_reload` torso (hand swap entry..last) exists but is never selected: clip cut at 57 %, gun on the wrong hand (visibly off the hands), BAR prop | breda |
| DP-28 | 47-rd pan, TOP; handle R | dp28 (Lt. Pato) / **mg_reload** | minor | the pan comes off and goes back on top (the gun's drum1 bone). The torso adds a BAR magazine prop to the left hand (0.5-1.65 s) | dp28 |
| **M1919 .30 cal** (carried, hip-fired; armory slot 4; not deployable) | 250-rd BELT from the LEFT, top cover, handle R (pulled twice) | **bar** (MG fallback) / mg_reload | **missing** | BAR box-magazine reload; BAR prop pushed up under the receiver; the ammo crate just hides at f1-40. `30cal.skd` has only `origin/tag_barrel/tag_eject` bones: no cover bone, no moving parts | m1919 |
| **MG42** (carried, `mg42portable.tik`; not deployable) | belt from the LEFT, top cover (latch at the rear), handle R | **bar** / mg_reload | **missing** | same as the M1919; `mg42.skd` has no cover bone, and `shellbelt` just hides | mg42 |
| Shotgun (+6) | tube, single shells | shotgun split | OK | - | shotgun |
| Bazooka / Panzerschreck / PIAT | single rocket | retail | OK (not rendered) | - | - |
| Colt 45 (+skins/variants except WWI) | 7-rd box in the grip | colt45 / pistol_reload | OK | - | colt45 |
| **"Colt 45 (M1911 WWI)"** | the mesh is a **WEBLEY** revolver (shaders `webleybody/webleykamer`; the pack also ships `webley_*.skc` for it): break-top | colt45 / pistol_reload | **wrong** | Colt magazine swap on a revolver | colt1911w |
| Walther P38 (+2, Silenced), Hi-Standard, Silenced Colt/Beretta, PPK, TT-33 (+silenced), Nambu | box in the grip | colt45 or p38 | OK (PPK/TT-33/Nambu not rendered; same clip as the Colt) | - | p38 |
| Luger P08 (+silenced) | box in the grip; TOGGLE | colt45 / pistol_reload | minor | Colt slide rack instead of the toggle | luger |
| Welrod | box = the grip; bolt (rear knob) | colt45 / pistol_reload | minor | slide rack instead of the rear bolt knob | welrod |
| Beretta M1934 (TA) | box in the grip | beretta / beretta_reload | OK (preview inconclusive) | - | beretta |
| Webley Revolver (+TT) | break-top, single rounds | webley split | OK | - | webley |
| Nagant Revolver | loading gate (right), single rounds | nagantrev split | OK | - | nagantrev |
| S&W M10 .38 | swing-out cylinder, left | m10 (East) / **pistol_reload** | minor | the hands are East's revolver reload, but the torso hangs a Colt MAGAZINE in the left hand (0-1.33 s) | m10 |
| **Mauser C96 (+Trench C96)** | fixed 10-rd box AHEAD of the trigger, STRIPPER-loaded from the top | p38 / pistol_reload | **wrong** | P38 grip-magazine swap: a Colt magazine pushed into the C96's grip | c96, c96trench |

**Counts** (one row per distinct reload setup; finish skins fold into their base): **OK 26, minor 11, wrong 17,
missing 2** (the M1919 and the MG42).

## Prioritised fix list

Hours are working estimates for one agent, offline, before any slot test. After each fixed hip clip, its
`_ads` rebake (below) adds about 1 h per gun.

### P0: server routing only (no art). About 3 h + one batched slot test

Add exact-name rows to `coop_mod/player_Torso.st`. `CondWeaponActive` tries the exact name first, so the rows sit
beside the base rows:

- RELOAD_RIFLE: `kar98_reload` <- "Arisaka Type 99" / "Arisaka Sniper"; `mosin_reload` <- "Mosin-Nagant Sniper" /
  "Silenced Mosin Sniper"; `enfield_reload` <- "Lee-Enfield Sniper"; `g43_reload` <- "G43 Sniper"; `carcano_reload` <-
  "Carcano Sniper"; `mp44_reload` <- "StG44 Scoped" (class rifle, so the row goes in RELOAD_RIFLE).
- RELOAD_WEAPON: `RELOAD_SPRINGFIELD` <- "Springfield M1903", "Silenced Kar98 Sniper" (their hands are the single-round
  split already).
- RELOAD_SMG: `mp40_reload` <- "Silenced MP40"; `moschetto_reload` <- "Beretta M38".
- RELOAD_MG: `breda_reload` <- "Breda" (exists in `anims_breda.txt`; check that its tps clip length matches the 5.73 s
  hands).
- Optional cgame line: give "Arisaka Sniper" the KAR98SNIPER prefix plus RELOAD_SPRINGFIELD (single rounds are what a
  scoped Arisaka really used).

This fixes 9 "wrong" rows outright: Arisaka(+Sniper), the Mosin snipers, Enfield Sniper, G43 Sniper, Carcano Sniper,
StG44 Scoped, M1903, Silenced Kar98 Sniper and Breda. It also clears the props on Silenced MP40 and Beretta M38.

### P1: torso anims of our own for the new guns (props + timing). About 4 h

New `anims_*.txt` entries. They reuse a retail tps skc for the third-person body (others see it). Timing comes from a
time-scaled copy of that skc (the ADS tools already write skc). Props are corrected:

- **FG42**: drop the BAR prop (or add an FG42 magazine prop, held horizontally), and match the 2.34 s hands.
- **Johnson**: no en-bloc prop. Keep the f1-57 hand swap, because East's clip plays correctly under it.
- **DP-28**: no BAR prop.
- **M10**: no Colt magazine.
- Grease gun / PPS-43: MP40 or no prop.

Then the four remaining "minor" rows become OK, except the cocking-side nits.

### P2: art (hand-keyed or rebuilt first-person clips)

| # | gun | approach | est. |
|---|---|---|---:|
| 1 | Type 100 (queued, ADS agent owns) | hand-key: left-side magazine out sideways and back in horizontally, off-hand at idle on the magazine well/housing. Then a torso with a Type 100 magazine prop and 2.43 s | 7 h |
| 2 | M1 Carbine | rebuild from the **G43** reload (same rifle hold, bottom detachable box), retimed to `garand_reload1.skc`'s skin7 hide f8-35. New torso + a carbine magazine prop (from the mesh's `gun clip` part). New cgame prefix `carbine` | 5 h |
| 3 | M1919 .30 cal | (a) re-rig the mesh: split the top cover onto its own bone (skd edit) and add a belt prop/surface, 5 h. (b) hand-key: latch at the rear, cover up, lay the belt in from the left, cover down, right-side charging handle x2, 10 h. (c) torso + prefix, 1 h | 16 h |
| 4 | MG42 | same pipeline. Cock on the right first, then the cover; shares (a) and (b) tooling, so the second gun is cheaper | 12 h |
| 5 | Thompson 50rd + 1928 Tommy (drum) | hand-key one drum reload (drum slides out sideways, new drum in, bolt). Both meshes share the Thompson skeleton, so one clip serves both. Drum prop. Exact-name prefix + torso rows | 7 h |
| 6 | MP18 | rebuild from the Sten's left-side clip retargeted to the MP40 hold (or from the fixed Type 100), with a snail-drum prop | 6 h |
| 7 | "BAR (M1918 WWI)" = Lewis | rebuild from the **DP-28** top-pan clip retargeted to the BAR hold, keyed to the gun's own pan bone (`lewis_reload.skc`). Exact-name prefix + torso | 5 h |
| 8 | "Colt 45 (M1911 WWI)" = Webley | routing only: exact-name -> WPREFIX_WEBLEY + RELOAD_WEBLEY (the pack ships `webley_*.skc` for this skeleton). Check the rig in the preview first | 1 h |
| 9 | Mauser C96 (+Trench) | hand-key: bolt back, stripper into the top guides, thumb the rounds down, strip the clip, bolt forward | 7 h |
| 10 | FG42 polish | add a right-hand charging-handle pull at the end of DaRKaNGeL's clip | 2 h |
| 11 | Luger toggle, Welrod knob | key the rack beat only (the magazine swap stays) | 2 h each |

Totals: **P0 3 h, P1 4 h, P2 about 72 h** (the belt guns are 28 h of that), plus about 12 h of `_ads` rebakes.
**About 90 h overall.** Without the cover re-rig, a hands-only belt reload (the cover never opens) would save about 8 h,
but it would not be authentic.

## Dependencies with the ADS reload work

1. **The `_ads` reloads are derived from the hip clips.** `hold_bake.py auto_recipe` builds `<prefix>_reload_ads`
   from the fps_anims hip row and its charge/idle pose. Every P2 clip, and every new prefix (carbine, drum Thompson,
   MP18, Lewis, M1919, MG42), must exist and pass review before its `_ads` version is baked. Rebake any `_ads` clip
   already made for a gun whose hip clip changes. Type 100 is one item: fix the hip clip first, then the ADS clip.
2. **Routing changes the hand tag the ADS baker assumes.** `auto_recipe` hard-codes "no server hand-off" for
   SMG/MG/pistol. Routing Breda to `breda_reload` introduces an entry..last hand-off, so its recipe needs an offhand
   window like the rifles'. Johnson's ab13 "gun drops out of frame" is very likely the `rifle_reload` f1-57 hand-off
   being missing offline: bake it with `offhand=(1, 57-in-hip-frames)`.
3. **Props drive the ADS agent's `free_tag` / stray-clip work** (bug-3354). Each P0/P1 change moves or removes a prop
   window, so land P0/P1 before that fix is finalised, or re-check it after.
4. Suggested order: P0 routing -> P1 torso/props -> P2 hip clips (one gun at a time, offline review) -> `_ads`
   rebake for that gun -> one batched slot run per group.

## Questions for the user

1. Two "variants" are other guns. "BAR (M1918 WWI)" is a **Lewis gun** and "Colt 45 (M1911 WWI)" is a **Webley
   revolver**. Should they be renamed (armory label, challenges), or keep the names and only get the right reloads?
2. Thompson 50rd, 1928 Tommy and MP18 are **drum** guns. Should they get drum reloads (about 13 h together), or be
   swapped to stick-magazine meshes?
3. M1919 / MG42: approve the full belt reload with an opening top cover (about 28 h; needs a mesh re-rig)? The
   alternative is hands-only with the cover shut (about 20 h, less authentic).
4. C96: build the top stripper-clip load (about 7 h), or accept the grip-magazine swap?
5. Scoped bolt rifles (Arisaka Sniper, Mosin snipers, Enfield Sniper): single-round loading is the historically right
   one for low-mounted scopes. Use it, or keep the clip reloads that the P0 routing restores?

## Files

- `tools/sheet.py`: the contact-sheet renderer (`python sheet.py <out> all|key,...`). Read-only over the live pk3s.
- `tools/torso.py`: parses the torso anims and their events.
- `tools/lens.py`: the duration table.
- `tools/gunanim.py`: which gun bones move in a world reload anim.
- `sheets/*.jpg`: 58 contact sheets, 960x540.
