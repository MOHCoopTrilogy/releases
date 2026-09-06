# ARCHIVED from docs/OPEN.md on 2026-09-05 - m6l2a contain (bugs 1732-1737)

Moved to keep OPEN.md under its 50 KB ceiling; still open, still in buglog.json under those ids.

### m6l2a contain — bugs 1732-1737, deployed 2026-08-12

1732 / 1734 / 1735 / 1736 are **closed** — each exposed the next, verified in a three-contain run
(kill / let-survive / kill). Causes in buglog. Still open:

**1739 unverified — the stun's re-assertion has never once fired.** The re-hit that pulls a guard back
into pain is gated on `curHp > minHp`, `minHp` = 40% of health. That floor predates bug-1731's drop to
`coop_bustVulnHealth` 25: 40% of 25 is **10**, exactly where the bash's own 15 damage lands him — false
from the first tick, and `BUSTSTUN` prints a flat `hp=10.000` in *every* contain, including the ones
that looked right. The stun rode on one pain animation, holding only when the guard faced away
(`EnemyIsDisguised` = `hasDisguise && (isDisguised || !CanSeeEnemy)`). 1737 is intact and still needed:
it makes pain *start*, not *hold*. Absolute floor of 2 while dropped. Verify: hp **decreases**
(10→7→4→1) instead of sitting flat.

**1738 unverified.** One latch both kept the corpse rediscoverable *and* pinned `seers` at 1 forever,
so the loiter timer ran on with every witness dead — cover blew 6 s after the player contained the
investigator himself. Now a live per-tick count. Verify: silence the investigator, stay by the body,
expect `BUSTBODY nobody has eyes on the body any more` and no escalation.

**1733 partial.** `PAINDETACH` still fires on a same-frame double hit — gap **exactly 3.0** both times
regardless of real damage (400, 15): the stun's `hurt 3` racing a round, which `actorPainHandler`'s
exact-equality test can't tolerate. Bashed guards only; 1734 covers both paths, so it degrades.

**Bullet sponges no longer reproduce** — a full Thompson run, none seen, and no damage value was
changed. Probably fixed by 1733, not confirmed.

