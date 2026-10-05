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

---
## DECISIONS (user, 2026-10-05)
1. Rename the misnamed variants and give them their real reloads: "BAR (M1918 WWI)" -> Lewis Gun (top pan); "Colt 45 (M1911 WWI)" -> Webley revolver (break-open).
2. Drum guns (Thompson 50rd, 1928 Tommy, MP18 left-side drum): build real drum reloads (~13 h).
3. M1919 .30 cal + MG42: FULL belt reload with an opening top cover (model rework, ~28 h).
4. C96: build the top stripper-clip load (~7 h).
5. Scoped bolt rifles (coordinator default, not asked): historically correct single-round loading.
Order: server routing + server-side reload fixes + renames first (they change hand/mag timing the ADS rebake depends on); new hand-keyed clips next; ADS rebakes after each fixed hip clip.

---
## PHASE A - built 2026-10-05 (server routing, server-side props/timing, renames)

No hand clip, fps_anims row, viewmodel .skc or cgame viewmodel code was touched (ADS agent owns those).

**Routing** (`coop_mod/player_Torso.st`, exact-name rows; `CondWeaponActive` tries the exact name before the
skin-suffix strip, so finish skins follow their base):
- RELOAD_WEAPON: `RELOAD_SPRINGFIELD` <- "Springfield M1903", "Silenced Kar98 Sniper"; `RELOAD_MG` <- "StG44 Scoped".
- RELOAD_RIFLE: `kar98_reload` <- Arisaka Type 99 / Arisaka Sniper; `mosin_reload` <- Mosin-Nagant Sniper / Silenced
  Mosin Sniper; `enfield_reload` <- Lee-Enfield Sniper; `g43_reload` <- G43 Sniper; `carcano_reload` <- Carcano Sniper;
  `coop_reload_johnson` <- Johnson M1941.
- RELOAD_SMG: `mp40_reload` <- Silenced MP40, M3 Grease Gun, Silenced Grease Gun, Silenced PPS-43;
  `moschetto_reload` <- Beretta M38.
- RELOAD_MG: `mp44_reload` <- StG44 Scoped; `coop_reload_fg42` <- FG 42 (was the BAR torso); `breda_reload` <- Breda
  (TA's own, never selected before); `coop_reload_dp28` <- DP-28.
- RELOAD_PISTOL: `coop_reload_m10` <- S&W M10 .38.
- ATTACK_MG_SECONDARY: "Lewis Gun" row (its butt-stroke used to come from the "BAR" suffix match).

**New torso aliases** (`models/player/base/anims_shared.txt`; times = seconds into the reload):
- `coop_reload_fg42`: the BAR torso retimed to 2.34 s (= DaRKaNGeL's hands; new
  `models/human/animation/viewmodel/mg/coop_tps_reload_fg42.skc`, frameTime-only copy). The FG42's own
  `models/ammo/fg42clip.tik` is in the left hand 0.67-1.34 s, exactly while FG42.tik hides the gun's magazine
  (measured hand-to-magazine distance: grab 0.6 s, away 0.69-1.29 s, seated 1.36 s). clip_fill 1.34 s.
  Fixes the double magazine (BAR prop + gun magazine 1.32-1.65 s) and the 0.9 s dead time.
- `coop_reload_johnson`: Garand torso, same f1-57 hand-off, **no** en-bloc prop; clip_fill f31.
- `coop_reload_dp28`: BAR torso, **no** BAR magazine prop; clip_fill 2.0 s (pan seated, before the rechamber).
- `coop_reload_m10`: Colt torso, **no** Colt magazine; clip_fill 1.87 s (cylinder closes).

**Renames** (item names only; tik paths, unlock ids, challenge ids and saves unchanged): `bar_bar1918.tik`
"BAR (M1918 WWI)" -> **"Lewis Gun"**; `colt45_colt1911w.tik` "Colt 45 (M1911 WWI)" -> **"Webley Mk VI"**. Armory
labels via `docs/tools/wire_mv2.py` (regenerated loadoutskins MV block, reqmv/mvp cfgs), challenge text via
`variant_challenges.py --emit`, Service Record names in `gen_service_record.py`, engine `cg_adssights.h` regenerated
(`ironsights_2026-09-28/engine/gen_sights_header.py` over a 2-tik overlay; 2-line diff - the by-name rig-solve lookup is
exact). Their reload is still the BAR/Colt one: the real Lewis/Webley reloads are phase B.

Offline after-sheets: `sheets/after/<key>.jpg`. In-engine: run `ra1` (below).

### Phase A in-engine check (run `ra2`, 2026-10-05, one batched run, slot "reloadauth")
Install `G:\mohaa-reloadauth` (byte copies of the LIVE set: exe d23dd662, cgame d563b759, game 6f68255a, gl2
16b8534d), overlay = the phase A files + the ironsights polling `weather.scr`; m3l2 harness spot; 22 guns, one
screenshot every 3rd frame at fixedtime 16. Sheets: `sheets/engine/<gun>.jpg` (12 frames each, HUD on).
- **0 `Script Error`**, no missing-animation warning for any new alias (`fg42clip.tik` cached = alias parsed). The only
  anim warning, `carcano_rechamber` missing for the Carcano Sniper, is pre-existing and unrelated.
- Every routed gun keeps the gun in the hands for the whole reload (no hand-swap jump, no gun across the screen);
  StG44 Scoped / G43 Sniper / Arisaka / scoped Mosin, Enfield and Carcano / M1903 / Silenced Kar98 Sniper all coherent.
- FG42: one magazine at all times (the gun's hides 0.66 s, the FG42 prop rides the hand, gun's returns 1.32 s).
- Ammo: the HUD's MAGS counter (= floor(reserve/clipsize)) steps down when clip_fill runs: FG42 ~1.39 s, Johnson
  ~1.1 s, DP-28 ~2.0 s, Breda ~4.4 s - each at its notetrack. M10 and the MP40-routed SMGs spent too few rounds
  to move the floor, so their fill moment is not visible on the HUD (reload completed; notetracks same form).
- Seen, NOT caused here: the **Beretta M38** (xw `moschetto.tik`) points almost straight up through idle and
  reload: the TA moschetto hands do not fit that mesh (cgame maps "Beretta M38" -> WPREFIX_MOSCHETTO). Phase B item.
  Breda's TA reload swings the gun low and brings a hand close to the camera (its own authored clip) - user eyeball.

## PHASE B - proposed order (not started)
1. **Type 100** (ADS agent, user-reported): fix the hip clip (left magazine out sideways), torso with
   `models/ammo/type100_clip.tik` (it exists) at 2.43 s, then its `_ads`.
2. **Single-round scoped bolt rifles** (Arisaka Sniper, Mosin snipers, Enfield Sniper): cgame prefix -> a single-feed
   set + RELOAD_SPRINGFIELD rows; mostly re-timing of the existing springfield/kar98sniper split per mesh. ~5 h.
   Cheap, removes the remaining "stripper clip under a scope".
3. **Webley Mk VI**: exact-name -> WPREFIX_WEBLEY + RELOAD_WEBLEY (its pack ships webley_*.skc for this skeleton);
   verify the rig in the preview first. ~1-2 h.
4. **M1 Carbine** (still wrong, not in the phase B list): rebuild from the G43 reload + carbine magazine prop. ~5 h.
5. **Lewis Gun**: DP-28 top-pan hands retargeted to the BAR hold, keyed to the gun's own pan bone. ~5 h.
6. **Beretta M38 hold** (found in ra2): map to MP40 hands or re-pose. ~1-2 h.
7. **Drum reloads**: one Thompson drum clip for Thompson 50rd + 1928 Tommy (`thompson_clip50.tik` prop exists),
   then the **MP18** left snail drum using the fixed Type 100 left-side work as reference. ~13 h.
8. **C96 stripper-clip top load**. ~7 h.
9. **M1919, then MG42 belt reloads** with an opening cover (mesh re-rig + belt prop + hands). ~28 h, last: largest,
   shares tooling, and nothing else waits on it.
After each hip clip lands: its `_ads` rebake (ADS agent), then a batched slot run per group.

## PHASE B progress (2026-10-05)
Engine: d154f251 (cgame per-weapon reload clips `coopr_<weapon key>_<suffix>`, data in anims_shared.txt; Webley Mk VI ->
Webley hands; test-only `coop_vmPrefixTest`), 7dbf3ca5 (ejected magazines rest on their side). Tools: `engine/apply_*.py`,
`tools/retarget.py` (donor clip -> per-gun clip: hand offsets in the gun frame, holds, idle seams, a hand tag that
carries a prop from the grip frame), `tools/skc_slice.py`, `tools/run_reloadauth.py` + `plan_rb1.py`, `tools/runsheets.py`
(sheets + automatic single-frame pop scan), `tools/ab_gif.py`. In-engine run `rb1` (cgame 4e7aaae2, game 55686351):
0 script errors, pop scores <= 0.3 (none). GIFs: `G:\mohaa-reloadauth\gifs\`.

| group | status | mod |
|---|---|---|
| 1 scoped bolt rifles single-round | done | f742cd3a |
| 2 Webley Mk VI break-top | done | 42cc8d19 |
| 3 M1 Carbine box magazine | done | a0a99baf |
| 4 Lewis pan (+ DP-28 pan, audit correction: its pan never left the gun) | done | ad10f762 |
| 5 Beretta M38 hold | no change: identical to the TA Moschetto hold in engine (same skeleton + world anims; MP40/Thompson hands looked the same) | - |
| 6 drums: Thompson 50rd, 1928 Tommy, MP18 snail drum | done (rb2 found a one-frame drum flicker -> overlap rule, fixed in rb3) | 404acd73 |
| 7 Mauser C96 (+Trench) stripper clip from the top | done; bolt does not move yet (mesh has no bolt bone - ADS agent's split will be keyed over f12-21 / f51-56) | 806b0cf5 |
| 8 M1919 + MG42 belt reloads, opening top cover | done (mesh: new 'cover' bone, tools/beltgun.py) | 12e9faf6 |
| + revolver spent cases (user add-on) | done: Webleys at the break-open, M10 at the ejector rod, Nagant one per round (already) | 05d1d236 + engine fcbfbb81 |

### Phase B notes (groups 4-8)
- **Thompson drum side**: period sources found (the 1928A1 manual, FM 23-40 references, auction/collector texts) say
  the drum is slid in "from the side" in receiver guides with the bolt back, without naming the side; the reload
  slides it out to the shooter's LEFT (the side the left hand works). Flagged for the user.
- **Overlap rule for every prop swap** (from rb2): the gun hides its part 2 frames AFTER the prop appears and shows it
  2 frames BEFORE the prop goes, with the hand still at the gun - one shared frame gave a one-frame drum flicker.
- **MP18**: the high snail drum keeps the gun low while it is handled (the MP40 donor dips it too); feed direction
  reads correctly, but the gun is partly out of view 1.0-1.5 s. Candidate for a hand-keyed polish pass.
- **M1919**: the box stays on the gun; there is no separate belt prop (its belt is part of the box mesh) - the hand
  lays the belt across the tray. MG42: the belt end is a prop.
- **Belt meshes**: `30calportable/30cal.skd` and `mg42portable/mg42.skd` are now mod overrides of the xw meshes (one
  extra bone; cover triangles 60 / 5, vertices duplicated 30 / 9). Any later mesh work on these guns starts from them.
- Engine: fcbfbb81 coop_ejectcases (spent cases). GIFs: `G:\mohaa-reloadauth\gifs\` (g4_lewis, rev_cases_webley,
  g6_drum_tommy1928, g7_c96, g8_m1919, g8_mg42; each < 20 MB; the C96/belt "before" halves are offline previews,
  those guns were never captured with their old reload in engine).

## PHASE B polish (2026-10-05, user: "make the hand animations smoother and look like they are actually working the mechanisms", "remove ammo box for 30", "hands bending all weird", "not funky/robotic")
Every phase B magazine / belt reload is now HAND-KEYED (`tools/keyclip.py` + `tools/recipes_keyed.py`), not a re-timed donor:
- **Moving parts on one timeline** with the hands (`tools/beltsched.py` belts, `tools/swapsched.py` drums/Lewis/C96): the
  gun's world reload moves its cover / charging handle / bolt (`tools/beltgun.py`, `tools/worldanim.py`) on exactly the
  frames a hand is on it; QA measures hand-to-part distance every moving frame (ads_bolt handle_qa measure, <= 2.5 u).
- **Natural arms** (`tools/natik.py`): hinge elbows (the borrowed IK bent elbows sideways up to 90 deg - retail 0), the
  elbow swivel chosen over the whole clip (Viterbi) to keep the wrist in range, the elbow trailing the hand by about a frame;
  exact idle arm at both ends.
- **Joint-limit QA** (`tools/jointqa.py`): geometric wrist flexion / deviation (window centred on the retail reload range,
  half-widths 70 / 60 / 40), elbow off-hinge > 5 deg, forearm twist > 25 deg/frame, fingers bent back / sideways - every
  frame. Final: 0 frames over on M1919, MG42, Thompson 50rd, 1928, MP18, Lewis; C96 one 38 deg/frame turn at f7 while the
  hand is still below the frame edge (pitch -50 deg).
- **Life**: eased pchip / slerp keys, fingers curl over ~4 frames (outer joints a frame behind), a slow breathing drift of
  the gun, damped kicks where a hand strikes or a part slams home (cover slap, bolt home after a pull, drum / pan smacked in,
  rounds stripped).

| gun | what the hands do now |
|---|---|
| M1919 | finger on the latch f13, fingers under the cover's rear edge lift it (f15-20), flick to 75 deg, belt end pinched out to the left, a SHORT LENGTH OF BELT (prop `coop_belt_30cal.tik`, no ammo box - the crate surface is dropped from the mesh) laid on the tray and seated, palm shuts the cover, right hand pulls the charging handle twice |
| MG42 | right hand cocks first (pull + push), latch, cover, belt prop, cover shut |
| Thompson 50rd | left hand pulls the top knob back f11-16 (its Bolt bone follows - `Thompson/coop_tommy50_reload.skc`), drum slides out left f24, full drum in f60, smack |
| 1928 Tommy | drum only (the mesh has no bolt bone) |
| MP18 | drum off its sleeve and back, gun raised 1 u (no longer sits low), left hand keeps the gun by the drum while the RIGHT hand hooks the right-side handle (Bone2, `coop_mp18/coop_mp18_reload.skc` rebuilt at 1/30 s) f52-57, it flies home |
| Lewis | pan lifted off its post, full pan lowered with a 20 deg turn to lock, smack (prop f28-60) |
| C96 (+Trench) | pistol lowered 2.5 u and canted 35 deg; hand over the top palm down: bolt ears back f13-18, full clip into the guides f41, thumb strips the rounds f42-44, empty clip pulled f47-50 and tossed |

DP-28 and the revolvers (Webley, Webley Mk VI, Nagant, M10) keep their author / retail clips (not re-keyed).
In-engine runs: rb4 (first keyed pass: C96 hand floated palm-up beside the pistol, MP18 right hand palm-up, M1919 flick
threw the hand into the view), rb5 (fixed those), rb6 (natural IK + life: the swivel put the right elbow up and its sleeve
across the camera -> elbow-down / near-eye / gun-arm-in-view costs, forearm-twist continuity in the Viterbi), rb7 (all
guns; reviewer: M1919 snapped at the end - the right hand's return ran past the clip end - and its handle hand looked
open; Lewis pan at the frame edge), rb8 (handle gripped with wrapped fingers and back 3 frames before the end, Lewis 1.5 u
higher). Mod commit 6cf61e58. GIFs `G:\mohaa-reloadauth\gifs\polish_*.gif` (before = last committed version). Tools added this pass: keyclip, recipes_keyed,
natik, jointqa, swapsched, worldanim; `runsheets.py` ALL=1 writes every-frame pages.
