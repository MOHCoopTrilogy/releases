# TRAPS T14 worked examples, archived 2026-08-22

Pruned from `docs/TRAPS.md` to make room for the scene-actor trap. The RULE stays in
T14; these are the long case studies behind it.


**Tell:** a map graded clean by a read-through then storms on boot - t2l2 graded **A-** statically and
throws 265 errors on coop boot, *degraded not dead*, which is why a read-through missed it. **A live
boot is the only real test**, and **absence does not log**: a parse error screams, but a VO line that
never plays, a trigger nobody walks into, an alias resolving to nothing are silent, so error-driven
testing cannot find them by construction. You need an **expectation manifest** (what *should* fire,
from the BSP entity lump) diffed against **engine instrumentation** (what *did*) - the coverage sweep.

**Settled 2026-08-06 by the 4-player coverage sweep.** 49 walker-valid maps threw **26,230 script
errors across 548 sites**, none reported by any static audit, concentrated in **shared** files so few
fixes repair many maps: `vehicle_warning.scr` 12,690 (48%), `gags/t2l3_friendly.scr` 8,694 (33%),
`gags/t3l1_enemyspawn.scr` 972, `global/spotlight.scr` 798, `coop_mod/officer.scr:1754` 666 (our **own**
code, all 48 maps). The dominant cause is `$player`-as-array ([T5](#t5)) hitting a retail SP script that
dereferences `.origin` - invisible in SP *and* solo coop, since `OP_UN_TARGETNAME` yields a plain
listener at one match and a container only at 2+. **It needs two connected players to reproduce at
all**, which is why years of solo testing never saw the trilogy's largest error source.

**A MEASUREMENT HARNESS FAILS SILENTLY TOO — a broken one does not error, it reports.** Four AI A/B runs
(2026-08-15) were each invalidated a different invisible way, all four looking clean. **Refuse to report
unless preconditions held, and prove the guard fires** - the four modes and six rules are in
[reference/harness_and_reproduction.md](reference/harness_and_reproduction.md). **A declaration with no
producer is the same silence** (bugs 1596-1598): cross-reference mechanically, walking the WHOLE tree - a
`maps/*.scr` glob misses `maps/<map>/*.scr` and miscounted three wired challenges as dead.

---

<a name="t16"></a>
