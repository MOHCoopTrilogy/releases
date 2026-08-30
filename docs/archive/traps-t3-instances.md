# T3 silent-veto — the confirmed instance table

Moved out of `docs/TRAPS.md` on 2026-08-12 to keep that file under its 60 KB ceiling.

**The PATTERN and its rules stay in TRAPS.md T3** — that is what a fresh session needs. This file is
the evidence behind it: each row is a feature that was built, shipped, and never once executed.
Read it when you want to know how varied the shape is, or when you suspect a new one and want to
compare tells.

**Confirmed instances:**

| Feature | Why it never ran | Bug |
|---|---|---|
| **All AI grenades** | `GrenadeWillHurtTeamAt` compared `.length() < 65536` — i.e. any squadmate within 65,536 **units** (the whole map) vetoes the throw. Actors auto-squad-merge at first shots → ~100% of offensive grenades AND the kick/return chain suppressed. Fixed to `.lengthSquared()` (256u blast radius). | actor_anim_audit |
| **Officer Stuka + binoc airstrike** | An up-trace to detect a ceiling **hits the skybox brush** (sky brushes are `CONTENTS_SOLID`), so low-skybox maps read as "indoors" and silently disabled both. Fixed by testing `SURF_SKY` (0x4) — via int div/mod, since MOHAA has no bitwise AND. | sky_trace |
| **`s_sfxduck` (two attempts)** | Server-stuffed SETs of `CVAR_ARCHIVE` cvars are **dropped** by `CG_IsSetVariableAllowed` unless whitelisted. Two earlier attempts silently did nothing. | sfx_duck |
| **AI tactical retreat** | The engaged-check required `self.enemy`, a formal target lock that **scripted damage never sets**, so it never committed. | 1104 |
| **`MAX_SNAPSHOT_ENTITIES`** | A file-local `#define` stayed at 1024 for 8 days while everything downstream was raised to 2048. Entity 1025+ dropped by a bare `if (full) return;` whose own comment read *"silently discard entities"* — **no `Com_Printf`, zero evidence in any log.** | 1186 |
| **`cg_dbnoEyeDrop`** (3 placements) | Ran, but its write was **discarded downstream** twice (eye rebuilt from the model tag; view-height smoothing hard-assigns `origin[2]`). v1 silently moved the THIRD-person pivot instead. See "the write is overwritten" below. | 1238 |
| **The `SHIPPED-CODE-DISABLED` class** | Squad brain, morale, tactical retreat and the whole `coop_aiDynamic` layer are wired into `main.scr` behind gates testing `== "1"` on cvars **seeded in no shipped cfg**. They have never run for a player. | see [OPEN.md](OPEN.md#never-ran) |
| **A label with NO CALLER AT ALL** | `coop_stealthArmOnHurt` — the watchdog that arms an unarmed player being shot — is defined at `itemhandler.scr:1423` and **threaded by nothing**, anywhere. Found only because a new feature hosted inside it never appeared. Worse than dormant: bug-1674 diagnosed a race *through* it and bug-1676 shipped a fix *into* it, both reasoning about code that has never executed. **A grep for the label name, not for its cvar, is the only check that finds this class.** | 1688 |
| **m3l1b's FLAK 88s** | `startFiring` on `$88mm_weapon1/2` never fired: they are class **`Animate`**, not `TurretGun`, so the whole turret API silently fails. A follow-up `setAimTarget` fix was wrong the same way — correct `TurretGun::Think` analysis applied to an entity that was never a TurretGun. **Check the entity's CLASS before reasoning about its API.** | 1553 |
| **Service Record `coop_srsync`** | A client console command wired to a UI `stuffcommand`, which **never executes** from the disconnected menu - so five successive rewrites living inside `CL_SyncSR_f` could not take effect and the symptom was byte-identical every time. Work that must run on the main menu belongs in `CL_Init` (proven to run) or in `exec`+`seta` builtins. | 1544, 1546 |
| **47 shipped challenges** | v1.2.1 added ~50 `chal_def` rows and none of the hooks meant to feed them. `chal_bump` early-exits when `level.coop_chal_statN[stat]` is NIL, so an unbumped stat is a **no-op, not an error** — the rows show in the Service Record and can never be completed, and every static check passes. Corollary that cost two duplicate challenges: **absence of a hook is not absence of a feature** — check `chal_def` by title and feat, never by whether a producer exists. | 1596–1598 |
| **A whole map's lighting + effects (e2l1)** | A bare `level waittill spawn` in a retail sub-script. In coop that event has already fired, and a failed `waittill` **does not wait** - so the script ran before the map's entities existed. See the shape note below. | 1294 |

---

## Compressed out of T3 on 2026-08-22 (budget)

TRAPS kept the rule sentence of each of these; the full retelling lives here.

**⭐ A guard written for one question is wrong for the neighbouring one** (bug-1687).
`coop_isProtectedActor` answers *"leave this actor alone?"* and on m2l2a says yes to the whole cast (14
`ai_alarm` actors, anything with an `alarmthread`, every papers checker, the scene actors); reused for
*"who would notice a corpse?"* it vetoed everybody. **Re-read what a predicate was written to decide
before reusing it; when the answers differ, SPLIT rather than widen** — detection now filters on
nothing, the role uses a narrower `coop_bustCanKneel`, and the original stays for the containment sweep.

**⭐ Gating one entry point is not gating the feature** (bug-1685). Papers had **three** writers -
`enableClickablePapers`, `forcePapersInHand`, persistent `coop_papersAnytime` - and only two carried the
`coop_busted` guard, so pressing fire equipped papers and swallowed the trigger ("he just doesn't
shoot"). **Grep every writer of the shared state before calling a gate complete.** Same shape in our own
tooling (bug-1860): `docgen.py` applied `SELF_EXCLUDE` to the porcelain FILE LIST but not to the
`git diff --shortstat` it embeds in CHRONOLOGY, so every `build` changed the number CHRONOLOGY reports
about itself and **`check` could never pass** - a permanently red oracle trains everyone to ignore it.

**⭐ Our own guard disabled the retail mechanism**, twice in one day. On m2l2a `$naxos` is a
`trigger_multiple` with `spawnflags 128` = `TRIGGER_DAMAGE`, so the engine gives it
`takedamage = DAMAGE_YES` + `CONTENTS_CLAYPIDGEON` (`trigger.cpp:285-289`) - **shooting it is how retail
completes that objective**, and our stealth workaround opened with `$naxos nottriggerable` (bug-1671).
Same shape as bug-1669's limp *warning* disabling its own feature. **Ask what the vanilla mechanism
already is before adding a guard**, and when a user says "this is how vanilla handles it", read the
ENTITY, not the scripts around it.

## Moved from TRAPS.md T3, 2026-08-28 (budget prune - the rules stay in TRAPS, the narrative lives here)

**HEADLESS CANNOT TEST A PLAYER-TIMING BUG - THE 2-PLAYER HARNESS CAN.** A bare dedicated boot has
no clients, so any race between "player spawns" and "map does X" has no window to lose and always
passes; three fixes shipped green headless and failed live on exactly that. **`launch_dedicated_2player.ps1
-Map <map>` + `spawn_clicker_2player.ps1` gives real players with no human in the loop** (the
clicker joins and re-joins across map changes); then `scratchpad/rcon.py map <map>` restarts with
both already present at t=0, the condition a listen server has. Do not ask the user to click.

**BEFORE RE-ASSERTING CONTESTED STATE, PROVE THE WRITE IS A *SET*.** A one-shot write into contested
state is a bet on ordering and this project loses it - but re-asserting onto a **toggle** is an
oscillator, not a fix, and `notarget` is a toggle on players ([T12](#t12)). **And judge by the state
itself, never a proxy**: five attempts were scored on `engaging`/`foeCls=Player`, both structurally blind
to that flag (`cansee` has no `FL_NOTARGET` test, `entity.cpp:2941`; `AddPotentialEnemy` rejects only
dead/IGNOREME, `actorenemy.cpp:280`), so an actor names a notarget'd player as `.enemy` while the engine
refuses the attack (`actor.cpp:9150`). **A flag with no getter cannot be debugged; add the getter first.**

**ONE RUN IS NOT PROOF WHEN THE BUG IS INTERMITTENT.** Two "fixed" verdicts on 2026-08-22 were single
runs - one a log truncated 11 s before the scripted fight starts, the other a config where the suspect
happened not to fire. Establish the *shape* of the measurement changing (`engaging 7->0` while
`canSeePlayer` stays 9), not the number.

**A vanilla scene reachable only from a BSP `trigger_once` never runs in coop.** m3l3's `main` carries
seven `//thread sceneN` lines "called from a trigger_once in the bsp"; scene6's one-off workaround hid
the pattern and scene7 shipped asleep - no crews, no MG nests, an objective that could never complete.
**Grep a map's `main` for commented-out `sceneN` threads, account for every one, guard each.**

## Rules held here (moved out of TRAPS T3 on 2026-08-30 to stay inside the 70 KB ceiling)

These four were kept in `TRAPS.md` as one-line rules while their narratives lived here. The rule
text now lives here too; `TRAPS.md` keeps a pointer.

- **Use `launch_dedicated_2player.ps1` + `spawn_clicker_2player.ps1`, never a bare headless boot,
  for anything player-timing.** A boot with no clients has no window to lose, so it always passes.
- **Prove a re-assert is a SET, not a toggle, and judge by the state itself, never a proxy** - a
  flag with no getter cannot be debugged.
- **One run is not proof when the bug is intermittent** - establish the SHAPE of the measurement
  changing.
- **Account for every commented-out `sceneN` thread in a map's `main`** - a vanilla scene reachable
  only from a BSP `trigger_once` never runs in coop.
