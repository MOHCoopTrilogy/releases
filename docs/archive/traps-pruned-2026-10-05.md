# TRAPS lines moved out 2026-10-05 (budget), verbatim

From T22 (usercmd button bits):

Two neighbours that ARE extensible, if you genuinely need wire state: the weapon-command enum has
16 of its 31 values used, and `entityState.surfaces[]` bit 6 was reclaimed once (bug-2080). Both
are **wire semantics** — changing either means shipping exe + cgame + game + both renderers together.
