<!-- GENERATED FILE - DO NOT EDIT.
     Produced by docs/tools/gen_public_pages.py from buglog.json, challenges.scr,
     the map scripts and the authored docs. Edits here are overwritten. -->

# Roadmap and known issues

What is planned, in progress, or known to be broken. This is generated from the project's open-work record, so it is the same list the developers work from - including the unflattering parts.

> This project is in **early alpha** and under heavy active development. If something here is not yet fixed, a bug report against it is still useful: it tells us it matters to someone.

## P0 — infrastructure, fix before feature work

- `renderer_opengl2.dll` has zero rollback points

## Defects with evidence

- e3l4: jeep passenger never completes the first supply run — INSTRUMENTED, cause open
- Pinned challenges: no in-mission pin surface
- m3l2: `SV_FindIndex overflow (max=1280)` ×243
- e2l2: 12× "applied to NULL listener"
- t2l2: 265 script errors on coop boot despite an A− static audit grade
- Phase C stealth contain (m2l2a) — shipped, mostly unverified
- m6l2a contain — bugs 1732-1737, deployed 2026-08-12
- ⚠️ m2l2a REGRESSION RISK — the attackplayer latch removal (bug-1700)
- `coop_stealthArmOnHurt` is dead code — and something else may be covering for it
- A hand-rolled distance returned a wrong value once and could not be reproduced
- objectives.scr's NEW OBJECTIVE toast collides with two live features
- Second vehicle-crew spawn path on t2l2 / t3l2 still unguarded
- Dedicated server segfaults on bare DM maps
- AI crouch posture stays disabled (crouch leg was the crasher); prone is BACK
- ET3 engine jink is built and dormant
- Airborne black-texture patch — 4th report in the same family

## gl2 open items

- Non-depth-writing surfaces cannot be fogged at all — the screen-space fog's structural gap
- The retail sky sources are 512×512
- `Z_TagMalloc` zero-size spam on the main menu
- Some bullet-hole decals render RED — deliberately not guessed at
- Invisible briefing NPC on e2l2
- Shimmer on thin decorative geometry (shadow acne)
- Bloom is a no-op at the shipped threshold
- Seven gl1 post-FX have no gl2 equivalent
- `r_globalFogDebug` is still `CVAR_TEMP`
- Diagnostic scaffolding not yet stripped

## Diagnostic pending — a probe exists, awaiting one boot

- m1l1 2nd-ranger_private actors render mangled
- Reload camera dip never visible
- Mine detector possibly still lost after DBNO revive

## Config

- Nine post-FX cvars are menu-wired AND force-reset by `autoexec.cfg` every launch
- 144 `coop_*` cvars are seeded nowhere
- The bug-595 0-byte `omconfig.cfg` decoy is still on disk
- `build.ps1`'s `_research` exclusion is uncommitted

## Sweep-blocking maps (2026-08-06) - need dedicated sessions

- e3l4 AI spawner threads die on AISpawnPoint/PathNode (bug-1471, OPEN)
- Unwired challenges: 25 still have no producer (bugs 1596-1598, OPEN)

## m2l2a stealth - state after Phase A (2026-08-10)

- Scripted-conversation guard sweep (TRAPS: waittill outranges its guard)

