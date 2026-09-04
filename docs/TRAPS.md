# TRAPS — every way this project has broken itself more than once

**The highest-value file in the doc set.** Each entry is a failure family that recurred. Read the
**Tell** first — that is what you will observe. Status legend in
[SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md#status-vocabulary).

> Pruned 2026-08-20 and 2026-09-02; every rule, bug id and `file:line` anchor kept. War-story
> detail: [`archive/traps-pruned-2026-08-20.md`](archive/traps-pruned-2026-08-20.md).

## ClientThink runs once per USERCMD, not once per server frame

Anything integrating `level.frametime` inside ClientThink advances once per COMMAND, so its rate scales
with client framerate - com_maxfps 180 against sv_fps 40 is ~4.5x, and it differs between players on one
server. This bit four systems in a single session (recoil recovery, crouch-to-prone dwell, stress and
brace envelopes) and two silently changed a balance number, since stress multiplies bullet spread.
**Use elapsed time:** keep `m_fCoop<X>Last`, take `dt = level.time - last`, clamp it (0.1-0.25 s) so a
hitch cannot dump the whole envelope, and seed the member in the constructor - player memory is not zeroed.

## Per-weapon TIK data: read the copy the ENGINE resolves, under the name it actually ships as

Two independent ways a per-weapon table reads the wrong thing.

**Which COPY.** Pak priority is main < mainta < maintt < the mod's own pk3s - **the LAST copy wins**. An
extractor that sweeps in that order and keeps the FIRST match ships Spearhead's values: a G43 authored at
1 degree of yaw got 16, and it reached the player's real aim on every shot. Resolve last-wins, and include
the mod's own `models/weapons`, which beat every pak. **Also strip trailing `//` before tokenizing a TIK
line** - at least one weapon carries an ACTIVE viewkick line with a commented-out alternative appended on
the SAME line, and a naive tokenizer reads straight through into the comment.

**Which NAME.** See [`item_name` suffixes](#itemname) - the same variant-naming trap, both halves.

## Quick index

**Every `##` heading is an entry — grep them for the full set.** Below is only what a grep cannot
give you.

**Open now:** [T11](#t11) trusting the record over the code · [T14](#t14) verification that lied.
**Recurring:** [T1](#t1) parse killers · [T3](#t3) silent veto · [T4](#t4) capacity families ·
[T6](#t6) what loads != what you shipped · [T10](#t10) deploy gaps · [T12](#t12) same-named trees.
**Legacy numbers:** **T13** = [cross-cutting](#cross-cutting) Q5, **T15** =
`reference/harness_and_reproduction.md`, **T18** = `archive/traps-t16-failsafe-recursion.md`.
---

<a name="t1"></a>
## T1 — Morpheus parse killers: one bad token silently kills the WHOLE `.scr`

**Recurred under 17 bug ids:** 089, 298, 331, 348, 402, 533, 739/750, 910, 962, 1067, 1069, 1105,
1205, 1283, 1285, 1751, 1908.

**Tell:** a feature silently does nothing, with **no error at the failure site**; every `::` call into
the file logs `Script was not properly loaded`. A whole subsystem dying at once (bug-533 took helmet +
sandbag + medkit + emotes) means the shared bus file. The compiler is all-or-nothing: one syntax error
kills the entire file and the map runs with no script - raw team menu, unstartable.

> **An assignment with no value is a parse killer and the error points at the WRONG line** (bug-1908):
> `level.coop_loRosterTab[69] = ` with nothing after it makes the parser take the *next* statement as the
> value and die on **that** statement's `=`. A bare trailing `=` is legal continuation that retail
> `global/MountGunOrPlantCharge.scr` relies on - fatal only when the next code line is itself an
> assignment. `docs/tools/check_empty_rhs.py` runs every build. It came from a **generator** rendering an
> empty column: validate a generator's inputs.
>
> **All three scanners pass a file that cannot compile** - they check brace depth, line shape and string
> termination, not *expression* syntax; `println "a" + x + "b"` without parens kills the file and scans
> clean (bug-1751). **Not verified until a server has loaded the map and the log shows no `parse error`.**

**Run all three — they catch disjoint classes:**

| tool | catches | blind to |
|---|---|---|
| `docs/tools/depthscan2.py` | brace/label depth (never negative; 0 at each column-0 label) | everything below |
| `docs/tools/linecheck.py` | a line **starting** with a binary operator | everything below |
| odd-quote scan (comment- and string-aware, per line) | unterminated / multi-line string literals | the rest of T1 |

The log names only the **first** offending line - bug-1283 had two multi-line strings in one file and
fixing the reported one would have left it equally dead. **Fix the class, not the line.**

**The 11 confirmed triggers are tabulated in
[`archive/traps-t1-triggers.md`](archive/traps-t1-triggers.md)** - read it before writing `.scr`. The four
that recur most: **command syntax on an `EV_GETTER`** (must use property syntax); **a parenthesised
negative `(-1)` or a bare negative in a COMMAND ARG slot** (compute to a local - but negative *vector
components* are fine); **an unquoted `+`/`-` directive argument** such as `surface X -nodraw` (valid TIKI,
fatal in script, and braces still balance so the depth scan misses it); and **a real newline inside a
string literal**, usually from a generator.

**NOT a parse killer:** `spawn <class>` **with** inline keyvalues is fine (192 working occurrences incl.
`main.scr`). `KNOWN_WORKING_STATE.md` still forbids it and is wrong - see [90-folklore.md](90-folklore.md).

1. **`developer 1` is mandatory** - compile errors are developer-gated at `fgame/scriptthread.cpp:2858`,
   `:2869`, `:2883`; without it the failure is *completely* silent.
2. **Raw brace counts are an invalid check** - two opposite errors cancel on a broken file (bug-239), and
   comment/string braces miscount. Use a **running-depth scan**: never negative, 0 at every column-0
   label (internal `goto` labels may sit at depth 1).
3. Scanners live in `docs/tools/` (`depthscan2.py`, `linecheck.py`, `quotecheck.py`, `scrlint.py`).
   Verify any claimed script command against engine source **before** it lands.


---

<a name="t2"></a>

**A trailing comment swallows the closing brace** (4 occurrences, C++ too). `if (!p) { p = ...; }`
plus `// note` puts the brace INSIDE the comment; the compiler blames the NEXT function, often
hundreds of lines down. `depthscan2.py` finds it - the culprit is the first line where depth climbs
and stays, never the reported line.

## T2 — Generators corrupt the files they write

**Bugs:** 259, 331, 480, 962, 1247, 1363, 1600, `bug-ps-home-var`.

**Tell:** the output looks right in a diff and is silently rejected downstream; TIKI in particular
**drops bad aliases without a word.** Every instance is a TOOL writing project data, not a human:

| What happened | Bug |
|---|---|
| Bytes read out of a `.pk3` (already CRLF) written back through Python **text** mode → `\r\r\n` on 434 lines. TIKI silently dropped **every** alias in `anims_shared.txt`, killing the salute emote. | 259 |
| A bash-heredoc Python generator collapsed the two-char `\n` escape into literal newlines in 4 string literals → T1 parse kill. | 331, 962 |
| A shader generator's brace matcher mishandled mixed CRLF/LF plus `//`-commented braces, emitting blocks missing closing braces (45 open / 43 close) → white-square HUD icons. | 480 |
| A **texture upscaler** tiled (3x3 -> resize -> crop centre) then ran UnsharpMask on the CROPPED result; a convolution clamps at the border, so it invented edge pixels and reintroduced the exact seam tiling existed to prevent (14x worse on `ocean1b`), and Lanczos lobes separately overshot a capped alpha (189 -> 255). Fix: sharpen **inside** the tiled space, clamp each channel back to the source range. | 1247 |
| A PowerShell harness assigned `$home`, a **built-in automatic variable**; the assignment silently no-op'd and logs landed in the user profile. | ps-home-var |
| `sed -i` on a **CRLF** `.scr` stripped every CR while correctly deleting its 16 target lines, turning a 16-line edit into a 331-line whole-file rewrite. The check that cleared it, `grep -c $'\r'`, reports **0 on a CRLF file** under Git Bash - a broken detector handing back a false all-clear. | 2081 |

- **Binary mode on BOTH sides, repo files included.** `open(p, encoding=...)` translates newlines on
  *read*, so a CRLF file arrives as LF and `\r\n` patterns match nothing; `newline=""` on write then
  flips the **whole file** to LF. Both fail silently - `str.replace` returns unchanged rather than
  raising. Use `rb`/`wb`; the tree is **not uniform** (`challenges.scr` CRLF, `lobbyui.scr` LF-only,
  `docs/TRAPS.md` LF - bug-1600 was this file flipped by a prune script). Detect per file and **assert
  the match count before every replace**; that assert caught bug-1363.
  Not Python-only: **`sed -i` and any shell in-place rewriter flip the whole file the same way** (bug-2081).
  Detect endings by counting `b'\r\n'` against bare `b'\n'` on the RAW BYTES - `grep -c $'\r'`
  answers 0 on a CRLF file and will clear a broken edit. Then confirm the diff is the SHAPE you
  intended (`cmp`, `git diff --numstat`): a whole-file diff on a 16-line edit is the tell.
  With `core.autocrlf=true`, `git checkout --` re-stamps CRLF onto a file whose blob is LF, so
  a 'clean' status does **not** mean the bytes on disk are the ones you started with.
- **Never** emit script files through a bash heredoc.
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

**⭐ A guard written for one question is wrong for the neighbouring one** (bug-1687).
**Re-read what a predicate was written to decide before reusing it; when the answers differ, SPLIT
rather than widen.** `coop_isProtectedActor` ("leave this actor alone?") reused for "who would
notice a corpse?" vetoed the entire m2l2a cast.

**⭐ Gating one entry point is not gating the feature** (bugs 1685, 1860). **Grep every writer of the
shared state before calling a gate complete** - papers had three writers, two guards; our own `docgen
check` had the same shape and could never pass.

**⭐ The same shape at the FIX end: a repair applied to one member of a set nobody enumerated.**
**Name the set a fix belongs to and check every member.** Three flavours, one sweep
(bugs 2171/2172/2175, 2026-08-30): a **pair** (one half of a client/server pair
flipped on), a **list** (three of nine stomping cfg lines commented out), a **direction** (a guard
added to one side of a two-way HUD conflict). Tell for the pair: **a cvar seeded in no cfg has no
default but the one in code, so two `Cvar_Get` calls with different defaults ARE the bug.**

**⭐ Our own guard disabled the retail mechanism**, twice in one day (bugs 1671, 1669). **Ask what the
vanilla mechanism already is before adding a guard**, and when a user says "this is how vanilla handles
it", read the ENTITY, not the scripts around it - m2l2a's `$naxos` carries `spawnflags 128`
(`TRIGGER_DAMAGE`), so *shooting it* is how retail completes that objective.

**⭐ A guard can key on data that does not exist yet when it runs.** **Print the keys a heuristic depends
on and confirm they are populated at that instant** - the scene-actor exemption tested `alarmthread != NIL`
23 s before anything assigns one, matching NOTHING while passing its own acceptance check vacuously.
Instrument first, repair second.

**The `waittill`-already-fired shape recurs on every remaining map.** `invalid waittill spawn for
'Level'` reads like a warning but means "this script ran at the wrong time": a failed `waittill` does not
abort and does not wait, and the damage surfaces as NULL-listener errors elsewhere. Fix with
`replace.scr::waitTillSpawn` / `::waitTillPrespawn`. **Do NOT bulk-replace** - 191 bare `level waittill`
sites ship and most are legitimately reached first, so **the runtime log is the oracle**: fix only sites
that actually throw, per map, as each is played ([T14](#t14)).

**A second shape: the write executes and is then overwritten.** Proving execution is necessary but not
sufficient - **grep every writer of a shared per-frame field and establish who runs last**, preferring
the LAST write site in a render/view path. Head tracking shipped INERT this way (bug-2101):
`PmoveAdjustAngleSettings` (`bg_pmove.cpp:1622`) rewrites all four bone controllers from `EndFrame`,
after `ClientThink` set them - **the cure is a different call site, not a different value.** The
dangerous variant lands somewhere real instead (bug-1238 moved the 3P pivot).

**The UI corollary - never trade a working widget for an unverified one; ADD ALONGSIDE IT.** A `.urc`
cannot be run or diffed from here, so the only oracle is the user's screenshot (bug-1546). And when you
fix a silent-discard branch, **add the warning even though you also raised the limit** -
`sv_snapshot.c:549-553` does.

**Four more rules + their instances: [`archive/traps-t3-instances.md`](archive/traps-t3-instances.md)**
- headless boots always pass; a flag with no getter cannot be debugged.

---

<a name="t4"></a>

**`int / int` IS C INTEGER DIVISION AND SILENTLY ZEROES WHOLE FEATURES** (bugs 2424/2425, four sites
in one day). `scriptvariable.cpp:1671-1679` divides two ints as ints, so **`38 / 100` is `0`** and a
percentage written that way disables what it scales with no error and no log line. The Higgins sink
ran all four legs for weeks issuing `rotatexup 0 / movedown 0`, printing `roll=0/0/0/0` the whole
time. A 70-step `( k / steps )` ramp is 0 until the last step then 1 - a hard flip that reads as "the
effect doesn't work". `wait ( 34 / 24 )` waits **1**, so `coop_cvarFade`'s 34-second fade has always
taken 24, on every map - hidden because `(vhi-vlo)/steps` was correct (floats), so only the CLOCK was
wrong and everything was uniformly fast. **Write `* 0.01`, or `* 1.0` before dividing** (`* 0.01`
survives a tunable later becoming a float). Auditing rule: a ratio is safe only if you can NAME the
float operand - `vector_length` results and accumulated fractions are; counts never are.

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
  count (bug-935); `MAX_SKELMORPH 12800` silently out-of-bounds (bug-1214). Three payouts for the
  invisible-actor symptom alone (bug-932 gl1, `renderergl2/tr_local.h:2339` gl2, bug-1135
  `R_AllocModel`).
- **Map the whole producer→consumer chain in one pass** (bug-1186's `MAX_SNAPSHOT_ENTITIES`).
- **A capacity never reset is a per-SESSION budget, and it kills an INNOCENT map** (bug-1803).
  `MAX_SKELETOR_CHANNELS` fills two process-global statics zeroed only at construction; after ~28 maps
  e2l2 merely held the 2,560th channel - blameless, fine from a fresh boot. **Ask of every limit: what
  frees an entry?** If nothing does, size it against everything the game can load (a measured 4,589
  whole-game proves 2,560 had to fall over). Resetting is NOT safe - `skelChannelList_c` stores *global*
  indices in every cached model.
- **A protocol raise ships four binaries** - see [ENGINE.md](ENGINE.md#protocol-coupling).
- **One capacity grows while nobody touches the code: `MAX_CVARS`** (bug-1582). *Archived* content
  consumes it - `omconfig.cfg` hit **3019** cvars (Service Record ~1500, armory locks ~500), crossing
  4096 a month after bug-598 doubled it. Doubling is headroom, not a cure; now 8192 + 80% warning.

- **⭐ Two constants that agree by COINCIDENCE are a bomb with no label** (bugs 2291-2293, 2315; three
  crashes and one blind revert). `TIKI_MAX_ENTITIES` was a hardcoded 2048 that merely *happened* to
  equal `MAX_GENTITIES`; `TIKI_End()` indexed `skel_entity_cache[i*2+j]` without the writer's
  `% TIKI_MAX_ENTITIES` wrap - in bounds by luck, zero margin - so 12 bits `delete`d 4096 garbage
  pointers and the blame landed on a blameless `GENTITYNUM_BITS` raise. **Grep a capacity's VALUE, not
  just its name; ask whether two limits are derived or merely equal today; an `==` against a capacity is
  always a bug.** **KNOWING THIS DOES NOT PREVENT IT:** I wrote this entry, then next day raised the
  sound channels 32→96 and shipped a launch crash - seven loops bounded `loop_sounds[64]` by
  `CHANNELS_3D+CHANNELS_2D` (bug-2315). **Write the build break in the same commit as the raise.** And
  **`ENTITYNUM_*` are PROTOCOL indices** (`MAX_GENTITIES-2`): size anything indexed by one off
  `MAX_GENTITIES`, never off `maxentities`, which is all `g_entities` was malloc'd at (bug-2291).
  **Diagnose this class from the FAULT ADDRESS, never by inspection** - two rounds of reading the diff
  produced two real-but-wrong fixes at ~an hour each; WER's fault RVA + the linker `.map` named it in a
  minute. Recipe in the `crash_dump_analysis` memory.

**Read `openmohaa-hzm/code/qcommon/q_shared.h:1690-1755` before touching any capacity constant.** The `MAX_SOUNDS` comment there is canonical - four binding constraints in the order they bite, each tagged with the bug that found it (including two failed attempts), backed by a compile-time `#error`. **Turn every capacity rule into a build break** - `MAX_SOUNDS` has that `#error` and never regressed; `TIKI_MAX_ENTITIES` had none and silently rotted out of sync (bug-2292).

---

<a name="t5"></a>
## T5 — `$player` is an array; NIL ≠ NULL; storms are sequential

**Bugs:** 1049, 1051, 1052, 1054, 1065, 1104, 1624, 1632, 1665; the 4-player sweep.
**Tell:** thousands of identical `Script Error` lines. **Solo boots cannot reproduce any of it.**

1. **`Cannot cast array to listener`** - vanilla SP treats `$player` as one entity, but with **2+
   connected players it is a 1-indexed ARRAY**, so `$player.origin`, `turnto $player`, `isAlive $player`
   all throw. Repair idiom: an **inline `$player[i]` scan** with a per-element NULL guard, or
   `$player[1]` with a NULL host guard. ⚠️ This line used to recommend
   `exec coop_mod/replace.scr::player_closestTo self` - do **not** reach for that first (bug-1665).
2. **`Cannot cast none to <type>`** - a `level.*` timing global the vanilla SP init would have set is
   never set in coop (`level.thundertime` / `windtime` / `shuttertime` / `rainvolume`);
   `weather.scr:378` alone threw **8,662 times**. Fix: NIL-guards restoring vanilla defaults.
3. **Stale pointers that PASS a NULL guard** - bug-1054's `coop_trackTankTarget` had no `else` branch, so
   a freed player ref lingered and evaded `== NULL`.

**⚠️ Guard with BOTH.** `NIL != NULL` and coop hits both; bug-1065 hardened `xp_award` with
`== NULL || == NIL` because `level.coop_smoke_player` is only ever assigned, never initialised. The open
bug-1220 (12× "applied to NULL listener" on e2l2) is this exact cure.

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

**Still open:** `global/vehicle_warning.scr` (4,270 casts, second-worst source) was **never extracted**;
plus a second vehicle-crew spawn path on t2l2/t3l2 that the `truck_load` guard does not cover.

---

<a name="t6"></a>
## T6 — What you shipped is not what loads

**Bugs:** 157, 247, 499/525/530/921/922 (a 5-round saga), 1129, 1190, 1216, 1610, 1633.
**Tell:** an asset edit has no visible effect, or a "black" surface appears, or a texture you never touched
changes.

| Load-order rule | Consequence |
|---|---|
| `.dds` beats `.jpg`/`.tga` | `R_LoadImage` rewrites the extension to `.dds` and tries `LoadDDS` **first** whenever texture compression is on, so a same-basename stock `.dds` beats your HD `.jpg` - this made 881 upscales dead. Disabling `r_ext_compressed_textures` is **not** a fix (~1400 stock-`.dds`-only textures would vanish); ship DXT `.dds` overrides with a full mip chain. |
| The engine tries `.jpg` **before** `.tga` | Menu art in particular |
| Shader **NAME** overrides lose the reverse-concat race | Whole-**FILE** overrides win: the filesystem dedupes by filename and the coop pak mounts last (bug-921 used bug-525's whole-file pattern on `scripts/equipment.shader`) |
| `zzzzzzzz_*` sorts after `zzzzzz_*` | bug-1190 |
| `.tik` surface directives must match the `.skd`'s real surface names | else `TIKI_InitTiki` drops them (bug-1216) |
| **A junction hides the loose half from your tools** | `G:\mohaa-gl2\{main,mainta,maintt}` are NTFS **junctions** into the GOG install. Git-Bash `find` does not follow them (needs `-L`) and a pak-only scan misses loose files entirely, so **both** scans that produced the retracted bug-2336 claim - "the install is missing most of its speech, tell the user to reinstall" - still produce it today. Python `os.walk` follows them. Any "is this asset present?" check must cover paks **and** the walked junction, or it will libel the user's install (bug-2386). |
| Loose files beat paks **both ways** | bug-2020: 7,755 loose dev-only files under `G:\mohaa-gl2\main\sound\` made 1,623 alias refs (chatter restoration included) work in dev, silent for everyone else. **Audit assets against the SHIPPED set (retail paks + mod source tree), never the dev install** - loose files mask this class. |
| Homepath `maintt/` beats basepath; loose files beat paks | **bug-1633:** stale cfgs in the live profile's `maintt/` shadowed every deployed change; `build.ps1` now deploys cfgs to all three targets. Also watch for 0-byte decoys (bug-595). |

**⭐ THE FINAL ANSWER when a name is contested** (bug-922, closing the 5-round black-pouch saga): **stop
fighting for the name.** Mint a NEW shader name existing only in the coop pak, pointing at a PRIVATE
texture path also only in the coop pak, and retarget the `.tik` surface. **Tell:** a "black" surface
showing per-face **shading** means a lit default shader is drawing it and your def never reached it.

**⭐ A playtest log only testifies about the build it loaded** (bug-1610). `coop_enigma.shader` existed
yet the log said `Couldn't find image file for shader enigma`: the client loaded 23:34 and quit 23:37:11,
the file was packed at **23:38:06**. **Compare the pk3 entry's timestamp
(`zipfile.getinfo(name).date_time`) against the `InitGame` line**, and verify fixes by reading them back
out of the deployed pk3.

**⭐ Imported third-party skin packs are this trap with the blast radius reversed.** A 2002-era skin pk3
routinely *redefines* stock shader names instead of minting its own, and the coop pak mounts last, so the
import silently repaints every other model (one redefined all 15 `viewsleeves*` shaders for one pilot
skin; another broke the holster on *every* skin; 39-pack sweep: `docs/proposals/skin_batch.md`). **Diff
an external pack's shader block names against `scripts/*.shader` and the retail paks, and its
`models/player/*.tik` basenames against the stock tiks** - a matching tik basename *replaces* the stock
model. `map foo.tga` resolves extension-agnostically, so a shader naming `.tga` beside a shipped `.jpg`
is **not** missing.

**Related generated-asset hazard:** ESRGAN upscales have shipped hallucinated worm noise (bug-1129), a
GPU-corrupted all-black `netgame_a/b` that blanked the server browser (bug-247), and 29 overridden
**vanilla** menu textures (bug-157). **Brightness-check output before commit**; ESRGAN is for photos and
text, and corrupts 1-2px chrome.

---

<a name="t7"></a>
## T7 — Cvar registration, flags, and exec order

**⭐ BINDS CANNOT LIVE IN `coop_defaults.cfg`.** Verified order in `qcommon/common.c`:
`coop_defaults.cfg` (:1841) -> `configs/<config>` (:1847) -> `autoexec.cfg` (:1862). Before-the-config
is exactly right for `seta` CVARS - that is why the file exists - but **`configs/omconfig.cfg` opens
with `unbindall`**, so any bind seeded there is created and then destroyed every launch (bug-2093: the
quick-grenade key looked completely dead while its engine code was fine and had never run). All 40 of
the project's binds are in `autoexec.cfg` for this reason.
The cost is real and unavoidable: autoexec re-forces the bind each launch, so a rebind is lost next
start. **Feature dead + code obviously correct = check the bind actually exists before debugging it.**

**Bugs:** 258, 682, 710, 918, 1125, 1148, 1152, 1427, 1492, 1669.

**An archived cvar is a latch - including one you add for debugging** (bug-1427, twice). A
`seta`-archived switch rides `omconfig.cfg` forever and re-fires on every later load (`coop_buildmap`
broke e3l4 twice in one evening); editing omconfig.cfg externally loses the race, as the engine rewrites
it from memory at shutdown. The repeat came from the other side: `CVAR_ARCHIVE` on `r_novis` for one
test wrote `seta r_novis "1"` into the user's config and cost a `0xC00000FF` startup crash. **Consume
mode-flipping cvars one-shot at map init** (copy to a level var, `setcvar` back to 0, never a live
`getcvar`), and never give a diagnostic `CVAR_ARCHIVE`.

**⭐ Script `getcvar` CREATES the cvar EMPTY, permanently defeating the engine's own default**
(bug-1669). `ScriptThread::Getcvar` is `gi.Cvar_Get(name, "", 0)` (`fgame/scriptthread.cpp:2628`), so
the first *script* read of an unregistered cvar creates it with `""`; the engine's later
`Cvar_Get(name, "1", CVAR_ARCHIVE)` finds it existing, updates only the reset string, and **keeps the
empty value** - `->integer` is 0 forever. That is how limping was dead: `coop_limpWarn` is threaded at
player setup (`player.scr:224`) and getcvar'd `coop_limp` before `Player::TickLimp` registered it -
**the warning system silently switched off the feature it exists to warn about** - and it had also
killed `coop_tinnitusBlast` and `coop_goreDripCorpseTime`. One trap, three dead features.

- **Detect:** rcon the cvar — `is:"" default:"1"` means it fired; a genuinely unknown cvar prints
  **nothing**, and that control query is what proved it rather than inferred it.
- **Fix:** pre-register engine-owned `coop_*` cvars in `G_InitGame` (`fgame/g_main.cpp`), which runs
  before any script. **Any new engine `coop_*` cvar that script also reads must go in that block.**
- **Find the collision set:** intersect engine `Cvar_Get("coop_*", <non-empty default>)` against every
  `getcvar("coop_*")` in the scripts. It was six; four were genuinely broken.

*(summary table moved to [`archive/traps-t7-cvar-table.md`](archive/traps-t7-cvar-table.md) - the rules it tabulates are the prose above and below.)*

**⚠️ A workaround written into the SAVED config outlives the bug it worked around and beats
`coop_defaults.cfg` forever** - `seta` in a saved config is a fossil, not a decision, so **record a
cvar mitigation with its bug id and clear it when that bug closes** (bug-1990). LIVE case:
`r_ext_multisample 0` mitigates a gl2 foliage-cutout artifact still open as bug-1298, so the archived
`0` stays until it closes. [T11](#t11) biting inside T7.

**⚠️ gl2 is the renderer we ship and test on** - confirm from the qconsole banner, never a doc;
this section once claimed gl2 was abandoned and produced a wrong fix (2026-08-21). Two corollaries:
**any cvar comment naming a renderer is suspect until re-read against that renderer's `tr_init.c`**
- `r_mapOverBrightBits` defaults 1 in gl1 and **2** in gl2 (`renderergl2/tr_init.c:1886`), so a
comment calling 1 "the engine default" silently halved lightmap overbright on every world surface;
and **grep the OTHER renderer for a token before trusting the feature works** - what gl1 implements
can be a `// FIXME: unimplemented` stub in gl2 (`nofog`, bug-2186), so a bug appearing just after a
renderer feature ships reads as a gap that feature exposed.

**The structural fix is half-built:** `coop_defaults.cfg` execs **BEFORE** the saved config, so its values
are true defaults a menu change overrides and persists. Migration out of `autoexec.cfg` is incomplete, and
any menu-wired cvar still `seta`'d there **cannot** persist; the two files are disjoint, so they never
fight. Counts live in `docs/generated/CVARS_COOP.md` - never hand-copied here. **A cvar seeded nowhere**
(no engine `Cvar_Get`, no cfg line) makes `getcvar` return `""` on a clean profile and a script fallback
branch silently decides behaviour, so **calling such a cvar "default N" describes a branch, not a
default.****

**Archived client state keyed by POSITION rots on every catalogue change** (bug-1926, full entry in
`archive/traps-pruned-2026-08-20.md`): **persist IDs, never positions**; stamp any positional cache with
a crc of the id list and wipe on mismatch; a generated lookup map is `set`, not `seta`.

---

<a name="t8"></a>
## T8 - server->client stufftext is a lossy, filtered channel

Six ways a server->client message is silently destroyed, and one on the receiving end. In short:
an embedded quote truncates the wire argument, so send values UNQUOTED and one statement per
stufftext; `cg_servercmds_filter.cpp` silently drops server-stuffed `exec`, `vstr` and unlisted
`set`, which has presented as three unrelated bugs and as "one mode of a multi-mode feature works,
the rest collapse together"; `Cvar_Set_f` re-joins tokenised args so runs of whitespace normalise
to one space; client `exec`/`vstr` INSERT at the buffer front while server stufftext APPENDS, so
the last textual line of a client chain wins and a server echo arrives a round trip later; and the
name bus dispatches ONE token per ~0.75s batch in BUS INDEX order, destroying every other stacked
token. On the receiving end, a `.urc` widget below its menu's declared canvas height draws nothing
at all, with no error. Remote clients need the updated `cgame.dll` for any of it.
Worked cases and the exact call sites in
**[`archive/traps-t8-stufftext.md`](archive/traps-t8-stufftext.md)**. Bugs 595, 597, 736, 758, 772,
773, 1364, 1365, 1991.

## T9 - Same-frame spawn / model / solid race

**Fixed; pattern known.** Full write-up in
[archive/traps-t9-spawn-race.md](archive/traps-t9-spawn-race.md). Short form: a `spawn`, its `model`
and `solid` cannot all land in one frame — step them.

---

<a name="t10"></a>
## T10 — Deploy gaps: the source is not what is running

**Bugs:** 089 (the mirror case), 930, 1172, 1219.

**Tell:** a fix that is definitely in the source has no effect in play, or a log line reports a limit
lower than the header says. Both directions happen: edited but never built/deployed (bug-089); and built
and deployed when it shouldn't have been (bug-1172 - `build.ps1` runs during a gl2 sandbox session
pushed sandbox-only `MAX_SOUNDS 2000` / `MAX_ENTITIES 4095` / `MAX_TIKI_ALIASES 8192` binaries into the
user's **real install**).

**The deploy set is complete now - verify it anyway.** This paragraph used to say `build.ps1` skipped
`openmohaa.exe`, `game.dll` and `renderer_opengl2.dll`. It ships **all six** (both renderers and
`omohaaded.exe` included, `build.ps1:200-215`) since bug-1796/bug-1634 - T11 biting inside T10, and the
record was wrong for a month. While gl2 *was* missing, every renderer-side fix silently failed to reach
the running game. **A "verified" claim must name which binaries were deployed and when, and prove it by
hashing the deployed file against the build output** - a timestamp check misreads 12-hour times and will
tell you a good deploy failed. `build.ps1` refuses to deploy while the game is running, so if you edited
and did not deploy, everything the user tests is the PREVIOUS build and every conclusion is void.
**Some changes must ship as a PAIR or they are worse than not shipping:** `bg_pmove.cpp` compiles into
`game.dll` *and* `cgame.dll`, so a movement change in it desyncs client prediction from server truth if
either ships alone (bug-2149); a protocol-constant change ships exe + cgame + game together.

---

<a name="t11"></a>
## T11 — Trusting the record over the code  ⚠️ STRUCTURAL

**Agreement between reviewers is NOT corroboration when they share an upstream source** (bug-1290). A multi-agent audit called "the injury vignette is permanently maxed after any DBNO revive" a live bug and two independent critique lenses confirmed it - all three had inherited one unchecked premise (that `healthonly 9999` puts 9999 into health; it clamps to `max_health`), so the "fix" would have hidden genuine low health. **Verify a finding's load-bearing premise against the code yourself** - agents reading the same brief are one witness, not three.

**A later entry can silently reverse an earlier one, so read the ordered LIST, not one entry.**
`docs/generated/FIX_INDEX.md` (file -> ordered bug ids) is the fix; the story belongs in HISTORY. Nothing
in the schema flags a reversal, so **edit the original entry** when you supersede a finding - bug-1473/1474
were corrected in place on 2026-08-06 after being filed on the wrong files.

- **⭐ A plan's STATUS HEADER is a record too, and it rots hardest.**
  `_research/composure_and_ads_plan.md` led with "**PLAN ONLY — nothing built**" for four days
  after its Part A was built, committed (`9e71d739`) and shipped in v1.4.4. The correction existed —
  500 lines further down, in a revision section. On 2026-08-24 the stale header sent a session to
  re-fix a fixed defect from line numbers that had already moved. Same shape as the unmarked
  `_final.md` release notes (HISTORY 07-18). **When a plan ships, edit its header in the same
  commit**: a superseded diagnosis standing at the TOP of a file outranks a correction at the
  bottom, because the top is what gets read. Mark the superseded body too, not just the header.
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
tree. **Ship risk: CLOSED (re-verified 2026-08-17):** `build.ps1:32`'s
`$excludeTop = @("_notes", "_research")` is committed and the deployed
`zzzzzz_co-op_hzm_mod_code.pk3` has **zero** `_research`/`_notes` entries. **Still open:** the regression harness - the
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

**And one level down again: two ENGINE EVENTS sharing a script command name** (bug-2064, the most
expensive of the three). `notarget` is declared **twice** as `EV_NORMAL` - `Entity::NoTarget`
(SETS from its argument) and `Player::NoTargetCheat` (ignores the argument, **XORs** the flag) -
and `ScriptMaster` keeps one **name -> eventnum entry, last write wins** (`scriptmaster.cpp:616`)
over an unordered container. **Which handler a script command reaches is therefore a build
detail, not a decision.** For players the cheat won, turning every `player notarget 1` into a
flip; it read as *intermittent* across five sessions because the outcome was call **parity**.
**Grep the engine for a second `Event` with the same command string before trusting a script
command's signature**, and when there is one make BOTH handlers agree for BOTH call shapes
(argument = set, none = toggle) rather than betting on the lookup. Same tell as `.gun`
(bug-2046) and `enableEnemy` (bug-2034): *the command name is not the contract, the `Event`
declaration is.*

---

<a name="t14"></a>
## T14 — Your verification lied: audits that pass, harnesses that measure nothing

**Bugs:** 1026-1027, 1218-1220, 1473-1490, 1596-1598, 1812-1813, 2101-2102.

**PROBE DESIGN - three ways a probe lies.** *(1) Nested inside the condition it measures* - blind; put
it OUTSIDE the branch and print the deciding inputs (3 instances 2026-08-22; archive). *(2) Reading back
your own input* - `m_fCoopHeadYaw` tracked perfectly while the networked value was clobbered by a
subsystem the probe never read (bug-2102). **Probe the FINAL consumed value**; prefer a **sentinel the
other writer cannot produce** (head `11/22`): `0.00` on 328/328 samples, then `35.00` once fixed.
*(3) Never exercising the branch* - **force it**: `coop_boneDebug 2` runs the prone maths on a standing
player, separating "the maths is wrong" from "prone never engaged".
*(worked examples archived to `docs/archive/traps-t14-worked-examples.md`)*

**THE TOOL LIED, NOT THE CODE - four species, 2026-09-03, all returning plausible numbers.**
*(a)* **`grep` bails on a binary line**: one `qconsole.log` is a 13.9 MB single line with a NUL, so
plain grep prints `Binary file ... matches` and **nothing else** - two of eight runs vanished from a
census and a marker was declared "never fired". **Always `grep -a` on logs.** *(b)* **A shell-eaten
pattern matches everything**: `grep -c $'\r'` returned each file's TOTAL LINE COUNT, "proving" three
pure-LF files were CRLF - and a CRLF misread is how T2 corruption starts. **Count bytes, never grep,
for line endings.** *(c)* **A pass that cannot fail**: `node --check f | head -5 && echo OK` prints OK
unconditionally because `head` exits 0. **Gate on the tool's own exit code, never through a pipe.**
*(d)* **`check_map_compiles.py` is flaky against a LIVE dedicated server** - 3 errors once, 0 on four
re-runs, while the server's own log showed 0. Confirm no `omohaaded`/`openmohaa` is running first.
**And absence of a marker is not absence of behaviour**: `playsound` on an entity prints nothing, so
grepping for it measures the marker. Three Omaha systems were mis-diagnosed as dead this way. Every
new beat gets a `^~^~^` marker or a census reads it as missing.

## T16 — Waits that never complete: failsafe recursion, missing anims, unguarded `waittill`

**Bugs:** 1361 → 1366 (e3l4 supply/delivery), 1367, 1368, 1370, 1579, 1921, 1945; same shape as the AB41
and truck-unload failsafes. Worked example: **`docs/archive/traps-t16-failsafe-recursion.md`**.

**Tell:** the same user report twice with a failsafe log line in between; or an actor frozen mid-action —
standing upright while dead, unresponsive after a conversation, a sequence that just stops — no error.

**A recovery path must contain no wait that the failure mode can block.** The e3l4 failsafe bounded a
blocking wait at 45 s then "recovered" by calling a routine opening with `runto` + `waittill movedone` -
the actor's whole problem was having no nav path, so the soft-lock moved rather than closed. For actors:
no `runto`/`walkto`/`waittill turndone`/`waittill animdone`, no unbounded
`while (vector_length(...) > N)`. Seat or place them directly, taking the **tail** of the vanilla routine.
Grep the recovery path for `waittill` before shipping, and check the *next* stage for the same shape.

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

**A scripted conversation strands when a `waittill` outranges its guard** (bug-1579) - retail chatter
helpers assume the talkers are alive and idle, and coop breaks all three assumptions. (a) A `waittill`
**outside** the guard that started the anim/say waits forever, because no anim was issued: wait only on
an actor you actually animated, recorded in a local, and never re-test the condition. (b) `isalive` on a
NULL entity throws and the thrown statement is SKIPPED, so the guard vanishes and its body runs
unguarded - test `!= NULL` first and separately. (c) `thinkstate != "attack"` is not "idle": a CURIOUS /
GRENADE / PAIN actor overrides the scripted idle anim, so gate on `== idle` (`anim` runs at
`THINKLEVEL_IDLE` via `Actor::PlayAnimation` -> `SetThinkIdle(THINK_ANIM)`, `actor.cpp:10819`; there is
no `THINKSTATE_ANIM`). **Silence the LINE, never abort the THREAD** - the tail of these labels holds the
RELEASE (`runto`, `enable_ai`, `type_disguise`) that hands actors back to normal AI, and ending early
leaves them frozen, dying on their feet with no death animation. Safe exception: a dead-end label
nothing waits on (`M1L3c` radio room). Sites: **docs/OPEN.md**; helper `replace.scr::convOk`.

---

<a name="t17"></a>
## T17 — Script VALUE types: 'none', keyvalue strings, and who owns an event

One failure in variants: the value is not the type the reader assumes, the thread dies at that line, and
the caller still reports success. **Tell:** a feature that "does nothing" with no crash, plus a
`Script Error` naming a file and line you were not looking at.

- **Reading a level var CREATES it with type `none`** — `GetVariable` returns non-NULL for a var that
  exists but was never *assigned*, so a NULL guard passes and `intValue()` throws. **Always ASSIGN a
  level var before anything reads it.** (bug-1371)
- **Map entity keyvalues arrive as STRINGS** — `int()`-coerce once at the top, not per comparison.
  (bug-1352, bug-1372)
- **A command registered on `ScriptThread` is NOT a Player event** — `iprintlnbold`/`iprintln` are
  ScriptThread-only, so `<player> iprintlnbold "..."` silently fails; the Player form is
  `iprint <text> 1`.

  Worked examples and the failure histories for these three are in
  [`archive/traps-pruned-2026-08-20.md`](archive/traps-pruned-2026-08-20.md).

---

<a name="t19"></a>
## T19 — A radius is a SPHERE, and hand-rolled distance is not trustworthy

**Bugs:** 1689, 1690. **Tell:** a proximity prompt fires on the floor below or through a ceiling - "the
Naxos text appears when you are downstairs underneath the room", "you get caught on the 2nd floor for his
dead body on the first".

**`vector_length` is a 3D distance**, so every "within N units" test is a sphere - almost never what is
meant in a building. **"Near" is a HORIZONTAL question plus a same-storey question, tested as both**: 2D
distance plus a vertical band (96u; a MOHAA storey is ~128). Three sites in one feature had it.

**Flatten both points to z=0 inside a vector literal and use `vector_length`** (locals inside a literal
are fine - `props.scr:407`, `tracescan.scr:79`), **not hand-rolled pythagoras**: a
`sqrt( (dx*dx) + (dy*dy) )` here returned **265.965 for two points 2013u apart**, twice across two
builds, while `dz` by plain subtraction was exactly right. No mechanism is claimed - only that
`vector_length` was right on every sample and the hand-rolled form was not on at least one.
`aimaneuver.scr:129` uses the same inline form, never checked. **And a range must be the right SIZE for
its job:** that feature's warning was drawn off the *action* prompt's 112u bash range, so it appeared
only once the player was already on top of the officer.

---

<a name="t20"></a>
## T20 — One flag, two states; and one-way latches

Four shapes from the m6l1c stealth route (2026-08-11); in each the symptom pointed away from the cause.

- **A flag that answers two questions gets tested for the wrong one.** `is_disguised` is the engine's
  per-frame opinion (`player.cpp:5519-5545`: disguise + no alarm + nothing real in hand + nobody
  attacking with real threat); `has_disguise` is the mod's own grant. Testing the first where the second
  was meant read "someone is shooting at you" as "the grant failed" (bugs 1701, 1701b, 1703). Tell:
  **the player's viewmodel and HUD stutter** - AI churn alone does not stutter a client. **Count how
  many things can make a flag false before testing it, and bound every self-re-threading retry.**
- **A one-way primitive lives in more files than you grepped.** Bare `attackplayer` is
  `Actor::ForceAttackPlayer`, cleared **only in the Actor constructor** (`actor.cpp:3092`), and while
  set `EnemyIsDisguised()` is false unconditionally - one call blinds that actor for the map.
  `attackentity <ent>` is the reversible form; four sites took three sweeps (bugs 1700, 1704, 1708).
- **An absorbing state hides everything downstream.** `EnemyIsDisguised()` also returned false for any
  actor in `THINKSTATE_ATTACK` and it ratchets. Fixed by requiring real threat (bug-1707), the treatment
  `player.cpp:5541` already had. Blocked-aggro across one run: **1051 -> 0**.
- **A flag two systems both own is a race, and it comes back.** `coop_clickablePapersEnabled` (set by
  `enableClickablePapers`, cleared by `coop_bustArm`) re-armed mid-bash restarts the papers loop, which
  force-equips papers into the hand holding the drawn pistol and **the player cannot shoot**: bug-1709
  (0.5 s re-check), bug-1726 (stacked per-target loops), bug-1732 (dedupe insufficient - the guard
  `coop_activeWeapon == NULL` means both "hand empty" *and* "no raise finished"), bug-1735 and bug-1736
  (`coop_busted` overloaded once `bust.scr` set it earlier, then cleared only on the success path). **One writer per player; clear the
  flag and yield a frame before threading a loop that sets it; split the latch from the state and clear
  it on every exit. Moving a flag's assignment earlier rewrites every guard that reads it.**

---

<a name="cross-cutting"></a>
## Cross-cutting: the questions to ask before "it doesn't work"

1. **Did it compile?** ([T1](#t1) — `developer 1`, running-depth scan)
2. **Did it run?** ([T3](#t3) - prove execution before tuning; check the gate cvar is seeded). And when a
   constant becomes a cvar, **update every reader in the same pass**: `coop_aiBuffer` converted the
   unsponge detectors but not `actorPainHandler`, so the AI pain handler detached on every actor's first
   hit, silently (bug-1733) - and fixing it exposed a reader right only by accident (bug-1734).
3. **Is the binary I'm testing the one I built?** ([T10](#t10) — three binary states are live now)
4. **Am I reading the record or the code?** ([T11](#t11) — the code wins; read the record to the END)
5. **Am I guessing, or measuring?** (was T13) **BISECT FIRST - a cvar bisect beats any number of
   hypotheses** (bug-1298): turn things off one at a time until the symptom moves. Six deployed
   hypotheses on the gl2 "white distant objects" bug changed nothing; one bisect found it.
6. **Symptom or design?** A fix producing the MIRROR IMAGE of the bug means the design underneath is
   wrong. "Stuck prone" and "popped back to crouch" were one flaw from two sides (bug-2108): an escape
   valve added to work around a broken standup trace force-stood the player a second after they let go.
   **The user's phrasing often names the design** - "space or control should put me back into crouch"
   described the INPUT MODEL, and was read as a trace bug twice.

---

<a name="tiki"></a>
## TIKI and sound-alias traps

**`<actor> say <alias>` IS AN ANIMATION CALL, NOT A SOUND CALL** - it drives the mouth and can
block; a missing alias animates a silent mouth. **A bare animation alias DROPS THE NOTETRACKS that
do the work** (three occurrences). Both stories, with the five failed fixes that preceded the first,
are in `docs/reference/tiki_and_sound_aliases.md`.

**A sound alias's `maps` field is a LOAD FILTER.** `aliascache explode_tank ... maps "m2l2b "` means
the alias **does not exist** elsewhere, and `playsound` on it is silent with no error and no log line
(bug-2248). Grep for **name AND maps field** before using one; tokens match as PREFIXES, so `m3l1b`
does **not** cover `m3l1a` (bug-2394, metal footsteps). Same trap the other way round: on a `loaded`
(3D) alias `maxDist` is a hard START gate, not a rolloff - a 200/2000 alias never begins for a listener
outside it (the Omaha whistle needed re-aliasing at 600/9000, not just more volume). **`streamed`
aliases are the exception, and it matters:** `S_OPENAL_StartSound` diverts `SFX_FLAG_STREAMED` to the
2D path and returns *before* `PickChannel3D` (`snd_openal_new.cpp:1953`), so a streamed line has no
start gate and costs no 3D channel. Most scripted dialogue is `streamed` - so neither maxDist nor the
3D channel pool can ever explain a silent scripted line, and bug-2309's 32->96 3D raise could not have.

**...but sometimes it is CURATION and widening it IS the defect** (bug-2307, mine): clearing 179
`needs an alias` errors by making the AI callout pools trilogy-wide made the beach bark nonstop - the
engine fires those with no cooldown, so the map list *was* the rate limit. On the real outages
something **audibly broke**; here only the log was noisy. **A console error is not evidence of a
defect - silence can be authored.** (`always` gets the ALIAS, the maps field gets the **CACHE**,
`scriptmaster.cpp:499`; uncached plays *badly* - bug-2304.)

**An animation pack is gated by a PREFIX match on the MAP NAME.** `new_generic_human.tik` wraps packs
in `includes <tok...> { }` and `TIKI_ParseIncludes` (`tiki_parse.cpp:345`) makes a block live only if
one token is a **prefix of the live map name** - so `includes test utils traf holodeck coop` does NOT
match `m3l1a`, and crate_carry/welding/workers were unreachable on Omaha while three sessions faked
around them. Adding a pack costs one `$include` line in the right block.
**`docs/tools/check_map_anims.py` resolves that chain and fails the build** on any `anim`, `playsound`
or model path that does not resolve on the map; its docstring carries the three facts it encodes (SKC
loop flag at offset **8**, a looping alias never fires ANIMDONE so a following `waittill animdone`
parks forever, and sound aliases resolve as PREFIX GROUPS - `alias.c:545`). `check_say_aliases.py` does
the same for `say`/`sayd`, which that tool never covered.

**A TIKI's `init { server { ... } }` runs even when you `spawn script_model model "<path>"`.**
`models/fx/fx_tank_explosion.tik` carries `classname Explosion` / `radiusdamage 120` in its own init
block, so a purely cosmetic set piece killed the player beside it (bug-2244) while the script contained
no `radiusdamage` anywhere - an audit of the script therefore found nothing. **Read the TIKI, not just
the script**, and copy a retail effect under a `coop_` name minus those lines rather than editing the
original. Read the other way, the same fact decides how you spawn one: `init { client { } }` fires when
the entity first reaches a **snapshot**, after the server set the origin, so *spawn, then position* is
correct (`bh_water_hard`); a **server** block fires at spawn, so its origin must be inline or the effect
bursts at the world origin. The two read identically in a script.

**Dialogue prefixes name the speaker's SIDE: `dfr_` friendly, `den_` German** - mixed in one
per-mission folder, so filtering by mission alone gets both (36 of 64 Omaha "prior-mission" lines were
enemy). Filter on the prefix, not the path.

More in **`docs/reference/tiki_and_sound_aliases.md`** - read it before touching a `.tik` or adding an
alias; `audit_weapons.py` and `audit_shaders.py` make those traps testable.

---

<a name="script-error"></a>
## ⭐ A `Script Error` does NOT kill the thread — it SKIPS the statement (verified 2026-08-06)

**This corrects a premise that shaped many earlier diagnoses, including several in this file.**
`ScriptException::next_abort` defaults to **0** (`script/scriptexception.cpp:30`), and
`ScriptVM::HandleScriptException` (`script/scriptvm.cpp:1915-1933`) only rethrows `if (exc.bAbort)`;
otherwise it prints `^~^~^ Script Error : …` and **returns**. The `catch` sits *inside* the
per-instruction loop, so execution resumes at the **next instruction**. Only **two** sites in the whole
VM set `next_abort = -1`: stack overflow (`scriptvm.cpp:1038`) and **command overflow** (`:1867`) — the
latter is `ERR_DROP` and really does take the server down (t2l3, bug-1493).

**Read every error site as "this statement was skipped", not "everything below died."**
- **An `invalid waittill` means the script does NOT WAIT.** Everything below runs *immediately* -
  sequences fire before their preconditions, entities are touched before they spawn. That is why the
  `waitTillSpawn`/`waitTillPrespawn` shims still matter (bugs 1458-1469).
- A cast error inside a `while` body removes the *statement*, not the loop - exactly how t2l3 span 4,347
  times with no yield and killed the server.
- **Values parsed out of a `.dat` file are STRINGS** (bug-1352): the character-walking splitters (fogmode,
  blueprint, save files) return strings, so a later `if( x > 0 )` throws and *that assignment never
  happens* while the caller prints success. Coerce with `float()`/`int()` at load; the tell is "works when
  set live, never when loaded from its own save".
- **A probe that throws prints nothing** while filling the log with errors - silently useless on exactly
  the cases worth watching. Sanitise every field before concatenating: an unset var reads `none`, and
  `"str" + none` throws (bugs 1702, and the SPAWNDISG probe before it, the same day).

---

<a name="turrets"></a>
## Turrets and AI spread: three ways a weapon tune never reaches the gun

**Bugs:** 1920, 1940, 1946, 1950. **Rule: before tuning a value, prove the failing PATH reads it -
grep the consumer, not the setter.** Three instances; full write-up in
[`archive/traps-pruned-2026-08-20.md`](archive/traps-pruned-2026-08-20.md).

- **A MANNED turret never reads `bulletspread`** - `weapon.cpp`'s `FT_BULLET` sets `vSpread` only for
  `owner->client`, and the `(max+base)/2` fallback is for `owner == NULL` (unmanned guns, which do not
  fire). An actor-manned turret's ONLY dispersion is `m_vAIBulletSpread`, set solely by the
  `aibulletspread` event (retail SH/BT use 300-450; the handler ignores arg 2). Gunner `accuracy` does
  nothing - only `Actor::GunTarget` consults it. (bug-1940)
- **AI spread is an AVERAGE** - `Weapon::Fire` gives a non-client owner
  `(bulletspreadmax + bulletspread) / 2`, so `bulletspread 120 120` averages with 0 to an effective
  60 and the tune feels dead. **Set all four args: `bulletspread B B M M`.** Player fire uses a
  base/max lerp and is unaffected. (bug-1920)
- **`TurretGun` fixes NEVER reach `VehicleTurretGun`** - it overrides `Think()`,
  `UpdateFireControl()` and `GetMuzzlePosition()`, so halftrack / tank hull MG / jeep guns silently
  skip every TurretGun-path tune: MG heat never cycled (bug-1946), and AI road gunners kept full
  damage and accuracy because the coop trio (damage scale, spread bonus, wandering aim error) was
  TurretGun-only (bug-1950). **Any turret-behavior change ships BOTH class paths.** The trio is
  `extern`'d in `weapturret.h`.

---

<a name="itemname"></a>
## Weapon variant suffixes - every consumer must strip them (two conventions, do not mix)

A variant exists twice under two different spellings, and an exact-name key misses almost the whole set
in both. **TIK FILENAME `<base>_<finish>`** (`G43_dhg43fleck`): 481 weapon TIKs ship and only ~41 are
base guns, so an exact key covers ~8% - dead on 428 while working on the handful you test with. **Try
the full name, then drop trailing `_segments` one at a time; never cut at the FIRST underscore**, since
real base names contain one (`m1_garand`, `svt_rifle`). **DISPLAY STRING `"<Base Gun> (<Finish>)"`**:
whole-string comparison of `weapon->item_name` mismatches all 247 variants and falls through to the
default. `CoopStripSkinSuffix` splits on `" ("` - a different convention for a different string, so
neither substitutes for the other. FOUR consumers, one missed for three days: `CG_GetVMAnimPrefixIndex`
and `CG_FindAdsTune` (`cg_modelanim.c`), and `Player::CondWeaponActive` (`player_conditionals.cpp`)
inline. The missed one read as the wrong MAGAZINE during reload - the clip is not part of the gun, it is
an `Animate` spawned by an `attachmodel` frame command in the THIRD-PERSON torso anim, picked by
`IS_WEAPON_ACTIVE`. **Any new consumer tries the exact match first, then the stripped base name.**
(bug-1982)

---

<a name="procedural"></a>
## Procedural view/weapon motion

Four rules, each of which already cost a shipped regression that review, build and deploy all passed:
(1) integrate an oscillator's phase, never compute it as `time * frequency`; (2) never write a periodic
term into a state variable an exponential ease is tracking - ease an AMPLITUDE and recompute the
oscillation statelessly; (3) a cap expressed as a multiple of the thing it caps is not a cap; (4) a
shared budget that uniformly scales its members makes every control inside it non-linear. Worked cases
in **[`archive/traps-view-motion.md`](archive/traps-view-motion.md)**.
Read it before touching view bob, sway, recoil, lean or the ADS transform.

## Writing `.health` directly bypasses EVERY piece of damage feedback

`ent.health = ent.health - n` is not a quiet way to deal damage - it skips `Sentient::Damage`
entirely. No pain sound, no hit flash, no hitreact, and no `STAT_DAMAGEDIR`, the only field
`coop_dmgIndicator` reads. m3l3's church barrage did this, so damage arrived from nowhere: the
shells were audible, but nothing said you had been HIT, and the user reasonably called it random.

The floor is the second half. Clamping `health` to 1 after the subtraction makes the effect
non-lethal only in the narrowest sense - it never lands the kill, but pins the player at one hit
point so the next stray round does. That reads as the effect killing them, because it did. Put the
floor on the AMOUNT, at a survivable share of max health.

Deal damage with the real event and pass a direction (`vector_normalize(victim - source)`) like a
bullet does; `player.cpp` derives the indicator bearing from arg 5, the DIRECTION, not the position.
(bug-2015)

## Coop systems that touch EVERY actor will find the scripted ones

Every global actor pass - the weapon-variant roll, the AI personality roll, enemy
count-scaling - runs on a map's SCRIPTED CAST as readily as on its garrison, and a scripted
actor is defined by state the pass casually overwrites. `coop_variantRoll` ends in
`self.weapon = <tik>` + `self unholster` and re-armed m1l1's truck driver **while he was
holding the steering wheel**; the personality roll overwrites `type_attack` on ~65% of rolls
and locks a prone pose on ~12%, destroying the think the map assigned.

**Every fix for this has been correct and too narrow.** bug-1949 guarded the variant roll
with `self.no_idle` - which appears in 19 scripts while **42 hold ler actors**, so m1l1 broke
a month later anyway. That arithmetic is the tell: a guard that covers fewer sites than the
hazard has is a guard you will write again.

**The rule: one shared scene test, never a private one per pass.**
`officer.scr::coop_isProtectedActor` is that test. A new global pass calls it; it must not
invent a second, narrower check that will drift out of step with the first.

**Detecting scenery generically.** Maps declare it three ways; `audit_scene_actors.py` finds
all three, and each now has a guard (bugs 2033/2035/2037/2038 - one per pass, because each fix
patched only the consumer that had just broken):

| marker | readable as | guarded in |
|---|---|---|
| `exec global/disable_ai.scr` | `coop_aiDisabled` (our override sets it) | `coop_isProtectedActor` |
| `anim_scripted` | `self.no_idle` | `coop_isProtectedActor` |
| `threatbias ignoreme` | `self.threatbias == 0 - 6969` | `coop_variantRoll` **and** `coop_apply_personality` |

The last row was once "variant roll only", on the reasoning that `ignoreme` means *do not target
me*, not *I am scenery* - live-but-untargetable AI do exist (m5l1b:704, e1l3/hacks' Claus). A live
measurement beat the reasoning (bug-2051): m1l1's `barrel_guy`/`bazooka_wall` set-pieces were
carrying roles we assigned and targeting the player, so the personality roll honours it too. Keep
the general rule - **match a guard's scope to what it costs to be wrong** - but note which way it
was settled.

**Before guarding on a property, prove you can READ it.** `enableEnemy` is a lone `EV_SETTER`
(actor.cpp:1470) so reading throws - 136 errors a map, and since *a Script Error skips the
statement*, that guard shipped having never once executed (bug-2034). `threatbias` has a real
`EV_GETTER` (sentient.cpp:469) and reads fine. Registration tells you which you have, but that
same reasoning produced bug-2034 - so **probe it at runtime first, then re-probe against a
baseline count after**, or an over-broad guard silently kills the feature instead. A depth scan
proves a script *parses*, never that a property is *readable*.

Actors that are only *holstered* still have no generic marker; flag those with
`flags["coop_sceneActor"] = 1`, which is what spawned actors need anyway since a targetname
list cannot reach them.

---

<a name="t21"></a>
## T21 — Removing an enemy from the fight is not the same as killing him

**Bugs:** 1972 (M3L3 church), 2088 (array counts), 2091 (m3l1b bunker). **Three times, three maps.**

**Tell:** an objective that says "kill them all" never completes and the survivor is somebody the player
recruited or disabled.

Maps count enemies in **two unrelated ways**, and a fix for one does nothing for the other:

| mechanism | example | repaired by |
|---|---|---|
| an ARRAY of living axis | `level.coop_actorArray["german"]` | `aihandler.scr::coop_moveActorToTeam` (bug-2088) |
| a PER-ACTOR `waittill death` | `m3l1b.scr:1671-1697`, one watcher per defender | `coop_countasdead` (bug-2091) |

bug-2088 was believed to cover both and shipped untested; it could not, because the second kind
never counts anything — it *waits on a body to die*. Recruiting that body removes it.

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

**Use a server console command instead — it needs no protocol change at all.** The Quake `+`/`-`
bind convention is intact here: key-down builds `+cmd <key> <time>` (`cl_keys.cpp:1266`), key-up
builds `-cmd <key> <time>` (`:1078`), and unmatched commands forward to the server. Register both
forms in `G_ConsoleCmds` (`gamecmds.cpp:120`) — that table takes a plain function pointer and
**ignores the trailing key/time args**, so no Event format string is needed. Record only the key
state in the handler and do the work in a per-frame tick, or a tap released before your state
machine is ready gets swallowed. `+coopnade` (quick grenade) is the worked example.

Two neighbours that ARE extensible, if you genuinely need wire state: the weapon-command enum has
16 of its 31 values used, and `entityState.surfaces[]` bit 6 was reclaimed once (bug-2080). Both
are **wire semantics** — changing either means shipping exe + cgame + game + both renderers together.

---

<a name="t23"></a>
## T23 — Wired, plausible, and doing nothing

**Bugs:** 2099 (prone). Two causes, one feature, no error message from either; the first is the
missing-notetrack rule, now filed once under [TIKI/sound](#tiki).

**⭐ `last_ucmd` is not continuous — never reset a hold timer on one frame of no input.** Probe:
`up=-127` the whole time a key was held, yet the hold read `0.02 → 0.00 → 0.27 → 0.00`. The server
reads `upmove 0` on the odd frame (usercmd not yet refreshed). It presented as *"only works on
certain terrain"* — never terrain, just whether the jitter spared a clean 0.35 s. Hold-to-do-X needs
a grace period (150 ms) before treating a key as released.

**Shape:** four causes all presented as "prone is broken" and no two shared a fix. Resist the
single-root-cause instinct; probe each symptom. None of the four was found by reasoning about code.
