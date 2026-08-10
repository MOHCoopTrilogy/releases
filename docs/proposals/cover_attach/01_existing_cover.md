# Cover-attach research 1: the existing TAKE COVER system, exhaustively

Research for the "walk up + press button while crouched -> attach to cover" feature.
All paths relative to `C:\mohaa-coop-dev\`. Mod = `hzm-mohaa-coop-mod/`, engine = `openmohaa-hzm/`.

**Headline**: the script file is a 47-line thin shim. ~95% of the cover system is ENGINE-side
(`Player::TickCoopCover`, fgame `game.dll`) plus statemap/anim data. Standing back-to-wall (WALL)
cover has been **hard-disabled** in the engine (`if (false)` guard) for being crash-prone; only
crouched LOW cover is live today. That means several subsystems (corner-side probe, peek step-out,
wall blindfire steering) are currently **dead code that still ships**.

---

## 1. The script shim: `coop_mod/takecover.scr`

Whole file = one label, `coop_cover_toggle local.player` (takecover.scr:17). Behavior:

- **Guards** (takecover.scr:19-24): refuses when player NULL, dead (`isAlive`), spectator
  (`.dmteam`), DBNO (`self.flags["coop_dbno_active"] == 1`), on a turret (`.turret != NULL`),
  or in a vehicle (`.vehicle != NULL`). Each prints a machine-parseable `^~^~^ TAKECOVER:` line.
- **Toggle-off** (takecover.scr:27-32): if `local.player.coop_incover > 0` it sends
  `local.player coop_setcover 0`, iprints "Cover released", ends.
- **Request** (takecover.scr:37): `local.player coop_setcover 1`. The engine validates
  IMMEDIATELY inside the event (see section 4), so the very next line can read back
  `local.player.coop_incover` for authoritative same-press feedback (takecover.scr:34-36).
- **Feedback** (takecover.scr:39-45): `coop_incover == 0` -> iprint "No cover here - face a low
  wall, sandbags or crates to crouch behind"; else "In cover - hold FIRE to blind-fire over the
  top". Comment at takecover.scr:44: *"wall (standing back-to-wall) cover was removed for being
  crash-prone; only LOW/crouch remains"*.
- **No monitor loop, no per-player script state**: header (takecover.scr:5-11) says the engine
  validates per frame and drops the pose itself, "so this thread never needs a monitor loop".
  The script keeps zero state of its own — everything lives in engine members (section 4) and
  the `coop_incover` getter.
- Header warning (takecover.scr:15): **`coop_mod/cover.scr` is the SANDBAG DEPLOYABLE, a
  different feature** (bus 9, `cover_place`, player.scr:567). Same warning in FEATURES.md:238/682.

`coop_incover` values (takecover.scr:7-8, engine getter section 4): `0` none, `1` requested but
no valid pose, `2` standing back-to-wall (unreachable today), `3` crouched low cover.

## 2. Bus wiring: how the button reaches the script

The **name-append bus** — the project's standard "client button -> server script" bridge
(vanilla MOHAA has no client->script command channel; the player's NAME is the wire).

1. **Bind published to players**: `ui/BIND.SCR:51` — `binditem "Coop: Take Cover" "append name ,c1x"`.
   Pressing the bound key appends the marker text ` ,c1` + data char `x` to the player's netname.
   (BIND.SCR is the Controls menu item list; every coop bindable does this, BIND.SCR:38-55.)
2. **Marker table**: `coop_mod/variables.scr::getNameAppendCommands` (variables.scr:132-182) maps
   bus index -> marker string. Index 26 = `" ,c1"`, comment "take cover toggle (data: x)"
   (variables.scr:160). Markers are 3-4 chars starting with `" ,"`; the trailing char(s) after the
   marker are the DATA payload (single `x` = "no data, just fire").
3. **Detection**: the per-player `manage` loop calls `manageNamechange` on netname change
   (player.scr:115, player.scr:311). `manageNamechange` (player.scr:354-444) iterates the whole
   marker table, and for each marker found in the netname extracts the data via `playerExtract`
   (player.scr:449+) into `self.flags["coop_extracted"+i]` (player.scr:379-391), then threads
   `playerNameCommand` (player.scr:403), then **cleans the name back** with
   `stufftext ("set name "+cleanName)` (player.scr:415-417) and waits (40-frame timeout with
   re-entry, player.scr:422-436). Names longer than 23 chars can't carry commands
   (player.scr:407-411).
4. **Dispatch**: `playerNameCommand` (player.scr:535-618) finds the first non-NIL extracted slot
   and switches on the index. Bus 26 -> `thread coop_mod/takecover.scr::coop_cover_toggle
   local.player` (player.scr:584). Data char is passed to handlers that want it (e.g. armory);
   takecover ignores it.

Full recipe context also in memory `bindable_coop_commands` and FEATURES.md:58 (indices in use).

## 3. Engine surface: events and members

Event definitions, `code/fgame/player.cpp`:

- `coop_setcover` (int active) — request/release, player.cpp:1349-1356. Handler
  `Player::EventCoopSetCover` player.cpp:12619-12631: sets `m_bCoopCoverRequested`, zeroes the
  grace timer, then calls `TickCoopCover()` **synchronously** so validation happens inside the
  event; if the request produced no pose it clears the request on the spot (player.cpp:12627-12630)
  — this is what makes the script's immediate read-back authoritative (player.cpp:12477-12480).
- `coop_incover` — **EV_GETTER** (property syntax only — see memory `dev_visibility_gotchas`:
  calling it any other way parse-kills the file), player.cpp:1357-1365. Handler
  `EventGetCoopCover` player.cpp:12634-12649: 0/1/2/3 as in section 1.
- Declarations: player.h:914-915, `TickCoopCover()` player.h:1021.

Per-player engine state (player.h:377-402, comment block 377-384 is the architecture statement:
*"The engine - not the statemap or script - is the single authority for dropping out"*):

| member | meaning |
|---|---|
| `m_bCoopCoverRequested` | player asked for cover (player.h:386) |
| `m_bCoopCoverWall` / `m_bCoopCoverLow` | requested + pose geometrically valid THIS frame (387-388) |
| `m_bCoopBlindfire` | covered + fire held + gun-class weapon this frame (389) |
| `m_iCoopCoverSent` | last `coop_coverView` value stuffed to client, change-gated (390) |
| `m_iCoopBfButtons` / `m_bCoopBfShotDone` | semi-auto blindfire edge detect / one-shot latch (391-392) |
| `m_vCoopCoverNormal` | ANCHORED cover OUT normal (wall: away from wall; low: back at player) (396) |
| `m_iCoopCoverSide` | 1 = opening LEFT, -1 = RIGHT (wall only) (397) |
| `m_bCoopCoverPeek` | RMB peek-aim active (398) |
| `m_fCoopCoverBadTime` | grace-window start (used TickCoopCover 13614-13622) |
| `m_fCoopPeekFrac` | eased peek step-out fraction (13664) |
| `m_iCoopVarCoverLast` | change gate for the `coop_incover` entity-var push (player.h:402, init -1 player.cpp:2379) |

Statemap conditionals (pure mirrors, `player_conditionals.cpp:1043-1074, 1093-1096`):
`COOP_COVER` = `m_bCoopCoverWall`, `COOP_COVER_LOW` = `m_bCoopCoverLow`,
`COOP_COVER_PEEK` = `m_bCoopCoverPeek`, `COOP_COVER_OPENRIGHT` = `m_iCoopCoverSide < 0`,
`COOP_BLINDFIRE` = `m_bCoopBlindfire`. Declared player.h:579-580.

## 4. `Player::TickCoopCover` — the per-frame validator (player.cpp:13452-13730)

Runs from `ClientThink` right after `TickSprint`, same `last_ucmd` timing (player.cpp:5258;
design comment 13248-13270). Also runs once inside the `coop_setcover` event (12624).

**Flow**:

1. **Not requested** -> clear everything, `SendCoopCoverView()`, return (13457-13465).
2. **Hard cancels** (13467-13478): `deadflag`, spectator, `m_pVehicle`, `m_pTurret`, `m_pLadder`,
   `level.playerfrozen`, `m_bFrozen`, `FL_IMMOBILE`, **any** `last_ucmd.forwardmove/rightmove`,
   or `upmove > 0` (jump; crouch upmove<0 does NOT cancel). Cancels the whole request — the
   statemap `!` exits fire the same frame. Note: `SendCoopCoverView()` MUST be on every exit path
   (13272-13276 — it originally wasn't, and releasing cover left the client camera lifted).
3. **How the wall/obstacle is found: raw world traces, no entity queries.**
   Cvars fetched live each frame (13481-13488): `coop_coverWallDist 40`, `coop_coverLowDist 48`,
   `coop_coverLowHeight 72` (head-clear height, raised from hardcoded 58 on 07-19 so taller
   crates register — 13483), `coop_coverGrace 0.5` — all `CVAR_ARCHIVE`, engine-registered
   (nothing seeded in autoexec.cfg). Probe direction = `yaw_forward` (flat view yaw, "same source
   CondSolidForward uses", 13489).
   - **WALL block is disabled wholesale**: `if (false)` at 13501, comment 13497-13500: *"REMOVED -
     it was buggy and could crash (the entry view-snap + the peek step-out that setOrigin()'s the
     body toward a corner could shove the player into geometry)"*. Inside the dead block (kept as
     reference): entry = chest-height (48u) trace FORWARD `fWallD`, accept if hit plane is
     mostly-vertical (`|normal.z| < 0.7`) and facing the player (`dot(normal, fwd) < -0.5`), then
     **snap view yaw to the wall normal** (`SetViewAngles`, 13530-13532), anchor
     `m_vCoopCoverNormal`/`m_vCoopCoverBaseOrg`; sustain = trace from the ANCHORED base along the
     ANCHORED normal so free-look/peek can't break it (13505-13521); plus the open-side probe
     (step 44u left/right along the wall, re-trace; sets `m_iCoopCoverSide`, 13551-13576).
   - **LOW (live path)** (13579-13610): trace 1 from `origin + (0,0,36)` (crouch-chest) along
     probe dir for `fLowD` must HIT a mostly-vertical solid facing the player
     (`|normal.z| < 0.7`, `dot < -0.5`); trace 2 from `origin + (0,0,fLowH)` (head, default 72u)
     over the same line must be CLEAR (fraction >= 1). On first engage the obstacle OUT normal is
     anchored (`m_vCoopCoverNormal = -probe`, `m_vCoopCoverBaseOrg = origin`, 13603-13606); while
     the pose holds, the probe direction is the anchored `-m_vCoopCoverNormal`, NOT the live view
     (13588-13590) — so free-look and RMB peek cannot break the tuck.
   - **Stance is NOT checked** — the statemap owns height ("modheight duck" tucks the player
     automatically when LOW engages from STAND, 13260-13261). You do NOT need to be crouched
     already; pressing the bind while standing in front of a low wall crouch-snaps you.
4. **Geometry grace** (13612-13622): if neither pose is valid, start/extend `m_fCoopCoverBadTime`;
   past `coop_coverGrace` (0.5 s) the request is dropped so the toggle can't go stale in the open.
   Brief gaps (stance morph, doorway edge while turning) survive.
5. **Pose flags + PEEK** (13625-13648): `m_bCoopCoverPeek` = (pose valid) AND
   `last_ucmd.buttons & BUTTON_COOPADS` (the dedicated ADS button = `+button13`, BIND.SCR:58,
   usercmd bit13 from the ADS rework). On peek RELEASE the view yaw snaps back to face the
   obstacle (13637-13648), pitch zeroed.
6. **PEEK STEP-OUT [216]** (13651-13682): eases `m_fCoopPeekFrac` toward 1 only when
   `m_bCoopCoverPeek && m_bCoopCoverWall` (13658) — **wall-only, so with wall cover disabled this
   never engages**; low-cover peek is the stand-up in the statemap instead (section 5). The
   mechanism (kept, dead): slide origin `coop_peekStep 30`u along the wall toward the detected
   side + `coop_peekOut 8`u outward, bbox-traced with `MASK_PLAYERSOLID` then `setOrigin`
   (13669-13681).
7. **BLIND FIRE** (13684-13712): pose valid, NOT peeking, `BUTTON_ATTACKLEFT` held, active
   weapon class in PISTOL|RIFLE|SMG|MG (13692-13696). Empty clip -> flag off so reload can run
   (13697-13698). Semi-auto: press EDGE only (must release trigger to re-arm, 13699-13703);
   full-auto: held (13704-13706). One-click-one-shot enforcement is in
   `Player::CoopBlindfireAllowShot` (13287-13322), asked by `Weapon::Shoot` per round: first
   round latches `m_bCoopBfShotDone` AND drops `m_bCoopBlindfire` mid-anim to cut the multi-fire
   clip short (safe because the muzzle raise is gated on the POSE, not the flag — 13311-13318).
8. **Script-visible stamps [235]** (13714-13726): pushes entity var `coop_incover` (0/1,
   change-gated via `m_iCoopVarCoverLast`) and `coop_bf_t` (level.time refreshed every
   blind-firing frame) via `Vars()->SetVariable`. NOTE the property read
   `local.player.coop_incover` resolves the EV_GETTER (0-3), which SHADOWS this 0/1 entity var —
   proven by the 08-07 xp.scr fix (xp.scr:636-640: `== 1` never matched because reads returned
   2/3; now `>= 2`). The var push effectively serves nothing for property reads; `coop_bf_t`
   (no getter) is read normally (xp.scr:642, 0.75 s window = blindfire kill).
9. **`SendCoopCoverView()`** (13277-13285): change-gated
   `stufftext "set coop_coverView %d"` to the owning client; 1 while a pose is live and NOT
   peeking. Per-frame stufftext would flood the reliable channel — same rule as `coop_limpView`.

**Pose replication to cgame**: `PMF_COOP_COVER` = pm_flags bit 13 (bg_public.h:274), set/cleared
every frame in EndFrame from `m_bCoopCoverWall || m_bCoopCoverLow` (player.cpp:8424-8430).

## 5. Statemaps (the visible pose)

`.st` files are pk3 data BUT parse errors **ERR_DROP the server**, and `LoadStateTable` needs a
client — the first LISTEN launch after a .st edit is the real test (FEATURES.md:241-245).

**Legs** — `coop_mod/player_legs.st`:
- Entry edges: from STAND (player_legs.st:56-61) `COVER_WALL : COOP_COVER`,
  `COVER_LOW : COOP_COVER_LOW`; from CROUCH_IDLE (569-570) `COVER_LOW : COOP_COVER_LOW`
  (comment: "already crouched at a low obstacle when the pose engages").
- Block header (1889-1906): full-body AI cornering anims own every bone while the torso parks in
  COVER_TORSO; engine clears the request so `!` exits restore defaults same frame; fire states
  MUST ping-pong back via `ANIMDONE_LEGS` — a self-transition early-returns in `SetPartAnim`
  (same anim) and sticks on the last frame with no restart and no further fire commands
  (1902-1905). That is a REUSABLE gotcha for any anim-driven fire loop.
- `COVER_WALL` (1909-1931): modheight stand; anim `coop_cover_wall`; exits to COVER_WALL_FIRE on
  COOP_BLINDFIRE, STAND on !COOP_COVER, FALL. (Unreachable today — COOP_COVER never true.)
- `COVER_WALL_FIRE` (1933-1959): right corners use the OVERHEAD crate spray `coop_blindfire_low`
  (COOP_COVER_OPENRIGHT row, 1942-1946) because `mp44_wall_blindfire_right.skc` shoots with the
  LEFT hand while MOHAA guns stay on tag_weapon_right = rifle at the ceiling (bug-310).
- `COVER_LOW` (1961-1988): entrycommands `modheight "duck"`, `movementstealth "1.25"`,
  `moveposflags "crouching"`; anim `coop_cover_low`. Exits: `COVER_LOW_PEEK : COOP_COVER_PEEK`
  (must sit ABOVE the blindfire row — while peeked, fire is AIMED, 1977-1980),
  `COVER_LOW_FIRE : COOP_BLINDFIRE`, `CROUCH_IDLE : !COOP_COVER_LOW`, `FALL_DUCKED : FALLING`.
- `COVER_LOW_PEEK` [223] (1995-2023): **the low-cover peek = stand up in place** — modheight
  "stand" raises bbox + eye for real line-of-sight over the obstacle; plays the standing
  wall-cover hold; exitcommands re-assert duck.
- `COVER_LOW_FIRE` (2026-2047): duck, plays `coop_blindfire_low`, ping-pongs via ANIMDONE_LEGS.
- The legs statemap has NO `KILLED` state — the engine force-jumps death; adding a KILLED edge
  crashes at parse (bug-382).

**Torso** — `coop_mod/player_Torso.st`:
- STAND dispatch rows (84-89): `COVER_TORSO : COOP_COVER` / `COOP_COVER_LOW` — must sit ABOVE
  the attack edges so hip ATTACK can't fight the full-body anims.
- `COVER_TORSO` (206-238): `camera behind` (**this is what forces third person view mode**,
  together with the cgame PMF gate), action `none` (whole body to legs), NO attack edges on
  purpose (blindfire rounds come from anim frame commands); reload + weapon switch still work
  (return to STAND which re-enters here); exits to COVER_PEEK_TORSO on COOP_COVER_PEEK, STAND
  when both poses gone.
- `COVER_PEEK_TORSO` [217] (247-289): cover-owned aim state. Exists because routing peek through
  the vanilla AIM state bounced AIM->STAND->COVER_TORSO->AIM in one evaluation pass = engine
  infinite-loop guard = server kill (bug-313, comment 241-245). **Lesson: never transition INTO a
  vanilla hub state whose exits you don't control.** Holds TRUE shouldered aim via `coop_aim_*`
  action rows per weapon class (263-273; bug-323: `stand_idle` is a muzzle-up CARRY, the AI
  *_aim anims are the real aim holds); fire dispatch rows copied from AIM (287-288).

## 6. Animations — `models/player/base/anims_shared.txt`

Donor set = the AI cornering family, weapon-agnostic, skc paths verified in main/Pak0.pk3
(533-539). No `weight` flag anywhere — weight POOLS numbered aliases under the digit-stripped
base name and makes them unaddressable (bug-260, comment 538).

- `coop_cover_wall` = `weapon_rifle/cornering/rifle_wall_alert_left.skc` (540)
- `coop_cover_low` = `weapon_mp40/cornering/mp40_crate_alert.skc` (541)
- `coop_blindfire_wall` = mp40_wall_blindfire_left + server frame commands `1/3/5/7 fire` (542-551)
- `coop_blindfire_low` = mp40_crate_blindfire + `1/3/5/7/9/11/13 fire` (552-564) — **the anim
  pulls the trigger**, copied verbatim from vanilla AI aliases; COVER_*_FIRE states just play it
- `coop_blindfire_wall_r` = mp44_wall_blindfire_right + fire frames (594-603) — unused in states
  (bug-310, right corners reuse `coop_blindfire_low`)
- `coop_aim_rifle/smg/mg/pistol` = AI aim holds for the peek torso (569-574)
- Any statemap-referenced alias MUST resolve or the server dies (bug-306/307 lesson).

## 7. Weapon integration (fgame `weapon.cpp`)

- **Low-cover muzzle raise** — `GetMuzzlePosition` (1682-1700): while `IsCoopCoverLow() &&
  !IsCoopCoverPeek()` raise fire origin by `coop_blindfireRaise` (registered "32" here; fallback
  literal 26.0f — and cgame registers the same cvar as "26", see section 8). Gated on the POSE,
  not the blindfire flag — trailing anim-frame rounds after trigger release/dry-clip used to lose
  the raise and shoot into the cover (1688-1695).
- **Spread penalty** — `Shoot` (1936-1947): while `IsCoopBlindfiring()`, bullet spread x
  `coop_blindfireSpread` (3.0) — "unaimed fire is a suppression tool".
- **Wall blindfire corner steering** (1973-2004, dead while wall cover is off): rotate the aim
  basis `coop_blindfireYaw` (50 deg) around Z toward the open side, slide fire origin
  `coop_blindfireOut` (20u) along the wall + 8u out so rounds clear the edge.
- **Semi-auto one-click** — `Weapon::Shoot` asks `Player::CoopBlindfireAllowShot()` per round
  (section 4.7).

## 8. cgame integration

- **Auto-3P**: `cg_view.c:2476-2478` — `PMF_COOP_COVER` forces `cg.renderingThirdPerson`;
  server drops the flag the same frame cover ends. `cg_modelanim.c:1287` draws your own model.
- **No orbit capture while covered [232]**: `CG_FreecamEligible` returns qfalse under
  `PMF_COOP_COVER` (cg_view.c:1627-1637). History in the comment: bug-303 originally FORCED the
  orbit (view-dependent sustain trace); after the sustain was anchored and [226] made the server
  view track the camera, the layered orbit double-applied pitch and wedged the camera past
  vertical (bug-327). Final model: mouse aims directly, camera chases live aim.
- **Cover camera lift**: `CG_CoopCoverViewLift` (cg_view.c:139-148) — `coop_coverView` (mirrored
  from server via change-only stufftext) times `coop_coverViewRaise` (16, CVAR_ARCHIVE); applied
  in `CG_OffsetThirdPersonView` BEFORE the chase camera derives (cg_view.c:169-171). 3P-only by
  design — applying it in 1P left a stale lift on exit (comment 136-138).
- **Crosshair truth**: `CG_DrawCrosshair3P` traces from the MUZZLE height while covered —
  reads the SAME `coop_blindfireRaise` cvar the server fires from so they cannot drift
  (cg_drawtools.cpp:1495-1512). Wall-yaw steering deliberately not mirrored (client lacks side
  + normal, 1501-1503).
- **HUD fade exemption**: `PMF_COOP_COVER` keeps the HUD visible (cg_drawtools.cpp:2059).

## 9. Cvar inventory (all engine-registered, none seeded in cfgs)

| cvar | default | where | role |
|---|---|---|---|
| `coop_coverWallDist` | 40 | player.cpp:13481 | wall probe reach (dead) |
| `coop_coverLowDist` | 48 | player.cpp:13482 | low chest-probe reach |
| `coop_coverLowHeight` | 72 | player.cpp:13483 | head-clear height (was hardcoded 58) |
| `coop_coverGrace` | 0.5 | player.cpp:13484 | geometry-invalid grace seconds |
| `coop_peekStep` / `coop_peekOut` | 30 / 8 | player.cpp:13656-13657 | wall peek step-out (dead) |
| `coop_blindfireSpread` | 3.0 | weapon.cpp:1941 | blindfire spread multiplier |
| `coop_blindfireRaise` | **32 (fgame) / 26 (cgame)** | weapon.cpp:1697 / cg_drawtools.cpp:1508 | low-cover fire-origin raise |
| `coop_blindfireYaw` / `coop_blindfireOut` | 50 / 20 | weapon.cpp:1981-1982 | wall corner steering (dead) |
| `coop_coverView` | 0, NOT archived | cg_view.c:144 | server->client pose mirror |
| `coop_coverViewRaise` | 16 | cg_view.c:145 | 3P camera lift while covered |

All tunables are `CVAR_ARCHIVE` = live-tunable in console and persisted. First registration wins
the default; the `coop_blindfireRaise` 32-vs-26 split means the effective default depends on
which DLL registers first (archived value usually masks it, but it is a latent drift).

## 10. Interactions with other systems

- **ADS**: peek IS the ADS button (`BUTTON_COOPADS`, +button13). While peeked: real aimed fire
  (COVER_PEEK_TORSO fire rows), full accuracy, no blindfire, no muzzle raise, no camera lift
  (SendCoopCoverView sends 0 while peeking, player.cpp:13279).
- **Sprint / movement**: no explicit sprint interlock needed — ANY forward/right move or jump in
  `last_ucmd` hard-cancels the request (player.cpp:13468-13469). TickCoopCover runs right after
  TickSprint in ClientThink (player.cpp:5258).
- **3P shoulder cam / freecam**: covered = forced 3P + no orbit capture (section 8).
- **DBNO / turret / vehicle / ladder**: blocked at the script gate (takecover.scr:22-24) AND
  hard-cancelled engine-side (13468); DBNO itself is published to the engine via the parallel
  `coop_setdbno` event (player.cpp:12609-12617) — the pattern coop_setcover mirrors.
- **XP**: `xp.scr` pays +blindfire-kill (`coop_bf_t` within 0.75 s, xp.scr:642) or +cover-kill
  (`coop_incover >= 2`, xp.scr:640, fixed 08-07 from `== 1`); one bonus only (priority chain,
  bug-1514).
- **Build-mode geometry**: buildmode props are given SOLID_BBOX clips at human height explicitly
  SO the takecover traces work against them (buildmode_catalog.scr:2008, 2209) — placed props
  are already valid cover.
- **Deployed sandbags** (`cover.scr`): collision deliberately set to 54u so the 36u chest trace
  hits and the (then-58u) head trace clears (bug-536) — the two features already compose.

## 11. markwall / killwall — proven wall-interrogation surface

Wall probe v5, bug-953. Both are `EV_CONSOLE` **player events = bindable console commands**
(player.cpp:1325-1340), suggested binds documented at autoexec.cfg:47-49. This is the precedent
that the engine can interrogate and report exactly what a player is aiming at.

- **`markwall`** — `Player::EventCoopMarkWall` (player.cpp:12553-12604), report-only. Traces
  512u from the eye along `v_angle` with `MASK_PLAYERSOLID & ~CONTENTS_BODY`, then runs
  differential re-traces with bits stripped to classify the hit **species**: `clip`
  (CONTENTS_PLAYERCLIP), `fence` (CONTENTS_FENCE), `solidnodraw` (world + SURF_NODRAW),
  `entity`, else `solid`. Reports: species, brush id (`gi.PointBrushnum` of endpos nudged 2u
  inward), shader name (`gi.GetShader(tr.shaderNum)->shader`), `surfaceFlags` hex, entityNum,
  endpos, distance — to BOTH the server log (machine-parseable `^~^~^ WALLPROBE MARK` line,
  12587-12598) and the player's HUD print (12599-12603).
- **`killwall`** — `EventCoopKillWall` (player.cpp:12503-12551): same trace; refuses entities
  and visible geometry; if invisible species on the world, dispatches `cm_killbrush <n>` (live +
  persisted to the loose cmpatch file).
- **Capability summary for the proposal**: from engine code, a single G_Trace from the player
  already yields plane normal, surfaceFlags, shader, contents species, entity vs world, and
  brush id — everything an "is this attachable cover?" classifier could want. Script-side,
  the pattern for exposing any of it is the `coop_setcover`/`coop_incover` event+getter pair
  (or an entity-var push, with the shadowing caveat in section 4.8).

## 12. Known defects, quirks, dead code (with bug ids)

1. **WALL cover removed** — `if (false)` player.cpp:13501; takecover.scr:44. Crash causes:
   entry view-snap + peek step-out `setOrigin` shoving the player into geometry (13497-13500);
   earlier hard crash bug-308 (cgame `get_camera_offset(NULL,NULL)` null write on the first
   PMF_COOP_COVER frame). `coop_incover == 2` can never occur now.
2. **Dead-but-shipping**: COVER_WALL/COVER_WALL_FIRE states, side probe, peek step-out
   (wall-gated at 13658 — so LOW peek has NO lateral step, only the stand-up), wall blindfire
   steering + `coop_blindfireYaw/Out`, `coop_blindfire_wall(_r)` aliases, `coop_peekStep/Out`.
3. **`coop_blindfireRaise` default mismatch** 32 (fgame) vs 26 (cgame) + weapon.cpp fallback
   literal 26.0f (section 9).
4. **Stale 58u comments**: weapon.cpp:1686 and bug-536's fix text still describe the old 58u
   head trace; the height is `coop_coverLowHeight` = 72 since 07-19 (player.cpp:13483). Sandbag
   54u collision still clears either way.
5. **`Vars()` `coop_incover` push (0/1) is shadowed by the same-named EV_GETTER (0-3)** for
   property reads — cost one real bug (xp `== 1`, fixed to `>= 2` on 08-07, xp.scr:636-640).
   Any new state mirror should avoid reusing a getter's name for an entity var.
6. **OPEN.md:417 is stale**: "cover-peek physical step-out" is listed as queued design (bug-311)
   but was implemented as [216] — for WALL cover only, and is now dead with it.
7. **Semi-auto blindfire one-click** (bugs fixed 08-07): COVER_*_FIRE clips carry several fire
   frames; the latch + mid-anim flag drop in `CoopBlindfireAllowShot` is what stops G43
   triple-taps (player.cpp:13287-13322).
8. **SendCoopCoverView on every exit path** — early returns once skipped it and the client kept
   the camera lift after release (13272-13276).
9. **Statemap crash classes to respect**: undefined target state = parse-time ERR_DROP
   (bug-382); transition into vanilla AIM hub = infinite-loop guard server kill (bug-313);
   weighted numbered aliases unaddressable (bug-260); missing alias referenced by a state =
   ERR_DROP on first fire (bug-306/307).
10. Status: FEATURES.md:232-239 — `SHIPPED-UNVERIFIED`, "shipped as EXPERIMENTAL with known
    bugs"; anchors `Player::TickCoopCover`, bugs 303-329. Bipod plan already clones this recipe
    (`Player::TickCoopBipod`, FEATURES.md:936).
