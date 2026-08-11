# TRAPS T16 (archived detail) — a failsafe that escapes a hang by calling the same hang

Moved out of `docs/TRAPS.md` on 2026-08-10 to stay under its size ceiling. The *rule* and the
two engine facts remain in TRAPS; this file keeps the worked example and the evidence.

## T16 — A failsafe that escapes a hang by calling code containing the same hang

**Bugs:** 1361 → 1366 (e3l4 supply/delivery), same shape as the AB41 and truck-unload failsafes.

A timeout around a blocking wait is only as good as the recovery path. The e3l4 supply failsafe bounded
`while (level.gotSupplies < 2)` at 45s and then recovered by calling
`global/jeepanim.scr::PassengerGetInJeep` — which **opens with `runto` + `waittill movedone`**. The
actor's whole problem was that it had no nav path, so the recovery blocked exactly where the original
did, one line before the `level.gotSupplies = 2` that would have released the mission. The soft-lock
moved rather than closing, and the second report looked like the first fix simply hadn't worked.

**Rule: a recovery path must contain no wait that the failure mode can block.** For actors that means
no `runto`/`walkto`/`waittill movedone`/`waittill turndone`/`waittill animdone` and no unbounded
`while (vector_length(...) > N)` distance loop. Seat/position them directly instead — take the **tail**
of the vanilla routine (everything after its movement), which is still the retail recipe minus the walk.

**Two engine facts make actor waits unsafe** (verified in source, bug-1368): `Unregister(STRING_TURNDONE)`
exists in exactly one place, `Actor::IdleTurn` (`actor.cpp:5032`), reached only from the anim/idle
thinks — no runner think calls it, so a failed `runto` pins the actor in `THINK_RUNNER` and any
`waittill turndone` requested there blocks **forever**. `waittill movedone` is safe: `CheckUnregister`
(`actor.cpp:7793`) fires it even on `parm.movefail`. So **`runto` → `turndone` hangs; `runto` →
`movedone` does not**, and every `while (vector_length(...) > N){ waitframe }` after a `runto` is
unbounded by construction. Ritual knew this — `e3l4/Bunker1.scr` has a commented-out
`waittill turndone` replaced by `wait 0.5`, with the identical live twin 30 lines below.

**Never invent an exit/placement offset when the model carries an authored one.** The e3l4 jeep
dismount took three attempts: `origin + (0 0 80)` (the roof — copied from `t2l2.scr:1468`, safe
there only because that ride has ENDED), a 96-unit lateral guess (lands inside bunker geometry),
then finally `gettagposition "passenger_enter"` — the tag the artist placed for exactly this, on
exactly that vehicle, walkable by construction and already used by the boarding code. Vehicles
carry `driver_enter` / `passenger_enter` / `*_seat` tags. An offset that works at one stop is a
guess about free space at every other stop. (bugs 1367, 1370)

**Tell:** the same user report twice, with a failsafe log line in between. Grep the recovery path
for `waittill` before shipping it, and check the *next* stage for the same shape — e3l4 had a
second identical spin in `deliverSupplies`.

---

<a name="t18"></a>
## T18 — The HUD: a slot that fades, one already taken, a prompt nobody clears

Three failures, one subsystem, **nine sightings.** All cheap to avoid; none logs.

**1. A slot below 100 fades out exactly when the player needs to read it.**
`cg_drawtools.cpp:651-653` multiplies alpha by `s_hudFadeAlpha` for **every slot below 100** when
the player is calm — and standing still holding a key *is* calm. **Six features:** the team-revive
HUD at 21-26, the blueprint ack, the XP micro popup, the cover and ammo prompts, and the Phase C
contain prompt. bug-1668 is the worked example: the XP was always awarded (96→106 by rcon),
only the popup was invisible — kill XP popped fine *because shooting keeps the HUD awake*, which is
what made it look revive-specific. **Anything a stationary player must read goes at ≥ 100.**

**2. The slot map rotted, and a literal grep does not detect it** (bug-1680).
`_research/hud_slot_map.md` was hand-maintained and drifted until it advertised **141-149 as free
when only 149 was left**, and showed no conflict for `objectives.scr`, which quietly owns
**135-142** and collides with both the DBNO revive channel and the XP micro popup. It hid because
several features **compute** the slot (`local.slot = 136 + local.line`), so grepping digits finds
135 and 142 and misses 136-141. **Sweep, don't read: `python docs\tools\hudslots.py`** — it lists
computed sites separately: *absence from the literal table is not evidence a slot is free*. Same
shape as [T11](#t11): the record was trusted over the code, and the record was a list.

**3. `ihuddraw` state persists on the client until someone overwrites that slot** (bug-1679).
Every transient prompt is torn down by the loop that drew it, so **any exit that loop does not
model leaves the text on screen permanently.** Reported case: the revive prompt is drawn on
*candidates* (any teammate in range and facing the body) while all four teardowns cleared only the
*reviver* and the *downed player* — two roles a candidate is not — so it stuck the instant the
patient resolved, with the `coop_revivePrompt` latch pinned at 1 so nothing cleared it later
either. Spectating was just the route the user noticed; a spectator passed the range and facing
tests too, because `isAlive` does not exclude one.
**Rule: write the teardown for every exit, including the ones you do not own** — dying, spectating,
the tracked entity vanishing — and register the slot in the backstop at
`player.scr::manageSpectator`, the one transition that provably ends all of them. Release the latch
flag there too, or the prompt returns believing it is still drawn.

