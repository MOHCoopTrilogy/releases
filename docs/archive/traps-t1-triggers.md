# T1 - confirmed Morpheus parse-kill triggers

Moved out of `docs/TRAPS.md` on 2026-08-28 for budget; it is a lookup table, not a rule. The rules stay
in [TRAPS.md T1](../TRAPS.md). Each row killed a whole `.scr` file silently, under the listed bug id.

| Confirmed trigger | Bug |
|---|---|
| Command syntax on an `EV_GETTER` property (`local.e getmins`) — must use property syntax | 910 |
| A script command a sub-agent invented (`userinfo`, `getcurrentdmweapontype`) | 298, 1067 |
| A function call inside a vector literal, or with one in the same expression | 348, 402 |
| Negatives/arithmetic: parenthesised `(-1)`, or in a COMMAND ARG slot — `$ent coopammo 0 - 1`. Compute to a local. **But** negative *vector components* are fine: `( 4016 0 - 967 0 - 328 )` == `( 4016 -967 -328 )`. **For a vector that STARTS negative, write the plain literal** - `setsize ( -58 -115 0) (58 115 110)`, the form shipped working code uses (objective_drop.scr:103, officer.scr:4900). Do not lead with `(0 - 58 ...`: it reads as a parenthesised expression rather than a vector and there is no error either way (bug-2196). | 1069, 1826, 1830 |
| An empty-array literal `[]` — morlang has none | 1105 |
| An unquoted `+`/`-` directive argument: `surface X -nodraw`, `surface X "+skin1"` — valid TIKI syntax, fatal in script (`unexpected TOKEN_PLUS`), **quote it**. Braces balance, so the depth scan misses it. | 533, 1308 |
| A leading `&&` or `\|\|` on a continuation line | 739/750 |
| A real newline inside a string literal — from a generator, or a hand-typed banner | 331, 962, 1283, 1285 |
| A backslash in a script path (resolved to `coop_modhelmet.scr`) | 1205 |
| Em-dash, UTF-8 BOM, any non-ASCII; duplicate label; label/brace mismatch | (CLAUDE.md) |
