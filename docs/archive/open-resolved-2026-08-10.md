# Resolved / non-defect items retired from docs/OPEN.md (2026-08-10)

Moved out to stay under the 45 KB ceiling. Neither is an open defect: the first is struck through
and resolved, the second was diagnosed as a harness artifact rather than a mod bug.

### ~~m5l3 will not hand off to the next map~~ — LIKELY RESOLVED by bug-1498
Was: measured fine (105/109) but reloaded itself with no script marker of any kind - "whatever
issues the `map` command is outside the coop script layer" was the standing theory. That theory
was right: `Player::Respawn` (player.cpp:2903) took the SP branch and issued a silent engine
`restart` whenever `g_gametype` read 0 during one of `changeGameType`'s live-cvar windows - no
log line, indistinguishable from "something outside the script layer." Fixed 2026-08-06 (guard
on `game.maxclients>1`, prints `COV RESPAWN_SP_SUPPRESSED`). m5l3 measured 109/109 clean on the
first run after the fix, with `RESPAWN_SP_SUPPRESSED` firing 6 times across the session - the
race was real and is now caught rather than silently reloading. Re-verify on a normal (non-sweep)
launch before fully closing.

### t2l1 / t2l3: sweep-harness auto-join, not a mod defect (2026-08-06)
Both set `level.coop_physicsOff=1` before their spawn gate, and the walker declines to force-join
while that flag is set, so sweep clients sit spectator until its patience timeout. **The mod's real
join path (`coop_mod/player.scr:874`, auto-join on `primaryfireheld`) is not gated on that flag at
all.** Still unconfirmed: whether a human holding fire during the black-screen lock joins on these
two maps - the one successful live join observed was on t2l4, which has no `physicsOff` lock.
Test: relaunch at t2l1 or t2l3 and hold fire the instant the screen goes black.

