# OPEN — defects, unverified work, and unbuilt plans

Status vocabulary in [SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md#status-vocabulary).
Snapshot date **2026-07-29**. The buglog is live and concurrently written — it grew 634→639 during
the audit that produced this — so treat counts as of that date.

## Sections

> The 2026-08-18 evening playtest batch was archived on 2026-08-22 to
> `docs/archive/open-playtest-batch-2026-08-18.md` - three releases have shipped since it was
> written, so none of it was still an open question.

[P0 — infrastructure](#p0) · [Never ran](#never-ran) · [Defects with evidence](#defects) ·
[gl2 open items](#gl2) · [Diagnostic pending](#diagnostic) · [Awaiting playtest](#unverified) ·
[Planned, not built](#planned) · [Record-vs-code discrepancies](#discrepancies) ·
[Tooling lost](#tooling-lost) · [Config](#config) · [Cheapest wins](#cheapest)

---

<a name="p0"></a>
## e2l1 (Kasserine glider) - parked

Four open item sets from the 2026-08-03 round (remaining glider items, the crash-landing arrival
spec, the unresponsive truck "statue", and the P40 final-tank explosion chain) are parked in
[archive/e2l1_open_items.md](archive/e2l1_open_items.md). Still open, just not the active front.

## P0 — infrastructure, fix before feature work

*Re-verified 2026-08-15 by sha256, not by mtime. Four of the five entries here were stale and have
been moved to [archive/open-p0-cleared-2026-08-15.md](archive/open-p0-cleared-2026-08-15.md). The
method matters more than the result: mtime only says when a file was written, so every claim below
was settled by hashing the live binary against the published manifest.*

**What was measured.** 8 of the 9 binaries in `manifests/manifest-1.2.9.json` are **byte-identical**
to the live copies in `G:\mohaa-gl2` — `openmohaa.exe`, `cgame.dll`, `renderer_opengl1.dll`,
`renderer_opengl2.dll`, `omohaaded.exe`, `SDL2.dll`, `OpenAL64.dll`, `libcurl.dll`. Only `game.dll`
differs, because it was rebuilt after v1.2.9 shipped and has not been published yet.

### `renderer_opengl2.dll` has zero rollback points
`OPEN` · *Re-counted 2026-08-15 using the real `*_bak.*` convention: `game` 80, `openmohaa` 43,
`cgame` 25, `renderer_opengl1` 19, `omohaaded` 3, `renderer_opengl2` **0** (174 total).*

**This one survives, unchanged.** The `<binary>_pre_<feature>_bak.<ext>` convention is the project's
only binary rollback system and it is entirely manual. The module with no backup at all is the one
whose port is still in progress, which is precisely the one most likely to need reverting.

---

<a name="never-ran"></a>
## Never ran — `SHIPPED-CODE-DISABLED`

A status class this project needed and did not have. These are wired into `main.scr` behind gates
testing `== "1"` on cvars **seeded in no shipped cfg** — `autoexec.cfg`, `coop_defaults.cfg` and
`coop_mod/*.cfg` all return zero hits. Note the gates test `== "1"` while the cvar is **unset (empty
string)**, not `"0"` — so records describing these as "default 0" imply a deliberate shipped default
that does not exist.

| System | Gate cvar | Gate site | Records claim |
|---|---|---|---|
| ~~Engine juke/hide + AI maneuver mover~~ | `coop_aiDynamic` | `main.scr:247`, `:250` | **NOW SEEDED** - g_main.cpp:307 (archived) + autoexec.cfg:583 |
| ~~Squad brain~~ | `coop_aiSquad` | `main.scr:255` | **NOW SEEDED** - g_main.cpp:308 + autoexec.cfg:586 |
| ~~Squad morale break~~ | `coop_moraleEnable` | `main.scr:257` | **NOW SEEDED** - autoexec.cfg:594 |
| ~~Tactical retreat~~ | `coop_retreatEnable` | `wounded.scr` | **NOW SEEDED** - autoexec.cfg:596 |
| Last-known search sweep | `coop_aiSearch` | `aisquad.scr:226` | was the ONLY one still unseeded - seeded 2026-08-17, **never run before that** |

**[2026-08-17] This table was stale.** Four of the five had since been seeded (engine pre-registration
and autoexec), leaving only `coop_aiSearch` genuinely dead - which is exactly the failure mode the
section warns about, so it is corrected in place rather than appended to.

**⚠️ The AI maneuver mover was verified only by the bot rig — which sets the gate cvar itself.** It
has never run for a player. See [TRAPS.md § T15](TRAPS.md#t15).

**Also unseeded** (from the 144 `coop_*` cvars seeded nowhere): `coop_aiScale`, `coop_aiScaleChance`,
`coop_aiScaleTest`, `coop_health` (the 750 lives at `server.scr:223-227` as an *else-branch*),
`coop_dbnoCorpseRevive`, `coop_unsponge` (its on-by-default status rests on a comment at
`aihandler.scr:277`, "unset counts as 1" — and it is a **fresh bullet-sponge fix**, bug-1212).

**Decision needed:** for each, either seed a deliberate default in `coop_defaults.cfg`, or document it
as opt-in. Right now the shipped behaviour is whatever a fallback branch happens to do.

---

<a name="defects"></a>
## Requested, not yet started (2026-08-18)

- **Reload magazine keeps the stock skin on a finished gun.** The gun's own `Clip` surface IS
  reskinned (verified on the gold Thompson) and the mesh has only four surfaces, so the magazine
  seen in hand during reload is a DIFFERENT model. `models/ammo/thompson_clip.tik` is cached by the
  weapon tik but nothing in the content or the engine spawns it by name, and no viewmodel or
  human_thompson animation attaches it - so its source is still unidentified. Needs a runtime
  answer, not more static searching.

## Awaiting the next playtest (2026-08-17)

- **Panzerfaust: REMOVED (2026-08-18).** Never fired despite the bug-1907 elimination
  campaign; the user called it a dead end. Stripped from every system; armory id 73 stays a
  permanent hole (never renumber). The WW1 flamethrower remains the candidate for a future
  launcher-slot novelty if wanted.
- **Skin system: built end-to-end, awaiting menu playtest (2026-08-18).** All 357 finish variants
  across 45 guns; the finish strip (8 buttons + VARIANT) in the armory; 7 finish challenges; both
  unlock gates server-side at apply AND spawn; 25 imported model variants across 12 host guns
  on the strip's VARIANT button, gated on each gun's Elite challenge. Stage finishes visually approved in play ("three metal finishes are good"). STILL
  OPEN: the in-hand reload magazine keeps the stock skin (models/ammo/<gun>_clip.tik - reference
  point unknown, needs a runtime probe; both the MP40 and Tommy packs ship replacement clip
  models we can use once found); MOHPA porter unidentified - credits entry pending.

## Defects with evidence

### e3l4: jeep passenger never completes the first supply run — INSTRUMENTED, cause open
Freezes at the jeep, never reaches a crate, spams `Path not found in Actor::MoveToPatrolCurrentNode`.
Driver runs the same chain and succeeds; the passenger completes it at a *later* bunker, so it is not
a missing anim or bad model. Failsafes (22s/30s) delete the parked thread and seat the crew, so the
map completes; 12 `^~^~^ E3L4P` breadcrumbs will name the hanging call next run. Same map, possibly
related: constant `couldn't find end node` for unrelated actors. bug-1361/1366, [TRAPS T16](TRAPS.md).

### Pinned challenges: no in-mission pin surface
Lobby and disconnected Service Record can pin; the in-mission `chal_menu` panel cannot — no cursor,
and the lobby cursor's click is `BUTTON_ATTACKLEFT` (`player.cpp:13559`) so reusing it would fire the
weapon and swing aim. Needs a `game.dll` change. Disconnected pins queue in the player's name and
apply on next connect, one at a time. bug-1362/1364.

### m3l2: `SV_FindIndex overflow (max=1280)` ×243
`OPEN` · *bug-1219* — explained entirely by the P0 deploy gap above. **Will resolve when the current
exe is deployed.** Do not "fix" it in source; source already says 1600.

### e2l2: 12× "applied to NULL listener"
`OPEN` · *bug-1220* — on `origin`/`hide`/`notsolid`/`nottriggerable`/`triggereffect`/`set_respawn`/
`notdroppable`. The known cure is [TRAPS.md § T5](TRAPS.md#t5): guard the entity refs with **BOTH**
`NIL` and `NULL`, because they are different and coop hits both. Detected 2026-07-29.

### t2l2: 265 script errors on coop boot despite an A− static audit grade
`OPEN` · *bug-1026* — 36× `Couldn't load models/nil.tik`, missing `models/vehicles/panzerwerfer42.tik`
×4, plus "must specify explicit classname". Addon MG42 nest gunner AI and the panzerwerfer
rocket-artillery vehicle fail to resolve → unmanned nests, missing vehicle. Map still reaches
coop-ready, so **degraded, not dead** — which is why the read-through missed it. The fix field reads
literally "OPEN - needs investigation." See [TRAPS.md § T14](TRAPS.md#t14).

### Phase C stealth contain (m2l2a) — shipped, mostly unverified

The contain loop itself IS play-verified end to end (bash -> stun -> pistol -> kill -> 10s clean ->
"Situation Contained" -> papers restored; user: *"Situation contained worked"*). Everything built
around it on 2026-08-10 is deployed and **not** confirmed in play:

- the **15s loiter -> cover blown** outcome (the investigator itself IS verified: bug-1695/1696)
- escalation firing the real alarm via `trigger $waittrigger_alarm_master`
- "seeing the stun animation" as an escalation route
- the Naxos room/hold prompts and the sabotage progress bar
- the squad-wide papers free-pass CODE (bug-1693) - the observed behaviour comes from the engine
  demoting an accepting sentry to a saluter, so the new path has never run

Since confirmed in play: the contain loop, the escalation loadout (1692), the bust-time aggro
exemption (1686).

### m6l2a contain — bugs 1732-1737, deployed 2026-08-12

1732 / 1734 / 1735 / 1736 are **closed** — each exposed the next, verified in a three-contain run
(kill / let-survive / kill). Causes in buglog. Still open:

**1739 unverified — the stun's re-assertion has never once fired.** The re-hit that pulls a guard back
into pain is gated on `curHp > minHp`, `minHp` = 40% of health. That floor predates bug-1731's drop to
`coop_bustVulnHealth` 25: 40% of 25 is **10**, exactly where the bash's own 15 damage lands him — false
from the first tick, and `BUSTSTUN` prints a flat `hp=10.000` in *every* contain, including the ones
that looked right. The stun rode on one pain animation, holding only when the guard faced away
(`EnemyIsDisguised` = `hasDisguise && (isDisguised || !CanSeeEnemy)`). 1737 is intact and still needed:
it makes pain *start*, not *hold*. Absolute floor of 2 while dropped. Verify: hp **decreases**
(10→7→4→1) instead of sitting flat.

**1738 unverified.** One latch both kept the corpse rediscoverable *and* pinned `seers` at 1 forever,
so the loiter timer ran on with every witness dead — cover blew 6 s after the player contained the
investigator himself. Now a live per-tick count. Verify: silence the investigator, stay by the body,
expect `BUSTBODY nobody has eyes on the body any more` and no escalation.

**1733 partial.** `PAINDETACH` still fires on a same-frame double hit — gap **exactly 3.0** both times
regardless of real damage (400, 15): the stun's `hurt 3` racing a round, which `actorPainHandler`'s
exact-equality test can't tolerate. Bashed guards only; 1734 covers both paths, so it degrades.

**Bullet sponges no longer reproduce** — a full Thompson run, none seen, and no damage value was
changed. Probably fixed by 1733, not confirmed.

### ⚠️ m2l2a REGRESSION RISK — the attackplayer latch removal (bug-1700)

**User-requested review item.** m2l2a is signed off as very playable; bug-1700 changes the aggro
funnel *every* map uses, to make loud→quiet missions possible on m6l1c.

`sentientIsSeen` now supplies `local.sentient` when the caller's target is NULL, so `attackPlayer`
takes its `attackentity` branch instead of the latching `attackplayer`. Unmeasured consequences on
m2l2a:

- **`attackentity` is advisory, `attackplayer` was forcing.** A guard that used to commit may now
  decline — that would make cover-blown escalation *weaker*, not stronger.
- **The latch was also masking the disguise on m2l2a.** Without it, a guard who engaged you can be
  fooled again by the uniform. On the papers route that is effectively a difficulty change.
- **Phase C sits downstream** — the contain path reaches `sentientIsSeen` through
  `anim/disguise_deny.scr` / `disguise_accept.scr`.
- **Latch split CLOSED 2026-08-11** (bugs 1707/1708) - see `docs/archive/open-resolved-2026-08-10.md`.

**Acceptance test — PASSED 2026-08-11.** Full m2l2a stealth run by the user against the whole
day's global changes (bug-1707 engine threat gate, four attackplayer latch sites, two disguise
retry-loop fixes, spawn-click fire lock). Log evidence: quiet Naxos sabotage, two officer
contains offered (`canContain=1`), two body investigations armed, sentries correctly refused
(`canContain=0`), and **zero** Script Errors, parse failures, salute-guard flips (SALATK) or
latch restores — against 1789 restores in the broken run that started the investigation.
The user's verdict: "m2l2a ran fine with what you asked".

### `coop_stealthArmOnHurt` is dead code — and something else may be covering for it

Defined at `itemhandler.scr:1423`, **threaded by nothing anywhere** (bug-1688). It is the watchdog
that arms an unarmed player who is being shot. Deliberately not enabled mid-playtest. **Open
question:** with it dead, what arms a player shot while unarmed? `maps/m2l2a.scr::coop_blownOnDamage`
polls player health and threads `coop_armOnBlown`, so m2l2a may be covered *by the map* — which would
mean every other `coop_noWeapon` map has no such safety net at all. Worth one grep before enabling.

### A hand-rolled distance returned a wrong value once and could not be reproduced

bug-1690. `sqrt( (dx*dx) + (dy*dy) )` gave 265.965 for points 2013u apart, twice, then computed
correctly at a different position. **Mechanism unexplained; no trap entry claims one.** All affected
sites now use `vector_length` on flattened points. `coop_mod/aimaneuver.scr:129` uses the same inline
form and has never been checked.

### objectives.scr's NEW OBJECTIVE toast collides with two live features

bug-1680. It owns 135-142 (header 135, lines **computed** `136 + local.line`), overlapping the DBNO
team-revive channel (135-140) and the XP micro popup (142-144). All three are mission-time and can
co-display. Not fixed: rewriting a widget that currently works is a blind bet with no oracle
(TRAPS T3 UI corollary). Moving the toast into the menu-only 216-249 range would fix it and return
eight fade-exempt slots — **the ≥100 band is now completely full.**

### Second vehicle-crew spawn path on t2l2 / t3l2 still unguarded
`OPEN` · *`_research/coop_2player_sweep.md` residual list* — the `vehicles_thinkers.scr` NIL-crew guard
fixed the jeep maps but a **different function** spawns the halftrack and T-34 crews (t2l2 25 casts,
t3l2 8). Named in the audit's own residual list; no follow-up found in the buglog.


### Dedicated server segfaults on bare DM maps
`OPEN` · *bug-330* — `game.dll` crashes loading `obj`/`obj_team1` under a dedicated server. Baseline
reproduces with **zero rendezvous cvars**, so it is not NAT-related. Coop maps load fine — likely a
coop hook assuming coop init ran. Fix: "none yet." ⭐ Also recorded: `omohaaded.exe` has headless env
quirks (stalls **with** `fs_homepath`, dies **without** it); the working dedicated recipe is the
**CLIENT exe with `+set dedicated 1`** from the GOG dir.



### AI crouch posture stays disabled (crouch leg was the crasher); prone is BACK
`PARTIAL` · *`anim/attack.scr`* — the recorded crash lived in the CROUCH leg only
(`AttackLongRangeCrouch`→`AttackCrouchDodge` command overflow; repro: m1l1 barrels), so crouch
stays hard-zeroed. Prone re-enabled 2026-08-18 behind `coop_aiRetailProne` honouring
`level.aipronechance`, plus a dwell loop (bug-1922) so divers stay down 3-6 volleys instead of
popping straight back up. Prone feel awaits playtest; crouch needs an engine fix first.

### ET3 engine jink is built and dormant
`OPEN` · *`actor_turret.cpp State_Turret_Combat`* — `coop_aiJinkMs` default 0 because the rig caught it
never firing. Dead member `m_iCoopJinkTime` remains. A re-do needs forcing it from the retarget path
or gating to aggr-role TURRET enemies.

### Airborne black-texture patch — 4th report in the same family
`OPEN` · *bug-921* — four separate fixes against the same visible symptom (bugs 499/525/530/921). A
later 5-round resolution via the shader-isolation recipe is attributed to bug-922, **but bug-921 was
never marked resolved.** Cannot determine from the record alone whether the airborne pouch is
currently correct. **Needs one look.**


## gl2 open items

### Non-depth-writing surfaces cannot be fogged at all — the screen-space fog's structural gap
`OPEN` · *bug-1296 · Anchor: `renderergl2/glsl/globalfog_fp.glsl`, `renderergl2/tr_postprocess.c`*

gl1 fogs **per surface during each surface's own draw** and carries a per-stage decision table
(`renderergl1/tr_shader.c:3227-3279`: additive→BLACK, modulate→WHITE, alpha-blend→fog colour). gl2
replaced that with a screen-space pass driven by the depth buffer. A surface with `blendfunc` and no
`depthWrite` (~13.5% of shader defs — propeller discs, some glass/water/FX) **leaves depth at 1.0**,
so no depth-based pass can ever reach it. Those surfaces render unfogged regardless of cvar.

**The obvious fixes were all evaluated and rejected on evidence, 2026-08-02 — do not re-propose them
without reading this:**

| Idea | Why it fails |
|---|---|
| Make them write depth | Breaks transparency sorting outright — they would occlude each other. Also unsupported: gl1/gl2 depthmask construction is verbatim identical, and the one divergence runs the *opposite* way (gl1 clears the mask in a case gl2 does not) |
| Stencil "is sky" mask | Fixes *which* pixels are exempt, not the *distance* they are fogged at — a non-depth-writing prop is then correctly classed as not-sky and fogged at zFar, i.e. buried. Also expensive: **no gl2 FBO has a stencil attachment**, `tr.globalFogFbo` deliberately has none to avoid a feedback loop (`tr_fbo.c:327-329`), and `FBO_Blit` unconditionally ORs `GLS_DEPTHTEST_DISABLE` (`tr_fbo.c:642`) |
| Port gl1's per-stage fog into gl2's forward pass | **Double-fogs** every blended stage over opaque geometry — the screen-space pass fogs per *pixel* by the wall's depth, the forward pass per *surface* by its own: a tracer at 1000u renders 0.27× instead of 0.52×, halving distant tracers/flashes/explosions including this mod's own FX. Also blends in the **wrong colour space** (forward fog is pre-tonemap; the screen-space pass runs post-tonemap because `r_globalFogPreTone` is pinned to 0 until gl1's ACES grade is ported) |

**Conclusion:** a coherent hybrid needs a per-pixel "already fogged" mark, which *is* the expensive
stencil attachment. Not worth it for the residual class. Fixed instead: the epsilon (bug-1296), which
was the dominant cause and covered all *depth-writing* geometry.

### The retail sky sources are 512×512
`OPEN` · *bug-1295* — gl2 no longer DXT1-compresses them (that was ours), but the source itself is
512² per cube face and reads soft at modern resolutions. Upscaling is possible but must be done as a
**set** — faces are upscaled independently by any tool, so cube-edge seams can drift, and ESRGAN
hallucinates detail that reads as mottling on smooth cloud gradients. User is willing "unless there is
risk of it looking worse"; decide only after seeing the uncompressed 512.

### `Z_TagMalloc` zero-size spam on the main menu
`OPEN` · *`bug-gl2-ztagmalloc`* — `Z_TagMalloc, Negative or zero size 0 tag 12` every gl2 menu frame;
the same A/B menu boot under gl1 is clean. Cause unknown. ⭐ The investigation **did** close off a
wrong theory: the widget UI otherwise renders fine under gl2 (What's New board, text, buttons all
draw), so the "`.urc`-invisible / FBO-ordering" theory is **dead**. Next step: find what tag 12 means
and grep `Z_TagMalloc` callers missing a size-0 guard.

### Some bullet-hole decals render RED — deliberately not guessed at
`OPEN` · *`bug-gl2-decal-red-dds`, `bug-gl2-01`* — `rgbGen` is **refuted**: gl2's default-rgbGen
resolution (`tr_shader.c:1988-2001`) and the `CGEN_VERTEX` mark-color path are byte-identical to gl1,
and both mark shaders (`bulletset_1`, `bullet_plasterhit`) carry explicit `rgbgen vertex` so they
never hit the default. **Explicitly left UNFIXED:** *"a neutral texture through an rgbGen-identical
shader cannot produce red, so the mechanism is unexplained; guessing risks regressing 2370 working
world DDS or the mark system."* A decisive boot test was handed to the user instead. ⭐ **This
restraint is a model entry** — see [TRAPS.md § T13](TRAPS.md#t13).

### Invisible briefing NPC on e2l2
`OPEN` (accepted, low impact) · *`bug-gl2-e2l2-briefing-npc-invisible`* — `$lyndon`
(`models/human/sc_al_brit_cmd`) is invisible during the e2l2 intro cinematic; present and targetable,
`SKELDRAW ent=213`. **NOT the model** — the same model type renders fine in gl2 on other maps
(user-confirmed), refuting model/skinning/composition/58-bone theories. **NOT render-state** — none of
`r_test_forcepose`/`twosided`/`maskrfx`/`noprepass`/`forcelod0` changed it. If revisited, the recorded
direction is the **e2l2 intro camera/cinematic view setup**, not the model or renderer.

### Shimmer on thin decorative geometry (shadow acne)
`OPEN` · *bug-1164* — user-reported on m1l1 wall trim; not present on gl1. Same session as bug-1209,
which newly **wired** gl2 character sun-cascade shadows — worth checking whether that wiring interacts
with or worsens this.

### Bloom is a no-op at the shipped threshold
`OPEN` · *bug-1149* — proven working at deliberately extreme settings (m3l1a mean 123.5→171.4, near
58.0→178.8, correct wide Gaussian) but does nothing at threshold 0.664756, because **gl2 thresholds
the pre-tone HDR buffer while gl1 thresholds its display-referred LDR backbuffer** — same chain
position, different numeric domain. **Open decision: re-map the threshold into HDR domain, or move
gl2's bloom after the tone stage.**

### Seven gl1 post-FX have no gl2 equivalent
`PLANNED` · gl1 order is SSAO → DoF → **bloom (done)** → god rays → **grade (done)** → FXAA → sharpen
→ heat haze → rain. All live in `renderergl1/tr_postprocess_gl1.c` as self-contained GLSL; **the bloom
port is the stated template for each.** ⚠️ `coop_defaults.cfg` ships `r_ppSSAO 1`, and bug-1211 records
that `r_ppSSAO 1` under gl2 turned the screen black until guarded — **the default config and the gl2
renderer are on a collision course if gl2 ever becomes the default.**

### `r_globalFogDebug` is still `CVAR_TEMP`
`OPEN` · *`renderergl2/tr_init.c:1926`* — temporarily moved off `CVAR_CHEAT` because a listen server
runs `sv_cheats 0` and clamped it back to 0, so the debug views could never enable (the first run
produced 3 identical captures). **Restore it to `CVAR_CHEAT`** at scaffolding-strip time.

### Diagnostic scaffolding not yet stripped
`OPEN` (deferred deliberately) · ~90 interleaved sites. Deferred for good reasons — `CMDTRACE`/`IMM2D`
solved bug-1144, `r_globalFogDebug` is still in use, the heavy probes are gated behind `r_skeldiag`
default 0, and a 90-site edit is not a safe tail-of-session change. Two loose ends to close at strip
time: the `r_globalFogDebug` flag above, and `tr_model.cpp`'s ungated
`SKELREG`/`SKELDIAG`/`SKELDRAW` — though those are **deduped to once per model handle**
(`tr_model.cpp:50-51`), so "spams" overstates it; they are bounded by model count, not frame rate.

---

<a name="diagnostic"></a>
## Diagnostic pending — a probe exists, awaiting one boot

### m1l1 2nd-ranger_private actors render mangled
`OPEN` · *bug-1213; bug-1184; bug-1214; open task #16* — limbs stretched into spikes, faces flattened,
both in and out of the truck; the `2nd-ranger_captain` in the same truck renders correctly. **Six
investigations.** ⭐ **The mod data is exonerated with proof** — a full TIKI setup plus a skeletor merge
simulation of both models using the real session keyvalues was independently re-derived. **No guess
was shipped**; instead a decisive gated diagnostic was added (`^~^~^ POSECHK` in
`tiki/tiki_tag.cpp TIKI_GetFrameInternal`, cvar `tiki_posecheck 1`), plus two real engine defects
found in passing (bug-1189). bug-1214 raised `MAX_SKELMORPH` 12800→131072 as a related latent silent
OOB. **Candidates not ruled out:** corrupted retail `truck_idle`/`twitch_guy01.skc`, `MAX_SKELBONES`
interaction with gl2 cascade shadows, or the per-frame `gettagangles` puppeteering itself.
⚠️ Note the workaround that IS live: `maps/m1l1.scr:341` uses `truck_idle_guy02`/`truck_twitch_guy02`
instead of the duplicate-channel guy01 retail clips (bug-1162) — a script-level workaround for a
retail asset defect, not an asset fix. And `maps/m1l1.scr:1683` carries the bug-1184 revert.

### Reload camera dip never visible
`OPEN` · *bug-165 (2026-06-29 — one of the oldest still-open items)* — `cg_reloadCamDip` has no visible
effect even at 6. **The entire signal chain was source-verified**: `player_Torso.st`
`viewmodelanim reload` ×10 → `player.cpp:11750` → `VM_ANIM_RELOAD` → `ps.iViewModelAnim` set and
networked — **the same field the WORKING ADS off-hand-hide reads** at `cg_modelanim.c:1752` — and
`cgame.dll` confirmed loading from the GOG root per `qconsole.log`. "PENDING runtime data": a temp
diagnostic behind `cg_reloadCamDebug 1` prints every `iViewModelAnim` transition to determine whether
the signal fires at all.

### Mine detector possibly still lost after DBNO revive
`OPEN` · *bug-898; bug-893; bug-919* — marked "UNRESOLVED — needs live confirmation".
`coop_reissueMissionItems` runs on all revive/respawn paths (`dbno.scr:687`, `medkit.scr:383`,
`itemGetAll:761`) and gives via bare `self item` under the `changeGameType`-0 wrap added by bug-893.
**Two candidate causes remain distinguishable only in play:** present-but-holstered, versus genuinely
absent. A diagnostic behind `coop_missionItemDebug 1` prints the gametype **during** the give (proving
the wrap took) then does `self use <item>` + `returnActiveWeapon` per mission item to print PRESENT vs
ABSENT. ⚠️ **bug-919 later retired `coop_missionItemDebug` to 0 in autoexec, so the probe is currently
off.**

---

<a name="unverified"></a>
## Awaiting playtest — `SHIPPED-UNVERIFIED`

The full list is [FEATURES.md](FEATURES.md) (roughly 60 of ~75 systems). These are the ones where the
record ends explicitly in "NOT YET VISUALLY VERIFIED", "awaiting user go", or "feel unverified" — i.e.
someone consciously stopped short:

| Item | Note |
|---|---|
| **Headshot gore chain** (bug-1142) | Sandbox-verified 10/10 on m1l1+m3l2 and 20/20 kills; **play rollout staged** |
| **13-bit `frameInfo` anim-index widening** | Open task **#16** to verify — may or may not fix bug-1213 |
| **`coop_unsponge`** bullet-sponge sweep (bug-1212) | Landed in the last hours of the mined window |
| **Officer heal budget** `coop_officerMaxHeals` (bug-1215) | Same |
| **gl2 frozen-clock fix** (bug-1147) | Author's own note: *"not eyeball-verified — needs a menu with an animated shader"* |
| **gl2 AO and foliage fixes** | |
| **Tank MG gunner slot** | Prototype; needs m5l2a/b tuning for seat position, weapon, exposure |
| **AI combat "feel"** (`coop_aiRetargetMs` etc.) | Verified *firing*; the felt effect needs a listen-server playtest — the bot's fixed ~350u anchor sits in the vanilla mid-band |
| **Stale-objective wedge self-heal** | Untested live |
| **All four gore tiers** | Built + deployed, untested in-game |
| **NAT hole-punch phase 1** | Signaling verified locally; **no real-world friend test** (blocked on a VM). Engine commit records an unresolved dedicated-server crash "under investigation" with no follow-up. |
| **Jeep passenger seating** | Untested multi-player |
| **XP system phase 1** | Built 2026-07-07, untested |
| **Weapon + cosmetic unlocks** | Built 2026-07-16, untested |
| **Armory carry-over volleys** | rcon-verified at the wire level; untested live |

---

<a name="planned"></a>
## Planned, not built

| Item | State | Anchor |
|---|---|---|
| **Coop test menu** — 94 tests across 10 subsystems, each with catches/drive/verify/evidence/risk | **The largest designed-but-unexecuted work in the project.** Several named probes exist, so parts may be built. **No run log or results file found.** Either schedule it or explicitly retire it. | `_research/coop_test_menu.md` (132 KB) |
| **Bipod / supported aim** | Verdict: BUILD a weapon-stance supported aim (~250 LOC, game.dll + pk3); REJECT the turret-swap approach. Needs no new usercmd bit, no new PMF, no new stat. | `bipod_design.md` |
| **Limb dismemberment** | ⚠️ Read bug-861 and bug-892 first — the phase-0 precursor shipped and was pulled the same week. | `_research/limb_dismemberment_plan.md` |
| **Cover-peek physical step-out** | User verdict on peek v1: *"VERY janky - you dont actually pop out from the door opening."* Root cause understood: peek v1 only releases the torso and swings the camera; **the BODY never physically steps toward the corner**, so the muzzle stays behind the wall edge. Design queued: slide origin ~24–32u toward the detected open side (traced, collision-safe), slide back on release, keep velocity zero. | bug-311 |
| **Jeep .30cal manning pose** | Measure-first, explicitly not to be guessed. | bug-309 |
| **Blender sprint carry-pose** | Pipeline 100% working; **the user paused mid-edit** at arm-bone selection. | `blender_sprint_edit.md` |
| **Installer** | Built (Inno Setup 6, git-tracked). **DO NOT EXECUTE until explicitly asked.** | `installer/hzm_coop.iss` |
| **gl1 post-FX → gl2 ports** | 7 remaining; bloom is the template. | see [gl2](#gl2) |
| **Shadow mapping Phase B/C** | Not started. Phase A decal shadows shipped and user-approved. | `shadows_status.md` |
| **NAT phases 2+** | Phase 1 committed and locally verified. | `nat_holepunch_plan.md` |
| **Weapon-weight Phase 2** | Movement drag + rotational muzzle swing. | `weapon_weight_research.md` |
| **m3l1b FLAK objective v2** | Gun crews, back-field defenders, plant animation. | `m3l1b_cut_flak88_objective.md` |
| **Deployables skill tree** | **REJECTED by the user** — building their own model. Doc kept, marked superseded. | `skilltree_plan.md` |

---

<a name="discrepancies"></a>
## Record-vs-code discrepancies

Moved to [archive/open-record-vs-code.md](archive/open-record-vs-code.md) - they are documentation
corrections rather than open defects, and the code is authoritative in every case.

## Tooling lost

Mostly **resolved** - verified present 2026-08-07: `scratchpad/rcon.py` (rebuilt), and in-repo
`docs/tools/`: `depthscan2.py`, `scrlint.py`, `docgen.py`, `quotecheck.py`, `linecheck.py`,
`gen_service_record.py` (supersedes the old `gen_sr4.py`).

Still missing, all generators for already-shipped artifacts:

| Tool | Consequence |
|---|---|
| `gen_gore_skins.py` | Blood-mask skins un-regenerable (bug-817 reverted them to a specific coverage) |
| `gen_cosmetic_unlocks.py` | Cosmetic unlock tables un-regenerable |
| `split_options_persist.py` | Named in `coop_defaults.cfg`'s own line-2 header as that file's generator |
| `coopaudit/fourplayer_trig.ps1` + `coopaudit/REVERT_botinput.md` | Cannot re-run the 4P combat rig; no recorded revert path for an engine change still live in `player.cpp` |

**Rule:** anything under `%LOCALAPPDATA%\Temp\claude\...` is session-scoped and will vanish. A tool
worth citing belongs in `docs/tools/` or `scratchpad/` with a note here.

## Config

### Nine post-FX cvars are menu-wired AND force-reset by `autoexec.cfg` every launch
`OPEN` · *`autoexec.cfg` lines 661, 662, 663, 669, 670, 705, 713, 714, 729 vs `ui/coop_postfx.urc` + `ui/coop_postfx2.urc`*

`r_ppLowHealthStart`, `r_ppLowHealthAmount`, `r_ppLowHealthBeat`, `r_ppSharpen`, `r_ppSharpenAmount`,
`r_ppHeatAmount`, `r_ppRainDrops`, `r_ppRainAmount`, `r_ppMuzzleRadius`. Because `autoexec.cfg` execs
**after** the saved config, a player's menu change is wiped on every launch. **Fix: move these nine to
`coop_defaults.cfg`.** The other 4 `r_pp*` lines in `autoexec.cfg` (`MuzzleX`, `MuzzleY`,
`SunShaftDecay`, `SunShaftThreshold`) are correctly non-menu and can stay.

⭐ Good news: the two files are **strictly disjoint** — a `comm -12` on their `seta <name>` token sets
returns empty. There is zero double-seeding, so they never fight. The only defect is which **side** of
the saved config a cvar sits on. Current counts: `autoexec.cfg` has 179 `seta coop_*` and 13
`seta r_pp*`.

### 144 `coop_*` cvars are seeded nowhere
`OPEN` · For those, `getcvar` returns `""` on a clean profile and a script fallback branch silently
decides behaviour. **Documenting such a cvar as "default N" describes a branch, not a default.** The
consequential ones are in [Never ran](#never-ran).

### The bug-595 0-byte `omconfig.cfg` decoy is still on disk
`OPEN` · *`%APPDATA%\openmohaa\maintt\omconfig.cfg` — 0 bytes, 2026-07-04 10:37* — the lesson was
recorded but **the artefact was never removed**, so the identical session-loss is still available to
any future debugging pass. **Deleting one 0-byte file closes a documented multi-hour trap.** The same
directory also holds 15 `boot_<map>.cfg` harness files and a 2026-07-05 `whatsnew_pending.cfg`.

### `build.ps1`'s `_research` exclusion is uncommitted
`OPEN` · *`git diff build.ps1` — one line, `$excludeTop = @("_notes")` → `@("_notes", "_research")`*
The only modification in the workspace repo's working tree, and **one `git checkout` from being
lost**. Until it, releases up to and including v1.1.55 packed the mod's `_research` tree into the
shipped code pak. Corroborated: the released pak is **272,839 B larger** than the post-fix rebuild,
which is the right order of magnitude. **Commit it.**

---

<a name="cheapest"></a>
## Cheapest wins, roughly ordered

Effort/impact ranking was the audit's own acknowledged gap; this is an inference from signature, not a
measurement.

1. **Delete the 0-byte `omconfig.cfg` decoy.** One file, closes a documented multi-hour trap.
2. **Commit `build.ps1`'s one-line `_research` exclusion.** One commit, stops shipping design docs.
3. **Deploy the current `openmohaa.exe` + `game.dll`.** A copy. Resolves bug-1219 and the protocol
   mismatch. Back up first.
4. **Fix `hzm_cvars.txt:11`** `coop_lmsLifes` → `coop_lmsLives`. One character class, ships to players.
5. **Fix the three stale in-code comments** (`main.scr:134` Director default, `q_shared.h:1680`
   bug-866→892, `blueprint.scr:5-7` INERT header). Each will otherwise mislead a future session.
6. **bug-1218 m3l2 label.** Add the label or drop the `setthread`. Exact site known.
7. **bug-1027 e3l4 `outro.scr`.** Signature matches T1 exactly; a `developer 1` boot should name the
   line. Restores the BT campaign ending.
8. **Decide the four `SHIPPED-CODE-DISABLED` gates.** Either seed defaults or document as opt-in.
   Nothing to build — the code exists.
9. ~~Extract `global/vehicle_warning.scr`~~ — **DONE 2026-08-06** as bug-1473, fixed at the caller
   instead (`gags/t3l1_enemyspawn.scr`); removed all 12,690 casts, not just the estimated 4,270.
10. **Restore `r_globalFogDebug` to `CVAR_CHEAT`.** One flag.
11. **Promote `_research/regression/` out of `_research`.** Protects the only automated verification.
12. **Take one fresh look at the m3l3 courtyard.** The fix exists and was never evaluated.

## GL2 RENDERER: styled-lightmap surfaces pulse red (was: e2l1 rails) - TOP GL2 VISUAL DEFECT
CONFIRMED by user bisect 2026-08-04: GL1 clean, GL2 blinks. Affects any surface with a styled
lightmap: e2l1 bridge rails (both, uniformly), e2l2 panels near the radio tower + scattered
panels. Script setlightstyle changes have NO effect on it (flattening all 5 styles to constant
ramps changed nothing) -> rend2 is not sampling the style ramp; it produces its own red
oscillation for styled lightmap slots. Fix lives in renderergl2 lightmap/style handling
(tr_shade/tr_bsp: how MAXLIGHTMAPS style slots are merged). Supersedes an earlier, narrower
"e2l1 rails only, source unidentified" writeup - the styled-lightmap mechanism above is the
generalized, current answer; the per-surface elimination process that led to it is not repeated
here.

## Deploy infrastructure: phantom file locks + a mystery .pk3 renamer (2026-08-04)
Recurring transient locks on G:\mohaa-gl2\maintt pk3s (copies fail "in use", hashes verify
fine after). Worse: at 13:00 the GOG maintt pk3s were found renamed to .pk3.stale by an
unidentified actor mid-deploy (my rename-fallback only touched gl2; something else did GOG).
Recovered from APPDATA copies, all hashes verified. Suspects: AV/indexer, or a leaked
PowerShell child from the collided-watcher era. If it recurs, audit with Sysinternals handle.exe
before any deploy.

## GL2: distant objects pop out of / into fog instead of fading (user 2026-08-04, LOW priority)
User (e2l2, night profile dist=1000 bias=450): "distant objects still pop out when clearly the
fog should cover them". Explicitly deferred by the user - do NOT start a broad investigation
without being asked.

Leading hypothesis, cheap to test when we do pick it up: this is the **model LOD/impostor swap
distance**, not the fog maths. gl2 was already measured swapping the oak to its flat impostor at
~900u where gl1 does it at ~1352u. With a 1000u farplane, fog at 900u is only ~78% opaque - not
enough to hide a swap - so the LOD change reads as a pop. Predictions that would confirm it:
  - the pop distance tracks the MODEL, not the fog distance (raise farplane, pop stays at ~900)
  - `r_uselod 0` (already set in PLAY-GL2.bat) does not remove it -> it is the impostor path,
    not the LOD-level path
  - gl1 shows the same scene without popping at the same fog values
Second candidate if that is disproved: forward global fog not reaching full opacity at the cull
plane for TIKI surfaces, so `farplane_cull` removes geometry that is still partly visible.
Related family: the confirmed GL2 styled-lightmap defect (bug-1331).

## Holdout mode ON HOLD (2026-08-05)
User parked the gamemode to focus on trilogy-wide coop. Untested when parked: officer finale,
death->spectate + wave-end respawn + wipe->missionfailed + 30s cooldown, call radio (cat 44),
textured ladder rails + lattice ghost, native-light torture test, S93 BAR look. The 24-stop
candidate map tour stays deployed (y_hzm_maptour.pk3 + maptour.cfg) - quarantined and inert
unless exec'd; round-2 verdicts (stops 15-24) never given. See memory holdout_gamemode.md.

## Coop spawn-point gaps (re-measured 2026-08-07)

The 2026-08-05 audit here claimed **20 maps author no coop spawn sets** and listed m3l1b, m5l2a,
m6l1a, e3l1 and others. A fresh scan of `coop_mod/spawnlocations.scr` contradicts it: **44 of 58 base
map labels carry start coords**, and 26 maps have `_updateN` checkpoints on top. Treat the old figure
as retired.

Genuinely without start coords (14), and only three of those are real gaps:

| Label | Status |
|---|---|
| `m2l2b` | **REAL GAP.** No start coords; first coverage is `m2l2b_update1` at a mid-map trigger, so map-load to that trigger is uncovered. Needs one point. |
| `t1l1 t1l2 t1l3 t2l1 t2l3 t2l4 t3l1 t3l2` | Labels exist but are empty, so players fall back to the engine default. The 07-22 live-boot audit verified all boot coop-ready and spawn fine - **polish, not a hole.** One start point each. |
| `m1l1`, `t2l2`, `m6l3a` | Intentionally empty - players are glued to a truck / halftrack / train at spawn, so ground points do not apply. |
| `e1l3_finalEscape`, `e1l3_lockPicking` | Not maps - sequence sub-labels. |

`m3l1b` was the one map with **zero** coverage end to end; closed 2026-08-07 (start spawns +
`m3l1b_update1` on the map's own `level.clear_bunker >= 6` gate).

**Capture note:** `viewpos` prints `cg.refdef.vieworg` - the EYE. Spawn origins are feet, so subtract
`DEFAULT_VIEWHEIGHT` (**82**) from every captured z, or actors spawn head-height in the air and clip.
Its yaw also accumulates past a full turn (-422, 667), so normalise into 0..360. Build mode's `P`
marker uses `player.origin` and needs neither correction.

## Sweep-blocking maps (2026-08-06) - need dedicated sessions
Two maps stopped the trilogy coverage sweep dead and were skipped so the other ~40 could be measured:
- **m2l2a** - multiple independent defects. Both its raw waittills killed the main thread so NO player
  could spawn (bug-1458, fixed); it then threw `Cannot cast 'array' to listener` at line 78 -
  `$player.has_disguise = 1` inside a `gametype == 0` branch that is somehow entered in coop, where
  `$player` is an array. Needs a proper pass.
- **m3l3** - restart loop: reloaded 12 times in one run. The retail missioncomplete door (bug-1463)
  and the force-list transition trigger (bug-1464) were both fixed and it STILL loops, so a third
  transition path exists on this map. Investigate with covtrace on and the force pass disabled.

### e3l4 AI spawner threads die on AISpawnPoint/PathNode (bug-1471, OPEN)
`global/ai.scr:1037` does `self waittill trigger`, but on e3l4 that thread is started on
AISpawnPoint (x5) and PathNode (x1) entities, which cannot be waited on that way - the throw kills
the spawner thread and its AI set never spawns. Confined to e3l4 across the entire trilogy sweep,
so it is that map's spawner wiring (likely a targetname collision), not a global defect. Fix the
collision at source rather than adding a blind skip, which would hide the wiring error.

### Unwired challenges: 25 still have no producer (bugs 1596-1598, OPEN)
`chal_def` declares them, nothing bumps their stat, and `chal_bump` early-exits when
`level.coop_chal_statN[stat]` is NIL - a **no-op, not an error**, so they render in the Service
Record and can never be completed. Shipped this way in v1.2.1 (commit 7410b61). 22 were wired on
2026-08-08; the per-entry anchor, feasibility verdict and cut list for the rest live in
[proposals/orphan_challenge_triage.md](proposals/orphan_challenge_triage.md).

**Check with a whole-tree scan.** The first checker globbed `maps/*.scr`, which does not match
`maps/<map>/*.scr`, so three already-wired challenges were miscounted as dead and the original
figure of 49 was inflated. Walk the tree.
