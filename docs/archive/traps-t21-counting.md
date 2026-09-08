# T21 - the two ways a map counts enemies

Pruned out of `TRAPS.md` on 2026-09-08 for space. The rule that matters - an actor moved to
your team can NEVER be killed by the player, so the softlock is absolute - stays in T21.

Maps count enemies in **two unrelated ways**, and a fix for one does nothing for the other:

| mechanism | example | repaired by |
|---|---|---|
| an ARRAY of living axis | `level.coop_actorArray["german"]` | `aihandler.scr::coop_moveActorToTeam` (bug-2088) |
| a PER-ACTOR `waittill death` | `m3l1b.scr:1671-1697`, one watcher per defender | `coop_countasdead` (bug-2091) |

bug-2088 was believed to cover both and shipped untested; it could not, because the second kind
never counts anything — it *waits on a body to die*. Recruiting that body removes it.
