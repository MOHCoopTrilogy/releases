# Carrying the m2l2a stealth layer to the other disguise maps — PLAN

**Written 2026-08-11, after Phase C shipped on m2l2a (bugs 1676-1698).** Everything here is
measured from the BSP entity dumps in `map_entities/` and from the shipped scripts, not recalled.

---

## 1. What the data actually says

`type_disguise` is set on **1,900+ actors across 44 maps** — and almost all of it is noise.
**`salute` is the map-editor DEFAULT**, not a marker: it is on 84/84 actors in e1l3, 202/202 in
e3l4, 100/100 in t1l2. Treating it as a role is what silently switched the AI-dynamics personality
system off across most of the game once before, so the counts below deliberately ignore it.

The roles that mean something:

| map | officer | sentry | rover | none (see-through watcher) | `coop_enableDisguises` | `$waittrigger_alarm_master` |
|---|---:|---:|---:|---:|:--:|:--:|
| **m2l2a** | **2** | 3 | – | 10 | ✅ | ✅ |
| **m6l1c** | **3** | 2 | – | 29 | ❌ | ✅ |
| **t3l1** | – | **14** | **4** | 8 | ❌ | ❌ |
| e1l4 | – | 4 | – | 14 | ✅ | ✅ |
| t3l2 | – | 2 | – | 6 | ❌ | ❌ |
| e3l2 | – | 1 | – | – | ❌ | ❌ |
| m2l2b | – | – | – | 6 | ✅ | ❌ |
| e3l1 / e3l3 | – | – | – | 56 / 43 | ❌ | ❌ |
| m1l2b / m1l3c / m6l3a / t1l3 | – | – | – | 6 / 2 / 4 / 5 | ❌ | ❌ |
| e1l3 | – | – | – | – | ❌ (papers-only, its own path) | ❌ |

**Three facts fall straight out of that table:**

1. **`officer` exists on exactly two maps: m2l2a and m6l1c.** The contain prompt is gated on
   `type_disguise == "officer"`, so today it is *structurally* incapable of firing anywhere else.
2. **`$waittrigger_alarm_master` exists on exactly three maps: e1l4, m2l2a, m6l1c.** Escalation's
   `trigger $waittrigger_alarm_master` therefore only reaches the full authored cascade on those.
   `coop_bustGoLoud` already falls back to `takeAllDisguises` when the entity is NULL, so nothing
   breaks elsewhere — it is just a quieter escalation.
3. **t3l1 is the largest sentry population in the game (14 + 4 rovers, the only `rover` map)** and
   has neither the disguise system enabled nor an alarm master.

---

## 2. The recommendation, in priority order

### Tier 1 — **m6l1c**. Do this one first, and possibly only this one.

It is the closest thing to a second m2l2a in the trilogy, and it is *already* a disguise mission:

- **3 officers, 2 sentries, 29 watchers** — a richer checker population than m2l2a itself
- `$waittrigger_alarm_master` present, so escalation gets the real alarm cascade
- an explicit objective: *"Infiltrate the base (Hint: find a disguise)"* (`m6l1c.scr:413,559`)
- a live papers mechanic — `level.papers`, `$papers1/$papers2` props, a papers gate at `:462`
- it already switches roles dynamically at runtime (`soldier1/2` → `"none"` → `"salute"`, `:562-584`)

**But it does NOT set `level.coop_enableDisguises`.** That single flag gates the whole coop
disguise layer, so on m6l1c the coop side is dormant today and the map runs a hand-rolled
alarm-zone hack instead (`:313 hackresetaionguysoutside`, whose own comment says it exists "to get
coop to work with disguises").

### Tier 2 — **e1l4 and m2l2b**: enable the disguise system already, but have **no officers**.

The contain can never fire there as written. This is a **design decision, not a port**: either
widen the role gate to include `sentry`, or accept that contain is an officer-only mechanic and
these maps keep papers-only stealth. Do not widen it silently — see §4.

### Tier 3 — **t3l1**: the largest sentry map, but no papers, no disguise flag, no alarm master.

Real work, not a carry-over. Park it until Tier 1 is proven.

### Not applicable

Every other map. `salute`-only maps have no checkers, and `none`-only maps (e3l1, e3l3) have
watchers with nobody to report to.

---

## 3. What is portable today, and what is welded to m2l2a

| Phase C component | portable? | why |
|---|---|---|
| `coop_bustBash` / stun / pain handler | ✅ | pure actor mechanics, no map data |
| `coop_bustArm` / `coop_bustDisarm` | ✅ | needs only a papers item + the player |
| `coop_bustWitnessed` + contained/escalated | ✅ | walks `level.coop_actorArray["german"]` |
| `coop_bustBodyWatch` + investigation | ✅ | corpse + actor array only |
| escalation → **real alarm** | ⚠️ | needs `$waittrigger_alarm_master` — 3 maps; falls back cleanly |
| contain prompt (role gate) | ❌ | `type_disguise == "officer"` — 2 maps only |
| **`coop_stealthStart`** | ❌ | a GLOBAL cvar read by m2l2a-specific code in `m2l2a.scr:64,1056` |
| unarmed papers-only start | ❌ | set in `m2l2a.scr`; every map needs its own decision |
| Naxos sabotage bar / room prompts | ❌ | m2l2a mission content, does not generalise |

**The one real architectural blocker is `coop_stealthStart`.** It is a single global boolean doing
two different jobs: "is the stealth route enabled at all" and "does THIS map start you unarmed".
Porting to a second map with it as-is means m6l1c's start silently follows m2l2a's switch.

---

## 4. The plan

### Step 1 — split the gate (do this before touching any map)

Replace the global read with a per-map level flag set by the map, plus the global as a master
kill-switch:

```
// in <map>.scr::main, gametype != 0 branch
level.coop_stealthMap = 1          // this map has a papers/disguise stealth route
```

and everywhere Phase C currently tests `getcvar("coop_stealthStart") == "1"`, test
`level.coop_stealthMap == 1 && getcvar("coop_stealthStart") != "0"`. Five sites:
`bust.scr:780`, `itemhandler.scr:1245`, `:2749`, `m2l2a.scr:64`, `:1056`.

This is a pure refactor with **zero behaviour change on m2l2a** (it sets the flag, the cvar is 1),
and it is what makes every later step a one-line opt-in rather than a copy-paste.

### Step 2 — m6l1c opt-in, smallest possible diff

1. `level.coop_enableDisguises = game.true` in `m6l1c.scr::main`
2. `level.coop_stealthMap = 1`
3. **do NOT** set `coop_noWeapon` / `coop_startUnarmed` yet — let m6l1c keep its armed start for
   the first pass. Contain still works: what it needs is a *disguised* player, and the map's own
   uniform pickup provides that.
4. verify the papers item resolves (`level.coop_itemPapers`) — m6l1c has `$papers1/$papers2` props
   and a `level.papers` flag, which is **not** the same thing as the coop inventory item

### Step 3 — measure before designing anything else

Run the map with `coop_aggroDebug 1` and read: does `^~^~^ CONTAIN challenge` fire, with what
`role=`? m6l1c reassigns `type_disguise` at runtime, so the officers may not be officers at the
moment they challenge. **That question is unanswerable from the entity dump alone** — the dump is
the spawn state, and `:562-584` proves the map mutates it live.

### Step 4 — only then decide the Tier-2 question

With real data from two maps, decide whether `sentry` should be containable. If yes it is one line;
if no, e1l4/m2l2b stay papers-only and that is a legitimate answer.

---

## 5. Traps this will walk into (all already paid for once)

- **`salute` is not a role.** Any heuristic keyed on it hits ~90% of every map in the game.
- **`coop_isProtectedActor` is true for the entire cast on an alarm map.** It answers "leave this
  actor alone", and reusing it for "who would notice X" vetoes everybody (bug-1687). m6l1c has an
  alarm master, so it will behave exactly like m2l2a here.
- **The entity dump is the SPAWN state.** m6l1c rewrites `type_disguise` at runtime. Print the key
  at the moment the code depends on it (bug-1642's lesson: a guard can key on data that does not
  exist yet).
- **A cvar archived in a player's config beats `coop_defaults` forever** (bugs 1427, 1698, 1699 —
  three times in two days). If Step 1 adds any new cvar, decide up front whether it is a preference
  (coop_defaults, menu-owned) or a forced gate (autoexec).
- **`disable_ai` is only `enableEnemy = 0`.** It stops nothing. Damage is the only lever script has
  on an actor's think (bug-1682, and again in bug-1695).

---

## 6. Honest scope estimate

- **Step 1** (split the gate): ~30 minutes, no playtest needed beyond an m2l2a regression run.
- **Step 2+3** (m6l1c opt-in + measure): one session, most of it playtesting.
- **Tier 2/3**: unknown until Step 3 produces data. Do not estimate them yet.

**The single highest-value thing here is m6l1c**, because it is the only other map in the trilogy
with officers, an alarm cascade, a papers mechanic and an explicit "find a disguise" objective. If
the carry-over works anywhere, it works there — and if it does not work there, it will not work
anywhere else either, which is worth knowing before touching t3l1.
