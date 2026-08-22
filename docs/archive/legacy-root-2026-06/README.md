# Legacy root documentation — frozen 2026-08-22

62 markdown files that used to sit loose in `C:\mohaa-coop-dev\`, written 2026-06-19 to
2026-06-25 (plus two July stragglers). They are **frozen history**. Do not read them to
answer a question about how the project works today, and do not add to them.

## Why they were moved

They were the ancestors of the current doc set, written before it existed — and they are two
months stale. Two of them still carried **active instructions to future sessions**:

- `KNOWN_WORKING_STATE.md` — line 2 reads *"Update this file at the START of every session
  before touching any code."* Its content stops at 2026-06-21.
- `coop_menu_modernization_proposal.md` — similar read-me-first framing.

That is exactly the failure mode `.wolf/anatomy.md` was frozen for: a stale file that tells
sessions to trust it, so they do, and act on facts that stopped being true. Leaving them in
the repo root — the first place anyone looks — made that likely rather than possible.

## Where their content lives now

| Then | Now |
|---|---|
| `KNOWN_WORKING_STATE.md` feature inventory | `docs/FEATURES.md` (+ status per feature) |
| `fix_*.md` post-mortems (12 files) | `.wolf/buglog.json` — 1,388 keyed entries, searchable |
| `*_research.md` / `*_audit.md` | `docs/TRAPS.md`, `docs/DECISIONS.md`, or superseded outright |
| `COOP_CONVERSION_MASTER.md`, `hzm_coop_framework_guide.md` | `docs/SOURCE_OF_TRUTH.md` + `docs/generated/SUBSYSTEMS.md` |
| per-map notes and trackers | `docs/generated/` (swept from source, cannot drift) |
| `_session_handoff.md`, `_phillips_dossier.md` | one-off session artifacts, no successor needed |

## Status

**Untracked in git**, as they always were — only `README.md` at the repo root was ever
tracked. They are kept because a few contain reasoning worth finding again (the Frontline
soundtrack mapping, the objective interaction audit, the overhead-marker replication
research). Nothing here is load-bearing: if this directory vanished, no current behaviour
would become unexplainable.

If you find something here that is still true and still matters, **promote it** to the
authored docs rather than citing this directory — that is the rule that produced the freeze
(see `docs/21-user-preferences.md`, "Search buglog.json BEFORE theorising").
