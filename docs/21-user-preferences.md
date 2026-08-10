# 21 — How the user works

Read every session. These are corrections the user actually made, not inferences.

---

## Pace and autonomy

> **"Ship it; don't ask."**
> *"I need you to stop pushing back on so many changes… we used to be way more productive than this."*
> — 2026-07-28

After a run of self-inflicted regressions, the assistant started gating finished work behind
confirmation. That is the **wrong trade**. Default to **executing and reporting**, not proposing and
waiting.

The distinction that matters:

| Keep | Drop |
|---|---|
| Verifying **before** shipping — build all coupled binaries together, check the math, read the real error | **Asking** whether to ship |
| Naming a real risk in one line | Long risk preambles |

**Content-only changes (pk3 assets: fonts, textures, `.tik`, `.scr`, `.urc`) cannot crash the engine
and must never be held back for "stability" reasons.** Only **engine binary / protocol** changes
warrant staging around the user's testing.

---

## Communication

- **Acknowledge mid-work messages IMMEDIATELY.** When the user sends something while you are deep in
  tool calls ("he spawns in now…", "now he isn't spawning"), respond to it in your next visible text
  — even one sentence — before continuing. *"id appreciate some acknowledgement when i want to you
  btw."* Silence while grinding tools reads as being ignored.
- **Tell them FIRST when an automated test will pop game windows on their screen.**
- Their symptom framing can point at the wrong layer — **read the log evidence before assuming.**
  "DBNO isn't triggering" was false; the log had the full down→bleed→died cycle. The real issue was
  audio audibility.
- When they say *"increase the vignette more"* during a specific state, they want the feature **kept
  and strengthened**, not disabled. Reinforce the existing feel; don't remove it.
- When they say *"X used to work and broke when we did Y"*, **trust that** and go to git history /
  the buglog / memory FIRST. Do not spend hours re-deriving from live code. And when reverting Y,
  **diff every file Y touched against the original engine** — a partial revert leaves orphans (that
  is exactly how the turret-camera regression survived a "full revert").

---

## Testing

> **"Do the commands yourself and watch console yourself."** — 2026-07-19

The user is the **sole tester**. Never hand them debug homework (`set <cvar> 1`, act, relay a
console reading). Drive the console yourself over rcon and read `qconsole.log`. Tooling is already
in place — see [01-project-map.md](01-project-map.md) §4.

> **"You might want to watch console every time you deploy too, just in case we are missing any
> problems."** — 2026-07-27

**After EVERY deploy + boot, sweep the WHOLE log, not just the feature under test.** Report anything
new even if unrelated to the current bug. Treat `Couldn't load X` as a real defect until both
existence and format are verified.

**ALWAYS build + deploy before telling the user to test.** Multiple fixes were edited in source and
left undeployed; the user tested the old build and reported "did not change anything". Source edits
are invisible in-game until `build.ps1` (scripts/cfg/textures) or a rebuild + manual copy (fgame/exe).

---

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

## Tuning workflow

- **Live visual tuning, then bake.** Add `CVAR_ARCHIVE` cvars read every frame, dial them in-game by
  eye, then bake the final values as compiled defaults. This is the established pattern for ADS
  offsets, turret cameras, post-FX, and AI timers.
- **When re-baking from a CROUCH tuning pass, edit ONLY the 5 crouch fields per gun.** *"PLEASE ONLY
  UPDATE CROUCH"* (emphatic). `adssave` logs both stand and crouch even in a crouch pass — ignore
  the stand line. Bake via a script that keeps the first 5 stand tokens verbatim.
- **A `CVAR_ARCHIVE` cvar with a stale saved value silently re-breaks features.** `omconfig` is
  rewritten on game exit, so scrubbing a bad archived value only sticks if the game is closed
  afterwards. If a behaviour-gating cvar MUST be a fixed value, hard-code it in the engine.
- **NEVER `seta` a user-facing PREFERENCE in `autoexec.cfg`** — exec order is `default.cfg` →
  `menu.cfg` → saved `configs/omconfig.cfg` → **`autoexec.cfg` LAST**, so every autoexec `seta`
  clobbers the user's menu choice each launch. There is no set-if-unset command. Preferences =
  engine registration default + `CVAR_ARCHIVE`; `coop_defaults.cfg` holds the menu-controlled
  options. autoexec `seta` is only for shipped TUNING defaults deliberately re-asserted per release.

---

## Documentation and memory hygiene

- **`.wolf/buglog.json` is the record that still works** because it is structured and keyed. Keep
  logging to it: read the tail, take `max(numeric id)+1` immediately before writing, verify with
  `json.load` and an entry-count check afterwards, and copy the file aside first.

---

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

## Gore is permanent, and everything stays killable (2026-08-03)

> **"I don't ever want blood wiped from any model... All models should be susceptible to complete
> annihilation by shooting them even if dead."**

Two standing rules, both stronger than they sound:

1. **Blood is never removed once applied.** Any code path that clears a gore skin tier, resets
   `m_iCoopGoreSkinTier`, or re-asserts a surface skin without preserving the blood bits is a
   defect. This already bit once: `CG4Aglider.tik`'s bank anims re-asserted `-skin1 +skin2` and
   wiped the bloodied windscreen seconds after it appeared (bug-1316). When adding a skin tier,
   check every OTHER writer of that surface before shipping.
2. **Corpses must remain shootable and destructible.** `Actor::BecomeCorpse`
   (`fgame/actor.cpp:12198`) currently does `setContents(CONTENTS_TRIGGER)` + `setSolidType(SOLID_NOT)`,
   so a body cannot be hit at all once it drops - that is retail's anti-stuck measure, and it is
   the reason "annihilating" a corpse does nothing today. The fix must keep bodies out of the
   PLAYER movement mask (or players snag on them) while putting them back in the SHOT trace mask.
   Not a one-liner; scope it properly.

## Instrument BEFORE fixing - standing instruction (user, 2026-08-10)

> "let's make it the standard practice to always build probes first to test"

For any defect whose cause is not already proven, **ship a measurement pass first and a fix second**.
Do not spend a playtest cycle on a guess.

The evidence from one session:

| Approach | Outcome |
|---|---|
| Scene actors: A3 probe run, THEN fix written against the data | worked first try; also revealed the planned fix keyed on data that does not exist yet at that moment, so it would have shipped clean and fixed nothing |
| Card players: three fixes written from code reading | all three failed; the real writer was a system no review had named |
| Blueprint pickup: EIGHT resolver attempts by inference | all eight failed. The ninth printed the four filter fields and settled it in one run: the filter never rejected anyone: the cross-file helper call returned NULL (bug-1665) |
| Team revive: two fixes by inference | both failed; only instrumenting moved it forward |
| "White distant objects": six hypotheses, each deployed | a whole day, nothing changed. *"I dont feel like this has helped at all"* |

When inspection says the wiring is correct, say so and ask for an empirical A/B — never ship a
guess to fill the silence.

**Rules for the probe itself** (each learned by getting it wrong):
- initialise every accumulator - an unset local reads as `none`, `none + float` throws, and a Script
  Error SKIPS the statement, so the probe emits errors instead of data;
- do not reuse an existing marker name, and place the print where the thing being measured actually
  happens (below early-exit rejects, not above them);
- gate on `coop_aggroDebug`, and arm it from a cfg that runs AFTER `autoexec.cfg` - a `+set` on the
  command line is overridden by the shipped autoexec and the probe stays silent;
- **verify the probe is live before asking for a test** (rcon read the cvar, confirm the marker
  appears) rather than assuming it armed.
