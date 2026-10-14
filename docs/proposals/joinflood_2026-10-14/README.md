# Remote join flood on the public dedicated servers (bug-3909 / bug-3903) - investigation + fix

## HANDOVER (keep this current - the next session starts here)

- **Status (2026-10-14 13:40): reproduction harness being built. Nothing fixed, nothing deployed.**
- **Branches / worktrees**
  - engine `joinflood-next` from e8838a89 (= v1.10.23 source), worktree `C:\mohaa-coop-dev\openmohaa-hzm-joinflood`,
    build dir `.cmake` there (configured like progsync's). Uncommitted: the `sv_netProbe` instrument
    (`tools/patch_netprobe.py`, server exe only - test tool, not for shipping unless decided).
  - mod `joinflood-next` from coop-wip 7a5211a0 (= v1.10.23), worktree `C:\mohaa-coop-dev\hzm-mod-joinflood`.
- **Harness:** `tools/run_joinflood.py` (private copy G:\mohaa-hudfeed5, sub-folder `joinflood\`, slot owner
  hudfeed5, IPv4 127.0.0.1 only, ports 12791 server / 12792-12793 clients, fake qkey identities with a veteran-sized
  record; `sv_lanForceRate 0` + client rate 90000 / snaps 40 / cl_maxpackets 100 = the internet path).
  Runs are moved to `H:\hzm_archive\joinflood\<run>\`.

## Evidence from the public servers (read-only)

- The user's record on his PC: chal 3256 B, unlocks 2532 B, pend 1508 B, bpfound 86 B, xp 4 B (sizes only).
  The servers' copy for him is EMPTY (chal 0 B, xp 1 B): the upload has never completed on either server.
- srv2 13:02:46 (stock lobby): COOPSYNC want (5 records) at +12 s; SVCMDQ 512 at +90 s; upload timed out at +132 s;
  client timed out at +164 s with 2663 parked.
- srv1 13:09:44 (patched lobby): want at +11 s; name change x2 at +52 s; SVCMDQ 512 at +104 s (ui_removehud only
  24, seta 396 -> 1143 in 8 s); upload timed out at +131 s; client timed out at +193 s with 1916 parked.

## Working hypothesis (to be proven or killed by the harness)

1. (v1.10.23) The client exe never sends the 2nd fragment of a client->server packet (bug-3905) and every client
   packet re-carries ALL unacknowledged client commands. The progression upload puts ~510-byte `coopsync d` chunks
   in that set and RE-SENDS one after 3 s when the server's `coopsave got` is late; with a userinfo (name/skin
   change) or a second chunk unacked at the same time the packet crosses ~1300 bytes and from then on nothing the
   client sends ever reaches the server -> no usercmds (phone-jack icon), no acks (server queue only grows), timeout.
2. (older, amplifier) bulk reliable pushes (lobby HUD loop, challenge/Armory seta exports) fill the 256 in-flight
   window; every snapshot re-carries the whole window -> ~10+ KB snapshots, 1300-byte fragments, slow acks; the
   `coopsave got` waits behind it in the FIFO, which triggers (1).

## Runs

(none yet)
