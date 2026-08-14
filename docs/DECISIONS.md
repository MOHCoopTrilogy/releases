# DECISIONS — what was chosen, why, and what was rejected

Each entry: the choice, the reasoning, and — where it exists — **the road not taken**, which is
usually the more useful half. Anchors are bug ids or `file:line`.

## Index

[Architecture](#arch) · [Engine vs script](#engine-vs-script) · [Renderer](#renderer) ·
[Assets & content](#assets) · [Build & release](#build) · [Process](#process) ·
[Rejected outright](#rejected)

---

<a name="arch"></a>
## Architecture

### Coop init runs synchronously in one frame
**Chosen:** every coop-integrated map calls `waitthread coop_mod/main.scr::main` as its **first**
statement, and that thread completes the entire ~50-step init before yielding. `wait` and `waitframe`
are **forbidden** in or before it.
**Why:** map scripts immediately proceed to vanilla setup and `level waittill prespawn`; anything
coop-dependent that ran later would race. `level.coop_mainScriptLoaded` gates downstream consumers,
with `waitForMainScript` for anything that must be sure.
**The cost, discovered later:** `coop_weather_init` is threaded from inside `main.scr::main`, but maps
set `level.coop_weatherTheme` on the **next** line — so the theme always read NIL and the feature
never fired. Fixed by waiting for prespawn inside the thread. **Anything the map configures *after*
calling main must not be read *during* main.**

### Per-player state lives in `self.flags["coop_*"]`, not new entity fields
**Why:** no engine change needed, survives the script/engine boundary, and avoids colliding with
engine-registered `Actor` property names. That collision is a real failure mode: vanilla
`attack.scr` assigned `self.aipronechance`/`self.aicrouchchance`, which are **engine-registered
read-only stub setters**, producing hundreds of "Cannot set a read-only variable" plus
incompatible-type comparisons that corrupted the AI attack state machine (Germans aiming at the
ground). Renamed to `coop_`-prefixed vars at 9 sites.
**⭐ General rule that came out of it: any `self.<name> = X` in coop scripts must avoid
engine-registered property names.**

### The bindable-command bus is a name-append channel
**Chosen:** a keypress appends a marker to the player name; `manageNamechange` extracts it;
`playerNameCommand` dispatches.
**Why:** it needs no new usercmd bits (there is exactly one left — see below), no new network message,
and it works for remote clients with no engine change.
**⭐ And it is the only way to reach cheat-flavoured actions at all:** the cheat gate is
`Entity::CheckEventFlags`, reachable only from the console/clientcommand path, and `sv_cheats` is
latched off on a coop listen server. So `self noclip` **must** route through script, never a direct
keybind.
**Known cost, accepted:** one token per name change, so pileups lose later tokens.

### ADS moved to its own usercmd bit — and that was the last one
**Chosen:** `BUTTON_COOPADS` = bit 13, freeing secondary-fire so the vanilla rifle-butt **bash**
(which the AIM state had shadowed) works again.
**⚠️ HARD CONSTRAINT this creates:** `usercmd.buttons` is 16-bit and bit 13 was the **last free bit**
(12 = `BUTTON_COOPWALK`, 14 = `BUTTON_ANY`, 15 = MOUSE, 7–11 = weapon commands). **A second custom
button requires a protocol change.** This is why the bipod design deliberately reuses RMB rather than
asking for a bit.

### The objectives panel was retired in favour of the URC menu
**Chosen (2026-07-12):** `coop_objPanel 0` is the autoexec default; wrapping is done **server-side**
into `coop_oN` + `coop_oNb`.
**Why:** the user saw both displays at once and called it "obnoxious." Side objectives also moved off
slots 7/8 onto dedicated `coop_so1`/`so2` cvars after a hard collision with e3l2/m4l2 primaries.
**Road not taken:** keeping the script-drawn panel as an option — rejected as one more thing to keep
in sync.

### Prefer a reconciling sweep over patching call sites you do not own
**Chosen (bug-1212):** the bullet-sponge fix (`nolongpain`/`enablepain` left set by retreat scripts)
was implemented as **one self-healing reconciliation sweep** folded into the existing 1.5 s
`coop_reinf_brain` loop, rather than N per-site patches.
**Why:** some offending sites live in **retail scripts the mod does not ship**. A sweep also
self-heals when a new retail path is discovered. **Good architectural precedent for this codebase.**

---

<a name="engine-vs-script"></a>
## Engine vs script

The recurring question is *"can this be done in script, or does it need the engine?"* The answers are
not intuitive.

### Script was enough (and the engine change was the wrong instinct)

- **Signal smoke stripping German grenades.** Not a TIK problem: the smoke was a **world `Weapon`
  entity**, so pickup hit `PickupWeapon`'s MP grenade-class branch, which forces grenade reselection
  and drops the player's other grenade-class weapon. Fixed purely in script — spawn a `script_model` +
  `trigger_multiple` and give via `item` (the giveItem path), which never enters that branch. The
  `removeAdditionalStartAmmo` theory was a **red herring**.
- **Destroyable-objective failsafe.** Rather than change how objectives complete, poll the target and
  fire the box's own `BlowUp`, which runs the full canonical wreck/FX/damage/objective sequence.
- **Officer heal-retreat.** `waittill movedone` never fires cleanly when the actor takes pain — so poll
  and re-issue `runto` instead of waiting on an event that may never arrive.
- **m1l1 truck actor anims.** A retail asset defect (duplicate-channel `guy01` clips) worked around at
  **script** level by using `truck_idle_guy02`/`truck_twitch_guy02` (`maps/m1l1.scr:341`, bug-1162) —
  not by editing the asset.

### The engine was genuinely required

- **Blast tinnitus behind cover.** A pure-script fix is impossible: `RadiusDamage`'s sight trace means
  zero damage = **zero script signal**. The engine now stamps `coop_blastPing`.
- **Lobby input.** `Player::TickCoopLobbyInput` reads A/D/F straight from usercmd so remote clients
  need no binds.
- **Armory clickability.** Stacked `enabledcvar`-gated Buttons were unclickable because
  `FindResponder` hit-tests in reverse file order checking only `m_visible`. **The armory requires
  that exe** (bug-587).
- **Overhead officer icon.** Vanilla draws the team icon only for `ET_PLAYER` and only same-team — and
  **there is no script access to this system at all.** But `EF_AXIS` is already set on every German
  actor's entity state every frame, so it was a ~40-line **cgame** edit with zero fgame changes.
- **Solid vehicle riders.** Required both damage-immunity changes and
  `cg_predict.c::CG_LockRiderOriginToVehicle` — the rider's view was being interpolated independently
  of the vehicle.

### Reuse what the engine already computes

- **Suppression FX** reuses the engine's own bullet ZING closest-approach computation, which already
  excludes the first/last 128u of flight — and therefore excludes your own outgoing shots for free.
- **3P free cam** rides `cgi.get_camera_offset()`, which returns a live `float*` to FAKK-era globals
  nothing else writes = a **zero-ABI client→cgame bridge**.
- **Auto-reverb** was **already built in the fork and forgotten** (`coop_autoReverb` default 1); the
  only blocker was `s_reverb` defaulting to 0.
- **Visible holstered weapons**: EA shipped the complete system and disabled it with comment slashes —
  79 retail TIKs have commented `holstertag`/`holsteroffset` lines.
- **`CarryableTurret`/`PortableTurret`** ship complete in retail maintt pak1, so a deployable .30cal is
  wiring, not new engine work.
- **The MP hitmarker** is disabled at retail only because alias `dm_hit_notify` points at `null.wav` —
  one alias line restores it.

**⭐ The methodology this crystallised into (now in CLAUDE.md): before designing any coop fix for a map
feature, find how a confirmed-working map or the vanilla scripts already handle it, and copy that
exact recipe.** Grep `maps/`, `global/`, `coop_mod/` first. The original devs usually solved it
(`scene2::KFiveInit` for entity replacement, `vehicles_thinkers::truck_load` for crews, `autotruck`'s
own loopsounds instead of the engine's flapping vehicle-sound state machine). **Only invent when the
search comes up empty.**

---

<a name="renderer"></a>
## Renderer

### gl1 ships; gl2 develops in a fully isolated install
**Chosen:** `cl_renderer` defaults to `"opengl1"` (`cl_main.cpp:3231`). gl2 lives at `G:\mohaa-gl2` —
its own `main`/`mainta`/`maintt` (junctioned to the same real game data, so mod content is
intentionally shared), its own binaries, its own **two** homepaths (`home`, `home_test`), and
`PLAY-GL2.bat` pinning `fs_basepath`, `fs_homepath`, `cl_renderer opengl2`, `com_target_game 2`,
resolution, `developer 1`, `logfile 2`.
**Why the batch file forces latched graphics cvars on the command line:** applying them from the
in-game menu triggers a `vid_restart` that **crashes** under gl2 (recorded in the batch file's own
comments).
**Why isolation at all:** bug-1172 — every `build.ps1` run during a gl2 sandbox session pushed
sandbox-only `MAX_SOUNDS 2000` / `MAX_ENTITIES 4095` / `MAX_TIKI_ALIASES 8192` binaries into the
user's **real install**. `MAX_ENTITIES` in `renderercommon/new/tr_types_new.h:33` still reads 1023
from that emergency revert, even though the analysis proving it could be raised was independently
verified correct.
**Refinement worth keeping:** only **cross-binary protocol** constants can corrupt a mixed set;
renderer-local constants cannot.

### Never trigger a renderer restart from inside a menu
`REVERTED` · *bug-1181, bug-1177* — enabling Ambient Occlusion and pressing APPLY closed the game
instantly: `0xC0000005` in `renderer_opengl2.dll InitShaderEx+0xE7`, stack `UIFont::CheckRefreshFont`.
**Not the SSAO code — the crash never reaches it.** The cause was `ui_checkrestart` added to the APPLY
button so a latched toggle would apply immediately: that issues `vid_restart` **from an open menu**,
and gl2 tears down and re-initialises while UI fonts are live. Reverted to plain `popmenu 0`, AO row
relabelled "Ambient Occlusion (needs vid_restart)", archived `seta r_ppSSAO` forced back to 0.

### Drive GL through the engine's state cache, never raw `qgl*`
**Chosen:** everything in `tr_postprocess_gl1.c` goes through `GL_State`/`GL_Bind`.
**Why:** raw `qgl*` calls desync the engine's `glState` **cache** — the root cause of two failed post-FX
attempts. `glPushAttrib` is **unlinkable** in this DLOPEN renderer.
**Related:** the 3D→2D hook **must** live in `Set2DWindow` (`tr_draw.c`), not `RB_SetGL2D`, because
cgame enters 2D via the exported `re.Set2DWindow` directly. Consequence: anything added to
`RB_PostFxApply` is automatically HUD-safe.

### Fix the render-state cause, not the draw order
**bug-1140 (framebuffer ghosting):** `tr.renderFbo` persists across frames, so a frame with **no scene
submitted** (fullscreen menu) still shows the last 3D content. The fix was a **first-2D-draw clear**
(`R_Ensure2DClear`), not a draw-order change.
**bug-1144 (gun over menus):** menu quads were being **depth-REJECTED**, never mis-ordered. Same
instinct, same correction.

### Real shadow mapping was deferred; decal shadows shipped
**Chosen:** Phase A = one elongated azimuth-rotated shadow decal per entity, with the renderer
publishing each map's **real** sun direction so shadows follow the map automatically.
**Why:** shipped and user-approved for a fraction of the cost. ⚠️ Marked **"do NOT re-implement"** — it
was nearly rebuilt from scratch once. Phase B/C is not started.

### Two gl2 defects were deliberately left unfixed
See [TRAPS.md § T13](TRAPS.md#t13). `bug-gl2-decal-red-dds` and `bug-gl2-viewmodel-over-menu` were left
open rather than risk regressing 2,370 working DDS textures / working HUD-over-3D compositing. **These
are among the most disciplined entries in the whole record.**

---

<a name="assets"></a>
## Assets & content

### Brush surgery replaced regional clip-strip zones
`REVERTED → replaced` · *bugs 938, 942, 946, 951; `cm_load.c:856`*
The e1l2 invisible-wall hunt is a four-round worked example of **narrowing by species**:
1. 33 `trigger_landmine` entities were `damageable=1`, and `SetDamageable(true)` calls
   `setContentsSolid` — every armed mine was an invisible solid box. → `CONTENTS_WEAPONCLIP` (still in
   `MASK_SHOT` so shooting mines works, movement passes through, stepping on one still detonates).
2. The 15cm artillery TIK ships `setsize (-80 -80 0)(80 80 80)` and stays SOLID → tightened to
   (-48 -48 0)(48 48 80), cutting 56 blocked grid segments to 20.
3. A **regional** playerclip strip via `coop_clipStripZones`.
4. **REVERTED (3)** — region stripping is **wrong-grained**, because boundary clip and phantom-wall
   clip coexist in the same regions, so it let players clip out of bounds.
**Replaced by:** `cm_load.c` reading `cmpatch/<map>.txt` from the pak and zeroing **listed brush**
contents. ⭐ Critical detail: **the SERVER loads `maps/<name>_sml.bsp`**, so the suffix must be
stripped. New wall reports are now pak-only fixes.

### When a shader name is contested, stop fighting for it
`bug-922`, closing a 5-round saga. **Mint a NEW shader name existing only in the coop pak, pointing at
a PRIVATE texture path also existing only in the coop pak, and retarget the `.tik` surface.**
**Why:** shader-NAME overrides lose the reverse-concat race; whole-FILE overrides win because the
filesystem dedupes by filename and the coop pak mounts last.
⭐ **Diagnostic tell:** if a "black" surface shows per-face **shading**, a lit default shader is drawing
it and your identity def is not reaching that surface at all.

### Ship DXT `.dds` overrides rather than disable texture compression
**Why:** `R_LoadImage` rewrites the extension to `.dds` and tries `LoadDDS` **first** whenever
compression is on, so a same-basename stock `.dds` always beat the HD `.jpg` — 881 upscales were dead.
**Road not taken:** disabling `r_ext_compressed_textures`, which would make ~1400
stock-`.dds`-only textures vanish. Chosen instead: `zzzzzzz_dds_override.pk3` (872 DXT `.dds`, 485 MB)
with full mip chains.

### ESRGAN is for photos and text, not chrome
**Evidence across three incidents:** a hallucinated worm-noise upscale of `m3l3grass_bocroad_new` won
via the shader remap (bug-1129); a GPU-corrupted fully-black upscale of `netgame_a/b` shipped and
blanked the server browser (bug-247); a 2× pass swept in **29 vanilla** menu textures and the
overrides had to be removed so the engine could fall back to stock (bug-157).
**Decisions:** brightness-check upscale outputs before commit; validate on sustained runs (the GPU
corrupts); and **never upscale a bitmap font** — it invents detail and produces uneven stroke weights.
The @3x atlases were regenerated by rendering a real vector font (Bahnschrift) into the existing cell
rects (bug-1185).

### Generated-asset intensity needs a per-round user checkpoint
`REVERTED` · *bugs 795, 796, 817* — gore round 4 over-cranked everything (uniform heavy tier soaking
~60–75% of the cloth, 2–4 drench blobs, 14–20 patches, spray/smear cast-off, a measured-coverage
top-up loop). User verdict on the shipped build: *"dial the blood back… put it to what it originally
was, now it's way too much."* Reverted to the moderate earlier coverage; spray/smear primitives and
the coverage loop removed entirely.

### Assertion gates, not review, for generators
**Why:** review never held. Every generator corruption ([TRAPS.md § T2](TRAPS.md#t2)) was a tool
writing project data. What worked: balance asserts, zero-stale-ref asserts, count asserts
(`assert NS == 76`), and bug-1009's connectivity flood-fill gate. **Make the generator fail loudly.**

### The imported-weapons pak is deliberately standalone
`zzzzz_xw_weapons.pk3` is **not managed by `build.ps1`** and overwrites nothing vanilla or coop.
**Why:** 18 net-new guns with unique names/weapontypes/weapongroups, isolatable and removable.
**Accepted cost:** source lives at `C:\mohaa-coop-dev\_xw_weapons\` — untracked, outside both git
repos — with its own hand-rolled `_pre_<feature>_bak` chain, and `publish_release.ps1` stages it from
the **deployed** maintt copy, so source and shipped artefact can silently diverge.
**⭐ The rule this produced:** the TIK `rank <order> <power>` **first** number is a GLOBAL weapon-select
slot shared across weapontypes. Every import had copied its parent's order, so only 39 of 71 guns were
reachable (bug-494, found in play). **Any future import must get a unique order.**

---

<a name="build"></a>
## Build & release

### Three paks, not one, and a deterministic packer
**Chosen:** `assets_snd` / `assets_tex` / `code`, ASCII-sorted so `code` mounts last and overrides.
**Why deterministic** (sorted entries, source-file mtimes not build time, git files excluded, an input
digest that skips unchanged buckets): **the auto-updater compares each pak's sha256 to the manifest**,
so non-determinism breaks updates (bug-237).
**Why the running-game abort:** the engine memory-maps the paks; overwriting mid-session makes it read
garbage at stale offsets → phantom "label does not exist" errors and a watchdog server crash
mid-playtest (bug-241).

### Releases stage binaries from the deployed install, not the build tree
**Chosen (`publish_release.ps1:48-55`, v1.1.51):** all five engine binaries come from `$gog`.
**Why:** a `--clean-first` rebuild would ship binaries nobody has played. **The artefact is exactly the
tested set.**
**The cost, accepted knowingly:** there is **no recorded mapping from a shipped `openmohaa.exe` back to
a commit** — and given ~10,750 uncommitted engine lines, there could not be one. Reproducible-from-
source is deliberately traded away.
**Guardrails that do exist and work:** refuses to overwrite a published tag; verifies every staged path
exists before hashing; refuses to publish if `latest.json` already carries the version, and prints the
restore command.

### `coop_defaults.cfg` exists because `autoexec.cfg` cannot hold defaults
**Chosen (bug-710):** a new cfg exec'd by an engine hook in `common.c` **before** the saved player
config.
**Why:** the engine execs `default.cfg` → saved config → `autoexec.cfg` **LAST**, so ~200 curated
`seta` lines in autoexec overwrote every menu-changed setting on every launch. Values in
`coop_defaults.cfg` are true defaults a menu change overrides and persists.
**Migration incomplete** — see [OPEN.md § Config](OPEN.md#config).

---

<a name="process"></a>
## Process

### The code wins over the record
**Established by bug-1184.** A `+180` roll correction documented as applied (bug-1173) was reverted
hours later as an unverified guess. Both entries are correct; the failure was reading the first and
stopping.
**⭐ The habit that fixes it: leave the correction AT THE SITE.** `maps/m1l1.scr:1683` carries a
six-line in-code revert comment naming bug-1184. `coop_mod/loadoutpick.scr:436-440` does the same for
bug-1205. `qcommon/q_shared.h:1690-1755` does it for the whole `MAX_SOUNDS` constraint family. **All
three survived contact with a later session.**

### Turn rules into build breaks
**bug-1198:** the `sound_index` 11-bit rule existed **only as a comment**. It is now
`#define SOUND_INDEX_BITS 11` + `#if MAX_SOUNDS > (1 << SOUND_INDEX_BITS) #error`.
**Decision: do this for every capacity constant.**
**Corollary (bug-1186):** when you fix a silent-discard branch, **add the warning even though you also
raised the limit** — `sv_snapshot.c:549-553` now names the constant to raise.

### Measure first; do not guess condition semantics
Recorded verbatim for bug-309 and honoured for bug-1213 and `bug-gl2-decal-red-dds`. When a mechanism
is unexplained in a high-blast-radius subsystem, **the correct deliverable is a decisive gated
diagnostic, not a fix.** See [TRAPS.md § T13](TRAPS.md#t13).

### Verify a fix by A/B with a pre-fix binary
**bug-1144's method, worth copying:** a pre-fix DLL was built by disabling **only** the new branch,
both DLLs kept, and the deployed file swapped between runs. That is what makes a renderer claim
credible.

### Budget 2–3 fix→re-sweep passes for script storms
**Because storms are sequential:** fixing one class lets maps progress further and exposes the next.
**A clean sweep after one fix means nothing.** See [TRAPS.md § T5](TRAPS.md#t5).

### Verify a claimed script command against engine source before it lands
**bug-298 and bug-1067** both shipped a script command that exists nowhere in the engine
(`player userinfo`, `getcurrentdmweapontype`), parse-killing a whole file each time.

### Separate "it broke" from "the user changed their mind"
Only the former is a lesson. bug-787 reversed a locked-cosmetic design pre-release at the user's
request after two full generator rewrites; nothing was defective.

---

<a name="rejected"></a>
## Rejected outright — roads not taken

| Rejected | Why | Anchor |
|---|---|---|
| **True skeletal ragdoll / Bullet physics** | No solver, and the skeleton is anim-only. Verdict: **not feasible**; Bullet is a "don't." Corpse blast impulse shipped instead as the cheap win. | `physics_research.md` |
| **Decals on skeletal models** | **Impossible** — `R_MarkFragments` walks world nodes only. Gore uses skin-bit texture tiers + bone-attached props + renderer UV wounds instead. | `player_gore_research.md` |
| **The deployables skill tree** (6 branches / ~36 nodes) | User verdict 2026-07-13: *"Not a big fan… do not build mine"* — they are building their own model. Doc kept, marked superseded. | `skilltree_plan.md` |
| **Turret-swap approach to bipods** | Rejected in favour of a weapon-stance supported aim (`Player::TickCoopBipod`), ~250 LOC, no new usercmd bit / PMF / stat. | `bipod_design.md` |
| **Runtime `SplinePath`/`flypath` for the bombing run** | Deliberately not used, to avoid a static-plane risk — even though it is what makes m3l2's bomber look good. **Remains the recommended upgrade.** | `plane_bomber_research.md` |
| **Regional playerclip strip zones** | Wrong-grained: boundary clip and phantom-wall clip coexist in the same regions, so stripping let players out of bounds. Replaced by per-brush surgery. | bug-951 |
| **Disabling `r_ext_compressed_textures`** | Would make ~1400 stock-`.dds`-only textures vanish. | `dds_shadowing_hd_fix.md` |
| **Server-side `fov`/`setfov` for ADS zoom** | Dead ends. A cgame `CG_CalcFov` zoom was used instead. | `ads_ironsight_port.md` |
| **Custom `viewmodelanim` tokens** | Silently fall through to idle — `Player::ViewModelAnim` accepts only a fixed set. The engine-recognised `charge` token was used. | `player.cpp:11696` |
| **Layering a torso weapon-hold over sprint** | **Structurally impossible.** Closed. The proper fix is a Blender re-authored anim. | `sprint_walk_stamina.md` |
| **Adding anim includes to individual model TIKs** | `MAX_TIKI_ALIASES` overflow risk. `$include human_thompson.tik` was moved into the **unconditional** block of `new_generic_human.tik` instead, which every allied model inherits — fixing ~1300 "unknown animation thompson_*" errors. | `sky_trace_and_airborne_anim_fixes.md` |
| **Fading the HUD via `m_alpha`** | urc `fadein` widgets re-pin it every frame. Used the post-Motion `SetHudFadeMul` instead. | `hud_fade.md` |
| **`popmenu;pushmenu` for Service Record tabs** | `MenuManager m_lock` drops the push. Tabs flip `enabledcvar` cvars instead. | bug-461 |
| **Notsolid vehicle riders** | ⭐ **SUPERSEDED HARD RULE — do NOT re-apply.** Riders are now solid and take real damage, enabled by the glue-immunity and view-lock engine fixes. | `t2l2_coop_seating.md` |
| **Warzone explosion variants; VFA wood footsteps** | User-rejected in play ("too cinematic/sub-heavy for close blasts"; "sounded bad in-game"). Artillery beds from the same library were **kept** — a separate judgement. | `audio_enhancements_research.md` |
| **`bsptransition` / `loadMap` / `leveltransition` on a live coop server** | Runs the persistant archive → crash. Use `stuffsrv "map <name>"`. | CLAUDE.md |
| **Re-enabling AI prone/crouch** | Reintroduces a **server crash** — `AttackCrouchDodge` spins into "Command overflow. Possible infinite loop." | `attack_scr_aiprone_fix.md` |
| **gl2 as the shipping renderer** | Not yet — 7 post-FX unported, several open defects, and `coop_defaults.cfg` ships `r_ppSSAO 1` which blanks the gl2 screen. | [OPEN.md § gl2](OPEN.md#gl2) |

### Reversed twice — decapitation
The clearest three-act revert in the record, and the one most worth re-reading before any gore work:

1. **bug-856/861** — shipped. User: *"the AI went all glitchy."* Pulled at user request. Exact cause
   never deep-investigated; the recorded lead was server-sim load (too many long-lived entities per
   blast death, no per-frame cap, under coop count-scaled hordes).
2. **bug-866** — re-implemented **safely** by copying the engine's own dead-body gib discipline
   (`Body::Damage`): dead-gated to the `ArmorDamage health<0.1` branch, **per-frame budget** (the key
   fix), one rigid non-`NewAnim`'d head prop, `EV_Stop` not `EV_Touch`, 4 s life, free wound-prop slot
   only (never an untracked attachment), precached on the spawn path.
3. **bug-892** — reverted from **SOURCE** anyway, so a protocol rebuild could not silently
   reintroduce it. Inert `.tik` assets kept. **Verified 2026-07-29: zero `CoopGoreTryDecapitate` /
   `HeadGibObject` symbols exist in `openmohaa-hzm/code/`.**

**⭐ The reason for the FIRST revert no longer holds.** The AI glitching was later attributed to the
entity-pool stomp (bugs 914–927, root-caused as `maxentities 2048` against `GENTITYNUM_BITS 10`
handing out slot 1022 repeatedly), which is fixed. **bug-866's safe pattern is the template for a
re-add** — and the memory topic `decap_safe_rebuild.md` was itself STALE and misled a later session
into assuming the code was present.

### Loading screens — single POT texture, new work only
The stock two-tile convention (two overlapping TGAs, e.g. `_1.tga` 1024x1024 + `_2.tga` 512x1024,
referenced by two `.urc` Labels) was traced to gl1's `Upload32` forcing every non-DDS texture to
power-of-two — the split exists purely to keep each tile already-POT so the forced resize is a
no-op, not because the renderer caps texture size or needs multiple images. Confirmed via
`renderergl1/tr_image.c`: `glConfig.maxTextureSize` is read straight from the driver (8192+ on any
modern GPU); `ResampleTexture`'s only real ceiling is a `2048` scanline-buffer cap that only bites
when a *non-POT* source rounds up past it. A single Label + a single exact-POT texture (e.g.
2048x2048) renders identically — `uiwidget.cpp`'s `Rend_DrawPicStretched` always stretch-blits
whatever it's given, tiled or not.

Also confirmed: the UI's generic shader lookup (`Rend_RegisterMaterial` → `RE_RegisterShaderNoMip`)
already forces `nomipmaps`/`nopicmip` on *any* menu graphic, named shader or not — that part needs
no fix. The one real gap: vanilla `mohmenu.shader` entries all set `force32bit` (locks full 8-bit
color regardless of `r_texturebits`/`r_colorbits`); a bare `.urc` path reference does not, so it
depends on cvar/driver defaults instead. Cheap to close — give the texture an explicit named shader
(`nomipmaps nopicmip cull none force32bit surfaceparm nolightmap`, matching every stock UI shader)
instead of referencing the raw path.

**Decision: apply this (single POT texture + explicit force32bit shader) to new loading screens
going forward; do not retrofit already-shipped ones (e3l4_arena, main.urc, etc.) — user call, "new
work only, for now."** First applied to m1l1 (`scripts/coop_loadscreens.shader` → `coop_load_m1l1`,
2048x2048, replaces the old `m1l1_1.tga`/`_2.tga` pair).

### Reviving downed allies will become a MEDIC-class ability

**Now:** any player can revive a downed ally by standing over them (`coop_mod/allysquad.scr`), and it
pays 5 XP in the existing `"revive"` category — half what reviving a *player* pays (`dbno.scr`, 10),
because an ally is worth less than a teammate but the save should still register.

**Intended future state (user, 2026-08-08):** once the skill tree lands, a **medic class will be the
only class able to revive downed allies.** Recorded here rather than built, because the skill tree
does not exist yet and gating on a class that cannot be selected would make the feature unreachable.

**What this constrains, so the later change stays cheap:** the revive check lives in exactly one
place — the proximity test inside `ally_go_down`'s bleed-out loop. Gating it later means adding one
class test at that site, not unpicking a system. Deliberately avoided: spreading revive eligibility
across the marker, the XP award and the announcement, which would have made the medic gate a
multi-site edit. Related: `skilltree/WEAPON_UNLOCKS.md` (weapon unlock chains), and note the earlier
decision that a *deployables* tree was rejected — the medic class is a role gate, not a deployable.

## Dedicated/listen parity is a REQUIREMENT, not a nice-to-have (user, 2026-08-10)

> **"anything that works on a listen server needs to function on dedicated for our entire mod across
> the entire trilogy"**

This is a standing acceptance criterion for every feature, on every map, in all three games - not a
property of the two features that happened to expose it. Treat a listen-only behaviour as a defect.

**Why it needs saying.** Coop grew up on a listen server, so "it works" has historically meant "it
works when the host is also a player". Three distinct things broke the moment a dedicated server was
actually used, and none were caught by any static check:

- **bug-1664** - dedicated never ran its command buffer at all (`Cbuf_Execute(0)` could not retire a
  `wait N`), so the server booted to silence and no map ever loaded.
- **bug-1667** - `timeBeginPeriod` was inside `#ifndef DEDICATED`, so dedicated ran on the ~15.6ms
  Windows timer and quantised every 25ms frame to ~31.2ms.
- The host-is-a-player assumption itself: on a listen server the host's inputs are acknowledged
  instantly and `SV_Frame` is driven by the render loop (`common.c:2354`), so *both* the timing and
  the fairness picture differ from what remote players actually get.

**Practical consequences.**
1. A feature verified only on a listen server is **not** verified. The 2-player harness now defaults
   to dedicated (`launch_dedicated_2player.ps1`) for exactly this reason.
2. Anything gated on `#ifndef DEDICATED` in the engine is suspect by default - read it and ask whether
   a server genuinely does not need it. Timing, cvar registration and command processing all do.
3. Client-only code paths (cgame HUD, sounds, view effects) must be driven by state the **server**
   sends, never by something only a listen host happens to have locally.
4. Conversely a fix that only helps dedicated does not discharge the requirement either - bug-1667 is
   dedicated-only, and the listen-server "slow server" case has a *different* cause still open.

## Two Tier-1 performance items REJECTED after reading the code (2026-08-10)

`docs/proposals/server_topology_and_limits.md` T1.4/T1.5 REJECTED. Both were argued from a premise
that did not survive inspection. Recorded so they are not re-proposed.

**T1.5 - debounce challenge disk writes.** The plan called `challenges.scr` completion writes "a
kill-driven event". They are not. The write sits in `chal_grant`, which fires only when a challenge
COMPLETES - a rare, once-ever-per-challenge event - not on every `chal_bump`. Debouncing it to the
30 s flush would trade real durability (losing an unlock to a crash) for effectively no CPU saving.

**T1.4 medkit scan - replace the 2048-entity scan with the cached list.** The plan said the cache
exists "for this exact purpose". It does not match the same thing. `coop_scan_health_entities`
(`medkit.scr:522`) is built ONCE at map init (`main.scr:164`) and matches **four hard-coded model
names**; the live scan matches **`classname == "Health"`**. So the cache misses (a) any health entity
spawned after init and (b) any whose model is outside those four. Swapping them would silently stop a
downed player picking up a pack that works today - a gameplay regression to buy CPU on a server that
measures 25 ms mean against a 25 ms budget with 1-2 frames/sec over. If it is ever revisited, the
shape is a periodically REBUILT cache (bounded staleness), not the existing one.

**The general lesson:** the topology plan was strong on engine facts and repeatedly wrong about mod
script intent. Verify a script claim against the script before acting on it - three of its items
(these two plus the buildmode diff-gate, which was already implemented) needed no work at all.

## Blueprints are not placed on vehicle maps (user, 2026-08-14)

Collectible blueprints are being placed map by map across the trilogy. **Driving/riding maps are
deliberately skipped** — starting with the m5l2a/m5l2b King Tiger pair, and the same reasoning
covers the jeep maps (m1l3a, m1l3b) and any other on-rails stretch.

The reason is that a blueprint is a *search* collectible: you wander, look behind things, and
find it. On a map where the player is driving or riding a vehicle they cannot stop, dismount or
backtrack, a hidden pickup is not a discovery — it is a thing that slides past the window. Worse,
`collectible.scr` persists the found-set per player and a found blueprint never respawns, so a
missed one on a vehicle map is missed *permanently*, with no way to go back for it.

**So an empty vehicle map is correct, not an oversight.** Do not "complete the set" by adding
blueprints to them later — check this entry first. The trilogy total is therefore always lower
than "every coop map × N", and `check_challenges.py` counts what is actually placed rather than
assuming full coverage, so the bp_* ladder stays honest either way.

Rejected alternative: place them at the vehicle's start/end points so they are grabbable while
stationary. That puts the collectible somewhere the player is already funnelled through, which
makes it free rather than hidden — the opposite of what the collectible is for.
