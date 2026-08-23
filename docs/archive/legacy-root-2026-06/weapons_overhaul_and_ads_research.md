# Weapons Overhaul (HD textures + sounds) & ADS Research
**Target:** OpenMOHAA-based HZM coop mod, MOHAA trilogy (AA + Spearhead + Breakthrough) run through one unified `com_target_game=2` (Breakthrough) profile.
**Mode:** Research only. No mod files were edited, nothing was built or launched. All proposals are staged, not applied.
**Date:** 2026-06-24

---

## Engine constraints re-verified against the source (these gate everything below)

**Renderer — `code/renderergl1/tr_image.c`, `R_LoadImage` (line 2399):**
- Image loaders present: `LoadTGA`, `LoadJPG`, `LoadPCX32`, `LoadBMP`, `LoadDDS`, `LoadGHOST`. **No PNG loader exists.** (tr_image.c:2429-2461)
- For a requested `.tga`/`.jpg`, the loader tries JPG first (if `r_loadjpg`), then falls back to TGA. (tr_image.c:2429-2443)
- **DDS is only attempted when `glConfig.textureCompression == TC_S3TC` (or `TC_S3TC_ARB`)** — `R_LoadImage` rewrites the extension to `.dds` and calls `LoadDDS` *before* TGA/JPG. (tr_image.c:2418-2425)
- `LoadDDS` accepts **only FourCC DXT1/DXT2/DXT3/DXT4/DXT5**; anything else (e.g. uncompressed/BC7/DX10-header DDS) is rejected and returns no pixels. (tr_image.c:1540-1558) DDS must also be **power-of-two** dimensions or it is rejected. (tr_image.c:1560-1576)
- `LoadTGA` accepts **only type 2 (RGB), 3 (gray), 10 (RLE-RGB)** and **only 24- or 32-bit**. **Colormapped/paletted TGA hard-errors** with `ERR_DROP` (a fatal load error, not a skip). (tr_image.c:1674-1684)
- **Verdict on textures:** HD weapon skins must be **TGA (24/32-bit, uncompressed or RLE)** or **JPG**. DDS works *only if DXT1-5 and power-of-two*, AND only on GPUs/contexts that report S3TC. PNG = silently nothing (gun shows untextured/white). Paletted/16-bit TGA = **fatal ERR_DROP crash** on load.

**Sound — `code/client/snd_codec_wav.c` (the active OLD-DMA path; `snd_*_new.cpp` are dead under `NO_MODERN_DMA`):**
- The loader parses a RIFF/WAVE container, reads the `fmt ` chunk (channels, rate, byte-align, bits) and the `data` chunk, then `Hunk_AllocateTempMemory(info->size)` and reads the whole PCM payload in one shot. (snd_codec_wav.c:131-186, 204-242)
- It does **not** validate `wav_format` — it just reads channels/rate/bits. It assumes **PCM**; an ADPCM/float/compressed WAV will be misinterpreted as PCM (garbage/noise), and an OGG/MP3 renamed `.wav` fails the `fmt `/`data` chunk scan and returns NULL with `ERROR: Incorrect/unsupported format`. (snd_codec_wav.c:142-182)
- The whole file is loaded into a single Hunk temp allocation (no streaming for SFX). This is the documented crash vector: the e3l4 `SubPen_Generator_Run.wav` (16-bit/44.1kHz/635 KB) overran this path. The risk scales with **uncompressed byte size = rate × (bits/8) × channels × seconds**.
- **Verdict on sounds:** replacement weapon SFX must be **PCM WAV**. Safe envelope: **mono, 16-bit, 22050 Hz** (vanilla MOHAA's house format) — a 2-second gunshot at that rate is ~88 KB. Keep individual SFX **under ~250 KB** and avoid 44.1 kHz stereo for anything but the shortest clips. OGG/MP3 will not load. (`.mp3` has a separate codec in some Q3 trees, but under this NO_MODERN_DMA build the registered codec set is WAV-centric; do not rely on OGG.)

**Load order:** paks load alphabetically, later wins; `zzzzzz_co-op_hzm_mod_mohaa.pk3` sorts last and **wins all conflicts**. `fs-unify` means one pak in `main\` reaches AA + SH + BT. Confirmed two copies of the coop pak exist on disk:
`C:\mohaa-coop-dev\zzzzzz_co-op_hzm_mod_mohaa.pk3` and `...\hzm-mohaa-coop-mod\zzzzzz_co-op_hzm_mod_mohaa.pk3` (the latter dir is the unpacked working tree).

**The weapon override layer the coop mod ships (the collision surface):**
The coop working tree (`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\models\weapons\`) ships **full weapon `.tik` definitions**, not just texture/sound stubs. Example `mp40.tik`:
- `setup` block binds the skelmodel and shader: `skelmodel mp40.skd`, `surface gun* shader MP40`, `surface Clip shader MP40`. (mp40.tik:5-8)
- `init/server` is the **full weapon stat block** (damage, spread, clipsize, ammo, secondary-fire = melee bash) and **hooks the coop item system**: `exec coop_mod/itemhandler.scr "initialiseItem" "smg" "MP40"`. (mp40.tik:142)
- `animations` block defines fire/reload/secondary with all client-side FX (`tagspawnlinked`, muzzleflash, shell eject) and **sound aliases** `mp40_snd_fire`, `mp40_snd_reload`, etc. (mp40.tik:159-691)
- Those sound aliases resolve through the coop-shipped **`ubersound/ubersound.scr`** (4273 lines), which maps e.g. `colt45_snd_fire → sound/weapons/fire/Colt45Fire1.wav`. (ubersound.scr:477) **The coop pak owns the master sound-alias table.**

`models/human/new_generic_human.tik` (the documented "anim fix") is a **separate file** — it is the NPC character animation aggregator that `$include`s every `human_*.tik` weapon-animation pack on every map. It contains **no weapon model/texture/shader references** — purely `$include models/human/animation/human_*.tik` lines. So the texture/skin layer and the anim-fix layer are *different files*; an overhaul does not touch `new_generic_human.tik`, but it very much can touch the weapon `.tik` files that carry the `exec ...itemhandler.scr` hook.

Coop shader files present: `scripts/coop_general_industrial.shader`, `scripts/general_industrial.shader`, `scripts/coop_hud_sprites.shader`. **No weapon-skin `.shader` and no weapon `.tga`/`.jpg` are shipped in the coop tree** — the gun *shaders* (e.g. shader `MP40`) live in the base game paks, and the coop pak only references them by name. This is the good news for Part A (see below).

---

# PART A — WEAPONS OVERHAUL (HD textures + sounds)

## A.1 Candidate mods (web findings)

| Mod | Scope | Replaces what | Asset formats (per descriptions) | Trilogy? | Risk for coop |
|---|---|---|---|---|---|
| **HD Weapons Pack and Sounds** (Nexus #28) | All base weapons | **HD weapon MODELS** (DarkAngel) **+ sounds** + textures | models (.skd/.skb) + .tik + WAV (sounds from the High-Res Conversion pack are WAV) | AA-focused | **HIGH** — replaces models & almost certainly the weapon `.tik`, colliding with coop's `.tik` + itemhandler hook |
| **Marcomix's Real Weapons (MRW) 2.0** | All weapons | HD skins, new **models**, new **animations**, optional ironsights | model + anim + .tik + textures | AA edition | **HIGH** — replaces models *and animations* (collides with both coop weapon `.tik` and the `human_*` anim packs `new_generic_human.tik` force-loads) |
| **Hi-Res Realism — Weapons texture pack** (addon to Hi-Res Realism) | Weapon **textures only** | Texture replacement, "retain original palette" | TGA/JPG-oriented texture pack (the author explicitly moved to TGA+JPG in v2.0 to drop DDS) | AA primarily | **LOW** — pure skins, no model/.tik |
| **MOHAA HD** (ModDB) | 3,500+ world+weapon textures | **textures only** (AI-upscaled) | originally **DDS**; an "AI Textures patch" / TGA-JPG variant exists | **Yes — AA + SH + BT** | **LOW–MED** — pure textures, but watch DDS-only variants vs the S3TC gate |
| **Enhanced Textures** / **Redux HD Textures** / **FAH Infantry HD Remaster** | World/character textures (FAH = soldier models) | textures (FAH also model) | mixed DDS/TGA | FAH = trilogy SP | LOW for the texture-only ones; FAH touches *character* models not guns |
| **MOHAA Weapon Soundpack** (ModDB addon) | Weapon **sounds only** | sound replacement | WAV (vanilla MOHAA sound format) | AA | **LOW–MED** — see sound-alias note below |

## A.2 Cross-reference against the constraints

**Texture format risk.** The MOHAA-HD-style AI-upscale packs historically shipped **DDS**. Under this renderer DDS only loads when (a) FourCC is DXT1-5, (b) dimensions are power-of-two, **and (c) the running GL context reports `TC_S3TC`**. If any of those fail, the gun renders untextured. The community itself flagged this: one author was asked for a non-DDS build and confirmed v2.0 would "add TGA and JPG" support — so **prefer the TGA/JPG variant of any HD texture pack**, not the DDS one, to be format-safe regardless of GPU. Any pack shipping **PNG** is a non-starter (no loader). Any pack with **paletted/16-bit TGA** will hard-crash on load (ERR_DROP) — unlikely from a modern HD pack, but worth a spot-check.

**Sound format risk.** Replacement weapon SFX must be PCM WAV inside the safe envelope above. The MOHAA High-Res / Weapon Soundpack assets are WAV (the format the game has always used), so format itself is fine. **The real catch is the alias table:** weapon fire sounds are referenced by *alias name* (`mp40_snd_fire`) and resolved in `ubersound/ubersound.scr`, which the coop pak **owns and wins**. A sound pack that drops new `.wav` files at the *same paths* the coop ubersound aliases point to (`sound/weapons/fire/...`) will be heard — **but only if it does not also ship its own `ubersound.scr`**, because the coop `ubersound.scr` will override the pack's and keep pointing at the original paths. So: a sound pack that **replaces the WAV files in place** works; a sound pack that **remaps aliases via its own ubersound.scr** is silently overridden by coop and has no effect.

**Model/.tik collision risk (the decisive one).** The HD Weapons Pack and MRW replace **weapon models and `.tik` files**. The coop pak's `models/weapons/*.tik` sort later (`zzzzzz...`) and **win**, so:
- If the overhaul pak sorts *before* coop (any normal name): coop's `.tik` wins → **the overhaul's new models/anims are silently ignored** (you get coop's vanilla-model gun, overhaul ineffective for anything defined in `.tik`/skelmodel). Only loose textures/sounds at matching paths would show.
- If the overhaul pak were renamed to sort *after* coop (more z's, as these mods literally instruct — "add more Z's"): the overhaul `.tik` wins → **coop's `exec coop_mod/itemhandler.scr` hook and stat tuning are dropped** → weapon pickups/loadouts/respawn and the documented per-map anim fix break. **This is the break-the-mod scenario.**
- A model swap can also desync the **animation tags** (`tag_barrel`, `tag_eject`) the coop `.tik` FX entries reference; a non-matching `.skd` makes muzzleflash/shell-eject spawn at the wrong tag or error.

## A.3 Recommendation & mount strategy

**Do a textures-and-sounds-only overhaul. Do not ship any weapon `.tik`, `.skd`, or `.skb`.**

1. **Textures:** take a weapon **skin** pack (Hi-Res Realism Weapons texture pack, or the TGA/JPG variant of MOHAA HD), and **strip it down to only the texture files** that live under the gun texture/shader paths (`textures/...`, `models/weapons/*.tga`). Re-pack as a pk3 named to sort **after the base game but BEFORE the coop pak** — e.g. `zz_hd_weapons_textures.pk3` (sorts after vanilla `pak*.pk3`, before `zzzzzz_co-op...`). Place in `main\` so fs-unify covers all three games. Because the coop pak ships **no** weapon textures/shaders, there is no conflict — the new skins are the highest-priority texture provider and just render. (If a future coop build ever adds a weapon `.shader`, it would then win; today it does not.)
   - Confirm every texture is TGA (24/32-bit) or JPG. Convert any DDS to TGA. Reject/convert any PNG. Spot-check for paletted TGA (would crash).
2. **Sounds:** take a WAV weapon soundpack and **ship only the `.wav` files at the original `sound/weapons/...` paths** — **do NOT include the pack's `ubersound.scr`** (coop's wins anyway). Same pak (`zz_hd_weapons_*`) is fine. Verify each WAV is PCM, mono/16-bit/22050 Hz where possible, and under the size envelope; re-encode the offenders. This sidesteps the alias problem and the large-WAV crash.
3. **If you specifically want new weapon MODELS** (true HD geometry, not just skins): there is **no silent-merge path**. You must do a **one-time manual merge per weapon**: take the overhaul's `.skd/.skb` + skin, but **keep coop's `.tik`** and only edit coop's `setup{ skelmodel ... surface ... shader ... }` to point at the new model/skin, **leaving the `init/server` block (incl. `exec coop_mod/itemhandler.scr ...`) and the `animations` tag names intact**. The new model must expose the same tags (`tag_barrel`, `tag_eject`, etc.) or the FX entries need adjusting. This is per-weapon hand-work and should be staged and bench-tested one gun at a time.

### PART A — BREAK-THE-MOD VERDICT
- **Pure texture + sound swap (TGA/JPG + PCM WAV, no `.tik`/model, no `ubersound.scr`): SAFE.** Mount as `zz_hd_weapons_*.pk3` in `main\`, sorting *before* the coop pak.
- **Any pack that ships weapon `.tik`/`.skd`/`.skb` or its own `ubersound.scr`: CONDITIONAL→BREAKS.** Sorted before coop → ineffective; sorted after coop → drops the itemhandler hook + anim fix and breaks weapon pickups/loadouts. Only safe via a deliberate per-weapon `.tik` merge that preserves coop's `init/server` hook and FX tags.

---

# PART B — ADS / AIM DOWN SIGHTS

## B.1 Does OpenMOHAA / vanilla already have ADS or a zoom?

**There is no "ironsight ADS" feature, but there IS a complete, server-authoritative weapon ZOOM system already wired — and the coop mod already uses it.**

- The weapon `.tik` keyword **`zoom <fov> [autozoom]`** sets the FOV a weapon zooms to. (`code/fgame/weapon.cpp:711-715`) There are companion keywords `zoomspreadmult` / `dmzoomspreadmult` (accuracy while zoomed, weapon.cpp:387-400) and `zoommovement` (max move speed while zoomed, weapon.cpp:801-805).
- The trigger is **secondary fire / right mouse**: in `Player::Postthink`/move handling, `if (new_buttons & BUTTON_ATTACKRIGHT) { weapon = GetActiveWeapon(WEAPON_MAIN); if (weapon && weapon->GetZoom()) ToggleZoom(weapon->GetZoom()); }`. (`code/fgame/player.cpp:4493-4498`)
- Zoom is **fully server-side**: `ToggleZoom`, `SafeZoom`/`ZoomOff` events (player.cpp:589-604, 1838-1839), `m_iInZoomMode`, and the FOV applied through `client->ps.fov` / `SetFov` (player.cpp:5979-6023, 6529). The client just renders the replicated FOV. `cg_view.c::CG_CalcFov` consumes `cg.camera_fov` and clamps `cg_fov` to 65-120 (cg_view.c:486-526, 860-864). There is **no client-only zoom/ADS/ironsight cvar** in cgame — the `zoom`/`fov` matches in `cgame` are FOV math and a couple of comments, not an ADS feature.
- The coop mod **already ships this on the right weapons**: `KAR98sniper.tik` `zoom 20` (line 115), `springfield.tik` `zoom 20` (110), `G43.tik` `zoom 30` (105), `svt_rifle.tik` `zoom 20` (104), and `coop_binoculars.tik` `zoom 20 1` (48). On those weapons, **RMB already aims-down/zooms** — that is the existing "ADS." Non-sniper guns instead define `secondary firetype melee` (rifle-butt bash), e.g. `mp40.tik:69`. So **RMB is already overloaded**: zoom on scoped weapons, melee on everything else.

**OpenMOHAA upstream:** there is no dedicated "ADS/ironsight" feature or cvar in the engine; the zoom system above is the inherited MoH mechanism. Community ADS is all built *on top* of it or via binds (below).

## B.2 Community ADS approaches and what layer they live in

1. **MohAim "Ironsight"** (GameFront / FilePlanet). Mechanism per the authors: **bind the *slow-walk* key to RMB**; pressing RMB switches to a walk/aim view (crosshair appears in run mode). The authors state **they did not edit the engine — "simply modded a solution"**, and that it is **"client and server side."** In practice this is a **config/bind + view-stance trick**, not a real FOV zoom (early versions explicitly *could not* add any zoom). It also had a famous bug: using it on AA mission 1 prevented exiting the truck (a stance/movement-state side effect). **Layer: config/bind (+ minor script/stance), client-visible, lowest risk — but it is a cosmetic stance shift, not zoom, and it competes for the same RMB the coop zoom/melee already uses.** [gamefront, fileplanet]
2. **Marcomix's Real Weapons (MRW 2.0)** ships an **optional ironsight** as part of a full overhaul: **new models + new animations + `.tik`**. Layer: **fgame/script + models/anims** = the high-risk layer (same collision as Part A's model overhauls). MRW 2.0 reportedly fixed the truck/crouch-stance bug of earlier ironsight attempts. [moddb MRW]
3. **Pure cgame view-model offset + FOV change on a key** (the "proper" ADS): would live in `cgame` (the project already builds `cgame`). This is the cleanest *engineering* path but **does not exist as a community drop-in for MOHAA**; it would be a custom cgame change.

## B.3 Coop compatibility analysis

- **The existing zoom system is the safe ADS substrate.** It is server-authoritative and already replicated/working in coop (the sniper weapons zoom today, and the coop binoculars use `zoom 20 1`). Extending "ADS zoom" to more weapons is just adding a `zoom <fov>` line to a weapon `.tik`.
- **But RMB is contested.** On non-scoped guns the coop `.tik` uses `secondary firetype melee`. Adding `zoom` to those weapons means RMB can no longer be melee (the engine routes `BUTTON_ATTACKRIGHT` to `ToggleZoom` whenever `GetZoom()` is non-zero, player.cpp:4496). So a "everything ADS" change **removes the rifle-butt bash** unless you choose a different input — and there is no separate ADS button in the input model.
- **The maptest harness watches secondary fire.** 50 coop files reference `secondaryfire*` (incl. `coop_mod/itemhandler.scr`, `player.scr`, `dbno.scr`, `cover.scr`, `medkit.scr`), and the harness checks `$player.secondaryfireheld`. Re-purposing RMB to ADS-zoom on weapons that today melee would change that signal and could trip coop secondary-fire logic (cover system, DBNO, medkit) and the maptest assertions. **Any ADS that reuses RMB must be validated against those scripts.**
- **MohAim's slow-walk-bind trick is the lowest-collision option** because it is a client config bind, not a weapon-behavior change — it does **not** touch weapon `.tik`, the itemhandler, or the alias table. Downsides: it provides a stance/view shift, **not** a real zoom; it still consumes RMB (conflicting with coop's secondary-fire scripts and the existing zoom-on-snipers); and it carries the historical truck/stance bug that must be retested on the coop map set before trusting it.

## B.4 Feasibility verdict

**Easiest viable ADS that won't break the mod: extend the *existing* server `zoom` system, conservatively, via weapon `.tik` only — and do it as part of the same per-weapon `.tik` merge discipline from Part A (preserve `init/server` + `exec coop_mod/itemhandler.scr`).**

- Add a modest `zoom <fov>` (e.g. 55-65, a light ADS pull-in rather than a sniper 20) plus `zoomspreadmult`/`zoommovement` to the SMG/rifle `.tik` files **only if you accept losing RMB melee on those guns**. This is server-replicated, coop-safe by construction (it's the same mechanism the snipers already use), and needs **zero engine/cgame/dll changes**.
- **What it touches:** the coop `models/weapons/*.tik` files (the layer coop already owns) — so it is an edit to coop's own files, not a foreign pak conflict. Must re-test the `secondaryfire`-dependent coop scripts (cover/DBNO/medkit) and the maptest `secondaryfireheld` assertion, since RMB semantics change on the affected weapons.
- **If you want a true cosmetic ADS (view-model raised to sights) with optional small zoom:** that is a **custom `cgame` change** (view-model origin/angle offset while `m_iInZoomMode`/a new ADS flag is set, plus a gentle FOV nudge). The project already builds `cgame`, so this is feasible and stays **client-side rendering** (the zoom state itself still rides the server `ToggleZoom`). This is more work but the only path to "modern ADS look" without importing MRW's model/anim overhaul.
- **Avoid** the MohAim slow-walk-bind hack as a shipping solution (cosmetic only, RMB conflict, legacy stance bug) and **avoid** importing MRW/HD-Weapons ironsights wholesale (model/anim/.tik overhaul = Part A's break scenario).

### PART B — BREAK-THE-MOD VERDICT
- **Extend the existing server `zoom` keyword in coop's own weapon `.tik` files: SAFE (mechanically) / CONDITIONAL (input).** No engine or pak-conflict risk — it's coop's own files and the same system the snipers use. The condition is RMB semantics: adding zoom to a melee-secondary weapon removes its rifle-butt and changes the `secondaryfire` signal the coop cover/DBNO/medkit scripts and the maptest harness read — **must be retested before shipping.**
- **Custom cgame view-model ADS: CONDITIONAL (engineering).** Clean, client-side render change on top of the existing server zoom; feasible since cgame is built, but it is bespoke code to write and test.
- **Importing MohAim (bind hack): CONDITIONAL.** Won't corrupt mod files, but cosmetic-only, RMB-contended, and carries a known stance/truck bug to retest.
- **Importing MRW / HD-Weapons ironsight wholesale: BREAKS** (drags in model/anim/.tik overhaul → same collision as Part A).

---

## Sources
**Codebase (file:line):**
- `code/renderergl1/tr_image.c:2399,2418-2461` (R_LoadImage format dispatch; DDS-before-TGA only under S3TC; no PNG)
- `code/renderergl1/tr_image.c:1540-1576` (LoadDDS: DXT1-5 only, power-of-two only)
- `code/renderergl1/tr_image.c:1674-1684` (LoadTGA: type 2/3/10, 24/32-bit only, paletted = ERR_DROP)
- `code/client/snd_codec_wav.c:131-186,204-242` (WAV RIFF/PCM loader, whole-file Hunk temp alloc)
- `hzm-mohaa-coop-mod/models/weapons/mp40.tik:5-8,69,142,159-691` (coop full weapon .tik + itemhandler hook + secondary melee + FX/sound aliases)
- `hzm-mohaa-coop-mod/ubersound/ubersound.scr:477` (coop owns the weapon sound-alias master table)
- `hzm-mohaa-coop-mod/models/human/new_generic_human.tik` (anim aggregator; no weapon model/texture refs)
- `hzm-mohaa-coop-mod/models/weapons/{KAR98sniper,springfield,G43,svt_rifle,coop_binoculars}.tik` (`zoom <fov>` already used = existing ADS)
- `code/fgame/weapon.cpp:387-400,711-715,801-805` (zoom / zoomspreadmult / zoommovement keywords)
- `code/fgame/player.cpp:4493-4498,5979-6023,6529` (RMB→ToggleZoom; server-authoritative FOV)
- `code/cgame/cg_view.c:486-526,860-864` (client FOV math, cg_fov clamp; no ADS cvar)

**Web:**
- HD Weapons Pack and Sounds — https://www.nexusmods.com/medalofhonoralliedassault/mods/28
- MOHAA HD (3,500+ textures, trilogy) — https://www.moddb.com/mods/medal-of-honor-allied-assault-hd
- Hi-Res Realism Texture Mod / Weapons addon — https://www.moddb.com/mods/hi-res-realism-texture-mod and https://www.moddb.com/mods/hi-res-realism-texture-mod/addons/hi-res-realism-weapons-texture-pack
- Enhanced Textures — https://www.moddb.com/mods/enhanced-textures
- FAH Infantry HD Remaster (AA+SH+BT) — https://www.moddb.com/mods/fah-infantry-hd-remaster
- MoHAA High-Resolution Multiplayer Conversion Pack (WAV sounds) — https://www.moddb.com/mods/mohaa/downloads/mohaa-high-resolution-multiplayer-conversion-pack-2-0
- MOHAA Weapon Soundpack — https://www.moddb.com/addons/medal-of-honor-allied-assault-weapon-soundpack
- MRW: Marcomix's Real Weapons (models+anims+optional ironsight) — https://www.moddb.com/mods/mrw-medal-of-honor-allied-assault-edition and https://www.gamepressure.com/download.asp?ID=59126
- MohAim Ironsight (slow-walk bind, no engine edit, client+server) — https://www.gamefront.com/games/medal-of-honor/file/mohaim and https://www.fileplanet.com/archive/p-76117/MohAim-Ironsight-The-Best-View
- x-null "MOHAA Ironsight project" thread — https://www.x-null.net/forums/threads/3436-Help!-MOHAA-Ironsight-project
- GameWatcher best mods — https://www.gamewatcher.com/games/medal-of-honor-allied-assault/mods/best
