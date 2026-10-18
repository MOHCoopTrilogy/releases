# TRAPS — every way this project has broken itself more than once

**The highest-value file in the doc set.** Each entry is a failure family that recurred. Read the
**Tell** first — that is what you will observe. Status legend in
[SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md#status-vocabulary).

> War stories: [`archive/traps-pruned-2026-08-20.md`](archive/traps-pruned-2026-08-20.md).

## ClientThink runs once per USERCMD, not once per server frame

Integrating `level.frametime` inside ClientThink advances once per COMMAND (com_maxfps 180 vs sv_fps 40 is ~4.5x), differing per player
(bit recoil, prone dwell, stress, brace, sprint pool bug-3372). **Use elapsed time:** keep `m_fCoop<X>Last`, `dt = level.time - last`
clamped to 0.1-0.25 s, and seed the member in the constructor (player memory is not zeroed).

## Quick index

**Open now:** [T11](#t11) trusting the record over the code · [T14](#t14) verification that lied.
---

<a name="t1"></a>
## T1 — Morpheus parse killers: one bad token silently kills the WHOLE `.scr`

**17 bug ids.**

**Tell:** a feature silently does nothing, with **no error at the failure site**; every `::` call into
the file logs `Script was not properly loaded`. The compiler is all-or-nothing: one syntax error
kills the entire file and the map runs with no script at all.
**An engine-new command fails the WHOLE file on an older game.dll** (bug-3423): isolate it in a helper `.scr` (`dbno_bleed.scr`).

> **An assignment with no value is a parse killer and the error points at the WRONG line** (bug-1908):
> the parser takes the *next* statement as the value and dies on **that** statement's `=`. A bare
> trailing `=` is legal continuation, so it is fatal only when the next code line is itself an
> assignment. `docs/tools/check_empty_rhs.py` runs every build.
>
> **All three scanners pass a file that cannot compile** (braces, line shape, strings - not *expression* syntax: bug-1751 an unparenthesized `+` in `println`; bug-2632 builtin args are SPACE-separated, a 2-arg builtin is `local.x = f a b`, a getter is `p.userinfo`). **Not verified until a server has loaded the map with no `parse error` in the log.**
>
>**A comment that lost its `//` scans perfectly** (twice; a fixer put `//` on a multi-line comment's first line only) - **`prosecheck.py` catches it.**

**Run all four — they catch disjoint classes; only the last reads a line as language:**

| tool | catches | blind to |
|---|---|---|
| `docs/tools/depthscan2.py` | brace/label depth (never negative; 0 at each column-0 label) | everything below |
| `docs/tools/linecheck.py` | a line **starting** with a binary operator | everything below |
| odd-quote scan (comment- and string-aware, per line) | unterminated / multi-line string literals | everything below |
| `docs/tools/prosecheck.py` | **English prose standing where a statement should be** | expression syntax |

The log names only the **first** offending line (bug-1283 had two). **Fix the class, not the line.**

**The 11 confirmed triggers are tabulated in
[`archive/traps-t1-triggers.md`](archive/traps-t1-triggers.md)** - read it before writing `.scr`. The four
that recur most: **command syntax on an `EV_GETTER`** (must use property syntax); **a parenthesised
negative `(-1)` or a bare negative in a COMMAND ARG slot** (compute to a local - but negative *vector
components* are fine); **an unquoted `+`/`-` directive argument** such as `surface X -nodraw` (valid TIKI,
fatal in script, and braces still balance so the depth scan misses it); and **a real newline inside a
string literal**, usually from a generator.

1. **`developer 1` is mandatory** - compile errors are developer-gated; without it the failure is silent.
2. **Raw brace counts are invalid** - opposite errors cancel (bug-239), comment/string braces
   miscount. Use a **running-depth scan** (never negative; 0 at every col-0 label, `goto` labels
   may sit at depth 1). Scanners: `docs/tools/{depthscan2,linecheck,quotecheck,scrlint}.py`.
3. **A call in a `}end <expr>` return position is NOT evaluated** (bug-2603): `}end int(local.s)`
   returns the token `int`, not a number. Assign first: `local.v = int(local.s)` ... `}end local.v`.
4. **An `EV_SETTER` is assigned, not called** (bug-2608): `ent.injail = 1`, never `ent injail 1` (a compile killer); `EV_NORMAL` events use the command form.
5. **An UNKNOWN COMMAND kills the file too, and a failed compile was a CRASH, not noise** (bug-2709/2868):
   `immortal` killed `admin.scr` for three releases, logged "harmless"; up to v1.9.0 a failed compile set up a
   game.dll double free on the next map change. Grep boot/soak logs for `Couldn't compile`; a hit is P0.


---

<a name="t2"></a>

**A trailing comment swallows the closing brace** (4 occurrences, C++ too). `if (!p) { p = ...; }`
plus `// note` puts the brace INSIDE the comment; the compiler blames the NEXT function, often
hundreds of lines down. `depthscan2.py` finds it - the culprit is the first line where depth climbs
and stays, never the reported line.

## T2 — Generators corrupt the files they write


**Tell:** the output looks right in a diff and is silently rejected downstream; TIKI in particular
**drops bad aliases without a word.** Every instance is a TOOL writing project data, not a human:

| What happened | Bug |
|---|---|
| `.pk3` bytes (already CRLF) written back in Python **text** mode → `\r\r\n`; TIKI dropped **every** `anims_shared.txt` alias. | 259 |
| A Python literal of script/C text (heredoc or not) made a `\n` escape a real newline → T1 kill, C2001. Use a fragment file. | 331, 962, 3002 |
| A shader generator's brace matcher broke on mixed CRLF/LF + `//`-commented braces (45 open / 43 close) → white-square HUD icons. | 480 |
| A **texture upscaler** sharpened AFTER cropping its 3x3 tile (clamp re-made the seam, Lanczos overshot alpha): sharpen tiled, clamp to source. **DXT encoders skew colour**: Pillow DXT5 tilts normals ~14 deg (use `gen_terrain_pak_*.py`);  **TGA: bottom-up** (loader ignores the top-down bit, PIL obeys it). | 1247, 2953, 2994, 3019 |
| A PowerShell harness assigned `$home`, a **built-in automatic variable**; the assignment silently no-op'd and logs landed in the user profile. | ps-home-var |

- **Binary mode on BOTH sides, repo files included.** `open(p, encoding=...)` translates newlines on
  *read*, so a CRLF file arrives as LF and `\r\n` patterns match nothing; `newline=""` on write then
  flips the **whole file** to LF. Both fail silently - `str.replace` returns unchanged rather than
  raising. Use `rb`/`wb`; the tree is **not uniform** (`challenges.scr` CRLF, `lobbyui.scr` LF-only,
  `docs/TRAPS.md` LF - bug-1600 was this file flipped by a prune script). Detect per file and **assert
  the match count before every replace**.
  Not Python-only: **`sed -i` and any shell in-place rewriter flip the whole file the same way** (bug-2081).
  Detect endings by counting `b'\r\n'` vs bare `b'\n'` on RAW BYTES (`grep -c $'\r'` says 0 on CRLF) and
  confirm the diff SHAPE (`git diff --numstat`): a whole-file diff on a 16-line edit is the tell.
  With `core.autocrlf=true` (**both** sub-repos), git's smudge filter runs on `git apply` as well as
  `git checkout --`, so **a patch that applies cleanly still rewrites every line ending in the file**
  (bug-2453) while `git diff` shows nothing (blob is LF); `build.ps1` packs the WORKING COPY, so that
  CRLF ships: after any `git apply`, re-count `b'\r'` per file. Hence `.scr` patches are Python fixers.
  **Never `git checkout`/`reset`/`restore` a shared authored doc**: others hold unstaged edits in it
  (bug-4037, 2026-10-18: wiped weeks of FEATURES edits, flipped it to CRLF). Rebase via `git merge-file`.
- **Derive generated hunks against the base the generator saw.** Diffing a lane's FULL patched
  copy against a text that already carries other lanes' edits turns every one of those edits into
  a deletion - and per-hunk uniqueness asserts pass, because each reverting FIND genuinely occurs
  once (bug-2482). Print the byte delta of every edit and read the signs: a `-10870` where an
  insert was expected is the only tell.
- **Verify the invariant you claim to preserve, against the ORIGINAL** - the seam regression was caught
  only by measuring edge-wrap error on output vs input per file.
- **Assertion gates, not review.** Review never held; balance asserts, zero-stale-ref asserts, count
  asserts (`assert NS == 76`) and bug-1009's connectivity flood-fill gate did.

---

<a name="t3"></a>
## T3 — Silent-veto bugs: the feature never ran, so nobody could observe it

**The project's most expensive recurring *shape*.** **Tell:** "we built X and it does nothing / has
no effect / can't be felt." Before tuning X, **prove X executes.** Instances:
`archive/traps-t3-instances.md`, `traps-t3-archived-rows.md`;
long narratives for the starred four in `archive/traps-pruned-2026-08-20.md`.

**⭐ FALSE NEGATIVE from the test harness: a dedicated boot prints no script output unless `developer 1`**
(bug-2637; ~12 rebuilds chased that phantom). `launch_dedicated_2player.ps1 -ServerCvars a,b` called from bash
`powershell -File` binds ONE string - every cvar lands on one dead `seta` line; call it from PowerShell. Headless
clients never click to deploy, and an intro ride (m1l1) keeps players inactive + unhittable: wait for
`coop_isActive` and the end of `coop_spawnProtOn` before any damage test (ST_HC, bug-2923).

**⭐ A guard written for one question is wrong for the neighbouring one** (bug-1687): re-read what a
predicate was written to decide before reusing it; when the answers differ, SPLIT rather than widen.

**⭐ Gating one entry point is not gating the feature** (bugs 1685, 1860): grep every writer of the
shared state before calling a gate complete.

**⭐ The same shape at the FIX end: a repair applied to one member of a set nobody enumerated.**
**Name the set a fix belongs to and check every member** (bugs 2171/2172/2175): a pair, a list, a
direction. Tell for the pair: a cvar seeded in no cfg has only its code default, so two `Cvar_Get`
calls with different defaults ARE the bug.

**⭐ Our own guard disabled the retail mechanism**, twice in one day (bugs 1671, 1669). **Ask what the
vanilla mechanism already is before adding a guard**, and when a user says "this is how vanilla handles
it", read the ENTITY, not the scripts around it - m2l2a's `$naxos` carries `spawnflags 128`
(`TRIGGER_DAMAGE`), so *shooting it* is how retail completes that objective.

**⭐ A guard can key on data that does not exist yet when it runs.** **Print the keys a heuristic depends
on and confirm they are populated at that instant** - the scene-actor exemption tested `alarmthread != NIL`
23 s before anything assigns one, matching NOTHING while passing its own acceptance check vacuously.
Instrument first, repair second.

**`invalid waittill spawn for 'Level'` means "this script ran at the wrong time"** - it does not wait
([Script Error](#script-error)). Fix with `replace.scr::waitTillSpawn` / `::waitTillPrespawn`, but **do
NOT bulk-replace**: 191 bare sites ship and most are reached first, so fix only sites the runtime log
shows throwing ([T14](#t14)).

**A second shape: the write executes and is then overwritten.** Proving execution is necessary but not
sufficient - **grep every writer of a shared per-frame field and establish who runs last**, preferring
the LAST write site in a render/view path. Head tracking shipped INERT this way (bug-2101):
`PmoveAdjustAngleSettings` (`bg_pmove.cpp:1622`) rewrites all four bone controllers from `EndFrame`,
after `ClientThink` set them - **the cure is a different call site, not a different value.** The
dangerous variant lands somewhere real instead (bug-1238 moved the 3P pivot).

**The UI corollary - never trade a working widget for an unverified one; ADD ALONGSIDE IT.** A `.urc`
cannot be run or diffed from here, so the only oracle is the user's screenshot (bug-1546). **A `UICheckBox`
always draws a raised 3D bevel** whatever its `borderstyle` (`uicheckbox.cpp` Draw); it vanishes only
because `bgcolor` also sets the border colour and alpha 0 propagates through `UBorderColor`, so an
invisible whole-row click target needs `bgcolor` alpha 0 AND a fully transparent checked/unchecked
shader (`textures/mohmenu/trans_click`, bug-2578). And when you
fix a silent-discard branch, **add the warning even though you also raised the limit** -
`sv_snapshot.c:549-553` does.

**Four more rules + their instances: [`archive/traps-t3-instances.md`](archive/traps-t3-instances.md)**
- headless boots always pass; a flag with no getter cannot be debugged.

---

<a name="t4"></a>

**`int / int` IS C INTEGER DIVISION AND SILENTLY ZEROES (OR MULTIPLIES) WHOLE FEATURES** (bugs
2424/2425, 2497). `scriptvariable.cpp:1671` divides ints as ints: **`38 / 100` is `0`**, `750 / 100` is
`7` (a 7x scale, 2497). `wait ( 34 / 24 )` waits **1**.
**Write `* 0.01`, or `* 1.0` before dividing.** A ratio is safe only if you can NAME the float
operand - `vector_length` results are; counts never are. **The build never compiles GLSL**: after any `.glsl` edit
OR merge run `glsl_variant_lint.py --emit` + glslang on its output; the lint cannot see a duplicate local (bug-2971, 3252). **Float compares have a 1e-4 dead band**
(`scriptvariable.cpp`): thresholds < 1e-4 never fire - scale first (bug-2963).

**A `sighttrace` ending at an entity's own origin ends INSIDE its box.** With the third arg 0 the mask
keeps CONTENTS_BODY/BBOX and a segment that ends inside the target's collision box reads as blocked -
so `isInCover`'s LOS clause vetoed every beach hit on every solid player for a week (bug-2497). Pull
the end point outside the box, or trace world-only (arg 1) first.

## T4 — A capacity family has more members than you think

**Bugs:** 891, 892, 914-935, 1186, 1214, 1582, 1803, 2291-2293; the whole entity-pool saga.

**Tell:** things vanish, alias, or corrupt at high entity/model/sound counts, often with **no log line
at all**. **The archetype, `maxentities 2048`:** shipped for *years* while `GENTITYNUM_BITS` was 10
(hard cap 1024) - it added no entities, it **disabled `AllocEdict`'s overflow guard**, so the allocator
handed out the world slot: a weekend of use-after-free minidumps.

- **A "comprehensive sweep" that greps only *suspected* files is not comprehensive** - bug-925 crashed in
  `sentient_combat.cpp`, missed by bug-920's sweep. **Fix the producer, not just the consumers** -
  `AddItem` appended entnums with no duplicate check while removal took one occurrence (bug-920). And
  **non-NULL is not enough**: a recycled slot may hold a *different class*, so guards became
  `item && item->isSubclassOf(Item)` (bug-919).
- **Audit bare array sizes, not just constant names** - `tr.skel_index[1024]` (bug-932b);
  `processed[MAX_ENTITIES]` where `MAX_ENTITIES` is the renderer *refentity* cap 1023, **not** the gentity
  count (bug-935); `MAX_SKELMORPH 12800` silently out-of-bounds (bug-1214). Same invisible-actor symptom
  paid out three times (bug-932, bug-1135 `R_AllocModel`, `renderergl2/tr_local.h:2339`).
- **A capacity never reset is a per-SESSION budget, and it kills an INNOCENT map** (bug-1803).
  `MAX_SKELETOR_CHANNELS` fills process-global statics zeroed only at construction; after ~28 maps e2l2
  held the 2,560th channel - fine from a fresh boot. **Ask of every limit: what frees an entry?** If
  nothing does, size it against everything the game can load (measured 4,589 whole-game). Resetting is NOT
  safe - `skelChannelList_c` caches *global* indices.
- **A protocol raise ships four binaries** - see [ENGINE.md](ENGINE.md#protocol-coupling). And **a raised
  size constant is a stack landmine**: `MAX_MSGLEN`→256KB (bug-1864) crashed the dedicated server the instant
  a browser sent `getstatus` - the OOB reply chain (`SVC_Status`→`SV_NET_OutOfBandPrint`→`NET_OutOfBandPrint`)
  allocates `char[MAX_MSGLEN]` on the *stack* at every hop, >1MB on a 1MB stack → `0xC00000FD` (bug-2727).
  Fix = `static` (ioq3 pattern; OOB send is single-threaded). **Grep every `[MAX_MSGLEN]`/large stack array
  when you raise a size constant - a public server gets `getstatus` in seconds, so it only crashes in prod.**
- **⭐ Two constants that agree by COINCIDENCE are a bomb with no label** (bugs 2291-2293, 2315; three
  crashes and one blind revert). `TIKI_MAX_ENTITIES` was a hardcoded 2048 that merely *happened* to
  equal `MAX_GENTITIES`; `TIKI_End()` indexed `skel_entity_cache[i*2+j]` without the writer's
  `% TIKI_MAX_ENTITIES` wrap - in bounds by luck, zero margin - so 12 bits `delete`d 4096 garbage
  pointers and the blame landed on a blameless `GENTITYNUM_BITS` raise. **Grep a capacity's VALUE, not
  just its name; ask whether two limits are derived or merely equal today; an `==` against a capacity is
  always a bug.** Knowing this does not prevent it (bug-2315: raised sound channels 32→96, shipped a
  launch crash - loops bounded `loop_sounds[64]` by `CHANNELS_3D+CHANNELS_2D`): **write the build break in
  the same commit as the raise.** And
  **`ENTITYNUM_*` are PROTOCOL indices** (`MAX_GENTITIES-2`): size anything indexed by one off
  `MAX_GENTITIES`, never off `maxentities`, which is all `g_entities` was malloc'd at (bug-2291).
  **Diagnose this class from the FAULT ADDRESS, never by inspection** - reading the diff produces
  real-but-wrong fixes; WER's fault RVA + the linker `.map` names it in a minute (recipe in the
  `crash_dump_analysis` memory; bug-2727 was cracked this way with no debugger installed).

**Read `openmohaa-hzm/code/qcommon/q_shared.h:1690-1755` before touching any capacity constant** (the canonical `MAX_SOUNDS` comment + its compile-time `#error`, bug-2292).

---

<a name="t5"></a>
## T5 — `$player` is an array; NIL ≠ NULL; storms are sequential

**Tell:** thousands of identical `Script Error` lines. **Solo boots cannot reproduce any of it.**

1. **`Cannot cast array to listener`** - vanilla SP treats `$player` as one entity, but with **2+
   connected players it is a 1-indexed ARRAY**, so `$player.origin`, `turnto $player`, `isAlive $player`
   all throw. Repair idiom: an **inline `$player[i]` scan** with a per-element NULL guard, or
   `$player[1]` with a NULL host guard - never `replace.scr::player_closestTo` first (bug-1665).
2. **`Cannot cast none to <type>`** - a `level.*` timing global the vanilla SP init would have set is
   never set in coop (`level.thundertime` / `windtime` / `shuttertime` / `rainvolume`);
   `weather.scr:378` alone threw **8,662 times**. Fix: NIL-guards restoring vanilla defaults.
3. **Stale pointers that PASS a NULL guard** - bug-1054's `coop_trackTankTarget` had no `else` branch, so
   a freed player ref lingered and evaded `== NULL`.

**⚠️ Guard with BOTH.** `NIL != NULL` and coop hits both; bug-1065 hardened `xp_award` with
`== NULL || == NIL` because `level.coop_smoke_player` is only ever assigned, never initialised.

**⭐ THE META-LESSON — SEQUENTIAL STORMS.** Fixing one class lets maps progress **further**, exposing the
next: the array-cast fixes are what unlocked the none-cast storm. **A storm blocks map progression and
hides every storm downstream.** Budget **2–3 fix→re-sweep passes**; a clean sweep after one fix means
nothing.

**Root cause of the biggest storm:** `addon_*` markers carry their model in `$ai_model`, not `.model`, so
`spawner_create` recorded NIL and the engine spawned `models/nil.tik` in a loop - an entity leak as well
as log spam (`global/spawner.scr:95-138`). Counts:
`docs/archive/traps-measured-wins-2026-07-22.md`. **The proven repair pattern:** extract the retail gag
verbatim from `mainta/pak1.pk3`, change **only** the single-entity `$player` refs, add NULL host guards,
leave everything else byte-identical (`gags/t2l4_start.scr:1-2`, `gags/t3l1_enemyspawn.scr:2`).

**Entities as `thread` parameters can arrive NIL, and a cross-file helper can return NULL outright**
(bugs 1624, 1632, 1665). Numbers always bind; an entity passed to `thread label a b c` may not survive
the boundary (and `ent thread label x` binds at most ONE arg). Park it in a **level array keyed by
numbers** (`level.coop_bpEnt[n + "_" + entnum] = ent`; precedent `level.coop_itemPapers`), pass numbers
only, re-read each tick. **⭐ bug-1665, NINE attempts:** `player_closestTo` returned **NULL on 90
consecutive measured samples** while a probe twelve lines below read both players fine (`hp=750
team=allies act=1 noclip=0`) - the label declares TWO params (`local.object local.origin`) and every
caller passes ONE. **When a helper "returns nothing", print INSIDE it and inline the same scan in the
caller; if the inline scan works, stop using the helper.**

---

<a name="t6"></a>
## T6 — What you shipped is not what loads

**Bugs:** 157, 247, 499/525/530/921/922 (a 5-round saga), 1129, 1190, 1216, 1610, 1633.
**Tell:** an asset edit has no visible effect, or a "black" surface appears, or a texture you never touched
changes.

| Load-order rule | Consequence |
|---|---|
| Pak order main < mainta < maintt < mod pk3s, **LAST copy wins** | A FIRST-match extractor shipped Spearhead's values (G43 yaw 1 -> 16; archive/traps-pruned-2026-09-05.md). |
| `.dds` beats `.jpg`/`.tga` | `R_LoadImage` tries `.dds` **first** (compression on): a stock `.dds` beat 881 HD `.jpg`s. Compression off is no fix (~1400 `.dds`-only textures vanish): ship full-mip DXT `.dds` overrides or NEW names (`env/hzmhd/`). gl1 can't read DX10/BC7 hdmem `.dds`: parse DX10 (bug-2994). |
| The engine tries `.jpg` **before** `.tga` | Menu art especially |
| Shader **NAME** overrides lose the reverse-concat race | Whole-**FILE** overrides win (filesystem dedupes by filename; coop pak mounts last; bug-921/525) |
| `zzzzzzzz_*` sorts after `zzzzzz_*` | bug-1190 |
| `.tik` surface directives must match the `.skd`'s real surface names | else `TIKI_InitTiki` drops them (bug-1216) |
| **A junction hides the loose half from your tools** | `G:\mohaa-gl2\{main,mainta,maintt}` -> GOG: `find -L`; pak-only scans miss loose files (bug-2336/2386). |
| Dev-only content skews audits **both ways** | bugs 2020, 2952, 2991. **Scope by the SHIPPED set (`manifests/latest.json`), never the install or the tool's own pak.** |
| **`newanim/<path>` beats `<path>` for every `.skc`** | tiki_files.cpp ~565 opens `newanim/`+path FIRST (Pak0 ships 2,415): a same-path clip override never loads (bug-3452). Ship a NEW `coop_` path, repoint the row. |
| Homepath `maintt/` beats basepath | **bug-1633:** stale cfgs in the live profile's `maintt/` shadowed every deploy (build.ps1 now deploys cfgs to all three targets); watch 0-byte decoys (bug-595). |

**⭐ THE FINAL ANSWER when a name is contested** (bug-922, closing the 5-round black-pouch saga): **stop
fighting for the name.** Mint a NEW shader name existing only in the coop pak, pointing at a PRIVATE
texture path also only in the coop pak, and retarget the `.tik` surface. **Tell:** a black surface with
per-face **shading** = a lit default shader drew it; your def never reached it.
**Precedence is PAK order, not file name** (verified 2026-09-05, bug-2485): both renderers resolve a
duplicated shader name to the highest-priority pak and, within one pak, to the alphabetically FIRST
shader file - a `zz_` prefix buys nothing. Define a name in exactly one coop file.

**⭐ A playtest log only testifies about the build it loaded** (bug-1610): the client quit at 23:37, the
file was packed at 23:38. **Compare the pk3 entry's timestamp (`zipfile.getinfo(name).date_time`) against
the `InitGame` line**, and verify fixes by reading them back out of the deployed pk3.

**⭐ Imported third-party skin packs are this trap with the blast radius reversed.** A 2002-era skin pk3
routinely *redefines* stock shader names instead of minting its own, and the coop pak mounts last, so the
import silently repaints every other model (one redefined all 15 `viewsleeves*` shaders for one pilot
skin; another broke the holster on *every* skin; 39-pack sweep: `docs/proposals/skin_batch.md`). **Diff
an external pack's shader block names against `scripts/*.shader` and the retail paks, and its
`models/player/*.tik` basenames against the stock tiks** - a matching tik basename *replaces* the stock
model. `map foo.tga` resolves extension-agnostically, so a shader naming `.tga` beside a shipped `.jpg`
is **not** missing.

**Related generated-asset hazard:** ESRGAN upscales have shipped worm noise, an all-black
`netgame_a/b` that blanked the server browser, and 29 overridden **vanilla** menu textures (bugs 1129,
247, 157). **Brightness-check output before commit**; it is for photos and text, and corrupts 1-2px
chrome.

---

<a name="t7"></a>
## T7 — Cvar registration, flags, and exec order

**⭐ BINDS CANNOT LIVE IN `coop_defaults.cfg`.** Order (`qcommon/common.c`): `coop_defaults.cfg` (:1841)
-> `configs/<config>` (:1847, **opens with `unbindall`**) -> `autoexec.cfg` (:1862). `seta` seeds go before
the config; a bind there dies every launch (bug-2093), so all binds live in `autoexec.cfg`. **Feature dead +
code obviously correct = check the bind exists first.** **And `exec` DROPS a file larger than the command
buffer - whole, silently, one line printed before qconsole.log opens:** autoexec passed the old 128 KB in
v1.8.8 and four releases shipped with no binds, What's New card or report webhook (bug-2908). Buffer is
1 MiB now; `build.ps1` blocks any cfg over 512 KB. **Both cfgs run on DEDICATED boots too** (`Com_Init`,
unconditional; both ship in the code pak): a default flipped for players flips every harness server, so a
harness that reads a marker passes `+set` for it (applied after both cfgs). `probe.scr` long claimed otherwise.


**An archived cvar is a latch** (bug-1427 x2, bug-2840). `seta` re-fires from `omconfig.cfg` every load
(`coop_buildmap` broke e3l4 twice; `r_novis 1` = a `0xC00000FF` startup crash), external edits lose (rewritten
at shutdown), and it FREEZES a tuning default (`bot_aimFloor "0.6"`). Consume mode-flips one-shot at map init;
never archive a diagnostic; new tuning knobs get flags `0` so default changes ship.

**⭐ Script `getcvar` CREATES the cvar EMPTY, permanently defeating the engine's own default**
(bug-1669). `ScriptThread::Getcvar` is `gi.Cvar_Get(name, "", 0)` (`fgame/scriptthread.cpp:2628`): a
script read before the engine registers the cvar creates it `""`, and the engine's later `Cvar_Get(name, "1",
...)` **keeps the empty value** (`->integer` 0 forever) - it killed `coop_limp`, `coop_tinnitusBlast`,
`coop_goreDripCorpseTime`.

**Script `.classname` is the C++ CLASS, not the spawn classname** (bug-2854): `RotatingDoor`, `Player`, not
`func_rotatingdoor`/`player` (`CLASS_DECLARATION`'s `#classname`). A `getentbyentnum` walk comparing BSP names
matched nothing ("doors opened=0"). Check the declaration before writing the comparison.

- **Detect:** rcon the cvar — `is:"" default:"1"` means it fired; a genuinely unknown cvar prints
  **nothing**.
- **Fix:** pre-register engine-owned `coop_*` cvars in `G_InitGame` (`fgame/g_main.cpp`), which runs
  before any script. **Any new engine `coop_*` cvar that script also reads must go in that block.**
- **Find the collision set:** intersect engine `Cvar_Get("coop_*", <non-empty default>)` against every
  `getcvar("coop_*")` in the scripts. It was six; four were genuinely broken.

*(summary table: [`archive/traps-t7-cvar-table.md`](archive/traps-t7-cvar-table.md).)*

**⚠️ A workaround in the SAVED config outlives its bug and beats `coop_defaults.cfg` forever** - **record
a cvar mitigation with its bug id and clear it when that bug closes** (bug-1990). LIVE: `r_ext_multisample 0`
stays until gl2 foliage-cutout bug-1298 closes. [T11](#t11) inside T7.

**⚠️ gl2 is the renderer we ship and test on** - confirm from the qconsole banner, never a doc.
Two corollaries:
**any cvar comment naming a renderer is suspect until re-read against that renderer's `tr_init.c`**
- `r_mapOverBrightBits` defaults 1 in gl1, **2** in gl2 (`tr_init.c:1886`): "1 = engine default" halved
world overbright; and **grep the OTHER renderer for a token before trusting a feature** - gl1 code can be
a `// FIXME: unimplemented` stub in gl2 (`nofog`, bug-2186). **A gl2 feature can still be unreachable**:
`alphaGen sCoord/tCoord` is GENERIC-only and a deform-free shader collapses into LIGHTALL - alpha 1, no
warning (bug-2486); bake the ramp into texture alpha (bug-2485). **A 2D quad's vertex alpha is NOT the
`R_SetColor` alpha**: an explicit 2D stage with `alphaGen vertex` draws at (1 - fade) - use `rgbGen/alphaGen
global` (bug-3462). Retail's `oneMinusVertex` is the same quirk, so the scope pillars bug-2008 called
transparent are opaque (s2b frames).

**The structural fix is half-built:** `coop_defaults.cfg` execs **BEFORE** the saved config, so its values
are true defaults a menu change overrides and persists. Migration out of `autoexec.cfg` is incomplete, and
any menu-wired cvar still `seta`'d there **cannot** persist; the two files are disjoint, so they never
fight. Counts live in `docs/generated/CVARS_COOP.md` - never hand-copied here. **A cvar seeded nowhere**
(no engine `Cvar_Get`, no cfg line) makes `getcvar` return `""` on a clean profile and a script fallback
branch silently decides behaviour, so **calling such a cvar "default N" describes a branch, not a
default.**

**Archived client state keyed by POSITION rots on every catalogue change** (bug-1926, full entry in
`archive/traps-pruned-2026-08-20.md`): **persist IDs, never positions**; stamp any positional cache with
a crc of the id list and wipe on mismatch; a generated lookup map is `set`, not `seta`.

---

<a name="t8"></a>
## T8 - server->client stufftext is a lossy, filtered channel

Ways a server->client message silently dies: an embedded quote truncates the wire argument, so send values UNQUOTED and one statement per
stufftext; the filter silently drops unscoped server-stuffed `exec`, unsafe `vstr` and unlisted
`set`; client `exec`/`vstr` INSERT at the buffer front while server stufftext APPENDS, so
the last line of a client chain wins and a server echo lags a round trip (a cfg `wait` holds it, bug-3211); and the
name bus dispatches ONE token per ~0.75s batch in BUS INDEX order, dropping other stacked tokens. A `.urc` widget below its menu's canvas height draws nothing, no error.

**The filter is a security boundary and must split EXACTLY like `Cbuf_Execute`** (`cmd.c`: quote
parity, `;`, LF, CR, `//`, `/* */`). `COM_ParseExt` keeps a glued `;` inside a token, so `echo;quit`
hid `quit`; a text ending inside `/*` carries into the next buffered stufftext and is refused;
vstr'd values are re-checked as statements (bug-2580). **A new server-vstr'd
name-bus marker needs a grammar entry in `cg_servercmds_filter.cpp` AND a shipped `cgame.dll` before
the pk3 change**, or remote clients silently drop it. Self-test: `docs/tools/sec1_filter_selftest/build.bat`.

**`name` is 32 chars: never put a must-not-lose signal on the name bus** (a truncated `,q<side>d` = can't spawn, bug-2767); use a registered `CVAR_USERINFO` cvar via `info_valueforkey`, as kit/cosmetics do.
**Client->server bulk** (bugs 3904/3905): a packet >~1.3 KB stalls (the exe never sends fragment 2; all unacked cmds ride each packet); dedicated drops cmds <1 s apart; `%` -> `.`. `cg_coopsync.c`.

**`showmenu`/`hidemenu`/`cinematic`/`spmap`/`map`/`disconnect` reach ONLY a listen host**
(`whiteListedLocalServerCommands`); remote clients drop them. Mirror: `coop_mod/menumirror.scr` (bug-3234).

**`ihuddraw_*` rides ONE snapshot, no retransmit**: a lost teardown strands it on a remote client -
claim on draw, re-send the hide: `coop_mod/hudresend.scr` (MP twin). Cases + bug ids: [archive](archive/traps-t8-stufftext.md).
**Every `coop_*` cvar is server-writable (bare form too): never put one on a command line or trust it as a destination** (bug-3276).

**A width-0 `ihuddraw` quad draws at the texture's NATIVE pixel size** (`0<w<1` truncates to 0; the rank bar's
promotion "gold square", bug-3076): hide a 0% fill with alpha.
**Hold-progress = the HD ring, by shader NAME** (bug-4035): a huddraw pair `textures/hud/coop_hold_track` +
`coop_hold_<revive|heal|place|use|objective>` (fill = slot+1, fraction = fill/track w) is drawn by `cgame/cg_hdprogress.c`
round the crosshair; `ihuddraw_color` ignored. `R_DrawTrianglePic` (exe+cgame together) culls back faces (`HD_Tri`). The pristine omconfig has `coop_hardcore 1` = NO bleed ring/crosshair in a harness: `seta coop_hardcore 0`.

## T9 - Same-frame spawn / model / solid race

**Fixed.** Write-up: [archive/traps-t9-spawn-race.md](archive/traps-t9-spawn-race.md). A `spawn`, its `model`
and `solid` cannot all land in one frame — step them. **And a `.tik` `model` swap RE-SOLIDIFIES:**
`ScriptSlave::SetModelEvent` (`scriptslave.cpp:893`) sets SOLID_BBOX for any .tik, so `notsolid` must
FOLLOW the swap (bug-2496, the Higgins hulls).

**Clip boxes (bug-3210, the m3l3 rocks).** (1) **A `script_model`'s box TURNS with its angles** - `ScriptSlave`
sets `EF_LINKANGLES` (`scriptslave.cpp:768`) and `CM_TransformedBoxTrace` rotates it, so a `getmins`/`getmaxs`
box is a crate around the anim bounds, and a clip sized "Y-long for yaw 90" lies ACROSS its target.
(2) **An asymmetric `setsize` is predicted as a SYMMETRIC box** (`IntegerToBoundingBox` keeps only maxs x/y,
~28u off): centre each clip on its own origin with integer half-extents. (3) **`disconnect_paths` on the full box
strands the nodes beside it** (`Path not found`, the actor stands still; `NearestStartNode` lifts its trace
32u): cut with the box inset by the hull half-width (15u), then restore it. Recipe: `gen_m3l3_rock_clips.py`.

**Wall props are placed by TRACE, never by eye (bug-4005).** Hand-snapped switches sat in doorways. Use `docs/tools/alarm_place.py` over `bsptrace.py`: origin = wall hit + normal * 3.3, yaw =
atan2(normal) exactly, z = floor + 52 (measured on vanilla; bell same wall +56); one flat plane
(57x48 patch, visible shader), 96 u clear in front, >= 56 u from every `func_*`/`script_object` mover (doors, windows,
ladders are NOT in the world brushes, a trace cannot see them), a pathnode near the stand spot, >= 700 u from spawns
(`info_player_start` is not the coop spawn). Defend zones likewise: `gen_counter_zones.py` (pathnodes float
0-110 u over the floor; outdoor ground is `terrain_z`, not a brush).

---

<a name="t10"></a>
## T10 — Deploy gaps: the source is not what is running

**Bugs:** 089 (the mirror case), 930, 1172, 1219.

**Tell:** a fix that is definitely in the source has no effect in play, or a log line reports a limit
lower than the header says. Both directions happen: edited but never built/deployed (bug-089); and built
and deployed when it shouldn't have been (bug-1172 - `build.ps1` run during a gl2 sandbox session
pushed sandbox-only limit binaries into the user's **real install**).

**The deploy set is complete (six binaries, bug-1796/1634) - verify anyway: a "verified" claim names the
binaries and proves them by HASH against the build output**. `build.ps1`
refuses while the game runs (the user then tests the PREVIOUS build); a wrong `cmake --target` prints
`MSB1009` that `| tail` masks, so a stale DLL deploys.
**Some changes must ship as a PAIR or they are worse than not shipping:** `bg_pmove.cpp` compiles into
`game.dll` *and* `cgame.dll`, so a movement change in it desyncs client prediction from server truth if
either ships alone (bug-2149); a protocol-constant change ships exe + cgame + game together.

**Push nav is DIRECTED** (bug-2870/2871): fall links are one-way; after nav changes run `push_spawn_sweep.py` + `nav_sinks.py` (bug-2901). The mesh bakes at level spawn, BEFORE MP scripts seed spawns / clear debris: keep it reversible. **Coop helpers reachable from MP must test `level.coop_mpRun == 1` before `inCoopMode`** (bug-2968).

**A bot feature that logs its DECISION proves nothing - log the ACT** (bugs 2875-2877): `CheckValidWeapon`
re-drew the gun in the no-weapon frame of every grenade switch (no bot grenade ever flew); `TurnThink` stops
turning inside 20 deg of target (exact aim needs `SetPrecise`); a bot's eye is the `usereyes_t` offset it
sends (lean was cosmetic). Log the outcome (`nadeloose`, BOTPROBE `cov=`).
**A gate that trims a rescue's false positives trims true ones**: bug-2889's 60u/s wedge gate froze a bot at 50u/s
(bug-2891). Re-soak the map behind the OLD behaviour.
**Bots are tuned at a PACE - `sv_dmspeedmult`** (autoexec 0.6; engine default 1.1). v1.8.8-1.9.1 dropped autoexec
(bug-2908), so every Push tune ran at 1.1 and regressed at 0.6: m4l2 stuck 14% vs 1-4%, all at the lift whose
timing assumed 1.1 (bug-2912). Soak at the shipped pace - check SPEEDPROBE `dm=`. **A steering state machine must
die with its bot**: the lift protocol outlived a death and steered the respawn straight at the lift across the
map - reset on spawn, drop when far. `Q_clamp(a,b,c)` ASSIGNS into `a`: use `Q_clamp_float`/`Q_min(Q_max())`.
**Under coop_sprint a CLEAR `BUTTON_RUN` is the SPRINT key** - "drop RUN to walk" made bots sprint across danger
ground (bug-2920); the walk is `BUTTON_COOPWALK`. **BT grenades COOK** (`minlife` -> P_CHARGE_LIFE): the hold that
throws farther also shortens the fuse, so charge-scaled lobs air-burst (~65%, bug-2925). A `CVAR_ROM` serverinfo
flag is written only by script `setcvar` (forced); a cfg `set` is refused - zero it per map in `G_SpawnEntities`.

---

<a name="t11"></a>
## T11 — Trusting the record over the code  ⚠️ STRUCTURAL

**Reviewers sharing an upstream source are one witness** (bug-1290: three lenses confirmed a "bug" resting on one unchecked premise). **Verify the load-bearing premise in the code yourself.**

**A later entry can silently reverse an earlier one, so read the ordered LIST, not one entry.**
`docs/generated/FIX_INDEX.md` (file -> ordered bug ids) is the fix; the story belongs in HISTORY. Nothing
in the schema flags a reversal, so **edit the original entry** when you supersede a finding - bug-1473/1474
were corrected in place on 2026-08-06 after being filed on the wrong files.

- **A plan's STATUS HEADER is a record too, and it rots hardest.**
  `_research/composure_and_ads_plan.md` still said "PLAN ONLY - nothing built" four days after Part A
  shipped in v1.4.4, with the correction 500 lines down, and sent a session to re-fix a fixed defect
  (bug-2089). **When a plan ships, edit its header and mark the superseded body in the same commit** -
  the top of a file is what gets read.
- **Wrong anchors are worse than no anchors.** `q_shared.h:1680` credits the `MAX_MODELS` 1024->2048
  raise to **bug-866**; the actual work is **bug-892**, and a grep at a wrong path reads as "already
  fixed". **28 bug ids cited in source comments have no buglog entry** - bug-237 (packer determinism,
  `build.ps1:11-15`), bug-241 (never deploy under a running game) and bug-239 (the brace-counting
  lesson) among them; **for those, the code comment IS the only record.** *(buglog tooling hazards: id formats,
  append-never-rewrite - `docs/reference/buglog_maintenance.md`.)*
- **⭐ Leave the correction at the site.** `maps/m1l1.scr:1683`, `coop_mod/loadoutpick.scr:436-440` and
  `q_shared.h:1690-1755` are self-documenting and all three survived a later session.
- **When classifying REVERTED, separate "it broke" from "the user changed their mind"** - only the former
  is a lesson; bug-787 reversed a design at the user's request.

---

<a name="t12"></a>
## T12 — Name collisions between two identically-named trees

**There are TWO `_research` trees** and records conflate them: `C:\mohaa-coop-dev\_research\` (design
docs, audits, **the regression harness**) and `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\_research\`
(buildmode inventories, `hud_slot_map.md`, `director_dda_plan.md`) - only the second is inside the shipped
tree; `build.ps1`'s `$excludeTop` skips both. **Still open:** the regression harness - the
only working automated verification - lives in a directory named `_research`, which the build script
treats as disposable; **promote it out**. Related: four uppercase map scripts (`M1*`, `M3*`, `M5*`,
`M6*.scr`) sit alongside lowercase counterparts, unchecked for case-collision in a pak.

**The same trap one level down: two subsystems sharing a `level.*` name** (bug-1612).
`coop_mod/ambience.scr:42` owns `level.coop_ambEnt` as a single `script_model`; the telephone-gag work
later added `level.coop_ambEnt[alias] = emitter` as a **dictionary**. The entity wins, so every indexed
read throws `[] applied to invalid type 'listener'` once per ambient on every map - skipped not fatal,
so nothing crashed, and the sole casualty was m1l2b's ringing-telephone gag, which polls that dictionary
100x0.1 s and so always burned 10 s and printed `PHONEGAG FAIL`. **Grep the mod tree before adding
a `level.coop_*` name — the error names the type, never the other owner.**

**And inside ONE label: a local used as an int flag, then as an array** (bug-2483). `local.ok = 1`
in a wait loop, `local.ok[n] = x` ninety lines later: `[]` on an int throws, the store is skipped,
both reads come back none and both 044a voices went to NIL for four days while the label's own
probe printed a healthy pick count. Grep a label for `local.X =` and `local.X[` before reusing a name.

**And one level down again: two ENGINE EVENTS sharing a script command name** (bug-2064). `notarget` is
declared twice as `EV_NORMAL` (`Entity::NoTarget` SETS, `Player::NoTargetCheat` XORs) and `ScriptMaster` keeps
one name -> eventnum entry, last write wins (`scriptmaster.cpp:616`): which handler runs is a build detail, and
the result looked intermittent (call parity). **Grep the engine for a second `Event` with the same command
string; if there is one, make BOTH handlers agree for both call shapes.** The `Event` declaration is the
contract, not the name (also `.gun` bug-2046, `enableEnemy` bug-2034). Full story: [archive](archive/traps-pruned-2026-09-28.md).

---

<a name="t14"></a>
## T14 — Your verification lied: audits that pass, harnesses that measure nothing


**PROBE DESIGN - three ways a probe lies** (plus: `r_gfxProbe` bit 2 PINS refdef.time, so
every dt-driven fade reads dead: bug-3072/3091). *(1) Nested inside the condition it measures* - blind; put
it OUTSIDE the branch and print the deciding inputs. *(2) Reading back
your own input* - `m_fCoopHeadYaw` tracked perfectly while the networked value was clobbered by a
subsystem the probe never read (bug-2102). **Probe the FINAL consumed value**; prefer a **sentinel the
other writer cannot produce** (head `11/22`).
*(3) Never exercising the branch* - **force it**: `coop_boneDebug 2` runs the prone maths on a standing
player, separating "the maths is wrong" from "prone never engaged".
*(worked examples archived to `docs/archive/traps-t14-worked-examples.md`)*

**THE TOOL LIED, NOT THE CODE - six species, all returning plausible results.**
*(a)* **`grep` bails on a binary line**: a NUL in `qconsole.log` makes plain grep print only
`Binary file ... matches`; a marker "never fired". **Always `grep -a` on logs.** *(b)* **A shell-eaten
pattern matches everything** (`grep -c $'\r'` = the line count, "proving" LF files CRLF): **count bytes.** *(c)* **A pass that cannot fail**: `x | head -5 && echo OK`
is always OK (`head` exits 0); a `.ps1`'s `exit 1` is no error to a `&` caller, so a failed build
published (bug-2579) - check `$LASTEXITCODE`. **Gate on the tool's exit code, not a pipe.**
*(d)* **`check_map_compiles.py` is flaky against a LIVE dedicated server** (stop
`omohaaded`/`openmohaa` first) **and only proves the map INITS** (bug-2530 broke 2 min in, passed).
*(e)* **The preprocessor dropped it**: the menu-theme picker passed build, audit and deploy from
`snd_main_new.cpp`, never compiled here (bug-2572). **After an engine
change, `grep -a -c` one of its string literals in the built binary.** *(g)* **GLSL lint + glslang never
see C**: staged `tr_hzm_wet.c` used file-static `s_worldData` and passed both (bug-3150) -
under a no-build rule, `cl /Zs` the touched files.
*(f)* **PowerShell 5.1 re-splits embedded double quotes to a native exe** (an rcon
`stufftext "..."` arrived as several args): send such payloads from python.
**Absence of a marker is not absence of behaviour** (`playsound` prints nothing): every new beat gets a `^~^~^`
marker or a census reads it as missing.
*(h)* **A rubric gates only what it measures**: water/wet passed every sparkle/seam gate; users saw ruled
cut-offs at object edges (a 1-tap height map traces outlines). Add an object-edge view.

**Harness:** `ui_startdmmap` sets `cheats 0` (tele/face refused); a `map` restart to get cheats back lost the
coop weather (bug-3174): move the camera by overlay script. **one frame = `wait 1; wait 1`** (bug-3314), **`cg_drawviewmodel 1` hides
the arms**, **one frame keeps ONE `screenshot` name** (static fileName): give each shot its own frame (bug-3253). A client is in `status` before its Player exists (`Could not find entity *0`). **A test client boots SPECTATING**; `join_team` alone leaves it out - gfxrun `join()` sends
`+attackprimary` from its console. Launch via `harness_window.py` (bug-3147). **A violation-planting self-test** writes only `zzselftest` names and
anchors in the checker's comment-stripped view (bug-2579).
**`god` is a no-op - the cheat is `dog`** (`god` = a NULL forwarder; bare `god` in rkeep/vcl/lt_ab did
nothing). Send `dog 1`/`notarget 1` and require `CHEAT: godmode ON`; add `g_ai 0`,
`coop_dbno 0`, `ui_gmbox 0`+`ui_checkrestart` or AI fire, shell shock, gmbox text hit frames (bug-3182).

## T16 — Waits that never complete: failsafe recursion, missing anims, unguarded `waittill`

**Bugs:** 1361-1366 (e3l4), 1367, 1368, 1370, 1579, 1921, 1945, 2487; same shape as the AB41 and
truck-unload failsafes. Example: `docs/archive/traps-t16-failsafe-recursion.md`.

**Tell:** a report repeated across a failsafe line; an actor frozen mid-action; a mover that never
finishes - **a `ScriptSlave` blocked by a solid actor never posts `movedone`**; `BlockFunc`
(`scriptslave.cpp:1360`) crush-ticks the blocker 2 hp/0.5 s and the kill gibs him (NULL). The
Higgins sink rolled its solid clip into a deck-hand for three sessions (bug-2487): drop the solids first.

**A recovery path must contain no wait that the failure mode can block.** The e3l4 failsafe bounded a
blocking wait at 45 s then "recovered" by calling a routine opening with `runto` + `waittill movedone` -
the actor's whole problem was having no nav path, so the soft-lock moved rather than closed. For actors:
no `runto`/`walkto`/`waittill turndone`/`waittill animdone`, no unbounded
`while (vector_length(...) > N)`. Place them directly (the **tail** of the vanilla routine); grep the
recovery path for `waittill`; check the *next* stage too.

**Two engine facts make actor waits unsafe** (bug-1368): `Unregister(STRING_TURNDONE)` exists in exactly
one place, `Actor::IdleTurn` (`actor.cpp:5032`), which no runner think reaches - so a failed `runto` pins
the actor in `THINK_RUNNER` and any `waittill turndone` there blocks **forever**, while `waittill
movedone` is safe because `CheckUnregister` (`actor.cpp:7793`) fires it even on `parm.movefail`.
**`runto` → `turndone` hangs; `runto` → `movedone` does not.** **And `runto <vector>` only works where the mapper baked
pathnodes** (bug-2246): a bare vector becomes a patrol node whose branch calls `SetPath()`, a graph
search, so with no nodes the actor never takes a step and the only symptom is one `Path not found` per
leg. The `IsSubclassOfWaypoint` branch instead does `SetDest` + `ANIM_MODE_DEST` and walks straight at
the point with no graph at all (`actor.cpp:3998`) - so for coop actors placed anywhere the map's own AI
does not go, **`spawn info_waypoint`, move it, and `runto` that**. Related: **never invent an
exit/placement offset when the model carries an authored one** - vehicles ship `driver_enter` /
`passenger_enter` / `*_seat` tags, walkable by construction (bugs 1367, 1370).

**Missing anim + `waittill` = a corpse standing at the wall.** `setmotionanim` with an alias the model
lacks silently no-ops and the following `waittill flaggedanimdone` hangs that handler FOREVER (bug-1921).
(1) Never feed a per-weapongroup anim name to `setmotionanim` without a whitelist + fallback (the
Cornering wall set is LIVE for exactly rifle/pistol/mp40/mp44/bar/thompson/sten/vickers). (2) Audit
aliases by grepping the tiki TEXT, not `.skc` FILENAMEs, which undercount badly. (3) An alias in
`human_<wg>.tik` is NOT resolvable unless that pack is `$include`d by the model - vanilla gates them in
per-map `includes` blocks, so a coop feature must add them unconditionally to our
`new_generic_human.tik` override (bug-1945).

**A scripted conversation strands when a `waittill` outranges its guard** (bug-1579; retail chatter assumes
live, idle talkers): (a) wait only on an actor you actually animated, held in a local; (b) test `!= NULL`
BEFORE `isalive`, separately - a throw skips the guard and runs its body; (c) gate on `thinkstate == idle`, not
`!= attack` (`anim` runs at `THINKLEVEL_IDLE`). **Silence the LINE, never abort the THREAD** - the label's tail
holds the release (`runto`, `enable_ai`, `type_disguise`). Helper `replace.scr::convOk`; detail in the
[archive](archive/traps-pruned-2026-09-28.md).

---

<a name="t17"></a>
## T17 — Script VALUE types: 'none', keyvalue strings, and who owns an event

One failure in variants: the value is not the type the reader assumes, the thread dies at that line, and
the caller still reports success. **Tell:** a feature that "does nothing" with no crash, plus a
`Script Error` naming a file and line you were not looking at.

- **Reading a level var CREATES it with type `none`** — `GetVariable` returns non-NULL for a var that
  exists but was never *assigned*, so a NULL guard passes and `intValue()` throws. **Always ASSIGN a
  level var before anything reads it.** (bug-1371)
  - **⭐ A THROW INSIDE A `while` CONDITION SKIPS THE WHOLE LOOP** (bug-2530). "Skips the statement"
    is survivable in a body and catastrophic in a test - the statement *is* the loop, so control
    falls to what follows. Both m3l1a ramp watchdogs read a var assigned later in the beat, threw on
    `120 + none`, and ran their **timed-out** branch at t=0: one forced the handoff, spawning the
    player on the beach a second into a cinematic that then played to nobody. **Seed at the READER,
    not at the feature's config block** - which may sit below the reader's thread site and behind
    the feature's own kill switch. `== NIL` and `!= 1` are safe on `none`; `+ - / <` are not.
- **Map entity keyvalues arrive as STRINGS** — `int()`-coerce once at the top, not per comparison.
  (bug-1352, bug-1372)
- **A command registered on `ScriptThread` is NOT a Player event** — `iprintlnbold`/`iprintln` are
  ScriptThread-only, so `<player> iprintlnbold "..."` silently fails; the Player form is
  `iprint <text> 1`. **The same shape one level up: a primitive that reads per-player and is actually
  the whole SERVER.** In coop `missionfailed` runs `replace.scr:2644` -> `main.scr:2015`
  `stuffsrv "map <this map>"` - a full reload for everyone, so failing one player with it restarts the
  other three. `fadeout`/`fadein`/`clearfade` write `level.m_fade_*`, which `Player::CalcBlend` copies
  to **every** client, so one player's blackout blacks out the server. Per-player failure and
  per-player screen state must be built from per-player primitives - `self.flags[...]` and an
  `ihuddraw_*` slot, which is per client (bug-2528).

  Worked examples and the failure histories for these three are in
  [`archive/traps-pruned-2026-08-20.md`](archive/traps-pruned-2026-08-20.md).

---

<a name="t20"></a>
## T20 — One flag, two states; and one-way latches

Shapes where the symptom pointed away from the cause (m6l1c, 2026-08-11).

- **A flag that answers two questions gets tested for the wrong one.** `is_disguised` is the engine's
  per-frame opinion (`player.cpp:5519-5545`); `has_disguise` is the mod's own grant. Testing the first
  where the second was meant read "someone is shooting at you" as "the grant failed" (bugs 1701,
  1701b, 1703). Tell: **the viewmodel and HUD stutter** - AI churn alone does not stutter a client.
  **Count how many things can make a flag false before testing it, and bound every self-re-threading
  retry.**
- **A one-way primitive lives in more files than you grepped.** Bare `attackplayer` is
  `Actor::ForceAttackPlayer`, cleared **only in the Actor constructor** (`actor.cpp:3092`), and while
  set `EnemyIsDisguised()` is false unconditionally - one call blinds that actor for the map.
  `attackentity <ent>` is the reversible form; four sites, three sweeps (bugs 1700, 1704, 1708).
- **An absorbing state hides everything downstream.** `EnemyIsDisguised()` also returned false for any
  actor in `THINKSTATE_ATTACK`, and it ratchets. Fixed by requiring real threat (bug-1707), as
  `player.cpp:5541` already did. Blocked-aggro across one run: **1051 -> 0**.
- **A flag two systems both own is a race, and it comes back.** `coop_clickablePapersEnabled` (set by
  `enableClickablePapers`, cleared by `coop_bustArm`) re-armed mid-bash restarted the papers loop and
  force-equipped papers into the hand holding the drawn pistol, so **the player could not shoot** -
  five rounds to kill it (bugs 1709, 1726, 1732, 1735, 1736). **One writer per player; clear the flag
  and yield a frame before threading a loop that sets it; split the latch from the state and clear it
  on every exit. Moving a flag's assignment earlier rewrites every guard that reads it.**
- **A one-shot guard is not an invariant.** Pinned challenges refused to ADD a finished one and dropped it
  when it finished, so a later path that landed a done one kept it for good (bug-2544); actor weapons took four
  fixes for one bad state (bugs 1957, 1971, 2009, 2546). **If a property must always hold, assert it in a routine
  that already runs unprompted** (the 3 s pin publisher, `Actor::Think`): cheap, self-healing, names the producer.
- **`hide` on a player is a latch.** cgame never submits a hidden (RF_DONTDRAW) player, so everything attached
  to it - view gun, dust veil - fails `R_GetRenderEntity` and vanishes (developer 2: `Could not find parent
  entity`). m1l1 hid everyone before reading `intro`; only the ride's end showed them, so `intro 0` = no gun all
  map (bug-3323). **Show on every exit of a hide.**

---

<a name="cross-cutting"></a>
## Cross-cutting: the questions to ask before "it doesn't work"

1. **Did it compile?** ([T1](#t1) — `developer 1`, running-depth scan)
2. **Did it run?** ([T3](#t3) - prove execution before tuning; check the gate cvar is seeded). And when a
   constant becomes a cvar, **update every reader in the same pass** (bug-1733/1734).
3. **Is the binary I'm testing the one I built?** ([T10](#t10) — three binary states are live now)
4. **Am I reading the record or the code?** ([T11](#t11) — the code wins; read the record to the END)
5. **Am I guessing, or measuring?** (was T13) **BISECT FIRST - a cvar bisect beats any number of
   hypotheses** (bug-1298): turn things off one at a time until the symptom moves.
6. **Symptom or design?** A fix producing the MIRROR IMAGE of the bug means the design underneath is
   wrong. "Stuck prone" and "popped back to crouch" were one flaw from two sides (bug-2108): an escape
   valve added to work around a broken standup trace force-stood the player a second after they let go.
   **The user's phrasing often names the design** - "space or control should put me back into crouch"
   described the INPUT MODEL, and was read as a trace bug twice.
7. **Did I look at the moment it breaks?** An event-bound symptom needs an engine screenshot AT the event
   (bug-3076: `coop_st_xp_mode promo`).

---

<a name="tiki"></a>
## TIKI and sound-alias traps

**`<actor> say <alias>` IS AN ANIMATION CALL, NOT A SOUND CALL** - it drives the mouth and can block;
a missing alias animates a silent mouth. **A bare animation alias DROPS THE NOTETRACKS that do the
work**. Both are in `docs/reference/tiki_and_sound_aliases.md`.

**A sound alias's `maps` field is a LOAD FILTER**: off-list the alias does not exist and `playsound` is
silent (bug-2248); with NEITHER `maps` nor `always` it registers nowhere - never strip
`always` to hush a warning (bug-2728/3098). Grep **name AND maps**; tokens are PREFIXES (`m4` covers `m4l3`, `m3l1b` not
`m3l1a`; bug-2394). A `loaded` alias's `maxDist` is a hard START gate; `streamed` ones go 2D (bug-2309).
**playsound names are PREFIX pools** (`X1` draws `X10..19`). Voice letter `n` = Manon (female), MP `z` = SAS
(UK); BT nation = speaker id `_AS/_BS/_RS` (bug-3385..3387).

**A `random` alias group registers under its digit-stripped STEM.** `crouch_beach_idle01..05 ...
random` loads as ONE anim, `crouch_beach_idle`; `anim crouch_beach_idle02` is `unknown animation`
(`tiki_files.cpp:1046`; bug-2214, 2498). Address the stem, never a member.

**An animation pack is gated by a PREFIX match on the MAP NAME.** `new_generic_human.tik` wraps packs
in `includes <tok...> { }` and `TIKI_ParseIncludes` (`tiki_parse.cpp:345`) makes a block live only if
one token is a **prefix of the live map name** - so `includes test utils traf holodeck coop` does NOT
match `m3l1a` (crate_carry/welding were unreachable on Omaha). Adding a pack is one `$include` line.
**`docs/tools/check_map_anims.py` fails the build** on any `anim`, `playsound` or model path that
does not resolve on the map; facts in its docstring (SKC loop flag at offset **8**,
a looping alias never fires ANIMDONE so a following `waittill animdone` parks forever, PREFIX GROUPS -
`alias.c:545`). `check_say_aliases.py` covers `say`/`sayd`.

**`gun X`/`.weapon = X` REBUILDS the actor with X as the `case weapon` key** (bug-3306/3325). No default
case: an unmatched key (getter name, `shotgun`, init weapon) drops all case content - the BODY where it is
built there, else identity gear (radio, helmet). Use `coop_actorArm`; keep identity gear
outside cases; `audit_actor_surfaces.py` checks both. Dying under `physics_off` skipped KILLED (bug-3324).

**A TIKI's `init { server { ... } }` runs even when you `spawn script_model model "<path>"`.**
`fx_tank_explosion.tik` carries `classname Explosion` / `radiusdamage 120` there, so a cosmetic set
piece killed the player while the script held no `radiusdamage` at all and a script audit found
nothing (bug-2244). **Read the TIKI, not just the script**; copy a retail effect under a `coop_` name
minus those lines. Same fact decides how you spawn one: an `init { client { } }` block fires at the
first **snapshot**, after the server set the origin, so *spawn, then position* is correct
(`bh_water_hard`); a **server** block fires at spawn, so its origin must be inline or the effect
bursts at the world origin. The two read identically in a script.

**A `script_model` carrier renders a tik's `originemitter` blocks and NOTHING ELSE** (bug-2477).
`sfx` blocks are recorded only while `LoadEffects` holds `m_pCurrentSfx`, and an `originspawn` in
`init { client {} }` is visited once at registration with NO entity - so a one-shot burst on a carrier
belongs in an animation's `enter` frame commands, as retail exp_flak_near does (bug-2507). An emitter
follows the carrier's ANGLES only with `notagaxis`. Author counts for `cg_effectdetail 1.0`: the mod
ships 1.0 against retail's 0.2, and `count`/`spawnrate` are multiplied by it, so x5-for-retail tiks
are 5x too dense here (2477, 2507).

**`playlocalsound <alias> 1` writes ONE FIELD, not a channel.** The loop branch of
`Player::PlayLocalSound` sets `edict->s.loopSound` (`player.cpp:18183`), one int, so a second local loop on the same entity **silently overwrites the first**, and
`stoplocalsound` also kills the CHAN_LOCAL one-shot; `dbno.scr` started three, only the last played
(bug-2432). Volume is hardcoded 1.0 - bake the level into the wav (bug-2431). Flag 1 is
`LOOPSOUND_FLAG_NO_PAN`: 2D, centred, **no distance falloff** - and loopSound is broadcast, so every
client emitted every *other* player's private body sounds until `CG_LoopSoundIsForeignLocal` (bug-2429).

More in **`docs/reference/tiki_and_sound_aliases.md`** (incl. dialogue aliasing) - read before
touching a `.tik` or adding an alias; `audit_weapons.py`/`audit_shaders.py` make those testable.

---

<a name="script-error"></a>
## ⭐ A `Script Error` does NOT kill the thread — it SKIPS the statement (verified 2026-08-06)

`ScriptException::next_abort` defaults to 0 (`scriptexception.cpp:30`); `ScriptVM::HandleScriptException`
(`scriptvm.cpp:1915-1933`) rethrows only `if (exc.bAbort)`, else prints `^~^~^ Script Error` and resumes at the NEXT
instruction. Only stack overflow (`:1038`) and command overflow (`:1867`, `ERR_DROP`, t2l3 bug-1493) abort.

**Read every error site as "this statement was skipped", not "everything below died."**
- **An `invalid waittill` means the script does NOT WAIT.** Everything below runs *immediately* -
  sequences fire before their preconditions, entities are touched before they spawn. That is why the
  `waitTillSpawn`/`waitTillPrespawn` shims still matter (bugs 1458-1469).
- A cast error inside a `while` body removes the *statement*, not the loop (t2l3 span 4,347 times with no yield).
- **Values parsed out of a `.dat` file are STRINGS** (bug-1352): `if( x > 0 )` throws and the assignment never
  happens while the caller prints success. Coerce with `float()`/`int()` at load; tell: works live, never from its save.
- **A probe that throws prints nothing.** An unset var reads `none` and `"str" + none` throws (bug-1702): sanitise first.

---

<a name="turrets"></a>
## Turrets and AI spread: five ways a tune never reaches the gun

**Bugs:** 1920, 1940, 1946, 1950. **Rule: before tuning a value, prove the failing PATH reads it -
grep the consumer, not the setter.** Full write-up:
[archive](archive/traps-pruned-2026-08-20.md).

- **A MANNED turret never reads `bulletspread`** - `weapon.cpp`'s `FT_BULLET` sets `vSpread` only for
  `owner->client` (unmanned guns: `(max+base)/2`). An actor's ONLY dispersion on one is `m_vAIBulletSpread`, set by the
  `aibulletspread` event (retail SH/BT: 300-450; arg 2 is ignored). Gunner `accuracy` does
  nothing. (bug-1940)
- **AI spread is an AVERAGE** - `Weapon::Fire` gives a non-client owner
  `(bulletspreadmax + bulletspread) / 2`, so `bulletspread 120 120` is an effective 60.
  **Set all four args: `bulletspread B B M M`.** Player fire is unaffected. (bug-1920)
- **`TurretGun` fixes NEVER reach `VehicleTurretGun`** - it overrides `Think()`,
  `UpdateFireControl()` and `GetMuzzlePosition()`, so halftrack, tank MG and jeep guns skip
  every TurretGun tune: no MG heat (bug-1946), full AI damage and accuracy (bug-1950).
  **Any turret-behavior change ships BOTH class paths.**
- **An AI gunner fires at `sv_fps`, not `firedelay`** - `AI_DoFiring` calls `Fire()` every frame
  of a burst (40 / s live; MG42 nests are tuned at it). `coopaibelt 1` gates a gun. (bug-3638)
- **On a turret the TORSO state is the whole body** (`movetype anim`; the legs machine is off, its
  turret rows are dead), and an action row is picked once, on entry. (bug-309, 3658)
- **`damage` event's LAST arg = hit LOCATION; 0 = HEAD = x4** (`ArmorDamage`). A floor needs the amount
  clamped AND location 3 (torso x1.0) (m3l3 church, mortars: bug-4032).

---

<a name="itemname"></a>
## Weapon variant suffixes - every consumer must strip them (two conventions, do not mix)

**Two spellings, and an exact-name key misses ~92% of the set in both** - full entry in
**[`archive/traps-weapon-variant-suffixes.md`](archive/traps-weapon-variant-suffixes.md)**. TIK filename
`<base>_<finish>`: drop trailing `_segments` one at a time, never cut at the FIRST underscore. Display
string `"<Base Gun> (<Finish>)"`: split on `" ("`. Different conventions; neither substitutes for the
other. **Any new consumer tries the exact match first, then the stripped base name.** (bug-1982)
A view-model PREFIX spans meshes (kar98: G98, Arisaka): gate per-mesh art on sight geometry (bug-3337).

---

<a name="procedural"></a>
## Procedural view/weapon motion

Six rules, [`archive/traps-view-motion.md`](archive/traps-view-motion.md): integrate oscillator phase, never
`time*frequency`; ease an amplitude, not a periodic state; cap in world units; a scaled shared budget makes
controls non-linear; never low-pass the pose-to-camera term (bug-3207). Read before touching view motion.
View-model previews: include the drawn bone controllers, the gun's hand surface, the engine weapon fov (bug-3334).

## Coop systems that touch EVERY actor will find the scripted ones

Every global actor pass - the weapon-variant roll, the AI personality roll, enemy count-scaling -
runs on a map's SCRIPTED CAST as readily as on its garrison, and a scripted actor is defined by state
the pass casually overwrites. `coop_variantRoll` ends in `self.weapon = <tik>` + `self unholster` and
re-armed scene actors (bug-1949; m1l1's rifle-on-wheel driver: bug-3052); the personality roll
overwrites `type_attack` and locks a prone pose on scripted actors.

**Every fix has been correct and too narrow.** bug-1949 guarded the variant roll with `self.no_idle`,
which appears in 19 scripts while **42 hold ler actors** - so m1l1 broke again a month later. That
arithmetic is the tell: a guard covering fewer sites than the hazard has is one you will write again.

**The rule: one shared scene test, never a private one per pass.**
`officer.scr::coop_isProtectedActor` is that test. A new global pass calls it; it must not
invent a second, narrower check that will drift out of step with the first.

**Detecting scenery generically.** Maps declare it three ways; `audit_scene_actors.py` finds
all three, and each now has a guard (bugs 2033/2035/2037/2038, one per pass):

| marker | readable as | guarded in |
|---|---|---|
| `exec global/disable_ai.scr` | `coop_aiDisabled` (our override sets it) | `coop_isProtectedActor` |
| `anim_scripted` | `self.no_idle` | `coop_isProtectedActor` |
| `threatbias ignoreme` | `self.threatbias == 0 - 6969` | `coop_variantRoll` **and** `coop_apply_personality` |

**Match a guard's scope to what it costs to be wrong** (bug-2051).

**Before guarding on a property, prove you can READ it.** `enableEnemy` is a lone `EV_SETTER`
(actor.cpp:1470), so reading throws - 136 errors a map, and since *a Script Error skips the
statement* that guard shipped having never once executed (bug-2034); `threatbias` has a real
`EV_GETTER` (sentient.cpp:469) and reads fine. **Probe at runtime first, then re-probe against a baseline
count.** A
depth scan proves a script *parses*, never that a property is *readable*.

Actors that are only *holstered* still have no generic marker; flag those with
`flags["coop_sceneActor"] = 1`, which spawned actors need anyway - a targetname list cannot reach
them. The *unarmed-looking* case is handled generically now: see the invariant bullet in
[T20](#t20).

---

<a name="t21"></a>
## T21 — Removing an enemy from the fight is not the same as killing him

**Bugs:** 1972 (M3L3 church), 2088 (array counts), 2091 (m3l1b bunker). **Three times, three maps.**

**Tell:** an objective that says "kill them all" never completes and the survivor is somebody the player
recruited or disabled.

Maps count enemies **two unrelated ways** - an ARRAY of living axis, and a PER-ACTOR
`waittill death` - and a fix for one does nothing for the other; bug-2088 shipped believing it
covered both. Detail in [`archive/traps-t21-counting.md`](archive/traps-t21-counting.md).

**⭐ And the resulting softlock is ABSOLUTE.** `Sentient::TakeDamage` filters same-team damage in
**every** gametype (`sentient.cpp:1705-1706`, and `:1752` states the consequence: *an allied victim
never reaches health <= 0*). Once an actor is on your team the player **cannot kill him by any means**,
and there is no player-side recovery or console command - the run is lost. Never design anything that
relies on a player finishing off an ally.

**The fix pattern, for anything that takes an actor out of the fight without killing him:** fire the
notification, not the death. `Unregister(STRING_DEATH)` is exactly what wakes a `waittill death` and
is what the real death path already uses (`Actor::Killed:5505`, `Actor::Remove:12229`); calling it
alone releases every waiter while health, deadflag, think state, gun and corpse stay untouched. It
cannot double-count, because each watcher does `waittill` -> `++` -> `end` and is gone before any
genuine later death. **Check what else waits on that actor first** — a watcher polling `isAlive`
(like `surrender.scr::convertedWatch`) is unaffected, but one using `waittill death` would fire early.

---

<a name="t22"></a>
## T22 — The usercmd button bits are FULL. Use a `+`/`-` console command.

**Tell:** you want a new held/bindable action and reach for a `BUTTON_*` bit.

There are none. `q_shared.h:1965-1978`: bits **0-6** stock, **7-11** are the weapon-command field
(`GetWeaponCommandMask`, a 5-bit enum — *not* spare bits), **12** `COOPWALK`, **13** `COOPADS`
(its own comment calls it *"the last free one"*), **14-15** `ANY`/`MOUSE`.

**Use a `+`/`-` console command instead — no protocol change.** Key-down builds `+cmd <key> <time>`
(`cl_keys.cpp:1266`), key-up `-cmd` (`:1078`). Register **both** forms in `G_ConsoleCmds`
(`gamecmds.cpp:120`) — plain function pointer, trailing key/time args ignored, no Event format string —
**and both in cgame's `commands[]`**, forwarding via `cgi.SendClientCommand("+yourcmd")`. Record only
key state in the handler; do the work in a per-frame tick, or a tap released before your state machine
is ready is swallowed.

⚠️ **BOTH REGISTRATIONS, or it is HOST-ONLY** (bug-2460). Unmatched `+`/`-` do **not** forward:
`CL_ForwardCommandToServer` (`cl_main.cpp:1056`) drops `-` silently, answers `+` with "Unknown command".
`Cmd_ExecuteString` (`qcommon/cmd.c:1002`) tries client cmds → cvars → **cgame** → **`SV_GameCommand`,
only if `com_sv_running`** → forward. So the host works via the local-server shortcut and every joiner
does nothing — which is also why it survives playtesting by whoever hosts. `G_ProcessClientCommand`
matches by literal name, so the `+`/`-` survives the relay. Worked example: `+coopnade` in
`cg_consolecmds.c`.

Wire-state neighbours (weapon-command enum, `surfaces[]` bit 6): `archive/traps-pruned-2026-10-05.md`.

---

<a name="t23"></a>
## T23 — Wired, plausible, and doing nothing

**Bugs:** 2099 (prone). Two causes, one feature, no error message from either; the first is the
missing-notetrack rule, now filed once under [TIKI/sound](#tiki).

**⭐ `last_ucmd` is not continuous** - one frame of `upmove 0` mid-hold (usercmd not yet refreshed) reset the hold timer and
read as "only works on certain terrain". Hold-to-do-X needs a 150 ms grace before treating a key as released.

**⭐ `startsolid` says where you ARE, not where you are GOING** (bug-2547): a prone box on a slope is already in solid,
so rejecting every `startsolid` candidate discarded all sixteen. Skip the trace while embedded; let the DESTINATION test carry
the safety, capped in distance.

**Shape:** five unrelated causes all read "prone is broken"; none was found by reasoning about code - probe each symptom.

<a name="t24"></a>
## T24 - A text fix applied per call site never holds: route the channel, then check the sink

**Bugs:** 3426, 3520, 3542, 3952, 4007. Four rounds converted `iprint`/`iprintlnbold` SITES to `feed.scr`; every later
print was born on the old top-left box again. **Route at the channel:** cgame `CG_CoopFeedRouteUntagged`
takes every untagged coop `print`/`hudprint` ("fail" lines, Hardcore, `coop_feed 0`, a hidden HUD stay old-box). **The sink lost text too**: check truncation, replacement, read time. Subtitles are drawn by the exe
(`cl_uiview3d.cpp`, `subtitle0-3`): cgame cannot move them, so the feed stands above them.
