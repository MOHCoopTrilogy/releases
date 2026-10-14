# Progression follows the player (bug-3903) - design + handover

## HANDOVER (keep this current - the next session starts here)

- **Status (2026-10-14 12:30): DONE and harness-proven (run r4, 28/28 checks). NOT deployed, pushed or
  released** - shipping needs the user's word (see "Ship steps").
- **Engine:** branch `progsync-next`, worktree `C:\mohaa-coop-dev\openmohaa-hzm-progsync`, base 0206e3c9
  (= v1.10.22 source), head **e8838a89** (5 commits). Build dir `.cmake` there; from PowerShell:
  `cmake --build . --config Release --target fgame cgame --parallel 4` -> `.cmake\code\server\fgame\Release\game.dll`,
  `.cmake\code\client\cgame\Release\cgame.dll`. `openmohaa.exe` / `omohaaded.exe` are NOT changed.
- **Mod:** branch `progsync-next`, worktree `C:\mohaa-coop-dev\hzm-mod-progsync`, base coop-wip 4f8a1019
  (= v1.10.22), head **a513b08c** (`coop_mod/xp.scr` xp_waitSync + call in xp_identify, `coop_mod/challenges.scr`).
- **Code map:** `code/fgame/bg_coopsync.h` (record list, merge rules, wire encoding, digests - shared by both
  sides), `code/fgame/g_coopsync.cpp` (server), `code/cgame/cg_coopsync.c` (client); hooks: g_client.cpp
  (connect / disconnect / userinfo -> coop_syncstate), gamecmds.cpp (G_ClientCommand), g_main.cpp (G_RunFrame),
  scriptthread.cpp (FS_WriteContent), cg_main.c (CG_Init / CG_Shutdown), cg_view.c (CG_DrawActiveFrame),
  cg_servercmds.c (`coopsave`).
- **Tests:** `tools/merge_selftest.c` (offline: merge rules, encoding, digests - ALL PASS);
  `tools/run_progsync.py run <name> [--phases 1,2,3,4,5]` (private copy G:\mohaa-hudfeed5, sub-folders
  `progsync\` (new dlls) and `progsync_old\` (released dlls), fake qkey identity, IPv4 127.0.0.1 only, ports
  12781-12784; everything is moved to `H:\hzm_archive\progression_sync\<name>\`).
- **Run r4 results** (`H:\hzm_archive\progression_sync\r4\results.json`, screenshots in `...\r4\pc\maintt\screenshots\`):
  1. remote client, dedicated server with NO record: the PC's 5000 XP shows on the server (scoreboard rank T/4,
     `p1_scoreboard_rank.jpg`); upload took 6.8 s (6 chunks); award+flush and an unlock came back to the PC
     byte-identical (paths with `/` intact); the first-join burst of rank-unlock rewrites reached the PC as 1 write;
     XP awarded right before a disconnect (no flush) was in the PC file at the disconnect.
  2. reconnect mid-mission and a map change on the same server: `already_same=7`, nothing uploaded, total intact.
  3. the same PC on server B holding an OLDER, different record: server and PC both end with the union of
     unlocks/blueprints, the higher challenge progress, the higher XP; the PC's own pin choice won.
  4. old (released) client on the new server: as today, nothing written on the PC, no wait.
  5. new client on an old (released) server: one handshake line, joins normally, nothing written on the PC.
  6. listen host: no handshake/upload/merge/wait; writes its own files as today.
- **Earlier runs** r1-r3 (archived) found the defects logged as bug-3904..3908 (escape `%`->`.`, the client
  fragment stall + flood protection, a build include, the join burst, harness IPv6 socket).
- **Open / not done:** no tamper check (decision row 15 default: honour system). Docs: one TRAPS line added (T8,
  client->server bulk limits) in the base checkout, uncommitted because TRAPS.md carries other sessions' edits.

## Ship steps (only with the user's yes)

1. Merge engine `progsync-next` (e8838a89) into the next integration branch, and mod `progsync-next` (a513b08c)
   into coop-wip; rebuild `game.dll` + `cgame.dll` from the merged tree (other lanes touch the same files - the
   hooks are small and self-contained, see "Code map").
2. `build.ps1` packs the code pak (xp.scr, challenges.scr) and deploys `cgame.dll`; `game.dll` is the manual copy
   (back up as `game_pre_progsync_bak.dll`) into `G:\mohaa-gl2` and the GOG root.
3. Release (publish_release.ps1): players need the new `cgame.dll` for their progression to travel; anyone who
   hosts needs the new `game.dll` + code pak. Old clients keep working exactly as today.
4. Public servers: stop both, put the new `game.dll` + code pak in place (the GOG-root `game.dll` is locked while
   `omohaaded.exe` runs), start them. Records already on the servers merge with each player's own on his first
   join with the new client - nothing to copy by hand.

## The problem in one paragraph

XP, rank, challenges, unlocks, pins, pending unlock names, medals and found blueprints are written by
whichever machine HOSTS the game, into `<its home>/maintt/coop_mod/save/<type>_<player id>.dat`. On your
own listen server that is your PC, so it works for the host. On anyone else's server (a friend's listen
server or the public dedicated servers) the files are written on THEIR disk: you start from zero there and
what you earn stays there.

## The fix in plain language

Your own PC's save files are the master copy. They travel with you:

1. **On join** (every map load), the game on your PC reads your own save files and sends them to the server
   while the map is loading. The server combines them with anything it already had for you (see "Merge")
   and writes the result into its own save files before the mod's scripts look you up - so the scripts,
   which are unchanged apart from a short wait, see your full progression.
2. **Whenever the server saves** your progression today (rank-up, unlock, challenge flush, mission end,
   blueprint pickup, 30/60 s autosaves), it also sends that file back to you, and your PC merges it into
   your own save file. No script save site had to change: the engine does this inside `fs_write_content`.
3. **On disconnect** your PC also folds in the last XP total the server showed you (it already sends that
   to you on every award), so XP earned in the last minute before you leave is not lost.

A listen-server host does none of this (his game and his server already share one set of files), so the
host case is unchanged.

## Merge rules (never lost, never doubled)

| file | rule |
|---|---|
| `xp_` | the higher total |
| `chal_` (`cid:progress\|...`) | per challenge, the higher progress; union of challenges |
| `unlocks_`, `medals_` (`a\|b\|c`) | union |
| `bpfound_` (`m_n\|m_n\|`) | union |
| `pins_`, `pend_` (preferences / a display queue) | the newest copy wins (yours on join, the server's afterwards) |

The same rules run on both sides (server on join, your PC on every download), so a stale or hostile copy
can only ever ADD progress, never take any away. Players who already played on the public servers before
the fix get the two records merged on their first join.

## Compatibility

- Old client on a new server: it sends nothing, the server behaves exactly as today.
- New client on an old server: the server ignores the upload and never sends anything back; nothing changes
  on your PC.
- The scripts wait (max 60 s; ~7 s for the test record, a few seconds more for a big one) only for a player whose
  upload has actually started - i.e. only on his first join of a server whose copy differs from his.
- Ships as a PAIR for full effect: `game.dll` (servers, and every listen host) + `cgame.dll` (every player).
  `openmohaa.exe` / `omohaaded.exe` are unchanged, so no protocol change. The script change (`xp.scr`,
  `challenges.scr`) is a bounded wait that is a no-op without the new game.dll.

## How it works (for the next engineer)

- Handshake (protocol 2), sent from `CG_Init` while the client is still CS_PRIMED: `coopsync begin 2 <7 digests>`
  (CRC-32 of each own record in an order-independent canonical form, `bg_coopsync.h`). Intercepted in
  `G_ClientCommand` BEFORE `G_ProcessClientCommand` (which refuses everything until the Player entity exists).
  The server compares with its own view (file merged with session cvar): all equal -> merge at once
  (`already_same=7`, the normal map-change case); else `coopsave want <types>` and `coop_syncstate` 1.
- Upload of wanted records: `coopsync d <type> <seq> <final> <declen> <chunk> <chunk>` (`!XX` escapes, `/` raw
  except in `//`; <= 2 args of 240 chars), ONE in flight, each acked with `coopsave got <type> <seq>`, resent
  after 3 s, >= 1.2 s apart (CG_CoopSync_Frame from CG_DrawActiveFrame). Why: the client exe never sends the
  2nd fragment of a >~1.3 KB packet and every packet carries all unacked reliable commands (bug-3905); a
  dedicated server drops an in-game client's command < 1 s after its previous one; `%` arrives as `.` (bug-3904).
  `declen -1` = no such file. Then `coopsync end` -> merge -> `coop_syncstate` 2, records that differ are sent
  down, `coopsave ack 2`. An upload that never ends goes FAILED after 120 s (no downloads that session).
- Server -> client: `coopsave <type> <part> <nparts> <chunk> ...` server commands (not stufftext, so the stufftext
  filter is not involved). `ScriptThread::FS_WriteContent` parks every write of `coop_mod/save/<type>_<id>.dat`
  for the client whose merged id matches; `G_CoopSync_Frame` (G_RunFrame) sends the newest copy at most once
  per second per record (a first join re-grants every rank unlock = dozens of rewrites in one frame).
- The client ignores `coopsave` unless it uploaded to this server this session; merges with the same rules;
  writes only if the result differs. `CG_Shutdown` folds `coop_xp_totalOwn` (pushed by `xp.scr` on every award)
  into the xp file, but only when the server acked AND the cvar changed during this session.
- A vid_restart re-runs CG_Init on a live connection: the server answers a second `begin` with just an ack.

## Safety

- The server can only ever cause your PC to write the seven known files `coop_mod/save/<type>_<your own id>.dat`.
  The file name is built on YOUR side from your own `cl_guid`; the server sends only a type word and content.
  Content is capped in size and limited to printable characters, and the merge means it can only add.
- **Honour system (no anti-cheat, as before):** a player can edit his own save files with a text editor
  (any XP, any unlock, any challenge) and every server he joins will believe him. Before this fix the same
  was true for the host on his own server; now it is true everywhere. Nothing stops this; that is the
  accepted design (decision rows 15-16).
- What a player could edit, concretely: `xp_<id>.dat` (one number), `chal_<id>.dat` (challenge progress),
  `unlocks_<id>.dat` (weapon/perk/cosmetic unlocks), `medals_<id>.dat`, `bpfound_<id>.dat` (blueprints),
  `pins_<id>.dat`, `pend_<id>.dat`, all plain text in `<home>/maintt/coop_mod/save/`.
- Identity is the `cl_guid` the client reports (as before). A modified client that reports someone ELSE's
  cl_guid could add to that player's record on that server, or replace his pinned challenges there - it can
  never remove progress. Same trust level the save ids had before this change.

## Test plan (private harness only, fake identities)

1. Remote client on a dedicated server, saves only in the client home: rank/XP shows on join; after an
   award + flush the changed files come back to the client home; after disconnect the XP is current.
2. Listen host: unchanged (no upload, no download lines in the log).
3. Reconnect mid-mission: nothing lost.
4. Same client on two servers in a row: progress from server A shows on server B.
5. Merge: server already holds an older/different record for the id: union/max result on both sides.
6. Old client (current release cgame) on the new server: unchanged behaviour.
