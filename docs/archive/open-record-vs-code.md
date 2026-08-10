# Record-vs-code discrepancies (archived from OPEN.md, 2026-08-08)

Moved to keep OPEN.md under its ceiling. These are documentation corrections, not open
defects - the code is authoritative in every case below.

## Record-vs-code discrepancies

Full detail and the corrections in [90-folklore.md](90-folklore.md). The ones that still matter:

| Discrepancy | Resolution |
|---|---|
| **`main.scr:134`'s inline comment says the Director defaults OFF** | It is ON (`autoexec.cfg:381`). **Fix the comment** — a future session will trust it. |
| **`q_shared.h:1680` credits `MAX_MODELS` 1024→2048 to bug-866** | The actual work is **bug-892**; bug-866 is the decapitation re-implementation. Cosmetic, but it misleads a grep-driven lookup. |
| **`blueprint.scr:5-7` says "INERT UNTIL WIRED: nothing threads into this file yet"** | It has **22** call sites. A session reading this header would wrongly conclude bug-1001's placement path was never wired. |
| **`actor.h:306`'s `MAX_BODYQUEUE` comment says "MAX_GENTITIES 1024"** | It is 2048. |
| **`hzm_cvars.txt:11` documents `coop_lmsLifes`** | Live cvar is `coop_lmsLives`. **This ships to players** — anyone following it sets a dead cvar and LMS silently stays off. (`main.scr:1568`'s own trailing comment reads *"cvar from coop_lmsLives to coop_lmsLives"* — a botched rename note.) |
| **`MEMORY.md`'s index flags "18 xw guns don't hip-fire" as OPEN** | Its own topic file records it SOLVED the same day. |
| **`MEMORY.md`'s index labels the m1l2a crash "ACTIVE, next = ASan"** | Its own topic file says "VERIFIED FIXED … reached CS_ACTIVE". |
| **`reactive_difficulty_plan.md` says "PLANNED, DO NOT BUILD until the user answers 8 decisions"** | `coop_mod/director.scr` exists, is threaded unconditionally, and is enabled by default. **Someone must decide whether those 8 decisions were ever answered.** |
| **`KNOWN_WORKING_STATE.md` forbids `spawn` with inline keyvalues** | 192 working occurrences including `main.scr`. See [SOURCE_OF_TRUTH.md § Maintaining](SOURCE_OF_TRUTH.md#6-maintaining-this). |

**Structural, not per-item:** `.wolf/buglog.json` has no supersession field, so a later entry can never
signal it undid an earlier one. See [TRAPS.md § T11](TRAPS.md#t11) for the full mechanism and the
fix that works (correct the original entry in place, as done tonight for bug-1473/1474/1480 etc.).

**Also unresolved:** how much of `buglog.json` was destroyed by the 2026-07-27 post-write hook clobber
vs never assigned — two audits infer ~632-637 lost/unassigned ids from the same gap count, neither
demonstrated. Established: 523 entries needed rebuilding from transcripts, all 8 `.bak` snapshots
contain zero entries absent from the current file, and 28 bug ids cited in source comments (incl.
bug-237, 239, 241) have no buglog entry — for those the code comment is the only record.

---

<a name="tooling-lost"></a>