# Cover Attach — Implementation Plan

Design for the user's ask: *"an auto attach to cover system using our existing cover
functionality where you walk up and press the button to attach to cover while crouched."*

Inputs: `docs/proposals/cover_attach/01_existing_cover.md` (existing system, exhaustive) and
`02_engine.md` (engine capabilities). All paths relative to `C:\mohaa-coop-dev\`.
Mod = `hzm-mohaa-coop-mod/`, engine = `openmohaa-hzm/`.

---

## 1. Feasibility verdict

**Needs engine — but only `game.dll`, and only ~100-150 lines inside a system that already
exists.** This is an *extension of `Player::TickCoopCover`* (fgame/player.cpp:13452-13730),
not a new feature. Script-only is ruled out on four independent grounds:

1. **No plane normal in script traces.** `traced` returns fraction/endpos/flags but not
   `plane.normal` (02_engine §d). The snap direction *is* the normal. The engine already
   computes and anchors it (`m_vCoopCoverNormal`, player.cpp:13603-13606).
2. **The cancel list lives engine-side.** Any `forwardmove/rightmove` in `last_ucmd`
   hard-cancels the request (player.cpp:13467-13478) before a script could react. Changing
   "movement = cancel" into "movement = ignored while attached" can only happen there.
3. **Safe snapping requires full-bbox traces + `startsolid` refusal** — the exact discipline
   whose absence killed WALL cover (`if (false)`, player.cpp:13497-13501). Script `setorigin`
   has neither.
4. **Prediction.** A server-side origin pin without `PMF_NO_PREDICTION` rubber-bands on
   clients; only the engine can set that flag.

**What the MG42-mount precedent buys us (02_engine §b) — essentially the whole hard part:**

| Mount mechanism | Reused for attach as |
|---|---|
| `P_ThinkActive` per-frame pin: compute pose → **full player-bbox** `G_Trace` → verify spot → `setOrigin` (weapturret.cpp:968-991) | The attach snap AND the v2 slide-along-wall step. Copy the shape verbatim. |
| Entry: `velocity = vec_zero`, state flag, prediction off (`Player::EnterTurret`, player.cpp:8901-8919; `PMF_TURRET \| PMF_NO_PREDICTION` in `TurretMove`) | Attach entry: zero velocity, `m_bCoopCoverAttached = true`, `PMF_NO_PREDICTION` while attached |
| Exit zeroes `new_buttons`/`server_new_buttons` so the mount press can't leak (weapturret.cpp:1665-1695) | Detach: same hygiene so the release press doesn't re-trigger anything |
| Facing gate `m_fMaxUseAngle` (weapturret.cpp:1726) | Already stricter in cover: `dot(normal, probe) < -0.5` |

Crucially, **no exe/cgame changes**: we keep `PMF_COOP_COVER` (already in the snapshot,
bg_public.h:274), keep the statemap conditions, keep `SendCoopCoverView`. All camera/HUD/3P
behavior is inherited unchanged. Single-DLL ship = the cheapest engine deploy class this
project has.

## 2. Attach state machine — and who owns it

**Owner: the engine, inside `TickCoopCover`.** This is the existing architecture statement
(player.h:377-384: *"The engine — not the statemap or script — is the single authority"*) and
we keep it. The script stays a thin request/feedback shim; the statemaps stay pure mirrors of
engine conditionals. One new member: `m_bCoopCoverAttached` (plus the snap-target vector).

```
                 bus-26 press (takecover.scr -> coop_setcover 1)
                                   |
  [FREE] ---------------------> [DETECT]      (existing: probes run inside the event;
                                   |           no pose -> request self-clears, iprint "No cover here")
                          pose valid (LOW)
                                   |
                              [ATTACHING]     (NEW: ease origin toward wall, full-bbox swept,
                                   |           <= ~3 frames; blocked mid-slide -> stop where we are,
                                   |           still attached - partial snap is fine)
                                   v
                               [HELD] <-------------------------+
                       (anchored to m_vCoopCoverNormal /        |
                        snap point; fwd/strafe input IGNORED,   |
                        not cancelling; statemap COVER_LOW      |
                        crouch pose as today)                   |
                          |            |                        |
                 BUTTON_COOPADS   BUTTON_ATTACKLEFT             |
                          v            v                        |
                       [PEEK]      [BLINDFIRE]  --release-------+
                 (existing stand-up  (existing COVER_LOW_FIRE,
                  COVER_LOW_PEEK,     muzzle raise, spread,
                  aimed fire)         semi-auto one-click latch)
                          |
                          +--> DETACH on ANY of:
                               - re-press bind (toggle-off path, takecover.scr:27-32)
                               - jump (upmove > 0)
                               - backpedal (forwardmove < -threshold, ~2 consecutive frames)
                               - geometry invalid past coop_coverGrace (existing 0.5s)
                               - death / DBNO / turret / vehicle / ladder / frozen (existing list)
                               -> clear all state, restore prediction, zero new_buttons,
                                  SendCoopCoverView() [MANDATORY on every exit path]
```

DETECT, PEEK, BLINDFIRE, and the grace-drop already exist and are untouched. The new work is
ATTACHING, the HELD input-filter, and the backpedal detach edge.

## 3. Exact detection rule

**Reuse the shipped LOW probes byte-for-byte** (player.cpp:13579-13610) — they are tuned,
playtested, and already compose with sandbags (54u collision, bug-536) and buildmode props
(explicit SOLID_BBOX clips, buildmode_catalog.scr:2008):

1. Probe dir = flat view yaw (`yaw_forward`); while held, the anchored `-m_vCoopCoverNormal`.
2. **Chest trace**: `origin + (0,0,36)` forward `coop_coverLowDist` (48u) must HIT a
   mostly-vertical solid facing the player (`|normal.z| < 0.7`, `dot(normal, probe) < -0.5`).
3. **Head trace**: `origin + (0,0,coop_coverLowHeight)` (72u), same line, must be CLEAR —
   this is what makes it *low* cover you can fire over.

**Crouch requirement: default OFF, cvar-gated.** The ask says "while crouched", but the
shipped system deliberately does not check stance — the statemap `modheight "duck"` snap-crouch
on engage (player.cpp:13260-13261, COVER_LOW entrycommands) is strictly better UX and already
what players know. Add `coop_coverAttachNeedCrouch` (default 0): when 1, the attach (not the
plain pose) additionally requires the crouched bbox (`maxs.z == 54 || 60`, the `PMF_DUCKED`
derivation at player.cpp:4514-4532). Ship 0, let the user flip it live to compare feel.

**Snap target**: `hitpos + m_vCoopCoverNormal * (bbox_half_depth + coop_coverAttachGap)`,
dropped to the player's current z (no vertical snap — gravity/ground handles z). Max travel is
bounded by the probe itself (≤48u minus body depth ≈ ≤32u of slide).

**Surface classification**: none needed for v1. The probes' plane tests already reject floors,
ramps and glancing hits. If bad cover surfaces show up in playtest (ladders, fences), the
`markwall` differential re-trace recipe (player.cpp:12553-12604) is the ready-made classifier
to bolt in — reject `CONTENTS_FENCE`, accept clip/solid/entity.

## 4. Movement model while attached

**v1: LOCKED. v2: slide-along-wall.** Ship locked first — it proves the feel with ~30 lines;
the slide reuses the turret pin and is a clean increment.

- **Input filter, not pmove surgery**: in `ClientThink`, after the ucmd copy but before Pmove,
  when `m_bCoopCoverAttached`: zero `forwardmove` (unless negative past the detach threshold)
  and zero `rightmove` (v1). No `PMF_NO_MOVE`/`FL_IMMOBILE` — those also kill gravity/ground
  handling and drag in the mannequin semantics; we want a normal standing player whose stick
  input is simply not forwarded. Jump (`upmove > 0`) is left visible so the existing cancel
  fires. This is the smallest possible change to the shipped cancel-list: attached flips the
  meaning of fwd/strafe from "cancel" to "ignored", backpedal/jump keep meaning "release".
- **Backpedal detach**: `forwardmove < -50` for 2 consecutive frames (debounce so a stick
  flick doesn't eject). On detach the player just stands up out of the pose exactly as today
  (`!COOP_COVER_LOW` statemap exits fire same frame).
- **The snap itself (ATTACHING)**: per-frame step of `coop_coverAttachSpeed` (240 u/s ≈ 2-3
  frames for a full-depth snap) toward the target, each step a **full-bbox
  `G_Trace(origin, mins, maxs, want, ..., MASK_PLAYERSOLID)`**, move only to `trace.endpos`,
  **refuse on `startsolid`** — the peek-slide discipline (player.cpp:13674-13680) that the
  dead WALL code violated. If blocked (teammate, prop), stop early and stay attached where we
  are; the pose probes still validate from the anchored normal, so partial snap is harmless.
- **v2 slide**: while HELD, `rightmove` drives lateral motion along the wall tangent
  (`normal × up`), same compute → bbox-trace → verify → `setOrigin` loop as
  `P_ThinkActive` (weapturret.cpp:968-991), at ~60% crouch speed, and each frame the chest/head
  probes re-run at the new spot — sliding off the end of the crate hits the existing grace
  window and drops cleanly. Gate behind `coop_coverSlide` (default 0 until v1 feel is signed
  off).
- **Prediction**: set `PMF_NO_PREDICTION` while `m_bCoopCoverAttached` (the glue/turret
  precedent, player.cpp:4485-4512). Attached movement is server-authored; letting the client
  predict it guarantees rubber-banding on the snap and the v2 slide.
- **Face-wall turn**: unchanged and free — the pose anchors `m_vCoopCoverNormal` on engage and
  peek-release already re-snaps view yaw to the obstacle (player.cpp:13637-13648). Free-look
  in HELD stays exactly as shipped (bug-327 lesson: do not add a view clamp on top).

## 5. Per-file implementation steps (reusing takecover.scr, not replacing it)

Ordered; steps 1-4 are the v1 prototype.

1. **`openmohaa-hzm/code/fgame/player.h`** — add to the existing coop-cover member block
   (player.h:377-402): `bool m_bCoopCoverAttached; Vector m_vCoopCoverAttachTarget;` and an
   `IsCoopCoverAttached()` accessor next to `IsCoopCoverLow()` (player.h:1030-1038). Init in
   the same constructor region as `m_iCoopVarCoverLast` (player.cpp:2379).
2. **`openmohaa-hzm/code/fgame/player.cpp` — `TickCoopCover`**:
   - Register cvars beside the existing block (13481-13488): `coop_coverAttach` (1),
     `coop_coverAttachGap` (2), `coop_coverAttachSpeed` (240), `coop_coverAttachNeedCrouch`
     (0), `coop_coverSlide` (0), `coop_coverDetachBack` (50). All `CVAR_ARCHIVE`,
     engine-registered like the rest — nothing seeded in cfgs.
   - On LOW engage (the anchor site, 13603-13606): if `coop_coverAttach`, compute snap target
     from the chest-trace hitpos, zero velocity, set `m_bCoopCoverAttached`.
   - New ATTACHING/HELD block: swept-bbox step toward target; backpedal-debounce detach edge.
   - **Rework the cancel list** (13467-13478): when attached, remove `forwardmove/rightmove`
     from the hard-cancel set (they are filtered instead); keep every other cancel. When
     `coop_coverAttach 0`, behavior is bit-identical to today — the rollback switch.
   - Every new exit path calls the full clear: attached=false, prediction restored,
     `new_buttons`/`server_new_buttons` zeroed, `SendCoopCoverView()` (the stale-camera-lift
     lesson, 13272-13276).
3. **`player.cpp` — `ClientThink`**: the attached input filter (zero fwd/strafe in the ucmd
   before Pmove) and `PMF_NO_PREDICTION` while attached (join the existing pm_flag derivation
   around 4485-4512).
4. **`hzm-mohaa-coop-mod/coop_mod/takecover.scr`** — messages only, guards and flow untouched:
   line 40 no-cover hint stays; line 45 success becomes
   `"Attached to cover - hold FIRE to blind-fire, jump or step back to release"`; line 46 log
   becomes `^~^~^ TAKECOVER: engaged LOW (attached)` when... the script can't see attached vs
   plain — EITHER leave the log as-is (fine for v1) OR bump the `coop_incover` getter to
   return 4 for attached-low (additive, nothing tests `== 3`; xp.scr uses `>= 2` which still
   matches). Prefer the getter bump: one line in `EventGetCoopCover` (12634-12649), gives
   script and future features the distinction for free.
5. **Statemaps / anims: NO CHANGES.** `COOP_COVER_LOW` remains the condition; attached is
   invisible to `player_legs.st`/`player_Torso.st`. This dodges the entire .st crash class
   (ERR_DROP on parse, bug-382/313) and means no first-listen-launch statemap risk.
6. **cgame / exe: NO CHANGES.** `PMF_COOP_COVER` continues to drive auto-3P, camera lift,
   HUD-fade exemption. `game.dll`-only ship (manual deploy to GOG root per the lobby-build
   note; `build.ps1` handles the rest).
7. **v2 (post-feel-signoff)**: the slide block in `TickCoopCover` behind `coop_coverSlide`;
   optionally the `markwall` species filter if playtests find junk surfaces.
8. **Bookkeeping**: buglog entries for anything fixed en route; FEATURES.md cover section gets
   the attach note + cvars; OPEN.md entry until playtested. Do not touch `docs/generated/`.

**Explicitly rejected**: a `useheld`/BUTTON_USE trigger. Bus 26 is already bound, shipped, and
documented ("Coop: Take Cover"); USE near cover would collide with doors, ammoboxes, DBNO
revives and `DistanceUse` triggers (02_engine §a lists five live USE consumers). Re-press
detach also falls out of the existing toggle for free.

## 6. 4-player / network considerations

- **All state is per-Player members** — the shipped pattern; nothing global, nothing in
  `level.`, so 4 simultaneous attachers are independent by construction.
- **Prediction**: the one real network change. `PMF_NO_PREDICTION` while attached (proven by
  turret/glue). Without it the snap and v2 slide fight client prediction visibly at any ping.
- **Two players, one crate**: the swept-bbox step stops at a teammate's body
  (`MASK_PLAYERSOLID` includes bodies) — partial snap, both stay attached, no overlap, no
  shove. v2 slide stops the same way.
- **Replication cost: zero new traffic.** Pose still rides the existing `PMF_COOP_COVER`
  snapshot bit; `coop_coverView` stufftext stays change-only (the flood rule). No new
  stufftext, no new configstrings, no protocol constants — so no exe/cgame version-pairing
  hazard (the entity-pool saga class).
- **Late joiners / respawn**: pm_flags arrive in the first snapshot; attach state dies with
  the player via the existing `deadflag` cancel. DBNO cancels via the existing list.
- **Dedicated vs listen**: no client dependency in the new code; but per project rule the
  first LISTEN launch is still the real test (statemaps unchanged, so no ERR_DROP exposure).
- **Getter shadowing trap**: if step 4's getter bump is taken, do NOT also push an entity var
  named `coop_incover` with different values — the EV_GETTER shadows entity vars for property
  reads (the 08-07 xp.scr bug). Any new var gets a new name (`coop_attach_t` style).

## 7. Risks + cheapest prototype

**Risks, ranked:**

1. **The WALL-cover crash class** (server-authored origin writes shoving players into
   geometry). Mitigation is structural: every origin write goes through full-bbox
   `G_Trace` + `startsolid` refusal + move-to-endpos-only; snap is small (≤~32u) and
   horizontal; no z writes. This discipline is the plan's one inviolable rule.
2. **Prediction jank** on snap/slide. Mitigated by `PMF_NO_PREDICTION`; residual risk is the
   1-frame transition feeling sticky — tune `coop_coverAttachSpeed` live (CVAR_ARCHIVE).
3. **Cancel-list regression** for players who liked tap-cover-then-strafe-out. Mitigated:
   `coop_coverAttach 0` restores shipped behavior exactly; backpedal/jump remain instant
   exits, so escape-under-fire latency is one input.
4. **Moving platforms/elevators**: anchored normal + snap point go stale. Existing 0.5s
   geometry grace already drops the pose; accept for v1 (same limitation ships today).
5. **Feel risk** — "magnetized" can read as "grabbed". This is why v1 is a locked minimal
   build with detach on three separate reflexes (jump, back, re-press).

**Cheapest possible prototype (one engine edit, one script line, ~1 session):**

- Steps 1-3 of §5 with the ATTACHING step simplified to *max 1 bbox-swept move per frame,
  locked HELD, no slide, no getter bump, no crouch gate* — roughly: 2 members, 4 cvars,
  ~40 lines in `TickCoopCover`, ~10 in `ClientThink`.
- takecover.scr line 45 message tweak (deployed via `.\build.ps1`; game.dll to GOG root).
- **Feel test script** (listen server, m1l1 beach sandbags + a buildmode crate):
  1. stand 40u off sandbags, press bind → body slides flush, crouch pose, camera lift — no
     clipping, no pop;
  2. hold FIRE → blindfire over top (unchanged); hold ADS → stand-up peek (unchanged);
  3. tap S → released; tap SPACE from cover → released; re-press → released;
  4. press bind at 40u with a teammate already flush → partial snap, both covered;
  5. `coop_coverAttach 0` → today's behavior byte-for-byte.
- Success = step 1 "feels like Gears-lite, not glue"; then green-light v2 slide.
