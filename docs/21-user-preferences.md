# 21 — How the user works

Read every session. These are corrections the user actually made, not inferences.
Pruned 2026-08-20; the longer originals of the compressed entries are in
[`archive/prefs-pruned-2026-08-20.md`](archive/prefs-pruned-2026-08-20.md).

---

## Pace and autonomy

> **"Ship it; don't ask."**
> *"I need you to stop pushing back on so many changes… we used to be way more productive than this."*
> — 2026-07-28

Gating finished work behind confirmation is the **wrong trade**. Default to **executing and
reporting**, not proposing and waiting. Keep verifying *before* shipping (build all coupled
binaries together, check the math, read the real error) and name a real risk in one line; drop the
asking and the risk preambles. **Content-only changes (pk3 assets: fonts, textures, `.tik`, `.scr`,
`.urc`) cannot crash the engine and must never be held back for "stability" reasons** - only
**engine binary / protocol** changes warrant staging around the user's testing.

---

## Communication

- **Acknowledge mid-work messages IMMEDIATELY.** When the user sends something while you are deep in
  tool calls ("he spawns in now…", "now he isn't spawning"), respond to it in your next visible text
  — even one sentence — before continuing. *"id appreciate some acknowledgement when i want to you
  btw."* Silence while grinding tools reads as being ignored.
- **Tell them FIRST when an automated test will pop game windows on their screen.**
- **Say plainly when something is not built.** Asked *"what do i need todo to test teh fog"* the
  correct answer was "nothing, it is not built" — not a list of cvars.
- Their symptom framing can point at the wrong layer — **read the log evidence before assuming.**
  "DBNO isn't triggering" was false; the log had the full down→bleed→died cycle, and the real
  issue was audio audibility.
- When they say *"increase the vignette more"* during a specific state, they want the feature
  **kept and strengthened**, not disabled.
- When they say *"X used to work and broke when we did Y"*, **trust that** and go to git history /
  the buglog FIRST rather than re-deriving from live code. When reverting Y, **diff every file Y
  touched against the original engine** - a partial revert leaves orphans, which is exactly how the
  turret-camera regression survived a "full revert".

---

## Testing

> **"Do the commands yourself and watch console yourself."** — 2026-07-19

The user is the **sole tester**. Never hand them debug homework (`set <cvar> 1`, act, relay a
console reading). Drive the console yourself over rcon and read `qconsole.log`. Tooling is already
in place — see [01-project-map.md](01-project-map.md) §4.

> **"I clicked for you. but you've built things before to do this yourself."** — 2026-08-22

**Look for the existing harness before asking the user for anything manual, including a click.**
Areal player in a dedicated test = `launch_dedicated_2player.ps1 -Map <map>` + `spawn_clicker_2player.ps1`
(joins both clients, re-joins across map changes); `rcon.py map <map>` then restarts with
both present at t=0. Both predate this session.
**`ls` the root for `launch_*`/`*_clicker` before calling a manual step unavoidable.**

> **"You might want to watch console every time you deploy too, just in case we are missing any
> problems."** — 2026-07-27

**After EVERY deploy + boot, sweep the WHOLE log, not just the feature under test**, and report
anything new even if unrelated to the current bug. Treat `Couldn't load X` as a real defect until
both existence and format are verified.

**ALWAYS build + deploy before telling the user to test, and verify the change actually reached
the binary/pk3.** Source edits are invisible in-game until `build.ps1` (scripts/cfg/textures) or a
rebuild + manual copy (fgame/exe); fixes have been left undeployed while the user tested the old
build and reported "did not change anything", and a morning went to a clamp that was a no-op in
the active path while `build.ps1` reported `unchanged` for a pk3 it had updated. Hash-compare
source against the shipped member and grep the built DLL for the new string.
([TRAPS.md § T10](TRAPS.md#t10).)

**The gl1/gl2 A/B is the highest-value test available.** It converted "unexplained missing smoke"
into "retail never wired the asset up" in one run. Ask for it early.

---

## Player experience

- **Single player is the spec.** Where coop and the original campaign disagree, match the original
  unless the difference exists to make coop work. Full entry in
  [`archive/prefs-pruned-2026-08-20.md`](archive/prefs-pruned-2026-08-20.md).

---

## Gore is permanent, and everything stays killable (2026-08-03)

> **"I don't ever want blood wiped from any model... All models should be susceptible to complete
> annihilation by shooting them even if dead."**

1. **Blood is never removed once applied.** Any path that clears a gore skin tier, resets
   `m_iCoopGoreSkinTier`, or re-asserts a surface skin without preserving the blood bits is a defect -
   `CG4Aglider.tik`'s bank anims re-asserted `-skin1 +skin2` and wiped the bloodied windscreen seconds
   after it appeared (bug-1316). **When adding a skin tier, check every OTHER writer of that surface
   first.**
2. **Corpses must remain shootable and destructible** - bug-1321 (flat `CONTENTS_WEAPONCLIP` bbox, so
   shots stop on a body while players walk through) plus bug-1975 (dead sentients route into
   `CoopGoreCorpseDamage`: tiers, holes, face, gib skins, decap; no health/pain/AI). **The lesson is
   the 17-day gap:** bug-1321 recorded the damage half as already in place and it was not
   (`ArmorDamage` opened `if (IsDead()) return;`), so a shot corpse bled and nothing anywhere said so.

---

## Tuning workflow

- **Live visual tuning, then bake.** Add `CVAR_ARCHIVE` cvars read every frame, dial them in-game by
  eye, then bake the final values as compiled defaults. This is the established pattern for ADS
  offsets, turret cameras, post-FX, and AI timers.
- **When re-baking from a CROUCH tuning pass, edit ONLY the 5 crouch fields per gun.** *"PLEASE ONLY
  UPDATE CROUCH"* (emphatic). `adssave` logs both stand and crouch even in a crouch pass — ignore the
  stand line. Bake via a script that keeps the first 5 stand tokens verbatim.
- **Cvar hygiene is a TRAPS matter, not a preference.** Preferences = engine registration default +
  `CVAR_ARCHIVE`; `coop_defaults.cfg` holds the menu-controlled options; `autoexec.cfg` `seta` is
  only for shipped TUNING defaults deliberately re-asserted per release (it execs LAST, so it
  clobbers the user's menu choice). Mechanism and bug ids: [TRAPS.md § T7](TRAPS.md#t7).

---

## Two failed attempts is the budget — then REVERT (2026-08-03)

- **Two failed attempts on the same symptom is the budget; then revert, do not iterate.** On a
  surface you cannot observe from here (a `.urc`), the SECOND failure triggers the revert - the
  Service Record tick was iterated six times, each round replacing a pin box that already worked.
  Put the honest conclusion in the buglog.
- **A revert means recovering the actual prior artifact** (`git show HEAD:<path>`), never
  reconstructing it from memory - that is how a "revert" becomes a seventh variant.

---

## Instrument BEFORE fixing — standing instruction (user, 2026-08-10)

> "let's make it the standard practice to always build probes first to test"

For any defect whose cause is not already proven, **ship a measurement pass first and a fix second**.
Everything attacked by inference has failed repeatedly - eight resolver attempts on the blueprint
pickup before the ninth simply *printed the four filter fields* and settled it in one run
(bug-1665); five attempts at m1l1's scripted ride before a probe read the flag back and showed the
write was a toggle (bug-2064). **Probe the DECIDING INPUT, not the outcome**, and verify the probe
is live before asking for a test. When inspection says the wiring is correct, say so and ask for an
empirical A/B; never ship a guess to fill the silence. Row-by-row evidence and the four rules for
writing a probe: [`archive/prefs-pruned-2026-08-20.md`](archive/prefs-pruned-2026-08-20.md).


---

## Planning and queueing

- **Plan, then have agents vet the plan, BEFORE writing code** (2026-08-20, stated three times:
  "before you write any code, I'd like for you to plan it all out and then have agents vet your plan
  multiple times over before rolling it out"; "instead of me doing hundreds more tests do more
  research and vet"). This is not ceremony - on the ADS work three independent reviews each found a
  defect the plan would otherwise have shipped, including the one that WAS the user's bug (an
  unscaled 38-degree crouch rotation) which the plan had wrongly assumed was already handled. Use
  independent LENSES (engine correctness / adversarial edge cases / this project's own bug history),
  not three copies of the same review: the history lens is what catches "you already built this and
  killed it", which reading the code alone cannot.
- **When many requests are in flight, keep a visible queue and batch the report** (2026-08-20: "Im
  throwing a lot at you so please make sure you dont miss anything", then "We have a lot going so
  just tell me when everything is done and ready"). Capture every incoming idea in writing as it
  arrives - the user fires them faster than they can be built - and report once at the end rather
  than narrating each step.

---

## Documentation and memory hygiene

- **`.wolf/buglog.json` is the record that still works** because it is structured and keyed. Copy
  the file aside first, take `max(numeric id)+1` immediately before writing, and verify with
  `json.load` plus an entry-count check afterwards.

## A setting is a promise

- **"If we removed settings for a bug reason that setting needs to be removed."** (2026-08-21) A
  control still toggleable after its feature was disabled is worse than none - the player toggles it,
  nothing happens, and the whole options screen reads as fake. Both directions: pull a feature, pull
  its control; force a cvar mitigation for a bug, clear it when that bug closes. Check with
  `docs/tools/audit_menu_cvars.py` (resolves each cvar to its cached pointer and counts real
  dereferences), never by eye - a cvar name appears only at its registration. **Verify its findings
  against source before deleting anything:** its first run called 8 live controls dead, all blind
  spots in the tool.

## Search `buglog.json` BEFORE theorising, not after

[user 2026-08-22] "Are we operating as efficiently as we can based off of what we have
learned as we go?" - the honest answer was no, and the day proved it.

Chasing why m1l1's scripted cast broke, two wrong diagnoses were proposed from first
principles (enemy count-scaling; then the personality roll alone) before the real cause -
the weapon-variant roll re-arming holstered actors - turned up. **That exact defect class
was already in the buglog as bug-1949**, complete with the guard someone had added for it.
One search for "unholster scripted actor" would have produced the precedent AND the fact
that its guard was too narrow, in a single step.

The protocol already says to read `buglog.json` before fixing. In practice it gets read
*after* a theory has formed, to confirm it. Read it FIRST, to find out whether the problem
is already solved or half-solved.

**Promote what you find.** Today's other lesson: wall cover's entire crash history existed
only in the buglog - `TRAPS.md` and `DECISIONS.md` had zero cover entries - so a session
following the documented reading order would have found no reason not to delete the
`if (false)` and rebuild the crash. The buglog is a search index, not a substitute for the
authored docs. If a buglog entry would change a future decision, it belongs in TRAPS or
DECISIONS too.

**Budgets are not the enemy.** Pruning keeps rules and drops war stories; nothing load-bearing
has been lost that way. The real inefficiency is knowledge that never left the buglog at all.
