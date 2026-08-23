# Fix: e3l1 "Command overflow. Possible infinite loop in thread" (TriggerOnce / triggerthread)

Date: 2026-06-24. Scope: source edits to `hzm-mohaa-coop-mod/maps/e3l1/Courtyard.scr` only.
No pk3 rebuild, no game launch, no GOG files touched. ASCII / no BOM / no stray tokens.

## Symptom
During the coop maptest, ~73 seconds into e3l1, the engine logged:

```
Game (Event: 'triggerthread', Object: 'TriggerOnce') : Command overflow. Possible infinite loop in thread.
```

Non-fatal: the engine aborted that one thread and the game continued, but it is a real
no-yield infinite loop.

## The offending loop (root cause)
File: `maps/e3l1/Courtyard.scr`
Thread: `StopTheFakeShooting` — set as the trigger thread on the TriggerOnce
`$endguysfiretrigger` at `Courtyard.scr:88`:

```
$endguysfiretrigger setthread StopTheFakeShooting
```

That object is the "TriggerOnce" named in the log; the event `triggerthread` is exactly the
callback fired by `setthread` when the trigger is touched. The trigger fires mid-level when
players reach the courtyard, which lines up with the ~73s mark.

Inside `StopTheFakeShooting`, three loops (pre-fix lines 102, 114, 126) targeted the coop
"closest player" helper but DROPPED the return value:

```
local.player = NIL
while(!local.player){
    exec coop_mod/replace.scr::player_closestTo $chasetruckpassenger[local.i]   // result discarded
}
```

`coop_mod/replace.scr::player_closestTo` returns the player via `}end local.playerReturn`
(replace.scr:371). The correct pattern (used everywhere else, e.g. Courtyard.scr:299
`local.player = exec ...player_random`, BritHQ.scr:209, replace.scr:649/672/688) is to ASSIGN
the result: `local.player = exec coop_mod/replace.scr::player_closestTo ...`.

Because the result was never assigned, `local.player` stayed NIL, so `while(!local.player)`
was always true. The loop body contained NO `waitframe`/`wait`/blocking call, so it re-ran the
helper thousands of times within a single server frame -> the engine's per-frame command budget
overflowed and it aborted the thread. This is the same class of bug as the motionblend.scr fix
(a `while` whose body returns/continues instantly with no waitframe).

There are three instances, one per enemy group: `$chasetruckpassenger`, `$guybehindcar`,
`$precourtyardguys`. All three are reached in the single `StopTheFakeShooting` invocation, so the
first one to run (`$chasetruckpassenger`, if that array is populated) is the one that overflows.

## The fix
For each of the three loops, (a) assign the helper's return into `local.player` so the loop can
actually terminate once a valid player is found, and (b) add a `waitframe` inside the loop body
so it yields every iteration and can never overflow even if no valid player exists for a moment
(e.g. all players momentarily dead/respawning during the maptest). Intent unchanged: each enemy
still ends up running to / targeting the closest active player.

Fixed lines (post-fix `Courtyard.scr`):
- 102-105 (`$chasetruckpassenger`)
- 115-118 (`$guybehindcar`)
- 128-131 (`$precourtyardguys`)

Each now reads:
```
while(!local.player){
    local.player = exec coop_mod/replace.scr::player_closestTo $<group>[local.i]
    waitframe
}
```

Parse hygiene: ASCII only, no BOM, no em-dash, no compound &&/|| across lines, no bare negative
in parens; brace/paren balance of `StopTheFakeShooting` verified unchanged.

## Other loops reviewed (NOT changed)
The two other trigger-set threads and the remaining `while(!local.player)` loops in e3l1 are
correctly formed and were left alone:
- `Intro.scr:284` `$CoolGun setthread CoolGunPickup` — body has no unbounded loop (it execs the
  pickup helper once, then `self remove`). Safe.
- `Courtyard.scr:298` (`StealthPositionSnipers`) — `local.player = exec ...player_random` (assigned),
  and `player_random` always returns a player once one exists. Acceptable; not the trigger thread.
- `BritHQ.scr:208` — `local.player = waitexec global/DistanceUse.scr ...` (assigned + waitexec
  blocks each iteration). Safe.
- `AfterSnipers.scr:105` and `:430` — `while(!local.player)` bodies contain `wait 1`, so they yield.
  Safe.

The single root cause of the reported overflow was the three unassigned, no-waitframe
`player_closestTo` loops in `StopTheFakeShooting`; all three are now fixed.
