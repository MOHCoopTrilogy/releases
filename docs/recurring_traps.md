# Taxonomy of Recurring Traps

Derived from `.wolf/buglog.json` (snapshot: 639 entries, 2026-07-29).
A "trap" here = a defect class that **recurred under two or more different bug ids**. These are the
highest-value entries in the whole record: each one has already cost multiple sessions.

Status vocabulary used throughout: `SHIPPED-VERIFIED` / `SHIPPED-UNVERIFIED` / `REVERTED` / `PLANNED` / `OPEN`.
Where a record and the live code disagree, the code wins and the disagreement is flagged in
`open_defects.md`.

---

## T1. Morpheus parse killers - one bad token silently kills the WHOLE .scr

**Recurrence: 12+ ids over 5 months.** The compiler is all-or-nothing: any single syntax error means
the entire file fails to compile and every `::` call into it logs *"Script was not properly loaded"*.
The symptom is always **a feature that silently does nothing**, never an error at the failure site.

| Trigger | Evidence | Note |
|---|---|---|
| Command syntax used on an `EV_GETTER` property | bug-910 (`local.e getmins`), bug-089 (`moveSpeedScale`), bug-1069 (`enableEnemy`) | must be `local.x = local.e.getmins` |
| A script command that **does not exist** (agent-invented) | bug-298 (`userinfo`), bug-1067 (`getcurrentdmweapontype`) | both were hallucinated by a sub-agent and shipped |
| Function call inside a vector literal | bug-348 `( 0 0 int(local.drop) )` | pull into a local first |
| Function call + vector literal in one expression | bug-402 `base + vector_scale(...) + ( 0 0 vs )` | split into single-op statements |
| Parenthesised arithmetic / bare negative in an expression | bug-1069 `( 0 - local.dir[1] ) * ( 1 0 0 )`, `( 0 - 1 )` | |
| Empty-array literal `[]` | bug-1105 (`local.mem = []`) | morlang has **no** empty-array literal |
| Unquoted surface flag `-nodraw` | bug-533 | parsed as MINUS identifier; must be `"-nodraw"` |
| Leading `&&` / `\|\|` on a continuation line | bug-739 / bug-750 (same defect logged twice) | statement ends at the newline - join onto one line |
| Real newline inside a string literal (generator escape mangling) | bug-331, bug-962 | see T2 |
| Backslash in a script path | bug-1205 (`coop_mod\helmet.scr`) | loader swallows `\`; resolves to `coop_modhelmet.scr` |

**Detection that actually works.** Brace counting is *not* sufficient - bug-1069 and bug-1105 both
pass a depth scan while being fatally broken (and bug-239 showed two opposite brace errors can
cancel). Use `scratchpad/depthscan2.py` (comment/string aware) **plus** a live boot with
`developer 1`, which is what gates script `println` and compile errors being printed at all.

**Live re-scan (2026-07-29, this session):** zero occurrences of `= []`, unquoted `-nodraw`,
backslash script paths, or live leading-`&&` lines in `hzm-mohaa-coop-mod/**/*.scr`.
The single leading-`||` hit (`global/old_friendly.scr:650`) is inside a `/* */` block and the file is
referenced by nothing. **Trap T1 is currently clean.**

---

## T2. Generators and encoding round-trips corrupt the files they write

**Recurrence: 6+ ids.** Every instance is a *tool* writing project data, not a human editing it.

- **bug-259** - CRLF DOUBLING. Bytes read out of a `.pk3` (already `\r\n`) written back through
  Python **text** mode became `\r\r\n` on 434 lines; the TIKI tokenizer then silently dropped every
  animation alias in `anims_shared.txt`, killing the salute emote.
  **Rule recorded:** *any file whose content comes from zip bytes must be written back in binary mode.*
- **bug-331** - a bash-heredoc Python generator collapsed the two-character `\n` escape into literal
  newlines inside 4 string literals -> unterminated string -> whole-file parse kill.
  **Rule recorded:** *never emit script files through a bash heredoc.*
- **bug-962** - same class again: patcher wrote raw `0x0A` inside morfuscript string literals.
- **bug-480** - shader generator's brace matcher mishandled mixed CRLF/LF and `//`-commented braces,
  emitting 2 shader blocks missing their closing brace (45 open / 43 close) -> white-square HUD icons.
  Fixed by normalising CRLF->LF and stripping comments *before* matching, plus a balance safety net.
- **bug-ps-home-var** - PowerShell harness assigned `$home`, a **built-in automatic variable**;
  the assignment silently did nothing and logs landed in the user profile instead of the test root.
  **Rule recorded:** never use `$home` or any other PS automatic variable name.

Cross-cutting rule: **generators need an assertion gate**, not review. Every generator that later
stopped causing bugs (`gen_loadout3.py`, `gen_xwfix.py`, `bsp2bp.py`) got one - balance asserts,
"0 stale refs" asserts, count asserts (`assert NS==76`), or bug-1009's connectivity flood-fill gate.

---

## T3. `build.ps1` deploys engine binaries into the real GOG install

**Recurrence: bug-1172 is the explicit one; ~10 further ids are "the fix was never built/deployed".**

`build.ps1` always copies `cgame.dll` and `renderer_opengl1.dll` to the **GOG root** as part of
packing the mod pk3s. That is intentional for normal mod work and *silently wrong* whenever the
working tree contains experimental engine constants.

- **bug-1172 (self-inflicted)** - every `build.ps1` run during a gl2 sandbox session pushed
  sandbox-only `MAX_SOUNDS 2000` / `MAX_ENTITIES 4095` / `MAX_TIKI_ALIASES 8192` binaries into the
  user's real install. Remediated by reverting the constants, rebuilding, and redeploying from the
  reverted state.
- **Mirror image, bug-089** - fixes "did nothing in-game" because they were edited in source and
  **never built/deployed**; the running game still had the old pk3.

**Rules that fell out:** a protocol-constant change ships **all four** binaries together
(`openmohaa.exe` + `cgame.dll` + `game.dll` + renderer) - bug-930 learned this by crashing when the
renderer was left behind. `game.pdb` and (since bug-932b) `cgame.pdb` ship next to their DLLs so WER
minidumps resolve. Homepath `maintt/` beats basepath, and loose files beat pk3s - which is why
bug-595 spent a session chasing a stale 0-byte `omconfig.cfg` decoy while the live config sat in
`maintt/configs/`.

---

## T4. Empty MOHAA array reports `.size == -1`

**bug-909.** The universal append idiom `arr[arr.size + 1] = x` therefore stores the **first**
element at index `[0]`, and every consumer loop (`for i = 1; i <= size`) skips it. Symptom: the first
item registered into any array is permanently invisible - here, the mine detector and the second
primary weapon were lost on every DBNO revive.

Fixed at 2 sites (`itemhandler.scr:1687`, `:1782`, both carrying an explanatory comment).

> **The fix note itself says "same idiom exists in loadout.scr/eventsystem.scr" - and those were never
> clamped.** Live scan 2026-07-29 finds **5 unclamped `.size + 1` append sites still in `coop_mod/`**:
> `aihandler.scr:521`, `eventsystem.scr:95`, `itemhandler.scr:1467`, `:1471`, `:1908`.
> Status: **OPEN (partial fix)** - see `open_defects.md` D-4.

---

## T5. NIL vs NULL are different, and coop hits both

**Recurrence: 7+ ids, including two "storm" events of ~17,100 errors each.**

Two distinct failure modes, both from SP scripts running in a coop context they were never written for:

1. **`Cannot cast 'none' to <type>`** - a `level.*` timing global the vanilla SP init path would have
   set is simply never set in coop. bug-1051 / bug-1052: `level.thundertime`, `level.windtime`,
   `level.shuttertime`, `level.rainvolume` -> `weather.scr:378` alone threw **8,662 times**.
   Fixed with NIL-guards restoring the documented vanilla defaults.
2. **Stale-pointer NULL guards that pass** - bug-1054: `coop_trackTankTarget` had no `else` branch,
   so a freed player reference lingered and *evaded* a `== NULL` check.
3. **Guard with BOTH** - bug-1065 hardened `xp_award` with `== NULL || == NIL` before a `.classname`
   deref, because `level.coop_smoke_player` is only *assigned*, never *initialised*.

**Sequential-storm effect (the meta-lesson, bug-1051/1052):** fixing one class of error lets maps
*progress further*, which exposes the next class. The `$player`-array cast fixes were what unlocked
the none-cast storm. Budget 2-3 fix -> re-sweep passes; a clean sweep after one fix means nothing.

Related and equally load-bearing: **`$player` is an array whenever 2+ players are connected.**
bug-1049 - `gags/t2l4_captain.scr` used bare `$player` as a single entity at ~20 sites; every one
throws `Cannot cast 'array' to listener` in multiplayer. The repair pattern is
`exec coop_mod/replace.scr::player_closestTo self`.

---

## T6. Asset-name and pak override collisions - the thing you shipped is not the thing that loads

**Recurrence: 8+ ids, incl. a 5-round saga (bug-499 -> 525 -> 530 -> 921 -> 922).**

- **Shader-NAME overrides lose the reverse-concat race**; **whole-FILE overrides win**, because the
  filesystem dedupes by filename and the coop pk3 mounts last (bug-921, bug-525 pattern).
- **`.dds` beats `.jpg`/`.tga`.** An HD/DDS pack silently shadows mod art (bug-1129, bug-gl2-decal-red-dds).
- **The final answer when a name is contested (bug-922, the "shader isolation recipe"):** stop
  fighting for the name. Mint a **new shader name that exists only in the coop pk3**, pointing at a
  **private texture path that also exists only in the coop pk3**, and retarget the `.tik` surface to it.
  Diagnostic tell: *if a "black" surface shows per-face shading, a lit default shader is drawing it -
  your identity definition is not reaching that surface at all.*
- **Ordering convention:** `zzzzzzzz_*` sorts after `zzzzzz_*` - used deliberately by
  `zzzzzzzz_hd_fxfix.pk3` / `_hd_groundfix` / `_seamfix` to land on top of an HD pack (bug-1190).
- **`.tik` surface directives must match the `.skd`'s real surface names** or `TIKI_InitTiki` drops
  them (bug-1216).

---

## T7. Engine hard limits - the "raise the constant" trap

**The single largest cluster in the log (~30 ids).** Every instance follows the same shape: a fixed
table or a wire field is too small, and the overflow is **silent** rather than diagnostic.

### T7a. The entity-pool / world-stomp saga (bugs 891, 892, 914-935, 1186) - the most expensive single thread in the project

`coop_mod/server.cfg` shipped `set maxentities 2048` **for years** while `GENTITYNUM_BITS` was 10,
hard-capping the wire at 1024 with slots 1022/1023 reserved as `ENTITYNUM_WORLD`/`ENTITYNUM_NONE`.
The setting did not add entities - it **disabled `AllocEdict`'s overflow guard**, so the allocator
handed out the world slot. That one lie produced an entire weekend of crash reports
(bug-914/915/917/919/920/925: five separate `use-after-free` minidumps in `Sentient::FindItem`,
`Entity::updateOrigin`, `Player::UpdateStats`, `Sentient::NextWeapon`).

Sub-lessons, each learned by a crash:
- **A "comprehensive sweep" that greps only suspected files is not comprehensive** - bug-925 crashed
  in `sentient_combat.cpp`, missed by bug-920's sweep. Grep the *symbol*, globally.
- **Fix the producer, not just the consumers** - bug-920: `Sentient::AddItem` appended entnums with
  no duplicate check while removal took only one occurrence.
- **A pointer being non-NULL is not enough** - bug-919: a recycled slot held a *different class*;
  guards were upgraded to `item && item->isSubclassOf(Item)`.
- **Raising the protocol constant ships FOUR binaries** - bug-930 crashed because the renderer
  (a protocol consumer, with a hardcoded `GORE_MAX_ENTNUM 1024`) was left behind.
- **Audit bare array sizes, not just constant names** - bug-932b (`tr.skel_index[1024]`),
  bug-935 (`processed[MAX_ENTITIES]`, where `MAX_ENTITIES` is the *renderer refentity* cap of 1023,
  not the gentity count). Two different constants named almost the same thing.
- **A capacity family has more members than you think** - bug-934 raised three snapshot constants;
  bug-1186 found the **fourth**, `MAX_SNAPSHOT_ENTITIES`, eight days later. It discarded every
  entity past the 1024th with *no log line at all*.

### T7b. `MAX_SOUNDS` - four different limits bind, in order

The clearest worked example in the codebase (comment block: `q_shared.h:1690-1745`):

1. **Configstring layout** - `CS_AXIS = MAX_SOUNDS + 2393` must stay under `MAX_CONFIGSTRINGS`.
   Broke at 2000 -> `SV_FindIndex: bad start index 4260` (**bug-1179, REVERTED**).
2. **Reliable commands** - each post-gamestate registration is one reliable command;
   `MAX_RELIABLE_COMMANDS` was 512 and the mod already queued ~140 loadout stufftexts.
   1600 pushed it to 514 -> *"Server disconnected"* mid-spawn, twice (**bug-1183, REVERTED**).
   Raising it to 1024 (power-of-two, `& (N-1)` masked) was the missing prerequisite.
3. **Wire** - `sound_index` is 11 bits and **silently truncates**. Hard cap 2048.
4. **`MAX_GAMESTATE_CHARS`** - the text pool, already ~75% of `MAX_MSGLEN`.

**The generalised lesson (bug-1198):** the rule "never exceed 2048, it silently truncates" existed
only as a *comment*. It is now a build break: `#define SOUND_INDEX_BITS 11` + `#if MAX_SOUNDS > (1 << SOUND_INDEX_BITS) #error`.
Do this for every capacity constant - a comment is not a guard.

### T7c. Same-named constant defined differently in three files
`MAX_SFX` was 1400 in `snd_local_new.h` (the *active* OpenAL system) and 4096 in both `snd_dma.c`
and `snd_openal.c` -> `ERR_FATAL S_FindName: out of sfx_t` (bug-1163). Sibling: bug-1194, where
`load_sfx_info` tested a hard-coded literal `1000` instead of `MAX_SFX_INFOS`, and tested `==` rather
than `>=`, so raising the macro did nothing and any overstep walked off the array.

---

## T8. Server -> client `stufftext` is a lossy, filtered channel

**Recurrence: 6+ ids, and it was the hidden root cause of an entire subsystem appearing dead.**

- **Quote truncation (bug-736, bug-758).** `Player::EventStuffText` sends `stufftext "<cmd>"`. Any
  embedded quote in your value **ends the wire-level argument early**. Symptom: client-side
  `Cvar ... does not exist` spam. Rule: send values **unquoted**, **one statement per stufftext**
  (`;`-joined multi-statements are the other half of the same trap).
- **The anti-malicious-server whitelist (bug-597).** `cg_servercmds_filter.cpp` silently drops
  server-stuffed `exec` and `vstr`. That ate the *entire coop-detect handshake*
  (`coop_mod/cfg/detect.cfg`), the objectives setup, and the armory pick carry-over - three
  "unrelated" bugs with one cause. Fixed with scoped exemptions: `exec` only for mod-namespaced
  paths, `vstr` only for `coop_*` / user-created cvars. **Remote clients need the updated `cgame.dll` too.**
- **Bare name-bus tokens are structurally undispatchable** (bug-772): `append name ,hn` with no data
  character makes `playerExtract` return NIL, so nothing dispatches. Every bus token needs a payload.

---

## T9. Cvar registration, flags and exec order

- **Exec order (bug-710).** OpenMOHAA execs `default.cfg` -> saved config -> **`autoexec.cfg` last**.
  `autoexec` was `seta`-ing ~200 curated defaults, so it overwrote every menu-changed setting on
  every launch. Fix: a new `coop_defaults.cfg` exec'd *before* the saved config, via an engine hook.
- **`Cvar_Get` OR-combines flags (bug-1125).** `r_lodscale` was registered twice in gl2, once
  `CVAR_CHEAT` and once `CVAR_ARCHIVE`; the cvar became cheat-protected and the slider silently reverted.
- **A `CVAR_CHEAT` temporarily flipped to `CVAR_ARCHIVE` for an A/B test archives the test value
  forever (bug-918)** - `r_entlight_scale 0.3` dimmed every entity on every launch afterwards, and
  the closing session re-saved it once after the first scrub.
- **Fail-open lock state is a security-shaped bug (bug-682).** The armory padlock recompute zeroed
  all lock cvars then relied on a server-pushed override that might never arrive - so un-earned
  weapons appeared unlocked. Redesigned **fail-locked**.
- **Menus can read a clamped cvar and lie (bug-1152).** gl2 clamps `r_ext_multisample` to 4; the
  8x MSAA plate had to be repointed at the unclamped `r_ext_framebuffer_multisample`.

---

## T10. gl1 -> gl2 renderer parity

~100 ids, essentially all of July. Not a single defect but a standing hazard: **`renderergl2` is a
different codebase (rend2 lineage), so every HZM feature added to gl1 is absent in gl2 until
explicitly ported** - post-FX chain (bug-1149, only bloom ported so far), tonemap/grade gating
(bug-1171), MSAA cvar (bug-1123), character shadows (bug-1209).

Two structural gl2 lessons worth keeping:
- **Frame-buffer persistence creates ghosts** (bug-1140): `tr.renderFbo` persists across frames, so a
  frame with **no scene submitted** (fullscreen menu) still shows the last 3D content. The fix is a
  first-2D-draw clear, not a draw-order change.
- **Don't guess at render order** (bug-gl2-decal-red-dds, bug-gl2-viewmodel-over-menu): both were
  explicitly left unfixed rather than risk regressing 2,370 working DDS textures / working
  HUD-over-3D compositing. Two of the most disciplined entries in the log.

---

## T11. Same-frame spawn -> model -> solid race

**bug-865, bug-829, bug-962.** MOHAA **defers `setmodel`**, so `getmins`/`getmaxs` read **zero** in the
same frame an entity is spawned - `solid` then links a zero-size box and the object is non-solid.
Fix pattern: "framedefer" - Phase A spawns + models + transforms everything, then a frame boundary,
then Phase B reads bounds and solidifies. Related: `getmins` returns **base** bounds, so per-entity
`scale` must be multiplied in manually.

---

## T12. Process traps (not code)

- **Sub-agent hallucination reaches production.** bug-298 and bug-1067 both shipped a script command
  that exists nowhere in the engine, parse-killing a whole file. Verify any claimed command against
  the engine source before it lands.
- **Trusting the record over the code.** bug-1184 explicitly reverted bug-1173's `+180` roll
  correction as an unverified guess. See `open_defects.md` D-1.
- **"Verified" without a playtest.** 17 entries carry an explicit `fix_verified: false` field
  (bugs 070, 072-074, 088-089, 091-092, 095-096, 098-100, 168, 229-231) - the only structured
  status marker in the log, used briefly in June and then abandoned. Everything after it is prose.
- **Duplicate entries.** bug-739 and bug-750 are the *same* defect logged twice with identical text;
  bug-1051 and bug-1052 are the same none-cast storm. Id gaps are **not** data loss: 632 of the
  ids in `bug-1..bug-1222` were never assigned, and all 8 `.bak` files were diffed - they contain
  **zero** entries absent from the current file.
