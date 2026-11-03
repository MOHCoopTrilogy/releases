# Modern MP front-end (2026-11-02)

User: "modernize the server browser and the start game menus in the multiplayer lobbies. Use the same camera zoom to
specific places (armory, service record, join game, host game)".

| piece | where |
|---|---|
| generator (urcs, room-at-pose includes, map names, localization, hover art -> menus3d pak) | `make_mpui.py` (run after `../mphub3d_2026-11-02/make_mphub3d.py`; `--base-pk3 <menus3d pak>`) |
| static checks (no client) | `check_mpui.py` |
| harness (private client `G:\mohaa-mpui`, non-primary display only) | `mpui_run.py setup / walk / host / pad / film` |
| mod | branch `mpui-next` (worktree `C:\mohaa-coop-dev\hzm-mod-mpui`) |
| engine | branch `mpui-engine` (worktree `H:\hzm_work\eng-mpui`): `cl_uiserverlist` hzmbrowser, `cl_uiscene` sceneleave 1, `uivertscroll` paper, `gserverlist.c` LAN socket, `cl_dedicated` ui_maxclients |
| evidence | `H:\hzm_work\mpui\deliver\` (MP4 + stills) |

## Re-shoot of the HOST A CO-OP GAME screen (pending: no free non-primary display on 2026-11-02)

Needs a NON-primary monitor (the harness refuses the primary by itself) and no other game client running.
Shoots 4:3, 16:9 (720p) and 21:9; the host-screen stills are `mp_walk_<res>_4[3-6]*.tga` and `mp_walk_<res>_46b_dedicated_on.tga`:

```
cd C:\mohaa-coop-dev\docs\proposals\mpui_2026-11-02 && python mpui_run.py setup && python mpui_run.py walk 43 && python mpui_run.py walk 720 && python mpui_run.py walk 219
```

Results land in `H:\hzm_work\mpui\runs\mpui_walk_<res>\`. Note: the last 4:3 attempt (22:37) stalled right after the attic
MP door with the loose `coop_defaults.cfg` newly copied into the client homepath; if it stalls again, delete
`G:\mohaa-mpui\home\maintt\coop_defaults.cfg` and re-run to tell the two apart.
