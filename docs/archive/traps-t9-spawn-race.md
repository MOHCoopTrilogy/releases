# T9 (archived) - same-frame spawn / model / solid race

Moved out of `docs/TRAPS.md` on 2026-08-08 to keep that file under its ceiling. Status was
**fixed, pattern known** - kept here because the pattern is still the correct fix if it recurs.

<a name="t9"></a>
## T9 — Same-frame spawn → model → solid race

**Bugs:** 829, 865, 962.

**Tell:** a spawned object is non-solid, or its bounds read zero.

**Mechanism:** MOHAA **defers `setmodel`**, so `getmins`/`getmaxs` read ZERO in the same frame an
entity is spawned. `solid` then links a zero-size box.

**Fix pattern — "framedefer":** Phase A spawns + models + transforms everything into locals → a
frame boundary → Phase B reads bounds and solidifies. Hit the baked build-mode placements on m1l1
(18 objects) and m1l2a (40).

**Companion:** `getmins` returns **BASE** bounds, so per-entity scale must be multiplied in manually
(bug-829, re-hit in bug-962).

**Related engine facts worth knowing:** `moveto`/`move` silently **no-op** on `script_model` — use
origin-stepping each tick. There is no runtime shader swap (script `surface` only toggles
skin1/skin2/nodraw) and scale is a **single uniform float**.

---
