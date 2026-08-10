# Server topology, limits, and the lag/desync plan

**Status:** research + plan. No engine source, no `coop_mod/` script, and no cfg was modified producing this.
**Date:** 2026-08-10. **Engine tree:** `C:\mohaa-coop-dev\openmohaa-hzm\code\` (uncommitted working tree as of today).
**Rule:** every behavioural claim carries a `file:line`. Where this contradicts an earlier record, the code wins.

---

## 0. Corrections to the brief

Five things in the framing I was given need adjusting before anything is built on them.

| Claim as given | What the code says |
|---|---|
| "`common.c:2354` computes `msec = com_frameTime - lastTime`" | The arithmetic is at **`qcommon/common.c:2347-2350`**. `:2354` is the first line of the bug-1664 comment block. Minor, but the surrounding lines matter — see §1. |
| "On a listen server the server tick is gated by the host's framerate" | **Half right, and the half that is wrong changes the fix.** The *simulation* is not gated: `SV_Frame` accumulates `sv.timeResidual += msec` (`server/sv_main.c:1101`) and runs the game in exact `1000/sv_fps` chunks in a `while` loop (`sv_main.c:1193-1211`), so at host 30 fps it still runs 40 ticks/sec, in a 1-1-1-2 pattern, each tick exactly 25 ms. What *is* gated by host framerate is **snapshot transmission and inbound packet processing**, because `SV_SendClientMessages()` is called once per `SV_Frame` call (`sv_main.c:1221`), i.e. once per main-loop iteration. The mod is not simulating slowly; it is *delivering* slowly. |
| "`MAX_SOUNDS` raised to 1280" | It is **1600** (`qcommon/q_shared.h:1742`), raised again under bug-1186 after `MAX_RELIABLE_COMMANDS` went 512→1024. 1280 was the bug-1183 revert, since superseded. |
| "the server is chronically behind" (bug-1663) | On a **listen** host this is not what the numbers mean. `sv.timeResidual` cannot accumulate — the `while` loop drains it every frame. A mean `msec` of 30-32 ms means *the host's main loop ran at 31-33 fps*, nothing more. The simulation kept up. (On a **dedicated** server the same reading did mean the frame was late, because there `minMsec = SV_FrameMsec()` — the loop rate *is* the tick rate.) |
| "the phone jack is that client's commands unacknowledged past `CMD_BACKUP`" | Correct (`cgame/cg_drawtools.cpp:188`, `CMD_BACKUP` = 128, `cgame/cg_public.h:35`). Worth adding that the "slow server" icon is additionally gated on `if (!developer->integer && !cgs.gametype) return;` (`cg_drawtools.cpp:354`) — coop is gametype 2, so it always shows. |
| "`ihuddraw`/stufftext traffic per player" (listed together as one pressure) | **Different transports with opposite failure modes.** `ihuddraw_*` is an unreliable, per-client, bit-packed CGM riding the snapshot; it fails by *silently dropping* (`server/sv_game.c:165-178`). `stufftext` is a reliable command; it fails by *kicking the client* (`server/sv_main.c:208`). Conflating them is how the actual defect in §5a stayed invisible. |

Everything else in the brief checked out, including the `sv_fps * msec > 1100` threshold and its 2500 ms rate limit (`sv_main.c:1135`), and the bug-1667 `timeBeginPeriod` fix (`sys/sys_win32.c:817-840`).

**One finding is a defect, not a performance item, and it is not in the brief at all:** `chal_ui_export` queues **996 reliable commands per player into a 1024-deep ring every 30 seconds, on by default**, and the failure mode is a client kick that the host can never see. See §5a. It should be fixed before any of the performance work.

---

## 1. The frame loop, exactly

### `Com_Frame` anatomy (`qcommon/common.c:2246-2449`)

```
2296  minMsec = dedicated ? SV_FrameMsec()          <-- dedicated: loop rate == sv_fps
                          : 1000 / com_maxfps      <-- listen:    loop rate == com_maxfps
                            (with the +/- bias corrector at :2311-2319)

2325  do {                                          <-- idle/sleep window
2329      SV_SendQueuedPackets()                    <-- ONE fragment per client, rate-gated
2339      NET_Sleep(timeVal - 1)                    <-- select() on the UDP sockets;
      } while (Com_TimeVal(minMsec))                    inbound client packets are handled HERE

2348  com_frameTime = Com_EventLoop()               <-- loopback packets + input events
2350  msec = com_frameTime - lastTime               <-- the WHOLE previous iteration
2365      Cbuf_Execute(msec)   (dedicated only)
2379  msec = Com_ModifyMsec(msec)                   <-- clamps to 200 (listen) / 5000 (dedicated)
2388  SV_Frame(msec)                                <-- sim + snapshot send
2420  Com_EventLoop()                               <-- second drain, "without a frame of latency"
2433  CL_Frame(msec)                                <-- CL_SendCmd, then SCR_UpdateScreen (blocks)
```

Two facts follow directly and are the spine of everything below.

**(a) `SV_Frame` self-gates the simulation, so calling it more often is free.** `sv_main.c:1093` computes `frameMsec = 1000 / sv_fps`; `:1101` adds the elapsed time to `sv.timeResidual`; `:1193-1211` runs `ge->RunFrame(svs.time, frameMsec)` only while the residual covers a whole tick. The timestep handed to the game module is *always* exactly `frameMsec`. Calling `SV_Frame(2)` twelve times and `SV_Frame(24)` once produce the same simulation. **There is no downside to driving `SV_Frame` faster than `sv_fps`, and that is the property the fix in §9 relies on.**

**(b) Everything *except* the simulation runs once per `SV_Frame` call, not once per tick.** `SV_CalcPings` (`:1190`), `SV_CheckTimeouts` (`:1218`), `SV_SendClientMessages` (`:1221`), `SV_MasterHeartbeat`, `SV_HandleNonPVSSound` (`:1234`) all sit *outside* the `while` loop. So the snapshot cadence is bounded above by the main-loop rate.

### The two topologies side by side

| | Listen (`com_dedicated 0`) | Dedicated (`com_dedicated 1/2`) |
|---|---|---|
| Loop rate `minMsec` | `1000/com_maxfps`, but the **real** period is `max(1000/com_maxfps, render+swap time)` | `SV_FrameMsec()` = `frameMsec - timeResidual` (`sv_main.c:1020-1035`) — loop rate **is** `sv_fps` |
| Simulation rate | exactly `sv_fps` (residual-driven) | exactly `sv_fps` |
| Snapshot send opportunities/sec | = host render fps | = `sv_fps` |
| Inbound usercmd processing | once per render frame | 40×/sec at `sv_fps 40` |
| Hitch clamp | `Com_ModifyMsec` clamps `msec` to **200 ms** (`common.c:2211`) — a longer stall silently drops simulation time | clamped to **5000 ms** (`:2201`) + prints `"Hitch warning: %i msec frame time"` (`:2199`) |
| Local client's netchan | `NA_LOOPBACK` → `FRAGMENT_SIZE` 9900 (`qcommon/net_chan.c:52`), **rate limiter bypassed entirely** (`sv_snapshot.c:1332`) | n/a |
| Host's usercmd send | every frame, `cl_maxpackets` bypassed for loopback (`client/cl_input.cpp:1067-1069`) | n/a |

**This is why the dedicated server measured better.** Nothing about dedicated is inherently faster; it simply has no render step in the loop, so its loop rate equals its tick rate by construction.

---

## 2. Q1 — Listen mechanics, quantified

### The governing law

> **On a listen host, remote clients receive at most one snapshot per host render frame.**

The chain: `SV_SendClientMessages` (`sv_snapshot.c:1301`) runs once per `SV_Frame`, which runs once per `Com_Frame`, which runs once per render. Within it, each client passes four gates:

1. `svs.time - c->lastSnapshotTime < c->snapshotMsec` → skip (`sv_snapshot.c:1315`) — the `snaps` gate.
2. `c->netchan.unsentFragments || c->netchan_start_queue` → skip (`:1324`) — the **fragment** gate.
3. `*c->downloadName` → skip (`:1321`).
4. `SV_RateMsec(c) > 0` → skip, set `SNAPFLAG_RATE_DELAYED` (`:1330-1342`) — the `rate` gate, **bypassed for `NA_LOOPBACK` and (with `sv_lanForceRate 1`) for LAN**.

### At host 30 fps with `sv_fps 40`

- **Simulation:** unaffected. 40 ticks/sec, 25 ms each, in a 1,1,1,2 burst pattern. `svs.time` advances 25 or 50 ms per iteration.
- **Snapshot rate:** ~30/sec, not 40. Even a client asking for `snaps 40` (`snapshotMsec` 25) cannot get more than one per loop iteration.
- **Snapshot spacing:** wall-clock ~33 ms, but `serverTime` inside them jumps 25 or 50 ms. The client's `serverTime` is therefore *irregular in both axes*.
- **Inbound latency:** a remote player's usercmd sits in the socket until the next `NET_Sleep`/`Com_EventLoop`, i.e. up to 33 ms, mean ~16 ms, on top of network RTT.
- **Client-side response:** `CL_AdjustTimeDelta` (`client/cl_cgame.cpp:1060-1115`) drifts `serverTimeDelta` **+1 ms per snapshot** normally and **−2 ms** whenever the previous interval had to be extrapolated (`:1101-1109`). Irregular arrival makes the extrapolation flag fire often, so the client oscillates around the boundary instead of settling. That oscillation is the micro-stutter players describe as "rubber-banding on nothing".
- **Extrapolation:** when `cg.nextSnap` is missing the cgame breaks out of its interpolation loop and extrapolates (`cgame/cg_snapshot.c:483-491`, comment at `:439-441`). Remote *players* are predicted locally so this is mostly invisible for your own movement; **AI, vehicles, and any player with `PMF_NO_PREDICTION` (vehicle riders, DBNO) are pure interpolation** and show it directly.

### The slow-server icon, converted to a framerate

`sv_main.c:1135`: `sv_fps * msec > 1100`. At `sv_fps 40` that is `msec > 27.5 ms`.

On a listen host `msec` **is the render frame period**, so:

> **The "slow server" icon lights for everyone whenever the host's framerate drops below ~36.4 fps.** At `sv_fps 20` the equivalent threshold is 18.2 fps; at `sv_fps 60` it is 54.5 fps.

The measured listen mean of 30-32 ms is exactly 31-33 fps — squarely under the threshold, so the icon is on essentially permanently, which is what was observed. The icon is *correctly* reporting "the host is not delivering at the promised rate"; it is *incorrectly* implying the simulation is late, which on a listen server it never is.

---

## 3. Q2 — Is the host advantaged?

Yes, measurably, and in one place it affects gameplay rather than only diagnostics.

**Input path.** The host's usercmds go over loopback, which bypasses `cl_maxpackets` (`cl_input.cpp:1067-1069`) and is delivered in-process. `Com_EventLoop` at `common.c:2348` drains loopback *before* `SV_Frame` in the same iteration, so the host's input reaches the simulation with **≈ one loop period of latency (5-6 ms at `com_maxfps 180`, ~33 ms if the host is at 30 fps)**. A remote player at `cl_maxpackets 30` (the engine default and floor, `cl_main.cpp:3979`, `cl_input.cpp:1077-1078`) has `1000/30 = 33 ms` of send quantisation, plus one-way network latency, plus up to one host loop period of arrival jitter.

**Output path.** The host's snapshot is never rate-choked (`sv_snapshot.c:1332`) and never fragmented (loopback `FRAGMENT_SIZE` 9900 vs 1300 for remote, `net_chan.c:52`). So the host is the only participant guaranteed to receive a complete, current world every frame.

**Round-trip asymmetry, order of magnitude:**

| | host | remote, 30 ms RTT, `cl_maxpackets 30`, `snaps 40` |
|---|---|---|
| input → simulated | ~5 ms (at 180 fps) | ~17 (send quantisation) + 15 (one way) + ~16 (host loop jitter at 30 fps) ≈ **48 ms** |
| simulated → seen | ~5 ms | ~15 (one way) + ~25 (one snapshot interval of interpolation buffer) ≈ **40 ms** |
| **total** | **~10 ms** | **~88 ms** |

**Does it affect fairness?** For a coop mod, "fairness" is really *hit registration against AI*. Two findings:

1. **There is no lag compensation anywhere in this engine.** I searched the whole tree for `antilag`, `unlagged`, `G_TimeShift`, `lagcomp`, `LagCompensat` — **zero hits**. Bullet traces are resolved server-side at the current server time using the angles carried in the usercmd. So a remote player must lead a moving target by their full input→simulate latency; the host must not. On a running AI at ~200 u/s, 48 ms is ~10 units of lead. That is a real, felt difference on head-sized targets, and it is worse on a host running at 30 fps than at 180.
2. It is **not** a diagnostics-only artefact, but it is also **not** the thing players will notice first. The dominant complaint from a 31-fps host will be interpolation stutter on AI and riders, not hit registration.

The honest summary: the host advantage is structural and unfixable without writing lag compensation, but **its magnitude is dominated by the host's loop rate**, which §9 does fix. Raising the host loop rate from 31 to 180 Hz removes ~16 ms of the ~48 ms gap and all of its jitter.

---

## 4. Q3 — Does vsync gate the server tick on a listen host?

**Yes. Confirmed from the code, with one important nuance.**

The chain is unbroken and single-threaded:

```
common.c:2433   CL_Frame(msec)
cl_main.cpp:2868    SCR_UpdateScreen()
cl_scrn.cpp:522-537     -> SCR_SimpleUpdateScreen() -> RE_EndFrame -> RB_SwapBuffers
renderergl1/tr_backend.c:1560  RB_SwapBuffers  -> GLimp_EndFrame
sdl/sdl_glimp.c:1250-1256      GLimp_EndFrame  -> SDL_GL_SwapWindow(SDL_window)
```

There is no render thread and no `r_smp` in this fork. `SDL_GL_SwapWindow` with `SDL_GL_SetSwapInterval(r_swapInterval)` (`sdl_glimp.c:866-868`) blocks the calling thread once the driver's swap queue is full. That thread is the main thread. The next `SV_Frame` cannot happen until it returns.

**The nuance that matters for this user's profile.** `r_swapInterval 1` quantises the loop period to multiples of the refresh interval. On the user's 180 Hz display that interval is 5.56 ms, so vsync alone costs almost nothing — the slow-server threshold of 27.5 ms is **5 refresh intervals** (27.8 ms), i.e. 36 fps. So:

> On a 180 Hz display, vsync is **not** the problem. On a **60 Hz** display it is severe: one missed refresh takes the loop from 16.7 ms to 33.3 ms, which is above the 27.5 ms threshold — a single dropped frame trips the icon and halves the snapshot rate. Any player hosting on a 60 Hz monitor with `r_swapInterval 1` is one dropped frame away from a visibly degraded server.

`coop_defaults.cfg:74` ships `seta r_swapInterval 1`, so 60 Hz hosting with vsync is the shipped default configuration. That is worth changing for hosts specifically (§9, item L2).

Secondary confirmations: `com_maxfpsUnfocused` and `com_maxfpsMinimized` both default to `0` (`common.c:1934`, `:1936`) and the code only applies them when `> 0` (`:2302-2305`), so the user's `0` settings are already the "don't throttle when alt-tabbed" behaviour and are correct for a host. **Leave them at 0** — setting either to a low value would throttle the *server* on a listen host, not just the renderer.

---

## 5. Q4 — Desync sources specific to this mod

The mod's server→client traffic uses **three different transports with wildly different costs and failure modes**, and most of the mod's problems come from not distinguishing them.

| Transport | Used by | Reliable? | Per-client cap | Behaviour at cap |
|---|---|---|---|---|
| **Reliable command queue** | `stufftext`, `print`/`iprintln`/`iprintlnbold`, `cs <n>` configstring updates, `svlag` | yes, retransmitted until acked | 1024 unacked (`qcommon/qcommon.h:215`) | **client kicked** — `SV_DropClient(client, "Server command overflow")` (`server/sv_main.c:208`) |
| **CGM channel** | every `huddraw_*`, and most cgame messages | no | **4096 bytes / 8192 datums per client per snapshot** (`server/sv_game.c:135-136`) | **silent drop**, `Com_DPrintf` once per 5 s (`sv_game.c:165-178`) — invisible without `developer 1` |
| **Snapshot inline** | `centerprint` / `locationprint` (`server/sv_game.c:1508`, `:1534`) | no | one string, overwritten | last-writer-wins, cleared after each send (`sv_snapshot.c:1272`) |

**CGM wire cost, exactly.** `PF_MSG_StartCGM` (`server/sv_game.c:382-400`) writes an 8-bit `svc_cgameMessage` tag for the first message in a block and a **1-bit continuation** for each subsequent one, then a **6-bit type**. So each `ihuddraw_*` after the first costs 7 bits of framing plus its payload, plus 8 or 16 bits for the element index (`fgame/huddraw.cpp:33-38`):

| call | bits | bytes |
|---|---|---|
| `ihuddraw_virtualsize` | 7 + 8 + 1 = 16 | 2.0 |
| `ihuddraw_alpha` (`huddraw.cpp:136-146`) | 7 + 8 + 8 = 23 | 2.9 |
| `ihuddraw_color` (`huddraw.cpp:114-127`) | 7 + 8 + 24 = 39 | 4.9 |
| `ihuddraw_rect` (`huddraw.cpp:80-86`) | 7 + 8 + 64 = 79 | 9.9 |
| `ihuddraw_string` (`huddraw.cpp:157-160`) | 7 + 8 + 8×(len+1) | ~10 + len |

**And a trap worth naming:** the `huddraw_*` family calls `gi.SetBroadcastAll()` (`huddraw.cpp:44, 57, 79, 95, 121, 141, 156, 169, 184, 203`) — **every client pays for it**. The `ihuddraw_*` family calls `gi.MSG_SetClient(cl_num)` (`huddraw.cpp:215, 224, 242, 255, 274, 286, 309, 325, 336, 345`) and costs one client. The mod uses `ihuddraw_*` at all 1158 sites, which is correct. Dropping the `i` on one line in a per-player HUD loop multiplies its cost by the player count, silently.

Three consequences, all specific to this mod:

**(1) `iprintln` is the expensive one; `centerprint` and `huddraw` are the cheap ones.** `fgame/scriptthread.cpp:2918-2993` implements every script print as `gi.SendServerCommand(i, "print \"...\"")` — one reliable slot **per player per print**. Worse, `SV_UpdateServerCommandsToClient` (`sv_snapshot.c:249-259`) re-serialises **every unacked command into every snapshot** until it is acked. So a backlog of N commands costs N string writes in each of the next several snapshots, which is how a reliable backlog turns into a `MAX_MSGLEN` snapshot overflow *before* it ever reaches the 1025 kick threshold. Anything that fires per-kill or more often must not use `iprintln`.

**(2) A rate-delayed client silently loses HUD state.** The CGM buffer is only drained and zeroed inside `SV_WriteCGMToClient` (`sv_game.c:546-547`), which only runs when that client actually gets a snapshot. A client skipped by the rate gate or the fragment gate keeps accumulating CGM until it hits 4096 bytes, then **drops the excess silently**. Since `huddraw_*` is how this mod draws objectives, DBNO, XP, challenges and the armory, the failure mode is: *network gets tight → HUD elements stop updating or go stale → looks like a script bug.* This is a causal chain worth writing into `TRAPS.md`.

**(3) Fragmentation is a self-amplifying snapshot stall.** For a remote client, `FRAGMENT_SIZE` is 1300 bytes (`net_chan.c:50-52`). Any snapshot over that fragments, and while fragments are pending that client is **skipped entirely** by `SV_SendClientMessages` (`sv_snapshot.c:1324-1328`). Fragments drain one per `SV_SendQueuedMessages` pass (`sv_client.c:1254-1276`), and each is additionally rate-gated by `SV_RateMsec`. At `rate 25000` a ~1330-byte fragment costs `1330*1000/25000 ≈ 53 ms`. **A 3-fragment snapshot therefore takes ~160 ms to deliver, during which the client receives nothing at all** — and CGM accumulates, per (2). A burst of entity spawns that pushes one snapshot over ~2600 bytes costs that client roughly four frames of world state.

### 5a. The one that is not a performance issue but a live disconnect bug

**`chal_ui_export` queues 996 reliable commands per player into a 1024-deep ring, every 30 seconds, by default.**

- `coop_mod/challenges.scr:59+` defines **332** challenges (`grep -c chal_def` = 332).
- `chal_ui_writeOne` (`challenges.scr:883-919`) emits exactly **3 `stufftext`** on both branches (`coop_uiD`, `coop_uiB`, `coop_uiN`).
- `chal_ui_export` (`challenges.scr:871-881`) walks the whole catalogue: **332 × 3 = 996 reliable commands per player per export.**
- `chal_flush` (`challenges.scr:850-861`) runs it for **every** connected player, with `thread` not `waitthread` — so all players' exports run **concurrently**.
- `chal_autosave_loop` (`challenges.scr:639-645`) calls `chal_flush` **every 30 seconds**, and it is also called at mission complete (`:2072`).
- It is **on by default**: `level.coop_chal_enabled = 1` at `challenges.scr:29`, disabled only if `coop_challenges == "0"` (`:31`), and `coop_challenges` is seeded in no shipped cfg.

`MAX_RELIABLE_COMMANDS` is 1024 and the client is dropped at 1025 (`server/sv_main.c:196-208`). **996 of 1024 is a 2.7% margin.**

The pacing comment at `challenges.scr:867-869` reads *"Paced so the 61 stufftext setas never overflow the command buffer."* **That comment is stale by a factor of 16** — it was true when the catalogue was ~20 challenges. The pacing (8 challenges = 24 commands per `waitframe`, `:879`) was tuned for a 61-command job and is now driving a 996-command job at `sv_fps 40`, i.e. **~960 new reliable commands per second per player** for about a second.

**Why this is worse than the raw number, and why it has probably never been seen on the host's own screen:**

`SV_UpdateServerCommandsToClient` (`sv_snapshot.c:249-259`) re-serialises **every unacked command into every snapshot**. So:

```
960 cmds/sec queued  ->  unacked ~= 960 x (RTT + ack interval)
                     ->  at 60 ms RTT + 33 ms (cl_maxpackets 30): ~90 unacked
                     ->  ~3.6 KB re-written into EVERY snapshot
                     ->  over FRAGMENT_SIZE (1300) -> 3 fragments
                     ->  client SKIPPED by SV_SendClientMessages while fragments pend (:1324)
                     ->  no snapshot -> no delivery -> no ack -> unacked grows
                     ->  bigger snapshot -> more fragments -> longer skip -> ...
```

That is a **positive-feedback divergence**, and its terminus is `SV_DropClient(client, "Server command overflow")`. The prediction it makes is specific and testable: **remote clients disconnect roughly 30 s into a session, or at mission complete, and the more distant the client the more reliably.**

It is invisible to the host because the host's netchan is `NA_LOOPBACK`: `FRAGMENT_SIZE` is 9900 not 1300 (`net_chan.c:52`), the rate gate is bypassed entirely (`sv_snapshot.c:1332`), and delivery is in-process, so the host's unacked count never leaves single digits. **"Works fine when I test it locally" is the exact signature of this bug.**

This outranks everything else in this document, including the decoupling work. See T0 in §8.

### 5b. Ranked mod-side cost list

*(Counts and cadences below are read directly from the scripts. Byte/sec figures assume average string lengths — treat those as order-of-magnitude. Per-iteration script CPU cost is judgement, not measurement; §10 says how to settle it.)*

| # | Source | file:line | Transport / pressure | Cost | Confidence |
|---|---|---|---|---|---|
| 1 | **`chal_ui_export`** — see §5a | `challenges.scr:871`, `:883-917`, `:639-645` | **reliable**, 996/player/flush | can **kick the client**; ~50 KB reliable per player per 30 s | counts measured, spiral reasoned |
| 2 | **`rate` throttling under firefight load** | `server/sv_main.c:1352-1388` | rate gate | calm snapshot ~400-600 B, firefight ~1000-1400 B. At 40/sec that is 16-56 KB/s vs `rate 25000` → **client silently drops from 40 to ~18 snapshots/sec exactly when the action starts** | mechanism firm, size est. |
| 3 | **Burst entity spawning** — officer battalion **22 spawns in ONE frame**, no `wait` in the loop | `officer.scr:1961-2007`; holdout wave 24-40 at `holdout.scr:383`; squads 6 each at `:2057`/`:2173`/`:2483`; dogs 5 at `:3147` | snapshot bytes → **fragmentation**; plus ~220 thread creations in one frame via `aihandler.scr:41-158` | newly-visible entities have no delta baseline and are sent in full; 22 at once is squarely over the 1300 B cliff. Crossing it costs ~100 ms of blackout, not ~20 ms of bytes | measured (spawn counts), size est. |
| 4 | **New sound/model registrations mid-map** (officer waves) | `server/sv_init.c:235`, `qcommon.h:208-210` | one **reliable** slot each | ~514 measured at m1l1 spawn. Waves register mid-map, on top of whatever `chal_ui_export` is doing | firm (documented measurement) |
| 5 | **`medkit_hud_monitor` full 2048-entity table scan** | `medkit.scr:103-115`, loop `:22`, started per player `player.scr:1076` | **server frame time** | every 5 s, **per player**, `while(local.si < local.maxent)` over `maxentities` = 2048 `getentbyentnum` calls with **no yield**. 8 players = 8 independent 2048-iteration scans. Fires in the common resting state (full health, <2 medkits). **The mod already builds the cached list this needs** — `coop_scan_health_entities` at `medkit.scr:522` | cadence measured, CPU cost est. |
| 6 | **`coop_corpseLife 0` — corpses never despawn** | `autoexec.cfg:357`, `corpse.scr:13` | entity pool + snapshot entities | every AI killed stays a networked entity for the whole map. Compounds with count-scaling and officer waves against the 2048 pool whose overflow is `ERR_DROP` | measured (it is a config default) |
| 7 | **File I/O on the server thread, on a kill-driven event** | `challenges.scr:993` → `chal_save_player` (`:842-843`) **and** `chal_pin_save` (`:2988-2989`) | **server frame time** | **2 synchronous `fs_write_content` every time any player completes any challenge.** `chal_flush` writes 2 files per player every 30 s (16 writes at 8 players) *and* launches the 8 concurrent exports of §5a in the same tick. A listen host's `Com_ModifyMsec` clamp is 200 ms (`common.c:2211`), so a bad stall loses simulation time outright | sites measured, per-write cost est. |
| 8 | **XP gain-popup per-frame CGM loop** | `xp.scr:952-1012`, `waitframe` at `:1011` | CGM bandwidth | 3 × `ihuddraw_rect` (79 bits) + `ihuddraw_alpha` (23 bits) = **32.5 B/frame/player → ~1.3 KB/s/player**, ~10 KB/s at 8. Window is `level.time + 3` refreshed at every 100-XP boundary (`xp.scr:460`), so in sustained combat it is effectively always on. No overflow risk (37 B vs the 4096 cap) but it is the largest steady CGM stream | measured |
| 9 | **Four always-on per-player `waitframe` loops** | `dbno.scr:87-152`, `ads.scr:16-37`, `thirdperson.scr:8-35`, plus level-wide `player.scr:42-176` | **server frame time** | 3 threads per player + 1 global, all at 40 Hz. At 8 players ≈ **1000 script thread resumptions/sec** before any gameplay | cadence measured, cost est. |
| 10 | **`getcvar` inside the per-frame DBNO loop** | `dbno.scr:101` | server frame time | 40 Hz × 8 players = **320 cvar lookups + string→int per second**, all returning the same value. Trivially hoistable above `:87`. `aihandler.scr:294-300` already does exactly this hoist, with a comment explaining why | measured |
| 11 | **`setcvar` per XP award** | `xp.scr:469` | server frame time | 2 string concatenations + a cvar set per award, and bonuses are separate awards (`:485-490`), so several per kill | measured |
| 12 | **Build-mode HUD, 6 long strings every 0.15 s, no diff gate** | `buildmode.scr:919-950` | CGM bandwidth | ~440 B/tick → ~2.9 KB/s + 6 string concats. Dev/host-only (`coop_build 1`), so low priority — but it is the clearest example of the anti-pattern | measured |

**What the sweep found to be *already correct*, and should not be touched:**

- **AI count-scaling is well-behaved** (`aihandler.scr:226-243`): staggered `wait 0.2` per replica, a hard cap checked per iteration, and it deliberately reuses the original's head model/skin (`:218-222`, `:252-257`) so a clone never mints a new `CS_MODELS` configstring — i.e. never spends a reliable slot. That is precisely the right mitigation.
- **Gore is entirely engine-side.** No script-spawned decals, blood entities or trails exist. The one script-side cost is a corpse `loopsound` at `gurgle.scr:104-108`, already capped at 5 and range-gated to 900 u.
- **`coop_track_marker` (`officer.scr:3878`) is dead code with no callers** — the overhead icon moved to a cgame `RT_SPRITE` (`officer.scr:1281-1283`). That migration removed a `script_model` per wave actor with a 20 Hz origin update. Large win, already banked.
- **`blueprint.scr` and `helmet.scr` are the best-behaved bursts in the codebase**: `waitframe` every 8 pieces / 1500 ops, and `helmet.scr:1424-1500` is diff-only with a generation stamp.
- **Steady-state HUD loops are diff-gated** (`medkit.scr:22`, `cover.scr:123`, `ammobox.scr:113`) — they emit only when the value changes. Correct, and free at rest.
- **`objectives.scr:496-505`/`:648-655`** issues 120 CGM calls in one frame but is diff-gated by a state signature (`:639`), and `coop_objPanel` defaults to 0 (`autoexec.cfg:950`), so it is normally inert.
- **No broadcast print fires per kill.** 242 `iprintlnbold`, 105 of them in `officer.scr`, all one-per-wave-event; most diagnostics are behind `level.cMTE_*` gates. The `iprintln` risk I expected is **not** present in this codebase. The 1554 `println` are console-only (no network cost).

**One caution for the currently-disabled AI systems.** `aibehav.scr:20`, `aicombat.scr:62`, `aimaneuver.scr:39` and `aisquad.scr:28` each evaluate **1-2 `getcvar` calls in the `while` condition itself**, so the cost lands the moment those cvars are turned on. `aisquad.scr:43-62` is additionally **O(N²)** over the AI set every 1.7 s. These are free today only because they are off.

**Two entities that bypass all culling and are worth auditing in the mod:** anything with `SVF_BROADCAST` or `SVF_SENDONCE` is sent to every client unconditionally (`sv_snapshot.c:735-738`), and any entity with a level-wide loop sound or `RF_ALWAYSDRAW` is sent regardless of PVS (`sv_snapshot.c:760-764`). These skip the PVS test, the area test and the distance cull. A handful is fine; a hundred is a permanent tax on every snapshot to every client.

**What *is* culled:** coop runs `g_gametype 2`, so the distance cull at `sv_snapshot.c:776-786` **is** active (it is skipped only in `GT_SINGLE_PLAYER`). Entities beyond `sv.farplane` (clamped to 12000 units, `:779-780`) and outside a generous forward cone are dropped. So map-wide entity count matters much less than *locally dense* entity count.

---

## 6. Q5 — Hard limits, and how close we are

| Limit | Value | Defined at | Enforced at | At the ceiling | Headroom today |
|---|---|---|---|---|---|
| `MAX_SNAPSHOT_ENTITIES` | 2048 | `server/sv_snapshot.c:285` | `:538` | **silent discard** + one-shot `Com_Printf` (`:549`) | Structurally unreachable — dedup means at most `MAX_GENTITIES` distinct numbers can land in one snapshot. **Not a live risk.** |
| `MAX_ENTITIES_IN_SNAPSHOT` (cgame) | 2048 | `cgame/cg_public.h:41` | `client/cl_cgame.cpp:208-211` | **silent truncation**, `Com_DPrintf` only | matches server. fine |
| `MAX_PARSE_ENTITIES` (client ring) | 8192 | `client/client.h:98` | `cl_cgame.cpp:185-187` | snapshot silently unavailable | 4 max snapshots of headroom. fine |
| `MAX_GENTITIES` / pool | 2048 (`GENTITYNUM_BITS` 11) | `qcommon/q_shared.h:1667-1668` | `fgame/level.cpp:1733`, `:1744` | **`ERR_DROP` "Level::AllocEdict: no free edicts"** | m2l2a spawns 489 at load; +80 scaled AI, +officer waves, +corpses, +gore, +dropped items. **This is the one that will bite.** No compile-time guard ties the `maxentities` cvar to `MAX_GENTITIES` — only the runtime clamp. |
| `MAX_MSGLEN` — snapshot | 131072 | `qcommon/qcommon.h:270` | `sv_snapshot.c:1288-1291` | **whole snapshot discarded**, `"WARNING: msg overflowed for %s"` | vast. Only reachable via a huge reliable backlog (see coupling below). |
| `MAX_MSGLEN` — gamestate | 131072 | same | `server/sv_client.c:869-873` | **`ERR_DROP`** + a 75% early warning (`:876-879`) | the warning is already wired; watch it at map load |
| `MAX_RELIABLE_COMMANDS` | 1024 | `qcommon/qcommon.h:215` | `sv_main.c:196-210` | **client kicked** — `"Server command overflow"` | **~514 measured at m1l1 spawn** (`qcommon.h:208-210`) = **50% used at the worst moment**. This is the tightest real limit. |
| `MAX_CONFIGSTRINGS` | 8192 | `q_shared.h:1787` | `sv_init.c:81-83` (`ERR_DROP`) | `ERR_DROP` both sides | `CS_MAX` = 3994 (`fgame/bg_public.h:127`) → ~4200 spare. comfortable |
| Configstring *pool* (per block) | `MAX_SOUNDS` 1600 etc. | `q_shared.h:1742` | `sv_init.c:192-197` | **returns slot 0** (= no sound/model) + yellow `Com_Printf` | 1600 covers the 179 distinct sounds that were being dropped at 1280. some headroom |
| `MAX_GAMESTATE_CHARS` | 98304 | `q_shared.h:1805` | `client/cl_parse.cpp:578-579` | **`ERR_DROP` on the CLIENT at connect** | ~75% of `MAX_MSGLEN`. Raising `MAX_SOUNDS` further spends this. |
| `SOUND_INDEX_BITS` | 11 → cap 2048 | `q_shared.h:1749` | compile-time `#error` at `:1750-1752` | **silent bit truncation** if the guard were removed | 1600/2048. guarded |
| `CMD_BACKUP` | 128 | `cgame/cg_public.h:35` | `cl_cgame.cpp:92-96` | roll-off; drives the phone-jack icon | at `com_maxfps 180` that is 0.7 s of history. fine |
| `PACKET_BACKUP` | 32 | `qcommon/qcommon.h:195` | `sv_snapshot.c:140-145` | delta abandoned → **full uncompressed snapshot** | effective delta window 29 frames. A 160 ms fragment stall at 40 Hz burns 6 of them — survivable, but two stacked stalls force a full snapshot, which is itself larger and more likely to fragment. **This is a positive-feedback loop.** |
| `MAX_PACKET_USERCMDS` | 32 | `qcommon/qcommon.h:199` | `cl_input.cpp:1163-1167` / `sv_client.c:1880-1883` | client clamps + prints; **server ignores the whole move packet** | at `com_maxfps 180` and `cl_maxpackets 30`, a client generates ~6 cmds per packet. fine. At 180 fps with `cl_maxpackets 30` and a 33 ms gap it is 6; only a >500 fps client would approach 32. |
| `FRAGMENT_SIZE` (remote) | 1300 | `qcommon/net_chan.c:50-52` | `net_chan.c:395` | fragments; **snapshots suppressed while pending** (`sv_snapshot.c:1324`); the overflow queue is an **unbounded** heap list (`sv_net_chan.c:228-246`) | **crossed routinely in firefights.** This is the most under-appreciated limit in the set. |
| `rate` | 1000-90000, **default 3000 if the client sends no key** | `sv_client.c:1553-1568` | `SV_RateMsec`, `sv_main.c:1352-1388` | snapshot skipped, `SNAPFLAG_RATE_DELAYED` | stock client advertises 25000 (`client/cl_main.cpp:4120`). **Binding under load.** |
| `MAX_CLIENTS` | 64 | `q_shared.h:1654` | `sv_init.c:426-430` | silent clamp | coop uses 4-8. fine |
| CGM buffer | 4096 B / client / snapshot | `server/sv_game.c:135` | `:182-189` | **silent drop**, `Com_DPrintf` 1×/5 s | unmeasured. Given how much `huddraw` this mod does, **measure it.** |

**Two couplings to keep in front of you:**

1. Reliable backlog → snapshot size. `SV_UpdateServerCommandsToClient` re-writes every unacked command into every snapshot (`sv_snapshot.c:253`). So a reliable backlog inflates snapshots, which fragments them, which suppresses snapshots, which stops the acks, which grows the backlog. **This is a runaway.** The 1024 kick threshold is the *end* of that spiral, not its start.
2. Every post-gamestate configstring set costs one reliable slot. That is why `MAX_SOUNDS` and `MAX_RELIABLE_COMMANDS` are chained (`q_shared.h:1715-1732`), and it is why officer waves — which register new models and sounds mid-map — are a *reliable-queue* event, not just an entity event.

**One latent hazard found while reading, currently unreachable:** `cgm_t.datatypes` is `Z_Malloc(CGM_DATA_SIZE)` = 4096 bytes (`sv_game.c:148`) but is bounds-checked against `CGM_DATATYPES_SIZE` = 8192 (`sv_game.c:186`) before being written at `datatypes[dtindex]` (`:211`). It is safe today only because every datum also costs at least one byte of `data`, so the `cursize` check at `:182` always trips first. **Anyone who raises `CGM_DATA_SIZE` without also fixing that `Z_Malloc` gets a 4 KB heap smash.** Worth a one-line fix (`Z_Malloc(CGM_DATATYPES_SIZE)`) purely as a trap remover.

---

## 7. Q6 — Rate, snaps, packets: what to ship

### What is shipped today

| cvar | engine default | shipped by the mod | where |
|---|---|---|---|
| `sv_fps` | 20 (`server/sv_init.c:1108`) | **40** | `autoexec.cfg:668` |
| `snaps` | 20 (`client/cl_main.cpp:4121`) | **40** | `autoexec.cfg:669` |
| `rate` | 25000 (`cl_main.cpp:4120`) | **not set anywhere** | — |
| `cl_maxpackets` | 30, clamped [30,125] (`cl_main.cpp:3979`, `cl_input.cpp:1077-1081`) | **not set anywhere** | — |
| `sv_maxRate` | 0 (`sv_init.c:1078`) | **not set** on the normal path | — |
| `sv_lanForceRate` | 1 (`sv_init.c:1133`) | not set | — |
| `com_maxfps` | 85 (`common.c:1910`) | **180** | `autoexec.cfg:657` |
| `r_swapInterval` | — | **1** | `coop_defaults.cfg:74` |

`coop_mod/start_server.cfg` — the actual host-start path, exec'd by the menu's Apply — touches **none** of the network cvars.

### The live trap: the "Load HZM Coop-Network-Server Configuration" button

`ui/coop_start.urc:399` wires a button to `stuffcommand "exec net_sv.cfg"`. Its title reads as an optimisation. What it actually does (`net_sv.cfg`):

```
set sv_fps 20;         // undoes autoexec's 40
set snaps 20;          // undoes autoexec's 40
set sv_maxRate 18000;  // hard-caps EVERY client below the engine default rate
set rate 14000;        // ~10 snapshots/sec once snapshots exceed 1400 bytes
set cl_timenudge 10;   // +10 ms of deliberate render latency
set cl_packetup 0;     // typo - the cvar is cl_packetdup; this line does nothing
```

`net_cl.cfg` (wired to a matching button at `ui/joininternetgame.urc:110`) sets the same client half.

These were sensible in ~2003 on a 56k-to-DSL population. Today they are a **net downgrade of every single network parameter the mod otherwise ships**, delivered through a button whose label promises the opposite. `sv_maxRate 18000` in particular is applied inside `SV_RateMsec` (`sv_main.c:1360-1366`) and caps every client regardless of their own `rate`. At 18000 B/s a 1400-byte firefight snapshot can go out at most **12.8 times per second**.

*(Also note `sv_main.c:1363` does `Cvar_Set("sv_MaxRate", "1000")` — capital M — which creates a second, unread cvar rather than clamping `sv_maxRate`. Harmless in practice since it only fires below 1000, but it is a real bug.)*

### Recommended shipped defaults, 2-8 players, home-hosted listen server

| cvar | recommend | why |
|---|---|---|
| `sv_fps` | **40** (keep) | 25 ms tick. Matches the interpolation need for vehicle riders that motivated it. 60 would be better for riders but multiplies snapshot count by 1.5 against a `rate` budget that is already the binding constraint — do not raise it until `rate` is fixed. |
| `snaps` | **40** (keep) | server clamps it to `sv_fps` anyway (`sv_client.c:1586-1587`) |
| `rate` | **60000** (from 25000) | This is the highest-leverage single number in the whole document. At 60000 a 1400-byte firefight snapshot costs 24 ms → 40/sec sustainable. Engine clamp is 90000 (`sv_client.c:1562-1563`); 60000 leaves margin and is honest for a home *host's upstream* (4 clients × 60 KB/s = 1.9 Mbit/s up, worst case, and real average is far below). Ship in `coop_defaults.cfg` so a player's menu choice can still override it. |
| `cl_maxpackets` | **60** | halves the remote player's input send quantisation from 33 ms to 17 ms. Costs ~2 KB/s upstream per client. The engine floor is 30 and the ceiling 125 (`cl_input.cpp:1077-1081`). |
| `sv_maxRate` | **0** (keep — and stop `net_sv.cfg` from setting 18000) | a host on a thin uplink should set this deliberately; it must not be a hidden default |
| `sv_minRate` | **0** (keep) | |
| `sv_lanForceRate` | **1** (keep) | gives LAN clients 99999 and bypasses the rate gate entirely (`sv_client.c:1553-1554`, `sv_snapshot.c:1332-1333`) |
| `cl_timeNudge` | **0** (keep; stop `net_cl.cfg` setting 10) | positive nudge subtracts from `cl.serverTime` (`cl_cgame.cpp:1272`) = deliberately render further in the past. It buys interpolation robustness at the cost of latency. Clamped to ±30 (`:1266-1270`). Leave it as a *player* knob for bad connections, not a shipped default. |
| `com_maxfps` | **180** for a client; see L2 for a host | |
| `r_swapInterval` | **1** for a client, **0 for a host on a ≤60 Hz display** | §4 |

**Bandwidth sanity check at the recommendation:** 4 clients × 40 snapshots/sec × ~700 B average = **112 KB/s ≈ 0.9 Mbit/s upstream** from the host in steady state, peaking to ~1.8 Mbit/s in a heavy firefight. That is well inside any modern home connection and roughly 4× what the shipped `net_sv.cfg` would allow.

---

## 8. The plan

Ordered by (expected effect) / (risk × effort). Tags: **[L]** helps the listen host, **[D]** helps dedicated, **[B]** both.

### Tier 0 — a live client-disconnect bug; fix before anything else

**T0.1 [B] Stop `chal_ui_export` from filling the reliable ring.** *(`coop_mod/challenges.scr` — currently owned by another workstream; hand this over rather than editing it here.)*

The problem is 996 commands against a 1024 ring (§5a). Three fixes, in order of preference:

1. **Diff-gate it.** Track the last-exported value per row per player and emit only rows that changed. In steady play almost nothing changes in 30 s, so a flush becomes a handful of commands instead of 996. `helmet.scr:1424-1500` already implements exactly this pattern (generation stamp + diff-only + 8-per-frame pacing) and is the in-repo template.
2. **Re-pace to the real catalogue size.** The `8 per waitframe` at `:879` was tuned for 61 commands and is now driving 996. Even without diffing, dropping to 2 challenges (6 commands) per `waitframe` cuts the queue-growth rate from ~960/sec to ~240/sec, which keeps unacked well inside one fragment. Costs ~4 s of wall time for a background job nobody is waiting on.
3. **Serialise across players.** `chal_flush:857` uses `thread`, so all players export concurrently. `waitthread` (or a small stagger) would at least stop N players' exports stacking in the same frames.

Do (1) and (3); (2) is the safety net if (1) turns out to be fiddly. Also **fix the stale comment at `:867-869`** — a comment that names a number 16× smaller than reality is how this survived.

- Effect: removes the only mechanism in the mod that can disconnect a player, and removes a 30-second periodic snapshot-fragmentation storm from every session.
- Risk: **low.** The export writes archived client cvars for the disconnected Service Record menu; a diff gate cannot lose data as long as the first export after connect is unconditional.
- Verify: `developer 1` + a remote (non-loopback, non-LAN) client; watch for `"Server command overflow"` and for the `"===== pending server commands ====="` dump that precedes it (`sv_main.c:203`). With T3.2's probe, peak unacked should stay under ~50 across a flush.

**T0.2 [B] Audit the same pattern elsewhere.** `chal_review` (`challenges.scr:2225`/`:2281`) emits ~340 reliable commands paced at `wait 0.03` — that one is *fine as written* and its comment at `:2278` shows the author knew about the buffer. The loadout registry's ~140 stufftexts at spawn (`qcommon.h:209`) plus mid-map sound registrations plus a badly-timed `chal_flush` can still stack. **T3.2 (the reliable-queue probe) is what makes this auditable rather than guessable** — build it with T0.1, not after.

### Tier 1 — no engine change, large effect

**T1.1 [B] Raise `rate` and `cl_maxpackets`.**
- Change: add `seta rate 60000` and `seta cl_maxpackets 60` to `coop_defaults.cfg` (**not** `autoexec.cfg` — per the shipped configuration contract, `coop_defaults.cfg` is exec'd *before* the saved player config so it is a true default a player can still override and persist; `autoexec.cfg` runs *after* and would stomp the player's menu choice every launch).
- Effect: removes the rate gate as the binding constraint in firefights; roughly doubles usable snapshot throughput under load and halves remote input quantisation.
- Risk: **low.** Both are per-client and clamped by the engine. A host on a genuinely thin uplink can still set `sv_maxRate`.
- Verify: `netprofiledump` (`server/sv_ccmds.c:2044`) before and after on the same fight; count `SNAPFLAG_RATE_DELAYED` frames; watch the lagometer.

**T1.2 [B] Neutralise `net_sv.cfg` / `net_cl.cfg`.**
- Change: either rewrite both files to the §7 recommended values, or remove the two buttons (`ui/coop_start.urc:399`, `ui/joininternetgame.urc:110`). Rewriting is better — the buttons are discoverable and a player who found one will find it again.
- Effect: closes a live regression path that silently reverses `sv_fps`, `snaps`, `rate` and `sv_maxRate` in one click.
- Risk: **very low.** These files are exec'd from nowhere else.
- Verify: click the button, then `sv_fps` / `rate` / `sv_maxRate` at the console.

**T1.3 [L] Stop rendering at vsync when hosting on a low-refresh display.**
- Change: in `coop_mod/start_server.cfg`, when the local machine is going to host, set `r_swapInterval 0` and cap `com_maxfps` at a value the machine reliably sustains (e.g. `com_maxfps 120`). Do **not** put it in `autoexec.cfg` — it must apply to hosts, not joiners.
- Effect: on a 60 Hz host this alone can be the difference between a 16.7 ms and a 33.3 ms loop period, i.e. between 60 and 30 snapshots/sec, and between the slow-server icon being off and permanently on.
- Risk: **low**, but it is a visible change (tearing). Make it a host-menu toggle rather than unconditional if the user objects to tearing.
- Verify: `sv_lagProbe 1`, compare `^~^~^ SVFRAME worst/mean/over` between `r_swapInterval` 0 and 1 on the same map and viewpoint.

**T1.4 [B] Cheap script fixes with no design change.** *(all in `coop_mod/` — hand over, do not edit here)*
- **`coop_corpseLife`**: set it non-zero. Today `0` means corpses persist for the whole map (`autoexec.cfg:357`, `corpse.scr:13`), which is the largest single contributor to entity-pool occupancy against a limit whose overflow is `ERR_DROP`. The project notes record `0` as a deliberate user preference, so **ask before changing it** — but the alternative (a distance/age cull that keeps nearby corpses) preserves the look and bounds the count.
- **`medkit.scr:103-115`**: replace the 2048-entity `getentbyentnum` scan with the cached `level.coop_health_ents` list that `coop_scan_health_entities` (`medkit.scr:522`) already builds for this exact purpose. Removes 8 × 2048 unyielded iterations per 5 s at 8 players.
- **`dbno.scr:101`**: hoist the `getcvar "coop_dbnoThreshold"` above the `waitframe` loop at `:87`. 320 redundant lookups/sec at 8 players. `aihandler.scr:294-300` is the in-repo precedent.
- **`officer.scr:1964-2007`**: add a `waitframe` every 4-6 spawns in the battalion loop. 22 entities + ~220 thread creations in one frame is both a frame spike and a guaranteed snapshot-fragmentation event. `blueprint.scr` already does exactly this pacing.
- **`buildmode.scr:919-950`**: diff-gate the six strings. Dev-only, so low priority, but it is a one-line pattern.
- Effect: removes the two worst CPU spikes and the worst spawn burst; bounds entity growth.
- Risk: **low per site**, but it touches `coop_mod/`, owned by another workstream — sequence it accordingly.
- Verify: `sv_lagProbe 1` `^~^~^ SVFRAME worst` before/after on an officer fight; `EDICTHI` tracing (`fgame/level.cpp:1754-1759`) for the corpse change.

**T1.5 [B] Move gameplay-event file I/O off the server thread's critical path.**
- Change: `challenges.scr:993` does **two** synchronous `fs_write_content` calls every time any player completes any challenge — a kill-driven event. Debounce: mark dirty, write on the existing 30 s flush / mission complete. `xp.scr:1538` (60 s loop) is already correct and is the model.
- Effect: removes a synchronous disk write from combat.
- Risk: **low**, with one real trade — a crash loses up to 30 s of challenge progress. That is already true of XP.
- Verify: `sv_lagProbe 1` while deliberately completing challenges in a fight.

### Tier 2 — engine changes, contained, high value

**T2.1 [L] Decouple the render from the main loop.** See §9 for the full verdict and design. This is the headline item.

**T2.2 [B] Make the "slow server" test measure the right thing.**
- Change: `server/sv_main.c:1135`. Today `sv_fps * msec > 1100` conflates "the host's render frame was long" with "the server is behind". Replace with a metric that is true on both topologies: measure the wall time of the `while (sv.timeResidual >= frameMsec)` block (i.e. how long `ge->RunFrame` actually took) and/or whether `sv.timeResidual` exceeded one full tick *after* the drain loop. Keep the 2500 ms broadcast rate limit.
- Effect: the icon becomes trustworthy. Today a listen host at 31 fps lights it permanently even though the simulation is perfect, which trains everyone to ignore it — and then it cannot warn about a real stall.
- Risk: **low.** Server-side only, no wire change; `svlag` is already a reliable command the cgame handles at `cgame/cg_servercmds.c:426`.
- Verify: it should go quiet on a healthy listen host at 31 fps and still fire when a script does 200 ms of work in one tick.

**T2.3 [B] Drain more than one fragment per loop iteration.**
- Change: `SV_SendQueuedMessages` (`server/sv_client.c:1254-1276`) sends at most one fragment per client per call, and `Com_Frame`'s idle loop (`common.c:2325-2343`) may call it only once when there is no slack. Let it loop while `SV_RateMsec(cl) == 0` and fragments remain, bounded by a small per-frame cap (say 4) so it cannot starve the rest of the frame.
- Effect: turns a 3-fragment snapshot from a ~3-frame blackout into a ~1-frame one, when the rate budget allows. Composes with T1.1 — at `rate 60000` the rate budget usually *does* allow it.
- Risk: **medium.** Fragment ordering and the terminating zero-length fragment (`net_chan.c:370-373`) must be preserved; the rate accounting must still be honoured per fragment or a client on a thin link gets flooded. Needs care, but the change is local.
- Verify: `netprofiledump` `percentFragmented`; measure the gap between consecutive `serverTime` values a client sees during a spawn burst.

**T2.4 [B] Fix the `cgm_t.datatypes` allocation.**
- Change: `server/sv_game.c:148`, `Z_Malloc(CGM_DATA_SIZE)` → `Z_Malloc(CGM_DATATYPES_SIZE)`.
- Effect: none today (unreachable, §6), but it removes a 4 KB heap smash that arms itself the moment anyone raises `CGM_DATA_SIZE` — which T1.4/T3.1 might well want to do.
- Risk: **none.** +4 KB per client.
- Verify: compile and run; it is a pure allocation size.

### Tier 3 — instrumentation, so the next decision is measured

**T3.1 [B] Snapshot-size probe.** Add a cvar-gated per-second report in `SV_SendClientSnapshot` (`sv_snapshot.c:1240`) printing, per client: mean/worst `msg.cursize`, count of snapshots over `FRAGMENT_SIZE`, count skipped by each of the four gates, and CGM bytes written. Model it on the existing `sv_lagProbe` block (`sv_main.c:1163-1187`) — same shape, same `^~^~^` prefix so `maptest_monitor.ps1` can parse it. **This is the missing instrument.** Every "est." in §5 becomes a number.

**T3.2 [B] Reliable-queue depth probe.** Report `reliableSequence - reliableAcknowledge` peak per client per second. The kick threshold is 1024 and the measured spawn peak is ~514 — the project is running at 50% of a limit whose failure mode is a client kick, with no visibility between "fine" and "disconnected".

**T3.3 [L] Host-loop probe.** Report the main-loop period distribution separately from `ge->RunFrame` time, so "the GPU is slow" and "the script did too much" stop looking identical. T2.2 needs this split anyway.

### Tier 4 — larger, only if Tiers 1-3 are not enough

**T4.1 [L] "Host dedicated + auto-connect" as a first-class option.** Launch `omohaaded.exe` as a child process and connect the local client to `127.0.0.1`. Zero engine change; the server loop then runs at exactly `sv_fps` by construction (`common.c:2298-2299`) and is completely immune to the host's GPU. Costs a second process's memory. Given that bugs 1664 and 1667 just made the dedicated path work properly, this is now a realistic ship — it needs a UI button and process management, not engine work.

Two properties worth noting. (a) The host's connection is no longer `NA_LOOPBACK` but a real UDP socket, which `Sys_IsLANAddress` treats as LAN — so with `sv_lanForceRate 1` the host still skips the rate gate (`sv_snapshot.c:1332-1333`) but **now fragments at 1300 bytes like everyone else** (`net_chan.c:52`). That removes the blind spot that hides §5a and item 3 of §5b from the person doing the testing, which is arguably worth more than the performance gain. (b) It removes the §3 input asymmetry, which is *correct* for a coop mod even though it makes the host's own experience marginally worse.

**T4.2 [B] Lag compensation.** There is none (§3). This is the only way to close the host-advantage gap properly. It is a large, invasive change (per-client position history, backward reconciliation in the trace path) and it is *not* justified by coop's requirements — AI are not other players, and 40-50 ms of lead is playable. **Recommend: do not build this.** Recorded here so the option is explicitly rejected rather than forgotten.

**T4.3 [B] Raise `sv_fps` to 60.** Only after T1.1 lands and T3.1 confirms the snapshot budget. It would improve interpolated riders further (the reason `sv_fps` went to 40 in the first place, per `autoexec.cfg:660-667`) but multiplies snapshot count by 1.5 against `rate`. **Measure first.**

---

## 9. Verdict: decoupling the server tick from the render frame

**Verdict: yes, do it — but decouple the *render*, not the *server*, and do it in-process.** It is the right call, the correct diagnosis of the listen-server problem, and it is a much smaller change than it sounds.

### Why it is the right diagnosis

The listen server is not slow. Its simulation is exact and on time (§1a). Its one defect is that `SV_Frame` — and therefore `SV_SendClientMessages` and the inbound `NET_Sleep`/`Com_EventLoop` drain — is called once per render, and the render blocks on the GPU and the vblank. Fix the coupling and the listen server delivers at `sv_fps` regardless of framerate. That is precisely the property that made the dedicated server measure better; there is nothing else dedicated does differently.

### The three ways to do it, evaluated

**Option A — separate server thread.** `SV_Frame` on its own timer in its own thread.
**Rejected.** The blast radius is the whole engine. `ge->RunFrame` reaches the Cvar system, the Zone/Hunk allocators, the filesystem, the console, the TIKI cache and the script VM, none of which are thread-safe. `Com_Error` uses a process-global `setjmp(abortframe)` at `common.c:2259` that is not thread-scoped. Sockets are shared between `SV_SendClientMessages` and the client's `NET_Sleep`. And the listen host's own cgame reads server state through the loopback netchan *and* through direct calls. This is a multi-month rewrite with an unbounded crash surface, in a codebase that is already carrying ~10,700 uncommitted engine lines. **No.**

**Option B — gate the render, free-run the loop. ← recommended.**
The loop already *wants* to run at `com_maxfps` (`common.c:2306-2307`, `minMsec = 1000/com_maxfps` = 5 ms at 180). The only thing holding it to render rate is `SCR_UpdateScreen()` at `client/cl_main.cpp:2868`. Add a render-due clock, and skip that one call when it is not time to draw:

```
in Com_Frame: minMsec = min(1000/com_maxfps, SV_FrameMsec())   // wake for whichever is due
in CL_Frame:  if (render is due)  SCR_UpdateScreen();          // <-- the only new gate
```

Everything else in `CL_Frame` keeps running at loop rate and *should*: `cls.realtime += cls.frametime` (`cl_main.cpp:2799`) is the client's clock and must stay continuous; `CL_SendCmd` (`:2843`) produces the host's usercmds — running it at 200 Hz is fine, `CMD_BACKUP` 128 still gives 0.64 s of history and `MAX_PACKET_USERCMDS` is not approached on loopback; `CL_SetCGameTime` (`:2852`) is cheap. `S_Update` (`:2871`) can stay at loop rate or be gated with the render — either works, gate it if profiling says it costs.

Note that `CG_ProcessSnapshots` runs *inside* `SCR_UpdateScreen` (via `CG_DrawActiveFrame`), so skipping the render also skips the local client's snapshot processing. That is correct and desirable — the local client only needs a world state when it draws one.

**Blast radius: small and enumerable.**
- Files: `qcommon/common.c` (`minMsec`), `client/cl_main.cpp` (one gate around `:2868`). Two files, ~15 lines.
- **No wire-format change.** No `exe + cgame + game + renderer` ship discipline required (`ENGINE.md § Protocol coupling` does not apply). Server-and-client-exe only.
- Behaviour when `!com_sv_running` (a pure client) must be unchanged — gate the whole thing on `com_sv_running && !com_dedicated`.
- Risks to check: (1) `com_frameTime`/`cls.realtime` divergence — both already advance from the same `msec`, so they stay consistent; (2) input sampling — `IN_Frame()` (`common.c:2345`) runs per iteration, so mouse sampling *improves*; (3) the `bias` frame-pacing corrector at `common.c:2311-2319` assumes one render per iteration and will need re-basing onto the render clock or the rendered frame pacing gets uneven — **this is the one genuinely fiddly part**; (4) demo recording and `cl_aviFrameRate` (`cl_main.cpp:2742-2752`) assume frame == render.

**What it buys, honestly.** With vsync on and a GPU-bound scene, the *maximum* gap between `SV_Frame` calls is still one render duration — the swap still blocks. What changes is the *distribution*: instead of every server frame being 32 ms apart, most are 5 ms apart with one 32 ms gap per rendered frame. Concretely at a 31 fps host:

| | today | with Option B (`com_maxfps 180`) |
|---|---|---|
| `SV_Frame` calls/sec | 31 | ~180 |
| snapshot send opportunities/sec | 31 | 40 (i.e. `sv_fps`-limited, as designed) |
| inbound usercmd read interval | 32 ms | 5.5 ms |
| fragment drain opportunities/sec | 31 | ~180 |
| worst gap | 32 ms | 32 ms *(unchanged — the swap still blocks)* |

Pairing it with T1.3 (`r_swapInterval 0` + a sustainable `com_maxfps`) is what shrinks the worst gap too. **Option B and T1.3 are complements, not alternatives.**

**Option C — drive only `SV_SendClientMessages` from a timer, leaving the sim where it is.** Rejected as strictly worse than B: it must still run after the sim, it does nothing for inbound usercmd latency or fragment draining, and it needs the same loop-rate change to be callable more often anyway. All of B's cost, a fraction of its benefit.

### Recommendation

Order: **T0.1** (the disconnect bug — it is not a performance item, it is a defect), then **T1.1 + T1.2 + T1.3** (no engine change; T1.1 is the largest single performance win in the document), then **measure with T3.1 + T3.2**, then land **Option B (T2.1)**. If T3.1 shows fragmentation is the dominant stall — which I expect on busy maps, and which T0.1 and T1.4's officer-spawn pacing both attack from the content side — land **T2.3** with it.

Note the ordering is not arbitrary: **T0.1 and T1.1 both reduce the pressure that T2.1 would otherwise have to absorb.** Landing the engine change first would make the script bug harder to see, not easier.

Hold **T4.1** (dedicated + auto-connect) in reserve. It achieves the same decoupling with *zero* engine risk and is now viable thanks to bugs 1664/1667. If Option B's frame-pacing corrector turns out to be a rabbit hole, T4.1 is the escape hatch and is arguably the better long-term shape anyway.

---

## 10. Verification protocol

Nothing here should be believed without a measurement. The instruments that already exist:

| Instrument | Where | Gives you |
|---|---|---|
| `sv_lagProbe 1` | `server/sv_init.c:1109`; output `sv_main.c:1146-1187` | `^~^~^ SVFRAME worst/mean/over/budget` per second, `^~^~^ SVLAG` + per-client `ping`/`unacked`/`rate` at each broadcast |
| `netprofiledump` | `server/sv_ccmds.c:2044` | packets/sec in+out, `percentFragmented`, `percentDropped` per client |
| `sv_netprofile 1` / `cl_netprofile 1` | `sv_init.c:1127`, `cl_main.cpp:70` | feeds the above |
| gamestate size warning | `sv_client.c:876-879`, fires over 75% of `MAX_MSGLEN` | join-time headroom |
| `developer 1` | mandatory for CGM overflow, delta roll-off, cgame truncation — all `Com_DPrintf` | the silent failures |
| `cl_showTimeDelta 1` | `cl_cgame.cpp:1112-1114` | `<RESET>` / `<FAST>` / drift — a direct read on snapshot-arrival regularity |

**The measurement that settles the listen-vs-dedicated question properly** (and the one bug-1663 explicitly left open): run the *same* map, the *same* fight, with the *same* client count, three ways — (a) listen host alone on the machine, probes on; (b) listen host with a second instance, as previously measured; (c) dedicated + two clients. The earlier listen numbers came from two instances sharing one GPU, which the brief already flags as a likely artefact. Until (a) exists, "listen is worse than dedicated" is measured but not *attributed*.

**The test conditions matter more than the test.** The mechanisms that hurt are selectively disabled by the topology you are most likely to test on:

| | fragmentation (1300 B) | rate gate | RTT-driven ack delay |
|---|---|---|---|
| **loopback** (listen host's own client) | **no** — `FRAGMENT_SIZE` 9900 (`net_chan.c:52`) | **no** — bypassed (`sv_snapshot.c:1332`) | ~0 |
| **LAN**, `sv_lanForceRate 1` (default) | **yes** | **no** — `rate` forced to 99999 (`sv_client.c:1553-1554`) | ~1 ms |
| **internet** | yes | yes | 20-150 ms |

So: **a listen host testing alone reproduces none of it**; a LAN test reproduces fragmentation but not the rate gate and not the ack delay that drives the §5a spiral. To force the real path without an internet partner, set `sv_lanForceRate 0` and a low client `rate`, and consider `net_dropsim` (`qcommon/net_ip.c:1638-1642`) to add loss. **Do not accept "it works on my machine" as evidence for anything in this document.**

**Suggested acceptance criteria**, on a busy m2l2a firefight with 2 **remote** clients, across at least two 30 s `chal_flush` boundaries:
- Zero `"Server command overflow"` drops; peak `reliableSequence - reliableAcknowledge` under **100** including across a flush.
- `percentFragmented` under 10% (from whatever it is today).
- Zero `SNAPFLAG_RATE_DELAYED` frames in steady state.
- No `"CGM buffer for client %i overflowed"` lines with `developer 1`.
- Client-observed `serverTime` gaps: 95th percentile under 40 ms.
- `sv_lagProbe 1`: no `^~^~^ SVFRAME` line at all during normal play on a host that is rendering above ~40 fps.

---

## 11. Open questions

1. **Solo listen-host baseline does not exist.** Everything comparing listen to dedicated rests on a two-instances-one-GPU measurement (§10). Until a solo run exists, "listen is worse than dedicated" is measured but not *attributed*.
2. **Nothing here has been tested against a genuinely remote client.** See the box above — this is the single biggest gap in the evidence, and it is the condition under which every predicted failure actually fires.
3. **CGM byte volume per snapshot is unmeasured**, and its overflow is silent (`Com_DPrintf`, 1×/5 s, `sv_game.c:165-178`). The XP popup alone is ~1.3 KB/s/player against a 4 KB *per-snapshot* cap, so the average is fine — but the cap is per snapshot, and a rate-delayed client accumulates. Suspect this in any past "the HUD went stale / the objective didn't update" report that was diagnosed as a script bug.
4. **Entity-pool headroom on a long officer fight is unmeasured.** 489 at load on m2l2a, a pool of 2048, `coop_corpseLife 0` so nothing is reclaimed, and the failure mode is `ERR_DROP`. `EDICTHI` tracing already exists at `fgame/level.cpp:1754-1759` — turn it on for one long fight.
5. **`SVF_BROADCAST` / `SVF_SENDONCE` / level-wide-loopsound census in the mod** — these bypass PVS, area *and* distance culling entirely (`sv_snapshot.c:735-738`, `:760-764`) and are a flat tax on every snapshot to every client. Not swept.
6. **Per-iteration script CPU cost is judgement, not measurement**, so items 5, 9, 10 and 11 in §5b are argued rather than proven. The cheap settlement: comment out the `medkit.scr:103` scan block and the `ads.scr` / `thirdperson.scr` monitors and compare `^~^~^ SVFRAME mean` at 8 players.
7. **`sv_main.c:1363` sets `sv_MaxRate` (capital M) instead of `sv_maxRate`** — a real one-character bug that creates a second, unread cvar. Harmless today because it only fires below 1000, but it means `sv_maxRate 500` is silently *not* clamped to 1000.

---

## 12. REMOTE-CLIENT TEST RIG (added 2026-08-10, answers open question #2)

Open question #2 said nothing had been tested against a genuinely remote client, and that this is the
condition under which every predicted failure actually fires. It does not need a VPN or a second site.

**Recipe: a second PC on the LAN + two cvars.**

| step | why |
|---|---|
| second PC on the LAN | its netchan is `NA_IP`, not `NA_LOOPBACK`, so it gets `MAX_REMOTE_PACKETLEN` 1400 instead of loopback's 9900 (`net_chan.c:52`). This is the big one - it is what lets the snapshot-fragmentation feedback loop of bug-1670 actually happen. |
| `sv_lanForceRate 0` | **required.** `Sys_IsLANAddress` returns true for 10/8, 172.16/12 and 192.168/16 (`net_ip.c:717-729`), and `sv_lanForceRate` DEFAULTS TO 1 (`sv_init.c:1133`), so a LAN client otherwise bypasses the rate gate entirely (`sv_snapshot.c:1332`). Without this, LAN testing silently keeps one of the two blind spots. |
| `sv_packetdelay 60` | the engine simulates latency natively (`common.c:1925-1926`, queued in `net_chan.c:768`). Dial it to find where things break rather than hoping a real connection is bad enough. `cl_packetdelay` is the client-side equivalent. |

**A VPN is NOT a substitute.** Home VPNs (WireGuard, Tailscale, router built-ins) hand out tunnel
addresses inside those same RFC1918 ranges, so `Sys_IsLANAddress` still reports LAN and you land in
exactly the LAN case above - with less control over latency. A VPN only helps if traffic genuinely
exits to the internet and the client presents a public IP.

**What this rig can finally verify:** bug-1670's fix under real fragmentation; peak `unacked` across a
first export (should stay far under 1024 - it measured 402 on loopback); whether the phone-jack
indicator has a real cause or is a loopback artifact; and the actual snapshot rate a remote player
receives when the host dips below `sv_fps`.
