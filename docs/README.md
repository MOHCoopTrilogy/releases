# HZM MOHAA Coop Mod — Source of Truth

**Built:** 2026-07-29. **Scope:** everything learned, fixed and added since day one, distilled from
`.wolf/cerebrum.md` (525 KB), `.wolf/memory.md` (1.29 MB), `.wolf/buglog.json` (634 entries), and
verified against the live source tree.

This set replaces the *navigation* role of `CLAUDE.md` (24 days stale), `.wolf/anatomy.md`
(indexes 141 of 1,667+ source files — ~8%), and the two append-only OpenWolf logs, which are past
readable size. `.wolf/buglog.json` remains authoritative for *individual bug detail* — it is
structured and keyed, and these documents cite it rather than duplicate it.

---

## Read in this order

### Core — the distilled knowledge (start here)

| # | Document | Read it when |
|---|---|---|
| 1 | [01-project-map.md](01-project-map.md) | You need the repo layout, build, deploy, run and test loop |
| 2 | [02-status-ledger.md](02-status-ledger.md) | You need to know what actually works, what was undone, what is broken |
| 3 | [03-record-vs-code.md](03-record-vs-code.md) | **Before trusting any record.** Where docs and code disagree, and why |
| 4 | [10-script-conventions.md](10-script-conventions.md) | Before writing or editing any `.scr` |
| 5 | [11-engine-conventions.md](11-engine-conventions.md) | Before touching C++, engine limits, or shipping a binary |
| 6 | [12-asset-conventions.md](12-asset-conventions.md) | Before touching UI (`.urc`), textures, sounds, `.tik`, fonts |
| 7 | [20-decisions.md](20-decisions.md) | You are about to redo a decision that was already made |
| 8 | [21-user-preferences.md](21-user-preferences.md) | Every session — how the user wants to be worked with |
| 9 | [90-folklore.md](90-folklore.md) | A "known fact" smells wrong and you want to check whether it was ever evidenced |

### Reference — generated inventories and the raw record

Built by parallel passes over the same sources. Use them to look things up; use the Core set to
understand them.

| Document | What it is |
|---|---|
| [SOT_01_TIMELINE.md](SOT_01_TIMELINE.md) | Chronology backbone from git history of all three repos + release manifests |
| [30-inventory-coop-subsystems.md](30-inventory-coop-subsystems.md) | Every `coop_mod/*.scr` with size, entry-point count, verbatim header comment |
| [31-inventory-coop-cvars.md](31-inventory-coop-cvars.md) | Every `coop_*` cvar: engine default vs cfg seed |
| [32-inventory-engine-cvars.md](32-inventory-engine-cvars.md) | Every `Cvar_Get` in the engine, with gl1/gl2 default conflicts called out |
| [33-inventory-build-deploy.md](33-inventory-build-deploy.md) | Line-anchored account of what `build.ps1` / `publish_release.ps1` actually do |
| [BUGLOG_INDEX.md](BUGLOG_INDEX.md) | Entry point for the buglog mining set below |
| [fix_ledger.md](fix_ledger.md) | All 639 buglog entries, one line each, chronological. Raw index |
| [open_defects.md](open_defects.md) | Buglog-derived OPEN / REVERTED / record-vs-code list |
| [recurring_traps.md](recurring_traps.md) | Defect classes that recurred under 2+ bug ids — the most expensive lessons |

> Where the Core set and a Reference file overlap (both cover reverts and code discrepancies), they
> were derived independently from the same sources and **agree** on the substantive findings —
> notably the `m1l1` `+180` revert and the `MAX_SOUNDS` staleness. Independent agreement is the
> point; treat a disagreement between them as a signal to go re-read the code.

---

## The status vocabulary (used throughout, exactly these five)

| Status | Means | How to spot it |
|---|---|---|
| **SHIPPED-VERIFIED** | In the code **and** confirmed working in play or by a measured probe | Buglog entry with a live-test result, or a user confirmation |
| **SHIPPED-UNVERIFIED** | In the code, never confirmed by a playtest | Buglog phrase "NOT YET VISUALLY VERIFIED", "untested", "awaiting user go" |
| **REVERTED** | Was done, then undone — **the highest-value entries** | Buglog "reverted", plus code confirming absence |
| **PLANNED** | Designed but not built | `_research/*.md`, memory-index "plan" entries, no matching code |
| **OPEN** | Known defect, no fix | Buglog "OPEN", "UNRESOLVED", "not yet identified" |

Anything that could not be anchored to a bug id, commit, or `file:line` is quarantined in
[90-folklore.md](90-folklore.md), not asserted here.

---

## ⚠️ Read this before shipping anything

**The deployed engine binaries do not currently match each other.** `openmohaa.exe` in the GOG root
is from 2026-07-21 and `game.dll` from 2026-07-24, while `cgame.dll` is from 2026-07-28 — spanning a
change to `MAX_CONFIGSTRINGS` (4096 → 8192), which sizes a struct `memcpy`'d whole across the
exe↔cgame boundary with no version guard, plus `GENTITYNUM_BITS` 10 → 11.

Full evidence and the mechanical fix: [03-record-vs-code.md §0](03-record-vs-code.md).

---

## The one rule that matters most

> **Where a record and the code disagree, the code wins — and the disagreement gets written down.**

This is not hypothetical. A `+180` roll correction on `maps/m1l1.scr` is documented in
`buglog.json` as applied (bug-1173). It is **not in the file** — bug-1184 reverted it a few hours
later. A session that read only bug-1173 would have "re-fixed" a correction that was already
proven wrong. Full case and the other live discrepancies: [03-record-vs-code.md](03-record-vs-code.md).

Corollary, learned the hard way and recorded in cerebrum (2026-06-29, weapon-weight): **before
(re)building any "planned / not built" feature, grep the actual code first.** The weapon-weight
sway was indexed as "PLAN (not built)" while a full `cg_weaponLag` block had been live in
`cg_view.c` for a day.

---

## Evidence conventions in these docs

- `bug-NNN` → an entry in `.wolf/buglog.json`. Look it up for the full root-cause/fix text.
- `path/file.ext:NNN` → verified against the working tree on 2026-07-29.
- `cerebrum <date>` → a dated entry in `.wolf/cerebrum.md` that is **not** independently
  code-verified. Treat as a strong lead, not proof.
- No anchor → it does not belong in these files. It is in [90-folklore.md](90-folklore.md).

## What these docs deliberately do not contain

- The per-action journal (`memory.md` is ~91% `| HH:MM | edited X |` lines). Discarded entirely.
- Per-bug reproduction detail. That is `buglog.json`'s job and it still does it well.
- Anything restated. The source logs repeat the same learning up to a dozen times; each appears
  here once, at its strongest formulation.
