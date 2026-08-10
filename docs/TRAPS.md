# TRAPS — every way this project has broken itself more than once

**The highest-value file in the doc set.** Each entry is a failure family that recurred. Read the
**Tell** first — that is what you will observe. Status legend in
[SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md#status-vocabulary).

## Quick index

Status: **!** = open now, **~** = recurring, blank = fixed/known pattern.

[T1](#t1)~ Morpheus parse killers · [T2](#t2) Generators corrupt the files they write · [T3](#t3)~ Silent-veto bugs · [T4](#t4)~ A capacity family has more members than you think · [T5](#t5) `$player` is an array; NIL ≠ NULL; storms are sequential · [T6](#t6)~ What you shipped is not what loads (pak / shader / extension order) · [T7](#t7) Cvar registration, flags, and exec order · [T8](#t8) Server→client stufftext is a lossy, filtered channel · [T9](#t9) Same-frame spawn → model → solid race · [T10](#t10)~ Deploy gaps · [T11](#t11)! Trusting the record over the code · [T12](#t12)! Name collisions between two identically-named trees · [T13](#t13) Guessing at a mechanism in a high-blast-radius subsystem · [T14](#t14)! Static audits pass while a live boot throws hundreds of errors · [T15](#t15)~ Harness and reproduction gotchas


---

<a name="t1"></a>
## T1 — Morpheus parse killers: one bad token silently kills the WHOLE `.scr`

**Recurred under 15+ bug ids:** 089, 298, 331, 348, 402, 533, 739/750, 910, 962, 1067, 1069, 1105, 1205, 1283, 1285.

**Check before you ship** — the three scanners catch disjoint classes, so run all three:

| tool | catches | blind to |
|---|---|---|
| `docs/tools/depthscan2.py` | brace/label depth (never negative; 0 at each column-0 label) | everything below |
| `docs/tools/linecheck.py` | a line **starting** with a binary operator | everything below |
| odd-quote scan (comment- and string-aware, per line) | unterminated / multi-line string literals | the rest of T1 |

The log names only the **first** offending line, never all of them: bug-1283 had two multi-line strings in
one file, and fixing just the reported one would have left the file equally dead. Fix the class, not the line.

**Tell:** a feature silently does nothing. **Never an error at the failure site.** Every `::` call
into the file logs `Script was not properly loaded`. If a whole subsystem went dead at once
(bug-533 killed helmet + sandbag + medkit + emotes together), suspect the shared bus file.

**Mechanism:** the compiler is all-or-nothing. Any syntax error kills the entire file and the map
then runs with no script at all — raw team menu, unstartable.

**Confirmed triggers, each with the bug that found it:**

| Trigger | Bug |
|---|---|
| Command syntax on an `EV_GETTER` property (`local.e getmins`) — must use property syntax | 910 |
| A script command that does not exist because a sub-agent invented it (`userinfo`, `getcurrentdmweapontype`) | 298, 1067 |
| A function call inside a vector literal | 348 |
| A function call **and** a vector literal in one expression | 402 |
| Parenthesised arithmetic / a bare negative `(-1)` | 1069 |
| An empty-array literal `[]` — morlang has none | 1105 |
| An unquoted `+`/`-` directive argument: `surface X -nodraw`, `surface X "+skin1"`. Valid TIKI frame-command syntax, fatal in script (`unexpected TOKEN_PLUS`) - **quote it**. The depth scan cannot catch this class; braces still balance. | 533, 1308 |
| A leading `&&` or `\|\|` on a continuation line | 739/750 |
| A real newline inside a string literal — from a generator, or hand-typed as a multi-line banner | 331, 962, 1283, 1285 |
| A backslash in a script path (resolved to `coop_modhelmet.scr`) | 1205 |
| Em-dash, UTF-8 BOM, any non-ASCII | (CLAUDE.md, longstanding) |
| Duplicate label; label/brace mismatch | (CLAUDE.md, longstanding) |

**Also NOT a parse killer, contrary to an older note:** `spawn <class>` **with** inline keyvalues is
fine — 192 working occurrences including `main.scr`. `KNOWN_WORKING_STATE.md` still forbids this;
it is wrong. See [90-folklore.md](90-folklore.md).

**Fix / check:**
1. **`developer 1` is mandatory** — compile errors are developer-gated at three call sites
   (`fgame/scriptthread.cpp:2858`, `:2869`, `:2883`). Without it the failure is *completely* silent.
2. **Raw brace counts are an invalid check.** Two opposite errors cancel and the count balances on a
   broken file (bug-239). Comment and string braces are miscounted. Use a **running-depth scan**:
   depth must never go negative, and must be 0 at every column-0 label (internal `goto` labels may
   legitimately sit at depth 1).
3. The three scanners now live in `docs/tools/` and all three run clean on the current tree
   (`depthscan2.py`, `linecheck.py`, `quotecheck.py`, plus `scrlint.py`). The older note here saying
   the depth scan "no longer exists" was true only of the `scratchpad/` copy — corrected 2026-08-08.
4. Verify any claimed script command against engine source **before** it lands.

**Live status:** clean (re-scans 2026-07-29, 2026-08-08) - but bug-1027 has exactly this
signature: `maps/e3l4/outro.scr` "was not properly loaded" + a 251x cascade.

---

<a name="t2"></a>
**`thread <label>` inside a boolean is ALWAYS TRUE (2026-08-10, bit 5 files at once).** `thread` starts the
label asynchronously and evaluates to a HANDLE, not to the return value, so
`if( x && thread foo::bar )` is `if( x && <truthy> )`. Five `anim/disguise_*.scr` gates were written
this way and therefore never guarded anything for years. Use `waitthread` when you want the value.
Corollary: because the branch they guarded ends in `end`, every statement BELOW it was unreachable
whenever the branch fired - four of them, including the squad-wide papers pass. **When you fix a
condition that was always true, audit what sits below its `end` as well.**

**`continue` in a `while` loop whose index advances at the BOTTOM = infinite loop = server hang
(2026-08-10).** `for` runs the increment on `continue`; `while` does not. `aihandler.scr`'s actor
sweep is a `while` at `:302` incrementing at `:484` - a `continue` anywhere between them spins
forever. Wrap the body in an inverted `if` instead. Check the loop KIND and where the increment
lives before writing any early-skip.

**Retail game data is NOT all inside the .pk3 files (2026-08-10).** `den_m2l2_258p.wav` - a real 14.2s
voiced PA line - lives loose at `main/sound/dialogue/m2l2/g/`, not in any pak. Five separate scans across
110 pak archives concluded "this audio does not exist"; it was sitting on disk the whole time. **When
checking whether a retail asset exists, search the loose game directories as well as the paks** - the
engine mounts both, so absence from paks proves nothing.

## T2 — Generators corrupt the files they write

**Bugs:** 259, 331, 480, 962, `bug-ps-home-var`.

**Tell:** the output looks right in a diff and is silently rejected downstream. TIKI in particular
**drops bad aliases without a word.**

**Every instance is a TOOL writing project data, not a human editing it:**

| What happened | Bug |
|---|---|
| Bytes read out of a `.pk3` (already CRLF) written back through Python **text** mode → `\r\r\n` on 434 lines. TIKI silently dropped **every** animation alias in `anims_shared.txt`, killing the salute emote. | 259 |
| A bash-heredoc Python generator collapsed the two-char `\n` escape into literal newlines in 4 string literals → T1 parse kill. | 331, 962 |
| A shader generator's brace matcher mishandled mixed CRLF/LF plus `//`-commented braces, emitting blocks missing closing braces (45 open / 43 close) → white-square HUD icons. | 480 |
| A **texture upscaler** preserved tiling correctly (3x3 tile -> resize -> crop centre) and then ran UnsharpMask on the CROPPED result. A convolution clamps at the border, so it invented new edge pixels and reintroduced the exact seam the tiling existed to prevent - measured 14x worse on `ocean1b`. Lanczos negative lobes separately overshot a deliberately-capped alpha (189 -> 255). Fix: sharpen **inside** the tiled space before cropping, and clamp each channel back to the source range. | 1247 |
| A PowerShell harness assigned `$home`, a **built-in automatic variable**. The assignment silently no-op'd and logs landed in the user profile. | ps-home-var |

**Rules that came out of it:**
- Any file whose content comes from zip bytes must be written back in **binary** mode. **This
  applies to the READ side too, and to ordinary repo files.** `open(p, encoding=...)` performs
  universal-newline translation on read, so a CRLF file arrives as LF; patterns you built with
  `
` then match nothing, and writing back with `newline=""` flips the **whole file** to LF.
  Both halves fail *silently* — `str.replace` returns the string unchanged rather than raising.
  Edit `.scr` in `rb`/`wb` throughout, and note the tree is **not uniform**: `challenges.scr` is
  CRLF, `lobbyui.scr` is LF-only. Detect per file, and **assert the match count before every
  replace** — that assert is what caught it. (bug-1363)
- **Never** emit script files through a bash heredoc.
- **Verify the invariant you claim to preserve, against the ORIGINAL.** The seam regression above was
  caught only by measuring edge-wrap error on output vs input per file. "It looks fine" would have
  shipped it. Same class as the count/balance asserts: cheap, mechanical, and it fired first try.
- **Assertion gates, not review.** Review never held. What worked: balance asserts, zero-stale-ref
  asserts, count asserts (`assert NS == 76`), bug-1009's connectivity flood-fill gate. Make the
  generator fail loudly rather than trusting the reader.

---

<a name="t3"></a>
## T3 — Silent-veto bugs: the feature never ran, so nobody could observe it

**This is the project's most expensive recurring *shape*.** Not one subsystem — a pattern.

**Tell:** "we built X and it does nothing / has no effect / can't be felt." Before tuning X, **prove
X executes.**

**Confirmed instances:**

| Feature | Why it never ran | Bug |
|---|---|---|
| **All AI grenades** | `GrenadeWillHurtTeamAt` compared `.length() < 65536` — i.e. any squadmate within 65,536 **units** (the whole map) vetoes the throw. Actors auto-squad-merge at first shots → ~100% of offensive grenades AND the kick/return chain suppressed. Fixed to `.lengthSquared()` (256u blast radius). | actor_anim_audit |
| **Officer Stuka + binoc airstrike** | An up-trace to detect a ceiling **hits the skybox brush** (sky brushes are `CONTENTS_SOLID`), so low-skybox maps read as "indoors" and silently disabled both. Fixed by testing `SURF_SKY` (0x4) — via int div/mod, since MOHAA has no bitwise AND. | sky_trace |
| **`s_sfxduck` (two attempts)** | Server-stuffed SETs of `CVAR_ARCHIVE` cvars are **dropped** by `CG_IsSetVariableAllowed` unless whitelisted. Two earlier attempts silently did nothing. | sfx_duck |
| **AI tactical retreat** | The engaged-check required `self.enemy`, a formal target lock that **scripted damage never sets**, so it never committed. | 1104 |
| **`MAX_SNAPSHOT_ENTITIES`** | A file-local `#define` stayed at 1024 for 8 days while everything downstream was raised to 2048. Entity 1025+ dropped by a bare `if (full) return;` whose own comment read *"silently discard entities"* — **no `Com_Printf`, zero evidence in any log.** | 1186 |
| **`cg_dbnoEyeDrop`** (3 placements) | Ran, but its write was **discarded downstream** twice (eye rebuilt from the model tag; view-height smoothing hard-assigns `origin[2]`). v1 silently moved the THIRD-person pivot instead. See "the write is overwritten" below. | 1238 |
| **The `SHIPPED-CODE-DISABLED` class** | Squad brain, morale, tactical retreat and the whole `coop_aiDynamic` layer are wired into `main.scr` behind gates testing `== "1"` on cvars **seeded in no shipped cfg**. They have never run for a player. | see [OPEN.md](OPEN.md#never-ran) |
| **m3l1b's FLAK 88s** | `startFiring` on `$88mm_weapon1/2` never fired: they are class **`Animate`**, not `TurretGun`, so the whole turret API silently fails. A follow-up `setAimTarget` fix was wrong the same way — correct `TurretGun::Think` analysis applied to an entity that was never a TurretGun. **Check the entity's CLASS before reasoning about its API.** | 1553 |
| **Service Record `coop_srsync`** | A client console command wired to a UI `stuffcommand`, which **never executes** from the disconnected menu - so five successive rewrites living inside `CL_SyncSR_f` could not take effect and the symptom was byte-identical every time. Work that must run on the main menu belongs in `CL_Init` (proven to run) or in `exec`+`seta` builtins. | 1544, 1546 |
| **47 shipped challenges** | v1.2.1 added ~50 `chal_def` rows and none of the hooks meant to feed them. `chal_bump` early-exits when `level.coop_chal_statN[stat]` is NIL, so an unbumped stat is a **no-op, not an error** — the rows show in the Service Record and can never be completed, and every static check passes. Corollary that cost two duplicate challenges: **absence of a hook is not absence of a feature** — check `chal_def` by title and feat, never by whether a producer exists. | 1596–1598 |
| **A whole map's lighting + effects (e2l1)** | A bare `level waittill spawn` in a retail sub-script. In coop that event has already fired, and a failed `waittill` **does not wait** - so the script ran before the map's entities existed. See the shape note below. | 1294 |

**Three further instances** (gl2 colour grade, the AI maneuver mover, `coop_weather_init`) are in
`docs/archive/traps-t3-archived-rows.md` — each one's *shape* is already taught above or in T1, so
only the evidence moved, not a lesson.

**The `waittill`-already-fired shape recurs on every remaining map.** The log line is
`invalid waittill spawn for 'Level'`, which reads like a warning but means "this script just ran at the
wrong time"; the damage surfaces elsewhere as NULL-listener errors. A failed `waittill` does **not**
abort - it simply does not wait.

- **Fix:** `waitthread coop_mod/replace.scr::waitTillSpawn` / `::waitTillPrespawn`.
- **Do NOT bulk-replace.** 191 bare `level waittill` sites ship; most are in briefing/lobby maps where
  the wait is legitimately reached first. **The runtime log is the oracle** - fix only the sites that
  actually throw, per map, as each is played. Same shape as [T14](#t14).
- Retail sub-scripts absent from the mod tree: extract into `maps/<map>/`, change **only** the
  offending line, say so in a header comment.

**A second shape, same tell: the write executes and is then overwritten.** "Does nothing" does not
prove the code is unreached - something downstream can clobber it. Proving execution is necessary but
**not sufficient**: also prove nothing later writes the same field. In a render/view path, grep the
whole function for every assignment to that field and prefer the LAST write site. The dangerous
variant is a misplaced write that still lands somewhere real (bug-1238 moved the 3P pivot) - then it
is not a no-op but a silent corruption of a neighbouring feature, possibly one being tuned right then.

**The UI corollary — never trade a working widget for an unverified one.** A `.urc` cannot be run or
diffed from here; the only oracle is the user's screenshot, so rewriting a widget that already works
is a blind bet — six attempts at one Service Record checkmark each replaced a functioning pin box and
each came back worse (bug-1546). **Add alongside it, or wait until someone can see it render.** On any
surface you cannot observe, a failed change costs not one edit but the thing that already worked.

**The cure that works:** an autonomous verification rig — its real value is catching a feature that
**silently doesn't fire**, which "looks-right, go-check" never would. And when you fix a
silent-discard branch, **add the warning even though you also raised the limit** — `sv_snapshot.c:549-553` does.

---

<a name="t4"></a>
**A guard can key on data that does not exist yet at the moment it runs (2026-08-10, measured).**
The planned scene-actor exemption tested `alarmthread != NIL`. Instrumentation showed
`coop_apply_personality` fires on all 55 germans **23 seconds before** `alarm_system_setup` assigns
any `alarmthread` - so the exemption would have matched NOTHING, shipped clean, and passed its own
acceptance check vacuously. Same class as a director that tags actors before the map has named them.
**Before writing a heuristic, print the keys it depends on and confirm they are populated at that
instant.** This is why the fix pass is instrumented first and repaired second - A3 before A4.

## T4 — A capacity family has more members than you think

**Bugs:** 891, 892, 914-935, 1186, 1214, 1582; the whole entity-pool saga.

**Tell:** things vanish, alias to each other, or corrupt at high entity/model/sound counts. Often
**no log line at all**, because the overflow branch discards silently.

**The archetype — `maxentities 2048`:** `coop_mod/server.cfg` shipped `set maxentities 2048` for
*years* while `GENTITYNUM_BITS` was 10 — a hard wire cap of 1024 with slots 1022/1023 reserved as
`ENTITYNUM_WORLD`/`NONE`. The setting **added no entities; it disabled `AllocEdict`'s overflow
guard**, so the allocator handed out the world slot. That one lie produced a weekend of
use-after-free minidumps (`Sentient::FindItem`, `Entity::updateOrigin`, `Player::UpdateStats`,
`Sentient::NextWeapon`) — and, we now believe, the AI glitching that got decapitation reverted.

**Sub-lessons, each bought with a crash:**

- **A "comprehensive sweep" that greps only *suspected* files is not comprehensive** — bug-925
  crashed in `sentient_combat.cpp`, missed by bug-920's sweep.
- **Fix the producer, not just the consumers** — `AddItem` appended entnums with no duplicate check
  while removal took only one occurrence (bug-920).
- **Non-NULL is not enough**: a recycled slot may hold a *different class*. Guards were upgraded to
  `item && item->isSubclassOf(Item)` (bug-919).
- **Audit bare array sizes, not just constant names** — `tr.skel_index[1024]` (bug-932b);
  `processed[MAX_ENTITIES]` where `MAX_ENTITIES` is the renderer *refentity* cap 1023, **not** the
  gentity count (bug-935); `MAX_SKELMORPH 12800` silently out-of-bounds (bug-1214). This class has
  now paid out **three separate times** for the invisible-actor symptom alone (bug-932 gl1,
  `renderergl2/tr_local.h:2339` gl2, bug-1135 `R_AllocModel`).
- **Map the whole producer→consumer chain in one pass** (bug-1186's `MAX_SNAPSHOT_ENTITIES`).
- **A protocol raise ships four binaries** — see [ENGINE.md](ENGINE.md#protocol-coupling).
- **One capacity grows while nobody touches the code: `MAX_CVARS`** (bug-1582). It is consumed by
  *archived* content: `omconfig.cfg` reached **3019** cvars (Service Record ~1500 over ~303 rows,
  armory locks ~500) and opening the SR binds **942** at once, crossing 4096 a month after bug-598
  raised it 2048->4096. Doubling is headroom, not a cure. Now 8192 + an 80% warning; **exe-only**.

**The best worked example in the codebase - `MAX_SOUNDS`.** Read
`openmohaa-hzm/code/qcommon/q_shared.h:1690-1755` **in full** before touching any capacity constant;
that comment is the canonical copy and is not reproduced here. It enumerates the four binding
constraints **in the order they bite** - configstring layout (`CS_AXIS = MAX_SOUNDS + 2393`, broke at
2000, bug-1179), reliable commands (`MAX_RELIABLE_COMMANDS`, must stay a power of two, bug-1183 twice),
the 11-bit `sound_index` wire field that **silently truncates**, and `MAX_GAMESTATE_CHARS` - tags each
with the bug that found it *including the two failed attempts*, and backs it with a compile-time
`#error` so the rule fails at BUILD time instead of silently.

**Do this for every capacity constant: turn the rule from a comment into a build break.**

---

<a name="t5"></a>
## T5 — `$player` is an array; NIL ≠ NULL; storms are sequential

**Bugs:** 1049, 1051, 1052, 1054, 1065, 1104; the 4-player sweep.

**Tell:** thousands of identical `Script Error` lines. **Solo boots cannot reproduce any of it.**

**Three distinct modes:**

1. **`Cannot cast array to listener`** — vanilla SP scripts treat `$player` as a single entity, but
   with **2+ connected players it is a 1-indexed ARRAY**. `$player.origin`, `turnto $player`,
   `isAlive $player` all throw. Repair idiom: an **inline `$player[i]` scan** with a per-element
   NULL guard, or `$player[1]` with a NULL host guard. ⚠️ This line used to recommend
   `exec coop_mod/replace.scr::player_closestTo self` — do **not** reach for that first; see the
   cross-file-helper trap below, where that exact label returned NULL on 90/90 measured samples
   while an inline scan of the same players succeeded (bug-1665).
2. **`Cannot cast none to <type>`** — a `level.*` timing global the vanilla SP init would have set is
   never set in coop (`level.thundertime` / `windtime` / `shuttertime` / `rainvolume`).
   `weather.scr:378` alone threw **8,662 times**. Fix: NIL-guards restoring documented vanilla defaults.
3. **Stale pointers that PASS a NULL guard** — bug-1054's `coop_trackTankTarget` had no `else`
   branch, so a freed player ref lingered and evaded `== NULL`.

**⚠️ Guard with BOTH.** `NIL != NULL` and coop hits both. bug-1065 hardened `xp_award` with
`== NULL || == NIL` because `level.coop_smoke_player` is only ever assigned, never initialised. The
currently-open bug-1220 (12× "applied to NULL listener" on e2l2) is this exact cure.

**⭐ THE META-LESSON — SEQUENTIAL STORMS.** Fixing one class lets maps progress **further**, exposing
the next class. The `$player` array-cast fixes are literally what unlocked the none-cast storm. **A
storm blocks map progression and hides every storm downstream.** Budget **2–3 fix→re-sweep passes**.
A clean sweep after one fix means nothing.

**Root cause of the biggest storm:** `addon_*` markers carry their model in `$ai_model`, not
`.model`, so `spawner_create` recorded NIL and the engine spawned `models/nil.tik` in a loop — an
entity leak as well as log spam (`global/spawner.scr:95-138`). Per-map before/after counts for the
2026-07-22 52-map tour: `docs/archive/traps-measured-wins-2026-07-22.md`.

**The proven repair pattern:** extract the retail gag verbatim from `mainta/pak1.pk3` into the mod,
change **only** the single-entity `$player` refs, add NULL host guards, leave everything else
byte-identical. See `gags/t2l4_start.scr:1-2`, `gags/t3l1_enemyspawn.scr:2`.

**Still open:** `global/vehicle_warning.scr` (4,270 casts, second-worst source) was **never
extracted** — the retail version is still live. And a second vehicle-crew spawn path on t2l2/t3l2
that the `truck_load` guard does not cover.

---

<a name="t6"></a>
**Entities as `thread` parameters can arrive NIL — and a cross-file helper can return NULL
outright (bugs 1624, 1632, 1665: three sightings).** Numbers always
bind; a player or model entity passed to `thread label a b c` may not survive the boundary (and an
ENTITY-thread `ent thread label x` binds at most ONE arg). The reliable pattern: park the entity in
a **level array keyed by numbers** (`level.coop_bpEnt[n + "_" + entnum] = ent`; precedent
`level.coop_itemPapers`) and pass only numbers; re-read the array each tick, which also self-heals
across respawns.

**⭐ The 2026-08-10 escalation (bug-1665, NINE attempts).** It is not only parameters. A
`waitthread <otherfile>::<helper>` can return **NULL** while an inline scan of the *same data on
the same tick* succeeds. `player_closestTo` returned NULL on **90 consecutive measured samples**
while a probe twelve lines below read both players fine (`hp=750 team=allies act=1 noclip=0`) and
printed a `want=` entnum matching a live player. Contributing shape: that label is declared with
TWO params (`local.object local.origin`) and every caller passes ONE, so `local.origin` is an
unset local inside the function. **Diagnostic rule: when a helper "returns nothing", do not
re-derive its inputs — print INSIDE the helper and inline the same scan in the caller. If the
inline scan works, stop using the helper.** Eight of the nine attempts failed by reasoning about
which filter rejected the player; the ninth printed all four filter fields and proved none did.

## T6 — What you shipped is not what loads

**Bugs:** 157, 247, 499/525/530/921/922 (a 5-round saga), 1129, 1190, 1216.

**Tell:** an asset edit has no visible effect, or a "black" surface appears, or a texture you never
touched changes.

**The load-order rules, in the order they bite:**

| Rule | Consequence |
|---|---|
| `.dds` beats `.jpg`/`.tga` | `R_LoadImage` rewrites the extension to `.dds` and tries `LoadDDS` **first** whenever texture compression is on. A same-basename stock `.dds` always beats your HD `.jpg`. This made 881 upscales dead. Disabling `r_ext_compressed_textures` is **not** a fix (~1400 stock-`.dds`-only textures would vanish) — ship DXT `.dds` overrides with a full mip chain. |
| The engine tries `.jpg` **before** `.tga` | Menu art in particular |
| Shader **NAME** overrides lose the reverse-concat race | Whole-**FILE** overrides win, because the filesystem dedupes by filename and the coop pak mounts last (bug-921 used bug-525's whole-file pattern on `scripts/equipment.shader`) |
| `zzzzzzzz_*` sorts after `zzzzzz_*` | bug-1190 |
| `.tik` surface directives must match the `.skd`'s real surface names | else `TIKI_InitTiki` drops them (bug-1216) |
| Homepath `maintt/` beats basepath; loose files beat paks | **bug-1633 (2026-08-09): the live launch profile runs `fs_homepath G:\mohaa-gl2\home` - stale `autoexec.cfg`/`coop_defaults.cfg` in its `maintt/` silently shadowed every deployed cfg change; `build.ps1` now deploys cfgs to all three targets (GOG maintt, APPDATA maintt, gl2-home maintt).** bug-595 lost a session to a stale **0-byte** `omconfig.cfg` decoy — **which is still on disk** at `%APPDATA%\openmohaa\maintt\omconfig.cfg`, 0 bytes, 2026-07-04 |

**⭐ THE FINAL ANSWER when a name is contested** (bug-922, closing the 5-round black-pouch saga):
**stop fighting for the name.** Mint a NEW shader name existing only in the coop pak, pointing at a
PRIVATE texture path also existing only in the coop pak, and retarget the `.tik` surface.

**⭐ The diagnostic tell:** if a "black" surface shows per-face **shading**, a lit default shader is
drawing it and **your identity def is not reaching that surface at all**.

**⭐ The timing variant — a playtest log only testifies about the build it loaded** (bug-1610).
`coop_enigma.shader` existed, yet the log still said `Couldn't find image file for shader enigma`,
reading as "the shader is wrong". The client loaded at 23:34 and quit at 23:37:11; the file was
packed at **23:38:06**. **Before treating a log as evidence about a new asset, compare the pk3
entry's timestamp (`zipfile.getinfo(name).date_time`) against the `InitGame` line** — a
stale-by-one-build log is indistinguishable from a real defect. Verify fixes by reading them back
**out of the deployed pk3**, not the source tree.

**⭐ Imported third-party skin packs are this trap with the blast radius reversed.** A 2002-era
MOHAA skin pk3 routinely *redefines* stock shader names rather than minting its own, and because
the coop pak mounts last the import wins — silently repainting every other model in the game.
Measured on a 39-pack sweep (2026-08-04, `docs/proposals/skin_batch.md`): `User-tr_fighter_pilot`
redefines 15 `viewsleeves*` shaders — every first-person sleeve in the game, for one pilot skin;
`user-Recon-MP` redefines stock `45holster` to point at a `holster.tga` it does not ship, breaking
the holster on *all* skins; `zzz_krugerland_MP_skin` collides on 7 mod-tree names. **Before
importing any external asset pack, diff its top-level shader block names against
`hzm-mohaa-coop-mod/scripts/*.shader` and against the retail paks, and diff its
`models/player/*.tik` basenames against the stock tiks — a matching tik basename *replaces* the
stock model instead of adding one.** Both checks are two greps; the one-off scripts that did them
(`packreport.py`, `texcheck.py`, `analyze.py`) were lost with the scratchpad — the surviving
verifiers live in `docs/tools/`. Note also that `map foo.tga` resolves
extension-agnostically, so a shader naming `.tga` beside a shipped `.jpg` is **not** a missing
texture — check all extensions before calling a pack broken.

**Related generated-asset hazard:** ESRGAN upscales have shipped hallucinated worm noise
(bug-1129), a GPU-corrupted all-black `netgame_a/b` that blanked the server browser (bug-247), and
29 overridden **vanilla** menu textures (bug-157). **Brightness-check output before commit**;
ESRGAN is for photos and text and corrupts 1–2px chrome.

---

<a name="t7"></a>
## T7 — Cvar registration, flags, and exec order

**Bugs:** 682, 710, 918, 1125, 1152, 258, 1148.

| Trap | Tell | Bug |
|---|---|---|
| **Exec order** — the engine execs `default.cfg` → saved config → `autoexec.cfg` **LAST**. `autoexec` was `seta`-ing ~200 curated defaults, so it overwrote every menu-changed setting on every launch. | Menu changes don't stick | 710 |
| **`Cvar_Get` ORs flags** — `r_lodscale` registered twice in gl2 (once `CVAR_CHEAT`, once `CVAR_ARCHIVE`) became cheat-protected and the slider silently reverted. | Slider reverts | 1125 |
| **A temporary flag flip persists** — flipping `r_entlight_scale` `CVAR_CHEAT`→`CVAR_ARCHIVE` for an A/B test **archived** the value 0.3 and dimmed every entity on every launch. | Global visual regression from a test | 918 |
| **Fail-open locks** — the armory padlock recompute zeroed all lock cvars then relied on a server push that might never arrive → un-earned weapons appeared unlocked. Redesigned fail-**LOCKED**. | Content unlocked that shouldn't be | 682 |
| **Clamped cvars lie to menus** — gl2 clamps `r_ext_multisample` to 4, so the 8× MSAA plate had to be repointed at the unclamped `r_ext_framebuffer_multisample`. | Menu offers a value the renderer refuses | 1152 |
| **`CVAR_ARCHIVE` probes poison every later boot** — an rcon probe set `r_toneMap 0`; it was silently retained and the feature never ran again. | See [T3](#t3) | 1148 |
| **`CVAR_CHEAT` probes are useless on a listen server** — `sv_cheats 0` clamps them straight back. `r_globalFogDebug` had to move to `CVAR_TEMP` (**and is still `CVAR_TEMP` at `renderergl2/tr_init.c:1926` — restore it**). | Debug view won't enable; identical captures | — |
| **Never `seta` a genuine user preference** in `autoexec.cfg` (`cg_adsShoulderRight`). | Preference resets each launch | 258 |
| **Never seed `coop_uiB*`/`coop_uiN*`** — wipes last-known challenge progress. | Progress lost | — |
| **⭐ `g_gametype` is LATCHED — the FIRST map of a launch runs before it applies.** `ui_startdmmap 2` sets it, the engine answers *"g_gametype will be changed upon restarting"*, and the real change lands at the **next** map load (observed 59 s later). So map #1 initialises with `g_gametype` **0**, `coop_mod/variables.scr:38` caches `level.gametype = 0`, and **`variables.scr:89`'s `if(level.gametype == 0){ end }` aborts the entire coop init** — after which every coop check takes its SP branch, including `replace.scr::waitForPlayer:105`, a raw `level waittill spawn` that throws — so it does not WAIT, and coop setup races on without players. Clients connect, get kits, never spawn. **Seed `+set g_gametype 2` on the command line.** | First map of a run has no coop; later maps in the same rotation are fine | 1492 |

**The structural fix is half-built:** `coop_defaults.cfg` execs **BEFORE** the saved config, so its
values are true defaults that a menu change overrides and persists. Migration out of `autoexec.cfg`
is incomplete, and any menu-wired cvar still `seta`'d there **cannot** persist. The two files are
disjoint, so they never fight. Current counts: `docs/generated/CVARS_COOP.md` — read them there,
never hand-copy them into this file.

**A cvar seeded nowhere** (no engine `Cvar_Get`, no cfg line) makes `getcvar` return `""` on a clean
profile, and a script fallback branch silently decides behaviour. **Calling such a cvar "default N"
describes a branch, not a default.**

---

<a name="t8"></a>
## T8 — Server→client stufftext is a lossy, filtered channel

**Bugs:** 595, 597, 736, 758, 772.

Two independent failure modes that between them made an entire subsystem look dead.

1. **Quote truncation** — `Player::EventStuffText` sends `stufftext "<cmd>"`, so any embedded quote
   in your value ends the wire-level argument early. Tell: client-side `Cvar ... does not exist`
   spam. **Rule: send values UNQUOTED, ONE statement per stufftext.** `;`-joined multi-statements
   are the other half of this. (bugs 736, 758)
2. **The whitelist** — `cg_servercmds_filter.cpp:304-316` silently drops server-stuffed `exec` and
   `vstr` as Reborn-exploit protection. That ate the **entire coop-detect handshake**
   (`coop_mod/cfg/detect.cfg`), the objectives setup, and the armory pick carry-over — presenting as
   **three unrelated bugs**. Fixed with scoped exemptions (exec only for mod-namespaced paths, vstr
   only for `coop_*`/user-created cvars). (bug-597)

3. **Whitespace collapse** — `Cvar_Set_f` (`cvar.c:936`) takes its value from `Cmd_ArgsFrom(2)`,
   which re-joins the *tokenised* args with a single space. So multi-word values survive unquoted
   (this is why the `coop_so1`/`coop_cp1` HUD pushes work at all), but **any run of whitespace inside
   the value is normalised to one space**. Never use space padding to align columns in a pushed
   string — the alignment is gone by the time the client sees it. Use a visible separator. (bug-1364)

Fourth mode: a bare name-bus token with no data character makes `playerExtract` return NIL and is
structurally undispatchable (bug-772).

**Related silent loss, on the receiving end:** a `.urc` widget placed below its menu's declared
canvas height **draws nothing at all** — `UIWidget::CalcClippedFrame` (`uilib/uiwidget.cpp:872`)
clamps a child to its parent's frame, so the height goes to 0. No error, no console line; the cvar
push works perfectly and the row is just absent. Either set `noparentclip` (`WF_DIRECTED`,
`uiwidget.cpp:1496`) or grow the canvas — prefer growing it, since the flag defeats clipping
everywhere. **Check the menu's declared size before adding rows to any panel.** (bug-1365)

**⚠️ Remote clients need the updated `cgame.dll` too.** Also: server-stuffed SETs of `CVAR_ARCHIVE`
cvars are dropped by `CG_IsSetVariableAllowed` unless whitelisted — see [T3](#t3).

---

<a name="t9"></a>
## T9 - Same-frame spawn / model / solid race

**Fixed; pattern known.** Full write-up moved to
[archive/traps-t9-spawn-race.md](archive/traps-t9-spawn-race.md) to keep this file under budget.
Short form: a `spawn`, its `model`, and `solid` cannot all land in one frame - step them.

<a name="t10"></a>
## T10 — Deploy gaps: the source is not what is running

**Bugs:** 089 (the mirror case), 930, 1172, 1219.

**Tell:** a fix that is definitely in the source has no effect in play — or a log line reports a
limit lower than the header says.

**Both directions have happened:**

- **Edited but never built/deployed** — bug-089: fixes "did nothing in-game."
- **Built and deployed when it shouldn't have been** — bug-1172: every `build.ps1` run during a gl2
  sandbox session pushed sandbox-only `MAX_SOUNDS 2000` / `MAX_ENTITIES 4095` / `MAX_TIKI_ALIASES
  8192` binaries into the user's **real install**. Remediated by reverting, rebuilding, redeploying.

**The exe is the usual gap.** `build.ps1` deploys the pk3s, `cgame.dll` and `renderer_opengl1.dll` -
but **not** `openmohaa.exe`, `game.dll` or `renderer_opengl2.dll`, which are hand-copied to the GOG root.
So the deployed set routinely spans several build dates, and a change can be live in source, in `.cmake`,
and *not* in the binary being run. A "verified" claim must name which binaries were deployed and when.
`build.ps1` refuses to deploy while the game is running - if you edited and did not deploy, everything the
user then tests is the PREVIOUS build, and every conclusion drawn from it is void.

**Rules:** a protocol-constant change ships **all four** binaries. `game.pdb`/`cgame.pdb` ship next to
their DLLs. Back up as `<binary>_pre_<feature>_bak.<ext>` — that hand-run convention *is* the
rollback system, and it has 157 entries and **zero** for `renderer_opengl2.dll`.

---

<a name="t11"></a>
## T11 — Trusting the record over the code  ⚠️ STRUCTURAL

**Corollary added 2026-08-02 (bug-1290): agreement between reviewers is NOT corroboration when they
share an upstream source.** A multi-agent audit reported "the injury vignette is permanently maxed
after any DBNO revive" as a confirmed live bug, and **two independent critique lenses each
independently confirmed it** — which is exactly what made it persuasive. It was false. All three had
inherited one unchecked premise from the same research pass: that `dbno.scr:49`'s `healthonly 9999`
puts 9999 into health. `Entity::EventSetHealthOnly` **clamps to `max_health`**, and
`player.cpp:8113` writes `stats[STAT_HEALTH]` as an already-normalised 0..100 percentage, so the
tracker cannot latch. The proposed "fix" would have been a real regression in the opposite direction —
hiding genuine low health after a revive.

**Rule:** before acting on a finding, verify its *load-bearing premise* against the code yourself, no
matter how many reviewers agree. Independent agents that read the same brief are one witness, not
three. It cost one wasted edit here only because the premise was cheap to check — two `grep`s.

**The commissioning example.** bug-1173 documents a `+180` roll correction on `maps/m1l1.scr` as
applied; bug-1184, hours later, **reverted it**. Both entries are correct and both are present — but
**the record only agrees with the code if it is read to the END.** A later session read bug-1173 and
stopped. **Read `docs/generated/FIX_INDEX.md` (file → ordered bug ids) rather than a single entry:**
one entry says what changed once, the ordered list gives the file's net current state. That index is
the fix for this trap and it now exists.

**Other record hazards:**
- **Wrong anchors are worse than no anchors.** `q_shared.h:1680` credits the `MAX_MODELS` 1024→2048
  raise to **bug-866**; the actual work is **bug-892**. A grep at a wrong path returns nothing and
  reads as "already fixed."
- **A later entry can silently reverse an earlier one**, and nothing in the schema says so. When you
  supersede a finding, **edit the original entry** rather than only appending — bug-1473/1474 were
  corrected in place on 2026-08-06 after being filed against the wrong files.
- **Ids are not all numeric** — ~25 use slugs (`bug-gl2-ztagmalloc`, `bug-ps-home-var`…). Numeric-only
  tooling silently skips them; `re.fullmatch(r"bug-(\d+)")` before `int()` or it throws.
- **Append, never rewrite.** A post-write hook once rewrote the log wholesale under its own schema,
  and `readJSON` returns a fallback on *any* parse failure, so one transient read failure = total
  loss. 523 entries had to be rebuilt from transcripts.
- **28 bug ids cited in source comments have no buglog entry** — including bug-237 (packer
  determinism, `build.ps1:11-15`), bug-241 (never deploy under a running game) and bug-239 (the
  brace-counting lesson). **For those, the code comment IS the only record.**

**⭐ The habit that works:** leave the correction **at the site**. `maps/m1l1.scr:1683`,
`coop_mod/loadoutpick.scr:436-440`, and `q_shared.h:1690-1755` are all self-documenting and all three
survived contact with a later session.

**Separately — when classifying REVERTED, separate "it broke" from "the user changed their mind."**
Only the former is a lesson. bug-787 reversed a locked-cosmetic design pre-release at the user's
request after two full generator rewrites; nothing was defective.

---

<a name="t12"></a>
## T12 — Name collisions between two identically-named trees  ⚠️ OPEN NOW

**There are TWO `_research` trees** and records conflate them:

| Path | Contents | Ship risk |
|---|---|---|
| `C:\mohaa-coop-dev\_research\` | design docs, audits, **the regression harness** | **None** — outside the mod |
| `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\_research\` | buildmode inventories, `coop_2player_sweep.md`, `coop_test_menu.md`, `director_dda_plan.md`, `hud_slot_map.md` | **Was shipped to players** |

`build.ps1:27`'s `$excludeTop = @("_notes", "_research")` only affects the **mod** tree. Until that
line — which is **uncommitted**, the only change in the workspace repo's working tree — releases up
to and including v1.1.55 packed design docs and retail script extracts into
`zzzzzz_co-op_hzm_mod_code.pk3` and shipped them to every player. Corroborated: the released pak is
272,839 B **larger** than the post-fix rebuild.

**Consequence to act on:** the regression harness — currently the project's **only** working
automated verification — lives in a directory named `_research`, a name the build script treats as
disposable. **Promote it out** before someone applies the exclusion logic to the wrong tree.

Related naming hazards: four uppercase map scripts (`M1*`, `M3*`, `M5*`, `M6*.scr`) sit alongside
lowercase counterparts — unchecked for case-collision inside a pak.

**The same trap one level down: two subsystems sharing a `level.*` name** (bug-1612).
`coop_mod/ambience.scr:42` owns `level.coop_ambEnt` as a **single `script_model`**; the telephone-gag
work later added `level.coop_ambEnt[alias] = emitter` as a **dictionary**. The entity wins, so every
indexed read throws `[] applied to invalid type 'listener'` — once per ambient, on every map. Skipped
not fatal, so nothing crashed; the sole casualty was m1l2b's ringing-telephone gag, which polls that
dictionary 100×0.1 s and so always burned 10 s and printed `PHONEGAG FAIL`. It shipped unable to work.
**Grep the mod tree before adding a `level.coop_*` name — the error names the type, never the other
owner.**

---

<a name="t13"></a>
## T13 — Guessing at a mechanism in a high-blast-radius subsystem  ⭐ THE ANTI-TRAP

**⭐ BISECT FIRST. A cvar bisect beats any number of hypotheses.** (2026-08-02, bug-1298.) When a
subsystem is large enough that a wrong guess costs a session, do not reason your way to the answer -
turn things off one at a time until the symptom moves. Six deployed hypotheses on the gl2 "white
distant objects" bug changed nothing; one bisect found it.

---


<a name="t14"></a>
## T14 — Static audits pass while a live boot throws hundreds of errors

**Bugs:** 1026, 1027, 1218, 1219, 1220, 1473–1490.

**Tell:** a map is graded clean by a read-through audit and then storms on boot. t2l2 was graded
**A−** statically and throws 265 errors on coop boot; it still reaches coop-ready, so it is
*degraded, not dead* — precisely why a read-through missed it. **A live boot is the only real test.**

**Absence does not log.** A parse error screams; a VO line that never plays, a trigger nobody walks
into, an alias resolving to nothing are all silent. Error-driven testing cannot find them by
construction — you need an **expectation manifest** (what *should* fire, extracted from the BSP
entity lump) diffed against **engine instrumentation** (what *did* fire). That is what the coverage
sweep is, and it is the reason all of the below was invisible until 2026-08-06.

**Settled 2026-08-06 by the 4-player coverage sweep.** 49 walker-valid maps produced **26,230 script
errors across 548 source sites**, none of which any static audit reported. They are not spread
evenly — they concentrate in **shared** files, so a few fixes repair many maps: `vehicle_warning.scr`
12,690 (48%), `gags/t2l3_friendly.scr` 8,694 (33%), `gags/t3l1_enemyspawn.scr` 972,
`global/spotlight.scr` 798, `coop_mod/officer.scr:1754` 666 (the mod's **own** code, all 48 maps).

**The dominant cause is `$player`-as-array** (see [T5](#t5)) reaching a retail SP script that
dereferences `.origin`. It is invisible in SP *and* in 1-player coop: `OP_UN_TARGETNAME` yields a
plain listener at exactly one match and a container only at 2+. **This class needs two connected
players to reproduce at all** — which is why years of solo testing never saw the largest error source
in the trilogy.

**A declaration with no producer is the same silence** (bugs 1596-1598, T3 row). Cross-reference
declarations against producers **mechanically, walking the whole tree** - a `maps/*.scr` glob misses
`maps/<map>/*.scr` and miscounted three wired challenges as dead.

---

<a name="t15"></a>
## T15 — Harness and reproduction gotchas

Each of these cost at least one session.

| Gotcha | Detail |
|---|---|
| **Check tools exist before citing them** | `scratchpad/` is wiped periodically. A working rcon client lives at `scratchpad/rcon.py` (rebuilt 2026-08-07) - if it is missing, rewrite it: the connectionless prefix is `b'ÿÿÿÿ'` and `lstrip("print
")` is a **character set**, not a prefix, so it eats the payload. In-repo tools that persist: `docs/tools/scrlint.py`, `hzm-mohaa-coop-mod/_research/cov_report.py`. |
| **rcon needs the direction byte** | Every rcon client must send the connectionless prefix `b'\xff\xff\xff\xff\x02'`. Without it the server logs `bad connectionless packet`, **silently runs nothing, and the harness still looks successful** — so every capture is wrong (bug-1143). |
| **The ESC menu cannot be opened with `keybd_event`** | SDL ignores synthetic keys. Use `rcon pushmenu dm_main` / `popmenu 0`. `dm_main` **is** the ESC board. |
| **Use an isolated homepath** | Harness cvar pollution once stomped the user's real `omconfig` (`r_customwidth`, fullscreen) and surfaced as a "4:3 bars" bug report (bug-1134). And `CVAR_ARCHIVE` probe values are silently retained by every later boot — force them in the boot cfg **and** on the command line. |
| **Coop join takes ~3 clicks and ~20s to settle** | Capture earlier and you get the 3P spawn pose with no HUD. |
| **`g_scriptcheck` + coop `game.*` vars = a fake crash** | `G_ArchivePersistant` `Com_Error`s on non-empty coop `game.*` vars if `g_scriptcheck` is on. Looks exactly like a crash. Force it 0. |
| **Load maps the real coop way** | `set ui_dmmap <m>` + `exec start_server.cfg` / `ui_startdmmap 2`. `devmap` is single-player and plain `map` does nothing on a running coop server. |
| **`.st` parse errors `ERR_DROP` the server** | Opposite of `.scr` silent-fail. And `LoadStateTable` needs a CLIENT, so **dedicated boots never parse it** — the first *listen* launch after any `.st` edit is the real test. |
| **An incremental fgame build skips a `.cpp` on a header-only change** | Touch the `.cpp` (cost a session on `actor.cpp`). |
| **`iprintlnbold` reaches `qconsole.log`; `println` does not** (without `developer 1`) | Use `iprintlnbold` for in-game bisect prints — but never ship dev prints to players. |
| **`rcon meminfo`** | The measurement tool for any renderer-zone question (`TAG_STATIC_RENDERER`). |
| **cdb / crash dumps** | Build RelWithDebInfo, reproduce, `.ecxr` for the **real** fault context - `0xc0000409` fail-fast masks an underlying `0xC0000005`. `game.pdb` ships next to `game.dll` so dumps resolve lines; `.symopt+0x40; .reload /i` force-maps a stale PDB. Some diagnoses come from the **Windows Application event log**, not the game log. |
| **Reproduction preconditions are load-bearing** | bug-1144 needed a **fullscreen menu over a LIVE session** — disconnecting does *not* reproduce it, because `UI_ClearBackground` clears depth once `clc.state <= CA_PRIMED`. Every earlier hunt saw a clean menu and concluded wrongly. |
| **Concentrate the test** | Morale break needs a *concentrated* map — m2l1's ~41 enemies never drop below the threshold under a localized damage-sim. |
| **The bot rig sets its own cvars** | A feature "verified" only by the rig may still be `SHIPPED-CODE-DISABLED` for players — the rig enables the gate itself. This is exactly what happened to the AI maneuver mover. |
| **Never attribute a log event by proximity to a map banner** | `COV MAPDONE` marks a map's **END**, so binning lines by "nearest preceding MAPDONE" labels every event with the **previous** map - off by exactly one, uniformly, and plausibly enough to survive review (it misfiled a 12,690-error storm and produced two bug entries against the wrong files). **A Morpheus script error prints its own `(path/file.scr, LINE)` - that pair is ground truth and needs no map attribution at all.** |
| **The engine TRUNCATES `qconsole.log` on every launch** | A driver that relaunches to make progress destroys the results it is collecting. Rotate the log per launch **and** have the reader scan `qconsole*.log` as a set — doing only one of the two silently loses runs (the observed symptom was a completion count going *down*, 34 → 32). |

---

## T17 — Script VALUE types: 'none', keyvalue strings, and who owns an event

Three variants of one failure: the value is not the type the reader assumes, and the thread dies at
that line while the caller still reports success.

**Reading a level var CREATES it with type `none`, and the engine then throws on it.** `int n = pv ?
pv->intValue() : 0` looks safe — it is not. `GetVariable` returns non-NULL for a variable that exists
but was never *assigned*, so the NULL guard passes and `intValue()` throws `Cannot cast 'none' to
int`. `coop_vehKill_monitor` merely *read* `level.coop_vehKills` each frame; that alone poisoned
`DrivableVehicle::Killed` so **no drivable vehicle on any map could be destroyed** — it aborted before
the explosion, the tank sat at negative health with `deadflag 2`, the VEHZOMBIE rescue revived it for
the next hit, and it read as invincible. **Always ASSIGN a level var before anything reads it**, and
prefer a type check over a NULL check on the engine side. (bug-1371)

**Map entity keyvalues arrive as STRINGS.** `#totalguys` / `#activeguys` compared against an int gave
115 errors a level in `global/parade.scr` and silently killed the parade spawn loop. `int()`-coerce
once at the top, not at each comparison. Same class as the parsed-`.dat` fog values. (bugs 1352, 1372)

**A command registered on `ScriptThread` is NOT a Player event.** `iprintlnbold` / `iprintln` live in
`scriptthread.cpp:225/234` only, so every `<player> iprintlnbold "..."` fails — 39 sites across 11
files, meaning those messages had *never once* reached a player. The Player-scoped equivalent is
`iprint <text> 1` (`player.cpp:1222`, `"sI"` = "prints a string to the player, optionally in bold").
Before calling `<entity> <command>`, confirm the command is registered on that entity's class.
(bug-1374)

**A bare identifier is a CONST STRING, and `int + conststring` CONCATENATES.** `local.wave1 +
local.wave2 + wave3 + 5` (note the missing `local.`) silently produced `"20wave35"`, and
`intValue()` on a string is `atoi` → **20**, against a gate waiting for 35. Total mission softlock,
no error. It is a *vanilla* typo, byte-identical in retail. (bug-1377)

**⚠️ Fixing a type error can UNMASK a latent logic bug.** That same line previously threw every
frame, and the throw aborted the parade's done-check — so the parade never stopped and the gate
happened to pass. Adding the correct `int()` coercion (bug-1372) made the comparison work, the
parade correctly stopped at 20, and the map became *unfinishable*. **After silencing a recurring
script error, re-test the feature it was firing in** — the error may have been load-bearing.

**Tell for all three:** a feature that "does nothing" with no crash, plus a `Script Error` line naming
a file and line you were not looking at.

---

## T16 — A failsafe that escapes a hang by calling code containing the same hang

**Bugs:** 1361 → 1366 (e3l4 supply/delivery), same shape as the AB41 and truck-unload failsafes.

A timeout around a blocking wait is only as good as the recovery path. The e3l4 supply failsafe bounded
`while (level.gotSupplies < 2)` at 45s and then recovered by calling
`global/jeepanim.scr::PassengerGetInJeep` — which **opens with `runto` + `waittill movedone`**. The
actor's whole problem was that it had no nav path, so the recovery blocked exactly where the original
did, one line before the `level.gotSupplies = 2` that would have released the mission. The soft-lock
moved rather than closing, and the second report looked like the first fix simply hadn't worked.

**Rule: a recovery path must contain no wait that the failure mode can block.** For actors that means
no `runto`/`walkto`/`waittill movedone`/`waittill turndone`/`waittill animdone` and no unbounded
`while (vector_length(...) > N)` distance loop. Seat/position them directly instead — take the **tail**
of the vanilla routine (everything after its movement), which is still the retail recipe minus the walk.

**Two engine facts make actor waits unsafe** (verified in source, bug-1368): `Unregister(STRING_TURNDONE)`
exists in exactly one place, `Actor::IdleTurn` (`actor.cpp:5032`), reached only from the anim/idle
thinks — no runner think calls it, so a failed `runto` pins the actor in `THINK_RUNNER` and any
`waittill turndone` requested there blocks **forever**. `waittill movedone` is safe: `CheckUnregister`
(`actor.cpp:7793`) fires it even on `parm.movefail`. So **`runto` → `turndone` hangs; `runto` →
`movedone` does not**, and every `while (vector_length(...) > N){ waitframe }` after a `runto` is
unbounded by construction. Ritual knew this — `e3l4/Bunker1.scr` has a commented-out
`waittill turndone` replaced by `wait 0.5`, with the identical live twin 30 lines below.

**Never invent an exit/placement offset when the model carries an authored one.** The e3l4 jeep
dismount took three attempts: `origin + (0 0 80)` (the roof — copied from `t2l2.scr:1468`, where it
is only safe because that ride has ENDED), then a 96-unit lateral guess (lands inside bunker
geometry), then finally `gettagposition "passenger_enter"` — the tag the artist placed for getting in
and out of that exact vehicle, which is walkable by construction and is the same tag the boarding
code uses. Vehicles carry `driver_enter` / `passenger_enter` / `*_seat` tags for precisely this.
An offset that works at one stop is a guess about free space at every other stop. (bugs 1367, 1370)

**Tell:** the same user report twice, with a failsafe log line present in between. Grep the recovery
path for `waittill` before shipping it, and check the *next* stage for the same shape — e3l4 had a
second identical spin in `deliverSupplies` waiting on two done-flags set at the end of those same
unbounded chains.

---

## Cross-cutting: the four questions to ask before "it doesn't work"

1. **Did it compile?** (T1 — `developer 1`, running-depth scan)
2. **Did it run?** (T3 — prove execution before tuning; check the gate cvar is actually seeded)
3. **Is the binary I'm testing the one I built?** (T10 — three binary states are live right now)
4. **Am I reading the record or the code?** (T11 — the code wins; read the record to the END)

## TIKI and sound-alias traps (found the hard way, 2026-08-03, e2l1 glider)

### A frame-command line inside `server{}` / `client{}` MUST start with a frame keyword
`TIKI_ParseFrameCommands` (`tiki/tiki_parse.cpp:113-133`) consumes the **first token of every line**
as the frame specifier. If it is not `start/first/end/last/every/exit/entry/enter` or a number, it
falls to `framenum = atoi(token)` — which silently yields frame 0 and **shifts the whole line left**:
`args[0]` becomes the first *argument*, and `fgame/animate.cpp:304/370` then fires an event named
after it. Retail `CG4Aglider.tik:332` and `:398` are bare `surface glider_body_glass -skin1 +skin2`
inside `bank_left`/`bank_right`, producing `Event 'glider_body_glass' does not exist` and no cracked
windscreen. **`enter` is a valid alias for `entry`** — do not "fix" that.

**The inverse is more dangerous:** in `setup{}` a bare `surface <name> shader <name>` is *correct and
required* — `setup` has no frame-specifier layer (`CG4Aglider.tik:9-20` are all bare). A regex for
"surface lines without a frame keyword" flags those as false positives, and prefixing them with
`entry` destroys every surface→shader binding on the model. **Validate by positive assertion on the
target lines, never by scanning for a negative.**

### A `ubersound` / `uberdialog` alias without a `maps "..."` spec never loads

The **narrow** spec is the same trap and easier to miss: `flak_snd_fire1..4` list `maps "m3l2 m5l2 m5l3 t1l3"`, so on m3l1b the alias simply is not there and the gun animates in silence. Proof is cheap - grep the session log for the wav name (`Flak88Fire`); zero loads means zero alias. Contrast `explode_flak88` (`maps "m e t"`) and `flak_snd_move` (`maps "m1 m2 m3 ..."`), which prefix-match and load fine on the same map. Verify the spec covers your map before touching anything else (bug-1548).
`bLoadForMap` (`cgame/cg_commands.cpp:4251`) prints
`ERROR bLoadForMap: <alias> alias with empty maps specification.` and returns false. The match is a
**prefix** compare (`Q_stricmpn(token, mapname, strlen(token))`), so `"e2l1 "` matches `e2l1.bsp`;
the working e2l1 dialogue aliases all end `maps "e2l1 "`. Un-commenting a retail alias is not enough
if the retail line lacked the spec. Symptom is silence with no PlaySound error.

### Per-map `includes <mapname...>` blocks gate anim registration (bug-1621, 2026-08-09)

Anim `$include`s inside `includes <map tokens>` blocks in `new_generic_human.tik` resolve at TIKI
LOAD by case-insensitive PREFIX match of each token vs `sv_mapname` (`TIKI_ParseIncludes`,
tiki_parse.cpp:320-374). A non-matching block is skipped with ZERO output at any developer level.
So the same spawn recipe animates on one map and floods `unknown animation` on another: m3l1b
lists `human_mg42.tik` (retail native nests), m2l2a/b and every custom map do not - the MG42 nest
gunner stood upright while firing. **Fix recipe:** add the pack to the UNCONDITIONAL coop include
set at the top of the mod's `new_generic_human.tik` (now mp44/bar/bazooka/thompson/coop_medic/
mg42). Cap is MAX_TIKI_LOAD_ANIMS 8192 / 13-bit net index; the m1l1 truck ride is the canary.

### "Missing" content is often CUT content that still ships
Before blaming the renderer or the coop layer, check whether the retail asset was ever wired up —
and search **loose files as well as archives** (`DFRUS_E2L1_GP1306`'s mp3 ships loose under
`maintt/sound/dialogue/`; a pk3-only search wrongly reported it missing). Four e2l1 glider defects
were retail authoring gaps of this kind, not bugs: a commented-out alias, 18/20 `cockpitBulletHit`
aliases never defined, the windscreen (above), and a fire/ember kit nothing references.

**But do not over-apply it: measured trilogy-wide, cut *dialogue* does not exist.** All **1,801**
map-bound VO aliases are referenced by some script (2026-08-06 scan). So when a line does not play,
the cause is always runtime, and there are only three: the thread that would play it died, the
trigger that would start it never fired, or the alias resolves to a missing wav. Check those, in that
order, instead of hunting for unwired content.

### Never leave a backup inside `hzm-mohaa-coop-mod/`
`build.ps1` packed a 6 MB `uberdialog.scr.bak_gp1306` straight into the shipped pk3. Write backups to
the scratchpad. Also: build.ps1's `Cache hit ... unchanged` line can be misleading — **verify a change
shipped by hash-comparing the source against the pk3 member**, not by reading the build log.

## Entities at health <= 0 that never died are UNKILLABLE (bug-1323)
`Entity::DamageEvent` early-outs on `health <= 0` (entity.cpp:2705) and script `hurt` routes
through it. An entity that crosses zero without its death completing visibly is entombed - no
shot, blast or scripted `hurt` will ever land again, and every `waittill death` waiter blocks
forever. A script failsafe MUST reset `self.health = 1` (script setter bypasses DamageEvent)
BEFORE the `hurt`. Vehicles are auto-rescued engine-side (Vehicle::CoopZombieRescue, `^~^~^
VEHZOMBIE` log line); other classes are not.

## ui_startdmmap silently re-pushes g_* server cvars from the archived menu values (bug-1326)
`UI_StartDMMap_f` (cl_ui.cpp:3422-3480) appends `set g_inactivespectate/g_inactivekick/
g_gametype/g_teamdamage/fraglimit/timelimit/sv_maxclients/sv_maplist/sv_hostname/cheats 0` from
the `ui_*` archived cvars to the command buffer AFTER any cfg that ran before it. Any `set g_<X>`
in start_server.cfg for those keys is stomped unless the `ui_<X>` twin is seeded alongside it.

## Scripted `surface head ...` silently hits the wrong LOD (bug-1332)
head1.skd (and likely other heads) contains TWO surfaces both named "head". An exact-name
surface command flips only the FIRST (Surface_NameToNum first-match); the rendered LOD stays
unchanged - no error, no warning. Use the retail prefix form `surface "head*" ...` which
applies to every match (entity.cpp:4237). Engine gore tiers are immune (they loop by index).

## ⭐ A `Script Error` does NOT kill the thread — it SKIPS the statement (verified 2026-08-06)
**This corrects a premise that shaped many earlier diagnoses, including several in this file.**
`ScriptException::next_abort` defaults to **0** (`script/scriptexception.cpp:30`), and
`ScriptVM::HandleScriptException` (`script/scriptvm.cpp:1915-1933`) only rethrows `if (exc.bAbort)`;
otherwise it prints `^~^~^ Script Error : …` and **returns**. The `catch` sits *inside* the
per-instruction loop, so execution resumes at the **next instruction**. Only **two** sites in the
whole VM set `next_abort = -1`: stack overflow (`scriptvm.cpp:1038`) and **command overflow**
(`:1867`) — the latter is `ERR_DROP` and really does take the server down (see t2l3, bug-1493).

**So read every error site as "this statement was skipped", not "everything below died."** The
consequences are different and often worse:
- **An `invalid waittill` means the script does NOT WAIT.** Everything below runs *immediately*
  instead of at the right moment — sequences fire before their preconditions, entities are touched
  before they spawn. That is why the `waitTillSpawn`/`waitTillPrespawn` shims still matter
  (bugs 1458-1469): they were fixing a real defect, just not the one the note claimed.
- A cast error inside a `while` body removes the *statement*, not the loop — which is exactly how
  t2l3 span 4,347 times with no yield and killed the server.

## Values parsed out of a .dat file are STRINGS - coerce before comparing (bug-1352)
The character-walking splitters (fogmode, blueprint, save files generally) return strings. Any
later `if( x > 0 )` against one throws "binary '>' applied to incompatible types 'string' and
'int'"; that statement is skipped (see above), so the assignment it guarded never happens while
the caller happily prints its success message. Wrap every parsed numeric in `float()` / `int()`
at load. Symptom shape: a feature works when set live in an editor but never when loaded from
its own saved file.

## A scripted conversation strands when a `waittill` outranges its guard (bug-1579)

Retail chatter helpers are written for single-player, where the talkers are always alive and idle.
Coop breaks all three assumptions, and each break has its own failure shape:

- **The `waittill` sits OUTSIDE the guard that started the anim/say.** No anim was issued, so nothing
  can ever fire `animdone`/`saydone` and the calling sequence stops there **forever**. Wait only on an
  actor you actually animated - record that in a local; never re-test the condition (one that was
  attacking when the anim was skipped, and has since calmed, passes the retest and waits for nothing).
- **`isalive` on a NULL entity throws, and a thrown statement is SKIPPED** — so the guard itself
  disappears and the body it was protecting runs unguarded. Test `!= NULL` first and *separately*.
- **`thinkstate != "attack"` is not "idle".** A CURIOUS / GRENADE / PAIN actor also runs its own
  think and overrides the scripted idle anim. Gate on `== idle`: `anim` runs at `THINKLEVEL_IDLE`
  (`Actor::PlayAnimation` → `SetThinkIdle(THINK_ANIM)`, `actor.cpp:10819`) and there is no
  `THINKSTATE_ANIM`, so a normal scripted exchange stays `idle` and is not silenced.

**Silence the LINE, never abort the THREAD.** The tail of these labels usually holds the RELEASE —
a `runto`, an `enable_ai`, a `type_disguise` — that hands the actors back to normal AI. Ending the
sequence early leaves them frozen: unresponsive, and dying on their feet with no death animation.
The one safe exception is a dead-end label nothing waits on (verified: `M1L3c` radio room).

Sites: `docs/proposals/conversation_guard_sites.json` - 196, of which **48 are do-not-guard**
(alarm cues; silencing those soft-locks a mission). Helper `replace.scr::convOk`. m6l1c done, 189 left.

## Archived dev-switch cvars latch across restarts (bug-1427)

A `seta`-archived mode switch (`coop_buildmap`) set once for an authoring session rides
omconfig.cfg forever and silently re-fires its branch on every later load - it broke campaign e3l4
twice in one evening, and editing omconfig.cfg from outside loses the race because the engine
rewrites it with the in-memory value at shutdown. **Any cvar that flips a map into a special mode
must be consumed one-shot at map init**: copy it into a level var in `main.scr::main`, `setcvar`
it back to 0 immediately, and make every reader use the level var - never a live `getcvar`.
