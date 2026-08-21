# 21-user-preferences.md passages pruned 2026-08-20

Moved out of `docs/21-user-preferences.md` on 2026-08-20 to get it back under its 12 KB ceiling
(it had reached 13,858 bytes).

**Nothing was deleted.** Every preference, every date and every verbatim user quote is still in the
live file; what is kept here is the fuller original wording, plus the technique material that is
really a TRAPS/probe-writing matter rather than a statement about how the user wants to be worked
with. Where a passage duplicated TRAPS.md, the live file now points at the TRAPS section instead of
restating the mechanism.

Read `docs/21-user-preferences.md` first.

---

## Cvar hygiene, in full — now a one-line pointer to TRAPS.md T7 in the live file

> original lines 110-118. Both bullets restate mechanisms that TRAPS.md T7 already carries with their bug ids (the archived-cvar latch, bug-1427; exec order, bug-710/258). The *preference* half - "preferences = engine default + CVAR_ARCHIVE; coop_defaults.cfg holds menu-controlled options; autoexec seta is only for shipped tuning defaults" - stayed in the live file.

- **A `CVAR_ARCHIVE` cvar with a stale saved value silently re-breaks features.** `omconfig` is
  rewritten on game exit, so scrubbing a bad archived value only sticks if the game is closed
  afterwards. If a behaviour-gating cvar MUST be a fixed value, hard-code it in the engine.
- **NEVER `seta` a user-facing PREFERENCE in `autoexec.cfg`** — exec order is `default.cfg` →
  `menu.cfg` → saved `configs/omconfig.cfg` → **`autoexec.cfg` LAST**, so every autoexec `seta`
  clobbers the user's menu choice each launch. There is no set-if-unset command. Preferences =
  engine registration default + `CVAR_ARCHIVE`; `coop_defaults.cfg` holds the menu-controlled
  options. autoexec `seta` is only for shipped TUNING defaults deliberately re-asserted per release.


---

## Diagnosis discipline (2026-08-03, the gl2 fog/glider day) — split and compressed

> original lines 129-146. The gl1/gl2 A/B line moved into **Testing**; "verify the change reached the binary/pk3" merged with "ALWAYS build + deploy before telling the user to test" (they were the same instruction stated twice); "say plainly when something is not built" moved to **Communication**; the two-failures-then-revert rules became their own section.

## Diagnosis discipline (2026-08-03, the gl2 fog/glider day)

- **The gl1/gl2 A/B is the highest-value test available.** It converted "unexplained missing smoke"
  into "retail never wired the asset up" in one run. Ask for it early.
- **Verify the change reached the binary/pk3 before saying "test this".** A morning was spent on a
  clamp that was a no-op in the active code path, and build.ps1 reported `unchanged` for a pk3 that
  had in fact been updated. Hash-compare source vs shipped member; grep the built DLL for the new
  string.
- **Two failed attempts on the same symptom is the budget — then REVERT, do not iterate.** The glider
  smoke went dense -> retimed -> removed. The Service Record tick was iterated *six* times, each round
  replacing a pin box that already worked, escalating to *"you need to revert back to what was
  working"*. On a surface you cannot observe from here (a `.urc`), the SECOND failure should trigger
  the revert on its own. Put the honest conclusion in the buglog so it is not re-attempted later.
- **A revert means recovering the actual prior artifact, not reconstructing it.** `git show
  HEAD:<path>` on the mod repo produced the exact working widget; rebuilding it from memory is how a
  "revert" quietly becomes a seventh variant.
- **Say plainly when something is not built.** Asked *"what do i need todo to test teh fog"* the
  correct answer was "nothing, it is not built" — not a list of cvars.

---

## Gore section — original longer wording

> original lines 150-167. Both standing rules and the user's verbatim quote are kept in the live file; only the surrounding narrative was shortened.

## Gore is permanent, and everything stays killable (2026-08-03)

> **"I don't ever want blood wiped from any model... All models should be susceptible to complete
> annihilation by shooting them even if dead."**

Two standing rules, both stronger than they sound:

1. **Blood is never removed once applied.** Any code path that clears a gore skin tier, resets
   `m_iCoopGoreSkinTier`, or re-asserts a surface skin without preserving the blood bits is a
   defect. This already bit once: `CG4Aglider.tik`'s bank anims re-asserted `-skin1 +skin2` and
   wiped the bloodied windscreen seconds after it appeared (bug-1316). When adding a skin tier,
   check every OTHER writer of that surface before shipping.
2. **Corpses must remain shootable and destructible.** Both halves ship: bug-1321 gives a body a
   flat `CONTENTS_WEAPONCLIP` bbox so shots stop on it while players walk through, bug-1975 routes
   dead sentients into `CoopGoreCorpseDamage` (tiers, holes, face, gib skins, decap; no
   health/pain/AI). **The lesson is the 17-day gap:** bug-1321 shipped the trace half and recorded
   the damage half as already in place. It was not - `ArmorDamage` opened `if (IsDead()) return;`
   - so a shot corpse bled, and nothing anywhere said so.

---

## Rules for the probe itself — moved here whole

> original lines 189-197. These four are technique for writing a probe, not a statement about how the user wants to be worked with. The live file keeps the instruction that matters at the point of use ("verify the probe is live before asking for a test") and points here for the rest.

**Rules for the probe itself** (each learned by getting it wrong):
- initialise every accumulator - an unset local reads as `none`, `none + float` throws, and a Script
  Error SKIPS the statement, so the probe emits errors instead of data;
- do not reuse an existing marker name, and place the print where the thing being measured actually
  happens (below early-exit rejects, not above them);
- gate on `coop_aggroDebug`, and arm it from a cfg that runs AFTER `autoexec.cfg` - a `+set` on the
  command line is overridden by the shipped autoexec and the probe stays silent;
- **verify the probe is live before asking for a test** (rcon read the cvar, confirm the marker
  appears) rather than assuming it armed.

---

## Player-experience and menu-foolproofing bullets — original wording

> original lines 70-99. Every rule and quote survives in the live file; the 2026-08-18 foolproof-menus bullet was moved up into this section from the bottom of the file, where it had been appended out of order.

## Player experience

- **Single player is the spec.** Asked how to resolve a timing trade-off, the user answered:
  *"the behavior that the mission is scripted to have in single player."* — 2026-08-02. When a coop
  behaviour and the retail SP behaviour disagree, reproduce SP unless there is a coop-specific reason
  not to. Corollaries seen the same day: a scripted mortar is meant to **kill** the two riflemen it
  targets, so make that deterministic rather than leaving it to `radiusdamage` falloff that decided it
  by 3 hit points (bug-1282); and an intro lock should hold to the **story beat** the scene is built
  around (the truck exploding), not to whenever the title cards happen to finish (bug-1289).
- **Generalise; do not special-case.** *"I'd like for it to work regardless of what weapon you have."*
  — 2026-08-02, on the low-health limp being wired for rifles only. When a feature is implemented for
  the one case that has perfect assets, say so explicitly and offer the general version; the user will
  take a slightly imperfect general behaviour over a perfect narrow one.
- **Never trade one visible artifact for another silently.** When a fix swaps a problem rather than
  solving it (gl2 fog: sky exempt → unfogged trees; sky fogged → buried sky), say which artifact each
  state buys and which is currently live, and treat it as unfinished.
- **Developer debug prints must NEVER reach players.** Gate every diagnostic `iprintln`/
  `iprintlnbold` behind the project `level.cMTE_coop_*` flag. *"Stop posting the REINF state —
  players don't need to know about that."* Genuine narrative/objective messages stay ungated.
- **Every VISUAL-EFFECT enhancement must be exposed in the in-game SETTINGS UI** (toggle + key
  sliders), never console-cvar-only. Two homes: renderer post-FX → `ui/coop_postfx.urc` (the
  "EFFECTS" button on Video Options); gameplay/coop features → `ui/coop_settings.urc` (reached by
  clicking the main-menu desk **telephone**).
- **Menu text must use the game font** (`facfont-20` for titles/buttons, `verdana-12` for body).
  Courier/Verdana-elsewhere was immediately flagged as *"different from the rest of the game."*
- **Explosion-death wound visuals must read as SLASHES / DEEP CUTS** (shrapnel lacerations), never
  circular bullet-hole marks.
- **No body gore on players, ever, and players never pool** (alive or dead). Pools mark dead
  **actors** only, both sides.


---

## Documentation and memory hygiene — original wording

> original lines 121-126. Compressed to one bullet; the buglog procedure is unchanged in substance.

## Documentation and memory hygiene

- **`.wolf/buglog.json` is the record that still works** because it is structured and keyed. Keep
  logging to it: read the tail, take `max(numeric id)+1` immediately before writing, verify with
  `json.load` and an entry-count check afterwards, and copy the file aside first.


---


---

# Second-pass originals (2026-08-20)

> Rules, dates and quotes for all of these remain in the live file.


## probe evidence table

Do not spend a playtest cycle on a guess. The evidence from one session:

| Approach | Outcome |
|---|---|
| Scene actors: A3 probe run, THEN fix written against the data | worked first try; also revealed the planned fix keyed on data that does not exist yet at that moment, so it would have shipped clean and fixed nothing |
| Card players: three fixes written from code reading | all three failed; the real writer was a system no review had named |
| Blueprint pickup: EIGHT resolver attempts by inference | all eight failed. The ninth printed the four filter fields and settled it in one run: the cross-file helper call returned NULL (bug-1665) |
| Team revive: two fixes by inference | both failed; only instrumenting moved it forward |
| "White distant objects": six hypotheses, each deployed | a whole day, nothing changed. *"I dont feel like this has helped at all"* |


## gore rules

not — `ArmorDamage` opened `if (IsDead()) return;` — so a shot corpse bled and nothing said so.


## two-failures section

- **Two failed attempts on the same symptom is the budget; then revert, do not iterate.** The glider
  smoke went dense → retimed → removed. The Service Record tick was iterated *six* times, each round
  replacing a pin box that already worked, escalating to *"you need to revert back to what was
  working"*. On a surface you cannot observe from here (a `.urc`), the SECOND failure should trigger
  the revert on its own. Put the honest conclusion in the buglog so it is not re-attempted later.
- **A revert means recovering the actual prior artifact, not reconstructing it.** `git show
  HEAD:<path>` on the mod repo produced the exact working widget; rebuilding it from memory is how a
  "revert" quietly becomes a seventh variant.


## single-player-is-spec

- **Single player is the spec.** Asked how to resolve a timing trade-off: *"the behavior that the
  mission is scripted to have in single player."* — 2026-08-02. When coop and retail SP disagree,
  reproduce SP unless there is a coop-specific reason not to. Corollaries from the same day: a
  scripted mortar is meant to **kill** the two riflemen it targets, so make that deterministic rather
  than leaving it to `radiusdamage` falloff that decided it by 3 hit points (bug-1282); and an intro
  lock should hold to the **story beat** the scene is built around (the truck exploding), not to
  whenever the title cards happen to finish (bug-1289).


---

# Third-pass originals (2026-08-20)


## Testing deploy paragraph

**ALWAYS build + deploy before telling the user to test, and verify the change actually reached the
binary/pk3.** Source edits are invisible in-game until `build.ps1` (scripts/cfg/textures) or a
rebuild + manual copy (fgame/exe), and multiple fixes were left undeployed while the user tested the
old build and reported "did not change anything". A morning also went to a clamp that was a no-op in
the active code path, with `build.ps1` reporting `unchanged` for a pk3 it had in fact updated —
hash-compare source against the shipped member, and grep the built DLL for the new string. (Mechanism:
[TRAPS.md § T10](TRAPS.md#t10).)


## Pace and autonomy body

After a run of self-inflicted regressions, the assistant started gating finished work behind
confirmation. That is the **wrong trade**. Default to **executing and reporting**, not proposing and
waiting.

| Keep | Drop |
|---|---|
| Verifying **before** shipping — build all coupled binaries together, check the math, read the real error | **Asking** whether to ship |
| Naming a real risk in one line | Long risk preambles |

**Content-only changes (pk3 assets: fonts, textures, `.tik`, `.scr`, `.urc`) cannot crash the engine
and must never be held back for "stability" reasons.** Only **engine binary / protocol** changes
warrant staging around the user's testing.


## VISUAL-EFFECT settings bullet

- **Every VISUAL-EFFECT enhancement must be exposed in the in-game SETTINGS UI** (toggle + key
  sliders), never console-cvar-only. Two homes: renderer post-FX → `ui/coop_postfx.urc` (the
  "EFFECTS" button on Video Options); gameplay/coop features → `ui/coop_settings.urc` (reached by
  clicking the main-menu desk **telephone**).


## communication misc

- Their symptom framing can point at the wrong layer — **read the log evidence before assuming.**
  "DBNO isn't triggering" was false; the log had the full down→bleed→died cycle. The real issue was
  audio audibility.
- When they say *"increase the vignette more"* during a specific state, they want the feature **kept
  and strengthened**, not disabled. Reinforce the existing feel; don't remove it.
- When they say *"X used to work and broke when we did Y"*, **trust that** and go to git history /
  the buglog / memory FIRST — do not re-derive from live code. When reverting Y, **diff every file Y
  touched against the original engine**; a partial revert leaves orphans (that is exactly how the
  turret-camera regression survived a "full revert").


---

# Fourth-pass originals (2026-08-20)


## probe evidence prose

Do not spend a playtest cycle on a guess. In one session the single defect that was **probed
first** was fixed first try - and the probe also revealed that the planned fix keyed on data that
does not exist yet at that moment, so it would have shipped clean and fixed nothing. Every defect
attacked by inference failed repeatedly: three fixes for the card players (the real writer was a
system no review had named), EIGHT resolver attempts for the blueprint pickup before the ninth
printed the four filter fields and settled it in one run (the cross-file helper returned NULL,
bug-1665), two for team revive, and six deployed hypotheses for the "white distant objects" bug
that cost a whole day and changed nothing - *"I dont feel like this has helped at all"*. Row-by-row
detail: [`archive/prefs-pruned-2026-08-20.md`](archive/prefs-pruned-2026-08-20.md).


## probe tail

When inspection says the wiring is correct, say so and ask for an empirical A/B — never ship a guess
to fill the silence. **Verify the probe is live before asking for a test** (rcon read its cvar,
confirm the marker appears). The four hard-won rules for writing the probe itself — initialise every
accumulator, do not reuse a marker name, place the print below the early-exit rejects, and arm the
debug cvar from a cfg that runs AFTER `autoexec.cfg` — are in
[`archive/prefs-pruned-2026-08-20.md`](archive/prefs-pruned-2026-08-20.md).



## two-failures bullets

- **Two failed attempts on the same symptom is the budget; then revert, do not iterate.** The
  glider smoke went dense → retimed → removed; the Service Record tick was iterated *six* times,
  each round replacing a pin box that already worked, escalating to *"you need to revert back to
  what was working"*. On a surface you cannot observe from here (a `.urc`), the SECOND failure
  should trigger the revert on its own. Put the honest conclusion in the buglog.
- **A revert means recovering the actual prior artifact, not reconstructing it.** `git show
  HEAD:<path>` produced the exact working widget; rebuilding from memory is how a "revert" quietly
  becomes a seventh variant.


## cvar hygiene bullet

- **Cvar hygiene is a TRAPS matter, not a preference** — a stale archived value silently re-breaks
  features, and `autoexec.cfg` `seta` clobbers the user's menu choice every launch because autoexec
  execs LAST. Preferences = engine registration default + `CVAR_ARCHIVE`; `coop_defaults.cfg` holds
  the menu-controlled options; autoexec `seta` is only for shipped TUNING defaults deliberately
  re-asserted per release. Full mechanism and bug ids: [TRAPS.md § T7](TRAPS.md#t7).


## log sweep paragraph

**After EVERY deploy + boot, sweep the WHOLE log, not just the feature under test.** Report anything
new even if unrelated to the current bug. Treat `Couldn't load X` as a real defect until both
existence and format are verified.


## buglog hygiene

- **`.wolf/buglog.json` is the record that still works** because it is structured and keyed. Read the
  tail, take `max(numeric id)+1` immediately before writing, verify with `json.load` plus an
  entry-count check afterwards, and copy the file aside first.


---

# Fifth-pass originals (2026-08-20)


## probe evidence prose

Do not spend a playtest cycle on a guess. In one session the single defect that was **probed
first** was fixed first try - and the probe also showed the planned fix keyed on data that does not
exist yet at that moment, so it would have shipped clean and fixed nothing. Everything attacked by
inference failed repeatedly: three fixes for the card players, EIGHT resolver attempts for the
blueprint pickup before the ninth printed the four filter fields and settled it in one run (the
cross-file helper returned NULL, bug-1665), two for team revive, and six deployed hypotheses on the
"white distant objects" bug that cost a whole day and changed nothing - *"I dont feel like this has
helped at all"*. When inspection says the wiring is correct, say so and ask for an empirical A/B -
never ship a guess to fill the silence. **Verify the probe is live before asking for a test** (rcon
read its cvar, confirm the marker appears). Row-by-row evidence and the four rules for writing the
probe itself: [`archive/prefs-pruned-2026-08-20.md`](archive/prefs-pruned-2026-08-20.md).


## foolproof menus bullet

- **Menus must be foolproof under heavy clicking** (2026-08-18, stated for the armory and extended to
  the Service Record): players *"will be clicking around a lot... it should be completely foolproof."*
  Every click-driven state must be idempotent, be re-echoed by the server after each apply, or archive
  the EXACT resulting state rather than a relative step. Rapid-click desync between an offline preview
  and server truth is a defect, not an edge case.


## artifact-swap bullet

- **Never trade one visible artifact for another silently.** When a fix swaps a problem rather than
  solving it (gl2 fog: sky exempt → unfogged trees; sky fogged → buried sky), say which artifact each
  state buys and which is currently live, and treat it as unfinished.
