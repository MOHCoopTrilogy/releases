# TRAPS - pruned 2026-11-10 (moved verbatim from docs/TRAPS.md to make room for the spawn un-mute trap)

## T11 bullets (condensed 2026-11-10)

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


## T11 REVERTED-classification bullet (doc-maintenance, moved 2026-11-10)

- **When classifying REVERTED, separate "it broke" from "the user changed their mind"** - only the former
  is a lesson; bug-787 reversed a design at the user's request.


## T10 bot pace / steering narrative (moved 2026-11-10)

**Bots are tuned at a PACE - `sv_dmspeedmult`** (autoexec 0.6; engine default 1.1). v1.8.8-1.9.1 dropped autoexec
(bug-2908), so every Push tune ran at 1.1 and regressed at 0.6: m4l2 stuck 14% vs 1-4%, all at the lift whose
timing assumed 1.1 (bug-2912). Soak at the shipped pace - check SPEEDPROBE `dm=`. **A steering state machine must
die with its bot**: the lift protocol outlived a death and steered the respawn straight at the lift across the
map - reset on spawn, drop when far.
## T10 bot DECISION-vs-ACT paragraph (condensed 2026-11-10)

**A bot feature that logs its DECISION proves nothing - log the ACT** (bugs 2875-2877): `CheckValidWeapon`
re-drew the gun in the no-weapon frame of every grenade switch (no bot grenade ever flew); `TurnThink` stops
turning inside 20 deg of target (exact aim needs `SetPrecise`); a bot's eye is the `usereyes_t` offset it
sends (lean was cosmetic). Log the outcome (`nadeloose`, BOTPROBE `cov=`).
