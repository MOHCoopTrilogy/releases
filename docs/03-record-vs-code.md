# 03 — Record vs Code: verified discrepancies

Every item here was checked against the working tree on **2026-07-29**. **The code wins.**

---

## 0. ⚠️⚠️ The DEPLOYED binaries do not match each other — live protocol mismatch

This is the highest-priority finding in this document set. It is not a doc-vs-code disagreement —
it is a **code-vs-shipped-artefact** disagreement, which is the same failure mode one layer down.

**Protocol constants, three ways:**

| Constant | HEAD `819a6e93` (2026-07-23) | Working tree (2026-07-28 21:25) | Cross-binary? |
|---|---|---|---|
| `GENTITYNUM_BITS` | **10** | **11** | yes — wire encoding |
| `MAX_MODELS` | **1024** | **2048** | yes — configstring layout |
| `MAX_SOUNDS` | **1280** | **1600** | yes — configstring layout + wire |
| `MAX_CONFIGSTRINGS` | **4096** | **8192** | yes — **sizes `gameState_t`** |
| `MAX_RELIABLE_COMMANDS` | **512** | **1024** | yes — per-client buffers |

**Deployed binary mtimes in the GOG root:**

| Binary | Deployed | Relative to `q_shared.h` (2026-07-28 21:25) |
|---|---|---|
| `openmohaa.exe` | **2026-07-21 17:15** | **7 days OLDER** — predates even the 07-23 HEAD commit |
| `game.dll` | **2026-07-24 09:33** | **4 days OLDER** |
| `cgame.dll` | 2026-07-28 22:57 | newer ✓ |
| `renderer_opengl1.dll` | 2026-07-28 22:57 | newer ✓ |

**Why this matters.** `sizeof(gameState_t)` is derived from `MAX_CONFIGSTRINGS` and is `memcpy`'d
**whole** across the exe↔cgame boundary (`CL_GetGameState` → cgame's own `gameState_t`) with **no
API version guard that would catch a mismatch** — this project's own `q_shared.h` comment says so.
A 4096-vs-8192 mismatch is a **2× struct-size disagreement across a DLL boundary**. `GENTITYNUM_BITS`
10 vs 11 additionally changes the entity wire encoding.

This is exactly the discipline the record repeatedly states and here is not being met:

> "Any change to `MAX_CONFIGSTRINGS` REQUIRES `openmohaa.exe` + `cgame.dll` + `game.dll` rebuilt and
> deployed together, or a stale DLL corrupts memory silently."

**Corroboration:** the parallel buglog audit found bug-1219 (2026-07-29) still reporting `max=1280`
from a **live** log — consistent with a server running the old exe/game.dll pair.

**Honest caveat:** file mtime proves when a file was *written*, not which source it was *built*
from. This is strong circumstantial evidence, not proof. **Verify the binaries themselves before
acting** — but do not ship anything else until this set is reconciled.

**The fix is mechanical:** rebuild `openmohaa`, `fgame`, `cgame` (and the renderer) from the current
tree and deploy all of them together. Freshly built copies already exist at
`.cmake/.../Release/` dated 2026-07-29 01:07 for cgame/game/renderer, and `.cmake/Release/openmohaa.exe`
dated 2026-07-28 21:46 — **note that exe predates the 21:25 `q_shared.h` edit by only 21 minutes, so
confirm it actually picked the change up rather than assuming.**

---

## 1. `MAX_SOUNDS` — the record says 1280; the code says 1600 ⚠️ HIGH

**Record** (`buglog.json` bug-1183, 2026-07-28T20:24, and `cerebrum.md` §"MAX_SOUNDS ->
reliable-command overflow"):

> "Reverted `MAX_SOUNDS` to the known-good **1280**… To actually raise sound capacity later,
> `MAX_RELIABLE_COMMANDS` must go 512 → 1024 FIRST."

**Code**, `openmohaa-hzm/code/qcommon/q_shared.h:1742`:
```c
#define	MAX_SOUNDS			1600	// raised 512->1024->1280->1600 (HZM coop)
```
`openmohaa-hzm/code/qcommon/qcommon.h:215`:
```c
#define	MAX_RELIABLE_COMMANDS	1024		// max string commands buffered for restransmit
```

**Reading:** this is not a contradiction, it is a **stale record**. The prerequisite bug-1183
named (`MAX_RELIABLE_COMMANDS` 512→1024) was done, and `MAX_SOUNDS` was then raised to 1600. The
buglog was never updated.

**Consequences to act on:**
- Do **not** "restore" `MAX_SOUNDS` to 1280 on the strength of bug-1183.
- This is a cross-binary protocol change, and **the deployed set does not currently satisfy it** —
  see §0 above.
- The 1280 → 1600 re-raise has **no buglog entry of its own**. The source comment attributes it to
  "bug-1186", but `bug-1186` documents `MAX_SNAPSHOT_ENTITIES`. **The attribution in the source
  comment is wrong** — a grep-driven lookup will land on the wrong entry. (Same class of error:
  `q_shared.h:1680` credits the `MAX_MODELS` raise to "bug-866", which is the decapitation
  re-implementation; the `MAX_MODELS` work is **bug-892**.)
- The `MAX_RELIABLE_COMMANDS` raise costs `1024 × MAX_STRING_CHARS (2048)` = **2 MB per buffer**,
  per `client_t` **and** per client-side `clc` (comment at `qcommon.h:211-214`). That cost was
  never measured in any record. Measure it.

---

## 2. The `+180` roll on `maps/m1l1.scr` — documented as applied, absent from the file

**Record:** bug-1173 (2026-07-28T18:51) — "Added `local.a[2] = local.a[2] + 180` … immediately
after each of the 3 passenger `gettagangles` calls."

**Code:** `maps/m1l1.scr` has 15 `gettagangles` call sites (lines 750, 767, 781, 944, 1387, 1607,
1620, 1629, 1661, 1674, 1682, 1696, 1704, 1712, 1724). **Zero `+ 180` anywhere in the file.**

**Reading:** bug-1184 (2026-07-28T20:xx) explicitly reverted it — "it was based on a gimbal-lock
theory I never confirmed, the live result is contortion rather than a clean rotation." So the
buglog *is* internally consistent if read to the end. **The failure mode is reading bug-1173 and
stopping.**

**The general lesson, which is the reason this document exists:** a buglog is append-only and a
later entry can silently invalidate an earlier one. Always grep the buglog for *every* mention of a
file/symbol before acting on the first hit, and confirm against the file.

The underlying defect (mangled `2nd-ranger_private` actors on m1l1) is **still OPEN** — bug-1213.

---

## 3. `.wolf/anatomy.md` claims complete coverage; it indexes ~8%

`OPENWOLF.md` instructs: *"Check `.wolf/anatomy.md` BEFORE reading any file. It has a 2-3 line
description and token estimate for **every file** in the project."*

Measured: `anatomy.md` has **141** entries. The mod tree alone holds **479** `.scr` files (268 of
them under `maps/`, 96 under `coop_mod/`), and the workspace holds 1,667+ source files overall.

**Reading:** anatomy.md is a partial index, not a manifest. A file's absence from it means nothing.
Do not skip a `Grep` because anatomy.md is silent. (cerebrum 2026-07-02 also records that
anatomy.md **regenerates and wipes hand-edited prose** — do not invest in editing it.)

---

## 4. `USE_RENDERER_DLOPEN` — source default OFF, this build ON

`openmohaa-hzm/CMakeLists.txt:17` declares the option with default **`OFF`**.
`.cmake/CMakeCache.txt` has `USE_RENDERER_DLOPEN:BOOL=ON`.

**Reading:** the cache is what this build uses, so cerebrum's "renderers are separate DLLs" is
correct **for this configured build tree**. If the `.cmake` directory is ever regenerated from
scratch without passing `-DUSE_RENDERER_DLOPEN=ON`, renderer changes will silently start linking
into `openmohaa.exe` and every "deploy `renderer_opengl1.dll`" step becomes a no-op.

---

## 5. `MAX_ENTITIES` (gl1 renderer) — the argument to raise it was won; the raise is not in

`cerebrum` (2026-07-28, bug-1437-adjacent) records: *"`MAX_ENTITIES` (gl1) was stuck at 1023 with
a comment claiming it can't be increased without changing drawsurf bit packing — independently
verified FALSE."*

**Code:** `code/renderercommon/new/tr_types_new.h:33` — `#define MAX_ENTITIES 1023`.

**Reading:** bug-1172 reverted it (4095→1023) as emergency remediation when `build.ps1` carried
sandbox engine changes onto the real install. The *analysis* stands; the *change* does not exist.
Treat as PLANNED, not shipped.

---

## 6. `build.ps1` always deploys engine binaries to the real GOG install ⚠️ ACTIVE FOOTGUN

`build.ps1:132-150` unconditionally copies `cgame.dll` and `renderer_opengl1.dll` from `.cmake/`
to `G:\GOG\…\` on **every** run, regardless of whether the invocation was mod-content-only.

`G:\mohaa-gl2\maintt` is a **junction to the same real GOG `maintt`**, so mod *content* is shared
between sandbox and play install by design — that part is fine. The hazard is engine binaries.

**Rule:** before any `build.ps1` run during gl2 or engine experimentation, check what the current
`.cmake` output for those two DLLs contains. The real danger is narrower than "any engine change":
only **cross-binary protocol constants** (`MAX_SOUNDS`, `MAX_MODELS`, `MAX_WEAPONS`,
`GENTITYNUM_BITS`, netfield widths) can corrupt a mixed set. Renderer-local constants cannot.
(bug-1172)

`build.ps1` is currently **modified and uncommitted** (1 line).

---

## 7. `CLAUDE.md` staleness

`CLAUDE.md` remains broadly correct on architecture and the parse-killer list. Where it is behind:

| CLAUDE.md says | Current truth |
|---|---|
| Key script files table lists 11 `coop_mod` files | There are **96** `.scr` in `coop_mod/` |
| Key cvars table lists 8 | The mod registers hundreds (`coop_*`, `cg_*`, `r_pp*`); `autoexec.cfg` alone is 950+ lines |
| Nothing about `developer 1` being mandatory | It gates **all** script prints and compile errors (bug-911) — the single most expensive omission |
| Nothing about the gl1/gl2 split | gl1 ships; gl2 is a sandbox at `G:\mohaa-gl2` |
| Parse-killer list is 4 items | The verified list is ~10 — see [10-script-conventions.md](10-script-conventions.md) |

`CLAUDE.md`'s own correction that "`spawn` with inline keyvalues is fine — an earlier note calling
it a parse killer was wrong" is confirmed (192 working occurrences).

---

## 7b. A sibling document's finding that did NOT reproduce (bug-909 append sites)

[open_defects.md](open_defects.md) §D-4 reports *"5 unguarded `arr[arr.size + 1]` append sites remain
in `coop_mod/`"* — `aihandler.scr:521`, `eventsystem.scr:95`, `itemhandler.scr:1467`, `:1471`,
`:1908` — each said to silently drop its first element if the array is empty (the bug-909 idiom).

**Checked all of them 2026-07-29. The finding does not hold.** Every named site is guarded, just not
by the clamp the audit was grepping for:

| Site | Guard actually present |
|---|---|
| `eventsystem.scr:95` | Wrapped in an explicit emptiness branch — `if (!level.coop_eventNameList) { [1] = … } else { [size+1] = … }` (`:91-96`) |
| `itemhandler.scr:1467`, `:1471` | `local.weaponArray[1] = NIL` seeds index 1 at `:1464`, immediately above |
| `loadout.scr` (108 sites, not flagged but the largest cluster) | `level.coop_weaponLoadout[1] = …` seeds index 1 at `:16`, before every `case` branch |

There are **111** `.size + 1` append sites in `coop_mod/` in total. Two carry the explicit bug-909
clamp (`itemhandler.scr:1687`); the rest are covered by a preceding index-1 seed or an emptiness
branch.

**Two lessons, and they are the point of this whole document:**
1. **A grep for the *fix* is not a test for the *bug*.** The audit searched for the clamp comment
   and treated its absence as exposure. The idiom is safe whenever the array is non-empty at that
   line, which a seed one line above guarantees.
2. **This document set is not exempt from its own rule.** Two independent passes over the same
   sources, run the same day, produced one confirmed shared finding (the `m1l1` revert), one where
   the sibling was *more* complete than this file (the `MAX_SOUNDS` attribution error, now merged
   into §1), and one that was simply wrong. **Verify against code before acting on anything here,
   including this file.**

---

## 8. Uncommitted-work exposure

| Repo | HEAD | Dirty files | What is only in the working tree |
|---|---|---|---|
| `openmohaa-hzm` | `819a6e93` (2026-07-23) | **139** | headshot gore chain, entity-1023 fix, `MAX_SOUNDS 1600`, `MAX_RELIABLE_COMMANDS 1024`, `MAX_CONFIGSTRINGS 8192`, 13-bit `frameInfo`, all gl2 work, font pipeline, `coop_unsponge` |
| `hzm-mohaa-coop-mod` | `f10ac19` (v1.1.54) | **146** | v1.1.55 content, gore skins, AI dialogue, weather typing, armory/helmet fixes |
| `C:\mohaa-coop-dev` | `216f7ca` (manifest 1.1.55) | 1 (`build.ps1`) | — |

This is not a code/record disagreement, but it is the same class of hazard: **the record (git)
does not describe the artefact (the tree)**. Six days of engine work has no restore point.

---

## 9. Two `.wolf` records that destroyed themselves — treat the logs as fragile

- **2026-07-27 00:58**: `.wolf/hooks/post-write.js` `autoDetectBugFix()` rewrote `buglog.json`
  with its own `{version,bugs}` schema and destroyed ~1147 entries. `readJSON` returns a fallback
  on *any* parse failure, then `writeJSON` rewrites the whole file — one transient read failure =
  total loss. **523 entries were reconstructed** from ~1.2 GB of session transcripts. Immutable
  copy: `.wolf/buglog.json.recovered_bak`.
- **How much was actually lost is UNRESOLVED.** `cerebrum` asserts "637 numeric ids in range remain
  lost". The parallel buglog audit ([open_defects.md](open_defects.md) §D-6) counts ~632 unassigned
  ids in `bug-1..bug-1222` and concludes the opposite — that sessions simply **guessed** at the next
  number and the gaps were never assigned. Both are inferences from the same gap count, and neither
  was demonstrated. **Do not treat a missing id as proof of loss, or as proof of nothing.** What *is*
  established: the clobber was real, and 523 entries had to be rebuilt from transcripts.
- `buglog.json` is **git-ignored** by the root `/*` rule. It has no version control. The dated
  `.bak_*` files in `.wolf/` are the only history.
- **Bug ids collide** when workflows run concurrently. Re-read the file and take
  `max(numeric ids)+1` immediately before writing, then re-check after. Open with
  `encoding='utf-8'` — the file has non-ASCII content and `json.load(open(...))` fails on
  Windows cp1252.

**Practical consequences:**
- The current ~639 entries are *not* a complete history, and the file is **live** — it grew from 634
  to 639 during this audit. Any ledger built from it is a snapshot. **Append, never rewrite.**
- **The buglog has no supersession field.** That is the structural defect behind the `m1l1` case in
  §2 — bug-1184 invalidates bug-1173 with nothing linking them but prose. Any successor format needs
  `status` and `superseded_by` as first-class fields.
- The one structured status field that existed, `fix_verified`, appears on exactly **17** entries,
  all from late June, and was then abandoned. Every later status claim is prose buried in the `fix`
  field — which is precisely why SHIPPED and SHIPPED-VERIFIED became indistinguishable and why this
  documentation set had to be written.
