# Loading-screen cinematic (engine playback) - 2026-10-18

Engine: branch `loadcine-next` (off rel-1.10.25-netfix dfc7079f = release exe lineage, exe aa8304ff), worktree
`openmohaa-hzm-loadcine`, commits 8df369af + follow-up. Design: docs/ENGINE.md "Loading cinematic". Exe only (no cgame/game/ded change).

Clip: `loadclips/<name>.hzlc` in the fixes pak, made by `docs/tools/gen_loadclip.py clip FRAMES NAME` (+ `pak`, `info`).
Packed 1024x512 JPEG flipbook (16:9 squeezed, drawn "cover"), 30 fps, loop-blended. Size = frames x ~25-70 KB
(placeholder dossier, text-heavy worst case: 69 KB/frame, 21 MB for 10.5 s; 512x256 q70: 25 KB/frame, 7.6 MB). Real game footage is
smoother: expect 25-45 KB at 1024x512, ~10 MB per 10 s; share clips across maps (rules take several clips).
Mod side (not applied, mod repo untouched): mod/loadingbar_widget.txt (widget into ui/loadingbar.txt) and mod/loadclips.txt rules.
cvars: cl_loadCinematic (1), cl_loadCineFps (30), cl_loadCineFadeMs (450), cl_loadCineVsync (1).
Note the HZM load design has no progress bar (stock bar only with ui_loadClassic 1); tip strip + medal draw over the clip.

Measured (harness hudfeed2, m1l1 listen load, warm, vsync 1 as the user plays, 4 ON/OFF pairs per setting; run cE):
 30 fps: ON 4211 ms vs OFF 4022 = +4.7%;  24 fps: ON 4196 vs 3952 = +6.2% (noise +-5%; loads are only ~4 s).
 Drawn clip frames: ~100 distinct in 4.2 s (~24 fps average; the rest of the time is inside blocking calls).
 Stalls: max gap 314-361 ms, one gap >200 ms per load - the SAME one the OFF baseline has (skel->alias, before
 coop_aircraft.scr); others 100-200 ms: 3-4 per load. Decode 1.6 ms/frame avg, 3 ms max.
 Swap interval: during=0 restored=1 now=1 on every load.
Remaining stall sources (not fixed, need renderer/game DLL ticks): gl2 R_Init (not visible), skel/alias parse blocks.
