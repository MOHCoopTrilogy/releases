<!-- GENERATED FILE - DO NOT EDIT.
     Produced by docs/tools/gen_public_pages.py from buglog.json, challenges.scr,
     the map scripts and the authored docs. Edits here are overwritten. -->

# Roadmap and known issues

What is planned, in progress, or known to be broken. This is generated from the project's open-work record, so it is the same list the developers work from - including the unflattering parts.

> This project is in **early alpha** and under heavy active development. If something here is not yet fixed, a bug report against it is still useful: it tells us it matters to someone.

## P0 — infrastructure, fix before feature work

- `renderer_opengl2.dll` rollback is a manual convention (the "zero backups" claim was a regex miss)

## Defects with evidence

- 2026-09-09 m4l3 + engine round — four fixes shipped, none seen in play yet
- e1l2 dedicated map-checksum residual (bug-2585)
- global/spotlight.scr: 5 Script Errors per spotlight per map load, and a gunner that never fires
- e3l4: jeep supply run + AISpawnPoint/PathNode — RESOLVED (verified 2026-09-15), playtest-nice-to-have
- Pinned challenges: no in-mission pin surface
- e2l2: 12× "applied to NULL listener" — UNCERTAIN (may be a decoy-log phantom)
- t2l2: 265 boot errors — RESOLVED (verified 2026-09-15)
- Phase C stealth contain (m2l2a) — shipped, mostly unverified
- m2l2a attackplayer-latch removal (bug-1700) — CLOSED, user-verified
- `coop_stealthArmOnHurt` is dead code — and something else may be covering for it
- A hand-rolled distance returned a wrong value once and could not be reproduced
- objectives.scr's NEW OBJECTIVE toast collides with two live features
- Second vehicle-crew spawn path on t2l2 / t3l2 still unguarded
- Dedicated server segfaults on bare DM maps
- AI crouch posture stays disabled (crouch leg was the crasher); prone is BACK
- ET3 engine jink is built and dormant
- Airborne black-texture patch — 4th report in the same family

## gl2 open items

- Non-depth-writing surfaces can't be fogged — RESOLVED (doc stale)
- The retail sky sources are 512×512
- `Z_TagMalloc` zero-size spam on the main menu
- Bullet-hole decals render RED — RESOLVED (doc stale)
- Invisible briefing NPC on e2l2 — likely fixed, PLAYTEST-GATED
- Shimmer on thin geometry (shadow acne) — RESOLVED (doc stale)
- Bloom flat haze + the seven gl1 post-FX ports — RESOLVED (doc stale)
- `r_globalFogDebug` is still `CVAR_TEMP`
- Diagnostic scaffolding not yet stripped

## Diagnostic pending — a probe exists, awaiting one boot

- m1l1 2nd-ranger_private actors render mangled — RESOLVED (doc stale)
- Reload camera dip never visible — RESOLVED (superseded)
- Mine detector after DBNO revive — RESOLVED (doc stale)

## Awaiting playtest — `SHIPPED-UNVERIFIED`

- Awaiting runtime verification after the next deploy (2026-09-13)

## Config

- Nine post-FX cvars were menu-wired AND force-reset by `autoexec.cfg` every launch
- `coop_*` cvars seeded nowhere — the consequential count is ~278 (not 144)
- The bug-595 0-byte `omconfig.cfg` decoy — REMOVED (verified 2026-09-15)

## Sweep-blocking maps (2026-08-06) - RESOLVED, sweep-harness confirm outstanding

- e3l4 AI spawner threads die on AISpawnPoint/PathNode (bug-1471, OPEN)
- Unwired challenges — CLOSED (every challenge now has a producer)

