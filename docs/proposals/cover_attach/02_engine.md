# Cover Attach — Research 2: Engine Capabilities

Read-only survey of `openmohaa-hzm/code` for a snap-to-cover attach ("walk up, press button
while crouched, attach to cover"). Line numbers are from the working tree as of 2026-08-09.

**Headline finding: the engine already ships a cover subsystem** — `Player::TickCoopCover`
(fgame/player.cpp:13452–13730, ticked every frame from `ClientThink` at player.cpp:5258) with
script request/read-back events, statemap conditions, a pm_flag, and cgame camera hooks. The
attach feature is an *extension of an existing, working spine*, not a from-scratch build.
Standing back-to-wall cover was **deliberately disabled** (hard `if (false)` guard,
player.cpp:13497–13501) after crash history: its entry view-snap + peek `setOrigin()` step-out
could shove the player into geometry. Only crouched LOW cover is live. Any snap-to-position
work must respect that lesson (see §b and §f).

---

## (a) Reading held keys / USE presses engine-side

**Server-held button state.** `Player::ClientThink` copies the client's usercmd each frame:
`buttons = current_ucmd->buttons` (player.cpp:5307); press *edges* are computed one line
earlier: `new_buttons = current_ucmd->buttons & ~buttons` (player.cpp:5299). Engine code
already reacts to USE edges directly (`new_buttons & BUTTON_USE`, player.cpp:5344).
`BUTTON_USE = 1 << 3` (qcommon/q_shared.h:1937,1952); `BUTTON_COOPADS` is the ADS-rework
bit 13 (q_shared.h:1945,1957).

**`useheld` — the getter the pickups poll.** `EV_GetUseHeld` is an `EV_GETTER` named
`"useheld"` (player.cpp:1279–1288), implemented as
`ev->AddInteger((buttons & BUTTON_USE) ? true : false)` in `Player::EventGetUseHeld`
(player.cpp:12452–12455), registered at player.cpp:2076. Script polls it with property syntax
(`local.player.useheld`) — live consumers: coop_mod/ammobox.scr:190, dbno.scr:607/862,
collectible.scr:194, cannonThink.scr:58, global/DistanceUse.scr:46. Siblings: `fireheld`,
`primaryfireheld`, `secondaryfireheld`, `coop_adsheld` (player.cpp:12457–12475).

**Lobby usercmd input bridge** (per-player, no client binds — the precedent for reading held
keys engine-side and publishing them to script):
- State lives on Player (player.h:403–417). Enabled per player by the script event
  `coop_lobbyinput` → `Player::CoopLobbyInput` (player.cpp:13734–13740), which also clears
  edge state so enabling mid-hold can't fire a phantom tap.
- `TickCoopLobbyInput` (player.cpp:13745–13770), ticked from ClientThink (player.cpp:5264):
  reads `last_ucmd.rightmove` with a ±20 deadzone and `last_ucmd.buttons & BUTTON_USE`,
  edge-detects both, and publishes via `Vars()->SetVariable("coop_lobbyInput", 31/32/33)` —
  script sees `self.coop_lobbyInput`.
- Mouse variant `TickCoopLobbyCursor` (player.cpp:13783–13830): wrap-safe short deltas of
  `last_ucmd.angles[YAW/PITCH]` → virtual 640×480 cursor vars + click edge.

**Delivery patterns available to the attach button.** (1) The shipped route: bindable-command
name-append bus 26 → `coop_mod/takecover.scr::coop_cover_toggle` → player event
`coop_setcover 1|0` (takecover.scr:1–47). (2) A pure engine route: watch
`new_buttons & BUTTON_USE` (or a `TickCoopLobbyInput`-style per-frame check gated on a mode
flag). (3) Script polling `useheld` in a proximity loop (the ammobox/DistanceUse shape).

## (b) Locking / constraining movement; anchored states

**Current cover semantics — movement is a *cancel*, not locked.** TickCoopCover hard-cancels
on `deadflag || IsSpectator() || m_pVehicle || m_pTurret || m_pLadder || level.playerfrozen ||
m_bFrozen || (flags & FL_IMMOBILE) || last_ucmd.forwardmove || last_ucmd.rightmove ||
last_ucmd.upmove > 0` (player.cpp:13467–13478). An attach that *holds* the player needs one of
the constraint mechanisms below instead of (or layered under) that cancel list.

**Mount = the full attach precedent (MG42).**
- Entry: `TurretGun::P_TurretUsed` (fgame/weapturret.cpp:1702–1738) — gated on facing
  (`AngleSubtract(viewYaw, angles[1]) <= m_fMaxUseAngle`, :1726) and DBNO
  (`player->IsCoopDbno()`, :1720) — then `P_TurretBeginUsed` (:1591–1629) → 
  `Player::EnterTurret` (player.cpp:8901–8919): sets `FL_PARTIAL_IMMOBILE`,
  `velocity = vec_zero`, `m_pTurret`, `setMoveType(MOVETYPE_TURRET)`, `SafeHolster(true)`.
- **Per-frame position pin** — the borrowable core: `TurretGun::P_ThinkActive`
  (weapturret.cpp:968–991) computes the desired body position
  (`vPos = origin - vForward * m_fUserDistance; vPos[2] -= 16`), drops it to ground with a
  **full player-bbox** trace, re-traces the final spot for solidity, and only then
  `owner->setOrigin(vPos)`. Compute-pose → bbox-trace → verify → setOrigin, every frame.
- Move path while mounted: `Player::TurretMove` (player.cpp:4878–4912) sets
  `PMF_TURRET | PMF_NO_PREDICTION`.
- Exit: `P_TurretEndUsed` (weapturret.cpp:1665–1695) → `Player::ExitTurret`
  (player.cpp:8936–8951) clears `FL_PARTIAL_IMMOBILE`, restores `MOVETYPE_WALK`, zeroes
  `new_buttons`/`server_new_buttons` so the mount press can't leak.

**Movement kill switches (all proven in-tree):**
- `FL_IMMOBILE` / `FL_PARTIAL_IMMOBILE` (g_local.h:62) → `PMF_NO_MOVE | PMF_NO_PREDICTION`
  (player.cpp:4485–4488). Pmove returns before processing movement on
  `PMF_NO_MOVE`/`PMF_FROZEN` (bg_pmove.cpp:1431, 1255). Used by the lobby mannequin poses
  (player.cpp:9041 etc.).
- Vehicle-seat glue: `m_pGlueMaster` → `PMF_NO_MOVE | PMF_NO_PREDICTION`
  (player.cpp:4490–4512).
- Freezes: script `freezeplayer` (scriptthread.cpp:407–414 → `level.playerfrozen`) and
  per-player `freezecontrols` (`EV_Player_FreezeControls` player.cpp:1558,
  `Player::FreezeControls` :14411–14414 → `m_bFrozen`) → `PMF_FROZEN` (player.cpp:4481–4483).
- Speed scaling (softer option): `moveSpeedScale` setter/getter (player.cpp:1683–1700) and
  `setspeed speed index` (player.cpp:1758–1766) fill `speed_multiplier[MAX_SPEED_MULTIPLIERS]`
  (player.h:441), applied multiplicatively to `client->ps.speed` (player.cpp:4649). Setting it
  to 0 immobilizes without touching pm_flags.
- Velocity writes: script-visible `velocity` setter (`EV_SetVelocity`, entity.cpp:1270–1278);
  engine zeroes it on turret entry.

**Stance forcing — yes, the engine can hold a player crouched.** `PMF_DUCKED` is *derived
from the bbox*, not from input: `maxs.z == 54 || 60` ⇒ `PMF_DUCKED`
(player.cpp:4514–4532). Proven recipe: the glue-duckable rider drives
`maxs.z = 54; viewheight = CROUCH_VIEWHEIGHT` directly from the crouch axis while
`PMF_NO_MOVE` blocks pmove's own stance machine (player.cpp:4498–4511). Alternatives:
`MOVECONTROL_CROUCH` movecontrol forces `PMF_NO_PREDICTION | PMF_DUCKED | PMF_VIEW_PRONE`
(player.cpp:4540–4542); and the legs statemap holds the visual crouch — `COVER_LOW`
(coop_mod/player_legs.st:1961–2043) is entered on the engine condition and exits via
`!COOP_COVER_LOW`.

**Engine ↔ script state contract already in place:** request via `coop_setcover`
(`EventCoopSetCover` player.cpp:12619–12631 — validates immediately, self-clears if nothing
coverable); read back via `coop_incover` getter 0/1/2/3 (player.cpp:12634–12649); plus a
change-gated entity var `coop_incover` for polling-free consumers ([235],
player.cpp:13717–13726). DBNO mirror (`coop_setdbno`, player.cpp:12609–12617) is the template
for adding more per-player published state.

## (c) View constraints (turret clamp recipe)

`TurretGun::P_UserAim` (weapturret.cpp:1532–1555): the server *owns* the view while mounted —
it accumulates usercmd angle **deltas** into `m_vUserViewAng` via `AngleSubtract` per axis.
`P_ThinkActive` then clamps: pitch to `[m_fPitchUpCap, m_fPitchDownCap]`
(weapturret.cpp:818–822), yaw to `±m_fMaxYawOffset` around `m_fStartYaw` with
`AngleSubtract` + `Q_clamp_float` (:828–831), and pushes the result with
`owner->SetViewAngles(m_vUserViewAng)` (:834). Camera side: a bound `Camera` entity at the gun
plus `CF_CAMERA_ANGLES_TURRETMODE` (:957) and per-gun `m_vViewOffset` (:940–955). This
delta-accumulate → clamp → SetViewAngles loop is directly borrowable for a cover yaw window.

Cover today deliberately does **not** clamp: it anchors the wall OUT normal
(`m_vCoopCoverNormal`) so the sustain check is view-independent and the mouse can free-look
(player.cpp:13492–13496 comment); on peek release it re-snaps yaw to the pose facing with
`SetViewAngles(va[YAW] = vectoyaw(normal))` (player.cpp:13637–13648). Client-side, the only
pitch limit in cover is the engine's own ±85 — bug-327 history says do NOT layer a second
orbit/clamp on top (cg_view.c:2485–2488 comment).

## (d) Traces: wall normal + distance

**Engine-side (what cover and markwall use)** — `G_Trace` returns a full `trace_t` incl.
`plane.normal`, `fraction`, `startsolid`, `surfaceFlags`, `shaderNum`, `entityNum`.
- Cover probes (player.cpp:13579–13609): chest ray at +36u forward `coop_coverLowDist` (48)
  must HIT a near-vertical plane (`|normal.z| < 0.7` and `DotProduct(normal, probe) < -0.5`);
  head ray at `coop_coverLowHeight` (72) must be CLEAR. Tunables incl. `coop_coverWallDist`
  (40) and `coop_coverGrace` (0.5 s) at player.cpp:13481–13488. Entry anchors
  `m_vCoopCoverNormal` + `m_vCoopCoverBaseOrg` (:13603–13606). Accessors already exist for
  other systems: `GetCoopCoverNormal()`, `GetCoopCoverSide()`, `IsCoopCoverLow()`
  (player.h:1030–1038).
- `markwall` (`Player::EventCoopMarkWall`, player.cpp:12553–12604): eye +
  `AngleVectors(v_angle)` × 512u, `MASK_PLAYERSOLID & ~CONTENTS_BODY`; classifies
  clip/fence/solidnodraw/entity by re-tracing with content bits removed; `gi.PointBrushnum`
  for the brush id and `gi.GetShader` for the shader name. Proof that deep wall interrogation
  is available as a bindable player event.

**Script-side (.scr)** — three thread commands (scriptthread.cpp):
- `trace start end [pass_entities mins maxs]` → endpos vector only (:877–885).
- `sighttrace …` → 0/1 (:886–894).
- `traced start end [pass_entities mins maxs mask]` → array with `allSolid, startSolid,
  fraction, endpos, surfaceFlags, shaderNum, contents, entityNum, location, entity`
  (:1985–1992; impl :7273–7362).

**Gap: no script trace returns `plane.normal`.** A script could approximate a normal from
offset traces, but there is no need — the engine computes and anchors the real normal in
`m_vCoopCoverNormal`. Attach logic wanting the normal should live engine-side (or a
`coop_covernormal` getter could be added on the `coop_incover` pattern).

## (e) 3P camera hooks that must know "in cover"

- **`PMF_COOP_COVER`** — pm_flags bit 13 (bg_public.h:274), set server-side while the pose is
  valid (player.cpp:8424–8430). Client consumers: forces third person (cg_view.c:2478 — but
  native zoom re-forces 1P *after* it, cg_view.c:2479–2484 [237]); own-model draw in 3P
  (cg_modelanim.c:1287); HUD-fade exemption (cg_drawtools.cpp:2059). A new attach state should
  keep setting this flag (or extend it) — every camera decision keys off it.
- **View lift**: `SendCoopCoverView` (player.cpp:13277–13285) mirrors `coop_coverView` 0/1 to
  the owning client via **change-only** stufftext (per-frame would flood the reliable buffer)
  and **must be called on every TickCoopCover exit path** — missing it on early returns was a
  real stale-camera bug. Client: `CG_CoopCoverViewLift` (cg_view.c:139–148, lift =
  `coop_coverViewRaise` 16u) applied before the chase camera derives in
  `CG_OffsetThirdPersonView` (cg_view.c:171). 3P-only by design — applying it in 1P left a
  stale lift.
- **Peek = real ADS**: `m_bCoopCoverPeek` rides `BUTTON_COOPADS` (player.cpp:13635–13636);
  `SendCoopCoverView` sends 0 while peeking (:13279) so the lift drops during aimed peek; the
  cgame shoulder-ADS camera engages on the same button, with `CG_AdsForceFirstPerson`
  (cg_view.c:2455) as the single 1P/3P decider.
- **`u_view3p` mirror**: the client reports its final view mode to the server
  (cg_view.c:2489–2495 → `m_bCoopView3p`, player.h:372); the turret code uses it to unfilter
  the world gun for 3P gunners (weapturret.cpp:807–815). Any attach that changes model/weapon
  visibility must respect this round trip.

## (f) Implications for the "auto attach" ask

Everything the ask needs exists as proven parts: input (bus 26 bind already toggles cover;
`useheld`/`new_buttons & BUTTON_USE` both readable), detection (TickCoopCover's traces +
anchored normal + `coop_incover` feedback), anchoring (turret's per-frame
compute→bbox-trace→`setOrigin` pin; PMF_NO_MOVE/FL_IMMOBILE family for hard locks;
`speed_multiplier` for soft locks), stance hold (maxs.z-driven PMF_DUCKED, glue-duckable
recipe), view (turret delta-clamp recipe if a yaw window is wanted), and camera (PMF_COOP_COVER
+ SendCoopCoverView already drive auto-3P). Two hard-won cautions bind any design: (1) the
wall-cover removal — never `setOrigin` a snap from point traces; always trace with the full
player bbox like the peek slide does (player.cpp:13674–13680: `G_Trace(origin, mins, maxs,
vWant, …)` and refuse on `startsolid`); (2) all client mirroring must be change-only and fire
on every state-machine exit path.
