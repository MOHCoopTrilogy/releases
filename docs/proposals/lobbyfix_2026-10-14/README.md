# lobbyfix 2026-10-14 (bug-3913 .. bug-3916)

## HANDOVER
Mod worktree `C:\mohaa-coop-dev\hzm-mod-lobbyfix`, branch `lobbyfix-next` (from coop-wip d5d4f6ce), HEAD 59f97938. Code pak only, no engine change. Nothing deployed, pushed or released. buglog entries 3913-3916 updated.

| bug | state | commits |
|---|---|---|
| 3916 SAS stuck short of gate | FIXED + proven (harness lf3): `maps/m1l2a.scr::coop_sasGateFailsafe` - stage 1 re-issue move (20 s), stage 2 warp to a hidden friendly node near the site (40 s), stage 3 charge usable without him (60 s). Gate, then flak. blowdoor/blowflak honour `level.coop_gateNoSas/coop_flakNoSas`. Dev cvars default off: `coop_sasfs_fast 1`, `coop_sasfs_test 1|2` | 128d1656, 4df3274d |
| 3913 mannequin stays | FIXED + proven (lf2-lf4): owner-gone check in the idle loop + `lobbyMannequinReaper` | 0621420e, ea9124a7 |
| 3914 bottom bar | FIXED (lf4 screenshot of the default bar; click path not driven): `coop_mod/lobbyui.scr`, LOADOUT opens the co-op armory directly, Allied/Axis/Coop/Back sub-bar removed, Service Record stays | 08ab745c |
| 3915 only player 1 changes uniform | NOT REPRODUCED. Two clients with identical unlocks both change uniform and both mannequins swap (lf4). Probable cause: server refuses LOCKED skins (SHOW-ALL-WITH-LOCK) so a friend without the unlock sees no change while the user (all unlocked) does. Only a developer-gated `ARMSKIN apply` println added. Ask the user whether the friend saw "Uniform locked" | c1e18098, 59f97938 |

Ship: code pak only - pack `lobbyfix-next` like the release code pak (`zzzzzz_co-op_hzm_mod_code.pk3`, scripts/ui/cfg, no assets), then the usual release/What's New steps. Files changed: coop_mod/helmet.scr, coop_mod/lobby.scr, coop_mod/lobbyui.scr, maps/m1l2a.scr.

## Harness
`run_lobbyfix.py <run> [--skip-sas]` wraps `joinflood_2026-10-14/tools/run_joinflood.py` (released exe + dlls, hudfeed5/hudfeed4 slots, DISPLAY2). Gotchas learned: script `println` is developer-gated (server cfg patched to `developer 1`); fake-client unlock records are random per seed, so give both clients the same known unlocks before comparing skin changes; name-bus tests must not reset the name themselves (the server does). Runs: `H:\hzm_archive\lobbyfix\lf1..lf4` (lf3 = SAS stages, lf4 = skins/mannequin/bar).
`patch_sas.py`, `patch_buglog.py` are the one-off patch scripts.
