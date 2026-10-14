# Remote join flood on the public dedicated servers (bug-3910, bug-3909, bug-3903) - investigation + fix

## HANDOVER (keep this current - the next session starts here)

- **Status (2026-10-14 14:45): root cause found and reproduced; fix built and committed; PROOF RUNS IN PROGRESS.
  Nothing deployed, pushed or released.**
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
| d1-d3_base_usercfg | released behaviour | user's cfg | (running - failure rate) |
