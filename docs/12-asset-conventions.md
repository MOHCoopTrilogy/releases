# 12 — Assets: UI, textures, audio, models, fonts

---

## 1. The precedence layers between "the file I edited" and "the file the engine reads"

This codebase has **at least five** name-mangling / precedence layers. Always confirm which file
actually resolves before editing or A/B-ing an asset.

1. **Pak mount order** — `maintt` > `mainta` > `main` under `com_target_game 2`.
2. **Homepath > basepath** for identically-named pk3s.
3. **Alphabetical pk3 order within a folder** — `.` (0x2E) sorts *before* `_` (0x5F), so a stale
   `<name>_prefix_bak.pk3` **overrides** `<name>.pk3`. Keep backups **outside** `maintt`.
4. **`@3x` hi-DPI fonts** — `R_LoadFont_sgl` builds `<name>@3x` and prefers it if
   `fonts/<name>@3x.RitualFont` exists, then resolves the sheet as `gfx/fonts/<name>@3x.tga`.
   Replacing the plain `.tga` is a **silent no-op** (bug-1181).
5. **DDS shadowing** — the engine tries `.dds` before `.jpg`/`.tga`. But gl1's `LoadDDS` only
   accepts fourCC DXT1-5; `DX10` fourCC files are **silently rejected**, so for those the live file
   is the highest-priority `.jpg`/`.tga`. Verify bytes 84:88 before assuming a `.dds` shadows.

**Shader names are a race you usually LOSE.** `ScanAndLoadShaderFiles` concatenates shader files in
**reverse** load order and `FindShaderInShaderText` returns the **first** match — so the file that
*loads later* wins a duplicate name, and the high-priority coop pk3 is listed first, loaded first,
concatenated last, and **loses**.

> **Shader isolation recipe** (closed a 5-round saga, bug-922): when an override mysteriously loses
> despite passing every static check — **fresh shader name + private texture path, both existing
> ONLY in the coop pk3, retarget the tik.** Nothing can race what only we define.
>
> Diagnostic that cracked it: the "black" surface had **per-face shading**. An `rgbGen identity` def
> renders FLAT — so shading proved our def was never reaching the surface. **Rendering-behaviour
> evidence beats static file audits.**

`whowins.py` (scratchpad) resolves the FULL provider chain. Check it before designing any revert
experiment — a whole-file revert can undo three providers' work at once.

---

## 2. Shaders

- **A malformed `.shader` (unbalanced braces) DESYNCS the parser and breaks EVERY shader parsed
  afterward**, including unrelated HUD/world shaders → white squares. Always brace-validate a
  generated `.shader` before packing (bug-480).
- **Never introduce a new `gfx/fonts/*` or UI texture name without also shipping a shader def** —
  `R_FindShader`'s default shader is **opaque**, so text/UI quads render as solid black bars. Vanilla
  font body: `nopicmip` + `nomipmaps` + `{ map <tga>, blendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA,
  rgbGen identity }`.
- **`rgbGen lightingSpherical` renders solid BLACK when the model's normals are bad** (SH lighting
  integrates to ~0). Fix that ONE surface with `rgbGen identity`; don't blanket-change siblings.
- **A decal/shader that multiplies a near-black texture by a dark `rgbGen vertex` tint is invisible
  on every real floor.** If a mark must always read, **bake the colour into the texture** and render
  `rgbGen identity` (bug-754).
- **Blood/decal flicker = z-fighting.** Ship a uniquely-named shader with `polygonOffset`.
- You can **silence or redirect an engine-hardcoded shader lookup with DATA ALONE**, because
  `R_InitShaders` runs `ScanAndLoadShaderFiles()` **before** `CreateExternalShaders()`. Defining the
  name in any mod `scripts/*.shader` wins (bug-1207).

---

## 3. TIKI / models

- **Read the `.skd`, not the `.tik`, for surface names.** Retail player TIKs can name surfaces the
  referenced `.skd` does not contain (`allied_british_tank.tik` ships double-underscore names that
  don't exist in `SC_AL_BRIT_INF.skd`). Extract real names from the binary `SKL <name>` markers.
- **Any `.skd` surface with no `surface <name> shader <X>` line falls back to using the surface NAME
  as the shader** → no image → **WHITE**. This is the classic white-weapon-part cause.
- **TIKI skin caps**: `MAX_TIKI_SHADER` = 4 shaders/surface; `entityState.surfaces` carries 2
  SKINOFFSET bits = indices 0-3. The renderer clamps out-of-range to 0. `case` blocks are mutually
  exclusive, so additions in *different* case blocks never share the 4-skin budget — audit per site.
- **`weight` on an alias means RANDOM POOL**: numbered aliases collapse under the digit-stripped base
  name and the numbered names return −1. Reference the **base** name for a random pick; add a
  weight-free alias for deterministic playback. The TIKI loader **rejects** a `weight` alias whose
  name doesn't end in a digit (bug-260).
- **Alias lookup is dual**: `setmotionanim`/`anim` = exact match (miss → `UnknownAnim` ScriptError
  that kills the thread); `Anim_Random`/`HasAnim` = **prefix** match.
- **Alias availability is map-gated** — `new_generic_human.tik` has ~52 per-map `includes` blocks.
- **`anims_shared.txt` ends with a closing brace** — new aliases go **before** it, never appended at
  EOF (bug-306). Alias paths are **relative** to `$path models/human/animation`.
- **A weapon `.tik`'s `rank <order> <power>` first number is a GLOBAL weapon-select slot key.** Two
  held weapons with the same order overwrite each other in the wheel — the second is in inventory
  but unreachable. Every import needs a globally-unique order. Vanilla banks: pistol 110-160,
  rifle 210-280, smg 310-350, mg 410-430, grenade 5xx, heavy 6xx.
- **`attachmodel` paths are canonicalised** — the `models/` prefix is optional and idempotent. The
  offset is applied in the **target tag's LOCAL frame**, so a large offset on a rotating bone makes
  the prop swing. `attachmodel` to `Bip01 Head` forces `use_angles=true`.
- **Skeletal gear rigs must be MERGED as an extra `skelmodel` line** in the human TIK (retail's own
  pattern) — `attachmodel` is rigid and won't animate with the body.
- **Attached models replicate** (parent/tag_num/attach_offset are netfields), and `surface +nodraw`
  replicates too — both mechanisms are server-authoritative, so teammates see them.
- **Static-prop size offline**: parse the idle `.skc` frame-0 bounds (`skcFrame_t` at header offset
  48) × the tik `scale`. **Only trust SKC version 13**; v14 has a different layout and reads garbage.
- **`md5_2_skX`** (`code/tools/md5_2_skX/`) converts Doom3 MD5 ⇆ MOHAA `.skd`/`.skc` — no 3ds Max
  needed. Gotchas: it hardcodes a −90 X roll on every root bone (author the md5 at that convention);
  it writes `ofsCollapse=0`, which the engine ingests as garbage LOD data → **crash at model
  registration** (fix: `skd_add_collapse.py`); `-decompile a.skd b.skc` without a `.tik` **segfaults**.
  Validate every conversion with `shapekit/skx_validate.py` before install.

---

## 4. UI (`.urc`)

- **`.urc` files end with `end.`** — resources appended after it are **silently ignored** and the
  menu renders normally otherwise, so the failure is invisible.
- **The parser SILENTLY DROPS single-line resource blocks.** Every field must be on its own line.
  No parse error is logged (bug: coop_settings "empty folder").
- **NEVER override a stock URC menu by shipping a same-named menu decl** — the loader creates a
  separate `Menu` object per container with **no name dedup**, and the stock menu draws underneath.
  Gate coop-only changes with two inverse cvars (`coop_active` / `coop_mpmenu`) instead (bug-720).
- **An unregistered `font "…"` in ANY `.urc` is a FATAL startup crash** — all menus are parsed at UI
  init. Use only **`verdana-12`**, **`verdana-14`**, **`facfont-20`**, **`courier-16`** (bug-519).
  `courier-16` is deliberately left monospace — the coop menu pages depend on column alignment.
- **URC Labels do NOT word-wrap.** A too-long `title` centres on the rect and overflows **both**
  sides off-screen. Split into stacked short Labels (~40-48 chars at verdana-12).
- **Menus do NOT auto-flow.** Adding rows does not push the button strip down; the button rect, the
  background widget rect, and the declared `menu NAME W H` height must all be moved manually.
- **`popmenu 0; pushmenu X` in ONE command can NEVER switch menus** — `PopMenu` sets `m_lock` and
  `PushMenu` bails on it. For tabs, use ONE menu with N pages gated by `enabledcvar` view cvars
  (bug-461).
- **`FindResponder` hit-tests in REVERSE file order.** Any widget overlapping an interactive one
  steals its clicks if defined later — define Labels **before** the Buttons they sit under. This
  fork also patched `FindResponder` so cvar-gated-off widgets are click-transparent, and so
  late-enabled widgets hit-test by `isEnabled()` rather than `m_visible` (bug-587, bug-593).
- **`enabledcvar` (including `!cvar` negation) is base-`UIWidget`** — works on everything.
- **`rendermodel 1` + `linkcvar` + `rendermodelfit 1`** = live 3D preview framed by the model's real
  bounds. With `fit 1`, `modelscale` self-cancels; keep `modeloffset "0 0 0"`. `modelangles` 3rd
  component is ROLL — upright weapons need `"0 90 180"`. **Framing values are EMPIRICAL** — tune
  against a live screenshot, never derive from the bounds math (bug-594).
- **URC menus must be self-sufficient when opened by a bare `pushmenu`.** One `open.cfg` (init +
  pushmenu inside) + a negated default gate (`enabledcvar "!cvar"`).
- **A menu can't compute anything** — disconnected-menu "live" progress = archived cvars only, pushed
  by the server via `stufftext "seta …"`.
- **APPLY runs `ui_checkrestart`**, which only fires `vid_restart` for **latched** cvars that a
  widget in the current menu `linkcvar`s and whose value changed. Multi-cvar popups need a hidden
  1×1 `linkcvar` Label per cvar. **Never do this on gl2** (see [11](11-engine-conventions.md)).
- **`ui_clickdebug 1`** is the engine click tracer — first tool for "menu clicks do nothing".
- **A briefing slide is a fullscreen UI menu drawn ABOVE the cgame HUD**, so `ihuddraw` is invisible
  during briefings. Draw into `ui/missionbriefingback.inc` instead.
- **Visible-but-off-stack menus are a LEGITIMATE pattern** (script `showmenu` = `ForceShow` with no
  stack entry). Never write a generalised "hide any menu not on the stack" sweep (bug-777).
- **`vid_restart` does NOT rescan `ui/*.urc`** — full teardown+rescan happens on every MAP CHANGE.

---

## 5. Fonts

- **RitualFont metrics are RESOLUTION-INDEPENDENT**: locations are design-space rects (256-wide,
  `v = y*aspect/256`) normalised to UVs at load. A higher-res sheet with the same proportional
  layout needs **zero** metric or `.urc` edits.
- **⚠️ The `.RitualFont` the engine loads may not be the one you expect.** `maintt/pak1.pk3` and
  `mainta/pak1.pk3` override `facfont-20` with their **own** version (height 14, aspect 1.0,
  256×256) — a completely different cell layout from AA's `main/Pak0` (height 16.94, aspect 2.0,
  256×128). Under `com_target_game 2` the **BT** one wins. Generating an atlas from the wrong pair
  garbles every glyph. Extract the winning `.RitualFont` by mount order and size the atlas from
  **its** aspect (bug-font-bleed).
- **A typeface swap is a RESKIN, not a re-metric** — advance widths stay the original's. A
  **condensed** replacement therefore reads gappy. Bahnschrift (DIN-style semi-condensed) matched;
  Oswald DemiBold did not. **Always A/B by composing real UI strings through the actual RitualFont
  metrics**, never by eyeballing the atlas.
- **Bebas Neue has no real lowercase** (lowercase codepoints map to uppercase glyphs). Check this
  before picking any display face.
- **Fitting a glyph into a fixed cell**: too tall → uniform scale; too **wide** → **horizontal-only
  squeeze**. Uniform-scaling an overwide glyph changes its baseline and renders as random letters
  looking superscripted mid-word.
- Vanilla `verdana-12/14`, `courier-16/18/20` and `marlett` atlases are **bilevel** (2 alpha levels,
  no antialiasing) — upscaling can never look good; re-render from the Windows TTFs.
  `facfont`/`handle`/`delima` are antialiased → alpha-aware premultiplied Lanczos works.
- **Stock atlases have ink touching cell edges in every font** — bilinear edge-sharing is
  stock-proven. Do not "fix" it with margins.
- **TGA layout**: vanilla MOHAA TGAs are a bare 18-byte header, descriptor `0x00`, bottom-up, no
  footer. PIL adds a TRUEVISION-XFILE footer and desc `0x08` — patch byte 17 to `0x00`.
  OpenMOHAA **warns and vertically FLIPS** top-down TGAs; ffmpeg `-pix_fmt bgra` outputs top-down, so
  add a `vflip`.

---

## 6. Textures / upscaling

- **ESRGAN corruption is CONTENT-SPECIFIC, not pack-wide** — chaotic straw/rut ground art grows
  crosshatch worms while sand/rock/grass siblings upscale cleanly. Verify per texture.
- **`realesrgan-ncnn-vulkan` silently produces BLACK output past ~18 images in a single-folder batch
  run** (exit code still 0). Fix: one process **per file** + a mean-brightness no-black gate. A
  4-file test does **not** reproduce it.
- It also produces **pure noise/black on tiny inputs** (<64px short side) — Lanczos pre-pad first.
- **Sustained batch runs corrupt outputs on this GPU** (227 files → 97 bad). Small batches (2 files)
  + 60 s cooldown + `-t 256 -j 1:1:1`, plus a validator (grayscale correlation < 0.65 = corrupt;
  black-fraction delta > 0.25 = corrupt) with a Lanczos fallback.
- **Plain Lanczos upscaling of UI textures is a visual NO-OP** — the GPU bilinear filter already does
  the same magnification. Use ESRGAN or re-author. **Always A/B a sample and show the user first.**
- **`tileshader` / `linkcvartoshader` widgets are DIM-SIZED**: ST coords derive from
  widgetSize/scale/**texture dims**, so a 4× texture draws as an empty top-left texel window. Those
  textures **must** ship at original dims (supersample then downscale).
- **Translucent white+alpha overlays show their RGB tinted through the glow** — keep RGB pure white.
- **Self-tiling recipe**: a 20 px mirror-blend band on both axes makes opposite edges match exactly
  (edge diff 42-49 → ~1). Vanilla low-res textures mask non-tiling edges with noise; AI upscales turn
  them into crisp seam lines.
- **Coop menu tile art goes in `ui/coop_tiles/`**, not `textures/mohmenu/`, so it rides the 2 MB code
  pk3 instead of forcing a 365 MB texture-pack re-download. UIWidget shader paths are arbitrary VFS
  keys — no directory restriction.
- **Custom skyboxes**: ship `env/<map>_{rt,bk,lf,ft,up,dn}.tga` — no shader needed. Must be `.tga`.
  **Cube-face orientation is the #1 gotcha**; ground truth is `renderergl1/tr_sky.c`. Generate cloud
  detail as **3D value-noise sampled BY DIRECTION**, not from an equirect — equirect→cube always
  radially smears at the poles. **Always verify a zenith + horizon montage before deploying.**

---

## 7. Audio

- **Format gate: MONO 16-bit PCM 22050 only.** The loader **silently rejects stereo** (and likely
  48 kHz). `Couldn't load sound` at registration means the cue will **never** play — the Frontline
  stingers shipped stereo and were silent for a week (bug-933b).
- **`ffmpeg`'s default WAV adds a LIST/INFO chunk** that pushes the data chunk past offset 44. Use
  `-ar 22050 -ac 1 -c:a pcm_s16le -fflags +bitexact -flags:a +bitexact`.
- **`S_LoadSound … rate=0 width=0` in the log is a RED HERRING** — it prints for *every* sound
  including stock ones that clearly play. Do not re-encode chasing it.
- **OpenMOHAA re-applies every channel's gain EVERY FRAME** via `S_OPENAL_Respatialize` →
  `openal_channel::set_gain`. Volume scaling done at sound **start** lasts one frame. **All**
  per-category scaling must live in `set_gain`.
- **OpenAL clamps per-source gain to 1.0** by default, so alias `soundparms` volume > 1 does nothing.
  This fork sets `AL_MAX_GAIN 8.0` per source at channel creation — which is why the historical
  "MOHAA guns sound weak on OpenAL ports" problem is fixed here.
- **Distance model**: `AL_INVERSE_DISTANCE_CLAMPED` guts gunfire beyond ~1000u (24% at 2000u). The
  original Miles engine was ~linear (~80%) and stock aliases were authored for that. This fork sets
  `AL_LINEAR_DISTANCE_CLAMPED` at context init.
- **The user's audio taxonomy is definitive** — 5 sliders partition ALL sound:
  Music = `s_musicvolume` · Dialogue = `s_dialogscale` · Ambience = `s_ambientvolume` (environmental
  **loops**) · SFX = `s_sfxvolume` (**everything else**) · menu UI clicks exempt.
- **Never touch `s_volume` for a duck** — it ducks gunshots too. Duck `s_musicvolume` +
  `s_ambientvolume`, or use the engine's `s_sfxduck` (effect channels only, music exempt).
- **Same-name alias pooling IS supported engine-side** (`Alias_ListFindRandom` picks by weight). The
  `DUPLICATE ALIASES` log line is a `Com_DPrintf`, **not** an error — do not "fix" it.
- **Auto environmental reverb is ALREADY BUILT** — `CG_UpdateEnvReverb` (`cg_view.c:362`), gated by
  `coop_autoReverb` (default 1) + `s_reverb` (default 0). Do **not** re-implement; just set
  `s_reverb 1`.
- **Once ANY alias plays a wav as `streamed`, `SFX_FLAG_STREAMED` sticks on the shared sfx entry
  forever** — re-aliasing the same file as `loaded` for 3D is best-effort only.
- **~285 AA "ghost subtitle" aliases resolve but their audio was DELETED.** `playsound` on them is
  totally silent, with no console error and no log line. Verify a wav exists in the paks before
  wrapping a retail alias (bug-775).
- **Verify "it used to work" against RETAIL** before treating it as a regression — 14 of 17
  `null.wav` aliases flagged as "missing sounds" are `null.wav` in the shipped game too.
- **Gun "impact"** is not loudness-matching: sub-thump at onset (~−13 dB, 65-85 Hz by class) + bass
  shelf + double compression + soft-clip saturation. Judge on **band balance** (lo ≤62%, hi ≥15% of
  0.5 s energy) **and** crack survival (hi-band ≥25% of first 30 ms) — never RMS alone. Reference
  profile: HD pack = 40/24/37. **Perceived distance = an audible sustained TRAIL**, so a tail
  envelope with a floor makes every shot read as far-away fire.
