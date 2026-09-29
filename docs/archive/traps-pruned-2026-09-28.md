# TRAPS archive - pruned 2026-09-28

Full text of two TRAPS.md paragraphs condensed on 2026-09-28 to make room for the m3l3 clip-box traps
(bug-3210, T9). The rules stayed in TRAPS.md; this is the narrative.

## T12 - two engine events sharing a script command name (bug-2064)

**And one level down again: two ENGINE EVENTS sharing a script command name** (bug-2064, the most
expensive of the three). `notarget` is declared **twice** as `EV_NORMAL` - `Entity::NoTarget`
(SETS from its argument) and `Player::NoTargetCheat` (ignores the argument, **XORs** the flag) -
and `ScriptMaster` keeps one **name -> eventnum entry, last write wins** (`scriptmaster.cpp:616`)
over an unordered container. **Which handler a script command reaches is therefore a build
detail, not a decision.** For players the cheat won, turning every `player notarget 1` into a
flip; it read as *intermittent* across five sessions because the outcome was call **parity**.
**Grep the engine for a second `Event` with the same command string before trusting a script
command's signature**, and when there is one make BOTH handlers agree for BOTH call shapes
(argument = set, none = toggle) rather than betting on the lookup. Same tell as `.gun`
(bug-2046) and `enableEnemy` (bug-2034): *the command name is not the contract, the `Event`
declaration is.*

## T16 - a scripted conversation strands when a `waittill` outranges its guard (bug-1579)

**A scripted conversation strands when a `waittill` outranges its guard** (bug-1579) - retail chatter
helpers assume the talkers are alive and idle, and coop breaks all three assumptions. (a) A `waittill`
**outside** the guard that started the anim/say waits forever, because no anim was issued: wait only on
an actor you actually animated, recorded in a local, and never re-test the condition. (b) `isalive` on a
NULL entity throws and the thrown statement is SKIPPED, so the guard vanishes and its body runs
unguarded - test `!= NULL` first and separately. (c) `thinkstate != "attack"` is not "idle": a CURIOUS /
GRENADE / PAIN actor overrides the scripted idle anim, so gate on `== idle` (`anim` runs at
`THINKLEVEL_IDLE` via `Actor::PlayAnimation` -> `SetThinkIdle(THINK_ANIM)`, `actor.cpp:10819`; there is
no `THINKSTATE_ANIM`). **Silence the LINE, never abort the THREAD** - the tail of these labels holds the
RELEASE (`runto`, `enable_ai`, `type_disguise`) that hands actors back to normal AI, and ending early
leaves them frozen, dying on their feet with no death animation. Safe exception: a dead-end label
nothing waits on (`M1L3c` radio room). Sites: bug-1579; helper `replace.scr::convOk`.
