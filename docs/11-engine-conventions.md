# 11 — Engine (C/C++) Conventions

---

## 1. Engine limits — the current table

Verified in the working tree 2026-07-29. **These are cross-binary protocol constants unless marked
otherwise** — see [01-project-map.md](01-project-map.md) §3.

| Constant | Value | File | Notes |
|---|---|---|---|
| `GENTITYNUM_BITS` | 11 | `q_shared.h:1667` | `MAX_GENTITIES` = 2048. Raised from 10 — closed the whole stale-entity crash family |
| `MAX_MODELS` | 2048 | `q_shared.h:1680` | raised 1024→2048 (bug-866: CS_MODELS overflow) |
| `MAX_SOUNDS` | **1600** | `q_shared.h:1742` | 512→1024→1280→1600. ⚠️ records still say 1280 — see [03](03-record-vs-code.md) |
| `SOUND_INDEX_BITS` | 11 | `q_shared.h:1749` | now enforced by `#if MAX_SOUNDS > (1<<…) #error` |
| `MAX_CONFIGSTRINGS` | 8192 | `q_shared.h:1787` | raised from 4096; every serialisation path audited |
| `MAX_GAMESTATE_CHARS` | 98304 | `q_shared.h:1805` | the whole gamestate goes in ONE message |
| `MAX_MSGLEN` | 131072 | `qcommon.h:270` | |
| `MAX_RELIABLE_COMMANDS` | **1024** | `qcommon.h:215` | raised from 512. **Must stay a power of two** (masked `&(N-1)`). Costs `N × MAX_STRING_CHARS` per `client_t` **and** per client `clc` |
| `MAX_WEAPONS` | 128 | `q_shared.h:1762` | raised from 64; configstring-layout only, no wire field |
| `MAX_HUDDRAW_ELEMENTS` | 256 | `q_shared.h:1788` | out-of-range slot index throws a ScriptException — stay 0-255 |
| `MAX_TIKI_LOAD_ANIMS` | 8192 | `tiki.h:36` | |
| `frameInfo[].index` | 13 bits | `msg.cpp:1355-1361` | `entityStateFields_ver_15` **only** (BT). Was 12 = silent truncation → wrong anims played → disfigured characters |
| `MAX_BODYQUEUE` | 128 | `actor.h:306` | raised from **5** |
| `MAX_SFX` | 4096 | `snd_local_new.h:181`, `snd_openal.c:151` | was inconsistently 1400 in one of three copies |
| `MAX_ENTITIES` (gl1 renderer) | 1023 | `tr_types_new.h:33` | **renderer-local, not protocol.** The "can't be raised" comment was disproved but the raise was reverted (bug-1172) |
| `MAX_MODEL_CHILDREN` | 16 | | `Entity::attach` fails on a full parent — a coop player with helmet + holstered guns + gear can genuinely hit it |
| `MAX_CVARS` | 4096 | | this mod runs a big cvar population: challenges ~360, armory ~40, objectives ~80, archived config ~800 |

### The rule that generated most of the above

> **A `MAX_*` macro is the ARRAY size, never automatically the ENCODABLE ceiling.**
> Every hard limit here has at least three independent ceilings and they are routinely different:
> the **array declaration**, the **bounds check**, and the **bit/wire width** that carries the index.
> When raising any limit, find all three.

`MAX_SOUNDS` alone has **four** stacked ceilings, in binding order:
1. **Configstring layout** — `CS_AXIS = MAX_SOUNDS + 2393 < MAX_CONFIGSTRINGS`. (2000 broke this →
   `SV_FindIndex: bad index` → bug-1179.)
2. **Wire** — `sound_index` is 11 bits → hard cap 2048, and this one **silently truncates**.
3. **Byte pool** — `MAX_GAMESTATE_CHARS` holds every configstring's text (~40 bytes per sound path).
4. **`MAX_RELIABLE_COMMANDS`** — every configstring set *after* the gamestate becomes one reliable
   command; overflow drops the client with "Server command overflow" (bug-1183).

### Corollaries, all paid for

- **The dangerous limits are the ones that print NOTHING.** `frameInfo[].index` truncation had no
  warning, no error, nothing to grep — it just played a different animation.
- **A capacity WARNING is load-bearing.** `SV_FindIndex`'s overflow warning fires because the engine
  is *refusing* to register more — and that refusal is what kept the reliable queue under its
  ceiling. Raising the cap to silence it converted a log nuisance into a client-dropping failure.
- **Never "fix" a silent overflow by making the wrap-around bigger.** `R_AddSpriteSurf` wrapped
  (`% MAX_SPRITES`) instead of refusing, converting an overflow into a garbage-pointer crash. Prefer
  a bounded refusal + one-shot `PRINT_WARNING`.
- **Do not enforce a bit-width relationship with a comment.** `MAX_SOUNDS`'s "silently truncates"
  rule sat as a comment through three raises. It is now `#if … #error`.
- **A compile-time guard referencing an undefined macro is worse than no guard.** `bg_public.h`'s
  `#if (CS_MAX) > MAX_CONFIGSTRINGS #error` was **silently dead its whole life** — `CS_MAX` was
  defined off `CS_PARTICLES`, which is not defined anywhere; an undefined identifier evaluates to
  `0` inside `#if`. Re-anchored to `(CS_AXIS + 1)`.
- **Do not trust "can't be increased" comments** — verify against the actual bit-packing math.
  gl1's own sort key already budgeted 12 entity bits while `MAX_ENTITIES` sat at 1023.
- **Do not trust a comment's claim about what a config ships** — `level.cpp` asserted
  "`maxentities 2048` in a config (shipped for years)"; zero cfg files anywhere set it.
- **When a constant is duplicated across files, check ALL copies.** `MAX_SFX` was 1400 in one of
  three headers; the other two already agreed on 4096.

### Renderer drawsurf sort key (both renderers)

`drawSurf_t::sort` is one unsigned 32-bit word.

| | dlight | pshadow | entity | staticmodel | shader |
|---|---|---|---|---|---|
| **gl1** | 0-3 | — | 8-19 | 20 | 21-31 → **11 bits = 2048** vs `MAX_SHADERS` 16384 |
| **gl2** | 0 | 1 | 4-15 | 16 | 17-30 → 14 bits, genuinely fits 16384 |

Use `MAX_SORTED_SHADERS` / `QSORT_SHADERNUM_BITS` (added 2026-07-28), **never** `MAX_SHADERS`, when
masking. Anything packed into that key inherits a ceiling — the static-model loop index and the
refEntity index both ride the 12-bit entity field (4095 max).

**Do not repack gl1's sort key as a side effect of an unrelated fix.** gl1 is the shipping renderer;
widening its shader field changes sort ORDER and the sprite key rides the same shift. That needs its
own reviewed, playtested change.

`MAX_SPRITES` (2048) is the **scene** sprite pool; `MAX_SPRITESURFS` (32768) is the **per-frame**
surf pool, one surf per sprite *per view* — portal sky, mirrors and gl2 sun cascades multiply it.

---

## 2. Renderer discipline (gl1 vs gl2)

- **gl1 is the shipping renderer.** `cl_renderer` defaults to `"opengl1"` (`cl_main.cpp:3229`), no
  override in `autoexec.cfg`. `renderer_opengl1.dll` in the GOG root is the actively-rebuilt one.
- **gl2 lives at `G:\mohaa-gl2`**, a separate isolated build. `r_genNormalMaps` is gl2-only and has
  zero gl1 equivalent.
- **`vid_restart` unloads and RELOADS the renderer DLL** (`CL_ShutdownRef` → `Sys_UnloadLibrary`).
  Every renderer global, every `cvar_t*`, and **every function-scope `static`** returns to its
  initial value. Never assume a renderer static survives.
- **gl1 calls `R_Init()` from `GetRefAPI`** (DLL load). **gl2/rend2 calls it from
  `RE_BeginRegistration`**, which does not run until `CL_StartHunkUsers`. Anything the client does
  between `CL_InitRef()` and `CL_StartHunkUsers()` hits a live gl1 and a **completely dead gl2**.
  That single ordering difference explains a whole family of "gl2-only crashes on settings apply".
- **Never make a menu button trigger `vid_restart` on gl2** — the renderer tears down under a live
  UI and `UIFont::CheckRefreshFont` calls back into it mid-teardown for an instant AV. The proper
  fix (a `tr.registered` readiness guard on the FONT path) is **still not applied** (bug-1181/1182).
- **gl2 port debugging pattern, proven 3×: diff the LIFECYCLE calls, not the render code.** gl2's
  port dropped `ri.Hunk_Clear` in `RE_BeginRegistration`, `R_ShutdownFont` in `RE_Shutdown`, and
  never incremented `r_sequencenumber`.
- **When a gl2/gl1 port keeps a pool allocator, diff the REUSE branch line by line.** gl2's
  `R_AllocModel` dropped gl1's `index = i` re-stamp → models registered into freed slots silently
  returned handle 0 → per-boot invisible-actor coin flip.
- **When porting a post-FX pass that reuses a gl1 threshold cvar**: check whether the gl2 source FBO
  can exceed `[0,1]` (`r_hdr` defaults **on**, `RGBA16F`), and if so `clamp()` the sample to `[0,1]`
  **before** the comparison. Do **not** reach for a smooth tonemap — Reinhard/ACES reclassify pixels
  differently around the threshold and force a re-derived constant; a plain clamp needs no
  recalibration and is a no-op when the source is already LDR (bug-1156).
- **gl2 GLSL edits are stringified at BUILD time; they compile at RUNTIME boot.** A syntax error is
  an `ERR_DROP` on the next gl2 boot. **Never put a double quote in a `.glsl` file, not even in a
  comment** — `stringify` emits it unescaped.
- **A gl2 GLSL uniform only receives data if its NAME matches `tr_glsl.c uniformsInfo`.** Wrong name
  = location −1 = all-zero uniform, silently.
- **`renderergl1` is the live copy for shared code.** Image loaders etc. are duplicated across
  `renderercommon/`, `renderergl1/`, `renderergl2/`, `qcommon/cm_fencemask.c`, `cgame/cg_lightstyles.cpp`.
  A LoadTGA crash-fix applied only to `renderercommon` did nothing.
- **Cheap honest A/B for a renderer change**: flip only the new branch off, build, keep that DLL
  beside the fixed one, swap the deployed file between runs. Two binaries, one source tree, no
  scaffolding left behind.

---

## 3. Diagnosis order and crash forensics

**Instrument the TOP of the pipeline first (is it SUBMITTED?), not the bottom (what colour did it
write?).** The week-long invisible-actor hunt measured backend GL state, occlusion and readbacks for
days; a 15-line probe at `RE_AddRefEntityToScene` answered "cgame never submits him" in ONE boot.

**When a bug reproduces only in renderer B, run a matrix of single-variable boot pairs** from an
isolated homepath: gl1+same-script (script innocent?), gl2+variant-script (trigger?), flood-colours
(drawn-dark vs not-drawn?). Each pair kills a whole hypothesis class in ~8 minutes.

**When several seemingly-unrelated bugs cluster around one repeated NUMBER in unrelated log lines,
grep that literal across the whole tree before theorising about corruption.** "entity 1023" turned
out to be a hardcoded pre-2048-protocol sentinel in `cl_invrender.cpp:160` (bug-1167).

### Crash dumps

- `0xC0000409` with `ExceptionInformation[0]=7` = `FAST_FAIL_FATAL_APP_EXIT` = `abort()` / uncaught
  C++ exception, **not** a stack-buffer overrun (subcode 2 would be the cookie).
- Post-mortem stacks show the **abort path** (ucrtbase), never the throw site.
- Minidump streams 21/22 give private-usage at death — 6-8.5 GB on a 16 GB box = OOM `bad_alloc`.
- A **NULL `cvar_t*` deref** shows up as a read from address **`0x30`** (`.integer`); `0x2C` is
  `.value`, `0x20` is `.flags`. Recognise instantly.
- WER dumps here use `MemoryListStream` (type 5), not `Memory64ListStream`.
- Tools: `scratchpad/dumpan.py` (exception + module + `.map` symbol), `scratchpad/stackscan.py`
  (naive scan). The `.map` **must** match the binary loaded at crash time — a rebuild invalidates it.
  `cdb.exe` is at `C:\Program Files\WindowsApps\Microsoft.WinDbg_*\amd64\`; `game.pdb` now ships next
  to `game.dll` so dumps resolve exact lines. `.symopt+0x40; .reload /i` force-maps a stale PDB.
- **The log's last line is not necessarily where it failed.** A crash whose `qconsole.log` ends at
  `----- finished R_Init -----` with `nvoglv64.dll` all over the stack looked like a renderer bug
  twice — both times the **server** had already died and the engine was re-running `R_Init` during
  teardown. Always grep for the real `ERROR:` / `Server` line first.
- **A deterministic "hang" at an exact log line during shader parse can be an ACCESS VIOLATION**, not
  a loop — under the launcher an AV presents as a silent alive-until-killed process with no crash log.
- The engine has **no top-level exception handler**; fgame's try/catch covers only `ScriptException`
  and `const char*`. `CL_Init` now installs `std::set_terminate` + `set_new_handler` that log to
  `qconsole.log` + `hzm_fatal.log` then `abort()` so the WER dump still lands.
- **`ScriptError` may ONLY be thrown from inside the script VM's try/catch.** Engine callbacks
  invoked from the client across the DLL boundary (`globals.SoundCallback` and friends) have no
  handler — a `ScriptError` there is `std::terminate` → `0xC0000409`. Convert to `DPrintf` + return.

---

## 4. Engine idioms and traps

- **`Container<T>` is 1-BASED.** A forward `for (i=0; i<NumObjects(); i++) RemoveObjectAt(i)` "clear"
  is doubly broken — `RemoveObjectAt(0)` no-ops **and** removal shrinks the list under the walking
  index. With 2+ entries most entries survive (bug-767).
- **`Event::GetString(n)` returns a `str` object, not `char*`.** Passing it to `%s` prints garbage.
  Use `.c_str()`.
- **`Q_stricmp` IS NULL-safe** in this tree (`q_shared.c:1262`). Stop re-deriving NULL-deref theories
  on it.
- **Never `pv->floatValue()` a `ScriptVariable` from `Vars()->GetVariable()` without checking
  `GetType()`** — `VARIABLE_NONE` slots exist after script reads of unset fields, and the throw
  escapes C++ callers like `RadiusDamage`, killing whole event chains (bug-948).
- **`Entity::Delete()` is the canonical destroy helper**: `delete this` outside thinks,
  `PostEvent(EV_Remove, 0)` inside them. Several sites hand-inline it — when you see the
  `if (g_iInThinks) … else delete …` shape, **check which object each arm acts on**. One had `this`
  in one arm and `obj` in the other for years.
- **ALL script execution runs inside `g_iInThinks`** (`g_main.cpp` brackets `Director.Unpause()`), so
  the "in thinks" arm is the NORMAL path for anything a `.scr` triggers, not the rare one.
- **`RF_FIRST_PERSON` is a CLIENT-ONLY flag** — nothing in fgame ever writes it. Useful for proving a
  cgame renderfx change is inert.
- **`RF_FLAGS_NOT_INHERITED` deliberately EXCLUDES** `RF_FIRST_PERSON`/`RF_THIRD_PERSON`/
  `RF_DEPTHHACK`, so `CG_AttachEntity` **does** propagate the parent's view-visibility to children.
- **Script threads cannot win a per-frame fight against entity `Think`.** `G_RunFrame` order =
  scripts → thinks → snapshot. Anything a script clears each frame gets re-set before the snapshot.
  To defeat a per-frame engine writer, change the **input** the engine reads, not the output.
- **CAMERA/BODY LOCKSTEP is a standing rule**: every force term on `cg.renderingThirdPerson`
  (`cg_view.c`) needs a term at the **same precedence** on `bThirdPerson` (`cg_modelanim.c`), or the
  camera ends up inside your own head.
- **`.st` statemap parse errors `ERR_DROP` the server** — the opposite failure mode to `.scr`'s
  silent compile failure. Always boot-test `.st` edits locally. Custom statemap features must never
  transition into vanilla hub states whose exits they don't control (one-frame cycles ERR_DROP).
  Don't add a state exit to a target state that doesn't exist in *that* statemap (legs vs torso).
- **`FL_IMMOBILE` freezes ONLY the statemap** (`EvaluateState` early-returns). It does **not** stop
  direct `SetPartAnim` calls from weapon/holster/spawn code — a forced pose still needs a per-frame
  re-assert. FL_IMMOBILE and weighted-pool idle cycling are mutually exclusive.
- **`renderergl1 Upload32` force-resamples non-power-of-two textures** (lossy box filter). Author
  atlases at power-of-two sizes.
- **New cvars a MENU writes must be registered `CVAR_ARCHIVE` in the EXE (`CL_Init`)** — cgame-only
  registration means a main-menu toggle before entering a game creates a flagless cvar that never
  persists (bug-317).
- **This build has NO libcurl.** `cl_curl.c` is dead code under `#ifdef USE_CURL` (never defined);
  the real path `sys_curl.c` needs `HAS_LIBCURL`, and `find_package(CURL)` failed here. For HTTPS,
  spawn PowerShell via `CreateProcessA` with the payload in a **file** (never on the command line).
- **`snd_info.cpp`'s `loopstart`/`loopend`/`maxnumber`/`maxfactor` branches are guarded by an
  INVERTED `if (!tiki.TokenAvailable(qtrue))`**, so none has ever been parsed. **Left alone
  deliberately** — fixing it would suddenly start applying real loop points. Do not "notice" it again
  and fix it without asking.
- **Check upstream OpenMOHAA commits since the fork point (`a72bc153`, ~311 commits behind) before
  building a custom fix** for any inexplicable physics/collision symptom.

---

## 5. Coop-specific engine facts

- **The coop pain handler buffers every German's ENGINE health to 5000**
  (`aihandler.scr::initialisePainVars`); the real HP is `flags["coop_actorActualHealth"]`,
  decremented only by `handlePain`, which then issues a synthetic **150000** overkill on real death.
  Consequences that keep biting:
  - "The bullet that killed" is **not** the killing blow the engine sees. Any "player killed X with
    Y" detection hooked into `BulletAttack` misses those kills — detect on the alive→dead edge
    inside `Sentient::ArmorDamage`.
  - Any script that sets `nolongpain 1` or `enablePain 0` on a buffered actor **permanently severs**
    the pain handler while engine health still reads ~5000 = a bullet sponge (bug-1212).
  - Never gate blast gore on `damage` magnitude — the overkill overwrites it. Use a chance roll or
    the hit location.
  - **`nodamage` + huge health is NOT enough to protect a scripted VIP** — `initialisePainVars`
    clamps health > 700 to 100. VIP convention: `health >= 1000000` ⇒ aihandler skips and sets
    `coop_actorStopPainHandler`.
- **Movement-mask changes need BOTH sides**: server pmove (`player.cpp`) **and** cgame prediction
  (`cg_predict.c:586`). Server-only = mushy rubber-band walls.
- **The SERVER loads `maps/<name>_sml.bsp`** (`sv_init.c:721`); the client loads `<name>.bsp`. Any
  map-file-keyed feature must handle both names.
- **Loose files do NOT override pk3 twins** on this engine (scripts + data; cfgs exec differently).
  Never design persistence around same-name loose files — use a distinct filename applied as an
  overlay (the `cmpatch _local` pattern).
- **Homepath beats basepath** for pk3 load precedence. A companion pk3 that must override coop files
  has to be in the **homepath** `maintt` with a name sorting after `zzzzzz_co-op`.
- **Engine→script generic hook**: `level.vars->SetVariable("coop_x", n)` in C++ + a per-map script
  monitor consuming the increments. `level.vars` resets each map, so the seen-count stays in sync.
- **Engine→script INPUT bridge**: read `last_ucmd` in a per-frame `Player` hook and
  `Vars()->SetVariable(name, val)`. This is how the coop lobby reads A/D/F with **zero client binds**.
- **Client→server bridge**: cgame `Cvar_Get(name, CVAR_USERINFO)` + `Cvar_Set` on change only →
  engine auto-sends a reliable userinfo update → fgame `G_ClientUserinfoChanged`. Keep keys tiny —
  userinfo is one `MAX_INFO_STRING`.
- **Server-set client cvars must clear `cg_servercmds_filter.cpp`.** The anti-Reborn whitelist
  **silently drops** non-whitelisted commands. `set` of a new/user-created cvar is allowed;
  `seta`/`sets` need whitelisting. Remote clients need the shipped `cgame.dll`. This single filter
  was the root of the dead lobby LOADOUT button, pick carry-over, and coop detection (bug-597).
- **`ihuddraw` in MP/coop is one CGM NETWORK MESSAGE per call** — even on a listen host. Too many in
  one frame overflow the snapshot buffer and the later ones are **silently dropped**.
- **`ihuddraw` is non-uniformly stretched** to fill the screen (`vidWidth/640`, `vidHeight/480`,
  per-axis). On 21:9 that is ×5.375 vs ×3.0. You **cannot** un-stretch server-side. `align center`
  positions textured quads and strings **differently** — lay out composites with left/top align in
  absolute 640×480 virtual coords.
