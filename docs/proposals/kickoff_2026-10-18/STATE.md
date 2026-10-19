# STATE - overwrite at every handoff, never append, under 60 lines

**Written:** 2026-10-19 ~00:30 by the coordinator of the 2026-10-18 "v1.10.32 queue" session. Live = v1.10.31. NOTHING deployed/published/pushed.
**Next session: do the v1.10.32 INTEGRATION + RELEASE (below), then the queued lanes.** Running when written: loadscreen agent rolling out trailers per mission.

## Harness
`docs/tools/harness_turn.py wait|release|status <name>` (SLOTS=2, 15 min, free copy of hudfeed2/4/5 via harness_guard). "joinflood"-named exes on hudfeed* are OUR agents. H: missing -> G:\claude_scratch_archive. Agents must never `git checkout/reset` shared files nor kill processes by name (both happened: bug-4037 FEATURES.md recovered + uncommitted; check_mp_isolation lock line restored).

## DONE + proven, ready to merge (mod branches off coop-wip, worktrees hzm-mod-*)
- coop-wip itself: bug-3984 allysquad, bug-4003 rewards, 0e332991 reinf_mg float duty (bug-4036; MG pacing now real - replay before softening MG).
- debrief-next f25f00bb | menu-debrief-next 9b127297 | gunner-rearm-next 25dd8d81 (bug-4005 id clash - renumber) | smoke-consume-next ..534558b9 (coin flip, indoor cache m2l2c/m6l3b/c/d)
- surrender-next ..07203f2d | hints-next 32400cb3 (What's New must be rewritten) | iconprompts-next (+engine 8cf29bf3; needs COOP_HDRING define)
- hdring-next efde21f9 (+engine hdring-engine 37a734bb) | textfeed-next 50c0c33e (+engine ba72a485, cgame c94af889)
- alarmplace-next ..54b55098 (panels, MG team/alarm, counter timer/zones/edge ring/stay-in, lost-zone penalty + alarm-on-start whitelist m3l2 m4l1 m4l2 e3l2 t3l1; same chapter only)
- alarmsnipers-next ..eae14c18 (16 audited roof-deck spots on 6 maps) | searchlight-next 7547b329 | mortar-next c47c00fa (+church barrage fix bug-4032)
- lobbyall-next (lobby at every mission start + between levels, timeouts; campaign already did) | c96-next b8fb26fa (+ship files in c96_model_2026-10-18/ship, fixes pak not applied; public README credit TODO)
- gunfit2-next 553e3337 -> armory-next 2f456973 (Showroom Armory) + engine armory-engine 845aaf16 (exe: 3D aspect fix bug-4053, MAX_CVARS 16384 bug-4052)
- alarmveh-next (off by default coop_alarmVeh 0; truck m4l1/t3l1/m4l2, halftrack m3l3/t2l3 after mission halftrack); ROUTES_HOWTO.md for 6 maps
- objectives-next (phase 1: objx.scr mechanics, m1l3c log+hold, m2l1 radios; only ~4-5 min added vs 10-15 target)
- gamepad-next engine 6cb3fc2a (menus with pad incl. pull-downs/sliders; netfix merged) + mod cc13550a; Ally test zip G:\mohaa-gamepad\ally_package.zip (steps in README_ALLY.txt; user not yet told to install)
- loadcine-next engine (play-once + hold, .hzlc v2); m1l1 trailer2 7.8 MB approved; rollout to all missions running; mod widget hook pending.

## INTEGRATION (next)
Engine: one integ branch on the netfix release lineage merging hdring-engine, iconprompts, textfeed, loadcine, armory-engine, gamepad -> new exe + cgame + ded. Mod: merge all branches into coop-wip (alarmplace-next before alarmsnipers/alarmveh/objectives/mortar). Then gen_fixes_pak (C96 ship, HD ramp, icons, load clips), What's New card, FEATURES/HISTORY (docs at ceilings - prune), full regression harness run, user playtest, RELEASE CHECKLIST in NEXT_SESSION.md with user's game closed + "go".
## Design waiting: objectives phase 2 (more maps, actor actions, reach +10-15 min); alarm vehicle routes for 6 maps (user places markers).
## Queued: weapon anim lanes (ads_twohand README end: bolts every shot, ADS shimmer, same ADS mounted/cover/3p, correct hands, Colt slide); new main menu.
## Parked: code signing (Smart App Control) - free route SignPath Foundation (OSS licence + public GitHub Actions), cheap Certum OSS, paid Azure Trusted Signing.
