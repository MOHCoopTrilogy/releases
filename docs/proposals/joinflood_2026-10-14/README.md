# Remote join flood on the public dedicated servers (bug-3910, bug-3909, bug-3903) - investigation + fix

## HANDOVER (keep this current - the next session starts here)

- **Status (2026-10-14 15:35): fix PROVEN on the harness; HOLDING (coordinator: v1.10.24 deploy in progress, no game
  runs until told). No harness process running. Next: f3-listen against the released v1.10.24 files when told.**
- **!! SHIP WARNING: do NOT ship the exes from `openmohaa-hzm-joinflood\.cmake`** - that dir was configured with
  `USE_RENDERER_DLOPEN=OFF` (static renderer; openmohaa.exe 2.73 MB vs the release 1.90 MB). Cherry-pick 15732bb2
  (only `code/client/cl_net_chan.cpp` + the `code/server/*` byte window matter; the probes are default-off) into the
  tree/build dir that produced the release exes (`openmohaa-hzm\.cmake`, USE_RENDERER_DLOPEN=ON) and build
  `omohaaded` + `openmohaa` there. The harness client runs e1-f5 used the static-renderer exe (its network code is
  identical); the server exe (no renderer) is unaffected.
- **Root cause (short):** the client exe only sends the FIRST fragment of a client->server packet over ~1300 bytes,
  and every client packet re-carries all unacknowledged client commands. A join alone queues ~1.5 KB of them
  (two userinfo + pak checksums + the v1.10.23 progression handshake), and v1.10.23's upload adds ~520-byte chunks
  re-sent every 3 s. Once over the limit nothing the client sends reaches the server again: no usercmds
  (connection-interrupted icon), no acks (server queue grows: SVCMDQ), timeout after 120 s. The server side feeds
  it: join/merge bursts put up to 256 commands (21.5 KB) in every snapshot = 17 fragments, re-sent every frame.
- **Fix:**
  - engine `joinflood-next` (worktree `C:\mohaa-coop-dev\openmohaa-hzm-joinflood`, from e8838a89 = v1.10.23),
    commit 15732bb2: `cl_net_chan.cpp` sends every fragment; `sv_main.c` `sv_cmdParkBytes` 2400 = max bytes of
    reliable commands in flight to a remote client (rest parks, FIFO, nothing dropped; loopback exempt; 0 = old
    behaviour). Plus test instruments `sv_netProbe` / `cl_netProbe` (default 0). game.dll / cgame.dll UNCHANGED.
    Build: `.cmake` there, `cmake --build . --config Release --target omohaaded openmohaa --parallel 4`.
  - mod `joinflood-next` (worktree `C:\mohaa-coop-dev\hzm-mod-joinflood`, from coop-wip 7a5211a0), commit 84f71d6d:
    `coop_mod/lobby.scr` = the public servers' bug-3909 hot patch, in source (`tools/patch_lobby_src.py`).
- **Ships as:** `openmohaa.exe` (players + listen hosts) + `omohaaded.exe` (servers) + code pak (lobby.scr).
- **Harness:** `tools/run_joinflood.py` (G:\mohaa-hudfeed5 sub-folder `joinflood\`, slot hudfeed5 (+hudfeed4 for a 2nd
  client), 127.0.0.1 IPv4 only, ports 12791-12793, fake qkey ids with a veteran-sized record, `--usercfg` = a
  read-only copy of the user's client config so the userinfo is his). Runs moved to `H:\hzm_archive\joinflood\`.
  Variants: `--srv/--cl new|old|fix`, `--lobby stock|patched|fix`, `--parkbytes 0` = released server behaviour
  (the harness server exe is always the joinflood build; the kill switch makes it the release). `--clprobe` = the
  joinflood client exe (it includes the fragment fix since 15732bb2).

## Evidence from the public servers (read-only)

- The user's record on his PC: chal 3256 B, unlocks 2532 B, pend 1508 B (sizes only). The servers' copy for him
  is EMPTY: the upload never completed.
- srv2 13:02:46 / srv1 13:09:44: want at +11 s; in-flight commands climb from the start (no acks) -> SVCMDQ 512 at
  +78..93 s; upload timed out at +131 s; client timed out at +164 / +193 s (sv_timeout 120: last packet received
  ~30-60 s after joining). The name change at +41 s (`,0203`) is the mod's fov-report name bus = userinfo traffic.

## Runs (H:\hzm_archive\joinflood\<run>\, server log srv\maintt\qconsole.log, SVNET = 1 line/s)

| run | srv / cl | client cfg | result |
|---|---|---|---|
| a1_new_stock | 1.10.23 / 1.10.23 | harness cfg, fps 60 | OK. Upload 30 s. After the merge one burst: 256 in flight + 81 parked, a 21.5 KB snapshot (318 seta + 5 coopsave). |
| a2_new_fps200 | same | harness cfg | OK. userinfo 566 B. |
| a3_new_poke | same | + name flips | OK (the mod's own name bus: 5 userinfo pairs in 3 s). |
| **a4_new_usercfg** | 1.10.23 / 1.10.23 | **user's cfg** | **REPRODUCED**: no server command acked from entry (in flight 60 -> 233 in 19 s, snapshots 4-9 KB); at +20 s every client packet a fragment (infrag 60/s, in 0), client `MAX_PACKET_USERCMDS` x10840, upload never done, timed out. |
| a5_old_usercfg | 1.10.22 / 1.10.22 | user's cfg | OK, full lobby + ready + mission. |
| b1_srvnew_clold | 1.10.23 / 1.10.22 cgame | user's cfg | OK. |
| b2_srvold_clnew | 1.10.22 / 1.10.23 cgame | user's cfg | DEAD at CS_PRIMED: every client packet a fragment from +11 s, timed out. |
| c1_new_clprobe | 1.10.23 / 1.10.23 + cl_netProbe | user's cfg | passed this time; CLNET at entry: 4 unacked = 1514 B (userinfo 495, coopsync begin 79, `cp` pak checksums 371, userinfo 545). Recovery is luck. |
| d1, d2 / **d3** _base_usercfg | released behaviour (`--parkbytes 0`, GOG client exe) | user's cfg | d1, d2 OK; **d3 DEAD** (64 s of fragment-only client packets, in flight 256, parked 1236). Baseline: 2 of 5 user-cfg joins died (a4, d3). The dead run's client ends with 602 of 3119 challenge/Armory UI cvars wrong. |
| e1-e5_fix_usercfg | **fix** exes + lobby fix | user's cfg | **5 of 5 OK.** In flight max 44 commands (<= 2400 B), parked peak 328-332 for ~1.5 s after the merge (293 seta + 5 coopsave) then 0, snapshot max 5.2 KB (was 21.5 KB), 0 s of fragment-only client packets, 0 s without a client packet; upload done in 36 s; UI cvars identical to d1 (3119, 0 differ). |
| f1_fix_full | fix | user's cfg | **OK**: 295 s in the lobby, ready-up, briefing 441 s (harness did not skip it), 0 s client silent / fragment-only, in flight max 44 (lobby) / 64 (briefing), parked max 332 / 105; no timeout; merge OK; UI cvars identical to d1. Shots `H:\hzm_archive\joinflood1_fix_full\pc1\maintt\screenshots\`. |
| f2_fix_two | fix, 2 remote clients | user's cfg x2 | OK network-wise (lobby 168/149 s, briefing 7 min: 0 s silent, 0 s fragment-only, in flight max 47/67); harness could not skip the briefing (Use from console inside the slide menu) -> fallback added: rcon `map m1l1`. |
| f3_fix_full_m1l1 | fix | user's cfg | OK: lobby 294 s, briefing, m1l1 362 s (client stayed a spectator - harness spawn step fixed after). In flight max 44/64/62. |
| **f4_fix_two_m1l1** | **fix, 2 remote clients** | user's cfg x2 | **ALL PASS: lobby 318/299 s, ready, briefing, m1l1 219 s spawned and riding the truck; 0 s silent / fragment-only for both; in flight max 44 (lobby) / 64 (briefing) / 61 (m1l1); parked peak 322 for ~1.5 s after each merge then 0; no timeout; both uploads merged (rank T/3 on the scoreboard); UI cvars = d1 except 1 challenge that progressed in the mission (0/8 -> 1/8).** Shots `H:\hzm_archive\joinflood4_fix_two_m1l1\pc1|pc2\maintt\screenshots\`. Seen at the very end only: 6 s of 200-600 ms ping on client 1 while the harness took its screenshots (in flight rose to 26, recovered). |
| f5_listen_fix | fix exe as LISTEN host + 1 remote client | user's cfg x2 | ALL PASS: host lobby/briefing/m1l1 normal, no SVNET for the host's own loopback client (exempt); remote client: lobby 148 s, m1l1 168 s, 0 s silent / fragment-only, in flight max 44/61/56, upload merged in 23 s. |

## Bound to state

With the fix a remote client never has more than 2400 bytes of reliable commands in flight (observed max 67
commands); bursts wait in the server-side park (observed peak ~330 for ~1.5 s after the progression merge, from the
Armory lock export + challenge export, then 0). Snapshots max ~5.8 KB (was 21.5 KB). Pre-existing, not changed:
one ~450 ms server frame at the merge (script cost of xp_identify / exports).

## Ship steps (coordinator)

1. Engine: cherry-pick 15732bb2 into the release tree, build `omohaaded` + `openmohaa` in the release build dir
   (USE_RENDERER_DLOPEN=ON). game.dll / cgame.dll unchanged.
2. Mod: merge `joinflood-next` 84f71d6d (`coop_mod/lobby.scr`) into coop-wip; code pak.
3. Players: new `openmohaa.exe` (the fragment fix is client-side) + code pak. Servers (public + any self-hosted
   dedicated): new `omohaaded.exe` + code pak; the public servers can then drop their loose `lobby.scr` override.
   Old clients on a new server are better off (small snapshots) but keep the client-side fragment limit until they update.
