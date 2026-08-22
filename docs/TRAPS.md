# TRAPS — every way this project has broken itself more than once

**The highest-value file in the doc set.** Each entry is a failure family that recurred. Read the
**Tell** first — that is what you will observe. Status legend in
[SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md#status-vocabulary).

> Compressed 2026-08-20 (71.6 KB -> under the 60 KB ceiling): every rule, bug id and `file:line`
> anchor kept, verified by an anchor-set diff. War-story detail and one relocated section are in
> [`archive/traps-pruned-2026-08-20.md`](archive/traps-pruned-2026-08-20.md).

## Quick index

**!** = open now, **~** = recurring.

[T1](#t1)~ parse killers · [T2](#t2) generators corrupt what they write · [T3](#t3)~ silent veto ·
[T4](#t4)~ capacity families · [T5](#t5) `$player` array / NIL != NULL / sequential storms ·
[T6](#t6)~ what loads != what you shipped · [T7](#t7) cvar registration, flags, exec order ·
[T8](#t8) stufftext, `exec` order, name bus · [T9](#t9) spawn race · [T10](#t10)~ deploy gaps ·
[T11](#t11)! record over code · [T12](#t12)~ same-named trees · [T14](#t14)! verification lied ·
[T16](#t16) waits that never complete · [T17](#t17) script value types · [T19](#t19) a radius is a
SPHERE · [T20](#t20) one flag two states · [`Script Error` skips the STATEMENT](#script-error) ·
[turrets/AI spread](#turrets) · [`item_name` suffixes](#itemname) · [view motion](#procedural) ·
[TIKI/sound](#tiki) · [cross-cutting](#cross-cutting).

**T13** = [Cross-cutting](#cross-cutting) Q5; **T15** = `reference/harness_and_reproduction.md`;
**T18** = `archive/traps-t16-failsafe-recursion.md`. Older docs still link to `#t13` / `#t15`.
---

<a name="t1"></a>
## T1 — Morpheus parse killers: one bad token silently kills the WHOLE `.scr`

**Recurred under 15+ bug ids:** 089, 298, 331, 348, 402, 533, 739/750, 910, 962, 1067, 1069, 1105, 1205, 1283, 1285, 1751, 1908.

**Tell:** a feature silently does nothing, with **no error at the failure site**; every `::` call into the
file logs `Script was not properly loaded`. A whole subsystem dying at once (bug-533 took helmet + sandbag
+ medkit + emotes) means the shared bus file. The compiler is all-or-nothing: one syntax error kills the
entire file and the map runs with no script at all - raw team menu, unstartable.

> **An assignment with no value is a parse killer, and the error points at the WRONG line** (bug-1908):
> `level.coop_loRosterTab[69] = ` with nothing after it makes the parser take the *next* statement as the
> value and die on **that** statement's `=`. Not "the line ends with `=`" - a bare trailing `=` is a legal
> continuation retail `global/MountGunOrPlantCharge.scr` relies on; fatal only when the next code line is
> itself an assignment. `docs/tools/check_empty_rhs.py` runs every build. It came from a **generator**
> rendering an empty column: validate a generator's inputs.
>
> **All three scanners pass a file that cannot compile** - they check brace depth, line shape and string
> termination, not *expression* syntax; `println "a" + x + "b"` without parens is `unexpected TOKEN_PLUS`,
> kills the file, and scans clean (bug-1751). **Not verified until a server has loaded the map and the log
> shows no `parse error`.**

**Run all three — they catch disjoint classes:**

| tool | catches | blind to |
|---|---|---|
| `docs/tools/depthscan2.py` | brace/label depth (never negative; 0 at each column-0 label) | everything below |
| `docs/tools/linecheck.py` | a line **starting** with a binary operator | everything below |
| odd-quote scan (comment- and string-aware, per line) | unterminated / multi-line string literals | the rest of T1 |

The log names only the **first** offending line - bug-1283 had two multi-line strings in one file and
fixing the reported one would have left it equally dead. **Fix the class, not the line.**

| Confirmed trigger | Bug |
|---|---|
| Command syntax on an `EV_GETTER` property (`local.e getmins`) — must use property syntax | 910 |
| A script command a sub-agent invented (`userinfo`, `getcurrentdmweapontype`) | 298, 1067 |
| A function call inside a vector literal, or with one in the same expression | 348, 402 |
| Negatives/arithmetic: parenthesised `(-1)`, or in a COMMAND ARG slot — `$ent coopammo 0 - 1`. Compute to a local. **But** negative *vector components* are fine: `( 4016 0 - 967 0 - 328 )` == `( 4016 -967 -328 )`. | 1069, 1826, 1830 |
| An empty-array literal `[]` — morlang has none | 1105 |
| An unquoted `+`/`-` directive argument: `surface X -nodraw`, `surface X "+skin1"` — valid TIKI syntax, fatal in script (`unexpected TOKEN_PLUS`), **quote it**. Braces balance, so the depth scan misses it. | 533, 1308 |
| A leading `&&` or `\|\|` on a continuation line | 739/750 |
| A real newline inside a string literal — from a generator, or a hand-typed banner | 331, 962, 1283, 1285 |
| A backslash in a script path (resolved to `coop_modhelmet.scr`) | 1205 |
| Em-dash, UTF-8 BOM, any non-ASCII; duplicate label; label/brace mismatch | (CLAUDE.md) |

**NOT a parse killer, contrary to an older note:** `spawn <class>` **with** inline keyvalues is fine - 192
working occurrences including `main.scr`. `KNOWN_WORKING_STATE.md` still forbids it and is wrong; see
[90-folklore.md](90-folklore.md).

1. **`developer 1` is mandatory** - compile errors are developer-gated at `fgame/scriptthread.cpp:2858`,
   `:2869`, `:2883`; without it the failure is *completely* silent.
2. **Raw brace counts are an invalid check** - two opposite errors cancel on a broken file (bug-239), and
   comment/string braces miscount. Use a **running-depth scan**: never negative, 0 at every column-0
   label (internal `goto` labels may sit at depth 1).
3. Scanners live in `docs/tools/` (`depthscan2.py`, `linecheck.py`, `quotecheck.py`, `scrlint.py`).
   Verify any claimed script command against engine source **before** it lands.

**Live status:** clean (re-scans 2026-07-29, 2026-08-08); bug-1027 (`e3l4/outro.scr`) has this
signature.

---

<a name="t2"></a>
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

- **Binary mode on BOTH sides, repo files included.** `open(p, encoding=...)` translates newlines on
  *read*, so a CRLF file arrives as LF and `\r\n` patterns match nothing; `newline=""` on write then
  flips the **whole file** to LF. Both fail silently - `str.replace` returns unchanged rather than
  raising. Use `rb`/`wb`; the tree is **not uniform** (`challenges.scr` CRLF, `lobbyui.scr` LF-only,
  `docs/TRAPS.md` LF - bug-1600 was this file flipped by a prune script). Detect per file and **assert
  the match count before every replace**; that assert caught bug-1363.
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
[`archive/traps-t3-instances.md`](archive/traps-t3-instances.md) and `traps-t3-archived-rows.md`;
long narratives for the starred four in `archive/traps-pruned-2026-08-20.md`.

**⭐ A guard written for one question is wrong for the neighbouring one** (bug-1687).
`coop_isProtectedActor` answers *"leave this actor alone?"* and on m2l2a says yes to the whole cast (14
`ai_alarm` actors, anything with an `alarmthread`, every papers checker, the scene actors); reused for
*"who would notice a corpse?"* it vetoed everybody. **Re-read what a predicate was written to decide
before reusing it; when the answers differ, SPLIT rather than widen** — detection now filters on
nothing, the role uses a narrower `coop_bustCanKneel`, and the original stays for the containment sweep.

**⭐ Gating one entry point is not gating the feature** (bug-1685). Papers had **three** writers -
`enableClickablePapers`, `forcePapersInHand`, persistent `coop_papersAnytime` - and only two carried the
`coop_busted` guard, so pressing fire equipped papers and swallowed the trigger ("he just doesn't
shoot"). **Grep every writer of the shared state before calling a gate complete.** Same shape in our own
tooling (bug-1860): `docgen.py` applied `SELF_EXCLUDE` to the porcelain FILE LIST but not to the
`git diff --shortstat` it embeds in CHRONOLOGY, so every `build` changed the number CHRONOLOGY reports
about itself and **`check` could never pass** - a permanently red oracle trains everyone to ignore it.

**⭐ Our own guard disabled the retail mechanism**, twice in one day. On m2l2a `$naxos` is a
`trigger_multiple` with `spawnflags 128` = `TRIGGER_DAMAGE`, so the engine gives it
`takedamage = DAMAGE_YES` + `CONTENTS_CLAYPIDGEON` (`trigger.cpp:285-289`) - **shooting it is how retail
completes that objective**, and our stealth workaround opened with `$naxos nottriggerable` (bug-1671).
Same shape as bug-1669's limp *warning* disabling its own feature. **Ask what the vanilla mechanism
already is before adding a guard**, and when a user says "this is how vanilla handles it", read the
ENTITY, not the scripts around it.

**⭐ A guard can key on data that does not exist yet when it runs.** The scene-actor exemption tested
`alarmthread != NIL`, but `coop_apply_personality` fires on all 55 germans **23 s before**
`alarm_system_setup` assigns any `alarmthread` — it would have matched NOTHING and passed its own
acceptance check vacuously. **Print the keys a heuristic depends on and confirm they are populated at
that instant**; this is why a fix pass is instrumented first, repaired second.

**The `waittill`-already-fired shape recurs on every remaining map.** `invalid waittill spawn for
'Level'` reads like a warning but means "this script ran at the wrong time"; a failed `waittill` does not
abort - it does not wait, and the damage surfaces as NULL-listener errors elsewhere. Fix with
`waitthread coop_mod/replace.scr::waitTillSpawn` / `::waitTillPrespawn`. **Do NOT bulk-replace:** 191
bare `level waittill` sites ship and most are legitimately reached first, so **the runtime log is the
oracle** - fix only sites that actually throw, per map, as each is played ([T14](#t14)). Retail
sub-scripts absent from the mod tree: extract into `maps/<map>/`, change **only** the offending line.

**A second shape: the write executes and is then overwritten.** Proving execution is necessary but not
sufficient - prove nothing later writes the same field, and prefer the LAST write site in a render/view
path. The dangerous variant is a misplaced write that lands somewhere real (bug-1238 moved the 3P pivot):
silent corruption of a neighbouring feature.

**The UI corollary - never trade a working widget for an unverified one.** A `.urc` cannot be run or
diffed from here; the only oracle is the user's screenshot, and six attempts at one Service Record
checkmark each replaced a functioning pin box and each came back worse (bug-1546). **Add alongside it.**

**A vanilla scene reachable only from a BSP `trigger_once` never runs in coop.** m3l3's `main` carries
seven `//thread sceneN` lines noted "called from a trigger_once in the bsp", which never fire on a coop
server. scene6's one-off workaround (`coop_churchApproach` threads it) hid the pattern, so scene7 shipped
asleep - no crews, no MG nests, no firing nebelwerfers, a final objective that could never complete, and a
session log with **zero** occurrences of `scene7`. **Grep a map's `main` for commented-out `sceneN`
threads, account for every one, and guard each (`level.coop_sceneNStarted`).**

**The cure that works:** an autonomous verification rig - its value is catching a feature that silently
doesn't fire. And when you fix a silent-discard branch, **add the warning even though you also raised the
limit** - `sv_snapshot.c:549-553` does.

---

<a name="t4"></a>
## T4 — A capacity family has more members than you think

**Bugs:** 891, 892, 914-935, 1186, 1214, 1582, 1803; the whole entity-pool saga.

**Tell:** things vanish, alias, or corrupt at high entity/model/sound counts, often with **no log line
at all**. **The archetype, `maxentities 2048`:** shipped for *years* while `GENTITYNUM_BITS` was 10
(hard cap 1024) - it **added no entities; it disabled `AllocEdict`'s overflow guard**, so the allocator
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

**Read `openmohaa-hzm/code/qcommon/q_shared.h:1690-1755` before touching any capacity constant** - the `MAX_SOUNDS` comment there is canonical and not reproduced here: four binding constraints in the order they bite (`CS_AXIS = MAX_SOUNDS + 2393`, bug-1179; `MAX_RELIABLE_COMMANDS` must stay a power of two, bug-1183 twice; the 11-bit `sound_index` that silently truncates; `MAX_GAMESTATE_CHARS`), each tagged with the bug that found it including the two failed attempts, backed by a compile-time `#error`. **Turn every capacity rule into a build break.**

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
| Loose files beat paks **both ways** | bug-2020: 7,755 loose dev-only files under `G:\mohaa-gl2\main\sound\` made 1,623 alias refs (chatter restoration included) work in dev, silent for everyone else. **Audit assets against the SHIPPED set (retail paks + mod source tree), never the dev install** - loose files mask this class. |
| Homepath `maintt/` beats basepath; loose files beat paks | **bug-1633:** stale cfgs in the live profile's `maintt/` shadowed every deployed change; `build.ps1` now deploys cfgs to all three targets. Also watch for 0-byte decoys (bug-595). |

**⭐ THE FINAL ANSWER when a name is contested** (bug-922, closing the 5-round black-pouch saga): **stop
fighting for the name.** Mint a NEW shader name existing only in the coop pak, pointing at a PRIVATE
texture path also only in the coop pak, and retarget the `.tik` surface. **Diagnostic tell:** if a
"black" surface shows per-face **shading**, a lit default shader is drawing it and your identity def is
not reaching that surface at all.

**⭐ A playtest log only testifies about the build it loaded** (bug-1610). `coop_enigma.shader` existed
yet the log said `Couldn't find image file for shader enigma`: the client loaded 23:34 and quit 23:37:11,
the file was packed at **23:38:06**. **Compare the pk3 entry's timestamp
(`zipfile.getinfo(name).date_time`) against the `InitGame` line**, and verify fixes by reading them back
out of the deployed pk3.

**⭐ Imported third-party skin packs are this trap with the blast radius reversed.** A 2002-era skin pk3
routinely *redefines* stock shader names instead of minting its own, and the coop pak mounts last, so the
import silently repaints every other model (one redefined all 15 `viewsleeves*` shaders for one pilot
skin; another broke the holster on *every* skin; 39-pack sweep: `docs/proposals/skin_batch.md`). **Diff
an external pack's top-level shader block names against `hzm-mohaa-coop-mod/scripts/*.shader` and the
retail paks, and its `models/player/*.tik` basenames against the stock tiks** - a matching tik basename
*replaces* the stock model. `map foo.tga` resolves extension-agnostically, so a shader naming `.tga`
beside a shipped `.jpg` is **not** missing.

**Related generated-asset hazard:** ESRGAN upscales have shipped hallucinated worm noise (bug-1129),
a GPU-corrupted all-black `netgame_a/b` that blanked the server browser (bug-247), and 29 overridden
**vanilla** menu textures (bug-157). **Brightness-check output before commit**; ESRGAN is for photos
and text, and corrupts 1-2px chrome.

---

<a name="t7"></a>
## T7 — Cvar registration, flags, and exec order

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

| Trap | Tell | Bug |
|---|---|---|
| **Exec order** — engine execs `default.cfg` → saved config → `autoexec.cfg` **LAST**; `autoexec` `seta`-ing ~200 curated defaults overwrote every menu change on every launch. | Menu changes don't stick | 710 |
| **A renderer cvar's FLAGS are as sticky as its value**, and four bugs are one lesson: `Cvar_Get` ORs flags (`r_lodscale` twice-registered in gl2 became `CVAR_CHEAT`, slider reverted, 1125); a flag flipped for one A/B test archived it (`r_entlight_scale` dimmed every entity, 918); a `CVAR_ARCHIVE` rcon probe is retained forever (`r_toneMap 0`, 1148); and `CVAR_CHEAT` probes are useless on a listen server since `sv_cheats 0` clamps them back — use `CVAR_TEMP` (`r_globalFogDebug` **is still `CVAR_TEMP` at `renderergl2/tr_init.c:1926` — restore it**). | Slider reverts, or a test becomes a global regression | 918, 1125, 1148 |
| **Fail-open locks** — the armory padlock recompute zeroed all lock cvars then relied on a server push that might never arrive. Redesigned fail-**LOCKED**. | Content unlocked that shouldn't be | 682 |
| **Clamped cvars lie to menus** — gl2 clamps `r_ext_multisample` to 4, so the 8× MSAA plate was repointed at the unclamped `r_ext_framebuffer_multisample`. | Menu offers a value the renderer refuses | 1152 |
| **Never `seta` a genuine user preference** in `autoexec.cfg` (`cg_adsShoulderRight`). | Preference resets each launch | 258 |
| **Never seed `coop_uiB*`/`coop_uiN*`** — wipes last-known challenge progress. | Progress lost | — |
| **`g_gametype` is LATCHED - the FIRST map of a launch runs before it applies.** `ui_startdmmap` sets it and starts the map in the same frame, so map 1 boots under the OLD value: coop gates read 0 and never arm. Put `+set g_gametype 2` on the command line for any automated/dedicated run. |

**⚠️ A workaround written into the SAVED config outlives the bug it worked around and beats
`coop_defaults.cfg` forever** - `seta` in a saved config is a fossil, not a decision, so **record a
cvar mitigation with its bug id and clear it when that bug closes** (bug-1990). MSAA is the LIVE
case: `r_ext_multisample 0` mitigates a gl2 foliage-cutout artifact that is **still open**
(bug-1298), so the archived `0` stays until it closes. This section used to say gl2 was abandoned
and the artifact fixed - **both false**, and acting on that record produced a wrong MSAA fix on
2026-08-21. **gl2 is the renderer we ship and test on**; confirm from the qconsole banner, never
from a doc. [T11](#t11) biting inside T7.

**The structural fix is half-built:** `coop_defaults.cfg` execs **BEFORE** the saved config, so its values
are true defaults a menu change overrides and persists. Migration out of `autoexec.cfg` is incomplete, and
any menu-wired cvar still `seta`'d there **cannot** persist; the two files are disjoint, so they never
fight. Counts live in `docs/generated/CVARS_COOP.md` - never hand-copied here. **A cvar seeded nowhere**
(no engine `Cvar_Get`, no cfg line) makes `getcvar` return `""` on a clean profile and a script fallback
branch silently decides behaviour, so **calling such a cvar "default N" describes a branch, not a
default.****

**Archived client state keyed by POSITION rots on every catalogue change** (bug-1926): `coop_pin1..5`
stored catalogue row indices, the panzerfaust removal shifted every later row by 3, and every player's
pins silently repointed at different challenges. **Persist IDs, never positions**; give any positional
cache a generation stamp (crc of the id list) and wipe on mismatch; and a generated lookup map must be
`set`, not `seta`. Full entry: `archive/traps-pruned-2026-08-20.md`.

---

<a name="t8"></a>
## T8 — Server→client stufftext is a lossy, filtered channel

**Bugs:** 595, 597, 736, 758, 772, 773, 1364, 1365.

1. **Quote truncation** - `Player::EventStuffText` sends `stufftext "<cmd>"`, so an embedded quote ends
   the wire argument early; tell is client-side `Cvar ... does not exist` spam. **Send values UNQUOTED,
   ONE statement per stufftext**; `;`-joined multi-statements are the other half. (bug-736, bug-758)
2. **The whitelist** - `cg_servercmds_filter.cpp:304-316` silently drops server-stuffed `exec` and `vstr`
   as Reborn-exploit protection, which ate the **entire coop-detect handshake**
   (`coop_mod/cfg/detect.cfg`), the objectives setup and the armory pick carry-over, presenting as
   **three unrelated bugs**. Fixed with scoped exemptions: exec only for mod-namespaced paths, vstr only
   for `coop_*`/user-created cvars. (bug-597)
   **A plain `set <cvar>` is filtered the same way, invisibly.** Stuff two cvars with only one listed
   and the listed half still works, so it reads as a *logic* bug: the 3-mode view cycle set
   `cg_3rd_person` (listed) + `cg_freecam` (not), so first person worked, free-cam and chase were
   identical, and archived `cg_freecam` was unclearable. **Symptom → check the list:** one mode of a
   multi-mode client feature works, the rest collapse together. (bug-1991)
3. **Whitespace collapse** - `Cvar_Set_f` (`cvar.c:936`) takes its value from `Cmd_ArgsFrom(2)`, which
   re-joins *tokenised* args with a single space. Multi-word values survive unquoted (why the
   `coop_so1`/`coop_cp1` HUD pushes work), but **any run of whitespace normalises to one space** - never
   pad with spaces to align columns; use a visible separator. (bug-1364)
4. **An undispatchable token** - a bare name-bus token with no data character makes `playerExtract`
   return NIL. (bug-772)
5. **Client `exec`/`vstr` INSERT at the buffer front; only stufftext APPENDS.** `Cmd_Exec_f`/`Cmd_Vstr_f`
   call `Cbuf_InsertText` (`cmd.c`), so a click's whole cfg chain runs depth-first, atomically, in textual
   order, and **the LAST textual line in a client chain wins** (`s<n>sel.cfg` corrects `coop_loMvPN` on its
   final line *because of* insert semantics - do not move it earlier). Server stufftext arrives frames
   later over the wire (`Cbuf_AddText`), always after the client's chain, so a server echo races the next
   click by a round trip and can revert a preview. Any comment claiming exec APPENDS is wrong.
6. **The name bus dispatches ONE token per ~0.75 s batch; every other stacked token is destroyed.**
   `playerNameCommand` breaks at the FIRST token with data and `playerCleanName` truncates at the first
   `" ,"`. Priority is **BUS INDEX order, not click order** (skin 31 > helmet 35 > weapons 42-45 > menu
   46 > pins 47 > finishes 48-51), so rapid armory clicking silently drops actions - helmets/skins got
   close-time commit replays for this (bug-773); weapons/finishes have none. A new bus feature must
   tolerate drops (archived-`seta` + join replay) or add a close-commit.

**Related silent loss, receiving end:** a `.urc` widget placed below its menu's declared canvas height
**draws nothing at all** - `UIWidget::CalcClippedFrame` (`uilib/uiwidget.cpp:872`) clamps a child to its
parent's frame, so the height goes to 0. No error, no console line; the cvar push works and the row is
just absent. Set `noparentclip` (`WF_DIRECTED`, `uiwidget.cpp:1496`) or grow the canvas - prefer growing
it. **Check the menu's declared size before adding rows to any panel.** (bug-1365)

**⚠️ Remote clients need the updated `cgame.dll` too.** Server-stuffed SETs of `CVAR_ARCHIVE` cvars are
dropped by `CG_IsSetVariableAllowed` unless whitelisted - see [T3](#t3).

---

<a name="t9"></a>
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

**The exe is the usual gap.** `build.ps1` deploys the pk3s, `cgame.dll` and `renderer_opengl1.dll` -
**not** `openmohaa.exe`, `game.dll` or `renderer_opengl2.dll`, hand-copied to the GOG root, so the
deployed set spans several build dates and a change can be live in source, in `.cmake`, and *not* in
the binary being run. **A "verified" claim must name which binaries were deployed and when.**
`build.ps1` refuses to deploy while the game is running, so if you edited and did not deploy,
everything the user tests is the PREVIOUS build and every conclusion is void. A protocol-constant
change ships **all four** binaries; `game.pdb`/`cgame.pdb` ship beside their DLLs; back up as
`<binary>_pre_<feature>_bak.<ext>` - that hand-run convention *is* the rollback system, with 157
entries and **zero** for `renderer_opengl2.dll`.

---

<a name="t11"></a>
## T11 — Trusting the record over the code  ⚠️ STRUCTURAL

**Agreement between reviewers is NOT corroboration when they share an upstream source** (bug-1290). A multi-agent audit called "the injury vignette is permanently maxed after any DBNO revive" a live bug and two independent critique lenses confirmed it - all three had inherited one unchecked premise (that `healthonly 9999` puts 9999 into health; it clamps to `max_health`), so the "fix" would have hidden genuine low health. **Verify a finding's load-bearing premise against the code yourself** - agents reading the same brief are one witness, not three.

**A later entry can silently reverse an earlier one, so read the ordered LIST, not one entry.**
`docs/generated/FIX_INDEX.md` (file -> ordered bug ids) is the fix; the story belongs in HISTORY. Nothing
in the schema flags a reversal, so **edit the original entry** when you supersede a finding - bug-1473/1474
were corrected in place on 2026-08-06 after being filed on the wrong files.

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
`zzzzzz_co-op_hzm_mod_code.pk3` has **zero** `_research`/`_notes` entries. *(This entry previously
read "OPEN NOW" and cited an uncommitted `build.ps1:27` - both stale; releases up to v1.1.55 did
ship design docs, which is history, not a live hazard.)* **Still open:** the regression harness - the
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

---

<a name="t14"></a>
## T14 — Your verification lied: audits that pass, harnesses that measure nothing

**Bugs:** 1026, 1027, 1218-1220, 1473-1490, 1596-1598, 1812-1813.

*(worked examples archived to `docs/archive/traps-t14-worked-examples.md`)*

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
**`runto` → `turndone` hangs; `runto` → `movedone` does not.** Related: **never invent an exit/placement
offset when the model carries an authored one** - vehicles ship `driver_enter` / `passenger_enter` /
`*_seat` tags, walkable by construction, and an offset that works at one stop is a guess about free space
at every other stop. (bugs 1367, 1370)

**Missing anim + `waittill` = a corpse standing at the wall.** `setmotionanim` with an alias the model
lacks silently no-ops, and the `waittill flaggedanimdone` after it hangs that handler FOREVER (bug-1921).
(1) Never feed a per-weapongroup anim name to `setmotionanim` without a whitelist + fallback - the
Cornering wall set is LIVE for exactly rifle/pistol/mp40/mp44/bar/thompson/sten/vickers. (2) Audit
aliases by grepping the tiki TEXT, not `.skc` FILENAMEs, which undercount badly (2 groups have
`wall_death` skc files; 8 have live aliases). (3) An alias in `models/human/animation/human_<wg>.tik` is
NOT resolvable unless that pack is `$include`d by the model - vanilla gates the packs inside per-map
`includes` blocks, so a coop feature must add them unconditionally to our `new_generic_human.tik`
override (bug-1945).

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
2. **Did it run?** ([T3](#t3) - prove execution before tuning; check the gate cvar is seeded). And when
   a constant becomes a cvar, **update every reader in the same pass**: `coop_aiBuffer` converted the
   unsponge detectors but not `actorPainHandler`, still testing the literal 5000 while actors buffered to
   the unseeded fallback 1000, so the AI pain handler detached on **every actor's first hit**, silently
   (bug-1733) - and fixing it exposed a reader right only by accident (bug-1734).
3. **Is the binary I'm testing the one I built?** ([T10](#t10) — three binary states are live now)
4. **Am I reading the record or the code?** ([T11](#t11) — the code wins; read the record to the END)
5. **Am I guessing, or measuring?** (was T13) **BISECT FIRST - a cvar bisect beats any number of
   hypotheses** (bug-1298): turn things off one at a time until the symptom moves. Six deployed
   hypotheses on the gl2 "white distant objects" bug changed nothing; one bisect found it.

---

<a name="tiki"></a>
## TIKI and sound-alias traps

In **`docs/reference/tiki_and_sound_aliases.md`**: frame-command lines inside `server{}`/`client{}`,
aliases without a `maps` spec never loading, per-map `includes` blocks, cut-but-shipped content, and
never leaving a backup inside the mod tree. Read it before touching a `.tik` or adding a sound alias.
`docs/tools/audit_weapons.py` and `docs/tools/audit_shaders.py` make those traps testable.

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

- **A MANNED turret never reads `bulletspread`** - `weapon.cpp`'s `FT_BULLET` sets `vSpread` only
  for `owner->client`, and the `(max+base)/2` fallback is for `owner == NULL` (unmanned guns, which
  do not fire). An actor-manned turret's ONLY dispersion is `m_vAIBulletSpread`, set solely by the
  `aibulletspread` script event (retail SH/BT use 300-450; the OpenMOHAA handler ignores arg 2).
  Gunner `accuracy` does nothing - only `Actor::GunTarget` consults it. `coop_mg42AiSpread` feeds
  the real member. (bug-1940)
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
## Weapon `item_name` carries a variant suffix - every consumer must strip it

A skin/model variant is named `"<Base Gun> (<Finish>)"`. Any code that compares `weapon->item_name`
whole-string silently mismatches all 247 variants and falls through to whatever the default is.
There are now FOUR such consumers and one of them was missed for three days: cgame's
`CG_GetVMAnimPrefixIndex` and `CG_FindAdsTune` strip it via `CoopStripSkinSuffix`
(`cg_modelanim.c`), and fgame's `Player::CondWeaponActive` (`player_conditionals.cpp`) now does the
same inline. The symptom of the one that was missed was subtle and easy to misread: the wrong
MAGAZINE in the player's hand during reload, because the clip is not part of the gun at all - it is
an `Animate` spawned by an `attachmodel` frame command in the THIRD-PERSON torso animation, chosen
by `IS_WEAPON_ACTIVE`. **Any new consumer of `item_name` must try the exact match first and then the
stripped base name.** (bug-1982)

---

<a name="procedural"></a>
## Procedural view/weapon motion: four rules that have each cost a shipped regression

Both were broken on 2026-08-20 in a single batch of viewmodel "feel" work, and both produced defects
that survived review, a clean build, and a deploy, and were only caught by the user playing.

**1. Never compute an oscillator's phase as `time * frequency`. Integrate it.**

```c
ph = cg.time * 0.001f * (4.0f + fSpeed * 0.012f);   // WRONG
s_phase += fDt * (4.0f + fSpeed * 0.012f);          // right
```
If a frequency that multiplies elapsed time changes, the phase jumps by
`elapsed_time * delta_frequency` — and elapsed time only grows, so the defect gets worse the longer
the map runs. Five minutes in, a walking-speed change of ONE unit displaced the footfall bob by 3.6
radians in a single frame. Player speed changes every frame, so the bob teleported around the sine
continuously. The idle-breathing term had the same bug keyed on health. (bug-1983)

**2. Never write a periodic term into a state variable that an exponential ease is tracking.**

An ease of the form `x += (target - x) * k` owns `x`. Adding a sine into `x` creates a feedback loop
with three distinct failure modes, all of which shipped at once: the ease fights the tremor as if it
were signal; any entry gate of the form `|x| > eps` is held true BY the tremor, so it can never
stop; and the return-to-rest snap `|x| < eps` can never fire either. Result: a permanent ~2.75 Hz
tremor on the CAMERA that lasted until map change. Because it rode the camera it made every other
system look broken too — the ADS transition, weapon handling, walking — which sent three separate
diagnoses in the wrong direction before the real cause was found.

**The fix pattern for both:** separate STATE from OUTPUT. Ease only an *amplitude*; recompute the
oscillation statelessly at apply time from fixed frequencies. Gate on an external condition (is the
animation live?), never on the magnitude of the value the oscillator itself is feeding. (bug-1984)

**3. A cap expressed as a multiple of the thing it caps is not a cap.** The sustained-fire recoil
ceiling was `6 x the per-shot kick`, so it scaled with every factor the kick scaled with and reached
6.1 units on an MG — half of it straight back into the near plane, which put the gun through the
camera. Ceilings on a physical displacement belong in world units, and a component that can reach
the eye needs its own saturation separate from the total. (bug-1985)

**4. A shared budget that uniformly scales its members makes every control inside it non-linear,
and past saturation, INERT.** The viewmodel feel budget clamps the summed offset to 9u and scales
every layer to fit. The idle inspect wrote raise/pull/centre into it without registering as an
authored stow, asking ~9.4u by itself while sharing the 9u with breathing, sway, bob and mass lag.
Turning `coop_inspectCentre` UP raised the total length, raised the scale-down factor, and cancelled
the gain - the user correctly reported the control did nothing. **When a user says "adjusting X has
no effect", suspect a clamp before suspecting the value.** A deliberate large pose must be
registered in the budget's exemption (`s_vFeelExempt`) as the medkit stow, collision retract and
DBNO eye drop already were. Exempt only what must be large: the inspect's rearward pull stays inside
the budget because the 4u rear cap guards against a long gun reaching the near clip plane. (bug-2016)

**Related, same family:** the reverted ragdoll torso-twist limit (bug-1981) pumped rotational energy
because a correction moved `pt` without `ptPrev` — in Verlet, velocity IS `pt - ptPrev`, so moving a
point alone injects velocity. Same underlying error: mutating state that another integrator owns.

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
| `threatbias ignoreme` | `self.threatbias == 0 - 6969` | `coop_variantRoll` **only** |

The last is deliberately NOT in the shared test: `ignoreme` means *do not target me*, not *I am
scenery*, so live-but-untargetable AI exist (m5l1b:704, e1l3/hacks' Claus). Blocking a weapon
**skin** on them is free; blocking their **personality** would revert them to stand-and-shoot
turrets. **Match a guard's scope to what it costs to be wrong.**

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
