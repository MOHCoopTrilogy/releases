# ARCHIVED from docs/TRAPS.md on 2026-09-05

Moved to keep TRAPS.md under its 70 KB ceiling. Both rules still hold; the bug ids are the record.

<a name="t19"></a>
## T19 — A radius is a SPHERE, and hand-rolled distance is not trustworthy

**Bugs:** 1689, 1690. **Tell:** a proximity prompt fires on the floor below or through a ceiling - "the
Naxos text appears when you are downstairs underneath the room", "you get caught on the 2nd floor for his
dead body on the first".

**`vector_length` is a 3D distance**, so every "within N units" test is a sphere - almost never what is
meant in a building. **"Near" is a HORIZONTAL question plus a same-storey question, tested as both**: 2D
distance plus a vertical band (96u; a MOHAA storey is ~128). Three sites in one feature had it.

**Flatten both points to z=0 inside a vector literal and use `vector_length`** (locals inside a literal
are fine - `props.scr:407`, `tracescan.scr:79`), **not hand-rolled pythagoras**: a
`sqrt( (dx*dx) + (dy*dy) )` here returned **265.965 for two points 2013u apart**, twice across two
builds, while `dz` by plain subtraction was exactly right. No mechanism is claimed - only that
`vector_length` was right on every sample and the hand-rolled form was not on at least one.
`aimaneuver.scr:129` uses the same inline form, never checked. **And a range must be the right SIZE for
its job:** that feature's warning was drawn off the *action* prompt's 112u bash range, so it appeared
only once the player was already on top of the officer.

---

---

## Writing `.health` directly bypasses EVERY piece of damage feedback

`ent.health = ent.health - n` is not a quiet way to deal damage - it skips `Sentient::Damage`
entirely. No pain sound, no hit flash, no hitreact, and no `STAT_DAMAGEDIR`, the only field
`coop_dmgIndicator` reads. m3l3's church barrage did this, so damage arrived from nowhere: the
shells were audible, but nothing said you had been HIT, and the user reasonably called it random.

The floor is the second half. Clamping `health` to 1 after the subtraction makes the effect
non-lethal only in the narrowest sense - it never lands the kill, but pins the player at one hit
point so the next stray round does. That reads as the effect killing them, because it did. Put the
floor on the AMOUNT, at a survivable share of max health.

Deal damage with the real event and pass a direction (`vector_normalize(victim - source)`) like a
bullet does; `player.cpp` derives the indicator bearing from arg 5, the DIRECTION, not the position.
(bug-2015)

---

## Per-weapon TIK data: read the copy the ENGINE resolves, under the name it actually ships as

Two independent ways a per-weapon table reads the wrong thing.

**Which COPY.** Pak priority is main < mainta < maintt < the mod's own pk3s - **the LAST copy wins**. An
extractor that sweeps in that order and keeps the FIRST match ships Spearhead's values: a G43 authored at
1 degree of yaw got 16, and it reached the player's real aim on every shot. Resolve last-wins, and include
the mod's own `models/weapons`, which beat every pak. **Also strip trailing `//` before tokenizing a TIK
line** - at least one weapon carries an ACTIVE viewkick line with a commented-out alternative appended on
the SAME line, and a naive tokenizer reads straight through into the comment.

**Which NAME.** See [`item_name` suffixes](#itemname) - the same variant-naming trap, both halves.
