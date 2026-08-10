# PROPOSED replacement for `C:\mohaa-coop-dev\CLAUDE.md`

**This file is a proposal. It has NOT been applied.** Review it, then move it to
`C:\mohaa-coop-dev\CLAUDE.md` if you agree.

**Design intent:** the current `CLAUDE.md` fails by *duplicating* content that then goes stale — it
documents 6 of ~50 boot steps, 11 of 96 coop files, 8 of 642 cvars, and names two entry points that
do not exist. The replacement below **points** rather than duplicates, so it should need updating only
when the build/deploy contract or the doc set's structure changes.

> ⚠️ **Applying this is now the last unfinished step, and there is an active contradiction until
> you do.** `.wolf/OPENWOLF.md` and `.claude/rules/openwolf.md` have both been amended: sessions
> are pointed at `docs/SOURCE_OF_TRUTH.md` and `docs/generated/`, and told that `anatomy.md`,
> `cerebrum.md` and `memory.md` are frozen. But the **current** `CLAUDE.md` still opens with:
>
> > *"Check .wolf/cerebrum.md before generating code. Check .wolf/anatomy.md before reading files."*
>
> That line loads into every session and tells sessions to do the opposite. The draft below drops
> it. Applying this file resolves it; nothing else will.

**Two changes worth making alongside it:**
1. `CLAUDE.md` and `.wolf/OPENWOLF.md` are **untracked** (`.gitignore` line 2 is `/*` and neither is in
   the 47-file allowlist). Nothing surfaces their age and no commit ever forces an update. **Consider
   adding both to the allowlist.**
2. The OPENWOLF mandates to read `.wolf/anatomy.md` before any file read and `.wolf/cerebrum.md`
   before any code generation were **not physically satisfiable** (see
   [SOURCE_OF_TRUTH.md § Maintaining](SOURCE_OF_TRUTH.md#6-maintaining-this)). ✅ Both are now
   removed from `.wolf/OPENWOLF.md`, replaced by the generated file map and by
   `docs/TRAPS.md` + `docs/generated/FIX_INDEX.md`. The buglog rule is kept verbatim, because it
   works. The draft below matches.

---
---

# CLAUDE.md

Guidance for Claude Code working in this repository.

## Read this first

**`docs/SOURCE_OF_TRUTH.md` is the entry point.** It is reconciled against live code and takes ~10
minutes. Do not rely on this file for detail — it deliberately contains almost none.

| Question | File |
|---|---|
| What is this, how do I build it, what will bite me today | `docs/SOURCE_OF_TRUTH.md` |
| **Every way this project has broken itself more than once** | **`docs/TRAPS.md`** ← read before debugging anything |
| Does feature X exist, and is it actually verified | `docs/FEATURES.md` |
| What did the fork change; which binaries ship together | `docs/ENGINE.md` |
| What is broken / unverified / planned right now | `docs/OPEN.md` |
| Why was it done this way; what was rejected | `docs/DECISIONS.md` |
| When did X ship | `docs/HISTORY.md` |
| Where does file X live | `docs/generated/filemap.tsv` (complete sweep — grep it) |
| Every `coop_*` / engine cvar, with default, flags and seed | `docs/generated/CVARS_COOP.md`, `CVARS_ENGINE.md` |
| Coop scripts, boot order, coop-integrated maps | `docs/generated/SUBSYSTEMS.md` |
| This file's bug history, in order | `docs/generated/FIX_INDEX.md` ← read before editing a file with history |
| Claims that could not be anchored, and debunked folklore | `docs/90-folklore.md` |

Everything under `docs/generated/` is **rebuilt from source** by `docs/tools/docgen.py` — the Stop
hook runs it automatically. Never edit those files; never hand-write an inventory that could be
derived. Verify with `python docs\tools\docgen.py check` (exit 1 == stale).

## The five rules

1. **The code wins over the record.** Where a doc, a buglog entry or a memory file disagrees with the
   source, trust the source and **fix the record**. Read a buglog entry to the END — the log is
   append-only and has no supersession field, so a later entry can silently undo an earlier one.
2. **Status honesty.** Classify every claim as exactly one of `SHIPPED-VERIFIED` (confirmed in play),
   `SHIPPED-UNVERIFIED` (in the code, never playtested), `SHIPPED-CODE-DISABLED` (wired but its gate
   cvar is seeded nowhere), `REVERTED`, `PLANNED`, `OPEN`. **Do not write "shipped" without saying
   which.**
3. **Anchor every substantive claim** — a bug id, a `file:line`, or a git ref. Unanchored claims go in
   `docs/90-folklore.md`, not into an assertion.
4. **Leave the correction at the site.** When you revert or work around something, put an in-code
   comment naming the bug id. `maps/m1l1.scr:1683`, `coop_mod/loadoutpick.scr:436-440` and
   `qcommon/q_shared.h:1690-1755` are the models — all three survived contact with later sessions.
5. **Before designing any coop fix for a map feature, find how a confirmed-working map or the vanilla
   scripts already handle it, and copy that exact recipe.** Grep `maps/`, `global/`, `coop_mod/`
   first. The original devs usually solved it. Only invent when the search comes up empty.

## Before you debug anything, ask four questions

1. **Did it compile?** Morpheus is all-or-nothing — one bad token silently kills the whole `.scr` and
   the only symptom is a feature doing nothing. **`developer 1` is mandatory** (script prints AND
   compile errors are developer-gated at `fgame/scriptthread.cpp:2858/:2869/:2883`). The engine's own
   `^~^~^` lines always print, so a log full of them proves nothing.
2. **Did it run?** Several "shipped" systems have never executed — their gate cvar is seeded in no
   config. Prove execution before tuning. See `docs/TRAPS.md#t3`.
3. **Is the binary I'm testing the one I built?** Three different binary sets are live right now
   (build tree, gl2 sandbox, real install). See `docs/TRAPS.md#t10`.
4. **Am I reading the record or the code?** See rule 1.

## Build & deploy — hazards first

```powershell
# From C:\mohaa-coop-dev — the game must NOT be running
.\build.ps1
```

- **It writes into the player's real GOG install**, always: 3 paks + `autoexec.cfg` +
  `coop_defaults.cfg` to both `maintt` paths, plus `cgame.dll` and `renderer_opengl1.dll` to the GOG
  **root**.
- **It does NOT deploy** `openmohaa.exe`, `game.dll` or `renderer_opengl2.dll`. Those are **manual**.
  Back up the existing one as `<name>_pre_<feature>_bak.<ext>` first — that convention is the only
  rollback the project has.
- **DLL copies fail silently** (try/catch → printed WARNING) while the script still prints `Done.`
- **Never run it with the game open.** The engine memory-maps the paks; overwriting mid-session
  produces phantom "label does not exist" errors and a server crash (bug-241).
- **Protocol constants ship as a set of four** — exe + cgame + game + renderer. Details and the current
  constant table: `docs/ENGINE.md#protocol-coupling`.

Engine build: `cmake --build .cmake --config Release` in `openmohaa-hzm/`. `game.pdb`/`cgame.pdb` ship
next to their DLLs so crash dumps resolve to lines.

## Running and testing

Launch OpenMOHAA (Breakthrough profile, `com_target_game 2`) → Multiplayer → Start Game → HZM Coop Mod
→ pick a map → Apply.

- **Always use `ui_startdmmap 2`.** Raw `map` or `devmap` takes the SP loading path even with
  `g_gametype 2` latched — you get a "Continue" button and coop init never runs.
- t-series maps run fine under the normal `com_target_game 2` launch. The old "needs target 1" note is
  **inverted** — under target 1 the coop paks never mount.
- Log: `%APPDATA%\openmohaa\maintt\qconsole.log` (`logfile 2` flushes per line). `^~^~^` lines are
  machine-parseable.
- Automated verification: `C:\mohaa-coop-dev\_research\regression\` — currently the **only** working
  automated check. Map rotation tester: `exec coop_mod/cfg/maptest_start.cfg`.

## Architecture in one paragraph

Every coop map calls `waitthread coop_mod/main.scr::main` **first**; that runs ~50 init steps
**synchronously in one frame** (`wait`/`waitframe` are forbidden in or before it), gated downstream by
`level.coop_mainScriptLoaded`. Per-player state lives in `self.flags["coop_*"]`. **`$player` is
1-indexed and becomes an ARRAY with 2+ players connected** — the single biggest source of
multiplayer-only script storms. Requires `g_gametype 2`. Map transition is
`stuffsrv "map <name>"`; **never** `bsptransition`/`loadMap`/`leveltransition` on a live coop server.
Full boot table: `docs/30-inventory-coop-subsystems.md`.

## Script gotchas worth memorising

- **Parse killers** (any one silently kills the WHOLE file): em-dash, UTF-8 BOM, any non-ASCII, a bare
  negative `(-1)`, parenthesised arithmetic, an empty-array literal `[]`, an unquoted directive
  argument, a leading `&&`/`||` on a continuation line, a backslash in a script path, a function call
  inside a vector literal, command syntax on an `EV_GETTER` property, a script command that does not
  exist, a real newline inside a string literal. **Full list with the bug that found each:
  `docs/TRAPS.md#t1`.**
- **`spawn` with inline keyvalues is FINE** (192 working occurrences). An older note calling it a
  parse killer is wrong.
- **Raw brace counts are an invalid check** — two opposite errors cancel (bug-239) and comment/string
  braces are miscounted. Use a running-depth scan: never negative, 0 at every column-0 label.
- **`NIL != NULL`.** Guard maybe-unset entity refs with **both**.
- **No `waittill pain`** — use `waittill damage` or an `events.scr` subscription.
- **`moveto`/`move` silently no-op on `script_model`** — origin-step each tick.
- **`getmins`/`getmaxs` read ZERO in the spawn frame** (`setmodel` is deferred) and return **BASE**
  bounds, so scale must be multiplied in manually.
- **`.st` parse errors `ERR_DROP` the server** (opposite of `.scr`), and dedicated boots never parse
  `.st` — the first *listen* launch after an `.st` edit is the real test.

Per-script trace prints: set `level.cMTE_coop_<script> = 1`. In-game bisect: `iprintlnbold` (it reaches
`qconsole.log`; `println` does not without `developer 1`). Never ship dev prints to players.

## Bug logging

`.wolf/buglog.json` is the project's working record and the one system that did not degrade — 639
structured entries with a lookup key.

- **Read it before fixing anything** — the fix may already be known.
- **Log after any error, failed build, user-reported problem, or fix.** The threshold is LOW.
- **Append, never rewrite.** A tool that rewrites it wholesale can lose concurrent writes; this has
  already happened once.
- **Known format gaps** (see `docs/TRAPS.md#t11`): no `superseded_by`, no `status`, no `verified_by`,
  no `code_anchor`, and no per-file current-state index. Until those exist, **reading a single entry in
  isolation is unsafe** — read the whole chain for that file. If you add fields, those five are the
  ones worth adding.

## Superseded records — do not treat as authority

`.wolf/anatomy.md` (~2% coverage, mostly session-temp paths), `.wolf/cerebrum.md` (521 KB, ~40
duplicated sections, later corrections sitting alongside the superseded originals),
`.wolf/memory.md` (1.29 MB append-only journal), and `KNOWN_WORKING_STATE.md` (38 days stale; asserts a
rule this file contradicts). Recommendations for each are in
`docs/SOURCE_OF_TRUTH.md#6-maintaining-this`. **Nothing has been deleted.**
