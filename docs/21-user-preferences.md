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
> **"I clicked for you. but you've built things before to do this yourself."** — 2026-08-22

The user is the **sole tester**. Never hand them debug homework (`set <cvar> 1`, act, relay a
reading). Drive the console yourself over rcon and read `qconsole.log` — tooling is in place, see
[01-project-map.md](01-project-map.md) §4.

**Look for the existing harness before asking for anything manual, including a click.** A real
2-player dedicated test = `launch_dedicated_2player.ps1 -Map <map>` + `spawn_clicker_2player.ps1`
(joins both clients, re-joins across map changes); `rcon.py map <map>` restarts with both present at
t=0. Both predate this session. **`ls` the root for `launch_*` / `*_clicker` before calling a manual
step unavoidable.**

> **"You might want to watch console every time you deploy too, just in case we are missing any
> problems."** — 2026-07-27

**After EVERY deploy + boot, sweep the WHOLE log, not just the feature under test**, and report
anything new even if unrelated. Treat `Couldn't load X` as a real defect until both existence and
format are verified.

**Always build + deploy before saying "test this", and verify the change reached the binary/pk3** —
hash-compare the source against the shipped member, grep the built DLL for the new string. Fixes have
been left undeployed while the user tested the old build and reported "did not change anything".
Full failure modes: [TRAPS.md § T10](TRAPS.md#t10).

**The gl1/gl2 A/B is the highest-value test available.** It converted "unexplained missing smoke"
into "retail never wired the asset up" in one run. Ask for it early.

---

## Player experience

- **Single player is the spec.** Where coop and the original campaign disagree, match the original
  unless the difference exists to make coop work. Full entry in
  [`archive/prefs-pruned-2026-08-20.md`](archive/prefs-pruned-2026-08-20.md).

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

## Read the record first, then MEASURE. Never theorise. (user, 2026-08-10 / 08-22)

> "let's make it the standard practice to always build probes first to test"
> "Are we operating as efficiently as we can based off of what we have learned as we go?"

Two halves of one discipline, and every expensive day in this project came from skipping one.

**1. Search `buglog.json` FIRST — before a theory forms, not after, to confirm one.** Chasing m1l1's
scripted cast, two diagnoses were reasoned from first principles before the real cause appeared; that
exact defect class was already filed as bug-1949, complete with the too-narrow guard someone had
added for it. One search would have produced the precedent AND its gap in a single step.

**2. For any cause not already proven, ship a MEASUREMENT pass first and a fix second.** Everything
attacked by inference has failed repeatedly: eight resolver attempts on the blueprint pickup before
the ninth simply printed the four filter fields (bug-1665); five on m1l1's ride before a probe read
the flag back and showed the write was a toggle (bug-2064); nine on the ADS jolt before a live trace
found the third-person min-distance fallback (bug-2000). **Probe the DECIDING INPUT, not the
outcome**, and prove the probe is live before asking for a test. When inspection says the wiring is
correct, say so and ask for an empirical A/B — never ship a guess to fill the silence.

**Promote what you find.** Wall cover's whole crash history lived only in the buglog, so a session
following the documented reading order found no reason not to delete the `if (false)` and rebuild the
crash. The buglog is a search index, not a substitute for the authored docs: if an entry would change
a future decision, it belongs in TRAPS or DECISIONS too.

**Budgets are not the enemy.** Pruning keeps rules and drops war stories; nothing load-bearing has
been lost that way. The real inefficiency is knowledge that never left the buglog at all.

Row-by-row evidence and the four rules for writing a probe:
[`archive/prefs-pruned-2026-08-20.md`](archive/prefs-pruned-2026-08-20.md).

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


## Offer the MECHANISM, not just the outcome — the user picks the smaller one (2026-08-24)

Asked how to stop a recruited enemy softlocking a kill-them-all objective, I offered two options:
model conversion as death-and-replace, or refuse to convert the last enemy. The user answered with a
third that was better than both — *"can we not just make it so if the last enemy left on the counter
is in a converted state that counts"* — which became a one-line `Unregister(STRING_DEATH)`: fire the
death NOTIFICATION and kill nothing. No corpse, no gore, no score, no replacement actor to lose state.

The pattern repeats (`notarget` as a setter not a toggle; `coop_vmAntiPop` rejected because smoothing
a 45-unit step is worse than the step). **When presenting options, describe the MECHANISM each one
uses, not only what it achieves** — the user reads mechanisms and routinely spots the minimal one.
Framing a choice purely in outcomes hides exactly the information they decide on.
