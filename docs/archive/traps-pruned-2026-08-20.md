# TRAPS.md passages pruned 2026-08-20

Moved out of `docs/TRAPS.md` on 2026-08-20 to get that file back under its 60 KB ceiling
(it had reached 71,602 bytes / 1,006 lines and 32 `## ` sections, ~12 of them appended
outside the T1..T20 taxonomy).

**Nothing here was deleted from TRAPS.md — it was compressed or merged.** Every rule, bug id,
`file:line` anchor and engine-constant name in these passages still appears in TRAPS.md, verified
mechanically (anchor-set diff before/after). What this file preserves is the **fuller original
wording**: the war-story detail, the measured numbers and the reasoning chains that were shortened
so the rule would stay legible.

Read TRAPS.md first. Come here only when you want the long form of one of these passages, or when
you are reopening the specific bug it came from.


**How to read this file.** The prune ran in rounds, and each round appended the text it replaced.
Sections above the first `---` divider (and the block titled *TRAPS.md passages pruned 2026-08-20*)
are extracted from the **true pre-prune file** (71,602 bytes). The later "Round-N originals" blocks
are intermediate states - already-compressed text that a subsequent round shortened again - so they
overlap each other. If you want the authoritative original wording of anything, use the first block
or `git show <pre-prune-commit>:docs/TRAPS.md`.

---

## T1 - the empty-RHS parse killer (bug-1908), full original wording

> original `docs/TRAPS.md` lines 27-36

> **An assignment with no value is a parse killer, and the error points at the WRONG line**
> (1908). `level.coop_loRosterTab[69] = ` with nothing after the `=` makes the parser read
> the *next* statement as the missing value, then die on **that** statement's `=` -
> `syntax error, unexpected TOKEN_ASSIGNMENT` reported against a line that is perfectly
> correct. Note the rule is **not** "the line ends with `=`": a bare trailing `=` is a legal
> line continuation and retail `global/MountGunOrPlantCharge.scr` relies on it. It is only
> fatal when the following code line is itself an assignment. `docs/tools/check_empty_rhs.py`
> now runs on every build. This one shipped from a **generator** rendering an empty column,
> which is the lesson: a generated file needs its inputs validated, because the generator
> will faithfully emit whatever the table says - including nothing.

---

## T2 - the full 'Rules that came out of it' bullets

> original `docs/TRAPS.md` lines 114-130

**Rules that came out of it:**
- Any file whose content comes from zip bytes must be written back in **binary** mode. **This
  applies to the READ side too, and to ordinary repo files.** `open(p, encoding=...)` performs
  universal-newline translation on read, so a CRLF file arrives as LF; patterns you built with
  `
` then match nothing, and writing back with `newline=""` flips the **whole file** to LF.
  Both halves fail *silently* — `str.replace` returns the string unchanged rather than raising.
  Edit `.scr` in `rb`/`wb` throughout, and note the tree is **not uniform**: `challenges.scr` is
  CRLF, `lobbyui.scr` is LF-only. Detect per file, and **assert the match count before every
  replace** — that assert is what caught it. (bug-1363)
- **Never** emit script files through a bash heredoc.
- **Verify the invariant you claim to preserve, against the ORIGINAL.** The seam regression above was
  caught only by measuring edge-wrap error on output vs input per file. "It looks fine" would have
  shipped it. Same class as the count/balance asserts: cheap, mechanical, and it fired first try.
- **Assertion gates, not review.** Review never held. What worked: balance asserts, zero-stale-ref
  asserts, count asserts (`assert NS == 76`), bug-1009's connectivity flood-fill gate. Make the
  generator fail loudly rather than trusting the reader.

---

## T3 - bug-1687, a guard written for one question

> original `docs/TRAPS.md` lines 147-155

**⭐ A GUARD WRITTEN FOR ONE QUESTION IS WRONG FOR THE NEIGHBOURING ONE (2026-08-10, bug-1687).**
`coop_isProtectedActor` answers *"should the AI-dynamics layer leave this actor alone"* and on
m2l2a says **yes to the entire cast** (14 actors named `ai_alarm`, anything with an `alarmthread`,
every papers checker, the scene actors). Reused unchanged to answer *"who would notice a corpse"*
it vetoed everybody, and two guards walked past a body twice with no reaction. **Before reusing a
predicate, re-read what it was written to decide** — and when the answers differ, split it rather
than widen it: detection now filters on nothing, while the *role* uses a narrower `coop_bustCanKneel`
that vetoes only the two reasons that actually apply. The original is untouched, because the
containment sweep still needs it.

---

## T3 - bug-1685 / bug-1860, gating one entry point

> original `docs/TRAPS.md` lines 158-165

`enableClickablePapers`, `forcePapersInHand`, and the persistent `coop_papersAnytime`. Two carried
the `coop_busted` guard; the third took a playtest to find, and until then pressing fire to shoot
equipped the papers instead and swallowed the trigger for two seconds ("he just doesn't shoot").
**Grep for every writer of the shared state before calling a gate complete.** Second
instance, 2026-08-17, in our own tooling: `docgen.py` applied `SELF_EXCLUDE` to the porcelain FILE
LIST but not to the `git diff --shortstat` it embeds in CHRONOLOGY, so every `build` changed the
number CHRONOLOGY reports about itself and **`check` could never pass** - the staleness oracle the
whole doc set rests on was permanently red, which trains everyone to ignore it (bug-1860).

---

## T3 - bug-1671, our own guard disabled the retail mechanism ($naxos)

> original `docs/TRAPS.md` lines 167-176

**A third shape, and the most embarrassing: OUR OWN GUARD DISABLED THE RETAIL MECHANISM.**
Twice in one day (2026-08-10). On m2l2a, `$naxos` is a `trigger_multiple` with `spawnflags 128` =
`TRIGGER_DAMAGE`, so the engine gives it `takedamage = DAMAGE_YES` + `CONTENTS_CLAYPIDGEON`
(`trigger.cpp:285-289`) - **shooting it is how retail completes that objective**. Our stealth
workaround opened with `$naxos nottriggerable` so the quiet route could control the timing, and
thereby deleted the retail solution; the user reported "shooting it dont do anything" (bug-1671).
Same shape as the limp above, where a *warning* disabled its own feature. **Before adding a guard,
ask what the vanilla mechanism for this already is** - and when a user says "this is how vanilla
handles it", go read the ENTITY, not the scripts around it. The first fix attempt here built a
whole damage-watcher on the wrong entity because it never asked what `$naxos` actually was.

---

## T3 - a guard keyed on data that does not exist yet (alarmthread timing)

> original `docs/TRAPS.md` lines 208-214

A guard can key on data that does not exist yet at the moment it runs (2026-08-10, measured).**
The planned scene-actor exemption tested `alarmthread != NIL`. Instrumentation showed
`coop_apply_personality` fires on all 55 germans **23 seconds before** `alarm_system_setup` assigns
any `alarmthread` - so the exemption would have matched NOTHING, shipped clean, and passed its own
acceptance check vacuously. Same class as a director that tags actors before the map has named them.
**Before writing a heuristic, print the keys it depends on and confirm they are populated at that
instant.** This is why the fix pass is instrumented first and repaired second - A3 before A4.

---

## T3 - scene6 / scene7, a vanilla scene reachable only from a BSP trigger_once

> original `docs/TRAPS.md` lines 216-224

**A vanilla scene reachable only from a BSP `trigger_once` never runs in coop (scene6; again
scene7, 2026-08-17).** m3l3's `main` carries seven `//thread sceneN` lines noted "called from a
trigger_once in the bsp". Those triggers do not fire on a coop server, so each scene stays dead
until something threads it. scene6 got a one-off workaround (`coop_churchApproach` threads it),
which hid the pattern instead of exposing it - so scene7 shipped asleep: no crews, no MG nests, no
firing nebelwerfers, and a final objective that could never complete. The cheap test: a whole
session log held **zero** occurrences of the string `scene7`. When integrating a map, grep its
`main` for commented-out `sceneN` threads and account for every one, then guard each scene
(`level.coop_sceneNStarted`) so the BSP trigger and your call site are both safe entries.

---

## T5 - entities as thread parameters, and the bug-1665 nine-attempt escalation

> original `docs/TRAPS.md` lines 316-337

Entities as `thread` parameters can arrive NIL — and a cross-file helper can return NULL
outright (bugs 1624, 1632, 1665: three sightings).** Numbers always
bind; a player or model entity passed to `thread label a b c` may not survive the boundary (and an
ENTITY-thread `ent thread label x` binds at most ONE arg). The reliable pattern: park the entity in
a **level array keyed by numbers** (`level.coop_bpEnt[n + "_" + entnum] = ent`; precedent
`level.coop_itemPapers`) and pass only numbers; re-read the array each tick, which also self-heals
across respawns.

**⭐ The 2026-08-10 escalation (bug-1665, NINE attempts).** It is not only parameters. A
`waitthread <otherfile>::<helper>` can return **NULL** while an inline scan of the *same data on
the same tick* succeeds. `player_closestTo` returned NULL on **90 consecutive measured samples**
while a probe twelve lines below read both players fine (`hp=750 team=allies act=1 noclip=0`) and
printed a `want=` entnum matching a live player. Contributing shape: that label is declared with
TWO params (`local.object local.origin`) and every caller passes ONE, so `local.origin` is an
unset local inside the function. **Diagnostic rule: when a helper "returns nothing", do not
re-derive its inputs — print INSIDE the helper and inline the same scan in the caller. If the
inline scan works, stop using the helper.** Eight of the nine attempts failed by reasoning about
which filter rejected the player; the ninth printed all four filter fields and proved none did.

**Still open:** `global/vehicle_warning.scr` (4,270 casts, second-worst source) was **never
extracted** — the retail version is still live. And a second vehicle-crew spawn path on t2l2/t3l2
that the `truck_load` guard does not cover.

---

## T6 - imported third-party skin packs (39-pack sweep)

> original `docs/TRAPS.md` lines 375-383

**⭐ Imported third-party skin packs are this trap with the blast radius reversed.** A 2002-era MOHAA
skin pk3 routinely *redefines* stock shader names rather than minting its own, and because the coop
pak mounts last the import wins - silently repainting every other model in the game (one pack
redefined all 15 `viewsleeves*` shaders for a single pilot skin; another broke the holster on *every*
skin). Evidence, 39-pack sweep: `docs/proposals/skin_batch.md`. **Before importing any external pack,
diff its top-level shader block names against `hzm-mohaa-coop-mod/scripts/*.shader` and the retail
paks, and diff its `models/player/*.tik` basenames against the stock tiks** - a matching tik basename
*replaces* the stock model instead of adding one. Both checks are two greps. Note `map foo.tga`
resolves extension-agnostically, so a shader naming `.tga` beside a shipped `.jpg` is **not** missing.

---

## T7 - the g_gametype LATCH table row (bug-1492), full original wording

> original `docs/TRAPS.md` lines 437-437

| **⭐ `g_gametype` is LATCHED — the FIRST map of a launch runs before it applies.** `ui_startdmmap 2` sets it, the engine answers *"g_gametype will be changed upon restarting"*, and the real change lands at the **next** map load (observed 59 s later). So map #1 initialises with `g_gametype` **0**, `coop_mod/variables.scr:38` caches `level.gametype = 0`, and **`variables.scr:89`'s `if(level.gametype == 0){ end }` aborts the entire coop init** — after which every coop check takes its SP branch, including `replace.scr::waitForPlayer:105`, a raw `level waittill spawn` that throws — so it does not WAIT, and coop setup races on without players. Clients connect, get kits, never spawn. **Seed `+set g_gametype 2` on the command line.** | First map of a run has no coop; later maps in the same rotation are fine | 1492 |

---

## T20 - the papers-race paragraph (bugs 1709, 1726, 1732, 1735, 1736)

> original `docs/TRAPS.md` lines 773-787

**A flag two systems both own is a race, and it comes back.** `coop_clickablePapersEnabled` is set by
`enableClickablePapers` and cleared by `coop_bustArm` to end the papers loop when a bash starts.
Anything re-arming it mid-bash restarts that loop, whose force-equip branch puts papers into the hand
already holding the drawn pistol - the gun alternates with `(none)` and **the player cannot shoot**.
Three unrelated causes, one symptom: a 0.5s re-check (1709), a squad-wide clear on papers ACCEPT plus
the re-offer answering it, and per-target threading that stacked loops so one clear stopped only the
newest (1726). Deduping was **not** sufficient (1732): one loop still steals the gun, since its guard
`coop_activeWeapon == NULL` means both "hand is empty" **and** "no raise ever finished", and in a bust
the second is true. Then `coop_busted` became the overloaded one twice within the hour - an
idempotence guard turned into an unconditional `end` once `bust.scr` set the flag earlier (1735), and
the flag cleared only on the success path, so a surviving guard left the player flagged for the
mission (1736).
> One writer per player at a time; clear the flag and yield a frame before threading a loop that sets
> it. **Split the latch from the state, and clear it on every exit, not just the happy one.** Moving
> a flag's assignment earlier silently rewrites every guard that reads it - grep them all first.

---

## Merged into T16: 'A scripted conversation strands when a waittill outranges its guard' (bug-1579)

> original `docs/TRAPS.md` lines 838-859

## A scripted conversation strands when a `waittill` outranges its guard (bug-1579)

Retail chatter helpers assume single-player: the talkers are always alive and idle. Coop breaks all
three assumptions, each with its own failure shape:

- **The `waittill` sits OUTSIDE the guard that started the anim/say.** No anim was issued, so nothing
  can fire `animdone`/`saydone` and the calling sequence stops **forever**. Wait only on an actor you
  actually animated - record it in a local; never re-test the condition (one that was attacking when
  the anim was skipped, and has since calmed, passes the retest and waits for nothing).
- **`isalive` on a NULL entity throws, and a thrown statement is SKIPPED** - so the guard itself
  disappears and the body it protected runs unguarded. Test `!= NULL` first and *separately*.
- **`thinkstate != "attack"` is not "idle".** A CURIOUS / GRENADE / PAIN actor runs its own think and
  overrides the scripted idle anim. Gate on `== idle`: `anim` runs at `THINKLEVEL_IDLE`
  (`Actor::PlayAnimation` -> `SetThinkIdle(THINK_ANIM)`, `actor.cpp:10819`) and there is no
  `THINKSTATE_ANIM`, so a normal scripted exchange stays `idle` and is not silenced.

**Silence the LINE, never abort the THREAD.** The tail of these labels usually holds the RELEASE —
a `runto`, an `enable_ai`, a `type_disguise` — that hands the actors back to normal AI. Ending the
sequence early leaves them frozen: unresponsive, and dying on their feet with no death animation.
The one safe exception is a dead-end label nothing waits on (verified: `M1L3c` radio room).

Sites, counts and remaining work: **docs/OPEN.md**. Helper `replace.scr::convOk`.

---

## Merged into T16: 'Missing anim + waittill = a corpse standing at the wall' (bugs 1921, 1945)

> original `docs/TRAPS.md` lines 879-893

## Missing anim + waittill = a corpse standing at the wall

`setmotionanim` with an alias the model does not have silently no-ops - and the
`waittill flaggedanimdone` after it then hangs that handler FOREVER (bug-1921: corner cover
users frozen upright when dead, or alive mid-grenade). Three rules: (1) never feed a
per-weapongroup anim name to setmotionanim without a whitelist + fallback (the Cornering wall
set is LIVE for exactly rifle/pistol/mp40/mp44/bar/thompson/sten/vickers); (2) when auditing
what anims exist, grep the tiki TEXT for aliases - an skc FILENAME probe undercounts badly,
because aliases point many names at shared skcs (only 2 groups have wall_death skc files; 8
have live aliases); (3) an alias existing in `models/human/animation/human_<wg>.tik` is NOT
resolvable at runtime unless that pack is `$include`d by the model - vanilla gates the packs
inside per-map "includes" blocks, so a coop feature must add the pack unconditionally to our
`new_generic_human.tik` override (bug-1945: alert scan / floorcrawl / dropgun / surrender all
erred "unknown animation" on every model until human_mp40/rifle/sten/vickers/pistol +
scripted/scientist joined the MP44/BAR/MG42 unconditional set).

---

## Merged into T17: 'Actor weapon swap is a SETTER property, not a command' (bug-1943)

> original `docs/TRAPS.md` lines 895-905

## Actor weapon swap is a SETTER property, not a command

`EV_Actor_SetWeapon` is EV_SETTER: `self.weapon = "models/weapons/x.tik"` works,
`self weapon models/weapons/x.tik` does not exist as a command - which is why retail's own
attempts at post-spawn swaps sit commented out in m1l2a/m5l3. Reading `self.weapon` on an
ACTOR returned raw `m_csWeapon` - the loadout string exactly as some script/tik wrote it
("mp40", a full path, any case, or EMPTY for tik-armed actors) - NOT the tik `name` field the
PLAYER getter returns; a display-name-keyed lookup on it missed 100% (bug-1943, caught by the
behavior odometer's variant=0). Since 2026-08-19 the engine getter returns the HELD weapon's
name field ("Mauser KAR 98K") with the raw fallback when unarmed. String-keyed array LOOKUPS
on it are still case-sensitive even though `==` is not (bug-1916 family).

---

## Merged into T8: 'Client exec/vstr INSERT at the buffer front; only stufftext APPENDS'

> original `docs/TRAPS.md` lines 919-930

## Client `exec`/`vstr` INSERT at the buffer front; only stufftext APPENDS

Verified in cmd.c: `Cmd_Exec_f` and `Cmd_Vstr_f` call `Cbuf_InsertText` - a click's whole
cfg chain runs depth-first, atomically, in textual order. The 2026-08-18 "exec APPENDS"
rationale (commit d2e7084 and a loadoutpick.scr comment) is WRONG about the engine; the
server-visual strip stays correct for a different reason - server stufftext arrives frames
later over the WIRE (Cbuf_AddText) and always lands after the client's instant chain.
Ordering rules that follow: (1) within one client chain, LAST textual line wins - s<n>sel.cfg
correcting coop_loMvPN on its final line only works because of insert semantics, so do not
"fix" it by moving the line earlier; (2) any server echo races the client's next click by one
round trip and can revert an instant preview - never send server echoes for state the client
already set correctly.

---

## Merged into T8: 'The name bus dispatches ONE token per ~0.75s batch'

> original `docs/TRAPS.md` lines 932-939

## The name bus dispatches ONE token per ~0.75s batch - every other stacked token is destroyed

playerNameCommand walks the token indexes and breaks at the FIRST with data; playerCleanName
then truncates the name at the first " ,", destroying the rest. Dispatch priority is BUS INDEX
order, not click order (skin 31 > helmet 35 > weapons 42-45 > menu 46 > pins 47 > finishes
48-51). Rapid armory clicking therefore silently drops actions - helmets/skins got close-time
commit replays for exactly this (bug-773); weapons/finishes have none. Any new bus feature
must either tolerate drops (archived-seta + join replay) or add a close-commit.

---

## Merged into the turret section: 'AI spread is an average - 2-arg bulletspread half-applies'

> original `docs/TRAPS.md` lines 861-867

## AI spread is an average - 2-arg bulletspread half-applies to AI shooters

`Weapon::Fire` gives a NON-client owner `(bulletspreadmax + bulletspread) / 2`. Most tiks never
set a max, so a script `bulletspread 120 120` averages with 0 into an effective 60 and the tune
feels dead (bug-1920, m3l3 MG42s "still hit every single shot"). Any spread tune aimed at AI
must set all four args: `bulletspread B B M M`. Player fire uses a different formula (base/max
lerp by spread factor), so player-facing tunes are unaffected.

---

## Merged into the turret section: 'TurretGun fixes NEVER reach VehicleTurretGun'

> original `docs/TRAPS.md` lines 869-877

## TurretGun fixes NEVER reach VehicleTurretGun

`VehicleTurretGun` overrides `Think()`, `UpdateFireControl()` and `GetMuzzlePosition()` - so
anything tuned in TurretGun's paths silently skips every vehicle-mounted gun (halftrack, tank
hull MG, jeep). THREE separate user reports traced to this one split on 2026-08-19: player MG
heat never cycling (bug-1946), and AI road gunners laser-accurate at full damage because the
whole coop tuning trio - damage scale, spread bonus, wandering aim error - was TurretGun-only
(bug-1950). Rule: any turret-behavior change ships BOTH class paths, or states in a comment why
the vehicle side is exempt. The trio is extern'd in weapturret.h for exactly this.

---

## Merged into the turret section: 'A MANNED turret never reads bulletspread'

> original `docs/TRAPS.md` lines 941-951

## A MANNED turret never reads bulletspread - the AI knob is `aibulletspread`

Three separate "fixes" tuned `bulletspread` on m3l3's MG42s and every one was a placebo
(bug-1940): weapon.cpp's FT_BULLET assigns vSpread only for owner->client (players); the
(max+base)/2 fallback is for owner==NULL - unmanned guns, which do not fire. An actor-manned
turret fires with vSpread=(0,0,0); its ONLY dispersion is m_vAIBulletSpread, applied at the
muzzle and set solely by the `aibulletspread` script event (retail SH/BT use 300-450; the
OpenMOHAA handler ignores arg 2). Gunner `accuracy` keys also do nothing for turrets (only
Actor::GunTarget consults accuracy, and turret aiming never calls it). coop_mg42AiSpread now
feeds the real member. Rule: before tuning a value, prove the failing PATH actually reads it -
grep the consumer, not the setter.

---

## The 'Script Error does NOT kill the thread' section, full original wording

> original `docs/TRAPS.md` lines 812-836

## ⭐ A `Script Error` does NOT kill the thread — it SKIPS the statement (verified 2026-08-06)
**This corrects a premise that shaped many earlier diagnoses, including several in this file.**
`ScriptException::next_abort` defaults to **0** (`script/scriptexception.cpp:30`), and
`ScriptVM::HandleScriptException` (`script/scriptvm.cpp:1915-1933`) only rethrows `if (exc.bAbort)`;
otherwise it prints `^~^~^ Script Error : …` and **returns**. The `catch` sits *inside* the
per-instruction loop, so execution resumes at the **next instruction**. Only **two** sites in the
whole VM set `next_abort = -1`: stack overflow (`scriptvm.cpp:1038`) and **command overflow**
(`:1867`) — the latter is `ERR_DROP` and really does take the server down (see t2l3, bug-1493).

**So read every error site as "this statement was skipped", not "everything below died."** The
consequences are different and often worse:
- **An `invalid waittill` means the script does NOT WAIT.** Everything below runs *immediately*
  instead of at the right moment — sequences fire before their preconditions, entities are touched
  before they spawn. That is why the `waitTillSpawn`/`waitTillPrespawn` shims still matter
  (bugs 1458-1469): they were fixing a real defect, just not the one the note claimed.
- A cast error inside a `while` body removes the *statement*, not the loop — which is exactly how
  t2l3 span 4,347 times with no yield and killed the server.
- **Values parsed out of a `.dat` file are STRINGS** (bug-1352). The character-walking splitters
  (fogmode, blueprint, save files) return strings, so a later `if( x > 0 )` throws and *that
  assignment never happens* while the caller prints its success message. Coerce with
  `float()`/`int()` at load. Tell: works when set live, never when loaded from its own save.
- **A probe that throws prints nothing** while filling the log with errors — so it is silently
  useless on exactly the cases worth watching. Sanitise every field before concatenating:
  an unset var reads `none`, and `"str" + none` throws (bugs 1702, and the SPAWNDISG probe
  before it, both the same day).

---

## Moved out of TRAPS.md entirely: 'Archived client state keyed by POSITION' (bug-1926)

> Single confirmed instance, not a recurring family — TRAPS.md's own bar. Kept here in full;
> a one-line pointer remains in TRAPS.md under T7.

## Archived client state keyed by POSITION rots on every catalogue change

`coop_pin1..5` stored catalogue row indices (`CVAR_ARCHIVE`) — the panzerfaust removal shifted every
later row by 3 and silently repointed every player's pins at different challenges (bug-1926).
Positional archived state (`coop_uiN`/`uiD`/`uiP` row cvars) shows the WRONG rows' data offline after
any renumber. The rules: (1) **persist IDs, never positions** — the server half of the pin system said
so in a comment while the client half did the opposite; (2) any positional cache that must exist gets a
GENERATION STAMP (crc of the id list, emitted by the same generator as the pages) and is wiped on
mismatch — blank beats wrong, the next join re-exports truth; (3) a generated lookup map must be `set`,
not `seta` — an archived map satisfies the "is it loaded?" probe forever and the current one never
loads.

---



---

# Longer original wording of passages tightened in the 2026-08-20 final pass

> Rules, bug ids and `file:line` anchors for all of these remain inline in TRAPS.md; only the
> mechanism narrative was shortened. Kept here verbatim as it stood before that pass.


## T20 - the four disguise/latch paragraphs

**A flag that answers two questions gets tested for the wrong one.** `is_disguised` is the engine's live
opinion, recomputed per frame (`player.cpp:5519-5545`): has a disguise, no alarm, nothing real in hand,
*and* nobody attacking you with real threat. `has_disguise` is the fact the mod's own grant sets. They
agree most of the time, which is what makes this expensive. Testing `is_disguised` where `has_disguise`
was meant read "someone is shooting at you" as "the grant failed" in two places (bugs 1701, 1701b,
1703), each re-running the whole disguise grant from a frame-rate loop, flipping gametype twice per pass
and resetting every AI think state (13-14/sec sustained). The tell was **the player's own viewmodel and
HUD stuttering** — AI churn alone does not stutter a client.
> Before testing a state flag in a retry, ask how many different things can make it false. If more than
> one, prefer the flag your own code sets. And **bound every self-re-threading retry**: a predicate that
> stays true burns a core until map end.

**Bare `attackplayer` is permanent, and lives in more files than you grepped.** It is
`Actor::ForceAttackPlayer`, setting `m_bForceAttackPlayer`, cleared **only in the Actor constructor**
(`actor.cpp:3092`); while set, `EnemyIsDisguised()` returns false unconditionally, so one call blinds
that actor to every disguise for the rest of the map. `attackentity <ent>` is the advisory, reversible
form. Four sites took **three sweeps** because the first two only grepped `aihandler.scr` (bugs 1700,
1704, 1708); every one already had a usable target a line or two above.
> Sweep the whole tree for a one-way primitive, not the file you found it in. Comment legitimate
> no-target fallbacks so the next sweep can tell them apart.

**An absorbing state hides everything downstream.** `EnemyIsDisguised()` also returned false for any
actor in `THINKSTATE_ATTACK`, so an actor that entered attack for any reason could never be fooled
again — and with the veto above it ratchets: each hostile that shoots you blanks your disguise for a
frame, which flips more actors. Fixed by requiring real threat (bug-1707), the same treatment
`player.cpp:5541` already had. Blocked-aggro across one run: **1051 → 0**.

**A flag two systems both own is a race, and it comes back.** `coop_clickablePapersEnabled` is set by
`enableClickablePapers` and cleared by `coop_bustArm` to end the papers loop when a bash starts; anything
re-arming it mid-bash restarts that loop, whose force-equip branch puts papers into the hand already
holding the drawn pistol — the gun alternates with `(none)` and **the player cannot shoot**. Three
unrelated causes, one symptom: a 0.5 s re-check (bug-1709), a squad-wide clear on papers ACCEPT plus the
re-offer answering it, and per-target threading that stacked loops so one clear stopped only the newest
(bug-1726). Deduping was **not** sufficient (bug-1732): one loop still steals the gun, since its guard
`coop_activeWeapon == NULL` means both "hand is empty" **and** "no raise ever finished", and in a bust
the second is true. Then `coop_busted` became the overloaded one twice within the hour — an idempotence
guard turned into an unconditional `end` once `bust.scr` set the flag earlier (bug-1735), and the flag
cleared only on the success path, so a surviving guard left the player flagged for the mission
(bug-1736).
> One writer per player at a time; clear the flag and yield a frame before threading a loop that sets it.
> **Split the latch from the state, and clear it on every exit, not just the happy one.** Moving a flag's
> assignment earlier silently rewrites every guard that reads it — grep them all first.


## T16 - setmotionanim three rules

**Missing anim + `waittill` = a corpse standing at the wall.** `setmotionanim` with an alias the model
does not have silently no-ops, and the `waittill flaggedanimdone` after it hangs that handler FOREVER
(bug-1921: corner-cover users frozen upright when dead, or alive mid-grenade). Three rules: (1) never
feed a per-weapongroup anim name to `setmotionanim` without a whitelist + fallback — the Cornering wall
set is LIVE for exactly rifle/pistol/mp40/mp44/bar/thompson/sten/vickers; (2) audit what anims exist by
grepping the tiki TEXT for aliases, since an `.skc` FILENAME probe undercounts badly (only 2 groups have
`wall_death` skc files; 8 have live aliases); (3) an alias in `models/human/animation/human_<wg>.tik`
is NOT resolvable at runtime unless that pack is `$include`d by the model — vanilla gates the packs
inside per-map `includes` blocks, so a coop feature must add the pack unconditionally to our
`new_generic_human.tik` override (bug-1945: alert scan / floorcrawl / dropgun / surrender all erred
"unknown animation" on every model until human_mp40/rifle/sten/vickers/pistol + scripted/scientist
joined the MP44/BAR/MG42 unconditional set).


## T17 - EV_SETTER actor weapon paragraph

**Some engine events are SETTER PROPERTIES, not commands.** `EV_Actor_SetWeapon` is `EV_SETTER`:
`self.weapon = "models/weapons/x.tik"` works; `self weapon models/weapons/x.tik` **does not exist as a
command**, which is why retail's own post-spawn swaps sit commented out in m1l2a and m5l3. (Command
syntax on the getter half of this class is a T1 parse killer, bug-910.) Reading `self.weapon` on an
ACTOR returned raw `m_csWeapon` — the loadout string as some script/tik wrote it ("mp40", a full path,
any case, or EMPTY for tik-armed actors) — **not** the tik `name` field the PLAYER getter returns, so a
display-name-keyed lookup missed 100% (bug-1943, caught by the behavior odometer's `variant=0`). Since
2026-08-19 the engine getter returns the HELD weapon's name field ("Mauser KAR 98K") with the raw
fallback when unarmed. String-keyed array LOOKUPS on it are still case-sensitive even though `==` is not
(bug-1916 family).


## T5 - storm root cause, repair pattern, thread-param escalation

**Root cause of the biggest storm:** `addon_*` markers carry their model in `$ai_model`, not `.model`,
so `spawner_create` recorded NIL and the engine spawned `models/nil.tik` in a loop — an entity leak as
well as log spam (`global/spawner.scr:95-138`). 2026-07-22 52-map tour counts:
`docs/archive/traps-measured-wins-2026-07-22.md`.

**The proven repair pattern:** extract the retail gag verbatim from `mainta/pak1.pk3`, change **only**
the single-entity `$player` refs, add NULL host guards, leave everything else byte-identical. See
`gags/t2l4_start.scr:1-2`, `gags/t3l1_enemyspawn.scr:2`.

**Entities as `thread` parameters can arrive NIL, and a cross-file helper can return NULL outright**
(bugs 1624, 1632, 1665). Numbers always bind; an entity passed to `thread label a b c` may not survive
the boundary (and `ent thread label x` binds at most ONE arg). Park the entity in a **level array keyed
by numbers** (`level.coop_bpEnt[n + "_" + entnum] = ent`; precedent `level.coop_itemPapers`) and pass
only numbers; re-read the array each tick, which self-heals across respawns.

**⭐ The escalation (bug-1665, NINE attempts).** `player_closestTo` returned **NULL on 90 consecutive
measured samples** while a probe twelve lines below read both players fine (`hp=750 team=allies act=1
noclip=0`); the label declares TWO params (`local.object local.origin`) and every caller passes ONE.
**When a helper "returns nothing", print INSIDE the helper and inline the same scan in the caller — if
the inline scan works, stop using the helper.** Eight of nine attempts failed by reasoning about which
filter rejected the player; the ninth printed all four filter fields and proved none did.


## T6 - stale-log timing variant and third-party skin packs

**⭐ A playtest log only testifies about the build it loaded** (bug-1610). `coop_enigma.shader` existed,
yet the log still said `Couldn't find image file for shader enigma` — the client loaded 23:34 and quit
23:37:11; the file was packed at **23:38:06**. **Compare the pk3 entry's timestamp
(`zipfile.getinfo(name).date_time`) against the `InitGame` line before treating a log as evidence about
a new asset**, and verify fixes by reading them back out of the deployed pk3, not the source.

**⭐ Imported third-party skin packs are this trap with the blast radius reversed.** A 2002-era MOHAA
skin pk3 routinely *redefines* stock shader names instead of minting its own, and because the coop pak
mounts last the import wins — silently repainting every other model (one pack redefined all 15
`viewsleeves*` shaders for one pilot skin; another broke the holster on *every* skin; 39-pack sweep:
`docs/proposals/skin_batch.md`). **Diff any external pack's top-level shader block names against
`hzm-mohaa-coop-mod/scripts/*.shader` and the retail paks, and its `models/player/*.tik` basenames
against the stock tiks** — a matching tik basename *replaces* the stock model. Note `map foo.tga`
resolves extension-agnostically, so a shader naming `.tga` beside a shipped `.jpg` is **not** missing.


## T7 - archived-cvar latch and the getcvar-creates-empty finding

**An archived cvar is a latch — including one you add for debugging** (bug-1427, twice). A
`seta`-archived switch rides `omconfig.cfg` forever and re-fires on every later load (`coop_buildmap`
broke e3l4 twice in one evening); editing omconfig.cfg externally loses the race, as the engine rewrites
it from memory at shutdown. The repeat came from the other side: giving `r_novis` `CVAR_ARCHIVE` to
persist for one test wrote `seta r_novis "1"` into the user's config and cost a `0xC00000FF` startup
crash. **Consume mode-flipping cvars one-shot at map init** (copy to a level var, `setcvar` back to 0,
never a live `getcvar`), and never give a diagnostic `CVAR_ARCHIVE`.

**⭐ Script `getcvar` CREATES the cvar EMPTY, permanently defeating the engine's own default**
(bug-1669). `ScriptThread::Getcvar` is `gi.Cvar_Get(name, "", 0)` (`fgame/scriptthread.cpp:2628`), so
the first *script* read of a cvar the engine has not registered yet creates it with `""`; the engine's
later `Cvar_Get(name, "1", CVAR_ARCHIVE)` finds it existing, updates only the reset string, and **keeps
the empty value** — `->integer` is 0 forever. That is how player limping was dead: `coop_limpWarn` is
threaded at player setup (`player.scr:224`) and getcvar'd `coop_limp` before `Player::TickLimp`
registered it — **the warning system silently switched off the feature it exists to warn about** — and
it had also killed `coop_tinnitusBlast` and `coop_goreDripCorpseTime`. One trap, three dead features.


## T8 - items 5 and 6 (buffer insert order, name bus)

5. **Client `exec`/`vstr` INSERT at the buffer front; only stufftext APPENDS.** Verified in `cmd.c`:
   `Cmd_Exec_f` and `Cmd_Vstr_f` call `Cbuf_InsertText`, so a click's whole cfg chain runs depth-first,
   atomically, in textual order. The 2026-08-18 "exec APPENDS" rationale (commit `d2e7084` and a
   `loadoutpick.scr` comment) is **WRONG about the engine**; the server-visual strip is right for a
   different reason — server stufftext arrives frames later over the WIRE (`Cbuf_AddText`) and always
   lands after the client's instant chain. So within one client chain the **LAST textual line wins**
   (`s<n>sel.cfg` correcting `coop_loMvPN` on its final line only works because of insert semantics — do
   not "fix" it by moving the line earlier), and any server echo races the client's next click by one
   round trip and can revert an instant preview.
6. **The name bus dispatches ONE token per ~0.75 s batch; every other stacked token is destroyed.**
   `playerNameCommand` breaks at the FIRST token with data and `playerCleanName` then truncates at the
   first `" ,"`. Priority is **BUS INDEX order, not click order** (skin 31 > helmet 35 > weapons 42-45 >
   menu 46 > pins 47 > finishes 48-51), so rapid armory clicking silently drops actions — helmets/skins
   got close-time commit replays for exactly this (bug-773); weapons/finishes have none. Any new bus
   feature must tolerate drops (archived-`seta` + join replay) or add a close-commit.


## T14 - the 4-player coverage sweep paragraph

**Settled 2026-08-06 by the 4-player coverage sweep.** 49 walker-valid maps threw **26,230 script errors
across 548 sites**, none reported by any static audit — and they concentrate in **shared** files, so few
fixes repair many maps: `vehicle_warning.scr` 12,690 (48%), `gags/t2l3_friendly.scr` 8,694 (33%),
`gags/t3l1_enemyspawn.scr` 972, `global/spotlight.scr` 798, `coop_mod/officer.scr:1754` 666 (the mod's
**own** code, all 48 maps). The dominant cause is `$player`-as-array ([T5](#t5)) reaching a retail SP
script that dereferences `.origin` — invisible in SP *and* in 1-player coop, because `OP_UN_TARGETNAME`
yields a plain listener at one match and a container only at 2+. **It needs two connected players to
reproduce at all**, which is why years of solo testing never saw the trilogy's largest error source.


## T11 - bug-1290, shared-premise corroboration

**Agreement between reviewers is NOT corroboration when they share an upstream source** (bug-1290). A
multi-agent audit reported "the injury vignette is permanently maxed after any DBNO revive" and **two
independent critique lenses each confirmed it**. It was false: all three inherited one unchecked premise
from the same research pass, that `dbno.scr:49`'s `healthonly 9999` puts 9999 into health.
`Entity::EventSetHealthOnly` **clamps to `max_health`**, and `player.cpp:8113` writes
`stats[STAT_HEALTH]` as an already-normalised 0..100 percentage, so the tracker cannot latch and the
proposed "fix" would have hidden genuine low health. **Verify a finding's load-bearing premise against
the code yourself** — independent agents reading the same brief are one witness, not three.


## T19 - the hand-rolled pythagoras measurement

**Take the horizontal distance with `vector_length` on both points flattened to z=0** via a vector
literal (locals inside a literal are fine — `props.scr:407`, `tracescan.scr:79`), **not with hand-rolled
pythagoras.** A `sqrt( (dx*dx) + (dy*dy) )` here returned **265.965 for two points 2013u apart**, twice
across two builds, while `dz` by plain subtraction on the next line was exactly right — so the feature
fired at the spawn whatever radius was set. The same expression instrumented a build later gave correct
numbers, so no claim is made about the mechanism; what is established is that `vector_length` was right
on every sample and the hand-rolled form was not on at least one. `aimaneuver.scr:129` uses the same
inline form and has never been checked.


## Turrets - item 1, aibulletspread

**1. A MANNED turret never reads `bulletspread`; the AI knob is `aibulletspread`** (bug-1940). Three
separate "fixes" tuned `bulletspread` on m3l3's MG42s and every one was a placebo: `weapon.cpp`'s
`FT_BULLET` assigns `vSpread` only for `owner->client` (players), and the `(max+base)/2` fallback is for
`owner == NULL` — unmanned guns, which do not fire. An actor-manned turret fires with `vSpread=(0,0,0)`;
its ONLY dispersion is `m_vAIBulletSpread`, applied at the muzzle and set solely by the `aibulletspread`
script event (retail SH/BT use 300-450; the OpenMOHAA handler ignores arg 2). Gunner `accuracy` keys do
nothing for turrets either — only `Actor::GunTarget` consults accuracy, and turret aiming never calls
it. `coop_mg42AiSpread` now feeds the real member.


## T3 - UI corollary and the BSP trigger_once scenes

**The UI corollary — never trade a working widget for an unverified one.** A `.urc` cannot be run or
diffed from here and the only oracle is the user's screenshot; six attempts at one Service Record
checkmark each replaced a functioning pin box and each came back worse (bug-1546). **Add alongside it,
or wait until someone can see it render.**

**A vanilla scene reachable only from a BSP `trigger_once` never runs in coop.** m3l3's `main` carries
seven `//thread sceneN` lines noted "called from a trigger_once in the bsp", and those triggers do not
fire on a coop server. scene6 got a one-off workaround (`coop_churchApproach` threads it) which hid the
pattern, so scene7 shipped asleep — no crews, no MG nests, no firing nebelwerfers, a final objective
that could never complete, and a whole session log with **zero** occurrences of `scene7`. **Grep a
map's `main` for commented-out `sceneN` threads, account for every one, and guard each
(`level.coop_sceneNStarted`) so the BSP trigger and your call site are both safe entries.**


## T4 - archetype paragraph

**Tell:** things vanish, alias, or corrupt at high entity/model/sound counts, often with **no log line
at all** — the overflow branch discards silently. **The archetype, `maxentities 2048`:** shipped for
*years* while `GENTITYNUM_BITS` was 10 (hard cap 1024). It **added no entities; it disabled
`AllocEdict`'s overflow guard**, so the allocator handed out the world slot — a weekend of
use-after-free minidumps.


---

# Round-3 originals (2026-08-20)

> Same rule: every bug id and `file:line` anchor below is still inline in TRAPS.md.


## T20 body (round 3)

**A flag that answers two questions gets tested for the wrong one.** `is_disguised` is the engine's
live opinion recomputed per frame (`player.cpp:5519-5545`) - disguise + no alarm + nothing real in hand
+ *nobody attacking you with real threat*; `has_disguise` is the fact the mod's own grant sets. Testing
`is_disguised` where `has_disguise` was meant read "someone is shooting at you" as "the grant failed"
(bugs 1701, 1701b, 1703), re-running the whole grant from a frame-rate loop at 13-14/sec, flipping
gametype twice per pass and resetting every AI think state. Tell: **the player's own viewmodel and HUD
stutter** - AI churn alone does not stutter a client.
> Ask how many different things can make a flag false before testing it in a retry; prefer the flag your
> own code sets. **Bound every self-re-threading retry** - a predicate that stays true burns a core.

**Bare `attackplayer` is permanent, and lives in more files than you grepped.** It is
`Actor::ForceAttackPlayer`, setting `m_bForceAttackPlayer`, cleared **only in the Actor constructor**
(`actor.cpp:3092`); while set, `EnemyIsDisguised()` returns false unconditionally, so one call blinds
that actor to every disguise for the rest of the map. `attackentity <ent>` is the reversible form. Four
sites took **three sweeps** because the first two only grepped `aihandler.scr` (bugs 1700, 1704, 1708).
> Sweep the whole tree for a one-way primitive, not the file you found it in; comment legitimate
> no-target fallbacks so the next sweep can tell them apart.

**An absorbing state hides everything downstream.** `EnemyIsDisguised()` also returned false for any
actor in `THINKSTATE_ATTACK`, so an actor that entered attack for any reason could never be fooled
again - and it ratchets: each hostile that shoots you blanks your disguise for a frame, flipping more
actors. Fixed by requiring real threat (bug-1707), the treatment `player.cpp:5541` already had.
Blocked-aggro across one run: **1051 -> 0**.

**A flag two systems both own is a race, and it comes back.** `coop_clickablePapersEnabled` is set by
`enableClickablePapers` and cleared by `coop_bustArm`; anything re-arming it mid-bash restarts the
papers loop, whose force-equip branch puts papers into the hand already holding the drawn pistol, and
**the player cannot shoot**. Three unrelated causes, one symptom: a 0.5 s re-check (bug-1709), a
squad-wide clear on ACCEPT plus the re-offer answering it, and per-target threading that stacked loops
so one clear stopped only the newest (bug-1726). Deduping was not sufficient (bug-1732) because the
guard `coop_activeWeapon == NULL` means both "hand is empty" **and** "no raise ever finished". Then
`coop_busted` became the overloaded one twice within the hour (bug-1735 - an idempotence guard turned
into an unconditional `end` once `bust.scr` set the flag earlier; bug-1736 - cleared only on the success
path, so a surviving guard left the player flagged for the mission).
> One writer per player at a time; clear the flag and yield a frame before threading a loop that sets
> it. **Split the latch from the state, and clear it on every exit, not just the happy one.** Moving a
> flag's assignment earlier silently rewrites every guard that reads it - grep them all first.


## T20 lede

Both shapes cost most of 2026-08-11 on the m6l1c stealth route, because in both the symptom pointed away
from the cause.


## T16 conversation bullets

- **The `waittill` sits OUTSIDE the guard that started the anim/say**, so no anim was issued, nothing can
  fire `animdone`/`saydone`, and the calling sequence stops **forever**. Wait only on an actor you
  actually animated — record it in a local; never re-test the condition (one that was attacking when the
  anim was skipped and has since calmed passes the retest and waits for nothing).
- **`isalive` on a NULL entity throws, and a thrown statement is SKIPPED** — the guard itself disappears
  and the body it protected runs unguarded. Test `!= NULL` first and *separately*.
- **`thinkstate != "attack"` is not "idle".** A CURIOUS / GRENADE / PAIN actor runs its own think and
  overrides the scripted idle anim. Gate on `== idle`: `anim` runs at `THINKLEVEL_IDLE`
  (`Actor::PlayAnimation` → `SetThinkIdle(THINK_ANIM)`, `actor.cpp:10819`) and there is no
  `THINKSTATE_ANIM`, so a normal scripted exchange stays `idle`.


## T16 release paragraph

**Silence the LINE, never abort the THREAD.** The tail of these labels usually holds the RELEASE — a
`runto`, an `enable_ai`, a `type_disguise` — that hands actors back to normal AI; ending early leaves
them frozen and dying on their feet with no death animation. The one safe exception is a dead-end label
nothing waits on (verified: `M1L3c` radio room). Sites and remaining work: **docs/OPEN.md**. Helper
`replace.scr::convOk`.


## T11 tail

**A later entry can silently reverse an earlier one, so read the ordered LIST, not one entry.**
`docs/generated/FIX_INDEX.md` (file → ordered bug ids) is the fix: one entry says what changed once, the
list gives the file's net current state (the story belongs in HISTORY). Nothing in the schema flags a
reversal, so when you supersede a finding **edit the original entry** rather than only appending —
bug-1473/1474 were corrected in place on 2026-08-06 after being filed on the wrong files.

- **Wrong anchors are worse than no anchors.** `q_shared.h:1680` credits the `MAX_MODELS` 1024→2048
  raise to **bug-866**; the actual work is **bug-892**. A grep at a wrong path returns nothing and reads
  as "already fixed."
- *(buglog tooling hazards — id formats, append-never-rewrite — are in
  `docs/reference/buglog_maintenance.md`)*
- **28 bug ids cited in source comments have no buglog entry** — including bug-237 (packer determinism,
  `build.ps1:11-15`), bug-241 (never deploy under a running game) and bug-239 (the brace-counting
  lesson). **For those, the code comment IS the only record.**

**⭐ The habit that works:** leave the correction **at the site**. `maps/m1l1.scr:1683`,
`coop_mod/loadoutpick.scr:436-440` and `q_shared.h:1690-1755` are self-documenting and all three
survived contact with a later session. **When classifying REVERTED, separate "it broke" from "the user
changed their mind"** — only the former is a lesson; bug-787 reversed a design at the user's request.


## T12 body

**Ship risk: CLOSED (re-verified 2026-08-17).** `build.ps1:32`'s
`$excludeTop = @("_notes", "_research")` is committed and the deployed
`zzzzzz_co-op_hzm_mod_code.pk3` contains **zero** `_research`/`_notes` entries. Releases up to v1.1.55
did ship design docs and retail script extracts; that is history, not a live hazard. *(This entry
previously read "OPEN NOW" and cited an uncommitted `build.ps1:27` — both stale.)*

**Still open:** the regression harness — the project's only working automated verification — lives in a
directory named `_research`, which the build script treats as disposable. **Promote it out** before
someone applies the exclusion logic to the wrong tree. Related: four uppercase map scripts (`M1*`,
`M3*`, `M5*`, `M6*.scr`) sit alongside lowercase counterparts, unchecked for case-collision in a pak.

**The same trap one level down: two subsystems sharing a `level.*` name** (bug-1612).
`coop_mod/ambience.scr:42` owns `level.coop_ambEnt` as a **single `script_model`**; the telephone-gag
work later added `level.coop_ambEnt[alias] = emitter` as a **dictionary**. The entity wins, so every
indexed read throws `[] applied to invalid type 'listener'` — once per ambient, on every map. Skipped
not fatal, so nothing crashed; the sole casualty was m1l2b's ringing-telephone gag, which polls that
dictionary 100×0.1 s, always burned 10 s and printed `PHONEGAG FAIL`.


## T14 head

**Tell:** a map graded clean by a read-through then storms on boot. t2l2 graded **A−** statically and
throws 265 errors on coop boot — *degraded, not dead*, which is exactly why a read-through missed it.
**A live boot is the only real test.**

**Absence does not log.** A parse error screams; a VO line that never plays, a trigger nobody walks
into, an alias resolving to nothing are silent — error-driven testing cannot find them by construction.
You need an **expectation manifest** (what *should* fire, from the BSP entity lump) diffed against
**engine instrumentation** (what *did*). That is the coverage sweep.


## T2 rules

- **Binary mode on BOTH sides, repo files included.** `open(p, encoding=...)` translates newlines on
  *read*, so a CRLF file arrives as LF and `\r\n` patterns match nothing; writing back with
  `newline=""` flips the **whole file** to LF. Both fail silently — `str.replace` returns unchanged
  rather than raising. Use `rb`/`wb`. The tree is **not uniform**: `challenges.scr` CRLF,
  `lobbyui.scr` LF-only, `docs/TRAPS.md` LF (bug-1600 was this file flipped by a prune script).
  Detect per file and **assert the match count before every replace** — that assert caught bug-1363.
- **Never** emit script files through a bash heredoc.
- **Verify the invariant you claim to preserve, against the ORIGINAL** — the seam regression was caught
  only by measuring edge-wrap error on output vs input per file.
- **Assertion gates, not review.** Review never held; balance asserts, zero-stale-ref asserts, count
  asserts (`assert NS == 76`) and bug-1009's connectivity flood-fill gate did.


## T4 skeletor + cvars bullets

- **A capacity never reset is a per-SESSION budget, and it kills an INNOCENT map** (bug-1803).
  `MAX_SKELETOR_CHANNELS` fills two process-global statics zeroed only at construction; after ~28 maps
  e2l2 merely held the 2,560th channel — blameless, fine from a fresh boot. **Ask of every limit: what
  frees an entry?** If nothing does, size it against everything the game can load: a measured 4,589
  whole-game proves 2,560 always had to fall over. Resetting is NOT safe — `skelChannelList_c` stores
  *global* indices in every cached model.
- **A protocol raise ships four binaries** — see [ENGINE.md](ENGINE.md#protocol-coupling).
- **One capacity grows while nobody touches the code: `MAX_CVARS`** (bug-1582). *Archived* content
  consumes it — `omconfig.cfg` hit **3019** cvars (Service Record ~1500, armory locks ~500), crossing
  4096 a month after bug-598 doubled it. Doubling is headroom, not a cure; now 8192 + 80% warning.


## T10 body

**Tell:** a fix that is definitely in the source has no effect in play — or a log line reports a limit
lower than the header says. Both directions have happened: edited but never built/deployed (bug-089,
fixes "did nothing in-game"); and built and deployed when it shouldn't have been (bug-1172 — every
`build.ps1` run during a gl2 sandbox session pushed sandbox-only `MAX_SOUNDS 2000` /
`MAX_ENTITIES 4095` / `MAX_TIKI_ALIASES 8192` binaries into the user's **real install**).

**The exe is the usual gap.** `build.ps1` deploys the pk3s, `cgame.dll` and `renderer_opengl1.dll` —
**not** `openmohaa.exe`, `game.dll` or `renderer_opengl2.dll`, which are hand-copied to the GOG root.
The deployed set routinely spans several build dates, so a change can be live in source, in `.cmake`,
and *not* in the binary being run. **A "verified" claim must name which binaries were deployed and
when.** `build.ps1` refuses to deploy while the game is running — if you edited and did not deploy,
everything the user then tests is the PREVIOUS build and every conclusion is void.

**Rules:** a protocol-constant change ships **all four** binaries; `game.pdb`/`cgame.pdb` ship next to
their DLLs; back up as `<binary>_pre_<feature>_bak.<ext>` — that hand-run convention *is* the rollback
system, and it has 157 entries and **zero** for `renderer_opengl2.dll`.


## T19 body

**`vector_length` is a 3D distance**, so every "within N units" test is a sphere — almost never what is
meant in a building. **"Near" is a HORIZONTAL question plus a same-storey question, tested as both**: 2D
distance plus a vertical band (96u; a MOHAA storey is ~128). Three sites in one feature had it.

**Take the horizontal distance with `vector_length` on both points flattened to z=0** via a vector
literal (locals inside a literal are fine - `props.scr:407`, `tracescan.scr:79`), **not with hand-rolled
pythagoras.** A `sqrt( (dx*dx) + (dy*dy) )` here returned **265.965 for two points 2013u apart**, twice
across two builds, while `dz` by plain subtraction on the next line was exactly right - so the feature
fired at the spawn whatever radius was set. Instrumented a build later the same expression gave correct
numbers, so no claim is made about the mechanism; what is established is that `vector_length` was right
on every sample and the hand-rolled form was not on at least one. `aimaneuver.scr:129` uses the same
inline form and has never been checked.

**A range must also be the right SIZE for its job.** That feature's warning was drawn off the *action*
prompt's 112u bash range, so it only appeared once the player was already on top of the officer. Give an
advisory its own, wider range.


## T17 unmask + thread-boolean

**⚠️ Fixing a type error can UNMASK a latent logic bug.** That same line previously threw every frame,
and the throw aborted the parade's done-check — so the parade never stopped and the gate happened to
pass. Adding the correct `int()` coercion (bug-1372) made the comparison work, the parade correctly
stopped at 20, and the map became *unfinishable*. **After silencing a recurring script error, re-test
the feature it was firing in** — the error may have been load-bearing.

**`thread <label>` inside a boolean is ALWAYS TRUE** (bit 5 files at once). `thread` starts the label
asynchronously and evaluates to a HANDLE, not the return value, so `if( x && thread foo::bar )` is
`if( x && <truthy> )`. Five `anim/disguise_*.scr` gates were written this way and never guarded anything
for years — use `waitthread` when you want the value. Corollary: because the branch they guarded ends in
`end`, every statement BELOW it was unreachable whenever the branch fired (four of them, including the
squad-wide papers pass). **When you fix a condition that was always true, audit what sits below its
`end` as well.**


## T3 second shape

**A second shape: the write executes and is then overwritten.** Proving execution is necessary but not
sufficient — also prove nothing later writes the same field; in a render/view path grep the whole
function and prefer the LAST write site. The dangerous variant is a misplaced write that lands somewhere
real (bug-1238 moved the 3P pivot): silent corruption of a neighbouring feature.


## Quick index tail

Unnumbered: [`Script Error` **skips the statement**, not the thread](#script-error) ·
[turrets and AI spread](#turrets) · [`item_name` variant suffixes](#itemname) ·
[procedural view/weapon motion](#procedural) · [TIKI and sound aliases](#tiki) ·
[cross-cutting questions](#cross-cutting).

**T13** is [Cross-cutting](#cross-cutting) Q5; **T15** is `reference/harness_and_reproduction.md`;
**T18** is `archive/traps-t16-failsafe-recursion.md`. Older docs still link to `#t13` / `#t15`.


---

# Round-4 originals (2026-08-20)

> Every bug id and `file:line` anchor below is still inline in TRAPS.md.


## T20 - full body to compact rule block

- **A flag that answers two questions gets tested for the wrong one.** `is_disguised` is the engine's
  per-frame opinion (`player.cpp:5519-5545`: disguise + no alarm + nothing real in hand + nobody
  attacking with real threat); `has_disguise` is the mod's own grant. Testing the first where the second
  was meant read "someone is shooting at you" as "the grant failed" (bugs 1701, 1701b, 1703), re-running
  the grant from a frame-rate loop at 13-14/sec and flipping gametype twice a pass. Tell: **the player's
  own viewmodel and HUD stutter** - AI churn alone does not stutter a client. **Ask how many things can
  make a flag false before testing it in a retry, and bound every self-re-threading retry.**
- **A one-way primitive lives in more files than you grepped.** Bare `attackplayer` is
  `Actor::ForceAttackPlayer` (`m_bForceAttackPlayer`), cleared **only in the Actor constructor**
  (`actor.cpp:3092`); while set, `EnemyIsDisguised()` returns false unconditionally, so one call blinds
  that actor for the map. `attackentity <ent>` is the reversible form. Four sites took **three sweeps**
  because the first two only grepped `aihandler.scr` (bugs 1700, 1704, 1708). **Sweep the whole tree,
  and comment legitimate no-target fallbacks.**
- **An absorbing state hides everything downstream.** `EnemyIsDisguised()` also returned false for any
  actor in `THINKSTATE_ATTACK`, and it ratchets - each hostile that shoots you blanks your disguise for
  a frame, flipping more actors. Fixed by requiring real threat (bug-1707), the treatment
  `player.cpp:5541` already had. Blocked-aggro across one run: **1051 -> 0**.
- **A flag two systems both own is a race, and it comes back.** `coop_clickablePapersEnabled` is set by
  `enableClickablePapers`, cleared by `coop_bustArm`; re-arming it mid-bash restarts the papers loop,
  which force-equips papers into the hand holding the drawn pistol and **the player cannot shoot**.
  Three causes, one symptom: a 0.5 s re-check (bug-1709); a squad-wide clear on ACCEPT plus the re-offer
  answering it; per-target threading stacking loops so one clear stopped only the newest (bug-1726).
  Deduping was not enough (bug-1732) - the guard `coop_activeWeapon == NULL` means both "hand is empty"
  and "no raise ever finished". Then `coop_busted` became the overloaded one twice in an hour (bug-1735,
  an idempotence guard turned unconditional `end` once `bust.scr` set the flag earlier; bug-1736,
  cleared only on the success path). **One writer per player; clear the flag and yield a frame before
  threading a loop that sets it; split the latch from the state and clear it on every exit. Moving a
  flag's assignment earlier rewrites every guard that reads it - grep them all first.**


## T16 - conversation block to compact rules

**A scripted conversation strands when a `waittill` outranges its guard** (bug-1579). Retail chatter
helpers assume single-player — talkers always alive and idle. Coop breaks all three:

- **The `waittill` sits OUTSIDE the guard that started the anim/say**, so nothing can fire
  `animdone`/`saydone` and the sequence stops **forever**. Wait only on an actor you actually animated,
  recorded in a local - never re-test the condition (one that has since calmed passes and waits forever).
- **`isalive` on a NULL entity throws, and a thrown statement is SKIPPED** - the guard disappears and the
  body it protected runs unguarded. Test `!= NULL` first and *separately*.
- **`thinkstate != "attack"` is not "idle".** A CURIOUS / GRENADE / PAIN actor overrides the scripted
  idle anim; gate on `== idle`. `anim` runs at `THINKLEVEL_IDLE` (`Actor::PlayAnimation` ->
  `SetThinkIdle(THINK_ANIM)`, `actor.cpp:10819`) and there is no `THINKSTATE_ANIM`, so a normal exchange
  stays `idle`.

**Silence the LINE, never abort the THREAD.** The tail of these labels holds the RELEASE - a `runto`,
an `enable_ai`, a `type_disguise` - that hands actors back to normal AI; ending early leaves them frozen
and dying on their feet with no death animation. Safe exception: a dead-end label nothing waits on
(verified: `M1L3c` radio room). Sites and remaining work: **docs/OPEN.md**; helper
`replace.scr::convOk`.


## T19 - body to compact rules

**`vector_length` is a 3D distance**, so every "within N units" test is a sphere - almost never what is
meant in a building. **"Near" is a HORIZONTAL question plus a same-storey question, tested as both**: 2D
distance plus a vertical band (96u; a MOHAA storey is ~128). Three sites in one feature had it.

**Take the horizontal distance with `vector_length` on both points flattened to z=0** via a vector
literal (locals inside a literal are fine - `props.scr:407`, `tracescan.scr:79`), **not with hand-rolled
pythagoras.** A `sqrt( (dx*dx) + (dy*dy) )` here returned **265.965 for two points 2013u apart**, twice
across two builds, while `dz` by plain subtraction on the next line was exactly right - so the feature
fired at the spawn whatever radius was set. Instrumented a build later the same expression was correct,
so no claim is made about the mechanism; what is established is that `vector_length` was right on every
sample and the hand-rolled form was not on at least one. `aimaneuver.scr:129` uses the same inline form
and has never been checked.

**A range must also be the right SIZE for its job.** That feature's warning was drawn off the *action*
prompt's 112u bash range, so it appeared only once the player was on top of the officer. Give an
advisory its own, wider range.


## T12 - body to compact form

**Ship risk: CLOSED (re-verified 2026-08-17).** `build.ps1:32`'s
`$excludeTop = @("_notes", "_research")` is committed and the deployed
`zzzzzz_co-op_hzm_mod_code.pk3` contains **zero** `_research`/`_notes` entries. Releases up to v1.1.55
did ship design docs and retail script extracts; that is history. *(This entry previously read "OPEN
NOW" and cited an uncommitted `build.ps1:27` - both stale.)*

**Still open:** the regression harness - the only working automated verification - lives in a directory
named `_research`, which the build script treats as disposable. **Promote it out.** Related: four
uppercase map scripts (`M1*`, `M3*`, `M5*`, `M6*.scr`) sit alongside lowercase counterparts, unchecked
for case-collision in a pak.

**The same trap one level down: two subsystems sharing a `level.*` name** (bug-1612).
`coop_mod/ambience.scr:42` owns `level.coop_ambEnt` as a single `script_model`; the telephone-gag work
later added `level.coop_ambEnt[alias] = emitter` as a **dictionary**. The entity wins, so every indexed
read throws `[] applied to invalid type 'listener'` - once per ambient, on every map, skipped not fatal,
so nothing crashed. The sole casualty was m1l2b's ringing-telephone gag, which polls that dictionary
100x0.1 s, always burned 10 s and printed `PHONEGAG FAIL`.


## T11 - premise paragraph to compact form

**Agreement between reviewers is NOT corroboration when they share an upstream source** (bug-1290).
A multi-agent audit called "the injury vignette is permanently maxed after any DBNO revive" a live bug
and **two independent critique lenses each confirmed it** - all three inherited one unchecked premise
from the same research pass, that `dbno.scr:49`'s `healthonly 9999` puts 9999 into health.
`Entity::EventSetHealthOnly` **clamps to `max_health`**, and `player.cpp:8113` writes
`stats[STAT_HEALTH]` as an already-normalised 0..100 percentage, so the tracker cannot latch and the
"fix" would have hidden genuine low health. **Verify a finding's load-bearing premise against the code
yourself** - independent agents reading the same brief are one witness, not three.


## T10 - body to compact form

**Tell:** a fix that is definitely in the source has no effect in play - or a log line reports a limit
lower than the header says. Both directions happen: edited but never built/deployed (bug-089); and built
and deployed when it shouldn't have been (bug-1172 - every `build.ps1` run during a gl2 sandbox session
pushed sandbox-only `MAX_SOUNDS 2000` / `MAX_ENTITIES 4095` / `MAX_TIKI_ALIASES 8192` binaries into the
user's **real install**).

**The exe is the usual gap.** `build.ps1` deploys the pk3s, `cgame.dll` and `renderer_opengl1.dll` -
**not** `openmohaa.exe`, `game.dll` or `renderer_opengl2.dll`, which are hand-copied to the GOG root, so
the deployed set routinely spans several build dates and a change can be live in source, in `.cmake`,
and *not* in the binary being run. **A "verified" claim must name which binaries were deployed and
when.** `build.ps1` refuses to deploy while the game is running - if you edited and did not deploy,
everything the user then tests is the PREVIOUS build and every conclusion is void.

**Rules:** a protocol-constant change ships **all four** binaries; `game.pdb`/`cgame.pdb` ship next to
their DLLs; back up as `<binary>_pre_<feature>_bak.<ext>` - that hand-run convention *is* the rollback
system, and it has 157 entries and **zero** for `renderer_opengl2.dll`.


## T3 - gating/retail-guard paragraphs to compact form

**⭐ Gating one entry point is not gating the feature** (bug-1685). Papers had **three** writers —
`enableClickablePapers`, `forcePapersInHand`, persistent `coop_papersAnytime` — and only two carried the
`coop_busted` guard, so pressing fire equipped papers and swallowed the trigger ("he just doesn't
shoot"). **Grep every writer of the shared state before calling a gate complete.** Same shape in our own
tooling (bug-1860): `docgen.py` applied `SELF_EXCLUDE` to the porcelain FILE LIST but not to the
`git diff --shortstat` it embeds in CHRONOLOGY, so every `build` changed the number CHRONOLOGY reports
about itself and **`check` could never pass** — a permanently red oracle trains everyone to ignore it.

**⭐ Our own guard disabled the retail mechanism**, twice in one day. On m2l2a `$naxos` is a
`trigger_multiple` with `spawnflags 128` = `TRIGGER_DAMAGE`, so the engine gives it
`takedamage = DAMAGE_YES` + `CONTENTS_CLAYPIDGEON` (`trigger.cpp:285-289`) — **shooting it is how retail
completes that objective**; our stealth workaround opened with `$naxos nottriggerable` and deleted it
(bug-1671, "shooting it dont do anything"). Same shape as bug-1669's limp *warning* disabling its own
feature. **Ask what the vanilla mechanism already is before adding a guard**, and when a user says
"this is how vanilla handles it", read the ENTITY, not the scripts around it.


## T6 - dds table cell

| `.dds` beats `.jpg`/`.tga` | `R_LoadImage` rewrites the extension to `.dds` and tries `LoadDDS` **first** whenever texture compression is on, so a same-basename stock `.dds` always beats your HD `.jpg` — this made 881 upscales dead. Disabling `r_ext_compressed_textures` is **not** a fix (~1400 stock-`.dds`-only textures would vanish); ship DXT `.dds` overrides with a full mip chain. |


## T7 - g_gametype table cell

| **⭐ `g_gametype` is LATCHED — the FIRST map of a launch runs before it applies.** `ui_startdmmap 2` sets it, the engine answers *"g_gametype will be changed upon restarting"*, and the change lands at the **next** map load (observed 59 s later). Map #1 initialises with `g_gametype` **0**, `coop_mod/variables.scr:38` caches `level.gametype = 0`, and **`variables.scr:89`'s `if(level.gametype == 0){ end }` aborts the whole coop init**; every later check then takes its SP branch, including `replace.scr::waitForPlayer:105`, a raw `level waittill spawn` that throws and so does not WAIT. Clients connect, get kits, never spawn. **Seed `+set g_gametype 2` on the command line.** | First map of a run has no coop | 1492 |


## T4 - MAX_SOUNDS closing paragraph

**Read `openmohaa-hzm/code/qcommon/q_shared.h:1690-1755` in full before touching any capacity
constant.** That `MAX_SOUNDS` comment is the best worked example in the codebase and is not reproduced
here: four binding constraints in the order they bite (`CS_AXIS = MAX_SOUNDS + 2393`, bug-1179;
`MAX_RELIABLE_COMMANDS` must stay a power of two, bug-1183 twice; the 11-bit `sound_index` that
silently truncates; `MAX_GAMESTATE_CHARS`), each tagged with the bug that found it including the two
failed attempts, backed by a compile-time `#error`. **Turn every capacity rule into a build break.**


---

# Round-5 originals: whole sections as they stood before the final rewrite

> Every bug id and `file:line` anchor below is still inline in TRAPS.md.


## Section t17

<a name="t17"></a>
## T17 — Script VALUE types: 'none', keyvalue strings, and who owns an event

Variants of one failure: the value is not the type the reader assumes, and the thread dies at that line
while the caller still reports success. **Tell:** a feature that "does nothing" with no crash, plus a
`Script Error` line naming a file and line you were not looking at.

**Reading a level var CREATES it with type `none`, and the engine then throws on it.** `int n = pv ?
pv->intValue() : 0` looks safe and is not: `GetVariable` returns non-NULL for a variable that exists but
was never *assigned*, so the NULL guard passes and `intValue()` throws `Cannot cast 'none' to int`.
`coop_vehKill_monitor` merely *read* `level.coop_vehKills` each frame; that alone poisoned
`DrivableVehicle::Killed` so **no drivable vehicle on any map could be destroyed** — it aborted before
the explosion, the tank sat at negative health with `deadflag 2`, the VEHZOMBIE rescue revived it for
the next hit, and it read as invincible. **Always ASSIGN a level var before anything reads it**, and
prefer a type check over a NULL check on the engine side. (bug-1371)

**Map entity keyvalues arrive as STRINGS.** `#totalguys` / `#activeguys` compared against an int gave
115 errors a level in `global/parade.scr` and silently killed the parade spawn loop. `int()`-coerce once
at the top, not at each comparison. Same class as the parsed-`.dat` fog values. (bug-1352, bug-1372)

**A command registered on `ScriptThread` is NOT a Player event.** `iprintlnbold` / `iprintln` live in
`scriptthread.cpp:225/234` only, so every `<player> iprintlnbold "..."` fails — 39 sites across 11 files,
meaning those messages had *never once* reached a player. The Player-scoped equivalent is
`iprint <text> 1` (`player.cpp:1222`, `"sI"` = "prints a string to the player, optionally in bold").
**Before calling `<entity> <command>`, confirm the command is registered on that entity's class.**
(bug-1374)

**Some engine events are SETTER PROPERTIES, not commands.** `EV_Actor_SetWeapon` is `EV_SETTER`:
`self.weapon = "models/weapons/x.tik"` works; `self weapon models/weapons/x.tik` **does not exist as a
command**, which is why retail's own post-spawn swaps sit commented out in m1l2a and m5l3. (Command
syntax on the getter half is a T1 parse killer, bug-910.) Reading `self.weapon` on an ACTOR returned raw
`m_csWeapon` - whatever some script/tik wrote ("mp40", a full path, any case, or EMPTY for tik-armed
actors) - **not** the tik `name` field the PLAYER getter returns, so a display-name-keyed lookup missed
100% (bug-1943). Since 2026-08-19 the getter returns the HELD weapon's name field with the raw fallback
when unarmed. String-keyed array LOOKUPS stay case-sensitive even though `==` is not (bug-1916 family).

**A bare identifier is a CONST STRING, and `int + conststring` CONCATENATES.** `local.wave1 +
local.wave2 + wave3 + 5` (note the missing `local.`) silently produced `"20wave35"`, and `intValue()` on
a string is `atoi` → **20**, against a gate waiting for 35. Total mission softlock, no error. It is a
*vanilla* typo, byte-identical in retail. (bug-1377)

**⚠️ Fixing a type error can UNMASK a latent logic bug.** That same line previously threw every frame,
and the throw aborted the parade's done-check, so the parade never stopped and the gate happened to
pass; the correct `int()` coercion (bug-1372) made the comparison work, the parade stopped at 20, and
the map became *unfinishable*. **After silencing a recurring script error, re-test the feature it was
firing in** - the error may have been load-bearing.

**`thread <label>` inside a boolean is ALWAYS TRUE.** `thread` starts the label asynchronously and
evaluates to a HANDLE, so `if( x && thread foo::bar )` is `if( x && <truthy> )`; five
`anim/disguise_*.scr` gates were written this way and never guarded anything for years. Use `waitthread`
when you want the value. Because the branch they guarded ends in `end`, four statements BELOW it were
unreachable whenever it fired, including the squad-wide papers pass. **When you fix a condition that was
always true, audit what sits below its `end` as well.**

**`continue` in a `while` loop whose index advances at the BOTTOM = infinite loop = server hang.** `for`
runs the increment on `continue`; `while` does not. `aihandler.scr`'s actor sweep is a `while` at `:302`
incrementing at `:484` — a `continue` between them spins forever. Wrap the body in an inverted `if`, and
**check the loop KIND and where the increment lives before writing any early-skip.**

---



## Section t1

<a name="t1"></a>
## T1 — Morpheus parse killers: one bad token silently kills the WHOLE `.scr`

**Recurred under 15+ bug ids:** 089, 298, 331, 348, 402, 533, 739/750, 910, 962, 1067, 1069, 1105, 1205, 1283, 1285, 1751, 1908.

**Tell:** a feature silently does nothing, with **no error at the failure site**; every `::` call into
the file logs `Script was not properly loaded`. A whole subsystem dying at once (bug-533 took helmet +
sandbag + medkit + emotes) means the shared bus file. The compiler is all-or-nothing: one syntax error
kills the entire file and the map runs with no script at all — raw team menu, unstartable.

> **An assignment with no value is a parse killer, and the error points at the WRONG line**
> (bug-1908). `level.coop_loRosterTab[69] = ` with nothing after it makes the parser take the *next*
> statement as the value and die on **that** statement's `=`. Not "the line ends with `=`" — a bare
> trailing `=` is a legal continuation retail `global/MountGunOrPlantCharge.scr` relies on; fatal only
> when the next code line is itself an assignment. `docs/tools/check_empty_rhs.py` runs every build.
> It came from a **generator** rendering an empty column: validate a generator's inputs.

> **All three scanners pass a file that cannot compile** — they check brace depth, line shape and
> string termination, not *expression* syntax. `println "a" + x + "b"` without parens is
> `unexpected TOKEN_PLUS`, kills the file, scans clean (bug-1751). **Not verified until a server has
> loaded the map and the log shows no `parse error`.**

**Run all three — they catch disjoint classes:**

| tool | catches | blind to |
|---|---|---|
| `docs/tools/depthscan2.py` | brace/label depth (never negative; 0 at each column-0 label) | everything below |
| `docs/tools/linecheck.py` | a line **starting** with a binary operator | everything below |
| odd-quote scan (comment- and string-aware, per line) | unterminated / multi-line string literals | the rest of T1 |

The log names only the **first** offending line — bug-1283 had two multi-line strings in one file and
fixing the reported one would have left it equally dead. **Fix the class, not the line.**

**Confirmed triggers, each with the bug that found it:**

| Trigger | Bug |
|---|---|
| Command syntax on an `EV_GETTER` property (`local.e getmins`) — must use property syntax | 910 |
| A script command a sub-agent invented (`userinfo`, `getcurrentdmweapontype`) | 298, 1067 |
| A function call inside a vector literal, or with one in the same expression | 348, 402 |
| Negatives/arithmetic: parenthesised `(-1)`, or in a COMMAND ARG slot — `$ent coopammo 0 - 1`. Compute to a local. **But** negative *vector components* are fine: `( 4016 0 - 967 0 - 328 )` == `( 4016 -967 -328 )` — don't "fix" them. | 1069, 1826, 1830 |
| An empty-array literal `[]` — morlang has none | 1105 |
| An unquoted `+`/`-` directive argument: `surface X -nodraw`, `surface X "+skin1"` — valid TIKI syntax, fatal in script (`unexpected TOKEN_PLUS`), **quote it**. Braces balance, so the depth scan misses it. | 533, 1308 |
| A leading `&&` or `\|\|` on a continuation line | 739/750 |
| A real newline inside a string literal — from a generator, or a hand-typed banner | 331, 962, 1283, 1285 |
| A backslash in a script path (resolved to `coop_modhelmet.scr`) | 1205 |
| Em-dash, UTF-8 BOM, any non-ASCII; duplicate label; label/brace mismatch | (CLAUDE.md) |

**NOT a parse killer, contrary to an older note:** `spawn <class>` **with** inline keyvalues is fine —
192 working occurrences including `main.scr`. `KNOWN_WORKING_STATE.md` still forbids it and is wrong;
see [90-folklore.md](90-folklore.md).

1. **`developer 1` is mandatory** — compile errors are developer-gated at `fgame/scriptthread.cpp:2858`,
   `:2869`, `:2883`; without it the failure is *completely* silent.
2. **Raw brace counts are an invalid check** — two opposite errors cancel on a broken file (bug-239),
   and comment/string braces miscount. Use a **running-depth scan**: never negative, 0 at every
   column-0 label (internal `goto` labels may sit at depth 1).
3. Scanners live in `docs/tools/` (`depthscan2.py`, `linecheck.py`, `quotecheck.py`, `scrlint.py`).
4. Verify any claimed script command against engine source **before** it lands.

**Live status:** clean (re-scans 2026-07-29, 2026-08-08). bug-1027 (`e3l4/outro.scr`) has this exact
signature.

---



## Section t5

<a name="t5"></a>
## T5 — `$player` is an array; NIL ≠ NULL; storms are sequential

**Bugs:** 1049, 1051, 1052, 1054, 1065, 1104, 1624, 1632, 1665; the 4-player sweep.
**Tell:** thousands of identical `Script Error` lines. **Solo boots cannot reproduce any of it.**

1. **`Cannot cast array to listener`** — vanilla SP treats `$player` as one entity, but with **2+
   connected players it is a 1-indexed ARRAY**, so `$player.origin`, `turnto $player`,
   `isAlive $player` all throw. Repair idiom: an **inline `$player[i]` scan** with a per-element NULL
   guard, or `$player[1]` with a NULL host guard. ⚠️ This line used to recommend
   `exec coop_mod/replace.scr::player_closestTo self` — do **not** reach for that first (bug-1665).
2. **`Cannot cast none to <type>`** — a `level.*` timing global the vanilla SP init would have set is
   never set in coop (`level.thundertime` / `windtime` / `shuttertime` / `rainvolume`);
   `weather.scr:378` alone threw **8,662 times**. Fix: NIL-guards restoring vanilla defaults.
3. **Stale pointers that PASS a NULL guard** — bug-1054's `coop_trackTankTarget` had no `else` branch,
   so a freed player ref lingered and evaded `== NULL`.

**⚠️ Guard with BOTH.** `NIL != NULL` and coop hits both; bug-1065 hardened `xp_award` with
`== NULL || == NIL` because `level.coop_smoke_player` is only ever assigned, never initialised. The open
bug-1220 (12× "applied to NULL listener" on e2l2) is this exact cure.

**⭐ THE META-LESSON — SEQUENTIAL STORMS.** Fixing one class lets maps progress **further**, exposing the
next: the array-cast fixes are what unlocked the none-cast storm. **A storm blocks map progression and
hides every storm downstream.** Budget **2–3 fix→re-sweep passes**; a clean sweep after one fix means
nothing.

**Root cause of the biggest storm:** `addon_*` markers carry their model in `$ai_model`, not `.model`,
so `spawner_create` recorded NIL and the engine spawned `models/nil.tik` in a loop - an entity leak as
well as log spam (`global/spawner.scr:95-138`). Counts:
`docs/archive/traps-measured-wins-2026-07-22.md`.

**The proven repair pattern:** extract the retail gag verbatim from `mainta/pak1.pk3`, change **only**
the single-entity `$player` refs, add NULL host guards, leave everything else byte-identical
(`gags/t2l4_start.scr:1-2`, `gags/t3l1_enemyspawn.scr:2`).

**Entities as `thread` parameters can arrive NIL, and a cross-file helper can return NULL outright**
(bugs 1624, 1632, 1665). Numbers always bind; an entity passed to `thread label a b c` may not survive
the boundary (and `ent thread label x` binds at most ONE arg). Park it in a **level array keyed by
numbers** (`level.coop_bpEnt[n + "_" + entnum] = ent`; precedent `level.coop_itemPapers`), pass numbers
only, re-read each tick. **⭐ bug-1665, NINE attempts:** `player_closestTo` returned **NULL on 90
consecutive measured samples** while a probe twelve lines below read both players fine (`hp=750
team=allies act=1 noclip=0`) - the label declares TWO params (`local.object local.origin`) and every
caller passes ONE. **When a helper "returns nothing", print INSIDE it and inline the same scan in the
caller; if the inline scan works, stop using the helper.** Eight attempts reasoned about which filter
rejected the player; the ninth printed all four filter fields and proved none did.

**Still open:** `global/vehicle_warning.scr` (4,270 casts, second-worst source) was **never
extracted** — the retail version is still live; plus a second vehicle-crew spawn path on t2l2/t3l2 that
the `truck_load` guard does not cover.

---



## Section t6

<a name="t6"></a>
## T6 — What you shipped is not what loads

**Bugs:** 157, 247, 499/525/530/921/922 (a 5-round saga), 1129, 1190, 1216, 1610, 1633.
**Tell:** an asset edit has no visible effect, or a "black" surface appears, or a texture you never
touched changes.

| Load-order rule | Consequence |
|---|---|
| `.dds` beats `.jpg`/`.tga` | `R_LoadImage` rewrites the extension to `.dds` and tries `LoadDDS` **first** whenever texture compression is on, so a same-basename stock `.dds` beats your HD `.jpg` - this made 881 upscales dead. Disabling `r_ext_compressed_textures` is **not** a fix (~1400 stock-`.dds`-only textures would vanish); ship DXT `.dds` overrides with a full mip chain. |
| The engine tries `.jpg` **before** `.tga` | Menu art in particular |
| Shader **NAME** overrides lose the reverse-concat race | Whole-**FILE** overrides win: the filesystem dedupes by filename and the coop pak mounts last (bug-921 used bug-525's whole-file pattern on `scripts/equipment.shader`) |
| `zzzzzzzz_*` sorts after `zzzzzz_*` | bug-1190 |
| `.tik` surface directives must match the `.skd`'s real surface names | else `TIKI_InitTiki` drops them (bug-1216) |
| Homepath `maintt/` beats basepath; loose files beat paks | **bug-1633:** the live profile runs `fs_homepath G:\mohaa-gl2\home`, and stale `autoexec.cfg`/`coop_defaults.cfg` in its `maintt/` silently shadowed every deployed cfg change; `build.ps1` now deploys cfgs to all three targets (GOG maintt, APPDATA maintt, gl2-home maintt). bug-595 lost a session to a stale **0-byte** `omconfig.cfg` decoy, **still on disk** at `%APPDATA%\openmohaa\maintt\omconfig.cfg` (0 bytes, 2026-07-04) |

**⭐ THE FINAL ANSWER when a name is contested** (bug-922, closing the 5-round black-pouch saga):
**stop fighting for the name.** Mint a NEW shader name existing only in the coop pak, pointing at a
PRIVATE texture path also existing only in the coop pak, and retarget the `.tik` surface. **Diagnostic
tell:** if a "black" surface shows per-face **shading**, a lit default shader is drawing it and your
identity def is not reaching that surface at all.

**⭐ A playtest log only testifies about the build it loaded** (bug-1610). `coop_enigma.shader` existed
yet the log said `Couldn't find image file for shader enigma`: the client loaded 23:34 and quit
23:37:11, the file was packed at **23:38:06**. **Compare the pk3 entry's timestamp
(`zipfile.getinfo(name).date_time`) against the `InitGame` line before treating a log as evidence about
a new asset**, and verify fixes by reading them back out of the deployed pk3.

**⭐ Imported third-party skin packs are this trap with the blast radius reversed.** A 2002-era skin pk3
routinely *redefines* stock shader names instead of minting its own, and the coop pak mounts last, so
the import silently repaints every other model (one pack redefined all 15 `viewsleeves*` shaders for one
pilot skin; another broke the holster on *every* skin; 39-pack sweep: `docs/proposals/skin_batch.md`).
**Diff an external pack's top-level shader block names against `hzm-mohaa-coop-mod/scripts/*.shader` and
the retail paks, and its `models/player/*.tik` basenames against the stock tiks** - a matching tik
basename *replaces* the stock model. Note `map foo.tga` resolves extension-agnostically, so a shader
naming `.tga` beside a shipped `.jpg` is **not** missing.

**Related generated-asset hazard:** ESRGAN upscales have shipped hallucinated worm noise (bug-1129), a
GPU-corrupted all-black `netgame_a/b` that blanked the server browser (bug-247), and 29 overridden
**vanilla** menu textures (bug-157). **Brightness-check output before commit**; ESRGAN is for photos and
text and corrupts 1–2px chrome.

---



## Section t8

<a name="t8"></a>
## T8 — Server→client stufftext is a lossy, filtered channel

**Bugs:** 595, 597, 736, 758, 772, 773, 1364, 1365.

1. **Quote truncation** — `Player::EventStuffText` sends `stufftext "<cmd>"`, so an embedded quote ends
   the wire-level argument early; tell is client-side `Cvar ... does not exist` spam. **Send values
   UNQUOTED, ONE statement per stufftext**; `;`-joined multi-statements are the other half. (bug-736,
   bug-758)
2. **The whitelist** — `cg_servercmds_filter.cpp:304-316` silently drops server-stuffed `exec` and
   `vstr` as Reborn-exploit protection, which ate the **entire coop-detect handshake**
   (`coop_mod/cfg/detect.cfg`), the objectives setup and the armory pick carry-over, presenting as
   **three unrelated bugs**. Fixed with scoped exemptions: exec only for mod-namespaced paths, vstr only
   for `coop_*`/user-created cvars. (bug-597)
3. **Whitespace collapse** — `Cvar_Set_f` (`cvar.c:936`) takes its value from `Cmd_ArgsFrom(2)`, which
   re-joins the *tokenised* args with a single space. Multi-word values survive unquoted (why the
   `coop_so1`/`coop_cp1` HUD pushes work at all), but **any run of whitespace inside the value
   normalises to one space** — never pad with spaces to align columns; use a visible separator.
   (bug-1364)
4. **An undispatchable token** — a bare name-bus token with no data character makes `playerExtract`
   return NIL. (bug-772)
5. **Client `exec`/`vstr` INSERT at the buffer front; only stufftext APPENDS.** Verified in `cmd.c`:
   `Cmd_Exec_f` and `Cmd_Vstr_f` call `Cbuf_InsertText`, so a click's whole cfg chain runs depth-first,
   atomically, in textual order. The 2026-08-18 "exec APPENDS" rationale (commit `d2e7084` and a
   `loadoutpick.scr` comment) is **WRONG about the engine**; the server-visual strip is right for a
   different reason - server stufftext arrives frames later over the WIRE (`Cbuf_AddText`), always after
   the client's instant chain. So within one client chain the **LAST textual line wins** (`s<n>sel.cfg`
   correcting `coop_loMvPN` on its final line only works because of insert semantics - do not move that
   line earlier), and any server echo races the next click by a round trip and can revert a preview.
6. **The name bus dispatches ONE token per ~0.75 s batch; every other stacked token is destroyed.**
   `playerNameCommand` breaks at the FIRST token with data and `playerCleanName` truncates at the first
   `" ,"`. Priority is **BUS INDEX order, not click order** (skin 31 > helmet 35 > weapons 42-45 > menu
   46 > pins 47 > finishes 48-51), so rapid armory clicking silently drops actions - helmets/skins got
   close-time commit replays for this (bug-773); weapons/finishes have none. A new bus feature must
   tolerate drops (archived-`seta` + join replay) or add a close-commit.

**Related silent loss, receiving end:** a `.urc` widget placed below its menu's declared canvas height
**draws nothing at all** — `UIWidget::CalcClippedFrame` (`uilib/uiwidget.cpp:872`) clamps a child to its
parent's frame, so the height goes to 0. No error, no console line; the cvar push works and the row is
just absent. Set `noparentclip` (`WF_DIRECTED`, `uiwidget.cpp:1496`) or grow the canvas — prefer growing
it, since the flag defeats clipping everywhere. **Check the menu's declared size before adding rows to
any panel.** (bug-1365)

**⚠️ Remote clients need the updated `cgame.dll` too.** Server-stuffed SETs of `CVAR_ARCHIVE` cvars are
dropped by `CG_IsSetVariableAllowed` unless whitelisted — see [T3](#t3).

---



---

# Round-6 originals (2026-08-20, final)

> Every bug id and `file:line` anchor below is still inline in TRAPS.md.


## T3 - remaining paragraphs

**The `waittill`-already-fired shape recurs on every remaining map.** `invalid waittill spawn for
'Level'` reads like a warning but means "this script ran at the wrong time"; a failed `waittill` does
not abort — it does not wait, and the damage surfaces as NULL-listener errors elsewhere. Fix with
`waitthread coop_mod/replace.scr::waitTillSpawn` / `::waitTillPrespawn`. **Do NOT bulk-replace:** 191
bare `level waittill` sites ship and most are legitimately reached first, so **the runtime log is the
oracle** — fix only sites that actually throw, per map, as each is played ([T14](#t14)). Retail
sub-scripts absent from the mod tree: extract into `maps/<map>/`, change **only** the offending line.

**A second shape: the write executes and is then overwritten.** Proving execution is necessary but not
sufficient - prove nothing later writes the same field, and in a render/view path grep the whole function
and prefer the LAST write site. The dangerous variant is a misplaced write that lands somewhere real
(bug-1238 moved the 3P pivot): silent corruption of a neighbouring feature.

**The UI corollary - never trade a working widget for an unverified one.** A `.urc` cannot be run or
diffed from here and the only oracle is the user's screenshot; six attempts at one Service Record
checkmark each replaced a functioning pin box and each came back worse (bug-1546). **Add alongside it,
or wait until someone can see it render.**

**A vanilla scene reachable only from a BSP `trigger_once` never runs in coop.** m3l3's `main` carries
seven `//thread sceneN` lines noted "called from a trigger_once in the bsp", and those triggers do not
fire on a coop server. scene6's one-off workaround (`coop_churchApproach` threads it) hid the pattern, so
scene7 shipped asleep - no crews, no MG nests, no firing nebelwerfers, a final objective that could never
complete, and a whole session log with **zero** occurrences of `scene7`. **Grep a map's `main` for
commented-out `sceneN` threads, account for every one, and guard each (`level.coop_sceneNStarted`) so
the BSP trigger and your call site are both safe entries.**

**The cure that works:** an autonomous verification rig — its value is catching a feature that silently
doesn't fire. And when you fix a silent-discard branch, **add the warning even though you also raised
the limit** — `sv_snapshot.c:549-553` does.


## T7 - table cells and closing paragraphs

| **Exec order** — the engine execs `default.cfg` → saved config → `autoexec.cfg` **LAST**, and `autoexec` was `seta`-ing ~200 curated defaults, overwriting every menu-changed setting on every launch. | Menu changes don't stick | 710 |
| **`Cvar_Get` ORs flags** — `r_lodscale` registered twice in gl2 (once `CVAR_CHEAT`, once `CVAR_ARCHIVE`) became cheat-protected and the slider silently reverted. | Slider reverts | 1125 |
| **A temporary flag flip persists** — flipping `r_entlight_scale` `CVAR_CHEAT`→`CVAR_ARCHIVE` for an A/B test **archived** the value 0.3 and dimmed every entity on every launch. | Global regression from a test | 918 |
| **Fail-open locks** — the armory padlock recompute zeroed all lock cvars then relied on a server push that might never arrive. Redesigned fail-**LOCKED**. | Content unlocked that shouldn't be | 682 |
| **Clamped cvars lie to menus** — gl2 clamps `r_ext_multisample` to 4, so the 8× MSAA plate had to be repointed at the unclamped `r_ext_framebuffer_multisample`. | Menu offers a value the renderer refuses | 1152 |
| **`CVAR_ARCHIVE` probes poison every later boot** — an rcon probe set `r_toneMap 0`; silently retained, feature never ran again. | See [T3](#t3) | 1148 |
| **`CVAR_CHEAT` probes are useless on a listen server** — `sv_cheats 0` clamps them back; `r_globalFogDebug` had to move to `CVAR_TEMP` (**still `CVAR_TEMP` at `renderergl2/tr_init.c:1926` — restore it**). | Debug view won't enable | — |
| **Never `seta` a genuine user preference** in `autoexec.cfg` (`cg_adsShoulderRight`). | Preference resets each launch | 258 |
| **Never seed `coop_uiB*`/`coop_uiN*`** — wipes last-known challenge progress. | Progress lost | — |
| **⭐ `g_gametype` is LATCHED — the FIRST map of a launch runs before it applies.** `ui_startdmmap 2` sets it, the engine answers *"g_gametype will be changed upon restarting"*, and the change lands at the **next** map load (observed 59 s later). Map #1 initialises with `g_gametype` **0**, `coop_mod/variables.scr:38` caches `level.gametype = 0`, and **`variables.scr:89`'s `if(level.gametype == 0){ end }` aborts the whole coop init** - every later check then takes its SP branch, including `replace.scr::waitForPlayer:105`, a raw `level waittill spawn` that throws and so does not WAIT. Clients connect, get kits, never spawn. **Seed `+set g_gametype 2` on the command line.** | First map of a run has no coop | 1492 |

**The structural fix is half-built:** `coop_defaults.cfg` execs **BEFORE** the saved config, so its
values are true defaults that a menu change overrides and persists. Migration out of `autoexec.cfg` is
incomplete, and any menu-wired cvar still `seta`'d there **cannot** persist. The two files are disjoint,
so they never fight. Counts live in `docs/generated/CVARS_COOP.md` — never hand-copied here.

**A cvar seeded nowhere** (no engine `Cvar_Get`, no cfg line) makes `getcvar` return `""` on a clean
profile, and a script fallback branch silently decides behaviour. **Calling such a cvar "default N"
describes a branch, not a default.


## T16 - failsafe paragraphs

**A recovery path must contain no wait that the failure mode can block.** The e3l4 failsafe bounded a
blocking wait at 45 s then "recovered" by calling a routine opening with `runto` + `waittill movedone`
— the actor's whole problem was having no nav path, so the soft-lock moved rather than closed. For
actors: no `runto`/`walkto`/`waittill turndone`/`waittill animdone`, no unbounded
`while (vector_length(...) > N)`. Seat or place them directly — take the **tail** of the vanilla routine.
Grep the recovery path for `waittill` before shipping, and check the *next* stage for the same shape.

**Two engine facts make actor waits unsafe** (bug-1368): `Unregister(STRING_TURNDONE)` exists in exactly
one place, `Actor::IdleTurn` (`actor.cpp:5032`), which no runner think reaches — so a failed `runto`
pins the actor in `THINK_RUNNER` and any `waittill turndone` there blocks **forever**.
`waittill movedone` is safe: `CheckUnregister` (`actor.cpp:7793`) fires it even on `parm.movefail`.
**`runto` → `turndone` hangs; `runto` → `movedone` does not.**

**Never invent an exit/placement offset when the model carries an authored one** — vehicles ship
`driver_enter` / `passenger_enter` / `*_seat` tags, walkable by construction; an offset that works at one
stop is a guess about free space at every other stop. (bugs 1367, 1370)


## Turrets - items 2 and 3

**2. AI spread is an AVERAGE — a 2-arg `bulletspread` half-applies to AI shooters** (bug-1920).
`Weapon::Fire` gives a NON-client owner `(bulletspreadmax + bulletspread) / 2`; most tiks never set a
max, so a script `bulletspread 120 120` averages with 0 into an effective 60 and the tune feels dead
(m3l3 MG42s "still hit every single shot"). **Any spread tune aimed at AI must set all four args:
`bulletspread B B M M`.** Player fire uses a different formula (base/max lerp by spread factor), so
player-facing tunes are unaffected.

**3. `TurretGun` fixes NEVER reach `VehicleTurretGun`.** It overrides `Think()`, `UpdateFireControl()`
and `GetMuzzlePosition()`, so anything tuned in TurretGun's paths silently skips every vehicle-mounted
gun (halftrack, tank hull MG, jeep). THREE separate user reports traced to this split on 2026-08-19:
player MG heat never cycling (bug-1946), and AI road gunners laser-accurate at full damage because the
whole coop tuning trio — damage scale, spread bonus, wandering aim error — was TurretGun-only
(bug-1950). **Any turret-behavior change ships BOTH class paths, or states in a comment why the vehicle
side is exempt.** The trio is `extern`'d in `weapturret.h` for exactly this.


## Script-error bullets

- **An `invalid waittill` means the script does NOT WAIT.** Everything below runs *immediately* —
  sequences fire before their preconditions, entities are touched before they spawn. That is why the
  `waitTillSpawn`/`waitTillPrespawn` shims still matter (bugs 1458-1469): they were fixing a real
  defect, just not the one the note claimed.
- A cast error inside a `while` body removes the *statement*, not the loop — exactly how t2l3 span 4,347
  times with no yield and killed the server.
- **Values parsed out of a `.dat` file are STRINGS** (bug-1352). The character-walking splitters
  (fogmode, blueprint, save files) return strings, so a later `if( x > 0 )` throws and *that assignment
  never happens* while the caller prints its success message. Coerce with `float()`/`int()` at load; the
  tell is "works when set live, never when loaded from its own save".
- **A probe that throws prints nothing** while filling the log with errors — silently useless on exactly
  the cases worth watching. Sanitise every field before concatenating: an unset var reads `none`, and
  `"str" + none` throws (bugs 1702, and the SPAWNDISG probe before it, the same day).


## T14 - closing paragraphs

**A MEASUREMENT HARNESS FAILS SILENTLY TOO — a broken one does not error, it reports.** Four AI A/B runs
(2026-08-15) were each invalidated a different invisible way, all four looking clean. **Refuse to report
unless preconditions held, and prove the guard fires.** The four modes and six rules:
[reference/harness_and_reproduction.md](reference/harness_and_reproduction.md).

**A declaration with no producer is the same silence** (bugs 1596-1598). Cross-reference mechanically,
walking the WHOLE tree — a `maps/*.scr` glob misses `maps/<map>/*.scr` and miscounted three wired
challenges as dead.


## Preamble

> Compressed 2026-08-20 from 71.6 KB to get back under the 60 KB ceiling. Every rule, bug id and
> `file:line` anchor was kept (verified by an anchor-set diff); the war-story detail behind the
> twenty most heavily trimmed or merged passages, and one section moved out whole, are verbatim in
> [`archive/traps-pruned-2026-08-20.md`](archive/traps-pruned-2026-08-20.md).


---

# Round-7 originals (2026-08-20, final)


## Quick index

Status: **!** = open now, **~** = recurring, blank = fixed/known pattern.

[T1](#t1)~ Morpheus parse killers · [T2](#t2) Generators corrupt the files they write ·
[T3](#t3)~ Silent-veto: the feature never ran · [T4](#t4)~ A capacity family has more members than
you think · [T5](#t5) `$player` is an array; NIL != NULL; storms are sequential ·
[T6](#t6)~ What you shipped is not what loads · [T7](#t7) Cvar registration, flags, exec order ·
[T8](#t8) Stufftext is lossy and filtered; `exec`/`vstr` order; the name bus ·
[T9](#t9) Same-frame spawn/model/solid race · [T10](#t10)~ Deploy gaps ·
[T11](#t11)! Trusting the record over the code · [T12](#t12)~ Name collisions between
identically-named trees · [T14](#t14)! Your verification lied · [T16](#t16) Waits that never
complete · [T17](#t17) Script value types · [T19](#t19) A radius is a SPHERE ·
[T20](#t20) One flag two states; one-way latches

Unnumbered: [`Script Error` **skips the statement**](#script-error) · [turrets and AI
spread](#turrets) · [`item_name` variant suffixes](#itemname) · [procedural view/weapon
motion](#procedural) · [TIKI and sound aliases](#tiki) · [cross-cutting questions](#cross-cutting).
**T13** is [Cross-cutting](#cross-cutting) Q5; **T15** is `reference/harness_and_reproduction.md`;
**T18** is `archive/traps-t16-failsafe-recursion.md`. Older docs still link to `#t13` / `#t15`.


## T1 blockquotes

> **An assignment with no value is a parse killer, and the error points at the WRONG line** (bug-1908).
> `level.coop_loRosterTab[69] = ` with nothing after it makes the parser take the *next* statement as the
> value and die on **that** statement's `=`. Not "the line ends with `=`" - a bare trailing `=` is a legal
> continuation retail `global/MountGunOrPlantCharge.scr` relies on; fatal only when the next code line is
> itself an assignment. `docs/tools/check_empty_rhs.py` runs every build. It came from a **generator**
> rendering an empty column: validate a generator's inputs.

> **All three scanners pass a file that cannot compile** - they check brace depth, line shape and string
> termination, not *expression* syntax. `println "a" + x + "b"` without parens is `unexpected TOKEN_PLUS`,
> kills the file, scans clean (bug-1751). **Not verified until a server has loaded the map and the log
> shows no `parse error`.**


## T3 mid paragraphs

**A second shape: the write executes and is then overwritten.** Proving execution is necessary but not
sufficient - prove nothing later writes the same field, and in a render/view path prefer the LAST write
site. The dangerous variant is a misplaced write that lands somewhere real (bug-1238 moved the 3P pivot):
silent corruption of a neighbouring feature.

**The UI corollary - never trade a working widget for an unverified one.** A `.urc` cannot be run or
diffed from here and the only oracle is the user's screenshot; six attempts at one Service Record
checkmark each replaced a functioning pin box and each came back worse (bug-1546). **Add alongside it,
or wait until someone can see it render.**

**A vanilla scene reachable only from a BSP `trigger_once` never runs in coop.** m3l3's `main` carries
seven `//thread sceneN` lines noted "called from a trigger_once in the bsp", and those triggers do not
fire on a coop server. scene6's one-off workaround (`coop_churchApproach` threads it) hid the pattern, so
scene7 shipped asleep - no crews, no MG nests, no firing nebelwerfers, a final objective that could never
complete, and a session log with **zero** occurrences of `scene7`. **Grep a map's `main` for commented-out
`sceneN` threads, account for every one, and guard each (`level.coop_sceneNStarted`).**


## T4 head bullets

- **A "comprehensive sweep" that greps only *suspected* files is not comprehensive** — bug-925 crashed
  in `sentient_combat.cpp`, missed by bug-920's sweep.
- **Fix the producer, not just the consumers** — `AddItem` appended entnums with no duplicate check
  while removal took only one occurrence (bug-920).
- **Non-NULL is not enough**: a recycled slot may hold a *different class*; guards became
  `item && item->isSubclassOf(Item)` (bug-919).
- **Audit bare array sizes, not just constant names** — `tr.skel_index[1024]` (bug-932b);
  `processed[MAX_ENTITIES]` where `MAX_ENTITIES` is the renderer *refentity* cap 1023, **not** the
  gentity count (bug-935); `MAX_SKELMORPH 12800` silently out-of-bounds (bug-1214). Three payouts for
  the invisible-actor symptom alone (bug-932 gl1, `renderergl2/tr_local.h:2339` gl2, bug-1135
  `R_AllocModel`).


---

# Round-8 originals (2026-08-20, final)


## T2 upscaler table cell

| A **texture upscaler** tiled correctly (3x3 → resize → crop centre) then ran UnsharpMask on the CROPPED result. A convolution clamps at the border, so it invented edge pixels and reintroduced the exact seam tiling existed to prevent (14x worse on `ocean1b`); Lanczos lobes separately overshot a capped alpha (189 → 255). Fix: sharpen **inside** the tiled space, clamp each channel back to the source range. | 1247 |


## T4 MAX_SOUNDS closing

**Read `openmohaa-hzm/code/qcommon/q_shared.h:1690-1755` in full before touching any capacity
constant.** That `MAX_SOUNDS` comment is the best worked example in the codebase and is not reproduced
here: four binding constraints in the order they bite (`CS_AXIS = MAX_SOUNDS + 2393`, bug-1179;
`MAX_RELIABLE_COMMANDS` must stay a power of two, bug-1183 twice; the 11-bit `sound_index` that silently
truncates; `MAX_GAMESTATE_CHARS`), each tagged with the bug that found it including the two failed
attempts, backed by a compile-time `#error`. **Turn every capacity rule into a build break.**


## T11 opening

**Agreement between reviewers is NOT corroboration when they share an upstream source** (bug-1290). A
multi-agent audit called "the injury vignette is permanently maxed after any DBNO revive" a live bug and
two independent critique lenses confirmed it - all three had inherited one unchecked premise, that
`dbno.scr:49`'s `healthonly 9999` puts 9999 into health. `Entity::EventSetHealthOnly` **clamps to
`max_health`**, and `player.cpp:8113` writes `stats[STAT_HEALTH]` as an already-normalised 0..100
percentage, so the tracker cannot latch and the "fix" would have hidden genuine low health. **Verify a
finding's load-bearing premise against the code yourself** - agents reading the same brief are one
witness, not three.


## T12 opening

**There are TWO `_research` trees** and records conflate them: `C:\mohaa-coop-dev\_research\` (design
docs, audits, **the regression harness**) and `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\_research\`
(buildmode inventories, `hud_slot_map.md`, `director_dda_plan.md`). Only the second is inside the
shipped tree.

**Ship risk: CLOSED (re-verified 2026-08-17).** `build.ps1:32`'s
`$excludeTop = @("_notes", "_research")` is committed and the deployed
`zzzzzz_co-op_hzm_mod_code.pk3` has **zero** `_research`/`_notes` entries. Releases up to v1.1.55 did
ship design docs and retail script extracts; history, not a live hazard. *(This entry previously read
"OPEN NOW" and cited an uncommitted `build.ps1:27` - both stale.)* **Still open:** the regression harness
- the only working automated verification - lives in a directory named `_research`, which the build
script treats as disposable; **promote it out**. Related: four uppercase map scripts (`M1*`, `M3*`,
`M5*`, `M6*.scr`) sit alongside lowercase counterparts, unchecked for case-collision in a pak.


## T16 setmotionanim

**Missing anim + `waittill` = a corpse standing at the wall.** `setmotionanim` with an alias the model
does not have silently no-ops, and the `waittill flaggedanimdone` after it hangs that handler FOREVER
(bug-1921). Three rules: (1) never feed a per-weapongroup anim name to `setmotionanim` without a
whitelist + fallback - the Cornering wall set is LIVE for exactly
rifle/pistol/mp40/mp44/bar/thompson/sten/vickers; (2) audit aliases by grepping the tiki TEXT, not
`.skc` FILENAMEs, which undercount badly (2 groups have `wall_death` skc files; 8 have live aliases);
(3) an alias in `models/human/animation/human_<wg>.tik` is NOT resolvable unless that pack is
`$include`d by the model - vanilla gates the packs inside per-map `includes` blocks, so a coop feature
must add them unconditionally to our `new_generic_human.tik` override (bug-1945).


## T17 level-var-none

- **Reading a level var CREATES it with type `none`.** `GetVariable` returns non-NULL for a variable that
  exists but was never *assigned*, so a NULL guard passes and `intValue()` throws `Cannot cast 'none' to
  int`. `coop_vehKill_monitor` merely *read* `level.coop_vehKills` each frame, which poisoned
  `DrivableVehicle::Killed` so **no drivable vehicle on any map could be destroyed** - it aborted before
  the explosion, the tank sat at negative health with `deadflag 2`, the VEHZOMBIE rescue revived it for
  the next hit, and it read as invincible. **Always ASSIGN a level var before anything reads it**, and
  prefer a type check over a NULL check engine-side. (bug-1371)


## Cross-cutting Q2

2. **Did it run?** ([T3](#t3) — prove execution before tuning; check the gate cvar is actually seeded) —
   and when a constant becomes a cvar, **update every reader in the same pass**. `coop_aiBuffer`
   converted the unsponge detectors but not `actorPainHandler`, still testing the literal 5000 while
   actors buffered to the unseeded fallback 1000: the AI pain handler detached on **every actor's first
   hit**, silently (bug-1733), and fixing it exposed a reader right only by accident (bug-1734).


## T5 modes 1-3

1. **`Cannot cast array to listener`** - vanilla SP treats `$player` as one entity, but with **2+
   connected players it is a 1-indexed ARRAY**, so `$player.origin`, `turnto $player`, `isAlive $player`
   all throw. Repair idiom: an **inline `$player[i]` scan** with a per-element NULL guard, or
   `$player[1]` with a NULL host guard. ⚠️ This line used to recommend
   `exec coop_mod/replace.scr::player_closestTo self` - do **not** reach for that first (bug-1665).
2. **`Cannot cast none to <type>`** - a `level.*` timing global the vanilla SP init would have set is
   never set in coop (`level.thundertime` / `windtime` / `shuttertime` / `rainvolume`);
   `weather.scr:378` alone threw **8,662 times**. Fix: NIL-guards restoring vanilla defaults.
3. **Stale pointers that PASS a NULL guard** - bug-1054's `coop_trackTankTarget` had no `else` branch, so
   a freed player ref lingered and evaded `== NULL`.


---

# Round-9 originals (2026-08-20, last)


## preamble note

> Compressed 2026-08-20 from 71.6 KB to get under the 60 KB ceiling. Every rule, bug id and `file:line`
> anchor was kept (verified by an anchor-set diff); the war-story detail behind the trimmed and merged
> passages, plus one section moved out whole, is verbatim in
> [`archive/traps-pruned-2026-08-20.md`](archive/traps-pruned-2026-08-20.md).


## Quick index list

[T1](#t1)~ parse killers · [T2](#t2) generators corrupt what they write · [T3](#t3)~ silent veto: it
never ran · [T4](#t4)~ capacity families · [T5](#t5) `$player` is an array, NIL != NULL, sequential
storms · [T6](#t6)~ what loads is not what you shipped · [T7](#t7) cvar registration/flags/exec order ·
[T8](#t8) stufftext is lossy, `exec`/`vstr` order, the name bus · [T9](#t9) same-frame spawn race ·
[T10](#t10)~ deploy gaps · [T11](#t11)! record over code · [T12](#t12)~ identically-named trees ·
[T14](#t14)! your verification lied · [T16](#t16) waits that never complete · [T17](#t17) script value
types · [T19](#t19) a radius is a SPHERE · [T20](#t20) one flag two states, one-way latches ·
[`Script Error` skips the STATEMENT](#script-error) · [turrets and AI spread](#turrets) ·
[`item_name` suffixes](#itemname) · [procedural view motion](#procedural) · [TIKI/sound](#tiki) ·
[cross-cutting](#cross-cutting).


## T19 body -> rule + anchors

**Bugs:** 1689, 1690. **Tell:** a proximity prompt fires on the floor below, or through a ceiling — "the
Naxos text appears when you are downstairs underneath the room", "you get caught on the 2nd floor for
his dead body on the first".

**`vector_length` is a 3D distance**, so every "within N units" test is a sphere - almost never what is
meant in a building. **"Near" is a HORIZONTAL question plus a same-storey question, tested as both**: 2D
distance plus a vertical band (96u; a MOHAA storey is ~128). Three sites in one feature had it.

**Flatten both points to z=0 inside a vector literal and use `vector_length`** (locals inside a literal
are fine - `props.scr:407`, `tracescan.scr:79`), **not hand-rolled pythagoras**: a
`sqrt( (dx*dx) + (dy*dy) )` here returned **265.965 for two points 2013u apart**, twice across two
builds, while `dz` by plain subtraction on the next line was exactly right. Instrumented a build later
the same expression was correct, so no mechanism is claimed - only that `vector_length` was right on
every sample and the hand-rolled form was not on at least one. `aimaneuver.scr:129` uses the same inline
form, never checked. **And a range must be the right SIZE for its job** - that feature's warning was
drawn off the *action* prompt's 112u bash range, so it appeared only once the player was on top of the
officer; give an advisory its own, wider range.


---

# Round-10 originals (2026-08-20, last)


## TIKI section

In **`docs/reference/tiki_and_sound_aliases.md`** (frame-command lines inside `server{}`/`client{}`,
aliases without a `maps` spec never loading, per-map `includes` blocks, cut-but-shipped content, never
leaving a backup inside the mod tree). Read it before touching a `.tik` or adding a sound alias. Two
auditors make those traps testable rather than playable: `docs/tools/audit_weapons.py` (every player
weapon) and `docs/tools/audit_shaders.py` (every shader file the engine can load).


## T11 anchors bullet

- **Wrong anchors are worse than no anchors.** `q_shared.h:1680` credits the `MAX_MODELS` 1024->2048
  raise to **bug-866**; the actual work is **bug-892**, and a grep at a wrong path reads as "already
  fixed."
- **28 bug ids cited in source comments have no buglog entry** - bug-237 (packer determinism,
  `build.ps1:11-15`), bug-241 (never deploy under a running game), bug-239 (the brace-counting lesson)
  among them. **For those, the code comment IS the only record.**


## T10 exe gap

**The exe is the usual gap.** `build.ps1` deploys the pk3s, `cgame.dll` and `renderer_opengl1.dll` -
**not** `openmohaa.exe`, `game.dll` or `renderer_opengl2.dll`, which are hand-copied to the GOG root, so
the deployed set spans several build dates and a change can be live in source, in `.cmake`, and *not* in
the binary being run. **A "verified" claim must name which binaries were deployed and when.**
`build.ps1` refuses to deploy while the game is running - if you edited and did not deploy, everything
the user tests is the PREVIOUS build and every conclusion is void. A protocol-constant change ships
**all four** binaries; `game.pdb`/`cgame.pdb` ship next to their DLLs; back up as
`<binary>_pre_<feature>_bak.<ext>` - that hand-run convention *is* the rollback system, with 157 entries
and **zero** for `renderer_opengl2.dll`.


## Cross-cutting Q5

5. **Am I guessing, or measuring?** (was T13) **⭐ BISECT FIRST — a cvar bisect beats any number of
   hypotheses** (bug-1298). Turn things off one at a time until the symptom moves; six deployed
   hypotheses on the gl2 "white distant objects" bug changed nothing, one bisect found it.


## Turrets item 1

**1. A MANNED turret never reads `bulletspread`; the AI knob is `aibulletspread`** (bug-1940). Three
"fixes" tuned `bulletspread` on m3l3's MG42s and every one was a placebo: `weapon.cpp`'s `FT_BULLET`
assigns `vSpread` only for `owner->client` (players), and the `(max+base)/2` fallback is for
`owner == NULL` - unmanned guns, which do not fire. An actor-manned turret fires with `vSpread=(0,0,0)`;
its ONLY dispersion is `m_vAIBulletSpread`, set solely by the `aibulletspread` script event (retail
SH/BT use 300-450; the OpenMOHAA handler ignores arg 2). Gunner `accuracy` keys do nothing either - only
`Actor::GunTarget` consults accuracy. `coop_mg42AiSpread` now feeds the real member.


## T3 opening

**The project's most expensive recurring *shape*.** **Tell:** "we built X and it does nothing / has no
effect / can't be felt." Before tuning X, **prove X executes.** Instances:
[`archive/traps-t3-instances.md`](archive/traps-t3-instances.md) and `traps-t3-archived-rows.md`; the
long narratives for the starred four are in `archive/traps-pruned-2026-08-20.md`.


## T14 opening

**Tell:** a map graded clean by a read-through then storms on boot. t2l2 graded **A-** statically and
throws 265 errors on coop boot - *degraded, not dead*, which is why a read-through missed it. **A live
boot is the only real test.** And **absence does not log**: a parse error screams, but a VO line that
never plays, a trigger nobody walks into, an alias resolving to nothing are silent, so error-driven
testing cannot find them by construction. You need an **expectation manifest** (what *should* fire, from
the BSP entity lump) diffed against **engine instrumentation** (what *did*) - the coverage sweep.


---

# Round-11 originals (2026-08-20, final)


## Turrets section body

**Bugs:** 1920, 1940, 1946, 1950. **The rule under all three: before tuning a value, prove the failing
PATH actually reads it — grep the consumer, not the setter.**

**1. A MANNED turret never reads `bulletspread`; the AI knob is `aibulletspread`** (bug-1940). Three
"fixes" tuned `bulletspread` on m3l3's MG42s and every one was a placebo: `weapon.cpp`'s `FT_BULLET`
assigns `vSpread` only for `owner->client` (players), and the `(max+base)/2` fallback is for
`owner == NULL` - unmanned guns, which do not fire. An actor-manned turret fires with
`vSpread=(0,0,0)`; its ONLY dispersion is `m_vAIBulletSpread`, set solely by the `aibulletspread`
script event (retail SH/BT use 300-450; the OpenMOHAA handler ignores arg 2). Gunner `accuracy` does
nothing either - only `Actor::GunTarget` consults it. `coop_mg42AiSpread` feeds the real member.

**2. AI spread is an AVERAGE — a 2-arg `bulletspread` half-applies to AI shooters** (bug-1920).
`Weapon::Fire` gives a NON-client owner `(bulletspreadmax + bulletspread) / 2`; most tiks never set a max,
so a script `bulletspread 120 120` averages with 0 into an effective 60 and the tune feels dead (m3l3
MG42s "still hit every single shot"). **Any AI spread tune must set all four args: `bulletspread B B M
M`.** Player fire uses a base/max lerp by spread factor, so player-facing tunes are unaffected.

**3. `TurretGun` fixes NEVER reach `VehicleTurretGun`.** It overrides `Think()`, `UpdateFireControl()` and
`GetMuzzlePosition()`, so anything tuned in TurretGun's paths silently skips every vehicle-mounted gun
(halftrack, tank hull MG, jeep). Three separate user reports traced to this split on 2026-08-19: player MG
heat never cycling (bug-1946), and AI road gunners laser-accurate at full damage because the whole coop
tuning trio - damage scale, spread bonus, wandering aim error - was TurretGun-only (bug-1950). **Any
turret-behavior change ships BOTH class paths, or says in a comment why the vehicle side is exempt.** The
trio is `extern`'d in `weapturret.h` for exactly this.


## T12 closed-risk history

**Ship risk: CLOSED (re-verified 2026-08-17):** `build.ps1:32`'s
`$excludeTop = @("_notes", "_research")` is committed and the deployed
`zzzzzz_co-op_hzm_mod_code.pk3` has **zero** `_research`/`_notes` entries. Releases up to v1.1.55 did ship
design docs and retail script extracts; history, not a live hazard. *(This entry previously read "OPEN
NOW" and cited an uncommitted `build.ps1:27` - both stale.)* **Still open:** the regression harness - the
only working automated verification - lives in a directory named `_research`, which the build script
treats as disposable; **promote it out**.


## T6 ESRGAN paragraph

**Related generated-asset hazard:** ESRGAN upscales have shipped hallucinated worm noise (bug-1129), a
GPU-corrupted all-black `netgame_a/b` that blanked the server browser (bug-247), and 29 overridden
**vanilla** menu textures (bug-157). **Brightness-check output before commit**; ESRGAN is for photos and
text and corrupts 1–2px chrome.


## T1 live status

**Live status:** clean (re-scans 2026-07-29, 2026-08-08). bug-1027 (`e3l4/outro.scr`) has this signature.


## Moved from TRAPS.md 2026-08-21 (over ceiling; operative rule kept in place)

- **Reading a level var CREATES it with type `none`.** `GetVariable` returns non-NULL for a variable
  that exists but was never *assigned*, so a NULL guard passes and `intValue()` throws `Cannot cast
  'none' to int`. `coop_vehKill_monitor` merely *read* `level.coop_vehKills` each frame, poisoning
  `DrivableVehicle::Killed` so **no drivable vehicle on any map could be destroyed**: it aborted before
  the explosion, the tank sat at negative health with `deadflag 2`, the VEHZOMBIE rescue revived it for
  the next hit, and it read as invincible. **Always ASSIGN a level var before anything reads it**, and
  prefer a type check over a NULL check engine-side. (bug-1371)
- **Map entity keyvalues arrive as STRINGS.** `#totalguys` / `#activeguys` compared against an int gave
  115 errors a level in `global/parade.scr` and silently killed the parade spawn loop. `int()`-coerce
  once at the top, not per comparison. Same class as the parsed-`.dat` fog values. (bug-1352, bug-1372)
- **A command registered on `ScriptThread` is NOT a Player event.** `iprintlnbold`/`iprintln` live in
  `scriptthread.cpp:225/234` only, so every `<player> iprintlnbold "..."` fails - 39 sites across 11
  files whose messages had *never once* reached a player. The Player-scoped form is `iprint <text> 1`
  (`player.cpp:1222`, `"sI"`). **Confirm a command is registered on that entity's class first.**
  (bug-1374)
- **Some engine events are SETTER PROPERTIES, not commands.** `EV_Actor_SetWeapon` is `EV_SETTER`:
  `self.weapon = "models/weapons/x.tik"` works, `self weapon models/weapons/x.tik` does not exist - which
  is why retail's own post-spawn swaps sit commented out in m1l2a and m5l3. (Command syntax on the getter
  half is a T1 parse killer, bug-910.) Reading `self.weapon` on an ACTOR returned raw `m_csWeapon` -
  whatever a script/tik wrote ("mp40", a full path, any case, or EMPTY for tik-armed actors) - **not**
  the tik `name` the PLAYER getter returns, so a display-name-keyed lookup missed 100% (bug-1943). Since
  2026-08-19 the getter returns the HELD weapon's name field with the raw fallback when unarmed.
  String-keyed array LOOKUPS stay case-sensitive even though `==` is not (bug-1916 family).
- **A bare identifier is a CONST STRING, and `int + conststring` CONCATENATES.** `local.wave1 +
  local.wave2 + wave3 + 5` (missing `local.`) produced `"20wave35"`, and `intValue()` on a string is
  `atoi` -> **20** against a gate waiting for 35: total mission softlock, no error, and it is a *vanilla*
  typo byte-identical in retail. (bug-1377)
- **⚠️ Fixing a type error can UNMASK a latent logic bug.** That same line threw every frame, and the
  throw aborted the parade's done-check, so the parade never stopped and the gate happened to pass; the
  correct `int()` coercion (bug-1372) made the comparison work, the parade stopped at 20, and the map
  became *unfinishable*. **After silencing a recurring script error, re-test the feature it fired in.**
- **`thread <label>` inside a boolean is ALWAYS TRUE** - it evaluates to a HANDLE, so
  `if( x && thread foo::bar )` is `if( x && <truthy> )`. Five `anim/disguise_*.scr` gates never guarded
  anything for years; use `waitthread` when you want the value. Because those branches end in `end`, four
  statements below were unreachable whenever one fired, including the squad-wide papers pass. **When you
  fix a condition that was always true, audit what sits below its `end`.**
- **`continue` in a `while` whose index advances at the BOTTOM = infinite loop = server hang.** `for`
  runs the increment on `continue`; `while` does not. `aihandler.scr`'s actor sweep is a `while` at
  `:302` incrementing at `:484`. Wrap the body in an inverted `if`, and **check the loop KIND and where
  the increment lives before writing any early-skip.**
