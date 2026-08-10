# 20 — Decision Log

Decisions with their rationale. Read before re-opening any of these.

---

## Design & product

| Decision | Rationale | Anchor |
|---|---|---|
| **Locked cosmetics are SHOWN with a lock + "UNLOCK: …" caption**, not hidden | User reversed the earlier hidden-locked design (bug-759/772) pre-release: *locked content should advertise how to earn it*. Snap-back reverts removed; the server apply-gate stays; preview may park on a locked item. | bug-787 |
| **Weapon-unlock chains, not a deployables skill tree** | Deployables tree rejected. Active = weapon unlock chains + a locked-armory hover UI. | memory `skilltree_plan` |
| **gl2 visual parity bar = EXACT MATCH to the OG trilogy, not "better"** | User: *"I don't want to ruin the vibe/environment/ambience of the OG trilogy when it comes to how much fog and how dark maps were originally."* gl1 same-scene captures are ground truth, verified **per map**. Fix the fog **math** until every map matches at scale 1 — never ship per-map fudge tables (runtime cvar sets don't reach DLL cvar instances anyway), and never brighten or thin fog "for visibility". | cerebrum 2026-07-27/28 |
| **`coop_corpseLife` default 0 (bodies persist)** | User's explicit choice. `MAX_BODYQUEUE` raised 5→128 to make it real — the engine recycles corpses independently of the script timer. | `autoexec.cfg:357`; `actor.h:306` |
| **e3l3 officer policy = NONE** | User vote. Scripted-vehicle-ride maps must not run free-roaming boss waves — a dog wave wedged the pathed AB41 on a barrier. The generic `level.coop_officer_hold` gate stays for maps that need a temporary hold instead of full removal. | Decision Log 2026-07-06 |
| **Officer waves scale around a 2-PLAYER baseline** | Solo scales *down* rather than 2P scaling up. | `coop_officerBase*` |
| **Real 3D tree models via `md5_2_skX`, not billboard reskins** | The billboard-card photo-tree swap was rejected ("looks bad"); flat crossed cards + photo-on-radial-blob does not read in-game. Also rejected: CC0 low-poly packs (Quaternius/Kenney/KayKit) as too stylized for realistic WW2. Preferred route was texture-reskin on existing meshes. | cerebrum 2026-06-30 (two entries) |
| **Never bulk-fill a retail alias with a grab-bag of "related" wavs** | That turned "incoming grenade!" into a pool of wounded-begging lines. Look up the alias's gloss in the dialogue TIK first (every generic bark's English gloss is a `/// COMMENT` line above its `first sound` line) and fill only from the matching taxonomy prefix. | cerebrum 2026-07-28 |
| **Do NOT add timer-driven random VO rolls to actors** | Two already exist (aihandler idle mutter, flchatter generic bark) and both read as noise. Drive VO from a **state change** or an engine `say` hook. | cerebrum 2026-07-28 |
| **Do NOT pick a VO pool from `self.team`** | MOHAA teams are only american/german, so British and Italian models land on the wrong pool. Read `self.model`. | cerebrum 2026-07-28 |
| **Release notes & the What's New card are player-facing only** | Never build-mode or dev tooling. User directive 2026-07-21. | |
| **Version scheme**: tiny polish releases append a digit (1.1.31, 1.1.32); real feature releases bump the third digit (1.1.4) | Updater is hash-based so ordering never matters. | cerebrum 2026-07-05 |
| **Never say "Boom Library" publicly** | Standing instruction on the sound-library sourcing. | memory `service_record_challenges` |

---

## Architecture

| Decision | Rationale | Anchor |
|---|---|---|
| **The mounted-turret camera is the gun's OWN TIKI `viewOffset`** — never a global or custom camera | `TurretGun::P_ThinkActive` does `SetPositionOffset(m_vViewOffset)` from each weapon's `.tik`. This is correct for **every** turret in the campaign because each defines its own. A 3rd-person "experiment" that replaced it hijacked every MP vehicle turret. | cerebrum 2026-06-30/07-01 |
| **The coop MG42 nest is a FAKE turret** (`mg42_gun_fake.tik`, `TurretGun` + `spawnflags 1`) — the "gun" you see is the player's first-person **viewmodel**, the world model is a bare tripod. Therefore `g_turretcameras 0` is CORRECT | Binding a turret camera gives the empty-tripod view. | cerebrum 2026-06-30 |
| **ADS = engine POSITION-OFFSET, not statemap aim poses** | A static charge-pose can't retrigger the hip `viewmodelanim fire` restart that continuous full-auto needs → single-shot regression on Thompson/BAR. Final architecture: cgame offsets the FP weapon model along the view axes. | cerebrum 2026-06-27 |
| **`CG_AdsForceFirstPerson()` is the SINGLE decider** for both third-person deciders (`cg_view.c` + `cg_modelanim.c`) | Future view-mode logic edits that helper, never the two call sites — otherwise they drift and you get a camera inside your own head. | cerebrum 2026-07-06 |
| **In-game "menus" for dynamic content = script-drawn `ihuddraw` panels, not `.urc`** | URC can't bind dozens of dynamic rows. Slots 0-255; the coop HUD auto-fade **exempts** slots ≥100, so persistent panels go there. | cerebrum 2026-07-09 |
| **Cosmetic unlocks ride the EXISTING challenge/rank haystack** — zero new plumbing | `flags["coop_chal_unlocks"]` is a pipe-separated token set, persisted to a cvar + `save/unlocks_<id>.dat`, restored on connect. | cerebrum 2026-07-16 |
| **Persistent per-player identity = `cl_guid`** | Already `CVAR_USERINFO\|CVAR_ROM`, sent automatically; readable from script with zero engine work. | cerebrum 2026-07-06 |
| **Coop adoption of weather = a thin CONTROLLER over `global/weather.scr`**, not a reimplementation | The SP weather is already MP-proven (retail `MP_Gewitter_DM` execs it). Coop only had to fix three gaps: rain ambience gated SP-only, the flash `setcvar r_fastsky` being host-only, and `$player` array handling. | cerebrum 2026-07-02 |
| **Weather TYPE is the shader name, never `rain.speed`** | MOHAA has exactly ONE precipitation system — rain, snow and the coop sandstorm all ride `cg.rain.*`. Classifying by speed made dust storms score as rain and get the wet-lens FX. | bug-1206 |
| **Per-client visual gating belongs in the CGAME, never in a server `setcvar`** | A script `setcvar` on a client/renderer cvar only reaches a **listen host** — and if the cvar is `CVAR_ARCHIVE` it also stomps the player's own preference for the session. | bug-1206 |
| **Fix a renderer-visible defect at the SIGNAL when the signal is renderer-agnostic** | Correcting the publish in `cg_view.c` fixed gl1 **and** gl2 at once, with zero edits to the contended renderergl2 files. | bug-1207 |
| **Invisible-wall fix pattern = `cmpatch/<map>.txt` brush neutralisation at CM load** | No engine rebuild. Never region mask-strip (kills boundary clip, bug-951). Never bulk-kill from offline classification — the drawverts check is blind to terrain-lump geometry. **Only in-game `killwall` with immediate player verification is safe**, and only user-proven ids get promoted to the pk3. | bug-951, bug-1175-era |
| **`coop_mod/voidguard.scr` is the permanent backstop UNDER collision work**, not a replacement for it | Universal OOB safety net on all maps, self-calibrating, no per-map setup. | cerebrum 2026-07-21 |
| **New armory skins/helmets are a GENERATED pipeline** — `gen_loadout3.py` then `gen_cosmetic_unlocks.py`, in that order | Skin count is dynamic; the ring self-links. **Never hand-edit generated files** — port edits into the generator, rerun, and diff against a pre-regen snapshot. | bug-755 |
| **Import weapon packs NET-NEW-ONLY (zero overwrite)** | Community packs are whole-game *replacements*: they reskin base guns AND add new ones, share model folders, and carry wrong copied `name`/`weapontype`. Namespace the whole chain per weapon. | cerebrum 2026-07-09/10 |
| **Release staging pulls engine binaries from the DEPLOYED GOG root**, not `.cmake` build dirs | A `--clean-first` rebuild can leave the build tree with stale or missing client outputs while the deployed set is what was actually play-tested. Caught at v1.1.51 preflight. | commit `49ab421` |
| **Secrets (Discord webhook) live in a LOOSE `maintt/*.cfg` ONLY, never in a pk3** | The webhook lives in `updater.ini`; `updater.ps1` regenerates the loose cfg on every launch. Grep the source tree and the built pk3 before shipping. | cerebrum 2026-07-10 |

---

## Process

| Decision | Rationale | Anchor |
|---|---|---|
| **THE fix methodology: find how a confirmed-working map or the vanilla scripts already solved it, and copy that exact recipe** | Standing user rule (2026-07-05). The original devs usually solved it. Proof from one session: `scene2::KFiveInit` for entity replacement (the vanilla recipe included a non-obvious −17z offset; the geometric yaw guess was wrong), `vehicles_thinkers::truck_load` for crews, `autotruck`'s own loopsounds instead of the engine's flapping vehicle-sound state machine. **Only invent when the grep comes up empty.** | CLAUDE.md + cerebrum 2026-07-05 |
| **Do long side-tasks INLINE, not via background agents** | Every user Esc interrupt of the main session also kills running background Agent tasks (three died this way). Inline progress persists on disk turn by turn. | cerebrum 2026-07-03 |
| **A user-stopped agent can leave PARTIAL edits** — `git diff` its target files and either complete or revert before building | The stuka agent left `coop_air_bombing_run` plumbing with no callers. | cerebrum 2026-07-05 |
| **While a background agent is editing the MOD tree, every `build.ps1` deploy ships its work-in-progress** | bug-299 crashed the server: an agent's statemap went into the pk3 with no matching engine conditionals in the exe. Check `git status` for foreign changes before any deploy. | bug-299 |
| **Never write `.scr` against a builtin an agent cited without grepping the engine Event table yourself** | `player userinfo` did not exist, and ONE unknown command silently kills the whole file's compile. | bug-298 |
| **Never generate script files through a bash-heredoc python** | The heredoc eats backslash sequences even when quoted; text-mode writes double CRLF (434 lines mangled → TIKI parser silently dropped all aliases). Write the generator to a file first, or use the Write tool. | bug-259, cerebrum 2026-07-04/22 |
| **Validate generated interchange files against the CONSUMER that will read them** | Round-trip through your own parser proves nothing about third-party parsers (our md5anim writer wrapped 6-per-line; Blender's reader expected one line per joint → IndexError). | cerebrum 2026-07-06 |
| **Trust live boot > adversarial verify > raw audit** | Static coop audits **over-predict**: NULL-listener "dead on load" findings for `addon_*` `$`-names are often false, because the engine spawns them via TIKI-classname fallback. t2l3 was graded F and actually loads fine. | bug-1022 |
| **Blueprint shipping gate**: flood-fill connectivity over piece AABBs (8u tolerance), ≥90% in the largest component, **plus** an isometric 3D render | Ortho elevations **lie** about scatter — depth clusters overlap into fake-contiguous walls. If pruning removes >45% of pieces, the source is a scatter-diorama; do not ship it. | bug-1002 r3, bug-1009 |
| **Deterministic zip recipe for release artefacts** | `ZipArchive.CreateEntry` stamps `LastWriteTime = NOW` unless assigned, so rebuilds are never byte-identical and sha256-based artefact reuse silently breaks. Sort entries, assign entry times from source files, exclude repo housekeeping. | bug-237 |
