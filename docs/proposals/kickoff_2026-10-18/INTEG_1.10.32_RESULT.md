# v1.10.32 integration result (2026-10-19)

Nothing deployed, published, pushed or restarted. coop-wip was NOT advanced: its checkout has uncommitted restore/generator state (fixes-pak base copies, regenerated armory cfgs), so the merge lives on branch `integ-1.10.32-mod` (worktree `hzm-mod-integ`, HEAD at the time of writing = lobbyall dc1d24a5 merge on top of 4313938b). To land it: `git -C hzm-mohaa-coop-mod merge --ff-only integ-1.10.32-mod` after checking `git status` there (the dirty files are not touched by the merge).

## Engine: branch `integ-1.10.32` (worktree `openmohaa-hzm-integ`, built in `.cmake`, Release, DLOPEN, 4 jobs)
Base rel-1.10.25-netfix dfc7079f (live exe aa8304ff). Merged with no conflicts: hdring-engine 37a734bb, iconprompts-next 8cf29bf3, textfeed-next ba72a485, loadcine-next 7197b285, armory-engine 845aaf16, gamepad-next 425c9834 (the 6cb3fc2a in the brief does not exist; 425c9834 is the tip and contains the netfix merge). All six verified with `merge-base --is-ancestor`. Extra commits: COOP_HDRING defined; loadcine play-once/.hzlc v2 (the code was an uncommitted edit in openmohaa-hzm-loadcine, snapshot 9374a21c, bug-4092) plus `LOADCINE skip ... why=` log lines.

Release set staged in `openmohaa-hzm-integ/release_set/` (md5s in `integ_release_set_md5.txt`):
- openmohaa.exe fe2d405d6e7af1543d63ddbb19e1fe6f (NEW)
- omohaaded.exe 43d6691555d99d71ff5929ccd33a3c2d (NEW)
- cgame.dll 7b07f858e21018092ee2b5ffe5d90661 (NEW)
- game.dll 126a66e3... = RELEASED (fgame sources identical to the progsync tip; no rebuild needed)
- renderer_opengl1.dll a15882c4 / renderer_opengl2.dll 8296bf86 = RELEASED (renderer sources unchanged; my rebuilt DLLs hash differently, do not ship them)

`$expect` for deploy_window: `@{ 'openmohaa.exe' = 'fe2d405d'; 'cgame.dll' = '7b07f858'; 'renderer_opengl2.dll' = '8296bf86' }`. deploy_window copies from `openmohaa-hzm\.cmake` (the base engine tree), so the six files above must be placed at those .cmake paths first (game.dll and the renderers = the released bytes, omohaaded = the new one). Not done by me.

## Mod: branch `integ-1.10.32-mod`
Merged in order: debrief, menu-debrief, gunner-rearm, smoke-consume, surrender, hints, iconprompts, hdring, textfeed, alarmplace, alarmsnipers, alarmveh, objectives, mortar, searchlight, lobbyall (twice: + dc1d24a5), c96, gunfit2, armory (one conflict, coop_defaults.cfg: kept both lines), gamepad (mod). rewards/t2l1 were already in coop-wip. After each merge: depthscan2 / linecheck / quotecheck / prosecheck on the changed .scr (all PASS, 57 files), plus at the end check_mp_isolation (22 passed), gen_loadout check PASS. The other generator checks fail identically before and after (CRLF checkout artefacts, untracked generated files, pak files not in the worktree); real content differences only: gen_mp_armory regenerates 152 tiles (deploy regenerates them) and one blank line in coop_defaults.cfg (committed).
Fixes made during integration (each its own commit, buglog 4087-4092):
- missioncomplete.scr: lobbyAlways read `level.coop_mpRun` in a form check_mp_isolation 7a refuses (would have blocked the build).
- **officer.scr coop_reinf_count yielded (alarmplace-next), so `exec` returned a thread pointer and every officer reinforcement squad spawn died with "int < pointer" (bug-4090).** Fixed and probe-verified. The alarmplace-next branch itself still has the bug.
- ui/loadingbar.txt: my own splice error (stray `resource and BEFORE...` line, bug-4091); loading cinematic now proven.
- buglog duplicate bug-4005 -> gunner-rearm entry is now bug-4086. Hint updates (6), loadcine hook, What's New card + version cfg (v1.10.32) applied.

## Fixes pak (docs repo commit e1871c5)
563 members, 46.7 MB, `gen_fixes_pak.py check` OK. Added: C96 no12u model (ship + ship2 hands/rows/Trench, 9 tiks as base pins), 24 icon-prompt tgas, m1l1 load clip (only one finished clip exists). HD ring ramp was already in. Built pak md5 daa35ed3dd6097ae894fdf2d570cdfce is in the base mod folder (rebuild after any source change).

## Regression (private harness G:\mohaa-hudfeed5\integ, integ exe/cgame/game, released renderers, fresh home, integ code pak + new fixes pak)
| item | result |
|---|---|
| maptest phase 1, all 54 campaign maps (3 batches) | PASS: every map loaded; only stock-map script errors (m1l3b, m4l0, m6l3c, e1l4, t2l4 gags) in files the merges do not touch |
| lobby hop (menu start -> lobby -> mission -> level end -> lobby -> next), before and after lobbyall dc1d24a5 | PASS, 0 script errors. Single m1l1 (chapter briefing) was not driven to the end (briefing slideshow is long in the harness) |
| Armory open | OPENS and lays out (tabs, cards, compare, locked rows) but the 3D previews (operator and guns) render as BLACK SILHOUETTES in the harness. **UNRESOLVED / needs a look**: lane proof (armory-engine build) shows textured guns. Not bisected: the armory-engine exe and the released exe both failed to take harness input (F12 step never ran), so the A/B could not be made. The lobby 3D mannequin is textured, so it is specific to the UI model widget |
| HD ring + icon prompt (hold) | PASS: heal icon inside the HD ring, key cap + "Hold" (test ring `coop_hdRingTest` itself not visible as the harness player stays spectator) |
| text feed line | PASS (feed lines at left, new style) |
| alarm pull + snipers | PASS (e3l1: 2 then 4 snipers on audited roof spots) |
| counter-attack defend-zone flow | PASS (e3l1 to 0:00, zone leave/enter/lost states, 0 script errors) |
| mortar fire | PASS (m3l2 crew, tube, warned round, damage) |
| searchlight | PASS (m4l3 undetected/detected/calm/ally); only the test driver's own "health must be greater than 0" |
| surrender convert | PASS (1/1 active, 0 errors) |
| pad menu | PASS (virtual pad drove the main menu, "Gamepad support ready 334 ms") |
| loading cinematic m1l1 | PASS after the two fixes above (LOADCINE begin/once=1/end, frame + tip strip + medal seen) |
| C96 | PARTIAL: files load, shader loaded, no TIKI errors; the gun was never equipped in the harness so firing/reload was not seen |
| dedicated server + 2 clients, new binaries | PASS: both clients joined, progression merged for both, no timeouts, 0 silent seconds, snapshots max 3.7 KB, both ran to the end. Caveat: the first harness check "ready-up launched" FAILED because the new lobby auto-skips an EMPTY lobby after 15 s (server started on co_lobby1 with nobody yet), so the clients joined the briefing; the harness then loaded m1l1 locally. Confirm that an idle public server on the lobby map moving on by itself is intended |

## Open / for the coordinator
1. Armory 3D previews black in the harness (above) - decide whether to check on the real client before release.
2. Public servers use loose `lobby.scr` overrides (public_servers\srv*\maintt\coop_mod\lobby.scr); they shadow the new lobby.scr (timeouts, empty skip, lobby objective lists). `setup_trilogy.py` step in the checklist must regenerate or drop them.
3. publish_release.ps1 was extended (commit 4a4b3d6): NoInstaller zip every release (split in parts under 2 GB, GitHub's asset limit; ~8 GB total), ModFilesOnly zip only when all engine binaries match the previous manifest (not built this time), SHA256SUMS.txt and the "Which download?" + checksum blocks appended to the notes. Parse-checked only, never run (dry run does not reach it). README download section and WINDOWS_SECURITY link added.
4. docs: TRAPS is at its ceiling so the new traps (exec of a label that yields returns a thread; splice snippets by block, not first keyword; isolation checker sanctions only `level.coop_mpRun == 1`) are in the buglog only.
5. G: had 0 bytes free; moved G:\mohaa-adsanim3\runs to F:\hzm_archive. adsanim\runs (50 GB) and hudfeed2\runs (173 GB) still on G:.

Drafts: `RELEASE_NOTES_v1.10.32_DRAFT.md`, `WHATSNEW_v1.10.32_DRAFT.md` (already applied to the mod).

## Update (blockers closed, 2026-10-19 10:30)
- Armory black previews: NOT an engine or renderer problem (released exe, released DLLs, rebuilt DLLs, released fixes pak all behaved the same; armory-next alone was textured). Bisected on the mod to coop_mod/lobby.scr: the new empty-lobby 15 s skip sent the harness server (started on co_lobby1 with nobody) on to the briefing, where the Armory UI opens without the lobby state. With `coop_lobbyTimeout 0` on the harness server the integrated Armory is textured. Not a player-facing bug. Renderers: sources unchanged, ship the RELEASED DLLs. CL_Draw3DModel aspect change survived (verified in the diff).
- One client session shows HD ring + icon prompt (lobby) and the textured Armory: `integ_ring_icon_armory_sheet.jpg`.
- C96 fire and reload in the integrated build: `integ_c96_fire.gif`, `integ_c96_reload.gif` (hip view; the muzzle-up pose in the fire frames and the bolt cycle were not judged against the design).
- Merged lobbyall-next 3662aed5 (23e8a5d2): scanners PASS, isolation 22/0, lobby hop re-run (m1l2a chain) 0 script errors.
- Public servers: loose files under srvN/maintt are only the three trilogy map scripts (m6l3e, t3l2, e3l4/Outro), lobby .pth caches and saves; no lobby.scr or other mod file shadows the new mod. `public_servers/aside_overrides.py [--apply]` (never touches saves) is in the release checklist.
