# 10 — MOHAA GameScript (`.scr`) Conventions

The language is called *morlang* / *morfuscript*. Its defining property: **a single syntax error
silently kills the compile of the WHOLE file**, and the map then runs with no script at all — raw
team menu, unstartable, no error unless `developer 1` is on.

---

## 1. Parse killers — the verified list

Each of these fails the entire file. Ordered by how often they have actually bitten.

| Killer | Correct form | Anchor |
|---|---|---|
| **Leading `&&` / `\|\|` on a continuation line** of a multi-line `if`/`while` | Put the operator at the line **END**, or use one line. Trailing continuation is legal. | bug-750 |
| **Unquoted `+`/`-` flag on `surface`** — `surface x -nodraw` parses as *minus the identifier* `nodraw` | `surface us_helmet "+nodraw"` / `"-nodraw"` / `"+skin1"` | bug-533 |
| **`EV_GETTER` used with command syntax** — `local.e getmins` | Property syntax only: `local.e.getmins` | bug-910 |
| **`EV_SETTER` used with command syntax** — `player moveSpeedScale 0.4` | `local.player.moveSpeedScale = 0.4` | cerebrum 2026-06-28 |
| **Comma-separated multi-arg builtin** — `vector_scale( vec, scalar )` | No precedent exists for `builtin(a, b)` in this codebase. 1-arg builtins are fine: `sin(x)`, `vector_normalize(v)`, `randomint(n)` | bug-402 |
| **Function call inside a vector literal** — `( 0 0 int(local.d) )` | Assign to a local first. Variables in vectors are fine: `( local.a local.b 0 )`. Arithmetic in parens is fine: `(local.m * 1.5)` | Do-Not-Repeat 2026-07-07 |
| **Empty-array literal** — `local.x = []` | morlang has no empty-array literal; an array is created by its first indexed assignment. Track an explicit count local. | cerebrum 2026-07-24 |
| **Bare negative in parentheses** — `(-1)` | | CLAUDE.md, confirmed |
| **UTF-8 BOM / any non-ASCII byte** (em-dash `—` especially) | Pure ASCII only | CLAUDE.md |
| **Label / brace mismatch** | See §2 | bug-239 |
| **Odd quote count on a line** (string literal broken across lines) | | bug-331 |
| **A call to a script builtin that does not exist** | One unknown command kills the file. **Grep the engine Event table yourself** — `player userinfo` did not exist and an agent cited it. | bug-298 |

**Not** a parse killer, despite an old note: `spawn <class>` with inline keyvalues
(`spawn trigger_relay targetname "x"`). 192 working occurrences including `coop_mod/main.scr:40`.

### Detecting them

- **`depthscan2.py` (running-depth brace scan) is necessary but NOT sufficient.** Brace counts can
  *balance* while the file is broken — two opposite errors cancel (bug-239, m1l3c). Requirements: depth
  must never go negative and must be 0 at every column-0 label (internal `goto` labels may
  legitimately sit at depth 1).
- depthscan **cannot** catch: leading-operator continuations, `EV_GETTER` misuse, invented commands,
  comma-arg builtins, function-calls-in-vectors. For those: **boot once with `developer 1` and grep
  the log for `Couldn't compile` / `Couldn't parse`** — the parser names file and line.
- depthscan2 does **not** strip `/* */` block comments, so a `}` inside one reports a spurious
  negative depth (`friendly.scr:2713-2719`). Re-scan with comments and strings stripped before
  treating a negative as real. Use a **state-machine** parser, not a regex strip.
- A `parse error … TOKEN_IDENTIFIER` is the **GameScript** compiler, not the `.urc` menu parser.
- **Cascade**: a parse error in a file threaded from a per-spawn hook takes down the whole
  name-command bus. Symptom = every name-append bind silently does nothing. Suspect any new `.scr`
  threaded at spawn (bug-533).

---

## 2. Runtime semantics that bite

### `NIL` vs `NULL` — distinct, never equal

A never-assigned variable reads **NIL**. A freed/absent entity reads **NULL**. `!= NULL` **passes
for NIL**. Guard maybe-unset entity slots with **both**:

```
if ( x != NIL && x != NULL ) { … }
```
(bug-948w). Entity-owner level vars (`level.coop_smoke_player`, `level.coop_binoc_owner`) must be
**NULL-initialised at map start** — lazily assigned ones read NIL and `!= NULL` misses them
(cerebrum 2026-07-23).

**Change-tracking with `flags[key] != value` is broken when the flag can be NIL** — morlang does
not treat `NIL != value` as "different", so the first-ever write is silently skipped. Check NIL
explicitly first (bug-533-adjacent, 2026-07-10).

### Stale entity refs — only `isAlive` catches them

A player ref that passes `!= NULL && != NIL` can still cast `'none'` on `.origin` — it is a
mid-respawn / just-freed player (a stale `SafePtr`). **No** equality or truthiness guard catches
that state. Only **`isAlive <ref>`** does, and it is safe to call on a stale ref (cerebrum 2026-07-22).

### Empty array `.size` is `-1`, not 0

The append idiom `array[array.size + 1] = x` therefore writes the **first** element to index `[0]`,
which every 1-indexed consumer loop silently skips. Clamp the computed index to `>= 1`, or seed the
array 1-indexed. This one idiom cost the minesweeper **and** the 2nd primary across multiple failed
fix rounds (bug-909).

### `$player` is an array

- Raw `$player` with `turnto/lookat/runto/say_to/.origin` **aborts the thread**. Use `$player[1]`
  (host) for single-target; keep `$player` only for broadcast (`item`/`ammo`/`takeall`/`useweaponclass`).
- `$player damage` = **team wipe**. Loop per player.
- The array-cast error (`Cannot cast 'array' to listener`) **only fires with 2+ clients CONNECTED**
  — solo boots cannot reproduce or verify these. Connected-but-unspawned counts.
- **The reported `file:line` is where the value is dereferenced, not where the bug is.** Trace up to
  the caller.
- **Storms are SEQUENTIAL**: a storm blocks map progression and hides every storm downstream.
  Budget 2-3 fix→re-sweep passes.
- **Fixing all `$player` statically is the wrong scope** — ~1764 bare sites across 176 files, the
  vast majority in dead retail paths. The dynamic sweep is the source of truth; use the static scan
  only to fix all sites in a sweep-flagged file at once.
- Several **retail** globals/gags served from the pak (`hoveringplane.scr`, `box_effects.scr`,
  `t1l1_end.scr`) storm with 2 players. Extract from the pak, override in the mod, and add NULL
  guards (`$player[1]` is NULL during respawn-blink).

(bugs from the 2026-07-22 4-player sweep)

### When counting script errors, count ALL `Script Error` lines

A harness that matched only `Cannot cast 'none'` reported m5l1a/b as clean while they stormed 4006×
`binary '*' applied to incompatible types 'none' and 'float'`. Other uncounted classes:
`command 'X' applied to NIL/NULL`, `Field 'X' applied to…` (cerebrum 2026-07-22).

### Other runtime facts

- A **runtime error kills that thread at that line** — everything after never runs. Guard init
  functions with self-healing re-entry.
- **No string×int coercion.** The `'* 1'` trick is a runtime type error. `float()` and `int()` casts
  are real (bug-302).
- **`getcvar()` returns a STRING.** `+ 0` concatenates (`"-4600" + 0` = `"-46000"`); `* 1` is a type
  error. Always `int( getcvar("x") )`. Both `getcvar "x"` and `getcvar("x")` parse.
- **`exec` vs `waitthread` for return values**: `exec` returns the real value **only** if the callee
  completes without ever yielding. If it yields or uses a nested `waitthread`, `exec` returns a
  **thread pointer**. Use `waitthread` to capture returns (cerebrum 2026-06-27).
- **`main.scr::containsText` is CASE-SENSITIVE**; the engine stores `weapon.model` **lowercased**.
  Its 3rd arg is `giveStartPos`, not a case flag. Emit substrings **longest-first** in match chains.
- **`thread <missing label>`** = runtime ScriptException that kills the calling thread
  (`scriptmaster.cpp:712`). Retail `m2l2b.scr:60 countdeaths3` does this on most playthroughs.
- **No `waittill pain`.** Use `waittill damage` or an `events.scr` subscription. `self waittill pain`
  never fires in OpenMOHAA — retail scripts that block on it hang forever (bug-1212).
- **Function parameters are declared on the label line**: `myfunc local.a local.b:{ … }`, called as
  `waitthread myfunc arg1 arg2`.
- **`coop_mod/replace.scr::player_origin` is a deliberate infinite-loop CRASH TRAP** — an
  intentional tripwire for deprecated call sites. Never call it.
- **`remove`, never `delete`, on AI actors.** And **never `remove` a LIVE actor if anything waits on
  its death** — the Listener destructor's `StoppedWaitFor(bDeleting=true)` **deletes** every parked
  thread rather than resuming it. Kill through the real damage path (bug-638).
- **`wait`/`waitframe` are forbidden** in or before `main.scr::main`.
- String literals support `\n` `\t` `\"` escapes.

---

## 3. Engine-behaviour facts every script author needs

- **`scale` is VISUAL-ONLY.** `Entity::setScale` never touches `r.mins`/`r.maxs`, so a `solid`
  `script_model` clips at its **base** bbox. After scaling, `setsize base_mins*scale base_maxs*scale`
  (bug-829).
- **`moveto`/`move` silently no-op on `script_model`** — use origin-stepping each tick.
- **`notsolid` entities are skipped by `RadiusDamage`** — ghost-scripted actors are grenade-proof.
- **A `notsolid` player cannot be shot.** Glued vehicle passengers need `solid` set after gluing —
  which then blocks a solid mover, so the vehicle must be `notsolid` too. Net rule for coop seats:
  **vehicles notsolid + passengers solid**.
- **`glue` vs `duckableglue`**: the third `can_duck` arg. Plain-glued players **cannot crouch**.
  Bed seats must use `duckableglue`.
- **`attachturretslot <slot> <player>`** seats a player; `detachturretslot <slot> <exit_vec>` ejects.
  **`douse` is not a MOHAA command** — it silently no-ops (that was the e3l3 AB41 "F sends it down
  the rail empty" bug).
- **`parm.other` is NOT the trigger activator** in a `trigger_use` setthread — it is a stale global.
  Use `waitthread coop_mod/replace.scr::player_closestTo self`.
- **`EV_POSTSPAWN` (-5.0f) is a one-time gate.** Anything script-spawned after level spawn never
  receives it — which is why script-spawned turrets have no eye bone and no floor snap.
- **Script-spawned Vehicles need `soundset "<prefix>_"`** or they play the generic unprefixed
  aliases = bizarre glitching engine noise.
- **Player weapon control**: `holster` is a **toggle** (never use for enforcement); `safeholster 1/0`
  is the one-way force with memory. `.gun` is not a readable player property (returns NIL silently).
- **`ihuddraw_*` are GLOBAL commands with the player as FIRST ARG** — `ihuddraw_shader <player>
  <slot> <path>`. The entity-prefix form throws.
- **`spawn models/player/<x>.tik` fails at runtime** — player models have no explicit Actor
  classname. Only `models/human/*.tik` can be spawned as actors.
- **Give a weapon**: `thread coop_mod/replace.scr::givePlayerWeapon "weapons/<file>.tik" <player>
  "one"|"all" <wait>`.
- **`item` (bare) bypasses the pickup guard**; a pickup-based give does not. In a team gametype a
  player can hold only **ONE primary** via a *pickup* (`weapon.cpp:3136`) — a second primary given as
  a spawned pickup is silently **dropped from engine inventory**. Re-issue primaries via bare `item`
  (bug-907).
- **Per-client looping sound**: `<player> playlocalsound <alias> 1` (the 3rd param is a **loop
  bool**). Positional world sound: `spawn script_model` + `model "fx/dummy.tik"` + `notsolid` +
  `loopsound <alias> <vol> <minDist>`; **omit** the `"levelwide"` 3rd arg to keep distance falloff.
- **Sound aliases are map-gated** by the trailing `maps "…"` prefix list. Coop-wide VO must be
  declared with `maps "m e t dm obj train"`. Any `ubersound/*.scr` is auto-registered — no include
  needed. **A later alias definition WINS** (duplicates are common and often intentional).
- **`ubersound.scr` terminates on a lone `end`** — aliases after it are ignored.
