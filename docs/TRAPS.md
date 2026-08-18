# TRAPS — every way this project has broken itself more than once

**The highest-value file in the doc set.** Each entry is a failure family that recurred. Read the
**Tell** first — that is what you will observe. Status legend in
[SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md#status-vocabulary).

## Quick index

Status: **!** = open now, **~** = recurring, blank = fixed/known pattern.

[T1](#t1)~ Morpheus parse killers · [T2](#t2) Generators corrupt the files they write ·
[T3](#t3)~ Silent-veto bugs: the feature never ran · [T4](#t4)~ A capacity family has more members
than you think · [T5](#t5) `$player` is an array; NIL != NULL; storms are sequential ·
[T6](#t6)~ What you shipped is not what loads · [T7](#t7) Cvar registration, flags, exec order ·
[T8](#t8) Stufftext is a lossy, filtered channel · [T9](#t9) Same-frame spawn/model/solid race ·
[T10](#t10)~ Deploy gaps · [T11](#t11)! Trusting the record over the code ·
[T12](#t12)~ Name collisions between identically-named trees · [T14](#t14)! Your verification lied ·
T16 Failsafe recursion · T17 Script value types · [T19](#t19) A radius is a SPHERE ·
T20 One flag two states; one-way latches
---

<a name="t1"></a>
## T1 — Morpheus parse killers: one bad token silently kills the WHOLE `.scr`

**Recurred under 15+ bug ids:** 089, 298, 331, 348, 402, 533, 739/750, 910, 962, 1067, 1069, 1105, 1205, 1283, 1285, 1751, 1908.

> **An assignment with no value is a parse killer, and the error points at the WRONG line**
> (1908). `level.coop_loRosterTab[69] = ` with nothing after the `=` makes the parser read
> the *next* statement as the missing value, then die on **that** statement's `=` -
> `syntax error, unexpected TOKEN_ASSIGNMENT` reported against a line that is perfectly
> correct. Note the rule is **not** "the line ends with `=`": a bare trailing `=` is a legal
> line continuation and retail `global/MountGunOrPlantCharge.scr` relies on it. It is only
> fatal when the following code line is itself an assignment. `docs/tools/check_empty_rhs.py`
> now runs on every build. This one shipped from a **generator** rendering an empty column,
> which is the lesson: a generated file needs its inputs validated, because the generator
> will faithfully emit whatever the table says - including nothing.

> **All three scanners pass a file that cannot compile** — they check brace depth, line shape and
> string termination, not *expression* syntax. `println "a" + x + "b"` without parens is
> `unexpected TOKEN_PLUS`, kills the whole file, and scans clean (1751). **Not verified until a
> server has loaded the map and the log shows no `parse error`.**

**Check before you ship** — the three scanners catch disjoint classes, so run all three:

| tool | catches | blind to |
|---|---|---|
| `docs/tools/depthscan2.py` | brace/label depth (never negative; 0 at each column-0 label) | everything below |
| `docs/tools/linecheck.py` | a line **starting** with a binary operator | everything below |
| odd-quote scan (comment- and string-aware, per line) | unterminated / multi-line string literals | the rest of T1 |

The log names only the **first** offending line: bug-1283 had two multi-line strings in one file, and
fixing the reported one would have left it equally dead. Fix the class, not the line.

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
| A function call inside a vector literal, or with one in the same expression | 348, 402 |
| Negatives/arithmetic: parenthesised `(-1)`, or in a COMMAND ARG slot — `$ent coopammo 0 - 1` (unparenthesised). Compute to a local. **But** negative *vector components* are fine: `( 4016 0 - 967 0 - 328 )` == `( 4016 -967 -328 )` — don't "fix" them. | 1069, 1826, 1830 |
| An empty-array literal `[]` — morlang has none | 1105 |
| An unquoted `+`/`-` directive argument: `surface X -nodraw`, `surface X "+skin1"`. Valid TIKI frame-command syntax, fatal in script (`unexpected TOKEN_PLUS`) - **quote it**. The depth scan cannot catch this class; braces still balance. | 533, 1308 |
| A leading `&&` or `\|\|` on a continuation line | 739/750 |
| A real newline inside a string literal — from a generator, or hand-typed as a multi-line banner | 331, 962, 1283, 1285 |
| A backslash in a script path (resolved to `coop_modhelmet.scr`) | 1205 |
| Em-dash, UTF-8 BOM, any non-ASCII; duplicate label; label/brace mismatch | (CLAUDE.md) |

**NOT a parse killer, contrary to an older note:** `spawn <class>` **with** inline keyvalues is fine
— 192 working occurrences including `main.scr`. `KNOWN_WORKING_STATE.md` still forbids it; it is
wrong. See [90-folklore.md](90-folklore.md).

**Fix / check:**
1. **`developer 1` is mandatory** — compile errors are developer-gated at three call sites
   (`fgame/scriptthread.cpp:2858`, `:2869`, `:2883`). Without it the failure is *completely* silent.
2. **Raw brace counts are an invalid check.** Two opposite errors cancel and the count balances on a
   broken file (bug-239). Comment and string braces are miscounted. Use a **running-depth scan**:
   depth must never go negative, and must be 0 at every column-0 label (internal `goto` labels may
   legitimately sit at depth 1).
3. All three scanners live in `docs/tools/` (`depthscan2.py`, `linecheck.py`, `quotecheck.py`,
   plus `scrlint.py`) and run clean on the current tree.
4. Verify any claimed script command against engine source **before** it lands.

**Live status:** clean (re-scans 2026-07-29, 2026-08-08). bug-1027 (`e3l4/outro.scr`) has this
exact signature.

---

<a name="t2"></a>
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
| A **texture upscaler** tiled correctly (3x3 -> resize -> crop centre) then ran UnsharpMask on the CROPPED result. A convolution clamps at the border, so it invented edge pixels and reintroduced the exact seam the tiling existed to prevent (14x worse on `ocean1b`); Lanczos lobes separately overshot a capped alpha (189 -> 255). Fix: sharpen **inside** the tiled space, clamp each channel back to the source range. | 1247 |
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

**Confirmed instances:** eleven plus three more, tabulated in
[`docs/archive/traps-t3-instances.md`](archive/traps-t3-instances.md); further rows in
`traps-t3-archived-rows.md`, whose shapes are already taught here or in T1 - only evidence moved, not
a lesson. The rules below are the part you need up front.

**⭐ A GUARD WRITTEN FOR ONE QUESTION IS WRONG FOR THE NEIGHBOURING ONE (2026-08-10, bug-1687).**
`coop_isProtectedActor` answers *"should the AI-dynamics layer leave this actor alone"* and on
m2l2a says **yes to the entire cast** (14 actors named `ai_alarm`, anything with an `alarmthread`,
every papers checker, the scene actors). Reused unchanged to answer *"who would notice a corpse"*
it vetoed everybody, and two guards walked past a body twice with no reaction. **Before reusing a
predicate, re-read what it was written to decide** — and when the answers differ, split it rather
than widen it: detection now filters on nothing, while the *role* uses a narrower `coop_bustCanKneel`
that vetoes only the two reasons that actually apply. The original is untouched, because the
containment sweep still needs it.

**⭐ GATING ONE ENTRY POINT IS NOT GATING THE FEATURE (bug-1685).** Papers had **three** writers —
`enableClickablePapers`, `forcePapersInHand`, and the persistent `coop_papersAnytime`. Two carried
the `coop_busted` guard; the third took a playtest to find, and until then pressing fire to shoot
equipped the papers instead and swallowed the trigger for two seconds ("he just doesn't shoot").
**Grep for every writer of the shared state before calling a gate complete.** Second
instance, 2026-08-17, in our own tooling: `docgen.py` applied `SELF_EXCLUDE` to the porcelain FILE
LIST but not to the `git diff --shortstat` it embeds in CHRONOLOGY, so every `build` changed the
number CHRONOLOGY reports about itself and **`check` could never pass** - the staleness oracle the
whole doc set rests on was permanently red, which trains everyone to ignore it (bug-1860).

**A third shape, and the most embarrassing: OUR OWN GUARD DISABLED THE RETAIL MECHANISM.**
Twice in one day (2026-08-10). On m2l2a, `$naxos` is a `trigger_multiple` with `spawnflags 128` =
`TRIGGER_DAMAGE`, so the engine gives it `takedamage = DAMAGE_YES` + `CONTENTS_CLAYPIDGEON`
(`trigger.cpp:285-289`) - **shooting it is how retail completes that objective**. Our stealth
workaround opened with `$naxos nottriggerable` so the quiet route could control the timing, and
thereby deleted the retail solution; the user reported "shooting it dont do anything" (bug-1671).
Same shape as the limp above, where a *warning* disabled its own feature. **Before adding a guard,
ask what the vanilla mechanism for this already is** - and when a user says "this is how vanilla
handles it", go read the ENTITY, not the scripts around it. The first fix attempt here built a
whole damage-watcher on the wrong entity because it never asked what `$naxos` actually was.

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


A guard can key on data that does not exist yet at the moment it runs (2026-08-10, measured).**
The planned scene-actor exemption tested `alarmthread != NIL`. Instrumentation showed
`coop_apply_personality` fires on all 55 germans **23 seconds before** `alarm_system_setup` assigns
any `alarmthread` - so the exemption would have matched NOTHING, shipped clean, and passed its own
acceptance check vacuously. Same class as a director that tags actors before the map has named them.
**Before writing a heuristic, print the keys it depends on and confirm they are populated at that
instant.** This is why the fix pass is instrumented first and repaired second - A3 before A4.

**A vanilla scene reachable only from a BSP `trigger_once` never runs in coop (scene6; again
scene7, 2026-08-17).** m3l3's `main` carries seven `//thread sceneN` lines noted "called from a
trigger_once in the bsp". Those triggers do not fire on a coop server, so each scene stays dead
until something threads it. scene6 got a one-off workaround (`coop_churchApproach` threads it),
which hid the pattern instead of exposing it - so scene7 shipped asleep: no crews, no MG nests, no
firing nebelwerfers, and a final objective that could never complete. The cheap test: a whole
session log held **zero** occurrences of the string `scene7`. When integrating a map, grep its
`main` for commented-out `sceneN` threads and account for every one, then guard each scene
(`level.coop_sceneNStarted`) so the BSP trigger and your call site are both safe entries.
---

<a name="t4"></a>
## T4 — A capacity family has more members than you think

**Bugs:** 891, 892, 914-935, 1186, 1214, 1582, 1803; the whole entity-pool saga.

**Tell:** things vanish, alias, or corrupt at high entity/model/sound counts. Often **no log line
at all** — the overflow branch discards silently.

**The archetype - `maxentities 2048`:** shipped for *years* while `GENTITYNUM_BITS` was 10 (a hard cap
of 1024). It **added no entities; it disabled `AllocEdict`'s overflow guard**, so the allocator handed
out the world slot: a weekend of use-after-free minidumps.

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
- **A capacity never reset is a per-SESSION budget, and it kills an INNOCENT map** (bug-1803).
  `MAX_SKELETOR_CHANNELS` fills two process-global statics zeroed only at construction. After ~28
  maps e2l2 merely held the 2,560th channel — blameless, fine from a fresh boot. **Ask of every
  limit: what frees an entry?** If nothing does, size it against everything the game can load: a
  measured 4,589 whole-game proves 2,560 always had to fall over. Resetting is NOT safe:
  `skelChannelList_c` stores *global* indices in every cached model.
- **A protocol raise ships four binaries** — see [ENGINE.md](ENGINE.md#protocol-coupling).
- **One capacity grows while nobody touches the code: `MAX_CVARS`** (bug-1582). *Archived* content
  consumes it: `omconfig.cfg` hit **3019** cvars (Service Record ~1500, armory locks ~500), crossing
  4096 a month after bug-598 doubled it. Doubling is headroom, not a cure. Now 8192 + 80% warning.

**The best worked example in the codebase - `MAX_SOUNDS`.** Read
`openmohaa-hzm/code/qcommon/q_shared.h:1690-1755` **in full** before touching any capacity constant -
that comment is canonical and is not reproduced here. It lists the four binding constraints **in the
order they bite** (configstring layout `CS_AXIS = MAX_SOUNDS + 2393`, bug-1179; `MAX_RELIABLE_COMMANDS`,
must stay a power of two, bug-1183 twice; the 11-bit `sound_index` that **silently truncates**;
`MAX_GAMESTATE_CHARS`), tags each with the bug that found it *including the two failed attempts*, and
backs it with a compile-time `#error` so the rule fails at BUILD time.

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

Entities as `thread` parameters can arrive NIL — and a cross-file helper can return NULL
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

**Still open:** `global/vehicle_warning.scr` (4,270 casts, second-worst source) was **never
extracted** — the retail version is still live. And a second vehicle-crew spawn path on t2l2/t3l2
that the `truck_load` guard does not cover.

---

<a name="t6"></a>
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

**⭐ Imported third-party skin packs are this trap with the blast radius reversed.** A 2002-era MOHAA
skin pk3 routinely *redefines* stock shader names rather than minting its own, and because the coop
pak mounts last the import wins - silently repainting every other model in the game (one pack
redefined all 15 `viewsleeves*` shaders for a single pilot skin; another broke the holster on *every*
skin). Evidence, 39-pack sweep: `docs/proposals/skin_batch.md`. **Before importing any external pack,
diff its top-level shader block names against `hzm-mohaa-coop-mod/scripts/*.shader` and the retail
paks, and diff its `models/player/*.tik` basenames against the stock tiks** - a matching tik basename
*replaces* the stock model instead of adding one. Both checks are two greps. Note `map foo.tga`
resolves extension-agnostically, so a shader naming `.tga` beside a shipped `.jpg` is **not** missing.

**Related generated-asset hazard:** ESRGAN upscales have shipped hallucinated worm noise
(bug-1129), a GPU-corrupted all-black `netgame_a/b` that blanked the server browser (bug-247), and
29 overridden **vanilla** menu textures (bug-157). **Brightness-check output before commit**;
ESRGAN is for photos and text and corrupts 1–2px chrome.

---

<a name="t7"></a>
## T7 — Cvar registration, flags, and exec order

**An archived cvar is a latch - including one you add for debugging (bug-1427; again 2026-08-17).**
A `seta`-archived switch rides `omconfig.cfg` forever and re-fires on every later load
(`coop_buildmap` broke e3l4 twice in one evening); editing omconfig.cfg externally loses the race,
as the engine rewrites it from memory at shutdown. The 2026-08-17 repeat came from the other side:
giving `r_novis` `CVAR_ARCHIVE` so it would persist for one test wrote `seta r_novis "1"` into the
user's config and cost a `0xC00000FF` startup crash next launch. Consume mode-flipping cvars
one-shot at map init (copy to a level var, `setcvar` back to 0, never a live `getcvar`), and never
give a diagnostic `CVAR_ARCHIVE`.

**⭐ Script `getcvar` CREATES the cvar EMPTY, permanently defeating the engine's own default
(bug-1669, 2026-08-10).** `ScriptThread::Getcvar` is `gi.Cvar_Get(name, "", 0)`
(`fgame/scriptthread.cpp:2628`) - an **empty** default. So the first *script* read of a cvar the
engine has not registered yet creates it with value `""`; the engine's later
`Cvar_Get(name, "1", CVAR_ARCHIVE)` finds it existing, updates only the reset string, and **keeps
the empty value** - so `->integer` is 0 forever.

That is how player limping was dead: `coop_limpWarn` is threaded at player setup (`player.scr:224`)
and getcvar'd `coop_limp` before `Player::TickLimp` registered it - **the warning system silently
switched off the feature it exists to warn about.** It had also killed `coop_tinnitusBlast` and
`coop_goreDripCorpseTime`, neither ever reported. One trap, three dead features.

- **Detect:** rcon the cvar. `is:"" default:"1"` means it fired. A genuinely unknown cvar prints
  **nothing** - that control query is what proved it rather than inferred it.
- **Fix:** pre-register engine-owned `coop_*` cvars in `G_InitGame` (`fgame/g_main.cpp`), which runs
  before any script. **Any new engine `coop_*` cvar that script also reads must go in that block.**
- **Find the collision set:** intersect engine `Cvar_Get("coop_*", <non-empty default>)` against
  every `getcvar("coop_*")` in the scripts. It was six; four were genuinely broken.


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

**Agreement between reviewers is NOT corroboration when they share an upstream source (bug-1290).**
A multi-agent audit reported "the injury vignette is permanently maxed after any DBNO revive" as a
confirmed live bug, and **two independent critique lenses each confirmed it** - which is what made it
persuasive. It was false: all three had inherited one unchecked premise from the same research pass,
that `dbno.scr:49`'s `healthonly 9999` puts 9999 into health. `Entity::EventSetHealthOnly` **clamps to
`max_health`**, and `player.cpp:8113` writes `stats[STAT_HEALTH]` as an already-normalised 0..100
percentage, so the tracker cannot latch; the proposed "fix" would have hidden genuine low health after
a revive. **Rule:** verify a finding's *load-bearing premise* against the code yourself no matter how
many reviewers agree - independent agents reading the same brief are one witness, not three.

**A later entry can silently reverse an earlier one, so read the ordered LIST, not one entry.**
`docs/generated/FIX_INDEX.md` (file -> ordered bug ids) is the fix and it now exists: one entry says
what changed once, the list gives the file's net current state (story: HISTORY). Nothing in the
schema flags a reversal, so when you supersede a finding **edit the original entry** rather than only
appending — bug-1473/1474 were corrected in place on 2026-08-06 after being filed on the wrong files.

**Other record hazards:**
- **Wrong anchors are worse than no anchors.** `q_shared.h:1680` credits the `MAX_MODELS` 1024→2048
  raise to **bug-866**; the actual work is **bug-892**. A grep at a wrong path returns nothing and
  reads as "already fixed."
- *(buglog tooling hazards - id formats, append-never-rewrite - moved to
  `docs/reference/buglog_maintenance.md`)*
- **28 bug ids cited in source comments have no buglog entry** — including bug-237 (packer
  determinism, `build.ps1:11-15`), bug-241 (never deploy under a running game) and bug-239 (the
  brace-counting lesson). **For those, the code comment IS the only record.**

**⭐ The habit that works:** leave the correction **at the site**. `maps/m1l1.scr:1683`,
`coop_mod/loadoutpick.scr:436-440`, and `q_shared.h:1690-1755` are all self-documenting and all three
survived contact with a later session.

**When classifying REVERTED, separate "it broke" from "the user changed their mind."** Only the
former is a lesson — bug-787 reversed a design at the user's request; nothing was defective.

---

<a name="t12"></a>
## T12 — Name collisions between two identically-named trees

**There are TWO `_research` trees** and records conflate them: `C:\mohaa-coop-dev\_research\`
(design docs, audits, **the regression harness**) and
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\_research\` (buildmode inventories, `hud_slot_map.md`,
`director_dda_plan.md`). Only the second is inside the shipped tree.

**Ship risk: CLOSED (re-verified 2026-08-17).** `build.ps1:32`'s
`$excludeTop = @("_notes", "_research")` is committed and the deployed
`zzzzzz_co-op_hzm_mod_code.pk3` contains **zero** `_research`/`_notes` entries. Releases up to
v1.1.55 did ship design docs and retail script extracts; that is history now, not a live hazard.
*(This entry previously read "OPEN NOW" and cited an uncommitted `build.ps1:27` - both were stale.)*

**Still open:** the regression harness - the project's only working automated verification - lives in
a directory named `_research`, a name the build script treats as disposable. **Promote it out** before
someone applies the exclusion logic to the wrong tree. Related: four uppercase map scripts (`M1*`,
`M3*`, `M5*`, `M6*.scr`) sit alongside lowercase counterparts, unchecked for case-collision in a pak.

**The same trap one level down: two subsystems sharing a `level.*` name** (bug-1612).
`coop_mod/ambience.scr:42` owns `level.coop_ambEnt` as a **single `script_model`**; the telephone-gag
work later added `level.coop_ambEnt[alias] = emitter` as a **dictionary**. The entity wins, so every
indexed read throws `[] applied to invalid type 'listener'` — once per ambient, on every map. Skipped
not fatal, so nothing crashed; the sole casualty was m1l2b's ringing-telephone gag, which polls that
dictionary 100×0.1 s and so always burned 10 s and printed `PHONEGAG FAIL`. It shipped unable to work.
**Grep the mod tree before adding a `level.coop_*` name — the error names the type, never the other
owner.**

---

<a name="t14"></a>
## T14 — Your verification lied: audits that pass, harnesses that measure nothing

**Bugs:** 1026, 1027, 1218-1220, 1473-1490, 1812-1813.

**Tell:** a map graded clean by a read-through then storms on boot. t2l2 graded **A−** statically
and throws 265 errors on coop boot — *degraded, not dead*, which is exactly why a read-through
missed it. **A live boot is the only real test.**

**Absence does not log.** A parse error screams; a VO line that never plays, a trigger nobody walks
into, an alias resolving to nothing are silent - error-driven testing cannot find them by
construction. You need an **expectation manifest** (what *should* fire, from the BSP entity lump)
diffed against **engine instrumentation** (what *did*). That is the coverage sweep.

**Settled 2026-08-06 by the 4-player coverage sweep.** 49 walker-valid maps threw **26,230 script
errors across 548 sites**, none reported by any static audit — and they concentrate in **shared**
files, so few fixes repair many maps: `vehicle_warning.scr` 12,690 (48%), `gags/t2l3_friendly.scr`
8,694 (33%), `gags/t3l1_enemyspawn.scr` 972, `global/spotlight.scr` 798, `coop_mod/officer.scr:1754`
666 (the mod's **own** code, all 48 maps).

**The dominant cause is `$player`-as-array** (see [T5](#t5)) reaching a retail SP script that
dereferences `.origin`. Invisible in SP *and* in 1-player coop: `OP_UN_TARGETNAME` yields a plain
listener at one match, a container only at 2+. **It needs two connected players to reproduce at
all** — which is why years of solo testing never saw the trilogy's largest error source.

**A MEASUREMENT HARNESS FAILS SILENTLY TOO - a broken one does not error, it reports.** Four AI A/B
runs (2026-08-15) were each invalidated a different invisible way, all four looking clean. **Refuse
to report unless preconditions held, and prove the guard fires.** The four modes and the six rules:
[reference/harness_and_reproduction.md](reference/harness_and_reproduction.md).

**A declaration with no producer is the same silence** (bugs 1596-1598, T3 row). Cross-reference
mechanically, walking the WHOLE tree — a `maps/*.scr` glob misses `maps/<map>/*.scr` and miscounted
three wired challenges as dead.

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

`thread <label>` inside a boolean is ALWAYS TRUE (2026-08-10, bit 5 files at once).** `thread` starts the
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

**Tell for all three:** a feature that "does nothing" with no crash, plus a `Script Error` line naming
a file and line you were not looking at.

---

## T16 — A failsafe that escapes a hang by calling code containing the same hang

**Bugs:** 1361 -> 1366 (e3l4 supply/delivery); same shape as the AB41 and truck-unload failsafes.
Worked example and evidence: **`docs/archive/traps-t16-failsafe-recursion.md`**.

**Rule: a recovery path must contain no wait that the failure mode can block.** The e3l4 failsafe
bounded a blocking wait at 45s and then "recovered" by calling a routine that opens with
`runto` + `waittill movedone` — the actor's whole problem was having no nav path, so the soft-lock
moved rather than closing, and the second report looked like the first fix simply hadn't worked.
For actors that means no `runto`/`walkto`/`waittill turndone`/`waittill animdone` and no unbounded
`while (vector_length(...) > N)`. Seat or place them directly — take the **tail** of the vanilla
routine (everything after its movement).

**Two engine facts make actor waits unsafe** (verified in source, bug-1368):
`Unregister(STRING_TURNDONE)` exists in exactly one place, `Actor::IdleTurn` (`actor.cpp:5032`),
which no runner think reaches — so a failed `runto` pins the actor in `THINK_RUNNER` and any
`waittill turndone` there blocks **forever**. `waittill movedone` is safe: `CheckUnregister`
(`actor.cpp:7793`) fires it even on `parm.movefail`. So **`runto` -> `turndone` hangs; `runto` ->
`movedone` does not.**

**Never invent an exit/placement offset when the model carries an authored one** — vehicles ship
`driver_enter` / `passenger_enter` / `*_seat` tags, walkable by construction. An offset that works
at one stop is a guess about free space at every other stop. (bugs 1367, 1370)

**Tell:** the same user report twice, with a failsafe log line in between. Grep the recovery path
for `waittill` before shipping it, and check the *next* stage for the same shape.

---

<a name="t19"></a>
## T19 — A radius is a SPHERE, and hand-rolled distance is not trustworthy

**Bugs:** 1689, 1690 (2026-08-10).

**Tell:** a proximity prompt fires on the floor below, or through a ceiling — "the Naxos text appears
when you are downstairs underneath the room", "you get caught on the 2nd floor for his dead body on
the first".

**`vector_length` is a 3D distance**, so every "within N units" test is a sphere — almost never what
is meant in a building. **"Near" is a HORIZONTAL question plus a same-storey question, tested as
both**: 2D distance plus a vertical band (96u; a MOHAA storey is ~128). Three sites in one feature
had it - a rule, not an oversight.

**Take the horizontal distance with `vector_length` on both points flattened to z=0** via a vector
literal (locals inside a literal are fine - `props.scr:407`, `tracescan.scr:79`), **not with
hand-rolled pythagoras.** A `sqrt( (dx*dx) + (dy*dy) )` here returned **265.965 for two points 2013u
apart**, twice across two builds, while `dz` by plain subtraction on the next line was exactly right -
so the feature fired at the spawn whatever radius was set. The same expression instrumented a build
later gave correct numbers, so no claim is made about the mechanism; what is established is that
`vector_length` was right on every sample and the hand-rolled form was not on at least one.
`aimaneuver.scr:129` uses the same inline form and has never been checked.

**A range must also be the right SIZE for its job.** That feature's warning was drawn off the
*action* prompt's 112u bash range, so it only appeared once the player was already on top of the
officer. Give an advisory its own, wider range.

---

## T20 — One flag, two states; and one-way latches

Both shapes cost most of 2026-08-11 on the m6l1c stealth route, because in both the symptom
pointed away from the cause.

**A flag that answers two questions gets tested for the wrong one.** `is_disguised` is the engine's
live opinion, recomputed per frame (`player.cpp:5519-5545`): has a disguise, no alarm, nothing real
in hand, *and* nobody attacking you with real threat. `has_disguise` is the fact the mod's own grant
sets. They agree most of the time, which is what makes this expensive. Testing `is_disguised` where
`has_disguise` was meant read "someone is shooting at you" as "the grant failed" in two places (bugs
1701, 1701b, 1703), each re-running the whole disguise grant from a frame-rate loop, flipping
gametype twice per pass and resetting every AI think state (13-14/sec sustained). The tell was **the
player's own viewmodel and HUD stuttering** - AI churn alone does not stutter a client.
> Before testing a state flag in a retry, ask how many different things can make it false. If more
> than one, you are not testing what you think - prefer the flag your own code sets. And **bound
> every self-re-threading retry**: a predicate that stays true burns a core until map end.

**Bare `attackplayer` is permanent, and lives in more files than you grepped.** It is
`Actor::ForceAttackPlayer`, setting `m_bForceAttackPlayer`, cleared **only in the Actor constructor**
(`actor.cpp:3092`); while set, `EnemyIsDisguised()` returns false unconditionally, so one call blinds
that actor to every disguise for the rest of the map. `attackentity <ent>` is the advisory,
reversible form. Four sites took **three sweeps** because the first two only grepped `aihandler.scr`
(bugs 1700, 1704, 1708); every one already had a usable target a line or two above.
> Sweep the whole tree for a one-way primitive, not the file you found it in. Comment legitimate
> no-target fallbacks so the next sweep can tell them apart.

**An absorbing state hides everything downstream.** `EnemyIsDisguised()` also returned false for any
actor in `THINKSTATE_ATTACK`, so an actor that entered attack for any reason could never be fooled
again - and with the veto above it ratchets: each hostile that shoots you blanks your disguise for a
frame, which flips more actors. Fixed by requiring real threat (bug-1707), the same treatment
`player.cpp:5541` already had. Blocked-aggro across one run: **1051 -> 0**.

**A flag two systems both own is a race, and it comes back.** `coop_clickablePapersEnabled` is set by
`enableClickablePapers` and cleared by `coop_bustArm` to end the papers loop when a bash starts.
Anything re-arming it mid-bash restarts that loop, whose force-equip branch puts papers into the hand
already holding the drawn pistol - the gun alternates with `(none)` and **the player cannot shoot**.
Three unrelated causes, one symptom: a 0.5s re-check (1709), a squad-wide clear on papers ACCEPT plus
the re-offer answering it, and per-target threading that stacked loops so one clear stopped only the
newest (1726). Deduping was **not** sufficient (1732): one loop still steals the gun, since its guard
`coop_activeWeapon == NULL` means both "hand is empty" **and** "no raise ever finished", and in a bust
the second is true. Then `coop_busted` became the overloaded one twice within the hour - an
idempotence guard turned into an unconditional `end` once `bust.scr` set the flag earlier (1735), and
the flag cleared only on the success path, so a surviving guard left the player flagged for the
mission (1736).
> One writer per player at a time; clear the flag and yield a frame before threading a loop that sets
> it. **Split the latch from the state, and clear it on every exit, not just the happy one.** Moving
> a flag's assignment earlier silently rewrites every guard that reads it - grep them all first.

## Cross-cutting: the four questions to ask before "it doesn't work"

1. **Did it compile?** (T1 — `developer 1`, running-depth scan)
2. **Did it run?** (T3 — prove execution before tuning; check the gate cvar is actually seeded)
   — and when a constant becomes a cvar, **update every reader in the same pass**. `coop_aiBuffer`
   converted the unsponge detectors but not `actorPainHandler`, still testing the literal 5000 while
   actors buffered to the unseeded fallback 1000: the AI pain handler detached on **every actor's
   first hit**, silently (1733), and fixing it exposed a reader right only by accident (1734).
3. **Is the binary I'm testing the one I built?** (T10 — three binary states are live right now)
4. **Am I reading the record or the code?** (T11 — the code wins; read the record to the END)


5. **Am I guessing, or measuring?** (was T13) **⭐ BISECT FIRST — a cvar bisect beats any number of hypotheses** (bug-1298). When a wrong guess costs a session, turn things off one at a time until the symptom moves. Six deployed hypotheses on the gl2 "white distant objects" bug changed nothing; one bisect found it.

## TIKI and sound-alias traps

Moved to **`docs/reference/tiki_and_sound_aliases.md`** (frame-command lines inside
`server{}`/`client{}`, aliases without a `maps` spec never loading, per-map `includes` blocks,
cut-but-shipped content, and never leaving a backup inside the mod tree). Read it before
touching a `.tik` or adding a sound alias. Two auditors make that file's traps testable
rather than playable: `docs/tools/audit_weapons.py` (every player weapon) and
`docs/tools/audit_shaders.py` (every shader file the engine can load).

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
- **Values parsed out of a `.dat` file are STRINGS** (bug-1352). The character-walking splitters
  (fogmode, blueprint, save files) return strings, so a later `if( x > 0 )` throws and *that
  assignment never happens* while the caller prints its success message. Coerce with
  `float()`/`int()` at load. Tell: works when set live, never when loaded from its own save.
- **A probe that throws prints nothing** while filling the log with errors — so it is silently
  useless on exactly the cases worth watching. Sanitise every field before concatenating:
  an unset var reads `none`, and `"str" + none` throws (bugs 1702, and the SPAWNDISG probe
  before it, both the same day).

## A scripted conversation strands when a `waittill` outranges its guard (bug-1579)

Retail chatter helpers assume single-player: the talkers are always alive and idle. Coop breaks all
three assumptions, each with its own failure shape:

- **The `waittill` sits OUTSIDE the guard that started the anim/say.** No anim was issued, so nothing
  can fire `animdone`/`saydone` and the calling sequence stops **forever**. Wait only on an actor you
  actually animated - record it in a local; never re-test the condition (one that was attacking when
  the anim was skipped, and has since calmed, passes the retest and waits for nothing).
- **`isalive` on a NULL entity throws, and a thrown statement is SKIPPED** - so the guard itself
  disappears and the body it protected runs unguarded. Test `!= NULL` first and *separately*.
- **`thinkstate != "attack"` is not "idle".** A CURIOUS / GRENADE / PAIN actor runs its own think and
  overrides the scripted idle anim. Gate on `== idle`: `anim` runs at `THINKLEVEL_IDLE`
  (`Actor::PlayAnimation` -> `SetThinkIdle(THINK_ANIM)`, `actor.cpp:10819`) and there is no
  `THINKSTATE_ANIM`, so a normal scripted exchange stays `idle` and is not silenced.

**Silence the LINE, never abort the THREAD.** The tail of these labels usually holds the RELEASE —
a `runto`, an `enable_ai`, a `type_disguise` — that hands the actors back to normal AI. Ending the
sequence early leaves them frozen: unresponsive, and dying on their feet with no death animation.
The one safe exception is a dead-end label nothing waits on (verified: `M1L3c` radio room).

Sites, counts and remaining work: **docs/OPEN.md**. Helper `replace.scr::convOk`.

