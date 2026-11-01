# Film Room - hand-over (2026-11-01)

The demo features around the server recorder (`../demo_editor_2026-11-01/SERVER_RECORDER.md`), and a
home for them in the menu. Not released.

| Where | Commit |
|---|---|
| engine, branch `filmroom` (worktree `openmohaa-hzm-filmroom`, from `rel-1.10.38-engine` 6c014c8d) | 0506e24b, 044016df |
| mod `hzm-mohaa-coop-mod` | 359446b0 |
| attic generator `../kickoff_2026-10-18/menus3d/make_main3d.py` | base repo (film hotspot + beam emitted) |
| art generator `tools/gen_filmroom_art.py` | base repo; outputs `textures/mohmenu/filmroom/*` (git-ignored images, packed from disk by build.ps1) |

## What the player gets

- **The Film Room** (`ui/filmroom.urc`): the attic's projector on the long counter is its door.
  Highlighted, the projector switches on: the housing lights, the lens glows and a flickering beam
  shines across the counter. Clicking it flies the camera to the projector, then opens a projection-booth
  browser of every demo. Each has a picture, type, maps, length, date and players, and can be played,
  made into a video, renamed or deleted. It also has filter tabs, the instant-replay length, and a
  credits button (the classic room's projector, which used to start the credits, opens the Film Room now).
- **Instant replay, HOME**: the last `cl_replay` / `sv_replay` seconds (default 120) as a demo, no
  recording needed. When hosting it covers the whole map (a ring in the server recorder); on someone else's
  server it is the client's own ring of what it received.
- **Any player's eyes, P** in a whole-map demo (`demo_pov`).
- **Clips, [ ] \\** (`demo_markin`, `demo_markout`, `demo_export`).
- **Tactical view, T** (`demo_tactical`): straight down, roofs clipped (gl2).
- **Server demos**: *Get this server's last match* in the Film Room (`getdemo last`, `demolist`).
- **Markers** on the timeline already existed (kills, deaths, AI kills, objectives). Whole-map demos now
  give them map-wide.

## How it works (the parts worth knowing)

- **Two recorder streams, one frame of input** (`sv_demo.c`). Entities, commands, sounds, prints and
  the cgame-message slot are gathered once and written into both the file and the ring.
  `SV_CopyCGMSlot` copies the slot into each stream without consuming it, and `SV_ResetCGMSlot` clears
  it after the frame.
- **Replay keyframes**: every 30 s a gamestate (flagged *skip*) and a full snapshot are written into
  the ring. A save starts at the newest keyframe older than the window and leaves the later skip
  gamestates out. The configstring commands between them carry the state. The client ring builds its
  keyframes from `cl.gameState` and `cl.snap` (`FR_BuildGamestate`, `FR_BuildFullSnapshot`) in place of
  the message that carried that snapshot.
- **Other players' playerStates after svc_EOF** (`SVR_WriteExtension` / `CL_FR_ParseExtension`), using
  magic 0x48 and version 1. Each player is delta coded, with a full state every 40 frames. Any client
  stops reading at svc_EOF, so old builds play these files unchanged. A seek invalidates the delta
  chains (`CL_FR_InvalidateExtension` in `DE_SeekTo`), so for up to a second after a seek P shows the
  recorded player.
- **`.dmi` info** (an info string) and `.jpg` (renderer `demothumb`, gl1 and gl2) sit beside every demo.
  Rotation and the Film Room's delete and rename handle all of them, plus `demos/cameras/<name>.cam/.names`.
- **Downloads** reuse the in-game UDP download channel. Only files directly inside `demos/` with
  `.dm_N`, `.dmi` or `.jpg` are allowed, on their own switch (`sv_allowDemoDownload`, default 1).
  `sv_allowDownload` and the pk3 rules are unchanged. `@last` is the newest *finished* demo, by
  `.dmi` time + length. While a download runs the server sends that client no snapshots, so the game
  holds still for those seconds, and the button says so. `CL_FR_DownloadDone` finishes it without the
  connect-time `CL_DownloadsComplete` (which would reload the level). The local file is named
  `<server>_<date>_<map>` from the downloaded `.dmi`.

## Measured / verified (harness `G:\mohaa-srvrec`, live 3D attic with `ui_atticMain 1`)

- **Host replay** (server ring, `sv_replay 60`): 75 s saved; the ring used 1.2 MB. Average 0.20 ms
  per frame with both streams running.
- **Client 2's replay** (client ring): 47 s saved; the ring used 455 KB.
- **`demo_pov 1`** shows client 2's own view: a different place, a different compass.
- **Tactical view** set `r_znear` 1380; rooms were visible from above.
- **Clip export**: a 6.0 s, 190 KB clip saved and played back.
- **`getdemo last`** against my dedicated server fetched its finished m2l1 demo (264 KB) and `.dmi`
  in about a second, and it shows under SERVER.
- **Attic**: the projector hotspot's glow lands on the projector, the board writes FILM ROOM, the
  fly frames the projector, and arrow keys / pad reach it (Right from MULTIPLAYER).
- **Film Room**: list, picture, details, every tab, rename and back, the replay-length selector.
  Selecting the same film twice keeps its picture (`RegisterShader`, not `RefreshShader`).

## Traps hit here (also in the bug log)

- **The harness showed the FLAT main menu**, a picture of the attic, because it never set
  `ui_atticMain 1`. Three rounds of hotspot checks were done against it: no camera flies, no
  Scene3D debug output, captions from the flat room. Launch harness clients with
  `seta ui_atticMain 1` to test the 3D attic.
- **`ui_scene_hot` is the hotspot's 1-based position** in the `scenehot` list. A new hotspot goes
  LAST, or every later button's index (the radios) shifts.
- **`va()` rotates a few static buffers**: three in one call overwrote each other (a download name
  turned into log garbage). Format into locals.
- **Heredoc escapes**: `\n` and `'\\'` got mangled in shell heredocs twice more. Write patch scripts
  with the Write tool.

## Open

- **A faded scope frozen on screen when seeking past the end of a demo** (seen on a Garand,
  which has no scope). The scope fade runs on the game clock, which stops while the editor holds the
  last frame. What starts a scope fade there is not found yet. Demo editor / scope code, not the recorder.
- The classic (flat) room's projector hover still shows no sign. There is no "film room" chalk art
  for the flat room.
