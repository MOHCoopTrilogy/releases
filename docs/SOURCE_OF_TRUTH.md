# HZM MOHAA Coop Mod — SOURCE OF TRUTH

**Last reconciled against live code: 2026-07-29.**
This is the entry point. Read it start to finish once (~10 min), then use the index at the bottom.

> **The rule that governs this doc set: where a record and the code disagree, THE CODE WINS.**
> Every claim here carries an anchor — a bug id, a `file:line`, or a git ref. Claims that cannot be
> anchored live in [90-folklore.md](90-folklore.md), never asserted silently.

---

## Status vocabulary (used in every file in this set)

| Status | Means |
|---|---|
| `SHIPPED-VERIFIED` | In the code AND confirmed working by a human playtest or an instrumented probe |
| `SHIPPED-UNVERIFIED` | In the code, deployed, never confirmed by a playtest |
| `SHIPPED-CODE-DISABLED` | In the code and wired, but its gate cvar is seeded nowhere — **has never run in a shipped session** |
| `REVERTED` | Was done, then undone. Say why. These are the most valuable entries. |
| `PLANNED` | Designed, not built |
| `OPEN` | A known defect with no fix |

`SHIPPED-CODE-DISABLED` is a status this project needed and did not have. Several "shipped" AI
systems turned out to be in this bucket — see [OPEN.md](OPEN.md#never-ran).

---

## 1. What this is

A cooperative-multiplayer conversion of **Medal of Honor: Allied Assault War Chest** (GOG edition),
running on a private fork of **OpenMOHAA**. Three sub-projects under `C:\mohaa-coop-dev\`:

| Directory | What | Scale |
|---|---|---|
| `hzm-mohaa-coop-mod/` | The mod: MOHAA `.scr` scripts, tiks, ui, sounds, textures | 96 `coop_mod/*.scr` (55,922 lines), 63 of 118 map scripts coop-integrated, 101 `.urc` menus, 642 distinct `coop_*` cvars |
| `openmohaa-hzm/` | HZM fork of the OpenMOHAA engine (C/C++, CMake) | ~12,100 committed lines over 125 files since the Aug-2025 upstream branch point, **plus ~10,750 uncommitted** |
| `moh-modelviewer/` | Node.js model preview tool | Rarely touched, no coverage |

Lineage: the mod descends from chrissstrahl's HZM Coop Mod (first commit 2020-01-08, `527e0d0`).
Near-dormant 2022–2025. Current development era began 2026-03. **"Since day one" in practice means
since 2026-06-21** — nothing before that is recoverable in any structured record.

---

## 2. Read this first — the five things that will bite you today

These are current as of 2026-07-29 and each is independently verified. Full detail in [OPEN.md](OPEN.md).

**1. The deployed engine binaries do not match each other.** Four different build dates are live in
the real install simultaneously:

| Binary | Deployed | Size |
|---|---|---|
| `openmohaa.exe` | **2026-07-21 17:15** | 1,708,544 |
| `game.dll` | **2026-07-24 09:33** | 3,999,744 |
| `cgame.dll` | 2026-07-28 22:57 | 617,984 |
| `renderer_opengl1.dll` | 2026-07-28 22:57 | 844,288 |
| `renderer_opengl2.dll` | **2026-07-03 14:23** | 939,520 |

`GENTITYNUM_BITS` and `MAX_SOUNDS` are **wire-format** constants. The exe predates
`MAX_CONFIGSTRINGS 4096→8192` and `GENTITYNUM_BITS 10→11`; the cgame postdates them. `gameState_t`
is sized by `MAX_CONFIGSTRINGS` and `memcpy`'d whole across the exe↔cgame boundary with no version
guard. **A current exe already exists on disk** (`.cmake/Release/openmohaa.exe`, 2026-07-28 21:46,
1,710,592 B) — it was simply never copied, because `build.ps1` has no exe deploy block. This is a
deploy gap, not a build gap. See [ENGINE.md § Protocol coupling](ENGINE.md#protocol-coupling).

**2. `build.ps1` writes into the player's real GOG install, always.** It unconditionally copies
`cgame.dll` and `renderer_opengl1.dll` to the GOG root on every run regardless of what is in your
working tree. This is how sandbox-only engine constants once reached the real install (bug-1172).
It deploys **no exe, no game.dll, no renderer_opengl2.dll** — those are manual. See §3.

**3. Neither repo describes what is running.** The engine has **10,754 uncommitted insertions across
119 files** plus 20 untracked files (including `tr_gore.c` in both renderers and 17 GLSL post-FX
shaders — the entire post-FX chain is untracked). The mod has 65 uncommitted files. One `git
checkout` destroys roughly 10k lines of engine work with no restore point.

**4. `developer 1` is mandatory and is not in the old CLAUDE.md.** Script `println` output **and**
script compile/runtime errors are both developer-gated — three separate early-returns at
`fgame/scriptthread.cpp:2858`, `:2869`, `:2883`. The engine's own `^~^~^` lines are C-side
`Com_Printf` and always print, so **a log full of `^~^~^` does not mean script prints are working.**
A parse error is otherwise completely silent (bug-911).

**5. `C:\mohaa-coop-dev\scratchpad\` does not exist.** Roughly fifteen records name tools there as
canonical: `rcon.py` (the whole "drive the console yourself" workflow), `depthscan2.py` (the *only*
sanctioned parse-break check, since raw brace counts are invalid — bug-239), `coopaudit/*.ps1` (the
combat-verification rig), `gen_sr4.py`, `gen_gore_skins.py`, `gen_cosmetic_unlocks.py`,
`split_options_persist.py` (named in `coop_defaults.cfg`'s own header as that file's generator).
All gone — "scratchpad" resolved to a session-scoped temp directory. **Every generated artefact in
the project is currently un-regenerable.** See [OPEN.md § Tooling](OPEN.md#tooling-lost).

---

## 3. Build and deploy

### The hazards, stated first

| Hazard | Detail |
|---|---|
| **Deploys to the live install** | `build.ps1` writes 8 paths, 5 of them inside the player's real GOG install. No backup, no version stamp, no rollback. |
| **DLL copies fail silently** | Both DLL copies are `try/catch`'d and downgrade to a printed WARNING. A locked file means the binary does not update while the script still prints `Done.` |
| **Never run it with the game open** | The engine memory-maps the paks; overwriting mid-session makes it read garbage at stale offsets → phantom "label does not exist" errors and a server crash (bug-241). `build.ps1` has a pre-flight abort for this — do not defeat it. |
| **Protocol constants ship as a set** | Change `GENTITYNUM_BITS`, `MAX_SOUNDS`, `MAX_CONFIGSTRINGS` or any wire field and you must ship **exe + cgame + game + renderer** together (bug-930: the renderer had a hardcoded `GORE_MAX_ENTNUM 1024`). `build.ps1` ships only 2 of the 4. |
| **The rollback system is 157 hand-made `.bak` files** | In the GOG root: 75 `game.dll`, 37 `openmohaa.exe`, 25 `cgame.dll`, 19 `renderer_opengl1.dll` — and **0 for `renderer_opengl2.dll`**, the most-churned module. Naming convention is `<binary>_pre_<feature>_bak.dll`. |

### Mod (script changes — most common)

```powershell
# From C:\mohaa-coop-dev  — game must NOT be running
.\build.ps1
```

Packs three paks (ASCII sort puts `code` last so it overrides the assets):

| Pak | Contents | Size |
|---|---|---|
| `zzzzzz_co-op_hzm_mod_assets_snd.pk3` | `sound/` | ~514 MB |
| `zzzzzz_co-op_hzm_mod_assets_tex.pk3` | `textures/ models/ gfx/ env/` | ~645 MB |
| `zzzzzz_co-op_hzm_mod_code.pk3` | everything else | ~19 MB |

Deploys to **both** `G:\GOG\...\maintt\` and `%APPDATA%\openmohaa\maintt\` (homepath wins), plus
`autoexec.cfg` and `coop_defaults.cfg` loose to both, plus `cgame.dll` and `renderer_opengl1.dll` to
the GOG **root** (not `maintt\`).

The packer is **deterministic on purpose** (bug-237): sorted entries, entry mtime = source file
mtime not build time, git files excluded, an input digest skips repacking an unchanged bucket. The
auto-updater compares each pak's sha256 to the manifest, so non-determinism breaks updates.

### Engine (C++ changes — rare)

```sh
# In openmohaa-hzm/
mkdir .cmake && cd .cmake
cmake -DFLEX_EXECUTABLE=... -DBISON_EXECUTABLE=... -DOPENAL_INCLUDE_DIR=... -DOPENAL_LIBRARY=... ../
cmake --build . --config Release
```

Output at `openmohaa-hzm\.cmake\code\...\Release\`. `build.ps1` picks up **only** `cgame.dll` and
`renderer_opengl1.dll`. `openmohaa.exe`, `game.dll` and `renderer_opengl2.dll` are **manual copies**
— back up the existing one as `<name>_pre_<feature>_bak.<ext>` first, that is the project's only
rollback mechanism.

`game.pdb` and `cgame.pdb` ship next to their DLLs in the GOG root so crash dumps resolve to lines.

### Releases

`publish_release.ps1` deliberately stages all five engine binaries **from the deployed GOG root**,
not from the build tree — the stated reason being that a clean rebuild would ship binaries nobody
has played. The trade is real: the artefact is exactly the tested set, but **there is no recorded
mapping from a shipped exe back to a commit**, and given the uncommitted engine tree there could not
be one. Per-file asset reuse is normal (manifest 1.1.55 points `game.dll` at v1.1.55 but
`openmohaa.exe`/`cgame.dll` at v1.1.51 and `renderer_opengl1.dll` at v1.1.50).

### Running and testing

Launch OpenMOHAA (Breakthrough profile, `com_target_game 2`) → Multiplayer → Start Game → HZM Coop
Mod → pick a map → Apply. Apply execs `coop_mod/start_server.cfg`, which ends with `ui_startdmmap 2`.

**Always use `ui_startdmmap 2`.** Raw `map <name>` or `devmap` triggers the SP loading path even
with `g_gametype 2` latched — you get a "Continue" button and coop init never runs.

t-series maps (`t1l1`–`t3l2`) run fine under the normal `com_target_game 2` launch (BT mounts
main+mainta+maintt). The old "t-series needs `com_target_game 1`" note is **inverted and wrong** —
under target 1 the coop pk3s never mount at all.

⚠️ **The install the user actually plays is `G:\mohaa-gl2`, not the GOG tree** (verified 2026-08-08
from the running process). `PLAY-GL2.bat` launches it with `+set fs_basepath "G:\mohaa-gl2" +set
fs_homepath "G:\mohaa-gl2\home"` — an **isolated homepath**, so everything the game *writes* lands
under `G:\mohaa-gl2\home\maintt\`, not `%APPDATA%`:

| What | Where it really is |
|---|---|
| Console log | `G:\mohaa-gl2\home\maintt\qconsole.log` (`logfile 2` is on the command line) |
| Build-mode captures, blueprints, XP/challenge/unlock saves | `G:\mohaa-gl2\home\maintt\coop_mod\save\` |
| Player config | `G:\mohaa-gl2\home\maintt\` |

`%APPDATA%\openmohaa\maintt\` is the homepath only for a plain GOG launch, and its copies are
**months stale** — reading them to check what just happened in-game silently answers the wrong
question. The coop pk3s are **hardlinked** between `G:\GOG\...\maintt\` and `G:\mohaa-gl2\maintt\`,
so `build.ps1` reaches both; the engine binaries are **not** linked and are copied by hand.
Console lines prefixed `^~^~^` are machine-parseable.

**There is one working automated verification system:** `C:\mohaa-coop-dev\_research\regression\`
(regress.ps1 / regress.py / hzmreg / roster.json / baselines / runs). It produced bugs 1218–1220. It
lives in the **workspace-root** `_research`, not the mod's — those are two different trees and only
the mod's is excluded from the shipped pak. See [TRAPS.md § T12](TRAPS.md#t12).

---

## 4. Architecture in brief

### Entry point

Every coop-integrated map script (`maps/<map>.scr::main`) calls `waitthread coop_mod/main.scr::main`
as its **first** statement. That runs the entire coop init **synchronously in one frame** — `wait`
and `waitframe` are forbidden in or before it.

`main.scr::main` (`coop_mod/main.scr:84-281`) runs **~50 `waitthread`/`thread`/`exec` statements**,
not the 6 the old CLAUDE.md documents. Two entry points in that old list do not exist under the
documented names:

- it is `events.scr::initialiseEvents` (`main.scr:128`), **not** `events.scr::init`
- it is `officer.scr::coop_officer_init` (`main.scr:133`), **not** `officer.scr::init`

Undocumented boot steps include `xp.scr::xp_init` (:103), `challenges.scr::chal_init` (:106),
`aihandler.scr::coop_reinf_brain` (:115), `exec loadout.scr` (:118),
`medkit.scr::coop_scan_health_entities` (:132), `director.scr::director_main` (:134),
`weather.scr::coop_weather_init` (:135), `ambience.scr::coop_ambience_init` (:136), and 11 cvar-gated
`coop_selftest_*` probes (:171-238). Full table in
[30-inventory-coop-subsystems.md](30-inventory-coop-subsystems.md).

`level.coop_mainScriptLoaded` gates everything downstream; scripts needing coop ready call
`waitthread coop_mod/main.scr::waitForMainScript`.

### Per-player state

All per-player state lives in `self.flags["coop_*"]` (`coop_isActive`, `coop_isHost`, `coop_deaths`,
`coop_respawnOrigin`…). **`$player` is 1-indexed and becomes an ARRAY whenever 2+ players are
connected** — this is the single biggest source of multiplayer-only script storms. See
[TRAPS.md § T5](TRAPS.md#t5).

### Gametype

Requires `g_gametype 2` (Team Match). Coop features gate on `level.gametype != 0`.
`main.scr::changeGameType` temporarily flips gametype for SP-only engine calls (disguises, some
sound callbacks); only one instance may run at a time.

### Map transition

- **Clean restart / advance**: `stuffsrv "map <name>"` → `SV_Map_f` (no archive, no gametype flip)
- **Never** use `bsptransition`, `loadMap` or `leveltransition` on a live coop server — they run the
  persistant archive and crash.

### Configuration

`autoexec.cfg` and `coop_defaults.cfg` are the de-facto configuration contract. The split matters:

- **`coop_defaults.cfg`** is exec'd by an engine hook **BEFORE** the saved player config → its
  values are true defaults that a menu change overrides and persists.
- **`autoexec.cfg`** is exec'd **AFTER** the saved config → anything set there re-forces the shipped
  value every launch and **wipes the player's menu choice**.

The migration between them is only half done. The two files are strictly disjoint (verified: zero
shared cvar names), so they never fight — but 9 post-FX cvars still sit in `autoexec.cfg` while
being menu-wired, and therefore cannot persist. See [OPEN.md § Config](OPEN.md#config).

Of 642 `coop_*` cvars: 147 registered with a default by the engine, 452 seeded by a shipped cfg,
**144 seeded nowhere at all** — for those, `getcvar` returns `""` on a clean profile and a script
fallback branch silently decides behaviour.

---

## 5. The doc set

### Core (this set — start here)

| File | What it answers |
|---|---|
| **SOURCE_OF_TRUTH.md** | *(this file)* What is this, how do I build it, what will bite me today |
| [FEATURES.md](FEATURES.md) | Every system built, by domain, with cvars and status |
| [ENGINE.md](ENGINE.md) | What the fork changed vs upstream, by subsystem + protocol-coupling rules |
| [**TRAPS.md**](TRAPS.md) | **Every way this project has broken itself more than once.** Highest-value file. |
| [OPEN.md](OPEN.md) | Open defects, unverified work awaiting playtest, planned-but-unbuilt |
| [DECISIONS.md](DECISIONS.md) | Significant technical decisions and why, including roads not taken |
| [HISTORY.md](HISTORY.md) | Condensed chronology, one line per item |
| [PROPOSED_CLAUDE.md](PROPOSED_CLAUDE.md) | Proposed replacement `CLAUDE.md` — **review and move, not applied** |

### Generated — `docs/generated/` (**DO NOT EDIT**, rebuilt from source)

Everything here is a pure function of the repository state, regenerated by
[`docs/tools/docgen.py`](tools/README.md). The Stop hook runs it automatically at the end of
any session that touched the project, so **these cannot go stale the way the reference files
below did**. If one is wrong, fix the code or the generator — never the file.

| File | What it is |
|---|---|
| [generated/FILEMAP.md](generated/FILEMAP.md) | Workspace census + full source index, from a complete sweep |
| `generated/filemap.tsv` | Every in-scope file, one row, greppable — use this to locate anything |
| [generated/CVARS_COOP.md](generated/CVARS_COOP.md) | Every `coop_*` cvar: engine default, flags, cfg seed + class, script sites, ui |
| [generated/CVARS_ENGINE.md](generated/CVARS_ENGINE.md) | Every cvar the engine registers, with default, flags and anchor, + the conflicting-default set |
| [generated/SUBSYSTEMS.md](generated/SUBSYSTEMS.md) | `coop_mod/*.scr` inventory, the extracted `main.scr::main` boot order, coop-integrated maps |
| [generated/FIX_LEDGER.md](generated/FIX_LEDGER.md) | Every buglog entry, chronological |
| [generated/FIX_INDEX.md](generated/FIX_INDEX.md) | **file → ordered bug ids** + tag index. Read this before touching a file with history. |
| [generated/CHRONOLOGY.md](generated/CHRONOLOGY.md) | Per-repo history, HEAD, remotes, and current uncommitted exposure |

Verify at any time — staleness is testable, not hoped-for:

```powershell
python docs\tools\docgen.py check    # exit 1 == the docs no longer match the code
python docs\tools\docgen.py build    # fix it
```

### Reference (earlier hand/grep-built inventories — superseded, kept for their prose)

| File | What it is |
|---|---|
| [30-inventory-coop-subsystems.md](30-inventory-coop-subsystems.md) | Superseded by `generated/SUBSYSTEMS.md`; keeps the per-file role commentary |
| [31-inventory-coop-cvars.md](31-inventory-coop-cvars.md) | Superseded by `generated/CVARS_COOP.md` (which also sweeps `.urc`) |
| [32-inventory-engine-cvars.md](32-inventory-engine-cvars.md) | Superseded by `generated/CVARS_ENGINE.md` |
| [33-inventory-build-deploy.md](33-inventory-build-deploy.md) | Every path `build.ps1` and `publish_release.ps1` write |
| [BUGLOG_INDEX.md](BUGLOG_INDEX.md) | How to read a buglog entry safely |
| [fix_ledger.md](fix_ledger.md) | Superseded by `generated/FIX_LEDGER.md` |
| [90-folklore.md](90-folklore.md) | Claims that could not be anchored, and claims the record itself debunked |

### Earlier partial passes (superseded by the Core set, kept for their detail)

`01-project-map.md`, `02-status-ledger.md`, `03-record-vs-code.md`, `10/11/12-conventions`,
`20-decisions.md`, `21-user-preferences.md`, `SOT_01_TIMELINE.md`, `recurring_traps.md`,
`open_defects.md`, `README.md`. Where these disagree with the Core set, **the Core set is newer and
has been re-verified against live code** — see [90-folklore.md](90-folklore.md) for the specific
corrections.

---

## 6. MAINTAINING THIS

### The split, and why it is the whole design

**Authored** (`docs/*.md`) holds judgement, causation and open questions — a human or an agent
writes it. **Generated** (`docs/generated/*`) holds inventories, indexes and counts — swept out
of the code by `docs/tools/docgen.py`.

The rule: **anything extractable from code, git or `buglog.json` MUST be generated.** A
regenerated doc cannot drift; a hand-maintained inventory always does, and not for want of
discipline. `.wolf/anatomy.md` promised "a 2-3 line description for every file in the project"
while its only update rules were reactive — add a file when a session happens to read it —
so complete coverage was **structurally impossible under its own rules**. It reached ~2%.
`.wolf/memory.md` was told to append per action with no ceiling anywhere; it reached 1.29 MB.
`.wolf/cerebrum.md` was told the bar was low *and* told to be read in full before generating
code; at 525 KB the first rule had made the second one impossible.

The authored files carry the counterweight the others lacked: a **size ceiling** (printed by
`docgen check`, tabulated in [generated/README.md](generated/README.md)) and a
**merge-and-prune** rule. Over budget means fold entries together and delete what the code now
makes obvious — never append past it. See [.wolf/OPENWOLF.md](../.wolf/OPENWOLF.md).

### What to update, when

| When you… | Update |
|---|---|
| Ship a feature | [FEATURES.md](FEATURES.md) entry + status; one line in [HISTORY.md](HISTORY.md) |
| A playtest confirms something | Flip `SHIPPED-UNVERIFIED` → `SHIPPED-VERIFIED` in FEATURES.md and remove it from [OPEN.md](OPEN.md) |
| Revert something | Move the FEATURES.md entry to `REVERTED` **and say why**. Add an in-code revert comment naming the bug id — see below. |
| Break the same way twice | New entry in [TRAPS.md](TRAPS.md). This is the only file that pays compound interest. |
| Make a real architectural choice | [DECISIONS.md](DECISIONS.md), including the option you rejected |
| Change a protocol constant | [ENGINE.md § Protocol coupling](ENGINE.md#protocol-coupling) + ship all four binaries |
| Find the record and the code disagree | Fix the record, note it in [90-folklore.md](90-folklore.md), and **trust the code** |
| Want a file list, cvar table, bug history or commit log | **Do not write one.** Read `docs/generated/`, or extend `docs/tools/docgen.py` so it is derived. |
| Notice a generated file is wrong | Fix the code or `docs/tools/docgen.py`. Editing `docs/generated/` is overwritten on the next Stop. |

### The one habit worth copying

`maps/m1l1.scr:1683` carries a six-line in-code comment naming bug-1184 and explaining exactly why a
change was reverted. That single comment is why the project's flagship record-vs-code discrepancy
resolved cleanly. **When you revert or work around something, leave the note at the site.** The same
pattern appears at `coop_mod/loadoutpick.scr:436-440` (bug-1205) and across
`qcommon/q_shared.h:1690-1755`, which is the best piece of institutional memory in the codebase — it
enumerates four binding constraints in the order they bite, each tagged with the bug that discovered
it, **including the two failed attempts**, and backs it with a compile-time `#error`.

### Superseded records — recommendations (nothing deleted)

| File | State | Recommendation |
|---|---|---|
| `.wolf/anatomy.md` | **Actively misleading.** Tracks 145 entries, most of them session-scoped temp scripts under `AppData\Local\Temp`; 129 of its section headers are empty. Real source is ~4,000 mod files + 2,143 engine files → **~2% useful coverage**, not 8%. | ✅ **DONE.** Replaced by `generated/FILEMAP.md` + `filemap.tsv`, built by full sweep so it cannot be partial. `OPENWOLF.md` no longer directs sessions to it. File kept, frozen. |
| `.wolf/cerebrum.md` | 521 KB / 1,687 lines / ~130k tokens. Four canonical sections at byte offsets 180 / 5,848 / 182,734 / 242,462, then ~40 duplicated per-date sections appended after them — including at least one pair where a later section corrects an earlier one **that is still present verbatim**, so a naive grep returns the superseded version. | ✅ **DONE.** Durable content is in [DECISIONS.md](DECISIONS.md), [TRAPS.md](TRAPS.md) and `21-user-preferences.md`; those now carry size ceilings and a merge-and-prune rule. `OPENWOLF.md` freezes cerebrum and drops the unsatisfiable "read before every code generation" mandate. File kept. |
| `.wolf/memory.md` | 1.29 MB append-only journal; roughly 91% is per-action noise (`\| HH:MM \| description \| files \| outcome \| ~tokens \|`). | ✅ **Growth stopped.** The per-action append is retired in both `OPENWOLF.md` and `post-write.js` (the hook that actually wrote it); `stop.js` still writes one bounded line per session. File kept — **rotating the existing 1.29 MB into `.wolf/archive/` is still worth doing** and needs a human call on what to keep. |
| `.wolf/buglog.json` | **The one record that works** — 639 entries and growing, structured, with a lookup key. But: no `superseded_by` field, no `status` field (the only machine-readable one, `fix_verified`, exists on 17 late-June entries then was abandoned), no `verified_by`, no `code_anchor`. **Reading any entry in isolation is unsafe by construction.** | **Keep and extend.** Add those four fields. Add a per-file index (`file → ordered bug ids → net current state`) — that single addition is what would have prevented the +180 roll incident. Append, never rewrite (a post-write hook once clobbered it wholesale). |
| `KNOWN_WORKING_STATE.md` (repo root) | 38 days stale and asserts a rule CLAUDE.md explicitly says is **wrong**: that `spawn <class>` takes no inline keyvalues. It does (192 working occurrences incl. `main.scr`). Written in imperative process-rule voice, so any session obeying it inherits a falsified constraint. | **Highest-priority archive candidate.** Its BOM check, bare-negative check and build-before-test rule are already lifted into [TRAPS.md](TRAPS.md). Move to `docs/archive/`. |
| ~55 root-level `.md` files dated 2026-06-21..25 | The original SP→coop conversion campaign record. Content either implemented (re-documented in `_research/coop_conversion_audit.md`) or invalidated. They sit at the repo **root**, so a glob finds them before the current `_research/` set. | **Move to `docs/archive/2026-06/` with a one-line index.** Do not delete — the `fix_*.md` files record root causes still cited today. Lift `COOP_CONVERSION_MASTER.md`'s 10-step coop-enable recipe out first. |
| `_research/release_drafts/release_notes_v1.2.0_final.md` | v1.2.0 was finalised 2026-07-18 and **never published**; the line continued 1.1.49 → 1.1.55. Three of the four v1.2.0 files are marked DRAFT; **this one is not**, and reads as authoritative. | Mark the whole v1.2.0 set superseded by the 1.1.50–1.1.55 manifests. |
| `_phillips_dossier.md` | Superseded by its own resolution header (bug-1135). | Archive — but **keep the "Refuted" list**, a genuinely valuable record of ~12 dead hypotheses. |
| `hzm_cvars.txt` (ships in the code pak) | Player-facing, 64 lines, documents `coop_lmsLifes` at line 11 — **a name nothing reads**. Live cvar is `coop_lmsLives` (`main.scr:1568`, `player.scr:142`, `dbno.scr:281`). | Fix the typo. A player following the shipped documentation sets a dead cvar and LMS silently stays off. |
| `CLAUDE.md` | 24 days stale (mtime 2026-07-05 22:59). **Untracked** — `.gitignore` line 2 is `/*` and it is not in the 47-file allowlist — so nothing surfaces its age and no commit ever forces an update. Documents 6 of ~50 boot steps, 11 of 96 coop files, 8 of 642 cvars, and names two entry points that do not exist. | Replace with [PROPOSED_CLAUDE.md](PROPOSED_CLAUDE.md). Consider adding it and `.wolf/OPENWOLF.md` to the git allowlist so they become reviewable. |

---

## 7. CONFIDENCE

**Well-evidenced — verified directly against live code during this pass:**
engine protocol constants (`q_shared.h:1667/1680/1742/1749/1787/1805`, `qcommon.h:215`,
`sv_snapshot.c:285`, `cg_public.h:41`, `tiki.h:36`, `actor.h:306`); the m1l1 +180 revert
(`maps/m1l1.scr:1683`); the m3l2 missing label (`maps/m3l2.scr:2854`, one reference, zero
definitions); deployed-binary timestamps and sizes; the 157 `.bak` files and the zero for
`renderer_opengl2.dll`; uncommitted counts (engine 119 files / 10,754 insertions / 20 untracked, mod
65 files / 2,478 insertions); the absence of `C:\mohaa-coop-dev\scratchpad\`; `coop_ddaEnabled 1` in
`autoexec.cfg:381`; the unseeded state of `coop_aiDynamic` / `coop_aiSquad` / `coop_moraleEnable` /
`coop_retreatEnable`; file counts (96 coop scripts, 63/118 coop maps); the existence and contents of
`_research/regression/`; the three developer-gate early-returns.

**Inferred — reasoned from strong circumstantial evidence, not proven:**
That the deployed `openmohaa.exe` was actually *built from* the older sources — mtime proves when a
file was written, not what it was compiled from; confirming needs binary inspection I did not do.
That `_research` shipped to players in ≤v1.1.55 — corroborated by the released code pak being
272,839 B larger than the post-fix rebuild, which is the right order of magnitude, but other content
also changed between those builds. That the buglog's ~632 unassigned ids were never assigned rather
than lost — two records disagree (~637 "lost" vs ~632 "never assigned") and **neither demonstrated
its claim**; treat the extent of the 2026-07-27 hook clobber as unresolved.

**Could not be confirmed:**
*Any* live behaviour. I did not build, deploy, or launch the game, so **every `SHIPPED-UNVERIFIED`
item stays unverified and no OPEN defect was reproduced.** Whether `maintt\cgame.dll` (a 33-day-old
copy present in *both* maintt trees) shadows the GOG-root copy for **module** loading — that needs
reading the engine's module-load path. What is inside the 10,754 uncommitted engine lines — measured
in aggregate, not read, and a concurrent workflow is actively editing `renderergl2/`. Per-map
completion status: `_research/coop_conversion_audit.md` grades t1l3/t2l3/t2l4 as **F**
(hard-uncompletable at 2+ players), but the addon-restore fix and gag overrides landed *after* that
grading and were never re-graded — the mechanism is fixed; whether those missions are now completable
is **unknown**.

**A known limitation of this doc set's own method:**
Verification status is largely unrecoverable from the historical record. Only 17 of 639 buglog
entries carry a machine-readable `fix_verified` flag; for the rest, status had to be inferred from
prose in a free-text field where "FIXED", "NOT YET VISUALLY VERIFIED", "PENDING runtime data",
"QUEUED" and "REVERTED" all read the same to a grep. A keyword pass over that field put 26 entries in
**both** the REVERTED and the VERIFIED buckets. Consequently the `SHIPPED-VERIFIED` set here is
deliberately small and the `SHIPPED-UNVERIFIED` set is almost certainly **under-counted** — some of
it was tested and simply never written down. Only the user can close most of these.
