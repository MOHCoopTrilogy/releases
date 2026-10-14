# Progression follows the player (bug-3903) - design + handover

## HANDOVER (keep this current - the next session starts here)

- **Status:** engine + script code written and BUILT; offline merge self-test passes; in-game harness written,
  first in-game run next. Nothing deployed, pushed or released.
- **Engine branch:** `progsync-next` in worktree `C:\mohaa-coop-dev\openmohaa-hzm-progsync` (base 0206e3c9 = v1.10.22
  source), commit 44e134ff. Build dir `.cmake` there (`cmake --build . --config Release --target fgame cgame --parallel 4`
  from PowerShell); outputs `.cmake\code\server\fgame\Release\game.dll`, `.cmake\code\client\cgame\Release\cgame.dll`.
- **Mod branch:** `progsync-next` in worktree `C:\mohaa-coop-dev\hzm-mod-progsync` (base coop-wip 4f8a1019 = v1.10.22),
  commit 42fe688c (`coop_mod/xp.scr` xp_waitSync + call sites in xp_identify and challenges chal_ensure).
- **Code map:** `code/fgame/bg_coopsync.h` (shared rules + wire encoding), `code/fgame/g_coopsync.cpp` (server),
  `code/cgame/cg_coopsync.c` (client); hooks in g_client.cpp (connect/disconnect/userinfo), gamecmds.cpp
  (G_ClientCommand), scriptthread.cpp (FS_WriteContent), cg_main.c (CG_Init/CG_Shutdown), cg_servercmds.c.
- **Tests:** `tools/merge_selftest.c` (offline, ALL PASS); `tools/run_progsync.py run <name> [--phases 1,2,3,4,5]`
  (private copy G:\mohaa-hudfeed5, sub-folders progsync\ + progsync_old\, fake qkey identity; results + homes are
  moved to H:\hzm_archive\progression_sync\<name>\).
- **Next:** run the harness phase by phase, fix what fails, then write the ship steps below.

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
- The server only waits (max 10 s) for a player whose upload has actually started.
- Ships as a PAIR for full effect: `game.dll` (servers, and every listen host) + `cgame.dll` (every player).
  `openmohaa.exe` / `omohaaded.exe` are unchanged, so no protocol change. The script change (`xp.scr`,
  `challenges.scr`) is a bounded wait that is a no-op without the new game.dll.

## How it works (for the next engineer)

- Wire, client -> server (sent from `CG_Init`, i.e. while the client is CS_PRIMED, before ClientBegin, which is
  also the only window without the 1-command-per-second flood protection): `coopsync begin 1`, then per record
  `coopsync d <type> <chunk> ...` (percent-encoded, args <= 240 chars because Cmd_Args_Sanitize truncates at 255)
  and `coopsync have <type> <decoded length>`, then `coopsync end`. Intercepted in `G_ClientCommand` BEFORE
  `G_ProcessClientCommand` (which refuses everything until the Player entity exists).
- On `end` the server merges with its session cvar AND its file, rewrites both, sets the entity var
  `coop_syncstate` 2 (1 while receiving), sends back what differs, then `coopsave ack 1`.
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
