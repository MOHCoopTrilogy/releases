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



---

<!-- moved out of docs/OPEN.md 2026-08-10 to stay under the size ceiling -->

### ~~`global/vehicle_warning.scr`: `$player` array-casts~~ — FIXED 2026-08-06
`FIXED` · *bug-1473; `gags/t3l1_enemyspawn.scr`* — was the **largest single defect in the trilogy**:
12,690 errors, 48% of all 26,230 script errors the 4-player sweep recorded. Fixed in the CALLER rather
than by extracting the retail global: all six bare-`$player` sites in `TankLookForPlayer` /
`TruckLookForPlayer` now resolve one real player via `replace.scr::player_closestTo self` and guard
NULL **and** NIL. Consequence removed: enemy tanks and trucks never detected a player and never
stopped. Deployed and hash-verified in the pk3. *Left open:* a previous sweep found this and even
prescribed the fix, and it still sat `OPEN` — findings need an owner, not just an entry.



<!-- moved out of docs/OPEN.md 2026-08-10 -->

### m3l3 ground seam — fixed, never shipped, never re-examined
`OPEN` · *`_session_handoff.md`; `zzzzzzzz_hd_groundfix.pk3` built 2026-07-27 18:02; not in `manifests/latest.json`*
Not a wrap seam (which is why an earlier 275-texture pass found nothing) and not a scale mismatch —
it is a cart road with dark grass verges **baked into the top/bottom edges**, so tiling repeats the
verges as hard parallel stripes. Row-band measurement: vanilla 512 spread 59.2/σ15.0, HD world 1024
spread 72.1/σ20.0 (**the HD upscale amplified the verge ~22%**), groundfix 1024 spread 59.7/σ14.9.
⭐ **Critical timing detail: the groundfix pak was built 19 minutes AFTER the screenshot later cited as
"seamfix didn't resolve it" — so no post-fix look exists.** Confirmed gl1, i.e. content not a gl2
defect. **Next action is one fresh look at that courtyard** before any further texture or UV work.

---

<a name="gl2"></a>